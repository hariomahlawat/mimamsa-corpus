"""C13-A0 double-coding toolkit: blinded packets, leakage check, agreement, X/Y adjudication, truth, store."""
import csv
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

PKG = Path(__file__).resolve().parents[1] / "legal_knowledge/audit_work/C13-A0-EVAL"
sys.path.insert(0, str(PKG / "tools"))
import c13_coding as K  # noqa: E402
import c13_common  # noqa: E402
from c13_tasks import POINTER_COLS, TASKS, case_key, citation_key  # noqa: E402

O = PKG / "outputs"
C12 = PKG.parent / "C12-CONSOLIDATION"


def rows_of(text):
    return list(csv.DictReader(io.StringIO(text)))


def sheet(h="H-OUT-C13", slot="coder_1"):
    return (O / f"packets/{h}/{slot}/CODER_SHEET.csv").read_text(encoding="utf-8")


def to_text(rows, cols):
    return c13_common.render_csv(rows, cols)


class Packets(unittest.TestCase):
    def test_packets_reproduce_and_pass_leakcheck(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(K.main(["--check"]), 0)
        for h, t in K.HOLDOUT_TASK.items():
            for slot in K.CODER_SLOTS:
                self.assertGreater(K.check_blank_sheet_text(sheet(h, slot), t), 0)

    def test_two_coders_same_items_different_order(self):
        a, b = rows_of(sheet(slot="coder_1")), rows_of(sheet(slot="coder_2"))
        self.assertEqual(sorted(r["item_id"] for r in a), sorted(r["item_id"] for r in b))
        self.assertNotEqual([r["item_id"] for r in a], [r["item_id"] for r in b])

    def test_coder_view_has_no_stratum_weight_or_extractor_field(self):
        for h in K.HOLDOUT_TASK:
            text = sheet(h)
            header = text.split("\n", 1)[0]
            for bad in ("stratum", "weight", "probab", "court", "pred", "extract", "outcome_meta", "rank"):
                self.assertNotIn(bad, header.lower(), h)
            for tok in K.FORBIDDEN_VALUE_TOKENS:
                self.assertNotIn(tok, text, h)
        for g in (PKG / "packets").glob("CODING_GUIDE_*.md"):
            for tok in K.FORBIDDEN_VALUE_TOKENS:
                self.assertNotIn(tok, g.read_text(encoding="utf-8"), g.name)


class LeakCheck(unittest.TestCase):
    def setUp(self):
        self.task = TASKS["outcome"]
        self.rows = rows_of(sheet())[:3]
        self.cols = POINTER_COLS + self.task.coding_fields

    def assertLeak(self, rows, cols):
        with self.assertRaises(K.LeakError):
            K.check_blank_sheet_text(to_text(rows, cols), "outcome")

    def test_clean_sheet_passes(self):
        self.assertEqual(K.check_blank_sheet_text(to_text(self.rows, self.cols), "outcome"), 3)

    def test_extra_stratum_column_fails(self):
        self.assertLeak([dict(r, stratum="OTHER") for r in self.rows], self.cols + ["stratum"])

    def test_prefilled_extractor_label_fails(self):
        self.assertLeak([dict(self.rows[0], printed_disposal="dismissed")] + self.rows[1:], self.cols)

    def test_forbidden_token_in_pointer_fails(self):
        self.assertLeak([dict(self.rows[0], rep_raw_store="BATCH_OR_MULTI")] + self.rows[1:], self.cols)

    def test_non_opaque_item_id_or_bad_path_fails(self):
        self.assertLeak([dict(self.rows[0], item_id="V3H001")] + self.rows[1:], self.cols)
        self.assertLeak([dict(self.rows[0], rep_raw_path="/home/x/y.pdf")] + self.rows[1:], self.cols)

    def test_completed_sheet_checks(self):
        with tempfile.TemporaryDirectory() as d:
            packet = Path(d) / "packet.csv"
            packet.write_text(to_text(self.rows, self.cols), encoding="utf-8")
            filled = [dict(r, coder_id="CODER-ONE", proceeding="CA 1/2020", printed_disposal="dismissed",
                           substantive_result="relief_refused", final_or_interim="final", page="3",
                           confidence="high") for r in self.rows]
            ok = Path(d) / "ok.csv"
            ok.write_text(to_text(filled, ["coder_id"] + self.cols), encoding="utf-8")
            _, errors = K.check_completed_sheet(ok, "outcome", "CODER-ONE", packet, ["CODER-TWO"])
            self.assertEqual(errors, [])
            other = Path(d) / "other.csv"   # another coder's labels pasted in
            other.write_text(to_text([dict(filled[0], notes="per CODER-TWO: dismissed")] + filled[1:],
                                     ["coder_id"] + self.cols), encoding="utf-8")
            with self.assertRaises(K.LeakError):
                K.check_completed_sheet(other, "outcome", "CODER-ONE", packet, ["CODER-TWO"])
            extra = Path(d) / "extra.csv"
            extra.write_text(to_text([dict(r, coder_b_label="x") for r in filled],
                                     ["coder_id"] + self.cols + ["coder_b_label"]), encoding="utf-8")
            with self.assertRaises(K.LeakError):
                K.check_completed_sheet(extra, "outcome", "CODER-ONE", packet)
            moved = Path(d) / "moved.csv"
            moved.write_text(to_text([dict(filled[0], rep_sha256="f" * 64)] + filled[1:], ["coder_id"] + self.cols),
                             encoding="utf-8")
            with self.assertRaises(K.LeakError):
                K.check_completed_sheet(moved, "outcome", "CODER-ONE", packet)


def oc(iid, proc, p, s, coder="A"):
    return dict(item_id=iid, coder_id=coder, proceeding=proc, printed_disposal=p, substantive_result=s,
                final_or_interim="final", page="2", confidence="high", excerpt="x", notes="")


class Agreement(unittest.TestCase):
    def test_reproduces_c12_v3_item_agreement(self):
        def load(c):
            out = []
            for seg in (1, 2, 3):
                p = C12 / f"holdout_v3/coding/coder_{c}_seg{seg}.csv"
                for r in csv.DictReader(io.StringIO(p.read_text(encoding="utf-8"))):
                    r["item_id"] = r["holdout_id"]
                    if r["item_id"] != "V3H035":        # file not locatable in C12 (tools F06): blank rows
                        out.append(r)
            return out
        items, summ = K.agreement("outcome", load("A"), load("B"))
        c12 = {r["holdout_id"]: r["status"] for r in
               csv.DictReader(io.StringIO((C12 / "holdout_v3/AGREEMENT.csv").read_text(encoding="utf-8")))}
        self.assertEqual({i["item_id"]: i["status"] for i in items}, {k: v for k, v in c12.items() if k != "V3H035"})
        self.assertEqual(summ["items_agree"], 134)
        self.assertGreater(summ["unmatched_units"], 0)      # proceeding-level misalignment is now visible (F02)

    def test_blank_or_off_vocabulary_fails(self):
        with self.assertRaises(ValueError):
            K.agreement("outcome", [oc("I1", "CA 1/2020", "dismissed", "")], [oc("I1", "CA 1/2020", "dismissed", "relief_refused")])
        with self.assertRaises(ValueError):
            K.agreement("outcome", [oc("I1", "CA 1/2020", "dismissed it", "relief_refused")],
                        [oc("I1", "CA 1/2020", "dismissed", "relief_refused")])

    def test_proceeding_level_strictness(self):
        a = [oc("I1", "CA 282/2020", "allowed", "relief_partly_granted"), oc("I1", "CA 283/2020", "allowed", "relief_granted")]
        b = [oc("I1", "CA 283/2020", "allowed", "relief_partly_granted"), oc("I1", "CA 282/2020", "allowed", "relief_granted")]
        items, summ = K.agreement("outcome", a, b)      # same label sets, swapped per proceeding -> DISAGREE
        self.assertEqual(items[0]["status"], "DISAGREE")
        items, _ = K.agreement("outcome", a, list(reversed(a)))
        self.assertEqual(items[0]["status"], "AGREE")

    def test_holdings_span_agreement(self):
        h = lambda iid, ex, page="4", t="holding": dict(item_id=iid, item_type=t, opinion="sole", page=page,  # noqa
                                                        excerpt=ex, certainty="certain", notes="")
        a = [h("I1", "The tribunal has no jurisdiction to entertain a challenge to a court martial sentence")]
        b = [h("I1", "tribunal has no jurisdiction to entertain challenge to court martial sentence", "5")]
        items, summ = K.agreement("holdings", a, b)
        self.assertEqual(items[0]["status"], "AGREE")
        self.assertEqual(summ["span_f1"], 1.0)
        none = [dict(item_id="I2", notes="NO_HOLDING")]
        items, _ = K.agreement("holdings", none, none)
        self.assertEqual(items[0]["status"], "AGREE")

    def test_relations_keys(self):
        self.assertEqual(citation_key("(2013) 7 SCC 316"), citation_key("2013 7 SCC 316"))
        self.assertEqual(citation_key("2025 INSC 549"), "INSC|2025|549")
        self.assertEqual(case_key("C.A. No. 4949 of 2013"), "4949-2013")


class AdjudicationTruthStore(unittest.TestCase):
    def setUp(self):
        self.a = [oc("I1", "CA 1/2020", "dismissed", "relief_refused", "CODER-ONE"),
                  oc("I2", "CA 2/2020", "allowed", "relief_granted", "CODER-ONE")]
        self.b = [oc("I1", "CA 1/2020", "dismissed", "relief_refused", "CODER-TWO"),
                  oc("I2", "CA 2/2020", "allowed", "relief_partly_granted", "CODER-TWO")]
        self.items, _ = K.agreement("outcome", self.a, self.b)

    def test_adjudication_sheet_is_anonymised(self):
        sheet, key = K.adjudication_sheet("outcome", self.a, self.b, self.items)
        self.assertNotIn("CODER-ONE", sheet)
        self.assertNotIn("CODER-TWO", sheet)
        self.assertNotIn("coder_id", sheet.split("\n", 1)[0])
        rs = rows_of(sheet)
        self.assertEqual({r["item_id"] for r in rs}, {"I2"})
        self.assertEqual({r["coding"] for r in rs}, {"X", "Y"})
        self.assertEqual(K.check_adjudication_sheet_text(sheet, {"CODER-ONE", "CODER-TWO"}), 2)
        self.assertEqual(rows_of(key)[0]["item_id"], "I2")

    def test_truth_requires_exact_adjudication_coverage(self):
        adj = [dict(oc("I2", "CA 2/2020", "allowed", "relief_granted"), agrees_with="X", reason="r")]
        truth = K.build_truth("outcome", self.a, self.b, self.items, adj)
        self.assertEqual({(t["item_id"], t["source"]) for t in truth}, {("I1", "BOTH_CODERS_AGREE"), ("I2", "ADJUDICATED")})
        with self.assertRaises(ValueError):           # stray adjudication of an agreed item (C12 tools F09)
            K.build_truth("outcome", self.a, self.b, self.items, adj + [oc("I1", "CA 1/2020", "allowed", "relief_granted")])
        with self.assertRaises(ValueError):           # missing adjudication
            K.build_truth("outcome", self.a, self.b, self.items, [])

    def test_store_is_versioned_immutable_and_tamper_evident(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "TRUTH.csv"
            f.write_text("item_id\nI1\n", encoding="utf-8")
            root = Path(d) / "store"
            K.store_version(root, "H-OUT-C13", 1, ["CODER-ONE", "CODER-TWO"], [f], "test")
            self.assertEqual(K.verify_store(root), [])
            with self.assertRaises(FileExistsError):
                K.store_version(root, "H-OUT-C13", 1, ["CODER-ONE"], [f], "test")
            K.store_version(root, "H-OUT-C13", 2, ["CODER-ONE", "ADJ"], [f], "test", parent_version=1)
            m = json.loads((root / "H-OUT-C13/v002/MANIFEST.json").read_text(encoding="utf-8"))
            self.assertEqual(m["parent_version"], 1)
            (root / "H-OUT-C13/v001/TRUTH.csv").write_text("item_id\nI9\n", encoding="utf-8")
            self.assertTrue(any("mismatch" in p for p in K.verify_store(root)))


if __name__ == "__main__":
    unittest.main()
