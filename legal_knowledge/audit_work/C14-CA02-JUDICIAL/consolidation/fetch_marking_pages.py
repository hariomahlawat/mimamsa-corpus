"""Fetch expected bytes from preserved queue for private marking review."""
import concurrent.futures
import hashlib
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

import pymupdf

root=Path('/workspace/c14-collection')
sources={x['doc_id']:x['source_url'] for x in map(json.loads,(root/'C14_EXTENDED_JUDICIAL.jsonl').open())}
cases=json.loads(Path('marking-dispositions.json').read_bytes())
output=Path('visual-review');output.mkdir(exist_ok=True,mode=0o700)
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        return None

def work(row):
    doc, digest=row['doc_id'],row['original_sha256']
    status=dict(doc_id=doc,source_sha256=digest)
    for delay in (0,3,9):
        time.sleep(delay)
        try:
            request=urllib.request.Request(sources[doc],headers={'User-Agent':'Mimamsa corpus preservation'})
            with urllib.request.build_opener(NoRedirect()).open(request,timeout=15) as r:
                data=r.read(50_000_001)
            break
        except urllib.error.HTTPError as e:
            if e.code not in (429,500,502,503,504) or delay==9:
                return dict(status,status=f'HTTP-{e.code}')
        except (TimeoutError,urllib.error.URLError) as e:
            if delay==9:return dict(status,status=type(e).__name__)
    if len(data)>50_000_000 or hashlib.sha256(data).hexdigest()!=digest:
        return dict(status,status='digest-or-size-hold')
    with pymupdf.open(stream=data,filetype='pdf') as pdf:
        if pdf.is_repaired or pdf.needs_pass or not data.rstrip().endswith(b'%%EOF'):
            return dict(status,status='integrity-hold')
        pages=sorted({f[0] for f in row['original_marking_flags'] if f[1] in ('ambiguous-body','standalone-marking')})
        for i in pages:
            page=pdf[i-1]
            pix=page.get_pixmap(dpi=100)
            if pix.width*pix.height>8_000_000:
                return dict(status,status='visual-size-hold',page=i)
            pix.save(output/(digest+f'-p{i}.png'))
    return dict(status,status='visual-review-ready',pages=pages)
with concurrent.futures.ThreadPoolExecutor(4) as pool,Path('marking-visual-fetch.jsonl').open('w') as f:
    for record in pool.map(work,(x for x in cases if x['status']=='context-and-visual-review-pending')):
        f.write(json.dumps(record)+'\n');f.flush()
