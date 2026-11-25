"""C13-A5 review F04: the graph export conforms to Track B contract v1 and passes B's own validator."""
import gzip
import json
import subprocess
import sys
import tarfile
import tempfile
import unittest
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "legal_knowledge" / "audit_work" / "C13-A5-GRAPH"
OUT = PKG / "contract_v1"
FOUO_SHA = "4284820e5bc2fb7f52ae9fbe8a61650f1579e9b6389ba206a916a69fed016b14"


def records():
    return [json.loads(l) for l in gzip.decompress((OUT / "candidates_graph_edges.jsonl.gz").read_bytes()).decode().splitlines() if l]


class ContractV1(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.recs = records()
        cls.man = json.loads((OUT / "CONTRACT_V1_EXPORT_MANIFEST.json").read_text())

    def test_manifest_matches_file(self):
        import hashlib
        raw = gzip.decompress((OUT / "candidates_graph_edges.jsonl.gz").read_bytes())
        self.assertEqual(hashlib.sha256(raw).hexdigest(), self.man["sha256_uncompressed"])
        self.assertEqual(len(self.recs), self.man["records"])

    def test_candidate_invariants(self):
        for r in self.recs:
            self.assertEqual(r["status"], "AUTOMATED_CANDIDATE_NOT_VERIFIED")
            self.assertIsNone(r["review_ref"])
            self.assertIsNone(r["evaluation_ref"])          # F01: no displayable precision
            self.assertEqual(r["payload"]["confidence"], "extracted")
            self.assertNotIn(FOUO_SHA, json.dumps(r))
        rels = {r["payload"]["relation"] for r in self.recs}
        self.assertLessEqual(rels, {"CITES_JUDGMENT", "CITES_PROVISION", "QUOTES_PROVISION", "FOLLOWS_PROPOSITION",
                                    "OVERRULES_OR_LIMITS_PROPOSITION"})

    def test_low_reliability_types_not_exported(self):
        self.assertIn("LOW_RELIABILITY_CANDIDATE", self.man["not_exported"])
        ids = {r["candidate_id"].split(".")[-1] for r in self.recs}
        for l in gzip.open(PKG / "graph" / "edges_candidate.jsonl.gz", "rt"):
            e = json.loads(l)
            if "LOW_RELIABILITY_CANDIDATE" in e["restrictions"]:
                self.assertNotIn(e["edge_id"], ids)

    def test_track_b_validator_accepts_every_record(self):
        commit = self.man["contract_commit"]
        try:
            tar = subprocess.run(["git", "-C", str(ROOT), "archive", commit, "app/contract"], capture_output=True, check=True).stdout
        except subprocess.CalledProcessError:
            self.skipTest("Track B contract commit %s not available in this clone" % commit)
        reg = ROOT / "config" / "restricted_material.json"
        with tempfile.TemporaryDirectory() as d:
            tarfile.open(fileobj=BytesIO(tar)).extractall(d, filter="data")
            if reg.exists():
                regp = reg
            else:
                regp = Path(d) / "register.json"
                regp.write_bytes(subprocess.run(["git", "-C", str(ROOT), "show", "72fe7a75:config/restricted_material.json"],
                                                capture_output=True, check=True).stdout)
            data = Path(d) / "cand.jsonl"
            data.write_bytes(gzip.decompress((OUT / "candidates_graph_edges.jsonl.gz").read_bytes()))
            r = subprocess.run([sys.executable, "-B", "-m", "mimamsa_contract", "--register", str(regp), "--json",
                                "record", "candidate", str(data)], cwd=Path(d) / "app" / "contract", capture_output=True, text=True)
            rep = json.loads(r.stdout)
            self.assertTrue(rep["ok"], [i for i in rep["issues"] if i.get("severity") != "warning"][:3])
            self.assertEqual(rep["checked_records"], len(self.recs))
            self.assertEqual([i for i in rep["issues"] if i.get("severity") == "warning"][:3], [])


if __name__ == "__main__":
    unittest.main()
