#!/usr/bin/env python3
"""Cycle 8 Workstream D: primary statutory and regulatory source completeness.

Read-only, offline, deterministic. Builds inventories and evidence matrices from
the committed registers of a Mimamsa repository snapshot. It never changes a legal
status, never infers a commencement date and never makes a network request.

Usage:
  build_c8_d.py REPO [--out DIR] [--check] [--verify-held SCRATCHPAD]

  REPO            repository snapshot root (read-only)
  --out DIR       output directory (default: the parent of this tools/ folder)
  --check         rebuild in memory and compare with the files in --out; exit 1 on drift
  --verify-held   also re-hash the held binaries / derived texts named in tools/inputs
                  and confirm every page reading (needle) on the page cited
"""
import argparse
import collections
import csv
import hashlib
import io
import json
import os
import re
import sys

AW = os.path.join('legal_knowledge', 'audit_work')
C5 = os.path.join(AW, 'SOURCE-LIBRARY-C5')
TOOLS = os.path.dirname(os.path.abspath(__file__))
INPUTS = os.path.join(TOOLS, 'inputs')

CNR = 'COMMENCEMENT NOTIFICATION REQUIRED'


# ----------------------------------------------------------------------------- io
def rcsv(path):
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def rjsonl(path):
    with open(path, encoding='utf-8') as f:
        return [json.loads(l) for l in f if l.strip()]


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def csv_text(fields, rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator='\n', extrasaction='raise')
    w.writeheader()
    for r in rows:
        w.writerow({k: ('' if r.get(k) is None else r.get(k)) for k in fields})
    return buf.getvalue()


def md_table(headers, rows):
    out = ['| ' + ' | '.join(headers) + ' |', '| ' + ' | '.join('---' for _ in headers) + ' |']
    for r in rows:
        out.append('| ' + ' | '.join(str(x).replace('|', '/').replace('\n', ' ') for x in r) + ' |')
    return '\n'.join(out)


def short(sha, n=12):
    return (sha or '')[:n]


def ids(xs, limit=None):
    xs = sorted(set(xs), key=natkey)
    if limit and len(xs) > limit:
        return ';'.join(xs[:limit]) + ';...(+%d)' % (len(xs) - limit)
    return ';'.join(xs)


def natkey(s):
    return [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', s)]


# ------------------------------------------------------------------- section parse
def secs_from_pid(pid):
    if '#' not in pid:
        return set()
    out = set()
    for x in pid.split('#', 1)[1].split(','):
        x = x.strip()
        m = re.match(r'^[sr](\d+[A-Za-z]?)$', x)
        if m:
            out.add(m.group(1).upper())
    return out


def secs_from_text(txt, kind):
    """kind 's' (sections) or 'r' (rules). Parenthesised sub-units are ignored."""
    t = re.sub(r'\([^)]*\)', '', txt or '')
    pref = r'(?:ss|s)' if kind == 's' else r'(?:rr|r)'
    out = set()
    for m in re.finditer(r'\b' + pref + r'\.\s*((?:\d+[A-Z]?\s*(?:,|and|&|->|to)?\s*)+)', t):
        for n in re.findall(r'\d+[A-Z]?', m.group(1)):
            out.add(n.upper())
    return out


# ------------------------------------------------------------------------- loader
class Data:
    def __init__(self, repo):
        self.repo = repo
        j = lambda *a: os.path.join(repo, *a)
        self.master = {r['source_id']: r for r in rcsv(j(C5, 'registers', 'source_master_register.csv'))}
        self.copies = rcsv(j(C5, 'registers', 'source_copy_register.csv'))
        self.copy_by_id = {r['copy_id']: r for r in self.copies}
        self.amend = rcsv(j(C5, 'registers', 'amendment_register.csv'))
        self.chain = rcsv(j(C5, 'registers', 'provision_amendment_chain.csv'))
        self.conflicts = rcsv(j(C5, 'registers', 'source_conflict_register.csv'))
        self.crosswalk = rcsv(j(C5, 'registers', 'corpus_crosswalk.csv'))
        self.acq = rcsv(j(C5, 'registers', 'acquisition_register.csv'))
        self.cov = json.load(open(j(C5, 'registers', 'coverage_summary.json')))
        self.held = rcsv(j(C5, 'baseline', 'held_binaries_manifest.csv'))
        self.frozen = json.load(open(j(C5, 'baseline', 'frozen_baseline_manifest.json')))
        self.cand = {}
        for f in ('A', 'B', 'C', 'D'):
            for r in rcsv(j(C5, 'discovery', f + '_candidates.csv')):
                self.cand[r['candidate_id']] = r
        self.kb = rjsonl(j('legal_knowledge', 'curated_originals', 'knowledge_base', 'v0.9', 'records_658.jsonl'))
        self.cases = rjsonl(j('legal_knowledge', 'curated_originals', 'case_law', 'v0.9', 'cases_53.jsonl'))
        self.kb_sha = sha256_file(j('legal_knowledge', 'curated_originals', 'knowledge_base', 'v0.9', 'records_658.jsonl'))
        self.cases_sha = sha256_file(j('legal_knowledge', 'curated_originals', 'case_law', 'v0.9', 'cases_53.jsonl'))
        self.cc = rcsv(j(AW, 'WS-D-QUALITY', 'canonical_coverage.csv'))
        self.v3 = {r['code']: r for r in rcsv(j(AW, 'PILOT-01', 'registers', 'source_code_resolution_v3.csv'))}
        self.ar_instr = {r['instr_id']: r for r in rcsv(j(AW, 'ARMY-RULES-CHAIN-01', 'army_rules_instrument_register.csv'))}
        self.c6_02 = rcsv(j(AW, 'C6-PREP', 'registers', 'c6_02_batch_a_files.csv'))
        self.c6_02_req = rcsv(j(AW, 'C6-PREP', 'discovery', 'c6_02_metadata_requests_v2.tsv')) if False else self._tsv(j(AW, 'C6-PREP', 'discovery', 'c6_02_metadata_requests_v2.tsv'))
        self.c6_03 = rcsv(j(AW, 'C6-PREP', 'registers', 'c6_03_desw_package.csv'))
        self.c6_04 = rcsv(j(AW, 'C6-PREP', 'registers', 'c6_04_custodian_request_inventory.csv'))
        self.c6_04d = rcsv(j(AW, 'C6-PREP', 'inputs', 'c6_04_discovery_candidates.csv'))
        self.snap1 = json.load(open(j(AW, 'ACQ-01', 'archive_org_metadata_snapshot.json')))
        self.snap2 = json.load(open(j(AW, 'ACQ-02', 'archive_org_metadata_snapshot_acq02.json')))
        self.derived_reg = {r['scratchpad_relative_path']: r for r in rcsv(j(AW, 'CALIBRATION-02', 'registers', 'held_sources_scratchpad.csv'))}
        self.aa_chain = {}
        for n in ('army_act_amendment_chain.csv', 'army_act_amendment_chain_addendum_cycle3.csv'):
            for r in rcsv(j(AW, 'WS-A-STATUTORY', n)):
                self.aa_chain[r['chain_id']] = r
        self.sched = {r['acq_id']: r for r in rcsv(j(AW, 'COORDINATION', 'CYCLE3-PLANNING', 'acquisition_schedule.csv'))}
        self.pilot_gaps = rcsv(j(AW, 'PILOT-01', 'registers', 'amendment_source_gaps.csv'))
        al = j(AW, 'AUTH-LEDGER', 'effective', 'v0000', 'coverage_summary.json')
        self.al_cov = json.load(open(al)) if os.path.exists(al) else None
        self.corr = {}
        for n in ('bns-ipc.jsonl', 'bnss-crpc.jsonl', 'bsa-iea.jsonl'):
            p = j('data', 'correspondence', n)
            if os.path.exists(p):
                self.corr[n] = (sha256_file(p), sum(1 for _ in open(p, encoding='utf-8')))
        self.held_md5 = rcsv(os.path.join(INPUTS, 'held_md5.csv'))
        self.readings = {r['reading_id']: r for r in rcsv(os.path.join(INPUTS, 'held_page_readings.csv'))}
        self.dreadings = {r['reading_id']: r for r in rcsv(os.path.join(INPUTS, 'derived_text_readings.csv'))}
        self.kb_by_id = {r['id']: r for r in self.kb}
        self.case_by_id = {r['id']: r for r in self.cases}
        self.kbx = [r for r in self.crosswalk if r['knowledge_base_record_id']]
        self.csx = [r for r in self.crosswalk if r['case_id']]

    @staticmethod
    def _tsv(path):
        with open(path, newline='', encoding='utf-8') as f:
            return list(csv.DictReader(f, delimiter='\t'))

    # helpers
    def copies_of(self, source_id):
        return [c for c in self.copies if c['source_id'] == source_id]

    def kb_for_source(self, source_id, statuses=None):
        rs = [r for r in self.kbx if r['source_id'] == source_id and (statuses is None or r['evidence_status'] in statuses)]
        return rs

    def reading(self, rid):
        r = self.readings.get(rid) or self.dreadings.get(rid)
        if rid in self.readings:
            return '%s sha256=%s p.%s ("%s")' % (rid, short(r['sha256'], 16), r['page'], r['reading_summary'])
        return '%s derived-text sha256=%s ("%s")' % (rid, short(r['sha256'], 16), r['reading_summary'])


def ref(path_key):
    return path_key


SCHED = 'COORDINATION/CYCLE3-PLANNING/acquisition_schedule.csv#'

AA_SCHED = {'AA-00': ['ACQ03-019'], 'AA-01': ['ACQ-01:act-commanders-in-chief-change-designation-1955', 'ACQ03-020'], 'AA-02': ['ACQ03-021'], 'AA-C3-01': ['ACQ03-021'],
            'AA-04': ['ACQ03-015'], 'AA-05': ['ACQ03-022'], 'AA-07': ['ACQ03-023', 'ACQ03-024'], 'AA-C3-02': ['ACQ-C3-05'], 'AA-C3-03': ['ACQ-C3-06'],
            'AA-13': ['ACQ03-027'], 'AA-09': ['ACQ03-017'], 'AA-10': ['ACQ03-025'], 'AA-11': ['ACQ03-018']}
AR_SCHED_FIXED = {'AR-001': ['ACQ03-026'], 'AR-030': ['ACQ03-028'], 'AR-036': ['ACQ03-027'], 'AR-002': ['ACQ03-010'], 'AR-003': ['ACQ03-011'], 'AR-004': ['ACQ03-012'],
                  'AR-005': ['ACQ03-013'], 'AR-032': ['ACQ03-014']}
OTHER_SCHED = {'CCCM': ['ACQ-01:rules-adjustment-jurisdiction-1978-so-488', 'ACQ-01:notif-adjustment-jurisdiction-amdt-so-4010-1986'],
               'AFT-PR': ['ACQ03-030', 'ACQ03-031', 'ACQ03-032', 'ACQ03-033', 'ACQ03-034', 'ACQ03-035'],
               'RAI-1927': ['ACQ-01:book-regs-army-india-1927'], 'GMO2023': ['ACQ-01:guide-medical-officers-mil-pensions-2023'], 'ER2023': ['ACQ-01:rules-entitlement-2023']}


def sched_txt(d, acq_ids):
    out = []
    for a in acq_ids:
        r = d.sched.get(a)
        if not r:
            continue
        out.append('%s [%s; %s; %s]%s' % (a, r['batch'], r['status_as_recorded'], r['pinned_integrity'], (' ' + r['url_as_recorded']) if r['url_as_recorded'].startswith('http') else ''))
    return ' || '.join(out)


def ar_sched(d, a):
    oid = a['origin_id']
    if oid in AR_SCHED_FIXED:
        return AR_SCHED_FIXED[oid], 'register mapping'
    dt = a['notification_date'][:10]
    hits = [k for k, r in d.sched.items() if k.startswith('ACQ03') and (dt in r['url_as_recorded'] or dt[8:10] + '-' + dt[5:7] + '-' + dt[:4] in r['item'])] if re.match(r'\d{4}-\d\d-\d\d', dt) else []
    if hits:
        return hits, 'date match'
    yr = a['notification_date'][:4]
    hits = [k for k, r in d.sched.items() if k.startswith('ACQ03') and ('.w.%s-' % yr) in r['url_as_recorded'] and 'Army' in r['item'] and 'r.187' not in r['item']]
    return hits, 'year match only (probable)' if hits else ''


# ===================================================================== TASK 1
def task_baseline(d):
    rows = []
    kb_ids = [r['id'] for r in d.kb]
    case_ids = [r['id'] for r in d.cases]
    kbx = d.kbx
    cites = [r for r in kbx if r['relationship_type'] == 'CITES']
    nocit = [r for r in kbx if r['relationship_type'] == 'NO_CITATION']
    st = collections.Counter(r['evidence_status'] for r in kbx)
    st_c = collections.Counter(r['evidence_status'] for r in cites)
    by = collections.defaultdict(list)
    for r in kbx:
        by[r['knowledge_base_record_id']].append(r)
    cls = collections.Counter()
    none_with_cit = 0
    for k, v in by.items():
        e = sum(x['evidence_status'] == 'EXACT_ANCHOR' for x in v)
        c = 'ALL_EXACT' if e == len(v) else ('SOME_EXACT' if e else 'NO_EXACT_ANCHOR')
        cls[c] += 1
        if c == 'NO_EXACT_ANCHOR' and any(x['relationship_type'] == 'CITES' for x in v):
            none_with_cit += 1
    sum_items = sum(int(r['n_items']) for r in d.cc)
    anchors = collections.Counter(r['anchor_copy_id'] for r in kbx if r['evidence_status'] == 'EXACT_ANCHOR')
    case_st = collections.Counter(r['evidence_status'] for r in d.csx)
    cw = 'SOURCE-LIBRARY-C5/registers/corpus_crosswalk.csv'

    def add(metric, reported, where, value, derivation, note=''):
        try:
            match = 'MATCH' if int(str(reported).replace(',', '')) == int(value) else 'DIFFERENCE'
        except ValueError:
            match = 'MATCH' if re.sub(r'\s', '', str(reported)) == re.sub(r'\s', '', str(value)) else 'n/a'
        rows.append(dict(metric=metric, reported_value=reported, reported_in=where, recomputed_value=value,
                         derivation=derivation, result=match, note=note))

    rep = 'SOURCE-LIBRARY-C5/reports/D6_CORPUS_COVERAGE_MATRIX.md; D8_CYCLE5_READINESS_REPORT.md; C6-01-PROVENANCE/reports/D6_CYCLE6_READINESS.md'
    add('KB records', '658', rep, len(set(kb_ids)),
        'count of distinct "id" in legal_knowledge/curated_originals/knowledge_base/v0.9/records_658.jsonl (%d lines); sha256 %s = frozen_baseline_manifest.json#original_corpus_sha256.records_658 (%s)'
        % (len(kb_ids), short(d.kb_sha, 16), 'MATCH' if d.kb_sha == d.frozen['original_corpus_sha256']['records_658'] else 'MISMATCH'))
    add('Case records', '53', rep, len(set(case_ids)),
        'count of distinct "id" in legal_knowledge/curated_originals/case_law/v0.9/cases_53.jsonl; sha256 %s = frozen manifest (%s)'
        % (short(d.cases_sha, 16), 'MATCH' if d.cases_sha == d.frozen['original_corpus_sha256']['cases_53'] else 'MISMATCH'))
    add('"KB citation items" as reported', '1,060', rep, len(kbx),
        cw + ': rows with knowledge_base_record_id non-empty (all rows, any relationship_type)',
        'Figure reproduces, but it is a crosswalk ROW count, not a citation-item count: it includes the NO_CITATION placeholder rows (next two lines).')
    add('  of which genuine citation items (relationship_type=CITES)', '1,060', rep, len(cites),
        cw + '#relationship_type=CITES; equals sum of WS-D-QUALITY/canonical_coverage.csv#n_items (%d) and WS-D canonical_coverage.md "Citation items: 983 total"' % sum_items,
        'DIFFERENCE: the true number of parsed KB citation items is %d. The reported 1,060 adds %d one-per-record NO_CITATION placeholders.' % (len(cites), len(nocit)))
    add('  of which NO_CITATION placeholder rows', 'not stated', rep, len(nocit),
        cw + '#relationship_type=NO_CITATION (one row per record that cites nothing; canonical_coverage.csv#citation_present=NO: %d)'
        % sum(1 for r in d.cc if r['citation_present'] == 'NO'), 'placeholders are counted as MISSING_EVIDENCE items in the reported 366')
    add('KB exact citation anchors', '42', rep, st['EXACT_ANCHOR'],
        cw + '#evidence_status=EXACT_ANCHOR (KB rows); anchor_copy_id: ' + '; '.join('%s=%d' % kv for kv in sorted(anchors.items())),
        'MATCH. Share of genuine citation items: %d/%d = %.1f%% (not %d/%d = %.1f%%). All 42 point to the as-notified 1954 Army Rules facsimile; currency is not implied.'
        % (st['EXACT_ANCHOR'], len(cites), 100.0 * st['EXACT_ANCHOR'] / len(cites), st['EXACT_ANCHOR'], len(kbx), 100.0 * st['EXACT_ANCHOR'] / len(kbx)))
    add('KB PARTIAL_MATCH items', '652', rep, st['PARTIAL_MATCH'], cw + '#evidence_status=PARTIAL_MATCH (KB rows; all are CITES)')
    add('KB MISSING_EVIDENCE items', '366', rep, st['MISSING_EVIDENCE'], cw + '#evidence_status=MISSING_EVIDENCE (KB rows)',
        'of which %d are genuine citation items and %d are NO_CITATION placeholders' % (st_c['MISSING_EVIDENCE'], st['MISSING_EVIDENCE'] - st_c['MISSING_EVIDENCE']))
    add('KB records with no exact anchor', '618', rep, cls['NO_EXACT_ANCHOR'],
        'records grouped by ' + cw + '#knowledge_base_record_id; class NO_EXACT_ANCHOR = no row with EXACT_ANCHOR',
        'MATCH, but %d of the 618 cite nothing at all; %d records have at least one citation item and no exact anchor' % (cls['NO_EXACT_ANCHOR'] - none_with_cit, none_with_cit))
    add('KB records, all items exact', '10', rep, cls['ALL_EXACT'], 'same grouping; every row EXACT_ANCHOR')
    add('KB records, some items exact', '30', rep, cls['SOME_EXACT'], 'same grouping; at least one but not all rows EXACT_ANCHOR')
    add('Case records EXACT / PARTIAL / MISSING', '6 / 7 / 40', rep, '%d / %d / %d' % (case_st['EXACT_ANCHOR'], case_st['PARTIAL_MATCH'], case_st['MISSING_EVIDENCE']),
        cw + '#case_id rows (53) by evidence_status')
    cs = d.cov
    add('coverage_summary.json kb items (EXACT/PARTIAL/MISSING)', '42 / 652 / 366', 'SOURCE-LIBRARY-C5/registers/coverage_summary.json#crosswalk_kb_items_by_status',
        '%d / %d / %d' % tuple(cs['crosswalk_kb_items_by_status'][k] for k in ('EXACT_ANCHOR', 'PARTIAL_MATCH', 'MISSING_EVIDENCE')), 'json values: %s' % json.dumps(cs['crosswalk_kb_items_by_status'], sort_keys=True), 'json agrees with the crosswalk recount')
    if d.al_cov is not None:
        v = d.al_cov.get('kb_records_by_anchor_class', {})
        add('AUTH-LEDGER effective v0000 NO_EXACT_ANCHOR', '618', 'AUTH-LEDGER/effective/v0000/coverage_summary.json#kb_records_by_anchor_class',
            v.get('NO_EXACT_ANCHOR', -1), 'json value; AUTH-LEDGER effective state v0000 has not changed the C5 coverage', '')
    return rows


# ===================================================================== TASK 2
def master_row(d, source_id):
    return d.master.get(source_id, {})


def copy_fields(d, copy_id):
    c = d.copy_by_id[copy_id]
    return dict(copy_id=copy_id, sha256=c['sha256'], carrier=c['copy_carrier_provenance'], provenance_class=c['copy_evidence_class'],
                eligible_for_exact_anchor=c['eligible_for_exact_anchor'], pages=c['pages'], held='YES')


def derived_fields(d, rel):
    r = d.derived_reg.get(rel, {})
    return dict(copy_id='(none: derived text only)', sha256=r.get('sha256', ''), carrier='DERIVED_TEXT (scratchpad %s; no source binary in held_binaries_manifest.csv)' % rel,
                provenance_class='NOT_A_SOURCE_COPY', eligible_for_exact_anchor='NO', pages='', held='DERIVED_TEXT_ONLY')


def kb_text_mentions(d, pattern):
    rx = re.compile(pattern, re.I)
    return sorted({r['id'] for r in d.kb if rx.search(r.get('body', '') + ' ' + r.get('references', '') + ' ' + r.get('title', ''))}, key=natkey)


INSTRUMENT_TEXT_PATTERNS = {
    'AA1950': r'\bArmy Act\b|\bAA s\.?\s?\d',
    'AR1954': r'\bArmy Rules?\b|\bAR r\.?\s?\d|\bArmy Rule \d',
    'AFT2007': r'\bAFT Act\b|Armed Forces Tribunal Act',
    'BNS2023': r'\bBNS\b|Bharatiya Nyaya Sanhita',
    'BNSS2023': r'\bBNSS\b|Bharatiya Nagarik Suraksha Sanhita',
    'BSA2023': r'\bBSA\b|Bharatiya Sakshya Adhiniyam',
    'SANHITA2024': r'1 July 2024|1st July,? 2024|commencement notification',
    'IPC1860': r'\bIPC\b|Indian Penal Code',
    'CRPC1973': r'\bCrPC\b|\bCr\.P\.C\b|Code of Criminal Procedure',
    'IEA1872': r'Indian Evidence Act|\bEvidence Act\b|\bIEA\b',
    'CCCM': r'Adjustment of Jurisdiction|1978 Rules|S\.O\.? ?4010',
    'DPP1950': r'Disposal of Private Property',
    'AFA1950': r'\bAir Force Act\b',
    'NA1957': r'\bNavy Act\b',
    'ISO2023': r'Inter-Services Organi[sz]ation|\bISO Act\b',
    'TRA': r'Tribunals Reforms',
}

INSTRUMENT_SOURCES = {
    'AA1950': ['C5-SRC-P0-ARMY-ACT-1950-INDIACODE'],
    'AR1954': ['C5-SRC-P0-ARMY-RULES-1954'],
    'AFT2007': ['C5-SRC-P0-AFT-ACT-2007-INDIACODE', 'C5-SRC-P1-AFT-PROC-RULES'],
    'BNS2023': ['C5-SRC-P1-BNS-2023'],
    'BNSS2023': ['C5-SRC-P0-BNSS-2023-INDIACODE'],
    'BSA2023': ['C5-SRC-P0-BSA-2023-INDIACODE'],
    'SANHITA2024': ['C5-SRC-P0-SANHITA-COMMENCEMENT-2024'],
    'IPC1860': [], 'CRPC1973': [], 'IEA1872': [],
    'CCCM': ['C5-SRC-P1-CCCM-ADJ-RULES'],
    'DPP1950': [], 'AFA1950': [], 'NA1957': [],
    'ISO2023': ['C5-SRC-P1-ISO-ACT-RULES'],
    'TRA': [],
}

INSTRUMENT_NAMES = collections.OrderedDict([
    ('AA1950', 'Army Act 1950 (Act 46 of 1950) and amending Acts'),
    ('AR1954', 'Army Rules 1954 (S.R.O. 484 of 27-11-1954) and amending S.R.O.s'),
    ('AFT2007', 'Armed Forces Tribunal Act 2007 (Act 55 of 2007), amendments (Finance Act 2017; TRA 2021; TRA 2026) and AFT Procedure/Practice Rules'),
    ('TRA', 'Tribunals Reforms Acts 2021 (33 of 2021) and 2026 (17 of 2026) (shown under AFT2007)'),
    ('BNS2023', 'Bharatiya Nyaya Sanhita 2023 (Act 45 of 2023)'),
    ('BNSS2023', 'Bharatiya Nagarik Suraksha Sanhita 2023 (Act 46 of 2023)'),
    ('BSA2023', 'Bharatiya Sakshya Adhiniyam 2023 (Act 47 of 2023)'),
    ('SANHITA2024', 'Commencement notifications for BNS, BNSS and BSA (Gazette Extraordinary 24-02-2024)'),
    ('IPC1860', 'Indian Penal Code 1860 (historical)'),
    ('CRPC1973', 'Code of Criminal Procedure 1973 (historical)'),
    ('IEA1872', 'Indian Evidence Act 1872 (historical)'),
    ('CCCM', 'Criminal Courts and Court-martial (Adjustment of Jurisdiction) Rules 1978 and S.O. 4010 of 1986'),
    ('DPP1950', 'Army and Air Force (Disposal of Private Property) Act 1950 and Amendment Act 2000'),
    ('AFA1950', 'Air Force Act 1950 (Act 45 of 1950)'),
    ('NA1957', 'Navy Act 1957 (Act 62 of 1957)'),
    ('ISO2023', 'Inter-Services Organisations (Command, Control and Discipline) Act 2023 and Rules 2025'),
])


def task_matrix(d):
    rows = []
    M = 'SOURCE-LIBRARY-C5/registers/source_master_register.csv#'
    CP = 'SOURCE-LIBRARY-C5/registers/source_copy_register.csv#'
    AM = 'SOURCE-LIBRARY-C5/registers/amendment_register.csv#'
    AQ = 'SOURCE-LIBRARY-C5/registers/acquisition_register.csv#'
    C6 = 'C6-PREP/registers/c6_02_batch_a_files.csv#'
    n = [0]

    def add(key, category, item, source_id='', copy_id=None, derived=None, completeness='', missing='', gaps='', route='', evidence=''):
        n[0] += 1
        m = master_row(d, source_id) if source_id else {}
        parent_only = bool(source_id) and not copy_id and m.get('holding_state', '').startswith('HELD')
        r = dict(row_id='D-SSM-%03d' % n[0], instrument_key=key, instrument=INSTRUMENT_NAMES[key], holding_category=category, item=item,
                 c5_source_id=source_id or '(no C5 source row)', c5_holding_state=('(parent source row is %s; THIS item is not held)' % m.get('holding_state', '')) if parent_only else m.get('holding_state', ''),
                 copy_id='', sha256='', carrier='', provenance_class='', eligible_for_exact_anchor='', pages='', held='NO',
                 completeness=completeness or ('NOT HELD' if parent_only else (m.get('completeness_status', '') if source_id else '')), what_is_missing=missing, gap_flags=gaps,
                 acquisition_route=route, evidence=evidence)
        if copy_id:
            r.update(copy_fields(d, copy_id))
            evidence = (CP + copy_id + '; ' + evidence).strip('; ')
            r['evidence'] = evidence
        elif derived:
            r.update(derived_fields(d, derived))
        rows.append(r)
        return r

    # ---- Army Act 1950
    k = 'AA1950'
    add(k, 'ORIGINAL_ENACTMENT', 'Army Act 1950 as enacted: Gazette of India Extraordinary No.306 of 1950', 'C5-SRC-P0-ARMY-ACT-1950',
        missing='the enacted (Gazette) text; no copy held', gaps='ORIGINAL_ENACTMENT_NOT_HELD',
        route='C5-ACQ-01; archive.org in.gazette.e.1950.306/E-2350-1950-0011-109089.pdf (md5 68bcdd4e8db91eb83d1e6b92a393b2db, 6491633 bytes; pinned); approval A-C5-1',
        evidence=M + 'C5-SRC-P0-ARMY-ACT-1950; ' + AQ + 'C5-ACQ-01; ' + C6 + 'C5C-001')
    add(k, 'OFFICIAL_CONSOLIDATION', 'India Code compilation "As on the 21st July, 2025" (51 pp.)', 'C5-SRC-P0-ARMY-ACT-1950-INDIACODE',
        copy_id='C5-SRC-P0-ARMY-ACT-1950-INDIACODE~C1',
        missing='consolidation only: retrieval provenance undocumented (no C4 register row); cannot stand in for the enacted text; India Code amending-Acts item page BLOCKED (C5C-003)',
        gaps='CONSOLIDATION_NOT_ENACTMENT; PROVENANCE_UNDOCUMENTED',
        evidence='; '.join(d.reading(x) for x in ('R08', 'R09', 'R11')))
    add(k, 'NOTIFICATION', 'Commencement of the Act under s.1(2): S.R.O. 120 of 22-07-1950 (named only in a compilation footnote)', '',
        missing='the appointing notification S.R.O. 120/1950; compilation footnote is not evidence of commencement', gaps=CNR,
        route='not in C5 acquisition_register / C6-02; probable candidate in ACQ-03 (PR #23, unmerged): ' + sched_txt(d, ['ACQ03-019']),
        evidence=AM + 'C5-AMD-AA-00; ' + d.reading('R10') + '; ' + d.reading('R11'))
    add(k, 'AUTHORITATIVE_AMENDMENT', 'Army (Amendment) Act 1992 (37 of 1992): India Code Gazette scan', 'C5-SRC-P0-AA-AMD-ACT37-1992',
        copy_id='C5-SRC-P0-AA-AMD-ACT37-1992~C1', missing='no commencement section printed: effective date NOT_STATED_PENDING_ADVICE (AQ-05)', gaps='COMMENCEMENT_NOT_STATED (AQ-05 preserved)',
        evidence=AM + 'C5-AMD-AA-08-s2..s19')
    add(k, 'AUTHORITATIVE_AMENDMENT', 'Army (Amendment) Act 1992: second held copy (PDF trailer /ID variant)', 'C5-SRC-P0-AA-AMD-ACT37-1992',
        copy_id='C5-SRC-P0-AA-AMD-ACT37-1992~C2', missing='duplicate carrier; provenance undocumented', gaps='DUPLICATE_COPY (C5-CF-C5-01 CLOSED_TECHNICAL)',
        evidence='SOURCE-LIBRARY-C5/registers/source_conflict_register.csv#C5-CF-C5-01')
    add(k, 'OFFICIAL_CONSOLIDATION', 'Army (Amendment) Act 1992: India Code text rendering (3 pp.; not a Gazette image)', 'C5-SRC-P0-AA-AMD-ACT37-1992',
        copy_id='C5-SRC-P0-AA-AMD-ACT37-1992~C3', missing='text rendering only', gaps='CONSOLIDATION_NOT_ENACTMENT')
    add(k, 'AUTHORITATIVE_AMENDMENT', 'Air Force and Army Laws (Amendment) Act 1975 (13 of 1975): Gazette Extraordinary (2 pp.)', 'C5-SRC-P0-AA-AMD-ACT13-1975',
        copy_id='C5-SRC-P0-AA-AMD-ACT13-1975~C1', missing='retrieval provenance undocumented; no commencement section (s.4(2) saving); compilation states w.e.f. 25-1-1975', gaps='PROVENANCE_UNDOCUMENTED; COMMENCEMENT_NOT_DETERMINED',
        evidence=AM + 'C5-AMD-AA-06')
    add(k, 'INCOMPLETE_EXTRACT', 'Commanders-in-Chief (Change in Designation) Act 1955 (19 of 1955): India Code repealed-record text, 1 page', 'C5-SRC-P0-AA-AMD-ACT19-1955',
        copy_id='C5-SRC-P0-AA-AMD-ACT19-1955~C1', missing='the Schedule (the amendments themselves) is not in the held copy; s.1(2) appointing notification not held', gaps='INCOMPLETE_EXTRACT; ' + CNR,
        route=sched_txt(d, AA_SCHED['AA-01']),
        evidence=AM + 'C5-AMD-AA-01')
    for aid, item in [('C5-AMD-AA-02', 'Adaptation of Laws (No.3) Order 1956 (see also AA-C3-01)'), ('C5-AMD-AA-04', 'Repealing and Amending Act 1974 (56 of 1974)'),
                      ('C5-AMD-AA-05', 'Air Force and Army Laws (Amendment) Ordinance 1975'), ('C5-AMD-AA-07', 'Act 20 of 1983 (Delegated Legislation Provisions (Amendment) Act per compilation list; s.193A)'),
                      ('C5-AMD-AA-C3-02', 'Notification S.O. 3912(E) of 30-10-2019 (application to UT of J&K and Ladakh, per compilation note)'),
                      ('C5-AMD-AA-C3-03', 'Repealing and Amending Act 1957 (36 of 1957) (s.194 and Schedule repealed)'),
                      ('C5-AMD-AA-13', 'Any amending Act after 1992 (NOT_FOUND in searched sources; not proof of none)')]:
        a = next(x for x in d.amend if x['amendment_id'] == aid)
        add(k, 'NO_RELIABLE_COPY', item, 'C5-SRC-P0-AA-AMD-OTHER', missing='instrument not held; known only from %s' % a['evidence_level'], gaps='AMENDMENT_INSTRUMENT_NOT_HELD',
            route=sched_txt(d, AA_SCHED.get(a['origin_id'], [])) or master_row(d, 'C5-SRC-P0-AA-AMD-OTHER').get('acquisition_state', ''), evidence=AM + aid + '; ' + SCHED + ','.join(AA_SCHED.get(a['origin_id'], [])))
    add(k, 'NOTIFICATION', 'Gazette notifications under the Army Act (s.4 application, s.9 active service, etc.)', 'C5-SRC-P1-AA-NOTIFICATIONS',
        missing='none held; discovery not performed', gaps='NOT_CHECKED', route='DISCOVERY_REQUIRED (phase 6)', evidence=M + 'C5-SRC-P1-AA-NOTIFICATIONS')
    for sid in ('C5-SRC-P2-MML-MML-VOL-2-AA--PDF', 'C5-SRC-P2-MML-MML-VOL-2-AA--DOC'):
        add(k, 'SECONDARY_COMPILATION', 'Manual of Military Law vol 2 (Army Act) owner-supplied file', sid, copy_id=sid + '~C1',
            missing='issuer/edition not established (HELD_UNVERIFIED_MANUAL); never an authority for current text', gaps='SECONDARY_ONLY', evidence=M + sid)

    # ---- Army Rules 1954
    k = 'AR1954'
    add(k, 'ORIGINAL_ENACTMENT', 'Army Rules 1954 as notified: S.R.O. 484, Gazette Pt II s.4 No.47, 27-11-1954 (88-page issue)', 'C5-SRC-P0-ARMY-RULES-1954',
        copy_id='C5-SRC-P0-ARMY-RULES-1954~C1', missing='as-notified text only; r.1 has no commencement clause (NOT_STATED_PENDING_ADVICE, AQ-05)', gaps='COMMENCEMENT_NOT_STATED (AQ-05 preserved)',
        evidence=AM + 'C5-AMD-AR-000')
    add(k, 'OFFICIAL_CONSOLIDATION', 'India Code compilation (214 pp.)', 'C5-SRC-P0-ARMY-RULES-1954-INDIACODE', copy_id='C5-SRC-P0-ARMY-RULES-1954-INDIACODE~C1',
        missing='consolidation; provenance undocumented; r.23(3) wording differs from the 1954 Gazette (C-01 CONFLICTING)', gaps='CONSOLIDATION_NOT_ENACTMENT; PROVENANCE_UNDOCUMENTED',
        evidence='SOURCE-LIBRARY-C5/registers/source_conflict_register.csv#C5-CF-C-01')
    for sid, m in sorted(d.master.items()):
        if not sid.startswith('C5-SRC-P0-AR-AMD-AR-'):
            continue
        cps = d.copies_of(sid)
        for c in cps:
            prim = c['copy_evidence_class'] == 'DOCUMENTED_PRIMARY_COPY'
            decl = 'declaration' in m['title']
            add(k, 'NOTIFICATION' if decl else 'AUTHORITATIVE_AMENDMENT', m['title'], sid, copy_id=c['copy_id'],
                completeness=m['completeness_status'],
                missing='' if prim else 'retrieval provenance undocumented (no C4 register row); cannot yet anchor exactly',
                gaps=('R188E_DECLARATION_NOT_AMENDMENT; ' if decl else '') + ('' if prim else 'PROVENANCE_UNDOCUMENTED'),
                evidence=M + sid)
    for aid in ('C5-AMD-AR-001', 'C5-AMD-AR-030'):
        a = next(x for x in d.amend if x['amendment_id'] == aid)
        add(k, 'NO_RELIABLE_COPY', '%s (%s) - instrument not found' % (a['notification_number'], a['notification_date']), 'C5-SRC-P0-ARMY-RULES-1954',
            missing='instrument NOT_FOUND; provisions affected: %s' % a['affected_provisions'], gaps='AMENDMENT_INSTRUMENT_NOT_LOCATED', route=sched_txt(d, AR_SCHED_FIXED.get(a['origin_id'], [])) or 'discovery retry', evidence=AM + aid)
    add(k, 'NO_RELIABLE_COPY', '10 possible Army Rules S.R.O.s 2022-06-23..2026-06-24 (subject unconfirmed) + AR-036 (not searched authoritatively)', 'C5-SRC-P0-AR-AMD-POST-2022',
        missing='not held; subject of each S.R.O. unconfirmed; weekly Gazettes not searched', gaps='AMENDMENT_CHAIN_OPEN_AFTER_2022-06-06',
        route='C5-ACQ-06 (10 files pinned in C6-02); approval A-C5-1; ' + sched_txt(d, ['ACQ03-027']), evidence=M + 'C5-SRC-P0-AR-AMD-POST-2022; ' + AM + 'C5-AMD-AR-036; ' + C6 + 'C5C-004..C5C-013')
    ocr = [a for a in d.amend if a['origin_id'] in ('AR-002', 'AR-003', 'AR-004', 'AR-005', 'AR-032')]
    add(k, 'NO_RELIABLE_COPY', '5 instruments located from a text layer only: ' + '; '.join('%s %s' % (a['notification_number'], a['notification_date'][:10]) for a in ocr),
        'C5-SRC-P0-ARMY-RULES-1954', missing='no held binary registered; page-image check outstanding (LOCATED_UNVERIFIED)', gaps='TEXT_LAYER_ONLY',
        route='candidates pinned in ACQ-03 (PR #23, unmerged): ' + ', '.join(sum((AR_SCHED_FIXED[a['origin_id']] for a in ocr), [])),
        evidence='; '.join(AM + a['amendment_id'] for a in ocr))
    hints = [a for a in d.amend if a['evidence_level'].startswith('HINT_ONLY') and a['publication_source_id'] == 'C5-SRC-P0-ARMY-RULES-1954']
    add(k, 'NO_RELIABLE_COPY', '%d full-text-search hints not opened (%s)' % (len(hints), ', '.join(a['origin_id'] for a in hints)), 'C5-SRC-P0-ARMY-RULES-1954',
        missing='hints only (TO_CHECK); provisions mostly unknown', gaps='HINT_ONLY',
        route='candidates in ACQ-03 (PR #23, unmerged): ' + '; '.join('%s->%s (%s)' % (a['origin_id'], ','.join(ar_sched(d, a)[0]) or 'none', ar_sched(d, a)[1] or '-') for a in hints),
        evidence='ARMY-RULES-CHAIN-01/README.md (Completeness table); ' + SCHED + 'ACQ03-*')
    add(k, 'ORIGINAL_ENACTMENT', 'Interim rules under AA ss.21, 102(4) and 191 (Gazette Extraordinary No.8, 1950) - historical layer', 'C5-SRC-P2-ARMY-RULES-1950-INTERIM',
        missing='not held', gaps='HISTORICAL_LAYER_NOT_HELD', route='archive.org candidate C5C-002 (historical layer)', evidence=M + 'C5-SRC-P2-ARMY-RULES-1950-INTERIM')
    for sid in ('C5-SRC-P2-MML-MML-VOL-2-AR--DOC', 'C5-SRC-P2-MML-MML-VOL-2-AR--DOC-1'):
        add(k, 'SECONDARY_COMPILATION', 'Manual of Military Law vol 2 (Army Rules) owner-supplied file', sid, copy_id=sid + '~C1',
            missing='unverified manual', gaps='SECONDARY_ONLY', evidence=M + sid)

    # ---- AFT Act 2007 + TRA
    k = 'AFT2007'
    add(k, 'ORIGINAL_ENACTMENT', 'AFT Act 2007 as enacted: Gazette Extraordinary Pt II s.1, 28-12-2007', 'C5-SRC-P0-AFT-ACT-2007',
        missing='enacted text not held', gaps='ORIGINAL_ENACTMENT_NOT_HELD',
        route='C5-ACQ-02; in.gazette.central.e.2007-12-28.020/020.pdf (md5 4cf633923182d8a4d87a9ad9d51f3c11, 574004 bytes); duplicate item C5C-017 identical md5; A-C5-1',
        evidence=M + 'C5-SRC-P0-AFT-ACT-2007; ' + C6 + 'C5C-016')
    add(k, 'OFFICIAL_CONSOLIDATION', 'India Code compilation (English) "As on the 1st September, 2026" (16 pp.)', 'C5-SRC-P0-AFT-ACT-2007-INDIACODE',
        copy_id='C5-SRC-P0-AFT-ACT-2007-INDIACODE~C1', missing='consolidation; provenance undocumented', gaps='CONSOLIDATION_NOT_ENACTMENT; PROVENANCE_UNDOCUMENTED',
        evidence='; '.join(d.reading(x) for x in ('R01', 'R02', 'R05')))
    add(k, 'OFFICIAL_CONSOLIDATION', 'India Code compilation (Hindi) (13 pp.)', 'C5-SRC-P0-AFT-ACT-2007-INDIACODE', copy_id='C5-SRC-P0-AFT-ACT-2007-INDIACODE~C2',
        missing='Hindi text; not page-equivalent to the English compilation', gaps='CONSOLIDATION_NOT_ENACTMENT')
    acq_txt = ' '.join(json.dumps(r) for r in d.acq + d.c6_02 + list(d.sched.values()))
    so14 = 'S.O. 14(E)' in acq_txt
    add(k, 'NOTIFICATION', 'Commencement of the Act under s.1(2): Notifn. S.O. 14(E) of 13-06-2008 (named only in a compilation footnote; date stated 15-06-2008)', '',
        missing='the appointing notification', gaps=CNR,
        route='NOT REGISTERED: string "S.O. 14(E)" %s in acquisition_register.csv / c6_02_batch_a_files.csv / COORDINATION acquisition_schedule.csv; discovery required' % ('FOUND' if so14 else 'NOT FOUND'),
        evidence=d.reading('R03') + '; ' + d.reading('R04'))
    add(k, 'NO_RELIABLE_COPY', 'Finance Act 2017 (7 of 2017) s.181 (inserted s.9A; compilation says w.e.f. 26-5-2017)', '',
        missing='amending instrument not held and not in the C5 master register', gaps='AMENDMENT_INSTRUMENT_NOT_HELD; NOT_REGISTERED; COMMENCEMENT_BASIS_NOT_EVIDENCED',
        route='discovery required (Gazette of India 2017)', evidence=d.reading('R02') + '; ' + d.reading('R06'))
    pg = next((g for g in d.pilot_gaps if g['gap_id'] == 'AMD-16'), {})
    add(k, 'NO_RELIABLE_COPY', 'Tribunals Reforms Act 2021 (33 of 2021) (listed as an amending Act; no footnote in the held compilation shows which AFT provisions it changed)', '',
        missing='instrument not held and not in the C5 master register. PILOT-01 amendment_source_gaps.csv#AMD-16 records "%s" for a corpus doc id, but no such binary is in held_binaries_manifest.csv (unverified claim)' % pg.get('held_in_corpus', ''),
        gaps='AMENDMENT_INSTRUMENT_NOT_HELD; NOT_REGISTERED; PROVISIONS_AFFECTED_UNKNOWN', route='discovery required (Gazette of India 2021)',
        evidence=d.reading('R02') + '; ' + d.reading('R20') + '; PILOT-01/registers/amendment_source_gaps.csv#AMD-16')
    add(k, 'AUTHORITATIVE_AMENDMENT', 'Tribunals Reforms Act 2026 (17 of 2026): Gazette Extraordinary Pt II s.1 No.31, 13-08-2026 (15 pp.)', 'C5-SRC-P0-TRA-2026',
        copy_id='C5-SRC-P0-TRA-2026~C1', missing='retrieval provenance undocumented (no C4 register row); s.1(2) commencement by notification (not held)',
        gaps='PROVENANCE_UNDOCUMENTED; ' + CNR, evidence='; '.join(d.reading(x) for x in ('R18', 'R19', 'R20', 'R21', 'R22')))
    add(k, 'NOTIFICATION', 'Commencement notification(s) for TRA 2026 under s.1(2) (compilation footnote says s.9A substitution w.e.f. 25-08-2026)', '',
        missing='appointing notification(s); different dates may be appointed for different provisions', gaps=CNR, route='not registered; discovery required (egazette 2026)',
        evidence=d.reading('R07') + '; ' + d.reading('R19'))
    add(k, 'NO_RELIABLE_COPY', 'Armed Forces Tribunal (Procedure) Rules 2008 (Gazette Extraordinary Pt II s.4, 17-09-2008 per derived OCR)', 'C5-SRC-P1-AFT-PROC-RULES',
        derived='derived/statutes/rules-aft-procedure-rules-2008.txt', missing='no held binary; derived OCR text only (poor quality); provenance unknown',
        gaps='DERIVED_TEXT_ONLY', route='C5 says DISCOVERY_REQUIRED, but candidates exist in ACQ-03 (PR #23, unmerged): ' + sched_txt(d, ['ACQ03-030', 'ACQ03-033']), evidence=d.reading('D06') + '; CALIBRATION-02/registers/held_sources_scratchpad.csv#derived/statutes/rules-aft-procedure-rules-2008.txt')
    add(k, 'NO_RELIABLE_COPY', 'AFT (Procedure) Amendment Rules 2011 and AFT Practice Rules 2009', 'C5-SRC-P1-AFT-PROC-RULES', missing='no copy (binary or derived)', gaps='NOT_HELD; AMENDMENT_INSTRUMENT_NOT_HELD (2011 Rules)',
        route='candidates in ACQ-03 (PR #23, unmerged): ' + sched_txt(d, ['ACQ03-031', 'ACQ03-032', 'ACQ03-034', 'ACQ03-035']),
        evidence=M + 'C5-SRC-P1-AFT-PROC-RULES')

    # ---- BNS / BNSS / BSA
    for key, enact, cons, cons_copy, readings, notif_cand, ident, acq in [
        ('BNS2023', 'C5-SRC-P1-BNS-2023', None, None, ('D01',), 'C5C-023', 'in.gazette.central.e.2023-12-25.250883', 'C5-ACQ-20'),
        ('BNSS2023', 'C5-SRC-P0-BNSS-2023', 'C5-SRC-P0-BNSS-2023-INDIACODE', 'C5-SRC-P0-BNSS-2023-INDIACODE~C1', ('R12', 'R13', 'R14'), 'C5C-021', 'in.gazette.central.e.2023-12-25.250884', 'C5-ACQ-03'),
        ('BSA2023', 'C5-SRC-P0-BSA-2023', 'C5-SRC-P0-BSA-2023-INDIACODE', 'C5-SRC-P0-BSA-2023-INDIACODE~C1', ('R15', 'R16', 'R17'), 'C5C-022', 'in.gazette.central.e.2023-12-25.250882', 'C5-ACQ-04')]:
        c6 = next(r for r in d.c6_02 if r['archive_identifier'] == ident)
        add(key, 'ORIGINAL_ENACTMENT', '%s as enacted: Gazette Extraordinary 25-12-2023' % INSTRUMENT_NAMES[key].split(' (')[0], enact,
            missing='enacted text not held', gaps='ORIGINAL_ENACTMENT_NOT_HELD',
            route='%s; %s/%s (md5 %s, %s bytes; pinned); A-C5-1' % (acq, ident, c6['file_name'], c6['expected_md5'], c6['expected_bytes']), evidence=M + enact + '; ' + C6 + c6['candidate_id'])
        if cons:
            add(key, 'OFFICIAL_CONSOLIDATION', 'India Code compilation "As on the 6th October, 2025"', cons, copy_id=cons_copy,
                missing='consolidation; provenance undocumented; no list of amending Acts printed (absence is not proof of no amendment)', gaps='CONSOLIDATION_NOT_ENACTMENT; PROVENANCE_UNDOCUMENTED',
                evidence='; '.join(d.reading(x) for x in readings))
        else:
            add(key, 'NO_RELIABLE_COPY', 'India Code compilation "As on the 6th October, 2025" - derived text only', enact, derived='derived/statutes/act-bns-2023.txt',
                missing='no held binary of any BNS text', gaps='DERIVED_TEXT_ONLY', evidence=d.reading('D01') + '; ' + M + enact + ' (provenance: "only derived text held earlier (not a binary)")')
        nc = next(r for r in d.c6_02 if r['candidate_id'] == notif_cand)
        add(key, 'NOTIFICATION', 'Commencement notification (%s); stated in the consolidation footnote only' % nc['publication'], 'C5-SRC-P0-SANHITA-COMMENCEMENT-2024',
            missing='the notification text (date appointed and any section-specific exceptions must be read from it)', gaps=CNR,
            route='C5-ACQ-05; %s/%s (md5 %s, %s bytes; pinned); A-C5-1' % (nc['archive_identifier'], nc['file_name'], nc['expected_md5'], nc['expected_bytes']),
            evidence=d.reading(readings[1] if len(readings) > 1 else readings[0]) + '; ' + C6 + notif_cand)

    # ---- historical codes
    for key, rel, rid, corr in [('IPC1860', None, None, 'bns-ipc.jsonl'), ('CRPC1973', 'derived/statutes/act-crpc-1973.txt', 'D04', 'bnss-crpc.jsonl'),
                                ('IEA1872', 'derived/statutes/act-evidence-1872.txt', 'D05', 'bsa-iea.jsonl')]:
        add(key, 'ORIGINAL_ENACTMENT', INSTRUMENT_NAMES[key] + ' as enacted / as last amended before repeal', 'C5-SRC-P1-IPC-CRPC-IEA',
            missing='no held copy; historical version at the relevant date (pre-01-07-2024 offences) not identified', gaps='NO_RELIABLE_COPY; HISTORICAL_VERSION_NOT_IDENTIFIED',
            route='DISCOVERY_REQUIRED (not searched in C5)', evidence=M + 'C5-SRC-P1-IPC-CRPC-IEA')
        if rel:
            add(key, 'NO_RELIABLE_COPY', 'derived text rendering (edition/as-on date not printed)', 'C5-SRC-P1-IPC-CRPC-IEA', derived=rel,
                missing='no source binary; edition and amendment state unknown', gaps='DERIVED_TEXT_ONLY',
                evidence=d.reading(rid) + '; CALIBRATION-02/registers/held_sources_scratchpad.csv#' + rel)
        if corr in d.corr:
            sh, nl = d.corr[corr]
            add(key, 'SECONDARY_COMPILATION', 'section correspondence table data/correspondence/%s (%d lines)' % (corr, nl), '',
                missing='a correspondence table is not the text of either code', gaps='SECONDARY_ONLY', evidence='data/correspondence/%s sha256=%s' % (corr, short(sh, 16)))
    add('CRPC1973', 'SECONDARY_COMPILATION', 'BPRD BNSS-CrPC comparison (derived text)', '', derived='derived/statutes/ref-bprd-comparison-bnss-crpc.txt',
        missing='secondary comparison only', gaps='SECONDARY_ONLY', evidence='CALIBRATION-02/registers/held_sources_scratchpad.csv#derived/statutes/ref-bprd-comparison-bnss-crpc.txt')

    # ---- CCCM
    add('CCCM', 'NO_RELIABLE_COPY', 'Criminal Courts and Court-martial (Adjustment of Jurisdiction) Rules 1978 (S.O. 488, MHA, 09-02-1978; Gazette 25-02-1978)', 'C5-SRC-P1-CCCM-ADJ-RULES',
        missing='not held. C5 master says NOT_CHECKED / DISCOVERY_REQUIRED, but a pinned archive.org candidate already exists in ACQ-01-B2 (REGISTER INCONSISTENCY)', gaps='NOT_HELD; C5_REGISTER_NOT_RECONCILED_WITH_ACQ-01',
        route=sched_txt(d, OTHER_SCHED['CCCM'][:1]), evidence=M + 'C5-SRC-P1-CCCM-ADJ-RULES; ' + SCHED + OTHER_SCHED['CCCM'][0] + '; ACQ-01/archive_org_metadata_snapshot.json#in.gazette.central.w.1978-02-25.48290')
    add('CCCM', 'NO_RELIABLE_COPY', 'Amendment Rules 1986: MHA Notification S.O. 4010 (dated 24-11-1986 per ACQ-01/PILOT-01; "dated 6th December 1986" per the C5 master title; Gazette 06-12-1986)', 'C5-SRC-P1-CCCM-ADJ-RULES',
        missing='not held; date of the notification differs between registers (unresolved; read from the page image after acquisition)', gaps='NOT_HELD; AMENDMENT_INSTRUMENT_NOT_HELD; DATE_DISCREPANCY_BETWEEN_REGISTERS',
        route=sched_txt(d, OTHER_SCHED['CCCM'][1:]), evidence=M + 'C5-SRC-P1-CCCM-ADJ-RULES (RV-01 corrected an earlier mislabel); ' + SCHED + OTHER_SCHED['CCCM'][1] + '; PILOT-01/registers/source_discovery_2026-11-22.csv#T5-02')
    add('CCCM', 'SECONDARY_COMPILATION', 'Rajya Sabha Debates 03-03-1987 "Papers Laid on the Table" cols 207-208 (records laying of S.O. 4010/1986)', 'C5-SRC-P2-RS-PAPERS-LAID-1987',
        copy_id='C5-SRC-P2-RS-PAPERS-LAID-1987~C1', missing='parliamentary record of laying, not the instrument', gaps='NOT_THE_INSTRUMENT', evidence='C5-PIC-02; RV-01')

    # ---- DPP
    add('DPP1950', 'ORIGINAL_ENACTMENT', 'Army and Air Force (Disposal of Private Property) Act 1950 (principal Act)', 'C5-SRC-P1-DPP-ACT-1950',
        missing='no copy; no Gazette candidate recorded for the 1950 Act; India Code BLOCKED (C5C-025)', gaps='NO_RELIABLE_COPY', route='DISCOVERY_RETRY (India Code)', evidence=M + 'C5-SRC-P1-DPP-ACT-1950')
    for cid in ('C5C-026', 'C5C-027'):
        c6 = next(r for r in d.c6_02 if r['candidate_id'] == cid)
        add('DPP1950', 'AUTHORITATIVE_AMENDMENT', 'Amendment Act 2000 (archive item %s; the two items may be the same Act)' % c6['archive_identifier'], 'C5-SRC-P1-DPP-ACT-1950',
            missing='not held; file name, md5 and bytes NOT_PINNED', gaps='NOT_HELD; UNPINNED (P-C7-02-META decision)', route='C5-ACQ-21; owner decision C6-02-D1 / P-C7-02-META',
            evidence=C6 + cid)
    add('DPP1950', 'NO_RELIABLE_COPY', '1999 Bill to amend the Act (Gazette 1999-02-26)', 'C5-SRC-P1-DPP-ACT-1950', missing='not held (a Bill is not law)', gaps='NOT_HELD',
        evidence='SOURCE-LIBRARY-C5/discovery/C_candidates.csv#C5C-028')

    # ---- Air Force / Navy
    add('AFA1950', 'NO_RELIABLE_COPY', 'India Code compilation "As on the 21st July, 2025" - derived text only', '', derived='derived/statutes/act-air-force-1950.txt',
        missing='no held binary; no C5 master-register row (instrument unregistered); Gazette text not located', gaps='DERIVED_TEXT_ONLY; NOT_REGISTERED',
        evidence=d.reading('D02') + '; CALIBRATION-02/registers/held_sources_scratchpad.csv#derived/statutes/act-air-force-1950.txt')
    add('NA1957', 'NO_RELIABLE_COPY', 'India Code compilation "As on the 1st June, 2026" - derived text only', '', derived='derived/statutes/act-navy-1957.txt',
        missing='no held binary; no C5 master-register row (instrument unregistered); Gazette text not located', gaps='DERIVED_TEXT_ONLY; NOT_REGISTERED',
        evidence=d.reading('D03') + '; CALIBRATION-02/registers/held_sources_scratchpad.csv#derived/statutes/act-navy-1957.txt')
    add('ISO2023', 'NO_RELIABLE_COPY', 'ISO (Command, Control and Discipline) Act 2023 and Rules 2025', 'C5-SRC-P1-ISO-ACT-RULES', missing='not held; not searched', gaps='NOT_HELD; NOT_CHECKED',
        route='DISCOVERY_REQUIRED', evidence=M + 'C5-SRC-P1-ISO-ACT-RULES')

    # attach instrument-level dependency counts
    dep = {}
    for key in INSTRUMENT_NAMES:
        srcs = INSTRUMENT_SOURCES.get(key, [])
        xs = [r for r in d.kbx if r['source_id'] in srcs]
        tm = kb_text_mentions(d, INSTRUMENT_TEXT_PATTERNS[key])
        dep[key] = dict(items=len(xs), records=len({r['knowledge_base_record_id'] for r in xs}),
                        exact=sum(r['evidence_status'] == 'EXACT_ANCHOR' for r in xs), text=len(tm))
    for r in rows:
        dd = dep[r['instrument_key']]
        r['instrument_kb_items_crosswalk'] = dd['items']
        r['instrument_kb_records_crosswalk'] = dd['records']
        r['instrument_kb_records_text_mention'] = dd['text']
    return rows, dep


# ===================================================================== TASK 3
RESERVED = {
    # rule number -> conflict ids (C5 source_conflict_register) whose state is preserved verbatim
}


def conflict_state(d, cid):
    r = next((x for x in d.conflicts if x['conflict_id'] == cid), None)
    return '%s %s' % (cid.replace('C5-CF-', ''), r['status']) if r else cid


def task_amend(d):
    rows = []
    AM = 'SOURCE-LIBRARY-C5/registers/amendment_register.csv#'
    copy_by_sha = collections.defaultdict(list)
    for c in d.copies:
        copy_by_sha[c['sha256']].append(c)
    chain_by_instr = collections.defaultdict(list)
    for c in d.chain:
        chain_by_instr[c['instrument_ref']].append(c)
    # conflicts keyed by rule numbers they concern
    rule_conf = collections.defaultdict(list)
    for c in d.conflicts:
        if c['status'].startswith('CLOSED') or c['conflict_id'].startswith('C5-CF-WSB') or c['conflict_id'].startswith('C5-CF-OND'):
            continue
        for rn in re.findall(r'(?:\br\.|\bRule )(\d+[A-Z]?)', c['affected_provision']):
            rule_conf[rn].append(c['conflict_id'])
    sec_conf = {'75': ['C5-CF-C-06'], '76': ['C5-CF-C-06'], '121': ['C5-CF-C-05'], '127': ['C5-CF-C-05'], '133': ['C5-CF-C-07']}

    def gap_from(a):
        s = a['effective_date_status']
        if s.startswith('STATED_IN_INSTRUMENT'):
            return 'NONE (commencement stated in the instrument)'
        if 'notification' in s.lower() or 'appointing' in s.lower():
            return CNR
        if s.startswith('NOT_STATED_PENDING_ADVICE'):
            return 'NOT_STATED_PENDING_ADVICE (AQ-05; preserved, no date inferred)'
        if s.startswith('UNKNOWN') and a['evidence_level'].startswith('COMPILATION'):
            return 'INSTRUMENT_NOT_HELD (known from compilation footnotes only)'
        if s.startswith('UNKNOWN'):
            return 'INSTRUMENT_NOT_LOCATED' if a['evidence_level'] in ('NOT_FOUND', 'HINT_ONLY', 'NOT_SEARCHED_AUTHORITATIVELY') or 'not located' in s else 'UNKNOWN'
        if s.startswith('NOT_APPLICABLE'):
            return 'NOT_APPLICABLE'
        return 'NOT_DETERMINED (preserved)'

    for a in d.amend:
        fam = {'C5-SRC-P0-ARMY-RULES-1954': 'Army Rules 1954', 'C5-SRC-P0-ARMY-ACT-1950': 'Army Act 1950'}.get(a['publication_source_id'])
        if not fam:
            continue
        oid = a['origin_id']
        chains = chain_by_instr.get(oid, []) if fam == 'Army Rules 1954' else []
        ctypes = sorted({c['change_type'] for c in chains})
        instr = d.ar_instr.get(oid, {})
        held = bool(a['sha256'])
        cps = copy_by_sha.get(a['sha256'], []) if held else []
        cp = cps[0] if cps else {}
        # conflicts
        confs = set()
        if fam == 'Army Rules 1954':
            nums = secs_from_text(a['affected_provisions'], 'r') | set().union(*[secs_from_text(c['provision'], 'r') for c in chains]) if chains else secs_from_text(a['affected_provisions'], 'r')
            for rn in nums:
                confs.update(rule_conf.get(rn, []))
            if oid == 'AR-000':
                confs.update(['C5-CF-C-01', 'C5-CF-U-01'])
        else:
            for sn in secs_from_text(a['affected_provisions'], 's'):
                confs.update(sec_conf.get(sn, []))
        intervals = sorted({c['applicable_period'] for c in chains if c['effective_date_status'].startswith('STATED_IN_INSTRUMENT') and c['applicable_period'] and c['applicable_period'] != 'NOT_DETERMINED'})
        retro = instr.get('retrospective_deemed_effect_from', '')
        hist = ''
        if intervals:
            hist = ' || '.join(intervals)
        if retro:
            hist = (hist + ' || ' if hist else '') + 'retrospective deemed effect from %s as printed (legal effect: AQ-06)' % retro
        rows.append(dict(
            row_id='D-AMC-' + a['amendment_id'].replace('C5-AMD-', ''), instrument_family=fam,
            provision_affected=a['affected_provisions'], amending_instrument='%s%s' % (a['notification_number'], (' - ' + instr['short_title_as_printed']) if instr.get('short_title_as_printed') else ''),
            amendment_type=((instr.get('nature') or '') + ((' | ' if instr.get('nature') else '') + '; '.join(ctypes) if ctypes else '')) if fam == 'Army Rules 1954'
            else (d.aa_chain.get(oid, {}).get('change_as_printed', '') or 'not recorded'),
            enactment_or_issue_date=a['notification_date'], publication_date=a['publication_date'],
            commencement_as_printed=a['commencement_as_printed'],
            commencement_date_evidenced=a['effective_date'] if a['effective_date_status'].startswith('STATED_IN_INSTRUMENT') else '',
            commencement_status_preserved=a['effective_date_status'], commencement_gap=gap_from(a),
            supporting_document_held='YES' if held else 'NO', document_sha256=a['sha256'], copy_id=cp.get('copy_id', ''),
            copy_evidence_class=cp.get('copy_evidence_class', ''), gazette_identity=a['gazette_identity'],
            evidence_level=a['evidence_level'], verification_status=a['verification_status'], amendment_chain_status=a['amendment_chain_status'],
            provision_chain_rows='%d: %s' % (len(chains), ids([c['chain_row_id'] for c in chains], 12)) if chains else '0',
            unresolved_conflicts='; '.join(conflict_state(d, c) for c in sorted(confs)),
            historical_applicability_interval=hist or 'NOT EVIDENCED',
            source_evidence=AM + a['amendment_id'] + '; origin ' + a['origin_register'] + '#' + oid))

    # Army Act principal commencement: AA-00 handled above; add reserved-state rows for Army Rules
    for cid in ('C5-CF-C-01', 'C5-CF-U-01', 'C5-CF-C-02', 'C5-CF-C-03', 'C5-CF-SC4-01', 'C5-CF-C-08', 'C5-CF-U-07', 'C5-CF-C-09', 'C5-CF-U-08', 'C5-CF-U-04'):
        c = next(x for x in d.conflicts if x['conflict_id'] == cid)
        rows.append(dict(row_id='D-AMC-RES-' + cid.replace('C5-CF-', ''), instrument_family='Army Rules 1954 (reserved state)',
                         provision_affected=c['affected_provision'], amending_instrument='(see source_a / source_b in the conflict register)',
                         amendment_type='RESERVED STATE - preserved verbatim; not resolved here', enactment_or_issue_date='', publication_date='',
                         commencement_as_printed='', commencement_date_evidenced='', commencement_status_preserved='', commencement_gap='n/a',
                         supporting_document_held='', document_sha256='', copy_id='', copy_evidence_class='', gazette_identity='',
                         evidence_level='', verification_status=c['status'], amendment_chain_status='', provision_chain_rows='',
                         unresolved_conflicts='%s: %s%s' % (cid.replace('C5-CF-', ''), c['status'], (' | reserved: ' + c['reserved_status']) if c['reserved_status'] else ''),
                         historical_applicability_interval='NOT EVIDENCED',
                         source_evidence='SOURCE-LIBRARY-C5/registers/source_conflict_register.csv#%s; origin %s#%s' % (cid, c['origin_register'], c['origin_id'])))

    R = d.reading

    def hand(rid, fam, prov, instr, typ, issue, comm_ev, comm_status, gap, held, sha, copy_id, ver, conf, hist, ev):
        cp = d.copy_by_id.get(copy_id, {})
        rows.append(dict(row_id=rid, instrument_family=fam, provision_affected=prov, amending_instrument=instr, amendment_type=typ,
                         enactment_or_issue_date=issue, publication_date='', commencement_as_printed='', commencement_date_evidenced=comm_ev,
                         commencement_status_preserved=comm_status, commencement_gap=gap, supporting_document_held=held, document_sha256=sha,
                         copy_id=copy_id, copy_evidence_class=cp.get('copy_evidence_class', ''), gazette_identity='', evidence_level='', verification_status=ver,
                         amendment_chain_status='NOT_CHECKED (no amendment register exists for this instrument in C5)', provision_chain_rows='',
                         unresolved_conflicts=conf, historical_applicability_interval=hist, source_evidence=ev))

    tra = d.copy_by_id['C5-SRC-P0-TRA-2026~C1']['sha256']
    aft = d.copy_by_id['C5-SRC-P0-AFT-ACT-2007-INDIACODE~C1']['sha256']
    hand('D-AMC-AFT-00', 'AFT Act 2007', 's.1(2) commencement of the whole Act', 'Act 55 of 2007 (principal); appointing Notifn. S.O. 14(E) of 13-06-2008',
         'principal Act; commencement by notification', '2007-12-25 (assent, as printed in the compilation)', '',
         'NOT_DETERMINED from primary evidence: compilation footnote states 15-06-2008 vide S.O. 14(E)', CNR, 'NO (compilation only)', aft, 'C5-SRC-P0-AFT-ACT-2007-INDIACODE~C1',
         'COMPILATION_FOOTNOTE_ONLY', '', 'NOT EVIDENCED', '; '.join(R(x) for x in ('R03', 'R04', 'R05')))
    hand('D-AMC-AFT-01', 'AFT Act 2007', 's.9A (inserted)', 'Finance Act 2017 (7 of 2017) s.181', 'insertion (per compilation footnote)', 'NOT_DETERMINED (instrument not held)', '',
         'NOT_DETERMINED: compilation says w.e.f. 26-5-2017; commencement basis of the Finance Act provision not evidenced', 'COMMENCEMENT_BASIS_NOT_EVIDENCED (instrument not held)',
         'NO', '', '', 'COMPILATION_FOOTNOTE_ONLY', '', 'NOT EVIDENCED', R('R06') + '; ' + R('R02'))
    hand('D-AMC-AFT-02', 'AFT Act 2007', 'UNKNOWN (no footnote in the held compilation attributes any AFT provision to Act 33 of 2021)', 'Tribunals Reforms Act 2021 (33 of 2021)',
         'listed as an amending Act only', 'NOT_DETERMINED (instrument not held)', '', 'NOT_DETERMINED', 'INSTRUMENT_NOT_HELD',
         'NO', '', '', 'LISTED_IN_COMPILATION_ONLY', 'TRA 2021 is repealed by TRA 2026 s.24(1) (savings s.24(2)-(4)); effect on AFT text is a legal question, not resolved', 'NOT EVIDENCED',
         R('R02') + '; ' + R('R20') + '; PILOT-01/registers/amendment_source_gaps.csv#AMD-16')
    hand('D-AMC-AFT-03', 'AFT Act 2007', 's.9A (substituted)', 'Tribunals Reforms Act 2026 (17 of 2026) s.18 and Second Schedule item 9', 'substitution',
         '2026-08-13 (assent and Gazette, as printed)', '', 'NOT_DETERMINED from primary evidence: s.1(2) commencement by notification; compilation says w.e.f. 25-08-2026', CNR,
         'YES (amending Act held; notification not held)', tra, 'C5-SRC-P0-TRA-2026~C1', 'TEXT_LAYER_READ_C8 (provenance undocumented)', '', 'NOT EVIDENCED',
         '; '.join(R(x) for x in ('R18', 'R19', 'R21', 'R22', 'R07')))
    hand('D-AMC-AFT-04', 'AFT Act 2007 / TRA 2021', 'whole of TRA 2021 (repeal); savings for appointments and selections', 'Tribunals Reforms Act 2026 s.24', 'repeal with savings',
         '2026-08-13', '', 'NOT_DETERMINED: depends on the s.1(2) notification', CNR, 'YES (amending Act held; notification not held)', tra, 'C5-SRC-P0-TRA-2026~C1',
         'TEXT_LAYER_READ_C8 (provenance undocumented)', '', 'NOT EVIDENCED', R('R20') + '; ' + R('R19'))
    hand('D-AMC-AFT-05', 'AFT Procedure Rules', 'whole (Procedure Rules 2008; Amendment Rules 2011 r.12A/r.7; Practice Rules 2009)', 'subordinate legislation made under the AFT Act (rule-making provision not checked; not held)', 'principal and amending rules',
         'NOT_DETERMINED', '', 'NOT_DETERMINED', 'INSTRUMENT_NOT_HELD', 'NO (derived OCR text of the 2008 Rules only)', '', '', 'NOT_CHECKED', '', 'NOT EVIDENCED',
         R('D06') + '; SOURCE-LIBRARY-C5/registers/source_master_register.csv#C5-SRC-P1-AFT-PROC-RULES')

    for key, sid, cons_copy, read_ids, cand, gazette in [
        ('BNS 2023', 'C5-SRC-P1-BNS-2023', '', ('D01',), 'C5C-023', 'in.gazette.central.e.2024-02-24.252353'),
        ('BNSS 2023', 'C5-SRC-P0-BNSS-2023', 'C5-SRC-P0-BNSS-2023-INDIACODE~C1', ('R13',), 'C5C-021', 'in.gazette.central.e.2024-02-24.252354'),
        ('BSA 2023', 'C5-SRC-P0-BSA-2023', 'C5-SRC-P0-BSA-2023-INDIACODE~C1', ('R16',), 'C5C-022', 'in.gazette.central.e.2024-02-24.252352')]:
        sha = d.copy_by_id[cons_copy]['sha256'] if cons_copy else ''
        conf = 'C-07 ADVISOR QUESTION (AA s.133 names the Indian Evidence Act 1872; BSA s.1(2), s.170): not a source conflict; preserved' if key == 'BSA 2023' else ''
        hand('D-AMC-%s-COMM' % key.split()[0], key, 'whole Act (commencement); any section-specific exception must be read from the notification',
             'commencement notification (Gazette Extraordinary 24-02-2024; archive %s)' % gazette, 'commencement notification', '2023-12-25 (enactment Gazette per archive.org metadata; not held)', '',
             'NOT_DETERMINED from primary evidence: consolidation/derived footnote states 01-07-2024 (%s)' % ('derived text only' if not cons_copy else 'compilation footnote'),
             CNR, 'NO', sha, cons_copy, 'COMPILATION_FOOTNOTE_ONLY' if cons_copy else 'DERIVED_TEXT_ONLY', conf,
             'NOT EVIDENCED from primary documents',
             '; '.join(R(x) for x in read_ids) + '; C6-PREP/registers/c6_02_batch_a_files.csv#' + cand + '; SOURCE-LIBRARY-C5/registers/source_master_register.csv#C5-SRC-P0-SANHITA-COMMENCEMENT-2024')
    hand('D-AMC-BNSS-REPEAL', 'BNSS 2023 / CrPC 1973', 'CrPC 1973 whole (repeal); savings for pending matters', 'BNSS s.531', 'repeal with savings', '2023-12-25 (not held)', '',
         'operative from BNSS commencement, which is not evidenced by a held notification', CNR, 'NO (compilation only)', d.copy_by_id['C5-SRC-P0-BNSS-2023-INDIACODE~C1']['sha256'],
         'C5-SRC-P0-BNSS-2023-INDIACODE~C1', 'COMPILATION_TEXT_ONLY', '', 'CrPC applicability interval: NOT EVIDENCED from primary documents', R('R14'))
    hand('D-AMC-BSA-REPEAL', 'BSA 2023 / IEA 1872', 'Indian Evidence Act 1872 whole (repeal); savings for pending matters', 'BSA s.170', 'repeal with savings', '2023-12-25 (not held)', '',
         'operative from BSA commencement, which is not evidenced by a held notification', CNR, 'NO (compilation only)', d.copy_by_id['C5-SRC-P0-BSA-2023-INDIACODE~C1']['sha256'],
         'C5-SRC-P0-BSA-2023-INDIACODE~C1', 'COMPILATION_TEXT_ONLY', 'C-07 ADVISOR QUESTION (AA s.133); preserved', 'IEA applicability interval: NOT EVIDENCED from primary documents', R('R17'))
    hand('D-AMC-BNS-REPEAL', 'BNS 2023 / IPC 1860', 'IPC 1860 (repeal and savings under BNS s.358, cited by 6 KB items)', 'BNS s.358', 'repeal with savings', '2023-12-25 (not held)', '',
         'NOT_DETERMINED: no BNS text held (derived text only)', CNR, 'NO', '', '', 'NOT_CHECKED (no held text)', '', 'IPC applicability interval: NOT EVIDENCED',
         'SOURCE-LIBRARY-C5/registers/corpus_crosswalk.csv (provision act-bns-2023#s358); ' + R('D01'))
    return rows


# ===================================================================== TASK 4
def parse_pin(text):
    md5 = re.search(r'md5\s*([0-9a-f]{32})', text or '')
    size = re.search(r'(?:size|bytes;?)\s*(\d{4,})|(\d{4,})\s*bytes', text or '')
    return (md5.group(1) if md5 else ''), ((size.group(1) or size.group(2)) if size else '')


def task_c602(d):
    rows = []
    md5_held = {r['md5']: r for r in d.held_md5}
    snap_ids = set(d.snap1) | set(d.snap2)
    snap_md5 = {}
    for k, v in d.snap1.items():
        for f in v.get('files', []):
            snap_md5[f.get('md5')] = (k, f.get('name'))
    for k, v in d.snap2.items():
        for f in v.get('pdf_files', []):
            snap_md5[f.get('md5')] = (k, f.get('name'))
    acq = {r['acq_c5_id']: r for r in d.acq}
    seen_md5 = collections.Counter(r['expected_md5'] for r in d.c6_02 if re.match(r'^[0-9a-f]{32}$', r['expected_md5']))
    master_by_cand = {}
    for sid, m in d.master.items():
        for c in m['discovery_candidate_ids'].split(';'):
            if c.strip():
                master_by_cand.setdefault(c.strip(), sid)
    for r in d.c6_02:
        cand = d.cand.get(r['candidate_id'], {})
        cmd5, csize = parse_pin(cand.get('url_or_identifier', '') + ' ' + cand.get('notes', ''))
        if not csize:
            m = re.match(r'(\d+)', cand.get('content_length', ''))
            csize = m.group(1) if m else ''
        a = acq.get(r['acq_c5_id'], {})
        amd5, asize = parse_pin(a.get('integrity_pin', ''))
        pinned = bool(re.match(r'^[0-9a-f]{32}$', r['expected_md5']))
        checks = []
        if pinned:
            checks.append('C5 candidate md5 %s' % ('MATCH' if cmd5 == r['expected_md5'] else ('NOT_RECORDED' if not cmd5 else 'MISMATCH ' + cmd5)))
            checks.append('C5 candidate bytes %s' % ('MATCH' if csize == r['expected_bytes'] else ('NOT_RECORDED' if not csize else 'MISMATCH ' + csize)))
            if r['acq_c5_id'] in ('C5-ACQ-05', 'C5-ACQ-06'):
                checks.append('acquisition_register pin is batch-level (%s)' % (a.get('integrity_pin', '')[:60] or 'empty'))
            else:
                checks.append('acquisition_register pin %s' % ('MATCH' if (amd5 == r['expected_md5'] and asize == r['expected_bytes']) else ('MISMATCH %s/%s' % (amd5, asize) if amd5 else 'NOT_RECORDED')))
        snap = 'IN_COMMITTED_SNAPSHOT' if r['archive_identifier'] in snap_ids else 'NOT_IN_COMMITTED_SNAPSHOT (ACQ-01/ACQ-02 snapshots cover other identifiers only)'
        held_dup = md5_held.get(r['expected_md5'])
        snap_dup = snap_md5.get(r['expected_md5'])
        other = []
        if held_dup:
            other.append('HELD under %s (sha256 %s)' % (held_dup['first_held_path'], short(held_dup['sha256'], 16)))
        if snap_dup:
            other.append('same md5 as snapshot item %s/%s' % snap_dup)
        if pinned and seen_md5[r['expected_md5']] > 1:
            other.append('md5 duplicated within the batch')
        missing = ['sha256 (only computable after download)']
        if not pinned:
            missing = ['file_name', 'download_url', 'expected_md5', 'expected_bytes'] + missing
        sid = master_by_cand.get(r['candidate_id'], '')
        same_pub_held = ''
        if sid:
            sibs = [s for s in d.master if s.startswith(sid) and s != sid and d.master[s]['holding_state'].startswith('HELD')]
            if sibs:
                same_pub_held = 'compilation held for the same Act: ' + '; '.join('%s (sha256 %s)' % (s, short(d.master[s]['sha256'], 12)) for s in sibs) + ' - not the same document'
        dep = []
        for s in [sid] + [s for s in d.master if sid and s.startswith(sid) and s != sid]:
            dep += d.kb_for_source(s)
        if r['candidate_id'] in ('C5C-021', 'C5C-022', 'C5C-023'):
            dep = d.kb_for_source('C5-SRC-P0-SANHITA-COMMENCEMENT-2024')
        rows.append(dict(
            acq_c5_id=r['acq_c5_id'], candidate_id=r['candidate_id'], c5_source_id=sid, publication=r['publication'], archive_identifier=r['archive_identifier'],
            file_name=r['file_name'], expected_md5=r['expected_md5'], expected_bytes=r['expected_bytes'], pin_status='PINNED' if pinned else 'NOT_PINNED',
            metadata_reconciliation='; '.join(checks) if checks else 'not reconcilable (no pin)', committed_snapshot_check=snap,
            held_under_other_identifier='; '.join(other) if other else 'NO (expected md5 matches none of the %d held binaries, none of the ACQ-01/ACQ-02 snapshot files)' % len(d.held_md5) if pinned else 'NOT CHECKABLE (no md5)',
            related_holding=same_pub_held, missing_fields='; '.join(missing), identity_status=r['identity_status'],
            kb_items_on_dependent_sources=len(dep), kb_records_on_dependent_sources=len({x['knowledge_base_record_id'] for x in dep}),
            approval_state=r['approval_state'], prerequisites=r['prerequisites'],
            evidence='C6-PREP/registers/c6_02_batch_a_files.csv#%s; SOURCE-LIBRARY-C5/discovery/%s_candidates.csv#%s' % (r['candidate_id'], r['candidate_id'][3], r['candidate_id'])))
    return rows


# ===================================================================== TASK 5
PENSION_CODES = collections.OrderedDict([
    ('V6-S01', 'PRA2008-PT1'), ('V6-S02', 'PRA2008-PT2'), ('V6-S04', 'ER2023-APPX-I'), ('V6-S07', 'GMO2023-APPX-II'),
    ('V6-S05', 'DESW-FAQ-PIB'), ('V6-S06', 'DESW-FAQ-PIB'), ('V6-S08', 'DESW-WEB'), ('V6-S09', 'DESW-CIRCULAR-INDEX'),
    ('V6-S10', 'CIRC-OROP-CORR-2025'), ('V6-S11', 'CIRC-BROADBAND-2023'), ('V6-S12', 'CGDA-SPARSH'), ('V6-S13', 'CGDA-SPARSH'), ('V6-S22', 'DESW-WEB'),
    ('V6-S03', 'UNRESOLVED-V6-S03'),
    ('V6-S14', 'J-DHARAMVIR-2013'), ('V6-S15', 'J-RAJBIR-2015'), ('V6-S16', 'J-NSYADAV-2019'), ('V6-S17', 'J-RAMAVTAR-2014'),
    ('V6-S18', 'J-GIRISH-FEB-2026'), ('V6-S19', 'J-GIRISH-OCT-2026'), ('V6-S20', 'J-MULLIKOTE-2026'), ('V6-S21', 'AFT-ACT-2007'),
])

PENSION_TEXT = collections.OrderedDict([
    ('ER1982', r'Entitlement Rules?[^.\n]{0,30}1982|\bER[- ]?1982|1982 Entitlement'),
    ('ER2008', r'Entitlement Rules?[^.\n]{0,30}2008|\bER[- ]?2008|2008 Entitlement'),
    ('ER2023-APPX-I', r'Entitlement Rules?[^.\n]{0,30}2023|\bER[- ]?2023|2023 entitlement'),
    ('GMO-ANY', r'Guide to Medical Officers|\bGMO\b|medical guide'),
    ('PRA1961', r'Pension Regulations?[^.\n]{0,40}1961|\b1961 (?:PRA|Pension|instruments?|Regulations?)|PRA[- ]?1961|1961, 2008'),
    ('PRA2008-ANY', r'Pension Regulations?[^.\n]{0,40}2008|2008 PRA|\bPRA[- ]?2008|\bPRA\b'),
    ('CIRCULARS', r'\bcircular|MoD letter|Government letter|corrigendum|sanction letter'),
])

PEN_DOCS = collections.OrderedDict([
    ('PRA2008-PT1', ('Pension Regulations for the Army 2008, Part I', 'C5-SRC-P1-PRA-2008-PT1', 'C5-ACQ-07', 'B', 'NOT_HELD')),
    ('PRA2008-PT2', ('Pension Regulations for the Army 2008, Part II', 'C5-SRC-P1-PRA-2008-PT2', 'C5-ACQ-08', 'B', 'NOT_HELD')),
    ('PRA1961', ('Pension Regulations for the Army 1961, Parts I and II', 'C5-SRC-P1-PRA-1961', 'none (NOT_FOUND; DESW archive pages unread)', 'B', 'NOT_HELD')),
    ('ER1982', ('Entitlement Rules for Casualty Pensionary Awards 1982', 'C5-SRC-P1-ER-1982', 'none (NOT_FOUND; DISCOVERY_RETRY)', 'B', 'NOT_HELD')),
    ('ER2008', ('Entitlement Rules for Casualty Pensionary Awards 2008 (two non-identical DESW files)', 'C5-SRC-P1-ER-2008', 'C5-ACQ-10', 'B', 'NOT_HELD')),
    ('ER2023-APPX-I', ('Entitlement Rules 2023 (Appendix-I to MoD letter 21-09-2023) - complete publication', 'C5-SRC-P1-ER-GMO-2023', 'C5-ACQ-09 (49,925,674-byte file)', 'B', 'NOT_HELD_COMPLETE')),
    ('GMO2023-APPX-II', ('Guide to Medical Officers (Military Pensions) 2023 (Appendix-II) - complete publication', 'C5-SRC-P1-ER-GMO-2023', 'C5-ACQ-09 (same combined file)', 'B', 'NOT_HELD')),
    ('ER2023-HELD-INCOMPLETE', ('HELD incomplete ER-2023 copy (letter + ER-2023 App-I + annexures; GMO-2023 ABSENT) - kept distinct', 'C5-SRC-P1-ER-2023-HELD-13MB', 'n/a (held; compare after C5-ACQ-09)', 'B', 'HELD_INCOMPLETE_PROVENANCE_UNDOCUMENTED')),
    ('GMO-2002-2008', ('Guide to Medical Officers (Military Pensions) 2002 and 2008 (+2008 Ch. amendment)', 'C5-SRC-P1-GMO-2002-2008', 'none (NOT_FOUND; 404)', 'B', 'NOT_HELD')),
    ('CIRC-PRA-ER', ('PRA/ER amending circulars: Reg 18 Pt II (14-11-2013); family pension (05-10-2020); ER 2008 second appeal (2021)', 'C5-SRC-P1-PEN-CIRCULARS', 'C5-ACQ-11', 'C', 'NOT_HELD')),
    ('CIRC-BROADBAND-2023', ('MoD letter 27-12-2023 on broad-banding of disability element (V6-S11)', '', 'not registered in C5 (code UNMAPPED)', 'C', 'NOT_HELD')),
    ('CIRC-OROP-CORR-2025', ('OROP table correction letter 13-10-2025 (V6-S10, PROBABLE)', '', 'not registered in C5 (code UNMAPPED)', 'C', 'NOT_HELD')),
    ('DESW-FAQ-PIB', ('DESW FAQ (Q1-12) and PIB/DESW clarification on ER/GMO 2023 (secondary)', 'C5-SRC-P1-DESW-FAQ-PIB', 'DISCOVERY_REQUIRED', 'C', 'NOT_HELD')),
    ('DESW-WEB', ('DESW web pages (kinds of pension overview V6-S08; grievance channel V6-S22)', '', 'not registered in C5 (codes UNMAPPED)', 'C', 'NOT_HELD')),
    ('DESW-CIRCULAR-INDEX', ('DESW circulars index (V6-S09)', 'C5-SRC-P1-DESW-REPOSITORIES', 'DISCOVERY_RETRY', 'C', 'NOT_HELD')),
    ('CGDA-SPARSH', ('CGDA SPARSH portal and FAQs (V6-S12, V6-S13)', '', 'not registered in C5 (codes UNMAPPED)', 'C', 'NOT_HELD')),
    ('UNRESOLVED-V6-S03', ('Code V6-S03 (UNRESOLVABLE identity)', '', 'identity must be resolved first', 'C', 'UNKNOWN')),
    ('J-DHARAMVIR-2013', ('Dharamvir Singh v UOI (SC 02-07-2013)', 'C5-SRC-J-SC-2013-DHARAMVIR', 'provenance registration (no download)', 'B', 'HELD_PROVENANCE_UNDOCUMENTED')),
    ('J-RAJBIR-2015', ('UOI v Rajbir Singh (SC 13-02-2015)', 'C5-SRC-J-SC-2015-RAJBIR', 'provenance registration (no download); 3 non-identical copies', 'B', 'HELD_PROVENANCE_UNDOCUMENTED')),
    ('J-NSYADAV-2019', ('Ex Cfn N S Yadav v UOI (SC 2019)', 'C5-SRC-J-SC-2019-NS-YADAV', 'provenance registration (no download)', 'B', 'HELD_PROVENANCE_UNDOCUMENTED')),
    ('J-RAMAVTAR-2014', ('UOI v Ram Avtar (SC 10-12-2014)', '', 'not held; official SC copy to locate', 'B', 'NOT_HELD')),
    ('J-GIRISH-FEB-2026', ('UOI v Sgt Girish Kumar, 2026 INSC 149 (12-02-2026)', 'C5-SRC-J-SC-2026-GIRISH-FEB', 'provenance registration (no download)', 'B', 'HELD_PROVENANCE_UNDOCUMENTED')),
    ('J-GIRISH-OCT-2026', ('UOI v Sgt Girish Kumar, 2026 INSC 1113 (clarification 12-10-2026)', '', 'not held; official SC copy to locate', 'B', 'NOT_HELD')),
    ('J-MULLIKOTE-2026', ('UOI v Balakrishnan Mullikote, 2026 INSC 286 (24-03-2026)', 'C5-SRC-J-SC-2026-MULLIKOTE', 'provenance registration (no download)', 'B', 'HELD_PROVENANCE_UNDOCUMENTED')),
    ('AFT-ACT-2007', ('AFT Act 2007 (cited from pension records)', 'C5-SRC-P0-AFT-ACT-2007-INDIACODE', 'C5-ACQ-02 (Gazette)', 'A', 'HELD_COMPILATION_ONLY')),
])

CASE_PENSION = {
    # case id -> pension doc keys from the case 'provisions' field (explicit wording only)
}


def pension_case_deps(d):
    out = collections.defaultdict(set)
    for c in d.cases:
        p = ' '.join(c.get('provisions') or [])
        if re.search(r'Pension Regulations? 1961|Pension Regulation 179 \(1961|Pension Regulations for Army 1961', p):
            out['PRA1961'].add(c['id'])
        if re.search(r'Pension Regulations 2008', p):
            out['PRA2008-PT1'].add(c['id'])
        if re.search(r'Pension Regulations and Entitlement Rules', p):
            out['ER-AT-DISCHARGE (edition not stated)'].add(c['id'])
        if re.search(r'Pension Regulations \(historical', p) or re.search(r'Army pension regulations', p):
            out['PRA-EDITION-NOT-STATED'].add(c['id'])
        if re.search(r'Air Force Pension Regulation', p):
            out['PR-AIR-FORCE'].add(c['id'])
        if re.search(r'MoD (?:disability rounding|circular|letters)|Broad-banding', p):
            out['CIRCULARS (MoD letters named in case provisions)'].add(c['id'])
    return out


def task_pension(d):
    # record -> codes
    rec_codes = collections.defaultdict(set)
    for r in d.kb:
        for code in re.findall(r'\bV6-S\d\d\b', r.get('references', '')):
            rec_codes[r['id']].add(code)
    doc_recs = collections.defaultdict(set)
    for rid, codes in rec_codes.items():
        for c in codes:
            doc_recs[PENSION_CODES[c]].add(rid)
    text_recs = {}
    for k, pat in PENSION_TEXT.items():
        rx = re.compile(pat, re.I)
        text_recs[k] = {r['id'] for r in d.kb if (k != 'CIRCULARS' or r['module'] == 'M08') and rx.search(r.get('body', '') + ' ' + r.get('title', '') + ' ' + r.get('references', ''))}
    cdeps = pension_case_deps(d)
    m08 = [r['id'] for r in d.kb if r['module'] == 'M08']
    held_ok = {k for k, v in PEN_DOCS.items() if v[4].startswith('HELD')}
    rows = []
    # single-source closers
    rec_missing = {}
    for rid, codes in rec_codes.items():
        need = {PENSION_CODES[c] for c in codes}
        rec_missing[rid] = {x for x in need if PEN_DOCS[x][4] not in ('HELD_PROVENANCE_UNDOCUMENTED', 'HELD_COMPILATION_ONLY')}
    for key, (name, sid, acq, tier, state) in PEN_DOCS.items():
        cited = doc_recs.get(key, set())
        tkey = {'ER1982': 'ER1982', 'ER2008': 'ER2008', 'ER2023-APPX-I': 'ER2023-APPX-I', 'GMO2023-APPX-II': 'GMO-ANY', 'GMO-2002-2008': 'GMO-ANY',
                'PRA1961': 'PRA1961', 'PRA2008-PT1': 'PRA2008-ANY', 'PRA2008-PT2': 'PRA2008-ANY', 'CIRC-PRA-ER': 'CIRCULARS'}.get(key)
        tm = text_recs.get(tkey, set()) if tkey else set()
        sole = sorted([rid for rid in cited if rec_missing.get(rid) == {key}], key=natkey)
        cx = d.kb_for_source(sid) if sid else []
        cw_status = collections.Counter(x['evidence_status'] for x in cx)
        cases = set()
        if key == 'PRA1961':
            cases = cdeps.get('PRA1961', set())
        if key == 'PRA2008-PT1':
            cases = cdeps.get('PRA2008-PT1', set())
        if key in ('ER1982', 'ER2008', 'PRA1961'):
            cases = cases | cdeps.get('ER-AT-DISCHARGE (edition not stated)', set())
        if key == 'CIRC-PRA-ER':
            cases = cdeps.get('CIRCULARS (MoD letters named in case provisions)', set())
        m = d.master.get(sid, {})
        blockers = ''
        if acq.startswith('C5-ACQ-0') or acq.startswith('C5-ACQ-1'):
            c3 = [x for x in d.c6_03 if x['acq_c5_id'] == acq.split()[0]]
            if c3:
                blockers = '%s; %s' % (c3[0]['pr9_allow_list'], 'desw.gov.in robots.txt returned 403 (Cycle 5): fail-closed, no bypass')
        if key == 'ER2023-APPX-I':
            blockers += '; ER-2023 Appendix-I text is physically present in the held incomplete copy 29f6fa2c (pp.2-19 per RV-19) but that copy is provenance-undocumented and incomplete, so it cannot anchor'
        if key == 'GMO2023-APPX-II':
            blockers += '; separate DESW URL recorded in ACQ-01-B4: ' + sched_txt(d, OTHER_SCHED['GMO2023'])
        if key == 'CIRC-PRA-ER':
            blockers += '; case_ids are cases whose provisions name MoD letters/circulars generally, not necessarily these circulars'
        if key in ('PRA1961', 'ER1982', 'ER2008'):
            blockers += '; DCLR-SC-2013-N08 and DCLR-SC-2015-N09 name "Pension Regulations and Entitlement Rules in force at discharge/then applicable" without an edition'
        if key == 'ER2023-HELD-INCOMPLETE':
            blockers = 'held copy is INCOMPLETE (GMO-2023 absent) and provenance undocumented; must not be treated as the complete publication (C5-CF-C5-03 OPEN)'
        rows.append(dict(pension_doc_key=key, document=name, c5_source_id=sid or '(none)', c5_holding_state=m.get('holding_state', ''), state=state,
                         sha256=m.get('sha256', ''), consequence_tier=tier, acquisition_route=acq, blockers=blockers.strip('; '),
                         kb_records_citing_by_code=len(cited), kb_record_ids_citing=ids(cited),
                         kb_records_sole_missing_source=len(sole), kb_record_ids_closed_if_acquired=ids(sole),
                         kb_records_text_mention=len(tm), kb_record_ids_text_mention=ids(tm, 40),
                         crosswalk_items=len(cx), crosswalk_status='; '.join('%s=%d' % kv for kv in sorted(cw_status.items())),
                         case_ids=ids(cases),
                         evidence=('SOURCE-LIBRARY-C5/registers/source_master_register.csv#' + sid if sid else 'PILOT-01/registers/source_code_resolution_v3.csv') +
                         '; codes: ' + ','.join(c for c, v in PENSION_CODES.items() if v == key)))
    # per-record matrix for M08 + any record citing V6 codes
    rec_rows = []
    allrec = sorted(set(m08) | set(rec_codes), key=natkey)
    for rid in allrec:
        need = sorted({PENSION_CODES[c] for c in rec_codes.get(rid, set())})
        miss = sorted(rec_missing.get(rid, set()))
        heldund = [x for x in need if x not in miss]
        tm = [k for k, s in text_recs.items() if rid in s]
        cx = [x for x in d.kbx if x['knowledge_base_record_id'] == rid]
        rec_rows.append(dict(record_id=rid, module=d.kb_by_id[rid]['module'], codes=';'.join(sorted(rec_codes.get(rid, set()))),
                             required_docs=';'.join(need), docs_not_held=';'.join(miss), docs_held_but_not_primary=';'.join(heldund),
                             closure_set=';'.join(miss) if miss else ('NONE (all cited pension sources held; provenance registration needed)' if need else 'NO PENSION CODE CITED'),
                             text_mentions=';'.join(tm),
                             crosswalk_status='; '.join('%s=%d' % kv for kv in sorted(collections.Counter(x['evidence_status'] for x in cx).items()))))
    summary = dict(m08=len(m08), coded=len(rec_codes), text=text_recs, doc_recs=doc_recs, cdeps=cdeps)
    return rows, rec_rows, summary


# ===================================================================== TASK 6
def task_regs(d):
    M = 'SOURCE-LIBRARY-C5/registers/source_master_register.csv#'
    A = 'SOURCE-LIBRARY-C5/discovery/A_candidates.csv#'
    R4 = 'C6-PREP/registers/c6_04_custodian_request_inventory.csv#'
    rows = []

    def add(item, cls, sid, req, cand, evid, held='NO', note='', authority='', marking=''):
        m = d.master.get(sid, {})
        rows.append(dict(inv_id='D-REG-%02d' % (len(rows) + 1), publication=item, classification=cls, c5_source_id=sid or '(none)',
                         c5_holding_state=m.get('holding_state', ''), held=held, sha256=m.get('sha256', '') if held != 'NO' else '',
                         access_marking=marking or m.get('access_marking', '') or 'NOT_OBSERVED_OR_NOT_CHECKED', authority_status=authority,
                         custodian_request_id=req, discovery_candidates=cand, evidence=evid, notes=note))

    add('Regulations for the Army, Revised Edition 1987, Vol I', 'OFFICIAL_BUT_UNVERIFIED', 'C5-SRC-P0-RA-1987', 'RA-1987-V1', 'C5A-001;C5A-002;C5A-006;C5D-004;C5D-006',
        M + 'C5-SRC-P0-RA-1987; ' + R4 + 'RA-1987-V1; ' + A + 'C5A-001',
        note='No official full-text host located; CDA-hosted copies labelled Vol-I (C5D-004) not examined (owner decision C5-ACQ-26); two-volume structure only from a 2014 secondary listing',
        authority='governing publication (MoD); edition currency NOT ESTABLISHED', marking='UNKNOWN (sibling RAF reprint reported FOUO)')
    add('Regulations for the Army, Revised Edition 1987, Vol II', 'OFFICIAL_BUT_UNVERIFIED', 'C5-SRC-P0-RA-1987', 'RA-1987-V2', 'C5D-005', R4 + 'RA-1987-V2',
        note='CDA-hosted copy labelled Vol-II not examined', authority='as Vol I', marking='UNKNOWN')
    add('RA 1987 amendment lists / correction slips and incorporation record', 'UNPUBLISHED', 'C5-SRC-P0-RA-1987', 'RA-1987-SLIPS', 'C5A-005',
        R4 + 'RA-1987-SLIPS; SOURCE-LIBRARY-C5/registers/amendment_register.csv#C5-AMD-RA1987-SLIPS; source_conflict_register.csv#C5-CF-C5-04',
        note='none located (NOT_FOUND); publication status unknown - classed UNPUBLISHED only in the sense that no public copy is evidenced', authority='amendment chain AMENDMENT_CHAIN_INCOMPLETE', marking='UNKNOWN')
    add('RA 1987 Chapter V (Reserve Forces) paras 201-220 - India Code extract', 'PUBLICLY_AVAILABLE', 'C5-SRC-P0-RA-1987-CH5-INDIACODE', '', '',
        M + 'C5-SRC-P0-RA-1987-CH5-INDIACODE; SOURCE-LIBRARY-C5/registers/source_copy_register.csv#C5-SRC-P0-RA-1987-CH5-INDIACODE~C1', held='YES (INCOMPLETE_EXTRACT, 5 pp.; provenance undocumented)',
        note='government-hosted extract only; cannot represent the full regulations', authority='official consolidation extract')
    add('Regulations for the Army 1962 (earlier DSR edition), with amendment slips', 'OFFICIAL_BUT_UNVERIFIED', 'C5-SRC-P0-RA-1962', 'RA-1962', 'C5A-007;C5A-008',
        M + 'C5-SRC-P0-RA-1962; ' + R4 + 'RA-1962; ' + A + 'C5A-008',
        note='existence evidenced only by citation in a 1987 Gazette; supersession by RA 1987 NOT evidenced by any held instrument (not assigned)', authority='historical edition; status NOT DETERMINED')
    add('"Regulations for the Army 2008" (edition claim in repo records)', 'OFFICIAL_BUT_UNVERIFIED', 'C5-SRC-P0-RA-2008-CLAIM', '', 'C5A-003', M + 'C5-SRC-P0-RA-2008-CLAIM',
        note='NOT_FOUND in searched sources; no such edition evidenced - treat as unverified claim')
    add('DSR vol 1 / vol 2 (Army) Scribd uploads', 'ACCESS_CONTROLLED', 'C5-SRC-P0-DSR-VOLS-SCRIBD', '', 'C5A-025', M + 'C5-SRC-P0-DSR-VOLS-SCRIBD; ' + A + 'C5A-025',
        note='DO_NOT_ACQUIRE: third-party upload; restricted marking suspected (sibling AF volume FOUO); never authoritative', authority='not an authority', marking='RESTRICTED_MARKING_SUSPECTED')
    add('Regulations for the Medical Services of the Armed Forces (RMSAF) 2010 (revised), with amendments', 'OFFICIAL_BUT_UNVERIFIED', 'C5-SRC-P1-RMSAF-2010', 'RMSAF-2010', 'C5A-017',
        M + 'C5-SRC-P1-RMSAF-2010; ' + R4 + 'RMSAF-2010', note='only a Scribd transcription seen (not acceptable, not authoritative); no official host located', marking='UNKNOWN')
    add('RMSAF 1983 edition', 'OFFICIAL_BUT_UNVERIFIED', 'C5-SRC-P1-RMSAF-2010', 'RMSAF-1983', 'C5A-018', R4 + 'RMSAF-1983; ' + A + 'C5A-018', note='NOT_FOUND; existence inferred from the 2010 supersession note only')
    add('Army Order 45/2001 (cited by KB ADM-014; discussed in Pooja Pal 2026)', 'ACCESS_CONTROLLED', 'C5-SRC-P0-ARMY-ORDERS-INSTRUCTIONS', 'AO-45-2001', 'C5C-030',
        R4 + 'AO-45-2001; ' + M + 'C5-SRC-P0-ARMY-ORDERS-INSTRUCTIONS',
        note='Army Orders are outside CLAUDE.md public scope; no public host (C5C-030 NOT_FOUND); request needs scope extension P-C6-04-SCOPE and A-C5-3', marking='UNKNOWN')
    add('Army Order 13/2006/PS (reported reference in the D&V handbook)', 'ACCESS_CONTROLLED', 'C5-SRC-P0-ARMY-ORDERS-INSTRUCTIONS', 'AO-13-2006-PS', 'DV-SOH-2014-R4',
        R4 + 'AO-13-2006-PS; C6-PREP/inputs/c6_04_discovery_candidates.csv#DV-SOH-2014-R4', note='UNVERIFIED_EXTRACTION_CANDIDATE: existence not confirmed', marking='UNKNOWN')
    add('Army Orders / Instructions cited by category (COI-002, COI-007, COI-018, COI-029, COI-033, COI-046, CM-040, HCE-030, HCE-031, HCE-033)', 'ACCESS_CONTROLLED',
        'C5-SRC-P0-ARMY-ORDERS-INSTRUCTIONS', 'AO-CATEGORY', 'C5C-030', R4 + 'AO-CATEGORY', note='owner must name the specific orders before any request')
    add("Staff Officers' Handbook: Processing of Statutory/Non-Statutory Complaints on D&V Matters (May 2014, apparent)", 'OFFICIAL_BUT_UNVERIFIED', '', 'DV-SOH-2014', 'DV-SOH-2014',
        R4 + 'DV-SOH-2014; C6-PREP/inputs/c6_04_discovery_candidates.csv#DV-SOH-2014',
        note='UNVERIFIED DISCOVERY LEAD. Scribd upload 733107547 not opened, not downloaded, NOT AUTHORITATIVE. Guidance, not governing authority. Reported references (AA ss.26, 27, 164; RA 1987 paras 364, 365, 368; AO 13/2006/PS) are unverified extraction candidates.',
        authority='guidance only', marking='UNKNOWN')
    add('D&V policy letters on statutory / non-statutory complaints (reported in the handbook)', 'UNPUBLISHED', '', '(none: owner scope decision first)', 'DV-SOH-2014-R5',
        'C6-PREP/inputs/c6_04_discovery_candidates.csv#DV-SOH-2014-R5', note='internal letters; outside CLAUDE.md public scope; inventory only after an authorised handbook copy is held')
    for sid, cand in [('C5-SRC-P2-RAI-1927', 'C5A-009'), ('C5-SRC-P2-RAI-1940-PT2', 'C5A-010'), ('C5-SRC-P2-RAI-C1930', 'C5A-011'), ('C5-SRC-P2-RAI-IOR-SET', 'C5A-012'),
                      ('C5-SRC-P2-ARMY-REGS-INDIA', 'C5A-013'), ('C5-SRC-P2-RELEASE-REGS-1945', 'C5A-014'), ('C5-SRC-P2-AI-IAO-1911-1933', 'C5A-015'), ('C5-SRC-P2-RMS-INDIA-1930', 'C5A-016')]:
        add(d.master[sid]['title'], 'HISTORICAL_SUPERSEDED', sid, '', cand, M + sid + '; ' + A + cand + ('; ' + SCHED + OTHER_SCHED['RAI-1927'][0] if sid == 'C5-SRC-P2-RAI-1927' else ''),
            note='C5 "historical layer"; the superseding instrument is not evidenced in the registers (class is a scope label, not a legal-status finding)' +
            ('; pinned archive.org candidate in ACQ-01-B3 (not configured): ' + sched_txt(d, OTHER_SCHED['RAI-1927']) if sid == 'C5-SRC-P2-RAI-1927' else ''))
    for sid, cand in [('C5-SRC-P2-RAF-1964', 'C5A-019'), ('C5-SRC-P2-RNAVY-PT1', 'C5A-020'), ('C5-SRC-P2-RNAVY-PT2', 'C5A-021'), ('C5-SRC-P2-RNAVY-PT3', 'C5A-022'),
                      ('C5-SRC-P2-INAS-1973', 'C5A-023'), ('C5-SRC-P2-RNAVY-AMDT-2022-2024', 'C5A-024')]:
        c = d.cand.get(cand, {})
        add(d.master[sid]['title'], 'PUBLICLY_AVAILABLE', sid, '', cand, M + sid + '; ' + A + cand,
            note='official host %s (HTTP %s); not held; cross-service comparator (P2)%s' % (c.get('host', ''), c.get('http_status', ''), '; FOUO marking reported by a search snippet - record the printed marking on receipt' if cand == 'C5A-019' else ''),
            marking=('REPORTED FOUO (search snippet)' if cand == 'C5A-019' else ''))
    add('Territorial Army Regulations 1948 (Revised Edition 1976)', 'PUBLICLY_AVAILABLE', 'C5-SRC-P1-TA-REGULATIONS', '', 'C5D-002', M + 'C5-SRC-P1-TA-REGULATIONS; SOURCE-LIBRARY-C5/discovery/D_candidates.csv#C5D-002',
        note='India Code-hosted file identified via search index only; India Code robots UNAVAILABLE at discovery; not held')
    return rows


# ===================================================================== TASK 7
CASE_HAND_MAP = {
    'V7-S07': 'DCLR-SC-1997-N07', 'V7-S09': 'DCLR-SC-2015-N06', 'V7-S11': 'DCLR-SC-2008-N10', 'V6-S17': 'DCLR-SC-2014-A08', 'V6-S19': 'DCLR-SC-2026-008',
    'SRC-JETHI': 'DCLR-SC-2013-N05', 'SRC-INDER': 'DCLR-SC-1997-N03', 'SRC-HUSSAIN': 'DCLR-SC-1997-N04', 'VISHAV': 'DCLR-SC-2016-010', 'RANDHIR': 'DCLR-SC-2019-006',
    'case:Kuldeep Yadav': 'DCLR-SC-2019-003', 'case:Vishav Priya Singh': 'DCLR-SC-2016-010', 'case:Randhir Singh': 'DCLR-SC-2019-006',
}

CASE_PROV_PATTERNS = {
    'AA1950': r'Army Act', 'AR1954': r'Army Rules?|Army Rule', 'AFT2007': r'AFT Act', 'NA1957': r'Navy Act', 'IEA1872': r'Evidence Act',
    'CRPC1973': r'CrPC|Criminal procedure', 'BSA2023': r'\bBSA\b', 'FIN2017': r'Finance Act 2017',
    'PRA': r'Pension Regulation', 'PR-AF': r'Air Force Pension', 'CIRC': r'MoD (?:disability|circular|letters)|Broad-banding', 'AFSPA': r'AFSPA',
    'CONST': r'Constitution',
}


def unmapped_key(r):
    b = r['basis']
    m = re.match(r'WS-D (code|statute|case):(.+?)\[', b)
    if not m:
        return ('OTHER', b[:60])
    kind, val = m.group(1), m.group(2)
    if kind == 'case':
        name = re.split(r'\s*(?:\(|¶|paras?\b|,)', val)[0].strip()
        return ('case', name)
    return (kind, val)


def task_gaps(d, pen_summary):
    rows = []
    kbx = d.kbx
    nonexact = [r for r in kbx if r['evidence_status'] != 'EXACT_ANCHOR' and r['relationship_type'] == 'CITES']
    assigned = collections.defaultdict(set)  # crosswalk row index -> gap ids

    idx = {id(r): i for i, r in enumerate(kbx)}

    def case_deps(pattern):
        return sorted({c['id'] for c in d.cases if re.search(pattern, ' '.join(c.get('provisions') or []))}, key=natkey)

    def add(gid, source, sid, gtype, basis, xrows, cases, tier, consequence, route, auth, upper=None, note=''):
        recs = {r['knowledge_base_record_id'] for r in xrows}
        for r in xrows:
            if r['evidence_status'] != 'EXACT_ANCHOR':
                assigned[idx[id(r)]].add(gid)
        rows.append(dict(gap_id=gid, missing_or_incomplete_source=source, c5_source_id=sid or '(none)', gap_type=gtype, dependency_basis=basis,
                         n_kb_records=len(recs), n_kb_items=len(xrows), kb_record_ids=ids(recs),
                         n_cases=len(cases), case_ids=ids(cases), upper_bound_kb_records=('' if upper is None else len(upper)),
                         consequence_tier=tier, legal_consequence=consequence, acquisition_route=route, authorisation_required=auth, note=note))

    src = lambda s: [r for r in kbx if r['source_id'] == s]
    aa = src('C5-SRC-P0-ARMY-ACT-1950-INDIACODE')
    aftx = src('C5-SRC-P0-AFT-ACT-2007-INDIACODE')
    bnssx = src('C5-SRC-P0-BNSS-2023-INDIACODE')
    bsax = src('C5-SRC-P0-BSA-2023-INDIACODE')
    bnsx = src('C5-SRC-P1-BNS-2023')
    arx = src('C5-SRC-P0-ARMY-RULES-1954')
    aa_recs = {r['knowledge_base_record_id'] for r in aa}
    aft_recs = {r['knowledge_base_record_id'] for r in aftx}
    ar_recs = {r['knowledge_base_record_id'] for r in arx}
    san_recs = {r['knowledge_base_record_id'] for r in bnssx + bsax + bnsx + src('C5-SRC-P0-SANHITA-COMMENCEMENT-2024')}

    A1 = 'A-C5-1 (download approval) + crawler-config PR stacked on #8'
    add('G-AA-ENACT', 'Army Act 1950 as enacted (Gazette Extraordinary No.306/1950)', 'C5-SRC-P0-ARMY-ACT-1950', 'ORIGINAL_ENACTMENT_NOT_HELD (only India Code compilation held)',
        'CROSSWALK_SOURCE C5-SRC-P0-ARMY-ACT-1950-INDIACODE (all PARTIAL)', aa, case_deps(CASE_PROV_PATTERNS['AA1950']), 'A',
        'every Army Act proposition stops at a consolidation; acquisition gives the as-enacted text only - current wording also needs the amendment chain (Acts 19/1955, 56/1974, 13/1975, 20/1983, 37/1992, ALO 1956, S.O. 3912(E)/2019)',
        'C5-ACQ-01 (pinned)', A1)
    add('G-AFT-ENACT', 'AFT Act 2007 as enacted (Gazette Extraordinary 28-12-2007)', 'C5-SRC-P0-AFT-ACT-2007', 'ORIGINAL_ENACTMENT_NOT_HELD (compilation only)',
        'CROSSWALK_SOURCE C5-SRC-P0-AFT-ACT-2007-INDIACODE', aftx, case_deps(CASE_PROV_PATTERNS['AFT2007']), 'A',
        'AFT jurisdiction/appeal propositions rest on a consolidation; amendments by Finance Act 2017, TRA 2021 and TRA 2026 also needed for current text', 'C5-ACQ-02 (pinned)', A1)
    add('G-BSA-ENACT', 'BSA 2023 as enacted (Gazette 25-12-2023)', 'C5-SRC-P0-BSA-2023', 'ORIGINAL_ENACTMENT_NOT_HELD (compilation only)',
        'CROSSWALK_SOURCE C5-SRC-P0-BSA-2023-INDIACODE', bsax, case_deps(CASE_PROV_PATTERNS['BSA2023']), 'A',
        'court-martial evidence propositions (AA s.133 interface, electronic records) rest on a consolidation', 'C5-ACQ-04 (pinned)', A1)
    add('G-BNSS-ENACT', 'BNSS 2023 as enacted (Gazette 25-12-2023)', 'C5-SRC-P0-BNSS-2023', 'ORIGINAL_ENACTMENT_NOT_HELD (compilation only)',
        'CROSSWALK_SOURCE C5-SRC-P0-BNSS-2023-INDIACODE', bnssx, [], 'A', 'civil-military jurisdiction / procedure propositions rest on a consolidation', 'C5-ACQ-03 (pinned)', A1)
    add('G-BNS-ENACT', 'BNS 2023 (any reliable text)', 'C5-SRC-P1-BNS-2023', 'NO_RELIABLE_COPY (derived text only)', 'CROSSWALK_SOURCE C5-SRC-P1-BNS-2023 (MISSING)',
        bnsx, [], 'A', 'offence-definition and IPC-repeal (s.358) propositions have no held text at all', 'C5-ACQ-20 (pinned)', A1)
    sanx = src('C5-SRC-P0-SANHITA-COMMENCEMENT-2024')
    add('G-SAN-COMM', 'BNS/BNSS/BSA commencement notifications (Gazette 24-02-2024)', 'C5-SRC-P0-SANHITA-COMMENCEMENT-2024', CNR,
        'CROSSWALK_SOURCE (direct) + UPPER_BOUND all BNS/BNSS/BSA-citing records', sanx, case_deps(r'BSA|CrPC|Evidence Act|Criminal procedure'), 'A',
        'IPC/CrPC/IEA to BNS/BNSS/BSA switch date and any section-specific exception (BNS s.106(2) per footnotes) are unevidenced by a primary document', 'C5-ACQ-05 (3 files pinned)', A1,
        upper=san_recs)
    aft_s1 = [r for r in aftx if '1' in secs_from_pid(r['provision_id'])]
    add('G-AFT-COMM', 'AFT Act commencement notification S.O. 14(E) of 13-06-2008', '', CNR + ' (not registered for acquisition)',
        'SECTION_OVERLAP s.1 (direct) + UPPER_BOUND all AFT-citing records', aft_s1, [], 'A', 'start date of AFT jurisdiction (and transfer of pending cases) rests on a compilation footnote',
        'not registered; discovery required', 'owner approval of discovery + A-C5-1 for any download', upper=aft_recs)
    aft_9a = [r for r in aftx if '9A' in secs_from_pid(r['provision_id'])]
    add('G-TRA2026-COMM', 'TRA 2026 commencement notification(s) under s.1(2)', '', CNR + ' (not registered)', 'SECTION_OVERLAP AFT s.9A (direct)', aft_9a, [], 'B',
        'date from which the substituted AFT s.9A (and the TRA 2021 repeal) operates; no KB record cites s.9A', 'not registered; discovery required', 'owner approval of discovery')
    add('G-TRA2021', 'Tribunals Reforms Act 2021 (33 of 2021)', '', 'AMENDMENT_INSTRUMENT_NOT_HELD; provisions affected unknown', 'UPPER_BOUND all AFT-citing records (no direct dependency evidenced)',
        [], [], 'B', 'which AFT provisions TRA 2021 changed (and with what effect after its repeal by TRA 2026 s.24) is unknown from held evidence', 'not registered; discovery required', 'owner approval of discovery',
        upper=aft_recs)
    add('G-FIN2017', 'Finance Act 2017 (7 of 2017) s.181 (Part XIV tribunals provisions)', '', 'AMENDMENT_INSTRUMENT_NOT_HELD', 'SECTION_OVERLAP AFT s.9A + CASE_PROVISIONS', aft_9a,
        case_deps(CASE_PROV_PATTERNS['FIN2017']), 'B', 'history of AFT s.9A between 2017 and 2026', 'not registered; discovery required', 'owner approval of discovery')
    aa_s1 = [r for r in aa if '1' in secs_from_pid(r['provision_id'])]
    add('G-AA-COMM', 'Army Act commencement notification S.R.O. 120 of 22-07-1950', '', CNR + ' (not registered)', 'SECTION_OVERLAP s.1 (direct) + UPPER_BOUND all Army Act-citing records',
        aa_s1, [], 'B', 'commencement of the Act (historical; low practical risk but unevidenced)', 'probable candidate ' + sched_txt(d, ['ACQ03-019']), 'A-C5-1 (PR #23 stack)', upper=aa_recs)
    # Army Act amending instruments by section overlap (register rows for the same instrument are merged)
    aa_groups = collections.OrderedDict()
    for a in d.amend:
        if a['publication_source_id'] != 'C5-SRC-P0-ARMY-ACT-1950' or a['origin_id'] in ('AA-00', 'AA-03', 'AA-09', 'AA-10', 'AA-11', 'AA-12', 'AA-C3-04', 'AA-C3-05'):
            continue
        aa_groups.setdefault(a['notification_number'], []).append(a)
    merged = []
    for num, grp in aa_groups.items():
        a = dict(grp[0])
        if len(grp) > 1:
            a['origin_id'] = '+'.join(x['origin_id'] for x in grp)
            a['affected_provisions'] = ' ; '.join(x['affected_provisions'] for x in grp)
        merged.append(a)
    for a in merged:
        held = bool(a['sha256'])
        if held and a['origin_id'].startswith('AA-08'):
            continue  # Act 37/1992 is held with a documented primary copy
        secs = secs_from_text(a['affected_provisions'], 's')
        throughout = 'throughout' in a['affected_provisions'].lower()
        xr = [r for r in aa if secs & secs_from_pid(r['provision_id'])]
        gt = 'AMENDMENT_INSTRUMENT_NOT_HELD' if not held else ('INCOMPLETE_EXTRACT (Schedule absent)' if a['origin_id'] == 'AA-01' else 'HELD_PROVENANCE_UNDOCUMENTED')
        held_sid = next((c['source_id'] for c in d.copies if c['sha256'] == a['sha256']), '') if held else ''
        add('G-AA-' + a['origin_id'], 'Army Act amending instrument: ' + a['notification_number'], 'C5-SRC-P0-AA-AMD-OTHER' if not held else held_sid, gt,
            'SECTION_OVERLAP (%s)%s' % (', '.join('s.' + s for s in sorted(secs, key=natkey)) or 'none parsed', '; plus "throughout" substitution - UPPER_BOUND all Army Act records' if throughout else ''),
            xr, [], 'A' if not held else 'B', 'wording of the affected sections after %s cannot be traced to the instrument' % a['notification_number'],
            (sched_txt(d, sum((AA_SCHED.get(o, []) for o in a['origin_id'].split('+')), [])) or 'not located') if not held else ('provenance registration (no download); Gazette candidate ' + sched_txt(d, AA_SCHED.get(a['origin_id'], [])) if AA_SCHED.get(a['origin_id']) else 'provenance registration (no download)'),
            'A-C5-1' if not held else 'owner decision on provenance addendum',
            upper=aa_recs if throughout or a['origin_id'] == 'AA-13' else None)
    # Army Rules
    post = 'G-AR-POST2022'
    add(post, 'Army Rules amendments after 06-06-2022 (10 candidate S.R.O.s + AR-036 unsearched)', 'C5-SRC-P0-AR-AMD-POST-2022', 'AMENDMENT_CHAIN_OPEN', 'UPPER_BOUND all Army Rules-citing records (provisions unknown)',
        [], case_deps(CASE_PROV_PATTERNS['AR1954']), 'A', 'any rule, including the 42 exact anchors, may have been amended after 2022; exact anchors are to the as-notified 1954 text only',
        'C5-ACQ-06 (10 pinned)', A1, upper=ar_recs)
    for oid in ('AR-030', 'AR-001'):
        a = next(x for x in d.amend if x['origin_id'] == oid)
        rn = secs_from_text(a['affected_provisions'], 'r')
        xr = [r for r in arx if rn & secs_from_pid(r['provision_id'])]
        add('G-' + oid, 'Army Rules amending instrument not found: %s (%s)' % (a['notification_number'], a['notification_date']), 'C5-SRC-P0-ARMY-RULES-1954', 'AMENDMENT_INSTRUMENT_NOT_LOCATED',
            'SECTION_OVERLAP (%s) + UPPER_BOUND all Army Rules records' % (', '.join('r.' + x for x in sorted(rn)) or 'unknown provisions'), xr, [], 'A',
            'unknown change to the Army Rules (%s)' % a['affected_provisions'], sched_txt(d, AR_SCHED_FIXED.get(oid, [])) or 'discovery retry', 'custodian route or Indian-network egazette run (owner decision)', upper=ar_recs)
    for a in d.amend:
        if a['publication_source_id'] != 'C5-SRC-P0-ARMY-RULES-1954':
            continue
        if not (a['evidence_level'].startswith('HINT_ONLY') or a['evidence_level'].startswith('TEXT_LAYER_ONLY')):
            continue
        rn = secs_from_text(a['affected_provisions'], 'r')
        if not rn:
            continue
        xr = [r for r in arx if rn & secs_from_pid(r['provision_id'])]
        add('G-' + a['origin_id'], 'Army Rules instrument %s (%s; %s)' % (a['notification_number'], a['notification_date'], a['evidence_level']), 'C5-SRC-P0-ARMY-RULES-1954',
            'TEXT_LAYER_ONLY' if a['evidence_level'].startswith('TEXT') else 'HINT_ONLY', 'SECTION_OVERLAP (%s)' % ', '.join('r.' + x for x in sorted(rn, key=natkey)), xr, [], 'A',
            'possible change to %s not verified on a page image' % a['affected_provisions'], ('%s (%s)' % (sched_txt(d, ar_sched(d, a)[0]), ar_sched(d, a)[1])) if ar_sched(d, a)[0] else 'no candidate recorded', 'A-C5-1 (PR #23 stack)')
    undoc = [a for a in d.amend if a['publication_source_id'] == 'C5-SRC-P0-ARMY-RULES-1954' and a['sha256'] and
             any(c['sha256'] == a['sha256'] and c['copy_evidence_class'] != 'DOCUMENTED_PRIMARY_COPY' for c in d.copies)]
    rn = set()
    for a in undoc:
        rn |= secs_from_text(a['affected_provisions'], 'r')
    xr = [r for r in arx if rn & secs_from_pid(r['provision_id'])]
    add('G-AR-UNDOC', '%d held Army Rules amendment Gazettes without documented provenance (%s)' % (len(undoc), ', '.join(a['origin_id'] for a in undoc)), '', 'HELD_PROVENANCE_UNDOCUMENTED',
        'SECTION_OVERLAP (rules amended by these instruments)', xr, [], 'B',
        'amended rules cannot reach EXACT_ANCHOR; provenance registration is necessary but NOT sufficient under the C5 rule (amended rules also need a complete chain)', 'provenance registration (no download)',
        'owner decision on authentication addendum (AUTH-LEDGER tranche 1)')
    # AFT procedure rules: crosswalk + unmapped statutes
    apr = src('C5-SRC-P1-AFT-PROC-RULES') + [r for r in kbx if r['source_id'] == 'UNMAPPED' and re.search(r'statute:(Procedure Rules?|Practice Rules|2011 Rule)\[', r['basis'])] + \
        [r for r in kbx if r['source_id'] == 'UNMAPPED' and re.search(r'code:(V7-S04|V7-S14)\[', r['basis'])]
    add('G-AFT-PR', 'AFT (Procedure) Rules 2008, Amendment Rules 2011, Practice Rules 2009', 'C5-SRC-P1-AFT-PROC-RULES', 'NOT_HELD (derived OCR of the 2008 Rules only)',
        'CROSSWALK_SOURCE + UNMAPPED statute/code rows naming the Procedure/Practice Rules', apr, [], 'A', 'AFT filing, limitation, review and procedure propositions have no held text',
        'C5 says DISCOVERY_REQUIRED, but pinned archive.org candidates exist: ' + sched_txt(d, OTHER_SCHED['AFT-PR'][:3]), 'A-C5-1 (PR #23 stack); C5 register reconciliation')
    add('G-CCCM', 'Criminal Courts and Court-martial (Adjustment of Jurisdiction) Rules 1978 and S.O. 4010/1986', 'C5-SRC-P1-CCCM-ADJ-RULES', 'NOT_HELD',
        'CROSSWALK_SOURCE (MISSING since RV-01)', src('C5-SRC-P1-CCCM-ADJ-RULES'), [], 'A', 'choice of forum between criminal court and court-martial (AA ss.125-126) rests on unheld rules',
        'C5 says DISCOVERY_REQUIRED, but both instruments are pinned in ACQ-01-B2: ' + sched_txt(d, OTHER_SCHED['CCCM']), 'A-C5-1 (PR #8 config); C5 register reconciliation')
    add('G-RA1987', 'Regulations for the Army 1987 (complete, with correction slips)', 'C5-SRC-P0-RA-1987', 'NOT_HELD (5-page India Code extract only)', 'CROSSWALK_SOURCE',
        src('C5-SRC-P0-RA-1987'), [], 'B', 'regulatory propositions (e.g. complaints, discipline administration) unanchored', 'custodian route (C6-04 RA-1987-V1/V2/SLIPS)', 'scope extension P-C6-04-SCOPE + A-C5-3')
    ao = src('C5-SRC-P0-ARMY-ORDERS-INSTRUCTIONS') + [r for r in kbx if r['source_id'] == 'UNMAPPED' and 'AO 45/2001' in r['basis']]
    add('G-AO', 'Army Orders / Instructions (AO 45/2001 named; others by category)', 'C5-SRC-P0-ARMY-ORDERS-INSTRUCTIONS', 'NOT_HELD (outside public scope)', 'CROSSWALK_SOURCE + UNMAPPED AO 45/2001 rows',
        ao, [], 'C', 'administrative-instruction propositions unanchored; owner must name the orders', 'custodian route (C6-04 AO-45-2001, AO-CATEGORY)', 'scope extension P-C6-04-SCOPE + A-C5-3')
    add('G-ISO', 'ISO (Command, Control and Discipline) Act 2023 and Rules 2025', 'C5-SRC-P1-ISO-ACT-RULES', 'NOT_HELD', 'CROSSWALK_SOURCE', src('C5-SRC-P1-ISO-ACT-RULES'), [], 'A',
        'inter-service command and discipline propositions unanchored', 'DISCOVERY_REQUIRED', 'owner approval of discovery')
    # pension
    for gid, sid, codes, title, tier, cons, route, auth in [
        ('G-PRA-PT1', 'C5-SRC-P1-PRA-2008-PT1', ['V6-S01'], 'Pension Regulations for the Army 2008 Part I', 'B', 'service/invalid/family pension entitlement propositions', 'C5-ACQ-07 (DESW)', 'A-C5-2 + DESW allow-list PR + readable robots (403 now)'),
        ('G-PRA-PT2', 'C5-SRC-P1-PRA-2008-PT2', ['V6-S02'], 'Pension Regulations for the Army 2008 Part II', 'B', 'pension procedure propositions', 'C5-ACQ-08 (DESW)', 'A-C5-2 + DESW allow-list PR + readable robots (403 now)'),
        ('G-ER2023', 'C5-SRC-P1-ER-GMO-2023', ['V6-S04'], 'Entitlement Rules 2023 (Appendix-I) complete publication (held copy 29f6fa2c is incomplete and non-primary)', 'B', 'attributability/aggravation entitlement propositions for post-21-09-2023 claims', 'C5-ACQ-09 (DESW; only URL in draft PR #9)', 'A-C5-2 + robots'),
        ('G-GMO2023', 'C5-SRC-P1-ER-GMO-2023', ['V6-S07'], 'Guide to Medical Officers (Military Pensions) 2023 (Appendix-II) - ABSENT from the held copy', 'B', 'medical-assessment propositions; code V6-S07 is UNMAPPED in the C5 crosswalk although its identity (GMO 2023) is resolved in v3', 'C5-ACQ-09 (DESW)', 'A-C5-2 + robots'),
        ('G-PEN-CIRC', '', ['V6-S10', 'V6-S11'], 'Pension letters: broad-banding 27-12-2023 (V6-S11) and OROP corrigendum 13-10-2025 (V6-S10)', 'C', 'rate/broad-banding propositions', 'not registered (UNMAPPED codes); DESW', 'A-C5-2 + allow-list + robots'),
        ('G-DESW-WEB', 'C5-SRC-P1-DESW-FAQ-PIB', ['V6-S05', 'V6-S06', 'V6-S08', 'V6-S09', 'V6-S12', 'V6-S13', 'V6-S22'], 'DESW/CGDA/PIB web guidance (secondary; not governing authority)', 'C', 'guidance only - should be replaced by the governing instrument, not acquired as authority', 'DISCOVERY_REQUIRED', 'n/a (secondary)')]:
        xr = [r for r in kbx if (sid and r['source_id'] == sid and r['basis'] and any(c in r['basis'] or c in r['provision_id'] for c in codes))]
        xr += [r for r in kbx if r['source_id'] == 'UNMAPPED' and any(('code:%s[' % c) in r['basis'] for c in codes)]
        if gid in ('G-PRA-PT1', 'G-PRA-PT2', 'G-ER2023') and not xr:
            xr = src(sid)
        if gid == 'G-DESW-WEB':
            xr = src(sid) + [r for r in kbx if r['source_id'] == 'UNMAPPED' and any(('code:%s[' % c) in r['basis'] for c in codes)]
        add(gid, title, sid, 'NOT_HELD' if gid != 'G-ER2023' else 'HELD_COPY_INCOMPLETE_AND_NON_PRIMARY', 'CROSSWALK_SOURCE / UNMAPPED code rows (%s)' % ','.join(codes), xr, [], tier, cons, route, auth)
    pen_text = pen_summary['text']
    cdeps = pen_summary['cdeps']
    for gid, key, title, sid in [('G-ER1982', 'ER1982', 'Entitlement Rules 1982', 'C5-SRC-P1-ER-1982'), ('G-ER2008', 'ER2008', 'Entitlement Rules 2008', 'C5-SRC-P1-ER-2008'),
                                 ('G-PRA1961', 'PRA1961', 'Pension Regulations for the Army 1961', 'C5-SRC-P1-PRA-1961'), ('G-GMO-0208', 'GMO-ANY', 'Guide to Medical Officers 2002/2008 (historical editions)', 'C5-SRC-P1-GMO-2002-2008')]:
        recs = pen_text.get(key, set())
        cs = set(cdeps.get('ER-AT-DISCHARGE (edition not stated)', set())) if key in ('ER1982', 'ER2008') else (cdeps.get('PRA1961', set()) if key == 'PRA1961' else set())
        rows.append(dict(gap_id=gid, missing_or_incomplete_source=title, c5_source_id=sid, gap_type='NOT_HELD (NOT_FOUND or not acquired)',
                         dependency_basis='TEXT_MENTION (keyword in record body/title/references; not a coded citation - indicative)', n_kb_records=len(recs), n_kb_items=0,
                         kb_record_ids=ids(recs), n_cases=len(cs), case_ids=ids(cs), upper_bound_kb_records='', consequence_tier='B',
                         legal_consequence='historical-regime entitlement questions (claims under earlier rules) cannot be anchored to the rules in force at the relevant date',
                         acquisition_route=d.master.get(sid, {}).get('acquisition_state', ''), authorisation_required='A-C5-2 (DESW) or custodian route', note='text-mention dependency is indicative only'))
    # historical codes and other statutes
    for gid, key, title, sid, extra_pat in [('G-IEA', 'IEA1872', 'Indian Evidence Act 1872 (historical version)', 'C5-SRC-P1-IPC-CRPC-IEA', r'code:V9-S08\['),
                                            ('G-CRPC', 'CRPC1973', 'Code of Criminal Procedure 1973 (historical version)', 'C5-SRC-P1-IPC-CRPC-IEA', None),
                                            ('G-IPC', 'IPC1860', 'Indian Penal Code 1860 (historical version)', 'C5-SRC-P1-IPC-CRPC-IEA', None),
                                            ('G-NAVY', 'NA1957', 'Navy Act 1957', '', None), ('G-AFA', 'AFA1950', 'Air Force Act 1950', '', None),
                                            ('G-DPP', 'DPP1950', 'Army and Air Force (Disposal of Private Property) Act 1950 / Amendment Act 2000', 'C5-SRC-P1-DPP-ACT-1950', None)]:
        xr = [r for r in kbx if extra_pat and r['source_id'] == 'UNMAPPED' and re.search(extra_pat, r['basis'])]
        tm = kb_text_mentions(d, INSTRUMENT_TEXT_PATTERNS[key])
        cpat = {'IEA1872': CASE_PROV_PATTERNS['IEA1872'], 'CRPC1973': CASE_PROV_PATTERNS['CRPC1973'], 'NA1957': CASE_PROV_PATTERNS['NA1957']}.get(key)
        cs = case_deps(cpat) if cpat else []
        add(gid, title, sid, 'NO_RELIABLE_COPY (derived text only or nothing)' if key != 'DPP1950' else 'NOT_HELD (2 items unpinned)',
            'UNMAPPED code rows (direct) + TEXT_MENTION records as upper bound', xr, cs, 'A' if key in ('IEA1872', 'CRPC1973', 'IPC1860') else 'B',
            'pre-01-07-2024 offences/proceedings and cross-service comparisons need the historical text in force at the relevant date', d.master.get(sid, {}).get('acquisition_state', 'not registered'),
            'owner approval of discovery' + (' + P-C7-02-META decision' if key == 'DPP1950' else ''), upper=set(tm))
    # judgments: held-undocumented SC copies
    for sid in sorted(d.master):
        m = d.master[sid]
        if not sid.startswith('C5-SRC-J-') or m['holding_state'] not in ('HELD_OFFICIAL_COURT_COPY_PROVENANCE_UNDOCUMENTED', 'HELD_AUTHENTICATION_PENDING'):
            continue
        cs = sorted({r['case_id'] for r in d.csx if r['source_id'] == sid}, key=natkey)
        add('G-J-' + sid.replace('C5-SRC-J-', ''), m['title'], sid, m['holding_state'], 'CROSSWALK_SOURCE (KB items PARTIAL) + case record', src(sid), cs, 'B',
            'binding SC authority held but cannot anchor until copy provenance is registered (no download needed); provenance never settles subsequent treatment (R-T2-7)',
            'provenance registration (AUTH-LEDGER tranche 2)', 'owner decision P-D3 / tranche 2')
    # judgments: missing (UNMAPPED case/code rows), grouped
    groups = collections.defaultdict(list)
    for r in kbx:
        if r['source_id'] != 'UNMAPPED':
            continue
        kind, val = unmapped_key(r)
        if kind == 'code':
            v3 = d.v3.get(val, {})
            rid = v3.get('resolved_identity', '')
            if re.search(r'\bv\.?\s|Union of India|judgment', rid) and not re.search(r'Act|Rules|Regulations|portal|Constitution', rid.split(',')[0]):
                cid = CASE_HAND_MAP.get(val)
                groups[('JUDGMENT', cid or val, rid.split(';')[0][:110])].append(r)
            else:
                groups[('CODE', val, rid[:90] or v3.get('resolution_class', 'UNKNOWN'))].append(r)
        elif kind == 'case':
            cid = CASE_HAND_MAP.get('case:' + val)
            groups[('JUDGMENT', cid or ('case:' + val), val)].append(r)
        elif kind == 'statute':
            if re.search(r'Procedure Rules?|Practice Rules|2011 Rule', val):
                continue
            groups[('STATUTE', val, val)].append(r)
        else:
            groups[('OTHER', val, val)].append(r)
    case_titles = {c['id']: c['title'] for c in d.cases}
    for (kind, key, label), xr in sorted(groups.items(), key=lambda kv: (-len({r['knowledge_base_record_id'] for r in kv[1]}), kv[0])):
        if kind == 'CODE' and key in ('V6-S04', 'V6-S05', 'V6-S06', 'V6-S07', 'V6-S08', 'V6-S09', 'V6-S10', 'V6-S11', 'V6-S12', 'V6-S13', 'V6-S22', 'V7-S04', 'V7-S14', 'V9-S08'):
            continue
        cid = key if key.startswith('DCLR-') else CASE_HAND_MAP.get(key)
        cs = [cid] if cid else []
        if kind == 'JUDGMENT':
            add('G-JM-' + re.sub(r'[^A-Za-z0-9]+', '-', key)[:40].strip('-'), 'Judgment not held: %s%s' % (label, (' [case record %s: %s]' % (cid, case_titles.get(cid, ''))) if cid else ''), '',
                'NOT_HELD (citation not mapped to a C5 source)', 'UNMAPPED crosswalk rows (%s)' % ', '.join(sorted({unmapped_key(x)[1] for x in xr})), xr, cs, 'B', 'case-law proposition unanchored; official copy to be located (no commercial databases)',
                'locate official court copy', 'owner approval of discovery / download')
        else:
            v3 = d.v3.get(key, {})
            add('G-UM-' + re.sub(r'[^A-Za-z0-9]+', '-', key)[:40].strip('-'), '%s source not mapped: %s (%s)' % (kind.title(), key, label), '', 'UNMAPPED (%s)' % (v3.get('resolution_class') or kind),
                'UNMAPPED crosswalk rows', xr, [], 'C' if kind in ('CODE', 'OTHER') else 'B', 'citation identity or holding unresolved', 'identity resolution first', 'n/a')
    covered = {r['case_id'] for r in rows for r in []}
    # case-only rows for missing case judgments not linked above
    linked = set()
    for g in rows:
        for c in g['case_ids'].split(';'):
            if c:
                linked.add(c)
    for r in d.csx:
        if r['evidence_status'] == 'MISSING_EVIDENCE':
            cid = r['case_id']
            gid = 'G-JC-' + cid
            if any(g['gap_id'] == gid for g in rows):
                continue
            if any(cid in g['case_ids'].split(';') and g['gap_id'].startswith('G-JM-') for g in rows):
                continue
            add(gid, 'Judgment not held for case record %s: %s' % (cid, case_titles.get(cid, '')), '', 'NOT_HELD (no official copy indexed)', 'case record own source (crosswalk case row MISSING)',
                [], [cid], 'B', 'the case record has no held official copy', 'locate official court copy', 'owner approval of discovery / download')
    # Army Rules chain completeness (C5 EXACT_ANCHOR rule excludes amended / reserved rules)
    chainx = [r for r in arx if r['evidence_status'] == 'PARTIAL_MATCH' and 'recorded amendment or reserved conflict' in r['basis']]
    reserved_rules = {'23', '177', '182', '192', '193', '194'}
    resx = {r['knowledge_base_record_id'] for r in chainx if reserved_rules & secs_from_pid(r['provision_id'])}
    add('G-AR-CHAIN', 'Complete, verified Army Rules amendment chain for rules with a recorded amendment or reserved conflict', 'C5-SRC-P0-ARMY-RULES-1954',
        'AMENDMENT_CHAIN_INCOMPLETE (C5 rule: amended or reserved rules cannot anchor exactly)', 'CROSSWALK_SOURCE rows whose basis is "recorded amendment or reserved conflict"', chainx,
        case_deps(CASE_PROV_PATTERNS['AR1954']), 'A',
        'current wording of amended rules cannot be stated; %d of these records cite a rule in a reserved state (r.23(3) CONFLICTING, r.182 OPEN, r.193 OPEN, r.194 PROPOSAL, r.192/r.177 CONFLICTING), which also needs legal review' % len(resx),
        'C5-ACQ-06 post-2022 S.R.O.s; AR-001/AR-030 discovery; image checks of AR-002..005, AR-032; 13 hints; provenance of 21 undocumented copies; legal review of reserved states',
        'A-C5-1 + discovery approval + adviser review (no determination here)')
    for gid, label, pat in [('G-REC-NOLOC', 'Record-side: citation has no provision locator (source identified and held)', 'no provision locator'),
                            ('G-REC-INFERRED', 'Record-side: citation identity only inferred (co-citation or short case name)', 'inferred identity')]:
        xr = [r for r in kbx if r['evidence_status'] == 'PARTIAL_MATCH' and pat in r['basis']]
        rows.append(dict(gap_id=gid, missing_or_incomplete_source=label, c5_source_id='(various)', gap_type='RECORD_SIDE (not an acquisition gap)', dependency_basis='crosswalk basis "%s"' % pat,
                         n_kb_records=len({r['knowledge_base_record_id'] for r in xr}), n_kb_items=len(xr), kb_record_ids=ids({r['knowledge_base_record_id'] for r in xr}),
                         n_cases=0, case_ids='', upper_bound_kb_records='', consequence_tier='C', legal_consequence='no acquisition fixes these; the record needs a locator / confirmed identity',
                         acquisition_route='n/a (record correction proposal)', authorisation_required='n/a', note='sources: ' + ', '.join('%s=%d' % kv for kv in sorted(collections.Counter(r['source_id'] for r in xr).items()))))
        for r in xr:
            assigned[idx[id(r)]].add(gid)
    # NO_CITATION placeholder note row
    nc = [r for r in kbx if r['relationship_type'] == 'NO_CITATION']
    rows.append(dict(gap_id='G-NOCIT', missing_or_incomplete_source='(no source: record cites nothing)', c5_source_id='NONE', gap_type='NO_CITATION', dependency_basis='crosswalk NO_CITATION rows',
                     n_kb_records=len(nc), n_kb_items=0, kb_record_ids=ids({r['knowledge_base_record_id'] for r in nc}), n_cases=0, case_ids='', upper_bound_kb_records='',
                     consequence_tier='C', legal_consequence='no acquisition can anchor these records; they need citations first', acquisition_route='n/a', authorisation_required='n/a', note='not a source gap'))
    # ranking
    tier_rank = {'A': 0, 'B': 1, 'C': 2}
    side = [g for g in rows if g['gap_id'] in ('G-NOCIT', 'G-REC-NOLOC', 'G-REC-INFERRED')]
    acq = [g for g in rows if g not in side]
    acq.sort(key=lambda g: (-int(g['n_kb_records']), tier_rank[g['consequence_tier']], -(g['upper_bound_kb_records'] or 0), -int(g['n_cases']), g['gap_id']))
    for i, g in enumerate(acq, 1):
        g['rank'] = i
    pot = sorted(acq, key=lambda g: (-max(int(g['n_kb_records']), int(g['upper_bound_kb_records'] or 0)), tier_rank[g['consequence_tier']], -int(g['n_kb_records']), g['gap_id']))
    for i, g in enumerate(pot, 1):
        g['rank_potential'] = i
        g['potentially_affected_kb_records'] = max(int(g['n_kb_records']), int(g['upper_bound_kb_records'] or 0))
    for g in side:
        g['rank'] = 'n/a (record-side)'
        g['rank_potential'] = 'n/a'
        g['potentially_affected_kb_records'] = g['n_kb_records']
    rows = acq + side
    unassigned = [kbx[i] for i in range(len(kbx)) if kbx[i]['relationship_type'] == 'CITES' and kbx[i]['evidence_status'] != 'EXACT_ANCHOR' and i not in assigned]
    return rows, nonexact, unassigned


# ===================================================================== MARKDOWN
def md_baseline(rows):
    out = ['# C8-D Task 1: baseline recompute of the KB citation figures', '',
           'Recomputed offline from committed files only (`tools/build_c8_d.py`). Every figure names the file and column it comes from.', '',
           md_table(['metric', 'reported', 'recomputed', 'result', 'derivation', 'note'],
                    [[r['metric'], r['reported_value'], r['recomputed_value'], r['result'], r['derivation'], r['note']] for r in rows]), '',
           '## Difference found', '',
           '- **1,060 is not a citation-item count.** It is the number of KB rows in `SOURCE-LIBRARY-C5/registers/corpus_crosswalk.csv`, which includes one `NO_CITATION` placeholder row for each of the 77 records that cite nothing. The number of parsed KB citation items is **983** (CITES rows; equal to the sum of `WS-D-QUALITY/canonical_coverage.csv#n_items`, and to the "983 total" already stated in `WS-D-QUALITY/canonical_coverage.md`).',
           '- Consequently the reported **366 MISSING items** contain 77 placeholders; genuine missing citation items are **289**. The exact-anchor share is 42/983 (4.3%), not 42/1,060 (4.0%).',
           '- **618 records with no exact anchor** reproduces, but 77 of them cite nothing at all; 541 records have at least one citation item and no exact anchor.',
           '- All other figures (42, 652, 658, 53, 10/30, 6/7/40) reproduce exactly. KB and case-file hashes equal the frozen C5 baseline manifest.', '',
           'No register was changed. The correction is a labelling one: future reports should say "1,060 crosswalk rows (983 citation items + 77 no-citation placeholders)".']
    return '\n'.join(out) + '\n'


def md_matrix(rows, dep):
    out = ['# C8-D Task 2: priority statutory instrument completeness matrix', '',
           'Source: `statutory_source_matrix.csv` (%d rows). Categories are kept apart: **ORIGINAL_ENACTMENT** (Gazette/notified text), **OFFICIAL_CONSOLIDATION** (India Code compilation or government text rendering), **AUTHORITATIVE_AMENDMENT** (amending instrument as published), **NOTIFICATION** (commencement / declarations), **SECONDARY_COMPILATION** (manuals, correspondence tables, parliamentary records), **INCOMPLETE_EXTRACT**, **NO_RELIABLE_COPY** (including derived text with no source binary). A consolidation is never treated as the enactment, and no current text is reconstructed from an old enactment plus an incomplete amendment list.' % len(rows), '',
           'Commencement: where an Act or Rules commence by a separate notification that is not held, the row carries **%s**. Compilation footnotes naming a date are recorded as such and are not treated as evidence of commencement.' % CNR, '']
    hdr = ['instrument', 'original enactment held', 'consolidation held', 'commencement notification held', 'amending instrument rows (held / not held or not located)', 'KB items (crosswalk)', 'KB records (crosswalk)', 'KB records (text mention)']
    tab = []
    for key, name in INSTRUMENT_NAMES.items():
        rs = [r for r in rows if r['instrument_key'] == key]
        if not rs:
            continue
        oe = [r for r in rs if r['holding_category'] == 'ORIGINAL_ENACTMENT' and 'historical layer' not in r['item']]
        co = [r for r in rs if r['holding_category'] == 'OFFICIAL_CONSOLIDATION' and r['c5_source_id'].endswith('-INDIACODE')]
        nt = [r for r in rs if r['holding_category'] == 'NOTIFICATION' and 'ommencement' in r['item']]
        AMF = ('AMENDMENT_INSTRUMENT_NOT_HELD', 'AMENDMENT_INSTRUMENT_NOT_LOCATED', 'AMENDMENT_CHAIN_OPEN', 'TEXT_LAYER_ONLY', 'HINT_ONLY')
        am_held = [r for r in rs if r['holding_category'] in ('AUTHORITATIVE_AMENDMENT', 'INCOMPLETE_EXTRACT') and r['held'] == 'YES' and 'trailer' not in r['item']]
        am_not = [r for r in rs if (r['holding_category'] == 'AUTHORITATIVE_AMENDMENT' and r['held'] != 'YES') or any(f in r['gap_flags'] for f in AMF)]
        f = lambda xs: ('YES (%s)' % ', '.join(short(x['sha256'], 8) + ('' if x['provenance_class'] == 'DOCUMENTED_PRIMARY_COPY' else '*') for x in xs if x['held'] == 'YES')) if any(x['held'] == 'YES' for x in xs) else 'NO'
        am = am_held
        amn = am_not
        dd = dep[key]
        tab.append([name, f(oe), f(co) if co else ('derived text only' if any(r['held'] == 'DERIVED_TEXT_ONLY' for r in rs) else 'NO'), f(nt) if nt else 'n/a (none recorded)',
                    '%d / %d' % (len(am), len(amn)), dd['items'], dd['records'], dd['text']])
    out += [md_table(hdr, tab), '', '`*` = held copy whose retrieval provenance is undocumented (copy_evidence_class PROVENANCE_UNDOCUMENTED_COPY); such copies cannot anchor exactly.', '']
    out += ['## Key gaps per instrument', '']
    for key, name in INSTRUMENT_NAMES.items():
        rs = [r for r in rows if r['instrument_key'] == key and r['gap_flags']]
        if not rs:
            continue
        out.append('**%s**' % name)
        for r in rs:
            if r['held'] == 'YES' and r['provenance_class'] == 'DOCUMENTED_PRIMARY_COPY' and not r['gap_flags'].strip():
                continue
            out.append('- `%s` %s: %s - %s%s' % (r['row_id'], r['holding_category'], r['item'], r['gap_flags'], (' (route: %s)' % r['acquisition_route']) if r['acquisition_route'] else ''))
        out.append('')
    out += ['## Observations', '',
            '- **Air Force Act 1950 and Navy Act 1957 have no C5 master-register row**; only derived India Code texts exist in the scratchpad (no source binary). They should be registered before any reliance.',
            '- **AFT Act commencement notification S.O. 14(E)/2008 and the TRA 2026 commencement notification are not in any acquisition register** (C5 acquisition_register, C6-02 batch). They are new gaps raised here.',
            '- **Tribunals Reforms Act 2021** is listed as an amending Act in the held AFT compilation (R02) but no footnote attributes any AFT provision to it, and it is repealed by TRA 2026 s.24(1) (R20). PILOT-01 `amendment_source_gaps.csv#AMD-16` says a corpus document for TRA 2021 is "HELD"; no such binary is in `held_binaries_manifest.csv`, so that claim is unverified.',
            '- No KB record cites AFT s.9A, the only provision the held compilation attributes to Finance Act 2017 and TRA 2026.',
            '- BNSS and BSA compilations (as on 06-10-2025) print no list of amending Acts; absence in a compilation is not proof of no amendment.',
            '- IPC 1860 has no copy of any kind (not even derived text); CrPC 1973 and IEA 1872 exist only as derived text of unknown edition.', '']
    return '\n'.join(out) + '\n'


def md_amend(rows):
    fams = collections.Counter(r['instrument_family'] for r in rows)
    gaps = collections.Counter((r['instrument_family'], r['commencement_gap']) for r in rows)
    out = ['# C8-D Task 3: amendment and commencement evidence matrix', '',
           'Source: `amendment_commencement_matrix.csv` (%d rows). Army Rules and Army Act rows are carried from `SOURCE-LIBRARY-C5/registers/amendment_register.csv` with their recorded states **preserved verbatim** (`commencement_status_preserved`, `verification_status`, `amendment_chain_status`). AFT Act, TRA and BNS/BNSS/BSA rows are new and cite held page readings (`tools/inputs/held_page_readings.csv`). A commencement date appears in `commencement_date_evidenced` **only** where the instrument itself states it (STATED_IN_INSTRUMENT). Publication dates are never used as commencement dates.' % len(rows), '',
           md_table(['family', 'rows'], sorted(fams.items())), '', '## Commencement gaps by family', '',
           md_table(['family', 'commencement_gap', 'rows'], [[a, b, n] for (a, b), n in sorted(gaps.items())]), '',
           '## Reserved states preserved (not resolved)', '',
           '- r.23(3): C-01 / U-01 **CONFLICTING** (retained until legal review); no located amending instrument 1963-2022 amends r.23 (R23-VERIFY-01).',
           '- r.182: SC4-01 **OPEN** (S.R.O. 17(E)/1993 item 36 printed wording; no corrigendum searched or located).',
           '- r.193: C-08 / U-07 **OPEN** (chronology incomplete; no correction proposed); U-04 discrepancy candidate.',
           '- r.194: C-09 / U-08 **PROPOSAL** pending legal review (AQ-02).',
           '- r.192: C-02 CONFLICTING; r.177: C-03 CONFLICTING pending text comparison.',
           '- AQ-05 (instrument silent on commencement) and AQ-06 (retrospective deemed effect, AR-024 from 1979-06-04 as printed) remain adviser questions.', '',
           '## New rows (outside the C5 amendment register)', '']
    for r in rows:
        if r['row_id'].startswith(('D-AMC-AFT', 'D-AMC-BNS', 'D-AMC-BNSS', 'D-AMC-BSA')):
            out.append('- `%s` %s - %s: %s; commencement gap **%s**.' % (r['row_id'], r['amending_instrument'], r['provision_affected'], r['commencement_status_preserved'], r['commencement_gap']))
    out += ['', 'Historical applicability intervals are filled only where a chain row has a stated commencement; everywhere else the column says NOT EVIDENCED. The IPC/CrPC/IEA to BNS/BNSS/BSA transition date (01-07-2024) appears only in consolidation/derived footnotes and is therefore not evidenced by a primary document.']
    return '\n'.join(out) + '\n'


def md_c602(rows):
    pinned = sum(r['pin_status'] == 'PINNED' for r in rows)
    out = ['# C8-D Task 4: C6-02 Gazette acquisition readiness (offline reconciliation)', '',
           'Source: `c6_02_readiness.csv` (%d files). No network call was made. Checks used only committed metadata: the C6-02 batch register, C5 discovery candidates, the C5 acquisition register and the committed archive.org metadata snapshots (`ACQ-01/archive_org_metadata_snapshot.json`, `ACQ-02/archive_org_metadata_snapshot_acq02.json`), plus md5 values computed from the %s held binaries (`tools/inputs/held_md5.csv`).' % (len(rows), '67'), '',
           '## Results', '',
           '- **%d of %d pinned** (md5 + bytes); 2 DPP Amendment Act 2000 items unpinned (file name, URL, md5, bytes missing).' % (pinned, len(rows)),
           '- Pins reconcile with the C5 candidate rows: %d md5 MATCH, %d bytes MATCH.' % (sum('C5 candidate md5 MATCH' in r['metadata_reconciliation'] for r in rows), sum('C5 candidate bytes MATCH' in r['metadata_reconciliation'] for r in rows)),
           '- **None of the 20 identifiers is in a committed metadata snapshot** (the ACQ-01/ACQ-02 snapshots cover the held Army Rules Gazettes only), so the pins rest on the Cycle 5 discovery records alone. They can be cross-checked only at download time.',
           '- **No expected md5 equals any held binary or any snapshot file**: none of the 20 documents is already held under another identifier. Compilations of the same Acts are held (Army Act, AFT Act, BNSS, BSA) but they are different documents and are not substitutes.',
           '- `sha256` is missing for every row by design (computable only after download).', '',
           md_table(['candidate', 'publication', 'identifier', 'pin', 'reconciliation', 'held elsewhere', 'KB items on dependent sources'],
                    [[r['candidate_id'], r['publication'][:60], r['archive_identifier'], r['pin_status'], r['metadata_reconciliation'], r['held_under_other_identifier'][:60], r['kb_items_on_dependent_sources']] for r in rows]), '',
           '## Post-download verification procedure (for use only after approval A-C5-1)', '',
           '1. Before any request: confirm the owner approval reference and the stacked crawler-config PR; read archive.org robots.txt (must be RULES_PARSED and allow the path); data-node redirects only to `*.archive.org`, each with its own robots decision. Unpinned identifiers are not fetched.',
           '2. Fetch into a new, empty quarantine directory, one file per identifier; record time, URL, final URL, status, bytes in the request log (log format v2).',
           '3. Verify **bytes == expected_bytes** and **md5 == expected_md5** from this register; any mismatch: quarantine, do not register, report.',
           '4. Compute **sha256**; check the PDF signature (`%PDF`) and that no other container format is present; record page count and text-layer class with the same profiler used for `held_binaries_manifest.csv`.',
           '5. Check the sha256 against all held binaries (duplicate detection) and record any alias.',
           '6. Page-image check of the masthead (Gazette issue, date, Part/Section, S.R.O./Act number) and of every operative page relied on; record render sha256 in a page-image-check register.',
           '7. For the 10 possible Army Rules S.R.O.s: read the subject on the page image; record whether each amends the Army Rules (and which rules) or is unrelated; never infer from metadata.',
           '8. For the three commencement notifications: transcribe the appointed date and any section-specific exception exactly; only then may a commencement date be entered, as STATED_IN_INSTRUMENT, with the page reference.',
           '9. Add a reviewed source-authentication addendum row (copy-level provenance) before any copy is used for EXACT_ANCHOR; locators must pass the AUTH-LEDGER-02 strict parser.',
           '10. Re-run the crosswalk build; report the movement of items from PARTIAL to EXACT separately for each source; do not change legal status or reserved states.', '',
           '## Decision item P-C7-02-META (restated; not executed)', '',
           '- **Question for the owner:** approve a metadata-only request route for the two unpinned DPP Amendment Act 2000 identifiers (`in.gazette.central.e.2000-08-25.168`, `in.gazette.e.2000.379`)?',
           '- **Scope:** only `https://archive.org/metadata/<identifier>` for the two listed identifiers; JSON only (content-type exactly application/json), body cap 512 KB, no redirects followed, no document body ever requested; keep only `files[]` entries for the expected PDF (`name`, `size`, `md5`, `sha1`); zero or several matches = PIN_AMBIGUOUS (fail closed); robots must be RULES_PARSED and allow `/metadata/`; GET without prior 200 HEAD allowed for this route only (archive.org answers HEAD 405, as logged in `C6-PREP/discovery/c6_02_metadata_requests_v2.tsv`).',
           '- **Implementation if approved:** a separately reviewed change to `SOURCE-LIBRARY-C5/tools/discovery_guard.py` with the mocked tests listed in `C7-PREP/WORKSTREAMS_READINESS.md`; the crawler is not touched.',
           '- **Still required afterwards:** A-C5-1 for any download. Unpinned downloads are not acceptable.',
           '- **Status:** NOT APPROVED, NOT EXECUTED. No network call was made in Cycle 8.']
    return '\n'.join(out) + '\n'


def md_pension(rows, rec_rows, s):
    m08 = s['m08']
    coded = s['coded']
    nd = [r for r in rec_rows if r['docs_not_held']]
    out = ['# C8-D Task 5: pension and entitlement source coverage', '',
           'Sources: `pension_source_coverage.csv` (one row per document) and `pension_record_dependency.csv` (one row per record). Dependencies come from the `V6-S..` citation codes in each KB record\'s `references` field, resolved through `PILOT-01/registers/source_code_resolution_v3.csv`. Keyword mentions are reported separately and are indicative only.', '',
           '- M08 (pension) records: **%d**. Records citing at least one V6 code: **%d**. Records with at least one cited pension document not held: **%d**.' % (m08, coded, len(nd)),
           '- The held ER-2023 copy (`29f6fa2c...`, 35 pp., 13,011,188 bytes) contains the covering letter, ER-2023 (Appendix-I) and annexures; **GMO-2023 (Appendix-II) is absent**. It is kept as a distinct row, is provenance-undocumented, and is never treated as the complete publication (the complete file is C5-ACQ-09, 49,925,674 bytes; comparison is C5-CF-C5-03, OPEN).',
           '- **Blockers preserved:** only the ER/GMO 2023 URL is in draft PR #9; all other DESW items need an allow-list extension; desw.gov.in robots.txt returned 403, so the fail-closed rule applies (no bypass). Approval A-C5-2 is required.',
           '- **Register observation:** code V6-S07 (GMO 2023, %d records) is resolved in v3 but is UNMAPPED in the C5 crosswalk (`corpus_source_map.csv` has no V6-S07 row). Its records are therefore counted as "citation not identified" rather than as dependent on C5-SRC-P1-ER-GMO-2023. Proposed fix for a later cycle: add the mapping (not done here).' % len(s['doc_recs'].get('GMO2023-APPX-II', set())), '',
           md_table(['document', 'state', 'records citing (code)', 'records closed if acquired (sole missing source)', 'records (text mention)', 'cases', 'route'],
                    [[r['document'][:70], r['state'], r['kb_records_citing_by_code'], r['kb_records_sole_missing_source'], r['kb_records_text_mention'], r['case_ids'] or '-', r['acquisition_route'][:50]] for r in rows]), '',
           '"Closed if acquired" means the document is the only cited pension source of that record that is not held; acquiring it would leave the record dependent only on held (if still unregistered) sources. It does not mean the record becomes legally verified.', '',
           '## Historical regimes', '',
           'ER 1982, ER 2008, PRA 1961 and GMO 2002/2008 are not cited by code, but records and cases discuss them (Dharamvir Singh and Rajbir Singh under the earlier entitlement regime; Mullikote under PRA 1961 and 2008; Jujhar Singh and K J S Buttar under PRA 1961). ER 1982, PRA 1961 and GMO 2002/2008 were NOT_FOUND in the searched sources; ER 2008 has two non-identical DESW files (C5-ACQ-10, comparison C5-CF-C5-02 OPEN). Which edition governs a claim depends on dates of service events and is a legal question; nothing here assigns a regime.']
    return '\n'.join(out) + '\n'


def md_drafts(regs):
    hdr = '**DRAFT — NO CORRESPONDENCE AUTHORISED.** Not sent. Not to be sent without owner approval of scope (P-C6-04-SCOPE), of the request text and of access-marking handling (A-C5-3). Placeholders in [brackets]; no personal details are included.'
    letters = [
        ('CR-01', 'Regulations for the Army, Revised Edition 1987 (Vols I and II) and all amendment lists / correction slips', '[Custodian: Ministry of Defence / Army HQ publication authority]',
         'RA-1987-V1; RA-1987-V2; RA-1987-SLIPS', ['an authorised copy of each volume, including the printed title page (publisher, printer, job number) and the printed access marking;',
                                                    'every amendment list / correction slip issued since 1987, with the amendment-incorporation record;',
                                                    'confirmation whether the 1987 edition remains the current edition, and of any later edition.']),
        ('CR-02', 'Regulations for the Army 1962, with amendment slips (historical edition)', '[Custodian: MoD / Army HQ library or archive]', 'RA-1962',
         ['an authorised copy (or confirmation that none is held for release);', 'the record of its replacement, if any, by the 1987 edition (no supersession is assumed by the project).']),
        ('CR-03', 'Regulations for the Medical Services of the Armed Forces (2010 revised, and 1983 edition), with amendments', '[Custodian: DGAFMS]', 'RMSAF-2010; RMSAF-1983',
         ['authorised copies with title page and access marking;', 'the amendment record since 2010.']),
        ('CR-04', 'Army Order 45/2001 and Army Order 13/2006/PS', '[Custodian: Army HQ (AG\'s Branch)]', 'AO-45-2001; AO-13-2006-PS',
         ['confirmation of existence and publication status of each order;', 'if publicly releasable, an authorised copy with its access marking; if not, a statement to that effect (no restricted material is requested).']),
        ('CR-05', "Staff Officers' Handbook: Processing of Statutory/Non-Statutory Complaints on D&V Matters (May 2014, apparent)", '[Custodian: Addl DG Discipline & Vigilance, AG\'s Branch (apparent issuer, unverified)]', 'DV-SOH-2014',
         ['confirmation whether this handbook was issued, its date and current status;', 'if releasable, an authorised copy with access marking. The project has NOT opened or used the third-party (Scribd) upload and treats it as non-authoritative.']),
        ('CR-06', 'Criminal Courts and Court-martial (Adjustment of Jurisdiction) Rules 1978 and Amendment Rules 1986 (S.O. 4010 of 06-12-1986)', '[Custodian: Ministry of Home Affairs / Gazette publication authority]', '(C8-D; C5-SRC-P1-CCCM-ADJ-RULES)',
         ['FALLBACK ONLY: both instruments are already pinned as archive.org Gazette facsimiles in ACQ-01-B2; send only if those copies fail post-download verification or a certified copy is required;',
          'certified or official Gazette copies of the 1978 Rules (S.O. 488) and of S.O. 4010/1986, including the date of S.O. 4010 as printed;', 'any later amendment notifications (including any made after BNSS 2023).']),
        ('CR-07', 'Historical pension instruments: Entitlement Rules 1982; Pension Regulations for the Army 1961 (Parts I and II); Guide to Medical Officers (Military Pensions) 2002 and 2008', '[Custodian: Department of Ex-Servicemen Welfare]', '(C8-D; C5-SRC-P1-ER-1982, -PRA-1961, -GMO-2002-2008)',
         ['official copies, with the covering letters and effective-date clauses as printed;', 'confirmation of the amendment record of each instrument.']),
    ]
    out = ['# Custodian request drafts (C8-D Task 6)', '', hdr, '', 'Inventory and classification: `regulations_custodian_inventory.csv`. Each draft below maps to request ids in `C6-PREP/registers/c6_04_custodian_request_inventory.csv` where one exists.', '']
    for lid, subj, to, req, asks in letters:
        out += ['---', '', '## %s: %s' % (lid, subj), '', hdr, '', '- **To:** %s' % to, '- **From:** [project owner / authorised signatory]', '- **Request ids:** %s' % req, '- **Subject:** Request for an authorised copy: %s' % subj, '',
                'Dear [title],', '', 'The [project name] research project is compiling a record of publicly published military-law instruments for an offline reference system. We respectfully request:', '']
        out += ['%d. %s' % (i, a) for i, a in enumerate(asks, 1)]
        out += ['', 'Handling: any copy supplied will be kept in a private store; printed access markings will be recorded and respected; restricted material will not be placed in any public store, and no third-party copy will be relied on.', '',
                'We do not ask for any material that is not authorised for release.', '', 'Yours faithfully,', '[name, designation] — [contact placeholder]', '', '*%s*' % 'DRAFT — NO CORRESPONDENCE AUTHORISED', '']
    return '\n'.join(out) + '\n'


def md_findings(base, matrix_rows, dep, amend_rows, c602, pen_rows, pen_sum, regs, gaps, unassigned, nonexact):
    top = [g for g in gaps if g['gap_id'] != 'G-NOCIT'][:15]
    out = ['# PRIMARY_SOURCES_C8_FINDINGS (Cycle 8, Workstream D)', '',
           '**Scope:** inventories and evidence matrices only. No download, no network request, no crawler/config/robots change, no legal status changed, no commencement date inferred, no reserved state resolved. Repository snapshot read-only at commit bb1f0971. All outputs regenerate with `python tools/build_c8_d.py <repo> --check`.', '',
           '## 1. Baseline (recomputed)', '']
    for r in base:
        out.append('- %s: reported %s, recomputed **%s** (%s)' % (r['metric'].strip(), r['reported_value'], r['recomputed_value'], r['result']))
    out += ['', '**Discrepancy:** "1,060 KB citation items" counts crosswalk rows, including 77 NO_CITATION placeholders; the true number of citation items is **983**, and genuine MISSING items are **289** (not 366). 618 reproduces, but 77 of those records cite nothing (541 have citations and no exact anchor). Details: `BASELINE_RECOMPUTE.md`.', '',
            '## 2. Key gaps per instrument', '']
    gl = {
        'AA1950': 'Gazette as enacted NOT held (pinned C5-ACQ-01 = ACQ03-029 = ACQ-C3-01); only an India Code compilation (provenance undocumented). Commencement S.R.O. 120/1950 not held (%s; probable candidate ACQ03-019 in PR #23). Act 37/1992 held with documented provenance; Act 13/1975 held (undocumented); Act 19/1955 extract lacks its Schedule (Gazette pinned ACQ-01-B6; appointing S.R.O. 2(E)/1955 candidate ACQ03-020). ALO 1956, Act 56/1974, Ordinance 1975 and Act 20/1983 (+ its commencement notification) not held but pinned in ACQ-03 (PR #23); RAA 1957 and S.O. 3912(E)/2019 not located.' % CNR,
        'AR1954': '1954 S.R.O. 484 held (documented primary). 24 amending/declaration Gazettes held, only 3 with documented provenance (AR-006, AR-029, AR-031). Chain open after 06-06-2022 (10 candidate S.R.O.s, subject unconfirmed); AR-001 and AR-030 not found; 5 text-layer-only; 13 hints unopened. Reserved: r.23(3) CONFLICTING, r.182 OPEN, r.193 OPEN, r.194 PROPOSAL.',
        'AFT2007': 'Gazette as enacted NOT held (pinned C5-ACQ-02); compilation as on 01-09-2026 held (undocumented). Commencement S.O. 14(E)/2008 not held and not registered (%s). Finance Act 2017 and TRA 2021 not held or registered; TRA 2021 provisions affected unknown. TRA 2026 held (undocumented) - substitutes s.9A and repeals TRA 2021, but commences by notification (%s). AFT Procedure Rules 2008/2011 and Practice Rules 2009: no held copy, although archive.org candidates are pinned in ACQ-03 (ACQ03-030..032, PR #23) - the C5 master still says DISCOVERY_REQUIRED.' % (CNR, CNR),
        'BNS2023': 'No reliable copy at all (derived text only); Gazette pinned (C5-ACQ-20); commencement notification not held (%s).' % CNR,
        'BNSS2023': 'Gazette not held (pinned C5-ACQ-03); compilation held (undocumented); commencement footnote S.O. 848(E) only (%s).' % CNR,
        'BSA2023': 'Gazette not held (pinned C5-ACQ-04); compilation held (undocumented); commencement footnote S.O. 849(E) only (%s); C-07 adviser question on AA s.133 preserved.' % CNR,
        'SANHITA2024': 'All three 2024 notifications not held; pinned (C5-ACQ-05). The 01-07-2024 switch date is evidenced only by compilation/derived footnotes.',
        'IPC1860': 'No copy of any kind (not even derived text).', 'CRPC1973': 'Derived text only (edition unknown); BNSS s.531 repeal read from the compilation.',
        'IEA1872': 'Derived text only (edition unknown); BSA s.170 repeal read from the compilation.',
        'CCCM': '1978 Rules (S.O. 488) and S.O. 4010/1986 not held (only the Rajya Sabha papers-laid record), but BOTH are already pinned in ACQ-01-B2 (PR #8); the C5 master says NOT_CHECKED / DISCOVERY_REQUIRED. S.O. 4010 is dated 24-11-1986 in ACQ-01/PILOT-01 and "6th December 1986" in the C5 title (Gazette date): unresolved.',
        'DPP1950': 'Principal Act: no copy, India Code blocked. Amendment Act 2000: 2 archive items unpinned (P-C7-02-META).',
        'AFA1950': 'Derived text only; not registered in C5.', 'NA1957': 'Derived text only; not registered in C5.', 'ISO2023': 'Not held; not searched.',
    }
    for k, v in gl.items():
        out.append('- **%s:** %s' % (INSTRUMENT_NAMES[k], v))
    out += ['', '## 3. Highest-value acquisitions (by dependent records; `source_to_record_gap_matrix.csv`)', '',
            md_table(['rank', 'gap', 'source', 'KB records (direct)', 'KB items', 'upper bound', 'cases', 'tier', 'route', 'authorisation'],
                     [[g['rank'], g['gap_id'], g['missing_or_incomplete_source'][:70], g['n_kb_records'], g['n_kb_items'], g['upper_bound_kb_records'], g['n_cases'], g['consequence_tier'], g['acquisition_route'][:40], g['authorisation_required'][:50]] for g in top]), '',
            'Direct = the record has a crosswalk item that depends on the source. Upper bound = records that could be affected where the affected provisions are unknown (e.g. post-2022 Army Rules S.R.O.s could touch any rule, including the 42 exact anchors).', '',
            'Every one of the %d non-exact KB citation items is assigned to at least one gap row: %s.' % (len(nonexact), 'YES' if not unassigned else 'NO - %d unassigned' % len(unassigned)), '',
            '**Priority order (combining dependent records, legal consequence and readiness):**',
            '1. **Batch A Gazettes under A-C5-1** (already pinned): Army Act 1950 (%s records), AFT Act 2007 (%s), BSA (%s), BNSS (%s), BNS (%s) and the three 2024 commencement notifications (%s direct; %s upper bound). These convert compilation-only reliance into enacted text; current text still needs the amendment chains.' % tuple(
                [next(g['n_kb_records'] for g in gaps if g['gap_id'] == x) for x in ('G-AA-ENACT', 'G-AFT-ENACT', 'G-BSA-ENACT', 'G-BNSS-ENACT', 'G-BNS-ENACT', 'G-SAN-COMM')] + [next(g['upper_bound_kb_records'] for g in gaps if g['gap_id'] == 'G-SAN-COMM')]),
            '2. **Provenance registration of already-held copies (no download):** 7 SC judgments and the 21 undocumented Army Rules Gazettes (AUTH-LEDGER tranches 1-2). Necessary but not sufficient for amended rules.',
            '3. **AFT Procedure Rules 2008/2011 and Practice Rules 2009** (%s records) - already pinned in ACQ-03 (PR #23), needs A-C5-1 and C5 register reconciliation; and the **10 post-2022 Army Rules S.R.O.s** (pinned in C6-02; upper bound %s records).' % (next(g['n_kb_records'] for g in gaps if g['gap_id'] == 'G-AFT-PR'), next(g['upper_bound_kb_records'] for g in gaps if g['gap_id'] == 'G-AR-POST2022')),
            '4. **Batch B (DESW) under A-C5-2**: PRA 2008 Pt I (%s records), Pt II (%s), complete ER/GMO 2023 file (ER %s, GMO %s records). Blocked by allow-list and robots 403.' % tuple(next(g['n_kb_records'] for g in gaps if g['gap_id'] == x) for x in ('G-PRA-PT1', 'G-PRA-PT2', 'G-ER2023', 'G-GMO2023')),
            '5. **Commencement notifications:** AFT S.O. 14(E)/2008 and TRA 2026 s.1(2) notification(s) are in NO register (discovery approval needed); Army Act S.R.O. 120/1950 has a probable candidate (ACQ03-019, PR #23).',
            '6. **CCCM Rules 1978 / S.O. 4010/1986** (%s records): pinned in ACQ-01-B2 (PR #8) - only A-C5-1 is needed; then the historical IPC/CrPC/IEA texts (discovery).' % next(g['n_kb_records'] for g in gaps if g['gap_id'] == 'G-CCCM'),
            '7. **Custodian route (scope extension needed):** RA 1987 + slips, RMSAF, named Army Orders, D&V handbook (lead only).', '',
            '## 3a. Register reconciliation findings (not corrected here)', '',
            '- **C5 does not carry forward candidates pinned in ACQ-01 / ACQ-03.** `COORDINATION/CYCLE3-PLANNING/acquisition_schedule.csv` and `ACQ-01/batches.json` hold pinned archive.org candidates for the CCCM Rules 1978 and S.O. 4010/1986 (ACQ-01-B2), the AFT Procedure Rules 2008, Amendment Rules 2011 and Practice Rules 2009 (ACQ03-030..032), the Army Act commencement notification (ACQ03-019, probable), Act 19/1955 and its appointing S.R.O. (ACQ-01-B6, ACQ03-020), ALO 1956, Ordinance 1975, Acts 56/1974 and 20/1983 (+ commencement), and Army Rules hint/OCR instruments (ACQ03-001..014, 036..039). The C5 master register records several of these as NOT_CHECKED / DISCOVERY_REQUIRED, and `D6_CORPUS_COVERAGE_MATRIX.md` says the CCCM items still need "locating". These are acquisition-readiness gaps, not discovery gaps.',
            '- **GMO 2023 has a separate DESW URL** in ACQ-01-B4 (`desw.gov.in/sites/default/files/2026-10/GMO 2023.pdf`, not pinned) besides the combined 49.9 MB ER/GMO file in C6-03; not in PR #9.',
            '- **Code V6-S07 (GMO 2023, 11 records) is UNMAPPED in the C5 crosswalk** although v3 resolves it; `corpus_source_map.csv` has no V6-S07 row.',
            '- **PILOT-01 AMD-16** says a TRA 2021 corpus document is "HELD"; no such binary is in `held_binaries_manifest.csv`.',
            '- **Air Force Act and Navy Act** have derived texts but no C5 source rows.',
            '- **Baseline label:** "1,060 KB citation items" should read "1,060 crosswalk rows (983 citation items + 77 no-citation placeholders)".', '',
            '## 4. Authorisations required (none granted; none exercised)', '',
            md_table(['item', 'what it authorises', 'needed for'], [
                ['A-C5-1', 'owner approval of real downloads of the pinned archive.org Gazettes, via a crawler-config PR stacked on #8 (adds *.archive.org; staging lists archive.org only)', 'C6-02 Batch A (18 pinned files)'],
                ['A-C5-2', 'owner approval of DESW downloads', 'C6-03 (PRA 2008, ER 2008, complete ER/GMO 2023, circulars)'],
                ['A-C5-3', 'approval of custodian request text and access-marking handling', 'C6-04 drafts (CUSTODIAN_REQUEST_DRAFTS.md)'],
                ['P-C7-02-META', 'metadata-only archive.org route for the 2 unpinned DPP identifiers (guard change, mocked tests, logged run)', 'pinning C5C-026/027; A-C5-1 still needed to download'],
                ['Allow-list extension', 'config PR adding the DESW file paths beyond the single ER/GMO 2023 URL in draft PR #9', 'C6-03'],
                ['Robots', 'a later successful robots read of desw.gov.in (currently 403 => fail-closed) or an owner-side manual retrieval with sha256 recorded', 'C6-03'],
                ['Scope extension P-C6-04-SCOPE', 'narrow extension of CLAUDE.md scope to named publications (RA 1987, RMSAF, named AOs) with access-marking handling', 'C6-04; Army Orders are otherwise out of scope'],
                ['Discovery approval', 'guarded discovery for instruments with no candidate in any register (AFT S.O. 14(E)/2008, TRA 2026 s.1(2) notification(s), TRA 2021, Finance Act 2017, S.O. 3912(E)/2019, RAA 1957, IPC/CrPC/IEA historical texts, Air Force/Navy Act Gazettes, ISO Act/Rules)', 'new gaps raised in C8-D'],
                ['PR #8 / PR #23 stack', 'approval and merge of the existing unmerged config PRs that already pin CCCM (ACQ-01-B2), Act 19/1955 (B6), AFT Procedure/Practice Rules and Army Act amending instruments (ACQ-03)', 'items already pinned outside C5'],
            ]), '',
            '## 5. Limitations', '',
            '- Technical inventory only; nothing here is legal advice, a legal-status finding or a currency claim.',
            '- Compilation footnotes and derived texts were read only to identify what is missing; they are never treated as commencement or amendment evidence.',
            '- Text-layer readings (PyMuPDF) of held PDFs were used for the AFT, Army Act, BNSS, BSA compilations and TRA 2026; they were not page-image checked in C8. Needles are re-verifiable with `--verify-held`.',
            '- Text-mention dependencies (pension historical regimes, IPC/CrPC/IEA, Air Force/Navy Acts) are keyword-based and indicative; coded dependencies come from the crosswalk and v3 code resolution.',
            '- Section-overlap dependencies parse section/rule numbers from register text; parenthesised sub-units are ignored, so overlaps are at section/rule level.',
            '- Archive.org pins come from Cycle 5 metadata and could not be re-verified offline; none of the 20 identifiers is in a committed snapshot.',
            '- The baseline discrepancy is a definitional one; no register was edited.', '',
            '## 6. Output files', '',
            '- `BASELINE_RECOMPUTE.md`, `baseline_recompute.csv`', '- `statutory_source_matrix.csv`, `statutory_source_matrix.md`', '- `amendment_commencement_matrix.csv`, `amendment_commencement_matrix.md`',
            '- `c6_02_readiness.csv`, `c6_02_readiness.md`', '- `pension_source_coverage.csv`, `pension_record_dependency.csv`, `pension_source_coverage.md`',
            '- `regulations_custodian_inventory.csv`, `CUSTODIAN_REQUEST_DRAFTS.md`', '- `source_to_record_gap_matrix.csv`', '- `PRIMARY_SOURCES_C8_FINDINGS.md` (this file)', '- `OUTPUT_SHA256SUMS`',
            '- `tools/build_c8_d.py`, `tools/inputs/held_page_readings.csv`, `tools/inputs/derived_text_readings.csv`, `tools/inputs/held_md5.csv`']
    return '\n'.join(out) + '\n'


# ===================================================================== MAIN
def build(repo):
    d = Data(repo)
    files = collections.OrderedDict()
    base = task_baseline(d)
    files['baseline_recompute.csv'] = csv_text(['metric', 'reported_value', 'reported_in', 'recomputed_value', 'derivation', 'result', 'note'], base)
    files['BASELINE_RECOMPUTE.md'] = md_baseline(base)
    mrows, dep = task_matrix(d)
    mf = ['row_id', 'instrument_key', 'instrument', 'holding_category', 'item', 'c5_source_id', 'c5_holding_state', 'held', 'copy_id', 'sha256', 'carrier', 'provenance_class',
          'eligible_for_exact_anchor', 'pages', 'completeness', 'what_is_missing', 'gap_flags', 'acquisition_route', 'instrument_kb_items_crosswalk', 'instrument_kb_records_crosswalk',
          'instrument_kb_records_text_mention', 'evidence']
    files['statutory_source_matrix.csv'] = csv_text(mf, mrows)
    files['statutory_source_matrix.md'] = md_matrix(mrows, dep)
    arows = task_amend(d)
    af = ['row_id', 'instrument_family', 'provision_affected', 'amending_instrument', 'amendment_type', 'enactment_or_issue_date', 'publication_date', 'commencement_as_printed',
          'commencement_date_evidenced', 'commencement_status_preserved', 'commencement_gap', 'supporting_document_held', 'document_sha256', 'copy_id', 'copy_evidence_class',
          'gazette_identity', 'evidence_level', 'verification_status', 'amendment_chain_status', 'provision_chain_rows', 'unresolved_conflicts', 'historical_applicability_interval', 'source_evidence']
    files['amendment_commencement_matrix.csv'] = csv_text(af, arows)
    files['amendment_commencement_matrix.md'] = md_amend(arows)
    crows = task_c602(d)
    cf = ['acq_c5_id', 'candidate_id', 'c5_source_id', 'publication', 'archive_identifier', 'file_name', 'expected_md5', 'expected_bytes', 'pin_status', 'metadata_reconciliation',
          'committed_snapshot_check', 'held_under_other_identifier', 'related_holding', 'missing_fields', 'identity_status', 'kb_items_on_dependent_sources', 'kb_records_on_dependent_sources',
          'approval_state', 'prerequisites', 'evidence']
    files['c6_02_readiness.csv'] = csv_text(cf, crows)
    files['c6_02_readiness.md'] = md_c602(crows)
    prows, rec_rows, psum = task_pension(d)
    pf = ['pension_doc_key', 'document', 'c5_source_id', 'c5_holding_state', 'state', 'sha256', 'consequence_tier', 'acquisition_route', 'blockers', 'kb_records_citing_by_code',
          'kb_record_ids_citing', 'kb_records_sole_missing_source', 'kb_record_ids_closed_if_acquired', 'kb_records_text_mention', 'kb_record_ids_text_mention', 'crosswalk_items',
          'crosswalk_status', 'case_ids', 'evidence']
    files['pension_source_coverage.csv'] = csv_text(pf, prows)
    files['pension_record_dependency.csv'] = csv_text(['record_id', 'module', 'codes', 'required_docs', 'docs_not_held', 'docs_held_but_not_primary', 'closure_set', 'text_mentions', 'crosswalk_status'], rec_rows)
    files['pension_source_coverage.md'] = md_pension(prows, rec_rows, psum)
    regs = task_regs(d)
    files['regulations_custodian_inventory.csv'] = csv_text(['inv_id', 'publication', 'classification', 'c5_source_id', 'c5_holding_state', 'held', 'sha256', 'access_marking', 'authority_status',
                                                             'custodian_request_id', 'discovery_candidates', 'evidence', 'notes'], regs)
    files['CUSTODIAN_REQUEST_DRAFTS.md'] = md_drafts(regs)
    gaps, nonexact, unassigned = task_gaps(d, psum)
    gf = ['rank', 'rank_potential', 'gap_id', 'missing_or_incomplete_source', 'c5_source_id', 'gap_type', 'dependency_basis', 'n_kb_records', 'n_kb_items', 'upper_bound_kb_records', 'potentially_affected_kb_records', 'n_cases', 'case_ids',
          'consequence_tier', 'legal_consequence', 'acquisition_route', 'authorisation_required', 'kb_record_ids', 'note']
    files['source_to_record_gap_matrix.csv'] = csv_text(gf, gaps)
    files['PRIMARY_SOURCES_C8_FINDINGS.md'] = md_findings(base, mrows, dep, arows, crows, prows, psum, regs, gaps, unassigned, nonexact)
    sums = ''.join('%s  %s\n' % (hashlib.sha256(v.encode('utf-8')).hexdigest(), k) for k, v in files.items())
    files['OUTPUT_SHA256SUMS'] = sums
    return files, d


def verify_held(d, root):
    bad = []
    try:
        import pymupdf as fitz
    except ImportError:
        import fitz
    for r in d.held_md5:
        p = os.path.join(root, r['first_held_path'])
        b = open(p, 'rb').read()
        if hashlib.sha256(b).hexdigest() != r['sha256'] or hashlib.md5(b).hexdigest() != r['md5']:
            bad.append('hash ' + p)
    for r in d.readings.values():
        p = os.path.join(root, r['held_path'])
        if sha256_file(p) != r['sha256']:
            bad.append('reading sha ' + r['reading_id'])
            continue
        t = ' '.join(fitz.open(p)[int(r['page']) - 1].get_text().split())
        if r['needle'] not in t:
            bad.append('needle ' + r['reading_id'])
    for r in d.dreadings.values():
        p = os.path.join(root, r['scratchpad_path'])
        b = open(p, 'rb').read()
        if hashlib.sha256(b).hexdigest() != r['sha256'] or r['needle'] not in ' '.join(b.decode('utf-8', 'replace').split()):
            bad.append('derived ' + r['reading_id'])
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('repo')
    ap.add_argument('--out', default=os.path.dirname(TOOLS))
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--verify-held')
    a = ap.parse_args()
    files, d = build(a.repo)
    rc = 0
    if a.verify_held:
        bad = verify_held(d, a.verify_held)
        print('verify-held: %s' % ('OK (%d hashes, %d page readings, %d derived readings)' % (len(d.held_md5), len(d.readings), len(d.dreadings)) if not bad else 'FAIL ' + '; '.join(bad)))
        rc |= 1 if bad else 0
    if a.check:
        drift = []
        for k, v in files.items():
            p = os.path.join(a.out, k)
            if not os.path.exists(p) or open(p, encoding='utf-8').read() != v:
                drift.append(k)
        print('check: %s' % ('OK (%d files reproduce)' % len(files) if not drift else 'DRIFT ' + ', '.join(drift)))
        rc |= 1 if drift else 0
    else:
        os.makedirs(a.out, exist_ok=True)
        for k, v in files.items():
            with open(os.path.join(a.out, k), 'w', encoding='utf-8', newline='') as f:
                f.write(v)
        print('wrote %d files to %s' % (len(files), a.out))
    sys.exit(rc)


if __name__ == '__main__':
    main()
