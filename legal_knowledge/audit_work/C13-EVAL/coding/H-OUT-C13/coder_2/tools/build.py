import csv,re,sys
W=sys.argv[1]
D={'allowed','partly_allowed','dismissed','dismissed_as_withdrawn','dismissed_as_infructuous','dismissed_in_default','disposed_of','disposed_of_with_directions','remanded','set_aside_and_remanded','transferred','not_final','other','unclear'}
S={'relief_granted','relief_partly_granted','relief_refused','no_adjudication','remanded_for_fresh_decision','interim_only','unclear'}
orig=list(csv.DictReader(open(f"{W}/tools/CODER_SHEET.orig.csv")))
cols=list(orig[0].keys())
codes={}
err=0
for ln,l in enumerate(open(f"{W}/tools/codes.txt"),1):
    l=l.rstrip('\n')
    if not l.strip() or l.startswith('#'): continue
    f=l.split('|')
    if len(f)==11: f.append('')
    if len(f)!=12: print("BADLEN",ln,l[:80]); err+=1; continue
    codes.setdefault(f[0],[]).append(f)
def norm(s): return re.sub(r'\s+',' ',s).strip()
def pages(iid):
    try: t=open(f"{W}/txt/{iid}.txt").read()
    except: return []
    return [norm(p) for p in re.split(r'\n=====PAGE \d+=====\n',t)[1:]]
out=[]
ids={r['item_id'] for r in orig}
for k in codes:
    if k not in ids: print("UNKNOWN",k); err+=1
for r in orig:
    iid=r['item_id']
    if iid not in codes:
        out.append(dict(coder_id='coder_2',**r)); continue
    P=pages(iid)
    for f in codes[iid]:
        _,host,proc,disp,sub,party,fi,para,exc,conf,notes,pg=f
        if notes.startswith('UNCODABLE:'):
            assert not any([host,proc,disp,sub,party,fi,para,exc,conf]),iid
        else:
            if disp not in D: print("BADDISP",iid,disp); err+=1
            if sub not in S: print("BADSUB",iid,sub); err+=1
            if fi not in ('final','interim'): print("BADFI",iid,fi); err+=1
            if conf not in ('high','medium','low'): print("BADCONF",iid,conf); err+=1
            if len(exc)>200: print("LONG",iid,len(exc)); err+=1
            if not pg:
                hits=[i+1 for i,p in enumerate(P) if norm(exc) in p]
                if not hits: print("NOTFOUND",iid,exc[:70]); err+=1
                else: pg=str(hits[-1])
        n=dict(r); n.update(host_case_numbers=host,proceeding=proc,printed_disposal=disp,substantive_result=sub,party_specific=party,final_or_interim=fi,page=pg,para=para,excerpt=norm(exc),confidence=conf,notes=notes)
        out.append(dict(coder_id='coder_2',**n))
with open(f"{W}/CODER_SHEET.csv",'w',newline='') as fh:
    w=csv.DictWriter(fh,fieldnames=['coder_id']+cols); w.writeheader(); w.writerows(out)
print("rows",len(out),"items coded",len(codes),"errors",err)
