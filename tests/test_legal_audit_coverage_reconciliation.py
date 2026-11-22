"""WS-D cycle 2: coverage reconciliation (WS-C kb658 inventory vs WS-D scorecard) integrity.

The committed CSV must cover all 658 records exactly once, every disagreement must carry at least one
deterministic explanation tag, and the markdown matrix must match the CSV. Regeneration is checked only
when both local inputs exist (WS-C inventory and crawler corpus ref); CI checkouts may lack them.
Coverage is about locating sources, never legal correctness."""
import collections
import csv
import importlib.util
import io
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WSD = ROOT / "legal_knowledge" / "audit_work" / "WS-D-QUALITY"
SPEC = importlib.util.spec_from_file_location("wsd_recon", WSD / "scripts" / "coverage_reconciliation.py")
REC = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REC)
ROWS = list(csv.DictReader(io.StringIO((WSD / "coverage_reconciliation.csv").read_text(encoding="utf-8"), newline="")))
MD = (WSD / "coverage_reconciliation.md").read_text(encoding="utf-8")


def ref_ok(ref):
    return subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--verify", "-q", ref], capture_output=True).returncode == 0


class CoverageReconciliation(unittest.TestCase):
    def test_all_658_records_once(self):
        ids = [r["record_id"] for r in ROWS]
        self.assertEqual(len(ids), 658)
        self.assertEqual(len(set(ids)), 658)

    def test_every_disagreement_explained_and_agreements_untagged(self):
        for r in ROWS:
            if r["agree"] == "NO":
                tags = r["explanation_tags"].split(";")
                self.assertNotIn("UNEXPLAINED", tags, r["record_id"])
                self.assertTrue(set(tags) <= set(REC.RULES), r["record_id"])
            else:
                self.assertEqual(r["explanation_tags"], "", r["record_id"])
                self.assertEqual(r["wsc_bucket"], r["wsd_bucket"])

    def test_buckets_follow_declared_mapping(self):
        for r in ROWS:
            self.assertEqual(REC.C_BUCKET[r["wsc_state"]], r["wsc_bucket"])
            self.assertEqual(REC.D_BUCKET[r["wsd_state"]], r["wsd_bucket"])

    def test_wsc_totals_match_published_wsc_summary(self):
        c = collections.Counter(r["wsc_state"] for r in ROWS)
        self.assertEqual(dict(c), {"FULL": 379, "PARTIAL": 131, "SOURCE_GAP": 56, "UNRESOLVED": 14, "NO_CITATION": 78})

    def test_wsd_totals_match_scorecard(self):
        c = collections.Counter(r["wsd_state"] for r in ROWS)
        self.assertEqual(c["D_CODED_ALL_SEARCHABLE"], 279)
        self.assertEqual(c["D_PLAIN_ALL_STATUTE_SEARCHABLE"], 169)
        self.assertEqual(sum(v for k, v in c.items() if k.startswith("D_CODED")), 389)

    def test_markdown_agreement_line_matches_csv(self):
        agree = sum(r["agree"] == "YES" for r in ROWS)
        self.assertIn(f"**Agreement: {agree}/658", MD)
        self.assertIn("PROPOSAL ONLY", MD)

    @unittest.skipUnless(ref_ok("origin/raw-data") and (ref_ok("origin/claude/ws-c-mml") or (ROOT / REC.WSC_PATH).is_file()),
                         "local WS-C inventory or crawler corpus ref unavailable")
    def test_regeneration_equals_committed(self):
        rows, _ = REC.build("auto", "origin/raw-data")
        self.assertEqual([{k: str(v) for k, v in r.items()} for r in rows], ROWS)


if __name__ == "__main__":
    unittest.main()
