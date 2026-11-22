#!/usr/bin/env python3
"""WS-B cycle 3 registers (new *_cycle3 files; prior files are not rewritten).

Inputs: identity_resolution.csv, crosswalk_cases53_kb658.csv (cycle 1-2 outputs), the intern snapshot (read-only
extraction of origin/raw-data), the cycle-3 citation scan JSON, the WS-C coverage inventory (from
origin/claude/integration-cycle2), the cycle-3 network log. Hand-reviewed rows are in this file.
Usage: python3 cycle3_registers.py --snapshot <dir> --citescan <json> --wsc-inventory <csv> --netlog <tsv>
All rows are proposals; legal-advisor and JAG states are NOT_STARTED.
"""
import argparse, csv, json, os, re, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__)); WS = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import manual_registers as M  # noqa: E402  (C, CASE, REND dictionaries; cycle 1-2 data)
from case_specs import SPECS  # noqa: E402

SPEC = {s[0]: s for s in SPECS}
CID2SPEC = {s[1]: s[0] for s in SPECS if s[1]}

OR_A = 'https://api.sci.gov.in/officereport/2022/10779/10779_2022_2022-07-22_916.html (sha256 93c2c26c...)'
REND3 = {
 ('NAGA', '53'): '8f27eb6c0a2ef613ecb20d5f0c0a5e71040630d03e23fca6004092934e4b8bed',
 ('NAGA', '54'): '5d655faee79210a66f3a320164552d1eaea498a9c75d842c5ae7606673064435',
 ('RANJIT', '6'): '9df4dc5388e74607ce189f4a422061194746b2d0750b8371e96bf04a2284f9c0',
 ('MULLIKOTE', '26'): '399364540e07761a7dc636a1a365e16f8ea4a46fd4e128f1c6594f1da6128305',
 ('MULLIKOTE', '31'): '1f23da6a64491440634cd844c4471b6cdf9fdeb524838b76c812e69ede4e74b1',
 ('GIRISH_MAIN', '10'): 'cb6de66b0d4d30ed45b4b0d79f747f9f60db2be613b2b980aea979b048f23d8e',
}

# rows whose anchor quote lies on a page of the range that was NOT rendered (avoid claiming a page image)
ANCHOR_NOT_IMAGED = {('MULLIKOTE', '39, 41'), ('MULLIKOTE', '43')}

# ------------------------------------------------------------------ task 3: holdings (cycle 3)
H3 = [
 ('NAGA','51-52','conclusions (1)-(6)','HOLDING_ON_MIRROR','AFSPA 1958 within Parliament\'s competence (Entry 2/2A List I); deployment is "in aid of the civil power", which continues to function; the Act does not supplant civil power and is not colourable legislation.','The Central Act does not displace the civil power of the State by the armed forces of the Union','CURATED_CONSISTENT (curated: constitutionality upheld subject to safeguards)','V8-S15 users','MIRROR (SCR via AWS). Constitution Bench.'),
 ('NAGA','52-53','conclusions (7)-(8)','HOLDING_ON_MIRROR','s.3 declaration of "disturbed area" requires a grave law-and-order situation; it must be for a limited duration with periodic review before the expiry of six months.','A declaration under Section 3 has to be for a limited duration and there should be periodic review of the declaration before the expiry of six months.','CURATED_CONSISTENT','V8-S15 users','Page image p.53 checked (start of p.53 completes "of six months"). Six-month figure is consequential - FOR INDEPENDENT COORDINATOR CHECK.'),
 ('NAGA','53','conclusions (13)-(16)','HOLDING_ON_MIRROR','Powers under s.4(a)-(d) and s.5 (including for NCOs) not violative of Arts.14, 19, 21; minimal force under s.4(a); arrested person handed to nearest police station with least possible delay for production before a magistrate within 24 hours excluding journey time; seized property handed over with a report.','should be handed over to the officer-in-charge of the nearest police station with least possible delay so that he can be produced before nearest magistrate within 24 hours','CURATED_CONSISTENT','V8-S15 users','Page image p.53 checked. Numbers/conditions consequential - FOR INDEPENDENT COORDINATOR CHECK. CrPC references now BNSS 2023.'),
 ('NAGA','54','conclusions (17)-(21)','HOLDING_ON_MIRROR','CrPC search-and-seizure provisions to be followed; s.6 sanction discretion not arbitrary but reasons must be given; "Do\'s and Don\'ts" binding and to be amended; complaints of misuse to be inquired into, with compensation and sanction where allegations found correct.','the Central Government shall pass an order giving reasons','CURATED_CONSISTENT','V8-S15 users','Page image p.54 checked. FOR INDEPENDENT COORDINATOR CHECK.'),
 ('NAGA','55','result','DISPOSITION_ON_MIRROR','CAs 721-24/1985 (Delhi HC) dismissed; CAs 2173-76/1991 allowed to the extent indicated; CA 2551/1991 dismissed; writ petitions disposed of.','Appeals/Petitions disposed','CURATED_CONSISTENT','V8-S15 users','Text layer of mirror.'),
 ('MANJEET','24-26','22-23','RATIO_ON_MIRROR','Under Entitlement Rules r.14(b) the Medical Board must record reasons why a disease could not be detected at entry; absent reasons the claimant gets the statutory inference; primacy of Board opinion does not relieve it of the obligation to record reasons.','ought to have been obligatorily recorded by the Medical Board sans whereof, the respondent would be entitled to the benefit of the statutory inference','CURATED_HOLDING_EMPTY (proposal fills gap)','PEN-*','MIRROR only. 1982 rules; see Isaac 2026 39(ii)-(iii).'),
 ('ANGAD','15-16','16','RATIO_ON_MIRROR','No note at entry: presumption of sound health (Rule 5(a)); deterioration presumed due to service (Rule 5(b)); recording a NANA conclusion without reasons shows lack of application of mind; Board view not upheld.','simply recording a conclusion that the disability was not attributable to service, without giving a reason','CURATED_HOLDING_EMPTY (proposal fills gap)','PEN-*','MIRROR only. IAF regulation (A-07).'),
 ('KESHAR','7-8','8-10','RATIO_ON_MIRROR','Relying on Baljit Singh (1996) 11 SCC 315 and Dhir Singh China (2003) 2 SCC 382: where the Medical Board opinion that the illness was not attributable to service has not been assailed, it must be accepted.','The opinion of the Medical Board has not been assailed in this proceeding and, therefore, must be accepted.','CURATED_HOLDING_EMPTY (proposal fills gap)','PEN-*','MIRROR only; quotation within Keshar of Dhir Singh China para 7. Pre-Dharamvir line; Isaac 2026 does not name Keshar.'),
 ('MULLIKOTE','21-22','33','RATIO','Condonation of shortfall in qualifying service up to 12 months is specifically provided in para 125 Pension Regulations 1961 and para 44 Pension Regulations 2008.','The condonation of shortfall of qualifying service up to twelve (12) months is specifically provided','CURATED_CONSISTENT (curated pinpoint 33-44 = CORRECTED version)','PEN-J-07;PEN-046','CORRECTED version (pp.1-31). Text layer. Para 125 text as quoted says "upto six months"; para 44 says 12 months - the Court\'s statement of "twelve (12) months" for both should be read with the quoted text (FOR INDEPENDENT COORDINATOR CHECK).'),
 ('MULLIKOTE','24-26','39, 41','HOLDING','No inconsistency between condonation provisions and DSC provisions; DSC respondents entitled to condonation of shortfall up to one year after determining qualifying service under paras 9/18 and Note 5 of letter 30.10.1987.','this Court holds that the Respondents are entitled to condonation of shortfall in qualifying service up to one (1) year','CURATED_CONSISTENT','PEN-J-07;PEN-046','Text layer.'),
 ('MULLIKOTE','26','42','HOLDING','Once the Pension Regulations provide for condonation, MoD/DESW cannot stipulate an exception by executive letters (20 June 2017, 22 March 2022); administrative fiat cannot amend clear Regulations.','it cannot, by administrative fiat, amend or override clear and categorical provisions of the Regulations','CURATED_CONSISTENT (curated: regulations cannot be overridden by executive letters)','PEN-J-07;PEN-046','Page image p.26 checked. FOR INDEPENDENT COORDINATOR CHECK.'),
 ('MULLIKOTE','26-27','43','COURT_OBSERVATION','Limitation (Tarsem Singh) not examined since not invoked; notes Girish Kumar reaffirmed pension as a vested right; question of law left open.','In any event, the said question of law is left open.','NOT_IN_CURATED','PEN-J-07;V7-JD-04','Text layer.'),
 ('MULLIKOTE','31','51','OPERATIVE_DISPOSITION','Appeals dismissed, no costs (CORRECTED version).','The Appeals are accordingly dismissed, with no order as to costs.','CURATED_CONSISTENT','PEN-J-07','Page image p.31 checked. Supersedes for citation purposes cycle-1 row WSB-H-030 which cites the second (uncorrected, renumbered) version pp.61-62 paras 97-99 (corrections_cycle3.csv CR-C3-01).'),
 ('GIRISH_MAIN','10-11','13-14','COURT_SUMMARY_OF_PRECEDENT','Ram Avtar (three judges, order 10.12.2014) dismissed 800+ Union appeals; personnel retiring on completion of tenure with disability attributable/aggravated are eligible for broad-banding; courts/tribunals directed to take note.','by an order dated 10.12.2014 dismissed more than 800 appeals filed by the Union of India','NOT_IN_CURATED','PEN-J-04;PEN-J-05;PEN-023;PEN-044','Page image p.10 checked. Official account of Ram Avtar (A-C2-01 identity support). FOR INDEPENDENT COORDINATOR CHECK (number of appeals).'),
 ('GIRISH_MAIN','11-12','15','RATIO','Pension is not bounty but deferred compensation and a vested right partaking of property; cannot be withheld except by authority of law; applies to disability pension.','Pension, as authoritatively settled by this Court, is neither a bounty nor an ex gratia payment','CONSISTENT','PEN-J-05','Text layer.'),
 ('PARASHOTAM','14-15','18-19','COURT_OBSERVATION','s.30 appeal to the SC is subject to s.31 (leave of AFT on a point of law of general public importance or SC leave); the appeal mechanism is restrictive.','There is, thus, no doubt that the appeal mechanism is restrictive in character','CURATED_NOT_STATED','V7-JD-03;AFT-*','Text layer. (PILOT-01 independent reviewer previously located paras 18-19 at p.14.)'),
 ('PARASHOTAM','15','20-21','PARTY_ARGUMENT','ASG sought exclusion of Art.226 review for CoI/court-martial/discipline, pension and service matters, Official Secrets Act and espionage cases.','Learned counsel sought embargo from the High Court exercising jurisdiction under Article 226','NOT_IN_CURATED','V7-JD-03;V7-WF-08','Argument rejected at paras 29-30 (WSB-H-014). Text layer.'),
 ('RANJIT','6','5-6 (SCR p.519-520)','HOLDING','Non-compliance with s.130 (right to object to members) goes to the root of jurisdiction and vitiates the court-martial proceedings; test of real likelihood of bias is whether a reasonable person with the information would think bias likely.','the non-compliance of the mandate of section 130 is an infirmity which goes to the root of the jurisdiction and without more, vitiates the proceedings','CURATED_CONSISTENT','KB-016;KB-027;CM-JD-01','Page image p.6 checked. Follows PPS Bedi (AIR 1982 SC 1413). FOR INDEPENDENT COORDINATOR CHECK.'),
 ('MANI_RAM','','','NO_COPY_IN_HAND','No WS-B-held copy; identity metadata only (office report OR-A). Holding cannot be proposed.','','CURATED_HOLDING_EMPTY','PEN-*','PQ-002 / PQ-C2-07.'),
 ('DHINGRA_SR','','','NO_COPY_IN_HAND','Civilian/Railways comparator; intern removed the mirror copy (excluded log). Holding cannot be proposed.','','CURATED_HOLDING_EMPTY (QUARANTINED_COMPARATIVE_LEAD)','—','PQ-003.'),
]

def holdings3():
    C = dict(M.C); CASE = dict(M.CASE); REND = dict(M.REND); REND.update(REND3)
    hdr = ['row_id','spec_key','case53_id','judgment','decision_date','copy_url','copy_sha256','copy_role','carrier_provenance',
           'wording_read_from','page_render_sha256','pdf_page','para_pinpoint','passage_type','ws_b_paraphrase','anchor_quote_verbatim',
           'comparison_with_curated','affected_kb_ids','uncertainty','technical_review_state','legal_advisor_state','jag_validation_state','cycle']
    rows = []
    for i, (k, pg, para, typ, ph, q, cmp_, kb, unc) in enumerate(H3, 1):
        url, sha, role = C.get(k, ('', '', 'NOT_HELD')); cid, name, d = CASE.get(k, (SPEC[k][1], SPEC[k][2], SPEC[k][4]))
        rsha = ''
        if pg and (k, para) not in ANCHOR_NOT_IMAGED:
            a_, _, b_ = pg.partition('-')
            for pp in ([str(x) for x in range(int(a_), int(b_) + 1)] if b_ else [a_]):
                if (k, pp) in REND:
                    rsha = REND[(k, pp)]; break
        prov = {'OFFICIAL_COURT_COPY': 'ISSUING_AUTHORITY', 'NOT_HELD': 'UNKNOWN'}.get(role, 'THIRD_PARTY_ARCHIVAL_FACSIMILE')
        read = 'PAGE_IMAGE' if rsha else ('PDF_TEXT_LAYER' if pg else 'NOT_READ')
        if not pg:
            ts = 'NOT_REVIEWED_NO_COPY'
        elif role == 'OFFICIAL_COURT_COPY':
            ts = 'PASSAGE_LOCATED_OFFICIAL_COPY' + ('_PAGE_IMAGE_CHECKED' if rsha else '_TEXT_LAYER')
        else:
            ts = 'PASSAGE_LOCATED_MIRROR_COPY_ONLY_NOT_OFFICIAL' + ('_MIRROR_PAGE_IMAGE' if rsha else '')
        rows.append([f'WSB-H3-{i:03d}', k, cid, name, d, url, sha, role, prov, read, rsha, pg, para, typ, ph, q, cmp_, kb, unc, ts,
                     'NOT_STARTED', 'NOT_STARTED', 'C3'])
    return hdr, rows

# ------------------------------------------------------------------ task 1: authoritative copies for mirror-only cases
# The 11 P0 cases of issue #4 (explicit list; the curated 'L' prefix is NOT a P0 marker - e.g. L06 Buttar is not P0)
P0_ISSUE4 = {'DCLR-SC-1964-A11', 'DCLR-SC-2005-L01', 'DCLR-SC-2015-L02', 'DCLR-SC-2015-L03', 'DCLR-SC-2016-L04', 'DCLR-SC-2008-L05',
             'DCLR-SC-1996-L07', 'DCLR-SC-2005-L08', 'DCLR-SC-2008-L09', 'DCLR-SC-2007-L10', 'DCLR-SC-1997-L11'}

def parse_netlog_line(line):
    """TSV written by the cycle-3 lookup loop: time, purpose, method, url, http_status, content_type,
    size_download, headers. Status and content type are SEPARATE fields."""
    p = line.rstrip('\n').split('\t')
    if len(p) < 5:
        return None
    return {'time': p[0], 'purpose': p[1], 'method': p[2], 'url': p[3], 'status': p[4].strip(),
            'content_type': (p[5].strip() if len(p) > 5 else ''), 'headers': (p[7].strip() if len(p) > 7 else '')}

def classify_head(status, content_type):
    """HTTP availability only. A responding URL is NOT a held copy and says nothing about the identity or
    authenticity of the bytes; acquisition remains a separate, approved step."""
    if status == '200' and content_type.split(';')[0].strip().lower() == 'application/pdf':
        return 'OFFICIAL_HOST_URL_RESPONDS_200_PDF (availability only; identity, authenticity and acquisition NOT established; bytes not held)'
    if status == '200':
        return 'OFFICIAL_HOST_URL_RESPONDS_200_NOT_PDF (content type ' + (content_type or 'unknown') + ')'
    return 'OFFICIAL_HOST_URL_HEAD_INCONCLUSIVE (HEAD ' + (status or '?') + '; HEAD 404 also returned for control URL whose bytes were previously obtained)'

def authoritative(netlog):
    head = {}
    for line in open(netlog, encoding='utf-8'):
        rec = parse_netlog_line(line)
        if rec and rec['purpose'] != 'CONTROL_DHARAMVIR':
            head[rec['purpose']] = rec
    ctrl = [l for l in open(netlog, encoding='utf-8') if 'CONTROL_DHARAMVIR' in l]
    ids = list(csv.DictReader(open(os.path.join(WS, 'identity_resolution.csv'), encoding='utf-8')))
    rows, pend = [], []
    diary = {'MANJEET': 'Diary 36581/2013 (OR-A)', 'ANGAD': 'Diary 35734/2011 (OR-A)'}
    for r in ids:
        if not r['case53_id'] or r['identity_state'] != 'IDENTITY_CORROBORATED_INTERN_MIRROR_ONLY':
            continue
        k = r['spec_key']; url = r['curated_primary_source_url']
        if k in head:
            h = head[k]
            st = classify_head(h['status'], h['content_type'])
            hres = f"{h['time']} HEAD status={h['status']} content_type={h['content_type']} {h['headers']}".strip()
        elif url:
            st, hres = 'OFFICIAL_HOST_URL_IN_CURATED_RECORD_NOT_CHECKED', ''
        else:
            st, hres = 'NO_OFFICIAL_URL_LOCATED', ''
        host_note = 'government-hosted SCR volume (s3waas.gov.in): an official report volume, not the court\'s judgment PDF' if 's3waas' in url else ''
        rows.append([k, r['case53_id'], r['ws_b_label'], r['intern_decision_date'], r['intern_sha256'], 'NO (no WS-B-held court copy)',
                     url, hres, st, diary.get(k, ''), host_note, 'C3'])
        pend.append([f'PQ-C3-{len(pend)+1:02d}', k, r['case53_id'], 'Supreme Court of India', r['intern_case_numbers'] or r['curated_case_number'],
                     r['intern_decision_date'], url or 'unknown',
                     'P0' if r['case53_id'] in P0_ISSUE4 else ('P1' if st.startswith('OFFICIAL_HOST_URL_RESPONDS_200_PDF') else 'P2'),
                     'Official court copy needed to replace mirror-only pinpoints; ' + (diary.get(k, '') or 'no diary number known'),
                     st.split(' (')[0], 'ACQUISITION_REQUEST_ONLY', 'NO', 'C3'])
    for k in ('GIRISH_CLAR', 'RAVINDER', 'PRAFUL', 'DHINGRA_SR', 'RANJIT_REVIEW'):
        r = next(x for x in ids if x['spec_key'] == k)
        pend.append([f'PQ-C3-{len(pend)+1:02d}', k, r['case53_id'], 'Supreme Court of India', r['curated_case_number'], r['curated_decision_date'],
                     r['curated_primary_source_url'] or 'unknown', 'P1', 'Unresolved after cycle 3 (identity_resolution_cycle3.csv)',
                     'NOT_CHECKED', 'ACQUISITION_REQUEST_ONLY', 'NO', 'C3'])
    h1 = ['spec_key', 'case53_id', 'case', 'decision_date', 'intern_mirror_sha256', 'official_copy_held', 'official_url_located',
          'read_only_lookup_result', 'state', 'official_record_corroboration', 'note', 'cycle']
    h2 = ['queue_id', 'spec_key', 'case53_id', 'court', 'case_number', 'decision_date', 'official_url_or_holder_if_known', 'priority', 'note',
          'official_url_http_check', 'action', 'downloaded_by_ws_b', 'cycle']
    return (h1, rows), (h2, pend), ctrl

# ------------------------------------------------------------------ task 2: identities
I3 = [
 ('GIRISH_CLAR','DCLR-SC-2026-008','UNRESOLVED','No official record reachable without CAPTCHA; not in intern corpus (2025-26 coverage gap); held texts do not cite it.','none','PQ-C3'),
 ('RAVINDER','DCLR-SC-2012-A05','CITATION_LEAD_FROM_LATER_JUDGMENT (not official copy)','Delhi HC W.P.(C) 3545/2025 (intern eCourts mirror hc-delhi-2025-w-p-c-3545-2025-dlhc010148412025-1-2025-03-27, p.43-44, fn21) cites "Union of India v Ravinder Kumar (2015) 12 SCC 291" and quotes it as following Jujhar Singh - consistent with curated SC order of 2012-05-23 (CA 1837/2009) but date/case number not printed there. Manjeet 2015 (intern mirror p.10, para 11) mentions a different Delhi HC LPA (SW) 212/2006 UoI v Ravinder Kumar.','LEAD','Curated bosir order URL not checked.'),
 ('PRAFUL','DCLR-SC-2003-A06','UNRESOLVED','Not in intern corpus or held texts (non-military evidence case).','none','PQ-C3'),
 ('DHINGRA_SR','DCLR-SC-2008-L05','UNCHANGED (excluded-log lead)','Intern removed the mirror copy 2007-12-14 (sha c42a5be2...).','LEAD','PQ-003'),
 ('RANJIT_REVIEW','DCLR-SC-1988-R02','UNRESOLVED','No held text cites (1989) 2 SCC 438; curated source is Indian Kanoon only.','none','PQ-012'),
 ('RAM_AVTAR','DCLR-SC-2014-A08','A-C2-01 RESOLUTION PROPOSED','Official Girish 2026 paras 13-14 (p.10, page image cb6de66b...) describe "Union of India and Others v. Ram Avtar" as a three-judge order of 10.12.2014 dismissing 800+ Union appeals on broad-banding; official office report OR-A gives C.A. 418/2012, Diary 21005/2011. The curated accessible_source_url (S P Rathore, Diary 33390/2018) is a later judgment describing Ram Avtar, not the order. Proposal: treat the curated URL as WRONG_DOCUMENT; identity = SC order 10.12.2014 in C.A. 418/2012 and connected. FOR INDEPENDENT COORDINATOR CHECK.','OFFICIAL_RECORD_CORROBORATED','PQ-017 / PQ-C2-07'),
 ('RAM_SARUP','DCLR-SC-1964-A11','A-C2-02 RESOLUTION PROPOSED','Official PPS Bedi JUDIS copy (sha 211dbaf4..., p.2, cases-referred list) prints "[1964] 5 SCR 931" (editorial list); intern SCR mirrors of PPS Bedi 1982, Babita 2020 and UoI 1992 also print "[1964] 5 SCR 931"; the 2003 SC judgment sc-2003-union-of-india-and-ors-2003insc274 (mirror) cites AIR (1965) SC 247 and EEVFAM 2016 (mirror) cites (1964) 5 SCR 931. Only official Jasbir fn18 prints "(1964) 4 SCR 931". Proposal: [1964] 5 SCR 931 (= AIR 1965 SC 247) with Jasbir fn18 as a probable typographical variant; final confirmation from the HF-held JUDIS copy (sha 88f84411...). FOR INDEPENDENT COORDINATOR CHECK.','MAJORITY_OF_COPIES_NOT_DECISIVE (policy: agreement is not authority)','Read HF copy'),
]

def identities3():
    hdr = ['spec_key', 'case53_id', 'cycle3_state', 'evidence', 'evidence_strength', 'next_action', 'technical_review_state',
           'legal_advisor_state', 'jag_validation_state', 'cycle']
    return hdr, [list(x) + ['PROPOSAL', 'NOT_STARTED', 'NOT_STARTED', 'C3'] for x in I3]

# ------------------------------------------------------------------ task 4: subsequent treatment
T3 = [
 ('PPS_BEDI','DCLR-SC-1982-001','s.130 objection procedure mandatory','RANJIT','6','5','FOLLOWED (relied on: "Prithvi Pal Singh v. Union of India, AIR 1982 SC 1413")','s.130 / bias','KB-016;CM-JD-01','Official copy, page image p.6.'),
 ('RAM_AVTAR','DCLR-SC-2014-A08','Broad-banding for personnel retiring with service-attributable disability','GIRISH_MAIN','10-11','13-14','DESCRIBED AND APPLIED (in rem, three judges)','Broad-banding arrears','PEN-J-04;PEN-J-05','Official copy, page image p.10.'),
 ('TARSEM;GIRISH_MAIN','DCLR-SC-2008-N10;DCLR-SC-2026-007','Limitation for continuing pension claims','MULLIKOTE','26-27','43','NOT_EXAMINED (Tarsem not invoked); Girish reaffirmation quoted; question left open','Limitation','V7-JD-04;PEN-J-05;PEN-J-07','Official copy (CORRECTED version), text layer.'),
 ('KESHAR;BALACHANDRAN;BALJIT','DCLR-SC-2007-L10;DCLR-SC-2005-L08;DCLR-SC-1996-L07','Board opinion not assailed must be accepted','KESHAR','7-8','8-10','FOLLOWED (Keshar follows Baljit and Dhir Singh China)','Board deference','PEN-*','Mirror copy.'),
]
SCAN_VALID = {  # spec -> regex that the citing snippet must also satisfy (filters same-name different cases)
 'MANJEET': r'Union of India', 'KESHAR': r'Union of India', 'VIRENDRA': r'Ex\.?\s*Sep|9267|2020', 'JASBIR': r'Sikkim',
 'PS_GILL': r'Union of India (?:&|and) (?:Ors|Others)\.? v\.? P\.\s?S\.\s?Gill', 'BALJIT': r'Union of India|1996',
 'SANTOSH_LOHAR': r'Lohar', 'MANI_RAM': r'Bh?aira',
}
# Citation leads whose page was checked on a page render of the intern mirror PDF (PR #26 review fix):
# (spec, intern doc_id) -> (printed reporter page, render sha256)
PRINTED_VERIFIED = {
 ('ANGAD', 'sc-2025-bijender-singh-2025insc549'): ('[2025] 4 SCR 1551', '93238c4136c34e921653856fb0b0f5f2da5ac251b11872555d00d093e16912f2'),
 ('BALACHANDRAN', 'sc-2009-secretary-ministry-of-defence-2009insc1059'): ('[2009] 13 (Addl.) SCR 418', '91b2cf981c258c1b9a30658cf9058592f1399b3aa93c2924098a54953bf46ccf'),
 ('NAVJOT', 'sc-2016-extra-judicial-execution-victi-2016insc527'): ('[2016] 4 SCR 919', '43bcea026ce7a76847742c4224a453785fd99df01eaeef7b5d826f10386667c8'),
}
P0 = {'NAVJOT','MANJEET','ANGAD','MANI_RAM','DHINGRA_SR','BALJIT','BALACHANDRAN','SURINDER_RATHORE','KESHAR','NAGA','RAM_SARUP'}

def treatment3(scan):
    C = M.C; CASE = M.CASE
    hdr = ['row_id','earlier_spec_keys','earlier_case53_ids','proposition','later_judgment','later_copy_url','later_copy_sha256','later_copy_role',
           'pdf_page','para','treatment','scope','affected_kb_ids','uncertainty','exhaustiveness','technical_review_state','legal_advisor_state',
           'jag_validation_state','cycle','printed_page_if_verified','page_render_sha256']
    rows = []
    for t in T3:
        later = t[3]; url, sha, role = C.get(later, ('', '', 'NOT_HELD'))
        rows.append([f'WSB-T3-{len(rows)+1:03d}', t[0], t[1], t[2], CASE.get(later, ('', later, ''))[1], url, sha, role, t[4], t[5], t[6], t[7], t[8], t[9],
                     'NOT_EXHAUSTIVE', 'PASSAGE_LOCATED_OFFICIAL_COPY' if role == 'OFFICIAL_COURT_COPY' else 'NOT_VERIFIED_ON_OFFICIAL_COPY',
                     'NOT_STARTED', 'NOT_STARTED', 'C3', '', ''])
    summary = []
    for k, hits in sorted(scan.items()):
        vrx = SCAN_VALID.get(k)
        kept = [h for h in hits if not vrx or re.search(vrx, h[4], re.I)]
        rej = len(hits) - len(kept)
        sc = [h for h in kept if h[2].startswith('Supreme')]
        hc = [h for h in kept if not h[2].startswith('Supreme')]
        for d, doc, court, pg, snip in sc:
            loc = 'SCR_HEADNOTE_OR_CASE_LIST_LIKELY (editorial label, not evidence of treatment)' if (int(pg) <= 4 and re.search(r'relied on|referred to|distinguished|followed|Case Law', snip, re.I)) else 'BODY_OR_UNCLASSIFIED'
            rows.append([f'WSB-T3-{len(rows)+1:03d}', k, SPEC[k][1], 'citation located by name scan', f'intern doc {doc} ({d})',
                         'https://indian-supreme-court-judgments.s3.ap-south-1.amazonaws.com (intern mirror)', '', 'INTERN_MIRROR_SCR',
                         (str(pg) if pg else ''), '', 'CITED_TREATMENT_NOT_CLASSIFIED', loc, '', re.sub(r'\s+', ' ', snip[100:300]),
                         'NOT_EXHAUSTIVE: name scan of intern corpus only; absence is not proof of no treatment',
                         'LEAD_ONLY', 'NOT_STARTED', 'NOT_STARTED', 'C3'] + list(PRINTED_VERIFIED.get((k, doc), ('', ''))))
        summary.append([k, SPEC[k][1], 'P0' if k in P0 else 'CALIBRATION_OR_KB', len(hits), rej, len(sc), len(hc),
                        'Counts are discovery leads only; no precedent strength is inferred from frequency.', 'C3'])
    return (hdr, rows), (['spec_key', 'case53_id', 'group', 'name_hits_total', 'rejected_same_name_other_case', 'sc_citing_docs',
                           'hc_citing_docs', 'caveat', 'cycle'], summary)

# ------------------------------------------------------------------ task 5: KB records flagged by WS-C
NAME2SPEC = {'Ranjit Thakur': 'RANJIT', 'Parashotam Dass': 'PARASHOTAM', 'Virendra Kumar': 'VIRENDRA', 'P S Gill': 'PS_GILL',
             'Randhir Singh': 'RANDHIR', 'Vishav Priya Singh': 'VISHAV', 'Prithi Pal Singh Bedi': 'PPS_BEDI', 'Kuldeep Yadav': 'KULDEEP',
             'Pooja Pal': 'POOJA_PAL', 'Sukhdev Singh': 'SUKHDEV', 'Nalin Kumar Bhatia': 'NALIN', 'Ram Avtar': 'RAM_AVTAR',
             'Tarsem Singh': 'TARSEM', 'L Chandra Kumar': 'CHANDRA_KUMAR', 'Ram Sarup': 'RAM_SARUP', 'Anvar P V': 'ANVAR',
             'Arjun Panditrao Khotkar': 'ARJUN', 'Sonu alias Amar': 'SONU'}
UNRESOLVED_PLAIN = {'ADM-017': ['NITISHA_MA'], 'ADM-SC-11': ['NITISHA_MA'], 'ADM-027': ['NALIN', 'INSC_2023_985', 'INSC_2026_281']}

def kb_links(inv_path):
    kb = {json.loads(l)['id']: json.loads(l) for l in open(os.path.join(WS, '..', '..', 'curated_originals/knowledge_base/v0.9/records_658.jsonl'), encoding='utf-8')}
    idr = {r['spec_key']: r for r in csv.DictReader(open(os.path.join(WS, 'identity_resolution.csv'), encoding='utf-8'))}
    xw = collections.defaultdict(set)
    for r in csv.DictReader(open(os.path.join(WS, 'crosswalk_cases53_kb658.csv'), encoding='utf-8')):
        if r['kb_record_id']:
            xw[r['kb_record_id']].add(r['spec_key'])
    rows = []
    for r in csv.DictReader(open(inv_path, encoding='utf-8')):
        flags = r['broken_or_unresolved_flags'] + ' ' + r['info_flags']
        if not (r['case_names_matched'] or 'CASE_NAME' in flags or 'PLAIN_CASE_CITATION' in flags):
            continue
        rid = r['record_id']; specs = []
        for m in [x for x in r['case_names_matched'].split(';') if x]:
            name = m.split('->')[0]
            specs.append(NAME2SPEC.get(name, CID2SPEC.get(m.split('->')[-1], '?')))
        specs += UNRESOLVED_PLAIN.get(rid, [])
        rec = kb[rid]; blob = rec['title'] + ' ' + rec['body'] + ' ' + rec['references']
        for k in specs:
            s = SPEC.get(k)
            m_ = re.search(s[3], blob, re.I) if s else None
            ev = re.sub(r'\s+', ' ', blob[max(0, m_.start() - 40):m_.end() + 60]) if m_ else ''
            idrow = idr.get(k, {})
            rows.append([rid, ';'.join(t for t in flags.split() if 'CASE' in t), k, s[1] if s else '', s[2] if s else '',
                         idrow.get('identity_state', ''), idrow.get('held_copy_sha256', '')[:64], idrow.get('intern_sha256', '')[:64],
                         'ALREADY_IN_WS_B_CROSSWALK' if k in xw.get(rid, set()) else 'NEW_LINK_CYCLE3', ev[:200],
                         'Name/citation link only; proposition-level support not verified', 'C3'])
    hdr = ['kb_record_id', 'wsc_flags', 'spec_key', 'case53_id', 'case', 'identity_state', 'official_copy_sha256', 'intern_mirror_sha256',
           'crosswalk_status', 'kb_text_evidence', 'caveat', 'cycle']
    return hdr, rows

# ------------------------------------------------------------------ corrections + network log
CR = [
 ('CR-C3-01', 'holdings_register.csv WSB-H-030 (MULLIKOTE)', 'Cites pp.61-62 paras 97-99, which belong to the second, uncorrected and differently numbered version inside the official PDF (pp.32-62). The CORRECTED version (pp.1-31) carries the curated pinpoints (paras 33-44, 51). Cite WSB-H3 Mullikote rows instead. Also: respondent service number differs between versions (p.1 "2568912 M"; p.32 "256812 M").', 'Mullikote official PDF pp.1, 21-31, 32 (page images p.26, p.31)', 'Prior row retained unchanged; superseded for citation by cycle-3 rows'),
 ('CR-C3-02', 'network_lookup_log_cycle3.csv', 'The 11 HEAD lookups of 2026-11-22T17:06Z-17:07Z each sent two HEAD requests in immediate succession (status, then headers) before the 3-second pause - i.e. 22 requests, pairs <3 s apart, contrary to the <=1 req/3 s rule. No body bytes were requested. Subsequent request (control) was single.', 'scratchpad lookups/head_log_c3.tsv', 'Deviation recorded; not repeated'),
 ('CR-C3-03', 'adverse_conflict_queue.csv A-08', 'A-08 (Mullikote two versions) is confirmed and sharpened: versions are numbered differently (51 vs 99 paragraphs), so pinpoints must state the version.', 'as CR-C3-01', 'No change to prior row'),
]

def main():
    ap = argparse.ArgumentParser()
    for a in ('--snapshot', '--citescan', '--wsc-inventory', '--netlog'):
        ap.add_argument(a, required=True)
    a = ap.parse_args()
    out = {}
    out['holdings_register_cycle3.csv'] = holdings3()
    (auth, pend, ctrl) = authoritative(a.netlog)
    out['authoritative_copy_status_cycle3.csv'] = auth
    out['pending_acquisition_cycle3.csv'] = pend
    out['identity_resolution_cycle3.csv'] = identities3()
    t, s = treatment3(json.load(open(a.citescan)))
    out['subsequent_treatment_cycle3.csv'] = t
    out['citation_scan_summary_cycle3.csv'] = s
    out['kb658_case_name_links_cycle3.csv'] = kb_links(a.wsc_inventory)
    out['corrections_cycle3.csv'] = (['correction_id', 'target', 'finding', 'evidence', 'handling'], [list(x) for x in CR])
    log = []
    for line in open(a.netlog, encoding='utf-8'):
        p = line.rstrip('\n').split('\t')
        log.append([p[0], p[1], p[2], p[3], ' '.join(p[4:]), 'NO_BODY_BYTES_REQUESTED'])
    log += [['2026-11-22 (cycle 2)', 'MANI_RAM/RAM_AVTAR office reports', 'GET', 'api.sci.gov.in officereport x2 (HTML)', '200', 'HTML text only; sha recorded in reviewed_matches.py'],
            ['2026-11-22 (cycle 2)', 'diary directory probes', 'GET', 'api.sci.gov.in/supremecourt/2011/13135/ and /21005/', '200 empty', 'no listing']]
    out['network_lookup_log_cycle3.csv'] = (['utc_time', 'purpose', 'method', 'url', 'result', 'note'], log)
    for name, (hdr, rows) in out.items():
        with open(os.path.join(WS, name), 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f, lineterminator='\n'); w.writerow(hdr)
            for r in rows:
                assert len(r) == len(hdr), (name, r[:2]); w.writerow(r)
        print(name, len(rows))

if __name__ == '__main__':
    main()
