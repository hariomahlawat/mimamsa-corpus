"""C13-A0 PROTOCOL v1.1 fixes (GA0 review 5e07e010): validated interval (F01), weighted size restatement (F02),
party-specific descriptive (F03), pre-exposed subsets (F04/F06), UNCODABLE (F05) and the P3 fixes."""
import csv
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

PKG = Path(__file__).resolve().parents[1] / "legal_knowledge/audit_work/C13-A0-EVAL"
sys.path.insert(0, str(PKG / "tools"))
import c13_ci_sim  # noqa: E402
import c13_coding as K  # noqa: E402
import c13_common  # noqa: E402
import c13_power  # noqa: E402
import c13_score as SC  # noqa: E402
import c13_sensitivity  # noqa: E402
import c13_stats as S  # noqa: E402
from c13_tasks import POINTER_COLS, TASKS  # noqa: E402

O = PKG / "outputs"


def jload(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def quiet(fn, *a):
    with redirect_stdout(io.StringIO()):
        return fn(*a)


class ValidatedInterval(unittest.TestCase):
    def test_clopper_pearson_known_values(self):
        _, lo, hi = S.clopper_pearson(81, 263)
        self.assertAlmostEqual(lo, 0.2527, places=3)
        self.assertAlmostEqual(hi, 0.3676, places=3)
        _, lo, hi = S.clopper_pearson(10, 10)
        self.assertAlmostEqual(lo, 0.025 ** 0.1, places=6)
        self.assertEqual(hi, 1.0)

    def test_design_cp_is_not_narrower_than_kish_when_cells_have_no_errors(self):
        units = [(f"j{i}", "A" if i < 20 else "B", 1.0 if i < 20 else 25.0, 1, 1) for i in range(40)]
        cp = S.design_cp(units)
        self.assertEqual(cp["p"], 1.0)
        self.assertLess(cp["lo"], 1.0)
        _, klo, _ = S.weighted_wilson(units)
        self.assertLessEqual(cp["lo"], klo + 1e-9)

    def test_committed_simulation_validates_coverage(self):
        summ = jload(O / "ci_validation/CI_COVERAGE_SUMMARY.json")
        self.assertTrue(summ["validated"])
        self.assertGreaterEqual(summ["min_coverage_design_cp95_outcome_p090_099"], 0.95)
        rows = list(csv.DictReader(io.StringIO((O / "ci_validation/CI_COVERAGE.csv").read_text(encoding="utf-8"))))
        ps = {float(r["nominal_p"]) for r in rows if r["holdout"] == "H-OUT-C13"}
        self.assertTrue({0.90, 0.95, 0.98, 0.99} <= ps)
        for r in rows:
            self.assertGreaterEqual(float(r["coverage_design_cp95"]), 0.95, r)

    def test_quick_simulation_recomputes(self):
        out = c13_ci_sim.build(nsim=120, p_out=[0.98], p_hold=[0.6])
        for r in csv.DictReader(io.StringIO(out["ci_validation/CI_COVERAGE.csv"])):
            self.assertGreaterEqual(float(r["coverage_design_cp95"]), 0.90, r)

    @unittest.skipUnless(os.environ.get("MIMAMSA_C13_FULL") == "1", "full simulation takes about a minute")
    def test_full_simulation_reproduces(self):
        self.assertEqual(quiet(c13_common.write_or_check, c13_ci_sim.build(), O, True, "x"), 0)

    def test_pass_rule_uses_validated_interval(self):
        est = dict(weighted=0.99, unweighted=0.99, weighted_design_cp95=[0.94, 1.0],
                   weighted_cluster_bootstrap95_secondary_not_for_pass_rule=[0.97, 1.0])
        self.assertEqual(SC.target_status(est, 0.95), "MET_POINT_ONLY")
        est["weighted_design_cp95"] = [0.951, 1.0]
        self.assertEqual(SC.target_status(est, 0.95), "MET_LOWER_BOUND")
        self.assertEqual(SC.target_status(est, 0.95, descriptive=True), "DESCRIPTIVE_ONLY")


class Restatement(unittest.TestCase):
    def test_power_and_sensitivity_reproduce(self):
        self.assertEqual(quiet(c13_common.write_or_check, c13_power.build(), O, True, "x"), 0)
        self.assertEqual(quiet(c13_common.write_or_check, c13_sensitivity.build(), O, True, "x"), 0)

    def test_restated_figures(self):
        r = jload(O / "holdouts/SIZE_RESTATEMENT_V1_1.json")
        self.assertAlmostEqual(r["H-OUT-C13"]["kish_deff"], 2.0, delta=0.05)
        self.assertGreater(r["H-HOLD-C13"]["recall_halfwidth_at_p060"], 0.08)          # not +/-7pp
        self.assertGreater(r["H-REL-C13"]["kish_deff_overall"], 5)
        self.assertIn("DESCRIPTIVE ONLY", r["party_specific_expected_gold_units_H-OUT"]["decision"])

    def test_curated_pre_exposed_judgments_registered(self):
        rows = {r["judgment_key"]: r for r in csv.DictReader(io.StringIO(
            (O / "holdouts/PRE_EXPOSED_SUBSET.csv").read_text(encoding="utf-8")))}
        for k in ("JK-16dcc07543999d26", "JK-76ec35cd7ab232b5", "JK-88f84411abdb3028", "JK-05e9484593272fe0"):
            self.assertIn("CURATED_KB_CONTENT", rows[k]["categories"])
            self.assertEqual(rows[k]["primary_sensitivity"], "true")
        self.assertIn("NEAR_IDENTICAL_SPENT_SIBLING", rows["JK-3b5da3990d543f3a"]["categories"])
        self.assertEqual(sum("CASE_NUMBER_REVIEWED" in r["categories"] for r in rows.values()), 27)

    def test_holdouts_not_redrawn(self):
        reg = jload(O / "holdouts/HOLDOUT_REGISTRATION.json")
        self.assertEqual(reg["sizes"]["H-OUT-C13"], 300)
        for v in reg["holdouts"].values():
            for rel, sha in v["files"].items():
                self.assertEqual(c13_common.sha256_bytes((O / rel).read_bytes()), sha)


def oc(iid, coder, notes="", **kw):
    r = dict(item_id=iid, coder_id=coder, proceeding="CA 1/2020", printed_disposal="dismissed",
             substantive_result="relief_refused", final_or_interim="final", page="2", confidence="high", notes=notes)
    r.update(kw)
    return r


class Uncodable(unittest.TestCase):
    def test_agreement_on_uncodable(self):
        u = lambda c, code: dict(item_id="I1", coder_id=c, notes=f"UNCODABLE:{code}")  # noqa: E731
        items, summ = K.agreement("outcome", [u("A", "SHA_MISMATCH")], [u("B", "SHA_MISMATCH")])
        self.assertEqual(items[0]["status"], "AGREE")
        self.assertEqual(summ["items_uncodable_both"], 1)
        items, _ = K.agreement("outcome", [u("A", "SHA_MISMATCH")], [oc("I1", "B")])
        self.assertEqual(items[0]["status"], "DISAGREE")
        with self.assertRaises(ValueError):
            K.agreement("outcome", [u("A", "NOT_A_CODE")], [u("B", "NOT_A_CODE")])

    def test_guides_document_uncodable(self):
        for g in (PKG / "packets").glob("CODING_GUIDE_*.md"):
            self.assertIn("UNCODABLE:", g.read_text(encoding="utf-8"), g.name)


class P3Fixes(unittest.TestCase):
    def setUp(self):
        self.task = TASKS["outcome"]
        self.cols = POINTER_COLS + self.task.coding_fields
        self.rows = list(csv.DictReader(io.StringIO(
            (O / "packets/H-OUT-C13/coder_1/CODER_SHEET.csv").read_text(encoding="utf-8"))))[:2]

    def _returned(self, d, filled):
        p = Path(d) / "ret.csv"
        p.write_text(c13_common.render_csv(filled, ["coder_id"] + self.cols), encoding="utf-8")
        pk = Path(d) / "packet.csv"
        pk.write_text(c13_common.render_csv(self.rows, self.cols), encoding="utf-8")
        return p, pk

    def test_f08_model_tokens_in_free_text_and_required_other_coder(self):
        with tempfile.TemporaryDirectory() as d:
            ok = [dict(r, **{k: v for k, v in oc(r["item_id"], "C1").items() if k != "item_id"}) for r in self.rows]
            p, pk = self._returned(d, ok)
            K.check_completed_sheet(p, "outcome", "C1", pk, ["C2"])
            with self.assertRaises(K.LeakError):
                K.check_completed_sheet(p, "outcome", "C1", pk, [])
            bad = [dict(ok[0], notes="AUTOMATED_CANDIDATE_NOT_VERIFIED extractor V4 output: dismissed")] + ok[1:]
            p, pk = self._returned(d, bad)
            with self.assertRaises(K.LeakError):
                K.check_completed_sheet(p, "outcome", "C1", pk, ["C2"])

    def test_f09_adjudication_key_not_recomputable_from_code(self):
        a = [oc("I1", "C1", printed_disposal="allowed", substantive_result="relief_granted")]
        b = [oc("I1", "C2")]
        items, _ = K.agreement("outcome", a, b)
        _, k1 = K.adjudication_sheet("outcome", a, b, items)
        _, k2 = K.adjudication_sheet("outcome", a, b, items)
        s1 = list(csv.DictReader(io.StringIO(k1)))[0]["run_seed"]
        s2 = list(csv.DictReader(io.StringIO(k2)))[0]["run_seed"]
        self.assertNotEqual(s1, s2)
        self.assertEqual(len(s1), 32)
        self.assertEqual(K.adjudication_sheet("outcome", a, b, items, seed="x"),
                         K.adjudication_sheet("outcome", a, b, items, seed="x"))

    def test_f07_store_required(self):
        with redirect_stdout(io.StringIO()), self.assertRaises(SystemExit):
            import contextlib
            with contextlib.redirect_stderr(io.StringIO()):
                SC.main(["--task", "outcome", "--holdout", "H-OUT-C13", "--truth", "t", "--pred", "p", "--out-dir", "o"])

    def test_f10_h_rel_clusters_are_judgments(self):
        d = SC.load_design("H-REL-C13")
        self.assertEqual(len(d), 160)
        self.assertLess(len({v["cluster"] for v in d.values()}), 160)
        self.assertTrue(all(v["cluster"].startswith("JK-") for v in d.values()))

    def test_f11_reserve_opening_recomputes_weights(self):
        base = SC.load_design("H-HOLD-C13", reserve_open="none")
        full = SC.load_design("H-HOLD-C13", reserve_open="all")
        self.assertEqual(set(SC.load_design("H-HOLD-C13")), set(full))      # recorded decision FULL_OPEN
        self.assertEqual(len(base), 75)
        self.assertEqual(len(full), 113)
        cell = "HC_DEL|MEDIUM_5_14P"
        wb = {v["weight"] for v in base.values() if v["cell"] == cell}
        wf = {v["weight"] for v in full.values() if v["cell"] == cell}
        self.assertEqual(len(wb), 1)
        self.assertLess(next(iter(wf)), next(iter(wb)))
        part = SC.load_design("H-HOLD-C13", reserve_open={cell: 2})
        self.assertEqual(sum(v["cell"] == cell for v in part.values()),
                         sum(v["cell"] == cell for v in base.values()) + 2)
        for slot in K.CODER_SLOTS:          # FULL_OPEN: one packet of 113 per coder
            text = (O / f"packets/H-HOLD-C13/{slot}/CODER_SHEET.csv").read_text(encoding="utf-8")
            self.assertEqual(K.check_blank_sheet_text(text, "holdings"), 113)
            ids = {r["item_id"] for r in csv.DictReader(io.StringIO(text))}
            self.assertEqual(ids, set(full))

    def test_reserve_decision_recorded_before_coding(self):
        d = jload(PKG / "decisions/H-HOLD_RESERVE_DECISION.json")
        self.assertEqual(d["decision"], "FULL_OPEN")
        self.assertTrue(d["made_before_any_coding"])
        sha = c13_common.sha256_file(PKG / "decisions/H-HOLD_RESERVE_DECISION.json")
        self.assertIn(sha, (PKG / "PROTOCOL_C13.md").read_text(encoding="utf-8"))

    def test_f04_sensitivity_and_f12_breakdown_status(self):
        design = SC.load_design("H-OUT-C13")
        ids = sorted(design)[:40]
        sub = {i: design[i] for i in ids}
        truth = [dict(item_id=i, proceeding="CA 1/2020", printed_disposal="dismissed",
                      substantive_result="relief_refused") for i in ids]
        pre = {design[ids[0]]["cluster"]: {"CURATED_KB_CONTENT"}}
        res, _ = SC.run("outcome", "H-OUT-C13", truth, truth, sub, pre_exposed=pre)
        self.assertEqual(res["sensitivity"]["without_primary_pre_exposed"]["items_excluded"], 1)
        for c, v in res["by_court"].items():
            self.assertIn("targets_status", v)
        self.assertEqual(res["subsets"]["gold_party_specific"]["targets_status"]["printed_disposal"]["strict_precision"],
                         "DESCRIPTIVE_ONLY")


if __name__ == "__main__":
    unittest.main()
