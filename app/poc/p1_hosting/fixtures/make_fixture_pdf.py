"""Write a valid synthetic PDF (no dependencies) for smoke and R2-N01 range tests. No corpus content.

python make_fixture_pdf.py out.pdf                      # 1 page, ~4 KB
python make_fixture_pdf.py out.pdf --pages 300 --pad 20000   # 300 pages, each with ~20 KB incompressible padding
"""
import argparse, os

ap = argparse.ArgumentParser()
ap.add_argument("out"); ap.add_argument("--pages", type=int, default=1); ap.add_argument("--pad", type=int, default=4000)
a = ap.parse_args()
n = a.pages
objs = {1: b"<< /Type /Catalog /Pages 2 0 R >>", 3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"}
kids = []
for i in range(n):
    page_id, content_id = 4 + 2 * i, 5 + 2 * i
    kids.append(b"%d 0 R" % page_id)
    text = b"BT /F1 18 Tf 72 760 Td (Mimamsa synthetic fixture page %d - court martial section 69) Tj ET\n" % (i + 1)
    # incompressible padding as a PDF comment inside the content stream, so file size grows realistically
    pad = b"%" + os.urandom(a.pad // 2).hex().encode()[: a.pad] + b"\n"
    stream = text + pad
    objs[page_id] = b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents %d 0 R /Resources << /Font << /F1 3 0 R >> >> >>" % content_id
    objs[content_id] = b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream"
objs[2] = b"<< /Type /Pages /Kids [" + b" ".join(kids) + b"] /Count %d >>" % n
out, offs = bytearray(b"%PDF-1.4\n"), {}
for i in sorted(objs):
    offs[i] = len(out); out += b"%d 0 obj\n" % i + objs[i] + b"\nendobj\n"
x = len(out); size = max(objs) + 1
out += b"xref\n0 %d\n0000000000 65535 f \n" % size + b"".join(b"%010d 00000 n \n" % offs[i] for i in range(1, size))
out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (size, x)
open(a.out, "wb").write(out)
print(a.out, len(out), "bytes", n, "pages")
