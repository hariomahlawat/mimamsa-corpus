import csv, hashlib, os, sys, shutil
from huggingface_hub import hf_hub_download
W=sys.argv[1]
rows=list(csv.DictReader(open(os.path.join(W,'CODER_SHEET.csv'))))
seen={}
for r in rows:
    p=r['rep_raw_path']; sha=r['rep_sha256']
    if p in seen: continue
    dst=os.path.join(W,'src',sha+'.pdf')
    st='ok'
    if not os.path.exists(dst):
        try:
            f=hf_hub_download('hariomahlawat/mimamsa-corpus',p,repo_type='dataset',revision='5524c3d9',local_dir=os.path.join(W,'src','_hf'))
            shutil.copy(f,dst)
        except Exception as e:
            st='FAIL '+type(e).__name__; seen[p]=st; print(p,st); continue
    h=hashlib.sha256(open(dst,'rb').read()).hexdigest()
    if h!=sha: st='MISMATCH'
    seen[p]=st
    if st!='ok': print(p,st)
print('done',len(seen),sum(v=='ok' for v in seen.values()))
