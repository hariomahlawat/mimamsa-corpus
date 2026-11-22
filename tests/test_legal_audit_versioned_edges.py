"""WS-D cycle 3: version- and date-bounded statutory edges.

No edge may point to a version whose effective date is unstated unless the edge is flagged
EFFECTIVE_DATE_UNSTATED; stated dates must be the register's own; fixed determinations are carried unchanged;
non-version rows never become edges; regeneration is byte-identical. Structural only."""
import csv
import hashlib
import importlib.util
import io
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AW = ROOT / "legal_knowledge" / "audit_work"
WSD = AW / "WS-D-QUALITY"
SPEC = importlib.util.spec_from_file_location("wsd_vedges", WSD / "scripts" / "build_versioned_edges.py")
VE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VE)
EDGES = list(csv.DictReader(io.StringIO((WSD / "relation_graph_versioned_edges.csv").read_text(encoding="utf-8"), newline="")))
SUMMARY = json.loads((WSD / "relation_graph_versioned_summary.json").read_text(encoding="utf-8"))
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def rows(rel):
    return list(csv.DictReader(io.StringIO((AW / rel).read_text(encoding="utf-8"), newline="")))


class VersionedEdges(unittest.TestCase):
    def test_edges_exist(self):
        self.assertGreater(len(EDGES), 0)
        self.assertEqual(SUMMARY["summary"]["edges"], len(EDGES))

    def test_no_unstated_effective_date_without_flag(self):
        for e in EDGES:
            stated = e["effective_date_status"].startswith("STATED_IN_INSTRUMENT")
            if not e["valid_from"]:
                self.assertIn("EFFECTIVE_DATE_UNSTATED", e["flags"].split(";"), (e["record_id"], e["version_id"]))
            if "EFFECTIVE_DATE_UNSTATED" in e["flags"].split(";"):
                self.assertEqual(e["valid_from"], "", (e["record_id"], e["version_id"]))
            if e["valid_from"]:
                self.assertTrue(stated, (e["record_id"], e["version_id"]))
                self.assertRegex(e["valid_from"], ISO)

    def test_stated_dates_are_the_registers_own(self):
        reg = {}
        for r in rows("ARMY-RULES-CHAIN-01/statutory_version_register_seed.csv"):
            reg[f"{r['provision']}@{r['version']}"] = r
        for r in rows("WS-A-STATUTORY/provision_change_log.csv"):
            reg[r["change_id"]] = r
        for r in rows("WS-A-STATUTORY/army_act_amendment_chain.csv"):
            reg[r["chain_id"]] = r
        for e in EDGES:
            self.assertIn(e["version_id"], reg, e["version_id"])
            # Grouped amendment events (review fix PR #25): every evidence row must exist, the version_id must be one
            # of them, valid_from must be a STATED effective date of one of them, and the status must be one of theirs.
            refs = e["evidence_refs"].split(";")
            self.assertIn(e["version_id"], refs)
            for ref in refs:
                self.assertIn(ref, reg, ref)
            srcs = [reg[ref] for ref in refs]
            if e["valid_from"]:
                self.assertIn(e["valid_from"], {x["effective_date"] for x in srcs if x["effective_date_status"].startswith("STATED_IN_INSTRUMENT")},
                              e["version_id"])
            if not e["effective_date_status"].startswith("CONFLICTING_EVIDENCE"):
                self.assertIn(e["effective_date_status"], {x["effective_date_status"] for x in srcs}, e["version_id"])

    def test_valid_to_not_before_valid_from(self):
        for e in EDGES:
            if e["valid_from"] and e["valid_to"]:
                self.assertLessEqual(e["valid_from"], e["valid_to"], (e["record_id"], e["version_id"]))

    def test_fixed_determinations_carried_unchanged(self):
        seen = set()
        for e in EDGES:
            if e["version_id"].startswith("r.23(3)@"):
                self.assertEqual(e["determination_state"], "CONFLICTING"); seen.add("r23")
            if e["version_id"].startswith("r.193@"):
                self.assertEqual(e["determination_state"].split()[0], "OPEN"); seen.add("r193")
            if e["version_id"].startswith("r.194@"):
                self.assertIn(e["determination_state"].split()[0], ("OPEN", "PROPOSAL")); seen.add("r194")
            self.assertNotRegex(e["determination_state"].upper(), r"APPROVED|RESOLVED|ADJUDICATED")
        self.assertTrue({"r23"} <= seen)

    def test_non_version_rows_never_edges(self):
        for e in EDGES:
            self.assertNotRegex(e["change_or_version"], r"NO AMENDMENT|\(no amendment\)|\(not amendment\)")

    def test_inputs_pinned_and_current(self):
        for k, v in SUMMARY["inputs"].items():
            got = hashlib.sha256((ROOT / v["path"]).read_bytes()).hexdigest()
            if got != v["sha256"]:
                self.fail(f"input {k} changed - regenerate versioned edges: run scripts/build_versioned_edges.py")

    def test_regeneration_is_byte_identical(self):
        for p, text in VE.outputs().items():
            self.assertEqual(p.read_text(encoding="utf-8"), text, p.name)


if __name__ == "__main__":
    unittest.main()
