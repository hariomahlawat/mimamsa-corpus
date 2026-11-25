"""C13-A0 scoring harness: synthetic checks for every task (no corpus, no holdout text)."""
import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

PKG = Path(__file__).resolve().parents[1] / "legal_knowledge/audit_work/C13-A0-EVAL"
sys.path.insert(0, str(PKG / "tools"))
import c13_score as SC  # noqa: E402

D = {f"I{i}": dict(court="SC" if i < 3 else "DEL", stratum="S1" if i % 2 else "S2", weight=1.0 if i < 3 else 3.0,
                   sha256=str(i) * 64) for i in range(6)}


class Score(unittest.TestCase):
    def test_self_test(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(SC.main(["--check"]), 0)

    def test_unknown_items_refused(self):
        with self.assertRaises(ValueError):
            SC.run("outcome", "T", [dict(item_id="ZZ", proceeding="1/2020")], [], D)

    def test_outcome_extra_and_missed_units(self):
        truth = [dict(item_id="I1", proceeding="CA 1/2020", printed_disposal="allowed", substantive_result="relief_granted"),
                 dict(item_id="I1", proceeding="CA 2/2020", printed_disposal="dismissed", substantive_result="relief_refused"),
                 dict(item_id="I2", proceeding="CA 3/2020", printed_disposal="unclear", substantive_result="unclear")]
        pred = [dict(item_id="I1", proceeding="CA 1/2020", printed_disposal="allowed", substantive_result="relief_granted"),
                dict(item_id="I1", proceeding="CA 9/2020", printed_disposal="dismissed", substantive_result="relief_refused"),
                dict(item_id="I2", proceeding="CA 3/2020", printed_disposal="dismissed", substantive_result="")]
        res, rows = SC.run("outcome", "T", truth, pred, D)
        c = res["overall"]["printed_disposal"]["categories"]
        self.assertEqual(c, {"CORRECT": 1, "MISSED": 1, "EXTRA_UNIT_NO_GOLD": 1, "PRED_ON_UNDETERMINABLE": 1})
        sp = res["overall"]["printed_disposal"]["strict_precision"]
        self.assertEqual((sp["k"], sp["n"]), (1, 3))
        cov = res["overall"]["printed_disposal"]["coverage"]
        self.assertEqual((cov["k"], cov["n"]), (1, 2))
        self.assertIn("SC", res["by_court"])
        self.assertEqual(res["evidence_anchor"]["counts"].get("NO_ANCHOR"), 3)

    def test_anchor_statuses(self):
        pages = {"x": {1: "Alpha beta.", 2: "The petition is dismissed."}}
        self.assertEqual(SC.anchor_status(dict(page="2", excerpt="petition is  dismissed"), pages, "x"), "ANCHOR_OK")
        self.assertEqual(SC.anchor_status(dict(page="1", excerpt="petition is dismissed"), pages, "x"), "ANCHOR_WRONG_PAGE")
        self.assertEqual(SC.anchor_status(dict(page="1", excerpt="allowed"), pages, "x"), "ANCHOR_NOT_FOUND")
        self.assertEqual(SC.anchor_status(dict(page="1", excerpt="x"), pages, "y"), "PAGE_TEXT_UNAVAILABLE")

    def test_holdings_lower_bound_and_adjudicated_precision(self):
        g = [dict(item_id="I1", item_type="holding", opinion="sole", page="3",
                  excerpt="limitation does not bar a claim for disability pension which is a continuing cause"),
             dict(item_id="I3", item_type="holding", opinion="lead", page="8",
                  excerpt="the summary court martial proceedings stand vitiated for want of a hearing")]
        p = [dict(item_id="I1", pred_id="P1", item_type="holding", opinion="sole", page="3",
                  excerpt="limitation does not bar a claim for disability pension which is a continuing cause"),
             dict(item_id="I1", pred_id="P2", item_type="holding", opinion="sole", page="9",
                  excerpt="costs are made easy between the parties in the circumstances")]
        res, _ = SC.run("holdings", "T", g, p, D)
        h = res["overall"]["holding"]
        self.assertEqual((h["recall"]["k"], h["recall"]["n"]), (1, 2))
        self.assertEqual((h["precision_reference_match_LOWER_BOUND"]["k"],
                          h["precision_reference_match_LOWER_BOUND"]["n"]), (1, 2))
        self.assertIn("LOWER BOUND", res["milestone"]["precision_basis"])
        res, _ = SC.run("holdings", "T", g, p, D, adjudication={"P1": "CORRECT", "P2": "CORRECT"})
        self.assertEqual(res["overall"]["holding"]["precision_true_adjudicated"]["unweighted"], 1.0)
        self.assertIn("true", res["milestone"]["precision_basis"])

    def test_relations_per_type(self):
        g = [dict(item_id="I4", page="5", cited_string="(2013) 7 SCC 316", target="(2013) 7 SCC 316", relation_type="follows"),
             dict(item_id="I4", page="5", cited_string="2025 INSC 549", target="2025 INSC 549", relation_type="cites")]
        p = [dict(item_id="I4", page="5", cited_string="2013 7 SCC 316", target="(2013) 7 SCC 316", relation_type="applies"),
             dict(item_id="I4", page="5", cited_string="2025 INSC 549", target="2025 INSC 549", relation_type="cites")]
        res, _ = SC.run("relations", "T", g, p, D)
        rt = res["overall"]["relation_type"]
        self.assertEqual(rt["strict_precision"]["k"], 1)
        self.assertEqual(rt["family_precision"]["k"], 2)          # follows / applies share the POSITIVE family
        self.assertEqual(set(res["by_predicted_relation_type"]), {"applies", "cites"})
        self.assertEqual(res["targets_status"]["relation_type"]["strict_precision"], "NO_TARGET")


if __name__ == "__main__":
    unittest.main()
