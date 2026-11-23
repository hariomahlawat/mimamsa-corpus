#!/usr/bin/env python3
"""Regression checks for the two cycle-3 review findings (PR #26, Codex P2). Stdlib only.

F1  citation-lead page numbers: cycle3_citescan.py yields ONE-BASED PDF pages (text markers start at
    [[page 1]]); the register must carry that page unchanged (first, intermediate and final page cases).
F2  network-log parsing: status (column 5) and content type (column 6) are separate TSV fields; a
    '200' + 'application/pdf' HEAD result must be classified as a responding official-host PDF URL, and
    must never be reported as a held copy.
Usage: python3 check_cycle3_fixes.py   (exit 0 = pass)
"""
import os, re, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import cycle3_registers as R  # noqa: E402

fails = []

def scanner_page(text, pos):
    """Page as computed by cycle3_citescan.py (helper if present, else its documented expression)."""
    src = open(os.path.join(HERE, 'cycle3_citescan.py'), encoding='utf-8').read()
    if 'def page_of' in src:                      # helper (importable without running the scan)
        ns = {}
        exec(re.search(r'(def page_of\(.*?\n(?:    .*\n)+)', src).group(1), {'re': re}, ns)
        return ns['page_of'](text, pos)
    assert "count('[[page ')" in src, 'scanner page expression changed; update this check'
    return text[:pos].count('[[page ')

def independent_page(text, pos):
    nums = [int(m.group(1)) for m in re.finditer(r'\[\[page (\d+)\]\]', text[:pos])]
    return nums[-1] if nums else None

# ---------------- F1
pages = ['[[page %d]] filler text page %d ' % (i, i) for i in range(1, 6)]
for target in (1, 3, 5):                           # first, intermediate, final page
    txt = ''.join(p + ('Union of India v. Manjeet Singh cited here ' if i + 1 == target else '') for i, p in enumerate(pages))
    pos = txt.index('Manjeet Singh')
    pg = scanner_page(txt, pos)
    exp = independent_page(txt, pos)
    if pg != exp:
        fails.append(f'F1 scanner page {pg} != marker page {exp} (target {target})')
    scan = {'MANJEET': [['2016-01-01', 'sc-test-doc', 'Supreme Court of India', pg, ' ' * 100 + txt[max(0, pos - 50):pos + 80]]]}
    (hdr, rows), _ = R.treatment3(scan)
    lead = [r for r in rows if r[4].startswith('intern doc sc-test-doc')]
    got = lead[0][hdr.index('pdf_page')] if lead else None
    if got != str(exp):
        fails.append(f'F1 register pdf_page {got} != {exp} (citation on page {target})')
# boundary: citation before any marker (no page known) must not crash and must not invent page 1
txt0 = 'preamble Union of India v. Manjeet Singh [[page 1]] x'
pos0 = txt0.index('Manjeet'); pg0 = scanner_page(txt0, pos0)
if pg0 not in (0, None):
    fails.append(f'F1 citation before first marker gave page {pg0}')
(hdr0, rows0), _ = R.treatment3({'MANJEET': [['2016-01-01', 'sc-test-doc0', 'Supreme Court of India', pg0, ' ' * 100 + txt0]]})
lead0 = [r for r in rows0 if r[4].startswith('intern doc sc-test-doc0')]
if lead0 and lead0[0][hdr0.index('pdf_page')] != '':
    fails.append(f"F1 register invented pdf_page {lead0[0][hdr0.index('pdf_page')]} for a pre-marker citation")

# ---------------- F2
with tempfile.TemporaryDirectory() as d:
    nl = os.path.join(d, 'log.tsv')
    with open(nl, 'w') as f:
        f.write('2026-11-22T17:07:49Z\tBUTTAR\tHEAD\thttps://cdnbbsr.s3waas.gov.in/x.pdf\t200\tapplication/pdf\t0\tcontent-length: 507320;\n')
        f.write('2026-11-22T17:06:59Z\tKULDEEP\tHEAD\thttps://api.sci.gov.in/x.pdf\t404\ttext/html\t0\tContent-Length: 3283;\n')
        f.write('2026-11-22T17:07:00Z\tNITISHA\tHEAD\thttps://api.sci.gov.in/y.pdf\t200\ttext/html\t0\t\n')   # boundary: 200 but not PDF
        f.write('2026-11-22T17:08:06Z\tCONTROL_DHARAMVIR\tHEAD\thttps://api.sci.gov.in/jonew/judis/40493.pdf\tHTTP/1.1 404 Not Found;\n')
    (h1, rows), (h2, pend), _ = R.authoritative(nl)
    st = {r[0]: r[h1.index('state')] for r in rows}
    held = {r[0]: r[h1.index('official_copy_held')] for r in rows}
    if not st.get('BUTTAR', '').startswith('OFFICIAL_HOST_URL_RESPONDS_200_PDF'):
        fails.append(f"F2 BUTTAR 200 application/pdf classified as {st.get('BUTTAR')}")
    if not st.get('KULDEEP', '').startswith('OFFICIAL_HOST_URL_HEAD_INCONCLUSIVE'):
        fails.append(f"F2 KULDEEP 404 classified as {st.get('KULDEEP')}")
    if st.get('NITISHA', '').startswith('OFFICIAL_HOST_URL_RESPONDS_200_PDF'):
        fails.append('F2 NITISHA 200 text/html wrongly classified as PDF')
    if 'NOT established' not in st.get('BUTTAR', ''):
        fails.append('F2 responding-URL state does not state that identity/authenticity/acquisition are not established')
    pr = {r[1]: r[h2.index('priority')] for r in pend}
    # boundary: priority from the explicit issue-#4 P0 list, then HTTP availability (not the curated 'L' prefix)
    if any(r[2] == 'DCLR-SC-2011-L06' and r[h2.index('priority')] == 'P0' for r in pend):
        fails.append('F2 Buttar (L06, not an issue-#4 P0 case) given P0')
    if 'official_url_http_check' not in h2:
        fails.append('F2 pending queue lacks official_url_http_check column')
    if any(not v.startswith('NO') for v in held.values()):
        fails.append('F2 a responding URL was reported as a held copy')

print('\n'.join(fails) if fails else 'OK: F1 and F2 checks pass')
sys.exit(1 if fails else 0)
