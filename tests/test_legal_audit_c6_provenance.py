"""C6-01 provenance-recovery package: reproducibility and safeguards (offline; no held binaries needed)."""
import csv, hashlib, json, subprocess, sys, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PKG = REPO / "legal_knowledge/audit_work/C6-01-PROVENANCE"
sys.path.insert(0, str(PKG / "tools"))
import build_provenance as P  # noqa: E402


def read(name):
    with open(PKG / "registers" / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class C6Provenance(unittest.TestCase):
    def test_rebuild_identical(self):
        for k, t in P.outputs().items():
            self.assertEqual((PKG / "registers" / k).read_text(encoding="utf-8"), t, k)

    def test_originals_and_c4_register_unchanged(self):
        h = lambda p: hashlib.sha256((REPO / p).read_bytes()).hexdigest()
        self.assertEqual(h("legal_knowledge/curated_originals/knowledge_base/v0.9/records_658.jsonl"), "9a8f0d193065762ffa987116dc761bcb734008d2a87a946f5591741f5befcfc1")
        self.assertEqual(h("legal_knowledge/curated_originals/case_law/v0.9/cases_53.jsonl"), "8b8d53cd1434f7c1c6eaebe77f1fe295fb8b81b755e93276999b4b40b3c8f89a")
        with open(REPO / "legal_knowledge/audit_work/CALIBRATION-02/registers/source_authentication_register.csv", encoding="utf-8") as f:
            self.assertEqual(sum(1 for _ in csv.DictReader(f)), 13)  # proposals never edit the original register

    def test_scope_and_denominators(self):
        s = json.loads((PKG / "registers/c6_01_summary.json").read_text())
        self.assertEqual(s["denominators"], {"held_unique_binaries_c5": 67, "held_binary_paths_c5": 93, "undocumented_copies_c5": 54,
                                             "scope_sources": 34, "scope_copies": 36})
        self.assertEqual(sum(s["outcomes_by_copy"].values()), 36)

    def test_classification_rules(self):
        allowed = {"PROVENANCE_DOCUMENTED", "PROVENANCE_PARTIALLY_DOCUMENTED", "IDENTITY_VERIFIED_PROVENANCE_UNDOCUMENTED",
                   "NO_RECOVERABLE_PROVENANCE", "AUTHENTICATION_PENDING"}
        for r in read("provenance_recovery_register.csv"):
            self.assertIn(r["proposed_outcome"], allowed)
            ids = r["identity_verification"]
            if r["proposed_outcome"] == "PROVENANCE_DOCUMENTED":
                self.assertIn(r["locator_strength"], ("FULL", "MD5_SIZE"), r["copy_id"])
                court = "-J-" in r["source_id"]
                self.assertTrue(("I:" in ids) or (court and "T:" in ids), r["copy_id"])
                self.assertEqual(r["contradictions"], "NONE_FOUND_IN_SEARCHED_REGISTERS")
            if "T:" in ids and "I:" not in ids:
                self.assertIn("-J-", r["source_id"], "text-layer identity accepted only for court copies")

    def test_proposals_match_documented_rows_and_c4_rule_inputs(self):
        rec = {r["sha256"]: r for r in read("provenance_recovery_register.csv")}
        held = {}
        with open(REPO / "legal_knowledge/audit_work/CALIBRATION-02/registers/held_sources_scratchpad.csv", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                held.setdefault(r["sha256"], set()).add(r["scratchpad_relative_path"])
        props = read("source_authentication_proposals.csv")
        self.assertEqual({p["sha256"] for p in props}, {s for s, r in rec.items() if r["proposed_outcome"] == "PROVENANCE_DOCUMENTED"})
        for p in props:
            self.assertEqual(p["authentication_state"], "PROVENANCE_DOCUMENTED")
            self.assertTrue(p["provenance_references"].strip())
            self.assertEqual({x.strip() for x in p["held_paths"].split(";")}, held[p["sha256"]])
            self.assertIn("PROPOSAL - not incorporated", p["limitations"])

    def test_isaac_untouched(self):
        isaac = "3f49a31464fec174cdbff5d9e194fa888ca00529b6246eacdc8ac2368eab4653"
        self.assertNotIn(isaac, {r["sha256"] for r in read("provenance_recovery_register.csv")})
        self.assertNotIn(isaac, {p["sha256"] for p in read("source_authentication_proposals.csv")})

    def test_non_primary_classes_for_records_and_incomplete_copies(self):
        cls = {p["sha256"][:8]: p["effective_source_class"] for p in read("source_authentication_proposals.csv")}
        self.assertEqual(cls.get("fa51a4b1"), "NON_PRIMARY_PARLIAMENTARY_RECORD")   # RS papers-laid page
        self.assertEqual(cls.get("29f6fa2c"), "NON_PRIMARY_OFFICIAL_PUBLICATION_COPY")  # incomplete ER 2023 copy

    def test_coverage_baseline_matches_cycle5(self):
        s = json.loads((PKG / "registers/c6_01_summary.json").read_text())["coverage_impact"]
        c5 = json.loads((REPO / "legal_knowledge/audit_work/SOURCE-LIBRARY-C5/registers/coverage_summary.json").read_text())
        for k in ("crosswalk_kb_items_by_status", "crosswalk_case_rows_by_status", "kb_records_by_anchor_class"):
            self.assertEqual(s["baseline"][k], c5[k])

    def test_simulation_does_not_leak_into_cycle5_registers(self):
        sys.path.insert(0, str(REPO / "legal_knowledge/audit_work/SOURCE-LIBRARY-C5/tools"))
        import build_registers as B
        P.coverage_impact(read("source_authentication_proposals.csv"))
        for k, t in B.build().items():
            self.assertEqual((REPO / "legal_knowledge/audit_work/SOURCE-LIBRARY-C5/registers" / k).read_text(encoding="utf-8"), t, k)


class C6Prep(unittest.TestCase):
    PREP = REPO / "legal_knowledge/audit_work/C6-PREP/registers"

    def rows(self, name):
        with open(self.PREP / name, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def test_no_approval_no_correspondence(self):
        for r in self.rows("c6_02_batch_a_files.csv"):
            self.assertEqual(r["approval_state"], "NOT_APPROVED")
            self.assertNotIn("aftjabalpur", r["download_url"])
        for r in self.rows("c6_03_desw_package.csv"):
            self.assertIn(r["approval_state"], ("NOT_APPROVED", "n/a"))
        for r in self.rows("c6_04_custodian_request_inventory.csv"):
            self.assertEqual(r["correspondence"], "NONE SENT (not authorised)")

    def test_incomplete_er2023_kept_separate(self):
        self.assertTrue(any("29f6fa2c" in r["size_pin"] and r["acq_c5_id"].startswith("HELD") for r in self.rows("c6_03_desw_package.csv")))

    def test_adviser_pack_unchanged_and_no_determination(self):
        s = json.loads((self.PREP / "c6_05_adviser_pack_status.json").read_text())
        self.assertEqual((s["c4_adviser_topics"], s["c4_calibration_escalations"], s["ws_b_inconsistencies_open"], s["determinations_made"]), (13, 29, 13, 0))
        self.assertEqual(s["reserved_states"]["C5-CF-C-01"], "CONFLICTING (r.23(3))")
        self.assertEqual(s["reserved_states"]["C5-CF-SC4-01"], "OPEN (r.182)")


if __name__ == "__main__":
    unittest.main()
