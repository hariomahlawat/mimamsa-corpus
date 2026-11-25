import csv,sys,hashlib
from huggingface_hub import hf_hub_download
for r in csv.DictReader(open(sys.argv[1])):
    if '15bd03cc' not in r['rep_raw_store']: continue
    for rv in ('5524c3d9','main'):
        try:
            p=hf_hub_download('hariomahlawat/mimamsa-corpus',r['rep_raw_path'],repo_type='dataset',revision=rv)
            h=hashlib.sha256(open(p,'rb').read()).hexdigest()
            print(r['item_id'],rv,'present', h==r['rep_sha256'])
        except Exception as e: print(r['item_id'],rv,'absent',type(e).__name__)
