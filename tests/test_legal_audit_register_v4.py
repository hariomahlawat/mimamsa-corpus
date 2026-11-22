"""WS-D cycle 2: proposed v4 citation-code register (new file) vs frozen v3.

v4 must: leave v3 untouched (hash), contain exactly the 87 inventory codes, have usage columns equal to
the recomputed inventory for every code, differ from v3 only in n_records/records_using (plus two appended
columns), change no resolution class, and match its deterministic generator and diff. Structural only."""
import collections
import csv
import hashlib
import importlib.util
import io
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WSD = ROOT / "legal_knowledge" / "audit_work" / "WS-D-QUALITY"
P1 = ROOT / "legal_knowledge" / "audit_work" / "PILOT-01"
SPEC = importlib.util.spec_from_file_location("wsd_v4", WSD / "scripts" / "build_register_v4.py")
V4B = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(V4B)
SPEC2 = importlib.util.spec_from_file_location("bci_v4", P1 / "build_code_inventory.py")
BCI = importlib.util.module_from_spec(SPEC2)
SPEC2.loader.exec_module(BCI)


def rows(path):
    return list(csv.DictReader(io.StringIO(path.read_text(encoding="utf-8"), newline="")))


V3 = rows(P1 / "registers" / "source_code_resolution_v3.csv")
V4 = rows(WSD / "registers" / "source_code_resolution_v4_proposed.csv")
DIFF = rows(WSD / "registers" / "source_code_resolution_v4_diff.csv")
STALE = {"SC_GILL", "SC_PPS", "SC_VK", "SRC-AA", "SRC-AR", "SRC-AR185", "SRC-JETHI", "SRC-VIR"}


class RegisterV4Proposal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inv, _, _ = BCI.inventory()

    def test_frozen_v3_unchanged(self):
        self.assertEqual(hashlib.sha256((P1 / "registers" / "source_code_resolution_v3.csv").read_bytes()).hexdigest(), V4B.V3_SHA)

    def test_same_87_codes_in_same_order(self):
        self.assertEqual([r["code"] for r in V4], [r["code"] for r in V3])
        self.assertEqual(set(r["code"] for r in V4), set(self.inv))
        self.assertEqual(len(V4), 87)

    def test_usage_equals_inventory_for_every_code(self):
        for r in V4:
            recs = sorted(self.inv[r["code"]])
            self.assertEqual(r["records_using"], ";".join(recs), r["code"])
            self.assertEqual(int(r["n_records"]), len(recs), r["code"])

    def test_only_usage_columns_differ_and_classes_unchanged(self):
        for a, b in zip(V3, V4):
            for k in a:
                if k not in ("n_records", "records_using"):
                    self.assertEqual(a[k], b[k], (a["code"], k))
        cls = collections.Counter(r["resolution_class"] for r in V4)
        self.assertEqual(cls["RESOLVED_RECORD_EXPLICIT"] + cls["CORROBORATED_OFFICIAL"], 72)
        self.assertEqual(cls["RESOLVED_CO_CITATION"], 3)

    def test_diff_is_exactly_the_known_stale_rows_additions_only(self):
        self.assertEqual({d["code"] for d in DIFF}, STALE)
        self.assertEqual(len(DIFF), 16)
        added = 0
        for d in DIFF:
            if d["column"] == "records_using":
                old, new = set(d["v3_value"].split(";")), set(d["v4_value"].split(";"))
                self.assertTrue(old < new, d["code"])
                added += len(new - old)
        self.assertEqual(added, 14)
        self.assertEqual({r["code"] for r in V4 if r["change_vs_v3"] != "UNCHANGED"}, STALE)

    def test_committed_files_equal_regeneration(self):
        cols, regen, diff = V4B.build()
        self.assertEqual(list(V4[0].keys()), cols)
        self.assertEqual(regen, V4)
        self.assertEqual(diff, DIFF)

    def test_forms_used_column_is_not_stale(self):
        kb = {json.loads(l)["id"]: json.loads(l) for l in BCI.KB.read_text(encoding="utf-8").splitlines() if l.strip()}
        for r in V4:
            got = {V4B.FORMS_V3[f] for rid in self.inv[r["code"]] for f in V4B.forms(r["code"], kb[rid])}
            self.assertEqual(got, set(r["forms_used"].split("|")), r["code"])


if __name__ == "__main__":
    unittest.main()
