import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import c16_exchange_v21 as x


def test_relationship_projection_preserves_every_source_relationship():
    inventory = {
        "i1": {"inventory_id": "i1", "sha256": "a" * 64,
               "relative_path": "Army/section 1/example.pdf"}
    }
    identities = {"a" * 64: {"doc_id": "local-a", "work_identity": {"graph_node_ref": "JUD:local-a"}}}
    subject = [{"inventory_id": "i1", "source_copy_sha256": "a" * 64,
                "relative_path": "Army/section 1/example.pdf", "source_label": "Army",
                "target_node_id": "SUBJ:local:army", "basis": "FOLDER_PATH",
                "verification": "CURATED_NAVIGATION"}]
    provisions = [{"inventory_id": "i1", "source_copy_sha256": "a" * 64,
                   "relative_path": "Army/section 1/example.pdf", "source_label": "AA 1",
                   "target_node_id": "PROV:AA-1950:s.1", "basis": "FILENAME_PATTERN",
                   "verification": "CANDIDATE", "abbreviation_expansion": {"abbreviation": "AA", "reading": "Army Act", "alternatives": []}}]

    calls = []
    def classification(category, **kwargs):
        calls.append((category, kwargs))
        return {"relationship_id": f"r{len(calls)}", "category": category,
                "is_finding": kwargs["is_finding"] if "is_finding" in kwargs else False}

    rows = x.project_relationships(subject, provisions, inventory, identities, classification)
    assert len(rows) == 2
    assert [c[0] for c in calls] == ["classified_under_subject", "associated_with_provision"]
    assert all(not row["is_finding"] for row in rows)
    assert calls[0][1]["uncertainty"].startswith("Owner folder classification")
    assert calls[1][1]["target"] == {"resolved": True, "node_id": "PROV:AA-1950:s.1"}


def test_relationship_projection_fails_on_missing_identity_binding():
    raw = [{"inventory_id": "missing", "source_copy_sha256": "a" * 64,
            "relative_path": "x.pdf", "source_label": "x", "target_node_id": "SUBJ:local:x",
            "basis": "FOLDER_PATH", "verification": "CURATED_NAVIGATION"}]
    try:
        x.project_relationships(raw, [], {}, {}, lambda *a, **k: {})
    except ValueError as error:
        assert "identity binding" in str(error)
    else:
        raise AssertionError("unbound relationships must fail closed")


def test_jsonl_is_canonical_lf_with_no_terminal_blank_record():
    data = x.jsonl_bytes([{"b": 2, "a": 1}])
    assert data == b'{"a":1,"b":2}\n'
