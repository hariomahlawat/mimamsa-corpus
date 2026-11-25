"""C13-A5 passage-level treatment rules: synthetic passages for the guard rails, plus build bookkeeping and --check."""
import importlib.util
import sys as _sys
_sys.dont_write_bytecode = True  # keep tools/ free of __pycache__
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

PKG = Path(__file__).resolve().parents[1] / "legal_knowledge" / "audit_work" / "C13-A5-GRAPH"
_spec = importlib.util.spec_from_file_location("treatment_c13", PKG / "tools" / "treatment_c13.py")
T = importlib.util.module_from_spec(_spec)
sys.path.insert(0, str(PKG / "tools"))
_spec.loader.exec_module(T)

CIT = "(1998) 2 SCC 580"
SC = "Supreme Court of India"
HC = "High Court of Delhi"


def run(sentence, court=SC, opinion="SOLE_OPINION", lead="12. We have considered the matter. "):
    text = "[[page 1]] " + lead + sentence + " 13. Nothing further."
    s = text.index(CIT) if CIT in text else text.index("X v. Y")
    return T.classify(text, court, s, s + len(CIT), opinion, "BODY", SC)


class Rules(unittest.TestCase):
    def test_explicit_overruling_by_supreme_court(self):
        r = run("The decision in X v. Y, %s is hereby overruled." % CIT)
        self.assertEqual(r["relation"], "OVERRULES")
        self.assertEqual(r["overruling_language"], "EXPLICIT")

    def test_declaratory_wording_is_disapproves_not_overrules(self):
        r = run("The judgment in X v. Y, %s does not lay down the correct law." % CIT)
        self.assertEqual(r["relation"], "DISAPPROVES")

    def test_criticism_or_distinguishing_never_overrules(self):
        for s in ("The decision in X v. Y, %s is clearly distinguishable on facts." % CIT,
                  "We are unable to agree with the reasoning in X v. Y, %s." % CIT):
            self.assertNotEqual(run(s)["relation"], "OVERRULES", s)

    def test_high_court_overruling_words_not_routed(self):
        r = run("The decision in X v. Y, %s is overruled." % CIT, court=HC)
        self.assertEqual(r["relation"], "CITES")

    def test_separate_opinion_no_proposal(self):
        r = run("The decision in X v. Y, %s is overruled." % CIT, opinion="SEPARATE_OPINION")
        self.assertEqual(r["relation"], "CITES")

    def test_plea_or_objection_overruled_is_not_treatment(self):
        r = run("In X v. Y, %s the court said that if the objection regarding such plea is overruled, the trial proceeds." % CIT)
        self.assertNotEqual(r["relation"], "OVERRULES")

    def test_interrogative_is_not_treatment(self):
        r = run("Would the decision in X v. Y, %s stand overruled by a later decision?" % CIT)
        self.assertEqual(r["relation"], "CITES")

    def test_quotation_after_held_thus(self):
        r = run("In X v. Y, %s is overruled." % CIT, lead="12. In Triveniben this Court held thus: Therefore the decision ")
        self.assertEqual(r["relation"], "CITES")

    def test_submission_is_not_court_voice(self):
        r = run("Learned counsel submitted that the case is squarely covered by X v. Y, %s." % CIT)
        self.assertEqual(r["voice"], "PARTY_SUBMISSION")

    def test_follows_in_court_voice(self):
        r = run("The issue is squarely covered by X v. Y, %s and we follow it." % CIT)
        self.assertEqual(r["relation"], "FOLLOWS")


class ReviewFixes(unittest.TestCase):
    """Review f915ac11 F02 (voice) and F03 (binding/subject) regressions, on synthetic passages."""

    def test_quotation_opened_paragraphs_earlier(self):
        lead = "12. The Supreme Court observed: \u201c5. Earlier facts are recited here. 6. More recital follows here. "
        r = run("The matter is squarely covered by X v. Y, %s." % CIT, lead=lead)
        self.assertEqual(r["voice"], "QUOTED_PASSAGE")

    def test_reproduction_lead_in(self):
        r = run("The case is covered by X v. Y, %s." % CIT, lead="12. The relevant paragraph is reproduced hereinbelow: 34. ")
        self.assertEqual(r["voice"], "QUOTED_PASSAGE")

    def test_party_contention_with_wherein_it_was_held(self):
        r = run("Before the AFT, the petitioner primarily contented that the order was contrary to X v. Y, %s, wherein it was held "
                "that the disease is presumed to be due to service." % CIT, court=HC)
        self.assertEqual(r["voice"], "PARTY_SUBMISSION")

    def test_high_court_this_court_with_supreme_court_report_is_quoted(self):
        r = run("In X v. Y, %s, this Court considered the scope of judicial review." % CIT, court=HC)
        self.assertEqual(r["relation"], "CITES")

    def test_footnote_marker_binds_to_its_own_footnote(self):
        text = ("[[page 1]] 2. The issue is covered by a recent decision in UOI v Madso4. 1 \u201cthe AFT\u201d, hereinafter "
                "3 (2013) 7 SCC 316 4 2025 SCC OnLine Del 2018 3. Next.")
        wrong = text.index("(2013) 7 SCC 316")
        right = text.index("2025 SCC OnLine Del 2018")
        r1 = T.classify(text, HC, wrong, wrong + 16, "OPINION_NOT_IDENTIFIED", "BODY", SC)
        r2 = T.classify(text, HC, right, right + 24, "OPINION_NOT_IDENTIFIED", "BODY", SC)
        self.assertEqual(r1["relation"], "CITES")
        self.assertEqual(r2["relation"], "FOLLOWS")

    def test_reported_distinguishing_in_a_list(self):
        r = run("In X v. Y, %s, the earlier view was distinguished." % CIT)
        self.assertEqual(r["relation"], "CITES")

    def test_statutory_subject_is_not_distinguishing(self):
        r = run("In view of X v. Y, %s, Article 323A does not apply to the Tribunal." % CIT, court=HC)
        self.assertNotEqual(r["relation"], "DISTINGUISHES")

    def test_explained_in_authority_is_considers_not_explains(self):
        r = run("The principles of judicial review have been explained in X v. Y, %s." % CIT)
        self.assertEqual(r["relation"], "CONSIDERS")

    def test_is_followed_by_is_not_follows(self):
        r = run("Plaque rupture is followed by thrombus, as noted in X v. Y, %s." % CIT)
        self.assertNotEqual(r["relation"], "FOLLOWS")

    def test_elision_marker_signals_quotation(self):
        r = run("X v. Y, %s itself is per incuriam." % CIT, lead="98. Earlier text. xx xx xx 99. However, the \u201carbitrariness\u201d test. ")
        self.assertEqual(r["voice"], "QUOTED_PASSAGE")

    def test_raw_target_fragment_cleaned(self):
        self.assertEqual(T.clean_raw_target("isposed of in the following terms"), "\u2026 of in the following terms")
        self.assertEqual(T.clean_raw_target("MP Sharma"), "MP Sharma")


class Build(unittest.TestCase):
    def test_summary_bookkeeping(self):
        s = json.loads((PKG / "treatment" / "TREATMENT_SUMMARY_C13.json").read_text())
        self.assertFalse(s["frozen"])
        self.assertFalse(s["a0_passages_read"])
        self.assertEqual(s["a0_holdout"]["id_columns_read"], ["rep_doc_id", "rep_sha256", "page"])
        self.assertEqual(s["dev_eval_in_sample"]["excluded_rows_in_a0_holdout"], 0)
        self.assertIn("IN-SAMPLE", s["dev_eval_in_sample"]["note"])

    @unittest.skipIf(os.environ.get("C13_SKIP_SLOW"), "slow --check skipped")
    def test_tools_reproduce(self):
        py = sys.executable
        for tool in ("scnum_reconfirm_c13.py", "identity_c13.py", "graph_c13.py", "review_recheck_c13.py",
                     "contract_v1_export_c13.py", "package_c13.py"):
            r = subprocess.run([py, "-I", "-B", str(PKG / "tools" / tool), "--check"], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, tool + r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
