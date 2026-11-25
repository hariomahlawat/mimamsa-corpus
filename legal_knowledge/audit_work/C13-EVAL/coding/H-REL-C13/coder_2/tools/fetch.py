import csv, hashlib, os, sys, shutil, json
from huggingface_hub import hf_hub_download
W='/tmp/claude-0/-home-user-mimamsa-corpus/9dd71a54-b050-5d1e-a2e9-2ceef8ac3e20/scratchpad/c13/coding/H-REL-C13/coder_2/'
SRC=W+'src/'
rows=list(csv.DictReader(open(W+'CODER_SHEET.csv')))
status={}
for r in rows:
    p=r['rep_raw_path']; sha=r['rep_sha256']
    if p in status: continue
    dst=SRC+sha+'.pdf'
    try:
        if not os.path.exists(dst):
            f=hf_hub_download('hariomahlawat/mimamsa-corpus',p,repo_type='dataset',revision='5524c3d9',cache_dir=W+'hfcache')
            shutil.copy(f,dst)
        h=hashlib.sha256(open(dst,'rb').read()).hexdigest()
        status[p]='OK' if h==sha else 'MISMATCH:'+h
    except Exception as e:
        status[p]='ERR:'+type(e).__name__+':'+str(e)[:200]
    print(p,status[p],flush=True)
json.dump(status,open(W+'tools/fetch_status.json','w'),indent=1)
