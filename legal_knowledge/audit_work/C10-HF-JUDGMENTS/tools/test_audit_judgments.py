#!/usr/bin/env python3
"""Offline tests for the C10 Hugging Face judicial-corpus audit (assembly reproducibility, accounting, labelling, rules)."""
import csv, gzip, io, json, subprocess, sys, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import jextract as J  # noqa: E402
import audit_judgments as AJ  # noqa: E402

REPO = str(HERE.parents[3])
try:
    import pymupdf  # noqa: F401
    HAVE_PYMUPDF = True
except ImportError:
    HAVE_PYMUPDF = False


def have_commits():
    return all(subprocess.run(["git", "-C", REPO, "cat-file", "-e", c], capture_output=True).returncode == 0
               for c in (AJ.RAW, AJ.STAGING))


class Rules(unittest.TestCase):
    def test_parse_date_forms(self):
        self.assertEqual(J.parse_date("18.03.2025"), "2025-03-18")
        self.assertEqual(J.parse_date("1st July 2025"), "2025-07-01")
        self.assertEqual(J.parse_date("NOVEMBER 6 2024"), "2024-11-06")
        self.assertIsNone(J.parse_date("31.13.2020"))

    def test_norm_case(self):
        self.assertEqual(J.norm_case_string("W.P.(C)/10368/2026"), "WPC-10368-2026")
        self.assertEqual(J.norm_case_string("OA 484/2018"), "OA-484-2018")
        self.assertIsNone(J.norm_case_string("no number here"))

    def test_relevance_rules(self):
        self.assertEqual(J.classify_relevance({"direct": 5}, "TEXT_LAYER_OK")[0], "DIRECT_MILITARY_LAW")
        self.assertEqual(J.classify_relevance({"direct": 0, "admin": 4}, "TEXT_LAYER_OK")[0], "MILITARY_ADMIN_SERVICE_PENSION")
        self.assertEqual(J.classify_relevance({"general": 3, "admin": 1}, "TEXT_LAYER_OK")[0], "GENERAL_LAW_POTENTIALLY_APPLICABLE")
        self.assertEqual(J.classify_relevance({}, "NO_TEXT_LAYER")[0], "RELEVANCE_UNCERTAIN_REVIEW")
        self.assertEqual(J.classify_relevance({}, "TEXT_LAYER_OK")[0], "NOT_RELEVANT_CURRENT_SCOPE")

    @unittest.skipUnless(HAVE_PYMUPDF, "PyMuPDF (requirements.txt pymupdf==2.1) is not installed in this environment")
    def test_outcome_and_decision_date_on_synthetic_pdf(self):
        import pymupdf
        doc = pymupdf.open()
        body = ("IN THE HIGH COURT OF DELHI AT NEW DELHI  Pronounced on: 01.07.2025  W.P.(C) 140/2024  "
                "The impugned order dated 12.03.2019 was passed under the Army Act. " * 3)
        p = doc.new_page(); p.insert_textbox(pymupdf.Rect(36, 36, 560, 800), body, fontsize=9)
        p = doc.new_page(); p.insert_textbox(pymupdf.Rect(36, 36, 560, 800),
                                             "We are of the considered view that the court martial proceedings were vitiated by bias. "
                                             "In view of the above, the petition is accordingly dismissed. JULY 1, 2025", fontsize=9)
        r = J.extract(doc.tobytes(), pymupdf)
        self.assertEqual(r["outcome_candidate"], "dismissed")
        self.assertIn("2025-07-01", r["decision_date_candidates"])
        self.assertNotIn("2019-03-12", r["decision_date_candidates"])   # an earlier order's date is not decision evidence
        self.assertIn("WPC-140-2024", r["case_numbers_text_p1_3"])
        self.assertTrue(all(x["status"] == "AUTOMATED_CANDIDATE_NOT_VERIFIED" for x in r["propositions"]))
        self.assertIn("Army Act, 1950", r["statutes"])

    @unittest.skipUnless(HAVE_PYMUPDF, "PyMuPDF (requirements.txt pymupdf==2.1) is not installed in this environment")
    def test_unreadable_bytes_are_a_result(self):
        import pymupdf
        self.assertEqual(J.extract(b"not a pdf", pymupdf)["pdf_status"], "UNREADABLE")


@unittest.skipUnless(have_commits(), "pinned raw-data / staging commits are not in this clone")
class Assembly(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import jassemble
        cls.out, cls.binary, cls.st = jassemble.build(REPO)

    def test_outputs_reproduce(self):
        for k, v in self.out.items():
            self.assertEqual((AJ.OUT / k).read_text(encoding="utf-8"), v, k)
        for k, v in self.binary.items():
            self.assertEqual((AJ.OUT / k).read_bytes(), v, k)

    def test_accounting_complete(self):
        st = self.st
        self.assertEqual(sum(st["file_dispositions"].values()), st["source_files"])
        self.assertEqual(sum(st["record_dispositions"].values()), st["metadata_records"])
        self.assertEqual(sum(st["excluded_dispositions"].values()), st["excluded_records"])
        cont = list(csv.DictReader(io.StringIO(self.out["CONTINUATION_MANIFEST.csv"])))
        self.assertEqual(len(cont), st["source_files"] - st["file_dispositions"].get("PROCESSED", 0))
        self.assertEqual(st["batches_complete"], st["batches"])

    def test_every_record_and_file_in_master_inventory(self):
        inv = list(csv.DictReader(io.StringIO(self.out["HF_JUDGMENT_MASTER_INVENTORY.csv"])))
        self.assertEqual(sum(1 for r in inv if r["collection"] == "SOURCE_FILE"), self.st["source_files"])
        self.assertEqual(sum(1 for r in inv if r["collection"] == "METADATA_RECORD"), self.st["metadata_records"])
        self.assertTrue(all(r["disposition"] for r in inv))

    def test_excluded_dispositions_complete(self):
        rows = list(csv.DictReader(io.StringIO(gzip.decompress(self.binary["HF_JUDGMENT_EXCLUDED_DISPOSITIONS.csv.gz"]).decode())))
        self.assertEqual(len(rows), self.st["excluded_records"])
        self.assertTrue(all(r["disposition"].startswith("EXCLUDED_FILE_NOT_RETAINED") for r in rows))

    def test_nothing_labelled_legally_verified(self):
        for name in ("HF_JUDGMENT_HOLDINGS.jsonl", "HF_JUDGMENT_LEGAL_ISSUES.jsonl"):
            for l in self.out[name].splitlines():
                self.assertEqual(json.loads(l)["status"], "AUTOMATED_CANDIDATE_NOT_VERIFIED")
        meta = list(csv.DictReader(io.StringIO(self.out["HF_JUDGMENT_METADATA_AUDIT.csv"])))
        self.assertEqual({r["verification"] for r in meta}, {"AUTOMATED_NOT_LEGALLY_VERIFIED"})
        copies = list(csv.DictReader(io.StringIO(self.out["HF_JUDGMENT_COPY_REGISTER.csv"])))
        self.assertEqual({r["hf_bytes"] for r in copies}, {"NOT_CHECKED"})



class TitleSignal(unittest.TestCase):
    def test_title_prevents_not_relevant(self):
        c = J.classify_relevance({}, "TEXT_LAYER_OK", "UNION OF INDIA Vs ARMED FORCES TRIBUNAL AND ANR")[0]
        self.assertEqual(c, "RELEVANCE_UNCERTAIN_REVIEW")
        c = J.classify_relevance({"admin": 1}, "TEXT_LAYER_OK", "UNION OF INDIA Vs GP CAPT X (RETD)")[0]
        self.assertEqual(c, "MILITARY_ADMIN_SERVICE_PENSION")
        self.assertEqual(J.classify_relevance({}, "TEXT_LAYER_OK", "BHATNAGARS AND CO. LTD. versus THE UNION OF INDIA")[0],
                         "NOT_RELEVANT_CURRENT_SCOPE")


class ReviewFixes(unittest.TestCase):
    """Regression tests for the workstream review of 3257ebb9 (WS-01, WS-02, WS-07)."""
    def test_batch_key_depends_on_extractor_source(self):
        k = AJ.batch_key(["a" * 64])
        orig = AJ.extractor_fingerprint
        try:
            AJ.extractor_fingerprint = lambda: "0" * 64
            self.assertNotEqual(AJ.batch_key(["a" * 64]), k)
        finally:
            AJ.extractor_fingerprint = orig
        self.assertEqual(AJ.batch_key(["a" * 64]), k)

    def test_bare_army_is_a_service_term(self):
        c = J.classify_relevance({}, "TEXT_LAYER_OK", "SUMIT ARORA Vs UNION OF INDIA")[0]
        self.assertEqual(c, "NOT_RELEVANT_CURRENT_SCOPE")  # title alone has no signal
        self.assertTrue(J.ADMIN.search("as per the existing policies of the Indian Army the petitioner was posted"))
        self.assertTrue(J.ADMIN.search("a medical officer of the Army posted at Base Hospital"))


    @unittest.skipUnless(HAVE_PYMUPDF, "PyMuPDF (requirements.txt pymupdf==2.1) is not installed in this environment")
    def test_readable_pdf_without_eof_is_truncated_copy(self):
        import hashlib, os, tempfile, pymupdf
        doc = pymupdf.open()
        for _ in range(2):
            p = doc.new_page(); p.insert_text((72, 72), "Army Act court martial petition dismissed")
        data = doc.tobytes().replace(b"%%EOF", b"")
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, "t.pdf"), "wb") as fh:
                fh.write(data)
            old = os.environ.get("MIMAMSA_WORKING_STORE")
            os.environ["MIMAMSA_WORKING_STORE"] = td
            try:
                item = dict(sha256=hashlib.sha256(data).hexdigest(), path="t.pdf", location="X", byte_source="working_store:t.pdf")
                rec = AJ._work((REPO, item))
            finally:
                if old is None:
                    os.environ.pop("MIMAMSA_WORKING_STORE", None)
                else:
                    os.environ["MIMAMSA_WORKING_STORE"] = old
        if rec.get("pdf_status") == "OPENED":
            self.assertEqual(rec["extraction"], "PROCESSED_TRUNCATED_COPY")
        else:
            self.assertEqual(rec["extraction"], "INCOMPLETE_COPY_TRUNCATED")
        import jassemble
        self.assertEqual(jassemble.source_completeness(rec), jassemble.TRUNC)

    def test_source_completeness_rules(self):
        import jassemble as JA
        self.assertEqual(JA.source_completeness({"extraction": "PROCESSED", "pdf_eof_anywhere": True, "pdf_eof_marker": True}), "COMPLETE_FILE_STRUCTURE")
        self.assertEqual(JA.source_completeness({"extraction": "PROCESSED", "pdf_eof_anywhere": True, "pdf_eof_marker": False}),
                         "STORED_COPY_TAIL_CUT_AFTER_EARLIER_EOF_BASE_REVISION_PRESENT")
        self.assertEqual(JA.source_completeness({"extraction": "PROCESSED_TRUNCATED_COPY", "pdf_eof_anywhere": False}), JA.TRUNC)
        self.assertEqual(JA.source_completeness(None), "NOT_AVAILABLE")

    def test_bare_army_moves_classification_out_of_not_relevant(self):
        n = len(J.ADMIN.findall("posted as per the policies of the Indian Army at the Army hospital"))
        self.assertGreater(n, 0)
        self.assertNotEqual(J.classify_relevance({"admin": n}, "TEXT_LAYER_OK", "SUMIT ARORA Vs UNION OF INDIA")[0],
                            "NOT_RELEVANT_CURRENT_SCOPE")

    def test_title_rescreen_rank_forms(self):
        import jassemble as JA
        for t in ("COL.T.PRASAD Vs UOI", "MAJ.GEN. X v UOI", "CAPT X v UOI"):
            self.assertTrue(JA.TITLE_SCREEN.search(t), t)
        for t in ("SUB INSPECTOR RAM v STATE", "GEN MANAGER v X", "SUB DIVISIONAL OFFICER v Y"):
            self.assertFalse(JA.TITLE_SCREEN.search(t), t)


@unittest.skipUnless(have_commits(), "pinned raw-data / staging commits are not in this clone")
class TruncationAccounting(unittest.TestCase):
    def test_truncated_marked_in_research_outputs(self):
        import jassemble as JA
        copies = list(csv.DictReader(io.StringIO((AJ.OUT / "HF_JUDGMENT_COPY_REGISTER.csv").read_text(encoding="utf-8"))))
        trunc = {r["sha256"] for r in copies if r["disposition"] == "PROCESSED_TRUNCATED_COPY"}
        self.assertTrue(trunc)
        for name in ("HF_JUDGMENT_HOLDINGS.jsonl", "HF_JUDGMENT_LEGAL_ISSUES.jsonl"):
            for l in (AJ.OUT / name).read_text(encoding="utf-8").splitlines():
                o = json.loads(l)
                self.assertEqual(o["sha256"] in trunc, o["source_completeness"] == JA.TRUNC, name)
        for r in csv.DictReader(io.StringIO((AJ.OUT / "HF_JUDGMENT_RELEVANCE.csv").read_text(encoding="utf-8"))):
            if r["source_completeness"] == JA.TRUNC:
                self.assertNotIn("OCR", r["reason"])

    def test_outcome_contradiction_only_when_both_sides_present(self):
        for r in csv.DictReader(io.StringIO((AJ.OUT / "HF_JUDGMENT_METADATA_AUDIT.csv").read_text(encoding="utf-8"))):
            if "crawler outcome" in r["contradictions"]:
                self.assertTrue(r["outcome_meta"])
                self.assertNotIn(r["outcome_text_candidate"], ("", "NOT_FOUND"))
                self.assertNotEqual(r["outcome_meta"], r["outcome_text_candidate"])

    def test_truncated_copies_are_unresolved_and_listed(self):
        copies = list(csv.DictReader(io.StringIO((AJ.OUT / "HF_JUDGMENT_COPY_REGISTER.csv").read_text(encoding="utf-8"))))
        cont = {r["sha256"] for r in csv.DictReader(io.StringIO((AJ.OUT / "CONTINUATION_MANIFEST.csv").read_text(encoding="utf-8")))}
        trunc = [r for r in copies if "TRUNCATED" in r["disposition"]]
        self.assertTrue(trunc)
        self.assertTrue(all(r["sha256"] in cont for r in trunc))
        self.assertFalse(any(r["sha256"] in cont for r in copies if r["disposition"] == "PROCESSED"))

    def test_batches_match_current_extractor(self):
        for bp in sorted((AJ.HERE.parent / "work" / "batches").glob("batch_*.jsonl")):
            with bp.open(encoding="utf-8") as fh:
                head = json.loads(fh.readline())
            self.assertEqual(head["input_key"], AJ.batch_key(head["shas"]), bp.name)


if __name__ == "__main__":
    unittest.main()
