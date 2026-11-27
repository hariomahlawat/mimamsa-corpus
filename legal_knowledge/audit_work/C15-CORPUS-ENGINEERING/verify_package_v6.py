"""Read-only independent checks of candidate identities, search and contract anchors."""
from collections import defaultdict
import argparse
import hashlib
import json
import sqlite3
from pathlib import Path

from mimamsa_contract.evidence import evidence_keys, resolve_span

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('package',type=Path)
args=parser.parse_args()
root=args.package.resolve()
manifest=json.loads((root/'manifest.json').read_bytes())
assert manifest['active_import_allowed'] is False
for name, digest in manifest['files'].items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest() == digest
conn=sqlite3.connect((root/'search.sqlite').as_uri()+'?mode=ro&immutable=1',uri=True)
assert conn.execute('PRAGMA integrity_check').fetchone()==('ok',)
assert not conn.execute('PRAGMA foreign_key_check').fetchone()
pages_by_doc=defaultdict(dict)
for doc,physical,text in conn.execute('SELECT doc_id,physical_page,derivative FROM pages'):
    assert physical not in pages_by_doc[doc]
    pages_by_doc[doc][physical]=text
fields=('case_number_mentions','order_heading_mentions','coram_heading_mentions',
        'disposition_phrase_mentions','citation_mentions','provision_mentions')
seen=set()
anchor_count=0
for line in (root/'records.jsonl').open():
    row=json.loads(line)
    key=row['doc_id']
    assert key.casefold() not in seen and row['application_eligible'] is False
    seen.add(key.casefold())
    pages=pages_by_doc.pop(key)
    assert sorted(pages)==list(range(1,row['page_count']+1))
    assert [hashlib.sha256(pages[i].encode()).hexdigest() for i in sorted(pages)]==row['page_text_sha256']
    assert conn.execute('SELECT source_sha,text_sha,revision FROM documents WHERE id=?',(key,)).fetchone()==(
        row['original_sha256'],row['derivative_sha256'],row['hf_revision'])
    for field in fields:
        for item in row[field]:
            number=item['page']
            text=pages[number]
            assert text[item['start']:item['end']]==item['text']
            anchor=dict(source_copy_sha256=row['original_sha256'], page=number,
                        pipeline_name='cycle14-preserved-text',pipeline_version='v1',
                        derivative_text_sha256=row['derivative_sha256'],
                        char_start=item['start'],char_end=item['end'])
            page,span,warning=evidence_keys(anchor)
            assert page.page==number and page.source_copy_sha256==row['original_sha256'] and not warning and span
            derivative=dict(source_copy_sha256=row['original_sha256'],
                            pipeline=dict(name='cycle14-preserved-text',version='v1'),
                            text_sha256=row['derivative_sha256'],
                            passages=[dict(page=number,char_start=0,char_end=len(text))])
            assert resolve_span(span,[derivative])
            assert not resolve_span(span,[dict(derivative,text_sha256='0'*64)])
            anchor_count+=1
assert not pages_by_doc
assert len(seen)==manifest['counts']['candidate_records']
assert conn.execute("SELECT count(*) FROM pages WHERE pages MATCH 'court'").fetchone()[0]==manifest['counts']['search_hits_for_court']
assert conn.execute('SELECT count(*) FROM citation_mentions').fetchone()[0]==manifest['counts']['citation_mentions']
print(json.dumps(dict(documents=len(seen),contract_span_checks=anchor_count,
                      rejected_wrong_derivative=anchor_count,sqlite_integrity='ok')))
