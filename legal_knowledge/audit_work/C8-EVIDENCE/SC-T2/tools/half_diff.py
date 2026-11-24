"""Compare two page ranges of one PDF by text layer (normalised words), ignoring running footers.
usage: python half_diff.py <pdf> <a_start>-<a_end> <b_start>-<b_end>"""
import sys, re, difflib, pymupdf
d = pymupdf.open(sys.argv[1])
def rng(s):
    a, b = map(int, s.split("-"))
    t = []
    for i in range(a, b + 1):
        x = d[i - 1].get_text()
        x = re.sub(r"Civil Appeal No\.____of 2026 arising out of Diary No\.27246/2023 & connected matters\s*Page \d+ of 62", " ", x)
        t.append(x)
    return re.findall(r"\S+", " ".join(t))
A, B = rng(sys.argv[2]), rng(sys.argv[3])
print("words", len(A), len(B))
sm = difflib.SequenceMatcher(None, A, B, autojunk=False)
print("ratio", round(sm.ratio(), 5))
for op, i1, i2, j1, j2 in sm.get_opcodes():
    if op != "equal":
        print(op, "| A:", " ".join(A[max(0,i1-4):i2+4])[:220], "| B:", " ".join(B[max(0,j1-4):j2+4])[:220])
