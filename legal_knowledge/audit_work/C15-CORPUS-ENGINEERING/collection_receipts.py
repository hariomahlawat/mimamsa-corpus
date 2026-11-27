"""Summarize observed queue dispositions and pin-level read-back without counting replays."""
import argparse
from collections import Counter
import json
from pathlib import Path

def load(path):
    return json.loads(path.read_bytes())

def events(path):
    with path.open() as f:
        yield from (json.loads(x) for x in f)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('consolidation',type=Path)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    root=args.consolidation
    retry=list(events(root/'judicial-retry/extended.jsonl'))
    jobs=load(root/'judicial-retry/extended-queue.json')['jobs']
    dispositions={x[0]:x[1] for batch in retry for x in batch.get('result',[])}
    verified={e['revision'] for e in retry if e.get('verified')}
    retry_files={path:sha for e in retry if e.get('revision') in verified for path,sha in e.get('files',{}).items()}
    staged=[]
    staged_origins=set()
    for file in sorted(root.glob('staged-upload*/official-upload.json')):
        pos=file.parent.name.rsplit('-',1)[-1]
        if not pos.isdecimal() or int(pos)<3:continue
        receipt=load(file)
        if receipt['verified'] and receipt['files']:
            staged_origins.update(x['sha256'] for x in receipt['entries'] if x['status']=='queued-for-upload')
            staged.append({'revision':receipt['revision'],'originals':sum(p.endswith('/original.pdf') for p in receipt['files']),
                           'derivatives':sum(p.endswith('/text.txt') for p in receipt['files']),
                           'groups':dict(Counter(x['id'].split('-')[0] for x in receipt['entries'] if x['status']=='queued-for-upload'))})
    missing_batch=[r['revision'] for r in retry if r.get('verified') is False and r['revision'] not in verified]
    result={'retry_queue':len(jobs),'distinct_retry_targets_with_disposition':len(dispositions),
            'distinct_retry_target_dispositions':dict(Counter(dispositions.values())),
            'retry_verified_originals':sum(x.endswith('/original.pdf') for x in retry_files),
            'retry_verified_derivatives':sum(x.endswith('/text.txt') for x in retry_files),
            'retry_verified_revisions':sorted(verified),'unverified_revisions':missing_batch,
            'additional_staged_verified_originals':len(staged_origins),'staged_commit_receipts':staged,
            'active_application_promotion':False}
    args.output.write_text(json.dumps(result,indent=2)+'\n')
