"""Build a preservation-only candidate package from verified Cycle 14 receipts."""
import argparse
import collections
import csv
import hashlib
import json
import re
import sqlite3
from pathlib import Path

import pymupdf

CITATION = re.compile(r'\b(?:20\d{2}[: ](?:INSC|PHHC|DHC|AHC|KHC|BHC|KAR)[: ]\d+|\(\d{4}\)\s*\d+\s+SCC\s+\d+|AIR\s+\d{4}\s+SC\s+\d+)\b', re.I)
SECTION = re.compile(r'\b(?:sections?|articles?|rules?)\s+\d+[A-Z]?(?:\([^)]+\))?\s+of\s+the\s+(?:[A-Za-z][\w-]*\s+){0,7}(?:Act|Rules|Constitution)\b', re.I)
CASE = re.compile(r'\b(?:CWP|CRWP|CRM-M|RSA|LPA|FAO|CRR|CRA-S)[- /]\d+[- /]\d{4}\b', re.I)
TYPE = re.compile(r'^\s*(?:JUDGMENT|ORDER|INTERIM ORDER|ORAL JUDGMENT|REVIEW ORDER|CLARIFICATION ORDER)\s*$', re.M | re.I)
DISPOSITION = re.compile(r'\b(?:petition|appeal|application)\s+(?:is|stands)\s+(?:dismissed|allowed|disposed of)\b[^.\n]{0,80}', re.I)
CORAM = re.compile(r'^\s*(?:CORAM|BEFORE)\s*:\s*[^\n]{4,180}', re.I | re.M)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line]

def csv_rows(path):
    with path.open(encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle))

def scan(pages, pattern, limit=120):
    return [dict(page=i, start=m.start(), end=m.end(), text=m.group())
            for i, text in enumerate(pages, 1) for m in pattern.finditer(text)][:limit]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('checkpoint', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--consolidation', type=Path)
    parser.add_argument('--repair', type=Path)
    args = parser.parse_args()
    root = args.checkpoint.resolve()
    dest = args.output.resolve()
    dest.mkdir(parents=True, exist_ok=False, mode=0o700)
    intake = {r['doc_id']: r for r in csv_rows(root/'recovery-register.csv')}
    restrictions = json.loads((root/'register.json').read_bytes())['items']
    blocked = {v.casefold() for i in restrictions for v in
               (i['doc_id'], i['source_sha256'], *i.get('derived_sha256', []), *i.get('hosted_paths', [])) if v}
    old = collections.defaultdict(dict)
    for r in rows(root/'independent.jsonl'):
        if r['status'] == 'verified' and r['actual'] == r['expected']:
            old[r['path'].split('/')[-2]][r['path'].split('/')[-1]] = r
    inputs = []
    for r in csv_rows(root/'PHHC_T1_RECOVERY_534_EXECUTION.csv'):
        digest = r['expected_sha256']
        pair = old[digest]
        if pair.keys() >= {'original.pdf','text.txt'} and pair['original.pdf']['revision'] == pair['text.txt']['revision']:
            inputs.append((r['doc_id'], digest, pair['text.txt']['actual'], pair['original.pdf']['revision']))
    for r in rows(root/'C14_EXTENDED_JUDICIAL.jsonl'):
        if r['status'] == 'uploaded-verified' and r['hf']['verified']:
            inputs.append((r['doc_id'], r['expected_sha256'], r['derived_sha256'], r['hf']['revision']))
    summary = json.loads((root/'C14_EXTENDED_EXECUTION.json').read_bytes())
    extra_folders = []
    official = {}
    receipts = list(summary['official_uploads'])
    if args.consolidation:
        live = args.consolidation.resolve()
        retry = live/'judicial-retry'
        staging_receipts = sorted(live.glob('staged-upload*/official-upload.json'))
        extra_folders = [retry/'extended-files']+[p.parent/'official-files' for p in staging_receipts]
        receipts.extend(json.loads(p.read_bytes()) for p in staging_receipts)
        journal = rows(retry/'extended.jsonl')
        verified = {r['revision'] for r in journal if r.get('verified')}
        attempted = {r[2]:r[0] for batch in journal for r in batch.get('result',[])
                     if r[1]=='verified-local'}
        for batch in journal:
            if batch.get('revision') not in verified or 'files' not in batch:
                continue
            for path,digest in batch['files'].items():
                kind = path.rsplit('/',1)[-1]
                original = path.split('/')[-2]
                if kind == 'text.txt':
                    inputs.append((attempted[original],original,digest,batch['revision']))
    for receipt in receipts:
        if not receipt['verified']:
            continue
        for r in receipt['entries']:
            if r['status'] != 'queued-for-upload':
                continue
            h = r['sha256']
            texts = [value for path, value in receipt['files'].items() if path.endswith('/'+h+'/text.txt')]
            if len(texts) == 1:
                key = r.get('doc_id',r['id'])
                official[key] = r
                inputs.append((key,h,texts[0],receipt['revision']))
    repairs = {r['doc_id']:r for r in rows(args.repair/'repair-register.jsonl') if r['status'].startswith('mapped')} if args.repair else {}
    conn = sqlite3.connect(dest/'search.sqlite')
    conn.executescript("""
    CREATE TABLE documents(id TEXT PRIMARY KEY, source_sha TEXT NOT NULL, text_sha TEXT NOT NULL, revision TEXT NOT NULL);
    CREATE TABLE citation_mentions(doc_id TEXT NOT NULL REFERENCES documents(id), citation TEXT NOT NULL, page INTEGER NOT NULL);
    CREATE INDEX mention_citation ON citation_mentions(citation);
    CREATE VIRTUAL TABLE pages USING fts5(doc_id UNINDEXED, physical_page UNINDEXED, derivative);
    """)
    seen = {}
    counts = collections.Counter()
    skips = []
    with (dest/'records.jsonl').open('w') as output:
        for doc, pdf_hash, text_hash, revision in sorted(set(inputs)):
            if doc in seen and seen[doc] != (pdf_hash,text_hash,revision):
                raise ValueError('Conflicting provenance for candidate identity')
            seen[doc] = (pdf_hash,text_hash,revision)
            if blocked.intersection(x.casefold() for x in (doc,pdf_hash,text_hash) if x):
                counts['restricted_excluded'] += 1
                continue
            reviewed = repairs.get(doc)
            lineage = None
            if reviewed:
                provenance = reviewed['provenance']
                if provenance['original_sha256'] != pdf_hash or provenance['legacy_derivative_sha256'] != text_hash:
                    raise ValueError('Repair provenance disagrees with preserved bytes')
                paths = {name:(args.repair/reviewed[name]).resolve() for name in ('pages_file','derivative_file')}
                if not all(path.is_relative_to(args.repair.resolve()) for path in paths.values()):
                    raise ValueError('Repair path escaped package')
                packed = paths['pages_file'].read_bytes()
                replacement = paths['derivative_file'].read_bytes()
                if sha(packed) != reviewed['pages_file_sha256'] or sha(replacement) != reviewed['derivative_sha256']:
                    raise ValueError('Repair artifact digest mismatch')
                if reviewed['derivative_sha256'].casefold() in blocked:
                    counts['restricted_excluded'] += 1
                    continue
                object_pages = json.loads(packed)['pages']
                physical_pages = reviewed['page_count']
                if [r['physical_page'] for r in object_pages] != list(range(1,physical_pages+1)):
                    raise ValueError('Repair physical pages do not match the page count')
                pages = [r['text'] or '' for r in object_pages]
                for obj,text in zip(object_pages,pages,strict=True):
                    if obj['text'] is not None and sha(text.encode()) != obj['text_sha256']:
                        raise ValueError('Repair page hash mismatch')
                lineage = dict(legacy_derivative_sha256=text_hash, replacement_derivative_sha256=reviewed['derivative_sha256'],
                    original_preservation_revision=provenance['hf_revision'],
                    replacement_format='physical-page-v1',
                    out_of_scope_pages=[row['physical_page'] for row in object_pages if row['text'] is None],
                    page_quality=[{k:v for k,v in row.items() if k!='text'} for row in object_pages])
                text_hash = reviewed['derivative_sha256']
                counts['repaired_candidates'] += 1
            else:
                folders = [root/folder for folder in ('extended-files','batch-files','official-files')] + extra_folders
                pdf = next((folder/(pdf_hash+'.pdf') for folder in folders
                            if (folder/(pdf_hash+'.pdf')).is_file() and (folder/(pdf_hash+'.txt')).is_file()
                            and sha((folder/(pdf_hash+'.txt')).read_bytes()) == text_hash),None)
                txt = pdf.with_suffix('.txt') if pdf else None
                if not txt or not txt.is_file():
                    counts['local_pair_missing'] += 1
                    skips.append(dict(doc_id=doc,status='local_pair_missing'))
                    continue
                raw, derivative = pdf.read_bytes(), txt.read_bytes()
                if sha(raw) != pdf_hash or sha(derivative) != text_hash:
                    counts['local_digest_mismatch'] += 1
                    skips.append(dict(doc_id=doc,status='local_digest_mismatch'))
                    continue
                with pymupdf.open(stream=raw,filetype='pdf') as source:
                    physical_pages = len(source)
                    if source.is_repaired or source.needs_pass or not raw.rstrip().endswith(b'%%EOF'):
                        counts['source_integrity_hold'] += 1
                        continue
                decoded = derivative.decode('utf-8')
                pages = [decoded] if physical_pages == 1 else decoded.split('\n\f\n')
                if len(pages) != physical_pages:
                    counts['unbound_or_partial_page_map'] += 1
                    skips.append(dict(doc_id=doc,status='unbound_or_partial_page_map',physical_pages=physical_pages,segments=len(pages)))
                    continue
            metadata = intake.get(doc,{})
            citations = scan(pages,CITATION)
            cases = scan(pages[:1],CASE,12)
            types = scan(pages[:1],TYPE,3)
            coram = scan(pages[:1],CORAM,3)
            disposition = scan(pages,DISPOSITION,30)
            empty_pages = [i for i,page in enumerate(pages,1) if not page.strip()]
            record = dict(schema='mimamsa-c14-document-candidate-v1',doc_id=doc,
                court_metadata=metadata.get('court') or None,title_metadata=metadata.get('title') or None,
                decision_date_metadata=metadata.get('decided') or None,bench=None,jurisdiction=None,
                case_number_mentions=cases,order_heading_mentions=types,order_type=None,
                coram_heading_mentions=coram,disposition_phrase_mentions=disposition,
                neutral_citation=None,reported_citations=None,citation_mentions=citations,
                cited_judgments=None,subsequent_judgments=None,provision_mentions=scan(pages,SECTION),
                service_branch=None,subject=None,material_facts=None,issues=None,arguments=None,
                reasoning=None,ratio=None,other_observations=None,operative_directions=None,final_disposition=None,
                source_url=metadata.get('source_url') or official.get(doc,{}).get('url'),
                original_sha256=pdf_hash,derivative_sha256=text_hash,hf_revision=revision,
                page_count=physical_pages,page_text_sha256=[sha(p.encode()) for p in pages],
                extraction_quality=dict(state='review-required' if empty_pages else 'page-map-present',
                    empty_pages=empty_pages,anchor_unit='one-based physical page and zero-based Unicode offsets'),
                relevance='unassessed',integrity='receipt-and-local-digest-verified',legal_authority='unreviewed',
                application_eligible=False,historical_exclusion_is_advisory=True)
            if lineage:
                record['derivative_lineage'] = lineage
                record['extraction_quality']['state'] = reviewed['status']
                record['extraction_quality']['empty_pages'] = sorted(set(empty_pages)-set(lineage['out_of_scope_pages']))
                counts['out_of_scope_page_slots'] += len(lineage['out_of_scope_pages'])
            for anchor in citations + cases + types + coram + disposition + record['provision_mentions']:
                assert pages[anchor['page']-1][anchor['start']:anchor['end']] == anchor['text']
            conn.execute('INSERT INTO documents VALUES(?,?,?,?)',(doc,pdf_hash,text_hash,revision))
            conn.executemany('INSERT INTO citation_mentions VALUES(?,?,?)',
                ((doc,' '.join(a['text'].upper().split()),a['page']) for a in citations))
            conn.executemany('INSERT INTO pages VALUES(?,?,?)',((doc,i,text) for i,text in enumerate(pages,1)))
            output.write(json.dumps(record,ensure_ascii=False,sort_keys=True)+'\n')
            counts['candidate_records'] += 1
            counts['physical_pages'] += physical_pages
            counts['citation_mentions'] += len(citations)
    conn.commit()
    assert conn.execute('PRAGMA integrity_check').fetchone() == ('ok',)
    assert not conn.execute('PRAGMA foreign_key_check').fetchone()
    assert conn.execute('SELECT count(*) FROM documents').fetchone()[0] == counts['candidate_records']
    assert conn.execute('SELECT count(*) FROM pages').fetchone()[0] == counts['physical_pages']
    counts['search_hits_for_court'] = conn.execute("SELECT count(*) FROM pages WHERE pages MATCH 'court'").fetchone()[0]
    assert counts['search_hits_for_court'] > 0
    conn.close()
    report = dict(schema='mimamsa-c14-candidate-package-v1', active_import_allowed=False,counts=dict(counts),
        restriction_register_sha256=sha((root/'register.json').read_bytes()),skips=skips,
        files={name:sha((dest/name).read_bytes()) for name in ('records.jsonl','search.sqlite')})
    (dest/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(dict(counts))

if __name__ == '__main__':
    main()
