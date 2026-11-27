import csv, hashlib, os, shutil, sys, json
from huggingface_hub import hf_hub_download
W = sys.argv[1]
SRC = os.path.join(W, 'src')
rows = list(csv.DictReader(open(os.path.join(W, 'ADJUDICATION_SHEET.csv'))))
files = {}
for r in rows:
    files[r['rep_sha256']] = r['rep_raw_path']
status = {}
for sha, path in files.items():
    dest = os.path.join(SRC, sha + '.pdf')
    if os.path.exists(dest) and hashlib.sha256(open(dest,'rb').read()).hexdigest() == sha:
        status[sha] = 'ok-cached'; continue
    got = None
    for rev in ('5524c3d9', 'main'):
        try:
            p = hf_hub_download('hariomahlawat/mimamsa-corpus', path, repo_type='dataset', revision=rev)
            got = (p, rev); break
        except Exception as e:
            status[sha] = f'err {rev}: {type(e).__name__}'
    if not got:
        continue
    h = hashlib.sha256(open(got[0],'rb').read()).hexdigest()
    if h != sha:
        status[sha] = f'SHA_MISMATCH rev={got[1]} got={h}'; continue
    shutil.copyfile(got[0], dest)
    status[sha] = f'ok rev={got[1]}'
json.dump(status, open(os.path.join(W, 'tools', 'fetch_status.json'), 'w'), indent=1)
from collections import Counter
print(Counter(v.split(' ')[0] + (' '+v.split(' ')[1] if v.startswith('ok rev') else '') for v in status.values()))
for k, v in status.items():
    if not v.startswith('ok'): print(k, v)
