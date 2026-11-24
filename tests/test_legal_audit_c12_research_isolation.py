"""Capabilities with deferred P2 findings stay restricted to non-operational research (Cycle 12 closeout)."""
import csv
import json
import unittest
from pathlib import Path

C = Path(__file__).resolve().parents[1] / "legal_knowledge" / "audit_work" / "C12-CONSOLIDATION"
DEFERRED_P2 = {"C11-extraction F05", "C11-extraction F06", "C11-extraction F07", "C11-extraction F08", "WSG-R04"}
SOURCE_ALIAS = {"fable_review_extraction_c11_findings.csv": "C11-extraction ", "review_wsg_forms_findings.csv": ""}


class ResearchIsolation(unittest.TestCase):
    def test_every_deferred_p2_is_mapped_to_a_restricted_capability(self):
        rows = list(csv.DictReader(open(C / "CAPABILITY_RESTRICTIONS.csv", encoding="utf-8")))
        mapped = {f for r in rows if r["restriction"] == "NON_OPERATIONAL_RESEARCH_ONLY"
                  for f in r["deferred_findings"].split(";") if f}
        self.assertEqual(mapped, DEFERRED_P2)
        for r in rows:
            self.assertTrue((C / r["artefact"]).is_file(), r["artefact"])

    def test_deferred_set_matches_findings_register(self):
        reg = csv.DictReader(open(C / "findings_consolidation/FINDINGS_CONSOLIDATED.csv", encoding="utf-8"))
        open_p2 = {SOURCE_ALIAS.get(r["source_file"].rsplit("/", 1)[-1], r["source_file"] + ":") + r["id"]
                   for r in reg if r["severity"] in ("P1", "P2") and r["current_status"] != "CLOSED_VERIFIED"}
        self.assertEqual(open_p2, DEFERRED_P2)

    def test_form_fields_not_legally_approved(self):
        rows = list(csv.DictReader(open(C / "forms_registry/outputs/FORM_FIELDS.csv", encoding="utf-8")))
        self.assertTrue(rows)
        self.assertEqual({r["verification_status"] for r in rows}, {"DISCOVERED_FROM_SOURCE_NOT_LEGALLY_APPROVED"})

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
