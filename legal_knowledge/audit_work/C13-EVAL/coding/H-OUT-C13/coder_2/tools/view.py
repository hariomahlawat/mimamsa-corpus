import sys,re,csv
W=sys.argv[1]; a,b=int(sys.argv[2]),int(sys.argv[3]); H=int(sys.argv[4]) if len(sys.argv)>4 else 1400; T=int(sys.argv[5]) if len(sys.argv)>5 else 2200
rows=list(csv.DictReader(open(f"{W}/tools/CODER_SHEET.orig.csv")))
for i,r in enumerate(rows[a:b],a):
    try: t=open(f"{W}/txt/{r['item_id']}.txt").read()
    except: print(f"#### {i} {r['item_id']} NOFILE"); continue
    t=re.sub(r'[ \t]+',' ',t); t=re.sub(r'\n\s*\n+','\n',t); t=t.replace('\n',' ¶ ')
    t=re.sub(r'=====PAGE (\d+)=====',r'[[P\1]]',t)
    np=t.count('[[P')
    print(f"#### {i} {r['item_id']} {r['rep_raw_path'].split('/')[2]} pages={np}")
    print("HEAD:",t[:H]); print("TAIL:",t[-T:] if len(t)>H else ''); print()
