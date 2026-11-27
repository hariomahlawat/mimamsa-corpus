"""Word-level text-layer comparison of page ranges in two PDFs, after dropping bare page-number lines and 'Page N' footers.
usage: python copy_diff.py <pdfA> <a_start>-<a_end> <pdfB> <b_start>-<b_end> [max_ops]"""
import sys, re, difflib, pymupdf
def words(p, r):
    d = pymupdf.open(p); a, b = map(int, r.split("-")); out = []
    for i in range(a, b + 1):
        t = d[i - 1].get_text()
        t = "\n".join(l for l in t.splitlines() if not re.fullmatch(r"\s*(Page\s+)?\d+\s*", l))
        out += re.findall(r"\S+", t)
    return out
A, B = words(sys.argv[1], sys.argv[2]), words(sys.argv[3], sys.argv[4])
m = int(sys.argv[5]) if len(sys.argv) > 5 else 40
sm = difflib.SequenceMatcher(None, A, B, autojunk=False)
ops = [o for o in sm.get_opcodes() if o[0] != "equal"]
print("words", len(A), len(B), "ratio", round(sm.ratio(), 5), "non-equal ops", len(ops))
for op, i1, i2, j1, j2 in ops[:m]:
    print(op, "| A:", " ".join(A[i1:i2])[:160], "| B:", " ".join(B[j1:j2])[:160])
