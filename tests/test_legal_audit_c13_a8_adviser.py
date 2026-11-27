"""C13-A8 legal-adviser package: schema, de-duplication, anchor resolution, RM-001 exclusion, reproducibility.

unittest only (CI has no pytest). Reads committed files only.
"""
import csv
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TOOLS = REPO / "legal_knowledge" / "audit_work" / "C13-A8-ADVISER" / "tools"
sys.path.insert(0, str(TOOLS))

import validate_adviser_c13 as V  # noqa: E402
from a8_registers import RM001_DOC, RM001_SHA, Registers  # noqa: E402


class A8Package(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.R = Registers()
        (_, cls.q), (_, cls.a), (_, cls.d) = V.load()

    def test_schema(self):
        self.assertEqual(V.check_schema(), [])

    def test_every_question_not_legally_reviewed_and_awaiting(self):
        for x in self.q:
            self.assertEqual(x["legal_review_status"], "NOT LEGALLY REVIEWED")
            self.assertEqual(x["adviser_answer_status"], "AWAITING_ADVISER")
            self.assertEqual(x["adviser_answer"], "")

    def test_priorities_are_three_tiers_with_one_p0(self):
        pri = {x["priority"] for x in self.q}
        self.assertEqual(pri, {"P0", "P1", "P2"})
        p0 = [x for x in self.q if x["priority"] == "P0"]
        self.assertEqual(len(p0), 1)
        self.assertIn("C12:AQ-STA-01", p0[0]["origin_ids"])

    def test_deduplication(self):
        self.assertEqual(V.check_dedup(), [])

    def test_known_duplicates_are_merged(self):
        by_origin = {f"{r['origin_workstream']}:{r['origin_id']}": r["question_id"] for r in self.d}
        self.assertEqual(by_origin["C12:AQ-STA-01"], by_origin["A4:A4-ADV-068"])
        self.assertEqual(by_origin["C12:AQ-STA-15"], by_origin["C12:AQ-STA-16"])
        self.assertEqual(by_origin["A4:A4-ADV-090"], by_origin["A4:A4-ADV-094"])
        self.assertEqual(by_origin["A5:GT-ba24ae19e50b1234"], by_origin["C12:AQ-HCW-01"])
        self.assertEqual(by_origin["A6:review_c13_a6_1b05490f/F07"], by_origin["C12:AQ-ROL-03"])

    def test_dedup_detects_a_planted_duplicate(self):
        orig = V.load

        def planted():
            (qc, q), (ac, a), (dc, d) = orig()
            dup = dict(q[-1], question_id=f"A8-Q{len(q) + 1:03d}")
            q2 = q + [dup]
            a2 = a + [dict(x, question_id=dup["question_id"]) for x in a if x["question_id"] == q[-1]["question_id"]]
            d2 = d + [dict(d[-1], origin_id=d[-1]["origin_id"], question_id=dup["question_id"])]
            return (qc, q2), (ac, a2), (dc, d2)
        V.load = planted
        try:
            errs = V.check_dedup()
        finally:
            V.load = orig
        self.assertTrue(any("duplicates" in e for e in errs), errs)
        self.assertTrue(any("more than one question" in e for e in errs), errs)

    def test_every_anchor_resolves_to_registered_file_and_hash(self):
        self.assertEqual(V.check_anchors(self.R), [])
        self.assertTrue(all(x["sha256"] and x["stored_path"] for x in self.a))

    def test_anchor_check_rejects_an_unregistered_hash(self):
        orig = V.load

        def tampered():
            (qc, q), (ac, a), (dc, d) = orig()
            a = [dict(x) for x in a]
            i = next(k for k, x in enumerate(a) if x["anchor_kind"] == "SOURCE_PAGE")
            a[i]["sha256"] = "0" * 64
            return (qc, q), (ac, a), (dc, d)
        V.load = tampered
        try:
            errs = V.check_anchors(self.R)
        finally:
            V.load = orig
        self.assertTrue(errs)

    def test_rm001_absent(self):
        self.assertEqual(V.check_rm001(), [])
        for x in self.a:
            self.assertNotEqual(x["sha256"], RM001_SHA)
            self.assertNotEqual(x["doc_id"], RM001_DOC)
        shas, docs = V.restricted_identifiers()
        self.assertIn(RM001_SHA, shas)
        self.assertIn(RM001_DOC, docs)

    def test_build_reproduces(self):
        self.assertEqual(V.check_build_reproduces(), [])

    def test_counts_match_build_info(self):
        import json
        info = json.loads((V.OUT / "BUILD_INFO.json").read_text(encoding="utf-8"))
        self.assertEqual(info["questions"], len(self.q))
        self.assertEqual(info["anchors"], len(self.a))
        self.assertEqual(info["status"], "NOT LEGALLY REVIEWED")


if __name__ == "__main__":
    unittest.main()
