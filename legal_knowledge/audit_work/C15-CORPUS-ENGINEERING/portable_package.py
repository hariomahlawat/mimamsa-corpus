"""Export and rebuild an isolated candidate search database using only the standard library."""
import argparse
import contextlib
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3

SCHEMA = """
CREATE TABLE documents(id TEXT PRIMARY KEY, source_sha TEXT NOT NULL, text_sha TEXT NOT NULL, revision TEXT NOT NULL);
CREATE TABLE citation_mentions(doc_id TEXT NOT NULL REFERENCES documents(id), citation TEXT NOT NULL, page INTEGER NOT NULL);
CREATE INDEX mention_citation ON citation_mentions(citation);
CREATE VIRTUAL TABLE pages USING fts5(doc_id UNINDEXED, physical_page UNINDEXED, derivative);
"""

def digest(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f,'sha256').hexdigest()

def jsonlines(path):
    with path.open(encoding='utf-8') as f:
        yield from (json.loads(line) for line in f)

def export(source,dest):
    dest.mkdir(mode=0o700)
    shutil.copyfile(source/'records.jsonl',dest/'records.jsonl')
    shutil.copyfile(source/'search.sqlite',dest/'search.sqlite')
    shutil.copyfile(source/'manifest.json',dest/'source-manifest.json')
    with contextlib.closing(sqlite3.connect((source/'search.sqlite').resolve().as_uri()+'?mode=ro&immutable=1',uri=True)) as db:
        with (dest/'pages.jsonl.gz').open('wb') as file,gzip.GzipFile(filename='',fileobj=file,mode='wb',mtime=0) as pagefile:
            for doc,page,text in db.execute('SELECT doc_id,physical_page,derivative FROM pages ORDER BY doc_id,physical_page'):
                pagefile.write((json.dumps([doc,page,text],ensure_ascii=False)+'\n').encode())
    manifest={'format':'mimamsa-isolated-candidate-v1','application_eligible':False,
              'files':{name:digest(dest/name) for name in ('records.jsonl','search.sqlite','source-manifest.json','pages.jsonl.gz')}}
    (dest/'portable-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')

def rebuild(source,dest):
    manifest=json.loads((source/'portable-manifest.json').read_bytes())
    if manifest['format']!='mimamsa-isolated-candidate-v1' or manifest['application_eligible'] is not False:
        raise ValueError('Invalid candidate generation')
    for name in ('records.jsonl','source-manifest.json','pages.jsonl.gz'):
        if digest(source/name)!=manifest['files'][name]:
            raise ValueError(f'Artifact digest mismatch for {name}')
    dest.mkdir(mode=0o700)
    with contextlib.closing(sqlite3.connect(dest/'search.sqlite')) as db:
        db.executescript(SCHEMA)
        db.execute('PRAGMA foreign_keys=ON')
        expected={}
        for row in jsonlines(source/'records.jsonl'):
            if row['application_eligible'] is not False:
                raise ValueError('Unexpected application eligibility')
            doc=row['doc_id']
            db.execute('INSERT INTO documents VALUES(?,?,?,?)',(doc,row['original_sha256'],row['derivative_sha256'],row['hf_revision']))
            expected[doc]=row['page_text_sha256']
            db.executemany('INSERT INTO citation_mentions VALUES(?,?,?)',
              ((doc,' '.join(a['text'].upper().split()),a['page']) for a in row['citation_mentions']))
        seen=set()
        with gzip.open(source/'pages.jsonl.gz','rt',encoding='utf-8') as file:
            for line in file:
                doc,page,text=json.loads(line)
                if not 1<=page<=len(expected[doc]) or (doc,page) in seen:
                    raise ValueError('Invalid page identity')
                if hashlib.sha256(text.encode()).hexdigest()!=expected[doc][page-1]:
                    raise ValueError('Page text mismatch')
                seen.add((doc,page))
                db.execute('INSERT INTO pages VALUES(?,?,?)',(doc,page,text))
        if len(seen)!=sum(map(len,expected.values())):
            raise ValueError('Missing physical page')
        db.commit()
        if db.execute('PRAGMA integrity_check').fetchone()!=('ok',) or db.execute('PRAGMA foreign_key_check').fetchone():
            raise ValueError('Invalid rebuilt search database')
        counts={'documents':len(expected),'pages':len(seen),'citation_mentions':db.execute('SELECT count(*) FROM citation_mentions').fetchone()[0],
                'search_hits_for_court':db.execute("SELECT count(*) FROM pages WHERE pages MATCH 'court'").fetchone()[0]}
    prior=json.loads((source/'source-manifest.json').read_bytes())['counts']
    expected_counts={'documents':prior['candidate_records'],'pages':prior['physical_pages'],
                     'citation_mentions':prior['citation_mentions'],'search_hits_for_court':prior['search_hits_for_court']}
    if counts!=expected_counts:
        raise ValueError('Rebuilt search counts mismatch')
    (dest/'receipt.json').write_text(json.dumps(counts,indent=2)+'\n')
    print(json.dumps(counts))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('export','rebuild'))
    parser.add_argument('source',type=Path)
    parser.add_argument('destination',type=Path)
    args=parser.parse_args()
    {'export':export,'rebuild':rebuild}[args.action](args.source,args.destination)
