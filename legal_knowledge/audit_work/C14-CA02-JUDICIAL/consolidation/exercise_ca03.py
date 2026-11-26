"""Run PR #59 on immutable copies of the manually enriched sample."""
import hashlib
import json
import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory

from pipeline.assessment_register import Journal
from pipeline.candidate_workflow import run_candidates

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

source=Path('/workspace/c14-collection')
rows={r['doc_id']:r for r in map(json.loads,open('package-v2/records.jsonl'))}
reviews=list(map(json.loads,open('manual-enrichment.jsonl')))
blocked={v.casefold() for item in json.loads((source/'register.json').read_bytes())['items']
         for v in (item['doc_id'],item['source_sha256'],*item.get('hosted_paths',[]),*item.get('derived_sha256',[])) if v}
with TemporaryDirectory(dir='.') as work:
    root=Path(work)
    (root/'data/raw').mkdir(parents=True)
    entries=[]
    for review in reviews:
        row=rows[review['doc_id']]
        digest=row['original_sha256']
        filename=digest+'.pdf'
        path='data/raw/'+filename
        data=next((source/folder/filename).read_bytes() for folder in ('extended-files','batch-files','official-files') if (source/folder/filename).is_file())
        assert sha(data)==digest
        (root/path).write_bytes(data)
        entries.append(dict(metadata=dict(doc_id=row['doc_id'],sha256=digest,raw_path=path,
                              page_count=row['page_count'],title=row['title_metadata']),
                declared_bytes=len(data),previous_event_id=None,recovery_state='HISTORICALLY_EXCLUDED_CANDIDATE'))
    payload=json.dumps(dict(schema='c14-candidate-batch-v1',purpose='ISOLATED_CANDIDATE_REVIEW',
                            documents=entries),sort_keys=True).encode()
    with sqlite3.connect(root/'journal.sqlite') as conn:
        journal=Journal(conn)
        allowed=lambda **values:any(v.casefold() in blocked for v in values.values())
        result=run_candidates(root,payload,expected_sha256=sha(payload),journal=journal,restricted=allowed)
        second=run_candidates(root,payload,expected_sha256=sha(payload),journal=journal,restricted=allowed)
        assert result==second and result['journal']['events']==len(entries)
        assert not result['release_allowed'] and not result['research_eligible']
        for row in entries:
            m=row['metadata']
            assert sha((root/m['raw_path']).read_bytes())==m['sha256']
        Path('ca03-isolated-receipt.json').write_text(json.dumps(result,indent=2)+'\n')
        print('CA-03 isolated documents:',len(result['documents']))
