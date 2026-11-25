import csv,os,re,glob,sys
T=os.path.dirname(os.path.abspath(__file__)); W=os.path.dirname(T)
D={'allowed','partly_allowed','dismissed','dismissed_as_withdrawn','dismissed_as_infructuous','dismissed_in_default','disposed_of','disposed_of_with_directions','remanded','set_aside_and_remanded','transferred','not_final','other','unclear'}
S={'relief_granted','relief_partly_granted','relief_refused','no_adjudication','remanded_for_fresh_decision','interim_only','unclear'}
C={}
MAINSTORE={'HO13-299e337653','HO13-b3ece22f38','HO13-c123b2ef4d','HO13-5f043e05ca','HO13-c7541dbf29'}
def R(iid,hcn,rows):
    C[iid]=('R',hcn,rows)
def U(iid,code,expl,page=''):
    C[iid]=('U',code,expl,page)
for f in sorted(glob.glob(os.path.join(T,'codes','*.py'))):
    exec(open(f).read(),{'R':R,'U':U})
orig=list(csv.DictReader(open(os.path.join(T,'CODER_SHEET.orig.csv'))))
cols=list(orig[0].keys())
def norm(s): 
    s=s.replace('­','')
    return re.sub(r'\s+',' ',s).strip()
out=[];errs=[]
for r in orig:
    iid=r['item_id']
    if iid not in C: out.append(dict(r)); continue
    c=C[iid]
    if c[0]=='U':
        d=dict(r); d['notes']=f'UNCODABLE:{c[1]} {c[2]}'; d['page']=str(c[3]); out.append(d); continue
    txt=open(os.path.join(T,'txt',r['rep_sha256']+'.txt')).read()
    pages=re.split(r'\n=====PAGE \d+=====\n',txt)[1:]
    for (proc,disp,sub,party,foi,page,para,exc,conf,notes) in c[2]:
        assert disp in D,(iid,disp); assert sub in S,(iid,sub); assert foi in ('final','interim'),(iid,foi); assert conf in ('high','medium','low'),iid
        if len(exc)>200: errs.append((iid,'excerpt>200'))
        pg=norm(pages[int(page)-1]) if int(page)<=len(pages) else ''
        if 'page image' not in notes and norm(exc) not in pg: errs.append((iid,'excerpt not on page',page,exc[:60]))
        d=dict(r); d.update(host_case_numbers=c[1],proceeding=proc,printed_disposal=disp,substantive_result=sub,party_specific=party,final_or_interim=foi,page=str(page),para=str(para),excerpt=exc,confidence=conf,notes=notes)
        out.append(d)
with open(os.path.join(W,'CODER_SHEET.csv'),'w',newline='') as fh:
    w=csv.DictWriter(fh,fieldnames=['coder_id']+cols); w.writeheader()
    for d in out:
        d['coder_id']='coder_1'
        if d['item_id'] in MAINSTORE and d['notes'] and 'store=HF@main' not in d['notes']: d['notes']=d['notes']+' store=HF@main (absent at 5524c3d9; sha256 verified at main and at 15bd03cc).'
        w.writerow(d)
print('coded',len(C),'of',len(orig),'rows',len(out))
for e in errs: print('ERR',e)

