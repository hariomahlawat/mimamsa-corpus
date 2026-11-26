import hashlib
import json
from pathlib import Path
import shutil

base=Path('/workspace/c14-collection')
dest=Path('staged-upload')
dest.mkdir(exist_ok=True,mode=0o700)
entries=[]
def read(path):
    return list(map(json.loads,path.open())) if path.exists() else []
def add(row, root):
    if row.get('status')!='eligible-local':
        return
    digest=row['sha256']
    raw=root/(digest+'.pdf')
    assert hashlib.sha256(raw.read_bytes()).hexdigest()==digest
    for ext in ('pdf','txt'):
        shutil.copyfile(root/(digest+'.'+ext),dest/'official-files'/(digest+'.'+ext))
    entries.append(row)
for file in ('official-pilot.jsonl','official-aft-followup.jsonl','official-aft-blank-recheck.jsonl'):
    for item in read(base/file):
        add(item,base/'official-files')
for file in ('aft-expansion.jsonl','aft-rest.jsonl'):
    for item in read(Path('aft-expansion')/file):
        add(item,Path('aft-expansion/official-files'))
queue={x['doc_id']:x for x in json.loads((base/'extended-queue.json').read_bytes())['jobs']}
for x in json.loads((base/'source-retry-local.json').read_text()):
    if x[1]=='verified-local':
        doc,_,h,size,pages,ocr=x
        assert queue[doc]['expected_sha256']==h
        add(dict(id='PHHC-RETRY',doc_id=doc,url=queue[doc]['source_url'],sha256=h,pages=pages,ocr=ocr,
                 status='eligible-local'),base/'extended-files')
for x in json.loads(Path('marking-dispositions.json').read_bytes()):
    if x['status']=='visual-false-positive-cleared-local':
        digest=x['original_sha256']
        assert hashlib.sha256((Path('marking-cleared')/(digest+'.txt')).read_bytes()).hexdigest()==x['derivative_sha256']
        add(dict(id='PHHC-MARKING-REVIEW',doc_id=x['doc_id'],url=queue[x['doc_id']]['source_url'],sha256=digest,
                 pages=x['page_count'],ocr=0,status='eligible-local',documentary_status=x['context']),Path('marking-cleared'))
register=(base/'register.json').read_bytes()
blocked={v.casefold() for item in json.loads(register)['items'] for v in
         (item['doc_id'],item['source_sha256'],*item.get('hosted_paths',[]),*item.get('derived_sha256',[])) if v}
for x in entries:
    text_sha=hashlib.sha256((dest/'official-files'/(x['sha256']+'.txt')).read_bytes()).hexdigest()
    assert not any(v in (x['sha256']+' '+text_sha+' '+x.get('doc_id','')+' '+x.get('url','')).casefold() for v in blocked)
(dest/'official-pilot.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in entries))
print('Staged distinct sources',len({row['sha256'] for row in entries}))
