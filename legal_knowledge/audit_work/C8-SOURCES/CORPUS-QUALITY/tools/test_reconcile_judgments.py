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
        if os.path.lexists(self.out):  # the tool refuses an existing --out without --overwrite
            os.remove(self.out)
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

    # --- output-path guard (review RC-02) ------------------------------------------------------
    def _batch_file(self):
        p = os.path.join(self.tmp.name, "b.jsonl")
        with open(p, "w") as f:
            f.write(json.dumps(item()) + "\n")
        return p

    def _main(self, argv):
        err = io.StringIO()
        with redirect_stderr(err), redirect_stdout(io.StringIO()):
            code = rj.main(argv)
        return code, err.getvalue()

    def _no_temp_left(self):
        left = [n for n in os.listdir(self.tmp.name) if n.startswith(".reconcile-")]
        self.assertEqual(left, [], "temporary report file left behind")

    def test_out_symlink_to_input_refused(self):
        p = self._batch_file()
        link = os.path.join(self.tmp.name, "link.csv")
        os.symlink(self.fx.cases, link)
        before = rb(self.fx.cases)
        for extra in ([], ["--overwrite"]):
            code, err = self._main(self.fx.args(p, link) + extra)
            self.assertEqual(code, 2)
            self.assertIn("resolves to input", err)
            self.assertEqual(rb(self.fx.cases), before)
        self._no_temp_left()

    def test_out_hardlink_to_input_refused(self):
        p = self._batch_file()
        hl = os.path.join(self.tmp.name, "hard.csv")
        os.link(self.fx.identity, hl)
        before = rb(self.fx.identity)
        for extra in ([], ["--overwrite"]):
            code, err = self._main(self.fx.args(p, hl) + extra)
            self.assertEqual(code, 2)
            self.assertIn("resolves to input", err)
            self.assertEqual(rb(self.fx.identity), before)

    def test_out_existing_non_input_refused_without_overwrite(self):
        p = self._batch_file()
        other = os.path.join(self.tmp.name, "records_copy.jsonl")
        with open(other, "w") as f:
            f.write('{"id": "KEEP"}\n')
        code, err = self._main(self.fx.args(p, other))
        self.assertEqual(code, 2)
        self.assertIn("already exists", err)
        self.assertEqual(rb(other), b'{"id": "KEEP"}\n')
        code, err = self._main(self.fx.args(p, other) + ["--overwrite"])
        self.assertEqual(code, 0)
        self.assertTrue(rb(other).startswith(b"line,item_id,classification"))
        self._no_temp_left()

    def test_out_non_regular_target_refused_even_with_overwrite(self):  # re-review RR-01
        p = self._batch_file()
        fifo = os.path.join(self.tmp.name, "a.fifo")
        os.mkfifo(fifo)
        link = os.path.join(self.tmp.name, "link.csv")
        target = os.path.join(self.tmp.name, "target.csv")
        with open(target, "w") as f:
            f.write("keep\n")
        os.symlink(target, link)
        for out in (fifo, link):
            code, err = self._main(self.fx.args(p, out) + ["--overwrite"])
            self.assertEqual(code, 2, err)
            self.assertIn("not a regular file", err)
        self.assertTrue(os.path.islink(link))
        self.assertEqual(rb(target), b"keep\n")
        import stat as _stat
        self.assertTrue(_stat.S_ISFIFO(os.lstat(fifo).st_mode))
        self._no_temp_left()

    def test_out_existing_file_inside_repo_refused_with_overwrite(self):  # re-review RR-02
        p = self._batch_file()
        repo = os.path.join(self.tmp.name, "repo")
        os.makedirs(repo)
        reg = os.path.join(repo, "register.csv")
        with open(reg, "w") as f:
            f.write("keep\n")
        code, err = self._main(self.fx.args(p, reg) + ["--overwrite", "--repo", repo])
        self.assertEqual(code, 2, err)
        self.assertIn("inside the repository", err)
        self.assertEqual(rb(reg), b"keep\n")

    def test_deeply_nested_json_fails_closed(self):  # re-review RR-03
        p = os.path.join(self.tmp.name, "deep.jsonl")
        with open(p, "w") as f:
            f.write("[" * 100000 + "]" * 100000 + "\n")
        code, err = self._main(self.fx.args(p, self.out))
        self.assertEqual(code, 2, err)
        self.assertFalse(os.path.exists(self.out))

    def test_out_input_path_refused_even_with_overwrite(self):
        p = self._batch_file()
        for target in (p, self.fx.cases, os.path.join(self.tmp.name, ".", "holdings.csv")):
            before = rb(target)
            code, err = self._main(self.fx.args(p, target) + ["--overwrite"])
            self.assertEqual(code, 2)
            self.assertEqual(rb(target), before)

    def test_out_inside_curated_originals_refused(self):
        p = self._batch_file()
        d = os.path.join(self.tmp.name, "curated_originals")
        os.mkdir(d)
        code, err = self._main(self.fx.args(p, os.path.join(d, "r.csv")))
        self.assertEqual(code, 2)
        self.assertIn("curated_originals", err)
        self.assertEqual(os.listdir(d), [])

    def test_out_directory_or_missing_parent_exit_2(self):
        p = self._batch_file()
        code, err = self._main(self.fx.args(p, self.tmp.name))
        self.assertEqual(code, 2)
        code, err = self._main(self.fx.args(p, os.path.join(self.tmp.name, "nodir", "r.csv")))
        self.assertEqual(code, 2)
        self.assertIn("parent directory", err)

    # --- input hygiene and fail-open cases (review RC-10) --------------------------------------
    def test_known_hash_with_contradictory_metadata_flagged(self):
        err = io.StringIO()
        code, rows, errtxt = self.run_batch([item(sha256=SHA_A, court="High Court of Delhi",
                                                  case_numbers=["W.P.(C) 77/2015"], judgment_date="2015-05-05",
                                                  parties="Foxtrot v Golf")])
        self.assertEqual(code, 0)
        self.assertEqual(rows[0]["classification"], "EXACT_DUPLICATE")
        self.assertEqual(rows[0]["flags"], "METADATA_CONFLICT_WITH_KNOWN_HASH")
        self.assertIn("WARNING", rows[0]["reasons"])
        self.assertIn("metadata conflicts", errtxt)

    def test_known_hash_consistent_metadata_not_flagged(self):
        code, rows, _ = self.run_batch([item(sha256=SHA_A, case_numbers=["Civil Appeal No. 1111 of 2018"],
                                             judgment_date="2019-03-01", parties="Union of India v Alpha Kumar")])
        self.assertEqual(rows[0]["classification"], "EXACT_DUPLICATE")
        self.assertEqual(rows[0]["flags"], "")

    def test_within_batch_duplicate_conflict_flagged(self):
        s = h("twice-conflict")
        code, rows, _ = self.run_batch([item(sha256=s, item_id="a"),
                                        item(sha256=s, item_id="b", judgment_date="2010-01-01")])
        self.assertEqual(rows[1]["classification"], "EXACT_DUPLICATE")
        self.assertEqual(rows[1]["flags"], "METADATA_CONFLICT_WITH_KNOWN_HASH")

    def test_untyped_case_number_not_strong(self):
        code, rows, _ = self.run_batch([item(case_numbers=["2202/2019"], judgment_date="2020-07-10",
                                             parties="Hotel v India")])
        self.assertEqual(rows[0]["classification"], "POSSIBLE_MATCH_REVIEW")
        self.assertIn("UNTYPED", rows[0]["reasons"])

    def test_formula_cells_neutralised(self):
        code, rows, _ = self.run_batch([item(item_id="@SUM(1+1)", parties="=cmd|' /C calc'!A0 v India")])
        self.assertEqual(code, 0)
        self.assertEqual(rows[0]["item_id"], "'@SUM(1+1)")
        self.assertTrue(rows[0]["parties"].startswith("'="))

    def test_malformed_duplicate_json_key(self):
        p = os.path.join(self.tmp.name, "dupkey.jsonl")
        line = json.dumps(item())[:-1] + ', "court": "High Court of Delhi"}'
        with open(p, "w") as f:
            f.write(line + "\n")
        code, err = self._main(self.fx.args(p, self.out))
        self.assertEqual(code, 2)
        self.assertIn("duplicate JSON key 'court'", err)
        self.assertFalse(os.path.exists(self.out))

    def test_malformed_duplicate_item_id(self):
        self.assert_fail_closed([item(item_id="x"), item(item_id="x", sha256=h("other"))], "duplicate item_id")

    def test_malformed_nul_byte(self):
        self.assert_fail_closed([item(parties="Union of India v Echo\x00 Prasad")], "control character")

    def test_malformed_future_date(self):
        self.assert_fail_closed([item(judgment_date="2999-01-01")], "in the future")

    def test_malformed_ancient_date(self):
        self.assert_fail_closed([item(judgment_date="1700-01-01")], "implausible")

    def test_malformed_non_string_list_member(self):
        self.assert_fail_closed([item(case_numbers=["CA 1/2020", 5])], "must be strings")

    def test_non_utf8_csv_exit_2(self):
        p = os.path.join(self.tmp.name, "latin.csv")
        with open(p, "wb") as f:
            f.write(b"court,case_numbers,judgment_date,parties,sha256,source_url\n"
                    b"Supreme Court,CA 1/2020,2020-01-01,Jos\xe9 v India," + SHA_B.encode() + b",x\n")
        code, err = self._main(self.fx.args(p, self.out))
        self.assertEqual(code, 2)
        self.assertIn("not valid UTF-8", err)
        self.assertFalse(os.path.exists(self.out))

    def test_csv_duplicate_header_exit_2(self):
        p = os.path.join(self.tmp.name, "duphdr.csv")
        with open(p, "w") as f:
            f.write("court,court,case_numbers,judgment_date,parties,sha256,source_url\n"
                    "SC,HC,CA 1/2020,2020-01-01,A v B," + SHA_B + ",x\n")
        code, err = self._main(self.fx.args(p, self.out))
        self.assertEqual(code, 2)
        self.assertIn("duplicate column", err)

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
