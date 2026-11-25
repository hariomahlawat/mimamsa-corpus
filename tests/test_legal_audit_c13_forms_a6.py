"""C13 A6 forms workstream: official-copy transcription (WS-G R04), expanded register, oracle."""
import csv
import hashlib
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
A6 = REPO / "legal_knowledge" / "audit_work" / "C13-A6-FORMS"
OUT = A6 / "outputs"
TOOLS = A6 / "tools"
C12FR = REPO / "legal_knowledge" / "audit_work" / "C12-CONSOLIDATION" / "forms_registry" / "outputs"
sys.path.insert(0, str(TOOLS))

import a6_common as C  # noqa: E402
import spec_oracle as SO  # noqa: E402
import spec_register as SR  # noqa: E402
import spec_transcriptions as ST  # noqa: E402

VS = "DISCOVERED_FROM_SOURCE_NOT_LEGALLY_APPROVED"
RM_SHA = "4284820e5bc2fb7f52ae9fbe8a61650f1579e9b6389ba206a916a69fed016b14"
RM_ID = "regs-regulations-for-the-air-force-reprinted-edition-2000"


def rows(name):
    with open(OUT / name, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def sources_available():
    return os.path.isfile(os.path.join(C.SCRATCH, C.SOURCES["AR54-GAZ"]["path"])) and os.path.isdir(C.C7)


class Outputs(unittest.TestCase):
    def test_c12_inputs_unchanged(self):
        for fn, h in SR.C12_INPUTS.items():
            self.assertEqual(hashlib.sha256((C12FR / fn).read_bytes()).hexdigest(), h, fn)

    def test_every_row_research_only(self):
        for name in ("OFFICIAL_TRANSCRIPTIONS.csv", "FORM_FIELDS_C13_v2.csv", "FORM_REGISTER_C13.csv"):
            self.assertEqual({r["verification_status"] for r in rows(name)}, {VS}, name)
        reg = rows("FORM_REGISTER_C13.csv")
        self.assertEqual({r["legal_approval_state"] for r in reg}, {"NOT_APPROVED"})
        self.assertEqual({r["applicability_state"] for r in reg}, {"NOT_ESTABLISHED"})

    def test_transcriptions_only_from_official_copies(self):
        keys = {r["source_key"] for r in rows("OFFICIAL_TRANSCRIPTIONS.csv")}
        self.assertTrue(keys)
        self.assertFalse(any(k.startswith("MML") for k in keys))
        for k in keys:
            self.assertEqual({r["copy_sha256"] for r in rows("OFFICIAL_TRANSCRIPTIONS.csv") if r["source_key"] == k},
                             {C.SOURCES[k]["sha256"]})

    def test_page_image_log_is_reproducible_and_complete(self):
        log = rows("PAGE_IMAGE_LOG.csv")
        self.assertGreaterEqual(len(log), 60)
        for r in log:
            self.assertTrue(r["copy_sha256"] and r["pdf_page"] and r["dpi"] and r["renderer"].startswith("pymupdf"))
            self.assertIn("render_pages.py", r["reproduce_with"])
            self.assertEqual(r["review_state"], "PENDING_INDEPENDENT_REVIEW")
        fams = {r["form_family_id"] for r in log}
        trans = {r["form_family_id"] for r in rows("OFFICIAL_TRANSCRIPTIONS.csv")}
        self.assertEqual(fams, trans)

    def test_r04_scope_and_counts(self):
        st = rows("R04_FAMILY_STATUS.csv")
        r04 = [r for r in st if r["in_r04_22"] == "True"]
        self.assertEqual(len(r04), 22)
        summ = json.loads((OUT / "SUMMARY.json").read_text(encoding="utf-8"))
        self.assertEqual(summ["r04"]["families"], 22)
        self.assertEqual(summ["r04"]["official_transcribed_full"] + summ["r04"]["official_amending_text_only"]
                         + summ["r04"]["official_not_held"], 22)
        stat = [r for r in st if r["statutory_candidate"] == "True"]
        self.assertEqual(len(stat), 39)
        # families with no official copy carry no official rows and are not filled from MML
        for r in st:
            if r["official_status"] == "OFFICIAL_COPY_NOT_HELD":
                self.assertEqual(r["official_fields"], "0")

    def test_not_held_families_stay_mml_only(self):
        reg = {r["form_id"]: r for r in rows("FORM_REGISTER_C13.csv")}
        for fam in ("FF-DPPR53-S1-F1", "FF-ISLR38-FA", "FF-ITR42-PASS", "FF-AR54-APPII-P1"):
            self.assertTrue(reg[fam]["source_fidelity_c13"].startswith("MML_ONLY_UNVERIFIED"), fam)

    def test_illegible_spans_are_marked_not_filled(self):
        t = rows("OFFICIAL_TRANSCRIPTIONS.csv")
        ill = [r for r in t if "[illegible]" in r["field_label_as_printed"]]
        self.assertTrue(ill)
        self.assertEqual({r["legibility"] for r in ill}, {"CONTAINS_ILLEGIBLE_SPAN"})
        # Form G operative line: the officer categories are not completed from another edition
        g = [r["field_label_as_printed"] for r in t if r["form_family_id"] == "FF-AR54-APPIV-P2-FG"]
        self.assertTrue(any("deliver the said (Name) [illegible] warrant officer" in x for x in g))

    def test_statutory_rows_quote_shall(self):
        for r in rows("FORM_REGISTER_C13.csv"):
            if r["form_authority_type_candidate"] == "STATUTORY_PRESCRIBED":
                self.assertIn("shall", r["requirement_language_as_printed"], r["form_id"])

    def test_versioned_field_file_does_not_touch_c12(self):
        ff = rows("FORM_FIELDS_C13_v2.csv")
        self.assertTrue(any(r["field_set_version"].startswith("OFFICIAL_PAGE_IMAGE_TRANSCRIPTION_C13") for r in ff))
        self.assertTrue(any(r["field_set_version"].startswith("CARRIED_FROM_C12") for r in ff))
        c12 = list(csv.DictReader(open(C12FR / "FORM_FIELDS.csv", encoding="utf-8")))
        self.assertEqual({r["verification_status"] for r in c12}, {VS})

    def test_acquisition_requests_cover_restricted_air_force(self):
        acq = rows("ACQUISITION_REQUESTS_A6.csv")
        self.assertTrue(any(r["status"] == "NEEDS_AUTHORISED_SOURCE" and r["service"] == "AIR_FORCE" for r in acq))
        self.assertEqual({r["action_taken"] for r in acq}, {"NONE (no download made in A6)"})


class Restricted(unittest.TestCase):
    def test_restricted_material_never_a_source(self):
        for k, s in C.SOURCES.items():
            self.assertFalse(C.is_restricted(sha256=s["sha256"], path=s["path"]), k)
        for name in ("OFFICIAL_TRANSCRIPTIONS.csv", "FORM_FIELDS_C13_v2.csv", "FORM_REGISTER_C13.csv",
                     "PAGE_IMAGE_LOG.csv", "R04_COMPARISON.csv", "ORACLE_CASES.jsonl", "ACQUISITION_REQUESTS_A6.csv"):
            txt = (OUT / name).read_text(encoding="utf-8")
            self.assertNotIn(RM_SHA, txt, name)
            self.assertNotIn(RM_ID, txt, name)
        self.assertTrue(C.is_restricted(path=f"data/text/{RM_ID}.txt"))
        self.assertTrue(C.is_restricted(sha256="212ac873869bf3298b8194f6ad8a1a994b990242a3dab5d0f927e3e4c4ce2cea"))

    def test_read_source_refuses_restricted(self):
        C.SOURCES["_RM"] = dict(root="c7git", path=f"data/raw/indiacode/0000/{RM_SHA}.pdf", sha256=RM_SHA)
        try:
            with self.assertRaises(PermissionError):
                C.read_source("_RM")
        finally:
            del C.SOURCES["_RM"]

    def test_mirror_matches_gov_single_source_of_truth(self):
        r = subprocess.run(["git", "-C", str(REPO), "show", "claude/c13-gov:config/restricted_material.json"],
                           capture_output=True, text=True)
        if r.returncode != 0:
            self.skipTest("claude/c13-gov branch not available")
        items = json.loads(r.stdout)["items"]
        gov = {i["doc_id"]: i for i in items}
        self.assertIn(C.RESTRICTED_MIRROR["doc_id"], gov)
        g = gov[C.RESTRICTED_MIRROR["doc_id"]]
        self.assertEqual(g["source_sha256"], C.RESTRICTED_MIRROR["source_sha256"])
        self.assertEqual(set(g["derived_sha256"]), set(C.RESTRICTED_MIRROR["derived_sha256"]))
        self.assertEqual(set(g["hosted_paths"]), set(C.RESTRICTED_MIRROR["hosted_paths"]))
        for it in items:  # every gov item must be caught by the guard
            self.assertTrue(C.is_restricted(sha256=it["source_sha256"]) or "forms_registry" not in it.get("exclude_from", []))


class Oracle(unittest.TestCase):
    def setUp(self):
        with open(OUT / "ORACLE_CASES.jsonl", encoding="utf-8") as fh:
            self.cases = [json.loads(x) for x in fh]

    def test_cases_are_synthetic_and_gated(self):
        self.assertGreaterEqual(len(self.cases), 80)
        cats = {c["category"] for c in self.cases}
        self.assertTrue({"correct", "borderline", "defective", "abstain"} <= cats)
        for c in self.cases:
            self.assertTrue(c["synthetic"])
            self.assertIn("SYNTHETIC", c["marking"])
            if c["synthetic_document"]:
                self.assertTrue(c["synthetic_document"].startswith("SYNTHETIC TEST DOCUMENT"))
            self.assertEqual(c["expected_legal_consequence"], "NOT_DETERMINED")
            self.assertTrue(c["expected_operational_gate"].startswith("REFUSED_RESEARCH_ONLY"))

    def test_oracle_not_imported_by_other_tools(self):
        users = [p.name for p in TOOLS.glob("*.py") if "spec_oracle" in p.read_text(encoding="utf-8") and p.name != "spec_oracle.py"]
        self.assertEqual(users, ["build_a6.py"])

    def test_pinpoint_guard_rejects_unmatched_mutation(self):
        bad = ("X-01", "FF-AR54-APPIII-P2", "defective", [("drop", "No Such Column")], "t", "FAIL_SOURCE_SUPPORTED", "r", [])
        trows = [dict(family=e["family"], source=e["source"], page=e["page"], label=l, kind=k)
                 for e in ST.T for (l, k) in e["fields"]]
        SO.CASES.append(bad)
        try:
            with self.assertRaises(SystemExit):
                SO.build_oracle(trows)
        finally:
            SO.CASES.pop()

    def test_findings_column_is_borderline_not_pass(self):
        c = {x["case_id"]: x for x in self.cases}["OR-03"]
        self.assertEqual(c["expected_result"], "REVIEW_REQUIRED")
        self.assertIn("Findings", c["synthetic_document"])


@unittest.skipUnless(sources_available(), "held sources not available on this host")
class Reproducible(unittest.TestCase):
    def test_build_check(self):
        r = subprocess.run([sys.executable, "-I", str(TOOLS / "build_a6.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
