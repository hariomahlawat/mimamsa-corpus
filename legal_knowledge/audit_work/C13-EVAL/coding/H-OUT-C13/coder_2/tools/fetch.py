import csv, hashlib, os, sys, shutil
from concurrent.futures import ThreadPoolExecutor
from huggingface_hub import hf_hub_download
import fitz
W=sys.argv[1]
rows=list(csv.DictReader(open(f"{W}/CODER_SHEET.csv")))
def go(r):
    sha=r['rep_sha256']; dst=f"{W}/src/{sha}.pdf"
    try:
        if not os.path.exists(dst):
            p=hf_hub_download("hariomahlawat/mimamsa-corpus", r['rep_raw_path'], repo_type="dataset", revision="5524c3d9", cache_dir=f"{W}/src/.cache")
            shutil.copy(p,dst)
        h=hashlib.sha256(open(dst,'rb').read()).hexdigest()
        if h!=sha: return (r['item_id'],'MISMATCH')
        d=fitz.open(dst); out=[]
        for i,pg in enumerate(d): out.append(f"\n=====PAGE {i+1}=====\n"+pg.get_text())
        t=''.join(out); open(f"{W}/txt/{r['item_id']}.txt",'w').write(t)
        return (r['item_id'],f"OK pages={len(d)} chars={len(t)}")
    except Exception as e: return (r['item_id'],'ERR '+repr(e)[:200])
with ThreadPoolExecutor(8) as ex:
    for res in ex.map(go,rows): print(*res)
