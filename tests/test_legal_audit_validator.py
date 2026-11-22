"""Regression checks for the legal database audit validator; no external dependencies."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("legal_audit_validator",
    ROOT / "tools" / "legal_audit" / "validate.py")
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


class AuditSchemaTests(unittest.TestCase):
    def test_schema_self_check(self):
        validator.schema_check()

    def test_missing_batch_fails_closed(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertFalse(validator.validate_batch(Path(root), strict=True))

    def test_invalid_source_and_orphan_finding_fails(self):
        import json
        with tempfile.TemporaryDirectory() as root:
            d = Path(root)
            for folder in ("sources", "findings", "reviews"):
                (d / folder).mkdir()
            finding = {
                "finding_id": "F1", "batch_id": "PILOT", "record_id": "KB1",
                "original_sha256": "a" * 64, "workstream": "STATUTORY",
                "severity": "P0", "issue_type": "CONFLICT", "claim": "Unverified",
                "original_location": "v0.9:KB1", "original_text": "x",
                "proposed_text": None, "rationale": "Requires original Gazette",
                "source_ids": ["NONEXISTENT"], "verification_state": "SOURCE_VERIFIED",
                "review_state": "ACCEPTED_FOR_CANDIDATE", "requires_legal_review": False
            }
            (d / "findings" / "F1.json").write_text(json.dumps(finding), encoding="utf-8")
            self.assertFalse(validator.validate_batch(d, strict=True))


    def test_manual_only_cannot_verify_statutory_law(self):
        import json
        with tempfile.TemporaryDirectory() as root:
            d = Path(root)
            for folder in ("sources", "findings", "reviews"):
                (d / folder).mkdir()
            source = {
                "source_id": "MML-2-P152",
                "source_type": "MANUAL",
                "title": "Manual of Military Law",
                "issuer": "User-provided source, original publisher unconfirmed",
                "locator": "legal_knowledge/manual_sources/originals/MML 2.pdf",
                "pinpoint": "PDF p.152",
                "retrieved_on": "2026-11-22",
                "verification_state": "SOURCE_VERIFIED",
                "authenticity": "USER_SUPPLIED_REFERENCE"
            }
            finding = {
                "finding_id": "F-MANUAL-ONLY", "batch_id": "PILOT",
                "record_id": "KB1", "original_sha256": "a" * 64,
                "workstream": "STATUTORY", "severity": "P1",
                "issue_type": "POTENTIAL_CONFLICT",
                "claim": "A legal claim cannot be proven by MML alone",
                "original_location": "v0.9:KB1", "original_text": "example",
                "proposed_text": None, "rationale": "Original Gazette needed",
                "source_ids": ["MML-2-P152"],
                "verification_state": "SOURCE_VERIFIED",
                "review_state": "PENDING", "requires_legal_review": True
            }
            (d / "sources" / "mml.json").write_text(json.dumps(source), encoding="utf-8")
            (d / "findings" / "finding.json").write_text(json.dumps(finding), encoding="utf-8")
            self.assertFalse(validator.validate_batch(d))


if __name__ == "__main__":
    unittest.main()
