"""WS-D deliverable 2: full 87-code citation register completeness against the frozen KB.

Recomputes the code inventory from records_658.jsonl via PILOT-01/build_code_inventory.py and
asserts the baseline exactly: 87 codes, no missing, no extra, per-class counts 39/33/3/9/2/1,
firm 72/87, inclusive 75/87, 269 records with no code, the [VERIFY] placeholder set, and the
frozen KB hash. It also pins the known stale usage counts in the v3 register (8 rows carried
from v2) so that any NEW drift fails. These are structural checks only: a passing run never
means a citation is legally correct, and the co-citation class is never counted as confirmed.
"""
import collections
import csv
import hashlib
import importlib.util
import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
B = ROOT / "legal_knowledge" / "audit_work" / "PILOT-01"
SPEC = importlib.util.spec_from_file_location("build_code_inventory_wsd", B / "build_code_inventory.py")
BCI = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BCI)
REG_ROWS = list(csv.DictReader((B / "registers" / "source_code_resolution_v3.csv").open(encoding="utf-8")))
REG = {r["code"]: r for r in REG_ROWS}
COVERAGE = json.loads((B / "registers" / "source_code_coverage_v3.json").read_text(encoding="utf-8"))

KB_SHA = "9a8f0d193065762ffa987116dc761bcb734008d2a87a946f5591741f5befcfc1"
BASELINE_CLASSES = {"RESOLVED_RECORD_EXPLICIT": 39, "CORROBORATED_OFFICIAL": 33, "RESOLVED_CO_CITATION": 3,
                    "PROBABLE": 9, "CATEGORY_ONLY": 2, "UNRESOLVABLE": 1}
FIRM = {"RESOLVED_RECORD_EXPLICIT", "CORROBORATED_OFFICIAL"}
# Exact baseline membership of the non-firm classes (any promotion/demotion must be a reviewed change).
NON_FIRM = {
    "RESOLVED_CO_CITATION": {"V9-S01", "V9-S02", "V9-S03"},
    "PROBABLE": {"AR_ALT", "V6-S02", "V6-S10", "V6-S13", "V6-S22", "V7-S04", "V7-S16", "V8-S11", "V9-S08"},
    "CATEGORY_ONLY": {"SRC-AO", "AO"},
    "UNRESOLVABLE": {"V6-S03"},
}
# Defect D-WSD-001 (WS-D finding): v3 register rows inherited from v2 whose n_records/records_using
# were not recounted under the v3 grammar. Value = records the inventory finds but the register omits.
KNOWN_STALE_USAGE = {
    "SC_GILL": {"J-03"}, "SC_PPS": {"J-01"}, "SC_VK": {"J-02"},
    "SRC-AA": {"COI-002", "COI-043"}, "SRC-AR": {"COI-002", "COI-043", "COI-044"},
    "SRC-AR185": {"COI-046"}, "SRC-JETHI": {"COI-039", "COI-041"},
    "SRC-VIR": {"COI-039", "COI-041", "COI-044"},
}


class CitationRegisterCompleteness(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inv, cls.uncoded, cls.placeholders = BCI.inventory()

    def test_frozen_kb_hash_is_the_inventory_input(self):
        self.assertEqual(hashlib.sha256(BCI.KB.read_bytes()).hexdigest(), KB_SHA)

    def test_exactly_87_codes_no_missing_no_extra(self):
        self.assertEqual(len(self.inv), 87)
        self.assertEqual(len(REG_ROWS), 87, "register must have exactly one row per code")
        self.assertEqual(len(REG), len(REG_ROWS), "duplicate code rows in register")
        self.assertEqual(sorted(set(self.inv) - set(REG)), [], "codes used but unregistered")
        self.assertEqual(sorted(set(REG) - set(self.inv)), [], "register codes not used by any record")

    def test_class_counts_exactly_baseline(self):
        got = collections.Counter(REG[c]["resolution_class"] for c in self.inv)
        self.assertEqual(dict(got), BASELINE_CLASSES)
        firm = sum(got[k] for k in FIRM)
        self.assertEqual(firm, 72)
        self.assertEqual(firm + got["RESOLVED_CO_CITATION"], 75)

    def test_non_firm_class_membership_is_pinned(self):
        for cls_name, codes in NON_FIRM.items():
            got = {c for c, r in REG.items() if r["resolution_class"] == cls_name}
            self.assertEqual(got, codes, cls_name)

    def test_records_without_codes_and_placeholders(self):
        self.assertEqual(len(self.uncoded), 269)
        self.assertEqual(len(set(self.uncoded)), 269)
        coded = {r for recs in self.inv.values() for r in recs}
        self.assertEqual(len(coded), 658 - 269)
        self.assertEqual(coded & set(self.uncoded), set())
        self.assertEqual({k: sorted(v) for k, v in self.placeholders.items()}, {"VERIFY": ["CM-026", "CM-040"]})

    def test_builder_main_exit_and_published_coverage_agree(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = BCI.main()
        self.assertEqual(rc, 0)
        out = json.loads(buf.getvalue())
        self.assertEqual(out["codes_used"], COVERAGE["denominator_codes"])
        self.assertEqual(out["by_class"], COVERAGE["by_class"])
        self.assertEqual(out["records_without_codes"], COVERAGE["records_without_any_code"])
        self.assertTrue(COVERAGE["firm"].startswith("72/87"))
        self.assertTrue(COVERAGE["inclusive_with_co_citation"].startswith("75/87"))
        self.assertEqual(out["usage_links"], COVERAGE["usage_weighted_record_code_links"]["total_links"])

    def test_firm_codes_carry_evidence(self):
        for c, r in REG.items():
            if r["resolution_class"] == "CORROBORATED_OFFICIAL":
                self.assertTrue(r["official_corroboration_url"].startswith("https://"), c)
                self.assertRegex(r["official_sha256"], r"^[0-9a-f]{64}$", c)
            if r["resolution_class"] in FIRM:
                self.assertTrue(r["resolved_identity"].strip(), c)
                self.assertTrue(r["evidence_record_quotes"].strip(), c)

    def test_register_usage_counts_only_known_stale_rows(self):
        stale = {}
        for c, recs in self.inv.items():
            listed = {x for x in REG[c]["records_using"].split(";") if x}
            self.assertLessEqual(listed, recs, f"{c}: register lists records that do not use the code")
            if int(REG[c]["n_records"]) != len(recs) or listed != recs:
                stale[c] = recs - listed
                self.assertEqual(int(REG[c]["n_records"]), len(listed), c)
        self.assertEqual(stale, KNOWN_STALE_USAGE)


if __name__ == "__main__":
    unittest.main()
