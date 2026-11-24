#!/usr/bin/env python3
"""C10 workstream D (corpus quality): citation coverage after the unified corpus reconciliation.

Deterministic and offline. Every input is pinned:
  * git objects read with `git cat-file` at fixed commits:
      REGISTER_COMMIT  staging 21e73b83: SOURCE-LIBRARY-C5 crosswalk, AUTH-LEDGER effective v0000 registers,
                       records_658 / cases_53 (read only), C8 CORPUS-QUALITY, PILOT-01, WS-A, WS-B, WS-C and
                       CALIBRATION-02 finding registers;
      C9_COMMIT        PR #41 head cfc52d57: C9 CORRECTIONS package and C9 STATUTORY instrument records;
      RAW_DATA_COMMIT  raw-data ad77758d: only to re-hash the GitHub copies named in the curated candidate tables.
  * a byte snapshot of the C10 reconciliation outputs copied into ../inputs/c10_outputs_snapshot/ and pinned by
    SHA-256 below (the live ../../outputs/ folder is compared for information only, because it may be regenerated).

Four dimensions are kept apart for every citation item and are never merged:
  A SOURCE_AVAILABILITY   where a copy of the cited source is held (HF / GitHub raw-data / ephemeral C5 working store).
                          Availability is not authentication and never upgrades a citation anchor.
  B SOURCE_AUTHENTICATION AUTH-LEDGER effective v0000 state. The C10 reconciliation authenticates nothing.
  C CITATION_RESOLUTION   EXACT_ANCHOR / PARTIAL_MATCH / MISSING_EVIDENCE exactly as in the baseline crosswalk.
  D LEGAL_APPLICABILITY   NOT_DETERMINED; existing flags are copied, never re-assessed.

Usage:
  python build_quality_c10.py --repo <git checkout with the pinned commits>          write ../outputs/
  python build_quality_c10.py --repo <git checkout> --check                         exit 1 if any output differs

The script stops (exit 2) if the Cycle 8/9 baseline (983 citation items: 42 / 652 / 289; 77 NO_CITATION rows;
658 KB records; all 42 exact anchors on C5-SRC-P0-ARMY-RULES-1954~C1) cannot be reproduced from the pinned inputs.
"""
import argparse, collections, csv, hashlib, io, json, os, re, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
SNAP = PKG / "inputs" / "c10_outputs_snapshot"
LIVE = PKG.parent.parent / "outputs"
OUT = PKG / "outputs"

REGISTER_COMMIT = "21e73b8348767d5f1524167fcec538e1aad6e732"
C9_COMMIT = "cfc52d5792796050dcae351afda5609f7db41a5f"      # PR #41 head
RAW_DATA_COMMIT = "ad77758d4569ba6aafa955cc7843d874489e10f7"
AW = "legal_knowledge/audit_work/"
LED = AW + "AUTH-LEDGER/effective/v0000/"
C9C = AW + "C9-LEGAL-EVIDENCE/CORRECTIONS/"
C9S = AW + "C9-LEGAL-EVIDENCE/STATUTORY/"

SNAP_PINS = {
    "UNIFIED_CORPUS_INVENTORY.csv": "91519458af20c6bd849ccb8ab72d4dd32057fa0382738fa240055fe8a5b22e91",
    "MISSING_SOURCE_EVIDENCE.csv": "3aa947cb076431d40d27d6bc3e0d285f6304c36980d6043e2e41520bfbb95b21",
    "UNREGISTERED_HELD_SOURCES.csv": "3f6be222e5cd48962819d0ba31572fee0a23cf321cbe23128db75e57d68977d6",
    "RECONCILIATION_MANIFEST.json": "df8598c8f99c426da098d896d8b7a6736908283cde210d15fed9df16e71328c6",
    "lk_declared_sidecars.tsv": "be154debd080243cf33417c36fa520e1fabbeebeb9e6d12942c7de3589e619d5",
}

PRES_SHORT = {"HF_AND_GITHUB_RAW_DATA": "HF+GH", "HF_ONLY": "HF_ONLY", "C5_WORKING_STORE_ONLY_NOT_IN_HF_OR_GITHUB": "WS_ONLY"}

# ---------------------------------------------------------------------------------------------------------------
# Curated table 1: C5 citation sources that have no registered copy -> C9 STATUTORY instrument ids. The held copies
# are then taken from C9 instrument_records.csv#held_copies (C9 read the pages); nothing is identified here.
SOURCE_TO_C9_INSTRUMENTS = {
    "C5-SRC-P1-AFT-PROC-RULES": ["I-AFT-PR-2008", "I-AFT-PR-AMD-2011", "I-AFT-PRAC-2009"],
    "C5-SRC-P1-BNS-2023": ["I-BNS-2023"],
    "C5-SRC-P0-SANHITA-COMMENCEMENT-2024": ["I-BNS-COMM-SO850E", "I-BNSS-COMM-SO848E", "I-BSA-COMM-SO849E"],
    "C5-SRC-P1-PRA-2008-PT1": ["I-PRA-2008-PT1"],
    "C5-SRC-P1-PRA-2008-PT2": ["I-PRA-2008-PT2"],
    "C5-SRC-P1-ER-GMO-2023": ["I-ER-2023", "I-GMO-2023"],
    "C5-SRC-P1-CCCM-ADJ-RULES": ["I-CCCM-1978", "I-CCCM-SO4010-1986"],
    "C5-SRC-P1-ISO-ACT-RULES": ["I-ISO-2023"],
    # C5-SRC-P0-ARMY-ORDERS-INSTRUCTIONS, C5-SRC-P0-RA-1987, C5-SRC-P1-DESW-FAQ-PIB: no C9 instrument record.
}
# C9 verification_status prefixes that mean "the instrument itself is held (unregistered corpus raw copy)".
C9_HELD_PREFIX = ("HELD_CORPUS_RAW_UNREGISTERED",)
# Held copies C9 lists that are not the cited instrument (related material only).
C9_RELATED_NOTE = {
    "I-ER-2023": "C9 verification_status NOT_HELD_COMPLETE: the held DESW letter (C5-SRC-P1-ER-2023-HELD-13MB) is incomplete",
    "I-CCCM-SO4010-1986": "C9: NOT_HELD; only the Rajya Sabha 'papers laid' record (C5-SRC-P2-RS-PAPERS-LAID-1987) is held",
    "I-BNS-2023": "India Code compilation (as on 06-10-2025), not the Gazette text named by the C5 source",
}
# Copies C9 lists under an instrument that are not that instrument (review WS-03). They are reported, never proposed.
C9_COPY_NOT_INSTRUMENT = {
    "d163e785bfb3783287a641fc81621a6f16583f3435227110e066eb9d12c9d4da":
        "Hindi text in Gazette pagination (40.9 MB, page image read by the C10 workstream reviewer); listed by C9 under "
        "I-BNS-2023 but not the India Code compilation; not proposed",
}
# Related registered C5 sources (separate source rows) that hold part of an unheld cited source.
RELATED_REGISTERED = {
    "C5-SRC-P0-RA-1987": ("C5-SRC-P0-RA-1987-CH5-INDIACODE", "India Code extract of Chapter V (paras 201-220) only"),
}

# Curated table 2: alternate renditions of judgments in the canonical store (third-party S3 mirror of the Supreme
# Court Reports, crawler parent_doc_id 'sci'; or Hugging Face legal_knowledge files). Identity basis = first-page
# caption extracted from the pinned raw-data blob (pdftotext, AI agent reading, not human-confirmed) compared with
# cases_53 case_number / decision_date. Different bytes and different pagination from any C5 copy: these are never
# page-equivalent and can never carry an existing exact anchor.
# key -> (sha256, match_level, caption_quote)
CASE_CANDIDATES = {
    "DCLR-SC-1982-001": [("ebb86d4b3308eb89e9dfa2ef1d78d93463f15157278fce2c86b047c915251238", "DATE_MATCH", "LT. COL. PRtTHI PAL SINGB. BED! ETC. v. UNION OF INDIA & OTHERS ... August 25, 1982 (SCR p.393)")],
    "DCLR-SC-2019-003": [("b35f7f9e73f850351ed2779f17c3f0b68044a472f3a0a14fc0e68a865e36422a", "CASE_NO_AND_DATE_MATCH", "[2019] 15 S.C.R. 662 (Civil Appeal No.7603 of 2019) SEPTEMBER 25, 2019")],
    "DCLR-SC-2021-005": [("937ee98804344d1e30a7ed2419811befb2ffaa88a54c4c3fdb912cf172b881e4", "CASE_NO_AND_DATE_MATCH", "[2021] 4 S.C.R. 633 (Writ Petition (Civil) No 1109 of 2020) MARCH 25, 2021")],
    "DCLR-SC-2019-006": [("14e2d11aa4b88fe0f0cb4387d8539218c42c31a3df126d88cb268cab0b42e6d5", "CASE_NO_AND_DATE_MATCH", "[2019] 9 S.C.R. 925 (Criminal Appeal No.210 of 2017) JULY 08, 2019")],
    "DCLR-SC-2026-007": [("da0304734666c3663e90753dbcfdac809fe01bf19b9b03f4fcae628590d0d195", "CASE_NO_AND_DATE_MATCH", "[2026] 2 S.C.R. 615 : 2026 INSC 149 (Civil Appeal No(s). 6820-6824 of 2018) 12 February 2026")],
    "DCLR-SC-2023-009": [("483b70cbbe272ccbd27ef9fa216289ce87daac77fd8f262085db743acada3976", "CASE_NO_AND_DATE_MATCH", "[2023] 3 S.C.R. 598 (Civil Appeal No. 447 of 2023) MARCH 21, 2023")],
    "DCLR-SC-2016-010": [("3a4ed1aba90b8e35922a314c9f25142ee0261b91eb833e6fc36bc148312a1bd3", "CASE_NO_MATCH_DATE_OCR_GARBLED", "[2016] 5 S.C.R. 473 (Civil Appeal No. 8360 of2010) JULYOS,2016")],
    "DCLR-SC-2020-011": [("1de6c12b474985bf5ec905f6e6446ad30b15148e9ea4c13a99da7d8cf420fd24", "CASE_NO_AND_DATE_MATCH", "[2020] 3 S.C.R. 833 (Civil Appeal Nos. 9367-9369 of 2011) FEBRUARY 17, 2020")],
    "DCLR-SC-1983-N01": [("20a78326fc77d61bdfe1803691dfcbd59999100e6f0602ffdf518913a52db29f", "DATE_MATCH", "R. VISWAN & OTHERS v. UNION OF INDIA & OTHERS ... May 6, 1983")],
    "DCLR-SC-1990-N02": [("239c4e386f0e201b21bcdb0fdb954a0aa4bbe54dcbc17bba43cfe4babae253b4", "DATE_MATCH_OCR", "S.N. MUKHERJEE v. UNION bi' iNbiA AUGUST 28. 199ti")],
    "DCLR-SC-1997-N04": [("08ddb8a23d645c58ff3d8ef04397c95b3233cb84fa427fd113a2f25b090f8109", "DATE_MATCH", "UNION OF INDIA AND OTHERS v. IC-14827 MAJOR A. HUSSAIN ... DECEMBER 8, 1997")],
    "DCLR-SC-2013-N05": [("1ae0783e59765e9350856d71cbfe890a71474d1405600305517a2381036f4bbf", "CASE_NO_AND_DATE_MATCH", "[2013) 16 S.C.R. 495 (CIVIL APPEAL NO. 891-t OF 2012) OCTOBER 18, 2013")],
    "DCLR-SC-2015-N06": [("86de3643e66ec27b0e6a2a8ee007935a161790b0054ff924506d4c81b495289d", "CASE_NO_AND_DATE_MATCH", "[2015] 4 S.C.R. 676 (Civil Appeal No .. 7400 of 2013) MARCH 11, 2015")],
    "DCLR-SC-2013-N08": [("a9ccc45cd8c45d4d20652fe29057151435c33d1a3231e3f043a8543aef83b7c1", "CASE_NO_AND_DATE_MATCH", "[2013] 8 S.C.R. 1119 (Civil Appeal No. 4949 of 2013) JULY 2, 2013")],
    "DCLR-SC-2015-N09": [("c1ecdaeebf16bd67d832d501e76bc7b369358900a54f76c13375bcd4645ed7ea", "CASE_NO_AND_DATE_MATCH", "[2015] 2 S.C.R. 183 (Civil Appeal No. 2904 of 2011) FEBRUARY13, 2015")],
    "DCLR-SC-2008-N10": [("f8a14181e47c69e645840ca0369992d0906f02a93a4ec03ba7103f3f552cb4da", "CASE_NO_AND_DATE_MATCH", "[2008] 12 S.C.R. 104 (Civil Appeal No. 5151-52 of 2008) AUGUST 13, 2008")],
    "DCLR-SC-2020-N11": [("9a2c4360e23bcd661fab580fc989645d174ff49bfa064f473dbe35b9af6de3b7", "CASE_NO_AND_DATE_MATCH", "[2020] 10 S.C.R. 433 (Civil Appeal No. 2182-87 of 2020) MARCH 17, 2020")],
    "DCLR-SC-2000-N14": [("9edf9d95a342e8d7c66aab0a7209f5a52ed2843d69ef2a9b7e202e5eaad7db58", "DATE_MATCH", "UNION OF INDIA AND ANR v. CHARANJIT S. GILL AND ORS ... APRIL 24, 2000")],
    "DCLR-SC-1999-N15": [("76ec35cd7ab232b5f1c7bf05dfc28f2cf6032b1cdbe583e3b5059c18ed727e22", "DATE_MATCH", "UNION OF INDIA v. HIMMAT SINGH CHAHAR ... MAY 12, 1999")],
    "DCLR-SC-1991-A02": [("2d33465ae5d25d914635ca2d9bb727503eb260632f673622435818e12a0bcd3d", "DATE_MATCH", "EX-HAVILDAR RAT AN SINGH v. UNION OF INDIA AND ORS. ... NOVEMBER 19, 1991")],
    "DCLR-SC-2019-A03": [("2f89730f3d0ae1c81a1a423f259136c4423dc8cd43d7bc75a2a2a3121eec6e38", "CASE_NO_AND_DATE_MATCH", "[2019] 18 S.C.R. 990 (Civil Appeal No. 10870 of 2018) DECEMBER 11, 2019")],
    "DCLR-SC-1975-A07": [("89fb3c41563267d939062289bcaa774936110b503f8f7977ce7234a89a636147", "DATE_MATCH", "OUS KUTILINGAL ACHUDAN NAIR ... November 20, 1975")],
    "DCLR-SC-2011-A09": [("fbd764fee7148c1585e310a706e51fd3964460e34104959f252db7816bf14feb", "CASE_NO_AND_DATE_MATCH", "[2011] 8 S.C.R. 258 (Civil Appeal No. 4281 of 2006) JULY 15, 2011")],
    "DCLR-SC-2016-A12": [("15e63a38f9ee48f6c71f6a6e609c4cd737638d12d6e4b4c7f3a1d18dc629fff7", "CASE_NO_MATCH_DATE_OCR_GARBLED", "[2016] 4 S.C.R. 909 (Writ Petition (Criminal) No.129Of2012) JULYOS,2016")],
    "DCLR-SC-1964-A11": [("88f84411abdb3028e974792fef51a224770c987a9aa5ff7bc5a58654304738fd", "HF_PATH_AND_SIDECAR_ONLY_BYTES_NOT_READ", "HF legal_knowledge/judgment_originals/sci/historical/v3.3/ram_sarup_1963.pdf; sidecar source https://api.sci.gov.in/jonew/judis/3387.pdf, tier official_sci_judis_pdf_case_title_verified; record cites [1964] 5 SCR 931 and has no date")],
    "DCLR-SC-2016-L04": [("cce64004ab57b9747a85482bfddc7a4ebf0d35c5e56a6547b51065754d766787", "HF_PATH_AND_SIDECAR_ONLY_BYTES_NOT_READ", "HF legal_knowledge/judgment_sources/third_party_court_document_copies/2016/mani_ram_bhaira_mirror_2016.pdf; sidecar source is a private website (CA-4409-OF-2011-EX-HAV-MANI-RAM-BHAIRA...), third-party copy")],
    "DCLR-SC-2015-L02": [("c2f51fac25017d104cf5040bfc4eeac88b9111f5ea1f514eddb11d81465741dc", "PARTY_NAME_ONLY (record has no date or case number)", "(2015] 6 S.C.R. 192 (Civil Appeal Nos. 4357-4358 of 2015) MAY 12, 2015")],
    "DCLR-SC-2015-L03": [("77919f00c20215f08db90327b55431559a291f171d001dcdfe789d04b150daf1", "PARTY_NAME_ONLY (record has no date or case number)", "[2015] 2 S.C.R. 524 (Civil Appeal No. 11208 of 2011) FEBRUARY 24, 2015")],
    "DCLR-SC-2011-L06": [("16dcc07543999d260f4cba1e4c9329e336346a7abab62b564265aa8b8394da2a", "CASE_NO_AND_DATE_MATCH", "[2011] 4 S.C.R. 136 (Civil Appeal No. 5591 of 2006) MARCH 31, 2011")],
    "DCLR-SC-1996-L07": [("05e9484593272fe057eef0c133d815b97998c42d12e09c4e012aab1dfbb86646", "PARTY_NAME_ONLY (record has no date or case number)", "OCTOBER 11, 1996 ... Civil Appeal No.13272 of 1996")],
    "DCLR-SC-2005-L08": [("f696a5541cd41d4712aeb94c86d993f364f76e37de7008507cc1c8597548716a", "PARTY_NAME_ONLY (record has no date or case number)", "OCTOBER 21, 2005 ... Civil Appeal No. 1646 of I999")],
    "DCLR-SC-2008-L09": [("c295f22913ef898ebc2c8815e2fb1c9c645d462a05619b9701da8a8ca1fd7bdf", "PARTY_NAME_ONLY (record has no date or case number)", "[2008) 4 S.C.R. 909 (Civil Appeal No. 1960 of 2008) MARCH 13, 2008")],
    "DCLR-SC-2007-L10": [("89eb15de4987dc7b46c2acf1c2c448d38528e066b3d2479146b2154f3df8676a", "PARTY_NAME_ONLY (record has no date or case number)", "UNION OF INDIA AND ORS. v. KESHAR SINGH ... APRIL 20, 2007")],
    "DCLR-SC-1997-L11": [("00a6512e374c880e113494dfc51e085bb91d0fc134a0aa2cb09daa739e278531", "DATE_MATCH", "NAGA PEOPLE'S MOVEMENT OF HUMAN RIGHTS ETC. v. UNION OF INDIA NOVEMBER 27, I997")],
    "DCLR-SC-1987-R01": [("35b9c948fe6254c66c1a416055cbbd34050fcf132abc7b66d537fe6f711586ee", "DATE_MATCH", "RANJIT THAKUR v. UNION OF INDIA AND ORS. OCTOBER 15, 1987")],
    "DCLR-SC-2003-R03": [("676f2df941964780e2460e94e4ad23f62e3d9008efd512ef999370def6da4f04", "DATE_MATCH", "UNION OF INDIA AND ORS. v. SHIVENDRA BIKARAM SINGH ... APRIL 24, 2003.")],
}
# Rejected title-search hits (kept so the search is auditable): different judgment on the caption.
CASE_CANDIDATES_REJECTED = {
    "DCLR-SC-1997-N07": ("f316d8f97ff4e1fe454917f207726f2b3f842f87bb82258850336a405c5ffdbf", "Chandra Kumar Chopra v UoI, Crl.A. 665/2002, 11-05-2012: not L Chandra Kumar (1997)"),
    "DCLR-SC-2008-L05": ("bae31191140c5df63b08bd2eaef1f602150a10249ba681c1c0cac8be3d21f626", "Parshotam Lal Dhingra v UoI (1957/1958): not S R Dhingra (2007)"),
    "DCLR-SC-2012-A05": ("d85dee19a7bb2d53bc2c6f831c630bf38b765d0028e3638c721034cd7f1e38a7", "Ravinder Kumar Dhariwal v UoI, C.A. 6924/2021: not UoI v Ravinder Kumar (C.A. 1837/2009)"),
    "DCLR-SC-2026-008": ("da0304734666c3663e90753dbcfdac809fe01bf19b9b03f4fcae628590d0d195", "the February 2026 main judgment, not the 12-10-2026 clarification order (no October 2026 Girish item in the inventory)"),
    "DCLR-SC-1988-R02": ("35b9c948fe6254c66c1a416055cbbd34050fcf132abc7b66d537fe6f711586ee", "the 15-10-1987 judgment, not the 1988 review order"),
}
# C5 judgment source -> cases_53 id (to reuse CASE_CANDIDATES for the source's alternate renditions).
SOURCE_TO_CASE = {
    "C5-SRC-J-SC-1982-PPS-BEDI": "DCLR-SC-1982-001", "C5-SRC-J-SC-2020-VIRENDRA": "DCLR-SC-2020-002",
    "C5-SRC-J-SC-2023-PARASHOTAM": "DCLR-SC-2023-009", "C5-SRC-J-SC-2020-ARJUN": "DCLR-SC-2020-N13",
    "C5-SRC-J-SC-2014-ANVAR": "DCLR-SC-2014-N12", "C5-SRC-J-SC-2022-JASBIR": "DCLR-SC-2022-004",
    "C5-SRC-J-SC-2013-DHARAMVIR": "DCLR-SC-2013-N08", "C5-SRC-J-SC-2015-RAJBIR": "DCLR-SC-2015-N09",
    "C5-SRC-J-SC-2026-GIRISH-FEB": "DCLR-SC-2026-007", "C5-SRC-J-SC-2026-MULLIKOTE": "DCLR-SC-2026-N16",
    "C5-SRC-J-SC-1987-RANJIT-THAKUR": "DCLR-SC-1987-R01", "C5-SRC-J-SC-1990-SN-MUKHERJEE": "DCLR-SC-1990-N02",
    "C5-SRC-J-SC-2005-NAVJOT": "DCLR-SC-2005-L01",
}
# Source-level candidate not tied to a cases_53 row.
EXTRA_SOURCE_CANDIDATES = {
    "C5-SRC-J-SC-2019-NS-YADAV": [("d031a88ddc1dd76df23ea1148d289e83d5a2026604d68977e44bffea4c236060", "CASE_NO_MATCH",
                                   "[2019] 13 S.C.R. 260 NO. 1466828M EX CFN NARSINGH YADAV v. UNION OF INDIA & ORS. (Civil Appeal No. 7672 Of 2019) OCTOBER 03, 2019; the C5 working copy 3c50cdb7 p.1 prints CIVIL APPEAL NO. 7672 OF 2019 and army number 14666828M")],
    "C5-SRC-J-SC-2019-PS-GILL": [("009ea86c80839b4670bd4189c067d9d9997402db1aa25721a906d6a997b51e72", "CASE_NO_AND_DATE_MATCH",
                                  "[2019] 17 S.C.R. 405 (Criminal Appeal No. 404 of 2013) NOVEMBER 27, 2019")],
}
# Keyword detection of C5 judgment sources in free-text finding rows (heuristic; reported as such).
NAME_TO_SOURCE = [
    (r"\bIsaac\b", "C5-SRC-J-SC-2026-ISAAC"), (r"\bGirish\b", "C5-SRC-J-SC-2026-GIRISH-FEB"),
    (r"\bMullikote\b", "C5-SRC-J-SC-2026-MULLIKOTE"), (r"\bParashotam\b", "C5-SRC-J-SC-2023-PARASHOTAM"),
    (r"\bDharamvir\b", "C5-SRC-J-SC-2013-DHARAMVIR"), (r"\bRajbir\b", "C5-SRC-J-SC-2015-RAJBIR"),
    (r"\bVirendra\b", "C5-SRC-J-SC-2020-VIRENDRA"), (r"\bJasbir\b", "C5-SRC-J-SC-2022-JASBIR"),
    (r"\bBedi\b", "C5-SRC-J-SC-1982-PPS-BEDI"), (r"\bAnvar\b", "C5-SRC-J-SC-2014-ANVAR"),
    (r"\bKhotkar\b|\bArjun Panditrao\b", "C5-SRC-J-SC-2020-ARJUN"), (r"\bP\.? ?S\.? Gill\b", "C5-SRC-J-SC-2019-PS-GILL"),
    (r"\bRanjit Thakur\b", "C5-SRC-J-SC-1987-RANJIT-THAKUR"), (r"\bS\.? ?N\.? Mukherjee\b", "C5-SRC-J-SC-1990-SN-MUKHERJEE"),
    (r"\bNavjot\b", "C5-SRC-J-SC-2005-NAVJOT"), (r"\bN\.? ?S\.? Yadav\b|\bNarsingh Yadav\b", "C5-SRC-J-SC-2019-NS-YADAV"),
    (r"S\.R\.O\.? ?484\b|27-11-1954|Gazette of 27-11-1954|\b103686\b", "C5-SRC-P0-ARMY-RULES-1954"),
]

# Pinned files that already record candidate copies; a candidate found in one of them is not new to the audit.
KNOWN_FILES = [
    (REGISTER_COMMIT, AW + "WS-B-JUDGMENTS/identity_resolution.csv"),
    (REGISTER_COMMIT, AW + "WS-B-JUDGMENTS/intake_manifest.csv"),
    (REGISTER_COMMIT, AW + "WS-B-JUDGMENTS/pending_acquisition_cycle3.csv"),
    (REGISTER_COMMIT, AW + "CALIBRATION-02/registers/acquisition_readiness/acquisition_readiness.csv"),
    (REGISTER_COMMIT, "legal_knowledge/verification_batches/v3.3/04_Final_P0_Source_Recovery_Receipt.md"),
    (C9_COMMIT, C9S + "instrument_records.csv"),
    (C9_COMMIT, C9C + "consolidated_finding_register.csv"),
]

# Open-finding registers at REGISTER_COMMIT (task 3). (path, id col, priority col, status col, open predicate)
FINDING_REGISTERS = [
    ("PILOT-01/registers/corrections_register.csv", "finding_id", "severity", "status", lambda r: r["status"] == "PROPOSAL_NOT_APPLIED"),
    ("C8-SOURCES/CORPUS-QUALITY/cross_reference_findings.csv", "finding_id", "priority", "status", lambda r: True),
    ("C8-SOURCES/CORPUS-QUALITY/correction_proposals.csv", "proposal_id", "priority", "status", lambda r: True),
    ("WS-B-JUDGMENTS/adverse_conflict_queue.csv", "item_id", "severity", "state", lambda r: r["state"] == "OPEN"),
    ("WS-B-JUDGMENTS/pending_acquisition_cycle3.csv", "queue_id", "priority", "approval_state", lambda r: True),
    ("WS-A-STATUTORY/gaps_register.csv", "gap_id", "severity", "state", lambda r: True),
    ("WS-C-MML/candidate_corrections.csv", "cc_id", "severity", "applied", lambda r: True),
    ("CALIBRATION-02/proposals/correction_proposals.csv", "proposal_id", "severity", "incorporation_state", lambda r: True),
]


# ---------------------------------------------------------------------------------------------------------------
class Git:
    def __init__(self, repo):
        self.repo = repo
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}

    def blob(self, commit, path):
        return subprocess.run(["git", "-c", "core.useReplaceRefs=false", "-C", self.repo, "cat-file", "blob", f"{commit}:{path}"],
                              capture_output=True, check=True, env=self.env).stdout

    def text(self, commit, path):
        return self.blob(commit, path).decode("utf-8-sig")

    def csv(self, commit, path):
        return list(csv.DictReader(io.StringIO(self.text(commit, path))))

    def jsonl(self, commit, path):
        return [json.loads(l) for l in self.text(commit, path).splitlines() if l.strip()]


def sha256b(b):
    return hashlib.sha256(b).hexdigest()


def csv_text(fields, rows):
    s = io.StringIO()
    w = csv.DictWriter(s, fieldnames=fields, lineterminator="\n", extrasaction="raise")
    w.writeheader()
    for r in rows:
        w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in fields})
    return s.getvalue()


def s12(sha):
    return sha[:12]


SHA64 = re.compile(r"\b[0-9a-f]{64}\b")
SHAPFX = re.compile(r"(?:sha256[:= ]+|sha |\b)([0-9a-f]{8,63})(?:\.\.\.|…|\b)")
SRCID = re.compile(r"C5-SRC-[A-Z0-9][A-Z0-9+\-]*[A-Z0-9]")
CASEID = re.compile(r"DCLR-SC-\d{4}-[A-Z]?\d{2,3}")


class Data:
    def __init__(self, repo):
        g = self.g = Git(repo)
        # ---- C10 snapshot (pinned)
        self.snap_check = {}
        for name, pin in SNAP_PINS.items():
            b = (SNAP / name).read_bytes()
            got = sha256b(b)
            if got != pin:
                sys.exit(f"STOP: snapshot input {name} sha256 {got} != pinned {pin}")
            live = LIVE / name
            if name == "lk_declared_sidecars.tsv":
                live = PKG.parent.parent / "inputs" / "hf_snapshot" / name
            self.snap_check[name] = ("LIVE_MATCHES_SNAPSHOT" if live.exists() and sha256b(live.read_bytes()) == pin
                                     else ("LIVE_DIFFERS_FROM_SNAPSHOT" if live.exists() else "LIVE_ABSENT"))
        self.inv = {r["sha256"]: r for r in csv.DictReader(open(SNAP / "UNIFIED_CORPUS_INVENTORY.csv", encoding="utf-8"))}
        self.inv_by_pfx = collections.defaultdict(list)
        for s in self.inv:
            for n in (8, 10, 12, 16):
                self.inv_by_pfx[s[:n]].append(s)
        self.mse = list(csv.DictReader(open(SNAP / "MISSING_SOURCE_EVIDENCE.csv", encoding="utf-8")))
        self.sidecars = list(csv.DictReader(open(SNAP / "lk_declared_sidecars.tsv", encoding="utf-8"), delimiter="\t"))
        # ---- staging registers
        R = REGISTER_COMMIT
        self.cw_c5 = g.blob(R, AW + "SOURCE-LIBRARY-C5/registers/corpus_crosswalk.csv")
        self.cw_led = g.blob(R, LED + "corpus_crosswalk.csv")
        self.cw = list(csv.DictReader(io.StringIO(self.cw_led.decode("utf-8-sig"))))
        self.copies = g.csv(R, LED + "source_copy_register.csv")
        self.master = {r["source_id"]: r for r in g.csv(R, LED + "source_master_register.csv")}
        self.master_rows_c5 = g.csv(R, AW + "SOURCE-LIBRARY-C5/registers/source_master_register.csv")
        self.copies_c5 = g.csv(R, AW + "SOURCE-LIBRARY-C5/registers/source_copy_register.csv")
        self.states = {r["source_id"]: r for r in g.csv(R, LED + "source_states.csv")}
        self.led_cov = json.loads(g.text(R, LED + "coverage_summary.json"))
        self.kb_bytes = g.blob(R, "legal_knowledge/curated_originals/knowledge_base/v0.9/records_658.jsonl")
        self.cases_bytes = g.blob(R, "legal_knowledge/curated_originals/case_law/v0.9/cases_53.jsonl")
        self.kb = {d["id"]: d for d in (json.loads(l) for l in self.kb_bytes.decode("utf-8").splitlines() if l.strip())}
        self.cases = {d["id"]: d for d in (json.loads(l) for l in self.cases_bytes.decode("utf-8").splitlines() if l.strip())}
        self.regs = {p: g.csv(R, AW + p) for p, *_ in FINDING_REGISTERS}
        # ---- C9 package (PR #41 head)
        self.cfr = g.csv(C9_COMMIT, C9C + "consolidated_finding_register.csv")
        self.cpv2 = g.csv(C9_COMMIT, C9C + "correction_proposals_v2.csv")
        self.rimp = g.csv(C9_COMMIT, C9C + "record_impact.csv")
        self.instr = {r["instrument_id"]: r for r in g.csv(C9_COMMIT, C9S + "instrument_records.csv")}
        # ---- derived maps
        self.copies_by_src = collections.defaultdict(list)
        for c in self.copies:
            self.copies_by_src[c["source_id"]].append(c)
        self.copy_by_id = {c["copy_id"]: c for c in self.copies}
        self.kbx = [r for r in self.cw if r["knowledge_base_record_id"]]
        self.csx = [r for r in self.cw if r["case_id"]]
        # texts that already record candidate copies (for the 'new to the audit?' check)
        self.known = {}
        for c, path in KNOWN_FILES:
            self.known["%s@%s" % (path, c[:8])] = g.text(c, path)

    def presence(self, sha):
        r = self.inv.get(sha)
        return r["presence"] if r else "NOT_IN_UNIFIED_INVENTORY"

    def resolve_prefix(self, p):
        hits = self.inv_by_pfx.get(p[:16] if len(p) >= 16 else (p[:12] if len(p) >= 12 else (p[:10] if len(p) >= 10 else p[:8])), [])
        hits = [h for h in hits if h.startswith(p)]
        return hits[0] if len(hits) == 1 else None


# ---------------------------------------------------------------------------------------------------------------
def baseline(d):
    kbx = d.kbx
    cites = [r for r in kbx if r["relationship_type"] == "CITES"]
    nocit = [r for r in kbx if r["relationship_type"] == "NO_CITATION"]
    st = collections.Counter(r["evidence_status"] for r in cites)
    anchors = collections.Counter(r["anchor_copy_id"] for r in cites if r["evidence_status"] == "EXACT_ANCHOR")
    res = dict(crosswalk_rows=len(d.cw), kb_rows=len(kbx), cites=len(cites), no_citation=len(nocit),
               exact=st["EXACT_ANCHOR"], partial=st["PARTIAL_MATCH"], missing=st["MISSING_EVIDENCE"],
               kb_records=len(set(r["knowledge_base_record_id"] for r in kbx)), kb_records_in_file=len(d.kb),
               cases=len(d.cases), anchors=dict(anchors),
               nocit_missing=sum(1 for r in nocit if r["evidence_status"] == "MISSING_EVIDENCE"),
               crosswalk_c5_equals_ledger=(d.cw_c5 == d.cw_led))
    expect = dict(cites=983, exact=42, partial=652, missing=289, no_citation=77, kb_records=658, kb_records_in_file=658, cases=53)
    bad = {k: (res[k], v) for k, v in expect.items() if res[k] != v}
    if anchors != {"C5-SRC-P0-ARMY-RULES-1954~C1": 42}:
        bad["anchors"] = (dict(anchors), {"C5-SRC-P0-ARMY-RULES-1954~C1": 42})
    if not res["crosswalk_c5_equals_ledger"]:
        bad["crosswalk_c5_equals_ledger"] = (False, True)
    led = d.led_cov["crosswalk_kb_items_by_status"]
    if (led["EXACT_ANCHOR"], led["PARTIAL_MATCH"], led["MISSING_EVIDENCE"]) != (42, 652, 366):
        bad["ledger_coverage_summary"] = (led, "42/652/366 (366 = 289 + 77 NO_CITATION)")
    if bad:
        sys.stderr.write("STOP: baseline not reproduced: %s\n" % json.dumps(bad, sort_keys=True))
        sys.exit(2)
    return res


# ---------------------------------------------------------------------------------------------------------------
def copy_desc(d, c):
    p = d.presence(c["sha256"])
    return "%s:%s:%s" % (c["copy_id"], s12(c["sha256"]), PRES_SHORT.get(p, p))


def candidates_for_source(d, sid):
    """Copies in the canonical store that are NOT registered copies of `sid` but bear on it."""
    out = []  # (sha, kind, basis)
    for iid in SOURCE_TO_C9_INSTRUMENTS.get(sid, []):
        ir = d.instr.get(iid)
        if not ir:
            continue
        shas = sorted(set(SHA64.findall(ir["held_copies"])))
        held = ir["verification_status"].startswith(C9_HELD_PREFIX)
        for s in shas:
            kind = "C9_INSTRUMENT_COPY_UNREGISTERED" if held else "C9_RELATED_MATERIAL_ONLY"
            note = C9_RELATED_NOTE.get(iid, "")
            if s in C9_COPY_NOT_INSTRUMENT:
                kind, note = "C9_LISTED_COPY_NOT_THE_INSTRUMENT", C9_COPY_NOT_INSTRUMENT[s]
            out.append((s, kind, "C9 instrument_records.csv#%s held_copies; verification_status '%s'%s" % (
                iid, ir["verification_status"][:90], ("; " + note) if note else "")))
    if sid in RELATED_REGISTERED:
        rsid, note = RELATED_REGISTERED[sid]
        for c in d.copies_by_src.get(rsid, []):
            out.append((c["sha256"], "RELATED_REGISTERED_SOURCE_PART_ONLY", "%s (%s): %s" % (rsid, c["copy_id"], note)))
    case = SOURCE_TO_CASE.get(sid)
    for s, lvl, cap in (CASE_CANDIDATES.get(case, []) if case else []) + EXTRA_SOURCE_CANDIDATES.get(sid, []):
        if any(c["sha256"] == s for c in d.copies_by_src.get(sid, [])):
            continue
        out.append((s, "ALTERNATE_RENDITION_CANDIDATE_" + lvl.split(" ")[0], "first-page caption: " + cap))
    return out


def cand_desc(d, cands):
    return "; ".join("%s:%s:%s" % (s12(s), PRES_SHORT.get(d.presence(s), d.presence(s)), k) for s, k, _ in cands)


def availability(d, sid):
    """C10 availability class for a cited source and evidence strings."""
    if sid == "NONE":
        return dict(c10="NOT_APPLICABLE_NO_CITATION", base="NOT_APPLICABLE_NO_CITATION", copies="", cands="", cand_basis="")
    if sid == "UNMAPPED":
        return dict(c10="SOURCE_NOT_IDENTIFIED", base="SOURCE_NOT_IDENTIFIED", copies="", cands="", cand_basis="")
    st = d.states[sid]["effective_holding_state"]
    base = "HELD_C5_REGISTER_STORE_NOT_DISTINGUISHED" if st.startswith("HELD") else "NOT_HELD_C5_REGISTER"
    cps = d.copies_by_src.get(sid, [])
    pres = [d.presence(c["sha256"]) for c in cps]
    cands = candidates_for_source(d, sid)
    if "HF_AND_GITHUB_RAW_DATA" in pres:
        c10 = "HELD_HF_AND_GITHUB"
    elif "HF_ONLY" in pres:
        c10 = "HELD_HF_ONLY_HF_BYTES_NOT_CHECKED"
    elif "C5_WORKING_STORE_ONLY_NOT_IN_HF_OR_GITHUB" in pres:
        c10 = "HELD_WORKING_STORE_ONLY_EPHEMERAL"
    elif cps:
        c10 = "HELD_COPY_NOT_IN_INVENTORY"
    else:
        kinds = [k for s, k, _ in cands if d.presence(s) != "NOT_IN_UNIFIED_INVENTORY"]
        if any(k == "C9_INSTRUMENT_COPY_UNREGISTERED" for k in kinds):
            canon = any(k == "C9_INSTRUMENT_COPY_UNREGISTERED" and d.presence(s) in ("HF_AND_GITHUB_RAW_DATA", "HF_ONLY")
                        for s, k, _ in cands)
            c10 = "NOT_REGISTERED_UNREGISTERED_COPY_IN_CANONICAL_STORE" if canon else "NOT_REGISTERED_UNREGISTERED_COPY_WORKING_STORE_ONLY"
        elif kinds:
            c10 = "NOT_HELD_RELATED_MATERIAL_ONLY_" + ("WORKING_STORE" if all(
                d.presence(s) == "C5_WORKING_STORE_ONLY_NOT_IN_HF_OR_GITHUB" for s, k, _ in cands) else "CANONICAL_STORE")
        else:
            c10 = "NOT_HELD_NO_COPY_IN_ANY_STORE"
    return dict(c10=c10, base=base, copies="; ".join(copy_desc(d, c) for c in cps), cands=cand_desc(d, cands),
                cand_basis=" | ".join("%s: %s" % (s12(s), b) for s, _, b in cands))


def record_flags(d):
    """Existing legal-applicability flags per KB record (copied, not assessed)."""
    c9 = collections.defaultdict(list)
    for r in d.rimp:
        if r["target_kind"] == "kb":
            c9[r["record_id"]].append("%s[%s;%s]" % (r["impact_type"], r["finding_refs"], r["proposal_refs"] or "-"))
    pilot = collections.defaultdict(list)
    for r in d.regs["PILOT-01/registers/corrections_register.csv"]:
        if r["status"] == "PROPOSAL_NOT_APPLIED" and r["severity"] in ("P0", "P1", "P2"):
            pilot[r["record_id"]].append("%s(%s)" % (r["finding_id"], r["severity"]))
    adverse = collections.defaultdict(list)
    for r in d.regs["WS-B-JUDGMENTS/adverse_conflict_queue.csv"]:
        if r["state"] == "OPEN":
            for k in re.split(r"[;,\s]+", r["affected_kb_ids"]):
                if k:
                    adverse[k].append("%s(%s)" % (r["item_id"], r["severity"]))
    xref = collections.defaultdict(list)
    for r in d.regs["C8-SOURCES/CORPUS-QUALITY/cross_reference_findings.csv"]:
        for k in re.findall(r"\b[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-\d{2,3}\b", r["records_or_register_keys"]):
            xref[k].append("%s(%s,%s)" % (r["finding_id"], r["priority"], r["status"]))
    return c9, pilot, adverse, xref


# ---------------------------------------------------------------------------------------------------------------
def task1(d):
    c9, pilot, adverse, xref = record_flags(d)
    rows = []
    avail_cache = {}
    for i, r in enumerate(d.cw, start=2):  # i = line number in the pinned crosswalk file (header = 1)
        if not r["knowledge_base_record_id"]:
            continue
        sid = r["source_id"]
        if sid not in avail_cache:
            avail_cache[sid] = availability(d, sid)
        a = avail_cache[sid]
        kb = d.kb.get(r["knowledge_base_record_id"], {})
        anchor = r["anchor_copy_id"]
        apres = ""
        if anchor:
            c = d.copy_by_id[anchor]
            apres = PRES_SHORT.get(d.presence(c["sha256"]), d.presence(c["sha256"]))
        m = d.master.get(sid, {})
        stt = d.states.get(sid, {})
        cls = sorted(set(c["copy_evidence_class"] for c in d.copies_by_src.get(sid, [])))
        rec = r["knowledge_base_record_id"]
        rows.append(dict(
            item_id="C10Q-CW-%04d" % i, crosswalk_line=i, knowledge_base_record_id=rec,
            item_kind="CITATION_ITEM" if r["relationship_type"] == "CITES" else "NO_CITATION_PLACEHOLDER",
            source_id=sid, provision_id=r["provision_id"],
            A_availability_baseline=a["base"], A_availability_c10=a["c10"],
            A_registered_copies=a["copies"], A_anchor_copy_id=anchor, A_anchor_copy_store=apres,
            A_unregistered_or_alternate_candidates=a["cands"], A_candidate_basis=a["cand_basis"],
            A_note=("availability is not authentication and does not change C" if sid not in ("NONE", "UNMAPPED") else ""),
            B_ledger_v0000_holding_state=stt.get("effective_holding_state", ""),
            B_ledger_copy_evidence_classes=";".join(cls),
            B_anchor_copy_effective_status=(d.copy_by_id[anchor]["copy_effective_status"] if anchor else ""),
            B_c10_authentication_change="NONE (C10 reconciliation authenticates nothing: authentication_state NOT_AUTHENTICATED_BY_THIS_RECONCILIATION)",
            C_resolution_baseline=r["evidence_status"], C_resolution_c10=r["evidence_status"],
            C_resolution_change="NONE (anchors are not upgraded on availability)",
            C_crosswalk_basis=r["basis"],
            D_legal_applicability="NOT_DETERMINED",
            D_kb_status=kb.get("status", ""), D_operational_clearance=kb.get("operational_clearance", ""),
            D_source_currency_status=m.get("currency_status", ""),
            D_c9_record_impact="; ".join(c9.get(rec, [])), D_pilot01_open_p0_p2="; ".join(pilot.get(rec, [])),
            D_wsb_adverse_open="; ".join(adverse.get(rec, [])), D_c8_xref_findings="; ".join(xref.get(rec, [])),
        ))
    return rows, avail_cache


def task1_cases(d):
    rows = []
    for i, r in enumerate(d.cw, start=2):
        if not r["case_id"]:
            continue
        cid = r["case_id"]
        sid = r["source_id"]
        a = availability(d, sid)
        cc = CASE_CANDIDATES.get(cid, [])
        cs = d.cases.get(cid, {})
        anchor = r["anchor_copy_id"]
        apres = PRES_SHORT.get(d.presence(d.copy_by_id[anchor]["sha256"]), "") if anchor else ""
        rej = CASE_CANDIDATES_REJECTED.get(cid)
        rows.append(dict(
            item_id="C10Q-CW-%04d" % i, crosswalk_line=i, case_id=cid, title=cs.get("title", ""), source_id=sid,
            A_availability_baseline=a["base"], A_availability_c10=a["c10"], A_registered_copies=a["copies"],
            A_anchor_copy_id=anchor, A_anchor_copy_store=apres,
            A_case_level_candidates="; ".join("%s:%s:%s" % (s12(s), PRES_SHORT.get(d.presence(s), d.presence(s)), lvl.split(" ")[0]) for s, lvl, _ in cc),
            A_candidate_caption=" | ".join("%s: %s" % (s12(s), cap) for s, _, cap in cc),
            A_rejected_title_hit=("%s: %s" % (s12(rej[0]), rej[1]) if rej else ""),
            B_ledger_v0000_holding_state=d.states.get(sid, {}).get("effective_holding_state", "") if sid not in ("UNMAPPED", "NONE") else "",
            C_resolution_baseline=r["evidence_status"], C_resolution_c10=r["evidence_status"],
            C_resolution_change="NONE (third-party SCR renditions are not official copies and cannot carry an anchor)",
            D_legal_applicability="NOT_DETERMINED", D_case_status=cs.get("case_status", ""),
            D_post_decision_treatment_status=cs.get("post_decision_treatment_status", ""),
        ))
    return rows


def summary(d, rows, crows, base):
    cites = [r for r in rows if r["item_kind"] == "CITATION_ITEM"]
    out = []

    def add(dim, metric, b, c, derivation):
        out.append(dict(dimension=dim, metric=metric, baseline=b, c10=c,
                        change=("n/a" if "n/a" in (str(b), str(c)) else ("NONE" if str(b) == str(c) else "CHANGED")), derivation=derivation))
    cw = "AUTH-LEDGER/effective/v0000/corpus_crosswalk.csv@21e73b83 (byte-identical to SOURCE-LIBRARY-C5/registers/corpus_crosswalk.csv)"
    add("BASELINE", "KB crosswalk rows", 1060, base["kb_rows"], cw + ": rows with knowledge_base_record_id")
    add("BASELINE", "citation items (relationship_type=CITES)", 983, base["cites"], cw)
    add("BASELINE", "NO_CITATION placeholder rows", 77, base["no_citation"], cw + " (all MISSING_EVIDENCE)")
    add("BASELINE", "KB records", 658, base["kb_records"], cw + "; records_658.jsonl has %d ids" % base["kb_records_in_file"])
    add("BASELINE", "case records", 53, base["cases"], "cases_53.jsonl@21e73b83")
    for k, lab in (("exact", "EXACT_ANCHOR"), ("partial", "PARTIAL_MATCH"), ("missing", "MISSING_EVIDENCE")):
        add("C_CITATION_RESOLUTION", "citation items " + lab, {"exact": 42, "partial": 652, "missing": 289}[k],
            sum(1 for r in cites if r["C_resolution_c10"] == lab), "C10 value = baseline value per item; no anchor upgraded")
    add("C_CITATION_RESOLUTION", "exact anchors on C5-SRC-P0-ARMY-RULES-1954~C1 (sha c5ef95a9)", 42,
        sum(1 for r in cites if r["A_anchor_copy_id"] == "C5-SRC-P0-ARMY-RULES-1954~C1"), "anchor_copy_id")
    # A availability
    bA = collections.Counter(r["A_availability_baseline"] for r in cites)
    cA = collections.Counter(r["A_availability_c10"] for r in cites)
    for k in sorted(bA):
        add("A_SOURCE_AVAILABILITY", "baseline class " + k, bA[k], "n/a", "ledger v0000 effective_holding_state (store not distinguished)")
    for k in sorted(cA):
        add("A_SOURCE_AVAILABILITY", "C10 class " + k, "n/a", cA[k], "copy SHA-256 -> UNIFIED_CORPUS_INVENTORY.csv#presence")
    for k, v in sorted(collections.Counter((r["A_availability_baseline"], r["A_availability_c10"]) for r in cites).items()):
        add("A_SOURCE_AVAILABILITY", "baseline %s -> C10 %s" % k, v, v, "same items re-classified by store; no item moved between held and not-held registers")
    for res in ("EXACT_ANCHOR", "PARTIAL_MATCH", "MISSING_EVIDENCE"):
        cc = collections.Counter(r["A_availability_c10"] for r in cites if r["C_resolution_c10"] == res)
        for k in sorted(cc):
            add("A_x_C", "%s items with C10 availability %s" % (res, k), "n/a", cc[k], "cross-tabulation")
    add("A_SOURCE_AVAILABILITY", "EXACT_ANCHOR items whose anchor copy is WS_ONLY", "n/a",
        sum(1 for r in cites if r["A_anchor_copy_store"] == "WS_ONLY"), "anchor copy sha -> inventory presence")
    # B authentication
    bB = collections.Counter(r["B_ledger_v0000_holding_state"] or "(no source: UNMAPPED)" for r in cites)
    for k in sorted(bB):
        add("B_SOURCE_AUTHENTICATION", "ledger v0000 holding state " + k, bB[k], bB[k], "AUTH-LEDGER effective v0000 source_states.csv; C10 changes none")
    add("B_SOURCE_AUTHENTICATION", "anchor copy effective status EFFECTIVE_PRIMARY_VERIFIED", 42,
        sum(1 for r in cites if r["B_anchor_copy_effective_status"] == "EFFECTIVE_PRIMARY_VERIFIED"), "ledger copy register")
    add("B_SOURCE_AUTHENTICATION", "inventory rows newly authenticated by C10", 0,
        sum(1 for v in d.inv.values() if v["authentication_state"] != "NOT_AUTHENTICATED_BY_THIS_RECONCILIATION"), "UNIFIED_CORPUS_INVENTORY.csv#authentication_state")
    # D legal applicability
    add("D_LEGAL_APPLICABILITY", "citation items NOT_DETERMINED", 983, sum(1 for r in cites if r["D_legal_applicability"] == "NOT_DETERMINED"), "not assessed in C10")
    for fld, lab in (("D_c9_record_impact", "record has C9 record_impact entry"), ("D_pilot01_open_p0_p2", "record has open PILOT-01 P0-P2 finding"),
                     ("D_wsb_adverse_open", "record has open WS-B adverse/conflict item"), ("D_c8_xref_findings", "record named in C8 cross_reference_findings")):
        n = sum(1 for r in cites if r[fld])
        add("D_LEGAL_APPLICABILITY", "citation items where " + lab, n, n, "existing flag copied")
    for k, v in sorted(collections.Counter(r["D_kb_status"] for r in cites).items()):
        add("D_LEGAL_APPLICABILITY", "citation items with KB status " + k, v, v, "records_658.jsonl#status (unchanged)")
    # cases
    for k, v in sorted(collections.Counter(r["C_resolution_c10"] for r in crows).items()):
        add("CASES", "case rows " + k, v, v, cw + " case rows")
    for k, v in sorted(collections.Counter(r["A_availability_c10"] for r in crows).items()):
        add("CASES", "case rows C10 availability " + k, "n/a", v, "")
    add("CASES", "case EXACT_ANCHOR rows with anchor copy WS_ONLY", "n/a", sum(1 for r in crows if r["A_anchor_copy_store"] == "WS_ONLY"), "")
    add("CASES", "case EXACT_ANCHOR rows with anchor copy HF_ONLY (HF bytes NOT_CHECKED)", "n/a", sum(1 for r in crows if r["A_anchor_copy_store"] == "HF_ONLY"), "")
    add("CASES", "MISSING_EVIDENCE case rows with a canonical-store SCR or HF candidate rendition", "n/a",
        sum(1 for r in crows if r["C_resolution_c10"] == "MISSING_EVIDENCE" and r["A_case_level_candidates"]), "CASE_CANDIDATES (curated, first-page caption)")
    return out


# ---------------------------------------------------------------------------------------------------------------
def task2(d, rows, crows):
    cites = [r for r in rows if r["item_kind"] == "CITATION_ITEM"]
    ws_copies = [c for c in d.copies if d.presence(c["sha256"]) == "C5_WORKING_STORE_ONLY_NOT_IN_HF_OR_GITHUB"]
    by_src = collections.defaultdict(list)
    for r in cites:
        by_src[r["source_id"]].append(r)
    recs_all = collections.defaultdict(list)
    for r in cites:
        recs_all[r["knowledge_base_record_id"]].append(r)
    out = []
    for c in sorted(ws_copies, key=lambda c: c["copy_id"]):
        sid = c["source_id"]
        items = by_src.get(sid, [])
        src_all_ws = all(d.presence(x["sha256"]) == "C5_WORKING_STORE_ONLY_NOT_IN_HF_OR_GITHUB" for x in d.copies_by_src[sid])
        ex = [r for r in items if r["A_anchor_copy_id"] == c["copy_id"]]
        recs = sorted(set(r["knowledge_base_record_id"] for r in items)) if src_all_ws else []
        excl = [k for k in recs if all(x["A_availability_c10"] == "HELD_WORKING_STORE_ONLY_EPHEMERAL" for x in recs_all[k])]
        case_rows = [r for r in crows if r["source_id"] == sid]
        case_ex = [r for r in case_rows if r["A_anchor_copy_id"] == c["copy_id"]]
        cands = [x for x in candidates_for_source(d, sid) if d.presence(x[0]) in ("HF_AND_GITHUB_RAW_DATA", "HF_ONLY")]
        ms = [m for m in d.mse if m["item"] == c["copy_id"]]
        out.append(dict(
            copy_id=c["copy_id"], source_id=sid, sha256=c["sha256"], copy_evidence_class=c["copy_evidence_class"],
            working_store_paths=d.inv[c["sha256"]]["c5_working_store_paths"],
            source_all_copies_ws_only="YES" if src_all_ws else "NO",
            kb_citation_items_at_risk=len(items) if src_all_ws else 0, kb_exact_anchors_on_this_copy=len(ex),
            kb_records_with_items_at_risk=len(recs), kb_records_exclusively_at_risk=len(excl),
            case_rows_at_risk=len(case_rows) if src_all_ws else 0, case_exact_anchors_on_this_copy=len(case_ex),
            canonical_store_alternate_candidates=cand_desc(d, cands),
            alternate_candidate_limits=("different bytes and pagination; not page-equivalent; cannot carry an existing anchor; identity by first-page caption only" if cands else "none found"),
            c10_missing_source_evidence_row=(ms[0]["action"] if ms else "")))
    # totals
    ws_srcs = sorted(set(r["source_id"] for r in cites if r["A_availability_c10"] == "HELD_WORKING_STORE_ONLY_EPHEMERAL"))
    at_risk = [r for r in cites if r["A_availability_c10"] == "HELD_WORKING_STORE_ONLY_EPHEMERAL"]
    recs = sorted(set(r["knowledge_base_record_id"] for r in at_risk))
    excl = [k for k in recs if all(x["A_availability_c10"] == "HELD_WORKING_STORE_ONLY_EPHEMERAL" for x in recs_all[k])]
    exact_recs = sorted(set(r["knowledge_base_record_id"] for r in cites if r["C_resolution_c10"] == "EXACT_ANCHOR"))
    mitig = [r for r in at_risk if r["A_unregistered_or_alternate_candidates"] and any(
        t in r["A_unregistered_or_alternate_candidates"] for t in (":HF+GH:ALTERNATE", ":HF_ONLY:ALTERNATE"))]
    totals = dict(
        ws_only_registered_copies=len(ws_copies), ws_only_sources_cited_by_kb=len(ws_srcs),
        kb_citation_items_on_ws_only_sources=len(at_risk),
        of_which_exact=sum(1 for r in at_risk if r["C_resolution_c10"] == "EXACT_ANCHOR"),
        of_which_partial=sum(1 for r in at_risk if r["C_resolution_c10"] == "PARTIAL_MATCH"),
        kb_records_with_ws_only_dependency=len(recs), kb_records_exclusively_ws_only=len(excl),
        kb_records_with_exact_anchor=len(exact_recs),
        kb_records_with_exact_anchor_all_on_ws_only=len([k for k in exact_recs if k in recs]),
        army_rules_1954_items=sum(1 for r in at_risk if r["source_id"] == "C5-SRC-P0-ARMY-RULES-1954"),
        judgment_items=sum(1 for r in at_risk if r["source_id"].startswith("C5-SRC-J-")),
        ws_only_items_with_canonical_alternate_rendition=len(mitig),
        case_exact_anchor_rows_ws_only=sum(1 for r in crows if r["A_anchor_copy_store"] == "WS_ONLY"),
        case_exact_anchor_rows_hf_only=sum(1 for r in crows if r["A_anchor_copy_store"] == "HF_ONLY"),
        case_rows_on_ws_only_sources=sum(1 for r in crows if r["A_availability_c10"] == "HELD_WORKING_STORE_ONLY_EPHEMERAL"),
    )
    return out, totals


# ---------------------------------------------------------------------------------------------------------------
def scan(d, text):
    shas = set(SHA64.findall(text))
    for m in SHAPFX.finditer(text):
        p = m.group(1)
        if len(p) >= 8 and not p.isdigit() and re.search(r"[a-f]", p):
            full = d.resolve_prefix(p)
            if full:
                shas.add(full)
    srcs = set(s for s in SRCID.findall(text))
    srcs = set(s for s in srcs if s in d.master or s.split("~")[0] in d.master)
    kw = set(sid for pat, sid in NAME_TO_SOURCE if re.search(pat, text))
    cases = set(CASEID.findall(text))
    return shas, srcs, kw, cases


def known_in(d, sha):
    return [k for k, t in sorted(d.known.items()) if sha[:8] in t]


def evidence_effect(d, text, subject_cases=(), subject_sources=()):
    shas, srcs, kw, cases = scan(d, text)
    flags, inv_rows = [], []
    for s in sorted(shas):
        p = d.presence(s)
        inv_rows.append("%s:%s" % (s, PRES_SHORT.get(p, p)))
    src_pres = []
    for sid in sorted(srcs | kw):
        for c in d.copies_by_src.get(sid, []):
            src_pres.append(d.presence(c["sha256"]))
            if c["sha256"] not in shas:
                inv_rows.append("%s:%s (copy %s via %s)" % (c["sha256"], PRES_SHORT.get(d.presence(c["sha256"]), ""), c["copy_id"],
                                                             "source id" if sid in srcs else "name keyword"))
    pres = [d.presence(s) for s in shas] + src_pres
    if "C5_WORKING_STORE_ONLY_NOT_IN_HF_OR_GITHUB" in pres:
        flags.append("EVIDENCE_COPY_WORKING_STORE_ONLY")
    if "HF_ONLY" in pres:
        flags.append("EVIDENCE_COPY_HF_ONLY_BYTES_NOT_CHECKED")
    if "HF_AND_GITHUB_RAW_DATA" in pres:
        flags.append("EVIDENCE_COPY_HF_AND_GITHUB")
    if "NOT_IN_UNIFIED_INVENTORY" in pres:
        flags.append("SHA_NOT_IN_INVENTORY (render/page image or derived file)")
    # candidates for not-held subjects
    cand_lines, notes = [], []
    newc = False
    for cid in sorted(set(subject_cases) | cases):
        cw = [r for r in d.csx if r["case_id"] == cid]
        if not cw or cw[0]["evidence_status"] != "MISSING_EVIDENCE":
            continue
        for s, lvl, cap in CASE_CANDIDATES.get(cid, []):
            already = s[:8] in text
            kn = known_in(d, s)
            cand_lines.append("%s->%s:%s:%s%s" % (cid, s12(s), PRES_SHORT.get(d.presence(s), d.presence(s)), lvl.split(" ")[0],
                                                  " (cited by this row)" if already else (" (recorded in %s)" % ", ".join(k.split("/")[-1] for k in kn) if kn else " (NOT recorded in pinned registers)")))
            newc = newc or (not already and not kn)
            known_only = not already and bool(kn)
            if known_only:
                flags.append("CANDIDATE_RECORDED_ELSEWHERE")
        rej = CASE_CANDIDATES_REJECTED.get(cid)
        if rej:
            notes.append("%s: rejected title hit %s (%s)" % (cid, s12(rej[0]), rej[1]))
    for sid in sorted(set(subject_sources) | srcs | kw):
        if d.copies_by_src.get(sid):
            continue
        for s, k, b in candidates_for_source(d, sid):
            if k != "C9_INSTRUMENT_COPY_UNREGISTERED":
                continue
            already = s[:8] in text
            kn = known_in(d, s)
            cand_lines.append("%s->%s:%s:%s%s" % (sid, s12(s), PRES_SHORT.get(d.presence(s), d.presence(s)), k,
                                                  " (cited by this row)" if already else (" (recorded in %s)" % ", ".join(k2.split("/")[-1] for k2 in kn) if kn else " (NOT recorded in pinned registers)")))
            newc = newc or (not already and not kn)
            if not already and kn:
                flags.append("CANDIDATE_RECORDED_ELSEWHERE")
    if cand_lines:
        flags.append("CANDIDATE_COPY_FOR_UNHELD_SUBJECT")
    flags = list(dict.fromkeys(flags))
    if newc:
        change = "CHANGED_CANDIDATE_COPY_NOT_PREVIOUSLY_RECORDED"
    elif "CANDIDATE_RECORDED_ELSEWHERE" in flags:
        change = "NO_CHANGE_CANDIDATE_ALREADY_RECORDED_ELSEWHERE_NOW_IN_CANONICAL_STORE"
    elif "EVIDENCE_COPY_WORKING_STORE_ONLY" in flags:
        change = "NO_CHANGE_PRESERVATION_RISK"
    elif "EVIDENCE_COPY_HF_ONLY_BYTES_NOT_CHECKED" in flags and "EVIDENCE_COPY_HF_AND_GITHUB" not in flags:
        change = "NO_CHANGE_HF_ONLY_BYTES_NOT_CHECKED"
    elif "EVIDENCE_COPY_HF_AND_GITHUB" in flags:
        change = "NO_CHANGE_AVAILABILITY_CONFIRMED_IN_CANONICAL_STORE"
    else:
        change = "NO_CHANGE_NO_HELD_DOCUMENT_IDENTIFIED"
    return dict(flags=";".join(flags), inv_rows=" | ".join(inv_rows), srcs=";".join(sorted(srcs)), kw=";".join(sorted(kw - srcs)),
                cases=";".join(sorted(cases)), cands=" | ".join(cand_lines), change=change, notes=" | ".join(notes))


def task3(d):
    rows = []
    for x in d.cfr:
        text = " ".join(x.values())
        e = evidence_effect(d, text)
        rows.append(dict(register="C9-LEGAL-EVIDENCE/CORRECTIONS/consolidated_finding_register.csv@cfc52d57", item_id=x["finding_id"],
                         item_kind="C9_FINDING", priority=x["priority_evidence_standard"], status_as_recorded=x["status"],
                         records_or_keys=x["records_or_register_keys"], disagreement_or_dispute=("%s; %s" % (x["novelty"], x["prior_priority_note"]) if re.search("disput|disagree", x["priority_evidence_standard"] + x["novelty"], re.I) else ""), **e))
    for x in d.cpv2:
        text = " ".join(x.values())
        e = evidence_effect(d, text)
        rows.append(dict(register="C9-LEGAL-EVIDENCE/CORRECTIONS/correction_proposals_v2.csv@cfc52d57", item_id=x["proposal_id"],
                         item_kind="C9_PROPOSAL", priority=x["priority_evidence_standard"], status_as_recorded=x["status"],
                         records_or_keys=x["record_id"], disagreement_or_dispute="", **e))
    for path, idc, pc, sc, op in FINDING_REGISTERS:
        for x in d.regs[path]:
            if x[pc] not in ("P0", "P1", "P2") or not op(x):
                continue
            text = " ".join(v for v in x.values() if v)
            subj_cases = [x["case53_id"]] if path.endswith("pending_acquisition_cycle3.csv") and x.get("case53_id") else []
            e = evidence_effect(d, text, subject_cases=subj_cases)
            keys = x.get("record_id") or x.get("records_or_register_keys") or x.get("affected_kb_ids") or x.get("case53_id") or x.get("affected_ids") or x.get("target_ids") or ""
            disp = ""
            for k in ("independent_review", "disagreements", "reviewers_marking_no_defect", "corroborated_by_reviewers"):
                if x.get(k) and re.search(r"disput|disagree|reject", x[k], re.I):
                    disp = "%s: %s" % (k, x[k][:200])
            rows.append(dict(register=path + "@21e73b83", item_id=x[idc], item_kind="OPEN_REGISTER_ITEM", priority=x[pc],
                             status_as_recorded=x.get(sc, ""), records_or_keys=keys[:300], disagreement_or_dispute=disp, **e))
    return rows


# ---------------------------------------------------------------------------------------------------------------
def task3_proposals(d):
    """Versioned correction proposals (PROPOSAL_NOT_APPLIED) supported by an actual held document."""
    out = []
    mpath = AW + "SOURCE-LIBRARY-C5/registers/source_master_register.csv@21e73b83 (effective via AUTH-LEDGER v0000; change only by a ledger transition)"
    cpath = AW + "SOURCE-LIBRARY-C5/registers/source_copy_register.csv@21e73b83 (effective via AUTH-LEDGER v0000; change only by a ledger transition)"
    master = {r["source_id"]: r for r in d.master_rows_c5}
    n = 0

    def nid():
        nonlocal n
        n += 1
        return "C10-QP-%02d" % n

    # (1) cited, not-held sources with C9-identified unregistered instrument copies in the canonical store
    for sid in sorted(SOURCE_TO_C9_INSTRUMENTS):
        cands = [(s, k, b) for s, k, b in candidates_for_source(d, sid) if k == "C9_INSTRUMENT_COPY_UNREGISTERED"
                 and d.presence(s) in ("HF_AND_GITHUB_RAW_DATA", "HF_ONLY")]
        if not cands:
            continue
        m = master[sid]
        items = sum(1 for r in d.kbx if r["source_id"] == sid and r["relationship_type"] == "CITES")
        quote = "holding_state=%s | evidence_stage=%s | discovery_state=%s | discovery_candidate_ids=%s | acquisition_state=%s" % (
            m["holding_state"], m["evidence_stage"], m["discovery_state"], m["discovery_candidate_ids"], m["acquisition_state"])
        if sid == "C5-SRC-P1-BNS-2023":
            change = ("Do not change this Gazette-text source (the Gazette is still not held). Register a separate compilation source "
                      "(pattern of C5-SRC-P0-BNSS-2023-INDIACODE / C5-SRC-P0-BSA-2023-INDIACODE) with candidate copy %s "
                      "(presence %s), and only after copy-identity, provenance and fidelity review consider re-pointing the %d crosswalk "
                      "items. The second India Code file d163e785 (same title, 40.9 MB) is a Hindi text in Gazette pagination and is not proposed." % (
                          cands[0][0], d.presence(cands[0][0]), items))
        else:
            change = ("Record the following unregistered copies as candidate copies of this source (copy_role per instrument; "
                      "copy_evidence_class to be assigned by AUTH-LEDGER review, not here): %s. Keep holding_state unchanged until the "
                      "ledger review records copy identity, provenance and fidelity; then re-assess the %d MISSING_EVIDENCE crosswalk items "
                      "by reading the cited provisions (availability alone does not resolve them)." % (
                          "; ".join("%s (%s)" % (s, PRES_SHORT[d.presence(s)]) for s, _, _ in cands), items))
        out.append(dict(proposal_id=nid(), overlay_version="C10-v1", supersedes="", target_kind="register", target_file=mpath,
                        record_id=sid, field="holding_state; discovery_candidate_ids (no overwrite: new versioned row via ledger transition)",
                        current_text_quote=quote, proposal_type="REGISTER_CANDIDATE_COPY (no holding-state change)",
                        proposed_change=change,
                        primary_evidence=" | ".join("inventory %s presence=%s gh=%s hf=%s; %s" % (
                            s, d.inv[s]["presence"], d.inv[s]["gh_byte_verification"], d.inv[s]["hf_byte_verification"], b) for s, _, b in cands),
                        affected_items="%d KB citation items (crosswalk source_id=%s)" % (items, sid),
                        conditions="AUTH-LEDGER copy review; HF bytes NOT_CHECKED (GitHub raw-data copy re-hashed by C10 reconciliation)",
                        reviewer_disagreement_kept="", status="PROPOSAL_NOT_APPLIED"))
    # (2) working-store-only judgment sources with a canonical-store alternate rendition
    copies_c5 = collections.defaultdict(list)
    for c in d.copies_c5:
        copies_c5[c["source_id"]].append(c)
    for sid in sorted(SOURCE_TO_CASE.keys() | EXTRA_SOURCE_CANDIDATES.keys()):
        cps = copies_c5.get(sid, [])
        if not cps or not all(d.presence(c["sha256"]) == "C5_WORKING_STORE_ONLY_NOT_IN_HF_OR_GITHUB" for c in cps):
            continue
        cands = [(s, k, b) for s, k, b in candidates_for_source(d, sid) if k.startswith("ALTERNATE_RENDITION")
                 and d.presence(s) == "HF_AND_GITHUB_RAW_DATA"]
        if not cands:
            continue
        quote = " || ".join("copy_id=%s | copy_role=%s | held_paths=%s | page_equivalent_to=%s | eligible_for_exact_anchor=%s" % (
            c["copy_id"], c["copy_role"], c["held_paths"], c["page_equivalent_to"], c["eligible_for_exact_anchor"]) for c in cps)
        items = sum(1 for r in d.kbx if r["source_id"] == sid)
        cases = sum(1 for r in d.csx if r["source_id"] == sid)
        s, k, b = cands[0]
        out.append(dict(proposal_id=nid(), overlay_version="C10-v1", supersedes="", target_kind="register", target_file=cpath,
                        record_id=sid, field="new copy row (append; existing rows unchanged)", current_text_quote=quote,
                        proposal_type="REGISTER_ALTERNATE_RENDITION_CANDIDATE (preservation fallback for text; not an anchor substitute)",
                        proposed_change=("Append a candidate copy row for %s (third-party Supreme Court Reports rendition held in HF and GitHub raw-data) "
                                         "with copy_role THIRD_PARTY_SCR_RENDITION_CANDIDATE, page_equivalent_to empty and eligible_for_exact_anchor NO. "
                                         "It does not replace the registered copy, which must still be preserved in the canonical store "
                                         "(see C10 MISSING_SOURCE_EVIDENCE.csv). PDF page pinpoints in the corpus refer to the registered copy and do not carry over." % s),
                        primary_evidence="inventory %s presence=%s gh=%s; %s; candidate already recorded in: %s" % (
                            s, d.inv[s]["presence"], d.inv[s]["gh_byte_verification"], b, ", ".join(known_in(d, s)) or "none of the pinned registers"),
                        affected_items="%d KB crosswalk rows; %d case rows" % (items, cases),
                        conditions="identity confirmed only from the first-page caption by an AI agent; human check required; provenance of the S3 mirror undocumented",
                        reviewer_disagreement_kept="", status="PROPOSAL_NOT_APPLIED"))
    # (3) WS-B acquisition queue rows recording 'none' where an HF-held copy exists
    pq = {r["case53_id"]: r for r in d.regs["WS-B-JUDGMENTS/pending_acquisition_cycle3.csv"] if r["case53_id"]}
    for cid in sorted(CASE_CANDIDATES):
        for s, lvl, cap in CASE_CANDIDATES[cid]:
            r = pq.get(cid)
            if not r or r["mirror_copy"].strip() != "none" or d.presence(s) not in ("HF_ONLY", "HF_AND_GITHUB_RAW_DATA"):
                continue
            out.append(dict(proposal_id=nid(), overlay_version="C10-v1", supersedes="", target_kind="register",
                            target_file=AW + "WS-B-JUDGMENTS/pending_acquisition_cycle3.csv@21e73b83",
                            record_id=r["queue_id"], field="mirror_copy (overlay note; register row not overwritten)",
                            current_text_quote="mirror_copy=%s | official_copy_held=%s | identity_status=%s | official_target=%s" % (
                                r["mirror_copy"], r["official_copy_held"], r["identity_status"], r["official_target"]),
                            proposal_type="ACQUISITION_QUEUE_CANDIDATE_NOTE",
                            proposed_change=("Replace 'reportedly ... on the HF dataset' by an overlay note: the C10 Hugging Face listing shows a file at %s "
                                             "whose SHA-256 %s is declared only by the HF sidecar (bytes NOT_CHECKED; no download in C10). Keep mirror_copy, "
                                             "official_copy_held=NO and the acquisition open until the bytes are downloaded, hashed and the caption is read." % (
                                                 d.inv[s]["hf_paths"], s)),
                            primary_evidence="inventory %s presence=%s hf=%s; %s" % (s, d.inv[s]["presence"], d.inv[s]["hf_byte_verification"], cap),
                            affected_items="case %s (crosswalk MISSING_EVIDENCE)" % cid,
                            conditions="HF bytes NOT_CHECKED (sidecar-declared hash only); identity unconfirmed",
                            reviewer_disagreement_kept="", status="PROPOSAL_NOT_APPLIED"))
    return out


# ---------------------------------------------------------------------------------------------------------------
def verify_candidates(d):
    """Re-hash every GitHub raw-data copy named in the curated tables; confirm HF-only ones are in the inventory."""
    seen = {}
    allc = [s for v in CASE_CANDIDATES.values() for s, _, _ in v] + [s for v in EXTRA_SOURCE_CANDIDATES.values() for s, _, _ in v]
    allc += [v[0] for v in CASE_CANDIDATES_REJECTED.values()]
    for sid in SOURCE_TO_C9_INSTRUMENTS:
        allc += [s for s, _, _ in candidates_for_source(d, sid)]
    for s in sorted(set(allc)):
        r = d.inv.get(s)
        if not r:
            seen[s] = "NOT_IN_INVENTORY"
            continue
        if r["gh_raw_data_paths"]:
            b = d.g.blob(RAW_DATA_COMMIT, r["gh_raw_data_paths"].split(";")[0])
            seen[s] = "GH_REHASHED_MATCH" if sha256b(b) == s else "GH_REHASH_MISMATCH"
        else:
            seen[s] = r["presence"] + ":" + r["hf_byte_verification"]
    bad = {k: v for k, v in seen.items() if v in ("NOT_IN_INVENTORY", "GH_REHASH_MISMATCH") and k in d.inv}
    if bad:
        sys.exit("STOP: candidate verification failed: %s" % bad)
    return seen


def build(repo):
    d = Data(repo)
    base = baseline(d)
    rows, _ = task1(d)
    crows = task1_cases(d)
    summ = summary(d, rows, crows, base)
    pres_rows, pres_tot = task2(d, rows, crows)
    frows = task3(d)
    props = task3_proposals(d)
    ver = verify_candidates(d)
    files = {}
    F1 = list(rows[0].keys())
    files["citation_coverage_c10.csv"] = csv_text(F1, rows)
    files["case_coverage_c10.csv"] = csv_text(list(crows[0].keys()), crows)
    files["coverage_summary_c10.csv"] = csv_text(["dimension", "metric", "baseline", "c10", "change", "derivation"], summ)
    files["preservation_risk_c10.csv"] = csv_text(list(pres_rows[0].keys()), pres_rows)
    FF = ["register", "item_id", "item_kind", "priority", "status_as_recorded", "records_or_keys", "change", "flags", "inv_rows",
          "srcs", "kw", "cases", "cands", "notes", "disagreement_or_dispute"]
    ren = {"change": "c10_evidence_status_change", "flags": "c10_evidence_flags", "inv_rows": "inventory_rows",
           "srcs": "c5_source_ids_in_row", "kw": "c5_sources_by_name_keyword", "cases": "case_ids_in_row", "cands": "candidate_copies", "notes": "c10_note"}
    files["finding_status_c10.csv"] = csv_text([ren.get(k, k) for k in FF], [{ren.get(k, k): r.get(k, "") for k in FF} for r in frows])
    files["proposals_c10.csv"] = csv_text(list(props[0].keys()), props)
    fcount = collections.Counter((r["item_kind"], r["change"]) for r in frows)
    manifest = dict(
        workstream="C10 D corpus quality", register_commit=REGISTER_COMMIT, c9_commit=C9_COMMIT, raw_data_commit=RAW_DATA_COMMIT,
        c10_snapshot_pins=SNAP_PINS, c10_live_outputs_vs_snapshot=d.snap_check,
        protected_originals_sha256=dict(records_658=sha256b(d.kb_bytes), cases_53=sha256b(d.cases_bytes)),
        baseline_reproduced=base, preservation_totals=pres_tot,
        finding_status_counts={"%s|%s" % k: v for k, v in sorted(fcount.items())},
        finding_rows_by_register=dict(sorted(collections.Counter(r["register"] for r in frows).items())),
        proposals=len(props), candidate_verification=ver,
        limits=["HF byte integrity NOT_CHECKED (C10 capture: no download)", "candidate identities read from first-page captions by an AI agent, not human-confirmed",
                "availability is not authentication; no anchor, holding state or legal status changed"])
    files["QUALITY_C10_MANIFEST.json"] = json.dumps(manifest, indent=1, sort_keys=True) + "\n"
    sums = "".join("%s  %s\n" % (sha256b(files[k].encode()), k) for k in sorted(files))
    files["OUTPUT_SHA256SUMS"] = sums
    return files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    files = build(a.repo)
    if a.check:
        bad = [k for k, v in files.items() if not (OUT / k).exists() or (OUT / k).read_text(encoding="utf-8") != v]
        if bad:
            print("CHECK FAILED: " + ", ".join(sorted(bad)))
            sys.exit(1)
        print("CHECK OK: %d files reproduce byte-for-byte" % len(files))
        return
    OUT.mkdir(parents=True, exist_ok=True)
    for k, v in files.items():
        (OUT / k).write_text(v, encoding="utf-8")
    print("wrote %d files to %s" % (len(files), OUT))


if __name__ == "__main__":
    main()
