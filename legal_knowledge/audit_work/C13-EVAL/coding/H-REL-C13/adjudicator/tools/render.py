import sys, os, fitz, csv
W, iid, pg = sys.argv[1], sys.argv[2], int(sys.argv[3])
rows = list(csv.DictReader(open(os.path.join(W, 'ADJUDICATION_SHEET.csv'))))
order=[]
for r in rows:
    if r['item_id'] not in order: order.append(r['item_id'])
if iid.isdigit(): iid = order[int(iid)]
sha = [r for r in rows if r['item_id']==iid][0]['rep_sha256']
d = fitz.open(os.path.join(W, 'src', sha + '.pdf'))
out = os.path.join(W, 'img', f'{iid}_p{pg}.png')
d[pg-1].get_pixmap(dpi=110).save(out); print(out)
