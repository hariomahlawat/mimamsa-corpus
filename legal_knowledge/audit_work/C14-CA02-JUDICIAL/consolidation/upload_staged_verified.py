import json,os,hashlib,re,time
from pathlib import Path
from huggingface_hub import HfApi,CommitOperationAdd,hf_hub_download
token=os.environ['HF_TOKEN'];repo='hariomahlawat/mimamsa-corpus';api=HfApi(token=token)
receipt=Path('official-upload.json')
def confirm(j):
 for path,want in j['files'].items():
  for delay in (0,2,6,15,30):
   if delay:time.sleep(delay)
   try:
    downloaded=Path(hf_hub_download(repo,path,repo_type='dataset',revision=j['revision'],
                       force_download=True,token=token,cache_dir='verify-cache'))
    if hashlib.sha256(downloaded.read_bytes()).hexdigest()!=want:
     raise ValueError('Read-back digest mismatch')
    break
   except Exception as e:
    if delay==30: raise RuntimeError(f'Pinned read-back failed: {type(e).__name__}') from None
 j.update(verified=True)
 tmp=receipt.with_suffix('.tmp')
 tmp.write_text(json.dumps(j))
 tmp.replace(receipt)
if receipt.is_file():
 j=json.loads(receipt.read_bytes())
 if not j['verified']:confirm(j)
 print(j['revision'],len(j['files']))
 raise SystemExit(0)
info=api.dataset_info(repo);assert info.private
known=set()
for f in api.list_repo_tree(repo,repo_type='dataset',revision=info.sha,recursive=True):
 if not hasattr(f,'size') or not f.path.lower().endswith('.pdf'):continue
 h=getattr(f.lfs,'sha256',None) or next(iter(re.findall(r'(?<![a-f0-9])[a-f0-9]{64}(?![a-f0-9])',f.path)),None)
 if not h:
  fpath=hf_hub_download(repo,f.path,repo_type='dataset',revision=info.sha,token=token,cache_dir='cache')
  h=hashlib.sha256(Path(fpath).read_bytes()).hexdigest()
 known.add(h)
entries=[];files={}
for x in map(json.loads,open('official-pilot.jsonl')):
 if x['status']!='eligible-local':continue
 h=x['sha256']
 if h in known: entries.append(dict(x,status='duplicate-at-pinned-head'));continue
 known.add(h); entries.append(dict(x,status='queued-for-upload'))
 root='c14_aft_guwahati' if x['id'].startswith('AFT') else 'c14_statutory' if x['id'].startswith('CA01') else 'c14_tier1_extension' if x['id'].startswith('PHHC') else 'c14_curated_sc'
 for ext,name in [('pdf','original.pdf'),('txt','text.txt')]:
  files[f'legal_knowledge/preservation/{root}/v2/{h[:2]}/{h}/{name}']=Path('official-files')/(h+'.'+ext)
if files:
 result=api.create_commit(repo,[CommitOperationAdd(path_in_repo=p,path_or_fileobj=f) for p,f in files.items()],repo_type='dataset',parent_commit=info.sha,commit_message='Preserve screened official Cycle 14 tribunal and court sources')
 rev=result.oid
 hashes={p:hashlib.sha256(f.read_bytes()).hexdigest() for p,f in files.items()}
 j=dict(revision=rev,files=hashes,verified=False,entries=entries)
 Path('official-upload.json').write_text(json.dumps(j))
 confirm(j)
 print(rev,len(files))
else:
 Path('official-upload.json').write_text(json.dumps(dict(revision=info.sha,files={},verified=True,entries=entries)))
