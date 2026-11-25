import csv, hashlib, shutil, sys
from huggingface_hub import hf_hub_download
import fitz
W=sys.argv[1]; ids=sys.argv[2:]
for r in csv.DictReader(open(f"{W}/tools/CODER_SHEET.orig.csv")):
    if r['item_id'] not in ids: continue
    sha=r['rep_sha256']; dst=f"{W}/src/{sha}.pdf"
    try:
        p=hf_hub_download("hariomahlawat/mimamsa-corpus", r['rep_raw_path'], repo_type="dataset", revision="main", cache_dir=f"{W}/src/.cache")
        shutil.copy(p,dst)
    except Exception as e: print(r['item_id'],"ERR",repr(e)[:150]); continue
    h=hashlib.sha256(open(dst,'rb').read()).hexdigest()
    if h!=sha: print(r['item_id'],"MISMATCH"); continue
    d=fitz.open(dst); t=''.join(f"\n=====PAGE {i+1}=====\n"+pg.get_text() for i,pg in enumerate(d))
    open(f"{W}/txt/{r['item_id']}.txt",'w').write(t); print(r['item_id'],"OK",len(d),len(t))
