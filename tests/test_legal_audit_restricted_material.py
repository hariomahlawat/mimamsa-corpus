"""The restricted-material list must cover the FOUO RAF 2000 copy and all its derivatives (Cycle 13 section 31)."""
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("rm", ROOT / "scripts" / "restricted_material.py")
RM = importlib.util.module_from_spec(spec)
spec.loader.exec_module(RM)
FOUO = "4284820e5bc2fb7f52ae9fbe8a61650f1579e9b6389ba206a916a69fed016b14"
DOC = "regs-regulations-for-the-air-force-reprinted-edition-2000"


class RestrictedMaterial(unittest.TestCase):
    def test_fouo_copy_and_derivatives_are_restricted(self):
        self.assertTrue(RM.is_restricted(sha256=FOUO))
        self.assertTrue(RM.is_restricted(sha256=FOUO.upper()))
        self.assertTrue(RM.is_restricted(doc_id=DOC))
        self.assertTrue(RM.is_restricted(path=f"data/raw/indiacode/0000/{FOUO}.pdf"))
        self.assertTrue(RM.is_restricted(path=f"data/text/{DOC}.txt"))
        self.assertTrue(RM.is_restricted(path=f"data\\meta\\{DOC}.json"))
        self.assertTrue(RM.is_restricted(path=f"app/vault/{FOUO[:2]}/{FOUO}"))

    def test_ordinary_items_are_not_restricted(self):
        self.assertFalse(RM.is_restricted(sha256="0" * 64))
        self.assertFalse(RM.is_restricted(doc_id="act-army-1950"))
        self.assertFalse(RM.is_restricted(path="data/raw/sci/2009/abc.pdf"))

    def test_filter_and_config_shape(self):
        recs = [{"sha256": FOUO}, {"doc_id": DOC}, {"path": "data/text/x.txt"}]
        self.assertEqual(list(RM.filter_unrestricted(recs)), [{"path": "data/text/x.txt"}])
        cfg = json.loads((ROOT / "config" / "restricted_material.json").read_text(encoding="utf-8"))
        for it in cfg["items"]:
            for k in ("restriction_id", "source_sha256", "doc_id", "hosted_paths", "exclude_from", "status", "decision_note"):
                self.assertIn(k, it)
            self.assertTrue((ROOT / it["decision_note"]).is_file(), it["decision_note"])
            for scope in ("search_indexes", "embeddings", "application_release_bundles", "external_inference_services"):
                self.assertIn(scope, it["exclude_from"])


if __name__ == "__main__":
    unittest.main()
