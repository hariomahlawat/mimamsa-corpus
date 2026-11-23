"""CYCLE3-PLANNING generator controls (PR #30 review, P2 defect on the authentication queue).

Expected sets are derived here independently from the WS-B registers (stdlib only, no network):
  * every judgment that needs official-copy authentication has exactly one JUDGMENT_OFFICIAL_COPY row in
    source_authentication_queue.csv, keyed by the stable WS-B identity (spec_key);
  * acquisition references are only queue IDs recorded for that spec_key, else NO_ACQUISITION_REQUEST;
  * official copy, mirror copy, HTTP availability and identity status are separate, filled columns;
  * no row names a commercial legal database as host or holder;
  * build_planning.py is byte-identical on two runs and the committed outputs are current.
"""
import csv, io, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AW = ROOT / "legal_knowledge" / "audit_work"
WSB = AW / "WS-B-JUDGMENTS"
PLAN = AW / "COORDINATION" / "CYCLE3-PLANNING"
BUILDER = PLAN / "build_planning.py"
OUTPUTS = ("acquisition_schedule.csv", "affected_records_priority.csv", "source_authentication_queue.csv",
           "consistency_findings.csv", "planning_summary.json")
COMMERCIAL = ("indiankanoon", "casemine", "scconline", "manupatra")
HELD = "OFFICIAL_COPY_HELD"


def read(p):
    return list(csv.DictReader(io.StringIO(p.read_text(encoding="utf-8"), newline="")))


def expected_specs():
    """spec_key -> source descriptions, for every judgment still needing an official copy."""
    idr = {r["spec_key"]: r for r in read(WSB / "identity_resolution.csv")}
    held = {k for k, r in idr.items() if HELD in r["identity_state"]}
    need = {}

    def add(spec, why):
        if spec and spec not in held:
            need.setdefault(spec, []).append(why)

    for k, r in idr.items():
        add(k, "identity_resolution.csv:" + r["identity_state"])
    for r in read(WSB / "identity_resolution_cycle3.csv"):
        if HELD not in r["cycle3_state"]:
            add(r["spec_key"], "identity_resolution_cycle3.csv")
    for r in read(WSB / "authoritative_copy_status_cycle3.csv"):
        if r["official_copy_held"].upper().startswith("NO"):
            add(r["spec_key"], "authoritative_copy_status_cycle3.csv")
    for r in read(WSB / "holdings_register_cycle3.csv"):
        if r["copy_role"] != "OFFICIAL_COURT_COPY":
            add(r["spec_key"], "holdings_register_cycle3.csv")
    for name in ("pending_acquisition_cycle3.csv", "pending_source_queue.csv"):
        for r in read(WSB / name):
            for s in r["spec_key"].split(";"):
                add(s, name)
    return need


def queue_ids_by_spec():
    out = {}
    for name in ("pending_acquisition_cycle3.csv", "pending_source_queue.csv"):
        for r in read(WSB / name):
            for s in r["spec_key"].split(";"):
                if s:
                    out.setdefault(s, set()).add(r["queue_id"])
    return out


def judgment_rows():
    rows = read(PLAN / "source_authentication_queue.csv")
    return [r for r in rows if r["item_type"] == "JUDGMENT_OFFICIAL_COPY"]


def row_key(r):
    return r.get("case_key") or r["auth_id"].removeprefix("AUTH-J-")


class AuthenticationQueueCompleteness(unittest.TestCase):
    def test_every_unresolved_judgment_has_exactly_one_row(self):
        need = expected_specs()
        self.assertGreater(len(need), 0)
        keys = [row_key(r) for r in judgment_rows()]
        dup = sorted({k for k in keys if keys.count(k) > 1})
        missing = sorted(set(need) - set(keys))
        self.assertEqual(dup, [], f"duplicate queue rows: {dup}")
        self.assertEqual(missing, [], f"{len(missing)} unresolved judgments with no queue row: {missing}")

    def test_no_row_for_judgment_with_official_copy_held_only(self):
        need = expected_specs()
        extra = sorted(set(row_key(r) for r in judgment_rows()) - set(need))
        self.assertEqual(extra, [], f"rows for judgments not needing authentication: {extra}")

    def test_acquisition_reference_is_recorded_or_explicitly_absent(self):
        q = queue_ids_by_spec()
        for r in judgment_rows():
            k = row_key(r)
            ref = r.get("acquisition_request", "")
            self.assertTrue(ref, f"{k}: acquisition_request blank")
            if ref == "NO_ACQUISITION_REQUEST":
                self.assertNotIn(k, q, f"{k}: queue row exists but NO_ACQUISITION_REQUEST written")
            else:
                ids = set(ref.split(";"))
                self.assertEqual(ids, q.get(k, set()), f"{k}: {ref} differs from registers")

    def test_status_dimensions_are_separate_filled_columns(self):
        header = read(PLAN / "source_authentication_queue.csv")[0].keys()
        for col in ("case_key", "official_copy", "mirror_copy", "http_availability", "identity_status",
                    "identification_uncertainty", "acquisition_request", "authentication_requires", "source_file_row"):
            self.assertIn(col, header)
        for r in judgment_rows():
            for col in ("official_copy", "mirror_copy", "http_availability", "identity_status", "authentication_requires",
                        "source_file_row"):
                self.assertTrue(r[col].strip(), f"{row_key(r)}: {col} blank")


class NoCommercialSource(unittest.TestCase):
    def test_no_commercial_database_as_host_or_holder(self):
        for name in ("acquisition_schedule.csv", "source_authentication_queue.csv"):
            for n, r in enumerate(read(PLAN / name), 2):
                for col, v in r.items():
                    for c in COMMERCIAL:
                        self.assertNotIn(c, (v or "").lower(), f"{name} row {n} {col} names {c}")


class OpenInconsistenciesAndDispositions(unittest.TestCase):
    def test_ws_b_open_inconsistencies_listed_as_open_items(self):
        p = WSB / "open_inconsistencies_cycle3.csv"
        if not p.is_file():
            self.skipTest("register not present")
        oi = read(p)
        found = {r["finding_id"]: r for r in read(PLAN / "consistency_findings.csv")}
        for r in oi:
            fid = f"WSB-{r['item_id']}"
            self.assertIn(fid, found)
            self.assertEqual(found[fid]["disposition"], r["state"])
        by_spec = {}
        for r in oi:
            by_spec.setdefault(r["spec_key"], set()).add(f"WSB-{r['item_id']}")
        for r in judgment_rows():
            listed = {x.split(" ")[0] for x in r["open_inconsistencies"].split(";") if x.startswith("WSB-")}
            self.assertEqual(listed, by_spec.get(row_key(r), set()), row_key(r))

    def test_every_finding_has_a_disposition(self):
        for r in read(PLAN / "consistency_findings.csv"):
            self.assertIn(r["disposition"], ("OPEN", "RESOLVED", "VERIFIED", "INFORMATIONAL"), r["finding_id"])
            self.assertTrue(r["disposition_basis"].strip(), r["finding_id"])
            if r["disposition"] == "RESOLVED":
                self.assertTrue(r["fixing_commit_reported"].strip(), r["finding_id"])
                self.assertIn("check re-run", r["disposition_basis"], r["finding_id"])


class OfficialHostOnly(unittest.TestCase):
    def test_ws_b_host_is_official_or_not_recorded(self):
        for r in read(PLAN / "acquisition_schedule.csv"):
            if not r["acq_id"].startswith("PQ-"):
                continue
            h = r["host"]
            self.assertTrue(h.startswith("NOT_RECORDED") or h.endswith((".gov.in", ".nic.in")), f"{r['acq_id']}: {h}")
            self.assertEqual(r["source_located"] == "YES", not h.startswith("NOT_RECORDED"), r["acq_id"])


class Determinism(unittest.TestCase):
    def test_two_builds_byte_identical_and_committed_outputs_current(self):
        with tempfile.TemporaryDirectory() as d:
            outs = []
            for i in (1, 2):
                o = Path(d) / f"run{i}"
                o.mkdir()
                res = subprocess.run([sys.executable, str(BUILDER), "--out", str(o)], capture_output=True, text=True)
                self.assertEqual(res.returncode, 0, res.stderr)
                outs.append(o)
            for f in OUTPUTS:
                a, b = (outs[0] / f).read_bytes(), (outs[1] / f).read_bytes()
                self.assertEqual(a, b, f"{f} differs between runs")
                self.assertEqual(a, (PLAN / f).read_bytes(), f"committed {f} is stale")


if __name__ == "__main__":
    unittest.main()
