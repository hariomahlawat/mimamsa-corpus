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
    artifact = tmp_path / "artifacts" / "raw.txt";artifact.parent.mkdir(); artifact.write_text(text, encoding="utf-8")
    normalised=tmp_path/"artifacts"/"normalised.txt";normalised.write_text(text,encoding="utf-8")
    boxes=tmp_path/"artifacts"/"boxes.json";boxes.write_text("[]",encoding="utf-8")
    record = {"state": "COMPLETE", "evidence_verified": True, "unreadable": False,
              "access_disposition": "SCREENED_NO_MARKING_DETECTED", "source_sha256": "a" * 64,
              "verified_source_sha256": "a" * 64, "render_sha256": "b" * 64, "physical_page": 3,
              "configuration_sha256": "c" * 64, "mean_confidence": 88.5,
              "artifact_paths": {"raw_text": "artifacts/raw.txt","normalised_text":"artifacts/normalised.txt","word_boxes":"artifacts/boxes.json"},
              "artifact_sha256": {"raw_text": x.hashlib.sha256(text.encode()).hexdigest(),"normalised_text":x.hashlib.sha256(text.encode()).hexdigest(),"word_boxes":x.hashlib.sha256(b"[]").hexdigest()},
              "raw_text_path":"artifacts/raw.txt","normalised_text_path":"artifacts/normalised.txt","word_boxes_path":"artifacts/boxes.json"}
    config = {"configuration_sha256":"c"*64,"engine": "tesseract", "engine_version": "5.3", "languages": ["eng", "hin"],
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


def test_access_join_rejects_missing_mismatched_and_duplicate_rows():
    inventory = [{"inventory_id": "i1", "sha256": "a" * 64}]
    for access in ([],
                   [{"inventory_id": "i1", "source_sha256": "b" * 64, "document_access_disposition": "SCREENED_NO_MARKING_DETECTED"}],
                   [{"inventory_id": "i1", "source_sha256": "a" * 64, "document_access_disposition": "SCREENED_NO_MARKING_DETECTED"}] * 2):
        try:
            x.join_access_decisions(inventory, access)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid access join must fail closed")


def test_marked_observation_quarantines_every_duplicate_source_copy():
    inventory = [{"inventory_id": "i1", "sha256": "a" * 64}, {"inventory_id": "i2", "sha256": "a" * 64}]
    access = [{"inventory_id": "i1", "source_sha256": "a" * 64, "document_access_disposition": "SCREENED_NO_MARKING_DETECTED"},
              {"inventory_id": "i2", "source_sha256": "a" * 64, "document_access_disposition": "HELD_ACCESS_MARKING_REVIEW"}]
    joined = x.join_access_decisions(inventory, access)
    transferable, quarantine = x.partition_transferable(joined)
    assert transferable == []
    assert {row["inventory_id"] for row in quarantine} == {"i1", "i2"}


def test_incomplete_mixed_pdf_and_held_docx_export_no_derivatives_or_anchors():
    rows = [{"inventory_id": "pdf", "sha256": "a" * 64, "detected_format": "PDF",
             "document_access_disposition": "HELD_UNREADABLE_OR_PROCESSING_ERROR"},
            {"inventory_id": "docx", "sha256": "b" * 64, "detected_format": "DOCX", "derivative_sha256": "c" * 64,
             "document_access_disposition": "HELD_UNREADABLE_OR_PROCESSING_ERROR"}]
    transferable, quarantine = x.partition_transferable(rows)
    assert transferable == [] and len(quarantine) == 2


def test_pdf_anchor_rejects_wrong_config_duplicate_page_and_tampered_artifact(tmp_path):
    artifact = tmp_path / "raw.txt"; artifact.write_text("clean", encoding="utf-8")
    normalised=tmp_path/"normalised.txt";normalised.write_text("clean",encoding="utf-8")
    boxes=tmp_path/"boxes.json";boxes.write_text("[]",encoding="utf-8")
    base = {"state": "COMPLETE", "evidence_verified": True, "unreadable": False,
            "access_disposition": "SCREENED_NO_MARKING_DETECTED", "source_sha256": "a" * 64,
            "verified_source_sha256": "a" * 64, "render_sha256": "b" * 64, "physical_page": 1,
            "configuration_sha256": "wrong", "artifact_paths": {"raw_text": "raw.txt","normalised_text":"normalised.txt","word_boxes":"boxes.json"},
            "artifact_sha256": {"raw_text": x.hashlib.sha256(b"clean").hexdigest(),"normalised_text":x.hashlib.sha256(b"clean").hexdigest(),"word_boxes":x.hashlib.sha256(b"[]").hexdigest()},
            "raw_text_path":"raw.txt","normalised_text_path":"normalised.txt","word_boxes_path":"boxes.json"}
    config = {"configuration_sha256": "current", "engine": "tesseract", "engine_version": "5",
              "languages": ["eng"], "psm": [1], "preprocessing": [], "render_dpi": 300}
    class Canonical:
        @staticmethod
        def anchor_id(row): return "ANC-" + "1" * 24
    identities = {"a" * 64: {"doc_id": "local-a", "text_derivatives": []}}
    assert x.pdf_anchors([base], tmp_path, config, identities, Canonical) == []
    current = {**base, "configuration_sha256": "current"}
    try:
        x.pdf_anchors([current, dict(current)], tmp_path, config, identities, Canonical)
    except ValueError:
        pass
    else:
        raise AssertionError("duplicate page evidence must fail closed")
    artifact.write_text("tampered", encoding="utf-8")
    assert x.pdf_anchors([current], tmp_path, config, identities, Canonical) == []
