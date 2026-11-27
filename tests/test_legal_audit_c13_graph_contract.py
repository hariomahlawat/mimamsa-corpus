"""C13-A5 graph export: IC-01 data contract, candidate/reviewed separation, restricted-material exclusion."""
import gzip
import hashlib
import json
import unittest
from pathlib import Path

PKG = Path(__file__).resolve().parents[1] / "legal_knowledge" / "audit_work" / "C13-A5-GRAPH"
G = PKG / "graph"
FOUO_SHA = "4284820e5bc2fb7f52ae9fbe8a61650f1579e9b6389ba206a916a69fed016b14"
FOUO_DOC = "regs-regulations-for-the-air-force-reprinted-edition-2000"
ALWAYS_CANDIDATE = {"OVERRULES", "DISAPPROVES", "DOUBTS", "AMENDS_PROVISION_VERSION", "SUBSTITUTES_PROVISION_TEXT",
                    "INSERTS_PROVISION", "OMITS_PROVISION", "REPEALS_INSTRUMENT", "SAVES_OR_TRANSITIONS"}


def text(p):
    return gzip.decompress(p.read_bytes()).decode("utf-8") if p.suffix == ".gz" else p.read_text(encoding="utf-8")


def jsonl(p):
    return [json.loads(l) for l in text(p).splitlines() if l.strip()]


class GraphContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nodes = jsonl(G / "nodes.jsonl.gz")
        cls.cand = jsonl(G / "edges_candidate.jsonl.gz")
        cls.revd = jsonl(G / "edges_reviewed.jsonl")
        cls.edges = cls.cand + cls.revd

    def test_schema_validation(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema not installed")
        vn = jsonschema.Draft202012Validator(json.loads((PKG / "schema" / "graph_node.schema.json").read_text()))
        ve = jsonschema.Draft202012Validator(json.loads((PKG / "schema" / "graph_edge.schema.json").read_text()))
        bad_n = [n["node_id"] for n in self.nodes if list(vn.iter_errors(n))]
        bad_e = [e["edge_id"] for e in self.edges if list(ve.iter_errors(e))]
        self.assertEqual((bad_n[:5], bad_e[:5]), ([], []))

    def test_states_are_separated(self):
        self.assertTrue(all(e["verification_state"] != "REVIEWED_AI_DOCUMENTARY_NOT_LEGAL_VALIDATION" for e in self.cand))
        self.assertTrue(all(e["verification_state"] == "REVIEWED_AI_DOCUMENTARY_NOT_LEGAL_VALIDATION" for e in self.revd))
        self.assertFalse({e["edge_id"] for e in self.cand} & {e["edge_id"] for e in self.revd})
        self.assertNotIn("LEGALLY_VALIDATED", json.dumps(self.revd[:50]))

    def test_overrules_and_adverse_edges_always_candidates(self):
        self.assertFalse([e["edge_id"] for e in self.revd if e["edge_type"] in ALWAYS_CANDIDATE])

    def test_overrules_only_explicit_supreme_court_own_voice(self):
        ov = [e for e in self.edges if e["edge_type"] == "OVERRULES"]
        self.assertTrue(ov)
        for e in ov:
            self.assertEqual(e["court"], "Supreme Court of India", e["edge_id"])
            self.assertRegex(e["attributes"]["cue"].lower(), r"over-?\s?rul")
            self.assertEqual(e["attributes"]["voice"], "COURT_OWN_VOICE")
            self.assertNotIn(e["attributes"]["opinion"], ("SEPARATE_OPINION", "DISSENT"))
            self.assertEqual(e["attributes"]["overruling_language"], "EXPLICIT")

    def test_declaratory_wording_is_not_overrules(self):
        for e in self.edges:
            if e["edge_type"] == "DISAPPROVES" and "lay down" in (e["attributes"].get("cue") or ""):
                self.assertEqual(e["attributes"]["overruling_language"], "DECLARATORY_ONLY_NOT_EXPLICIT_OVERRULING")

    def test_every_edge_carries_required_contract_fields(self):
        for e in self.edges:
            self.assertIn(e["direction"], e["direction"])
            self.assertIn("extractor_version", e)
            if e["edge_class"] in ("CITATION", "JUDICIAL_TREATMENT", "STATUTORY_REFERENCE"):
                self.assertRegex(e["evidence"]["source_copy_sha256"], r"^[0-9a-f]{64}$")
                self.assertIsInstance(e["evidence"]["page"], int, e["edge_id"])
                self.assertTrue(e["evidence"]["passage"], e["edge_id"])
            if e["edge_type"] not in ("CITES", "CITES_PROVISION", "DECIDES_PROCEEDING", "HAS_PROVISION"):
                self.assertIn("UNVERIFIED_MARKER_REQUIRED", e["restrictions"], e["edge_id"])
            if e["target"] is None:
                self.assertTrue(e["target_raw"], e["edge_id"])

    def test_statutory_mention_kept_separate_from_applicability(self):
        cp = [e for e in self.edges if e["edge_type"] == "CITES_PROVISION"]
        self.assertTrue(cp)
        self.assertTrue(all(e["attributes"]["applicability"].startswith("NOT_INFERRED") for e in cp))
        self.assertTrue(all(not e["legal_effect"] for e in cp))

    def test_edge_targets_resolve_to_nodes(self):
        ids = {n["node_id"] for n in self.nodes}
        missing = [e["edge_id"] for e in self.edges if e["source"] not in ids or (e["target"] and e["target"] not in ids)]
        self.assertEqual(missing[:5], [])

    def test_research_restricted_layers_are_marked(self):
        for n in self.nodes:
            if n["node_type"] in ("PROPOSITION", "QUESTION_OF_LAW"):
                self.assertIn("NON_OPERATIONAL_RESEARCH_ONLY", n["restrictions"])
                self.assertIn("HIDDEN_FROM_USERS_THIS_CYCLE", n["restrictions"])
                self.assertEqual(n["attributes"]["status"], "AUTOMATED_CANDIDATE_NOT_VERIFIED")
            if n["node_type"] in ("FORM", "COMPETENT_AUTHORITY", "PROCEDURE", "ADMINISTRATIVE_REQUIREMENT"):
                self.assertIn("NON_OPERATIONAL_RESEARCH_ONLY", n["restrictions"])

    def test_restricted_material_absent_from_every_package_output(self):
        for p in sorted(PKG.rglob("*")):
            if p.is_file() and p.suffix in (".gz", ".jsonl", ".json", ".csv") and "hf" not in p.parts[-2:-1]:
                t = text(p)
                if p.name in ("IDENTITY_SUMMARY_C13.json",):
                    continue  # records only the withheld count and the register hash
                self.assertNotIn(FOUO_SHA, t, str(p))
                self.assertNotIn(FOUO_DOC, t, str(p))

    def test_manifest_hashes_match(self):
        m = json.loads((G / "IC01_EXPORT_MANIFEST.json").read_text())
        for name, info in m["files"].items():
            self.assertEqual(hashlib.sha256(text(G / name).encode()).hexdigest(), info["sha256"], name)
        self.assertEqual(m["contract"], "IC-01")

    def test_exported_passage_hash_recomputes(self):
        for e in self.edges:
            ev = e["evidence"]
            if ev["passage"]:
                self.assertEqual(hashlib.sha256(ev["passage"].encode()).hexdigest(), ev["passage_sha256"], e["edge_id"])
                self.assertLessEqual(len(ev["passage"]), 600)
            if e["edge_class"] == "JUDICIAL_TREATMENT":
                self.assertIsInstance(ev["char_start"], int, e["edge_id"])
                self.assertGreaterEqual(ev["char_end"], ev["char_start"])

    def test_low_reliability_types_are_flagged(self):
        for e in self.edges:
            if e["edge_type"] in ("DISTINGUISHES", "APPLIES", "EXPLAINS", "DOUBTS"):
                self.assertIn("LOW_RELIABILITY_CANDIDATE", e["restrictions"], e["edge_id"])
                self.assertEqual(e["attributes"]["reliability"], "LOW_RELIABILITY_CANDIDATE")

    def test_no_displayable_precision(self):
        ev = json.loads((G / "EDGE_TYPE_EVALUATION_C13.json").read_text())
        self.assertFalse(ev["treatment_dev_eval_in_sample"]["displayable"])
        for t, v in ev["per_edge_type"].items():
            self.assertIsNone(v.get("displayable_measured_precision"), t)
            if v.get("development_in_sample"):
                self.assertFalse(v["development_in_sample"]["displayable"])
        self.assertIn("independent_ai_review_f915ac11", ev["per_edge_type"]["FOLLOWS"])

    def test_overrules_unique_per_passage_and_target(self):
        seen = set()
        for e in self.edges:
            if e["edge_type"] == "OVERRULES":
                k = (e["evidence"]["doc_id"], e["evidence"]["char_start"], e["target"], e["target_raw"])
                self.assertNotIn(k, seen)
                seen.add(k)
                if e["target_raw"]:
                    self.assertFalse(e["target_raw"][0].islower(), e["target_raw"][:30])

    def test_summary_counts_match_files(self):
        s = json.loads((G / "GRAPH_SUMMARY_C13.json").read_text())
        self.assertEqual(s["nodes"], len(self.nodes))
        self.assertEqual(s["edges"], len(self.edges))
        self.assertEqual(s["edges_reviewed"], len(self.revd))
        self.assertEqual(s["restricted_hits_in_output"], 0)


if __name__ == "__main__":
    unittest.main()
