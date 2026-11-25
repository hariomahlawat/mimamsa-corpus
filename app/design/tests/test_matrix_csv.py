"""F19/F20: the capability traceability matrix is complete and consistent with the security test catalogue."""
from __future__ import annotations

import csv
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
CSV = REPO / "docs" / "architecture" / "CAPABILITY_TRACEABILITY_MATRIX.csv"
SEC = REPO / "docs" / "architecture" / "SECURITY_AND_DEPLOYMENT_ARCHITECTURE.md"
COLS = ["capability_id", "area", "capability", "product_refs", "user_workflow", "required_data", "backend_service",
        "storage_index_model", "frontend_workspace", "security_requirements", "performance_requirements",
        "evidence_approval_gates", "acceptance_tests", "phase", "gated_off", "dependencies_limitations"]
ROWS = list(csv.DictReader(CSV.open(encoding="utf-8")))


def _expand(text: str) -> set[str]:
    out = set()
    for m in re.finditer(r"T-([A-Z]+)-(\d\d)(?:\.\.(\d\d))?", text):
        a = int(m.group(2))
        b = int(m.group(3)) if m.group(3) else a
        out |= {f"T-{m.group(1)}-{i:02d}" for i in range(a, b + 1)}
    return out


def test_columns_and_unique_ids():
    assert list(ROWS[0].keys()) == COLS
    ids = [r["capability_id"] for r in ROWS]
    assert len(ids) == len(set(ids)) == 52


def test_no_empty_or_dash_cells():
    bad = [(r["capability_id"], k) for r in ROWS for k in COLS if r[k].strip() in ("", "—", "-")]
    assert bad == []


def test_all_eight_section18_areas_present():
    areas = {r["area"].split(" (")[0] for r in ROWS}
    for name in ["Universal legal search", "Judgment intelligence", "Statutory explorer", "Legal knowledge graph",
                 "Commander assistant", "Document Studio", "Research workspace", "Knowledge administration"]:
        assert name in areas, name


def test_every_product_requirement_referenced():
    refs = " ".join(r["product_refs"] for r in ROWS)
    assert [i for i in range(1, 31) if f"PR-{i:02d}" not in refs] == []


def test_every_security_test_mapped_to_a_capability():
    catalogue = set(re.findall(r"^\| (T-[A-Z]+-\d\d) \|", SEC.read_text(encoding="utf-8"), flags=re.M))
    mapped = set()
    for r in ROWS:
        mapped |= _expand(r["security_requirements"] + " " + r["acceptance_tests"])
    assert sorted(catalogue - mapped) == []


def test_gated_rows_are_later_and_commander_assistant_core_gated():
    for r in ROWS:
        if r["gated_off"] == "yes" and r["capability_id"] != "CAP-KA-06":
            assert r["phase"].startswith("later"), r["capability_id"]
    for cid in ["CAP-CA-01", "CAP-CA-02", "CAP-CA-03", "CAP-CA-05", "CAP-DS-03", "CAP-DS-04"]:
        assert next(r for r in ROWS if r["capability_id"] == cid)["gated_off"] == "yes"
