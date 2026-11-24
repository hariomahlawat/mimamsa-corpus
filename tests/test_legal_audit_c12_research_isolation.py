"""Capabilities with deferred P2 findings stay restricted to non-operational research (Cycle 12 closeout)."""
import csv
import json
import unittest
from pathlib import Path

C = Path(__file__).resolve().parents[1] / "legal_knowledge" / "audit_work" / "C12-CONSOLIDATION"
DEFERRED_P2 = {"C11-extraction F05", "C11-extraction F06", "C11-extraction F07", "C11-extraction F08", "WSG-R04"}


class ResearchIsolation(unittest.TestCase):
    def test_every_deferred_p2_is_mapped_to_a_restricted_capability(self):
        rows = list(csv.DictReader(open(C / "CAPABILITY_RESTRICTIONS.csv", encoding="utf-8")))
        mapped = {f for r in rows if r["restriction"] == "NON_OPERATIONAL_RESEARCH_ONLY"
                  for f in r["deferred_findings"].split(";") if f}
        self.assertEqual(mapped, DEFERRED_P2)
        for r in rows:
            self.assertTrue((C / r["artefact"]).is_file(), r["artefact"])

    def test_outcome_rows_remain_candidates(self):
        with open(C / "extractor_v3/outputs/OUTCOMES_V3.csv", encoding="utf-8") as f:
            bad = [r["judgment_id"] for r in csv.DictReader(f) if r["status"] != "AUTOMATED_CANDIDATE_NOT_VERIFIED"]
        self.assertEqual(bad, [])

    def test_holding_items_remain_candidates(self):
        n = 0
        with open(C / "holdings/outputs/HOLDINGS_C12.jsonl", encoding="utf-8") as f:
            for line in f:
                d = json.loads(line); n += 1
                self.assertEqual(d.get("status"), "AUTOMATED_CANDIDATE_NOT_VERIFIED")
                self.assertEqual(d.get("verification"), "NOT_VERIFIED_RATIO_NOT_DETERMINED")
        self.assertGreater(n, 0)

    def test_statutory_proposals_not_applied(self):
        rows = list(csv.DictReader(open(C / "statutory_citations/outputs/CORRECTION_PROPOSALS_C12.csv", encoding="utf-8")))
        self.assertTrue(rows)
        self.assertEqual({r["status"] for r in rows}, {"PROPOSED_NOT_APPLIED"})


if __name__ == "__main__":
    unittest.main()
