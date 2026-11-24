#!/usr/bin/env python3
"""Build the C12 legal-adviser review package from existing repository artefacts.

Read-only with respect to every input. Writes only into the adviser_package folder.
No legal conclusion is produced: the package lists questions, excerpts with pinpoints,
competing readings already recorded in the artefacts, affected records and missing evidence.

Usage: python3 -I tools/build_adviser_package.py   (run from anywhere)
"""
import csv
import hashlib
import io
import json
import re
import subprocess
import sys
from collections import Counter, OrderedDict
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent
AW = PKG.parent.parent                      # .../legal_knowledge/audit_work
C12W = AW.parent.parent                     # scratchpad/c12w (git worktree)
SCRATCH = C12W.parent
C7 = Path('/home/user/c7')
TEXT_COMMIT = 'ad77758d'
C9_COMMITS = ('cfc52d57', 'a61c0e57')
C9P = 'legal_knowledge/audit_work/C9-LEGAL-EVIDENCE'

IN = OrderedDict([
    ('GRAPH_SUMMARY', AW / 'C11-JUDICIAL-QUALITY/relations/outputs/GRAPH_SUMMARY.json'),
    ('TREATMENT_CANDIDATES', AW / 'C11-JUDICIAL-QUALITY/relations/outputs/TREATMENT_CANDIDATES.csv'),
    ('DOSSIER', AW / 'C11-JUDICIAL-QUALITY/relations/outputs/PRIORITY_TREATMENT_DOSSIER.md'),
    ('DISP_REL', AW / 'C11-JUDICIAL-QUALITY/review/DISPOSITIONS_relations_c11.md'),
    ('AFFECTED', AW / 'C11-JUDICIAL-QUALITY/curated/AFFECTED_RESEARCH_RECORDS.csv'),
    ('CURATED53', AW / 'C11-JUDICIAL-QUALITY/curated/CURATED_53_C11.csv'),
    ('ESC_C10', AW / 'C10-RECONCILIATION/workstreams/judicial/ADVISER_ESCALATIONS_C10.csv'),
    ('JT_C10', AW / 'C10-RECONCILIATION/workstreams/judicial/JUDICIAL_TREATMENT_C10.csv'),
    ('C9STAT_C10', AW / 'C10-RECONCILIATION/workstreams/judicial/C9_FINDING_STATUS_C10.csv'),
    ('AMD_GRAPH_C10', AW / 'C10-RECONCILIATION/workstreams/statutory/amendment_graph_c10.csv'),
    ('ESC_STAT_C10', AW / 'C10-RECONCILIATION/workstreams/statutory/escalation_matters_c10.csv'),
    ('STAT_FIND_C10', AW / 'C10-RECONCILIATION/workstreams/statutory/STATUTORY_C10_FINDINGS.md'),
    ('DISP_FINAL', AW / 'C10-RECONCILIATION/review/DISPOSITIONS_final_head_confirmations.md'),
    ('RR04_REVIEW', AW / 'C10-RECONCILIATION/review/final_head_confirmations/fable_review_7ccb9c2e.md'),
    ('AUTH_MATRIX', AW / 'C10-RECONCILIATION/outputs/CORPUS_AUTHORITY_MATRIX.md'),
    ('PR46_REVIEW', SCRATCH / 'c12/reviews/fable_review_pr46_c69eee41.md'),
    ('RECORDS658', AW.parent / 'curated_originals/knowledge_base/v0.9/records_658.jsonl'),
    ('BRIEF', Path('/home/user/mimamsa-corpus/CLAUDE.md')),
])
C9_FILES = ['DECISION_MATRIX_C9.md', 'CORRECTIONS/LEGAL_ADVISER_ESCALATION.md', 'STATUTORY/UNRESOLVED_MATTERS.md']

BANNER = ('**PREPARED BY AUTOMATED AGENTS. TECHNICAL AND DOCUMENTARY REVIEW ONLY. NO LEGAL VALIDATION.** '
          'Nothing in this package is a legal conclusion, a status change or an approval. Every reading of a '
          'source page was made by an AI agent from a text layer and is not human-confirmed. '
          'Questions are for a qualified legal adviser (or JAG, where the controlling policy requires it).')


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def git(*args, repo=C7):
    return subprocess.run(['git', '-C', str(repo), *args], capture_output=True, text=True, check=True).stdout


_TEXT = {}


def pages_of(doc):
    if doc not in _TEXT:
        try:
            t = git('show', f'{TEXT_COMMIT}:data/text/{doc}.txt')
        except subprocess.CalledProcessError:
            _TEXT[doc] = None
            return None
        parts = re.split(r'\[\[page (\d+)\]\]', t)
        _TEXT[doc] = {int(parts[i]): parts[i + 1] for i in range(1, len(parts), 2)}
    return _TEXT[doc]


def squash(s):
    s = s.replace('\u2019', "'").replace('\u2018', "'").replace('\u201c', '"').replace('\u201d', '"')
    return re.sub(r'\s+', '', s)


def verify(doc, page, quote):
    """Whitespace-insensitive verbatim check on the stated page, then across the page break."""
    pg = pages_of(doc)
    if pg is None:
        return 'NO_TEXT_FILE_AT_' + TEXT_COMMIT, ''
    q = squash(quote)
    if page in pg and q in squash(pg[page]):
        return 'VERIFIED_ON_STATED_PAGE', f'p.{page}'
    if page in pg and page + 1 in pg and q in squash(pg[page] + pg[page + 1]):
        return 'VERIFIED_SPANNING_PAGE_BREAK', f'pp.{page}-{page + 1}'
    if page - 1 in pg and page in pg and q in squash(pg[page - 1] + pg[page]):
        return 'VERIFIED_SPANNING_PAGE_BREAK', f'pp.{page - 1}-{page}'
    hits = [p for p, b in pg.items() if q in squash(b)]
    if hits:
        return 'FOUND_ON_OTHER_PAGE', ','.join(f'p.{h}' for h in hits)
    return 'NOT_FOUND', ''


# ---------------------------------------------------------------------------
# Excerpt registry. kind: COURT_VOICE / LATER_RELIANCE / EDITORIAL / STATUTE_COMPILATION / BENCH.
# origin: the artefact reading the excerpt is taken from.
# ---------------------------------------------------------------------------
P23 = 'sc-2023-union-of-india-ors-2023insc265'
SKS = 'sc-2015-union-of-india-ors-2015insc206'
TAR = 'sc-2008-union-of-india-ors-2008insc930'
GIR = 'sc-2026-union-of-india-through-its-sec-2026insc149'
X = OrderedDict()


def ex(ref, doc, page, para, quote, kind, origin, note=''):
    X[ref] = dict(ref=ref, doc=doc, page=page, para=para, quote=quote, kind=kind, origin=origin, note=note)


# High Court writs vs AFT
ex('RD-PARASHOTAM-T1', P23, 17, '32', 'We have, thus, no hesitation in concluding that the judgment in', 'COURT_VOICE', 'C11 dossier')
ex('RD-PARASHOTAM-T2', P23, 17, '32', 'Shri Kant Sharma & Anr.24 case does not lay down the correct law and is in conflict with judgments of the Constitution', 'COURT_VOICE', 'C11 dossier', "'24' is a footnote marker; the word 'overruled' is not used")
ex('C12-PARASHOTAM-LCK', P23, 17, '32', 'including in L. Chandra Kumar25 case, S.N. Mukherjee26 case, and Rojer Mathew27 case making it abundantly clear that there is no per se restriction on the exercise of', 'COURT_VOICE', 'C12 (this package; same paragraph)')
ex('RD-PARASHOTAM-T3', P23, 18, '32', 'power under Article 226 of the Constitution by the High Court. However, in respect of matters of self-discipline, the principles already stand enunciated.', 'COURT_VOICE', 'C11 dossier')
ex('RD-PARASHOTAM-ED', P23, 4, '-', '& Anr. (2015) 6 SCC 773 : [2015] 4 SCR 676 \u2013 held not correct law.', 'EDITORIAL', 'C11 dossier', 'reporter case-law entry; never the court\'s treatment')
ex('RD-PARASHOTAM-BENCH', P23, 1, '-', '[SANJAY KISHAN KAUL, B. V. NAGARATHNA AND ABHAY S. OKA, JJ.]', 'BENCH', 'C11 dossier')
ex('R-PARASH-H1', 'official copy wt:fe19875b', 22, '32', 'case does not lay down the correct law and is in conflict with judgments of the Constitution Benches', 'COURT_VOICE', 'C10 JUDICIAL_TREATMENT_C10.csv (quote_check VERBATIM_FOUND)', 'official SC copy in the C5 working store; not in the text layer')
ex('R-PARASH-H2', 'official copy wt:fe19875b', 22, '32', 'there is no per se restriction on the exercise of power under Article 226 of the Constitution by the High Court', 'COURT_VOICE', 'C10 JUDICIAL_TREATMENT_C10.csv (quote_check VERBATIM_FOUND)', 'in the SCR rendition the court-voice sentence runs from p.17 to p.18 with footnotes and margin letters between (C12-PARASHOTAM-LCK, RD-PARASHOTAM-T3)')
ex('RD-SHRIKANT-H1', SKS, 47, '34(iv)', '226 of the Constitution if an effective alternative remedy is available to the aggrieved person or the statute', 'COURT_VOICE', 'C11 dossier', 'same words also occur on p.44 inside a quotation of an earlier judgment')
ex('RD-SHRIKANT-H2', SKS, 49, '38', 'we are of the view that Delhi High Court was not', 'COURT_VOICE', 'C11 dossier', "continues: 'justified in entertaining the petition under Article 226'")
ex('RD-SHRIKANT-H3', SKS, 33, '25', 'judicial review vested in the High Court under Article 226 is one of the basic essential features of theConstitution', 'COURT_VOICE', 'C11 dossier')
ex('RD-SHRIKANT-BENCH', SKS, 1, '-', '[SUDHANSU JYOTI MUKHOPADHAYA AND', 'BENCH', 'C11 dossier', 'two-Judge Bench (with N.V. Ramana J., next line)')
ex('RD-JKHC-SKS', 'hc-jkl-2025-wp-c-2370-2025-jkhc010050362025-1-2025-10-06', 2, '6', 'Since the Apex Court in case titled as \u201cUnion of India vs. Shri Kant Sharma (2015) 6 SCC 773 has specifically provided that High Court', 'LATER_RELIANCE', 'C11 dossier / C10 R-SHRIKANT-T2', 'J&K HC 06-10-2025; Parashotam not cited in this order')
ex('RD-JKHC-SKS2', 'hc-jkl-2025-wp-c-2370-2025-jkhc010050362025-1-2025-10-06', 3, '6', 'should refrain from entertaining petitions under Article 226 if alternative or effective remedy is available', 'LATER_RELIANCE', 'C11 dossier')
ex('R-PARASH-T1', 'sc-2023-union-of-india-ors-2023insc1074', 16, '(SCR p.1041)', 'This position stood restated, recently, in Union of India v Parashotam Dass', 'LATER_RELIANCE', 'C10 JUDICIAL_TREATMENT_C10.csv')
ex('R-PARASH-T2', 'hc-allahabad-2026-wria-2923-2026-uphc011159512026-1-2026-04-02', 5, '18', "in the case of Parashotam Dass (Supra), the only issue before the Hon'ble Supreme Court was maintainability of writ petition", 'LATER_RELIANCE', 'C10 JUDICIAL_TREATMENT_C10.csv', 'territorial-jurisdiction question; Parashotam held inapplicable by the HC')
# Pension arrears
ex('RD-TARSEM-H1', TAR, 5, '5', 'will restrict the consequential relief relating to arrears normally', 'COURT_VOICE', 'C11 dossier', 'SCR rendition [2008] 12 SCR 104; OCR noise in the continuation')
ex('RD-TARSEM-H2', TAR, 6, '6', 'It ought to have restricted the relief relating to ar- rears to only three years before the date of writ petition', 'COURT_VOICE', 'C11 dossier')
ex('RD-GIRISH-T1', GIR, 11, '22', 'The reliance placed by the appellant on the decision of a two-Judge Bench of this Court in Tarsem Singh (supra) is of no assistance to it, as the legal landscape did not remain static after decision in Tarsem Singh.', 'COURT_VOICE', 'C11 dossier')
ex('RD-GIRISH-T2', GIR, 11, '22', 'the decision in Tarsem Singh (supra) has no application to the case in hand as ex-servicemen in the instant appeals are already in receipt of disability pension', 'COURT_VOICE', 'C11 dossier')
ex('RD-GIRISH-T3', GIR, 11, '22', 'decided the issue of applicability of instruction dated 31.01.2001 and the aforesaid decision is in rem.', 'COURT_VOICE', 'C11 dossier')
ex('RD-GIRISH-H1', GIR, 11, '22', 'Therefore, the bar contained in Section 22(1)(c) of the Act has no application to the', 'COURT_VOICE', 'C11 dossier', "continues on p.12: 'claims filed by the ex-servicemen before the Tribunal.'")
ex('RD-GIRISH-R1', GIR, 9, '14', 'The legal position continued to be uncertain until it was settled by a three-Judge bench of this Court in Union of India & Others v. Ram Avtar (supra).', 'COURT_VOICE', 'C11 dossier')
ex('RD-GIRISH-ED', GIR, 2, '-', 'Tarsem Singh [2008] 12 SCR 104 : (2008) 8 SCC 648 \u2013 held inapplicable.', 'EDITORIAL', 'C11 dossier', 'reporter matter; never the court\'s treatment')
ex('RD-GIRISH-BENCH', GIR, 1, '-', '[Pamidighantam Sri Narasimha and Alok Aradhe,* JJ.]', 'BENCH', 'C11 dossier')
ex('R-TARSEM-T3', 'official copy wt:10e1954f (Mullikote, 2026 INSC 286)', 27, '43', 'In any event, the said question of law is left open.', 'COURT_VOICE', 'C10 JUDICIAL_TREATMENT_C10.csv (quote_check VERBATIM_FOUND)', 'Mullikote is not in the ad77758d text layer')
ex('RD-DHC-TARSEM-A', 'hc-delhi-2026-w-p-c-16771-2025-dlhc010862002025-1-2026-03-11', 9, '27', 'view the law laid down by Supreme Court in Union of India & Ors v. Tarsem Singh8 , the arrears will be restricted to three years prior the OA,', 'LATER_RELIANCE', 'C11 dossier / C10 R-TARSEM-T4', 'Delhi HC 11-03-2026, after Girish; Girish not mentioned in the passage')
ex('RD-DHC-TARSEM-D', 'hc-delhi-2026-w-p-c-2053-2026-dlhc010054682026-1-2026-04-20', 3, '10', 'The reliance placed on Tarsem Singh (supra) is misconceived.', 'LATER_RELIANCE', 'C11 dossier / C10 R-TARSEM-T5')
ex('R-GIRISH-T1', 'hc-ph-2026-cwp-7955-2026-phhc010370702026-1-2026-03-17', 3, '-', 'has been settled by the Hon\u2019ble Supreme Court of India in a recently passed judgment in Civil Appeal Nos. 6820-6824 of 2018', 'LATER_RELIANCE', 'C10 JUDICIAL_TREATMENT_C10.csv', 'P&H HC reads Girish as settling the arrears question for a non-party claimant')
ex('R-TARSEM-T6', 'hc-jkl-2026-wp-c-1426-2026-jkhc020026572026-1-2026-05-19', 4, '(quoting Girish para 22)', 'For, yet another reason, the decision in Tarsem Singh (supra) has no application to the case in hand', 'LATER_RELIANCE', 'C10 JUDICIAL_TREATMENT_C10.csv', 'words are Girish\'s, reproduced by the HC (QUOTED_PASSAGE)')
ex('R-RAMAVTAR-T1', 'sc-2019-g-h-union-of-india-ors-2019insc1359', 4, '8', 'This Court in Ram Avtar (supra), while approving the judgment of the Armed Forces Tribunal only held that the principle of rounding off', 'COURT_VOICE', 'C10 JUDICIAL_TREATMENT_C10.csv', 'S P Rathore, SCR rendition [2019] 18 S.C.R. 990; no official copy held')
ex('R-SPRATHORE-H1', 'sc-2019-g-h-union-of-india-ors-2019insc1359', 5, '9', 'If a person is not entitled to the disability pension, there would be no question of rounding off.', 'COURT_VOICE', 'C10 JUDICIAL_TREATMENT_C10.csv')
ex('R-RAMAVTAR-H1', 'official copy wt:4f7ea3a4 (Girish)', 10, '13', 'by an order dated 10.12.2014 dismissed more than 800 appeals', 'COURT_VOICE', 'C10 JUDICIAL_TREATMENT_C10.csv (quote_check VERBATIM_FOUND)')
ex('RD-DHARAMVIR-H1', 'sc-2013-dharamvir-singh-2013insc408', 27, '28(ii)', 'A member is to be presumed in sound physical and mental condition upon entering service if there is no note or record at the time of entrance.', 'COURT_VOICE', 'C11 dossier', 'read with para 28(i): Entitlement Rules 1982')
ex('R-DHARAMVIR-T1', 'official copy wt:3f49a314 (N C Isaac, 2026 INSC 993)', 91, '34', 'substantially reproduce the 1982 scheme of causal connection, onus, and attributability/aggravation subject only to the limited qualification introduced by the proviso to Rule 7', 'COURT_VOICE', 'C10 JUDICIAL_TREATMENT_C10.csv (quote_check VERBATIM_FOUND)', 'Isaac is not in the ad77758d text layer; authentication pending')
ex('R-ISAAC-H1', 'official copy wt:3f49a314 (N C Isaac, 2026 INSC 993)', 93, '39(iii)', 'the principle in Rule 7 of the Entitlement Rules 2008 applies and the burden shifts', 'COURT_VOICE', 'C10 JUDICIAL_TREATMENT_C10.csv (quote_check VERBATIM_FOUND)')
# Statutes (India Code compilations in the text layer; sha prefixes as cited by C9/C10)
ex('C9R-R23-COMP', 'rules-army-rules-1954', 41, 'r.23(3)', 'You are obliged to say anything unless you wish to do so', 'STATUTE_COMPILATION', 'C9 ESC-03 / C10 ESC-R23-3 (compilation 48f52219)')
ex('C9R-R23-GAZ', 'Gazette 27-11-1954 (S.R.O. 484) archival facsimile c5ef95a9, PDF', 10, 'r.23(3)', 'You are not obliged to say anything unless you wish to do so', 'STATUTE_GAZETTE', 'C9 ESC-03 / C10 ESC-R23-3', 'printed p.300; facsimile is working-store only; not in the text layer')
ex('C9R-AR-01', 'rules-army-rules-1954', 189, 'r.168(2)', 'or until the completion of the field punishment, unless such field punishment is remitted by a competent authority', 'STATUTE_COMPILATION', 'C9-AG-AR168 (compilation 48f52219 p.189)')
ex('C12-AR182-COMP', 'rules-army-rules-1954', 197, 'r.182', 'nor shall any evidence respecting the proceedings of the court be given against any such person except upon the trial or such person for wilfully giving', 'STATUTE_COMPILATION', 'C12 (compilation 48f52219 p.197, cited by C9-AG-RES-SC4-01 as comparison)', "text layer prints 'trial or such person'")
ex('C12-AR193-COMP', 'rules-army-rules-1954', 209, 'r.193', 'The prescribed officer for the purposes of clause (i) of section 90 and clause (i) of section 91 shall be the Chief of the Army Staff or the officer commanding the Army.', 'STATUTE_COMPILATION', 'C12 (compilation 48f52219 p.209; PIC-29 per C9-AG-RES-C-08)')
ex('C12-AR194-COMP', 'rules-army-rules-1954', 209, 'r.194', 'Prescribed officer for the purpose of section 93 shall be, in the case of an officer, the Chief of the Army Staff', 'STATUTE_COMPILATION', 'C12 (compilation 48f52219 p.209; PIC-29 per C9-AG-RES-C-09)')
ex('C9R-AA-03a', 'act-army-1950', 27, 'ss.75-76', 'Omitted by the Army (Amendment) Act, 1992 (37 of 1992), s. 2 (w.e.f. 6-9-1992).', 'STATUTE_COMPILATION', 'C9 U-3 / C10 ESC-ACT37-1992 (compilation e47a4265)', 'compiler statement only; Act 37/1992 prints no commencement clause')
ex('C9R-AA-03b', 'act-army-1950', 36, 's.127', 'Omitted by the Army (Amendment) Act, 1992 (37 of 1992), s. 11 (w.e.f. 6-9-1992)', 'STATUTE_COMPILATION', 'C9 U-3 (compilation e47a4265)')
ex('C9R-AA-03c', 'act-army-1950', 48, 'Ch XVI', 'Omitted by the Army (Amendment) Act, 1992 (37 of 1992), s. 19 (w.e.f. 6-9-1992).', 'STATUTE_COMPILATION', 'C9 U-3 (compilation e47a4265)')
ex('C9-S26', 'act-army-1950', 16, 's.26(2)', 'the aggrieved person may complain to such officer\u2019s next superior officer', 'STATUTE_COMPILATION', 'C9 ESC-09 (compilation e47a4265 p.16)')
ex('C9-S133', 'act-army-1950', 37, 's.133', 'The Indian Evidence Act, 1872 (1 of 1872), shall, subject to the provisions of this Act, apply to all proceedings before a court-martial.', 'STATUTE_COMPILATION', 'C9 ESC-07 (compilation e47a4265 p.37)')
ex('C9-BSA-1-2', 'act-bsa-2023', 10, 's.1(2)', 'It applies to all judicial proceedings in or before any Court, including Courts-martial', 'STATUTE_COMPILATION', 'C9 ESC-07 (compilation 554b2b4a p.10)')
ex('C9-BSA-170-2', 'act-bsa-2023', 51, 's.170(2)', 'shall be dealt with under the provisions of the Indian Evidence Act, 1872 (1 of 1872), as in force immediately before such', 'STATUTE_COMPILATION', 'C9 ESC-07 (compilation 554b2b4a p.51)')
ex('C9R-BNSS-03', 'act-bnss-2023', 174, 's.531(1)', 'The Code of Criminal Procedure, 1973 (2 of 1974) is hereby repealed.', 'STATUTE_COMPILATION', 'C9 U-5 / C10 C9-AG-BNSS-REPEAL (compilation 572c7988 p.174)')
ex('C9R-AFT-05', 'act-armed-forces-tribunal-2007', 7, 's.9A fn', 'Ins. by Act 7 of 2017, s. 181 (w.e.f. 26-5-2017).', 'STATUTE_COMPILATION', 'C9-AG-AFT-01 (compilation 665863d1 p.7)', 'compiler statement only')
ex('C9R-AFT-06', 'act-armed-forces-tribunal-2007', 7, 's.9A fn', 'Subs by Act 17 of 2026, s. 18 and Sch. II for section 9A (w.e.f. 25-08-2026).', 'STATUTE_COMPILATION', 'C9-AG-AFT-03 (compilation 665863d1 p.7)', 'compiler statement only')
ex('C9R-RD-FIN17-02', 'act-the-finance-act-2017', 53, 's.156', 'The provisions of this Part shall come into force on such date as the Central Government may, by notification in the Official Gazette, appoint', 'STATUTE_COMPILATION', 'C9-AG-AFT-01 (7a5551ba p.53)')
ex('C9R-TRA-02', 'act-the-tribunals-reforms-act-2026', 1, 's.1(2)', 'It shall come into force on such date as the Central Government may, by notification in the Official Gazette, appoint; and different dates may be appointed for different provisions of this Act', 'STATUTE_COMPILATION', 'C9-AG-AFT-03 (be619533 p.1)')


# ---------------------------------------------------------------------------
# Inputs: affected records
# ---------------------------------------------------------------------------
def read_csv(key):
    with open(IN[key], newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


AFF = read_csv('AFFECTED')
AFF_BY_CASE = OrderedDict()
for r in AFF:
    AFF_BY_CASE.setdefault(r['case'], []).append(r)


def recs(*cases):
    out = []
    for c in cases:
        for r in AFF_BY_CASE.get(c, []):
            if r['record_id'] not in out:
                out.append(r['record_id'])
    return out


# ---------------------------------------------------------------------------
# Own-voice leads (30 adviser rows)
# ---------------------------------------------------------------------------
GS = json.loads(IN['GRAPH_SUMMARY'].read_text(encoding='utf-8'))
ADV_IDS = [r.split('|')[0] for r in GS['treatment']['adviser_rows']]
TC = {r['candidate_id']: r for r in read_csv('TREATMENT_CANDIDATES')}
ADV = [TC[i] for i in ADV_IDS]
assert len(ADV) == 30 and all(r['status'] == 'LEGAL_INTERPRETATION_ADVISER_REVIEW' for r in ADV)

NOISE = {
    'TC-9b500dbe0d15': 'V13-01: C.S. Gill p.19 is a description of court-martial procedure ("If the objection regarding such plea is overruled"): proposal to be withdrawn.',
    'TC-e8e740a5df2f': 'V13-01: Shatrughan Chauhan p.54 sits inside a quotation from Triveniben: proposal to be withdrawn.',
    'TC-8eee72cd601c': 'V13-01: SCAORA separate-opinion row is a rhetorical question: to be dropped.',
    'TC-741f5ae7f6ab': 'V13-01: SCAORA separate-opinion row is a negated statement ("no one has said ... that it does not lay down the correct law"): to be dropped.',
}
CAVEAT = {
    'TC-19f0e5a3af63': 'V13-02: p.1065 is Chandrachud J.\'s dissent, not Bhushan J.\'s opinion (bracketed footer preferred to running header).',
    'TC-bd7606d4e30b': 'V13-02: p.1065 is Chandrachud J.\'s dissent, not Bhushan J.\'s opinion (bracketed footer preferred to running header).',
    'TC-204093fae39f': 'V13-02: the Mafatlal p.105 author is not Ahmadi CJ (opinion label wrong; proposal unchanged).',
    'TC-8111df7aac52': 'V13-02: the Mafatlal p.105 author is not Ahmadi CJ (opinion label wrong; proposal unchanged).',
    'TC-cd1cb49fedd0': 'V13-02: the Mafatlal p.133 author is not Ahmadi CJ (opinion label wrong; proposal unchanged).',
    'TC-900ee3f8d5c6': 'V13-02: the Mafatlal p.133 author is not Ahmadi CJ (opinion label wrong; proposal unchanged).',
    'TC-09b5d373b025': 'V13-03: the candidate for Mohd. Saeed Siddiqui is wrong; (2004) 2 SCC 130 is Teri Oat Estates. Match on the party name in the sentence.',
    'TC-4289a1bc33bc': 'V13-04: "these two decisions" are named in the preceding sentences: Kerala HC (Subramanian) and Calcutta HC (Anand Singh Bisht).',
}

# group the 30 rows into leads by (source, cue page, cue paragraph, sentence)
LEADS = OrderedDict()
for r in sorted(ADV, key=lambda r: (r['source_date'], r['source_doc_id'], int(r['cue_page'] or 0), r['candidate_id'])):
    key = (r['source_doc_id'], r['cue_page'], r['cue_paragraph'], r['lead_target_raw'][:40] if r['lead_target_raw'] else r['cue_text'])
    LEADS.setdefault(key, []).append(r)


def trim_excerpt(e):
    e = e.strip()
    if e.endswith('\u2026'):
        e = e[:-1]
        e = e.rsplit(' ', 1)[0]
    parts = e.split(' ', 1)
    return parts[1] if len(parts) == 2 else e


# The Mafatlal p.133 rows carry different excerpts but one paragraph; keep as two leads if sentences differ.
LEAD_LIST = []
for key, rows in LEADS.items():
    LEAD_LIST.append(rows)

# Merge same-sentence pairs that the key split (identical trimmed excerpt core) -- deterministic.
final = []
for rows in LEAD_LIST:
    for f in final:
        if f[0]['source_doc_id'] == rows[0]['source_doc_id'] and f[0]['cue_page'] == rows[0]['cue_page'] and \
                f[0]['cue_paragraph'] == rows[0]['cue_paragraph'] and \
                (squash(trim_excerpt(f[0]['excerpt']))[40:120] == squash(trim_excerpt(rows[0]['excerpt']))[40:120]):
            f.extend(rows)
            break
    else:
        final.append(list(rows))
LEAD_LIST = final


def opinion_of(cid):
    for r in GS['treatment']['adviser_rows']:
        p = r.split('|')
        if p[0] == cid:
            return p[3], p[4]
    return '', ''


# ---------------------------------------------------------------------------
# Question register
# ---------------------------------------------------------------------------
Q = []


def q(qid, topic, title, question, sources, excerpts, competing, affected, missing, priority, origin, extra=None):
    competing = [re.sub(r'^\((\w)\) \(\1\) ', r'(\1) ', c) for c in competing]
    Q.append(OrderedDict(id=qid, topic=topic, title=title, question=question, sources=sources, excerpts=excerpts,
                         competing=competing, affected=affected, missing=missing, priority=priority, origin=origin,
                         extra=extra or []))


T_HCW = 'High Court writs vs AFT (Parashotam Dass / Shri Kant Sharma)'
T_PEN = 'Pension arrears and entitlement (Tarsem / Girish / unheld clarification / Ram Avtar / Dharamvir)'
T_OVR = 'Own-voice overruling leads (C11 adviser queue)'
T_STA = 'Disputed statutory edges and commencement'
T_AUT = 'Authority ranking of copies (RR-04)'
T_ROL = 'Legal-approval role (PR #46 F-01)'

PAR_RECS = recs('Parashotam')
q('AQ-HCW-01', T_HCW, 'Typed relation from Parashotam Dass to Shri Kant Sharma',
  'Which typed relation, if any, should the corpus record from Union of India v Parashotam Dass (2023 INSC 265, three Judges) to Union of India v Maj Gen Shri Kant Sharma ((2015) 6 SCC 773, two Judges): overrules / overruled_by, "declared not good law", "disapproved", or another label?',
  ['C11 TREATMENT_CANDIDATES.csv TC-222df5c885ad (only BOUND row of the 30; proposed OVERRULES at LEGAL_INTERPRETATION_ADVISER_REVIEW)',
   'C11 PRIORITY_TREATMENT_DOSSIER.md, sections "Union of India v. Major General Shri Kant Sharma" and "Union of India v. Parashotam Dass"',
   'C10 JUDICIAL_TREATMENT_C10.csv R-SHRIKANT-T1 (classification OVERRULED in documentary wording), P-SHRIKANT',
   'C10 ADVISER_ESCALATIONS_C10.csv ESC-C10-03 (second sentence)', 'C9 LEGAL_ADVISER_ESCALATION.md ESC-06 (a)'],
  ['RD-PARASHOTAM-T1', 'RD-PARASHOTAM-T2', 'C12-PARASHOTAM-LCK', 'RD-PARASHOTAM-T3', 'RD-PARASHOTAM-ED', 'RD-PARASHOTAM-BENCH', 'RD-SHRIKANT-BENCH', 'R-PARASH-H1'],
  ['(a) overrules / overruled_by: explicit wording "does not lay down the correct law" by a three-Judge Bench against a two-Judge decision (C10 R-SHRIKANT-T1 classifies it OVERRULED in documentary wording; C11 tool proposes OVERRULES for review only).',
   '(b) "declared not good law" / "disapproved": the word "overruled" is not used in para 32 (C11 dossier; WS-B label WSB-T-004 cited by C9 ESC-06).',
   'The reporter case-law entry ("held not correct law", p.4) is editorial matter and is not evidence of the court\'s treatment.'],
  PAR_RECS + ['DCLR-SC-2023-009', 'DCLR-SC-2015-N06'],
  ['Human confirmation of the AI readings (P-B / B2 in the C9 decision matrix).',
   'The official-copy locator (wt:fe19875b p.22) was read in C10 but not re-read in C11; it is outside the ad77758d text layer.',
   'No signed or official copy of Shri Kant Sharma is held (SCR rendition only).'],
  'P1', 'C9 ESC-06 (P1); C10 ESC-C10-03; C11 TC-222df5c885ad')

q('AQ-HCW-02', T_HCW, 'Which limbs of Shri Kant Sharma survive Parashotam para 32',
  'Does any limb of Shri Kant Sharma survive Parashotam para 32, in particular the alternative-remedy guidance in para 34(iii)-(iv), given that the J&K High Court relied on Shri Kant Sharma on 06-10-2025 without citing Parashotam?',
  ['C11 dossier, Shri Kant Sharma "Open questions and uncertainty"', 'C10 ESC-C10-03 (first sentence)', 'C10 R-SHRIKANT-H1, R-SHRIKANT-T2',
   'C11 AFFECTED_RESEARCH_RECORDS.csv rows for "Shri Kant Sharma"'],
  ['RD-SHRIKANT-H3', 'RD-SHRIKANT-H1', 'RD-SHRIKANT-H2', 'RD-PARASHOTAM-T2', 'C12-PARASHOTAM-LCK', 'RD-PARASHOTAM-T3', 'RD-JKHC-SKS', 'RD-JKHC-SKS2'],
  ['(a) Parashotam rejects the proposition in paras 37-38 (that the High Court should not entertain writs against AFT orders); paras 34(i)-(ii) (Art. 226 a basic feature; due regard to legislative intent) are consistent with Parashotam (C11 dossier).',
   '(b) Whether para 34(iii)-(iv) (alternative remedy) survives as a discretionary rule is recorded as open (C11 dossier; C10 ESC-C10-03).',
   'Later practice preserved as found: J&K HC WP(C) 2370/2025 (06-10-2025) relies on Shri Kant Sharma for the alternative-remedy point; the order concerned an original petition, not a writ against an AFT order (C11 dossier note).'],
  recs('Shri Kant Sharma'),
  ['Whether the J&K HC order of 06-10-2025 was appealed or later considered (not searched).',
   'Human confirmation of the AI readings; official copy of Shri Kant Sharma.'],
  'P1', 'C10 ESC-C10-03; C9 ESC-06')

q('AQ-HCW-03', T_HCW, 'Scope of the "self-discipline" reservation in Parashotam para 32',
  'What is the scope of the last sentence of Parashotam para 32 ("However, in respect of matters of self-discipline, the principles already stand enunciated."), and must research records that state the High Court writ position carry it?',
  ['C11 dossier, Parashotam "Open questions and uncertainty" (scope not defined in the paragraph)',
   'C11 AFFECTED_RESEARCH_RECORDS.csv (13 Parashotam rows; proposed_action asks about the self-discipline reservation)'],
  ['RD-PARASHOTAM-T3', 'C12-PARASHOTAM-LCK', 'R-PARASH-H2', 'R-PARASH-T2'],
  ['No competing readings of the reservation are recorded in the artefacts. The artefacts record only that the paragraph does not define its scope (C11 dossier).',
   'Related later treatment: Allahabad HC WRIA 2923/2026 treats Parashotam as deciding only maintainability of a writ petition (R-PARASH-T2), on a territorial-jurisdiction question.'],
  PAR_RECS,
  ['Any held judgment construing the reservation (not searched for in C10/C11).', 'Human confirmation of the readings.'],
  'P2', 'C11 AFFECTED_RESEARCH_RECORDS.csv; C11 dossier')

q('AQ-HCW-04', T_HCW, 'Research records on the High Court writ route; pinpoint and holding corrections',
  'Do the 13 research records that depend on Parashotam state the High Court writ position correctly in the light of para 32, and may the C9 pinpoint and holding corrections (F-JUD-017; C9-CP-E01 to E06) be applied?',
  ['C11 AFFECTED_RESEARCH_RECORDS.csv (Parashotam: 13 rows)', 'C9 LEGAL_ADVISER_ESCALATION.md ESC-06 (b) and "What the corpus says now"',
   'C9 LEGAL_ADVISER_ESCALATION.md Part 3 (C9-CP-E03, E05, E06)'],
  ['RD-PARASHOTAM-T2', 'RD-PARASHOTAM-T3', 'R-PARASH-H1', 'R-PARASH-T1'],
  ['C9 records: DCLR-SC-2023-009 pinpoint "11-16" points into the private parties\' submissions; its holding omits the para 32 ratio; its scope_and_caveats says the official PDF was not retrieved although it is held; KB-025 cites para 18 (Union\'s pleas); KB-028 omits para 32; V7-JD-02 and AFT-035 already caveat the treatment.',
   'C9 classification: pinpoints are incorrect citations (documentary); the holding is incomplete, not wrong; the relation type is a characterisation reserved for a human.'],
  PAR_RECS + ['DCLR-SC-2023-009', 'DCLR-SC-2015-N06'],
  ['Adviser decision on AQ-HCW-01 (relation type) before the wording can be finalised.'],
  'P1', 'C9 ESC-06 (b); C11 AFFECTED_RESEARCH_RECORDS.csv')

q('AQ-HCW-05', T_HCW, 'Re-acquire L. Chandra Kumar and S.R. Dhingra',
  'Should official copies of L. Chandra Kumar and S.R. Dhingra be re-acquired for the curated records? Both were in the crawler\'s SC selection but were removed as "no military keyword". L. Chandra Kumar is one of the Constitution Bench decisions named in Parashotam para 32.',
  ['C10 ADVISER_ESCALATIONS_C10.csv ESC-C10-06', 'WS-B identity statuses CITATION_METADATA_CORROBORATED_BY_OFFICIAL_RECORD_NO_COPY / UNRESOLVED_NO_COPY_IN_HAND (as cited by ESC-C10-06)'],
  ['C12-PARASHOTAM-LCK'],
  ['No competing readings: this is an acquisition decision. Under CLAUDE.md any real download run needs approval first.'],
  ['(curated records for L. Chandra Kumar and S.R. Dhingra; ids not listed in ESC-C10-06)'],
  ['Copies of both judgments; approval for a download run.'],
  'P3', 'C10 ESC-C10-06')

TAR_RECS = recs('Tarsem')
GIR_RECS = recs('Girish')
q('AQ-PEN-01', T_PEN, 'Does Tarsem\'s three-year arrears limit survive outside Girish\'s grounds',
  'After Union of India v Sgt Girish Kumar (2026 INSC 149) para 22, may the AFT and High Courts still restrict arrears to three years under Union of India v Tarsem Singh ((2008) 8 SCC 648) for claims outside Girish\'s two grounds (for example initial-grant rather than re-computation disability-pension claims)?',
  ['C11 dossier, Tarsem and Girish sections', 'C10 ESC-C10-01; JUDICIAL_TREATMENT_C10.csv R-TARSEM-*, R-GIRISH-*', 'C9 LEGAL_ADVISER_ESCALATION.md ESC-01 (a)',
   'C11 TREATMENT_CANDIDATES.csv TC-0befe2825ad3, TC-206496479449 (Girish -> Tarsem DISTINGUISHES, DOCUMENTARY_CHECK_REQUIRED)'],
  ['RD-TARSEM-H1', 'RD-TARSEM-H2', 'RD-GIRISH-T1', 'RD-GIRISH-T2', 'RD-GIRISH-T3', 'RD-GIRISH-H1', 'RD-GIRISH-BENCH', 'R-TARSEM-T3', 'RD-DHC-TARSEM-A', 'RD-DHC-TARSEM-D', 'R-GIRISH-T1', 'R-TARSEM-T6', 'RD-GIRISH-ED'],
  ['(a) Narrow, or question open: Girish para 22 gives the re-computation ground expressly (RD-GIRISH-T2); Mullikote para 43 left the question open (R-TARSEM-T3); Delhi HC 11-03-2026, after Girish, still restricts arrears by Tarsem (RD-DHC-TARSEM-A); Girish and Tarsem are both two-Judge Benches.',
   '(b) Broader: Girish\'s first ground ("legal landscape did not remain static", RD-GIRISH-T1) is tied to Ram Avtar being in rem (RD-GIRISH-T3); C9 records para 20 (official p.14) as a "consistent line of decisions" against curtailing disability pension to three years; P&H HC 17-03-2026 reads Girish as settling the arrears question for a non-party claimant (R-GIRISH-T1).',
   'Delhi HC 20-04-2026 calls reliance on Tarsem "misconceived" on a fact-based distinction (ACP upgradation), not a statement about Tarsem\'s authority (RD-DHC-TARSEM-D).'],
  TAR_RECS + ['PEN-048', 'DCLR-SC-2008-N10'],
  ['Official court copy of Tarsem (only an unregistered SCR-format rendition is held; C9 ESC-04).',
   'Mullikote (2026 INSC 286) and the official Girish copy are outside the ad77758d text layer; C10 readings not re-read in C11.',
   'The 12-10-2026 clarification order (see AQ-PEN-03).', 'Human confirmation of the AI readings.'],
  'P1', 'C9 ESC-01 (P1); C10 ESC-C10-01')

q('AQ-PEN-02', T_PEN, 'Relation type Girish -> Tarsem and the C9 warning wording',
  'Which relation should be recorded from Girish to Tarsem ("distinguishes" is proposed; the documents are recorded as supporting no stronger edge), and may the warning wording in C9-CP-A01 to A04 (which states that Tarsem is not recorded as overruled) be applied?',
  ['C9 LEGAL_ADVISER_ESCALATION.md ESC-01 (b), (c)', 'C10 C9_FINDING_STATUS_C10.csv C9-F-A01/A02 (UNCHANGED_EVIDENCE_ADDED)',
   'C11 TREATMENT_CANDIDATES.csv TC-0befe2825ad3, TC-206496479449'],
  ['RD-GIRISH-T1', 'RD-GIRISH-T2', 'RD-GIRISH-BENCH'],
  ['(a) distinguishes (C9 proposal; C10 and C11 both record the wording as distinguishing, not overruling).',
   '(b) Whether a coordinate (two-Judge) Bench could do more, and what relation to record, is expressly left to the adviser (C9 review LG-09); no artefact proposes a stronger edge.'],
  TAR_RECS,
  ['Decision on AQ-PEN-01.'],
  'P1', 'C9 ESC-01 (b)-(c)')

q('AQ-PEN-03', T_PEN, 'The unheld 12-10-2026 "clarification" of Girish Kumar',
  'Until an official copy of the reported 12-10-2026 order (reported as 2026 INSC 1113) is obtained and read, may the corpus state its content at all (and if so only with an "UNVERIFIED SOURCE" flag)? Will the owner/adviser authorise acquisition of an official copy, or confirm that it does not exist?',
  ['C11 dossier, "Union of India v. Sgt Girish Kumar (reported clarification order, 12-10-2026)" (deterministic search: 0 held judgments cite 2026 INSC 1113)',
   'C10 ESC-C10-02', 'C9 LEGAL_ADVISER_ESCALATION.md ESC-02 (a) and ESC-04', 'C11 AFFECTED_RESEARCH_RECORDS.csv (Girish: 9 rows, ACQUIRE_THEN_REVIEW)'],
  [],
  ['(a) Seven records state the clarification\'s content as fact (C9): PEN-045 "The Supreme Court clarified on 12 October 2026 ..."; PEN-048 "squarely rejects universalisation"; DCLR-SC-2026-007 scope_and_caveats "expressly prevents mechanical extension"; DCLR-SC-2026-008 holding; PEN-J-06; and by reference PEN-WF-08, PEN-CS-09, PEN-J-05.',
   '(b) The order is NOT HELD, its identity is UNRESOLVED, no held judgment cites it, and the only URL is a commercial database (a discovery lead, not a source, under CLAUDE.md). The C11 dossier says: do not treat Girish as modified or unmodified on this evidence.'],
  GIR_RECS + ['DCLR-SC-2026-007', 'DCLR-SC-2026-008'],
  ['An official copy of the order. The official lookup earlier met a CAPTCHA; CLAUDE.md requires stopping and reporting, not bypassing.',
   'Approval for a download run (CLAUDE.md).'],
  'P1', 'C9 ESC-02 (a), ESC-04; C10 ESC-C10-02')

q('AQ-PEN-04', T_PEN, 'Is Girish a "case-specific arrears award"?',
  'Is the corpus framing of the February 2026 Girish judgment as a "case-specific arrears award" supported by the judgment itself?',
  ['C9 LEGAL_ADVISER_ESCALATION.md ESC-02 (b)', 'C10 R-GIRISH-T1/T2/T3, P-GIRISH (24 held HC judgments apply Girish after 12-02-2026; 4 read)'],
  ['RD-GIRISH-T3', 'RD-GIRISH-H1', 'R-GIRISH-T1'],
  ['(a) Supports "case-specific": operative para 23 (official pp.16-17) quashes the three-year restriction and grants arrears to the appellants in the listed appeals (C9).',
   '(b) Points the other way: para 18 (official p.13) describes the Government order of 18.04.2016 "to confer upon all eligible pensioners the benefit of arrears of disability pension"; para 22 describes Ram Avtar as in rem (RD-GIRISH-T3); High Courts have applied Girish to non-party claimants (C10 R-GIRISH-T1, T2).',
   'C9 notes that the "not universal" framing currently rests on the unheld clarification (AQ-PEN-03).'],
  GIR_RECS + ['DCLR-SC-2026-007'],
  ['Official Girish copy pages 13 and 16-17 are outside the ad77758d text layer (paras 18 and 23 not re-verified here).', 'The clarification order.'],
  'P1', 'C9 ESC-02 (b)')

q('AQ-PEN-05', T_PEN, 'Ram Avtar identity, the S P Rathore limitation and the reach of "in rem"',
  'May the identity resolution be approved (Ram Avtar = SC order of 10-12-2014 in C.A. 418/2012 and connected appeals; the curated URL, which is the S P Rathore judgment, to be relabelled)? After an official copy of S P Rathore is held, may its limitation be propagated to the broad-banding records? Is Girish\'s "in rem" reading of Ram Avtar binding beyond broad-banding?',
  ['C9 LEGAL_ADVISER_ESCALATION.md ESC-08', 'C10 R-RAMAVTAR-H1, R-RAMAVTAR-T1, R-SPRATHORE-H1, P-RAMAVTAR', 'C11 dossier, Ram Avtar section',
   'C11 AFFECTED_RESEARCH_RECORDS.csv (Ram Avtar: 4 rows, ACQUIRE_THEN_REVIEW)'],
  ['RD-GIRISH-R1', 'R-RAMAVTAR-H1', 'RD-GIRISH-T3', 'R-RAMAVTAR-T1', 'R-SPRATHORE-H1'],
  ['(a) Girish treats Ram Avtar as in rem (RD-GIRISH-T3) and as settling the position (RD-GIRISH-R1).',
   '(b) S P Rathore para 8 reads Ram Avtar as holding "only" that the principle of rounding off applies, and para 9 states that without entitlement there is no rounding off (R-RAMAVTAR-T1, R-SPRATHORE-H1; SCR rendition only).',
   'C11 dossier records whether the "in rem" reading reaches beyond broad-banding as an open question.'],
  recs('Ram Avtar'),
  ['The Ram Avtar order itself (NOT HELD in any store; all citations UNRESOLVED; C9 ESC-04).',
   'An official copy of S P Rathore (C.A. 10870/2018); the limitation now rests on an SCR rendition and an intern mirror (WSB-T-024).',
   'PEN-J-04\'s source URL is an SC office report, which corroborates listing metadata only.'],
  'P2', 'C9 ESC-08; C11 dossier')

q('AQ-PEN-06', T_PEN, 'Dharamvir (1982 Rules) and N C Isaac (2008 Rules)',
  'How far does Union of India v Col N C Isaac (2026 INSC 993; paras 34-35, 39) limit the Dharamvir Singh presumption for claims under the Entitlement Rules 2008, and which pension research records need a rules-version or limitation note?',
  ['C10 ESC-C10-04; R-DHARAMVIR-T1, R-ISAAC-H1, P-DHARAMVIR', 'C11 dossier, Dharamvir section (Isaac not re-read in C11)',
   'C11 AFFECTED_RESEARCH_RECORDS.csv (Dharamvir: 3 rows)', 'CLAUDE.md quality check: "Dharamvir Singh (1982 Rules) vs the Sept 2026 SC ruling on 2008 Rules"'],
  ['RD-DHARAMVIR-H1', 'R-DHARAMVIR-T1', 'R-ISAAC-H1'],
  ['(a) Isaac para 34 records that the 2008 Rules "substantially reproduce the 1982 scheme ... subject only to the limited qualification introduced by the proviso to Rule 7" (R-DHARAMVIR-T1).',
   '(b) C10 notes Isaac para 35 (decisions that followed Dharamvir "without a detailed examination of the evidence" may be revisited) and para 39(iii) (Rule 7 of the 2008 Rules applies and the burden shifts, R-ISAAC-H1). Dharamvir is resolved as cited by 352 held judgments (C11 graph); the statute-link table never infers the Rules version.'],
  recs('Dharamvir') + ['DCLR-SC-2013-N08'],
  ['Isaac is outside the ad77758d text layer; its copy is AUTHENTICATION_PENDING (C10).', 'Which citing judgments concern 2008-Rules claimants (ENT-UNSPECIFIED rows).'],
  'P2', 'C10 ESC-C10-04')

# ---- Own-voice leads -------------------------------------------------------
SCAN_TERMS = ['Ajmer Singh', 'Subramanian', 'Anand Singh Bisht', 'Mafatlal', 'Kanhaiyalal', 'Charanjit', 'C S Gill', 'C.S. Gill',
              'Shatrughan', 'Vatheeswaran', 'Triveniben', 'Advocates-on-Record', 'Advocates on Record', 'SCAORA', 'Samsher',
              'Sriharan', 'Puttaswamy', 'Jabalpur', 'Bhanudas', 'Kharak', 'M P Sharma', 'MP Sharma', 'M.P. Sharma',
              'Joseph Shine', 'Sowmithri', 'Revathi', 'Rewathi', 'Kalyani', 'Saeed Siddiqui', 'Yogendra Kumar', 'Teri Oat']
_RECS = [json.loads(l) for l in IN['RECORDS658'].read_text(encoding='utf-8').splitlines() if l.strip()]
SCAN_HITS = {t: [r['id'] for r in _RECS if re.search(re.escape(t), json.dumps(r, ensure_ascii=False), re.I)] for t in SCAN_TERMS}
SCAN_ANY = sorted({i for v in SCAN_HITS.values() for i in v})
SCAN_NOTE = (f'C12 name scan of records_658.jsonl ({len(_RECS)} records) for the source and target names of these leads '
             f'({", ".join(SCAN_TERMS)}): ' + ('no match.' if not SCAN_ANY else 'matches: ' + ', '.join(SCAN_ANY) + '.') +
             ' Not in AFFECTED_RESEARCH_RECORDS.csv.')

LEAD_ROWS = []   # for the lead table
lead_q = 0
for rows in LEAD_LIST:
    r0 = rows[0]
    cids = [r['candidate_id'] for r in rows]
    att, op = opinion_of(r0['candidate_id'])
    ex_text = trim_excerpt(r0['excerpt'])
    page = int(r0['cue_page'])
    ref = 'LEAD-' + r0['candidate_id']
    ex(ref, r0['source_doc_id'], page, r0['cue_paragraph'] or '-', ex_text, 'COURT_VOICE_OR_OPINION', 'C11 TREATMENT_CANDIDATES.csv excerpt (trimmed to whole words)')
    targets = []
    for r in rows:
        t = r['cited_string']
        t += f" (anchor at p.{r['citation_page']})" if r['citation_page'] else ''
        if r['target_doc_ids']:
            t += f" -> {r['target_doc_ids']}"
        targets.append(t)
    noise = [NOISE[c] for c in cids if c in NOISE]
    cav = sorted({CAVEAT[c] for c in cids if c in CAVEAT})
    for r in rows:
        LEAD_ROWS.append(dict(cid=r['candidate_id'], src=r['source_doc_id'], date=r['source_date'], page=r['cue_page'], para=r['cue_paragraph'],
                              cue=r['cue_text'], attribution=att, opinion=op, raw=r['lead_target_raw'], cand=r['cited_string'],
                              cand_page=r['citation_page'], target_doc=r['target_doc_ids'], binding=r['binding_status'],
                              proposal=r['proposed_relation'] or '(none)', noise=NOISE.get(r['candidate_id'], ''),
                              caveat=CAVEAT.get(r['candidate_id'], '')))
    if r0['candidate_id'] == 'TC-222df5c885ad':
        next(qq for qq in Q if qq['id'] == 'AQ-HCW-01')['excerpts'].insert(0, ref)
        continue  # handled as AQ-HCW-01
    lead_q += 1
    qid = f'AQ-OVR-{lead_q:02d}'
    for d in LEAD_ROWS[-len(rows):]:
        d['qid'] = qid
    in_sep = att in ('SEPARATE_OPINION_LEAD', 'DISSENT_OPINION_LEAD')
    if noise:
        question = (f'Confirm that candidate row(s) {", ".join(cids)} are noise and should be disregarded (C11 disposition V13-01), '
                    'so that no treatment edge is recorded from this sentence.')
        prio = 'P3 (disregard pending withdrawal)'
        competing = ['(a) The tool flagged own-voice overruling wording (' + r0['cue_text'] + ').'] + ['(b) ' + n for n in noise]
    else:
        question = (f'Is the quoted sentence ({r0["source_doc_id"]}, p.{page}) the court\'s own treatment of a prior decision, which decision(s) does it refer to, '
                    'and should any typed edge (overrules / partly overrules / none) be recorded? '
                    + ('The sentence sits in a separate or dissenting opinion, so the tool made no proposal.' if in_sep else
                       'The tool proposes OVERRULES for review only; the target binding is not established.'))
        prio = 'P3'
        competing = [f'(a) Tool reading: own-voice wording "{r0["cue_text"]}"; attribution {att}; opinion {op}; '
                     f'proposal {r0["proposed_relation"] or "none"}.',
                     f'(b) Binding: {r0["binding_status"]}. Candidate target(s): ' + '; '.join(targets) +
                     (f'. Raw target text: "{r0["lead_target_raw"]}"' if r0['lead_target_raw'] else '. No raw target text recorded.')]
        if in_sep:
            competing.append('(c) Per the C11 method, wording in a separate or dissenting opinion "does not itself overrule"; whether the bench majority adopted it is not determined by the tool.')
        competing += cav
    hit_note = 'None identified. ' + SCAN_NOTE
    if r0['source_doc_id'] == 'sc-2000-union-of-india-and-anr-2000insc231':
        hit_note += ' The source judgment corresponds to curated case DCLR-SC-2000-N14 (Charanjit S Gill) per CURATED_53_C11.csv title; disregarding the row does not change that record.'
    q(qid, T_OVR, f'{r0["source_doc_id"]} p.{page}: "{r0["cue_text"]}"', question,
      [f'C11 TREATMENT_CANDIDATES.csv {", ".join(cids)}', 'C11 GRAPH_SUMMARY.json treatment.adviser_rows', 'C11 DISPOSITIONS_relations_c11.md (round 4 P3s)'],
      [ref], competing, [hit_note],
      ['Human confirmation of the reading on the page image (text-layer copy; not a signed court copy).',
       'Resolution of the target citation to a held document (target_state UNRESOLVED).'] +
      (['Withdrawal of the row in the follow-up change (V13-01).'] if noise else []),
      prio, 'C11 adviser queue (30 rows)', extra=[dict(cids=cids, attribution=att, opinion=op, binding=r0['binding_status'], targets=targets)])

# ---- Statutory ---------------------------------------------------------------
AMD = {r['edge_id']: r for r in read_csv('AMD_GRAPH_C10')}
ESCS = {r['matter_id']: r for r in read_csv('ESC_STAT_C10')}


def edges(*ids):
    for i in ids:
        assert i in AMD, i
    return list(ids)


def readings(eid):
    return [s.strip() for s in AMD[eid]['preserved_readings'].split('||') if s.strip()]


STA = []


def sq(qid, title, question, edge_ids, esc, excerpts, competing, affected, missing, prio, origin, owner=''):
    src = [f'C10 amendment_graph_c10.csv {", ".join(edge_ids)}' if edge_ids else 'C10 amendment_graph_c10.csv (no edge)']
    if esc:
        src.append(f'C10 escalation_matters_c10.csv {esc} (status: {ESCS[esc]["escalation_status"]})')
    q(qid, T_STA, title, question, src + origin[1], excerpts, competing, affected, missing, prio, origin[0],
      extra=[dict(edges=edge_ids, statuses=sorted({AMD[e]['c10_status'] for e in edge_ids}), owner=owner)])


sq('AQ-STA-01', 'Army Rule 23(3) caution wording',
   'Does the adviser accept the archival facsimile of the Gazette of 27-11-1954 (S.R.O. 484, printed p.300) as evidence of the notified text of r.23(3) pending a certified copy; is the amendment search sufficient given the remaining gaps; may the interim wording C9-CP-B01 to B06 (which quotes both versions and adopts neither) be displayed; and is the accused\'s right not to make a statement secured independently of r.23(3) (for example by Art. 20(3)), which C9 has not checked?',
   edges('C9-AG-RES-C-01', 'C9-AG-RES-U-01'), 'ESC-R23-3', ['C9R-R23-GAZ', 'C9R-R23-COMP'],
   ['(a) Gazette of 27-11-1954 (facsimile c5ef95a9, printed p.300) and MML copies: "You are not obliged to say anything unless you wish to do so".',
    '(b) India Code compilation (48f52219) p.41: "You are obliged to say anything unless you wish to do so".',
    'C9 records the omission of "not" as a probable transcription discrepancy, not a determined fact; the procedure limbs of r.23(3) read the same in both. Remaining gaps: E-7 of 17-06-1960, 17 S.R.O.s of 1960-1991 not located, S.R.O. 258/2002, S.R.O. 2(E)/2018, anything after 06-06-2022.'],
   ['HCE-010', 'V9-SC-19', 'EV-016', 'KB-006', 'V9-CL-04', 'V9-WF-05'],
   ['A certified copy of S.R.O. 484/1954; the gap instruments, image-checked (C9 ESC-04; U-2).', 'The Gazette facsimile is working-store only (PRESERVATION_RISK, C10).'],
   'P0', ('C9 ESC-03 (P0, reserved RES-r23(3)); C10 ESC-R23-3', ['C9 LEGAL_ADVISER_ESCALATION.md ESC-03', 'C9 UNRESOLVED_MATTERS.md U-2']),
   owner='qualified legal adviser')

sq('AQ-STA-02', 'Unsupported statement that r.23 was amended in 2022',
   'Can the adviser confirm that the earlier research statement "r.23 amended 2022" is not to be relied on, and decide what search is needed to close it?',
   [], 'ESC-R23-2022', [],
   ['(a) Registers: no instrument amends r.23 (31 instruments 1960-2022); S.R.O. 6(E)/2022 amends r.16A(4) only; C8 review RC-01 removed the claim from EV-016, HCE-010 and SC03.',
    '(b) The earlier statement (no supporting instrument ever identified). Status OPEN_UNSUPPORTED.'],
   ['EV-016', 'HCE-010', 'SC03'],
   ['The post-06-06-2022 S.R.O.s (10 pinned candidates), E-7/1960, S.R.O. 258/2002 and the AR hints, image-checked.', 'No held copy in HF/GitHub of any post-2022 Army Rules instrument (C10).'],
   'P2', ('C10 ESC-R23-2022; C9 U-2', ['C9 UNRESOLVED_MATTERS.md U-2']), owner='legal adviser on C-01; owner for acquisitions')

sq('AQ-STA-03', 'Army Rule 168(2) field-punishment words',
   'Which text of r.168(2) is current: the India Code compilation, which still prints the field-punishment words, or S.R.O. 17(E)/1993 item 31, which omits them? (Owner first to register the conflict.)',
   edges('C9-AG-AR168'), 'ESC-R168-2', ['C9R-AR-01'],
   ['(a) ' + readings('C9-AG-AR168')[0], '(b) ' + readings('C9-AG-AR168')[1],
    'Context recorded in C9 U-5: field punishment (AA ss.75-76) was omitted by Act 37/1992 (see AQ-STA-06). Not in any conflict register.'],
   ['(none listed in the C9/C10 artefacts)'],
   ['The 1993 Gazette copy is working-store only (PRESERVATION_RISK).', 'S.R.O. 331/1960 (also r.168(2)) is LOCATED_NOT_ACQUIRED.'],
   'P2', ('C10 ESC-R168-2; C9 U-5', ['C9 UNRESOLVED_MATTERS.md U-5']), owner=AMD['C9-AG-AR168']['decision_owner'])

sq('AQ-STA-04', 'S.R.O. 34 of 1963 identity and the S.R.O. 240/1955 date',
   'After the June-July 1963 Gazette issues are searched: is the held S.R.O. 34 of 05-01-1963 (a r.188(e) declaration) the instrument that later notes list among amendments as "SRO 34 dated 5 Jun 63", and does that affect the amendment chain? Which date of S.R.O. 240/1955 is correct (low consequence)?',
   edges('C9-AG-AR-008', 'C9-AG-SRO240-1955'), 'ESC-SRO34-1963', [],
   ['(a) ' + readings('C9-AG-AR-008')[0], '(b) ' + readings('C9-AG-AR-008')[1],
    'S.R.O. 240/1955: ' + ' vs '.join(readings('C9-AG-SRO240-1955'))],
   ['(none listed in the C9/C10 artefacts)'],
   ['Part II-S4 issues of June-July 1963 (discovery approval AP-C9-05).', 'Held copy 4acdb1a8 is working-store only.'],
   'P3', ('C10 ESC-SRO34-1963; C9 U-1', ['C9 UNRESOLVED_MATTERS.md U-1']), owner=AMD['C9-AG-AR-008']['decision_owner'])

sq('AQ-STA-05', 'S.O. 4010/1986 (CCCM Rules amendment) date',
   'Which date is that of the 1986 MHA notification S.O. 4010 amending the Criminal Courts and Court-Martial (Adjustment of Jurisdiction) Rules 1978? (Owner decision after a page check of the record copy.)',
   edges('C9-AG-CCCM-SO4010'), 'ESC-SO4010-1986', [],
   ['(a) ' + readings('C9-AG-CCCM-SO4010')[0], '(b) ' + readings('C9-AG-CCCM-SO4010')[1], '(c) ' + readings('C9-AG-CCCM-SO4010')[2]],
   ['(none listed in the C9/C10 artefacts)'],
   ['The notification itself (PR #8 scope, AP-C9-01); a page-image check of the record copy.'],
   'P3', ('C10 ESC-SO4010-1986; C9 U-4', ['C9 UNRESOLVED_MATTERS.md U-4']), owner=AMD['C9-AG-CCCM-SO4010']['decision_owner'])

A37 = [f'C9-AG-AA-08-s{i}' for i in range(2, 20)]
sq('AQ-STA-06', 'Commencement of Army (Amendment) Act 37 of 1992',
   'What is the commencement date of the Army (Amendment) Act 1992 (37 of 1992), which prints no commencement clause (AQ-05: effect of an Act with no commencement clause), and therefore of the 18 Army Act provisions it changed (including the omission of field punishment, ss.75-76, and of s.127)?',
   edges(*A37), 'ESC-ACT37-1992', ['C9R-AA-03a', 'C9R-AA-03b', 'C9R-AA-03c'],
   ['(a) Gazette scan f11d443e: assent 06-09-1992, Gazette No.59 of 07-09-1992, no commencement clause.',
    '(b) The compilation prints "w.e.f. 6-9-1992" only at ss.75-76, s.127 and Ch XVI; the other provisions carry undated footnotes. Compiler statements only; no date inferred.'],
   ['CM-011', 'CM-012 (version notes; see AQ-STA-07)'],
   ['Adviser answer to AQ-05; optionally a check of the 1992 Gazette for any notification or corrigendum.', 'All three Act 37/1992 copies are working-store only (PRESERVATION_RISK).'],
   'P1', ('C10 ESC-ACT37-1992; C9 U-3; CLAUDE.md known supersession cases (field punishment, s.127)', ['C9 UNRESOLVED_MATTERS.md U-3', 'C10 STATUTORY_C10_FINDINGS.md (ESCALATED_TO_LEGAL_ADVISER (AQ-05))']),
   owner='legal adviser (AQ-05)')

sq('AQ-STA-07', 'Army Act ss.122-123 limitation (CM-011, CM-012)',
   'Is "Apply the earliest relevant knowledge rule in Section 122(1)" a P1 misdescription or a P2 drafting ambiguity, and may the statute-tracking wording C9-CP-D01 replace it? Do s.122 and s.123(2) apply cumulatively to a person who has ceased to be subject to the Act? Which version applies where the offence or cessation preceded Act 37 of 1992?',
   [], None, [],
   ['(a) F-PROC-006 first pass: P1 misdescription.', '(b) Reviewer A (adopted provisionally, PILOT-01 D-05): P2 drafting ambiguity.',
    'C9 reads compilation e47a4265 p.35: s.122(1)(a) is the default starting point; (b) and (c) are conditional with "whichever is earlier" within each; s.123(2) sets three years after cessation with exclusions; footnotes record substitution by Act 37/1992 ss.9-10. CM-011 omits s.123(2) (F-PROC-007, P1, upheld).'],
   ['CM-011', 'CM-012'],
   ['Decision on AQ-STA-06 (Act 37/1992 commencement).'],
   'P1', ('C9 ESC-05 (LAQ-05, AQ-05)', ['C9 LEGAL_ADVISER_ESCALATION.md ESC-05']), owner='legal adviser')

sq('AQ-STA-08', 'AFT Act commencement vs establishment of the Tribunal',
   'How do the AFT Act s.1(2) commencement (compilation footnote: 15-06-2008 by S.O. 14(E) of 13-06-2008, notification not held) and the establishment of the Tribunal w.e.f. 10-08-2009 (S.R.O. 9(E) of 07-08-2009, held) relate?',
   edges('C9-AG-AFT-00', 'C9-AG-AFTSRO9E2009') if 'C9-AG-AFT-00' in AMD else [], 'ESC-AFT-COMMENCEMENT', [],
   ['(a) ' + ESCS['ESC-AFT-COMMENCEMENT']['reading_a'], '(b) ' + ESCS['ESC-AFT-COMMENCEMENT']['reading_b'],
    'C10: S.R.O. 14(E) of 21-10-2009 (bench jurisdiction) is a number collision, not the s.1(2) notification. Both readings preserved.'],
   ['(none listed in the C9/C10 artefacts)'],
   ['S.O. 14(E)/2008 (discovery approval AP-C9-05).'],
   'P2', ('C10 ESC-AFT-COMMENCEMENT', []), owner='owner (discovery) then legal adviser')

sq('AQ-STA-09', 'AFT procedural rules commencement',
   'May the AFT Procedure Rules 2008, Amendment Rules 2011 and Practice Rules 2009 (held, unregistered) be registered, and on what evidence is the Practice Rules 2009 commencement ("from the date of publication in the official gazette") to be fixed, given that the publication date is not on the held pages?',
   edges('C9-AG-AFTPRAC2009', 'C9-AG-AFT-05'), 'ESC-AFT-PROC-RULES', [],
   ['(a) ' + ESCS['ESC-AFT-PROC-RULES']['reading_a'], '(b) ' + ESCS['ESC-AFT-PROC-RULES']['reading_b'],
    'No inference of the publication date from the notification date (C9/C10).'],
   ['(none listed in the C9/C10 artefacts)'],
   ['Optional ACQ03-032 masthead; owner registration decision (AP-C9-02, revised).'],
   'P3', ('C10 ESC-AFT-PROC-RULES', []), owner='owner (registration)')

sq('AQ-STA-10', 'AFT s.9A under the Finance Act 2017 and the Tribunals Reforms Act 2026',
   'From what date does AFT Act s.9A operate in its 2017 inserted form and in its 2026 substituted form, given that both amending Acts commence by notification (not held) and the compilation gives "w.e.f." dates; and what is the effect of the TRA 2026 repeal of the TRA 2021 with savings?',
   edges('C9-AG-AFT-01', 'C9-AG-AFT-03', 'C9-AG-AFT-04', 'C9-AG-TRA2021-REPEAL'), 'ESC-TRA2026-COMMENCEMENT',
   ['C9R-RD-FIN17-02', 'C9R-AFT-05', 'C9R-TRA-02', 'C9R-AFT-06'],
   ['(a) ' + readings('C9-AG-AFT-01')[0] + ' || (b) ' + readings('C9-AG-AFT-01')[1],
    '(a) ' + readings('C9-AG-AFT-03')[0] + ' || (b) ' + readings('C9-AG-AFT-03')[1]],
   ['(none listed in the C9/C10 artefacts)'],
   ['The Finance Act 2017 Part XIV notification and the TRA 2026 commencement notification(s) (no candidate located).'],
   'P2', ('C10 ESC-TRA2026-COMMENCEMENT; C9 U-5', ['C9 UNRESOLVED_MATTERS.md U-5']), owner='owner (discovery) then legal adviser')

AR_AQ05 = [e for e, r in AMD.items() if r['c10_status'] == 'UNRESOLVED_COMMENCEMENT' and r['target_instrument_id'] == 'I-AR-1954']
sq('AQ-STA-11', 'Army Rules amending instruments with no commencement clause (AQ-05)',
   'On what date do the Army Rules 1954 (S.R.O. 484) and the amending S.R.O.s that print no commencement clause take effect (AQ-05)? Commencement is preserved as NOT_STATED_PENDING_ADVICE; no date is inferred.',
   edges(*AR_AQ05), None, [],
   ['No competing readings recorded: each edge records "commencement not evidenced" (NOT_STATED_PENDING_ADVICE, AQ-05); the authority matrix states that a publication date is never assumed to be the commencement date (an evidence rule, not a statement of law).'],
   ['(none listed in the C9/C10 artefacts)'],
   ['Adviser answer to AQ-05.'],
   'P2', ('C10 amendment_graph_c10.csv (AQ-05); C10 CORPUS_AUTHORITY_MATRIX.md section 3', []), owner='legal adviser (AQ-05)')

sq('AQ-STA-12', 'Army Rule 182 as substituted by S.R.O. 17(E)/1993 item 36',
   'Which text of r.182 (proceedings of a court of inquiry not admissible) is operative: the 1993 substitution (S.R.O. 17(E)/1993 item 36) or the 1954 notified text, as compared with the compilation and MML 2?',
   edges('C9-AG-RES-SC4-01'), None, ['C12-AR182-COMP'],
   ['(a) ' + readings('C9-AG-RES-SC4-01')[0][:400] + ' ...', '(b) ' + readings('C9-AG-RES-SC4-01')[1][:400] + ' ...',
    'Status: OPEN (no corrigendum searched or located). C10 review CL-01 notes this edge does hold quoted readings.'],
   ['(none listed in the C9/C10 artefacts)'],
   ['A corrigendum search for S.R.O. 17(E)/1993.'],
   'P2', ('C10 amendment_graph_c10.csv; C5 conflict SC4-01', []), owner=AMD['C9-AG-RES-SC4-01']['decision_owner'])

sq('AQ-STA-13', 'Army Rule 192 proviso (reduction in pay grade)',
   'Which text of the r.192 proviso is operative (amending instrument vs official consolidation vs manual; manual footnote cites S.R.O. 215)?',
   edges('C9-AG-RES-C-02'), None, [],
   ['(a) ' + readings('C9-AG-RES-C-02')[0], '(b) ' + readings('C9-AG-RES-C-02')[1]],
   ['(none listed in the C9/C10 artefacts)'],
   ['Itemised readings are not in the C5 conflict register; S.R.O. 215/1965 has no commencement clause (C9-AG-AR-011).'],
   'P3', ('C10 amendment_graph_c10.csv; C5 conflict C-02', []), owner=AMD['C9-AG-RES-C-02']['decision_owner'])

sq('AQ-STA-14', 'Army Rule 177(1)-(2) (Court of Inquiry)',
   'Which text of r.177(1)-(2) is operative? The conflict is CONFLICTING pending text comparison and legal review.',
   edges('C9-AG-RES-C-03'), None, [],
   ['(a) ' + readings('C9-AG-RES-C-03')[0], '(b) ' + readings('C9-AG-RES-C-03')[1]],
   ['(none listed in the C9/C10 artefacts)'],
   ['Text comparison (not yet done).'],
   'P3', ('C10 amendment_graph_c10.csv; C5 conflict C-03', []), owner=AMD['C9-AG-RES-C-03']['decision_owner'])

sq('AQ-STA-15', 'Army Rule 193 (prescribed officer, AA s.90(i) and s.91(i))',
   'Does r.193 cover s.90(i) as well as s.91(i), and which instrument gives the current text ("an Army" vs "the Army")?',
   edges('C9-AG-RES-C-08', 'C9-AG-RES-U-04', 'C9-AG-RES-U-07'), None, ['C12-AR193-COMP'],
   ['(a) S.R.O. 302/1987 substitutes r.193 for s.91(i) only ("Chief of the Army Staff or the Officer Commanding an Army") (C-08 evidence 1).',
    '(b) India Code compilation p.209 extends r.193 to s.90(i) and s.91(i), "officer commanding the Army" (C-08 evidence 2).',
    'U-04: the extension to s.90(i) is not supported by any located instrument; either an unlocated instrument added it or the compilation is in error (not determined). U-07: the compilation matches the 1993 substitution on the located evidence; open points remain.'],
   ['(none listed in the C9/C10 artefacts)'],
   ['Itemisation of S.R.O. 17(E)/1993 by WS-A and transcription of the 1954 base text; unlocated instruments (E-7/1960, S.R.O. 258/2002, post-2022).'],
   'P2', ('C10 amendment_graph_c10.csv; C5 conflicts C-08, U-04, U-07', []), owner=AMD['C9-AG-RES-C-08']['decision_owner'])

sq('AQ-STA-16', 'Army Rule 194 (prescribed officer, AA s.93)',
   'Is the operative r.194 the 1989 substituted text (S.R.O. 332/1989, which adds "or the Officer Commanding an Army" for officers)? This is a PROPOSAL pending legal review (AQ-02).',
   edges('C9-AG-RES-C-09', 'C9-AG-RES-U-08'), None, ['C12-AR194-COMP'],
   ['(a) S.R.O. 332/1989 (Gazette 02-12-1989 p.736) and MML 2 p.227 carry the added words.',
    '(b) The India Code compilation p.209 lacks the added words.', 'No later instrument affecting r.194 located (31 instruments; gaps AR-001, AR-030, AR-036).'],
   ['(none listed in the C9/C10 artefacts)'],
   ['The gap instruments.'],
   'P2', ('C10 amendment_graph_c10.csv; C5 conflicts C-09, U-08 (AQ-02)', []), owner=AMD['C9-AG-RES-C-09']['decision_owner'])

sq('AQ-STA-17', 'Last amendment before S.R.O. 17(E)/2019 (footnote discrepancy)',
   'Which instrument was the last amendment of the Army Rules before S.R.O. 17(E)/2019? (Documentary; owner decision.)',
   edges('C9-AG-LASTAMD-2019'), None, [],
   ['(a) ' + readings('C9-AG-LASTAMD-2019')[0], '(b) ' + readings('C9-AG-LASTAMD-2019')[1]],
   ['(none listed in the C9/C10 artefacts)'],
   ['None identified beyond owner review; S.R.O. 17(E)/2019 born-digital signature fails (P-D2a).'],
   'P3', ('C10 amendment_graph_c10.csv; C8-CR-14', []), owner=AMD['C9-AG-LASTAMD-2019']['decision_owner'])

sq('AQ-STA-18', 'Commencement of Acts 19 of 1955 and 13 of 1975 (Army Act amendments)',
   'From what dates do the Commanders-in-Chief (Change in Designation) Act 1955 (commencement by notification) and the Air Force and Army Laws (Amendment) Act 1975 (no commencement section; s.4(2) saving refers to 25-01-1975) take effect for the Army Act provisions they changed?',
   edges('C9-AG-AA-01', 'C9-AG-AA-06'), None, [],
   ['C9-AG-AA-01: ' + AMD['C9-AG-AA-01']['commencement_as_printed'],
    'C9-AG-AA-06: ' + ' || '.join(readings('C9-AG-AA-06')),
    'C9 U-6 carries Act 13/1975 "w.e.f. 25-1-1975" as OQ-A-04.'],
   ['(none listed in the C9/C10 artefacts)'],
   ['The Act 19/1955 commencement notification.'],
   'P3', ('C10 amendment_graph_c10.csv; C9 U-6 (OQ-A-04)', ['C9 UNRESOLVED_MATTERS.md U-6']), owner='legal adviser (AQ-05 / OQ-A-04)')

sq('AQ-STA-19', 'IPC, CrPC and Evidence Act repeal by BNS, BNSS and BSA: commencement evidence and references in military law',
   'On what evidence is the 01-07-2024 commencement of the BNS, BNSS and BSA to be recorded (notifications not held), and how do Army Act and Army Rules references to the CrPC (e.g. r.133(3) to CrPC s.340) and rules made under the CrPC (CCCM Rules 1978) read after BNSS s.531 and its saving s.531(2)(b)?',
   edges('C9-AG-BNS-REPEAL', 'C9-AG-BNSS-REPEAL', 'C9-AG-BSA-REPEAL'), None, ['C9R-BNSS-03'],
   ['C10 changed C9-AG-BNSS-REPEAL and C9-AG-BSA-REPEAL from NOT_LOCATED to UNRESOLVED_COMMENCEMENT: the repealing instruments are held (compilations and Hindi Gazette texts) but the commencement notifications (e.g. S.O. 849(E)) are not.',
    'C9 U-5 records how such references read after repeal as a legal question; no reading is proposed.'],
   ['(6 KB records cite BNS s.358 per C9-AG-BNS-REPEAL; ids not listed there)'],
   ['The BNS/BNSS/BSA commencement notifications (C5-ACQ-05); any post-BNSS adjustment rules; the CCCM Rules 1978 (PR #8).'],
   'P1', ('C9 U-5; C10 amendment_graph_c10.csv; CLAUDE.md known supersession case (IPC to BNS from 1 July 2024)', ['C9 UNRESOLVED_MATTERS.md U-5']), owner='legal adviser (interpretation); owner (acquisition)')

sq('AQ-STA-20', 'Army Act s.133 and the Bharatiya Sakshya Adhiniyam 2023',
   'From what date, and for which pending proceedings, is AA s.133\'s reference to the Indian Evidence Act 1872 to be read as a reference to the BSA (General Clauses Act s.8; BSA s.170(2))?',
   [], None, ['C9-S133', 'C9-BSA-1-2', 'C9-BSA-170-2'],
   ['C9 classifies this as an interaction between two Acts, not a source conflict: AA s.133 still names the 1872 Act "subject to the provisions of this Act"; BSA s.1(2) applies the BSA to Courts-martial; BSA s.170(2) saves the IEA for pending proceedings; the 01-07-2024 date comes from a compilation footnote.',
    'Severity recalibration S-02 proposes lowering the CM-025 omission from P1 to P2; CIV-034\'s title states a timeless conclusion.'],
   ['CM-025', 'EV-003', 'CIV-034'],
   ['The BSA commencement notification (not held).'],
   'P1', ('C9 ESC-07 (P1; C-07, LAQ-01)', ['C9 LEGAL_ADVISER_ESCALATION.md ESC-07']), owner='legal adviser')

sq('AQ-STA-21', 'ADM-022 and Army Act s.26(2) (wording confirmation)',
   'May "explicitly directs complaint to next superior" in ADM-022 be replaced by the permissive statutory wording (C9-CP-C01, superseding E8-CP-08)? The adviser need only confirm the wording.',
   [], None, ['C9-S26'],
   ['C9: s.26(2) and s.26(1) are permissive; s.26(3) imposes the receiving officer\'s duty. ADM-SC-06 and ADM-020 are already consistent with the statute.'],
   ['ADM-022', 'ADM-SC-06', 'ADM-020'],
   ['No Gazette copy of the 1950 Act is held; the evidence is a government compilation only.'],
   'P2', ('C9 ESC-09 (P2, Part 3)', ['C9 LEGAL_ADVISER_ESCALATION.md ESC-09']), owner='legal adviser (wording only)')

# ---- Authority ranking ---------------------------------------------------------
q('AQ-AUT-01', T_AUT, 'Relative order of open-data bulk copies and law-report (SCR) renditions',
  'Is the authority-matrix order correct that places open-data bulk copies of Supreme Court judgments (tier 4: e.g. the AWS S3 buckets that supplied all 346 data/raw/sci and 3,605 data/raw/hc files) above law-report renditions including SCR (tier 5), under a heading that says a lower tier never overrides a higher one on content, and that keeps bulk copies at tier 2 for High Courts? If not settled, should the order be marked "not settled pending legal-side review"?',
  ['C10 DISPOSITIONS_final_head_confirmations.md RR-04 (ESCALATED, legal side)', 'C10 final_head_confirmations/fable_review_7ccb9c2e.md RR-04',
   'C10 CORPUS_AUTHORITY_MATRIX.md section 3 ("Supreme Court judgments" tiers 1-6; "High Court and AFT judgments" tiers 1-3)'],
  [],
  ['(a) Current order (C10 matrix): tier 4 bulk copies ("Provenance of the copy is documented, but the copy is not court-hosted or certified") above tier 5 SCR renditions ("A comparator only ... never treated as a signed original"). No basis is stated.',
   '(b) Reviewer RR-04: the order needs legal-side confirmation; "it is not a finding that the order is wrong". Requested action: state the basis, or mark tiers 4/5 (and HC tier 2) as not settled.',
   'Documentary observation for the adviser (no conclusion): many held SC copies are labelled SCR_REPORT_RENDITION_AWS_ESCR_MIRROR (C11 dossier), i.e. law-report renditions obtained from an AWS mirror, so a single copy may fit the descriptions of both tier 4 and tier 5. The disposition records that the ranking is not used to change any status.'],
  ['(no research record changes on the ranking; it governs copy precedence for SCR-only cases such as Tarsem, Shri Kant Sharma, S P Rathore)'],
  ['Legal-side confirmation of the basis for the order.'],
  'P2', 'C10 RR-04')

q('AQ-AUT-02', T_AUT, 'SCR-format renditions as comparators and locators',
  'May the raw-store SCR-format copies (AWS mirror of e-SCR) be registered as reported-version comparators (AP-C9-02), and may e-SCR report pages be cited as locators? They are not signed court originals.',
  ['C10 ADVISER_ESCALATIONS_C10.csv ESC-C10-05 (relates to LG-12; AP-C9-02; P-D3)', 'C9 LEGAL_ADVISER_ESCALATION.md ESC-01 (Tarsem: AP-C9-02 as drafted covers statutory copies only)',
   'C9 DECISION_MATRIX_C9.md P-D3 (JUDIS renditions), RAW-01'],
  ['RD-PARASHOTAM-T1'],
  ['C10 matrix tier 5: law-report renditions are "a comparator only, after its own identity and provenance are recorded". The C11 dossier uses SCR text-layer page numbers as locators throughout (e.g. Parashotam para 32 at SCR p.17 vs official p.22), and states that the official-copy locator was not re-read.',
   'No artefact proposes treating an SCR rendition as a signed original.'],
  ['DCLR-SC-2008-N10', 'DCLR-SC-2015-N06', 'and every record whose only held copy is an SCR rendition'],
  ['Owner/adviser decision on extending AP-C9-02 to judicial renditions.'],
  'P2', 'C10 ESC-C10-05')

# ---- Legal-approval role -------------------------------------------------------
q('AQ-ROL-01', T_ROL, 'Approval tier and channel for operational use',
  'For each output class (authoritative template, mandatory constraint, procedural checklist, definitive advisory), is a designated legal-adviser decision sufficient, or is formal JAG validation required? How does an approval artefact reach an air-gapped deployment (signed release import only, or Admin transcription of an external artefact with the artefact attached, recording not being approving)?',
  ['scratchpad/c12/reviews/fable_review_pr46_c69eee41.md F-01 (P2) and capability rows 8 and 10', 'PR #46 blueprint at c69eee41: Studio 3.2 and 8.1; Vision 2 and 6; ADR-0002 "Not decided"; ADR-0003 "Outstanding" (as cited by F-01)'],
  [],
  ['F-01 records that the gate depends on an "attributable competent legal approval" artefact but no role, operation or channel can record one: only Admin and User exist, User has no shared writes, and Admin action is explicitly not legal approval.',
   'The controlling policy treats a designated legal-adviser decision and formal JAG validation as separate gates (per F-01); the blueprint does not say which applies. Result today: fail-closed.'],
  ['(none: no record is operationally approved; 658 records and 53 cases remain research/unapproved)'],
  ['An owner/legal-side decision on the tier per output class; an ADR entry recording it, or recording it as a blocking open decision.'],
  'P1', 'PR #46 review F-01')

q('AQ-ROL-02', T_ROL, 'Who decides "credible material" and who re-enables a blocked scope',
  'Who decides that new material is "credible" enough to mark an affected scope REVALIDATION_REQUIRED/BLOCKED, and who may re-enable it? Is the Vision\'s "Legal review workspace" Admin-operated, or deferred?',
  ['fable_review_pr46_c69eee41.md F-01, F-12 (INFO: "credible material" used as the blocking threshold in six files without criteria)'],
  [],
  ['F-01 records the gap; F-12 notes no criteria are defined. No artefact proposes a decider.'],
  ['(none)'],
  ['Named decider and criteria.'],
  'P2', 'PR #46 review F-01, F-12')

q('AQ-ROL-03', T_ROL, 'Who reviews proposed supersession and overruling edges, and who confirms AI page readings',
  'Who on the legal side reviews the proposed supersession, overruling and amendment edges in this package (an open question in the project brief), and who performs the human or reviewer-attested confirmation of AI page readings that option B2 of C9 decision P-B (recommended, not adopted) would require before an entry can create an anchor?',
  ['/home/user/mimamsa-corpus/CLAUDE.md, "Open questions to settle early"; Relations ("Anything other than cites needs human verification")',
   'C9 DECISION_MATRIX_C9.md P-B (recommendation B2: AI readings are supporting evidence only; nothing adopted)'],
  [],
  ['No competing readings: a role assignment. Every excerpt in this package is an AI reading and is not human-confirmed.'],
  ['(all questions in this register)'],
  ['A named reviewer or role.'],
  'P1', 'CLAUDE.md open questions; C9 P-B')


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------
COMPARATOR = {'wt:fe19875b': P23, 'wt:4f7ea3a4': GIR}   # official copy -> SCR rendition held in the text layer


def run_verification():
    out = []
    for ref, e in X.items():
        status, where = verify(e['doc'], e['page'], e['quote'])
        e['status'], e['where'] = status, where
        if status.startswith('NO_TEXT_FILE'):
            for k, rend in COMPARATOR.items():
                if k in e['doc']:
                    pg = pages_of(rend)
                    hits = [p for p, b in pg.items() if squash(e['quote']) in squash(b)]
                    if not hits:
                        hits = [p for p in pg if p + 1 in pg and squash(e['quote']) in squash(pg[p] + pg[p + 1])]
                    e['where'] = (f'comparator {rend} p.' + ','.join(map(str, hits))) if hits else f'comparator {rend}: not found'
        out.append(e)
    return out


VER = run_verification()
used = {r for qq in Q for r in qq['excerpts']}
unused = [r for r in X if r not in used]
assert not unused, unused
bad = [e for e in VER if e['status'] in ('NOT_FOUND', 'FOUND_ON_OTHER_PAGE')]

# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------


def pin(e):
    if e['para'] in ('', '-'):
        para = ''
    elif re.match(r'^(r\.|s\.|ss\.|Ch )', e['para']):
        para = f", {e['para']}"
    else:
        para = f", para {e['para']}"
    return f"{e['doc']} p.{e['page']}{para}"


def vtag(e):
    return {'VERIFIED_ON_STATED_PAGE': 'verified (stated page)',
            'VERIFIED_SPANNING_PAGE_BREAK': f"verified ({e['where']}, across page break)",
            'FOUND_ON_OTHER_PAGE': f"FOUND ON OTHER PAGE {e['where']}",
            'NOT_FOUND': 'NOT FOUND'}.get(e['status'], 'not re-verifiable here (no text file at ad77758d; carried from ' + e['origin'] + ')'
                                           + (f"; same words found in the SCR rendition ({e['where'][len('comparator '):]}); such hits can include reporter headnote pages, which are not court voice" if e['where'].startswith('comparator') and 'not found' not in e['where'] else ''))


def write_csv():
    p = PKG / 'ADVISER_QUESTIONS.csv'
    with open(p, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['id', 'topic', 'question', 'sources', 'pinpoints', 'competing_readings', 'affected_records', 'missing_evidence', 'priority'])
        for qq in Q:
            pins = []
            for r in qq['excerpts']:
                e = X[r]
                pins.append(f"{r}: {pin(e)} [{e['status']}]")
            srcs = list(qq['sources'])
            for x in qq['extra']:
                if x.get('edges'):
                    srcs.append('edge statuses: ' + ', '.join(x['statuses']) + (f"; decision owner: {x['owner']}" if x.get('owner') else ''))
            w.writerow([qq['id'], qq['topic'], qq['question'], ' | '.join(srcs), ' | '.join(pins) or '(no quoted excerpt; see sources)',
                        ' | '.join(qq['competing']), '; '.join(qq['affected']), ' | '.join(qq['missing']), qq['priority']])
    return p


def write_verification():
    p = PKG / 'EXCERPT_VERIFICATION.csv'
    with open(p, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['excerpt_ref', 'doc_id_or_copy', 'stated_page', 'paragraph', 'kind', 'quote', 'verification', 'found_at', 'origin', 'note', 'used_by'])
        for e in VER:
            by = [qq['id'] for qq in Q if e['ref'] in qq['excerpts']]
            w.writerow([e['ref'], e['doc'], e['page'], e['para'], e['kind'], e['quote'], e['status'], e['where'], e['origin'], e['note'], ';'.join(by)])
    return p


def md_escape(s):
    return s.replace('|', '\\|').replace('\n', ' ')


def write_md():
    L = []
    a = L.append
    a('# Legal-adviser review package, Cycle 12 (Mimamsa)')
    a('')
    a(BANNER)
    a('')
    a('Built by `tools/build_adviser_package.py` from existing artefacts only (see `PROVENANCE_C12.md`). No source file was modified; no record, register, edge or status was changed.')
    a('')
    by_topic = Counter(qq['topic'] for qq in Q)
    a('## 1. How to use this package')
    a('')
    a('- **What it is.** One register of every open question that earlier cycles (C9, C10, C11) and the PR #46 review escalated to the legal side, with the source wording and exact pinpoints, the readings already recorded in the artefacts, the research records affected, and the evidence still missing. It answers none of the questions.')
    a('- **Where to start.** Section 2 lists every question with its priority. P0 and P1 mark the items the source artefacts treat as most consequential. Each question in sections 3-8 has the same parts: question, sources, excerpts with pinpoints, competing readings, affected records, missing evidence.')
    a('- **Pinpoints.** `p.` is the PDF page of the text layer at raw-data commit `ad77758d` of `/home/user/c7` (`data/text/<doc_id>.txt`, `[[page N]]` markers). Many Supreme Court copies there are SCR renditions from the AWS e-SCR mirror, not signed court originals; their page numbers can differ from the official copy (for example Parashotam para 32 is SCR p.17 but official p.22). `para` is the printed paragraph number. Copies named `official copy wt:<sha>` are in the C5 working store and are not in the text layer.')
    a('- **Excerpt checks.** Every quoted excerpt was re-checked by this build, whitespace-insensitive and verbatim, on the stated page of the `ad77758d` text file where one exists. Results are shown next to each excerpt and in `EXCERPT_VERIFICATION.csv`. Excerpts from copies that are not in the text layer are marked "not re-verifiable here" and carry the earlier cycle\'s check.')
    a(f'- **Verification summary.** {len(VER)} excerpts: ' + ', '.join(f'{k} {v}' for k, v in sorted(Counter(e["status"] for e in VER).items())) + '.')
    a('- **Voice.** Excerpts are labelled COURT_VOICE (the court\'s own words), LATER_RELIANCE (a later court\'s words), EDITORIAL (reporter matter; never the court\'s treatment), BENCH, STATUTE_COMPILATION (India Code compilation; a compiler\'s "w.e.f." note is a compiler statement only) or STATUTE_GAZETTE.')
    a('- **Priorities.** Where the source artefact states a priority (C9 binding scale: P0 r.23(3); P1 Tarsem/Girish, Parashotam, s.133) it is carried. Otherwise the priority is a triage order for sequencing only. The adviser sets the final priority.')
    a('- **Known noise.** Four of the 30 C11 adviser rows are known noise (C11 disposition V13-01): TC-9b500dbe0d15 (C.S. Gill p.19), TC-e8e740a5df2f (Shatrughan Chauhan p.54), TC-8eee72cd601c and TC-741f5ae7f6ab (SCAORA). They are kept and marked **DISREGARD (V13-01)**, so the adviser can confirm the withdrawal.')
    a('- **Recording a decision.** Record each answer against its question id, outside this package (a decision record or the AUTH-LEDGER process). Applying any decision is a separate reviewed change with owner approval. This package is not edited to record decisions.')
    a('')
    a('## 2. Question register')
    a('')
    a('| Topic | Questions |')
    a('| --- | --- |')
    for t in [T_HCW, T_PEN, T_OVR, T_STA, T_AUT, T_ROL]:
        a(f'| {t} | {by_topic[t]} |')
    a(f'| **Total** | **{len(Q)}** |')
    a('')
    a('| Id | Priority | Topic | Question (short) |')
    a('| --- | --- | --- | --- |')
    for qq in Q:
        a(f"| {qq['id']} | {qq['priority']} | {qq['topic'].split(' (')[0]} | {md_escape(qq['title'])} |")
    a('')

    def qblock(qq):
        a(f"### {qq['id']}: {qq['title']}")
        a('')
        a(f"**Priority:** {qq['priority']}. **Origin:** {qq['origin']}.")
        a('')
        a(f"**Question.** {qq['question']}")
        a('')
        a('**Sources.**')
        for s in qq['sources']:
            a(f'- {s}')
        for x in qq['extra']:
            if x.get('edges'):
                a(f"- Edge statuses (C10): {', '.join(x['statuses'])}. Decision owner: {x.get('owner') or '-'}. Edges: {', '.join(x['edges'])}.")
        a('')
        if qq['excerpts']:
            a('**Excerpts with pinpoints.**')
            a('')
            a('| Ref | Pinpoint | Voice | Excerpt (verbatim) | Check |')
            a('| --- | --- | --- | --- | --- |')
            for r in qq['excerpts']:
                e = X[r]
                note = f" ({e['note']})" if e['note'] else ''
                a(f"| {r} | {md_escape(pin(e))} | {e['kind']} | \"{md_escape(e['quote'])}\"{md_escape(note)} | {md_escape(vtag(e))} |")
            a('')
        a('**Competing readings (as recorded in the artefacts; no view is taken).**')
        for c in qq['competing']:
            a(f'- {c}')
        a('')
        a('**Affected research records.** ' + ('; '.join(qq['affected']) if qq['affected'] else '-'))
        a('')
        a('**Evidence still missing.**')
        for m in qq['missing']:
            a(f'- {m}')
        a('')

    sec = 3
    for t in [T_HCW, T_PEN]:
        a(f'## {sec}. {t}')
        a('')
        if t == T_HCW:
            a('Affected-record basis: C11 `AFFECTED_RESEARCH_RECORDS.csv` (13 Parashotam rows, 2 Shri Kant Sharma rows; status PROPOSAL_NOT_APPLIED_ADVISER_REVIEW).')
        else:
            a('Affected-record basis: C11 `AFFECTED_RESEARCH_RECORDS.csv` (Tarsem 6, Girish 9, Ram Avtar 4, Dharamvir 3 rows). The 12-10-2026 clarification order is NOT HELD and NOT CITED in any held judgment: its content is unknown.')
        a('')
        for qq in Q:
            if qq['topic'] == t:
                qblock(qq)
        sec += 1

    a(f'## {sec}. {T_OVR}')
    a('')
    a('The C11 relations tool queued 30 rows at LEGAL_INTERPRETATION_ADVISER_REVIEW (GRAPH_SUMMARY.json `treatment.adviser_rows`). They are grouped below into source sentences. One row (TC-222df5c885ad, Parashotam -> Shri Kant Sharma) is BOUND and is handled as AQ-HCW-01. The other 29 rows form '
      f'{lead_q} leads, AQ-OVR-01 to AQ-OVR-{lead_q:02d}. No target in these 29 rows is resolved to a held document (target_state UNRESOLVED). ' + SCAN_NOTE)
    a('')
    a('Opinion labels come from SCR page headers. Per the C11 method, wording in a separate or dissenting opinion is sent as a lead with no proposal, because such an opinion "does not itself overrule". Known label errors are listed in the caveat column (C11 disposition V13-02 to V13-04).')
    a('')
    a('**All 30 adviser rows.**')
    a('')
    a('| Row | Question | Source (date) | Cue p./para | Cue | Opinion (attribution) | Candidate target (anchor p.) | Binding status | Proposal | Noise / caveat |')
    a('| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |')
    for d in LEAD_ROWS:
        tgt = d['cand'] + (f" (p.{d['cand_page']})" if d['cand_page'] else '') + (f" -> {d['target_doc']}" if d['target_doc'] else '')
        flag = ('**DISREGARD (V13-01)** ' + d['noise']) if d['noise'] else d['caveat']
        a(f"| {d['cid']} | {d.get('qid', 'AQ-HCW-01')} | {d['src']} ({d['date']}) | {d['page']}/{d['para'] or '-'} | {md_escape(d['cue'])} | {md_escape(d['opinion'])} ({d['attribution']}) | {md_escape(tgt)} | {md_escape(d['binding'])} | {d['proposal']} | {md_escape(flag)} |")
    a('')
    for qq in Q:
        if qq['topic'] == T_OVR:
            x = qq['extra'][0]
            noise = any(c in NOISE for c in x['cids'])
            if noise:
                qq['title'] = qq['title'] + ' [DISREGARD (V13-01)]'
            qblock(qq)
    sec += 1
    a(f'## {sec}. {T_STA}')
    a('')
    amd = read_csv('AMD_GRAPH_C10')
    cnt = Counter(r['c10_status'] for r in amd)
    a(f"Basis: C10 `amendment_graph_c10.csv` ({len(amd)} edges: " + ', '.join(f'{k} {v}' for k, v in sorted(cnt.items())) +
      '), C10 `escalation_matters_c10.csv` (9 matters), and the C9 escalation files. All 15 DISPUTED_PRESERVE_BOTH edges and all 43 UNRESOLVED_COMMENCEMENT edges are covered by AQ-STA-01 to AQ-STA-21 (see the coverage table at the end of this section). Readings are preserved, not resolved. A compilation "w.e.f." note is a compiler statement, and a publication date is never assumed to be a commencement date (C10 evidence rule).')
    a('')
    for qq in Q:
        if qq['topic'] == T_STA:
            qblock(qq)
    a('**Edge coverage.**')
    a('')
    a('| Edge | C10 status | Question |')
    a('| --- | --- | --- |')
    cov = {}
    for qq in Q:
        for x in qq['extra']:
            for e in x.get('edges', []):
                cov.setdefault(e, qq['id'])
    for r in amd:
        if r['c10_status'] in ('DISPUTED_PRESERVE_BOTH', 'UNRESOLVED_COMMENCEMENT'):
            a(f"| {r['edge_id']} | {r['c10_status']} | {cov.get(r['edge_id'], 'NOT COVERED')} |")
    a('')
    sec += 1
    for t in [T_AUT, T_ROL]:
        a(f'## {sec}. {t}')
        a('')
        for qq in Q:
            if qq['topic'] == t:
                qblock(qq)
        sec += 1
    a(f'## {sec}. Provenance')
    a('')
    a('See `PROVENANCE_C12.md` for every input file (path, sha256, git state) and commit. Excerpt checks: `EXCERPT_VERIFICATION.csv`. Machine-readable register: `ADVISER_QUESTIONS.csv`.')
    a('')
    a(BANNER)
    a('')
    p = PKG / 'ADVISER_PACKAGE_C12.md'
    p.write_text('\n'.join(L), encoding='utf-8')
    return p, cov


def write_provenance(cov_missing):
    L = []
    a = L.append
    a('# Provenance note: C12 legal-adviser package')
    a('')
    a(BANNER)
    a('')
    head = git('rev-parse', 'HEAD', repo=C12W).strip()
    a(f'- Built by: `tools/build_adviser_package.py` (automated agent, Claude Opus 5.5 subagent), {Path(IN["BRIEF"]).name} rules followed: no download, no commit, no source modified.')
    a(f'- Worktree holding the C9-C11 audit inputs: `{C12W}` at HEAD `{head}`. Git state per file is given below (`committed-clean` = tracked and identical to HEAD).')
    rels = [str(pth.relative_to(C12W)) for pth in IN.values() if str(pth).startswith(str(C12W))]
    same = subprocess.run(['git', '-C', str(C12W), 'diff', '--quiet', '35ffaed2', 'HEAD', '--', *rels]).returncode == 0
    a(f'- The worktree HEAD was `35ffaed2` when this task started; worktree inputs unchanged between `35ffaed2` and `{head[:8]}`: {"yes" if same else "NO"}.')
    a(f'- Raw-data / text-layer repository: `{C7}`; text layer read at commit `{git("rev-parse", TEXT_COMMIT).strip()}` (`data/text/<doc_id>.txt`).')
    for c in C9_COMMITS:
        a(f'- C9 commit `{git("rev-parse", c).strip()}`: {git("log", "-1", "--format=%s", c).strip()}')
    a('')
    a('## Input files')
    a('')
    a('| Key | Path | sha256 | Git state |')
    a('| --- | --- | --- | --- |')
    for k, pth in IN.items():
        try:
            rel = pth.relative_to(C12W)
            st = git('status', '--porcelain', '--', str(rel), repo=C12W).strip()
            tracked = git('ls-files', '--', str(rel), repo=C12W).strip()
            state = 'untracked' if not tracked else ('modified' if st else 'committed-clean')
        except ValueError:
            state = 'outside worktree'
            try:
                r2 = subprocess.run(['git', '-C', str(pth.parent), 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True)
                if r2.returncode == 0:
                    state += f' (repo HEAD {r2.stdout.strip()})'
            except Exception:
                pass
        a(f'| {k} | `{pth}` | `{sha256(pth)}` | {state} |')
    a('')
    a('## C9 files read from git (not from a working tree)')
    a('')
    a('| Commit | Path | Blob |')
    a('| --- | --- | --- |')
    for c in C9_COMMITS:
        for f in C9_FILES:
            a(f'| `{c}` | `{C9P}/{f}` | `{git("rev-parse", f"{c}:{C9P}/{f}").strip()}` |')
    a('')
    a('`DECISION_MATRIX_C9.md` and `STATUTORY/UNRESOLVED_MATTERS.md` are identical at both commits. `CORRECTIONS/LEGAL_ADVISER_ESCALATION.md` differs; the package uses the later version at `a61c0e57` (the final head accepted in C10 DISPOSITIONS_final_head_confirmations.md).')
    a('')
    a('## Text-layer documents read for excerpt checks')
    a('')
    docs = sorted({e['doc'] for e in VER if pages_of(e['doc']) is not None})
    a('| doc_id | blob at ad77758d |')
    a('| --- | --- |')
    for d in docs:
        a(f'| {d} | `{git("rev-parse", f"{TEXT_COMMIT}:data/text/{d}.txt").strip()}` |')
    a('')
    a('## Outputs')
    a('')
    a('`ADVISER_PACKAGE_C12.md`, `ADVISER_QUESTIONS.csv`, `EXCERPT_VERIFICATION.csv`, `PROVENANCE_C12.md`, `tools/` (build script and a read-only page grep helper), `SHA256SUMS`.')
    a('')
    a('## Limits')
    a('')
    a('- Every page reading is by an AI agent from a text layer; no page image was rendered and nothing is human-confirmed.')
    a('- Excerpts from copies outside the text layer (official copies in the C5 working store; Gazette facsimiles) could not be re-verified and are labelled so.')
    a('- Competing readings are taken from the artefacts; where none is recorded, the package says so rather than supplying one.')
    a(f'- Statutory edges not covered by a question: {", ".join(cov_missing) if cov_missing else "none"}.')
    a('')
    p = PKG / 'PROVENANCE_C12.md'
    p.write_text('\n'.join(L), encoding='utf-8')
    return p


def main():
    if bad:
        for e in bad:
            print('EXCERPT CHECK FAILED:', e['ref'], e['doc'], e['page'], e['status'], e['where'], file=sys.stderr)
        sys.exit(1)
    write_csv()
    write_verification()
    _, cov = write_md()
    amd = read_csv('AMD_GRAPH_C10')
    missing = [r['edge_id'] for r in amd if r['c10_status'] in ('DISPUTED_PRESERVE_BOTH', 'UNRESOLVED_COMMENCEMENT') and r['edge_id'] not in cov]
    write_provenance(missing)
    outs = ['ADVISER_PACKAGE_C12.md', 'ADVISER_QUESTIONS.csv', 'EXCERPT_VERIFICATION.csv', 'PROVENANCE_C12.md',
            'tools/build_adviser_package.py', 'tools/pgrep.py']
    (PKG / 'SHA256SUMS').write_text(''.join(f'{sha256(PKG / o)}  {o}\n' for o in outs), encoding='utf-8')
    print('questions:', len(Q), dict(Counter(qq['topic'] for qq in Q)))
    print('excerpts:', dict(Counter(e['status'] for e in VER)))
    print('uncovered statutory edges:', missing)


if __name__ == '__main__':
    main()
