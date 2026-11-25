import csv, hashlib, os, shutil, sys
from huggingface_hub import hf_hub_download
W = sys.argv[1]
rows = list(csv.DictReader(open(os.path.join(W, 'ADJUDICATION_SHEET.csv'))))
seen = {}
for r in rows:
    seen.setdefault(r['rep_sha256'], r['rep_raw_path'])
log = open(os.path.join(W, 'tools', 'fetch_log.txt'), 'w')
for sha, path in seen.items():
    dest = os.path.join(W, 'src', sha + '.pdf')
    if os.path.exists(dest) and hashlib.sha256(open(dest,'rb').read()).hexdigest() == sha:
        log.write(f'{sha} cached OK\n'); continue
    got = None
    for rev in ['5524c3d9', 'main']:
        try:
            p = hf_hub_download('hariomahlawat/mimamsa-corpus', path, repo_type='dataset', revision=rev)
            got = (p, rev); break
        except Exception as e:
            log.write(f'{sha} rev {rev} fail {type(e).__name__}\n')
    if not got:
        log.write(f'{sha} UNAVAILABLE\n'); continue
    h = hashlib.sha256(open(got[0],'rb').read()).hexdigest()
    shutil.copyfile(got[0], dest)
    log.write(f'{sha} rev {got[1]} sha_ok={h==sha}\n')
log.close()
