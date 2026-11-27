"""C13-A3 holdings redesign: hierarchical segmentation (opinions, voice, quotations) on synthetic judgments."""
import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "legal_knowledge" / "audit_work" / "C13-A3-HOLDINGS" / "tools"
sys.path.insert(0, str(TOOLS))
import c13_segment as sg  # noqa: E402

FILLER = ("The appellant was enrolled in the Army on 12.03.1990 and served in various units thereafter. "
          "He was posted to the unit at Jammu where the incident took place. ") * 12


def page(n, body):
    return "[[page %d]]\n%s\n\n" % (n, body)


def two_opinions_dissent_at_end():
    lead = ("JUDGMENT\n\nMOHAPATRA, J. Leave granted. These appeals arise from the judgment of the High Court.\n\n"
            + FILLER + "\n\nWe hold that the re-engagement was valid and binding on the respondent. "
            "The appeals are accordingly allowed.\n\n")
    dis = ("RUMA PAL, J. I have read the draft judgment prepared by my learned Brother. "
           + FILLER + "\n\nI would, for all these reasons, dismiss the appeals. I regret that I am differing with the views "
           "expressed by my learned Brothers.\n")
    return page(1, "UNION OF INDIA v. R.P. YADAV\n\n" + lead) + page(2, FILLER) + page(3, dis) + page(4, FILLER + "\nThe end.")


def split_verdict_escr():
    a = "Judgment / Order of the Supreme Court\n\nJudgment\n\nSanjay Karol J.\n\n" + FILLER + "\nThe approval is upheld.\n\n"
    b = "Judgment\n\nNagarathna, J.\n\n" + FILLER + "\nThe approval is set aside.\n\n"
    c = ("In view of the divergent opinions, the Registry shall place the matter before Hon'ble the Chief Justice of India "
         "for constituting an appropriate Bench. We direct accordingly.\n")
    return page(1, a) + page(2, FILLER) + page(3, b) + page(4, FILLER + "\n\n" + FILLER + "\n\n" + c)


class OpinionSegmentation(unittest.TestCase):
    def test_dissent_cue_at_opening_and_end(self):
        seg = sg.segment(two_opinions_dissent_at_end(), {"court": "Supreme Court of India"})
        roles = [o["role"] for o in seg["opinions"]]
        self.assertEqual(roles, ["lead_majority", "dissent"])
        self.assertIn("RUMA PAL", seg["opinions"][1]["author"])
        self.assertEqual(sg.court_status("dissent"), "DISSENT_NOT_THE_COURT")

    def test_split_verdict_with_reference_to_chief_justice(self):
        seg = sg.segment(split_verdict_escr(), {"court": "Supreme Court of India"})
        roles = [o["role"] for o in seg["opinions"]]
        self.assertEqual(roles[:2], ["split_opinion", "split_opinion"])
        self.assertEqual(roles[-1], "court_order")
        self.assertIn("KAROL", seg["opinions"][0]["author"])
        self.assertIn("NAGARATHNA", seg["opinions"][1]["author"])

    def test_single_opinion_is_sole(self):
        text = page(1, "JUDGMENT\n\nSIKRI, J. Leave granted.\n\n" + FILLER + "\nWe hold that the Tribunal had jurisdiction.\n")
        seg = sg.segment(text, {"court": "Supreme Court of India"})
        self.assertEqual([o["role"] for o in seg["opinions"]], ["sole"])

    def test_same_judge_ocr_variants(self):
        self.assertTrue(sg.same_judge("S.R. P ANDIAN", "S. RATNAVEL PANDIAN"))
        self.assertTrue(sg.same_judge("JAGDISH SINGH KL-JEHAR", "JAGDISH SINGH KHEHAR"))
        self.assertFalse(sg.same_judge("KURIAN", "ADARSH KUMAR GOEL"))


class Voice(unittest.TestCase):
    def v(self, s, prev=None, case=False, sect=""):
        return sg.classify_voice(s, None, prev, case, sect)[0]

    def test_precedent_question_forms_are_not_court_voice(self):
        for s in ["In Ex. Sapper Mohinder Singh v. Union of India, the issue for consideration before this Court was whether the summary court martial was valid.",
                  "There the question was whether the Tribunal could grant relief.",
                  "The question before this court was whether the pension could be withheld."]:
            self.assertEqual(self.v(s, case=True), "precedent_report", s)

    def test_court_rejection_of_submission_is_court_voice(self):
        self.assertEqual(self.v("This submission is clearly misconceived.", prev="submission"), "court")

    def test_submission_carry_over_until_pivot(self):
        self.assertEqual(self.v("It was submitted that the delay was fatal to the claim."), "submission")
        self.assertEqual(self.v("The appellant had served for nine years.", prev="submission"), "submission")
        self.assertEqual(self.v("We are unable to accept the contention.", prev="submission"), "court")

    def test_past_tense_report_after_case_citation(self):
        self.assertEqual(self.v("This Court held that the onus lies on the employer.", case=True), "precedent_report")


class QuotedBlocks(unittest.TestCase):
    def test_quote_source_attribution(self):
        intro = "In Union of India v. Rajbir Singh, this Court observed as under:\n"
        quote = "“" + ("The disability is attributable to military service unless the contrary is shown. " * 4) + "”"
        text = page(1, "JUDGMENT\n\nTHAKUR, J. Leave granted.\n\n" + FILLER + "\n\n" + intro + quote + "\n\nWe agree with the said view.\n")
        seg = sg.segment(text, {"court": "Supreme Court of India"})
        qs = [q for q in seg["quotes"] if q["kind"] == "precedent"]
        self.assertTrue(qs)
        self.assertIn("Rajbir Singh", qs[0]["source"] or "")
        inside = [r for r in seg["recs"] if r["voice"].startswith("quotation:")]
        self.assertTrue(inside)
        self.assertTrue(all(r["quote_kind"] == "precedent" for r in inside))


if __name__ == "__main__":
    unittest.main()
