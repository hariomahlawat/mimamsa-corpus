"""Stage the exact official CDA Guwahati copy of Army Pension Regulations Part I."""
import hashlib
import json
import os
import re
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
import pymupdf

origin='https://www.cdaguwahati.gov.in'
url=origin+'/pages/books/Pension%20Regulation%20army%20Pt-I.pdf'
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        return None
opener=urllib.request.build_opener(NoRedirect())
try:
    with opener.open(origin+'/robots.txt',timeout=15):
        raise RuntimeError('Source policy changed and requires review')
except urllib.error.HTTPError as exc:
    assert exc.code==404
with opener.open(urllib.request.Request(url,headers={'User-Agent':'Mimamsa corpus preservation'}),timeout=30) as response:
    assert response.geturl()==url and response.headers.get_content_type()=='application/pdf'
    data=response.read(40_000_001)
assert 0<len(data)<=40_000_000 and data.rstrip().endswith(b'%%EOF')
digest=hashlib.sha256(data).hexdigest()
items=json.loads(Path('/workspace/c14-collection/register.json').read_bytes())['items']
blocked={v.casefold() for x in items for v in (x['source_sha256'],x['doc_id'],*x.get('hosted_paths',[]),*x.get('derived_sha256',[])) if v}
assert not any(v in (digest+' '+url).casefold() for v in blocked)
marker=re.compile(r'^\s*(?:restricted|confidential|secret|classified|in camera|not for (?:publication|circulation)|for official use only)\s*$',re.I|re.M)
texts=[]
ocr_pages=[]
marks=[]
with pymupdf.open(stream=data,filetype='pdf') as d:
    assert not d.is_repaired and not d.needs_pass and 0<len(d)<=350
    for p in d:
        text=p.get_text(sort=True)
        if len(text.split())<20 or p.number in (0,len(d)-1) or p.get_image_info():
            pix=p.get_pixmap(dpi=120,colorspace=pymupdf.csGRAY)
            assert pix.width*pix.height<=8_000_000
            scan=subprocess.run(['tesseract','stdin','stdout','-l','eng'],input=pix.tobytes('png'),
                capture_output=True,timeout=45,check=True,env={'PATH':os.environ['PATH'],'OMP_THREAD_LIMIT':'1'}).stdout.decode()
            if marker.search(scan):
                marks.append(p.number+1)
            if len(text.split())<20 and scan.strip():
                ocr_pages.append(p.number+1)
                text=scan
        if marker.search(text):
            marks.append(p.number+1)
        texts.append(text)
first=' '.join(' '.join(texts[:4]).upper().split())
assert 'PENSION REGULATIONS FOR THE ARMY' in first and '2008' in first and ('PART-I' in first or 'PART - I' in first or 'PART-I' in first.replace(' - ','-'))
missing=[i for i,t in enumerate(texts,1) if not t.strip()]
out=dict(id='CA01-CDA-ARMY-PENSION-PART-I',url=url,sha256=digest,pages=len(texts),ocr=len(ocr_pages),
         ocr_pages=ocr_pages,access_mark_pages=sorted(set(marks)),empty_text_pages=missing,
         status='marking-review' if marks else 'text-review' if missing else 'eligible-local')
if out['status']=='eligible-local':
    Path('new-official',digest+'.pdf').write_bytes(data)
    Path('new-official',digest+'.txt').write_text('\n\f\n'.join(texts))
Path('cda-pension-result.jsonl').write_text(json.dumps(out)+'\n')
print(out['status'],out['pages'],out['ocr'])
