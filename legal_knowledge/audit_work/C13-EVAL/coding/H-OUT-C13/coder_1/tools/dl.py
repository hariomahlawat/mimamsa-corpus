import csv, hashlib, os, sys, shutil, subprocess
from huggingface_hub import hf_hub_download
W=sys.argv[1]; src=os.path.join(W,'src')
rows=list(csv.DictReader(open(os.path.join(W,'CODER_SHEET.csv'))))
log=open(os.path.join(W,'..','..','..','..','c13_coder1_scripts','dl.log') if False else sys.argv[2],'w')
for r in rows:
    sha=r['rep_sha256']; dest=os.path.join(src,sha+'.pdf')
    if os.path.exists(dest) and hashlib.sha256(open(dest,'rb').read()).hexdigest()==sha:
        log.write(f"{r['item_id']} OK cached\n"); continue
    rev='15bd03cc' if '15bd03cc' in r['rep_raw_store'] else '5524c3d9'
    got=None; how=''
    for rv in ([rev,'5524c3d9'] if rev!='5524c3d9' else [rev]):
        try:
            p=hf_hub_download('hariomahlawat/mimamsa-corpus', r['rep_raw_path'], repo_type='dataset', revision=rv)
            got=open(p,'rb').read(); how='hf@'+rv; break
        except Exception as e:
            how='hferr:'+type(e).__name__
    if got is None:
        try:
            got=subprocess.run(['git','-C','/home/user/c7','show','ad77758d:'+r['rep_raw_path']],capture_output=True,check=True).stdout; how+=' git'
        except Exception as e:
            log.write(f"{r['item_id']} UNAVAILABLE {how}\n"); continue
    h=hashlib.sha256(got).hexdigest()
    open(dest if h==sha else dest+'.mismatch','wb').write(got)
    log.write(f"{r['item_id']} {'OK' if h==sha else 'MISMATCH '+h} {how}\n"); log.flush()
