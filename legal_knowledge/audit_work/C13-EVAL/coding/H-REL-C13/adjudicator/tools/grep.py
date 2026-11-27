import csv, os, sys, re, fitz
W = sys.argv[1]; iid = sys.argv[2]; pat = sys.argv[3]
rows = list(csv.DictReader(open(os.path.join(W, 'ADJUDICATION_SHEET.csv'))))
order=[]
for r in rows:
    if r['item_id'] not in order: order.append(r['item_id'])
if iid.isdigit(): iid = order[int(iid)]
sha = [r for r in rows if r['item_id']==iid][0]['rep_sha256']
d = fitz.open(os.path.join(W, 'src', sha + '.pdf'))
if pat.startswith('PAGE:'):
    for p in pat[5:].split(','):
        print(f'=== PAGE {p} ==='); print(d[int(p)-1].get_text())
else:
    for i, pg in enumerate(d):
        t = pg.get_text().replace('\n', ' ')
        for m in re.finditer(pat, t, re.I):
            print(f'p{i+1}: ...{t[max(0,m.start()-150):m.end()+150]}...')
