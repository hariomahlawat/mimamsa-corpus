"""C13-A3 holdings redesign: passage classification, opinion-aware item types, anchors, status, exclusions."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
C13 = ROOT / "legal_knowledge" / "audit_work" / "C13-A3-HOLDINGS"
sys.path.insert(0, str(C13 / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import c13_corpus as cc  # noqa: E402
import c13_extract as cx  # noqa: E402
import c13_features as cf  # noqa: E402
from test_legal_audit_c13_holdings_segment import FILLER, page, split_verdict_escr, two_opinions_dissent_at_end  # noqa: E402

TOY = {"heads": {"holding": {"bias": -4.0, "w": {"sig:COURT_CONCLUSION_MARKER": 6.0, "w:hold": 2.0}},
                 "issue": {"bias": -5.0, "w": {"sig:ISSUE_HINT": 7.0}}},
       "thresholds": {"holding": 0.6, "holding_over_operative": 0.95, "holding_floor": 0.3, "floor_min_court_sentences": 15, "issue": 0.6}}


def toy_model():
    fd, p = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w") as f:
        json.dump(TOY, f)
    return cf.Model(p)


def doc():
    return page(1, "JUDGMENT\n\nSIKRI, J. Leave granted.\n\n" + FILLER +
                "\n\nThe short question that arises for our consideration is whether the Tribunal could direct appointment.\n\n"
                "It was submitted by learned counsel for the appellant that we hold the order bad.\n\n"
                "We hold that the Tribunal had no power to direct appointment to the post.\n\n"
                "Before parting, we may add that the authorities should decide the matter expeditiously.\n\n"
                "The appeal is accordingly allowed. No order as to costs.\n")


class Extract(unittest.TestCase):
    def setUp(self):
        self.m = toy_model()

    def run_doc(self, text, all_passages=False):
        return cx.analyze(text, {"judgment_id": "J-test", "sha256": "x", "court": "Supreme Court of India"}, self.m, all_passages)

    def test_classes_and_status(self):
        summ, items, passages, seg = self.run_doc(doc())
        by = {}
        for it in items:
            by.setdefault(it["item_type"], []).append(it["excerpt"])
        self.assertTrue(any("no power to direct appointment" in e for e in by.get("holding", [])), by)
        self.assertTrue(any("short question" in e for e in by.get("question_of_law", [])), by)
        self.assertTrue(any("accordingly allowed" in e for e in by.get("operative_direction", [])), by)
        self.assertTrue(any("Before parting" in e for e in by.get("obiter", [])), by)
        # the submission sentence containing "we hold" stays a party submission
        self.assertFalse(any("learned counsel" in e for e in by.get("holding", [])))
        classes = {p[4] for p in passages}
        self.assertIn("party_submission", classes)
        self.assertIn("material_fact", classes)
        self.assertTrue(classes <= set(cx.PASSAGE_CLASSES))
        for it in items:
            self.assertEqual(it["status"], "AUTOMATED_CANDIDATE_NOT_VERIFIED")
            a = it["anchor"]
            self.assertTrue(a["page"] >= 1 and a["char_end"] > a["char_start"])
            self.assertTrue(it["opinion_id"].startswith("OP"))

    def test_anchor_offsets_point_at_text(self):
        text = doc()
        _, items, _, _ = self.run_doc(text)
        for it in items:
            raw = " ".join(text[it["char_start"]:it["char_end"]].split())
            self.assertEqual(raw[:200], it["excerpt"][:200])

    def test_dissent_items_are_not_court_holdings(self):
        text = two_opinions_dissent_at_end().replace("I would, for all these reasons", "We hold that it is clear the contract was complete. I would, for all these reasons")
        _, items, _, seg = self.run_doc(text)
        dis = [it for it in items if it["opinion_role"] == "dissent" and it["passage_class"] == "holding"]
        self.assertTrue(dis)
        self.assertTrue(all(it["item_type"] == "dissent_holding_candidate" for it in dis))
        self.assertTrue(all(it["court_status"] == "DISSENT_NOT_THE_COURT" for it in dis))

    def test_split_verdict_items(self):
        text = split_verdict_escr().replace("The approval is upheld.", "We hold that it is clear the approval is valid.")
        _, items, _, _ = self.run_doc(text)
        sp = [it for it in items if it["passage_class"] == "holding" and it["opinion_role"] == "split_opinion"]
        self.assertTrue(sp)
        self.assertTrue(all(it["item_type"] == "split_opinion_holding_candidate" for it in sp))

    def test_deterministic(self):
        a = self.run_doc(doc())[1]
        b = self.run_doc(doc())[1]
        self.assertEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True))

    def test_restricted_copy_is_excluded(self):
        self.assertIn("4284820e5bc2fb7f52ae9fbe8a61650f1579e9b6389ba206a916a69fed016b14", cc.EXCLUDED_SHA256)


class Outputs(unittest.TestCase):
    """Checks on committed outputs, when present."""

    def test_committed_items_remain_candidates(self):
        p = C13 / "outputs" / "HOLDINGS_C13.jsonl"
        if not p.exists():
            self.skipTest("no full-run output committed")
        n = 0
        with open(p, encoding="utf-8") as f:
            for ln in f:
                x = json.loads(ln)
                n += 1
                self.assertEqual(x["status"], "AUTOMATED_CANDIDATE_NOT_VERIFIED")
                self.assertEqual(x["verification"], "NOT_VERIFIED_RATIO_NOT_DETERMINED")
                self.assertNotEqual(x["sha256"], "4284820e5bc2fb7f52ae9fbe8a61650f1579e9b6389ba206a916a69fed016b14")
                if x["opinion_role"] == "dissent":
                    self.assertNotEqual(x["item_type"], "holding")
        self.assertGreater(n, 0)

    def test_run_meta_hashes_match_tools(self):
        p = C13 / "outputs" / "RUN_META.json"
        if not p.exists():
            self.skipTest("no full-run output committed")
        import holdings_c13 as drv
        meta = json.loads(p.read_text())
        self.assertEqual(meta["tool_sha256"], drv.tool_hashes(drv.DEF_MODEL))


if __name__ == "__main__":
    unittest.main()
