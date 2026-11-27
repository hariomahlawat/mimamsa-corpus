# Usage: build.py  -> reads tools/codes/*.tsv? no: codes.jsonl ; writes CODER_SHEET.csv with coder_id column
import csv, json
W='/tmp/claude-0/-home-user-mimamsa-corpus/9dd71a54-b050-5d1e-a2e9-2ceef8ac3e20/scratchpad/c13/coding/H-REL-C13/coder_2/'
orig=list(csv.DictReader(open(W+'tools/ORIG_SHEET.csv')))
fields=['coder_id']+list(orig[0].keys())
codes={}
for line in open(W+'tools/codes.jsonl'):
    line=line.strip()
    if not line: continue
    d=json.loads(line); codes.setdefault(d['item_id'],[]).append(d)
ids={r['item_id'] for r in orig}
assert set(codes)<=ids, set(codes)-ids
out=[]
for r in orig:
    if r['item_id'] in codes:
        for c in codes[r['item_id']]:
            row=dict(r); row['coder_id']='coder_2'
            for k,v in c.items():
                if k!='item_id': row[k]=v
            if not row.get('page'): row['page']=r['pages_to_code']
            out.append(row)
    else:
        row=dict(r); row['coder_id']='coder_2'; out.append(row)
w=csv.DictWriter(open(W+'CODER_SHEET.csv','w',newline=''),fieldnames=fields)
w.writeheader(); w.writerows(out)
print('items coded',len(codes),'rows',len(out))
