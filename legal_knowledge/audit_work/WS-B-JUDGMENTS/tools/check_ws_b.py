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
# --- reconciliation checks (owner instruction, CF-WSB-PQ-C3-32 / CF-WSB-NOQUEUE) ---
import re
COMMERCIAL = re.compile(r'indiankanoon|casemine|scconline|scc\s*online|manupatra', re.I)
HOLDER_COL = re.compile(r'(url|holder|source_url|copy_url|held_copy|carrier|official_target|location|source_locator)', re.I)
for f in sorted(glob.glob(os.path.join(WS, '*.csv'))):
    rows = list(csv.DictReader(open(f, encoding='utf-8')))
    for r in rows:
        for col, v in r.items():
            if not col or not v or not HOLDER_COL.search(col) or not COMMERCIAL.search(v):
                continue
            # verbatim reproduction of the frozen curated record is allowed only when the same row flags it as not evidence
            if col.startswith('curated_') and re.search(r'commercial database .*not evidence', r.get('discrepancies', ''), re.I):
                continue
            print('COMMERCIAL DATABASE AS HOLDER/SOURCE', os.path.basename(f), list(r.values())[0], col, v[:80]); bad += 1
# completeness: every identity without a held official copy has a cycle-3 acquisition-request row (by stable spec_key)
idr = list(csv.DictReader(open(os.path.join(WS, 'identity_resolution.csv'), encoding='utf-8')))
q3 = list(csv.DictReader(open(os.path.join(WS, 'pending_acquisition_cycle3.csv'), encoding='utf-8')))
queued = {}
for r in q3:
    for k in r['spec_key'].split(';'):
        queued.setdefault(k.strip(), []).append(r)
for r in idr:
    if r['identity_state'].startswith('IDENTITY_CORROBORATED_OFFICIAL_COPY_HELD'):
        continue
    rr = queued.get(r['spec_key'])
    if not rr:
        print('UNRESOLVED IDENTITY WITHOUT CYCLE-3 QUEUE ROW', r['spec_key'], r['identity_state']); bad += 1
        continue
    for x in rr:
        if x.get('action') != 'ACQUISITION_REQUEST_ONLY' or x.get('downloaded_by_ws_b') != 'NO' or x.get('approval_state', 'NOT_APPROVED') != 'NOT_APPROVED':
            print('QUEUE ROW STATE INVALID', x['queue_id']); bad += 1
dup = [k for k, v in queued.items() if len(v) > 1]
if dup:
    print('DUPLICATE CYCLE-3 QUEUE ROWS FOR SPEC', dup); bad += 1
print('FAIL' if bad else 'OK'); sys.exit(1 if bad else 0)
