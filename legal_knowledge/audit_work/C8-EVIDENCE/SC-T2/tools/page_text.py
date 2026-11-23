"""Print the text layer of given pages. usage: python page_text.py <pdf> <page>[,<page>...]  (1-based)"""
import sys, pymupdf
d = pymupdf.open(sys.argv[1])
for p in sys.argv[2].split(","):
    print(f"----- p.{p}"); print(d[int(p)-1].get_text())
