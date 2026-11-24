import subprocess, sys, json, re, collections
repo, base, old_tip, new_tip = sys.argv[1:5]
g=lambda *a: subprocess.run(["git","-C",repo,*a],capture_output=True,check=True).stdout
P="legal_knowledge/audit_work/C8-EVIDENCE"
final={l.split()[2] for l in g("ls-tree","-r",old_tip,"--",P).decode().splitlines()}
frags=set()
for c in g("rev-list",f"{base}..{old_tip}").decode().split():
    for line in g("ls-tree","-r",c,"--",P).decode().splitlines():
        meta,path=line.split("\t",1); b=meta.split()[2]
        if b in final or not re.search(r"render_run[12]\.jsonl$|page_structure\.json$",path): continue
        data=g("cat-file","blob",b).decode("utf-8","replace")
        try: objs=[json.loads(data)]
        except Exception: objs=[json.loads(l) for l in data.splitlines() if l.strip()]
        def walk(o,k="$"):
            if isinstance(o,dict):
                for kk,v in o.items(): walk(v,kk)
            elif isinstance(o,list):
                for v in o: walk(v,k)
            elif isinstance(o,str) and k in("text","first_line","last_line"):
                w=40 if k=="text" else 30
                for i in range(0,max(len(o)-w+1,0),10):
                    f=o[i:i+w]
                    if len(re.findall(r"[A-Za-z]",f))>=20: frags.add(f)
        for o in objs: walk(o)
hits=collections.Counter(); scanned=0
for line in g("ls-tree","-r","-l",new_tip).decode().splitlines():
    meta,path=line.split("\t",1); parts=meta.split()
    if path.startswith(P+"/") or parts[1]!="blob" or parts[3]=="-" or int(parts[3])>3_000_000: continue
    d=g("cat-file","blob",parts[2])
    if b"\0" in d[:8000]: continue
    d=d.decode("utf-8","replace"); scanned+=1
    n=sum(1 for f in frags if f in d)
    if n: hits[path]=n
print("text blobs scanned outside C8-EVIDENCE:",scanned)
print("files outside C8-EVIDENCE containing any fragment:",len(hits))
for p,n in hits.most_common(): print(f"  {n:5d} {p}")
