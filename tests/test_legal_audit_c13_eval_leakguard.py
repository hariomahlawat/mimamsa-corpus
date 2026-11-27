"""C13-A0 leak guard (confirmation finding C01): no holdout judgment text anywhere under C13-A0-EVAL."""
import csv
import io
import json
import os
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

PKG = Path(__file__).resolve().parents[1] / "legal_knowledge/audit_work/C13-A0-EVAL"
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG / "tools"))
import c13_common  # noqa: E402
import c13_leakguard as L  # noqa: E402

REVIEWER_LIST = {"JK-1aa3838f30b79141", "JK-204366fba3be87b1", "JK-2890b7b47a443252", "JK-3775f27e8c6d1265",
                 "JK-3c00f93d93f6804f", "JK-566556d10756008c", "JK-6ad23cfb89323b87", "JK-7b198edc7afe64e3",
                 "JK-81730e236b81cfd5", "JK-8d5739ca50ff6b89", "JK-9c9c75f4aff795be", "JK-9da05d5ec12aa6fb",
                 "JK-a5fe29566f0774ec", "JK-c72781c1391284ec", "JK-cbf165489b0d8623", "JK-dc279e9f44680bd8",
                 "JK-e3c9f7c5d9d5a27c", "JK-f3a273f09da43b54"}


def rows(p):
    return list(csv.DictReader(io.StringIO(Path(p).read_text(encoding="utf-8"))))


class LeakGuard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fp = L.load_fp()

    def test_fingerprint_present_and_textless(self):
        self.assertGreater(len(self.fp), 100000)
        for x in list(self.fp)[:1000]:
            self.assertRegex(x, r"^[0-9a-f]{12}$")

    def test_no_holdout_text_under_c13_a0_eval(self):
        self.assertEqual(L.scan_tree(PKG, self.fp), {})

    def test_mechanism_flags_quoted_text(self):
        fake = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi omicron pi rho sigma"
        fp = L.shingle_hashes(fake) | {"000000000000"}
        self.assertGreaterEqual(L.scan_text("prefix " + fake + " suffix", fp), 1)
        self.assertEqual(L.scan_text("entirely different words here and there and everywhere today", fp), 0)

    def test_negative_control_removed_review_file_is_detected(self):
        r = subprocess.run(["git", "-C", str(REPO), "show",
                            "a4865e76:legal_knowledge/audit_work/C13-A0-EVAL/reviews/party_ppv.txt"],
                           capture_output=True)
        if r.returncode != 0:
            self.skipTest("commit a4865e76 not in this clone")
        self.assertGreaterEqual(L.scan_text(r.stdout.decode("utf-8", "replace"), self.fp), L.MIN_HITS)

    def test_text_bearing_review_files_removed(self):
        kept = sorted(p.name for p in (PKG / "reviews").rglob("*") if p.is_file())
        self.assertEqual(kept, ["confirmation_c13_a0_06340486.md", "review_c13_a0_5e07e010.md",
                                "review_c13_a0_5e07e010_findings.csv"])

    def test_exposed_judgments_registered_primary(self):
        sub = {r["judgment_key"]: r for r in rows(PKG / "outputs/holdouts/PRE_EXPOSED_SUBSET.csv")}
        for k in REVIEWER_LIST | {"JK-8edc4af5fdd3d9cf"}:
            self.assertIn("REVIEW_TEXT_EXPOSED", sub[k]["categories"], k)
            self.assertEqual(sub[k]["primary_sensitivity"], "true", k)
            self.assertIn("a4865e76", sub[k]["evidence"])
        self.assertEqual(sum("AUTHOR_DEV_SNIPPET_VIEWED" in r["categories"] for r in sub.values()), 10)

    def test_decision_wording_corrected_and_hashed(self):
        d = json.loads((PKG / "decisions/H-HOLD_RESERVE_DECISION.json").read_text(encoding="utf-8"))
        self.assertEqual(d["decision"], "FULL_OPEN")
        self.assertNotIn("Nothing has been coded or viewed", d["rationale"])
        self.assertIn("JK-c72781c1391284ec", d["exposure_disclosure"])
        sha = c13_common.sha256_file(PKG / "decisions/H-HOLD_RESERVE_DECISION.json")
        self.assertIn(sha, (PKG / "PROTOCOL_C13.md").read_text(encoding="utf-8"))

    @unittest.skipUnless(os.environ.get("MIMAMSA_C13_FULL") == "1", "needs the corpus (about 50 s)")
    def test_fingerprint_reproduces(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(c13_common.write_or_check(L.build(), c13_common.OUT, True, "x"), 0)


if __name__ == "__main__":
    unittest.main()
