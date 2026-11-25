import csv, os, sys, re
W = sys.argv[1]
rows = list(csv.DictReader(open(os.path.join(W, 'ADJUDICATION_SHEET.csv'))))
order = []
for r in rows:
    if r['item_id'] not in order: order.append(r['item_id'])
sel = sys.argv[2:]
idx = [order[int(s)] if s.isdigit() else s for s in sel]
for iid in idx:
    t = open(os.path.join(W, 'text', iid + '.txt')).read()
    m = re.search(r'===== PAGE \d+ <<CODE>>.*?(?=\n===== PAGE|\Z)', t, re.S)
    print('#'*20, order.index(iid), iid)
    print(m.group(0))
    for r in rows:
        if r['item_id'] != iid: continue
        print(f"  [{r['coding']}] p{r['page']} | {r['cited_string'][:60]} | {r['cited_case_name'][:40]} | T={r['target'][:45]} | {r['relation_type']} | {r['voice']} | {r['confidence']} | {r['notes'][:150]}")
