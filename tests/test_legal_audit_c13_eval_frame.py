"""C13-A0 classification frame, exclusions and fresh holdouts: byte-for-byte reproduction and design invariants.

Stage 2 (frame), exclusions, sampler and packets run from committed files only. Stage 1 (text features) needs the
corpus commit ad77758d and the C12 additions copy; it runs only with MIMAMSA_C13_FULL=1.
"""
import csv
import hashlib
import io
import json
import os
import sys
import unittest
from collections import Counter
from contextlib import redirect_stdout
from pathlib import Path

PKG = Path(__file__).resolve().parents[1] / "legal_knowledge/audit_work/C13-A0-EVAL"
sys.path.insert(0, str(PKG / "tools"))
import c13_common  # noqa: E402
import c13_exclusions  # noqa: E402
import c13_frame  # noqa: E402
import c13_sampler  # noqa: E402

O = PKG / "outputs"


def rows(p):
    return list(csv.DictReader(io.StringIO(Path(p).read_text(encoding="utf-8"))))


def jload(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def quiet(fn, *a):
    with redirect_stdout(io.StringIO()):
        return fn(*a)


class Reproduction(unittest.TestCase):
    def test_exclusions_reproduce(self):
        self.assertEqual(quiet(c13_common.write_or_check, c13_exclusions.build(), O, True, "x"), 0)

    def test_frame_reproduces(self):
        self.assertEqual(quiet(c13_common.write_or_check, c13_frame.build(), O, True, "x"), 0)

    def test_sampler_reproduces(self):
        self.assertEqual(quiet(c13_common.write_or_check, c13_sampler.build(), O, True, "x"), 0)

    @unittest.skipUnless(os.environ.get("MIMAMSA_C13_FULL") == "1", "needs corpus ad77758d + C12 additions copy")
    def test_features_reproduce(self):
        import c13_features
        self.assertEqual(quiet(c13_common.write_or_check, c13_features.build(), O, True, "x"), 0)


class Sums(unittest.TestCase):
    def test_sha256sums_cover_and_match(self):
        import c13_check_all
        self.assertEqual((PKG / "SHA256SUMS").read_text(encoding="utf-8"), c13_check_all.sums_text())
        self.assertIn("PROTOCOL_C13.md", (PKG / "SHA256SUMS").read_text(encoding="utf-8"))


class FrameInvariants(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.recs = rows(O / "frame/FRAME_RECORDS.csv")
        cls.js = rows(O / "frame/FRAME_JUDGMENTS.csv")

    def test_every_judicial_record_classified(self):
        self.assertEqual(len(self.recs), 4281)        # 4,259 at ad77758d + 18 C12 ingested + 4 held-original derived
        self.assertEqual(Counter(r["population"] for r in self.recs)["C12_INGESTED"], 18)
        self.assertEqual(len({r["doc_id"] for r in self.recs}), 4281)
        for r in self.recs:
            self.assertIn(r["text_quality"], c13_frame.TEXT_QUALITY)
            self.assertIn(r["stratum"], c13_frame.STRATA)
            self.assertIn(r["in_scope"], ("IN_SCOPE", "UNCERTAIN", "OUT_OF_SCOPE"))
            self.assertNotEqual(r["year_band"], "")

    def test_non_usable_reported_not_dropped(self):
        nu = rows(O / "frame/NON_USABLE_POPULATION.csv")
        self.assertEqual({r["doc_id"] for r in nu}, {r["doc_id"] for r in self.recs if r["text_quality"] != "USABLE"})
        self.assertTrue({"GARBLED", "IMAGE_ONLY", "TRUNCATED", "UNREADABLE"} <= {r["text_quality"] for r in nu})

    def test_text_quality_rules(self):
        f = dict(population="BASE_AD77758D", text_present="true", letters="5000", text_pages="4", pages_usable="4",
                 letter_share="0.9", meta_text_method="pdf_text", meta_ocr_confidence="")
        self.assertEqual(c13_frame.text_quality(f, {}, {}, None)[0], "USABLE")
        self.assertEqual(c13_frame.text_quality(f, {"pdf_status": "UNREADABLE"}, {}, None)[0], "UNREADABLE")
        self.assertEqual(c13_frame.text_quality(
            f, {"source_completeness": "STORED_COPY_TRUNCATED_CONTENT_MAY_BE_MISSING"}, {}, None)[0], "TRUNCATED")
        self.assertEqual(c13_frame.text_quality(dict(f, letter_share="0.3"), {}, {}, None)[0], "GARBLED")
        self.assertEqual(c13_frame.text_quality(dict(f, meta_text_method="ocr"), {}, {}, None)[0], "IMAGE_ONLY")
        self.assertEqual(c13_frame.text_quality(dict(f, text_present="false"), {}, {}, None)[0], "IMAGE_ONLY")
        self.assertEqual(c13_frame.text_quality(
            f, {}, {}, {"completeness": "COMPLETE_FILE_TEXT_LAYER_UNUSABLE_NEEDS_OCR"})[0], "GARBLED")

    def test_counts_table_matches_frame(self):
        t = rows(O / "frame/STRATUM_COUNTS.csv")
        rec = sum(int(r["n"]) for r in t if r["level"] == "record")
        jud = sum(int(r["n"]) for r in t if r["level"] == "judgment")
        self.assertEqual(rec, len(self.recs))
        self.assertEqual(jud, len(self.js))

    def test_restricted_material_absent(self):
        for p in O.rglob("*.csv"):
            self.assertNotIn(next(iter(c13_common.FOUO_EXCLUDED_SHA256)), p.read_text(encoding="utf-8"), p)


class HoldoutInvariants(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frame = {r["judgment_key"]: r for r in rows(O / "frame/FRAME_JUDGMENTS.csv")}
        cls.excluded = set(c13_exclusions.load_excluded())
        cls.samples = {h: rows(O / f"holdouts/{h}/SAMPLE.csv") for h in ("H-OUT-C13", "H-HOLD-C13", "H-REL-C13")}

    def test_sizes(self):
        self.assertGreaterEqual(len(self.samples["H-OUT-C13"]), 200)
        self.assertEqual(len(self.samples["H-OUT-C13"]), 300)
        hold = self.samples["H-HOLD-C13"]
        self.assertEqual(len(hold), jload(O / "holdouts/H-HOLD-C13/DESIGN.json")["size_justification"]["judgments"])
        self.assertTrue({"SC"} < {r["court"] for r in hold})          # SC and HC both present
        self.assertEqual(len(self.samples["H-REL-C13"]), 160)

    def test_no_spent_or_ineligible_unit(self):
        for h, s in self.samples.items():
            for r in s:
                self.assertNotIn(r["judgment_key"], self.excluded, h)
                self.assertEqual(self.frame[r["judgment_key"]]["eligible_fresh_holdout"], "true", h)
                self.assertEqual(self.frame[r["judgment_key"]]["text_quality"], "USABLE", h)
        for r in rows(O / "holdouts/H-HOLD-C13/RESERVE.csv"):
            self.assertNotIn(r["judgment_key"], self.excluded)

    def test_inclusion_probabilities_match_frame_counts(self):
        el = [r for r in self.frame.values() if r["eligible_fresh_holdout"] == "true"]
        pop = Counter((r["court"], r["stratum"]) for r in el)
        d = jload(O / "holdouts/H-OUT-C13/DESIGN.json")
        for s in d["strata"]:
            self.assertEqual(s["N_h"], pop[(s["court"], s["stratum"])])
            if s["n_h"]:
                self.assertAlmostEqual(s["inclusion_probability"], s["n_h"] / s["N_h"], places=5)
        n = Counter(r["design_cell"] for r in self.samples["H-OUT-C13"])
        for r in self.samples["H-OUT-C13"]:
            self.assertEqual(r["design_cell"], f"{r['court']}|{r['stratum']}")
            self.assertEqual(int(r["n_h"]), n[r["design_cell"]])
            self.assertAlmostEqual(float(r["design_weight"]), int(r["N_h"]) / int(r["n_h"]), places=4)
        self.assertEqual(sum(s["n_h"] for s in d["strata"]), 300)

    def test_registration_hashes(self):
        reg = jload(O / "holdouts/HOLDOUT_REGISTRATION.json")
        for h, v in reg["holdouts"].items():
            for rel, sha in v["files"].items():
                self.assertEqual(hashlib.sha256((O / rel).read_bytes()).hexdigest(), sha, rel)

    def test_sampler_refuses_text_less_and_invalid_paths(self):
        ok = dict(judgment_key="JK-x", text_quality="USABLE", rep_raw_path="data/raw/hc/2020/" + "a" * 64 + ".pdf",
                  rep_raw_store="HF@5524c3d9 (C12 hash ledger)", spent_sets="", eligible_fresh_holdout="true")
        c13_sampler.assert_drawable(ok)
        for bad in (dict(ok, text_quality="GARBLED"), dict(ok, text_quality="IMAGE_ONLY"),
                    dict(ok, rep_raw_store="NOT_FOUND_IN_PINNED_STORES"), dict(ok, rep_raw_path=""),
                    dict(ok, spent_sets="C12_V3_HOLDOUT_150"), dict(ok, eligible_fresh_holdout="false")):
            with self.assertRaises(c13_sampler.NotDrawable):
                c13_sampler.assert_drawable(bad)
        with self.assertRaises(c13_sampler.NotDrawable):
            c13_sampler.stratified_sample([dict(ok, text_quality="TRUNCATED")], lambda u: "A",
                                          lambda u: u["judgment_key"], {"A": 1}, "s")

    def test_spent_sets_cover_required_sources(self):
        s = jload(O / "exclusions/EXCLUSION_SUMMARY.json")["sets"]
        self.assertEqual(s["C11_HOLDOUT_56"]["judgments"], 56)
        self.assertEqual(s["C12_V3_HOLDOUT_150"]["judgments"], 150)
        self.assertEqual(s["C12_HOLDINGS_REFERENCE_30"]["judgments"], 30)
        srcs = {x["file"] for v in s.values() for x in v["sources"]}
        self.assertIn("C12-CONSOLIDATION/extractor_v3/tools/dev_gold_v3.json", srcs)
        self.assertIn("C12-CONSOLIDATION/holdings/outputs/dev_predictions/DEV_IDS.txt", srcs)


if __name__ == "__main__":
    unittest.main()
