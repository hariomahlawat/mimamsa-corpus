"""Tests for the C11 v2 outcome / proposition extractor, on synthetic texts (plus one optional integration check).

Run:  python3.11 -m unittest discover -s tests -v      (from the extraction/ folder)
Standard library only; PyMuPDF is not used anywhere.
"""
import json
import os
import shutil
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "tools"))
import v2core  # noqa: E402

FILLER = ("The petitioner was enrolled in the Army and served for a number of years before the events which gave rise to "
          "this litigation. The respondents filed a counter affidavit and the record was produced before us. ")
META = {"judgment_id": "J-test", "sha256": "0" * 64, "doc_ids": ["hc-test"], "case_numbers_meta": "W.P.(C)/100/2020",
        "court": "High Court of Delhi"}


def head(case="W.P.(C) 100/2020"):
    return ("[[page 1]]\nIN THE HIGH COURT OF DELHI AT NEW DELHI\n%s\nRAM SINGH ..... Petitioner\nversus\n"
            "UNION OF INDIA ..... Respondents\nCORAM:\nHON'BLE MR. JUSTICE A\nJUDGMENT\nA, J.\n" % case)


def sign():
    return "\n(A)\nJUDGE\n(B)\nJUDGE\nJANUARY 5, 2026\n"


def outcomes(text, meta=META):
    rows, props, _ = v2core.analyze(text, meta)
    return [(r["proceeding"], r["outcome"], r["abstain_reason"]) for r in rows], rows, props


class Reproducibility(unittest.TestCase):
    def test_same_input_same_output(self):
        t = head() + "1. " + FILLER * 3 + "\n2. Accordingly, the writ petition is dismissed.\n" + sign()
        a = v2core.analyze(t, META)
        b = v2core.analyze(t, META)
        self.assertEqual(json.dumps(a[:2], sort_keys=True), json.dumps(b[:2], sort_keys=True))
        self.assertEqual(a[0][0]["outcome"], "dismissed")

    def test_offsets_point_into_source(self):
        t = head() + "1. " + FILLER * 2 + "\n2. Accordingly, the writ petition is dismissed.\n" + sign()
        _, rows, props = outcomes(t)
        r = rows[0]
        self.assertIn("dismissed", t[int(r["char_start"]):int(r["char_end"])])
        for p in props:
            self.assertEqual(" ".join(t[p["char_start"]:p["char_end"]].split())[:50], p["excerpt"][:50])


class Abstain(unittest.TestCase):
    def test_empty_text(self):
        o, _, _ = outcomes("")
        self.assertEqual(o[0][1], v2core.UNVERIFIED)
        self.assertEqual(o[0][2], "NO_TEXT_LAYER_OR_TOO_SHORT")

    def test_no_operative_cue_in_long_judgment(self):
        body = "".join("%d. %s\n" % (i, FILLER * 2) for i in range(1, 30))
        t = head() + body + "30. " + FILLER * 8 + "\n" + sign()
        o, _, _ = outcomes(t)
        self.assertEqual(o[0][1], v2core.UNVERIFIED)

    def test_conflicting_dispositions_without_mapping(self):
        t = head() + "1. " + FILLER + "\n2. Accordingly, the appeal is allowed. The appeal is dismissed.\n" + sign()
        o, _, _ = outcomes(t)
        self.assertEqual(o[0][1], v2core.UNVERIFIED)
        self.assertIn("CONFLICTING", o[0][2])

    def test_extent_qualified_allowance_abstains(self):
        t = head() + "1. " + FILLER + "\n2. Accordingly, the writ petition is allowed to the extent indicated above.\n" + sign()
        o, _, _ = outcomes(t)
        self.assertEqual(o[0][1], v2core.UNVERIFIED)

    def test_no_label_is_ever_verified(self):
        t = head() + "1. " + FILLER + "\n2. We hold that the Tribunal had jurisdiction under the Armed Forces Tribunal Act. " \
            "Accordingly, the writ petition is dismissed.\n" + sign()
        _, rows, props = outcomes(t)
        for p in props:
            self.assertEqual(p["status"], "AUTOMATED_CANDIDATE_NOT_VERIFIED")
            self.assertNotIn("VERIFIED_HOLDING", json.dumps(p))
            self.assertIn(p["origin"], v2core.ORIGINS)


class MiscApplication(unittest.TestCase):
    def test_pending_applications_not_main_outcome(self):
        t = head() + "1. " + FILLER + "\n2. Accordingly, the writ petition is dismissed.\n" \
            "3. All pending misc. applications also stand disposed of.\n" + sign()
        o, _, _ = outcomes(t)
        self.assertEqual(o, [(o[0][0], "dismissed", "")])

    def test_only_misc_disposal_abstains(self):
        t = head() + "1. " + FILLER + "\n2. Pending application(s), if any, shall also stand disposed of.\n" + sign()
        o, _, _ = outcomes(t)
        self.assertEqual(o[0][1], v2core.UNVERIFIED)
        self.assertEqual(o[0][2], "ONLY_MISC_APPLICATION_DISPOSAL_FOUND")

    def test_delhi_style_exemption_heading(self):
        t = head() + "CM APPL. 55/2020 (exemption)\n1. Allowed, subject to all just exceptions.\nW.P.(C) 100/2020\n" \
            "2. " + FILLER + "\n3. The petition is dismissed as withdrawn.\n" + sign()
        o, _, _ = outcomes(t)
        self.assertEqual(o[0][1], "dismissed_as_withdrawn")


class QuotedBlocks(unittest.TestCase):
    def test_quoted_precedent_disposal_ignored(self):
        t = head() + "1. " + FILLER + "\n2. In Ram Lal v. Union of India, (2001) 3 SCC 1, this Court held as under:\n" \
            "“15. The court martial under the Army Act was not properly convened. For the reasons recorded above, " \
            "the appeal is allowed and the order of the Tribunal is set aside.”\n" \
            "3. In view of the above, the writ petition is dismissed.\n" + sign()
        o, rows, props = outcomes(t)
        self.assertEqual(o[0][1], "dismissed")
        quoted = [p for p in props if "convened" in p["excerpt"]]
        self.assertTrue(quoted and quoted[0]["origin"] == "QUOTED_PRECEDENT", props)
        self.assertIn("Ram Lal v. Union of India", quoted[0]["attributed_to"])

    def test_only_quoted_disposal_abstains(self):
        t = head() + "1. " + FILLER + "\n2. Accordingly, we notice what the Tribunal recorded:\n" \
            "“The Original Application is accordingly allowed.”\n" + sign()
        o, _, _ = outcomes(t)
        self.assertEqual(o[0][1], v2core.UNVERIFIED)

    def test_unmarked_intro_block_excluded(self):
        t = head() + "1. " + FILLER + "\n2. The Supreme Court in Sham Lal v. State, (1999) 2 SCC 5, held as under:-\n" \
            "8. The appeal is accordingly allowed.\n3. For the foregoing reasons, the writ petition is dismissed.\n" + sign()
        o, _, _ = outcomes(t)
        self.assertEqual(o[0][1], "dismissed")


class MultiProceeding(unittest.TestCase):
    def test_numbered_appeals_mapped(self):
        meta = dict(META, case_numbers_meta="", court="Supreme Court of India")
        t = ("[[page 1]]\nIN THE SUPREME COURT OF INDIA\nCIVIL APPEAL NO. 100 OF 2020\nWITH\nCIVIL APPEAL NO. 200 OF 2020\n"
             "UNION OF INDIA ... Appellants\nVERSUS\nX ... Respondents\nJUDGMENT\n1. " + FILLER +
             "\n2. In the result, Civil Appeal No. 100 of 2020 is allowed and Civil Appeal No. 200 of 2020 is dismissed.\n"
             "\n.....................J.\n.....................J.\nNEW DELHI;\nJANUARY 5, 2026\n")
        o, rows, _ = outcomes(t, meta)
        got = sorted((r["proceeding"], r["outcome"]) for r in rows)
        self.assertEqual(len(got), 2)
        self.assertIn("allowed", [g[1] for g in got if "100" in g[0]])
        self.assertIn("dismissed", [g[1] for g in got if "200" in g[0]])

    def test_party_based_mapping(self):
        t = head("CRL.A. 5/2020") + "1. " + FILLER + "\n2. Consequently, the appeals filed by the Union of India are allowed, " \
            "whereas, the appeals filed by the accused are dismissed.\n" + sign()
        o, rows, _ = outcomes(t, dict(META, case_numbers_meta=""))
        got = {r["outcome"] for r in rows}
        self.assertEqual(got, {"allowed", "dismissed"})
        self.assertEqual(len(rows), 2)

    def test_lower_forum_disposal_not_host_result(self):
        t = head("WP(C) 673/2026") + "1. " + FILLER + "\n2. For the foregoing reasons, the order impugned in this petition is " \
            "quashed and OA No. 188/2025 dismissed as having been rendered infructuous.\n" + sign()
        o, rows, _ = outcomes(t, dict(META, case_numbers_meta="WP(C)/673/2026"))
        self.assertNotEqual(o[0][1], "dismissed_as_infructuous")

    def test_common_order_blocks(self):
        t = head("OWP 1/2014") + "OWP No. 1/2014\n1. " + FILLER + "\n2. There is no merit, as such, the same is dismissed.\n" \
            "OWP No. 2/2004\n1. " + FILLER + "\n2. The present petition is, accordingly, disposed of.\n" + sign()
        o, rows, _ = outcomes(t, dict(META, case_numbers_meta="OWP/2/2004"))
        got = sorted((r["proceeding"], r["outcome"]) for r in rows)
        self.assertEqual(len(got), 2, got)


class TenseAndContext(unittest.TestCase):
    def test_past_recital_not_result(self):
        t = head() + "1. The Original Application was dismissed by the Tribunal. The earlier writ petition was " \
            "allowed. " + FILLER + "\n2. Accordingly, the writ petition is disposed of with the above directions.\n" + sign()
        o, _, _ = outcomes(t)
        self.assertEqual(o[0][1], "disposed_of_with_directions")

    def test_party_prayer_needs_adoption(self):
        t = head() + "1. Learned counsel for the petitioner submits that the petition may kindly be disposed of as not " \
            "pressed with liberty.\n" + sign()
        o, _, _ = outcomes(t)
        self.assertEqual(o[0][1], v2core.UNVERIFIED)
        t2 = t.replace(sign(), "\n2. Ordered accordingly.\n" + sign())
        o2, rows, _ = outcomes(t2)
        self.assertEqual(o2[0][1], "dismissed_as_withdrawn")
        self.assertIn("party_prayer_adopted", rows[0]["method"])

    def test_interim_order_not_final(self):
        t = head() + "1. Issue notice. Counter affidavit be filed within four weeks.\n2. List on 12.02.2026.\n" + sign()
        o, _, _ = outcomes(t)
        self.assertEqual(o[0][1], "not_final")

    def test_withdrawal(self):
        t = head() + "1. Learned counsel seeks permission to withdraw the writ petition with liberty. Accordingly, this " \
            "writ petition is dismissed with liberty as prayed for.\n" + sign()
        o, _, _ = outcomes(t)
        self.assertEqual(o[0][1], "dismissed_as_withdrawn")


class Editorial(unittest.TestCase):
    def test_scr_headnote_and_reporter_note(self):
        meta = dict(META, case_numbers_meta="", court="Supreme Court of India")
        t = ("[[page 1]]\nA\nB\n415\nUNION OF INDIA\nv.\nX\n(Civil Appeal No. 9 of 2019)\nSEPTEMBER 13, 2019\n"
             "Army Act, 1950 - s.69 - Court martial - Held: the appeal deserves to be allowed.\n"
             "Allowing the appeal, the Court\nHELD: 1. The Tribunal under the Armed Forces Tribunal Act exceeded "
             "its jurisdiction under section 15. [Para 5]\n[2019] 12 S.C.R. 415\n[[page 2]]\n"
             "The Judgment of the Court was delivered by\nHEMANT GUPTA, J.\n1. " + FILLER * 3 +
             "\n2. We hold that the court martial was properly convened under the Army Act. "
             "Consequently, the appeal is dismissed.\nDivya Pandey\nAppeal dismissed.\n")
        o, rows, props = outcomes(t, meta)
        self.assertEqual(o[0][1], "dismissed")
        heads = [p for p in props if p["page"] == 1]
        self.assertTrue(heads and all(p["origin"] == "EDITORIAL_HEADNOTE" for p in heads), heads)

    def test_majority_final_order(self):
        meta = dict(META, case_numbers_meta="", court="Supreme Court of India")
        t = ("[[page 1]]\nIN THE SUPREME COURT OF INDIA\nTRANSFERRED CASE NO. 1 OF 1981\nX ... Petitioners\nVERSUS\n"
             "UNION ... Respondents\nJUDGMENT\nP, J.\n1. " + FILLER * 30 + "\n2. In the result, the petitions are allowed.\n"
             "\n.....................J.\n(P)\nNEW DELHI;\nDECEMBER 30, 1981\nJUDGMENT\nQ, J.\n1. " + FILLER * 30 +
             "\n2. In the result, the petitions are dismissed.\n\n.....................J.\n(Q)\n"
             "ORDER\nIn view of the majority decision, all the Transferred Cases and Writ Petitions are dismissed.\n")
        o, rows, _ = outcomes(t, meta)
        self.assertEqual(o[0][1], "dismissed")


class Composite(unittest.TestCase):
    def test_foreign_scr_report_bound_in_same_file_is_ignored(self):
        meta = dict(META, case_numbers_meta="", court="Supreme Court of India")
        t = ("[[page 1]]\nUNION OF INDIA\nv.\nX\n(Civil Appeal No. 9 of 2013)\nMARCH 1, 2018\nThe Judgment of the Court was "
             "delivered by\n1. " + FILLER * 3 + "\n2. Consequently, the appeal is dismissed.\n[[page 2]]\n"
             "ADARSH SOCIETY\nv.\nUNION OF INDIA\n(Writ Petition (Civil) No. 129 Of 2018)\nFEBRUARY 16, 2018\n1. " + FILLER * 3 +
             "\n2. Consequently, the writ petition, sans merit, stands allowed.\n")
        o, rows, _ = outcomes(t, meta)
        self.assertEqual(o[0][1], "dismissed")
        self.assertEqual(rows[0]["page"], 1)
        self.assertIn("COMPOSITE_FILE_FOREIGN_DOCUMENT_IGNORED", rows[0]["flags"])


class Integration(unittest.TestCase):
    REPO = "/home/user/c7"

    @unittest.skipUnless(shutil.which("git") and os.path.exists("/home/user/c7/.git"),
                         "c7 repository with the text layer is not available on this machine")
    def test_ids_mode_runs(self):
        out = os.path.join(os.environ.get("TMPDIR", "/tmp"), "c11_v2_ids_test")
        tool = os.path.join(os.path.dirname(HERE), "tools", "extract_v2.py")
        r = subprocess.run([sys.executable, tool, "ids", "--ids", "J-000ffb0718331ccf", "--out", out],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(os.path.join(out, "OUTCOMES_V2.csv"), encoding="utf-8") as f:
            body = f.read()
        self.assertIn("J-000ffb0718331ccf", body)


if __name__ == "__main__":
    unittest.main()
