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


def test_pdf_anchor_binds_verified_source_render_config_and_text(tmp_path):
    text = "verified page text"
    artifact = tmp_path / "artifacts" / "raw.txt"
    artifact.parent.mkdir(); artifact.write_text(text, encoding="utf-8")
    record = {"state": "COMPLETE", "evidence_verified": True, "unreadable": False,
              "access_disposition": "SCREENED_NO_MARKING_DETECTED", "source_sha256": "a" * 64,
              "verified_source_sha256": "a" * 64, "render_sha256": "b" * 64, "physical_page": 3,
              "configuration_sha256": "c" * 64, "mean_confidence": 88.5,
              "artifact_paths": {"raw_text": "artifacts/raw.txt"},
              "artifact_sha256": {"raw_text": x.hashlib.sha256(text.encode()).hexdigest()}}
    config = {"engine": "tesseract", "engine_version": "5.3", "languages": ["eng", "hin"],
              "psm": [1], "preprocessing": ["grayscale"], "render_dpi": 300}
    class Canonical:
        @staticmethod
        def anchor_id(row): return "ANC-" + "1" * 24
    identities = {"a" * 64: {"doc_id": "local-a", "text_derivatives": []}}
    rows = x.pdf_anchors([record], tmp_path, config, identities, Canonical)
    assert len(rows) == 1
    anchor = rows[0]
    assert anchor["original_sha256"] == "a" * 64
    assert anchor["image_sha256"] == "b" * 64
    assert anchor["extraction"]["ocr_config"]["config_sha256"] == "c" * 64
    assert anchor["locator"]["physical_page"] == 3
    assert anchor["text_span"]["text_sha256"] == x.hashlib.sha256(text.encode()).hexdigest()
    assert identities["a" * 64]["text_derivatives"][0]["derivative_text_sha256"] == anchor["derivative_text_sha256"]


def test_pdf_anchor_rejects_unverified_or_held_evidence(tmp_path):
    rows = [{"state": "COMPLETE", "evidence_verified": False},
            {"state": "COMPLETE", "evidence_verified": True, "unreadable": False,
             "access_disposition": "HELD_ACCESS_MARKING_REVIEW"}]
    assert x.pdf_anchors(rows, tmp_path, {}, {}, object()) == []


def test_image_ocr_enrichment_prefers_verified_readable_second_pass():
    inventory = [{"embedded_images": [{"image_sha256": "a" * 64, "ocr_state": "REQUIRED"}]}]
    primary = [{"image_sha256": "a" * 64, "state": "COMPLETE", "evidence_verified": True,
                "unreadable": True, "artifact_sha256": {}}]
    secondary = [{"image_sha256": "a" * 64, "state": "COMPLETE", "evidence_verified": True,
                  "unreadable": False, "access_disposition": "SCREENED_NO_MARKING_DETECTED",
                  "artifact_sha256": {"raw_text": "b" * 64}}]
    x.enrich_image_ocr(inventory, primary, secondary)
    assert inventory[0]["embedded_images"][0]["ocr_state"] == "DONE"
    assert inventory[0]["embedded_images"][0]["ocr_derivative_sha256"] == "b" * 64


def test_image_ocr_enrichment_keeps_unreadable_fail_closed():
    inventory = [{"embedded_images": [{"image_sha256": "a" * 64, "ocr_state": "REQUIRED"}]}]
    primary = [{"image_sha256": "a" * 64, "state": "COMPLETE", "evidence_verified": True,
                "unreadable": True, "artifact_sha256": {}}]
    x.enrich_image_ocr(inventory, primary, [])
    assert inventory[0]["embedded_images"][0]["ocr_state"] == "FAILED"
    assert "ocr_derivative_sha256" not in inventory[0]["embedded_images"][0]
