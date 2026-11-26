"""Recheck source availability without sending a full queue to an unavailable host."""
import collections
import concurrent.futures
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path('/workspace/c14-collection')
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None

def probe(url):
    attempts = []
    for delay in (0, 3, 9):
        time.sleep(delay)
        try:
            request = urllib.request.Request(url,method='HEAD',headers={'User-Agent':'Mimamsa corpus preservation'})
            with urllib.request.build_opener(NoRedirect()).open(request,timeout=12) as response:
                attempts.append(response.status)
        except urllib.error.HTTPError as exc:
            attempts.append(exc.code)
        except (TimeoutError, urllib.error.URLError) as exc:
            attempts.append(type(exc).__name__)
        if attempts[-1] not in (429,500,502,503,504,'TimeoutError','URLError'):
            break
    return attempts

retry = json.loads((ROOT/'source-retry-local.json').read_bytes())
queue = {x['doc_id']:x for x in json.loads((ROOT/'extended-queue.json').read_bytes())['jobs']}
failed = sorted(x[0] for x in retry if x[1]=='HTTPError')
sites = {
    'Guwahati AFT listing':'https://aftrbghy.nic.in/judgements.asp',
    'AFT central judgments':'https://www.aft.gov.in/judgements/freetext',
    'Gazette Army Act':'https://egazette.gov.in/WriteReadData/2026/276593.pdf',
    'India Code 1960':'https://www.indiacode.nic.in/repealedfileopen?rfilename=A1960-58.pdf',
    'DESW robots':'https://desw.gov.in/robots.txt',
    'CGDA pension index':'https://cgda.nic.in/index.php?page=pensionerscol',
}
samples = {key:queue[key]['source_url'] for key in (failed[0],failed[len(failed)//2],failed[-1])}
with concurrent.futures.ThreadPoolExecutor(4) as pool:
    results = dict(zip([*samples,*sites],pool.map(probe,[*samples.values(),*sites.values()]),strict=True))
outage = all(results[k] and set(results[k]) == {503} for k in samples)
record = dict(schema='c14-source-recheck-v1',isolated=True,judicial_retry_count=len(failed),
              observations=results, judicial=[dict(doc_id=x,status='source-503-retryable' if outage
              else 'availability-recheck-required', directly_sampled=x in samples) for x in failed])
Path('source-recheck.json').write_text(json.dumps(record,indent=2)+'\n')
print(collections.Counter(tuple(v) for v in results.values()), 'deferred', len(failed))
