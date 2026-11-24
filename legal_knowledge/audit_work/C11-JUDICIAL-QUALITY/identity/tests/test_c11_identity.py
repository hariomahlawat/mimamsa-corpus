"""Tests for the C11 judgment-identity workstream (tools/identity_c11.py).

Run: python -m pytest -q tests/test_c11_identity.py   (or: python tests/test_c11_identity.py)
The reproduction test needs PyMuPDF and the corpus clone (env MIMAMSA_REPO, default /home/user/c7); without them it is
skipped with the reason. The accounting and classification tests read the committed outputs and need neither.
"""
import csv, hashlib, json, os, subprocess, sys, unittest
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent
OUT = PKG / "outputs"
TOOL = PKG / "tools" / "identity_c11.py"
C10 = PKG.parent.parent / "C10-HF-JUDGMENTS"
REPO = os.environ.get("MIMAMSA_REPO", "/home/user/c7")
EMPTY_SHA = hashlib.sha256(b"").hexdigest()
DUP_CLASSES = {"CONFIRMED_DUPLICATE_SAME_JUDGMENT", "SAME_JUDGMENT_DIFFERENT_RENDITION", "COMPOSITE_FILE"}
MERGING = DUP_CLASSES | {"POINTER_ORDER_NOT_A_SEPARATE_JUDGMENT"}


def rcsv(p):
    with open(p, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def have_pymupdf():
    try:
        import pymupdf  # noqa: F401
        return True
    except ImportError:
        try:
            import fitz  # noqa: F401
            return True
        except ImportError:
            return False


def have_repo():
    try:
        subprocess.run(["git", "-C", REPO, "cat-file", "-e", "ad77758d^{commit}"], check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


class Reproduction(unittest.TestCase):
    @unittest.skipUnless(have_pymupdf(), "PyMuPDF not installed: full rebuild impossible (checksum test still runs)")
    @unittest.skipUnless(have_repo(), "corpus clone with commit ad77758d not available (set MIMAMSA_REPO)")
    def test_check_reproduces(self):
        r = subprocess.run([sys.executable, "-I", "-B", str(TOOL), "--repo", REPO, "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr[-2000:])
        self.assertIn("OK", r.stdout)

    def test_checksums(self):
        for ln in (OUT / "OUTPUT_SHA256SUMS").read_text().splitlines():
            h, n = ln.split("  ", 1)
            self.assertEqual(hashlib.sha256((OUT / n).read_bytes()).hexdigest(), h, n)

    def test_check_without_pymupdf_skips_with_reason(self):
        if have_pymupdf():
            self.skipTest("PyMuPDF is installed here; the no-PyMuPDF path is exercised under a plain interpreter")
        r = subprocess.run([sys.executable, "-I", "-B", str(TOOL), "--repo", REPO, "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("SKIP full reproduction", r.stdout)


class Accounting(unittest.TestCase):
    def test_every_file_exactly_once(self):
        reg = rcsv(OUT / "JUDGMENT_IDENTITY_REGISTER.csv")
        cop = rcsv(C10 / "outputs" / "HF_JUDGMENT_COPY_REGISTER.csv")
        shas = [r["sha256"] for r in reg]
        self.assertEqual(len(shas), 3959)
        self.assertEqual(len(set(shas)), len(shas))
        self.assertEqual(set(shas), {r["sha256"] for r in cop})
        s = json.loads((OUT / "IDENTITY_SUMMARY.json").read_text())
        self.assertTrue(s["accounting"]["every_file_exactly_once"])
        self.assertEqual(s["accounting"]["register_rows"], 3959)

    def test_judgment_keys_consistent_with_count(self):
        reg = rcsv(OUT / "JUDGMENT_IDENTITY_REGISTER.csv")
        s = json.loads((OUT / "IDENTITY_SUMMARY.json").read_text())
        d = s["distinct_judgments"]
        keys = {r["judgment_key"] for r in reg}
        self.assertEqual(len(keys), d["judgment_entities_from_files"])
        self.assertEqual(d["revised_distinct_judgments"], d["judgment_entities_from_files"] + d["change_judgments_inside_composite_files"])
        self.assertEqual(len(d["additional_judgment_keys"]), d["change_judgments_inside_composite_files"])
        extra = [r["additional_judgments_in_file"].split(" | ")[0] for r in reg if r["additional_judgments_in_file"]]
        self.assertEqual(sorted(extra), sorted(d["additional_judgment_keys"]))
        self.assertTrue(d["sum_check"])
        # each judgment has exactly one representative or sole copy
        reps = [r["judgment_key"] for r in reg if r["copy_identity_role"] in ("REPRESENTATIVE_COPY_OF_JUDGMENT", "SOLE_COPY_OF_JUDGMENT")]
        self.assertEqual(sorted(reps), sorted(keys))

    def test_prior_same_text_finding_reproduced(self):
        s = json.loads((OUT / "IDENTITY_SUMMARY.json").read_text())
        rep = s["same_text_reproduction"]
        self.assertEqual(rep["reproduced"], {"groups": 62, "files": 292})
        groups = [g for g in rcsv(OUT / "SAME_TEXT_GROUPS.csv") if g["scope"] == "EXACT_TEXT_SHA256"]
        self.assertEqual(len(groups), 62)
        self.assertEqual(sum(int(g["n_files"]) for g in groups), 292)

    def test_23_plan_complete(self):
        plan = rcsv(OUT / "INCOMPLETE_23_RECOVERY_PLAN.csv")
        cont = rcsv(C10 / "outputs" / "CONTINUATION_MANIFEST.csv")
        self.assertEqual(sorted(p["sha256"] for p in plan), sorted(c["sha256"] for c in cont))
        self.assertTrue(all(p["downloaded"] == "NO" and p["approval_required"] for p in plan))


class ReviewFindings(unittest.TestCase):
    """C11 identity review (REVISE): F1-F3, F5, F7-F9 are reflected in the outputs."""

    def setUp(self):
        self.reg = {r["sha256"][:12]: r for r in rcsv(OUT / "JUDGMENT_IDENTITY_REGISTER.csv")}

    def same(self, prefixes):
        return len({self.reg[p]["judgment_key"] for p in prefixes}) == 1

    def test_f1_scanned_sets_merged(self):
        jamna = [k for k, r in self.reg.items() if r["court"] == "High Court of Delhi" and r["issue_date_meta"] == "2011-07-08"]
        self.assertEqual(len(jamna), 20)
        self.assertTrue(self.same(jamna))
        self.assertTrue(self.same(["75f7c670d822", "455c9c7517c1", "6069c60f0c77", "b95440b8721b"]))
        self.assertTrue(self.same(["081a8b226793", "3b347f95d7ee", "664ecaf6191a", "781f346a49ab", "79dfb85b0985", "90a7bf5a8a29"]))
        self.assertTrue(self.reg["081a8b226793"]["additional_judgments_in_file"].startswith("JK-081a8b22679359ab#p9-10"))

    def test_f1_footer_only_lead_does_not_merge_different_cases(self):
        self.assertFalse(self.same(["5bcd59ad8e28", "717a19122f4e"]))   # W.P.(C) 18383 vs 18333/2025, a clerk's footer

    def test_f2_f3_merged_and_p_h_pair_apart(self):
        g = {x["group_id"]: x for x in rcsv(OUT / "SAME_TEXT_GROUPS.csv")}
        self.assertEqual(g["STGX-48cde9cce413"]["classification"], "SAME_JUDGMENT_DIFFERENT_RENDITION")
        self.assertEqual(g["STGX-a40df1672bd1"]["classification"], "SAME_JUDGMENT_DIFFERENT_RENDITION")
        self.assertEqual(g["STGN-88c999976778"]["classification"], "UNRESOLVED")

    def test_f5_f9_keys_and_flags(self):
        self.assertTrue(self.reg["0f65307432d1"]["additional_judgments_in_file"].startswith("JK-0f65307432d16f74#p16-25 | SCI:WPC-129-2018"))
        self.assertTrue(self.reg["b64df349c9f5"]["composite_flag"].startswith("TWO_OPINIONS_SPLIT_VERDICT"))

    def test_f7_pointer_orders_linked(self):
        lead = {self.reg[p]["judgment_key"] for p in ("479005fadfeb", "6f1e4a7eb460", "7e1f56d0f695", "80011df68a8f", "c1a83ee07b70")}
        self.assertEqual(len(lead), 1)
        self.assertEqual(self.reg[[k for k in self.reg if k.startswith("b3ea334a")][0]]["judgment_key"], lead.pop())


class Classification(unittest.TestCase):
    def test_no_duplicate_when_text_empty(self):
        for g in rcsv(OUT / "SAME_TEXT_GROUPS.csv"):
            empty = EMPTY_SHA in g["text_sha256"].split(";") or "EMPTY_OR_NEAR_EMPTY" in g["text_quality"] or "NO_TEXT_EXTRACTED" in g["text_quality"]
            if empty:
                self.assertNotIn(g["classification"], DUP_CLASSES, g["group_id"])
                self.assertEqual(int(g["judgment_count_change"]), 0, g["group_id"])

    def test_classifier_rule_on_synthetic_empty_group(self):
        """The rule itself, independent of today's data: an empty-text group can never be a duplicate."""
        sys.path.insert(0, str(PKG / "tools"))
        import identity_c11 as t  # noqa: E402
        self.assertEqual(t.EMPTY_SHA, EMPTY_SHA)
        best = t.TIER_ORDER[0]   # bytes identical after masking: the strongest byte evidence there is
        for tq in (["EMPTY_OR_NEAR_EMPTY"], ["NO_TEXT_EXTRACTED"], ["EMPTY_OR_NEAR_EMPTY", "READABLE"]):
            cls, _ = t.classify_group(tq, best, ["High Court of Delhi"], ["2025-01-01"], [])
            self.assertNotIn(cls, DUP_CLASSES, tq)
            self.assertEqual(cls, "NOT_SAME_EMPTY_OR_NON_TEXT")
        cls, _ = t.classify_group(["NON_READABLE_TEXT_LAYER"], "PAGE_RENDERS_DIFFER", ["X"], ["d"], [])
        self.assertEqual(cls, "NOT_SAME_EMPTY_OR_NON_TEXT")
        self.assertEqual(t.classify_group(["READABLE"], best, ["X"], ["d"], [])[0], "CONFIRMED_DUPLICATE_SAME_JUDGMENT")
        self.assertEqual(t.classify_group(["READABLE"], best, ["X", "Y"], ["d"], [])[0], "UNRESOLVED")
        self.assertEqual(t.classify_group(["READABLE"], "PAGE_RENDERS_DIFFER", ["X"], ["d"], [])[0], "SAME_JUDGMENT_DIFFERENT_RENDITION")
        self.assertEqual(t.readable_ratio(""), 0.0)
        self.assertLess(t.readable_ratio('!"! #$% &\'()'), 0.4)
        self.assertGreater(t.readable_ratio("The petition stands dismissed by this Court"), 0.4)

    def test_merges_only_with_confirming_evidence(self):
        for g in rcsv(OUT / "SAME_TEXT_GROUPS.csv"):
            if g["scope"] == "EXACT_TEXT_SHA256" and g["classification"] == "CONFIRMED_DUPLICATE_SAME_JUDGMENT":
                self.assertNotIn("PAGE_RENDERS_DIFFER", g["byte_comparison"], g["group_id"])
                self.assertNotIn("BYTES_NOT_COMPARABLE", g["byte_comparison"], g["group_id"])
            if g["classification"] not in MERGING:
                self.assertEqual(int(g["judgment_count_change"]), 0, g["group_id"])
            else:
                self.assertLessEqual(int(g["judgment_count_change"]), 0)

    def test_everything_marked_automated(self):
        for n in ("JUDGMENT_IDENTITY_REGISTER.csv", "SAME_TEXT_GROUPS.csv", "COMPOSITE_AND_VERSION_CANDIDATES.csv", "INCOMPLETE_23_RECOVERY_PLAN.csv"):
            rows = rcsv(OUT / n)
            self.assertTrue(rows, n)
            self.assertTrue(all(r["verification"] == "AUTOMATED_NOT_LEGALLY_VERIFIED" for r in rows), n)


if __name__ == "__main__":
    unittest.main(verbosity=2)
