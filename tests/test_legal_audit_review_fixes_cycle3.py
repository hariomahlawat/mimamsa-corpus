"""Regression tests for the three Codex P2 findings on PR #25 (WS-D cycle 3). Evidence of the failures on the
pre-fix code is recorded in legal_knowledge/audit_work/WS-D-QUALITY/REVIEW_FIXES_CYCLE3.md. Structural only."""
import copy
import csv
import importlib.util
import io
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WSD = ROOT / "legal_knowledge" / "audit_work" / "WS-D-QUALITY"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


VE = load("ve_c3fix", WSD / "scripts" / "build_versioned_edges.py")
CC = load("cc_c3fix", WSD / "scripts" / "canonical_coverage.py")


def ref_ok(ref):
    return subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--verify", "-q", ref], capture_output=True).returncode == 0


def version_ids(V, inst, num):
    return {i for v in V.get((inst, num), []) for i in v.get("evidence_ids", [v["version_id"]])}


# ---------------- (1) multi-provision change-log entries ----------------
class Fix1MultiProvisionExpansion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.V = VE.versions()

    def test_rr_134_135_136_all_registered(self):
        for n in ("134", "135", "136"):
            self.assertIn("PCL-93-25", version_ids(self.V, "AR", n), f"r.{n} from 'rr.134,135,136' not registered")

    def test_ranges_letter_suffixes_and_lists(self):
        for n in ("172", "173", "174", "175", "176"):
            self.assertIn("PCL-93-34", version_ids(self.V, "AR", n), f"r.{n} from 'rr.172-176'")
        for n in ("170A", "170B"):
            self.assertIn("PCL-93-33", version_ids(self.V, "AR", n))
        for n in ("16A", "16B", "16C"):
            self.assertIn("PCL-BL-16", version_ids(self.V, "AR", n))
        self.assertIn("PCL-17E-2019", version_ids(self.V, "AR", "15B"))
        self.assertIn("PCL-17E-2019", version_ids(self.V, "AR", "16A"))

    def test_army_act_lists(self):
        for n in ("75", "76"):
            self.assertIn("AA-08-s2", version_ids(self.V, "AA", n))
        for n in ("139", "151", "174"):
            self.assertIn("AA-08-s14", version_ids(self.V, "AA", n))
        for n in ("4", "6", "7"):
            self.assertIn("AA-04", version_ids(self.V, "AA", n))
        for n in ("137", "151"):
            self.assertIn("AA-02", version_ids(self.V, "AA", n), "slash list 'ss.137/151'")

    def test_boundaries_no_invented_provisions(self):
        cases = {"rr.134,135,136": ["134", "135", "136"], "r.14(4),(5)": ["14"], "r.2 cl.(cc),(di),(dii)": ["2"],
                 "rr.172-176": ["172", "173", "174", "175", "176"], "rr.170A,170B": ["170A", "170B"],
                 "r.16A,16B,16C": ["16A", "16B", "16C"], "r.15B; r.16A(4) proviso, (5)(a) Explanation, (6)(a)": ["15B", "16A"],
                 "App. I Forms I,II": [], "Table below r.13 (col.3, cat. III(i)); App. I Form I": ["13"],
                 "rr.10–12": ["10", "11", "12"], "r.16A(4),(5)(a),(6)(a)": ["16A"]}
        for text, want in cases.items():
            self.assertEqual(VE.expand_provisions(text, "r"), want, text)
        aa = {"ss.4(3), 6(1), 7(1), 7(2)": ["4", "6", "7"], "ss.137/151 etc.": ["137", "151"], "s.81(1), (4)": ["81"],
              "s.169A": ["169A"], "Chapter XVI and heading": [], "ss.75, 76": ["75", "76"]}
        for text, want in aa.items():
            self.assertEqual(VE.expand_provisions(text, "s"), want, text)

    def test_records_citing_r135_r136_get_edges(self):
        edges, _, _ = VE.build()
        got = {(e["record_id"], e["provision"]) for e in edges if "PCL-93-25" in e["evidence_refs"].split(";")}
        for want in (("V9-WF-10", "r.135"), ("V9-SC-14", "r.135"), ("EV-006", "r.135"), ("EV-006", "r.136")):
            self.assertIn(want, got)


# ---------------- (2) duplicate evidence of one amendment event ----------------
class Fix2AmendmentEventIdentity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.edges, _, _ = VE.build()
        cls.V = VE.versions()

    def test_no_zero_length_or_reversed_intervals(self):
        bad = [(e["record_id"], e["version_id"], e["valid_from"], e["valid_to"]) for e in self.edges
               if e["valid_from"] and e["valid_to"] and e["valid_to"] <= e["valid_from"]]
        self.assertEqual(bad, [], f"{len(bad)} zero-length/reversed intervals, e.g. {bad[:3]}")

    def test_r177_seed_and_change_log_are_one_event(self):
        groups = self.V.get(("AR", "177"), [])
        with_8e = [g for g in groups if {"r.177@v2003", "PCL-8E-2003"} <= set(g["evidence_ids"])]
        self.assertEqual(len(with_8e), 1, f"r.177 S.R.O. 8(E)/2003 evidence not grouped: {[g['evidence_ids'] for g in groups]}")
        adm = [e for e in self.edges if e["record_id"] == "ADM-033" and e["provision"] == "r.177"]
        self.assertTrue(adm)
        self.assertEqual(len({e["version_id"] for e in adm}), len(adm), "duplicate edges for one event")

    def test_distinct_instruments_stay_distinct_versions(self):
        groups = self.V.get(("AR", "193"), [])
        keys = [g["event_key"] for g in groups]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertGreaterEqual(len(groups), 3, "r.193 1954 / 1987 / 1993 are separate events")
        self.assertTrue(any({"r.193@v1993", "PCL-93-38", "PCL-193-1993"} <= set(g["evidence_ids"]) for g in groups))

    def test_interval_guard_rejects_bad_successor(self):
        vs = [{"version_id": "A", "evidence_ids": ["A"], "event_key": "a", "pub": "2003-06-24", "eff": "2003-06-24",
               "status": "STATED_IN_INSTRUMENT", "det": "", "conflict": "", "sub": False, "ocr": False, "source": "x", "change": "x"},
              {"version_id": "B", "evidence_ids": ["B"], "event_key": "b", "pub": "2003-06-24", "eff": "2003-06-24",
               "status": "STATED_IN_INSTRUMENT", "det": "", "conflict": "", "sub": False, "ocr": False, "source": "x", "change": "x"}]
        self.assertEqual(VE.successor_bound(vs, 0), ("", "VALIDITY_INTERVAL_REJECTED"))


# ---------------- (3) coded-record locators and section checks ----------------
class Fix3CodedRecordSections(unittest.TestCase):
    @unittest.skipUnless(ref_ok("origin/raw-data"), "SKIPPED: local git ref origin/raw-data (crawler corpus) is absent, so the "
                     "real-corpus variant cannot run; the same behaviour is asserted without the ref by Fix3WithoutCorpusRef")
    def test_kb003_sections_bound_to_code_target(self):
        out, _ = CC.build("origin/raw-data")
        row = next(r for r in out if r["record_id"] == "KB-003")
        self.assertRegex(row["items"], r"code:SRC-AA=>act-army-1950\[id\]#s79,s80,s81,s82",
                         f"KB-003 Army Act ss.79-82 not bound to SRC-AA: {row['items']}")

    @unittest.skipUnless(ref_ok("origin/raw-data"), "SKIPPED: local git ref origin/raw-data (crawler corpus) is absent, so the "
                     "real-corpus variant cannot run; the same behaviour is asserted without the ref by Fix3WithoutCorpusRef")
    def test_missing_section_file_downgrades_coded_record(self):
        orig_load = CC.load

        def patched(name, path):
            mod = orig_load(name, path)
            if name == "cov_cc":
                real = mod.corpus

                def corpus(ref):
                    C = real(ref)
                    C = dict(C, sections=dict(C["sections"]))
                    C["sections"]["act-army-1950"] = set(C["sections"]["act-army-1950"]) - {"s80"}
                    return C
                mod.corpus = corpus
            return mod
        CC.load = patched
        try:
            out, _ = CC.build("origin/raw-data")
        finally:
            CC.load = orig_load
        row = next(r for r in out if r["record_id"] == "KB-003")
        self.assertNotEqual(row["source_searchable"], "ALL", "missing Army Act s.80 file did not downgrade KB-003")
        self.assertEqual(row["anchored_full"], "NO")

    @unittest.skipUnless(ref_ok("origin/raw-data"), "SKIPPED: local git ref origin/raw-data (crawler corpus) is absent, so the "
                     "real-corpus variant cannot run; the same behaviour is asserted without the ref by Fix3WithoutCorpusRef")
    def test_mixed_forms_not_discarded(self):
        out, _ = CC.build("origin/raw-data")
        rows = {r["record_id"]: r for r in out}
        # bracket form with locators for two codes
        self.assertRegex(rows["HCE-001"]["items"], r"code:AA=>act-army-1950\[id\]#s2,s79,")
        # V-series pipe form with Act sections
        self.assertRegex(rows["AFT-001"]["items"], r"code:V7-S01=>act-armed-forces-tribunal-2007\[id\]#s2,s3,s14,s15,s21,s22")


if __name__ == "__main__":
    unittest.main()


# ---------------- (1b) returned defect: sections OF THE AMENDING ACT are not Army Act provisions ----------------
AA04_TEXT = ("ss.4(3), 6(1), 7(1), 7(2): 'clause (i) of section 2' -> 'clause (i) of sub-section (1) of section 2' "
             "(s.3 and Second Schedule)")


class Fix1bAmendingActOwnSections(unittest.TestCase):
    def test_aa04_full_text_yields_only_army_act_sections(self):
        self.assertEqual(VE.army_act_sections(AA04_TEXT), ["4", "6", "7"],
                         "'(s.3 and Second Schedule)' is s.3 of the amending Act 56/1974, not Army Act s.3")

    def test_aa04_not_registered_against_army_act_s3(self):
        V = VE.versions()
        self.assertNotIn("AA-04", version_ids(V, "AA", "3"))
        for n in ("4", "6", "7"):
            self.assertIn("AA-04", version_ids(V, "AA", n))

    def test_no_false_s3_edges_from_aa04(self):
        edges, _, _ = VE.build()
        bad = [e["record_id"] for e in edges if e["provision"] == "s.3" and "AA-04" in e["evidence_refs"].split(";")]
        self.assertEqual(bad, [], f"false Army Act s.3 edges from AA-04: {bad}")

    def test_other_amending_act_reference_forms(self):
        cases = {"s.3(iv) (definition); s.3 of Act 19/1955: references construed": ["3"],
                 "s.3(viii) [J&K words omitted]; Explanation below s.70 omitted": ["3", "70"],
                 "s.12 of Act 37 of 1992 inserts words in s.135(1)": ["135"],
                 "ss.75, 76 (s.2 of the Army (Amendment) Act, 1992)": ["75", "76"],
                 "s.5 and the First Schedule": [],
                 "ss.137/151 etc.": ["137", "151"]}
        for text, want in cases.items():
            self.assertEqual(VE.army_act_sections(text), want, text)


# ---------------- condition (b): Fix3 behaviour without the crawler-corpus ref (committed minimal fixture) ----------------
# Minimal synthetic corpus: only the documents and Army Act / AFT Act section files these records need.
FIXTURE_CORPUS = {
    "ref": "fixture", "commit": "fixture-no-raw-data",
    "meta": {"act-army-1950", "rules-army-rules-1954", "act-armed-forces-tribunal-2007"},
    "sections": {"act-army-1950": {f"s{n}" for n in [2] + list(range(79, 89)) + [120, 121, 122]},
                 "act-armed-forces-tribunal-2007": {f"s{n}" for n in (2, 3, 14, 15, 21, 22)}},
    "sc_urls": {},
}


def build_with_corpus(corpus):
    orig_load = CC.load

    def patched(name, path):
        mod = orig_load(name, path)
        if name == "cov_cc":
            mod.corpus = lambda ref: corpus
        return mod
    CC.load = patched
    try:
        out, _ = CC.build("fixture")
    finally:
        CC.load = orig_load
    return {r["record_id"]: r for r in out}


class Fix3WithoutCorpusRef(unittest.TestCase):
    def test_kb003_sections_checked_against_fixture(self):
        rows = build_with_corpus(FIXTURE_CORPUS)
        self.assertRegex(rows["KB-003"]["items"], r"code:SRC-AA=>act-army-1950\[id\]#s79,s80,s81,s82")
        self.assertEqual(rows["KB-003"]["source_searchable"], "ALL")

    def test_missing_section_in_fixture_downgrades(self):
        c = dict(FIXTURE_CORPUS, sections=dict(FIXTURE_CORPUS["sections"]))
        c["sections"]["act-army-1950"] = FIXTURE_CORPUS["sections"]["act-army-1950"] - {"s80"}
        rows = build_with_corpus(c)
        self.assertNotEqual(rows["KB-003"]["source_searchable"], "ALL")
        self.assertEqual(rows["KB-003"]["anchored_full"], "NO")

    def test_mixed_forms_bound_without_ref(self):
        rows = build_with_corpus(FIXTURE_CORPUS)
        self.assertRegex(rows["HCE-001"]["items"], r"code:AA=>act-army-1950\[id\]#s2,s79,")
        self.assertRegex(rows["AFT-001"]["items"], r"code:V7-S01=>act-armed-forces-tribunal-2007\[id\]#s2,s3,s14,s15,s21,s22")
