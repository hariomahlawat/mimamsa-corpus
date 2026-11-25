import csv, os, sys, importlib.util
W=sys.argv[1]
spec=importlib.util.spec_from_file_location('codes',os.path.join(W,'scripts','codes.py'))
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
rows=list(csv.DictReader(open(os.path.join(W,'scripts','CODER_SHEET.orig.csv'))))
cols=['coder_id']+list(rows[0].keys())
F=['cited_string','cited_case_name','target','relation_type','voice','excerpt','confidence','notes']
by={}
for c in m.C:
    by.setdefault(c[0],[]).append(c)
REL={'cites','follows','applies','distinguishes','overrules','doubts','not_followed','refers_to_larger_bench','other','unclear'}
VO={'court_own','quoted_passage','party_submission','lower_forum','editorial','unclear'}
out=[]
for i,r in enumerate(rows):
    cs=by.get(i)
    if not cs:
        d=dict(r); d['coder_id']='coder_1'; out.append(d); continue
    for c in cs:
        d=dict(r); d['coder_id']='coder_1'
        if c[1]=='U':
            d['page']=r['pages_to_code']; d['notes']=f'UNCODABLE:{c[2]} {c[3]}'
        else:
            d['page']=r['pages_to_code']
            vals=list(c[1:])
            assert len(vals)==8,(i,c)
            for k,v in zip(F,vals): d[k]=v
            assert d['relation_type'] in REL,(i,c); assert d['voice'] in VO,(i,c); assert d['confidence'] in ('high','medium','low'),(i,c)
        out.append(d)
with open(os.path.join(W,'CODER_SHEET.csv'),'w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=cols); w.writeheader(); w.writerows(out)
coded=set(by); print('items coded',len(coded),'rows',len(out),'missing',[i for i in range(len(rows)) if i not in coded][:20])
