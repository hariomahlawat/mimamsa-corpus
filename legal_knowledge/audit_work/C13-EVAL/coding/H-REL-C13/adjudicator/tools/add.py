import csv, os, sys, re, fitz
W = sys.argv[1]
COLS = ["item_id","page","cited_string","cited_case_name","target","relation_type","voice","excerpt","confidence","notes","agrees_with","reason"]
OUT = os.path.join(W, 'ADJUDICATION_RESULT.csv')
sheet = list(csv.DictReader(open(os.path.join(W, 'ADJUDICATION_SHEET.csv'))))
order=[]
for r in sheet:
    if r['item_id'] not in order: order.append(r['item_id'])
sha = {r['item_id']: r['rep_sha256'] for r in sheet}
pg = {r['item_id']: r['pages_to_code'] for r in sheet}
new = []
for line in sys.stdin.read().split('\n'):
    if not line.strip(): continue
    f = [x.strip() for x in line.split('¦')]
    assert len(f) == 12, (len(f), line)
    if f[0].isdigit(): f[0] = order[int(f[0])]
    assert f[0] in sha, f[0]
    assert f[1] == pg[f[0]], (f[0], f[1])
    assert f[5] in ('cites','follows','applies','distinguishes','overrules','doubts','not_followed','refers_to_larger_bench','other','unclear',''), f[5]
    assert f[6] in ('court_own','quoted_passage','party_submission','lower_forum','editorial','unclear',''), f[6]
    assert f[8] in ('high','medium','low',''), f[8]
    assert f[10] in ('X','Y','NEITHER'), f[10]
    new.append(dict(zip(COLS, f)))
norm = lambda s: re.sub(r'\s+', ' ', s).strip()
for r in new:
    if r['excerpt']:
        t = norm(fitz.open(os.path.join(W,'src',sha[r['item_id']]+'.pdf'))[int(r['page'])-1].get_text())
        if norm(r['excerpt']) not in t:
            print('EXCERPT NOT FOUND:', r['item_id'], r['excerpt'][:80])
ids = {r['item_id'] for r in new}
old = list(csv.DictReader(open(OUT))) if os.path.exists(OUT) else []
old = [r for r in old if r['item_id'] not in ids]
allr = old + new
allr.sort(key=lambda r: order.index(r['item_id']))
with open(OUT, 'w', newline='') as fh:
    w = csv.DictWriter(fh, COLS); w.writeheader(); w.writerows(allr)
print('wrote', len(new), 'rows for', len(ids), 'items; total rows', len(allr), 'items', len({r['item_id'] for r in allr}))
