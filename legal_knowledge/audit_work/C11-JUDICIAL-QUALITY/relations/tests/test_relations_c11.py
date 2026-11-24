"""Tests for tools/relations_c11.py (standard library unittest; runs under python3.11 without PyMuPDF/jsonschema).

    python3.11 -I -m unittest discover -s tests -v            (from the relations/ folder)
    C11_SKIP_SLOW=1 ...                                       skips the ~2 minute byte-reproducibility rebuild

Tests that need the pinned git inputs skip with a reason when the repo or commits are unavailable.
"""
import csv
import os
import re
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.dirname(HERE)
TOOLS = os.path.join(WS, "tools")
OUT = os.path.join(WS, "outputs")
sys.path.insert(0, TOOLS)
import relations_c11 as R  # noqa: E402

REPO = os.environ.get("C11_REPO", "/home/user/c7")


def repo_ok():
    try:
        for c in (R.TEXT_COMMIT, R.AG_COMMIT, R.CURATED_COMMIT):
            subprocess.run(["git", "-C", REPO, "cat-file", "-e", c], check=True, capture_output=True)
        return True
    except Exception:
        return False


def read_csv(name):
    p = os.path.join(OUT, name)
    with open(p, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def stub_builder(src_court="High Court of Delhi", tgt_court=None):
    """Minimal Builder able to run classify_treatment on synthetic documents."""
    b = R.Builder.__new__(R.Builder)
    b.judg = {"J-src": {"jid": "J-src", "doc_id": "src", "alias_doc_ids": [], "sha": "0" * 64,
                        "meta": {"court": src_court, "issue_date": "2026-01-01", "parties": {}, "title": "src"}}}
    b.group_of = {"J-src": "G-src"}
    b.group_members = {"G-src": {"J-src"}}
    if tgt_court:
        b.judg["J-tgt"] = {"jid": "J-tgt", "doc_id": "tgt", "alias_doc_ids": [], "sha": "1" * 64,
                           "meta": {"court": tgt_court, "issue_date": "2000-01-01", "title": "Y v. Z",
                                    "parties": {"petitioner": ["Union of India"], "respondent": ["Yashpal Zorawar"]}}}
        b.group_of["J-tgt"] = "G-tgt"
        b.group_members["G-tgt"] = {"J-tgt"}
    return b


def run_treatment(text, src_court="High Court of Delhi", tgt_court=None):
    b = stub_builder(src_court, tgt_court)
    doc = R.Doc("src", text, src_court)
    b.docs = {"J-src": doc}
    cits = R.find_citations(text)
    assert cits, "synthetic text must contain a citation"
    c = cits[0]
    res = {"state": "RESOLVED", "group": "G-tgt", "methods": ["TEST"], "cands": [], "notes": []} if tgt_court else \
        {"state": "UNRESOLVED", "group": "", "methods": [], "cands": [], "notes": []}
    b.occ = [{"jid": "J-src", "ci": 0, "start": c["start"], "end": c["end"], "clus": [c], "res": res,
              "page": doc.page_at(c["start"]), "para": doc.para_at(c["start"]),
              "zone": "REPORTER_EDITORIAL" if c["start"] < doc.editorial_end else "BODY"}]
    b.classify_treatment()
    return b.cands


class TestCitationParsing(unittest.TestCase):
    def test_reporter_keys(self):
        t = ("Union of India v. Tarsem Singh [2008] 12 SCR 104 : (2008) 8 SCC 648; Bijender Singh, 2025 SCC OnLine SC 895; "
             "AIR 1962 SC 8; 2026 INSC 149; 2008 8 SCC 648.")
        keys = [c["key"] for c in R.find_citations(t)]
        self.assertIn("SCR|2008|12|104", keys)
        self.assertIn("SCC|2008|8|648", keys)
        self.assertIn("SCCOL|2025|SC|895", keys)
        self.assertIn("AIR|1962|SC|8", keys)
        self.assertIn("INSC|2026||149", keys)
        self.assertEqual(keys.count("SCC|2008|8|648"), 2)

    def test_parallel_cluster(self):
        t = "Tarsem Singh [2008] 12 SCR 104 : (2008) 8 SCC 648; Shiv Dass (2007) 9 SCC 274."
        cl = R.cluster(R.find_citations(t), t)
        self.assertEqual([len(c) for c in cl], [2, 1])

    def test_deterministic(self):
        t = "X v. Y (2013) 7 SCC 316 and Civil Appeal No. 4949 of 2013 " * 3
        self.assertEqual(R.find_citations(t), R.find_citations(t))
        self.assertEqual(R.find_case_numbers(t), R.find_case_numbers(t))


class TestNoOverrulesWithoutCue(unittest.TestCase):
    def test_plain_citation_gives_no_proposal(self):
        t = "12. The petitioner relies on Y v. Z (2001) 3 SCC 100. The facts are recorded in the order of the Tribunal.\n"
        self.assertEqual([c for c in run_treatment(t) if c["proposed"]], [])

    def test_negated_overruling_not_proposed(self):
        t = "14. The decision in Y v. Z (2001) 3 SCC 100 has not been overruled and continues to hold the field.\n"
        cands = run_treatment(t, "Supreme Court of India", "Supreme Court of India")
        self.assertFalse(any(c["proposed"] == "OVERRULES" for c in cands))

    def test_explicit_present_wording_goes_to_adviser(self):
        t = ("32. We have, thus, no hesitation in concluding that the judgment in Y v. Z (2001) 3 SCC 100 does not lay "
             "down the correct law.\n")
        cands = run_treatment(t, "Supreme Court of India", "Supreme Court of India")
        ov = [c for c in cands if c["proposed"] == "OVERRULES"]
        self.assertEqual(len(ov), 1)
        self.assertEqual(ov[0]["status"], R.STATUS_ADV)

    def test_high_court_cannot_overrule_supreme_court(self):
        t = "9. The judgment in Y v. Z (2001) 3 SCC 100 does not lay down the correct law.\n"
        cands = run_treatment(t, "High Court of Delhi", "Supreme Court of India")
        self.assertFalse(any(c["proposed"] == "OVERRULES" for c in cands))
        self.assertTrue(all(c["attribution"] != "COURT_LIKELY" for c in cands if c["cue_relation"] == "OVERRULES"))

    def test_past_history_is_reported_not_proposed(self):
        t = "21. Y v. Z (2001) 3 SCC 100 was overruled by a larger Bench in A v. B (2005) 2 SCC 1.\n"
        cands = run_treatment(t, "Supreme Court of India", "Supreme Court of India")
        self.assertFalse(any(c["proposed"] == "OVERRULES" for c in cands))

    @unittest.skipUnless(os.path.exists(os.path.join(OUT, "TREATMENT_CANDIDATES.csv")), "outputs not built")
    def test_outputs_overrules_only_with_explicit_cue(self):
        rx = [p for r, p in R.CUES if r == "OVERRULES"]
        for row in read_csv("TREATMENT_CANDIDATES.csv"):
            if row["proposed_relation"] in ("OVERRULES", "REVERSES", "QUESTIONS"):
                self.assertEqual(row["status"], R.STATUS_ADV, row["candidate_id"])
            if row["proposed_relation"] == "OVERRULES":
                self.assertTrue(any(p.search(row["cue_text"]) for p in rx), row["candidate_id"])
                self.assertEqual(row["attribution"], "COURT_LIKELY")
                self.assertEqual(row["negated"], "NO")
            self.assertNotEqual(row["status"], "LEGALLY_VALIDATED")
        for row in read_csv("CASE_CITATION_GRAPH.csv"):
            self.assertEqual(row["relation"], "CITES")
            self.assertNotEqual(row["status"], "LEGALLY_VALIDATED")


class TestAttribution(unittest.TestCase):
    def test_quoted_passage_not_attributed(self):
        t = ("17. In A v. B the Court held as under:\n“22. The reliance placed on Y v. Z (2001) 3 SCC 100 is of no "
             "assistance, and the decision does not lay down the correct law.”\n18. We now turn to the facts.\n")
        cands = run_treatment(t, "Supreme Court of India", "Supreme Court of India")
        self.assertTrue(cands)
        for c in cands:
            self.assertEqual(c["attribution"], "QUOTED_PASSAGE")
            self.assertEqual(c["proposed"], "")

    def test_leadin_without_quote_marks(self):
        t = ("17. The Supreme Court observed (SCC p. 7, para 9):\n9. The reliance on Y v. Z (2001) 3 SCC 100 is "
             "misplaced as it is clearly distinguishable.\n")
        cands = run_treatment(t)
        self.assertTrue(cands)
        self.assertTrue(all(c["proposed"] == "" for c in cands))

    def test_submission_not_attributed(self):
        t = ("8. Learned counsel for the respondents submitted that Y v. Z (2001) 3 SCC 100 is clearly distinguishable "
             "on facts.\n")
        cands = run_treatment(t)
        self.assertTrue(cands)
        for c in cands:
            self.assertEqual(c["attribution"], "PARTY_SUBMISSION_OR_MIXED")
            self.assertEqual(c["proposed"], "")

    def test_court_voice_distinguishing_is_proposed_for_documentary_check(self):
        t = "10. In our view, Y v. Z (2001) 3 SCC 100 is clearly distinguishable on facts.\n"
        cands = run_treatment(t)
        d = [c for c in cands if c["proposed"] == "DISTINGUISHES"]
        self.assertEqual(len(d), 1)
        self.assertEqual(d[0]["status"], R.STATUS_DOC)

    def test_reporter_editorial_zone(self):
        t = ("[[page 1]]\n[2026] 2 S.C.R. 615\nHeadnotes\nCase Law Cited\nY v. Z (2001) 3 SCC 100 – held inapplicable.\n"
             "[[page 2]]\nJudgment\n1. The appeals arise from the Tribunal.\n")
        cands = run_treatment(t, "Supreme Court of India")
        self.assertTrue(cands)
        for c in cands:
            self.assertEqual(c["attribution"], "REPORTER_EDITORIAL")
            self.assertEqual(c["proposed"], "")

    @unittest.skipUnless(repo_ok(), "pinned repo/commits not available")
    def test_real_hc_quote_of_girish_para22_is_quoted(self):
        did = "hc-jkl-2026-wp-c-1426-2026-jkhc020026572026-1-2026-05-19"
        t = R.git(REPO, "show", "%s:data/text/%s.txt" % (R.TEXT_COMMIT, did)).decode("utf-8")
        i = t.find("of no assistance to it")
        self.assertGreater(i, 0)
        inq, why = R.in_quotation(t, i, max(0, i - 2500))
        self.assertTrue(inq, why)

    @unittest.skipUnless(os.path.exists(os.path.join(OUT, "TREATMENT_CANDIDATES.csv")), "outputs not built")
    def test_outputs_non_court_attribution_never_proposed(self):
        for row in read_csv("TREATMENT_CANDIDATES.csv"):
            if row["attribution"] != "COURT_LIKELY":
                self.assertEqual(row["proposed_relation"], "", row["candidate_id"])


class TestVersionNotAssignedWithoutEvidence(unittest.TestCase):
    def _builder(self, edges):
        b = R.Builder.__new__(R.Builder)
        b.graph = {"I-TEST": edges}
        b.c10_li = {}
        return b

    def _agg(self):
        return {"inst": "AA-1950", "label": "Army Act, 1950", "ag": "I-TEST", "pid": "AA-1950:s.127", "subs": set(),
                "mentions": 1, "pages": {1}, "cues": {}, "best": None, "first": (1, "", "x"), "bare_only": False,
                "excluded_cues": {}}

    def test_evidenced_edge_alone_does_not_establish_version(self):
        edges = [{"edge_id": "E1", "provision": "s.127", "scope": "SPECIFIC", "provs": [("s", "127")], "status": "EVIDENCED",
                  "commencement": "1992-09-07", "kind": "omission"}]
        out = self._builder(edges)._finish_link("J-x", "2000-01-01", self._agg())
        self.assertEqual(out["vstat"], "VERSION_NOT_ESTABLISHED")
        self.assertIn("complete amendment history", out["vbasis"])

    def test_complete_history_still_blocked_by_unevidenced_or_unknown(self):
        old = R.COMPLETE_HISTORY_INSTRUMENTS
        try:
            R.COMPLETE_HISTORY_INSTRUMENTS = frozenset({"I-TEST"})
            e_unev = [{"edge_id": "E1", "provision": "s.127", "scope": "SPECIFIC", "provs": [("s", "127")],
                       "status": "UNRESOLVED_COMMENCEMENT", "commencement": "", "kind": "omission"}]
            self.assertEqual(self._builder(e_unev)._finish_link("J-x", "2000-01-01", self._agg())["vstat"], "VERSION_NOT_ESTABLISHED")
            e_unk = [{"edge_id": "E2", "provision": "unknown", "scope": "UNKNOWN", "provs": [], "status": "NOT_LOCATED",
                      "commencement": "", "kind": "possible amendment"}]
            self.assertEqual(self._builder(e_unk)._finish_link("J-x", "2000-01-01", self._agg())["vstat"], "VERSION_NOT_ESTABLISHED")
            e_ok = [{"edge_id": "E3", "provision": "s.127", "scope": "SPECIFIC", "provs": [("s", "127")], "status": "EVIDENCED",
                     "commencement": "1992-09-07", "kind": "omission"}]
            out = self._builder(e_ok)._finish_link("J-x", "2000-01-01", self._agg())
            self.assertEqual(out["vstat"], "VERSION_AT_JUDGMENT_DATE_INDICATED_NOT_VERIFIED")
            self.assertIn("E3", out["vbasis"])
        finally:
            R.COMPLETE_HISTORY_INSTRUMENTS = old

    def test_no_complete_history_instruments_declared(self):
        self.assertEqual(R.COMPLETE_HISTORY_INSTRUMENTS, frozenset())

    @unittest.skipUnless(os.path.exists(os.path.join(OUT, "STATUTE_JUDGMENT_LINKS.csv")), "outputs not built")
    def test_outputs_no_version_assigned(self):
        for row in read_csv("STATUTE_JUDGMENT_LINKS.csv"):
            self.assertEqual(row["version_status"], "VERSION_NOT_ESTABLISHED", row["link_id"])
            if row["instrument_id"] in ("IPC-1860", "BNS-2023", "CRPC-1973", "BNSS-2023") and row["judgment_date"] >= R.BNS_SWITCH:
                self.assertIn("NOT assumed", row["code_transition_note"])


class TestReproducibility(unittest.TestCase):
    @unittest.skipIf(os.environ.get("C11_SKIP_SLOW") == "1", "C11_SKIP_SLOW=1")
    @unittest.skipUnless(repo_ok(), "pinned repo/commits not available")
    @unittest.skipUnless(os.path.exists(os.path.join(OUT, "OUTPUT_SHA256SUMS")), "outputs not built")
    def test_check_mode_byte_identical(self):
        r = subprocess.run([sys.executable, "-I", os.path.join(TOOLS, "relations_c11.py"), "--repo", REPO, "--check"],
                           capture_output=True, text=True, timeout=1800)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("CHECK OK", r.stdout)

    @unittest.skipUnless(os.path.exists(os.path.join(OUT, "OUTPUT_SHA256SUMS")), "outputs not built")
    def test_sha256sums_match_files(self):
        import hashlib
        with open(os.path.join(OUT, "OUTPUT_SHA256SUMS"), encoding="utf-8") as f:
            for line in f:
                h, name = line.rstrip("\n").split("  ", 1)
                with open(os.path.join(OUT, name), "rb") as g:
                    self.assertEqual(hashlib.sha256(g.read()).hexdigest(), h, name)


if __name__ == "__main__":
    unittest.main()
