#!/usr/bin/env python3
"""Cycle 2: audit of the intern relevance filter against every case cited by the KB 658, the curated 53 and the
87-code register (the WS-B identity specs), plus the 'invalidation' false-positive class.

Reads identity_resolution.csv and intake_manifest.csv (built by build_registers.py) and the intern snapshot.
Writes intern_filter_audit.csv, allow_list_proposed.csv, intern_invalidation_false_positives.csv.
PROPOSAL ONLY: the intern corpus is not changed.
Usage: python3 cycle2_filter_audit.py --snapshot <dir>
"""
import argparse, csv, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); WS = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from case_specs import SPECS  # noqa: E402

# Expected relevance (WS-B judgment from the curated topic / KB context / official copies read; a reason, not a ruling)
MIL = 'MILITARY_LAW_CORE'
EXP = {k: MIL for k in [s[0] for s in SPECS]}
EXP.update({
 'CHANDRA_KUMAR': 'TRIBUNAL_JURISDICTION_GENERAL (relied on for AFT/Art.226 by KB V7-JD-01 and by Parashotam para 32)',
 'ROJER': 'TRIBUNAL_JURISDICTION_GENERAL (relied on by Parashotam para 32)',
 'ANVAR': 'EVIDENCE_GENERAL (KB V9 electronic evidence)', 'ARJUN': 'EVIDENCE_GENERAL (KB V9)',
 'NAVJOT': 'EVIDENCE_GENERAL (KB V9; P0 case)', 'SHAFHI': 'EVIDENCE_GENERAL (KB V9; overruled)',
 'PRAFUL': 'EVIDENCE_GENERAL (video-conference witness)', 'SONU': 'EVIDENCE_GENERAL (KB V9-JD-03)',
 'DHINGRA_SR': 'CIVIL_COMPARATOR (Railways; P0 quarantined lead)', 'SUKHDEV': 'CIVIL_COMPARATOR (civilian ACR; KB ADM-015 distinguishes it)',
 'BALBIR': 'MILITARY_CRIMINAL_JURISDICTION (Army Act ss.125-126 interplay, per Jasbir para 35)',
 'ADG_CBI': 'MILITARY_CRIMINAL_JURISDICTION (per Jasbir para 36)',
 'JOGINDER_HP': 'MILITARY_CRIMINAL_JURISDICTION (1978 Rules notice, per Jasbir paras 29-31)',
 'INSC_2023_985': 'UNIDENTIFIED (cited in KB ADM-027 promotion review)', 'INSC_2026_281': 'UNIDENTIFIED (cited in KB ADM-027)',
})
# Removals confirmed by date + party on the excluded log (others' excluded-log name hits are not the same case or unverified)
REMOVED_CONFIRMED = {'CHANDRA_KUMAR': 'exact date 1997-03-18 and parties', 'DHINGRA_SR': 'exact date 2007-12-14 and parties',
                     'SUKHDEV': 'date 2013-04-23 and parties (identity with KB citation is a lead)',
                     'NITISHA_MA': 'date 2023-11-03 and parties (MA number not seen; lead)'}
UNREPORTED_ORDER = {'VIRENDRA': 'official copy p.1 marked Non-Reportable', 'RAVINDER': 'curated source is a bosir order PDF', 'RAM_AVTAR': 'order of 10.12.2014 (office report)',
                    'MANI_RAM': 'order of 11.02.2016 (office report)', 'GIRISH_CLAR': 'clarification order', 'RANJIT_REVIEW': 'review order'}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--snapshot', required=True); a = ap.parse_args()
    meta = os.path.join(a.snapshot, 'data/meta')
    idr = {r['spec_key']: r for r in csv.DictReader(open(os.path.join(WS, 'identity_resolution.csv'), encoding='utf-8'))}
    out = []
    allow = []
    for key, cid, label, rx, date, nc, codes in SPECS:
        r = idr[key]; exp = EXP[key]
        docs = [d for d in r['intern_doc_ids'].split(';') if d]
        rel = sorted({(json.load(open(os.path.join(meta, d + '.json'))).get('relevance') or {}).get('status', '') for d in docs})
        kw = sorted({k for d in docs for k in ((json.load(open(os.path.join(meta, d + '.json'))).get('relevance') or {}).get('keywords') or {})})
        court = 'HC' if 'HC' in label else 'SC'
        if docs:
            status = 'KEPT'; ilabel = '|'.join(rel)
            assess = 'CORRECT_KEEP' if rel == ['relevant'] else ('KEPT_BUT_LABEL_BORDERLINE' if 'borderline' in rel else 'KEPT_OTHER_LABEL')
            evidence = f"intern doc {';'.join(docs)} sha {r['intern_sha256'][:16]}...; intern keywords {','.join(kw)}"
        elif key in REMOVED_CONFIRMED:
            status = 'REMOVED_BY_INTERN_FILTER'; ilabel = 'rejected (no military keyword)'
            if exp.startswith('MILITARY'):
                assess = 'INCORRECT_EXCLUSION_PROBABLE (removed text not read by WS-B; relevance from parties/KB topic)'
            elif exp.startswith('TRIBUNAL'):
                assess = 'EXCLUSION_CONFLICTS_WITH_KB_RELIANCE (no military keyword but relied on for AFT jurisdiction)'
            else:
                assess = 'EXCLUSION_CONSISTENT_WITH_FILTER_BUT_KB_CITED'
            evidence = f"excluded_judgments.jsonl: {r['intern_excluded_log_hits']} ({REMOVED_CONFIRMED[key]})"
        else:
            status = 'ABSENT_FROM_INTAKE'; ilabel = ''
            if key in UNREPORTED_ORDER and court == 'SC':
                assess = 'ABSENT_LIKELY_UNREPORTED_ORDER (SC bucket mirrors e-SCR reported judgments)'
            elif court == 'SC' and (date[:4] in ('2025', '2026')):
                assess = 'ABSENT_RECENT_COVERAGE_GAP (intern holds 8 SC documents dated 2025-2026)'
            elif court == 'SC':
                assess = 'ABSENT_UNDETERMINED (not pre-selected, not in bucket, or failed download - not determinable from the corpus)'
            else:
                assess = 'ABSENT_UNDETERMINED_HC'
            evidence = ('excluded-log name hits not the same case or unverified: ' + r['intern_excluded_log_hits']) if r['intern_excluded_log_hits'] else 'no kept record and no confirmed excluded-log entry'
        out.append([key, cid, label, court, exp, status, ilabel, assess, evidence, r['identity_state'], r['kb_source_codes'],
                    'FOR_INDEPENDENT_COORDINATOR_CHECK' if assess.startswith(('INCORRECT', 'EXCLUSION_CONFLICTS')) else ''])
        if status != 'KEPT' or assess != 'CORRECT_KEEP':
            allow.append([key, cid, label, court, r['curated_decision_date'] or r['expected_date_spec'] or r['intern_decision_date'],
                          r['curated_case_number'] or r['intern_case_numbers'], r['curated_reporter_citation'] or r['intern_reported_citations'],
                          exp, status, 'ALLOW_LIST_REGARDLESS_OF_KEYWORDS' if status != 'KEPT' else 'RELABEL_RELEVANT_PROPOSED',
                          'PROPOSAL_ONLY_INTERN_CORPUS_UNCHANGED'])
    hdr = ['spec_key', 'case53_id', 'case', 'court', 'expected_relevance_reason', 'intern_status', 'intern_label', 'assessment',
           'evidence', 'ws_b_identity_state', 'kb_source_codes', 'check_flag']
    w(os.path.join(WS, 'intern_filter_audit.csv'), hdr, out)
    w(os.path.join(WS, 'allow_list_proposed.csv'),
      ['spec_key', 'case53_id', 'case', 'court', 'decision_date', 'case_number', 'citation', 'reason', 'intern_status', 'proposal', 'state'], allow)
    # invalidation false-positive class
    fp = []
    for r in csv.DictReader(open(os.path.join(WS, 'intake_manifest.csv'), encoding='utf-8')):
        if 'INTERN_HIT_ONLY_VIA_INVALIDATION' in r['flags']:
            fp.append([r['intake_id'], r['sha256'], r['intern_doc_ids'].split(';')[0], r['n_intern_records'], r['court'],
                       r['decision_dates'], r['title_as_in_intern_meta'][:120], r['intern_relevance'], r['ws_b_lexical_class'],
                       r['ws_b_intake_decision']])
    w(os.path.join(WS, 'intern_invalidation_false_positives.csv'),
      ['intake_id', 'sha256', 'first_doc_id', 'n_records', 'court', 'date', 'title', 'intern_relevance', 'ws_b_lexical_class',
       'ws_b_intake_decision'], fp)
    import collections
    print('audit', len(out), collections.Counter(x[7].split(' ')[0] for x in out))
    st = os.path.join(WS, 'intake_stats.json'); d = json.load(open(st))
    d['cycle2_filter_audit_counts'] = dict(collections.Counter(x[7].split(' ')[0] for x in out))
    d['cycle2_filter_audit_denominator'] = len(out); d['cycle2_allow_list_rows'] = len(allow); d['cycle2_invalidation_false_positive_docs'] = len(fp)
    json.dump(d, open(st, 'w'), indent=1, sort_keys=True); print('allow', len(allow)); print('fp', len(fp))

def w(p, h, rows):
    with open(p, 'w', newline='', encoding='utf-8') as f:
        c = csv.writer(f, lineterminator='\n'); c.writerow(h)
        for r in rows:
            assert len(r) == len(h); c.writerow(r)

if __name__ == '__main__':
    main()
