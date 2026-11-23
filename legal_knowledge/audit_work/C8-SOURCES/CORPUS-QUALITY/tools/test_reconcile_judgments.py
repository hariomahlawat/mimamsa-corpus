#!/usr/bin/env python3
"""Offline unit tests for reconcile_judgments.py (stdlib unittest, synthetic fixtures only).

Run: python3 -m unittest test_reconcile_judgments -v   (from this directory)
"""
import csv
import hashlib
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reconcile_judgments as rj  # noqa: E402


def rb(p):
    with open(p, "rb") as f:
        return f.read()


def h(s):
    return hashlib.sha256(s.encode()).hexdigest()


SHA_A = h("alpha-official-copy")
SHA_A2 = h("alpha-second-copy")
SHA_B = h("bravo-mirror")
SHA_C5 = h("charlie-c5-copy")


class Fixture:
    def __init__(self, d):
        self.d = d
        self.cases = os.path.join(d, "cases.jsonl")
        with open(self.cases, "w") as f:
            f.write(json.dumps({"id": "DCLR-SC-2019-900", "title": "Union of India v Ex Sep Alpha Kumar",
                                "court": "Supreme Court of India", "decision_date": "2019-03-01",
                                "case_number": "Civil Appeal No. 1111 of 2018",
                                "reporter_citation": "(2019) 4 SCC 100", "original_pdf_sha256": SHA_A}) + "\n")
            f.write(json.dumps({"id": "DCLR-SC-2020-901", "title": "Union of India v Lt Col Bravo Singh",
                                "court": "Supreme Court of India", "decision_date": "2020-07-10",
                                "case_number": "C.A. 2201–2203/2019", "reporter_citation": "2020 INSC 555",
                                "original_pdf_sha256": ""}) + "\n")
            f.write(json.dumps({"id": "DCLR-SC-2015-902", "title": "Union of India v Major Delta Rao",
                                "court": "Supreme Court of India", "decision_date": "", "case_number": "",
                                "reporter_citation": "(2015) 2 SCC 50", "original_pdf_sha256": ""}) + "\n")
        self.identity = os.path.join(d, "identity.csv")
        with open(self.identity, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["spec_key", "case53_id", "curated_title", "curated_court",
                                              "curated_decision_date", "curated_case_number",
                                              "curated_reporter_citation", "intern_sha256", "intern_case_numbers",
                                              "intern_decision_date", "intern_neutral_citation",
                                              "intern_reported_citations", "intern_parties", "held_copy_sha256",
                                              "register_official_sha256", "expected_neutral_citation_spec"])
            w.writeheader()
            w.writerow({"spec_key": "BRAVO", "case53_id": "DCLR-SC-2020-901",
                        "curated_title": "Union of India v Lt Col Bravo Singh", "curated_court": "Supreme Court of India",
                        "curated_decision_date": "2020-07-10", "curated_case_number": "C.A. 2201–2203/2019",
                        "intern_sha256": SHA_B, "intern_decision_date": "2020-07-10"})
        self.holdings = os.path.join(d, "holdings.csv")
        with open(self.holdings, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["row_id", "spec_key", "case53_id", "judgment", "decision_date",
                                              "copy_sha256", "copy_role", "uncertainty"])
            w.writeheader()
            w.writerow({"row_id": "H-1", "spec_key": "ALPHA", "case53_id": "DCLR-SC-2019-900",
                        "judgment": "Union of India v Alpha Kumar, CA 1111/2018", "decision_date": "2019-03-01",
                        "copy_sha256": SHA_A, "copy_role": "OFFICIAL_COURT_COPY",
                        "uncertainty": "PDF holds CORRECTED and uncorrected versions"})
        self.copies = os.path.join(d, "copies.csv")
        with open(self.copies, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["copy_id", "source_id", "sha256", "copy_role"])
            w.writeheader()
            w.writerow({"copy_id": "C5-SRC-J-X~C1", "source_id": "C5-SRC-J-X", "sha256": SHA_C5,
                        "copy_role": "OFFICIAL"})
        self.csm = os.path.join(d, "csm.csv")
        with open(self.csm, "w", newline="") as f:
            f.write("key,source_id,basis\nDCLR-SC-2015-902,C5-SRC-J-X,case id\n")

    def args(self, incoming, out):
        return ["--incoming", incoming, "--out", out, "--cases", self.cases, "--identity", self.identity,
                "--holdings", self.holdings, "--copies", self.copies, "--case-source-map", self.csm]


def item(**kw):
    base = {"court": "Supreme Court of India", "case_numbers": ["Civil Appeal No. 7777 of 2021"],
            "judgment_date": "2022-01-05", "parties": "Union of India v Echo Prasad", "citations": [],
            "sha256": h("new-item"), "source_url": "https://example.invalid/x.pdf"}
    base.update(kw)
    return base


class ReconcileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.fx = Fixture(self.tmp.name)
        self.out = os.path.join(self.tmp.name, "report.csv")

    def tearDown(self):
        self.tmp.cleanup()

    def run_batch(self, items, ext=".jsonl"):
        p = os.path.join(self.tmp.name, "batch" + ext)
        if ext == ".jsonl":
            with open(p, "w") as f:
                for it in items:
                    f.write(json.dumps(it) + "\n")
        else:
            keys = sorted({k for it in items for k in it})
            with open(p, "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=keys)
                w.writeheader()
                for it in items:
                    w.writerow({k: (";".join(v) if isinstance(v, list) else v) for k, v in it.items()})
        err, outbuf = io.StringIO(), io.StringIO()
        with redirect_stderr(err), redirect_stdout(outbuf):
            code = rj.main(self.fx.args(p, self.out))
        rows = []
        if code == 0:
            with open(self.out, newline="") as f:
                rows = list(csv.DictReader(f))
        return code, rows, err.getvalue()

    # --- one test per class ---------------------------------------------------------------
    def test_exact_duplicate_corpus(self):
        code, rows, _ = self.run_batch([item(sha256=SHA_A)])
        self.assertEqual(code, 0)
        self.assertEqual(rows[0]["classification"], "EXACT_DUPLICATE")
        self.assertIn("DCLR-SC-2019-900", rows[0]["matched_corpus_keys"])

    def test_exact_duplicate_c5_copy_mapped_to_case(self):
        code, rows, _ = self.run_batch([item(sha256=SHA_C5)])
        self.assertEqual(rows[0]["classification"], "EXACT_DUPLICATE")
        self.assertIn("DCLR-SC-2015-902", rows[0]["matched_corpus_keys"])

    def test_exact_duplicate_within_batch(self):
        s = h("twice")
        code, rows, _ = self.run_batch([item(sha256=s, item_id="a"), item(sha256=s, item_id="b")])
        self.assertEqual(rows[0]["classification"], "NEW")
        self.assertEqual(rows[1]["classification"], "EXACT_DUPLICATE")
        self.assertIn("within batch", rows[1]["matched_on"])

    def test_same_judgment_new_copy(self):
        code, rows, _ = self.run_batch([item(case_numbers=["C.A. No. 2202 of 2019"], judgment_date="2020-07-10",
                                             parties="UOI v Bravo Singh", sha256=SHA_A2)])
        self.assertEqual(rows[0]["classification"], "SAME_JUDGMENT_NEW_COPY")
        self.assertEqual(rows[0]["matched_corpus_keys"], "DCLR-SC-2020-901")

    def test_version_relationship_marker_on_incoming(self):
        code, rows, _ = self.run_batch([item(case_numbers=["CA 2201/2019"], judgment_date="2020-07-10",
                                             sha256=SHA_A2, version_label="CORRECTED copy uploaded 2020-08-01")])
        self.assertEqual(rows[0]["classification"], "VERSION_RELATIONSHIP")
        self.assertIn("corrected", rows[0]["reasons"].lower())

    def test_version_relationship_marker_on_corpus_copy(self):
        code, rows, _ = self.run_batch([item(case_numbers=["Civil Appeal 1111 of 2018"], judgment_date="2019-03-01",
                                             sha256=SHA_A2)])
        self.assertEqual(rows[0]["classification"], "VERSION_RELATIONSHIP")

    def test_possible_match_same_case_other_date(self):
        code, rows, _ = self.run_batch([item(case_numbers=["C.A. 2201/2019"], judgment_date="2021-10-12")])
        self.assertEqual(rows[0]["classification"], "POSSIBLE_MATCH_REVIEW")
        self.assertIn("possible later/earlier order", rows[0]["reasons"])

    def test_possible_match_citation_only(self):
        code, rows, _ = self.run_batch([item(citations=["[2015] 2 SCC 50"], judgment_date="2015-06-01")])
        self.assertEqual(rows[0]["classification"], "POSSIBLE_MATCH_REVIEW")
        self.assertIn("DCLR-SC-2015-902", rows[0]["matched_corpus_keys"])
        self.assertIn("shared citation", rows[0]["reasons"])

    def test_possible_match_party_only(self):
        code, rows, _ = self.run_batch([item(parties="Union of India & Ors v Major Delta Rao (Retd)",
                                             judgment_date="2015-04-01")])
        self.assertEqual(rows[0]["classification"], "POSSIBLE_MATCH_REVIEW")
        self.assertIn("party-name similarity", rows[0]["reasons"])

    def test_new(self):
        code, rows, _ = self.run_batch([item()])
        self.assertEqual(rows[0]["classification"], "NEW")
        self.assertIn("does not prove absence", rows[0]["reasons"])

    def test_different_court_same_number_not_strong(self):
        code, rows, _ = self.run_batch([item(court="High Court of Delhi", case_numbers=["W.P.(C) 2201/2019"],
                                             judgment_date="2020-07-10", parties="Foxtrot v Golf")])
        self.assertNotIn(rows[0]["classification"], ("SAME_JUDGMENT_NEW_COPY", "VERSION_RELATIONSHIP"))

    def test_csv_input(self):
        code, rows, _ = self.run_batch([item(sha256=SHA_B, case_numbers=["CA 2201/2019"])], ext=".csv")
        self.assertEqual(code, 0)
        self.assertEqual(rows[0]["classification"], "EXACT_DUPLICATE")

    def test_deterministic_output(self):
        items = [item(sha256=SHA_A), item(), item(case_numbers=["C.A. 2201/2019"], judgment_date="2021-10-12")]
        self.run_batch(items)
        first = rb(self.out)
        self.run_batch(items)
        self.assertEqual(first, rb(self.out))

    def test_inputs_not_modified(self):
        before = {p: rb(p) for p in (self.fx.cases, self.fx.identity, self.fx.holdings,
                                                     self.fx.copies, self.fx.csm)}
        self.run_batch([item(sha256=SHA_A), item()])
        for p, b in before.items():
            self.assertEqual(rb(p), b)

    # --- malformed input: fail closed -------------------------------------------------------
    def assert_fail_closed(self, items, msg, ext=".jsonl"):
        if os.path.exists(self.out):
            os.remove(self.out)
        code, rows, err = self.run_batch(items, ext=ext)
        self.assertEqual(code, 2)
        self.assertFalse(os.path.exists(self.out), "no report may be written on malformed input")
        self.assertIn(msg, err)

    def test_malformed_bad_sha(self):
        self.assert_fail_closed([item(sha256="ABC123")], "sha256 must be 64")

    def test_malformed_bad_date(self):
        self.assert_fail_closed([item(judgment_date="2020-02-30")], "not a valid YYYY-MM-DD")

    def test_malformed_missing_field(self):
        it = item()
        del it["court"]
        self.assert_fail_closed([it], "missing required field 'court'")

    def test_malformed_no_provenance(self):
        it = item()
        del it["source_url"]
        self.assert_fail_closed([it], "source_url / provenance")

    def test_malformed_unparseable_case_number(self):
        self.assert_fail_closed([item(case_numbers=["pending"])], "no parseable")

    def test_one_bad_item_blocks_whole_batch(self):
        self.assert_fail_closed([item(), item(sha256="x")], "1 malformed item")

    def test_malformed_json_line(self):
        p = os.path.join(self.tmp.name, "bad.jsonl")
        with open(p, "w") as f:
            f.write("{not json}\n")
        err = io.StringIO()
        with redirect_stderr(err), redirect_stdout(io.StringIO()):
            code = rj.main(self.fx.args(p, self.out))
        self.assertEqual(code, 2)
        self.assertIn("invalid JSON", err.getvalue())

    def test_out_equal_to_input_refused(self):
        p = os.path.join(self.tmp.name, "b.jsonl")
        with open(p, "w") as f:
            f.write(json.dumps(item()) + "\n")
        err = io.StringIO()
        with redirect_stderr(err), redirect_stdout(io.StringIO()):
            code = rj.main(self.fx.args(p, self.fx.cases))
        self.assertEqual(code, 2)

    def test_missing_corpus_file_fails_closed(self):
        p = os.path.join(self.tmp.name, "b.jsonl")
        with open(p, "w") as f:
            f.write(json.dumps(item()) + "\n")
        err = io.StringIO()
        with redirect_stderr(err), redirect_stdout(io.StringIO()):
            code = rj.main(["--incoming", p, "--out", self.out, "--repo", os.path.join(self.tmp.name, "nope")])
        self.assertEqual(code, 2)
        self.assertIn("missing input", err.getvalue())

    # --- helpers ------------------------------------------------------------------------------
    def test_case_key_range_expansion(self):
        keys = rj.case_keys(["C.A. 6820–6824/2018"])
        self.assertIn(("CA", 6822, "2018"), keys)
        self.assertEqual(len(keys), 5)

    def test_case_key_types(self):
        self.assertIn(("WPC", 5992, "2026"), rj.case_keys(["W.P.(C) 5992/2026"]))
        self.assertIn(("SLPCRL", 2302, "2017"), rj.case_keys(["SLP (Crl.) No. 2302/2017"]))
        self.assertIn(("CRLA", 85, "2022"), rj.case_keys(["Criminal Appeal 85 of 2022"]))


if __name__ == "__main__":
    unittest.main()
