import csv,sys,re,fitz
W='/tmp/claude-0/-home-user-mimamsa-corpus/9dd71a54-b050-5d1e-a2e9-2ceef8ac3e20/scratchpad/c13/coding/H-REL-C13/coder_2/'
rows=list(csv.DictReader(open(W+'tools/ORIG_SHEET.csv')))
for i in map(int,sys.argv[1:]):
    d=fitz.open(W+'src/'+rows[i]['rep_sha256']+'.pdf'); t=' '.join(p.get_text() for p in d)
    hits=re.findall(r'(?i)army|military|armed forces|air force|navy|naval|court.martial|soldier|jawan|defence personnel|ex-servicem',t)
    print(i,rows[i]['item_id'],len(hits),sorted(set(h.lower() for h in hits)))
    for m in list(re.finditer(r'(?i)army|military|armed forces|air force|navy|court.martial|soldier|ex-servicem',t))[:4]:
        print('   ',t[max(0,m.start()-120):m.end()+80].replace('\n',' '))
