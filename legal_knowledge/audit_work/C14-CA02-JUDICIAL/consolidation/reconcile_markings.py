"""Record candidate access dispositions and stage visually cleared originals."""
import hashlib
import json
import os
import subprocess
from pathlib import Path

import pymupdf

ROOT = Path('/workspace/c14-collection')
REVIEWED = {
    '31884edf2911': (2, 'Classification of an employment role in the merits discussion'),
    '66022adc2a88': (4, 'Judicial narrative about information received by investigating police'),
    'cdcb596a3312': (2, 'Judicial discussion of the limits of writ jurisdiction'),
    '3c3c548932e0': (7, 'Figure of speech in counsel’s argument about res judicata'),
    '188b006da52b': (11, 'Classification of educational institutions in cited reasoning'),
    'e6454d14937f': (5, 'Discussion of employee performance reports and promotion'),
}
REVIEWED = {key:([page],reason) for key,(page,reason) in REVIEWED.items()}
independent = {}
for path in sorted(Path('.').glob('marking-assurance-*.json')):
    for row in json.loads(path.read_bytes()):
        independent[row['sha256']] = row
stage = Path('marking-cleared')
stage.mkdir(exist_ok=True,mode=0o700)
register_bytes = (ROOT/'register.json').read_bytes()
blocked = {v.lower() for item in json.loads(register_bytes)['items'] for v in
           (item['doc_id'],item['source_sha256'],*item.get('derived_sha256',[]),*item.get('hosted_paths',[])) if v}
out = []
for raw in (ROOT/'C14_EXTENDED_JUDICIAL.jsonl').read_text().splitlines():
    row = json.loads(raw)
    if row['status'] != 'marking-review':
        continue
    doc, sha = row['doc_id'], row['expected_sha256']
    diag = ROOT/'extended-files'/(sha+'.review.json')
    flags = json.loads(diag.read_bytes()) if diag.is_file() else []
    item = dict(doc_id=doc, original_sha256=sha, original_marking_flags=flags,
                status='context-and-visual-review-pending')
    reviewed = independent.get(sha)
    visual = REVIEWED.get(sha[:12])
    if reviewed:
        assert reviewed['doc_id'] == doc
        if reviewed['status'] in ('visual-false-positive','visual-false-positive-cleared'):
            visual = reviewed['reviewed_pages'],reviewed['reason']
        else:
            item.update(status='independent-visual-hold',context=reviewed['reason'],
                       visual_pages=reviewed['reviewed_pages'])
    if visual and not any(v in (doc+' '+sha+' '+row['source_url']).lower() for v in blocked):
        visual_pages, context = visual
        local = [ROOT/d/(sha+'.pdf') for d in ('batch-files','extended-files','official-files')]
        local.append(Path('visual-review')/(sha+'.pdf'))
        source = next(p for p in local if p.is_file())
        data = source.read_bytes()
        assert hashlib.sha256(data).hexdigest()==sha and data.rstrip().endswith(b'%%EOF')
        assert {f[0] for f in flags if f[1]=='ambiguous-body'} <= set(visual_pages)
        assert not any(f[1]=='standalone-marking' for f in flags)
        with pymupdf.open(stream=data,filetype='pdf') as pdf:
            assert not pdf.is_repaired and not pdf.needs_pass
            pages = []
            ocr_pages = []
            for physical in pdf:
                text = physical.get_text(sort=True)
                if len(text.split()) < 10:
                    pix = physical.get_pixmap(dpi=125,colorspace=pymupdf.csGRAY)
                    assert pix.width*pix.height <= 8_000_000
                    text = subprocess.run(['tesseract','stdin','stdout','-l','eng'],
                        input=pix.tobytes('png'),capture_output=True,check=True,timeout=45,
                        env={'PATH':os.environ['PATH'],'OMP_THREAD_LIMIT':'1'}).stdout.decode()
                    ocr_pages.append(physical.number+1)
                pages.append(text)
        if any(len(p.split())<10 for p in pages):
            item.update(status='visual-false-positive-extraction-hold',visual_pages=visual_pages,context=context,
                sparse_pages=[i for i,p in enumerate(pages,1) if len(p.split())<10],ocr_pages=ocr_pages)
            out.append(item)
            continue
        text = '\n\f\n'.join(pages).encode()
        derived = hashlib.sha256(text).hexdigest()
        assert derived not in blocked
        for suffix,content in (('.pdf',data),('.txt',text)):
            path = stage/(sha+suffix)
            if path.exists():
                assert path.read_bytes()==content
            else:
                path.write_bytes(content)
        item.update(status='visual-false-positive-cleared-local',visual_pages=visual_pages,context=context,
                    derivative_sha256=derived,page_count=len(pages),ocr_pages=ocr_pages,hf_verified=False)
    out.append(item)
Path('marking-dispositions.json').write_text(json.dumps(out,indent=2)+'\n')
print('Visual clearances',sum(x['status']=='visual-false-positive-cleared-local' for x in out),'of',len(out))
