"""Tests for the C12-F statutory-citation build.

Run with the pinned interpreter (README "Running"): <venv>/bin/python -m pytest -q tests   (or -m unittest).
Requires Python >= 3.11 with PyMuPDF; the recorded outputs were produced with Python 3.13 / PyMuPDF (VersionBind in SUMMARY.json).
"""
import csv
import hashlib
import json
import sys
import unittest
from collections import Counter
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG / "tools"))
import build_c12f as b  # noqa: E402
import render_pages_c12 as rp  # noqa: E402

OUT = PKG / "outputs"


def rows(name):
    with open(OUT / name, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


class Build(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files = b.render()
        cls.matrix = list(csv.DictReader(cls.files["IMPROVEMENT_MATRIX.csv"].decode().splitlines()))
        cls.verif = {v["verification_id"]: v for v in csv.DictReader(cls.files["PRIORITY_VERIFICATION.csv"].decode().splitlines())}
        cls.summary = json.loads(cls.files["SUMMARY.json"])
        cls.copies = {r["copy_id"]: r for r in b.read_csv(b.INPUTS["c5_copy"])}

    def test_check_mode_reproduces_outputs(self):
        self.assertEqual(b.main(["--check"]), 0)

    def test_deterministic(self):
        again = b.render()
        self.assertEqual({k: hashlib.sha256(v).hexdigest() for k, v in again.items()},
                         {k: hashlib.sha256(v).hexdigest() for k, v in self.files.items()})

    def test_frozen_originals_unchanged(self):
        for rel, pin in b.FROZEN.items():
            self.assertEqual(b.sha256_file(b.REPO / rel), pin)
            self.assertEqual(self.summary["frozen_originals"][rel]["worktree"], "MATCH")

    def test_universe_and_baseline(self):
        self.assertEqual(len(self.matrix), 983)
        self.assertEqual(len({r["item_id"] for r in self.matrix}), 983)
        self.assertEqual(Counter(r["baseline_state"] for r in self.matrix),
                         Counter({"EXACT_ANCHOR": 42, "PARTIAL_MATCH": 652, "MISSING_EVIDENCE": 289}))
        self.assertEqual(self.summary["before"], {"EXACT_ANCHOR": 42, "MISSING_EVIDENCE": 289, "PARTIAL_MATCH": 652})
        self.assertEqual(dict(Counter(r["c12_state_proposed"] for r in self.matrix)), self.summary["after_proposed"])

    def test_missing_never_promoted(self):
        for r in self.matrix:
            if r["baseline_state"] == "MISSING_EVIDENCE":
                self.assertEqual(r["c12_state_proposed"], "MISSING_EVIDENCE", r["item_id"])

    def test_every_exact_has_registered_eligible_copy_and_page(self):
        for r in self.matrix:
            if r["c12_state_proposed"] != "EXACT_ANCHOR":
                continue
            vids = [v for v in r["verification_ids"].split(";") if v]
            self.assertTrue(vids, r["item_id"])
            for vid in vids:
                v = self.verif[vid]
                self.assertIn(v["status"], ("ESTABLISHED_EXACT_VERSION_ANCHOR", "ESTABLISHED_PARA_PAGE_ANCHOR"), (r["item_id"], vid))
                self.assertTrue(v["pdf_page"].strip(), (r["item_id"], vid))
                for cid in [c.strip() for c in v["source_copy_id"].split("+")]:
                    self.assertEqual(self.copies[cid]["eligible_for_exact_anchor"], "YES", (r["item_id"], cid))

    def test_reserved_and_gap_rules_not_promoted(self):
        for r in self.matrix:
            if r["source_id"] == b.ARMY_RULES_SRC and "#" in r["provision_id"]:
                rules = set(r["provision_id"].split("#")[1].split(","))
                if rules & {"r15", "r22", "r23", "r177", "r182", "r184", "r193", "r194", "r25", "r13"}:
                    self.assertEqual(r["c12_state_proposed"], "PARTIAL_MATCH" if r["baseline_state"] != "MISSING_EVIDENCE" else "MISSING_EVIDENCE", r["item_id"])

    def test_only_partial_to_exact_transitions(self):
        allowed = {"EXACT_ANCHOR->EXACT_ANCHOR", "PARTIAL_MATCH->PARTIAL_MATCH", "MISSING_EVIDENCE->MISSING_EVIDENCE",
                   "PARTIAL_MATCH->EXACT_ANCHOR", "EXACT_ANCHOR->PARTIAL_MATCH"}
        self.assertTrue(set(self.summary["transitions"]) <= allowed)

    def test_priority_clusters_verified(self):
        # every Army Rules item citing r.22, r.23 or r.180 has a page-level verification row for that rule
        for r in self.matrix:
            if r["source_id"] == b.ARMY_RULES_SRC and "#" in r["provision_id"]:
                rules = r["provision_id"].split("#")[1].split(",")
                vs = [self.verif[v] for v in r["verification_ids"].split(";") if v]
                for rr in {"r22", "r23", "r180"} & set(rules):
                    hit = [v for v in vs if v["provision"] == f"Army Rules 1954 r.{rr[1:]}"]
                    self.assertTrue(hit, (r["item_id"], rr))
                    self.assertEqual(hit[0]["printed_page"].split(";")[0], {"r22": "299", "r23": "300", "r180": "341"}[rr])

    def test_page_evidence_all_verified(self):
        self.assertTrue(all(v == "VERIFIED" for v in self.summary["page_evidence_validation"].values()))

    def test_parse_rules(self):
        self.assertEqual(b.parse_rules("rr.134,135,136"), ["r134", "r135", "r136"])
        self.assertEqual(b.parse_rules("r.1 (S.R.O. 17(E)/1993 itself)"), ["r1"])
        self.assertEqual(b.parse_rules("unknown (possibly r.22 Explanation per MML difference)"), ["r22"])
        self.assertEqual(b.parse_rules("Section 7 heading and rr.172-176"), ["r172", "r173", "r174", "r175", "r176"])
        self.assertEqual(b.parse_rules("Table below r.13 (col.3, cat. III(i)); App. I Form I"), ["r13"])

    def test_outputs_sha256sums(self):
        sums = dict(line.split("  ")[::-1] for line in self.files["OUTPUT_SHA256SUMS"].decode().splitlines())
        for n, h in sums.items():
            self.assertEqual(hashlib.sha256(self.files[n]).hexdigest(), h)

    def test_proposals_not_applied(self):
        props = list(csv.DictReader(self.files["CORRECTION_PROPOSALS_C12.csv"].decode().splitlines()))
        self.assertTrue(props)
        self.assertTrue(all(p["status"] == "PROPOSED_NOT_APPLIED" and p["version"] == b.VERSION for p in props))
        promos = [p for p in props if p["proposal_type"] == "EVIDENCE_STATE_PROMOTION"]
        self.assertEqual(len(promos), sum(1 for r in self.matrix if r["c12_change"] == "PROMOTE_PARTIAL_TO_EXACT_PROPOSED"))

    # ------------------------------------------------------------------ v1.1 remediation (review_wsf_statutory F-01..F-10)
    def _rules(self, r):
        return set(r["provision_id"].split("#")[1].split(",")) if r["source_id"] == b.ARMY_RULES_SRC and "#" in r["provision_id"] else set()

    def test_counts_after_remediation(self):
        self.assertEqual(self.summary["after_proposed"], {"EXACT_ANCHOR": 99, "MISSING_EVIDENCE": 289, "PARTIAL_MATCH": 595})

    def test_F01_r15_blocked_while_oq_a_10_open(self):
        """Fails if any r.15-dependent item is promoted while OQ-A-10 / GAP-15 is open in the WS-A registers."""
        oq = {r["question_id"]: r for r in b.read_csv(b.INPUTS["wsa_open_questions"])}
        gaps = {r["gap_id"]: r for r in b.read_csv(b.INPUTS["wsa_gaps"])}
        still_open = not b.CLOSED_STATE.search(oq["OQ-A-10"]["state"]) or not b.CLOSED_STATE.search(gaps["GAP-15"]["state"])
        self.assertTrue(still_open, "OQ-A-10/GAP-15 closed: revisit this test and the r.15 promotions deliberately")
        r15 = [r for r in self.matrix if "r15" in self._rules(r)]
        self.assertTrue(r15)
        for r in r15:
            self.assertNotEqual(r["c12_state_proposed"], "EXACT_ANCHOR", r["item_id"])
            self.assertIn("OQ-A-10", r["c12_blockers"], r["item_id"])
        for i in ("C10Q-CW-0031", "C10Q-CW-0363", "C10Q-CW-0369", "C10Q-CW-0395", "C10Q-CW-0402"):
            self.assertEqual(next(r for r in self.matrix if r["item_id"] == i)["c12_state_proposed"], "PARTIAL_MATCH", i)

    def test_F01_every_open_alleged_amendment_blocks_its_rule(self):
        oa = b.open_alleged_amendments(b.read_csv(b.INPUTS["wsa_open_questions"]) + b.read_csv(b.INPUTS["wsa_open_questions_c3"]),
                                       b.read_csv(b.INPUTS["wsa_gaps"]), b.read_csv(b.INPUTS["wsc_open_questions"]),
                                       b.read_csv(b.INPUTS["wsa_mml_xcheck"]))
        self.assertIn("r15", oa)
        self.assertEqual(set(oa), set(self.summary["open_alleged_amendment_blockers_F01"]))
        for r in self.matrix:
            hit = self._rules(r) & set(oa)
            if hit and r["baseline_state"] != "MISSING_EVIDENCE":
                self.assertEqual(r["c12_state_proposed"], "PARTIAL_MATCH", (r["item_id"], hit))

    def test_F01_named_rules_ignores_instrument_numbers(self):
        self.assertEqual(b.named_rules("inserted '[or Military Secretary]' in r.15 (MML 2 p.142 says S.R.O. 17(E)/1993)"), ["r15"])
        self.assertEqual(b.named_rules("do any touch r.23, r.193 or r.194?"), ["r23", "r193", "r194"])
        self.assertEqual(b.named_rules("Which instrument does 'Rule 4-12' in V7-T01 refer to"), [])

    def test_F02_annotation_locator_not_anchorable(self):
        r = next(r for r in self.matrix if r["item_id"] == "C10Q-CW-0087")
        self.assertEqual(r["c12_state_proposed"], "PARTIAL_MATCH")
        self.assertIn("annotation/note", r["c12_blockers"])
        for r in self.matrix:
            if "annotation/note" in r["c12_blockers"]:
                self.assertNotEqual(r["c12_state_proposed"], "EXACT_ANCHOR", r["item_id"])

    def test_F03_promoted_army_rules_pages_image_checked(self):
        pe = b.read_csv(b.INPUTS["page_evidence"])
        for r in self.matrix:
            if r["c12_change"] == "PROMOTE_PARTIAL_TO_EXACT_PROPOSED" and self._rules(r):
                for v in [self.verif[x] for x in r["verification_ids"].split(";") if x]:
                    self.assertIn("1954 page span IMAGE_CHECKED", v["page_evidence_method"], (r["item_id"], v["provision"]))
        for e in pe:
            if e["checker"] == "C12 WS-F remediation (AI)":
                self.assertEqual(e["render_script"], rp.SCRIPT_ID)
                self.assertEqual(e["render_dpi"], "110")
                self.assertTrue(e["render_png_sha256"] and e["observed_on_image"])

    def test_F08_render_hashes_reproduce(self):
        self.assertEqual(rp.verify(), 0)

    def test_F08_prior_check_references_exist(self):
        pe = {e["evidence_id"]: e for e in b.read_csv(b.INPUTS["page_evidence"])}
        self.assertNotIn("R23-VERIFY-01 PIC-13", pe["PE-1961-141-R14"]["observed_on_image"])
        self.assertIn("ACQ02_PIC-13", pe["PE-1961-141-R14"]["check_type"])
        acq02 = {r["check_id"] for r in b.read_csv("legal_knowledge/audit_work/ACQ-02/page_image_checks_acq02.csv")}
        chain = {r["check_id"] for r in b.read_csv("legal_knowledge/audit_work/ARMY-RULES-CHAIN-01/page_image_checks_chain.csv")}
        self.assertIn("PIC-13", acq02)
        self.assertTrue({"PIC-30", "PIC-31"} <= chain)
        self.assertIn("shall be omitted", pe["PE-1993-17-R134-136"]["observed_on_image"])

    def test_F04_exact_never_propagates_to_record(self):
        rank = {"MISSING_EVIDENCE": 0, "PARTIAL_MATCH": 1, "EXACT_ANCHOR": 2}
        by = {}
        for r in self.matrix:
            by.setdefault(r["kb_record_id"], []).append(r)
        for rid, rs in by.items():
            mn = min((r["c12_state_proposed"] for r in rs), key=rank.get)
            for r in rs:
                self.assertEqual(r["record_level_state"], mn, r["item_id"])
                if r["c12_state_proposed"] == "EXACT_ANCHOR" and mn != "EXACT_ANCHOR":
                    self.assertTrue(r["exact_scope"].startswith("CITATION_LOCATOR_ONLY"), r["item_id"])
        jl = self.summary["record_scope_F04"]["judgment_promotions_on_records_with_partial_statutory_content"]
        self.assertTrue({"KB-005", "COI-003", "HCE-003", "HCE-004", "HCE-008", "HCE-029", "KB-012"} <= set(jl))

    def test_F05_page_ranges(self):
        def first(rule):
            return next(self.verif[x] for r in self.matrix for x in r["verification_ids"].split(";") if x and self.verif[x]["provision"] == f"Army Rules 1954 r.{rule}")
        self.assertEqual(first("179")["printed_page"].split(";")[0], "340-341")
        self.assertIn("AR-006:141-142", first("14")["printed_page"])
        self.assertEqual(first("186")["printed_page"].split(";")[0], "342-343")
        self.assertIn("AR-029:14-15", first("26")["printed_page"])

    def test_F06_r15b_applicability_note(self):
        for r in self.matrix:
            for v in [self.verif[x] for x in r["verification_ids"].split(";") if x]:
                if v["provision"] in ("Army Rules 1954 r.14", "Army Rules 1954 r.15"):
                    self.assertIn("r.15B", v["applicability_note"])
                    self.assertIn("AR-034", v["applicability_note"])

    def test_F07_x002_excludes_hce027(self):
        xv = list(csv.DictReader(self.files["CROSS_VOLUME_ISSUES.csv"].decode().splitlines()))
        x002 = next(x for x in xv if x["issue_id"] == "C12F-X002")
        self.assertNotIn("HCE-027", x002["records"])
        self.assertEqual(sum(len(f.split(": ")[1].split(",")) for f in x002["records"].split("; ")), 7)

    def test_F09_r135_scope_note(self):
        props = list(csv.DictReader(self.files["CORRECTION_PROPOSALS_C12.csv"].decode().splitlines()))
        self.assertTrue(any(p["proposal_type"] == "VERSION_NOTE" and "r.135" in p["target"] and "legal adviser" in p["proposed_value"].lower() for p in props))

    def test_review_reconciliation(self):
        rr = self.summary["review_reconciliation"]
        self.assertEqual(rr["not_supported_still_promoted"], [])
        self.assertEqual(rr["supported_not_promoted"], [])
        self.assertEqual(len(rr["not_supported_withdrawn"]), 6)


if __name__ == "__main__":
    unittest.main()
