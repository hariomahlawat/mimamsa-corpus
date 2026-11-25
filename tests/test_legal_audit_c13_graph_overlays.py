"""C13-A5 overlays: SC case-number reconfirmation (metadata only, additive HF file) and identity resolution (all copies kept)."""
import csv
import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "legal_knowledge" / "audit_work" / "C13-A5-GRAPH"
C12 = ROOT / "legal_knowledge" / "audit_work" / "C12-CONSOLIDATION" / "metadata" / "SC_CASE_NUMBER_OVERLAY_C12.jsonl"
C11_STATUS = ROOT / "legal_knowledge" / "audit_work" / "C11-JUDICIAL-QUALITY" / "scnum" / "review" / "SC_CASE_NUMBER_REVIEWED_STATUS.csv"


def rows(p):
    return list(csv.DictReader(open(p, encoding="utf-8")))


class ScnumOverlay(unittest.TestCase):
    def setUp(self):
        self.c12 = {json.loads(l)["doc_id"]: json.loads(l) for l in open(C12, encoding="utf-8")}
        self.c13 = [json.loads(l) for l in open(PKG / "scnum" / "SC_CASE_NUMBER_OVERLAY_C13.jsonl", encoding="utf-8")]

    def test_only_the_99_staged_records_and_values_unchanged(self):
        self.assertEqual(len(self.c12), 99)
        self.assertLessEqual({o["doc_id"] for o in self.c13}, set(self.c12))
        for o in self.c13:
            s = self.c12[o["doc_id"]]
            self.assertEqual(o["overlay_value"], s["proposed_value"])
            self.assertEqual(o["source_copy_sha256"], s["sha256"])
            self.assertEqual(o["original_value"], [])

    def test_unreviewed_candidates_not_applied(self):
        unrev = {r["doc_id"] for r in rows(C11_STATUS) if r["application_status"] == "APPLY_CANDIDATE_UNREVIEWED_CONFIRMED"}
        self.assertEqual(len(unrev), 266)
        self.assertFalse(unrev & {o["doc_id"] for o in self.c13})

    def test_metadata_only_scope(self):
        for o in self.c13:
            self.assertEqual(o["scope"], "METADATA_ONLY_NO_EVIDENCE_OR_AUTHENTICATION_STATUS_PROMOTED")
            self.assertEqual(o["status"], "METADATA_OVERLAY_ORIGINAL_UNCHANGED")
            self.assertEqual(o["field"], "case_numbers")

    def test_reconfirmation_rows_consistent(self):
        rec = rows(PKG / "scnum" / "SCNUM_RECONFIRMATION_C13.csv")
        self.assertEqual(len(rec), 99)
        self.assertEqual({r["doc_id"] for r in rec if r["verdict"] == "RECONFIRMED"}, {o["doc_id"] for o in self.c13})
        self.assertTrue(all(r["sha256_verified"] == "TRUE" for r in rec))
        img = {r["doc_id"] for r in rows(PKG / "scnum" / "PAGE_IMAGE_CHECKS_C13.csv")}
        for r in rec:
            if r["not_found_in_text_layer"] or r["type_label_not_found"]:
                self.assertIn(r["doc_id"], img, "text-layer gap without a page-image reading")

    def test_hf_file_is_the_overlay_and_was_verified(self):
        staged = PKG / "hf" / "staged" / "data" / "meta_overlays" / "c13_2026-11-25_sc_case_numbers.jsonl"
        self.assertEqual(staged.read_bytes(), (PKG / "scnum" / "SC_CASE_NUMBER_OVERLAY_C13.jsonl").read_bytes())
        ver = rows(PKG / "hf" / "VERIFICATION.csv")
        self.assertEqual(len(ver), 3)
        self.assertTrue(all(v["result"] == "MATCH" and v["expected_sha256"] == v["downloaded_sha256"] for v in ver))
        man = {r["hf_path"]: r["sha256"] for r in rows(PKG / "hf" / "STAGED_MANIFEST.csv")}
        for v in ver:
            self.assertEqual(man[v["hf_path"]], v["downloaded_sha256"])
            self.assertTrue(v["hf_path"].startswith("data/meta_overlays/"))
            self.assertFalse(v["hf_path"].startswith("data/meta/"))
        commit = rows(PKG / "hf" / "HF_COMMIT.csv")[0]
        self.assertEqual(commit["parent_commit"], "3864faf3bb24edef4bfb18fa0916cc788eb68d79")
        self.assertEqual(hashlib.sha256(staged.read_bytes()).hexdigest(), man[str(staged.relative_to(PKG / "hf" / "staged"))])


class IdentityOverlay(unittest.TestCase):
    def setUp(self):
        self.rows = rows(PKG / "identity" / "IDENTITY_RESOLUTION_OVERLAY_C13.csv")
        self.summary = json.loads((PKG / "identity" / "IDENTITY_SUMMARY_C13.json").read_text())

    def test_every_copy_kept(self):
        self.assertEqual(self.summary["copies_in_scope"], 128)
        self.assertEqual(self.summary["copies_in_overlay"] + self.summary["copies_withheld_restricted"], 128)
        self.assertEqual(len({r["copy_sha256"] for r in self.rows}), self.summary["copies_in_overlay"])
        self.assertTrue(all(r["copies_kept"] == "ALL" for r in self.rows))
        self.assertEqual(self.summary["files_with_several_doc_ids"], 42)
        self.assertEqual(self.summary["one_id_several_sha256_groups"], 11)

    def test_non_destructive_vocabulary(self):
        for r in self.rows:
            self.assertEqual(r["status"], "PROPOSED_IDENTITY_OVERLAY_ALL_COPIES_KEPT")
            for word in ("DELETE", "REMOVE", "DROP"):
                self.assertNotIn(word, r["resolution"])

    def test_common_judgments_give_one_judgment_several_proceedings(self):
        by_copy = {}
        for r in self.rows:
            if r["resolution"] == "ONE_JUDGMENT_SEVERAL_PROCEEDINGS":
                by_copy.setdefault(r["copy_sha256"], set()).add((r["logical_identity_id"], r["proceeding_id"]))
        for sha, s in by_copy.items():
            self.assertEqual(len({x[0] for x in s}), 1)
            self.assertEqual(len({x[1] for x in s}), len(s))


if __name__ == "__main__":
    unittest.main()
