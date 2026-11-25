import sys, fitz, csv, os
W="/tmp/claude-0/-home-user-mimamsa-corpus/9dd71a54-b050-5d1e-a2e9-2ceef8ac3e20/scratchpad/c13/coding/H-HOLD-C13/coder_1"
i=int(sys.argv[1]); rows=list(csv.DictReader(open(os.path.join(W,"tools","orig.csv"))))
d=fitz.open(os.path.join(W,"src",rows[i]["rep_sha256"]+".pdf"))
for p in sys.argv[2:]:
    pg=d[int(p)-1]; pix=pg.get_pixmap(dpi=90); out=os.path.join(W,"render","%03d_p%s.png"%(i,p)); pix.save(out); print(out)
