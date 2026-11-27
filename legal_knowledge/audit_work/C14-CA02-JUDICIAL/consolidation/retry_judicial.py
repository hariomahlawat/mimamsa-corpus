import time,urllib.error,os,csv,hashlib,json,re,subprocess,urllib.request,concurrent.futures
from pathlib import Path
import pymupdf
out=Path('extended-files');out.mkdir(exist_ok=True)
register=json.load(open('register.json'))['items']
restricted={s.lower() for x in register for s in [x['doc_id'],x['source_sha256'],*x.get('hosted_paths',[]),*x.get('derived_sha256',[])]}
mark=re.compile(r'\b(?:confidential|classified|restricted|secret|sealed|in camera|not for (?:publication|circulation)|for official use only)\b',re.I)
def fetch(row):
 name=row['doc_id']; h=row['expected_sha256'];url=row['source_url']
 if not re.fullmatch(r'[a-f0-9]{64}',h) or not re.fullmatch(r'https://indian-(?:high|supreme)-court-judgments\.s3\.ap-south-1\.amazonaws\.com/data/[^?#]+\.pdf',url):
  return(name,'unapproved-source')
 if any(s in (name+' '+h+' '+url).lower() for s in restricted): return (name,'restricted')
 req=urllib.request.Request(url,headers={'User-Agent':'Mimamsa corpus preservation contact repository hariomahlawat/mimamsa-corpus'})
 class NoRedirect(urllib.request.HTTPRedirectHandler):
  def redirect_request(self,*args,**kwargs): return None
 with urllib.request.build_opener(NoRedirect()).open(req,timeout=30) as r:
  if r.geturl()!=url: return (name,'redirect')
  raw=r.read(50_000_001)
 if len(raw)>50_000_000 or hashlib.sha256(raw).hexdigest()!=h: return (name,'hash-or-size-mismatch')
 with pymupdf.open(stream=raw,filetype='pdf') as p:
  if p.is_repaired or p.needs_pass or not raw.rstrip().endswith(b'%%EOF') or not 0<len(p)<=400:return (name,'integrity')
  texts=[]; ocr=0; findings=[]
  for page in p:
   native=page.get_text(sort=True)
   needs_ocr=(row.get('phase')=='held-recheck' or page.number in (0,len(p)-1)
              or len(native.split())<30 or page.get_image_info()
              or any(span['type']!=0 for span in page.get_texttrace())
              or sum(len(g['items']) for g in page.get_drawings())>10)
   scanned=''
   if needs_ocr:
    dpi=min(125,int(72*(8_000_000/max(page.rect.width*page.rect.height,1))**0.5))
    if dpi<90:return(name,'page-too-large',page.number+1)
    pix=page.get_pixmap(dpi=dpi,colorspace=pymupdf.csGRAY)
    pocr=subprocess.run(['tesseract','stdin','stdout','-l','eng'],input=pix.tobytes('png'),capture_output=True,timeout=45,env={'PATH':os.environ['PATH'],'OMP_THREAD_LIMIT':'1'})
    if pocr.returncode:return(name,'ocr-failure',page.number+1)
    scanned=pocr.stdout.decode()
   heading=re.compile(r'^(?:\s*)(?:confidential|classified|restricted|secret|sealed|not for (?:publication|circulation)|for official use only)(?:\s*)$',re.I|re.M)
   for kind,t in [('native',native),('ocr',scanned)]:
    if heading.search(t):
     findings.append([page.number+1,'standalone-marking',kind])
    elif mark.search(t):
     flat=' '.join(t.split())
     legal=r'(?:restricted to|restrictions? (?:on|under)|sealed (?:cover|envelope)|classified as|official secrets? act|confidential (?:communication|report|relationship)|secret (?:ballot|witness))'
     remaining=mark.search(re.sub(legal,'',flat,flags=re.I))
     findings.append([page.number+1,'ambiguous-body' if remaining else 'legal-context',kind,
                      sorted({m.group(0).lower() for m in mark.finditer(flat)})])
   if len(native.split())<20 and scanned.strip():
    native=scanned; ocr+=1
   if len(native.split())<5:findings.append([page.number+1,'sparse-text'])
   texts.append(native)
  if findings:
   with (out/(h+'.review.json')).open('w') as f:json.dump(findings,f)
  if any(f[1] in ('standalone-marking','ambiguous-body') for f in findings):return(name,'marking-review',h,len(raw),len(p),ocr)
  if any(f[1]=='sparse-text' for f in findings):return(name,'sparse-page-review',h,len(raw),len(p),ocr)
  (out/(h+'.pdf')).write_bytes(raw)
  (out/(h+'.txt')).write_text('\n\f\n'.join(texts))
  return(name,'verified-local',h,len(raw),len(p),ocr)
def safe(row):
 for delay in (0,3,9):
  if delay:time.sleep(delay)
  try:return fetch(row)
  except urllib.error.HTTPError as e:
   if e.code not in (429, 500,502,503,504) or delay==9:return(row['doc_id'],f'HTTP-{e.code}')
  except Exception as e:return(row['doc_id'],type(e).__name__)
from huggingface_hub import HfApi,CommitOperationAdd,hf_hub_download
repo='hariomahlawat/mimamsa-corpus';token=os.environ['HF_TOKEN'];api=HfApi(token=token)
q=json.load(open('extended-queue.json')); parent=q['revision'];rows=q['jobs']
def journal(record):
 with open('extended.jsonl','a') as f:
  f.write(json.dumps(record)+'\n');f.flush();os.fsync(f.fileno())
def verify(item):
 path,digest=item
 import time
 for attempt in range(7):
  try:
   got=hf_hub_download(repo,path,repo_type='dataset',revision=parent,token=token,force_download=True,cache_dir='verify-cache')
   if hashlib.sha256(Path(got).read_bytes()).hexdigest()==digest:return
   raise RuntimeError('Digest mismatch')
  except Exception as exc:
   if attempt==6:raise RuntimeError(f'Pinned read-back failed: {type(exc).__name__}') from None
   time.sleep(2**attempt)

seen=set()
if Path('extended.jsonl').exists():
 events=list(map(json.loads,open('extended.jsonl')))
 for i,e in enumerate(events):
  if e.get('verified') is False and not any(v.get('verified') and v.get('revision')==e['revision'] for v in events):
   parent=e['revision']
   with concurrent.futures.ThreadPoolExecutor(6) as pool:
    list(pool.map(verify,e['files'].items()))
   done={'revision':parent,'verified':True,'file_count':len(e['files']),'first_offset':e.get('first_offset',events[i-1]['first_offset']),'complete':True}
   journal(done)
   events.append(done)
 for e in events:
  if e.get('complete'):
   seen.add(e['first_offset'])
   if e.get('revision'): parent=e['revision']
if Path('official-upload.json').exists():
 extra=json.load(open('official-upload.json'))
 if extra.get('verified') and api.dataset_info(repo).sha==extra['revision']:
  parent=extra['revision']
with concurrent.futures.ThreadPoolExecutor(8) as ex:
 for start in range(0,len(rows),15):
  if start+3 in seen:continue
  result=list(ex.map(safe,rows[start:start+15]))
  for cooldown in (25,50):
   if sum(r[1] in ('HTTP-429','HTTP-503') for r in result)<8:break
   time.sleep(cooldown)
   def retry_transient(job):
    row, disposition=job
    return safe(row) if disposition[1] in ('HTTP-429','HTTP-503') else disposition
   result=list(ex.map(retry_transient,zip(rows[start:start+15],result,strict=True)))
  journal({'first_offset':start+3,'result':result})
  if sum(r[1] in ('HTTP-429','HTTP-503') for r in result)>=8:
   raise RuntimeError('Source outage persisted after bounded backoff; checkpoint retained')
  files={}
  for row in result:
   if row[1]!='verified-local':continue
   h=row[2]
   for ext in ('pdf','txt'):
    f=out/(h+'.'+ext)
    files[f'legal_knowledge/preservation/c14_tier1_extension/v1/{h[:2]}/{h}/'+('original.pdf' if ext=='pdf' else 'text.txt')]=f
  if not files:
   journal({'first_offset':start+3,'complete':True});continue
  info=api.dataset_info(repo);assert info.private and info.sha==parent
  c=api.create_commit(repo,[CommitOperationAdd(path_in_repo=p,path_or_fileobj=f) for p,f in files.items()],repo_type='dataset',parent_commit=parent,commit_message=f'Preserve verified Cycle 14 Tier 1 originals, offset {start+3}')
  parent=c.oid
  hashes={p:hashlib.sha256(f.read_bytes()).hexdigest() for p,f in files.items()}
  journal({'revision':parent,'files':hashes,'verified':False,'first_offset':start+3})
  list(ex.map(verify,hashes.items()))
  journal({'revision':parent,'verified':True,'file_count':len(files),'first_offset':start+3,'complete':True})
  print('Offset',start+3,'verified',len(files),parent,flush=True)
