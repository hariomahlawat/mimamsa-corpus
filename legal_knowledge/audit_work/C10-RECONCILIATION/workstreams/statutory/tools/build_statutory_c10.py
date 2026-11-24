#!/usr/bin/env python3
"""Cycle 10 workstream B (statutory and regulatory sources): deterministic builder.

Regenerates every CSV output of workstreams/statutory/ from pinned inputs:
  * git objects by commit in the staging worktree (default /home/user/c7):
      raw-data       ad77758d4569ba6aafa955cc7843d874489e10f7  (data/raw_manifest.csv + raw blobs)
      registers      21e73b8348767d5f1524167fcec538e1aad6e732  (C5 registers, AUTH-LEDGER HEAD)
      C9 statutory   cfc52d5792796050dcae351afda5609f7db41a5f  (PR #41 amendment graph etc.)
  * the C10 reconciliation outputs (../../outputs), each pinned by SHA-256.

Usage:
  python3 -I -B tools/build_statutory_c10.py            # write outputs
  python3 -I -B tools/build_statutory_c10.py --check    # regenerate in memory, compare, exit 1 on any difference

Needs PyMuPDF (import pymupdf) for page-text search and render-hash re-verification.
Nothing here changes a register, a ledger rule or a legal status. Every page reading is an
AI agent reading, not human-confirmed.
"""
import argparse, csv, hashlib, io, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUTDIR = os.path.dirname(HERE)
C10OUT = os.path.normpath(os.path.join(OUTDIR, '..', '..', 'outputs'))

RAW_COMMIT = 'ad77758d4569ba6aafa955cc7843d874489e10f7'
REG_COMMIT = '21e73b8348767d5f1524167fcec538e1aad6e732'
C9_COMMIT = 'cfc52d5792796050dcae351afda5609f7db41a5f'
C9_DIR = 'legal_knowledge/audit_work/C9-LEGAL-EVIDENCE/STATUTORY/'
REG_DIR = 'legal_knowledge/audit_work/SOURCE-LIBRARY-C5/registers/'
LEDGER_HEAD = 'legal_knowledge/audit_work/AUTH-LEDGER/ledger/HEAD'

C10_PINS = {
    'UNIFIED_CORPUS_INVENTORY.csv': '91519458af20c6bd849ccb8ab72d4dd32057fa0382738fa240055fe8a5b22e91',
    'MISSING_SOURCE_EVIDENCE.csv': '3aa947cb076431d40d27d6bc3e0d285f6304c36980d6043e2e41520bfbb95b21',
    'UNREGISTERED_HELD_SOURCES.csv': '3f6be222e5cd48962819d0ba31572fee0a23cf321cbe23128db75e57d68977d6',
    'COPY_EQUIVALENCE_REGISTER.csv': '8840e10e8ebf940677bba5045e1283d6189c34474517db6ecb8f0210cbe9d725',
    'SOURCE_IDENTITY_CONFLICTS.csv': '379bc1d79c09da85391130cbd2482a3e39270ae3515e78b0f4b1836d6deaa832',
}
HF_LK_LISTING = os.path.normpath(os.path.join(C10OUT, '..', 'inputs', 'hf_snapshot', 'listing_legal_knowledge.tsv'))
HF_LK_PIN = '5e7a482df3c67ae082489ee0df44367369bd23f9f865ac9921efbece500837a5'

AI = 'AI agent reading, not human-confirmed'
STATUSES = ['HELD_AUTHENTICATED', 'HELD_UNREGISTERED', 'HELD_PROVENANCE_UNCERTAIN',
            'HELD_SECONDARY_COMPILATION_ONLY', 'HELD_INCOMPLETE', 'AVAILABLE_OTHER_REPOSITORY',
            'LOCATED_NOT_ACQUIRED', 'NOT_FOUND_AFTER_DOCUMENTED_SEARCH']
WS_ONLY = 'C5_WORKING_STORE_ONLY_NOT_IN_HF_OR_GITHUB'


class BuildError(Exception):
    pass


def die(msg):
    raise BuildError(msg)


# ---------------------------------------------------------------- inputs
def git_bytes(repo, commit, path):
    p = subprocess.run(['git', '-C', repo, 'show', f'{commit}:{path}'], capture_output=True)
    if p.returncode:
        die(f'git show {commit[:8]}:{path} failed: {p.stderr.decode()[:200]}')
    return p.stdout


def git_csv(repo, commit, path):
    return list(csv.DictReader(io.StringIO(git_bytes(repo, commit, path).decode('utf-8-sig'))))


def pinned_csv(name):
    path = os.path.join(C10OUT, name)
    b = open(path, 'rb').read()
    h = hashlib.sha256(b).hexdigest()
    if h != C10_PINS[name]:
        die(f'C10 input {name} sha256 {h} != pinned {C10_PINS[name]}')
    return list(csv.DictReader(io.StringIO(b.decode('utf-8-sig'))))


def sha_prefix_map(rows):
    return {r['sha256']: r for r in rows}


def resolve(inv, prefix):
    m = [h for h in inv if h.startswith(prefix)]
    if len(m) != 1:
        die(f'sha prefix {prefix} resolves to {len(m)} inventory copies')
    return m[0]


# ---------------------------------------------------------------- page text / readings
def load_pdf(repo, raw_path):
    import pymupdf
    b = git_bytes(repo, RAW_COMMIT, raw_path)
    return b, pymupdf.open(stream=b, filetype='pdf')


def page_texts(repo, manifest_rows):
    """First two pages' text of every non-judgment raw PDF (India Code + official copies)."""
    out = {}
    for r in manifest_rows:
        if not ('/indiacode/' in r['raw_path'] or '/official_copies/' in r['raw_path']):
            continue
        b = git_bytes(repo, RAW_COMMIT, r['raw_path'])
        if hashlib.sha256(b).hexdigest() != r['sha256']:
            die(f'raw blob hash mismatch {r["raw_path"]}')
        if not b.startswith(b'%PDF'):
            out[r['sha256']] = b.decode('utf-8', 'replace')
            continue
        import pymupdf
        d = pymupdf.open(stream=b, filetype='pdf')
        out[r['sha256']] = ' '.join(' '.join(d[i].get_text() for i in range(min(2, d.page_count))).split())
    return out


# Readings made by this workstream. Rendered readings carry the render hash prefix (sha256 of the
# pixmap samples at the stated dpi, PyMuPDF 1.2x); text readings carry a substring that must occur.
READINGS = [
    ('C10R-BNS-H-01', 'd163e785', 1, 70, '3ae5cc45a4b5a895', None,
     'Hindi text. Running head "अनुभाग 1क] भारत का राजपत्र असाधारण", page number 9. Title "भारतीय न्याय संहिता, 2023 (2023 का अधिनियम संख्यांक 45) [25 दिसम्बर, 2023]". No Gazette masthead, issue number or issue date on the page. India Code watermark.'),
    ('C10R-BNS-H-02', 'd163e785', 145, 60, 'bb57db373499d43d', None,
     'Last held page = Gazette page 153: closing sub-sections (3) and (4) of the repeal-and-savings section (margin "1897 का 10"). No signature, imprint or printer\'s line on the held page.'),
    ('C10R-BNSS-H-01', '60d145c5', 1, 60, '9d69ff09f4c64562', None,
     'Hindi text. Running head "अनुभाग 1क] भारत का राजपत्र असाधारण", page 155. Title "भारतीय नागरिक सुरक्षा संहिता, 2023 (2023 का अधिनियम संख्यांक 46) [25 दिसम्बर, 2023]". No masthead. India Code watermark.'),
    ('C10R-BNSS-H-02', '60d145c5', 319, 60, '9d306a5c9abb707b', None,
     'Last held page = Gazette page 473: Form No. 58. No signature, imprint or printer\'s line on the held page.'),
    ('C10R-BSA-H-01', '72fc9a75', 1, 60, '2f69756578aa18db', None,
     'Hindi text. Running head "अनुभाग 1क] भारत का राजपत्र असाधारण", page 475. Title "भारतीय साक्ष्य अधिनियम, 2023 (2023 का अधिनियम संख्यांक 47) [25 दिसम्बर, 2023]". No masthead.'),
    ('C10R-BSA-H-02', '72fc9a75', 61, 80, 'cc00df26be81bd0e', None,
     'Last held page = Gazette page 535: end of the Schedule (certificate Part B), signed "डॉ राजीव मणि, सचिव, भारत सरकार"; imprint "UPLOADED BY THE MANAGER, GOVERNMENT OF INDIA PRESS, MINTO ROAD ... PUBLISHED BY THE CONTROLLER OF PUBLICATIONS" and "MGIPMRND—793GI(S3)—27-03-2024"; a digital-signature box dated 2024.03.27. The issue number and issue date are not on any held page; the printer\'s date is not treated as a publication date.'),
    ('C10R-AFT-GUW-01', '34584afa', 1, 90, 'e906fbd068fa7626', None,
     'Image-only page (no text layer). Gazette of India Extraordinary Part II Section 4, No. 8, New Delhi, Wednesday, July 28, 2010. Ministry of Defence notification dated 28-07-2010, S.R.O. 10(E): under s.5(4) of the AFT Act 2007 notifies the Bench at Guwahati "with effect from 31st day of July, 2010" with jurisdiction over Assam, Arunachal Pradesh, Meghalaya, Manipur, Mizoram, Nagaland, Tripura and Sikkim (as printed).'),
    ('C10R-AFT-CHN-01', 'be9e3e7e', 1, 110, '483dceb117ae22ec', None,
     'Gazette of India Extraordinary Part II Section 4, No. 02, 26-02-2015. S.R.O. 02(E) under s.5(4) AFT Act, "in partial modification of S.R.O. 14(E), dated 21st October, 2009", notifies the Chennai Bench jurisdiction over Telangana "with effect from 2nd day of June, 2014" (as printed). This S.R.O. 14(E) of 21-10-2009 is a bench-jurisdiction notification; it is a different instrument (date and subject) from the S.O. 14(E) of 13-06-2008 that the AFT compilation footnote cites for s.1(2). Number collision only; no identity inference.'),
    ('C10R-AFT-CHN-02', 'd483c44d', 1, None, None, 'in partial modification of S.R.O. 14(E), dated 21st October, 2009',
     'Text layer (crawl title "Jurisdiction for Telangana") carries the same S.R.O. 02(E)/2015 text as be9e3e7e; different bytes. Proposed relation SAME_LEGAL_DOCUMENT_DIFFERENT_BYTES (identity review).'),
    ('C10R-AFT-ESTT-01', '03961b02', 1, None, None, 'S.R.0. 9(E).—In exerciseof the powers conferred by Section 4 of the Armed Forces Tribunal Act, 2007',
     'Text layer (OCR) of crawl item "AFT-Estt-Day": Gazette Extraordinary Part II Section 4 No. 8, 7 August 2009, S.R.O. 9(E) under s.4 establishing the Armed Forces Tribunal. Same instrument as 8d774f1f (C9R-RD-AFTAPPT-IMG); different bytes.'),
    ('C10R-RAF-01', '4284820e', 1, None, None, 'For Official Use Only',
     'Text layer p.1: "For Official Use Only DEFENCE SERVICES REGULATIONS ... REGULATIONS FOR THE AIR FORCE REPRINTED EDITION 2000 (Orders issued upto 31st March, 2000 have been incorporated)". Access marking printed on the held copy.'),
    ('C10R-AA-SCH-01', '3a551c1f', 1, None, None, 'Rep. by the Repealing and Amending Act, 1957 (36 of 1957), s. 2 and the First Schedule',
     'Text layer: India Code Army Act item "THE SCHEDULE.—Rep. by the Repealing and Amending Act, 1957 (36 of 1957), s. 2 and the First Schedule." Compiler statement only; RAA 1957 itself not held.'),
    ('C10R-NAVY-IV-01', 'e4148ee0', 1, None, None, 'THE INDIAN NAVAL AUXILARY SERVICE REGULATIONS, 1973',
     'Text layer p.1: Regulations for the Navy Part IV = "THE INDIAN NAVAL AUXILARY SERVICE REGULATIONS, 1973" inserted as Part IV by Amendment No. 82 (SRO 232 dated 7 Aug 73). The C5 source C5-SRC-P2-INAS-1973 (NOT_HELD) is therefore held in this compilation.'),
    ('C10R-AFT-GAZ-01', '338d43ad', 1, None, None, 'NEW DELHI, FRIDAY, DECEMBER 28, 2007',
     'Text layer p.1 consistent with the C9 image reading C9R-RD-AFT07-IMG (Gazette Extraordinary Part II Section 1, No. 66, 28-12-2007; assent 25-12-2007 as printed). Crawl category "rule" is wrong (SOURCE_IDENTITY_CONFLICTS IC-CATEGORY-338d43addeaa).'),
]


def verify_readings(repo, inv, mrows):
    import pymupdf
    path_of = {r['sha256']: r['raw_path'] for r in mrows}
    out = []
    for rid, pre, page, dpi, rpre, needle, text in READINGS:
        h = resolve(inv, pre)
        b, d = load_pdf(repo, path_of[h])
        if dpi:
            pix = d[page - 1].get_pixmap(dpi=dpi)
            rh = hashlib.sha256(pix.samples).hexdigest()
            if not rh.startswith(rpre):
                die(f'{rid}: render sha256 {rh[:16]} != recorded {rpre} (PyMuPDF {pymupdf.VersionBind})')
            method = f'page image rendered at {dpi} dpi; render sha256 {rh[:16]}'
        else:
            t = ' '.join(d[page - 1].get_text().split())
            if ' '.join(needle.split()) not in t:
                die(f'{rid}: expected text not on page')
            method = 'text layer of the held page (substring verified by builder)'
        out.append({'reading_id': rid, 'sha256': h, 'page': page, 'pages_in_file': d.page_count,
                    'method': method, 'reading': text, 'reader': AI})
    return out


# ---------------------------------------------------------------- Task 1: primary-source status
# Each row: key, family, source, layer, status, held (sha prefixes counted as holdings of THIS row),
# related (held copies of a different layer, for orientation only), c5 ids, c9 ids, search regex
# (required for LOCATED/NOT_FOUND rows: run over inventory titles, raw page text and HF listing),
# basis and note.
SRC = [
    # Army Act 1950
    ('ST-AA-ENACTED', 'Army Act 1950', 'Army Act 1950 (46 of 1950) as enacted: Gazette of India Extraordinary', 'as enacted', 'LOCATED_NOT_ACQUIRED',
     [], ['e47a4265', '42b9a2f8'], 'C5-SRC-P0-ARMY-ACT-1950', 'I-AA-1950;C9-ACQ-077',
     r'gazette.{0,40}(1950).{0,40}army act|army act.{0,30}as enacted|in\.gazette\.e\.1950',
     'archive.org item in.gazette.e.1950.306 pinned by md5 68bcdd4e8db91eb83d1e6b92a393b2db (C9-ACQ-077); not acquired (A-C5-1 + crawler-config PR)',
     'No Gazette copy in HF, GitHub or the working store. 185 KB records depend on the Act (C9 gross count).'),
    ('ST-AA-COMPILATION', 'Army Act 1950', 'Army Act 1950: India Code compilation (English, as on 21-07-2025; Hindi version; Schedule note)', 'consolidated', 'HELD_SECONDARY_COMPILATION_ONLY',
     ['e47a4265', '42b9a2f8', '3a551c1f'], ['c8a791a1', '73fd3042'], 'C5-SRC-P0-ARMY-ACT-1950-INDIACODE', 'I-AA-1950',
     None, 'English compilation registered (C5 copy PROVENANCE_UNDOCUMENTED_COPY) and byte-identical to raw-data with a retrieval record (C9 provenance lead); Hindi compilation and Schedule note unregistered',
     'Compilation is not proof of amendment history or commencement. MML vol 2(AA) files are manuals (HF only), listed as related, not as copies of the Act.'),
    ('ST-AA-COMM-SRO120', 'Army Act 1950', 'Army Act commencement notification S.R.O. 120 of 22-07-1950 (as cited by the compilation footnote)', 'commencement', 'LOCATED_NOT_ACQUIRED',
     [], ['e47a4265'], 'C5-SRC-P0-AA-AMD-OTHER', 'I-AA-SRO120-1950;C9-AG-AA-00',
     r's\.?\s*r\.?\s*o\.?\s*120\b', 'candidate ACQ03-019 in PR #23 (identity of candidate unverified, C9)',
     'Commencement date is a compiler statement until the notification is image-checked.'),
    ('ST-AA-ACT19-1955', 'Army Act 1950 amendments', 'Commanders-in-Chief (Change in Designation) Act 1955 (19 of 1955)', 'amending Act', 'HELD_INCOMPLETE',
     ['b1deca27'], [], 'C5-SRC-P0-AA-AMD-ACT19-1955', 'I-AA-ACT19-1955;C9-AG-AA-01',
     None, 'C5 HELD_GOVERNMENT_COMPILATION_EXTRACT: 1-page text rendering, Schedule (the amendments) absent', 'PR #8 (AP-C9-01) would yield the Gazette with Schedule.'),
    ('ST-AA-ACT13-1975', 'Army Act 1950 amendments', 'Air Force and Army Laws (Amendment) Act 1975 (13 of 1975)', 'amending Act', 'HELD_PROVENANCE_UNCERTAIN',
     ['8358d2b3'], [], 'C5-SRC-P0-AA-AMD-ACT13-1975', 'I-AA-ACT13-1975;C9-AG-AA-06',
     None, 'C5 HELD_OFFICIAL_PUBLICATION_PROVENANCE_UNDOCUMENTED (2 pages)', "'w.e.f. 25-1-1975' compiler note preserved (OQ-A-04)."),
    ('ST-AA-ACT37-1992', 'Army Act 1950 amendments', 'Army (Amendment) Act 1992 (37 of 1992)', 'amending Act', 'HELD_PROVENANCE_UNCERTAIN',
     ['f11d443e', 'a5943b72', 'f1e69a74'], [], 'C5-SRC-P0-AA-AMD-ACT37-1992', 'I-AA-ACT37-1992;C9-AG-AA-08-s2..s19',
     None, 'f11d443e is DOCUMENTED_PRIMARY_COPY in the C5 copy register; no AUTH-LEDGER authentication (version 0)',
     'VOCABULARY NOTE: no allowed state expresses "registered, documented provenance, not authenticated"; HELD_PROVENANCE_UNCERTAIN is used because no authentication record exists. Commencement: see ESC-ACT37-1992.'),
    ('ST-AA-AMD-CANDIDATES', 'Army Act 1950 amendments', 'Adaptation of Laws (No.3) Order 1956; Air Force and Army Laws (Amendment) Ordinance 1975 (Ord. 3); Delegated Legislation Provisions (Amendment) Act 1983 (20 of 1983)', 'amending instruments', 'LOCATED_NOT_ACQUIRED',
     [], ['e47a4265'], 'C5-SRC-P0-AA-AMD-OTHER', 'I-AA-ALO3-1956;I-AA-ORD3-1975;I-AA-ACT20-1983',
     r'adaptation of laws|ordinance,? 1975|delegated legislation provisions? \(amendment\) act,? 1983(?!.*disposal)',
     'candidates in PR #23 (C9 AP-C9-04)', 'The DPP Act compilation lists "Delegated Legislation Provision (Amendment) Act, 1983 (20 of 1983)" in its amending-Acts list and the Army Act compilation does too; that is a list entry, not a copy.'),
    ('ST-AA-AMD-NOCANDIDATE', 'Army Act 1950 amendments', 'Repealing and Amending Acts 1957, 1960, 1974, 2001, 2017(2nd); Notification S.O. 3912(E) of 30-10-2019', 'amending instruments', 'NOT_FOUND_AFTER_DOCUMENTED_SEARCH',
     [], ['3a551c1f'], 'C5-SRC-P0-AA-AMD-OTHER', 'I-AA-RAA-1957;I-AA-RAA-1960;I-AA-RAA-1974;I-AA-RAA-2001;I-AA-RAA2-2017;I-AA-SO3912E-2019',
     r'repealing and amending act|3912',
     'search: C9 AP-C9-05 register search (no candidate) + C10 deterministic search of 4,103 held copies, raw page text and HF legal_knowledge listing (hits are list entries/footnotes only)',
     'DISAGREEMENT PRESERVED: the C5 group row C5-SRC-P0-AA-AMD-OTHER says NOT_HELD_CANDIDATE_LOCATED for the whole group; C9 found no candidate for these items.'),
    ('ST-AA-NOTIFS', 'Army Act 1950', 'Gazette notifications under the Army Act (s.4 application, s.9 active-service declarations etc.)', 'notifications', 'NOT_FOUND_AFTER_DOCUMENTED_SEARCH',
     [], [], 'C5-SRC-P1-AA-NOTIFICATIONS', 'I-AA-NOTIFS',
     r'active service|army act.{0,40}notification|section 9 of the army act',
     'search scope: C10 held-copy search only. External discovery has NOT been done (C5 NOT_HELD_NOT_CHECKED); phase 6', 'Status describes holdings only.'),
    # Army Rules 1954
    ('ST-AR-GAZETTE-1954', 'Army Rules 1954', 'Army Rules 1954: S.R.O. 484, Gazette of India Part II-S4 No. 47, 27-11-1954 (archival facsimile)', 'as made', 'HELD_PROVENANCE_UNCERTAIN',
     ['c5ef95a9'], [], 'C5-SRC-P0-ARMY-RULES-1954', 'I-AR-1954;C9-AG-AR-000',
     None, 'C5 DOCUMENTED_PRIMARY_COPY; all 42 exact anchors rest on this copy; no AUTH-LEDGER authentication (version 0)',
     'PRESERVATION: only in the ephemeral working store. VOCABULARY NOTE as for Act 37/1992.'),
    ('ST-AR-COMPILATION', 'Army Rules 1954', 'Army Rules 1954: India Code compilation (214 pp.)', 'consolidated', 'HELD_SECONDARY_COMPILATION_ONLY',
     ['48f52219'], ['8bb17d82', 'ed1d8a7f'], 'C5-SRC-P0-ARMY-RULES-1954-INDIACODE', 'I-AR-1954',
     None, 'registered; byte-identical to raw-data with retrieval record (C9 provenance lead)',
     'Prints r.23(3) "You are obliged..." and r.168(2) field-punishment words: see ESC-R23-3 and ESC-R168-2.'),
    ('ST-AR-AMD-HELD', 'Army Rules 1954 amendments', 'Army Rules amendment, corrigendum and r.188(e) declaration Gazettes held: S.R.O.s 205/1961 to 6(E)/2022 (24 copies; chain items AR-006..AR-035)', 'amending rules', 'HELD_PROVENANCE_UNCERTAIN',
     ['0b4c5b72', 'b76bf4aa', '4acdb1a8', 'cce0d06e', '682afce5', 'be7fefc9', '5126efa2', '7edc4de1', 'd283767e', 'dd6978db', 'd8ce1958', '225f624b',
      '972e5aa1', 'eaa233f8', '4392f326', '1d67bddd', '31fedb68', '0e4b8e47', 'dc67b628', 'e9bf2114', 'ca5d79c2', '7c12a7ec', '138c1da0', '2bdab5b7'], [],
     'C5-SRC-P0-AR-AMD-AR-006..AR-035', 'C9-AG-AR-006..C9-AG-AR-035', None,
     'registered; 3 copies DOCUMENTED_PRIMARY_COPY (S.R.O. 205/1961, 17(E)/1993, 8(E)/2003; per C5 copy register), the rest PROVENANCE_UNDOCUMENTED_COPY; no AUTH-LEDGER authentication',
     'PRESERVATION: every copy is in the working store only. Image-checked in C5/C8; graph statuses EVIDENCED 11 / UNRESOLVED_COMMENCEMENT 13 / DISPUTED_PRESERVE_BOTH 1 for the 25 held chain items AR-006..035 (C9, unchanged in C10).'),
    ('ST-AR-AMD-NOTHELD-LOCATED', 'Army Rules 1954 amendments', 'S.R.O. 331, 348, 351, 404 of 1960; S.R.O. 22 of 2010 (LOCATED_UNVERIFIED, text-layer leads only)', 'amending rules', 'LOCATED_NOT_ACQUIRED',
     [], [], 'C5-SRC-P0-ARMY-RULES-1954', 'I-AR-AMD-002..005;I-AR-AMD-032',
     r's\.?\s*r\.?\s*o\.?\s*(331|348|351|404)\b|1960.{0,30}army.{0,20}amendment|s\.?\s*r\.?\s*o\.?\s*22\b.{0,20}2010',
     'ARMY-RULES-CHAIN-01 leads (text-layer only); no held bytes', 'S.R.O. 331/1960 touches r.168(2) (C9 graph).'),
    ('ST-AR-AMD-POST2022', 'Army Rules 1954 amendments', 'Possible Army Rules amendments after 06-06-2022 (10 archive.org candidates, subject not confirmed)', 'amending rules', 'LOCATED_NOT_ACQUIRED',
     [], [], 'C5-SRC-P0-AR-AMD-POST-2022', 'I-AR-AMD-036;C9-ACQ-084..093',
     r'in\.gazette\.central\.e\.20(22-0[6-9]|22-1|23|24|25|26)',
     'pinned archive.org metadata (C5-ACQ-06); A-C5-1 + config PR needed', 'Decisive for the unsupported "r.23 amended 2022" reading (ESC-R23-2022).'),
    ('ST-AR-AMD-GAPS', 'Army Rules 1954 amendments', 'E-7/1960 (AR-001) and S.R.O. 258/2002 (AR-030)', 'amending rules', 'NOT_FOUND_AFTER_DOCUMENTED_SEARCH',
     [], [], 'C5-SRC-P0-ARMY-RULES-1954', 'I-AR-AMD-001;I-AR-AMD-030',
     r'\be-?7\b.{0,20}1960|s\.?\s*r\.?\s*o\.?\s*258\b',
     'search: ARMY-RULES-CHAIN-01 and C9 (GAP; custodian or Indian-network egazette run needed) + C10 held-copy search', ''),
    ('ST-AR-AMD-HINTS', 'Army Rules 1954 amendments', 'FTS/WS-A hints AR-012, 013, 015, 037-046 (identity unknown)', 'hints', 'LOCATED_NOT_ACQUIRED',
     [], [], 'C5-SRC-P0-ARMY-RULES-1954', 'I-AR-AMD-012;013;015;037..046',
     r'army \(first amendment\) rules,? 1972|s\.?\s*r\.?\s*o\.?\s*66\b',
     'unopened hints carried in PR #23 / ARMY-RULES-CHAIN-01', 'Identity unknown; may not be amendments at all.'),
    ('ST-AR-INTERIM-1950', 'Army Rules 1954', 'Rules under Army Act ss.21, 102(4), 191 (Gazette Extraordinary No. 8 of 1950)', 'historical rules', 'LOCATED_NOT_ACQUIRED',
     [], [], 'C5-SRC-P2-ARMY-RULES-1950-INTERIM', 'I-AR-INTERIM-1950;C9-ACQ-110',
     r'in\.gazette\.e\.1950\.8\b', 'archive.org pin md5 60ff798536c357ce3ef142d5fead48b6', ''),
    # AFT
    ('ST-AFT-GAZETTE', 'AFT Act 2007', 'Armed Forces Tribunal Act 2007 (55 of 2007): Gazette of India Extraordinary Pt II s.1 No. 66, 28-12-2007', 'as enacted', 'HELD_UNREGISTERED',
     ['338d43ad'], ['665863d1', '48f57c81'], 'C5-SRC-P0-AFT-ACT-2007', 'I-AFT-2007;C9-ACQ-078',
     None, 'raw-data retrieval record (India Code bitstream, 2026-11-21); C9 image reading C9R-RD-AFT07-IMG',
     'CORRECTION: C5 master register says NOT_HELD_CANDIDATE_LOCATED. Crawl category "rule" is wrong.'),
    ('ST-AFT-COMPILATION', 'AFT Act 2007', 'AFT Act 2007: India Code compilation (as on 01-09-2026) and Hindi compilation', 'consolidated', 'HELD_SECONDARY_COMPILATION_ONLY',
     ['665863d1', '48f57c81'], [], 'C5-SRC-P0-AFT-ACT-2007-INDIACODE', 'I-AFT-2007', None,
     'registered (two copy rows); byte-identical to raw-data with retrieval records', '89 KB records cite this source (all PARTIAL_MATCH).'),
    ('ST-AFT-COMM-SO14E-2008', 'AFT Act 2007', 'AFT Act s.1(2) commencement: Notification S.O. 14(E) of 13-06-2008 (as cited by the compilation)', 'commencement', 'NOT_FOUND_AFTER_DOCUMENTED_SEARCH',
     [], ['665863d1'], 'C5-SRC-P0-AFT-ACT-2007', 'I-AFT-SO14E-2008;C9-AG-AFT-00',
     r'\b14\s*\((e|E|अ)\)|13-06-2008|13th june,? 2008',
     'search: C9 AP-C9-05 (no candidate in any register) + C10 held-copy search; hits are S.R.O. 14(E) of 21-10-2009 references only (C10R-AFT-CHN-01/02)',
     'NUMBER COLLISION: S.R.O. 14(E) dated 21-10-2009 (Chennai Bench jurisdiction, referred to in held S.R.O. 02(E)/2015) is a different instrument.'),
    ('ST-AFT-SRO9E-2009', 'AFT Act 2007', 'S.R.O. 9(E) of 07-08-2009 establishing the Tribunal (appointed day 10-08-2009 as printed)', 'establishment notification', 'HELD_UNREGISTERED',
     ['8d774f1f', '03961b02'], [], '(none)', 'I-AFT-SRO9E-2009;C9-AG-AFTSRO9E2009', None,
     'two raw-data copies with retrieval records; in no register', 'Second copy 03961b02 is new in C10 (C10R-AFT-ESTT-01).'),
    ('ST-AFT-RDO-2008', 'AFT Act 2007', 'AFT Act (Removal of Difficulties) Order 2008, S.R.O. 18(E) of 21-07-2008', 'order', 'HELD_UNREGISTERED',
     ['1c6db257'], [], '(none)', 'I-AFT-RDO-2008;C9-AG-AFTRDO2008', None, 'raw-data retrieval record; in no register', ''),
    ('ST-AFT-BENCHES', 'AFT Act 2007', 'AFT Bench establishment and jurisdiction notifications under s.5(4) (13 Gazette notifications, 2009-2017)', 'notifications', 'HELD_UNREGISTERED',
     ['2027fecd', '34584afa', '38d8adfa', '3aa43869', '420b7bf5', '48a01377', '59974179', '61353e0f', '66a84e53', 'be9e3e7e', 'c32157ed', 'd483c44d', 'd56bded1'], [], '(none)', '(none in C9)', None,
     'raw-data retrieval records; in no register', 'Relevant to territorial jurisdiction of Regional Benches; 34584afa has no text layer (C10R-AFT-GUW-01).'),
    ('ST-AFT-PROC-RULES-2008', 'AFT rules', 'AFT (Procedure) Rules 2008, S.R.O. 26(E) of 17-09-2008', 'rules', 'HELD_UNREGISTERED',
     ['590cf7cd'], [], 'C5-SRC-P1-AFT-PROC-RULES', 'I-AFT-PR-2008;C9-AG-AFTPR2008', None, 'raw-data retrieval record; C9 image reading', 'CORRECTION: C5 says NOT_HELD_NOT_CHECKED; 46 crosswalk rows are MISSING_EVIDENCE against this source.'),
    ('ST-AFT-PROC-AMD-2011', 'AFT rules', 'AFT (Procedure) Amendment Rules 2011, S.R.O. 05(E) of 29-07-2011', 'amending rules', 'HELD_UNREGISTERED',
     ['fc27032f'], [], 'C5-SRC-P1-AFT-PROC-RULES', 'I-AFT-PR-AMD-2011;C9-AG-AFTPR2011', None, 'raw-data retrieval record; C9 image reading', ''),
    ('ST-AFT-PRACTICE-2009', 'AFT rules', 'AFT (Practice) Rules 2009, S.R.O. 6(E) of 11-05-2009', 'rules', 'HELD_INCOMPLETE',
     ['c57b113a'], [], 'C5-SRC-P1-AFT-PROC-RULES', 'I-AFT-PRAC-2009;C9-AG-AFTPRAC2009', None,
     'raw-data retrieval record; Gazette masthead (publication date) not on the held pages', 'Rules commence "from the date of publication in the official gazette"; publication date not evidenced (ESC-AFT-PROC-RULES).'),
    ('ST-AFT-OTHER-RULES', 'AFT rules', 'AFT administrative rules: Financial & Administrative Powers Rules 2008; Procedure for Investigation Rules 2008; Salary Rules 2009; Exemption from UPSC consultation 2011; Group A/B/C and Accounts Cadre recruitment rules 2013-2019', 'rules', 'HELD_UNREGISTERED',
     ['14c19950', '9565ce77', '4553e112', '379c4e0a', '5a7ea50c', '2e90ba87', 'e2ee7755', 'c85c9c0e', '0c030041'], [], '(none)', '(none in C9)', None,
     'raw-data retrieval records; in no register', 'Low legal consequence for the research records; register only on owner request.'),
    ('ST-AFT-FIN-2017', 'AFT amendments', 'Finance Act 2017 (7 of 2017), Part XIV s.181 (inserted AFT s.9A)', 'amending Act', 'HELD_UNREGISTERED',
     ['7a5551ba'], [], '(none)', 'I-AFT-FIN-2017;C9-AG-AFT-01', None, 'India Code rendition of the Act as enacted; raw-data retrieval record', 'Part XIV commencement notification not held.'),
    ('ST-AFT-TRA-2021', 'AFT amendments', 'Tribunals Reforms Act 2021 (33 of 2021)', 'amending Act', 'HELD_UNREGISTERED',
     ['0c2f4e9e'], [], '(none)', 'I-AFT-TRA-2021;C9-AG-AFT9A-TRA2021', None, 'India Code rendition with Legislative Department heading; raw-data retrieval record', ''),
    ('ST-AFT-TRA-2026', 'AFT amendments', 'Tribunals Reforms Act 2026 (17 of 2026): Gazette Extraordinary Pt II s.1 No. 31, 13-08-2026', 'amending Act', 'HELD_PROVENANCE_UNCERTAIN',
     ['be619533'], [], 'C5-SRC-P0-TRA-2026', 'I-AFT-TRA-2026;C9-AG-AFT-03;-04', None, 'registered PROVENANCE_UNDOCUMENTED_COPY; byte-identical to raw-data with retrieval record (provenance lead)', ''),
    ('ST-AFT-TRA2026-COMM', 'AFT amendments', 'TRA 2026 s.1(2) commencement notification(s)', 'commencement', 'NOT_FOUND_AFTER_DOCUMENTED_SEARCH',
     [], ['be619533', '665863d1'], '(none)', 'I-AFT-TRA2026-COMM',
     r'tribunals? reforms.{0,60}(notification|appoint)|25-08-2026|25th august,? 2026',
     'search: C9 AP-C9-05 (no candidate) + C10 held-copy search', 'Compilation prints s.9A "w.e.f. 25-08-2026" (compiler statement; C9-AG-AFT-03 preserved both).'),
    # Sanhitas
    ('ST-BNS-GAZETTE', 'BNS 2023', 'Bharatiya Nyaya Sanhita 2023 (45 of 2023) as enacted: Gazette text', 'as enacted', 'HELD_INCOMPLETE',
     ['d163e785'], ['d4449e99'], 'C5-SRC-P1-BNS-2023', 'I-BNS-2023;C9-ACQ-111', None,
     'Hindi text in Gazette Extraordinary Section 1A pagination (pp.9-153), India Code watermark; masthead, issue number/date and signature page absent (C10R-BNS-H-01/02). English Gazette: archive.org pin in.gazette.central.e.2023-12-25.250883 (not acquired)',
     'NEW IN C10: C9 treated the Gazette layer as NOT_HELD. The held pages are a Hindi-language Gazette printing, not the English Gazette the C5 source names.'),
    ('ST-BNS-COMPILATION', 'BNS 2023', 'BNS 2023: India Code compilation (as on 06-10-2025)', 'consolidated', 'HELD_SECONDARY_COMPILATION_ONLY',
     ['d4449e99'], [], 'C5-SRC-P1-BNS-2023', 'I-BNS-2023;C9-ACQ-122', None, 'unregistered; raw-data retrieval record', '12 crosswalk rows are MISSING_EVIDENCE against C5-SRC-P1-BNS-2023.'),
    ('ST-BNSS-GAZETTE', 'BNSS 2023', 'Bharatiya Nagarik Suraksha Sanhita 2023 (46 of 2023) as enacted: Gazette text', 'as enacted', 'HELD_INCOMPLETE',
     ['60d145c5'], ['572c7988'], 'C5-SRC-P0-BNSS-2023', 'I-BNSS-2023;C9-ACQ-079', None,
     'Hindi text in Gazette Section 1A pagination (pp.155-473); masthead and signature page absent (C10R-BNSS-H-01/02). English Gazette pinned in.gazette.central.e.2023-12-25.250884',
     'NEW IN C10 (C9: NOT_HELD).'),
    ('ST-BNSS-COMPILATION', 'BNSS 2023', 'BNSS 2023: India Code compilation (as on 06-10-2025) with Schedules', 'consolidated', 'HELD_SECONDARY_COMPILATION_ONLY',
     ['572c7988', 'd5e5554b', '0cdc96bb'], [], 'C5-SRC-P0-BNSS-2023-INDIACODE', 'I-BNSS-2023', None, 'compilation registered; First and Second Schedule files unregistered', ''),
    ('ST-BSA-GAZETTE', 'BSA 2023', 'Bharatiya Sakshya Adhiniyam 2023 (47 of 2023) as enacted: Gazette text', 'as enacted', 'HELD_INCOMPLETE',
     ['72fc9a75'], ['554b2b4a'], 'C5-SRC-P0-BSA-2023', 'I-BSA-2023;C9-ACQ-080', None,
     'Hindi text in Gazette Section 1A pagination (pp.475-535) ending with signature and Government of India Press imprint; masthead/issue number and date absent (C10R-BSA-H-01/02). English Gazette pinned in.gazette.central.e.2023-12-25.250882',
     'NEW IN C10 (C9: NOT_HELD).'),
    ('ST-BSA-COMPILATION', 'BSA 2023', 'BSA 2023: India Code compilation (as on 06-10-2025) with Schedule', 'consolidated', 'HELD_SECONDARY_COMPILATION_ONLY',
     ['554b2b4a', '63797c96'], [], 'C5-SRC-P0-BSA-2023-INDIACODE', 'I-BSA-2023', None, 'compilation registered; Schedule file unregistered', ''),
    ('ST-SANHITA-COMM-2024', 'Commencement notifications', 'BNS/BNSS/BSA commencement notifications S.O. 850(E), 848(E), 849(E) of 23-02-2024', 'commencement', 'LOCATED_NOT_ACQUIRED',
     [], ['d4449e99', '572c7988', '554b2b4a'], 'C5-SRC-P0-SANHITA-COMMENCEMENT-2024', 'I-BNS-COMM-SO850E;I-BNSS-COMM-SO848E;I-BSA-COMM-SO849E;C9-ACQ-081..083',
     r'\b(850|848|849)\s*\(e\)|2024-02-24', 'archive.org pins in.gazette.central.e.2024-02-24.252352/252353/252354 (md5 recorded in C9)',
     'Hits in held copies are compilation footnotes only. Publication is not commencement.'),
    # historical codes
    ('ST-IPC-1860', 'Historical codes', 'Indian Penal Code 1860 (45 of 1860; repealed by BNS)', 'consolidated', 'HELD_SECONDARY_COMPILATION_ONLY',
     ['fa8878e0'], ['3ad875b6'], 'C5-SRC-P1-IPC-CRPC-IEA', 'I-IPC-1860', None, 'India Code rendering ("Rep., Act 45 of 2023"); edition date not established',
     'CORRECTION: C5 says NOT_HELD_NOT_CHECKED. Text as at 30-06-2024 not established.'),
    ('ST-CRPC-1973', 'Historical codes', 'Code of Criminal Procedure 1973 (2 of 1974; repealed by BNSS)', 'consolidated', 'HELD_SECONDARY_COMPILATION_ONLY',
     ['865cc3e1', '982059ca'], ['aa3e4914'], 'C5-SRC-P1-IPC-CRPC-IEA', 'I-CRPC-1973', None, 'two India Code renderings (1974 print; consolidated), neither shown to be the text as at repeal', ''),
    ('ST-IEA-1872', 'Historical codes', 'Indian Evidence Act 1872 (1 of 1872; repealed by BSA)', 'consolidated', 'HELD_SECONDARY_COMPILATION_ONLY',
     ['06729a1f'], ['7693f293'], 'C5-SRC-P1-IPC-CRPC-IEA', 'I-IEA-1872', None, 'India Code rendering', ''),
    ('ST-BPRD-TABLES', 'Historical codes', 'Correspondence tables BNS-IPC, BNSS-CrPC, BSA-IEA (CAPT Bhopal)', 'secondary reference', 'HELD_SECONDARY_COMPILATION_ONLY',
     ['3ad875b6', 'aa3e4914', '7693f293'], [], '(none)', 'C9-ACQ-002..004', None, 'official_copies with retrieval records; authored commentary ("© Anil Kishore Yadav, IPS")', 'Never authority for statutory text.'),
    # pension / medical
    ('ST-PRA-2008', 'Pension Regulations', 'Pension Regulations for the Army 2008, Parts I and II', 'regulations', 'LOCATED_NOT_ACQUIRED',
     [], [], 'C5-SRC-P1-PRA-2008-PT1;C5-SRC-P1-PRA-2008-PT2', 'I-PRA-2008-PT1;I-PRA-2008-PT2;C9-ACQ-094;095',
     r'pension regulations for the army|pra.?2008', 'DESW URLs located; BLOCKED (desw.gov.in robots.txt 403, fail-closed)', '34 crosswalk rows MISSING_EVIDENCE.'),
    ('ST-PRA-1961', 'Pension Regulations', 'Pension Regulations for the Army 1961, Parts I and II', 'regulations', 'NOT_FOUND_AFTER_DOCUMENTED_SEARCH',
     [], [], 'C5-SRC-P1-PRA-1961', 'I-PRA-1961', r'pension regulations for the army.{0,20}1961', 'search: C5 (DESW archive pages 1-3) + C10 held-copy search; DESW archive pages 4-33 not searched', ''),
    ('ST-PEN-REGS-COMPARATORS', 'Pension Regulations', 'Navy (Pension) Regulations 1964 (comparator; Air Force Pension Regulations 1960 not held)', 'regulations', 'HELD_UNREGISTERED',
     ['f9e11e04'], [], 'C5-SRC-P2-PEN-REGS-AF-NAVY', '(none)', None, 'India Code text of S.R.O. 74 of 10-02-1964; raw-data retrieval record; amendment state not established',
     'CORRECTION (partial): C5 says NOT_HELD_CANDIDATE_LOCATED for the AF+Navy group; the Navy part is held.'),
    ('ST-ER-2023', 'Entitlement Rules', 'Entitlement Rules 2023 (MoD/DESW letter 21-09-2023, 13 MB copy)', 'rules', 'HELD_INCOMPLETE',
     ['29f6fa2c'], [], 'C5-SRC-P1-ER-2023-HELD-13MB;C5-SRC-P1-ER-GMO-2023', 'I-ER-2023', None, 'C5: INCOMPLETE (covering letter + ER; GMO absent), PROVENANCE_UNDOCUMENTED_COPY', 'PRESERVATION: working store only.'),
    ('ST-ER-2008', 'Entitlement Rules', 'Entitlement Rules for Casualty Pensionary Awards 2008', 'rules', 'LOCATED_NOT_ACQUIRED',
     [], [], 'C5-SRC-P1-ER-2008', 'I-ER-2008;C9-ACQ-097', r'entitlement rules', 'DESW URLs located; BLOCKED (robots 403)', ''),
    ('ST-ER-1982', 'Entitlement Rules', 'Entitlement Rules for Casualty Pensionary Awards 1982', 'rules', 'NOT_FOUND_AFTER_DOCUMENTED_SEARCH',
     [], [], 'C5-SRC-P1-ER-1982', 'I-ER-1982', r'entitlement rules.{0,40}1982', 'search: C5 (DESW archive partial) + C10 held-copy search', ''),
    ('ST-GMO-2023', 'Guide to Medical Officers', 'Guide to Medical Officers (Military Pensions) 2023', 'guide', 'LOCATED_NOT_ACQUIRED',
     [], ['29f6fa2c'], 'C5-SRC-P1-ER-GMO-2023', 'I-GMO-2023;C9-ACQ-096', r'guide to medical officers|\bgmo\b', 'PR #9 lists the DESW URL (size only, no hash); BLOCKED (robots 403)', ''),
    ('ST-GMO-2002-2008', 'Guide to Medical Officers', 'Guide to Medical Officers (Military Pensions) 2002 and 2008', 'guide', 'NOT_FOUND_AFTER_DOCUMENTED_SEARCH',
     [], [], 'C5-SRC-P1-GMO-2002-2008', 'I-GMO-2002-2008', r'guide to medical officers', 'search: C5 + C10 held-copy search', ''),
    ('ST-PEN-CIRCULARS', 'Pension circulars', 'DESW circulars amending PRA 2008 / ER 2008 (2013, 2020, 2021) and other letters', 'circulars', 'LOCATED_NOT_ACQUIRED',
     [], [], 'C5-SRC-P1-PEN-CIRCULARS', 'I-CIRC-PRA-ER;C9-ACQ-098', r'circular|d\(pen', 'DESW URLs located; BLOCKED (robots 403)', ''),
    # regulations / orders
    ('ST-RA-1987', 'Regulations for the Army', 'Regulations for the Army (Revised Edition) 1987', 'regulations', 'HELD_INCOMPLETE',
     ['4be12283'], [], 'C5-SRC-P0-RA-1987;C5-SRC-P0-RA-1987-CH5-INDIACODE', '(C5-ACQ-26)', None, 'Chapter V extract only (5 pages, retyped India Code extract); complete publication needs custodian route',
     'PRESERVATION: working store only. Access marking of the full publication not determined.'),
    ('ST-RA-1962', 'Regulations for the Army', 'Regulations for the Army 1962', 'regulations', 'NOT_FOUND_AFTER_DOCUMENTED_SEARCH',
     [], [], 'C5-SRC-P0-RA-1962', '', r'regulations for the army.{0,10}1962', 'search: C5 + C10 held-copy search', ''),
    ('ST-RAF-2000', 'Cross-service regulations', 'Regulations for the Air Force (Reprinted Edition 2000)', 'regulations', 'HELD_UNREGISTERED',
     ['4284820e'], [], 'C5-SRC-P2-RAF-1964', '(none)', None, 'raw-data retrieval record (India Code); printed marking "For Official Use Only" (C10R-RAF-01)',
     'CORRECTION: C5 says NOT_HELD_CANDIDATE_LOCATED. ACCESS RESTRICTION: the held copy prints "For Official Use Only"; owner decision on retention/use required before any registration or use.'),
    ('ST-NAVY-REGS', 'Cross-service regulations', 'Regulations for the Navy Parts I-IV (Part IV = Indian Naval Auxiliary Service Regulations 1973)', 'regulations', 'HELD_UNREGISTERED',
     ['68dd1cea', '884a893c', '272e4c22', 'e4148ee0'], [], 'C5-SRC-P2-RNAVY-PT1;C5-SRC-P2-RNAVY-PT2;C5-SRC-P2-RNAVY-PT3;C5-SRC-P2-INAS-1973', '(none)', None,
     'raw-data retrieval records (India Code compilations); no access marking found on first pages (keyword hits are body text)', 'CORRECTION: C5 says NOT_HELD for all four sources.'),
    ('ST-ARMY-ORDERS', 'Orders', 'Army Orders / Army Instructions / Special Army Orders affecting statutory powers', 'orders', 'NOT_FOUND_AFTER_DOCUMENTED_SEARCH',
     [], [], 'C5-SRC-P0-ARMY-ORDERS-INSTRUCTIONS', '', r'army orders?\b|army instructions?|special army order', 'search: C5 (NOT_FOUND_IN_SEARCHED_SOURCES) + C10 held-copy search', '10 crosswalk rows MISSING_EVIDENCE. Many are not publicly published (out of scope per CLAUDE.md).'),
    ('ST-CCCM-1978', 'Criminal courts and courts-martial', 'Criminal Courts and Court-martial (Adjustment of Jurisdiction) Rules 1978 and S.O. 4010/1986', 'rules', 'LOCATED_NOT_ACQUIRED',
     [], ['fa51a4b1'], 'C5-SRC-P1-CCCM-ADJ-RULES', 'I-CCCM-1978;I-CCCM-SO4010-1986', r'adjustment of jurisdiction|4010', 'in PR #8 authorised scope (ACQ-01 B2); execution pending (AP-C9-01)', 'Rajya Sabha papers-laid page fa51a4b1 (working store only) carries the date dispute (ESC-SO4010-1986).'),
    ('ST-RS-PAPERS-1987', 'Criminal courts and courts-martial', 'Rajya Sabha Debates 03-03-1987, Papers Laid (S.O. 4010/1986 entry)', 'parliamentary record', 'HELD_PROVENANCE_UNCERTAIN',
     ['fa51a4b1'], [], 'C5-SRC-P2-RS-PAPERS-LAID-1987', 'C9-AG-CCCM-SO4010', None, 'registered PROVENANCE_UNDOCUMENTED_COPY', 'PRESERVATION: working store only. Carries reading (a) of ESC-SO4010-1986.'),
    ('ST-DPP-1950', 'Other Acts', 'Army and Air Force (Disposal of Private Property) Act 1950: compilation (English, Hindi)', 'consolidated', 'HELD_SECONDARY_COMPILATION_ONLY',
     ['0884f3b5', '6ca297a1'], [], 'C5-SRC-P1-DPP-ACT-1950', 'I-DPP-1950', None, 'raw-data retrieval records', 'Amendment Act 2000 not held (LOCATED via pins needing metadata).'),
    ('ST-DPP-RULES-1953', 'Other Acts', 'Army and Air Force (Disposal of Private Property) Rules 1953, S.R.O. 308 of 11-07-1953', 'rules', 'HELD_UNREGISTERED',
     ['d969593b'], [], '(none)', '(none)', None, 'India Code text rendition; raw-data retrieval record', ''),
    ('ST-AFA-1950', 'Other Acts', 'Air Force Act 1950: India Code compilation (English, Hindi)', 'consolidated', 'HELD_SECONDARY_COMPILATION_ONLY',
     ['ef50375e', '0ccc8002'], [], '(none)', 'I-AFA-1950', None, 'raw-data retrieval records', ''),
    ('ST-NA-1957', 'Other Acts', 'Navy Act 1957: India Code compilation (English, Hindi)', 'consolidated', 'HELD_SECONDARY_COMPILATION_ONLY',
     ['db6d2b3e', 'ac7acfc7'], [], '(none)', 'I-NA-1957', None, 'raw-data retrieval records', ''),
    ('ST-ISO-2023', 'Other Acts', 'Inter-Services Organisations (Command, Control and Discipline) Act 2023 and Rules 2025', 'Act and rules', 'NOT_FOUND_AFTER_DOCUMENTED_SEARCH',
     [], [], 'C5-SRC-P1-ISO-ACT-RULES', 'I-ISO-2023', r'inter-?services organisation', 'search scope: C10 held-copy search only; external discovery not done (C5 NOT_HELD_NOT_CHECKED)', '4 crosswalk rows MISSING_EVIDENCE.'),
    ('ST-TA-1948', 'Other Acts', 'Territorial Army Act, Rules and Regulations 1948', 'Act, rules, regulations', 'LOCATED_NOT_ACQUIRED',
     [], [], 'C5-SRC-P1-TA-ACT-1948;C5-SRC-P1-TA-RULES-1948;C5-SRC-P1-TA-REGULATIONS', 'C9-ACQ-099..101', r'territorial army', 'India Code URLs located; host BLOCKED_ACCESS in C5 (robots policy decision A-C5-6)', ''),
    ('ST-DHC-RULES-CH6', 'Court rules', 'Delhi High Court Rules, Chapter 6 (cases against Government servants)', 'court rules', 'HELD_PROVENANCE_UNCERTAIN',
     ['f69e18be'], [], 'C5-SRC-P2-DHC-RULES-CH6', '', None, 'registered PROVENANCE_UNDOCUMENTED_COPY (chapter extract)', 'PRESERVATION: working store only.'),
    ('ST-MML', 'Manuals', 'Manual of Military Law (8 owner-supplied files)', 'manual', 'HELD_PROVENANCE_UNCERTAIN',
     ['3a2e3a4f', 'db211918', '73fd3042', 'c8a791a1', '8bb17d82', 'ed1d8a7f', '67d788b3', 'dfce01c1'], [], 'C5-SRC-P2-MML-*', '', None,
     'registered HELD_UNVERIFIED_MANUAL; HF only (bytes NOT_CHECKED by C10); edition and access marking not assessed', 'Never current law.'),
]

STATUS_FIELDS = ['source_key', 'family', 'source', 'layer', 'c10_status', 'preservation_risk', 'held_sha256', 'held_presence',
                 'held_register_state', 'held_copy_evidence_class', 'related_held_sha256', 'c5_source_ids', 'c9_refs',
                 'search_regex', 'search_hits', 'basis', 'note']


def build_status(inv, texts, hf_paths, ledger_version):
    rows = []
    for (key, fam, src, layer, st, held, related, c5, c9, rx, basis, note) in SRC:
        if st not in STATUSES:
            die(f'{key}: unknown status {st}')
        if st == 'HELD_AUTHENTICATED' and ledger_version == 0:
            die(f'{key}: HELD_AUTHENTICATED impossible at AUTH-LEDGER version 0')
        hs = [resolve(inv, p) for p in held]
        rs = [resolve(inv, p) for p in related]
        if st.startswith('HELD_') and not hs:
            die(f'{key}: HELD status without held copies')
        if not st.startswith('HELD_') and hs:
            die(f'{key}: non-HELD status but held copies listed')
        if st == 'HELD_UNREGISTERED':
            bad = [h[:8] for h in hs if inv[h]['register_state'] != 'UNREGISTERED_HELD' or inv[h]['presence'] == WS_ONLY]
            if bad:
                die(f'{key}: HELD_UNREGISTERED but registered or working-store-only copies {bad}')
        hits = ''
        if not st.startswith('HELD_'):
            if not rx:
                die(f'{key}: LOCATED/NOT_FOUND row needs a search regex')
            rgx = re.compile(rx, re.I)
            h_inv = sorted(h[:12] for h, r in inv.items() if r['category'] != 'judgment' and rgx.search(' '.join([r['title'], r['doc_id'], r['category']])))
            h_txt = sorted(h[:12] for h, t in texts.items() if rgx.search(t))
            h_hf = sorted(p for p in hf_paths if rgx.search(p))
            hits = f'inventory_titles={len(h_inv)}{(":" + "/".join(h_inv)) if h_inv else ""}; raw_page_text={len(h_txt)}{(":" + "/".join(h_txt)) if h_txt else ""}; hf_legal_knowledge_paths={len(h_hf)}'
        pres = [inv[h]['presence'] for h in hs]
        risk = 'PRESERVATION_RISK' if hs and all(p == WS_ONLY for p in pres) else ('PARTIAL_PRESERVATION_RISK' if any(p == WS_ONLY for p in pres) else '')
        rows.append({
            'source_key': key, 'family': fam, 'source': src, 'layer': layer, 'c10_status': st, 'preservation_risk': risk,
            'held_sha256': ';'.join(hs), 'held_presence': ';'.join(sorted(set(pres))),
            'held_register_state': ';'.join(sorted(set(inv[h]['register_state'] for h in hs))),
            'held_copy_evidence_class': ';'.join(sorted(set(inv[h]['c5_copy_evidence_class'] or 'none' for h in hs))),
            'related_held_sha256': ';'.join(rs), 'c5_source_ids': c5, 'c9_refs': c9, 'search_regex': rx or '',
            'search_hits': hits, 'basis': basis, 'note': note})
    return rows


# ---------------------------------------------------------------- Task 2: registration proposals
# Curated identity for every held-but-unregistered non-judgment copy in HF/GitHub (the builder fails
# if any is missing). fields: identity, issuing authority, completeness, fidelity, target C5 source,
# proposed classification, remaining verification, AP-C9-02 membership.
APC902_RAW = ['338d43ad', '590cf7cd', 'fc27032f', 'c57b113a', '1c6db257', '8d774f1f', '7a5551ba', '0c2f4e9e',
              'd4449e99', '0884f3b5', 'fa8878e0', '06729a1f', '865cc3e1', 'ef50375e', 'db6d2b3e']
APC902_COMPILATIONS = ['e47a4265', '48f52219', '665863d1', '48f57c81', '572c7988', '554b2b4a', 'be619533']

GZ = 'GAZETTE_FACSIMILE (India Code-served scan/born-digital Gazette pages)'
TR = 'TEXT_RENDITION (India Code typeset text of the instrument as made)'
CP = 'GOVERNMENT_COMPILATION (consolidated, "As on" date)'
PROP_GZ = 'PROPOSE DOCUMENTED_PRIMARY_COPY candidate: retrieval record = raw-data manifest row of the approved 2026-11-21 India Code run; owner to decide whether that record is first-class evidence under rule 1'
PROP_CP = 'PROPOSE government-compilation copy (PROVENANCE documented by retrieval record); never Gazette evidence'
PROP_TR = 'PROPOSE text-rendition copy with documented retrieval record; not a facsimile'
REMV = 'page-image identity check of masthead/notification number by a human; owner decision under AUTH-LEDGER rule 1; no download needed'

REG = {
    '338d43ad': ('AFT Act 2007 (55 of 2007), Gazette Extraordinary Pt II s.1 No. 66, 28-12-2007 (C9R-RD-AFT07-IMG)', 'Parliament / Ministry of Law and Justice (Legislative Department)', 'complete Act text, 14 pp. (C9)', GZ, 'C5-SRC-P0-AFT-ACT-2007', PROP_GZ, REMV + '; correct crawl category rule->act (IC-CATEGORY-338d43addeaa)'),
    '590cf7cd': ('AFT (Procedure) Rules 2008, S.R.O. 26(E), Gazette Extraordinary Pt II s.4 No. 19, 17-09-2008', 'Ministry of Defence (Central Government, s.41)', '47 pp.; masthead present', GZ, 'C5-SRC-P1-AFT-PROC-RULES', PROP_GZ, REMV),
    'fc27032f': ('AFT (Procedure) Amendment Rules 2011, S.R.O. 05(E), Gazette Extraordinary Pt II s.4 No. 4, 29-07-2011', 'Ministry of Defence', '2 pp.', GZ, 'C5-SRC-P1-AFT-PROC-RULES', PROP_GZ, REMV),
    'c57b113a': ('AFT (Practice) Rules 2009, S.R.O. 6(E) dated 11-05-2009', 'Ministry of Defence', '12 pp.; Gazette masthead absent (publication date not on held pages)', 'GAZETTE_EXTRACT_WITHOUT_MASTHEAD', 'C5-SRC-P1-AFT-PROC-RULES', PROP_GZ + '; completeness flag INCOMPLETE (masthead)', REMV + '; masthead from ACQ03-032 if required'),
    '1c6db257': ('AFT Act (Removal of Difficulties) Order 2008, S.R.O. 18(E), Gazette Extraordinary Pt II s.4 No. 13, 21-07-2008', 'Central Government (s.40)', '1 p.', GZ, '(none: new source row needed)', PROP_GZ, REMV),
    '8d774f1f': ('S.R.O. 9(E) of 07-08-2009 establishing the AFT (Gazette Extraordinary Pt II s.4 No. 8)', 'Ministry of Defence (s.4)', '1 p.', GZ, '(none: new source row needed)', PROP_GZ, REMV),
    '03961b02': ('S.R.O. 9(E) of 07-08-2009 establishing the AFT: second copy (crawl title "AFT-Estt-Day"; C10R-AFT-ESTT-01)', 'Ministry of Defence (s.4)', '1 p.', GZ, '(none: same new source row as 8d774f1f)', PROP_GZ + '; record as SAME_LEGAL_DOCUMENT_DIFFERENT_BYTES with 8d774f1f', REMV),
    '7a5551ba': ('Finance Act 2017 (7 of 2017); Part XIV s.181 inserts AFT s.9A', 'Parliament', '92 pp. rendition', TR, '(none: new source row needed)', PROP_TR, 'confirm s.181 page; Part XIV commencement notification still not held'),
    '0c2f4e9e': ('Tribunals Reforms Act 2021 (33 of 2021)', 'Parliament', '17 pp. rendition with Legislative Department heading', TR, '(none: new source row needed)', PROP_TR, 'crawl category "notification" is wrong (Act)'),
    'd4449e99': ('Bharatiya Nyaya Sanhita 2023: India Code compilation as on 06-10-2025', 'Parliament (compiled by Legislative Department)', '112 pp.', CP, 'C5-SRC-P1-BNS-2023 (or a new -INDIACODE row)', PROP_CP, 'owner decision whether to open C5-SRC-P1-BNS-2023-INDIACODE as for BNSS/BSA'),
    'd163e785': ('Bharatiya Nyaya Sanhita 2023: Hindi text in Gazette Extraordinary Section 1A pagination pp.9-153 (C10R-BNS-H-01/02)', 'Legislative Department (authoritative Hindi text publication)', 'masthead, issue number/date and closing signature/imprint not on held pages', 'GAZETTE_PAGES_HINDI_WITHOUT_MASTHEAD (India Code watermark)', 'C5-SRC-P1-BNS-2023 (language/edition distinct: new source row recommended)', 'PROPOSE separate Hindi-text source row; HELD_INCOMPLETE; not a substitute for the English Gazette', 'human identity check (issue number/date unknown); Hindi-reading reviewer'),
    '60d145c5': ('Bharatiya Nagarik Suraksha Sanhita 2023: Hindi text, Gazette Section 1A pagination pp.155-473 (C10R-BNSS-H-01/02)', 'Legislative Department', 'masthead and closing page not held', 'GAZETTE_PAGES_HINDI_WITHOUT_MASTHEAD (India Code watermark)', 'C5-SRC-P0-BNSS-2023 (new Hindi source row recommended)', 'PROPOSE separate Hindi-text source row; HELD_INCOMPLETE', 'human identity check; Hindi-reading reviewer'),
    '72fc9a75': ('Bharatiya Sakshya Adhiniyam 2023: Hindi text, Gazette Section 1A pagination pp.475-535, signed, GoI Press imprint 27-03-2024 (C10R-BSA-H-01/02)', 'Legislative Department', 'Act text from start to signature; issue masthead not held', 'GAZETTE_PAGES_HINDI_WITHOUT_MASTHEAD (India Code watermark; digital-signature box)', 'C5-SRC-P0-BSA-2023 (new Hindi source row recommended)', 'PROPOSE separate Hindi-text source row; HELD_INCOMPLETE', 'human identity check; signature validity not checked'),
    '0884f3b5': ('Army and Air Force (Disposal of Private Property) Act 1950: compilation as on 21-07-2025', 'Parliament (compiled)', '10 pp.', CP, 'C5-SRC-P1-DPP-ACT-1950', PROP_CP, ''),
    '6ca297a1': ('DPP Act 1950: Hindi compilation', 'Parliament (compiled)', '5 pp.', CP + ' Hindi', 'C5-SRC-P1-DPP-ACT-1950', PROP_CP, 'Hindi-reading reviewer'),
    'd969593b': ('Army and Air Force (Disposal of Private Property) Rules 1953, S.R.O. 308 of 11-07-1953', 'Ministry of Defence (s.16)', '6 pp.', TR, '(none: new source row needed)', PROP_TR, 'amendment state not established'),
    'fa8878e0': ('Indian Penal Code 1860 (45 of 1860), India Code rendering marked "Rep., Act 45 of 2023"', 'Parliament (compiled)', '119 pp.', CP, 'C5-SRC-P1-IPC-CRPC-IEA', PROP_CP, 'edition date; text as at 30-06-2024 not established'),
    '06729a1f': ('Indian Evidence Act 1872 (1 of 1872), India Code rendering', 'Legislature (compiled)', '61 pp.', CP, 'C5-SRC-P1-IPC-CRPC-IEA', PROP_CP, 'edition date'),
    '865cc3e1': ('Code of Criminal Procedure 1973 (2 of 1974), India Code copy ("1974-2.pdf"; C9: 1974 print)', 'Parliament', '259 pp.', 'TEXT_RENDITION/PRINT (edition not established)', 'C5-SRC-P1-IPC-CRPC-IEA', PROP_TR, 'not as at repeal'),
    '982059ca': ('Code of Criminal Procedure 1973, consolidated (official_copies host)', 'Parliament (compiled)', '226 pp.', CP, 'C5-SRC-P1-IPC-CRPC-IEA', PROP_CP, 'edition date; host provenance in raw_manifest'),
    'ef50375e': ('Air Force Act 1950: compilation as on 21-07-2025', 'Parliament (compiled)', '55 pp.', CP, '(none: new source row needed)', PROP_CP, ''),
    '0ccc8002': ('Air Force Act 1950: Hindi compilation', 'Parliament (compiled)', '37 pp.', CP + ' Hindi', '(none)', PROP_CP, 'Hindi-reading reviewer'),
    'db6d2b3e': ('Navy Act 1957: compilation as on 01-06-2026', 'Parliament (compiled)', '63 pp.', CP, '(none: new source row needed)', PROP_CP, ''),
    'ac7acfc7': ('Navy Act 1957: Hindi compilation', 'Parliament (compiled)', '49 pp.', CP + ' Hindi', '(none)', PROP_CP, 'Hindi-reading reviewer'),
    '42b9a2f8': ('Army Act 1950: Hindi compilation', 'Parliament (compiled)', '38 pp.', CP + ' Hindi', 'C5-SRC-P0-ARMY-ACT-1950-INDIACODE (additional copy row)', PROP_CP, 'Hindi-reading reviewer'),
    '3a551c1f': ('Army Act 1950: India Code item "THE SCHEDULE" (note: repealed by RAA 1957; C10R-AA-SCH-01)', 'India Code (compiler note)', '1 p.', 'COMPILER_NOTE', 'C5-SRC-P0-ARMY-ACT-1950-INDIACODE (component)', 'PROPOSE as component of the compilation; not a source copy of any instrument', ''),
    'd5e5554b': ('BNSS 2023 First Schedule (India Code file)', 'Parliament (compiled)', '47 pp.', CP, 'C5-SRC-P0-BNSS-2023-INDIACODE (component)', PROP_CP, ''),
    '0cdc96bb': ('BNSS 2023 Second Schedule (India Code file)', 'Parliament (compiled)', '61 pp.', CP, 'C5-SRC-P0-BNSS-2023-INDIACODE (component)', PROP_CP, ''),
    '63797c96': ('BSA 2023 Schedule (India Code file)', 'Parliament (compiled)', '2 pp.', CP, 'C5-SRC-P0-BSA-2023-INDIACODE (component)', PROP_CP, ''),
    '3ad875b6': ('Correspondence table BNS 2023 / IPC 1860 (CAPT Bhopal)', 'Central Academy for Police Training, Bhopal (authored)', '38 pp.', 'SECONDARY_REFERENCE', '(none)', 'PROPOSE secondary-reference row only; never statutory authority', ''),
    'aa3e4914': ('Correspondence table BNSS 2023 / CrPC 1973 (CAPT Bhopal)', 'CAPT Bhopal (authored)', '38 pp.', 'SECONDARY_REFERENCE', '(none)', 'PROPOSE secondary-reference row only', ''),
    '7693f293': ('Correspondence table BSA 2023 / IEA 1872 (CAPT Bhopal)', 'CAPT Bhopal (authored)', '14 pp.', 'SECONDARY_REFERENCE', '(none)', 'PROPOSE secondary-reference row only', ''),
    '4284820e': ('Regulations for the Air Force, Reprinted Edition 2000 (marked "For Official Use Only")', 'Government of India (Defence Services Regulations)', '1,320 pp.', CP, 'C5-SRC-P2-RAF-1964', 'HOLD: access-marking decision first (FOUO printed); then government-compilation copy', 'owner/legal decision on FOUO material before registration or any use'),
    '68dd1cea': ('Regulations for the Navy Part I', 'Government of India / Naval Headquarters', '487 pp.', CP, 'C5-SRC-P2-RNAVY-PT1', PROP_CP, 'edition/amendment date'),
    '884a893c': ('Regulations for the Navy Part II (Statutory)', 'Government of India', '188 pp.', CP, 'C5-SRC-P2-RNAVY-PT2', PROP_CP, 'edition/amendment date'),
    '272e4c22': ('Regulations for the Navy Part III (Statutory)', 'Government of India', '253 pp.', CP, 'C5-SRC-P2-RNAVY-PT3', PROP_CP, 'edition/amendment date'),
    'e4148ee0': ('Regulations for the Navy Part IV = Indian Naval Auxiliary Service Regulations 1973 (C10R-NAVY-IV-01)', 'Government of India', '99 pp.', CP, 'C5-SRC-P2-INAS-1973', PROP_CP, 'edition/amendment date'),
    'f9e11e04': ('Navy (Pension) Regulations 1964, S.R.O. 74 of 10-02-1964', 'Central Government (Navy Act s.184)', '319 pp.', CP, 'C5-SRC-P2-PEN-REGS-AF-NAVY', PROP_CP, 'amendment state'),
}
for _p, _t in [('2027fecd', 'Kolkata Bench, S.R.O. 18(E) of 18-11-2009'), ('34584afa', 'Guwahati Bench, S.R.O. 10(E) of 28-07-2010 (image only; C10R-AFT-GUW-01)'),
               ('38d8adfa', 'Srinagar (Jammu) Bench, S.R.O. 12(E) of 16-11-2016'), ('3aa43869', 'Lucknow Bench, S.R.O. 16(E) of 05-11-2009'),
               ('420b7bf5', 'Kochi Bench, S.R.O. 19(E) of 02-12-2009'), ('48a01377', 'Jurisdiction of Srinagar, S.R.O. 4(E) of 22-03-2017'),
               ('59974179', 'Mumbai Bench, S.R.O. 4(E) of 06-06-2011'), ('61353e0f', 'Chandigarh Bench, S.R.O. 17(E) of 10-11-2009'),
               ('66a84e53', 'Jabalpur Bench notification of 03-05-2016'), ('be9e3e7e', 'Chennai/Telangana jurisdiction, S.R.O. 02(E) of 26-02-2015 (C10R-AFT-CHN-01)'),
               ('c32157ed', 'Jaipur Bench, S.R.O. 15(E) of 28-10-2009'), ('d483c44d', 'Jurisdiction for Telangana = S.R.O. 02(E)/2015, second copy (C10R-AFT-CHN-02)'),
               ('d56bded1', 'Jurisdiction of Jabalpur, S.R.O. 3(E) of 22-03-2017')]:
    REG[_p] = (f'AFT bench notification under s.5(4): {_t} (number/date from page text; text-layer reading)', 'Ministry of Defence', '1 p.', GZ, '(none: new source row "AFT bench notifications" needed)', PROP_GZ, REMV)
for _p, _t in [('14c19950', 'AFT (Financial and Administrative Powers) Rules 2008, Gazette 12-09-2008'), ('9565ce77', 'AFT Procedure & Investigation Rules 2008 (crawl title), Gazette weekly 20-26 July 2008'),
               ('4553e112', 'AFT Salary Rules 2009, Gazette 18-05-2009'), ('379c4e0a', 'Exemption from UPSC consultation (Gazette Pt II s.3(i) No. 332, 21-06-2011)'),
               ('5a7ea50c', 'AFT Group A recruitment rules, S.R.O. 04(E) of 23-04-2018'), ('2e90ba87', 'AFT Group B recruitment rules (2018)'),
               ('e2ee7755', 'AFT Group C posts rules, S.R.O. 2(E) of 10-06-2013'), ('c85c9c0e', 'AFT Accounts Cadre posts rules, S.R.O. 11(E) of 12-06-2019'),
               ('0c030041', 'Amendment to AFT Accounts Cadre recruitment rules, S.R.O. 13(E) of 06-09-2019')]:
    REG[_p] = (f'{_t} (text-layer reading of p.1)', 'Ministry of Defence', 'as held', GZ, '(none)', 'DEFER (low legal consequence); register on owner request as Gazette copy with retrieval record', REMV)

REG_FIELDS = ['sha256', 'bytes', 'category_crawl', 'identity', 'issuing_authority', 'source_url', 'retrieved_at', 'presence',
              'hf_byte_verification', 'completeness', 'fidelity_class', 'existing_register_relationship', 'target_c5_source',
              'crosswalk_rows_for_target', 'equivalence_groups', 'proposed_authentication_classification', 'remaining_verification',
              'ap_c9_02_membership', 'ap_c9_02_c10_change']


def build_registration(inv, master, crosswalk, equiv):
    cw = {}
    for r in crosswalk:
        cw.setdefault(r['source_id'], {}).setdefault(r['evidence_status'], 0)
        cw[r['source_id']][r['evidence_status']] += 1
    msrc = {r['source_id']: r for r in master}
    eq = {}
    for g in equiv:
        for h in g['sha256s'].split(';'):
            eq.setdefault(h, []).append(f"{g['group_id']}:{g['classification']}")
    targets = [h for h, r in inv.items() if r['register_state'] == 'UNREGISTERED_HELD' and r['category'] not in ('judgment', 'linked_records')]
    full = {resolve(inv, p): v for p, v in REG.items()}
    missing = [h[:8] for h in targets if h not in full]
    if missing:
        die(f'registration proposals missing curated identity for {missing}')
    extra = [h[:8] for h in full if h not in targets]
    if extra:
        die(f'curated registration identity for copies not unregistered-held: {extra}')
    raw902 = {resolve(inv, p) for p in APC902_RAW}
    comp902 = {resolve(inv, p) for p in APC902_COMPILATIONS}
    rows = []
    for h in sorted(targets, key=lambda x: (inv[x]['category'], inv[x]['title'], x)):
        ident, auth, compl, fid, tgt, prop, remv = full[h]
        r = inv[h]
        cwc = []
        for sid in re.findall(r'C5-SRC-[A-Z0-9-]+', tgt):
            if sid in cw:
                cwc.append(f'{sid}: ' + ', '.join(f'{k}={v}' for k, v in sorted(cw[sid].items())))
            elif sid in msrc:
                cwc.append(f'{sid}: 0 rows')
        rel = []
        for sid in re.findall(r'C5-SRC-[A-Z0-9-]+', tgt):
            if sid in msrc:
                rel.append(f"{sid} holding_state={msrc[sid]['holding_state']}")
        if h in raw902:
            mem, chg = 'IN_AP-C9-02 (15 raw-store documents)', 'KEEP'
        else:
            mem = 'NOT_IN_AP-C9-02'
            if 'DEFER' in prop:
                chg = 'ADD_OPTIONAL_LOW_PRIORITY'
            elif 'HOLD' in prop:
                chg = 'ADD_AFTER_ACCESS_MARKING_DECISION'
            elif 'secondary-reference' in prop:
                chg = 'ADD_AS_SECONDARY_REFERENCE_ONLY'
            else:
                chg = 'ADD'
        rows.append({'sha256': h, 'bytes': r['bytes'], 'category_crawl': r['category'], 'identity': ident, 'issuing_authority': auth,
                     'source_url': r['source_url'], 'retrieved_at': r['retrieved_at'], 'presence': r['presence'],
                     'hf_byte_verification': r['hf_byte_verification'], 'completeness': compl, 'fidelity_class': fid,
                     'existing_register_relationship': '; '.join(rel) or 'none', 'target_c5_source': tgt,
                     'crosswalk_rows_for_target': '; '.join(cwc) or '0', 'equivalence_groups': ';'.join(eq.get(h, [])),
                     'proposed_authentication_classification': prop, 'remaining_verification': remv,
                     'ap_c9_02_membership': mem, 'ap_c9_02_c10_change': chg})
    # the 7 registered compilations in AP-C9-02: provenance attachment, not registration
    for h in sorted(comp902):
        r = inv[h]
        rows.append({'sha256': h, 'bytes': r['bytes'], 'category_crawl': r['category'], 'identity': r['title'] + ' (already registered)',
                     'issuing_authority': '', 'source_url': r['source_url'], 'retrieved_at': r['retrieved_at'], 'presence': r['presence'],
                     'hf_byte_verification': r['hf_byte_verification'], 'completeness': '', 'fidelity_class': CP if r['category'] != 'act_amendment' else GZ,
                     'existing_register_relationship': f"REGISTERED {r['c5_copy_ids']} ({r['c5_copy_evidence_class']})", 'target_c5_source': r['c5_source_ids'],
                     'crosswalk_rows_for_target': '; '.join(f'{s}: ' + ', '.join(f'{k}={v}' for k, v in sorted(cw.get(s, {}).items())) for s in r['c5_source_ids'].split(';') if s),
                     'equivalence_groups': ';'.join(eq.get(h, [])),
                     'proposed_authentication_classification': 'ATTACH retrieval record (raw-data manifest row) to the existing copy row as a provenance lead; no new copy row; class change only by owner decision under rule 1',
                     'remaining_verification': 'owner decision; no download', 'ap_c9_02_membership': 'IN_AP-C9-02 (7 held compilations)',
                     'ap_c9_02_c10_change': 'RESTATE_AS_PROVENANCE_ATTACHMENT'})
    # linked_records: summarised, not proposed
    lr = sorted(h for h, r in inv.items() if r['category'] == 'linked_records')
    for h in lr:
        r = inv[h]
        rows.append({'sha256': h, 'bytes': r['bytes'], 'category_crawl': 'linked_records', 'identity': r['title'], 'issuing_authority': 'India Code (search API JSON)',
                     'source_url': r['source_url'], 'retrieved_at': r['retrieved_at'], 'presence': r['presence'], 'hf_byte_verification': r['hf_byte_verification'],
                     'completeness': '', 'fidelity_class': 'DISCOVERY_METADATA (JSON listing)', 'existing_register_relationship': 'none', 'target_c5_source': '(none)',
                     'crosswalk_rows_for_target': '0', 'equivalence_groups': '', 'proposed_authentication_classification': 'DO NOT REGISTER as a source copy; keep as discovery metadata',
                     'remaining_verification': '', 'ap_c9_02_membership': 'NOT_IN_AP-C9-02', 'ap_c9_02_c10_change': 'EXCLUDE (metadata)'})
    return rows


# ---------------------------------------------------------------- Task 3: amendment graph
SEARCH_EDGE = {  # regexes for every C9 NOT_LOCATED edge (amending instrument identity)
    'C9-AG-AR-001': r'\be-?7\b.{0,20}1960|first amendment\) rules,? 1960',
    'C9-AG-AR-002': r's\.?\s*r\.?\s*o\.?\s*331\b', 'C9-AG-AR-003': r's\.?\s*r\.?\s*o\.?\s*348\b',
    'C9-AG-AR-004': r's\.?\s*r\.?\s*o\.?\s*351\b', 'C9-AG-AR-005': r's\.?\s*r\.?\s*o\.?\s*404\b',
    'C9-AG-AR-012': r'army.{0,30}amendment.{0,10}rules,? 1966', 'C9-AG-AR-013': r'army.{0,30}amendment.{0,10}rules,? 1967',
    'C9-AG-AR-015': r'army.{0,30}amendment.{0,10}rules,? 1974', 'C9-AG-AR-030': r's\.?\s*r\.?\s*o\.?\s*258\b',
    'C9-AG-AR-032': r's\.?\s*r\.?\s*o\.?\s*22\b.{0,30}2010|army.{0,20}amendment.{0,10}rules,? 2010',
    'C9-AG-AR-036': r'army.{0,20}amendment.{0,10}rules,? 20(2[2-6])',
    'C9-AG-AR-037': r'army.{0,20}amendment.{0,10}rules,? 195[5-9]', 'C9-AG-AR-038': r'army.{0,20}amendment.{0,10}rules,? 195[5-9]',
    'C9-AG-AR-039': r'army.{0,20}amendment.{0,10}rules,? 195[5-9]', 'C9-AG-AR-040': r'army.{0,20}amendment.{0,10}rules,? 195[5-9]',
    'C9-AG-AR-041': r'army.{0,20}amendment.{0,10}rules', 'C9-AG-AR-042': r'army.{0,20}amendment.{0,10}rules',
    'C9-AG-AR-043': r's\.?\s*r\.?\s*o\.?\s*66\b', 'C9-AG-AR-044': r'army.{0,20}amendment.{0,10}rules',
    'C9-AG-AR-045': r'army \(first amendment\) rules,? 1972', 'C9-AG-AR-046': r'army.{0,20}amendment.{0,10}rules',
    'C9-AG-AA-00': r's\.?\s*r\.?\s*o\.?\s*120\b', 'C9-AG-AA-02': r'adaptation of laws', 'C9-AG-AA-03': r'repealing and amending act,? 1960',
    'C9-AG-AA-04': r'repealing and amending act,? 1974', 'C9-AG-AA-05': r'ordinance,? 1975', 'C9-AG-AA-07': r'delegated legislation provisions? \(amendment\) act,? 1983',
    'C9-AG-AA-09': r'repealing and amending act,? 2001', 'C9-AG-AA-10': r'repealing and amending \(second\) act,? 2017',
    'C9-AG-AA-11': r'bill no\.? ?251', 'C9-AG-AA-12': r'bill no\.? ?30 of 1954', 'C9-AG-AA-13': r'army \(amendment\) act,? (199[3-9]|20\d\d)',
    'C9-AG-AA-C3-01': r'adaptation of laws', 'C9-AG-AA-C3-02': r'3912', 'C9-AG-AA-C3-03': r'repealing and amending act,? 1957',
    'C9-AG-AA-C3-04': r'regulation 12 of 1962|goa, daman', 'C9-AG-AA-C3-05': r'in\.gazette\.e\.1950\.306|army act.{0,20}as enacted',
    'C9-AG-AFT-00': r'\b14\s*\((e|E|अ)\)|13-06-2008',
    'C9-AG-BNS-COMM': r'\b850\s*\(e\)', 'C9-AG-BNSS-COMM': r'\b848\s*\(e\)', 'C9-AG-BSA-COMM': r'\b849\s*\(e\)',
    'C9-AG-BNSS-REPEAL': r'bharatiya nagarik suraksha sanhita', 'C9-AG-BSA-REPEAL': r'bharatiya sakshya adhiniyam',
}
CHANGES = {
    'C9-AG-BNSS-REPEAL': ('UNRESOLVED_COMMENCEMENT', 'STATUS_CHANGED',
                          'The repealing instrument (BNSS, s.531) is held in HF and GitHub: registered India Code compilation 572c79880b9f8eff (C9R-BNSS-03, p.174) and Hindi Gazette Section 1A text 60d145c5964afc41 (C10R-BNSS-H-01). C9 kept NOT_LOCATED from the C8 matrix although the compilation is registered; C9 already classed the parallel BNS repeal edge (C9-AG-BNS-REPEAL) UNRESOLVED_COMMENCEMENT on a compilation copy. Commencement still not evidenced: S.O. 848(E) not held. Held copies are compilation and incomplete Hindi Gazette text, not the English Gazette.'),
    'C9-AG-BSA-REPEAL': ('UNRESOLVED_COMMENCEMENT', 'STATUS_CHANGED',
                         'The repealing instrument (BSA, s.170) is held in HF and GitHub: registered compilation 554b2b4ae3d9f09b (C9R-BSA-03, p.51) and Hindi Gazette Section 1A text 72fc9a751097cb63 (C10R-BSA-H-01/02). Same reasoning as C9-AG-BNSS-REPEAL. S.O. 849(E) not held; commencement not evidenced.'),
    'C9-AG-AFT-00': (None, 'EVIDENCE_ADDED',
                     'Still NOT_LOCATED. Held copies mention "S.R.O. 14(E), dated 21st October, 2009" (bench jurisdiction; C10R-AFT-CHN-01/02); that is a different instrument from S.O. 14(E) of 13-06-2008. No identity inference.'),
    'C9-AG-AA-C3-03': (None, 'EVIDENCE_ADDED',
                       'Still NOT_LOCATED. India Code item 3a551c1f prints "THE SCHEDULE.—Rep. by the Repealing and Amending Act, 1957 (36 of 1957), s. 2 and the First Schedule" (C10R-AA-SCH-01): compiler statement only.'),
    'C9-AG-AFTSRO9E2009': (None, 'EVIDENCE_ADDED', 'Second held copy of S.R.O. 9(E)/2009: 03961b02ab4567b4 (C10R-AFT-ESTT-01), different bytes, same instrument.'),
    'C9-AG-BNS-COMM': (None, 'EVIDENCE_ADDED', 'Still NOT_LOCATED. Hindi Gazette text of BNS (d163e785) is held but carries the Act, not the S.O. 850(E) notification.'),
    'C9-AG-BNSS-COMM': (None, 'EVIDENCE_ADDED', 'Still NOT_LOCATED. Hindi Gazette text of BNSS (60d145c5) is held but carries the Act, not S.O. 848(E).'),
    'C9-AG-BSA-COMM': (None, 'EVIDENCE_ADDED', 'Still NOT_LOCATED. Hindi Gazette text of BSA (72fc9a75) is held but carries the Act, not S.O. 849(E).'),
}


def build_graph(c9graph, inv, texts, hf_paths):
    rows = []
    seen = set()
    for r in c9graph:
        e = r['edge_id']
        st = r['status']
        new, chg, ev = None, 'UNCHANGED', ''
        if e in CHANGES:
            new, chg, ev = CHANGES[e]
            seen.add(e)
        if st == 'NOT_LOCATED':
            if e not in SEARCH_EDGE:
                die(f'no search regex for NOT_LOCATED edge {e}')
            rgx = re.compile(SEARCH_EDGE[e], re.I)
            h_inv = sorted(h[:12] for h, x in inv.items() if x['category'] != 'judgment' and rgx.search(x['title'] + ' ' + x['doc_id']))
            h_txt = sorted(h[:12] for h, t in texts.items() if rgx.search(t))
            h_hf = [p for p in hf_paths if rgx.search(p)]
            srch = (f'C10 search /{SEARCH_EDGE[e]}/i: inventory titles {len(h_inv)}{(" [" + "/".join(h_inv) + "]") if h_inv else ""}; '
                    f'raw page text {len(h_txt)}{(" [" + "/".join(h_txt[:8]) + (" ..." if len(h_txt) > 8 else "") + "]") if h_txt else ""}; HF legal_knowledge paths {len(h_hf)}')
            if not new:
                srch += '. No hit is a copy of the amending instrument itself (hits, if any, are lists, footnotes or the target compilation).'
            ev = (ev + ' | ' if ev else '') + srch
        out = dict(r)
        out['c10_status'] = new or st
        out['c10_change'] = chg
        out['c10_evidence'] = ev  # C9 'evidence' is kept; C10 search evidence is separate (gate CSV check)
        rows.append(out)
    if seen != set(CHANGES):
        die(f'CHANGES reference unknown edges {set(CHANGES) - seen}')
    return rows


# ---------------------------------------------------------------- escalation register
ESC = [
    ('ESC-R23-3', 'Army Rule 23(3) caution wording', 'C9-AG-RES-C-01;C9-AG-RES-U-01',
     'Gazette of 27-11-1954 (S.R.O. 484, archival facsimile c5ef95a9, printed p.300): "You are not obliged to say anything unless you wish to do so"',
     'India Code compilation (48f52219) p.41: "You are obliged to say anything unless you wish to do so"',
     'ESCALATED_TO_LEGAL_ADVISER (conflict C-01 CONFLICTING, retained until legal review)',
     'No C10 change. The Gazette copy carrying reading (a) is working-store only (PRESERVATION_RISK); the compilation is in HF/GitHub.'),
    ('ESC-R23-2022', 'Unsupported "r.23 amended 2022"', '(no edge: no instrument)',
     'Registers: no instrument amends r.23 (R23-VERIFY-01 / C5-CF-U-01, 31 instruments 1960-2022); S.R.O. 6(E)/2022 amends r.16A(4) only (C8 D-AMC-AR-035); C8 review RC-01 removed the claim from EV-016, HCE-010, SC03',
     'An earlier research statement that r.23 was amended in 2022 (no supporting instrument ever identified)',
     'OPEN_UNSUPPORTED: not to be relied on; closure needs the post-06-06-2022 S.R.O.s (10 pinned candidates), E-7/1960, S.R.O. 258/2002 and the AR hints image-checked; legal adviser on C-01',
     'C10: no held copy in HF/GitHub of any post-2022 Army Rules instrument; S.R.O. 6(E)/2022 copy 2bdab5b7 is working-store only.'),
    ('ESC-R168-2', 'Army Rule 168(2) field-punishment words', 'C9-AG-AR168',
     'S.R.O. 17(E)/1993 item 31 omits the words (held e9bf2114 p.17)', 'India Code compilation r.168(2) still prints them (48f52219 p.189)',
     'OWNER_TO_REGISTER_CONFLICT then LEGAL_ADVISER (not in any conflict register)',
     'No C10 change. 1993 Gazette copy is working-store only (PRESERVATION_RISK). S.R.O. 331/1960 (also r.168(2)) remains LOCATED_NOT_ACQUIRED.'),
    ('ESC-SRO34-1963', 'S.R.O. 34 of 1963 identity', 'C9-AG-AR-008;C9-AG-SRO240-1955',
     'Held S.R.O. 34 dated 05-01-1963 is a r.188(e) declaration, not an amendment (4acdb1a8)',
     "Gazette NOTEs to 1982-1991 amendments list 'SRO 34 dated 5 Jun 63' among amendments; S.R.O. 2(E)/2018 lists 'S.R.O. 34 dated 05th January, 1963'",
     'OWNER_DISCOVERY_APPROVAL_PENDING (AP-C9-05: June-July 1963 Part II-S4 issues) then LEGAL_ADVISER',
     'No C10 change; no 1963 Part II-S4 issue in HF/GitHub (C10 search). Held copy 4acdb1a8 is working-store only.'),
    ('ESC-SO4010-1986', 'S.O. 4010/1986 date', 'C9-AG-CCCM-SO4010',
     "Rajya Sabha papers-laid page (fa51a4b1): 'Notification S.O. No. 4010, dated the 6th December, 1986'",
     'PILOT-01 / ACQ-01 B2: notification dated 24-11-1986 published in the Gazette of 06-12-1986 (C5 RV-01 says 8 Dec 1986)',
     'OWNER_ACQUISITION_EXECUTION_PENDING (AP-C9-01, PR #8 authorised scope) then page check',
     'No C10 change; notification not held anywhere. fa51a4b1 is working-store only.'),
    ('ESC-ACT37-1992', 'Act 37/1992 commencement', 'C9-AG-AA-08-s2..C9-AG-AA-08-s19 (18 edges)',
     'Gazette scan f11d443e: assent 06-09-1992, Gazette No.59 of 07-09-1992, no commencement clause',
     "Compilation prints 'w.e.f. 6-9-1992' only at ss.75-76, s.127 and Ch XVI; other provisions carry undated footnotes",
     'ESCALATED_TO_LEGAL_ADVISER (AQ-05: effect of an Act without a commencement clause); optional 1992 Gazette check',
     'No C10 change. All three Act 37/1992 copies are working-store only (PRESERVATION_RISK). No date inferred.'),
    ('ESC-AFT-COMMENCEMENT', 'AFT Act commencement and establishment', 'C9-AG-AFT-00;C9-AG-AFTSRO9E2009',
     'Compilation footnote to s.1(2): commencement 15-06-2008 vide S.O. 14(E) dated 13-06-2008 (notification not held)',
     'S.R.O. 9(E) of 07-08-2009 establishes the Tribunal w.e.f. 10-08-2009 (held 8d774f1f, 03961b02); a different event, not s.1(2) commencement',
     'OWNER_DISCOVERY_APPROVAL_PENDING (AP-C9-05) for S.O. 14(E)/2008; LEGAL_ADVISER on the relationship of the two dates',
     'C10: S.R.O. 14(E) of 21-10-2009 (bench jurisdiction) is a number collision, not the s.1(2) notification. Both readings preserved.'),
    ('ESC-AFT-PROC-RULES', 'AFT procedural rules commencement', 'C9-AG-AFTPR2008;C9-AG-AFTPR2011;C9-AG-AFTPRAC2009;C9-AG-AFT-05',
     'Procedure Rules 2008 (S.R.O. 26(E), Gazette 17-09-2008) and Amendment Rules 2011 (S.R.O. 05(E), 29-07-2011): EVIDENCED in C9 from held Gazette pages',
     'Practice Rules 2009 (S.R.O. 6(E) dated 11-05-2009): commence "from the date of publication in the official gazette"; publication date not on the held pages',
     'OWNER_REGISTRATION_DECISION_PENDING (AP-C9-02, revised) and optional ACQ03-032 masthead; no inference of publication date from the notification date',
     'No status change. All three are held in HF/GitHub, unregistered; C5 still says NOT_HELD_NOT_CHECKED.'),
    ('ESC-TRA2026-COMMENCEMENT', 'AFT s.9A under TRA 2026', 'C9-AG-AFT-03;C9-AG-AFT-04;C9-AG-TRA2021-REPEAL',
     'TRA 2026 s.1(2): commencement by notification; different dates may be appointed', "Compilation: s.9A 'w.e.f. 25-08-2026'",
     'OWNER_DISCOVERY_APPROVAL_PENDING (TRA 2026 notifications; no candidate)', 'No C10 change.'),
]
ESC_FIELDS = ['matter_id', 'matter', 'edges', 'reading_a', 'reading_b', 'escalation_status', 'c10_note']


# ---------------------------------------------------------------- Task 4: acquisition priorities
# factor levels 0-3 (X = access restriction penalty 0-2), documented per item; score is computed:
# score = 3*legal_consequence + 2*records_level + 2*source_quality_gap + no_alternative + 2*amend_commencement + readiness - access_penalty
# records_level: >=100 ->3, >=25 ->2, >=5 ->1, else 0. Commencement notifications use the upper bound of dependent records (stated).
ACQ = [
    # id, requirement, L, D(records), Q, A, C, R, X, records_basis, route
    ('AQ-AA-GAZ', 'Army Act 1950 as enacted (Gazette Extraordinary 1950)', 3, 185, 2, 3, 2, 2, 0, 'C9 gross 185 KB records', 'A-C5-1 + new crawler-config PR (archive.org pin md5 68bcdd4e...)'),
    ('AQ-AR-POST2022', 'Army Rules amendments after 06-06-2022 (10 candidates)', 3, 122, 3, 3, 3, 2, 0, 'Army Rules chain dependents (C9 122)', 'A-C5-1 + config PR (pins C5C-004..013)'),
    ('AQ-SANHITA-COMM', 'BNS/BNSS/BSA commencement notifications S.O. 850/848/849(E) of 2024', 3, 114, 3, 3, 3, 2, 0, 'upper bound 114 (1 direct); commencement affects every provision', 'A-C5-1 + config PR (pins C5C-021..023)'),
    ('AQ-AFT-SO14E', 'AFT Act s.1(2) commencement S.O. 14(E)/2008', 3, 89, 3, 3, 3, 0, 0, 'upper bound 89 (0 direct); commencement affects every provision', 'discovery approval (AP-C9-05); Indian-network egazette run'),
    ('AQ-AR-1960-2010', 'Army Rules S.R.O. 331/348/351/404 of 1960 and S.R.O. 22/2010', 2, 10, 3, 3, 3, 1, 0, 'C9: AR-004 5, AR-032 5', 'locate exact Gazette issues; A-C5-1'),
    ('AQ-AR-GAPS', 'E-7/1960 and S.R.O. 258/2002', 2, 0, 3, 3, 3, 0, 1, 'C9: 0 direct', 'custodian request (A-C5-3) or Indian-network egazette'),
    ('AQ-PRA-2008', 'Pension Regulations for the Army 2008 Parts I and II', 3, 34, 3, 3, 1, 1, 1, 'crosswalk 25 + 9 MISSING_EVIDENCE', 'A-C5-2 + allow-list beyond PR #9; robots 403 -> owner-side manual retrieval with sha256'),
    ('AQ-GMO-ER-2023', 'Guide to Medical Officers 2023 and complete Entitlement Rules 2023', 3, 14, 2, 3, 1, 1, 1, 'GMO 11 + ER 3', 'A-C5-2; PR #9 needs integrity pin; robots 403'),
    ('AQ-CCCM', 'CCCM (Adjustment of Jurisdiction) Rules 1978 and S.O. 4010/1986', 2, 8, 3, 3, 2, 3, 0, 'crosswalk 8 MISSING_EVIDENCE', 'AP-C9-01: PR #8 approval + logged download run (scope already authorised)'),
    ('AQ-AA-SRO120', 'Army Act commencement S.R.O. 120/1950', 3, 185, 3, 3, 3, 1, 0, 'upper bound 185 (0 direct); commencement affects every provision', 'PR #23 candidate ACQ03-019 (config + download approval)'),
    ('AQ-SANHITA-GAZ-EN', 'BNS/BNSS/BSA English Gazette texts', 2, 125, 1, 2, 1, 2, 0, 'BSA 64 + BNSS 49 + BNS 12 (Hindi Gazette text already held)', 'A-C5-1 + config PR (pins C5C-018..020)'),
    ('AQ-TRA2026-COMM', 'TRA 2026 commencement notification(s)', 2, 0, 3, 3, 3, 0, 0, '0 direct', 'discovery approval'),
    ('AQ-SRO34-1963', '1963 Part II-S4 issues (June-July) for S.R.O. 34', 1, 0, 3, 3, 2, 0, 0, '0 direct', 'discovery approval (AP-C9-05)'),
    ('AQ-ER-2008-CIRC', 'Entitlement Rules 2008 and PRA/ER amending circulars', 2, 5, 3, 3, 2, 1, 1, 'circulars 5', 'A-C5-2; robots 403'),
    ('AQ-RA-1987', 'Regulations for the Army 1987 complete', 2, 4, 2, 3, 1, 0, 2, 'crosswalk 4 MISSING_EVIDENCE', 'custodian (A-C5-3); access-marking handling'),
    ('AQ-AA-NOTIFS', 'Army Act notifications (s.4, s.9 active service etc.)', 2, 0, 3, 3, 2, 0, 0, '0 direct', 'discovery (phase 6)'),
    ('AQ-ISO', 'Inter-Services Organisations Act 2023 and Rules 2025', 2, 4, 3, 3, 1, 0, 0, 'crosswalk 4 MISSING_EVIDENCE', 'discovery'),
    ('AQ-AA-AMD-PR23', 'ALO 1956, Ordinance 3/1975, Act 20/1983', 1, 18, 3, 3, 2, 1, 0, 'ALO 18', 'PR #23 (config + download approval)'),
    ('AQ-AFT-PRAC-MAST', 'AFT Practice Rules 2009 Gazette masthead', 1, 43, 1, 2, 2, 1, 0, 'AFT rules 43 (shared)', 'PR #23 ACQ03-032'),
    ('AQ-DPP-2000', 'DPP Amendment Act 2000', 0, 0, 3, 3, 1, 0, 0, '0', 'P-C7-02-META then A-C5-1'),
]
ACQ_FIELDS = ['rank', 'acq_id', 'requirement', 'score', 'legal_consequence', 'dependent_records', 'dependent_records_level',
              'source_quality_gap', 'no_authoritative_alternative', 'amendment_commencement_significance', 'acquisition_readiness',
              'access_restriction_penalty', 'records_basis', 'route']


def dlevel(n):
    return 3 if n >= 100 else 2 if n >= 25 else 1 if n >= 5 else 0


def build_acq():
    rows = []
    for (aid, req, L, D, Q, A, C, R, X, basis, route) in ACQ:
        dl = dlevel(D)
        score = 3 * L + 2 * dl + 2 * Q + A + 2 * C + R - X
        rows.append({'acq_id': aid, 'requirement': req, 'score': score, 'legal_consequence': L, 'dependent_records': D,
                     'dependent_records_level': dl, 'source_quality_gap': Q, 'no_authoritative_alternative': A,
                     'amendment_commencement_significance': C, 'acquisition_readiness': R, 'access_restriction_penalty': X,
                     'records_basis': basis, 'route': route})
    rows.sort(key=lambda r: (-r['score'], -r['legal_consequence'], -r['acquisition_readiness'], r['acq_id']))
    for i, r in enumerate(rows, 1):
        r['rank'] = i
    return rows


# ---------------------------------------------------------------- preservation owner actions
PRES_FIELDS = ['order', 'sha256', 'bytes', 'category', 'title', 'c5_source_ids', 'c5_copy_evidence_class', 'kb_exact_anchor_rows',
               'working_store_paths', 'owner_action', 'agent_authorisation']


def build_preservation(inv, missing):
    rows = []
    for m in missing:
        if m['kind'] != 'REGISTERED_COPY_BYTES_NOT_IN_CANONICAL_STORE':
            continue
        r = inv[m['sha256']]
        if r['presence'] != WS_ONLY:
            die(f'{m["sha256"][:8]} listed as missing from canonical store but presence {r["presence"]}')
        stat = r['category'] not in ('JUDICIAL',)
        rows.append((-(int(r['kb_exact_anchor_rows'] or 0)), 0 if stat else 1, r['title'], m['sha256'], r))
    rows.sort()
    out = []
    for i, (_, _, _, h, r) in enumerate(rows, 1):
        out.append({'order': i, 'sha256': h, 'bytes': r['bytes'], 'category': r['category'], 'title': r['title'],
                    'c5_source_ids': r['c5_source_ids'], 'c5_copy_evidence_class': r['c5_copy_evidence_class'],
                    'kb_exact_anchor_rows': r['kb_exact_anchor_rows'], 'working_store_paths': r['c5_working_store_paths'],
                    'owner_action': ('OWNER: (1) copy the working-store file before the scratchpad is cleared; (2) run sha256sum and confirm '
                                     f'{h}; (3) upload to the canonical HF dataset under a path the owner chooses (suggested legal_knowledge/source_library/c5/<sha256>.<ext>); '
                                     '(4) record an upload receipt with HF revision and read-back sha256; (5) commit the receipt to staging'),
                    'agent_authorisation': 'NONE: upload is not authorised to agents'})
    if len(out) != 48:
        die(f'expected 48 working-store-only registered copies, got {len(out)}')
    return out


# ---------------------------------------------------------------- driver
def csv_text(fields, rows):
    s = io.StringIO()
    w = csv.DictWriter(s, fieldnames=fields, lineterminator='\n', extrasaction='raise')
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return s.getvalue()


def build(repo):
    inv = sha_prefix_map(pinned_csv('UNIFIED_CORPUS_INVENTORY.csv'))
    missing = pinned_csv('MISSING_SOURCE_EVIDENCE.csv')
    pinned_csv('UNREGISTERED_HELD_SOURCES.csv')
    equiv = pinned_csv('COPY_EQUIVALENCE_REGISTER.csv')
    pinned_csv('SOURCE_IDENTITY_CONFLICTS.csv')
    lk = open(HF_LK_LISTING, 'rb').read()
    if hashlib.sha256(lk).hexdigest() != HF_LK_PIN:
        die('HF legal_knowledge listing pin mismatch')
    hf_paths = [l.split('\t')[-1] for l in lk.decode().splitlines() if l.strip()]
    mrows = [r for r in git_csv(repo, RAW_COMMIT, 'data/raw_manifest.csv') if r['sha256'] != 'sha256']
    master = git_csv(repo, REG_COMMIT, REG_DIR + 'source_master_register.csv')
    crosswalk = git_csv(repo, REG_COMMIT, REG_DIR + 'corpus_crosswalk.csv')
    head = git_bytes(repo, REG_COMMIT, LEDGER_HEAD).decode().split()
    ledger_version = int(head[0])
    c9graph = git_csv(repo, C9_COMMIT, C9_DIR + 'amendment_graph.csv')
    if len(c9graph) != 116:
        die(f'C9 graph has {len(c9graph)} edges, expected 116')
    texts = page_texts(repo, mrows)
    readings = verify_readings(repo, inv, mrows)
    status = build_status(inv, texts, hf_paths, ledger_version)
    reg = build_registration(inv, master, crosswalk, equiv)
    graph = build_graph(c9graph, inv, texts, hf_paths)
    esc = [dict(zip(ESC_FIELDS, e)) for e in ESC]
    acq = build_acq()
    pres = build_preservation(inv, missing)

    def cnt(rows, k):
        c = {}
        for r in rows:
            c[r[k]] = c.get(r[k], 0) + 1
        return dict(sorted(c.items()))
    counts = {
        'schema': 'c10-statutory-counts/1',
        'pins': {'raw_data': RAW_COMMIT, 'registers': REG_COMMIT, 'c9_statutory': C9_COMMIT, 'c10_outputs': C10_PINS,
                 'hf_legal_knowledge_listing': HF_LK_PIN, 'auth_ledger_version': ledger_version},
        'status_counts': cnt(status, 'c10_status'),
        'preservation_risk_rows': sum(1 for r in status if r['preservation_risk'] == 'PRESERVATION_RISK'),
        'graph_c9_counts': cnt(c9graph, 'status'), 'graph_c10_counts': cnt(graph, 'c10_status'),
        'graph_changes': cnt(graph, 'c10_change'),
        'changed_edges': [r['edge_id'] for r in graph if r['c10_change'] != 'UNCHANGED'],
        'registration_rows': cnt(reg, 'ap_c9_02_c10_change'), 'readings': len(readings),
        'preservation_actions': len(pres),
    }
    files = {
        'primary_source_status_c10.csv': csv_text(STATUS_FIELDS, status),
        'registration_proposals_c10.csv': csv_text(REG_FIELDS, reg),
        'amendment_graph_c10.csv': csv_text(list(c9graph[0].keys()) + ['c10_status', 'c10_change', 'c10_evidence'], graph),
        'escalation_matters_c10.csv': csv_text(ESC_FIELDS, esc),
        'acquisition_priority_c10.csv': csv_text(ACQ_FIELDS, acq),
        'preservation_owner_actions_c10.csv': csv_text(PRES_FIELDS, pres),
        'readings_c10.csv': csv_text(['reading_id', 'sha256', 'page', 'pages_in_file', 'method', 'reading', 'reader'], readings),
        'c10_statutory_counts.json': json.dumps(counts, indent=1, sort_keys=True, ensure_ascii=False) + '\n',
    }
    return files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', default='/home/user/c7')
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    try:
        files = build(a.repo)
    except BuildError as e:
        print('BUILD FAILED:', e, file=sys.stderr)
        return 2
    sums = ''.join(f'{hashlib.sha256(v.encode()).hexdigest()}  {k}\n' for k, v in sorted(files.items()))
    files['OUTPUT_SHA256SUMS'] = sums
    bad = 0
    for name, text in sorted(files.items()):
        p = os.path.join(OUTDIR, name)
        if a.check:
            cur = open(p, encoding='utf-8').read() if os.path.exists(p) else None
            if cur != text:
                print('DIFFERS:', name)
                bad += 1
        else:
            with open(p, 'w', encoding='utf-8', newline='') as f:
                f.write(text)
    if a.check:
        print('CHECK', 'FAILED' if bad else 'OK', f'({len(files)} files)')
        return 1 if bad else 0
    print(f'wrote {len(files)} files to {OUTDIR}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
