"""WS-D cycle 3: canonical coverage (CP-01 / OQ-D-016) - three separate measures, denominator 658.

Checks the measure vocabulary and internal rules, that inferred identities are never counted as identified,
that inputs are pinned (and a changed input yields an explicit 'regenerate' failure), byte-identical
regeneration, and that the superseded outputs are preserved. Coverage is not legal correctness."""
import collections
import csv
import hashlib
import importlib.util
import io
import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WSD = ROOT / "legal_knowledge" / "audit_work" / "WS-D-QUALITY"
SPEC = importlib.util.spec_from_file_location("wsd_canon", WSD / "scripts" / "canonical_coverage.py")
CC = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CC)
ROWS = list(csv.DictReader(io.StringIO((WSD / "canonical_coverage.csv").read_text(encoding="utf-8"), newline="")))
DOC = json.loads((WSD / "canonical_coverage.json").read_text(encoding="utf-8"))
MD = (WSD / "canonical_coverage.md").read_text(encoding="utf-8")


def ref_ok(ref):
    return subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--verify", "-q", ref], capture_output=True).returncode == 0


class CanonicalCoverage(unittest.TestCase):
    def test_denominator_658_unique(self):
        ids = [r["record_id"] for r in ROWS]
        self.assertEqual(len(ids), 658)
        self.assertEqual(len(set(ids)), 658)
        self.assertEqual(DOC["summary"]["denominator_records"], 658)

    def test_vocabulary(self):
        for r in ROWS:
            self.assertIn(r["citation_present"], ("YES", "NO"))
            self.assertIn(r["source_identified"], ("ALL", "PARTLY", "NONE", "NOT_APPLICABLE"))
            self.assertIn(r["source_searchable"], ("ALL", "PARTLY", "NONE", "NOT_CHECKED", "NOT_APPLICABLE"))
            self.assertIn(r["anchored_full"], ("YES", "NO"))

    def test_measure_rules(self):
        for r in ROWS:
            rid = r["record_id"]
            if r["citation_present"] == "NO":
                self.assertEqual((r["source_identified"], r["source_searchable"], r["anchored_full"], r["n_items"]),
                                 ("NOT_APPLICABLE", "NOT_APPLICABLE", "NO", "0"), rid)
            if r["source_identified"] in ("NONE", "NOT_APPLICABLE"):
                self.assertEqual(r["source_searchable"], "NOT_APPLICABLE", rid)
            if r["anchored_full"] == "YES":
                self.assertEqual((r["source_identified"], r["source_searchable"], r["quality_flags"]), ("ALL", "ALL", ""), rid)

    def test_inferred_never_counted_as_identified(self):
        for r in ROWS:
            self.assertEqual(int(r["n_identified"]), r["items"].count("[id]"), r["record_id"])
            self.assertEqual(int(r["n_inferred"]), r["items"].count("[inferred]"), r["record_id"])
            for item in filter(None, r["items"].split(" | ")):
                if item.startswith(("code:V9-S01", "code:V9-S02", "code:V9-S03")):
                    self.assertNotIn("[id]", item, "co-citation codes are never identified")
                if item.startswith("case:"):
                    self.assertNotIn("[id]", item, "plain case names are never identified")

    def test_summary_matches_rows(self):
        S = DOC["summary"]
        for k in ("citation_present", "source_identified", "source_searchable", "anchored_full"):
            self.assertEqual(dict(collections.Counter(r[k] for r in ROWS)), S[k], k)
        self.assertEqual(S["items"]["identified"], sum(int(r["n_identified"]) for r in ROWS))

    def test_inputs_pinned_and_current(self):
        for k, v in DOC["inputs"].items():
            if "sha256" not in v:
                continue
            p = ROOT / v["path"]
            self.assertTrue(p.is_file(), v["path"])
            got = hashlib.sha256(p.read_bytes()).hexdigest()
            if got != v["sha256"]:
                self.fail(f"input {k} changed - regenerate canonical coverage: run "
                          f"legal_knowledge/audit_work/WS-D-QUALITY/scripts/canonical_coverage.py ({v['path']})")

    def test_not_described_as_legal_correctness_and_superseded_preserved(self):
        self.assertTrue(DOC["not_legal_correctness"])
        self.assertIn("not legal correctness", MD)
        for name in DOC["supersedes_preserved"]:
            self.assertTrue((WSD / name).is_file(), name)

    @unittest.skipUnless(ref_ok("origin/raw-data"), "crawler corpus ref unavailable")
    def test_regeneration_is_byte_identical(self):
        files = CC.outputs("origin/raw-data")
        for p, text in files.items():
            self.assertEqual(p.read_text(encoding="utf-8"), text, p.name)


if __name__ == "__main__":
    unittest.main()
