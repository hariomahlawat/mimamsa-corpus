#!/usr/bin/env python3
"""WS-B (Judicial Precedents) register builder.

Builds the machine-derived WS-B registers from READ-ONLY inputs:
  * intern intake: an extraction of `origin/raw-data` (data/meta, data/text, data/excluded_judgments.jsonl)
    made with `git archive <commit> data/meta data/text data/excluded_judgments.jsonl | tar -x -C <snap>`;
  * frozen curated originals (cases_53, records_658) and the PILOT-01 87-code register;
  * hand-written identity specs and reviewed matches (tools/case_specs.py, tools/reviewed_matches.py);
  * a list of judgment PDFs already held in the session scratchpad with their SHA-256 (held_copies.csv).

Outputs (in the WS-B-JUDGMENTS directory):
  intake_manifest.csv, identity_resolution.csv, crosswalk_cases53_kb658.csv,
  pending_source_queue.csv (auto part, merged with pending_source_queue_manual.csv), intake_stats.json

Nothing is downloaded; nothing outside WS-B-JUDGMENTS is written.
Usage: python3 build_registers.py --snapshot <dir> --raw-data-commit <sha>
"""
import argparse, csv, hashlib, json, os, re, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.dirname(HERE)
REPO = os.path.abspath(os.path.join(WS, '..', '..', '..'))
sys.path.insert(0, HERE)
from case_specs import SPECS            # noqa: E402
from reviewed_matches import MATCHES, C2    # noqa: E402

CASES53 = os.path.join(REPO, 'legal_knowledge/curated_originals/case_law/v0.9/cases_53.jsonl')
KB658 = os.path.join(REPO, 'legal_knowledge/curated_originals/knowledge_base/v0.9/records_658.jsonl')
CODES = os.path.join(REPO, 'legal_knowledge/audit_work/PILOT-01/registers/source_code_resolution_v3.csv')
CASES53_SHA = '8b8d53cd1434f7c1c6eaebe77f1fe295fb8b81b755e93276999b4b40b3c8f89a'
KB658_SHA = '9a8f0d193065762ffa987116dc761bcb734008d2a87a946f5591741f5befcfc1'

# ---------------------------------------------------------------- independent lexical relevance check
def _rx(words):
    return re.compile(r'\b(?:' + '|'.join(words) + r')\b', re.I)

STRONG = _rx([r'army\s+act', r'air\s+force\s+act', r'navy\s+act', r'armed\s+forces\s+tribunal',
              r'a\.?\s?f\.?\s?t\.?\s+act', r'AFT', r'court[\s-]+martial', r'courts[\s-]+martial', r'summary\s+of\s+evidence',
              r'entitlement\s+rules', r'release\s+medical\s+board', r'invaliding\s+medical\s+board',
              r'army\s+rules', r'pension\s+regulations\s+for\s+the\s+(?:army|air\s+force|navy)',
              r'regulations\s+for\s+the\s+army', r'armed\s+forces\s*\(special\s+powers\)', r'afspa'])
WEAK = _rx([r'invalided', r'disability\s+pension'])
SERVICE = _rx([r'army', r'air\s+force', r'navy', r'naval', r'sepoy', r'havildar', r'naik', r'subedar', r'jawan',
               r'ex[\s-]*servicem[ae]n', r'military', r'i\.?a\.?f\.?', r'j\.?c\.?o\.?', r'rifleman', r'sowar',
               r'gunner', r'signalman', r'craftsman', r'risaldar', r'sainik', r'defence\s+services',
               r'armed\s+forces', r'ex[\s.-]*hav', r'hav', r'nk', r'l\s*/\s*nk', r'ex[\s.-]*sep', r'cfn', r'rfn', r'gnr', r'sigmn',
               r'nb\.?\s*sub', r'lt\.?\s*col', r'wg\.?\s*cdr', r'sqn\.?\s*ldr', r'brig', r'maj\.?\s*gen', r'lt\.?\s*gen'])
INTERN_NARROW = _rx([r'army\s+act', r'air\s+force\s+act', r'navy\s+act', r'armed\s+forces\s+tribunal', r'courts?[\s-]+martial',
                     r'summary\s+of\s+evidence', r'disability\s+pension', r'entitlement\s+rules', r'invalided',
                     r'invalidment', r'invaliding', r'release\s+medical\s+board', r'AFT'])
CAPF = _rx([r'b\.?s\.?f\.?', r'border\s+security\s+force', r'c\.?r\.?p\.?f\.?', r'central\s+reserve\s+police',
            r'i\.?t\.?b\.?p\.?', r'c\.?i\.?s\.?f\.?', r'sashastra\s+seema\s+bal', r'assam\s+rifles', r'police'])
# Note: Assam Rifles is listed as CAPF marker only for flagging; it is not decisive.

def lexical(text):
    t = re.sub(r'\s+', ' ', text or '')
    s = len(STRONG.findall(t)); w = len(WEAK.findall(t)); sv = len(SERVICE.findall(t)); cp = len(CAPF.findall(t))
    if not t.strip():
        cls = 'TEXT_UNAVAILABLE'
    elif s >= 1 and (sv >= 1 or s >= 3):
        cls = 'MIL_CORE_LEXICAL'
    elif w >= 1 and sv >= 3:
        cls = 'MIL_PROBABLE_LEXICAL'
    elif (s + w) >= 1 and cp > sv:
        cls = 'CAPF_OR_OTHER_FORCE_LEAD'
    elif (s + w) >= 1:
        cls = 'WEAK_SIGNAL_REVIEW'
    else:
        cls = 'NO_MILITARY_SIGNAL'
    return s, w, sv, cp, cls

LINK_NOTES = {
    ('NITISHA', 'ADM-JD-04'): 'WRONG-DOCUMENT RISK: ADM-JD-04 digests MA 1913/2022 (Nitisha implementation application), not the 25 Mar 2021 judgment; paras 4-8, 19-22 unverified (OQ-D-004).',
    ('NITISHA', 'ADM-017'): 'WRONG-DOCUMENT RISK: ADM-017 cites the 3 Nov 2023 MA 1913/2022 judgment (spec NITISHA_MA), not the 2021 judgment.',
    ('NITISHA', 'ADM-SC-11'): 'WRONG-DOCUMENT RISK: ADM-SC-11 cites the 3 Nov 2023 MA 1913/2022 judgment (spec NITISHA_MA), not the 2021 judgment.',
    ('GIRISH_MAIN', 'PEN-J-06'): 'AMBIGUOUS: PEN-J-06 is the 12 Oct 2026 clarification (2026 INSC 1113), not the 12 Feb 2026 judgment.',
    ('GIRISH_CLAR', 'PEN-J-05'): 'AMBIGUOUS: PEN-J-05 is the 12 Feb 2026 judgment (2026 INSC 149), not the clarification.',
}

# ---------------------------------------------------------------- helpers
def sha256_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()

def write_csv(path, header, rows):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, lineterminator='\n')
        w.writerow(header)
        for r in rows:
            assert len(r) == len(header), (path, r)
            w.writerow(r)

def j(xs):
    return ';'.join(str(x) for x in xs if x not in (None, ''))

# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--snapshot', required=True)
    ap.add_argument('--raw-data-commit', required=True)
    a = ap.parse_args()
    snap = a.snapshot
    assert sha256_file(CASES53) == CASES53_SHA, 'cases_53 changed!'
    assert sha256_file(KB658) == KB658_SHA, 'records_658 changed!'

    meta_dir = os.path.join(snap, 'data/meta')
    recs = []
    for fn in sorted(os.listdir(meta_dir)):
        with open(os.path.join(meta_dir, fn), encoding='utf-8') as f:
            recs.append(json.load(f))
    judg = [r for r in recs if r.get('doc_type') == 'judgment']
    by_doc = {r['doc_id']: r for r in judg}

    def text_of(r):
        p = os.path.join(snap, r.get('text_path') or '')
        if r.get('text_path') and os.path.exists(p):
            with open(p, encoding='utf-8', errors='replace') as f:
                return f.read()
        return ''

    # ---------- 1. intake manifest: one row per distinct sha256 (document)
    groups = collections.OrderedDict()
    for r in sorted(judg, key=lambda r: (r['sha256'], r['doc_id'])):
        groups.setdefault(r['sha256'], []).append(r)
    # duplicate leads across different sha: same neutral citation
    nc_map = collections.defaultdict(set)
    for r in judg:
        if r.get('neutral_citation'):
            nc_map[r['neutral_citation']].add(r['sha256'])

    # reverse map of reviewed matches doc_id -> spec key
    doc2spec = collections.defaultdict(list)
    for key, m in MATCHES.items():
        for d in m['doc_ids']:
            doc2spec[d].append(key)
    spec_by_key = {s[0]: s for s in SPECS}

    rows = []
    stats = collections.Counter()
    cls_by_court = collections.defaultdict(collections.Counter)
    intern_vs_ws = collections.Counter()
    for i, (sha, rs) in enumerate(groups.items(), 1):
        r0 = rs[0]
        txt = text_of(r0)
        s, w, sv, cp, cls = lexical(txt)
        relv = sorted({(x.get('relevance') or {}).get('status') or '' for x in rs})
        intern_rel = relv[0] if len(relv) == 1 else 'MIXED:' + '|'.join(relv)
        dates = sorted({x.get('issue_date') or '' for x in rs})
        casenos = sorted({c for x in rs for c in (x.get('case_numbers') or [])})
        ncs = sorted({x.get('neutral_citation') for x in rs if x.get('neutral_citation')})
        reps = sorted({c for x in rs for c in (x.get('reported_citations') or [])})
        other_sha = sorted({o for n in ncs for o in nc_map[n] if o != sha})
        dup_kind = 'UNIQUE'
        if len(rs) > 1:
            if r0['source'] == 'sci':
                dup_kind = 'SAME_BYTES_YEAR_FOLDER_DUPLICATE' if len({x['source_record']['record_id'] for x in rs}) == 1 \
                    else 'SAME_BYTES_MULTIPLE_RECORDS'
            else:
                dup_kind = 'SAME_BYTES_COMMON_JUDGMENT_MULTIPLE_CASE_RECORDS' if len(casenos) > 1 else 'SAME_BYTES_MULTIPLE_RECORDS'
        if other_sha:
            dup_kind += '+SAME_NEUTRAL_CITATION_OTHER_BYTES'
        flags = []
        if r0.get('text_quality') == 'suspect': flags.append('TEXT_QUALITY_SUSPECT')
        if r0.get('text_method') == 'ocr': flags.append('OCR_TEXT_NOT_FOR_QUOTATION')
        if not txt: flags.append('NO_TEXT')
        if intern_rel in ('relevant',) and cls in ('NO_MILITARY_SIGNAL', 'WEAK_SIGNAL_REVIEW'): flags.append('INTERN_RELEVANT_BUT_WS_B_WEAK')
        if intern_rel == 'borderline' and cls == 'NO_MILITARY_SIGNAL': flags.append('LIKELY_FALSE_POSITIVE_KEYWORD')
        if cls == 'CAPF_OR_OTHER_FORCE_LEAD': flags.append('CHECK_SERVICE_IS_ARMED_FORCES')
        kw = set()
        for x in rs:
            kw |= set(((x.get('relevance') or {}).get('keywords') or {}).keys())
        # The intern's pipeline/judgments.py counts 'invalided' also on \binvalidation\b and 'armed forces tribunal'
        # also on a capitalised \bAFT\b (kept: a legitimate abbreviation). Re-count the intern keyword set WITHOUT 'invalidation'.
        if kw and intern_rel in ('relevant', 'borderline'):
            narrow = INTERN_NARROW.findall(re.sub(r'\s+', ' ', txt))
            if not narrow:
                flags.append('INTERN_HIT_ONLY_VIA_INVALIDATION')
                stats['intern_hit_only_broad_alt'] += 1
                if intern_rel == 'relevant': stats['intern_relevant_only_broad_alt'] += 1
        if len(dates) > 1: flags.append('DATE_DISAGREES_ACROSS_RECORDS')
        specs = sorted({k for x in rs for k in doc2spec.get(x['doc_id'], [])})
        c53 = sorted({spec_by_key[k][1] for k in specs if spec_by_key[k][1]})
        if cls in ('MIL_CORE_LEXICAL', 'MIL_PROBABLE_LEXICAL') or specs:
            include = 'INCLUDE'
        elif cls in ('WEAK_SIGNAL_REVIEW', 'CAPF_OR_OTHER_FORCE_LEAD', 'TEXT_UNAVAILABLE'):
            include = 'HOLD_FOR_REVIEW'
        elif intern_rel in ('relevant', 'not_checked'):
            include = 'HOLD_FOR_REVIEW'; flags.append('INTERN_WS_B_DISAGREE')
        else:
            include = 'EXCLUDE_PROPOSED'
        stats['documents'] += 1; stats['records'] += len(rs); stats['class:' + cls] += 1; stats['decision:' + include] += 1
        cls_by_court[r0['court']][include] += 1
        intern_vs_ws[(intern_rel, include)] += 1
        rows.append([
            f'WSB-INT-{i:05d}', sha, len(rs), j(x['doc_id'] for x in rs), r0['court'], r0['source_record']['system'],
            j(sorted({x['source_record']['record_id'] for x in rs})), r0['source_url'], r0.get('raw_path') or '',
            j(dates), j(casenos), r0['title'][:200], j(ncs), j(reps), r0.get('page_count') or '',
            r0.get('text_method') or '', r0.get('text_quality') or '', intern_rel, s, w, sv, cp, cls, include, dup_kind,
            j(other_sha), j(flags), j(specs), j(c53),
            'OFFICIAL_JUDICIAL_DECISION', 'THIRD_PARTY_ARCHIVAL_FACSIMILE', 'HASH_ONLY', 'NOT_APPLICABLE',
            'AWS Open Data mirror (CC-BY-4.0) of ' + ('SC e-SCR reports (SCR copy incl. editorial headnote)' if r0['source'] == 'sci' else 'eCourts HC judgment PDFs') +
            '; byte parity with the court-hosted copy NOT checked; intern raw sha256 = hash of mirror bytes only'])
    hdr = ['intake_id', 'sha256', 'n_intern_records', 'intern_doc_ids', 'court', 'source_system', 'source_record_ids',
           'carrier_url', 'intern_raw_path', 'decision_dates', 'case_numbers', 'title_as_in_intern_meta', 'neutral_citations',
           'reported_citations', 'page_count', 'text_method', 'text_quality', 'intern_relevance', 'ws_b_strong_hits',
           'ws_b_weak_hits', 'ws_b_service_context_hits', 'ws_b_capf_marker_hits', 'ws_b_lexical_class', 'ws_b_intake_decision',
           'duplicate_kind', 'same_neutral_citation_other_sha256', 'flags', 'ws_b_identity_spec_keys', 'case53_ids',
           'document_authority', 'carrier_provenance', 'copy_fidelity', 'amendment_chain_status', 'authority_rationale']
    write_csv(os.path.join(WS, 'intake_manifest.csv'), hdr, rows)

    # excluded log: count and spot-check of cases relevant to WS-B that the intern filter removed
    ex_path = os.path.join(snap, 'data/excluded_judgments.jsonl')
    excluded = []
    if os.path.exists(ex_path):
        with open(ex_path, encoding='utf-8') as f:
            excluded = [json.loads(l) for l in f if l.strip()]

    # ---------- 2. identity resolution
    cases = {}
    with open(CASES53, encoding='utf-8') as f:
        for l in f:
            c = json.loads(l); cases[c['id']] = c
    held = {}
    with open(os.path.join(HERE, 'held_copies.csv'), encoding='utf-8') as f:
        for h in csv.DictReader(f):
            held.setdefault(h['spec_key'], []).append(h)
    codes = list(csv.DictReader(open(CODES, encoding='utf-8')))
    code_by = {c['code']: c for c in codes}

    id_rows = []
    for key, cid, label, rx, date, nc, spec_codes in SPECS:
        c = cases.get(cid, {})
        m = MATCHES.get(key, {'doc_ids': [], 'method': 'NO_MATCH_FOUND', 'note': ''})
        ir = [by_doc[d] for d in m['doc_ids'] if d in by_doc]
        isha = j(sorted({r['sha256'] for r in ir}))
        idate = j(sorted({r['issue_date'] for r in ir}))
        inc = j(sorted({r.get('neutral_citation') or '' for r in ir}))
        irep = j(sorted({x for r in ir for x in r.get('reported_citations') or []}))
        icase = j(sorted({x for r in ir for x in r.get('case_numbers') or []}))
        ijudges = j(sorted({x for r in ir for x in r.get('judges') or []}))
        iparties = j(sorted({' / '.join([';'.join(r['parties'].get('petitioner', [])), ';'.join(r['parties'].get('respondent', []))]) for r in ir}))
        hc = held.get(key, [])
        hurl = j(h['official_url'] for h in hc); hsha = j(h['sha256'] for h in hc); hprov = j(h['carrier_provenance'] for h in hc)
        reg_urls = j(sorted({code_by[k]['official_corroboration_url'] for k in spec_codes if k in code_by and code_by[k]['official_corroboration_url']}))
        reg_sha = j(sorted({code_by[k]['official_sha256'] for k in spec_codes if k in code_by and code_by[k]['official_sha256']}))
        ex_hits = [e for e in excluded if re.search(rx, e.get('title', ''), re.I) and (not date or e.get('decided') == date)
                   and (('HC' in label) != (e.get('court', '').startswith('Supreme')))]
        ex_note = j(f"{e['decided']}|{e['sha256'][:16]}|{e['title'][:60]}" for e in ex_hits[:3])
        # comparisons
        disc = []
        cdate = c.get('decision_date', '') or ''
        if cid and cdate and idate and cdate != idate: disc.append(f'DATE curated {cdate} vs intern {idate}')
        if cid and not cdate and idate: disc.append(f'curated date missing; intern copy gives {idate}')
        if cid and not cdate and not idate and date: disc.append(f'curated date missing; spec date {date}')
        if date and idate and date not in idate.split(';'): disc.append(f'DATE spec {date} vs intern {idate}')
        if cid and c.get('primary_source_url', '').startswith('https://indiankanoon'): disc.append('curated primary_source_url is a commercial database (Indian Kanoon) - not evidence')
        official_in_hand = bool(hc and any(h['carrier_provenance'] in ('ISSUING_AUTHORITY',) for h in hc))
        if official_in_hand and ir:
            state = 'IDENTITY_CORROBORATED_OFFICIAL_COPY_HELD_AND_INTERN_COPY'
        elif official_in_hand:
            state = 'IDENTITY_CORROBORATED_OFFICIAL_COPY_HELD_NOT_IN_INTERN'
        elif ir and m['method'].startswith('COVER'):
            state = 'IDENTITY_CORROBORATED_INTERN_MIRROR_ONLY'
        elif ir:
            state = 'IDENTITY_LEAD_INTERN_METADATA_ONLY'
        elif hc:
            state = 'THIRD_PARTY_COPY_ONLY'
        elif 'conflict A-C2' in C2.get(key, '') and not ir and not hc:
            state = 'CITATION_METADATA_CONFLICTS_WITH_OFFICIAL_RECORD_NO_COPY'
        elif ('(official)' in C2.get(key, '') or C2.get(key, '').startswith('OR-')):
            state = 'CITATION_METADATA_CORROBORATED_BY_OFFICIAL_RECORD_NO_COPY'
        else:
            state = 'UNRESOLVED_NO_COPY_IN_HAND'
        id_rows.append([key, cid, label, c.get('title', ''), c.get('court', '') or ('High Court' if 'HC' in label else 'Supreme Court of India'),
                        cdate, c.get('case_number', ''), c.get('reporter_citation', ''), c.get('primary_source_url', ''),
                        date, nc, j(spec_codes), j(m['doc_ids']), isha, idate, icase, inc, irep, ijudges, iparties[:300],
                        m['method'], hurl, hsha, hprov, reg_urls, reg_sha, ex_note, state, j(disc), m.get('note', ''), C2.get(key, '')])
    id_hdr = ['spec_key', 'case53_id', 'ws_b_label', 'curated_title', 'curated_court', 'curated_decision_date', 'curated_case_number',
              'curated_reporter_citation', 'curated_primary_source_url', 'expected_date_spec', 'expected_neutral_citation_spec',
              'kb_source_codes', 'intern_doc_ids', 'intern_sha256', 'intern_decision_date', 'intern_case_numbers',
              'intern_neutral_citation', 'intern_reported_citations', 'intern_judges', 'intern_parties', 'match_method',
              'held_copy_url', 'held_copy_sha256', 'held_copy_carrier_provenance', 'register_official_url', 'register_official_sha256',
              'intern_excluded_log_hits', 'identity_state', 'discrepancies', 'note', 'cycle2_identity_evidence']
    write_csv(os.path.join(WS, 'identity_resolution.csv'), id_hdr, id_rows)

    # ---------- 3. crosswalk 53 cases / specs <-> KB 658
    kb = []
    with open(KB658, encoding='utf-8') as f:
        for l in f:
            kb.append(json.loads(l))
    code_to_spec = collections.defaultdict(set)
    for key, cid, label, rx, date, nc, spec_codes in SPECS:
        for cd in spec_codes:
            code_to_spec[cd].add(key)
    xw = []
    for key, cid, label, rx, date, nc, spec_codes in SPECS:
        m = MATCHES.get(key, {'doc_ids': []})
        idrow = next(r for r in id_rows if r[0] == key)
        links = collections.OrderedDict()
        for cd in spec_codes:
            if cd in code_by:
                for rid in code_by[cd]['records_using'].split(';'):
                    if rid:
                        links.setdefault(rid, set()).add('REGISTER_CODE:' + cd)
        name_rx = re.compile(rx, re.I)
        for r in kb:
            blob = r['title'] + ' ' + r['body'] + ' ' + r['references']
            if name_rx.search(blob):
                links.setdefault(r['id'], set()).add('LEXICAL_NAME_MATCH')
        if not links:
            xw.append([key, cid, label, '', '', 'NO_KB_LINK_FOUND', j(m['doc_ids']), idrow[13], idrow[21], idrow[22], idrow[27],
                       'Absence of a lexical/code link is not proof that no KB record relies on this case.'])
        for rid, kinds in links.items():
            kbr = next((x for x in kb if x['id'] == rid), None)
            strength = 'CURATION_DECLARED_SOURCE_CODE' if any(k.startswith('REGISTER_CODE') for k in kinds) else 'LEXICAL_LEAD_ONLY'
            if strength == 'LEXICAL_LEAD_ONLY' and sum(1 for s_ in SPECS if s_[3] == rx) > 1:
                strength = 'LEXICAL_LEAD_AMBIGUOUS_SAME_PARTY_PATTERN'
            xw.append([key, cid, label, rid, (kbr['title'][:120] if kbr else 'KB ID NOT FOUND'), strength + ':' + '|'.join(sorted(kinds)),
                       j(m['doc_ids']), idrow[13], idrow[21], idrow[22], idrow[27],
                       LINK_NOTES.get((key, rid), 'Link proposes that the KB record relies on/mentions this judgment; proposition-level support NOT verified.')])
    # OQ-D-008: per-case53 link counts and empty-holding citability flag
    n_code = collections.Counter(); n_lex = collections.Counter()
    for r in xw:
        if r[3]:
            (n_code if r[5].startswith('CURATION_DECLARED') else n_lex)[r[0]] += 1
    for r in xw:
        c = cases.get(r[1], {})
        empty = bool(r[1]) and not (c.get('holding') or '').strip()
        cls_ = c.get('case_class') or c.get('record_type') or ''
        cite = ('NOT_CITABLE_AS_AUTHORITY_HOLDING_EMPTY' if empty else 'HOLDING_PRESENT_UNVERIFIED') if r[1] else 'NOT_IN_CASES53'
        r.extend([n_code[r[0]], n_lex[r[0]], 'YES' if empty else ('NO' if r[1] else ''), cls_, cite])
    xw_hdr = ['spec_key', 'case53_id', 'ws_b_label', 'kb_record_id', 'kb_title', 'link_basis', 'intern_doc_ids', 'intern_sha256',
              'held_copy_url', 'held_copy_sha256', 'identity_state', 'caveat', 'spec_code_declared_kb_links', 'spec_lexical_kb_links',
              'case53_holding_empty', 'case53_class', 'citability_flag']
    case53_nolink = sorted({r[1] for r in xw if r[1] and n_code[r[0]] == 0})
    case53_nolink_any = sorted({r[1] for r in xw if r[1] and n_code[r[0]] == 0 and n_lex[r[0]] == 0})
    stats['case53_without_code_declared_kb_link'] = len(case53_nolink)
    stats['case53_without_any_kb_link'] = len(case53_nolink_any)
    stats['case53_holding_empty'] = sum(1 for c in cases.values() if not (c.get('holding') or '').strip())
    write_csv(os.path.join(WS, 'crosswalk_cases53_kb658.csv'), xw_hdr, xw)

    # ---------- 4. stats
    st = {
        'raw_data_commit': a.raw_data_commit,
        'intern_meta_records_total': len(recs),
        'intern_judgment_records': len(judg),
        'intern_judgment_records_by_court': dict(collections.Counter(r['court'] for r in judg)),
        'intern_relevance_by_record': dict(collections.Counter((r.get('relevance') or {}).get('status') for r in judg)),
        'distinct_judgment_documents_sha256': stats['documents'],
        'records_collapsed_as_same_bytes': stats['records'] - stats['documents'],
        'ws_b_lexical_class_by_document': {k[6:]: v for k, v in stats.items() if k.startswith('class:')},
        'ws_b_intake_decision_by_document': {k[9:]: v for k, v in stats.items() if k.startswith('decision:')},
        'ws_b_decision_by_court': {k: dict(v) for k, v in cls_by_court.items()},
        'intern_relevance_vs_ws_b_decision': {f'{a_}|{b_}': v for (a_, b_), v in sorted(intern_vs_ws.items())},
        'excluded_log_lines': len(excluded),
        'docs_intern_kept_only_via_word_invalidation': stats['intern_hit_only_broad_alt'],
        'docs_intern_relevant_only_via_word_invalidation': stats['intern_relevant_only_broad_alt'],
        'identity_specs': len(SPECS),
        'identity_state_counts': dict(collections.Counter(r[27] for r in id_rows)),
        'case53_identity_state_counts': dict(collections.Counter(r[27] for r in id_rows if r[1])),
        'crosswalk_rows': len(xw),
        'case53_without_code_declared_kb_link': stats['case53_without_code_declared_kb_link'],
        'case53_without_any_kb_link_ws_b': stats['case53_without_any_kb_link'],
        'case53_holding_empty': stats['case53_holding_empty'],
        'case53_mapped_to_intern_doc': sum(1 for r in id_rows if r[1] and r[12]),
        'crosswalk_basis_counts': dict(collections.Counter(r[5].split(':')[0] for r in xw)),
        'cases53_sha256': CASES53_SHA, 'records658_sha256': KB658_SHA,
    }
    with open(os.path.join(WS, 'intake_stats.json'), 'w') as f:
        json.dump(st, f, indent=1, sort_keys=True)
    print(json.dumps(st, indent=1, sort_keys=True))

if __name__ == '__main__':
    main()
