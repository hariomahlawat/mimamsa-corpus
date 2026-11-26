"""Fetch exact, independently cleared source bytes for local derivative validation."""
import concurrent.futures
import hashlib
import json
import re
import time
import urllib.request
import urllib.error
from pathlib import Path

root=Path('/workspace/c14-collection')
queue={r['expected_sha256']:r for r in map(json.loads,(root/'C14_EXTENDED_JUDICIAL.jsonl').open())}
selected=[r for p in Path('.').glob('marking-assurance-*.json') for r in json.loads(p.read_bytes())
          if r['status'] in ('visual-false-positive','visual-false-positive-cleared')]
register=json.loads((root/'register.json').read_bytes())['items']
blocked={v.casefold() for i in register for v in
         (i['doc_id'],i['source_sha256'],*i.get('hosted_paths',[]),*i.get('derived_sha256',[])) if v}
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        return None

def fetch(report):
    digest=report['sha256']
    row=queue[digest]
    url=row['source_url']
    assert row['doc_id']==report['doc_id']
    assert re.fullmatch(r'https://indian-(?:high|supreme)-court-judgments\.s3\.ap-south-1\.amazonaws\.com/data/[^?#]+\.pdf',url)
    assert not any(x in (row['doc_id']+' '+url+' '+digest).casefold() for x in blocked)
    dest=Path('visual-review')/(digest+'.pdf')
    if dest.is_file():
        assert hashlib.sha256(dest.read_bytes()).hexdigest()==digest
        return True
    for delay in (0,3,9):
        time.sleep(delay)
        try:
            with urllib.request.build_opener(NoRedirect()).open(url,timeout=15) as f:
                raw=f.read(50_000_001)
            assert len(raw)<=50_000_000 and hashlib.sha256(raw).hexdigest()==digest
            dest.write_bytes(raw)
            return True
        except urllib.error.HTTPError as exc:
            if exc.code not in (429,500,502,503,504):
                return False
        except (TimeoutError,urllib.error.URLError):
            pass
    return False

with concurrent.futures.ThreadPoolExecutor(4) as pool:
    good=sum(pool.map(fetch,selected))
print('Source check passes',good,'of',len(selected))
