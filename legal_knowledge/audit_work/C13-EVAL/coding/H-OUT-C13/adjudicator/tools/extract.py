import os, sys, fitz
W = sys.argv[1]
for f in sorted(os.listdir(os.path.join(W,'src'))):
    d = fitz.open(os.path.join(W,'src',f))
    out = []
    for i,p in enumerate(d):
        out.append(f'\n=== PAGE {i+1} ===\n' + p.get_text())
    t=''.join(out)
    open(os.path.join(W,'text',f[:-4]+'.txt'),'w').write(t)
    print(f[:12], len(d), len(t))
