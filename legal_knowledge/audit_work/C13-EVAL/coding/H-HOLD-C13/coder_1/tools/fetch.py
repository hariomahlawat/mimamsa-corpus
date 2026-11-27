import csv, hashlib, os, shutil, subprocess, sys
from huggingface_hub import hf_hub_download
W = sys.argv[1]
rows = list(csv.DictReader(open(os.path.join(W, "CODER_SHEET.csv"))))
log = []
for r in rows:
    sha = r["rep_sha256"]; p = r["rep_raw_path"]
    dest = os.path.join(W, "src", sha + ".pdf")
    if os.path.exists(dest) and hashlib.sha256(open(dest,"rb").read()).hexdigest()==sha:
        log.append((r["item_id"],"ok","cached")); continue
    got = None; how = None
    revs = ["5524c3d9"]
    if "15bd03cc" in r["rep_raw_store"]: revs.append("15bd03cc")
    for rev in revs:
        try:
            f = hf_hub_download("hariomahlawat/mimamsa-corpus", p, repo_type="dataset", revision=rev, cache_dir=os.path.join(W,"src",".cache"))
            got = open(f,"rb").read(); how = "hf@"+rev; break
        except Exception as e:
            how = "hf_err:%s" % type(e).__name__
    if got is None:
        try:
            got = subprocess.run(["git","-C","/home/user/c7","show","ad77758d:"+p],capture_output=True,check=True).stdout; how="git"
        except Exception as e:
            log.append((r["item_id"],"FILE_UNAVAILABLE",how)); continue
    h = hashlib.sha256(got).hexdigest()
    if h != sha:
        log.append((r["item_id"],"SHA_MISMATCH",how+" "+h)); continue
    open(dest,"wb").write(got)
    log.append((r["item_id"],"ok",how))
for l in log: print(*l, sep="\t")
