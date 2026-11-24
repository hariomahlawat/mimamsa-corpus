"""Tests for the C12-F statutory-citation build (run: python -m pytest tests/ or python -m unittest)."""
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
                if rules & {"r22", "r23", "r177", "r182", "r184", "r193", "r194", "r25", "r13"}:
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


if __name__ == "__main__":
    unittest.main()
