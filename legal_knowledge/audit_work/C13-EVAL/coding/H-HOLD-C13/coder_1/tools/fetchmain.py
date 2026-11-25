import csv, hashlib, os
from huggingface_hub import hf_hub_download
W="/tmp/claude-0/-home-user-mimamsa-corpus/9dd71a54-b050-5d1e-a2e9-2ceef8ac3e20/scratchpad/c13/coding/H-HOLD-C13/coder_1"
rows=list(csv.DictReader(open(os.path.join(W,"tools","orig.csv"))))
for i in (3,5,97):
    r=rows[i]
    for rev in ("5524c3d9","main"):
        try:
            f=hf_hub_download("hariomahlawat/mimamsa-corpus", r["rep_raw_path"], repo_type="dataset", revision=rev, cache_dir=os.path.join(W,"src",".cache2"))
            h=hashlib.sha256(open(f,"rb").read()).hexdigest()
            print(i, r["item_id"], rev, "present", "sha_ok" if h==r["rep_sha256"] else "SHA_DIFF")
        except Exception as e:
            print(i, r["item_id"], rev, "absent", type(e).__name__)
