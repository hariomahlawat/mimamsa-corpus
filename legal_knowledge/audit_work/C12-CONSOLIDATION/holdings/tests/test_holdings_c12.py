"""Tests for the C12 holdings extractor. Run: python3.11 -I -B -m unittest discover -s tests (from holdings/)."""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.join(os.path.dirname(HERE), "tools")
sys.path.insert(0, TOOLS)
import holdings_core as core  # noqa: E402
import holdings_c12 as drv  # noqa: E402

SCR = """[[page 1]]
A

B

ROHIT KUMAR
v.
UNION OF INDIA & ORS.
(Civil Appeal No. 12 of 2019)
JULY 08, 2019
[A. B. SHARMA AND C. D. VERMA, JJ.]

Army Act, 1950 - s.120 - Summary Court Martial - Held: the convening of an SCM
without grave reason for immediate action is contrary to law.

HELD: 1. The power to convene an SCM is a drastic power which must be exercised rarely.

CIVIL APPELLATE JURISDICTION : Civil Appeal No. 12 of 2019

X. Y. Kumar, Adv. for the Appellant.

P. Q. Rao, ASG, Advs. for the Respondents.

[[page 2]]
926
SUPREME COURT REPORTS
[2019] 9 S.C.R.

The Judgment of the Court was delivered by

A. B. SHARMA, J.

1. This appeal arises from a judgment of the Armed Forces Tribunal dated 7 December 2015. The appellant was enrolled on 29 October 1996 and was posted as a Lance Naik.

2. Learned counsel for the appellant submitted that the convening of the Summary Court Martial was contrary to Section 120 of the Army Act, 1950. It was urged that there was no grave reason for immediate action.

3. The question which arises for our consideration is whether a Summary Court Martial may be convened nine months after the incident.

4. In Union of India v. Vishav Priya Singh, this Court observed as follows:
"The power to order a Summary Court Martial is a drastic power vested in one single individual, namely the Commanding Officer, and it must therefore be exercised only where it is absolutely imperative that immediate action is taken in the interests of discipline."

[[page 3]]
927
SUPREME COURT REPORTS
[2019] 9 S.C.R.

5. We have considered the rival submissions. In our view, the power to order a Summary Court Martial is a drastic power which must be exercised only when immediate action is necessary. We hold that the convening of the Summary Court Martial nine months after the incident was contrary to law and cannot be sustained.

6. Before parting, we may observe that the authorities would do well to record reasons whenever a Summary Court Martial is convened.

7. We accordingly allow the appeal and set aside the impugned order of the Armed Forces Tribunal. No costs.
"""


def analyze(text, court="Supreme Court of India"):
    return core.analyze(text, {"judgment_id": "J-test", "sha256": "0" * 64, "court": court, "text_doc": "doc"})


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.summary, self.items = analyze(SCR)

    def by_type(self, t):
        return [i for i in self.items if i["item_type"] == t]

    def test_headnote_excluded(self):
        self.assertTrue(self.summary["headnote_detected"])
        self.assertEqual(self.summary["body_start_method"], "DELIVERED_BY")
        start = SCR.index("The Judgment of the Court was delivered by")
        for it in self.items:
            self.assertGreater(it["char_start"], start, it["excerpt"])
        self.assertFalse(any("HELD:" in i["excerpt"] for i in self.items))

    def test_holding_found_with_anchors(self):
        hs = self.by_type("holding")
        self.assertTrue(any("We hold that the convening" in h["excerpt"] for h in hs), [h["excerpt"] for h in hs])
        h = next(h for h in hs if "We hold that" in h["excerpt"])
        self.assertEqual(h["page"], 3)
        self.assertEqual(h["paragraph"], 5)
        self.assertEqual(h["opinion"], "sole")
        self.assertEqual(h["opinion_author"], "A. B. SHARMA")

    def test_excerpt_verbatim_at_offsets(self):
        for it in self.items:
            self.assertEqual(it["excerpt"], core.squash(SCR[it["char_start"]:it["char_end"]], core.EXCERPT_CAP))
            self.assertEqual(it["page"], core.page_at(core.page_index(SCR), it["char_start"]))

    def test_question_of_law(self):
        qs = self.by_type("question_of_law")
        self.assertEqual(len(qs), 1)
        self.assertTrue(qs[0]["legal_issue"].lower().startswith("whether a summary court martial"))

    def test_submission_not_holding(self):
        sub = [i for i in self.items if "Learned counsel for the appellant submitted" in i["excerpt"]]
        self.assertTrue(sub)
        self.assertTrue(all(i["item_type"] == "submission" for i in sub))
        urged = [i for i in self.items if "It was urged" in i["excerpt"]]
        self.assertTrue(all(i["item_type"] == "submission" for i in urged))

    def test_quoted_precedent(self):
        q = [i for i in self.items if "single individual" in i["excerpt"]]
        self.assertTrue(q)
        self.assertTrue(all(i["item_type"] == "quoted_precedent" for i in q))
        self.assertTrue(all(i["voice"] == "quoted_precedent" for i in q))

    def test_obiter_and_operative(self):
        self.assertTrue(any("Before parting" in i["excerpt"] for i in self.by_type("obiter_candidate")))
        self.assertTrue(any("allow the appeal" in i["excerpt"] for i in self.by_type("operative_direction")))

    def test_answer_linked_to_question(self):
        h = next(h for h in self.by_type("holding") if "We hold that" in h["excerpt"])
        q = self.by_type("question_of_law")[0]
        self.assertEqual(h["answers_question"], q["item_id"])

    def test_status_never_verified(self):
        for it in self.items:
            self.assertEqual(it["status"], "AUTOMATED_CANDIDATE_NOT_VERIFIED")
            self.assertEqual(it["verification"], "NOT_VERIFIED_RATIO_NOT_DETERMINED")
            self.assertIn(it["item_type"], core.ITEM_TYPES)
            self.assertNotIn("VERIFIED_RATIO", json.dumps(it).replace("NOT_VERIFIED_RATIO", ""))

    def test_deterministic(self):
        s2, items2 = analyze(SCR)
        self.assertEqual(json.dumps(self.items, sort_keys=True), json.dumps(items2, sort_keys=True))

    def test_statute_refs(self):
        refs = core.statute_refs("This is contrary to Section 120 of the Army Act, 1950 and Article 14.")
        keys = set((r["instrument_id"], r["provision"]) for r in refs)
        self.assertIn(("AA-1950", "s.120"), keys)
        self.assertIn(("COI", "art.14"), keys)
        refs = core.statute_refs("Rule 14 of the Army Rules, 1954 is not ultra vires.")
        self.assertIn(("AR-1954", "r.14"), set((r["instrument_id"], r["provision"]) for r in refs))


class OpinionTests(unittest.TestCase):
    def test_dissent_and_separate(self):
        body = ("\n\nThe following Judgments were delivered:\n\nSHARMA, J.-The appellant challenges the order. " + ("We find that the order is valid in law. " * 60) +
                "\n\nVERMA, J.-I have had the advantage of reading the judgment of my learned brother and I agree. " + ("I hold that the order is valid. " * 60) +
                "\n\nRAO, J.-I regret I am unable to agree with my learned brethren. " + ("In my opinion the order is void. " * 60))
        text = "[[page 1]]\nX v. Y\n" + body
        s, items = analyze(text, court="Supreme Court of India")
        labels = s["opinions"].split(";")
        self.assertEqual(len(labels), 3, labels)
        self.assertTrue(labels[0].startswith("lead:SHARMA"))
        self.assertTrue(labels[1].startswith("separate:VERMA"))
        self.assertTrue(labels[2].startswith("dissent:RAO"))
        diss = [i for i in items if i["opinion"] == "dissent"]
        self.assertTrue(diss)
        self.assertTrue(all(i["opinion_note"].startswith("NOT_THE_COURT") for i in diss))


class DriverTests(unittest.TestCase):
    def test_attach_carries_treatment_unchanged(self):
        s, items = analyze(SCR)
        h = next(i for i in items if "We hold that" in i["excerpt"])
        tc = {"candidate_id": "TC-1", "edge_id": "E-1", "cue_relation": "FOLLOWS", "proposed_relation": "", "cue_text": "followed",
              "cited_string": "x", "target_doc_ids": "", "target_title": "", "status": "LEGAL_INTERPRETATION_ADVISER_REVIEW",
              "binding_status": "", "attribution": "COURT_OWN_VOICE", "cue_page": "3", "citation_page": "3",
              "excerpt": "We hold that the convening of the Summary Court Martial nine months after the incident was contrary to law"}
        link = {"link_id": "SL-1", "instrument_id": "AA-1950", "provision_id": "AA-1950:s.120", "relationship": "STATUTE_MENTIONED",
                "status": "AUTOMATED_DETECTED", "version_status": "", "page": "2", "pages": "2;3", "excerpt": "unrelated text " * 5}
        drv.attach(items, [link], [tc])
        self.assertEqual(len(h["treatment"]), 1)
        self.assertIsNone(h["treatment"][0]["proposed_relation"])
        self.assertEqual(h["treatment"][0]["relation_status"], "LEGAL_INTERPRETATION_ADVISER_REVIEW")
        self.assertIn("no overruling inferred", h["treatment"][0]["policy"])
        sub = next(i for i in items if "contrary to Section 120" in i["excerpt"])
        self.assertEqual([x["link_id"] for x in sub["statute_links"]], ["SL-1"])
        self.assertEqual(sub["statute_links"][0]["match_basis"], "PROVISION_IN_SENTENCE_AND_MENTIONED_ON_SAME_PAGE")

    def test_no_overruling_vocabulary_invented(self):
        with open(os.path.join(TOOLS, "holdings_core.py"), encoding="utf-8") as f:
            src = f.read()
        self.assertNotIn('"overruled_by"', src)
        self.assertNotIn("OVERRULES", src)


@unittest.skipUnless(os.path.exists(os.path.join(drv.DEF_REPO, ".git")),
                     "c7 repository not available")
class IntegrationTests(unittest.TestCase):
    IDS = ["J-14e2d11aa4b88fe0", "J-35b9c948fe6254c6", "J-NOT-A-JUDGMENT"]

    def run_ids(self, d):
        idf = os.path.join(d, "ids.txt")
        with open(idf, "w") as f:
            f.write("# test\n" + "\n".join(self.IDS) + "\n")
        out = os.path.join(d, "out")
        r = subprocess.run([sys.executable, "-I", "-B", os.path.join(TOOLS, "holdings_c12.py"), "ids", "--ids-file", idf, "--out-dir", out],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(os.path.join(out, "HOLDINGS_C12.jsonl"), "rb") as f:
            a = f.read()
        with open(os.path.join(out, "HOLDINGS_C12_JUDGMENTS.csv"), "rb") as f:
            b = f.read()
        return a, b

    def test_ids_deterministic_and_unknown_id_reported(self):
        with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
            a1, b1 = self.run_ids(d1)
            a2, b2 = self.run_ids(d2)
        self.assertEqual(hashlib.sha256(a1).hexdigest(), hashlib.sha256(a2).hexdigest())
        self.assertEqual(b1, b2)
        self.assertIn(b"UNKNOWN_JUDGMENT_ID", b1)
        rows = [json.loads(x) for x in a1.decode().splitlines()]
        self.assertTrue(any(r["item_type"] == "holding" and r["judgment_id"] == "J-14e2d11aa4b88fe0" for r in rows))

    def test_frozen_tool_hashes_match(self):
        fz = os.path.join(os.path.dirname(HERE), "outputs", "FREEZE.json")
        if not os.path.exists(fz):
            self.skipTest("not frozen yet")
        with open(fz) as f:
            frozen = json.load(f)
        self.assertEqual(frozen["tool_sha256"], drv.tool_hashes())
        self.assertEqual(frozen["extractor"], core.VERSION)


if __name__ == "__main__":
    unittest.main()
