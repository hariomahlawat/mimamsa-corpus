"""C13-A9: Cycle 13 findings register and research-restriction assessment (records only).

Every finding of every Cycle 13 review is listed with its source review, severity, Cycle 13 status and the evidence
(commit or file) for that status. The five Cycle 12 deferred P2s are carried over. Statuses:
  CLOSED              fixed and confirmed by an independent reviewer or a coordinator spot-check, or informational
                      with no action;
  CLOSED_UNCONFIRMED  fixed by the author, with no independent or coordinator confirmation on record;
  OPEN                unresolved and still blocking or needing action now;
  DEFERRED            consciously carried to a later cycle or gate, with the reason;
  ACCEPTED_DEVIATION  accepted as is by a recorded disposition (process deviation, recorded exception, frozen record).

`--check` rebuilds and compares byte for byte. The build also verifies that each review file exists, that each finding
id occurs in its review file, that CSV severities match, and that every cited commit exists in git and every cited
file exists. Standard library plus git.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
PKG = REPO / "legal_knowledge/audit_work/C13-A9-CLOSEOUT"
AW = "legal_knowledge/audit_work"
STATUSES = ("CLOSED", "CLOSED_UNCONFIRMED", "OPEN", "DEFERRED", "ACCEPTED_DEVIATION")
VERIFICATIONS = ("INDEPENDENT_CONFIRMED", "COORDINATOR_SPOTCHECK", "AUTHOR_ONLY")

SRC = {
    "A0R": f"{AW}/C13-A0-EVAL/reviews/review_c13_a0_5e07e010_findings.csv",
    "A0C": f"{AW}/C13-A0-EVAL/reviews/confirmation_c13_a0_06340486.md",
    "A4R": f"{AW}/C13-A4-STATUTORY/reviews/review_c13_a4_5db80dfc_findings.csv",
    "A4C": f"{AW}/C13-A4-STATUTORY/reviews/confirmation_c13_a4_fa8715fa_findings.csv",
    "A5R": f"{AW}/C13-A5-GRAPH/reviews/findings_c13_a5_f915ac11.csv",
    "A6R": f"{AW}/C13-A6-FORMS/reviews/review_c13_a6_1b05490f_findings.csv",
    "A7R": f"{AW}/C13-A7-ACQUISITION/reviews/review_c13_a7_84e10767_findings.csv",
    "GOVR": f"{AW}/C13-GOV/reviews/review_c13_gov_dfce9140_findings.csv",
    "EVA1": f"{AW}/C13-EVAL/reviews/REVIEW_A1.md",
    "EVINT": f"{AW}/C13-EVAL/reviews/REVIEW_A2_A3_A5_INTEGRATION.md",
    "GA4": f"{AW}/C13-EVAL/REVIEW_GA4.md",
    "B0R": "docs/architecture/reviews/review_c13_b0_dc811848_findings.csv",
    "B0C1": "docs/architecture/reviews/confirmation_c13_b0_10ae5c04_findings.csv",
    "IMP": "docs/architecture/reviews/REVIEW_IMPORTER_E05_E06.md",
    "PR53": "docs/architecture/reviews/REVIEW_PR53_RECONCILIATION.md",
    "ASR": "docs/architecture/reviews/c13-assurance/README.md",
    "POC": "docs/architecture/poc/reviews/REVIEW_R2N01_POC.md",
    "C12F": f"{AW}/C12-CONSOLIDATION/findings_consolidation/FINDINGS_CONSOLIDATED.csv",
    "B1": "docs/architecture/b1/reviews/REVIEW_B1.md",
    "A0C2": f"{AW}/C13-A9-CLOSEOUT/reviews/confirmation2_c13_a0_f1d61f71.md",
    "A5C": f"{AW}/C13-A9-CLOSEOUT/reviews/confirmation_c13_a5_d09b7d91.md",
    "IMP3": "docs/architecture/reviews/REVIEW_IMPORTER_E05_E06_confirmation3.md",
    "A9R": f"{AW}/C13-A9-CLOSEOUT/reviews/REVIEW_A8_A9.md",
}
CONF = {  # confirmation / disposition records cited as evidence
    "A0C": f"{AW}/C13-A0-EVAL/reviews/confirmation_c13_a0_06340486.md",
    "A0P": f"{AW}/C13-A0-EVAL/PROTOCOL_C13.md",
    "A0X": f"{AW}/C13-A0-EVAL/EXPOSURE_REGISTER.md",
    "A4C": f"{AW}/C13-A4-STATUTORY/reviews/confirmation_c13_a4_fa8715fa.md",
    "A4RM": f"{AW}/C13-A4-STATUTORY/README.md",
    "A5RM": f"{AW}/C13-A5-GRAPH/README.md",
    "A5ER": f"{AW}/C13-A5-GRAPH/scnum/ERRATA_C13.md",
    "A6RM": f"{AW}/C13-A6-FORMS/README.md",
    "A7D": f"{AW}/C13-A7-ACQUISITION/DISPOSITIONS_C13.md",
    "GOVC": f"{AW}/C13-GOV/reviews/confirmation_c13_gov_1dcf2c0b.md",
    "B0D": "docs/architecture/reviews/disposition_c13_b0_dc811848.md",
    "B0C1": "docs/architecture/reviews/confirmation_c13_b0_10ae5c04.md",
    "B0C2": "docs/architecture/reviews/confirmation2_c13_b0_2e31d6c6.md",
    "RES": f"{AW}/C13-EVAL/eval/RESULTS_C13.md",
    "A2RM": f"{AW}/C13-A2-OUTCOME/README.md",
    "A3RM": f"{AW}/C13-A3-HOLDINGS/README.md",
    "A6R04": f"{AW}/C13-A6-FORMS/outputs/R04_FAMILY_STATUS.csv",
    "A6TEST": "tests/test_legal_audit_c13_forms_a6.py",
    "CI": ".github/workflows/crawler-security-ci.yml",
    "RR": f"{AW}/C12-CONSOLIDATION/RESEARCH_USE_RESTRICTIONS.md",
    "A0C2": f"{AW}/C13-A9-CLOSEOUT/reviews/confirmation2_c13_a0_f1d61f71.md",
    "A5C": f"{AW}/C13-A9-CLOSEOUT/reviews/confirmation_c13_a5_d09b7d91.md",
    "A6C": f"{AW}/C13-A9-CLOSEOUT/reviews/confirmation_c13_a6_839c33e3.md",
    "A7SEC": f"{AW}/C13-A9-CLOSEOUT/reviews/confirmation_c13_a7_security_4aa8edf4.md",
    "IMP3": "docs/architecture/reviews/REVIEW_IMPORTER_E05_E06_confirmation3.md",
    "A9R": f"{AW}/C13-A9-CLOSEOUT/reviews/REVIEW_A8_A9.md",
    "B1R": "docs/architecture/b1/reviews/REVIEW_B1.md",
    "CAP": f"{AW}/C12-CONSOLIDATION/CAPABILITY_RESTRICTIONS.csv",
}

C, CU, O, D, AD = STATUSES
IC, CS, AO = VERIFICATIONS


# Default verification basis per source: whose record states the recorded status.
DEFAULT_VER = {"A7R": "COORDINATOR_SPOTCHECK", "GA4": "AUTHOR_ONLY"}


def F(src, ids, sev, status, evidence, note="", ver=None):
    v = ver or DEFAULT_VER.get(src, "INDEPENDENT_CONFIRMED")
    return [(src, i, sev, status, evidence, note, v) for i in (ids if isinstance(ids, list) else [ids])]


def rng(prefix, a, b, width=2):
    return [f"{prefix}{i:0{width}d}" for i in range(a, b + 1)]


FINDINGS = []
# ---- A0 evaluation infrastructure
FINDINGS += F("A0R", rng("F", 1, 5), "P2", C, f"{CONF['A0C']} s.2-4 (P2: none open); protocol v1.1 {CONF['A0P']} s.9.1")
FINDINGS += F("A0R", rng("F", 6, 16), "P3", C, f"{CONF['A0C']} (author claims confirmed; P3 none new); {CONF['A0P']} s.9.1")
FINDINGS += F("A0C", "C01", "P1", C, f"{CONF['A0C2']} ('C01 CLOSED. GA0 ACCEPTED'); fix f1d61f71; merge b2f163ff; {CONF['A0X']}",
              "independent confirmation 2 by the GA0 reviewer (copied from the reviewer's scratch original; the committed A0 "
              "review copy is redacted and predates it); text stays in git history (not rewritten)")
FINDINGS += F("A0C2", ["L01", "L02"], "P3", D, f"{CONF['A0C2']} (new P3s; requested actions not done in C13)",
              "L01: leak-guard docstring/sensitivity (about 40-word quotes undetected); L02: scan every file the extractor "
              "branches add before each freeze. Carried to Cycle 14", ver="AUTHOR_ONLY")
FINDINGS += F("A0C2", "L03", "P3", C, f"{CONF['A0C2']} ('Requested action: none needed; note it in the register')",
              "membership oracle noted here as the reviewer asked; SAMPLE.csv already names the holdouts")
# ---- A1 OCR
FINDINGS += F("EVA1", ["A1-01", "A1-02"], "P1", C, f"{SRC['EVA1']} confirmation rounds 1-2 (final ACCEPT); commits c24da1ff, cc190fde")
FINDINGS += F("EVA1", ["A1-03", "A1-04", "A1-05", "A1-06"], "P2", C, f"{SRC['EVA1']} confirmation round 1; commit c24da1ff")
FINDINGS += F("EVA1", ["A1-07", "A1-08", "A1-09"], "P3", C, f"{SRC['EVA1']} confirmation rounds 1-2")
FINDINGS += F("EVA1", ["A1-10", "A1-11"], "P2", C, f"{SRC['EVA1']} confirmation round 2; commit 5bd0e3d5")
FINDINGS += F("EVA1", "A1-12", "P3", C, f"{SRC['EVA1']} confirmation round 2; commit 5bd0e3d5")
# ---- A2/A3/A5 pre-integration review
FINDINGS += F("EVINT", ["A5-01", "A5-02"], "P1", C, f"{SRC['EVINT']} s.4.5; commit a60f1079")
FINDINGS += F("EVINT", ["A2-01", "A2-02", "A2-03"], "P2", C, f"{SRC['EVINT']} s.4.5; commit 2a6c710e")
FINDINGS += F("EVINT", ["A3-01", "A3-02"], "P2", C, f"{SRC['EVINT']} s.4.5; commit 010aac1c", "A3-02 residual is N3")
FINDINGS += F("EVINT", "A5-03", "P2", C, f"{SRC['EVINT']} s.4.5; commit a60f1079")
FINDINGS += F("EVINT", "X-01", "P2", C, f"{SRC['EVINT']} s.4.5; coordinator decision D-HHOLD at commit 6ea94ec9",
              "reopens if the owner overrides D-HHOLD (OWNER_DECISIONS_C13.md OD-11)")
FINDINGS += F("EVINT", ["A2-04", "A2-05"], "P3", C, f"{SRC['EVINT']} s.4.5; commit 2a6c710e")
FINDINGS += F("EVINT", "A2-06", "P3", D, f"{SRC['EVINT']} s.4.5 ('deferred to next version'); frozen tools not edited",
              "A2/A3 hard-code the RM-001 sha instead of reading config/restricted_material.json; no current leak")
FINDINGS += F("EVINT", "A3-04", "P3", C, f"{SRC['EVINT']} (informational; verified, no action)")
FINDINGS += F("EVINT", "X-02", "P3", AD, "commits bf791e4b, af45a23a, 59abf9a7 (merge messages name A0 f1d61f71); b2f163ff",
              "A9-recorded deviation awaiting coordinator sign-off: the integration merge message b2f163ff does not name f1d61f71 "
              "(source s.4.5 says 'Open, coordinator items'); history is not rewritten; ancestry recorded here", ver="AUTHOR_ONLY")
FINDINGS += F("EVINT", "X-03", "P3", C, f"{CONF['A6TEST']} (Reproducible test skipUnless sources_available); {CONF['A9R']} F02 (verified resolved)",
              "source s.4.5 left it open as a coordinator item; resolution verified by the independent A8/A9 reviewer")
FINDINGS += F("EVINT", "X-04", "P3", C, f"{CONF['RES']} (in staging); {CONF['A9R']} F02 (verified resolved)",
              "source s.4.5 left it open as a coordinator item; resolution verified by the independent A8/A9 reviewer")
FINDINGS += F("EVINT", ["N1", "N2"], "P3", D, f"{SRC['EVINT']} s.4.6 (recommended follow-ups)",
              "A5 package/scnum --check not run in CI (skips without /home/user/c7); see RISK_REGISTER_C13 R13-12")
FINDINGS += F("EVINT", "N3", "P3", D, f"{SRC['EVINT']} s.4.6 ('carry the entry into the A0 register next cycle')")
FINDINGS += F("EVINT", "N4", "P3", C, f"{SRC['EVINT']} s.4.6 (informational, no action)")
# ---- GA4 evaluation review
_GA4N = ("applied by the evaluator (RESULTS_C13 s.10; C13-EVAL/eval/REVIEW_FIXES.json); the GA4 reviewer has not "
         "re-confirmed (no confirmation round exists)")
FINDINGS += F("GA4", "F1", "P1", CU, f"{CONF['RES']} s.10 (H-HOLD NOT SCORABLE; A3 descriptive only); {AW}/C13-EVAL/eval/REVIEW_FIXES.json", _GA4N)
FINDINGS += F("GA4", ["F2", "F3", "F4"], "P2", CU, f"{CONF['RES']} s.10; {AW}/C13-EVAL/eval/REVIEW_FIXES.json", _GA4N)
FINDINGS += F("GA4", ["F5", "F6", "F7", "F8", "F9"], "P3", CU, f"{CONF['RES']} s.10", _GA4N)
FINDINGS += F("GA4", "F10", "P3", D, f"{CONF['RES']} D-13; {SRC['GA4']} ('For the next protocol version')", ver="INDEPENDENT_CONFIRMED")
# ---- A4 statutory
FINDINGS += F("A4R", "R-01", "P1", C, f"{SRC['A4C']} (CLOSED_VERIFIED)")
FINDINGS += F("A4R", ["R-02", "R-03"], "P2", C, f"{SRC['A4C']} (CLOSED_VERIFIED)")
FINDINGS += F("A4R", ["R-04", "R-05", "R-06", "R-07", "R-08"], "P3", C, f"{SRC['A4C']} (CLOSED_VERIFIED)")
FINDINGS += F("A4R", ["R-09", "R-10", "R-11", "R-12", "R-13"], "INFO", C, f"{CONF['A4C']}; R-10 CLOSED_VERIFIED in {SRC['A4C']}")
FINDINGS += F("A4C", ["N-01", "N-02"], "P3", CU, f"{CONF['A4RM']} change log C13A4-v1.2",
              "author fix; not independently re-confirmed", ver="AUTHOR_ONLY")
FINDINGS += F("A4C", "N-03", "INFO", C, f"{CONF['A4C']} (reproduction passed)")
# ---- A5 graph
FINDINGS += F("A5R", ["F01", "F02", "F03", "F04"], "P2", C,
              f"{CONF['A5C']} (CLOSED); commits d09b7d91, fb8aac7f, b772206b",
              "F01: no displayable precision; blind GA4 relation_type precision 0.340")
FINDINGS += F("A5R", ["F05", "F06", "F08", "F09"], "P3", C, f"{CONF['A5C']} (CLOSED); commits b772206b, d09b7d91")
FINDINGS += F("A5R", "F07", "P3", C, f"{CONF['A5C']} (CLOSED, errata E2); {CONF['A5ER']}",
              "closed in wording: the reconfirmation is a presence check, not a completeness check")
FINDINGS += F("A5C", ["N1", "N3"], "P3", D, f"{CONF['A5C']} (new P3 notes)",
              "N1: proposition-type edges target judgment nodes (Track B must not present them as proposition-level); "
              "N3: voice gate misses some counsel statements. Extractor frozen; carried to the next version", ver="AUTHOR_ONLY")
FINDINGS += F("A5C", "N2", "P3", C, f"{CONF['A5C']} (observation: FOLLOWS concentrated in templates)",
              "informational; no action requested")
# ---- A6 forms
FINDINGS += F("A6R", "F01", "P2", C, f"{CONF['A6C']} (FIXED); {CONF['A6R04']}")
FINDINGS += F("A6R", ["F02", "F03", "F04", "F06"], "P3", C, f"{CONF['A6C']} (FIXED)")
FINDINGS += F("A6R", "F05", "P3", AD, f"{CONF['A6C']} (NOTED_ACCEPTED)",
              "embedded blanks not itemised retrospectively; optional itemisation in a later cycle")
FINDINGS += F("A6R", "F07", "INFO", O, f"{CONF['A6C']} (OPEN)",
              "human spot-check of the AI transcriptions before the Document Studio 3.3 legal gate; carried as A8-Q057")
FINDINGS += F("A6R", ["F08", "F09"], "INFO", C, f"{CONF['A6C']} (FIXED)")
FINDINGS += F("A6R", "F10", "INFO", C, f"{SRC['A6R']} (claims reproduced; no action)")
# ---- A7 acquisition
FINDINGS += F("A7R", "F01", "P1", C, f"{CONF['A7SEC']} (CONFIRMED); PR #51 merged at 9ed152af", ver="INDEPENDENT_CONFIRMED")
FINDINGS += F("A7R", "F02", "P2", C, f"{CONF['A7SEC']} (F02 closed); PR #51", ver="INDEPENDENT_CONFIRMED")
FINDINGS += F("A7R", "F03", "P2", C, f"{CONF['A7D']} (patch 0003 not integrated)", "adoption of 0003 is owner decision OD-09")
FINDINGS += F("A7R", "F04", "P2", AD, f"{CONF['A7D']} (accepted retroactively as a recorded process deviation)")
FINDINGS += F("A7R", "F05", "P3", AD, f"{CONF['A7D']} (recorded; must not recur)")
FINDINGS += F("A7R", "F06", "P2", O, f"{CONF['A7D']} (OPEN)", "20 redirect hosts unprobed; redirect_scopes not adopted")
FINDINGS += F("A7R", "F07", "P3", D, f"{CONF['A7D']} (precondition for adopting 0003)")
FINDINGS += F("A7R", "F08", "P3", AD, f"{CONF['A7D']} (recorded; DESW path pinning needed for any allow-list change)")
FINDINGS += F("A7R", "F09", "P3", AD, f"{CONF['A7D']} (accepted as benign); {CONF['A9R']} F04",
              "A9 addendum: the reviewer's actions (record the official egazette sha256 as pins; never use archive.org "
              "derivative files as byte pins; refer the Navy Act subject to A3) are DEFERRED to the next acquisition cycle, "
              "owner: coordinator; recording official sha256 pins is a precondition for any future pin list")
FINDINGS += F("A7R", "F10", "P3", D, f"{CONF['A7D']} (recorded; reviewer all-page scan found no marking)",
              "A9 addendum: extending the marking scanner to all pages and OCR'd image pages is DEFERRED to the next "
              "acquisition cycle, owner: coordinator")
FINDINGS += F("A7R", "F11", "P3", D, f"{CONF['A7D']} (recorded in the disposition only); {CONF['A9R']} F04",
              "A9 addendum: HF commit 9e3cf986 .gitattributes change (+44 LFS lines) is recorded here and in DISPOSITIONS; "
              "updating HF_COMMITS_C13.csv/HF_VERIFY_C13.csv is DEFERRED (frozen A7 records), owner: coordinator")
FINDINGS += F("A7R", "F12", "P3", D, f"{CONF['A7D']} (deferred to A9); A9 records it deferred",
              "11 legacy scripts/*.py not retired or routed through the allow-list (A9 brief: do not retire)")
FINDINGS += F("A7R", "F13", "P3", AD, f"{CONF['A7D']} (frozen C12 snapshot unchanged by design)")
FINDINGS += F("A7R", "F14", "P3", C, f"commit 2185a2c8; {CONF['CI']}; {CONF['A9R']} ('exactly what was asked')", ver="INDEPENDENT_CONFIRMED")
FINDINGS += F("A7R", "F15", "INFO", C, f"{SRC['A7R']} (claims verified by the reviewer; no action)",
              "absent from the DISPOSITIONS table; informational, recorded here", ver="INDEPENDENT_CONFIRMED")
FINDINGS += F("A7R", "F16", "P3", D, f"{CONF['A7D']} (deferred)", "log a from_header_sent flag per request; acquisition tool not changed in A9")
# ---- GOV
FINDINGS += F("GOVR", ["F01", "F02", "F03"], "P2", C, f"{CONF['GOVC']} (CLOSED)")
FINDINGS += F("GOVR", ["F04", "F05", "F06", "F07", "F08", "F09", "F10", "F11"], "P3", D,
              f"{CONF['GOVC']} ('Remaining P3 issues ... still open')", "not addressed in Cycle 13; carried to Cycle 14")
FINDINGS += F("GOVR", "F12", "P3", O, f"{CONF['GOVC']} (still open)",
              "a local scratch copy of a restricted derivative still exists outside the repository; needs coordinator deletion")
FINDINGS += F("GOVR", ["I01", "I02", "I03", "I04"], "INFO", C, f"{SRC['GOVR']} (informational)")
# ---- B0 architecture
FINDINGS += F("B0R", ["F01"] + rng("F", 3, 12), "P2", C, f"{SRC['B0C1']} (CLOSED); {CONF['B0D']}")
FINDINGS += F("B0R", "F02", "P2", C, f"{CONF['B0C2']} (F02 closed)")
FINDINGS += F("B0R", [f for f in rng("F", 13, 26) if f != "F21"], "P3", CU,
              f"{CONF['B0D']} (fixed); {CONF['B0C1']} ('P3s ... accepted as dispositioned')",
              "author fix; the confirmation accepted the dispositions without re-verifying each", ver="AUTHOR_ONLY")
FINDINGS += F("B0R", "F21", "P3", O, f"{CONF['B0D']} ('Recorded for owner decision', D-08)", "owner decision OD-14")
FINDINGS += F("B0R", ["I01", "I02", "I03", "I04"], "INFO", C, f"{SRC['B0R']} (informational)")
FINDINGS += F("B0C1", rng("C", 1, 9, 2), "P3", C, f"{CONF['B0C2']} (C01-C09 closed)")
# ---- importer / citation navigation
FINDINGS += F("IMP", [f"E{i}" for i in range(1, 9)], "P2", C, f"{SRC['IMP']} s.4.3; commit 4476892c")
FINDINGS += F("IMP", ["E9", "E10"], "P3", C, f"{SRC['IMP']} s.4.3; commit 4476892c")
FINDINGS += F("IMP", "N1", "P2", C, f"{CONF['IMP3']} ('N1: CLOSED'); commits 6927277d, fbf4dce7")
FINDINGS += F("IMP", "N2", "P2", C, f"{SRC['IMP']} s.5.2 (CLOSED); commit 6927277d")
FINDINGS += F("IMP", "N3", "P3", C, f"{SRC['IMP']} s.5.2")
FINDINGS += F("IMP", "N4", "P2", C, f"{CONF['IMP3']} ('N4: CLOSED'); commit fbf4dce7")
FINDINGS += F("IMP3", "N5", "P3", C, "commit 6793dec1; merge df75ae89 ('N5 P3 fixed at 6793dec1, coordinator spot-checked')",
              "filed in the third confirmation; fix spot-checked by the coordinator, not re-confirmed by the reviewer",
              ver="COORDINATOR_SPOTCHECK")
# ---- PR #53 reconciliation
FINDINGS += F("PR53", rng("F", 1, 4), "P2", C, f"{SRC['PR53']} s.5.2; commit bb22ebd3")
FINDINGS += F("PR53", rng("F", 5, 10), "P3", C, f"{SRC['PR53']} s.5.2; commit bb22ebd3")
FINDINGS += F("PR53", [f"C{i}" for i in range(1, 6)], "P3", C, f"commit 5f4b8071; {SRC['IMP']} s.1 ('C1-C5 ... All CLOSED')")
# ---- assurance (PR #54)
FINDINGS += F("ASR", "R2-N01", "P2", O, f"{SRC['ASR']} s.5; {SRC['POC']} s.10.8 (selected host BLOCKED)",
              "closable for hosted-Windows PoC scope only; selected-host acceptance needs owner hardware (OD-05)")
FINDINGS += F("ASR", ["ASR-E01", "ASR-E02"], "UNRATED", D, f"{SRC['ASR']} s.5", "evidence at B1/application gates (B1 IN_PROGRESS)")
FINDINGS += F("ASR", "ASR-E03", "UNRATED", O, f"{SRC['ASR']} s.5", "independent backup restoration under authorised custody; needs the second backup (OD-02)")
FINDINGS += F("ASR", "ASR-E04", "UNRATED", O, f"{SRC['ASR']} s.5; {CONF['RES']}", "no blind target met in C13; fresh datasets and human annotators needed (OD-12)")
FINDINGS += F("ASR", "ASR-E05", "UNRATED", C, f"{SRC['IMP']} (importer ASR-E05 ACCEPT); merge df75ae89")
FINDINGS += F("ASR", "ASR-E06", "UNRATED", C, f"{SRC['IMP']} (citation navigation ASR-E06; E8 closed); {CONF['B1R']} F01 and confirmation at 4fbe7c79",
              "design conflict closed in B0 (E8). The B1 held-copy implementation of ASR-E06 had an open P1 (B1 F01: "
              "ineligible originals served, earlier editions not withdrawn), CLOSED in the B1 confirmation at 4fbe7c79 "
              "(B1 not yet merged to staging)")
# ---- R2-N01 PoC implementation review
FINDINGS += F("POC", ["F01", "F02"], "P1", C, f"{SRC['POC']} s.10.5; commit edcea6c7", "F02 closed for hosted scope")
FINDINGS += F("POC", ["F03", "F04", "F05", "F06", "F08"], "P2", C, f"{SRC['POC']} s.10.5; commits edcea6c7, 8636237b")
FINDINGS += F("POC", "F07", "P2", O, f"{SRC['POC']} s.10.5 (OPEN: selected host)", "independent probes on the selected host")
FINDINGS += F("POC", ["F09", "F10", "F11", "F12", "F13"], "P3", C, f"{SRC['POC']} s.10.5")
FINDINGS += F("POC", "F14", "P3", AD, f"{SRC['POC']} s.10.5, s.10.8 (PARTIAL; recorded exception for hosted scope)")
FINDINGS += F("POC", [f"N{i}" for i in range(1, 6)], "P3", D, f"{SRC['POC']} s.10.6 ('carried into the selected-host plan')",
              "N5: service-mode F05 made deterministic at 8636237b; oracle-trace determinism not re-reviewed")

# ---- B1 prototype (review of claude/c13-b1 at fa72af91; confirmation at 4fbe7c79; B1 not yet in staging)
_B1 = f"{SRC['B1']} confirmation at 4fbe7c79"
FINDINGS += F("B1", "F01", "P1", C, f"{_B1} (CLOSED); fixes ae7d7da0")
FINDINGS += F("B1", ["F02", "F03", "F04", "F08"], "P2", C, f"{_B1} (CLOSED); fixes ae7d7da0")
FINDINGS += F("B1", "F05", "P2", C, f"{_B1} (CLOSED for the reported cases)", "related gap filed as F14 (open)")
FINDINGS += F("B1", "F06", "P2", C, f"{_B1} (CLOSED: display mitigation)",
              "mitigated in display only ('Judges (crawler; may be incomplete)'); the upstream metadata gap (crawler keeps "
              "only the first judge) is DEFERRED to Track A")
FINDINGS += F("B1", ["F07", "F09", "F12", "F13"], "P3", C, f"{_B1} (CLOSED)")
FINDINGS += F("B1", "F10", "P3", O, f"{_B1} ('Code CLOSED; policy OPEN (owner decision)')",
              "twin-withdrawal policy pending owner decision OD-21")
FINDINGS += F("B1", "F11", "P3", D, f"{_B1} ('Mostly CLOSED ... Open: no manual unlock procedure')",
              "no manual unlock procedure; deferred, owner decision OD-22")
_B1B = f"{SRC['B1']} second confirmation at f71957e5"
FINDINGS += F("B1", "F14", "P2", C, f"{_B1B} (CLOSED); Windows CI run 45719359168",
              "filed at 4fbe7c79; instrument-scope fallback no longer pins another instrument's provision")
FINDINGS += F("B1", ["F15", "F16"], "P3", C, f"{_B1B} (CLOSED)", "F15: judge: filter caveat; F16: restricted register required in production")
FINDINGS += F("B1", ["F17", "F18", "F19"], "P3", O, f"{_B1B} (residual P3s, non-blocking)",
              "F17: stale 'optional' register wording in B1_PROTOTYPE.md; F18: 'AA s.69' (Army Act) not recognised, "
              "instrument aliases (AA, AR, AFA) missing from scoping; F19: ambiguous-only queries return 0 results "
              "without a lexical fallback")
# ---- Independent review of this closeout (A8/A9); confirmation at f7dae727: ACCEPT
_A9C = f"{CONF['A9R']} confirmation at f7dae727"
FINDINGS += F("A9R", "F01", "P1", C, f"{_A9C} (CLOSED); fixes 3b250a73")
FINDINGS += F("A9R", "F02", "P2", C, f"{_A9C} (CLOSED); fixes 3b250a73")
FINDINGS += F("A9R", rng("F", 3, 9), "P3", C, f"{_A9C} (CLOSED)")
FINDINGS += F("A9R", "C-F01", "P3", CU, f"{_A9C} (new P3); B0 F13-F26 rows relabelled AUTHOR_ONLY in this register",
              "fixed after the confirmation; not re-confirmed", ver="AUTHOR_ONLY")

# ---- Cycle 12 deferred P2s carried into Cycle 13 (status in C13)
CARRY = [
    ("C12F", "C11-extraction F05", "P2", D,
     f"{CONF['A2RM']}; {CONF['RES']} s.1.2 (A2 Outcome V4 blind GA4: NOT_MET on all four targets)",
     "A2 V4 addressed the extent rule; blind H-OUT-C13: printed_disposal strict precision 0.898 [0.838, 0.941] and coverage "
     "0.833; substantive_result precision 0.882, coverage 0.760 (targets 0.95/0.85). Restriction stays.", IC),
    ("C12F", "C11-extraction F08", "P2", D,
     f"{CONF['A2RM']}; {CONF['RES']} s.1.2",
     "post-quote operative sentences: A2 V4 work, same blind result (NOT_MET). Restriction stays.", IC),
    ("C12F", "C11-extraction F06", "P2", D,
     f"{CONF['A3RM']}; {CONF['RES']} s.1.3 (H-HOLD NOT SCORABLE; descriptive only)",
     "A3 holdings redesign: H-HOLD-C13 not scorable (span F1 0.566 < 0.6); descriptive adjudicated precision 0.365 "
     "[0.241, 0.503], far below the 0.80 milestone. Re-annotation under an independent guideline needed. Restriction stays.", IC),
    ("C12F", "C11-extraction F07", "P2", D,
     f"{CONF['A3RM']}; {CONF['RES']} s.1.3",
     "origin labels (court voice): no independent measured origin-label precision in C13 (H-HOLD not scorable). Restriction stays.", IC),
    ("C12F", "WSG-R04", "P2", D,
     f"{CONF['A6R04']}; {CONF['A6C']}; {SRC['A6R']}",
     "21 of 22 families transcribed from official page images and recommended CLOSED_VERIFIED by independent review "
     "1b05490f (transcription fidelity only); IAFD-905 (FF-AR54-APPIII-P1D-CHAR) stays R04_STILL_DEFERRED (only para 9 "
     "held). Legal approval gate not met. Restriction stays.", IC),
]

RESTRICTIONS = [
    # capability, deferred findings, C13 evidence, reason not lifted
    ("judicial_outcome_extraction", "C11-extraction F05;C11-extraction F08",
     f"{CONF['RES']} s.1.2; {CONF['A2RM']}",
     "lift condition: fresh holdout >=95% strict precision and >=85% coverage per field, plus legal-adviser sign-off. "
     "Blind H-OUT-C13 (A2 V4): NOT_MET on all four targets (best: printed_disposal precision 0.898, coverage 0.833). "
     "No adviser appointed."),
    ("holdings_and_propositions", "C11-extraction F06",
     f"{CONF['RES']} s.1.3; {CONF['A3RM']}",
     "lift condition: re-measurement against two independent annotators plus adviser sign-off. H-HOLD-C13 not scorable "
     "(span F1 0.566 < 0.6; PD-01); descriptive precision 0.365; the coders were AI agents, not human annotators."),
    ("origin_labels_court_voice", "C11-extraction F07",
     f"{CONF['RES']} s.1.3",
     "lift condition: measured origin-label precision on an independent sample. None was measured in C13."),
    ("form_field_lists", "WSG-R04",
     f"{CONF['A6R04']}; {CONF['A6RM']}",
     "lift condition: transcription from official copies with reviewer confirmation, plus the legal approval gate "
     "(Document Studio 3.3). 21/22 families recommended closed on fidelity; IAFD-905 deferred; legal gate not met; human "
     "spot-check (A6 F07) open."),
    ("statutory_citation_promotions", "",
     f"{AW}/C13-A4-STATUTORY/README.md; {AW}/C13-A8-ADVISER/outputs/ADVISER_QUESTIONS_C13.csv",
     "lift condition: legal-adviser approval of each proposal. 67 promotion proposals (57 C12F + 10 C13) are in the A8 "
     "package, NOT LEGALLY REVIEWED; none approved."),
]

C12_CARRY_KEYS = {
    "C11-extraction F05": ("C11-JUDICIAL-QUALITY/review/fable_review_extraction_c11_findings.csv", "F05"),
    "C11-extraction F06": ("C11-JUDICIAL-QUALITY/review/fable_review_extraction_c11_findings.csv", "F06"),
    "C11-extraction F07": ("C11-JUDICIAL-QUALITY/review/fable_review_extraction_c11_findings.csv", "F07"),
    "C11-extraction F08": ("C11-JUDICIAL-QUALITY/review/fable_review_extraction_c11_findings.csv", "F08"),
    "WSG-R04": ("C12-CONSOLIDATION/reviews/review_wsg_forms_findings.csv", "WSG-R04"),
}
NOT_IN_REVIEW_FILE: set = set()
# Commits on claude/c13-b1 (not yet merged to staging); cited from REVIEW_B1.md, not required in this history.
B1_BRANCH_COMMITS = {"fa72af91", "4fbe7c79", "ae7d7da0", "f71957e5"}

F_COLS = ["finding_id", "workstream", "source_review", "review_finding_id", "severity", "status", "verification",
          "evidence", "note"]
R_COLS = ["capability", "c12_restriction", "deferred_findings", "c13_evidence", "c13_decision", "reason"]

WS = {"A0R": "A0", "A0C": "A0", "EVA1": "A1", "EVINT": "A2/A3/A5", "GA4": "C13-EVAL", "A4R": "A4", "A4C": "A4",
      "A5R": "A5", "A6R": "A6", "A7R": "A7", "GOVR": "GOV", "B0R": "B0", "B0C1": "B0", "IMP": "B0", "PR53": "B0",
      "ASR": "B0/B-PoC (PR #54)", "POC": "B-PoC", "C12F": "C12 carry-over", "B1": "B1", "A0C2": "A0", "A5C": "A5",
      "IMP3": "B0", "A9R": "A8/A9"}


def git_ok(sha):
    return subprocess.run(["git", "-C", str(REPO), "cat-file", "-e", f"{sha}^{{commit}}"],
                          capture_output=True).returncode == 0


def verify(rows_):
    errs = []
    texts = {k: (REPO / v).read_text(encoding="utf-8") for k, v in SRC.items()}
    csvsev = {}
    for k, v in SRC.items():
        if v.endswith(".csv") and k != "C12F":
            for r in csv.DictReader(io.StringIO(texts[k])):
                csvsev[(k, r["id"])] = r["severity"]
    for src, fid, sev, st, ev, note, ver in rows_:
        if st not in STATUSES:
            errs.append(f"{src} {fid}: status {st}")
        if ver not in VERIFICATIONS:
            errs.append(f"{src} {fid}: verification {ver}")
        if st == "CLOSED" and ver == "AUTHOR_ONLY":
            errs.append(f"{src} {fid}: CLOSED needs independent or coordinator confirmation (use CLOSED_UNCONFIRMED)")
        if st == "CLOSED_UNCONFIRMED" and ver != "AUTHOR_ONLY":
            errs.append(f"{src} {fid}: CLOSED_UNCONFIRMED must be AUTHOR_ONLY")
        if src == "C12F":
            want = C12_CARRY_KEYS[fid]
            ok = any(r["source_file"].endswith(want[0]) and r["id"] == want[1]
                     and r["current_status"].startswith("DEFERRED") and r["severity"] == "P2"
                     for r in csv.DictReader(io.StringIO(texts[src])))
            if not ok:
                errs.append(f"{fid}: not a deferred P2 in {SRC[src]}")
        elif (src, fid) in NOT_IN_REVIEW_FILE:
            pass
        elif not re.search(r"(?<![A-Za-z0-9-])" + re.escape(fid) + r"(?![0-9])", texts[src]):
            errs.append(f"{src} {fid}: id not found in {SRC[src]}")
        if (src, fid) in csvsev and src not in ("A4C", "B0C1") and csvsev[(src, fid)] != sev:
            errs.append(f"{src} {fid}: severity {sev} != CSV {csvsev[(src, fid)]}")
        for c in re.findall(r"\b([0-9a-f]{8})\b", ev):
            if c not in B1_BRANCH_COMMITS and not git_ok(c):
                errs.append(f"{src} {fid}: commit {c} not in git")
        for pth in re.findall(r"((?:legal_knowledge|docs|tests|\.github)/[^\s;,()']+)", ev):
            if not (REPO / pth).exists():
                errs.append(f"{src} {fid}: evidence file {pth} missing")
    keys = [(s, f) for s, f, *_ in rows_]
    if len(keys) != len(set(keys)):
        errs.append("duplicate finding rows")
    return errs


def build():
    all_rows = FINDINGS + CARRY
    errs = verify(all_rows)
    if errs:
        raise SystemExit("\n".join(errs))
    out = []
    for i, (src, fid, sev, st, ev, note, ver) in enumerate(all_rows, 1):
        out.append({"finding_id": f"C13-FR-{i:03d}", "workstream": WS[src], "source_review": SRC[src],
                    "review_finding_id": fid, "severity": sev, "status": st, "verification": ver,
                    "evidence": ev, "note": note})
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=F_COLS, lineterminator="\n")
    w.writeheader()
    w.writerows(out)
    rbuf = io.StringIO()
    w = csv.DictWriter(rbuf, fieldnames=R_COLS, lineterminator="\n")
    w.writeheader()
    cap = {r["capability"]: r for r in csv.DictReader(io.StringIO((REPO / CONF["CAP"]).read_text(encoding="utf-8")))}
    for c_, dfs, ev, why in RESTRICTIONS:
        w.writerow({"capability": c_, "c12_restriction": cap[c_]["restriction"], "deferred_findings": dfs,
                    "c13_evidence": ev, "c13_decision": "NOT_LIFTED_STILL_RESTRICTED", "reason": why})
    if set(cap) != {r[0] for r in RESTRICTIONS}:
        raise SystemExit("capability list differs from C12 CAPABILITY_RESTRICTIONS.csv")
    def cnt(rs, key):
        d = {}
        for r in rs:
            d[r[key]] = d.get(r[key], 0) + 1
        return dict(sorted(d.items()))
    c13 = [r for r in out if r["workstream"] != "C12 carry-over"]
    summary = {
        "findings_total": len(out),
        "cycle13_review_findings": len(c13),
        "c12_carry_over": len(out) - len(c13),
        "by_status_all": cnt(out, "status"),
        "by_status_cycle13_reviews": cnt(c13, "status"),
        "by_severity_cycle13_reviews": cnt(c13, "severity"),
        "by_verification_all": cnt(out, "verification"),
        "by_status_staging_integrated_reviews": cnt([r for r in c13 if r["workstream"] not in ("B1", "A8/A9")], "status"),
        "b1_review_by_status": cnt([r for r in out if r["workstream"] == "B1"], "status"),
        "a8_a9_review_by_status": cnt([r for r in out if r["workstream"] == "A8/A9"], "status"),
        "open_p1": [r["finding_id"] for r in out if r["status"] == "OPEN" and r["severity"] == "P1"],
        "closed_unconfirmed_p1": [f"{r['finding_id']} ({r['workstream']} {r['review_finding_id']})" for r in out
                                  if r["status"] == "CLOSED_UNCONFIRMED" and r["severity"] == "P1"],
        "open_p2": [f"{r['finding_id']} ({r['workstream']} {r['review_finding_id']})" for r in out
                    if r["status"] == "OPEN" and r["severity"] == "P2"],
        "restrictions_lifted": 0,
        "restrictions_still_restricted": len(RESTRICTIONS),
        "sources": SRC,
    }
    return {"FINDINGS_REGISTER_C13.csv": buf.getvalue(), "RESEARCH_RESTRICTIONS_C13.csv": rbuf.getvalue(),
            "FINDINGS_SUMMARY_C13.json": json.dumps(summary, indent=1) + "\n"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    files = build()
    if a.check:
        bad = [n for n, t in files.items() if (PKG / n).read_text(encoding="utf-8") != t] if all(
            (PKG / n).exists() for n in files) else list(files)
        print("CHECK " + ("OK" if not bad else "FAILED: " + ", ".join(bad)))
        sys.exit(1 if bad else 0)
    for n, t in files.items():
        (PKG / n).write_text(t, encoding="utf-8")
    s = json.loads(files["FINDINGS_SUMMARY_C13.json"])
    print(json.dumps({k: s[k] for k in ("findings_total", "cycle13_review_findings", "by_status_all",
                                         "by_status_cycle13_reviews", "open_p1", "open_p2")}, indent=1))


if __name__ == "__main__":
    main()
