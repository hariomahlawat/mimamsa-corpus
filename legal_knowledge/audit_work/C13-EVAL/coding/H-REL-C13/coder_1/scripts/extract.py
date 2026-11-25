import csv, os, sys, fitz
W=sys.argv[1]
rows=list(csv.DictReader(open(os.path.join(W,'CODER_SHEET.csv'))))
for i,r in enumerate(rows):
    d=fitz.open(os.path.join(W,'src',r['rep_sha256']+'.pdf'))
    p=int(r['pages_to_code']); n=d.page_count
    out=[f"### {i:03d} {r['item_id']} page {p} of {n}\n"]
    if p>n: out.append("PAGE_ABSENT\n")
    else:
        t=d[p-1].get_text()
        out.append(f"[chars={len(t.strip())}]\n"+t)
        if p>1: out.append("\n--- prev page tail ---\n"+d[p-2].get_text()[-700:])
    open(os.path.join(W,'pages',f"{i:03d}.txt"),'w').write(''.join(out))
    print(i,r['item_id'],p,n,len(d[p-1].get_text().strip()) if p<=n else 'ABSENT')
