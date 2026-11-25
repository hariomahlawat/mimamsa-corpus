import csv, random, re, sys, pymupdf
D, R = sys.argv[1], sys.argv[2]
rows=[r for r in csv.DictReader(open(D+'/scnum/SCNUM_RECONFIRMATION_C13.csv')) if not r['page_image_check']]
print('text-layer rows', len(rows))
random.seed(20261125)
samp=random.sample(rows, 22)
out=[]
for r in samp:
    doc=pymupdf.open(f"{R}/pdf/{r['sha256']}.pdf")
    pages=[p.get_text() for p in doc]
    vals=r['staged_value'].split(';')
    miss=[]; where={}
    for v in vals:
        m=re.match(r'([A-Z]+)-(\w+)-(\d{4})$', v); t,n,y=m.groups()
        hit=None
        for i,txt in enumerate(pages):
            flat=re.sub(r'\s+',' ',txt)
            for mm in re.finditer(r'(?<![\d])'+re.escape(n)+r'(?![\d])', flat):
                win=flat[max(0,mm.start()-400):mm.end()+400]
                if y in win or ('/'+y[2:]) in win: hit=i+1; break
            if hit: break
        if hit: where[v]=hit
        else: miss.append(v)
    print(r['doc_id'], 'n=',len(vals), 'miss=',miss, 'pages=',sorted(set(where.values()))[:5])
    out.append((r['doc_id'],len(vals),';'.join(miss)))
csv.writer(open(R+'/text_sample_result.csv','w')).writerows([('doc_id','n_values','missed_auto')]+out)
