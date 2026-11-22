"""WS-D artifact integrity: committed quality artifacts must equal what their deterministic scripts produce
from the frozen inputs, and must never inflate the baseline. Structural checks only; not legal verification."""
import csv
import importlib.util
import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WSD = ROOT / "legal_knowledge" / "audit_work" / "WS-D-QUALITY"
KB = ROOT / "legal_knowledge" / "curated_originals" / "knowledge_base" / "v0.9" / "records_658.jsonl"


def load(name):
    spec = importlib.util.spec_from_file_location(f"wsd_{name}", WSD / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class HashReproduction(unittest.TestCase):
    def test_frozen_hashes_reproduce_without_private_bytes(self):
        hr = load("hash_reproduction")
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = hr.main([])
        self.assertEqual(rc, 0)
        out = json.loads(buf.getvalue())
        self.assertTrue(all(f["match"] for f in out["files"]))
        kinds = {m["batch"]: m["by_kind"] for m in out["manifests"]}
        self.assertEqual(kinds["PILOT-01"], {"KB_RECORD": {"total": 25, "match": 25},
                                             "MML_PROVISION": {"total": 12, "match": 12},
                                             "CASE_ROW": {"total": 6, "match": 6}})
        self.assertEqual(kinds["R23-VERIFY-01"], {"KB_RECORD": {"total": 1, "match": 1},
                                                  "MML_PROVISION": {"total": 1, "match": 1}})

    def test_committed_report_records_all_checks_matching(self):
        rep = json.loads((WSD / "hash_reproduction.json").read_text(encoding="utf-8"))
        self.assertTrue(rep["summary"]["all_run_checks_match"])
        self.assertEqual(rep["summary"]["failures"], [])


class PlaintextIndex(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load("build_plaintext_index")
        cls.rows, cls.uncoded = cls.mod.build()
        cls.committed = list(csv.DictReader(io.StringIO((WSD / "plaintext_citation_index.csv").read_text(encoding="utf-8"))))
        cls.kb = {json.loads(l)["id"]: json.loads(l) for l in KB.read_text(encoding="utf-8").splitlines() if l.strip()}

    def test_covers_exactly_the_269_uncoded_records(self):
        self.assertEqual(len(self.uncoded), 269)
        self.assertEqual({r["record_id"] for r in self.committed}, set(self.uncoded))

    def test_committed_csv_equals_regeneration(self):
        regen = [{k: str(v) for k, v in r.items()} for r in self.rows]
        self.assertEqual(regen, self.committed)

    def test_offsets_slice_exact_original_text(self):
        for r in self.committed:
            rec = self.kb[r["record_id"]]
            ref = rec["references"]
            self.assertEqual(ref[int(r["ref_start"]):int(r["ref_end"])], r["exact_text"], r["record_id"])
            if r["body_start"]:
                b = int(r["body_start"])
                self.assertEqual(rec["body"][b:b + len(r["exact_text"])], r["exact_text"], r["record_id"])

    def test_no_unclassified_segments_and_hints_are_not_authority(self):
        self.assertNotIn("UNCLASSIFIED", {r["category"] for r in self.committed})
        self.assertIn("NOT legal", self.mod.__doc__)


class CitationScore(unittest.TestCase):
    def test_score_is_not_inflated(self):
        s = json.loads((WSD / "citation_resolution_score.json").read_text(encoding="utf-8"))
        c = s["code_level"]
        self.assertEqual((c["confirmed"]["numerator"], c["confirmed"]["denominator"]), (72, 87))
        self.assertEqual(c["inferred_co_citation"]["numerator"], 3)
        self.assertEqual(c["unresolved"]["numerator"], 12)
        self.assertEqual(c["confirmed_plus_inferred"]["numerator"], 75)
        self.assertNotIn("RESOLVED_CO_CITATION", s["definitions"]["CONFIRMED"])
        self.assertEqual(s["record_level"]["records_without_codes_plaintext_only"], 269)
        self.assertEqual(s["record_level"]["denominator_all_records"], 658)


if __name__ == "__main__":
    unittest.main()


class RelationGraph(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.S = load("relation_graph").build(None)  # no crawler corpus ref in CI checkouts
        cls.committed = json.loads((WSD / "relation_graph_summary.json").read_text(encoding="utf-8"))

    def test_no_dangling_edges_and_no_id_collisions(self):
        self.assertEqual({k: v for k, v in self.S["dangling"].items() if v}, {})
        for k in ("kb_id_collisions", "case_id_collisions", "kb_case_id_overlap", "source_id_in_multiple_batches"):
            self.assertEqual(self.S["duplicates"][k], [], k)

    def test_no_duplicate_kb_bodies(self):
        for k in ("kb_body_exact", "kb_body_normalised", "kb_body_near_duplicates"):
            self.assertEqual(self.S["duplicates"][k], [], k)

    def test_committed_report_matches_regeneration(self):
        # Batch-specific keys added by later integrations (new audit batches) are not compared;
        # corpus-level keys and the batches present at commit time must match exactly.
        for part in ("orphans", "duplicates"):
            for k, v in self.committed[part].items():
                if k.split(".")[0] in ("PILOT-01", "R23-VERIFY-01") or "." not in k:
                    if k == "source_id_in_multiple_batches":
                        continue
                    self.assertEqual(self.S[part][k], v, k)
        corpus_edges = ("case.related_cases", "code.target_case", "kb.uses_code")
        for k in corpus_edges:
            self.assertEqual(self.S["edges"][k], self.committed["edges"][k], k)
