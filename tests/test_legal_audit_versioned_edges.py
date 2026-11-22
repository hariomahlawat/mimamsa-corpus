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
        for r in rows("WS-A-STATUTORY/army_act_amendment_chain_addendum_cycle3.csv"):  # declared input since reconcile
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
            st = e["effective_date_status"]
            if st.startswith("CONFLICTING_EVIDENCE"):
                # every date listed must be a STATED effective date of one of the edge's member evidence rows
                listed = re.findall(r"\d{4}-\d{2}-\d{2}", st)
                self.assertGreaterEqual(len(listed), 2, st)
                stated = {x["effective_date"] for x in srcs if x["effective_date_status"].startswith("STATED_IN_INSTRUMENT")}
                for d in listed:
                    self.assertIn(d, stated, (e["version_id"], st))
                self.assertEqual(e["valid_from"], "", "conflicting stated dates must not be resolved")
                self.assertIn("EVIDENCE_EFFECTIVE_DATE_CONFLICT", e["flags"].split(";"))
            else:
                self.assertIn(st, {x["effective_date_status"] for x in srcs}, e["version_id"])

    def test_conflicting_evidence_path_fixture(self):
        """Two descriptions of one event (same instrument key and publication date) stating different commencement
        dates: grouped, flagged, never resolved, and the status lists exactly the stated dates."""
        base = {"source": "fixture", "change": "x", "sub": False, "ocr": False, "det": "", "conflict": "",
                "ikey": "SRO-216-1988", "pub": "1988-09-17"}
        a = dict(base, version_id="FX-1", eff="1988-09-17", status="STATED_IN_INSTRUMENT (on publication)")
        b = dict(base, version_id="FX-2", eff="1979-06-04", status="STATED_IN_INSTRUMENT (deemed from 4 June 1979)")
        groups = VE.group_events([a, b])
        self.assertEqual(len(groups), 1)
        g = groups[0]
        self.assertEqual(g["evidence_ids"], ["FX-1", "FX-2"])
        self.assertEqual(g["eff"], "")
        self.assertTrue(g["status"].startswith("CONFLICTING_EVIDENCE"))
        self.assertEqual(sorted(re.findall(r"\d{4}-\d{2}-\d{2}", g["status"])), ["1979-06-04", "1988-09-17"])
        self.assertIn("EVIDENCE_EFFECTIVE_DATE_CONFLICT", g["conflicts"])

    def test_r2_distinct_fields_model(self):
        """r.2 (S.R.O. 216/1988): commencement 1988-09-17 and retrospective deemed effect 1979-06-04 are DISTINCT
        fields of ONE event, flagged for AQ-06 - not CONFLICTING_EVIDENCE.

        Data correction, not a weakening: the earlier assertion that r.2 was CONFLICTING_EVIDENCE reflected
        WS-A's provision_change_log.csv holding the deemed date (1979-06-04) in effective_date for PCL-BL-02.
        WS-A corrected the row in place (18ae1078: effective_date 1988-09-17 + retrospective_deemed_effect_from
        1979-06-04), matching ARMY-RULES-CHAIN-01 after PR #28. A genuine conflict (two different STATED
        commencement dates) is still flagged: see test_conflicting_evidence_path_fixture."""
        groups = VE.versions().get(("AR", "2"), [])
        g = [x for x in groups if {"PCL-216-1988", "PCL-BL-02"} <= set(x["evidence_ids"])]
        self.assertEqual(len(g), 1, "one amendment event for r.2 under S.R.O. 216/1988")
        g = g[0]
        self.assertEqual(g["eff"], "1988-09-17")
        self.assertTrue(g["status"].startswith("STATED_IN_INSTRUMENT"))
        self.assertEqual(g["retro"], "1979-06-04")
        self.assertEqual(g["pub"], "1988-09-17")
        self.assertNotIn("EVIDENCE_EFFECTIVE_DATE_CONFLICT", g["conflicts"])
        self.assertNotIn("EVIDENCE_DEEMED_EFFECT_CONFLICT", g["conflicts"])

    def test_retrospective_fixture_is_not_a_conflict(self):
        base = {"source": "fixture", "change": "x", "sub": False, "ocr": False, "det": "", "conflict": "",
                "ikey": "SRO-216-1988", "pub": "1988-09-17", "eff": "1988-09-17", "status": "STATED_IN_INSTRUMENT (on publication)"}
        g = VE.group_events([dict(base, version_id="FX-A", retro="1979-06-04"), dict(base, version_id="FX-B", retro="")])
        self.assertEqual(len(g), 1)
        self.assertEqual((g[0]["eff"], g[0]["retro"]), ("1988-09-17", "1979-06-04"))
        self.assertEqual(g[0]["conflicts"], [])
        two = VE.group_events([dict(base, version_id="FX-A", retro="1979-06-04"), dict(base, version_id="FX-B", retro="1980-01-01")])
        self.assertIn("EVIDENCE_DEEMED_EFFECT_CONFLICT", two[0]["conflicts"])

    def test_edges_keep_publication_commencement_and_deemed_effect_distinct(self):
        for e in EDGES:
            if e["retrospective_deemed_effect_from"]:
                self.assertIn("RETROSPECTIVE_DEEMED_EFFECT_AQ06", e["flags"].split(";"))
                self.assertNotEqual(e["valid_from"], e["retrospective_deemed_effect_from"])
            if "RETROSPECTIVE_DEEMED_EFFECT_AQ06" in e["flags"].split(";"):
                self.assertRegex(e["retrospective_deemed_effect_from"], ISO)


class AddendumInput(unittest.TestCase):
    """WS-A army_act_amendment_chain_addendum_cycle3.csv is a declared, pinned input and its rows are read."""

    def test_declared_and_pinned(self):
        self.assertIn("wsa_aa_chain_addendum", VE.INPUTS)
        self.assertEqual(VE.INPUTS["wsa_aa_chain_addendum"].name, "army_act_amendment_chain_addendum_cycle3.csv")
        self.assertIn("wsa_aa_chain_addendum", SUMMARY["inputs"])
        self.assertIn("army_act_amendment_chain_addendum_cycle3.csv", (WSD / "relation_graph_versioned_report.md").read_text(encoding="utf-8"))

    def test_rows_are_read(self):
        V = VE.versions()
        ids = {i for gs in V.values() for g in gs for i in g["evidence_ids"]}
        for row in ("AA-C3-01", "AA-C3-02", "AA-C3-03"):
            self.assertIn(row, ids, f"addendum row {row} not read")
        self.assertNotIn("AA-C3-04", ids, "extension-only row ('none ...') must stay excluded")
        self.assertTrue(any(e["version_source"].endswith("army_act_amendment_chain_addendum_cycle3.csv") or
                            "AA-C3-" in e["evidence_refs"] for e in EDGES))

    def test_extends_row_joins_the_existing_event(self):
        V = VE.versions()
        g = [x for x in V.get(("AA", "137"), []) if "AA-C3-01" in x["evidence_ids"]]
        self.assertEqual(len(g), 1)
        self.assertIn("AA-02", g[0]["evidence_ids"], "AA-C3-01 declares 'extends AA-02': same instrument, one event")

    def test_instrument_not_examined_is_text_only_never_stated(self):
        for e in EDGES:
            refs = e["evidence_refs"].split(";")
            if any(r in ("AA-C3-01", "AA-C3-02", "AA-C3-03") for r in refs):
                self.assertIn("INSTRUMENT_NOT_EXAMINED", e["flags"].split(";"), e)
                self.assertIn("TEXT_OR_OCR_EVIDENCE_ONLY", e["flags"].split(";"), e)
                if set(refs) <= {"AA-C3-01", "AA-C3-02", "AA-C3-03"}:
                    self.assertEqual(e["valid_from"], "", e)

    def test_no_amending_act_own_sections_from_addendum(self):
        # AA-C3-03's change text cites 's. 2 and the First Schedule' of Act 36/1957; only s.194 is an Army Act provision
        V = VE.versions()
        aa3 = sorted(k[1] for k, gs in V.items() for g in gs if k[0] == "AA" and "AA-C3-03" in g["evidence_ids"])
        self.assertEqual(aa3, ["194"])


class VersionedEdgesTail(unittest.TestCase):
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
