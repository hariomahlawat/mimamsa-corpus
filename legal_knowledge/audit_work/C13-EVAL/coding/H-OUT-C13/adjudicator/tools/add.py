# usage: add.py W  < json list of rows on stdin ; rows keyed by result columns; replaces rows of same item_id
import json, sys, csv, os
W=sys.argv[1]
cols=["item_id","host_case_numbers","proceeding","printed_disposal","substantive_result","party_specific","final_or_interim","page","para","excerpt","confidence","notes","agrees_with","reason"]
new=json.load(sys.stdin)
path=os.path.join(W,'ADJUDICATION_RESULT.csv')
old=list(csv.DictReader(open(path))) if os.path.exists(path) else []
ids={r['item_id'] for r in new}
old=[r for r in old if r['item_id'] not in ids]
allr=old+[{c:r.get(c,'') for c in cols} for r in new]
for r in new:
    assert set(r)<=set(cols), set(r)-set(cols)
with open(path,'w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=cols); w.writeheader(); w.writerows(allr)
print(len(allr),'rows', len({r['item_id'] for r in allr}),'items')
