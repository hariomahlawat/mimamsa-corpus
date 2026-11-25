import csv, sys, fitz
W='/tmp/claude-0/-home-user-mimamsa-corpus/9dd71a54-b050-5d1e-a2e9-2ceef8ac3e20/scratchpad/c13/coding/H-REL-C13/coder_2/'
rows=list(csv.DictReader(open(W+'tools/ORIG_SHEET.csv')))
a,b=int(sys.argv[1]),int(sys.argv[2])
ctx=int(sys.argv[3]) if len(sys.argv)>3 else 0
for i in range(a,b):
    r=rows[i]
    pg=int(r['pages_to_code'])
    print('#'*20,i,r['item_id'],'page',pg)
    try:
        d=fitz.open(W+'src/'+r['rep_sha256']+'.pdf')
    except Exception as e:
        print('OPENERR',e); continue
    print('npages',d.page_count)
    if pg<1 or pg>d.page_count: print('PAGE_ABSENT'); continue
    for p in range(max(1,pg-ctx),min(d.page_count,pg+ctx)+1):
        t=d[p-1].get_text()
        print('--- PDF page',p,'chars',len(t), '<<TARGET>>' if p==pg else '')
        print(t)
