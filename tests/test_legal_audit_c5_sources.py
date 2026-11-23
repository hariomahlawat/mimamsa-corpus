"""Cycle 5 source-library package: structural and integrity tests (no network, no held binaries needed)."""
import csv, hashlib, json, re, sys, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PKG = REPO / "legal_knowledge/audit_work/SOURCE-LIBRARY-C5"
sys.path.insert(0, str(PKG / "tools"))
import build_registers as B  # noqa: E402
import check_c5 as C  # noqa: E402


def read(name):
    with open(PKG / "registers" / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class C5Package(unittest.TestCase):
    def test_validator_clean(self):
        old = sys.argv
        try:
            sys.argv = ["check_c5.py"]
            self.assertEqual(C.main(), 0)
        finally:
            sys.argv = old

    def test_rebuild_identical(self):
        for k, t in B.build().items():
            self.assertEqual((PKG / "registers" / k).read_text(encoding="utf-8"), t, k)

    def test_schema_matches_contract(self):
        sch = json.loads((PKG / "schemas/c5_registers.schema.json").read_text())
        self.assertEqual({k: v["columns"] for k, v in sch["registers"].items()}, B.COLS)

    def test_originals_unchanged(self):
        base = json.loads((PKG / "baseline/frozen_baseline_manifest.json").read_text())
        for k, rel in {"records_658": "legal_knowledge/curated_originals/knowledge_base/v0.9/records_658.jsonl",
                       "cases_53": "legal_knowledge/curated_originals/case_law/v0.9/cases_53.jsonl"}.items():
            self.assertEqual(hashlib.sha256((REPO / rel).read_bytes()).hexdigest(), base["original_corpus_sha256"][k])
        self.assertEqual(base["original_corpus_sha256"]["records_658"], "9a8f0d193065762ffa987116dc761bcb734008d2a87a946f5591741f5befcfc1")
        self.assertEqual(base["original_corpus_sha256"]["cases_53"], "8b8d53cd1434f7c1c6eaebe77f1fe295fb8b81b755e93276999b4b40b3c8f89a")

    def test_held_rows_hash_backed(self):
        held = {r["rehashed_sha256"] for r in csv.DictReader(open(PKG / "baseline/held_binaries_manifest.csv", encoding="utf-8"))}
        for r in read("source_master_register.csv"):
            shas = [s for s in r["sha256"].split(";") if s]
            if r["holding_state"].startswith("HELD"):
                self.assertTrue(shas and all(s in held for s in shas), r["source_id"])
            else:
                self.assertEqual(shas, [], r["source_id"])

    def test_primary_only_with_register_or_held_primary_class(self):
        auth = {r["sha256"]: r for r in csv.DictReader(open(REPO / "legal_knowledge/audit_work/CALIBRATION-02/registers/source_authentication_register.csv", encoding="utf-8"))}
        for r in read("source_master_register.csv"):
            if r["holding_state"].startswith("HELD_PRIMARY"):
                self.assertTrue(any(s in auth and auth[s]["authentication_state"] == "PROVENANCE_DOCUMENTED" for s in r["sha256"].split(";")),
                                f"{r['source_id']} is HELD_PRIMARY without a PROVENANCE_DOCUMENTED register row")

    def test_no_currency_or_approval_promotion(self):
        for r in read("source_master_register.csv"):
            self.assertNotEqual(r["amendment_chain_status"].split(" ")[0], "CHECKED_FOR_RELEVANT_PERIOD")
            self.assertNotRegex(" ".join(r.values()), r"LEGALLY_APPROVED|JAG_APPROVED|CURRENT_IN_FORCE")

    def test_acquisitions_not_approved_and_ranked(self):
        rows = read("acquisition_register.csv")
        self.assertEqual([int(r["rank"]) for r in rows], list(range(1, len(rows) + 1)))
        for r in rows:
            self.assertEqual(r["approval_state"], "NOT_APPROVED")
            self.assertNotIn("aftjabalpur", r["exact_location"])

    def test_injected_promotion_rejected(self):
        master = read("source_master_register.csv")
        bad = [dict(r, approval_state="APPROVED") for r in B.read(PKG / "inputs/acquisition_batches.csv")[:1]]
        with self.assertRaises(SystemExit):
            B.acquisition_rows(master, bad)
        t = dict(B.read(PKG / "inputs/target_publications.csv")[0], holding_state="HELD_GOVERNMENT_COMPILATION", held_sha256="")
        with self.assertRaises(SystemExit):
            B.master_rows({}, {}, {}, [t])
        t2 = dict(t, held_sha256="0" * 64)
        with self.assertRaises(SystemExit):
            B.master_rows({}, {}, {}, [t2])

    def test_crosswalk_complete_and_conservative(self):
        cw = read("corpus_crosswalk.csv")
        kb = {json.loads(l)["id"] for l in open(REPO / "legal_knowledge/curated_originals/knowledge_base/v0.9/records_658.jsonl", encoding="utf-8")}
        cs = {json.loads(l)["id"] for l in open(REPO / "legal_knowledge/curated_originals/case_law/v0.9/cases_53.jsonl", encoding="utf-8")}
        self.assertEqual({r["knowledge_base_record_id"] for r in cw if r["knowledge_base_record_id"]}, kb)
        self.assertEqual({r["case_id"] for r in cw if r["case_id"]}, cs)
        master = {r["source_id"]: r for r in read("source_master_register.csv")}
        amended = B.amended_rules()
        for r in cw:
            if r["evidence_status"] == "EXACT_ANCHOR":
                self.assertTrue(master[r["source_id"]]["holding_state"].startswith("HELD_PRIMARY"), r)
                if r["source_id"] == "C5-SRC-P0-ARMY-RULES-1954":
                    self.assertFalse(set(r["provision_id"].split("#", 1)[1].split(",")) & amended, r)

    def test_reserved_states(self):
        conf = {r["conflict_id"]: r for r in read("source_conflict_register.csv")}
        for cid, st in C.EXPECTED_RESERVED.items():
            self.assertEqual(conf[cid]["reserved_status"], st)
        self.assertEqual(sum(1 for c in conf if c.startswith("C5-CF-WSB-")), 13)

    def test_discovery_logs_no_binary_get_or_blocked_host(self):
        for log in (PKG / "discovery").glob("*_requests.tsv"):
            for line in open(log, encoding="utf-8"):
                p = line.rstrip("\n").split("\t")
                if len(p) >= 3:
                    self.assertNotIn("aftjabalpur", p[2])
                    if p[1].upper() == "GET":
                        self.assertIsNone(re.search(r"\.(pdf|docx?|zip)(\?|$)", p[2], re.I), line)


if __name__ == "__main__":
    unittest.main()
