"""WS-D cycle 3: proposed identity map (non-firm codes, short case names). No KPI inflation; byte-identical regeneration."""
import collections
import csv
import importlib.util
import io
import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WSD = ROOT / "legal_knowledge" / "audit_work" / "WS-D-QUALITY"
SPEC = importlib.util.spec_from_file_location("wsd_idmap", WSD / "scripts" / "build_identity_map.py")
IM = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(IM)
ROWS = list(csv.DictReader(io.StringIO((WSD / "identity_map_proposed.csv").read_text(encoding="utf-8"), newline="")))
DOC = json.loads((WSD / "identity_map_proposed.json").read_text(encoding="utf-8"))
NON_FIRM = {"AR_ALT", "V6-S02", "V6-S10", "V6-S13", "V6-S22", "V7-S04", "V7-S16", "V8-S11", "V9-S08",
            "SRC-AO", "AO", "V6-S03", "V9-S01", "V9-S02", "V9-S03"}


def ref_ok(ref):
    return subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--verify", "-q", ref], capture_output=True).returncode == 0


class IdentityMap(unittest.TestCase):
    def test_covers_exactly_the_15_non_firm_codes(self):
        self.assertEqual({r["item"] for r in ROWS if r["item_type"] == "CODE"}, NON_FIRM)

    def test_confidence_vocabulary_and_no_kpi_change(self):
        self.assertTrue({r["confidence"] for r in ROWS} <= {"confirmed", "inferred", "unresolved"})
        self.assertTrue(DOC["proposal_only"])
        self.assertEqual(DOC["published_kpi_unchanged"], "72/87")
        reg = list(csv.DictReader((ROOT / "legal_knowledge/audit_work/PILOT-01/registers/source_code_resolution_v3.csv").open(encoding="utf-8")))
        firm = sum(r["resolution_class"] in ("RESOLVED_RECORD_EXPLICIT", "CORROBORATED_OFFICIAL") for r in reg)
        self.assertEqual(firm, 72, "the frozen register must not be changed by a proposal")

    def test_confirmed_only_with_binding_evidence(self):
        for r in ROWS:
            if r["confidence"] == "confirmed":
                self.assertEqual(r["item_type"], "CODE")
                self.assertEqual(r["evidence_kind"], "RECORD_URL_FILENAME_EQUALS_OFFICIAL_CORPUS_ORIGINAL_FILENAME", r["item"])
                self.assertIn("original_filename", r["evidence"])

    def test_category_and_unresolvable_never_promoted(self):
        for r in ROWS:
            if r["current_state"] in ("CATEGORY_ONLY", "UNRESOLVABLE"):
                self.assertEqual(r["confidence"], "unresolved", r["item"])

    def test_short_case_names_never_confirmed(self):
        names = [r for r in ROWS if r["item_type"] == "CASE_NAME_REF"]
        self.assertTrue(names)
        self.assertNotIn("confirmed", {r["confidence"] for r in names})
        for r in names:
            if "UNRESOLVED_NO_COPY_IN_HAND" in r["evidence"] and not r["proposed_target"].startswith("DCLR-"):
                self.assertEqual(r["confidence"], "unresolved", r["item"])

    def test_inputs_pinned(self):
        for k in ("register", "wsb_identity", "wsc_lexicon", "wsc_inventory", "kb"):
            self.assertRegex(DOC["inputs"][k]["sha256"], r"^[0-9a-f]{64}$", k)

    @unittest.skipUnless(ref_ok("origin/raw-data"), "crawler corpus ref unavailable")
    def test_regeneration_is_byte_identical(self):
        files = IM.outputs("origin/raw-data")
        for p, text in files.items():
            self.assertEqual(p.read_text(encoding="utf-8"), text, p.name)


if __name__ == "__main__":
    unittest.main()
