"""Tests for the C11 Supreme Court case-number proposal (tools/scnum_c11.py).

Standard library only (unittest; also collected by pytest). The reproducibility
test needs the git repository /home/user/c7 (commits ad77758d, 21e73b83) and is
skipped with a stated reason when it is not available. No PyMuPDF is needed.
"""
import csv
import os
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCNUM = HERE.parent
sys.path.insert(0, str(SCNUM / "tools"))

import scnum_c11 as S  # noqa: E402

OUT = SCNUM / "outputs"
REPO = os.environ.get("SCNUM_REPO", "/home/user/c7")


def _repo_ok() -> bool:
    try:
        for c in (S.SOURCE_COMMIT, S.CURATED_COMMIT):
            subprocess.run(["git", "-C", REPO, "cat-file", "-e", c + "^{commit}"],
                           check=True, capture_output=True)
        return True
    except Exception:
        return False


def _rows(name):
    with open(OUT / name, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _hosts(text):
    """Parse a synthetic jurisdiction block and return (hosts, arising, parents)."""
    res = S.parse_block(text, 0, len(text))
    h = [n for r in res.hosts for n in r.normalised()]
    a = [n for r in res.arising for n in r.normalised()]
    p = [n for r in res.parents for n in r.normalised()]
    return h, a, p


class ParserUnitTests(unittest.TestCase):
    def test_scr_civil_appeal_with_impugned_number_excluded(self):
        h, a, _ = _hosts("Civil Appeal No. 1234 of 1980. From the Judgment and Order dated "
                         "12.3.1979 of the Delhi High Court in C.W.P. No. 567 of 1978.")
        self.assertEqual(h, ["CA-1234-1980"])
        self.assertEqual(a, ["CWP-567-1978"])

    def test_writ_petition_criminal_and_connected(self):
        h, a, _ = _hosts("Writ Petition (Criminal) No. 55 of 2013. Under Article 32 of the "
                         "Constitution of India. WITH W.P. (Crl.) Nos. 34, 56 & 136 of 2013.")
        self.assertEqual(h, ["WPCRL-55-2013", "WPCRL-34-2013", "WPCRL-56-2013", "WPCRL-136-2013"])
        self.assertEqual(a, [])

    def test_range_expansion_and_slp(self):
        h, _, _ = _hosts("Civil Appeal Nos. 4415- 16 of 2018. From the Judgment of the AFT in "
                         "O.A. No. 2002 of 2011. With S.L.P. (C) No. 99 of 2019.")
        self.assertEqual(h, ["CA-4415-2018", "CA-4416-2018", "SLPC-99-2019"])

    def test_arising_out_of_is_not_host(self):
        h, a, _ = _hosts("Criminal Appeal No. 210 of 2017 (Arising out of S.L.P. (Crl.) "
                         "No. 5000 of 2016)")
        self.assertEqual(h, ["CRLA-210-2017"])
        self.assertEqual(a, ["SLPCRL-5000-2016"])

    def test_parent_in_case_and_gutter_letters(self):
        h, _, p = _hosts("Civil Misc. Petition No. 20065of1988. B c In Civil Appeal No. 1702 "
                         "of 1987. From the Judgment of the Allahabad High Court.")
        self.assertEqual(h, ["CMP-20065-1988"])
        self.assertEqual(p, ["CA-1702-1987"])

    def test_old_scr_petitions_with_mixed_years(self):
        h, _, _ = _hosts("Petitions Nos. 377 of 1955 and 42, 46 of 1956. Petitions under "
                         "Article 32 of the Constitution.")
        self.assertEqual(h, ["PET-377-1955", "PET-42-1956", "PET-46-1956"])

    def test_slash_years_and_with_lists(self):
        h, a, _ = _hosts("Civil Appeal No. 3609 of 1996. From the Judgment of the Delhi High "
                         "Court in C.W.P. No. 917 of 1991. With CA Nos. 3612, 3613/96 and 7467/94.")
        self.assertEqual(h, ["CA-3609-1996", "CA-3612-1996", "CA-3613-1996", "CA-7467-1994"])
        self.assertEqual(a, ["CWP-917-1991"])

    def test_ocr_year_repair_is_flagged(self):
        res = S.parse_block("Civil Appeal No. 1646 of I999. From the Judgment", 0, 48)
        self.assertEqual(res.hosts[0].normalised(), ["CA-1646-1999"])
        self.assertFalse(res.hosts[0].clean)
        self.assertTrue(any(f.startswith("ocr_year_repaired") for f in res.hosts[0].flags))

    def test_diary_number(self):
        h, _, _ = _hosts("Civil Appeal D. No. 32135 of 2013 From the Judgment and Order")
        self.assertEqual(h, ["CADIARY-32135-2013"])

    def test_anchor_detection_tolerates_ocr_but_not_prose(self):
        self.assertTrue(S.find_anchors("text. CIVIL APPELLATE JuR1sorcnoN: Civil Appeal No. 3"))
        self.assertTrue(S.find_anchors("x ORIGINAL JURISDICTION : Writ Petition No. 1 of 1990"))
        self.assertFalse(S.find_anchors("the High Court had no jurisdiction: it said"))

    def test_type_normalisation(self):
        self.assertEqual(S.normalise_type("Special Leave Petition (Crl.)")[0], "SLPCRL")
        self.assertEqual(S.normalise_type("W.P. (C)")[0], "WPC")
        self.assertEqual(S.normalise_type("Transferred Case")[0], "TC")
        self.assertEqual(S.normalise_type("Crl. A.")[0], "CRLA")
        self.assertFalse(S.normalise_type("Regular Second Appeal")[1])


class OutputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (OUT / "SC_CASE_NUMBER_PROPOSALS.csv").exists():
            raise unittest.SkipTest("outputs not generated yet (run tools/scnum_c11.py --repo ...)")

    def test_accounting_sums_to_368(self):
        acc = {r["classification"]: int(r["count"]) for r in _rows("SC_CASE_NUMBER_ACCOUNTING.csv")}
        total = sum(v for k, v in acc.items() if k != "TOTAL")
        self.assertEqual(total, 368)
        self.assertEqual(acc["TOTAL"], 368)
        self.assertEqual(set(acc) - {"TOTAL"}, set(S.CLASSES))
        rows = _rows("SC_CASE_NUMBER_PROPOSALS.csv")
        self.assertEqual(len(rows), 368)
        self.assertEqual(len({r["doc_id"] for r in rows}), 368)
        for c in S.CLASSES:
            self.assertEqual(sum(r["classification"] == c for r in rows), acc[c])

    def test_no_host_equals_arising_in_same_row(self):
        for r in _rows("SC_CASE_NUMBER_PROPOSALS.csv"):
            hosts = {x for x in r["host_case_numbers_normalised"].split(";") if x}
            arising = {x for x in r["arising_from"].split(";") if x}
            self.assertFalse(hosts & arising, r["doc_id"])

    def test_row_invariants(self):
        for r in _rows("SC_CASE_NUMBER_PROPOSALS.csv"):
            self.assertEqual(r["method"], "AUTOMATED_RULES")
            self.assertEqual(r["status"], "PROPOSAL_NOT_APPLIED")
            self.assertLessEqual(len(r["evidence_excerpt"]), 200)
            self.assertIn(r["classification"], S.CLASSES)
            if r["classification"].startswith("CONFIRMED"):
                self.assertTrue(r["host_case_numbers_normalised"])
                self.assertNotIn("YEAR?", r["host_case_numbers_normalised"])
                self.assertEqual(r["flags"], "")
            if r["classification"] == "CONFIRMED_MULTIPLE_CONNECTED":
                self.assertGreater(int(r["connected_count"]), 0)
            if r["classification"] == "CONFIRMED_FROM_SOURCE":
                self.assertEqual(int(r["connected_count"]), 0)

    def test_review_queue_covers_non_confirmed_plus_sample(self):
        rows = _rows("SC_CASE_NUMBER_PROPOSALS.csv")
        rq = _rows("REVIEW_QUEUE.csv")
        need = {r["doc_id"] for r in rows if not r["classification"].startswith("CONFIRMED")}
        mand = {r["doc_id"] for r in rq if r["review_reason"].startswith("MANDATORY_")}
        self.assertEqual(need, mand)
        sample = [r for r in rq if r["review_reason"] == "SAMPLE_CONFIRMED"]
        self.assertEqual(len(sample), min(20, len(rows) - len(need)))

    def test_sha256sums_match(self):
        import hashlib
        for line in (OUT / "OUTPUT_SHA256SUMS").read_text().splitlines():
            digest, name = line.split("  ", 1)
            self.assertEqual(hashlib.sha256((OUT / name).read_bytes()).hexdigest(), digest, name)


class ReproducibilityTest(unittest.TestCase):
    def test_check_mode_reproduces_outputs(self):
        if not _repo_ok():
            self.skipTest("git repo %s with commits %s/%s not available"
                          % (REPO, S.SOURCE_COMMIT, S.CURATED_COMMIT))
        p = subprocess.run([sys.executable, str(SCNUM / "tools" / "scnum_c11.py"),
                            "--repo", REPO, "--check"], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("CHECK OK", p.stdout)


if __name__ == "__main__":
    unittest.main()
