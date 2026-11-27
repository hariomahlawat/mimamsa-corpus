#!/usr/bin/env python3
"""Tests for the C12 outcome extractor v3 (tools/v3core.py, tools/extract_v3.py).

Synthetic tests run anywhere (standard library only). Tests on the real text layer need the c7 repository at
commit ad77758d and the C10/C11 registers; they are skipped, with the reason, when those are missing.
Run:  python -I -B -m unittest discover -s tests -v      (from the extractor_v3 folder)
"""
import csv
import io
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.join(os.path.dirname(HERE), "tools")
sys.path.insert(0, TOOLS)
import v3core  # noqa: E402

U = v3core.UNVERIFIED
REPO = "/home/user/c7"


def page(n, body):
    return "[[page %d]]\n%s\n" % (n, body)


def run(text, cn="", jid="J-test"):
    rows, _ = v3core.analyze(text, {"judgment_id": jid, "sha256": "0" * 64, "doc_ids": ["d"], "case_numbers_meta": cn,
                                    "court": "test"})
    return rows


def by_proc(rows):
    return {r["proceeding"]: r for r in rows}


FILLER = ("The petitioner was enrolled in the Army and was discharged in low medical category. The Release Medical "
          "Board assessed the disability and the respondents rejected the claim for disability pension. ") * 6

JK_HEAD = """HIGH COURT OF JAMMU & KASHMIR AND LADAKH
AT JAMMU
Reserved on: 01.09.2025
Pronounced on: 03.11.2025

WP(C) No. 100/2024
WP(C) Nos. 101, 102 of 2024

1. WP(C) No.100/2024
Union of India and others v. A
.....Petitioner(s)
.....Respondent(s)
2. WP(C) No.101/2024
Union of India and others v. B
.....Petitioner(s)
.....Respondent(s)
3. WP(C) No.102/2024
Union of India and others v. C
.....Petitioner(s)
.....Respondent(s)

CORAM: HON'BLE MR. JUSTICE X, JUDGE

JUDGMENT

1. In all these petitions the Union of India challenges orders of the Armed Forces Tribunal. %s
""" % FILLER


def jk_batch(serial_gap=False):
    s3 = "4." if serial_gap else "3."
    return (page(1, JK_HEAD) +
            page(2, "1. WP(C) No.100/2024\n\n" + FILLER * 2 + "\n\nFor the foregoing reasons, we find no merit in this petition "
                 "and the same is, accordingly, dismissed.\n") +
            page(3, "2. WP(C) No.101/2024\n\n" + FILLER * 2 + "\n\nFor the foregoing reasons, we allow this petition and set aside "
                 "the impugned judgment passed by the AFT.\n") +
            page(4, s3 + " WP(C) No.102/2024\n\n" + FILLER * 2 + "\n\nFor the foregoing reasons, this petition is partly allowed.\n\n"
                 "(X)\nJudge\nJAMMU\n03.11.2025\n"))


class TestBatchSplitting(unittest.TestCase):
    def test_sections_get_their_own_outcome(self):
        rows = by_proc(run(jk_batch(), cn="WP(C)/101/2024"))
        self.assertEqual(rows["WP(C) 100/2024"]["printed_disposal"], "dismissed")
        self.assertEqual(rows["WP(C) 101/2024"]["printed_disposal"], "allowed")
        self.assertEqual(rows["WP(C) 101/2024"]["substantive_result"], "relief_granted")
        self.assertEqual(rows["WP(C) 102/2024"]["printed_disposal"], "partly_allowed")
        self.assertIn("BATCH_SECTIONS_3", rows["WP(C) 100/2024"]["flags"])

    def test_file_own_case_is_marked(self):
        rows = by_proc(run(jk_batch(), cn="WP(C)/101/2024"))
        self.assertEqual(rows["WP(C) 101/2024"]["file_case_role"], "OWN_CASE")
        self.assertEqual(rows["WP(C) 100/2024"]["file_case_role"], "CONNECTED_CASE")

    def test_own_case_not_in_text_gets_explicit_abstention(self):
        rows = by_proc(run(jk_batch(), cn="WP(C)/555/2024"))
        self.assertEqual(rows["WP(C) 555/2024"]["printed_disposal"], U)
        self.assertEqual(rows["WP(C) 555/2024"]["file_case_role"], "OWN_CASE")

    def test_serial_gap_abstains_for_the_section_before_the_gap(self):
        rows = by_proc(run(jk_batch(serial_gap=True)))
        self.assertEqual(rows["WP(C) 101/2024"]["printed_disposal"], U)
        self.assertIn("SERIAL_GAP", rows["WP(C) 101/2024"]["abstain_reason"])
        self.assertEqual(rows["WP(C) 100/2024"]["printed_disposal"], "dismissed")


SC_HEAD = """IN THE SUPREME COURT OF INDIA
CIVIL APPELLATE JURISDICTION
Civil Appeal No. 11 of 2020
From the Judgment and Order dated 01.01.2019 of the High Court of Delhi in W.P.(C) No. 999 of 2018
WITH
Civil Appeal No. 12 of 2020
Union of India ... Appellants
versus
X ... Respondents

J U D G M E N T

A. B. CDEF, J.
1. These appeals arise from the judgment of the High Court. %s
""" % FILLER


class TestMultiAppealMapping(unittest.TestCase):
    def test_numbered_dispositions_map_to_their_appeals(self):
        t = page(1, SC_HEAD) + page(2, "2. " + FILLER + "\n\n3. In the result, Civil Appeal No. 11 of 2020 is allowed and the "
                                    "impugned judgment is set aside. Civil Appeal No. 12 of 2020 is dismissed.\n\n"
                                    "...................J.\n(A. B. CDEF)\nNEW DELHI\nJANUARY 5, 2021\n")
        rows = by_proc(run(t))
        self.assertEqual(rows["CA 11/2020"]["printed_disposal"], "allowed")
        self.assertEqual(rows["CA 12/2020"]["printed_disposal"], "dismissed")
        self.assertNotIn("WP(C) 999/2018", rows)   # the impugned High Court number is not a host proceeding

    def test_generic_plural_disposition_expands_to_all_hosts(self):
        t = page(1, SC_HEAD) + page(2, "2. " + FILLER + "\n\n3. In the result, both the appeals are dismissed.\n\n"
                                    "...................J.\n(A. B. CDEF)\nNEW DELHI\nJANUARY 5, 2021\n")
        rows = by_proc(run(t))
        self.assertEqual(set(rows), {"CA 11/2020", "CA 12/2020"})
        self.assertTrue(all(r["printed_disposal"] == "dismissed" for r in rows.values()))


def hc_order(operative, num="CWP-101-2025"):
    return page(1, """IN THE HIGH COURT OF PUNJAB AND HARYANA AT CHANDIGARH
%s
Date of decision: 01.02.2026
A ....Petitioner
Versus
Union of India ....Respondents
CORAM: HON'BLE MR. JUSTICE P, JUDGE

P, J. (Oral)
1. %s
2. %s
(P)
JUDGE
01.02.2026
""" % (num, FILLER, operative))


class TestPartlyAllowed(unittest.TestCase):
    def test_partly_succeeds(self):
        r = run(hc_order("For the reasons recorded above, the appeal partly succeeds in the above terms."))[0]
        self.assertEqual(r["printed_disposal"], "partly_allowed")
        self.assertEqual(r["substantive_result"], "relief_partly_granted")

    def test_allowed_to_the_above_extent(self):
        r = run(hc_order("In view of the above, the writ petition is allowed to the above extent."))[0]
        self.assertEqual(r["printed_disposal"], "partly_allowed")
        self.assertIn("EXTENT_QUALIFIED", r["notes"])

    def test_extent_before_the_verb(self):
        r = run(hc_order("To the aforesaid extent, the present writ petition is allowed."))[0]
        self.assertEqual(r["printed_disposal"], "partly_allowed")

    def test_plain_allowed_stays_allowed(self):
        r = run(hc_order("In view of the above, the writ petition is allowed."))[0]
        self.assertEqual(r["printed_disposal"], "allowed")
        self.assertEqual(r["substantive_result"], "relief_granted")


class TestQuoteBoundary(unittest.TestCase):
    def test_court_sentence_after_closing_quote_is_own_voice(self):
        op = ("This Court in an earlier case held as under:-\n\n“ In view of the above, the writ petition is allowed. "
              "The respondents are directed to grant disability pension.”\n\nAccordingly, present petition is disposed of "
              "in terms of the aforesaid judgement. Petitioner shall also be entitled to the same relief.")
        r = run(hc_order(op))[0]
        self.assertEqual(r["printed_disposal"], "disposed_of_with_directions")
        self.assertEqual(r["substantive_result"], "relief_granted")
        self.assertIn("Accordingly, present petition is disposed of", r["excerpt"])

    def test_disposition_only_inside_quotation_abstains(self):
        op = ("The Supreme Court held as under:\n\n“In view of the above, the appeal is allowed and the order of the "
              "Tribunal is set aside, and the matter shall proceed in accordance with law.”")
        r = run(hc_order(op))[0]
        self.assertEqual(r["printed_disposal"], U)


DELHI = """IN THE HIGH COURT OF DELHI AT NEW DELHI
W.P.(C) 3433/2026 & CM APPL. 16497/2026
A ..... Petitioner
versus
UNION OF INDIA ..... Respondents
CORAM:
HON'BLE MR. JUSTICE Q
O R D E R
CM APPL. 16498/2026 (Exemption)
1. Exemption allowed, subject to all just exceptions.
2. The application stands disposed of.
W.P.(C) 3433/2026 & CM APPL. 16497/2026
3. %s
4. %s
Q, J
FEBRUARY 2, 2026
"""


class TestMiscApplicationExclusion(unittest.TestCase):
    def test_application_disposal_is_not_the_petition_outcome(self):
        r = run(page(1, DELHI % (FILLER, "There is no merit in the petition. The petition is dismissed. The pending "
                                          "applications are also disposed of as having become infructuous.")))
        r = by_proc(r)
        self.assertEqual(list(r), ["WP(C) 3433/2026"])
        self.assertEqual(r["WP(C) 3433/2026"]["printed_disposal"], "dismissed")

    def test_only_application_disposal_abstains(self):
        r = run(page(1, DELHI % (FILLER, "List on 05.03.2026. Pending application(s), if any, shall stand disposed of.")))
        self.assertNotIn(r[0]["printed_disposal"], ("disposed_of", "disposed_of_with_directions", "dismissed"))


class TestPrintedVersusSubstantive(unittest.TestCase):
    def test_disposed_of_with_set_aside_is_relief_granted(self):
        op = ("In view of the above, the impugned dismissal order dated 30.12.2021 is set aside. The petitioner shall be "
              "reinstated with consequential benefits. The writ petition is disposed of in above terms.")
        r = run(hc_order(op))[0]
        self.assertEqual(r["printed_disposal"], "disposed_of_with_directions")
        self.assertEqual(r["substantive_result"], "relief_granted")

    def test_disposed_of_on_withdrawal_is_no_adjudication(self):
        op = ("Learned counsel for the petitioner seeks leave to withdraw the present petition with liberty to approach "
              "the Armed Forces Tribunal. Leave as prayed for granted and the present petition is disposed of.")
        r = run(hc_order(op))[0]
        self.assertEqual(r["printed_disposal"], "disposed_of")
        self.assertEqual(r["substantive_result"], "no_adjudication")

    def test_remand_with_disposed_of(self):
        op = ("Accordingly, we dispose of this writ petition in the following terms: the impugned order passed by the AFT is "
              "set aside and the matter is remanded to the Tribunal for fresh decision in accordance with law.")
        r = run(hc_order(op))[0]
        self.assertIn(r["printed_disposal"], ("disposed_of_with_directions", "set_aside_and_remanded"))
        self.assertEqual(r["substantive_result"], "remanded_for_fresh_decision")

    def test_allowed_with_remand_keeps_printed_allowed(self):
        op = ("The matter is remanded back to the respondent for passing afresh reasoned and speaking order. The writ "
              "petition is, accordingly, allowed.")
        r = run(hc_order(op))[0]
        self.assertEqual(r["printed_disposal"], "allowed")
        self.assertEqual(r["substantive_result"], "remanded_for_fresh_decision")

    def test_withdrawn(self):
        r = run(hc_order("In view of the above, the present appeal is dismissed as withdrawn with liberty."))[0]
        self.assertEqual((r["printed_disposal"], r["substantive_result"]), ("dismissed_as_withdrawn", "no_adjudication"))

    def test_not_final(self):
        r = run(hc_order("Issue notice to the respondents. List on 12.03.2026."))[0]
        self.assertEqual((r["printed_disposal"], r["final_or_interim"]), ("not_final", "interim"))


class TestAbstention(unittest.TestCase):
    def test_no_disposition_abstains_with_reason(self):
        r = run(hc_order("Heard learned counsel for the parties at length on the question of limitation."))[0]
        self.assertEqual(r["printed_disposal"], U)
        self.assertEqual(r["substantive_result"], U)
        self.assertTrue(r["abstain_reason"])
        self.assertEqual(r["final_or_interim"], "")

    def test_carve_out_abstains(self):
        r = run(hc_order("Except to the extent indicated above, the writ petition is dismissed."))[0]
        self.assertEqual(r["printed_disposal"], U)

    def test_conflicting_generic_dispositions_abstain(self):
        r = run(hc_order("In view of the above, the writ petition is allowed. The writ petition is dismissed."))[0]
        self.assertEqual(r["printed_disposal"], U)

    def test_status_and_vocabulary(self):
        for r in run(jk_batch()):
            self.assertEqual(r["status"], v3core.STATUS)
            self.assertIn(r["printed_disposal"], v3core.PRINTED_VOCAB)
            self.assertIn(r["substantive_result"], v3core.SUBST_VOCAB)

    def test_no_text(self):
        r = run("", cn="CWP/1/2020")[0]
        self.assertEqual(r["printed_disposal"], U)
        self.assertEqual(r["proceeding"], "CWP 1/2020")


class TestNormalisation(unittest.TestCase):
    def test_canon_type(self):
        for raw, want in [("Civil Appeal Nos", "CA"), ("W.P.(C)", "WP(C)"), ("Criminal Appeal", "CRLA"), ("CWP", "CWP"),
                          ("Special Leave Petition (Civil)", "SLP(C)"), ("WRIT - A", "WRIT-A"), ("SPECIAL APPEAL", "SPLA"),
                          ("v. UNION OF INDIA (Writ Petition (Civil)", "WP(C)"), ("CrlA(S)", "CRLA(S)")]:
            self.assertEqual(v3core.canon_type(raw), want, raw)

    def test_no_word_is_not_a_case_type(self):
        cs = v3core.find_case_numbers("29.    WP(C) No. 1644/2024")
        self.assertEqual(len(cs), 1)
        self.assertEqual(cs[0]["ptype"], "wp")


class TestIdsFile(unittest.TestCase):
    def test_id_file_formats(self):
        import extract_v3
        d = tempfile.mkdtemp()
        cases = {"a.csv": "holdout_id,judgment_id,court\nH1,J-1,x\nH2,J-2,y\n", "b.txt": "# list\nJ-1\n\nJ-2\n",
                 "c.csv": "judgment_id\nJ-1\nJ-2\n", "d.csv": "\"J-1\",z\n\"J-2\",w\n"}
        for fn, body in cases.items():
            p = os.path.join(d, fn)
            with open(p, "w", encoding="utf-8") as f:
                f.write(body)
            self.assertEqual(extract_v3.read_ids(p), ["J-1", "J-2"], fn)


class TestBlindingAndSyntax(unittest.TestCase):
    def test_tools_never_reference_the_v3_holdout(self):
        for fn in os.listdir(TOOLS):
            if fn.endswith(".py"):
                with open(os.path.join(TOOLS, fn), encoding="utf-8") as f:
                    self.assertNotIn("holdout_v3", f.read(), fn)

    def test_tools_compile_under_this_interpreter(self):
        import py_compile
        for fn in ("v3core.py", "extract_v3.py", "eval_dev_v3.py", "build_dev_gold_v3.py"):
            py_compile.compile(os.path.join(TOOLS, fn), cfile=os.path.join(tempfile.mkdtemp(), "x.pyc"), doraise=True)


def _have_repo():
    if not os.path.isdir(REPO):
        return False
    try:
        subprocess.run(["git", "-C", REPO, "cat-file", "-t", "ad77758d"], check=True, capture_output=True)
        return True
    except Exception:
        return False


@unittest.skipUnless(_have_repo(), "c7 repository at commit ad77758d not available")
class TestRealText(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import extract_v3
        cls.E = extract_v3
        cls.J, _ = extract_v3.load_inputs()
        cls.store = extract_v3.TextStore()

    @classmethod
    def tearDownClass(cls):
        cls.store.close()

    def rows(self, jid):
        return by_proc(self.E.process_one(self.J[jid], self.store))

    def test_jk_batch_copy_maps_own_petition(self):
        # C11 holdout H042 (spent; development data): the copy stored for WP(C) 1279/2024
        r = self.rows("J-a09b2abfee8c4b21")
        self.assertEqual(r["WP(C) 1279/2024"]["file_case_role"], "OWN_CASE")
        self.assertEqual(r["WP(C) 1279/2024"]["printed_disposal"], "dismissed")
        self.assertEqual(r["WP(C) 1319/2024"]["printed_disposal"], "allowed")
        self.assertEqual(r["WP(C) 1653/2024"]["printed_disposal"], "partly_allowed")
        self.assertEqual(r["WP(C) 2301/2024"]["printed_disposal"], U)        # no disposal word printed
        self.assertEqual(r["WP(C) 2301/2024"]["substantive_result"], "relief_granted")

    def test_sc_partly_succeeds(self):
        r = self.rows("J-d29ce9d4b7627755")      # C11 H011
        self.assertEqual(r["CRLA 967/2017"]["printed_disposal"], "partly_allowed")

    def test_sc_limited_extent_and_listing(self):
        r = self.rows("J-81a996f5fc5a3566")      # C11 H012
        self.assertEqual(r["CA 20858/2017"]["printed_disposal"], "partly_allowed")
        self.assertNotEqual(r["SLP(C) 16441/2017"]["printed_disposal"], "partly_allowed")

    def test_quote_overrun_fixed(self):
        r = self.rows("J-edd9b3e010b4678e")      # C11 H034
        self.assertEqual(r["CWP 13553/2009"]["substantive_result"], "relief_granted")
        self.assertEqual(list(r), ["CWP 13553/2009"])   # numbers quoted from an earlier judgment are not hosts

    def test_deterministic(self):
        a = self.E.outcomes_csv(self.E.process_one(self.J["J-a09b2abfee8c4b21"], self.store))
        b = self.E.outcomes_csv(self.E.process_one(self.J["J-a09b2abfee8c4b21"], self.store))
        self.assertEqual(a, b)

    def test_ids_command(self):
        out = tempfile.mkdtemp()
        idf = os.path.join(out, "ids.csv")
        with open(idf, "w") as f:
            f.write("judgment_id,other\nJ-d29ce9d4b7627755,x\nJ-doesnotexist,y\n")
        subprocess.run([sys.executable, "-I", "-B", os.path.join(TOOLS, "extract_v3.py"), "ids", "--ids-file", idf,
                        "--out", out], check=True, capture_output=True)
        with open(os.path.join(out, "OUTCOMES_V3.csv"), encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(rows[0]["judgment_id"], "J-d29ce9d4b7627755")
        self.assertEqual(rows[-1]["abstain_reason"], "UNKNOWN_JUDGMENT_ID")


if __name__ == "__main__":
    unittest.main()
