import fitz, sys, os, glob
src=sys.argv[1]; out=sys.argv[2]; os.makedirs(out,exist_ok=True)
for f in sorted(glob.glob(os.path.join(src,'*.pdf'))):
    sha=os.path.basename(f)[:-4]
    try:
        d=fitz.open(f)
        parts=[]
        for i,p in enumerate(d):
            parts.append(f"\n=====PAGE {i+1}=====\n"+p.get_text())
        t=''.join(parts)
        open(os.path.join(out,sha+'.txt'),'w').write(t)
        print(sha, d.page_count, len(t.strip()))
    except Exception as e:
        print(sha,'ERR',e)
