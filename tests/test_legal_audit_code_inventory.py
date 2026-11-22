"""CI guard: the complete citation-code inventory of the frozen 658 records must stay fully registered.
Fails if a code used in the records lacks a register row, if a register row disappears, or if the inventory drifts
from the committed snapshot (e.g. a grammar change finds new codes) without the snapshot and register being updated."""
import csv
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
B = ROOT / "legal_knowledge" / "audit_work" / "PILOT-01"
SPEC = importlib.util.spec_from_file_location("build_code_inventory", B / "build_code_inventory.py")
BCI = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BCI)
SNAP = json.loads((B / "registers" / "code_inventory_snapshot.json").read_text(encoding="utf-8"))
REG = {r["code"]: r for r in csv.DictReader((B / "registers" / "source_code_resolution_v3.csv").open(encoding="utf-8"))}
CLASSES = {"CORROBORATED_OFFICIAL", "RESOLVED_RECORD_EXPLICIT", "RESOLVED_CO_CITATION", "PROBABLE", "CATEGORY_ONLY", "UNRESOLVABLE"}


class CodeInventoryCoverage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        inv, cls.uncoded, cls.placeholders = BCI.inventory()
        cls.inv = {c: sorted(r) for c, r in inv.items()}

    def test_inventory_matches_snapshot(self):
        self.assertEqual(self.inv, SNAP["codes"], "inventory drifted from snapshot: update snapshot AND register together")
        self.assertEqual(len(self.uncoded), SNAP["records_without_codes"])

    def test_complete_denominator_is_at_least_87(self):
        self.assertGreaterEqual(len(self.inv), 87)
        self.assertEqual(len(self.inv), SNAP["code_count"])

    def test_every_used_code_is_registered(self):
        self.assertEqual(sorted(set(self.inv) - set(REG)), [])

    def test_no_snapshot_code_silently_removed_from_register(self):
        self.assertEqual(sorted(set(SNAP["codes"]) - set(REG)), [])

    def test_register_rows_have_known_resolution_class(self):
        bad = {c: r["resolution_class"] for c, r in REG.items() if r["resolution_class"] not in CLASSES}
        self.assertEqual(bad, {})

    def test_placeholders_are_not_counted_as_codes(self):
        self.assertNotIn("VERIFY", self.inv)
        self.assertIn("VERIFY", self.placeholders)


if __name__ == "__main__":
    unittest.main()
