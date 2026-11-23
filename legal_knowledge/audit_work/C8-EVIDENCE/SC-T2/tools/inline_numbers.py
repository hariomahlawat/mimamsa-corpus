"""List bare-number lines (possible printed-report page numbers) per page of a PDF text layer.
usage: python inline_numbers.py <pdf>"""
import sys, re, pymupdf
d = pymupdf.open(sys.argv[1]); out = []
for i, p in enumerate(d, 1):
    n = [l.strip() for l in p.get_text().splitlines() if re.fullmatch(r"\s*\d{1,4}\s*", l)]
    if n: out.append(f"p{i}:{','.join(n)}")
print(" ".join(out) or "NONE")
