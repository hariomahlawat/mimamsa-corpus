#!/usr/bin/env python3
"""WS-B self-check: every CSV parses with consistent column counts; frozen originals unchanged;
no row claims legal-advisor or JAG approval; every holdings row on an official copy carries a sha256 and page."""
import csv, glob, hashlib, os, sys
WS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.abspath(os.path.join(WS, '..', '..', '..'))
FROZEN = {'legal_knowledge/curated_originals/case_law/v0.9/cases_53.jsonl': '8b8d53cd1434f7c1c6eaebe77f1fe295fb8b81b755e93276999b4b40b3c8f89a',
          'legal_knowledge/curated_originals/knowledge_base/v0.9/records_658.jsonl': '9a8f0d193065762ffa987116dc761bcb734008d2a87a946f5591741f5befcfc1'}
bad = 0
for p, h in FROZEN.items():
    if hashlib.sha256(open(os.path.join(REPO, p), 'rb').read()).hexdigest() != h:
        print('FROZEN CHANGED', p); bad += 1
for f in sorted(glob.glob(os.path.join(WS, '*.csv'))):
    rows = list(csv.reader(open(f, encoding='utf-8')))
    n = len(rows[0])
    odd = [i for i, r in enumerate(rows) if len(r) != n]
    if odd: print('BAD COLUMNS', os.path.basename(f), odd[:5]); bad += 1
    hdr = rows[0]
    for col in ('legal_advisor_state', 'jag_validation_state'):
        if col in hdr:
            k = hdr.index(col)
            if any(r[k] != 'NOT_STARTED' for r in rows[1:]): print('APPROVAL STATE SET', os.path.basename(f), col); bad += 1
    print(f'{os.path.basename(f)}: {len(rows)-1} rows x {n} cols')
H = list(csv.DictReader(open(os.path.join(WS, 'holdings_register.csv'), encoding='utf-8')))
for r in H:
    if r['copy_role'] == 'OFFICIAL_COURT_COPY' and (len(r['copy_sha256']) != 64 or not r['pdf_page']):
        print('OFFICIAL ROW MISSING SHA/PAGE', r['row_id']); bad += 1
    if r['wording_read_from'] == 'PAGE_IMAGE' and len(r['page_render_sha256']) != 64:
        print('RENDER SHA MISSING', r['row_id']); bad += 1
print('FAIL' if bad else 'OK'); sys.exit(1 if bad else 0)
