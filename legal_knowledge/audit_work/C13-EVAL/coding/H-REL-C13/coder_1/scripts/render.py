import fitz,sys,csv,os
W=sys.argv[1]; idx=int(sys.argv[2]); pg=int(sys.argv[3])
rows=list(csv.DictReader(open(os.path.join(W,'scripts','CODER_SHEET.orig.csv'))))
d=fitz.open(os.path.join(W,'src',rows[idx]['rep_sha256']+'.pdf'))
d[pg-1].get_pixmap(dpi=110).save(os.path.join(W,'img',f'{idx:03d}_{pg}.png'))
