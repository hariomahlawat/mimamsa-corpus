import csv, os, sys, fitz
W = sys.argv[1]
out = os.path.join(W, 'text'); os.makedirs(out, exist_ok=True)
rows = list(csv.DictReader(open(os.path.join(W, 'ADJUDICATION_SHEET.csv'))))
items = {}
for r in rows: items.setdefault(r['item_id'], (r['rep_sha256'], int(r['pages_to_code'])))
for iid, (sha, pg) in items.items():
    d = fitz.open(os.path.join(W, 'src', sha + '.pdf'))
    n = d.page_count
    with open(os.path.join(out, iid + '.txt'), 'w') as f:
        f.write(f'# {iid} pages={n} code_page={pg}\n')
        for p in range(max(1, pg-1), min(n, pg+1)+1):
            t = d[p-1].get_text()
            f.write(f'\n===== PAGE {p}{" <<CODE>>" if p==pg else ""} chars={len(t)} =====\n{t}')
    print(iid, n, pg, len(d[pg-1].get_text()) if pg<=n else 'ABSENT')
