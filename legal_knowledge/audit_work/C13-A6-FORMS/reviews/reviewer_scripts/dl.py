import sys, hashlib, shutil, os
sys.path.insert(0, sys.argv[1])
import a6_common as C
from huggingface_hub import hf_hub_download
out = sys.argv[2]
REV = "5524c3d99b6a069249012fecea75093b875a22c7"
for k, s in C.SOURCES.items():
    if k in ("AFA50-C7",): continue
    try:
        p = hf_hub_download("hariomahlawat/mimamsa-corpus", s["hf_path"], repo_type="dataset", revision=REV)
    except Exception as e:
        print(k, "FAIL", type(e).__name__, str(e)[:120]); continue
    b = open(p, "rb").read(); h = hashlib.sha256(b).hexdigest()
    dst = os.path.join(out, k + ".pdf"); open(dst, "wb").write(b)
    print(k, s["hf_path"][:60], "OK" if h == s["sha256"] else "MISMATCH " + h, len(b))
