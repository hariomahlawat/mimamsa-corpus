"""Authority versus carrier provenance: deterministic policy checks (no legal adjudication).

Run: python -m unittest discover -s tests -p "test_legal_audit_*.py" -v
"""
import copy
import importlib.util
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("audit_authority_validator",
    ROOT / "tools" / "legal_audit" / "validate.py")
V = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(V)
HASH = "a" * 64

OFFICIAL = {
    "source_id": "S-LAW", "source_type": "STATUTE",
    "title": "Sample statute, government-hosted compilation",
    "issuer": "Government of India", "locator": "https://indiacode.gov.in/example",
    "pinpoint": "s.1, printed p.1", "retrieved_on": "2026-11-22",
    "version_or_decision_date": "2026-11-22",
    "sha256": "b" * 64,
    "verification_state": "SOURCE_VERIFIED",
    "authenticity": "OFFICIAL_COMPILATION", "content_role": "ENACTED_TEXT",
}
GAZETTE = {
    "source_id": "S-GAZ-1954", "source_type": "GAZETTE",
    "title": "Gazette of India, 27 November 1954, S.R.O. 484",
    "issuer": "Government of India, Ministry of Defence",
    "locator": "https://archive.org/details/in.gazette.central.w.1954-11-27.103686",
    "pinpoint": "Printed p.300, Rule 23(3)", "retrieved_on": "2026-11-22",
    "version_or_decision_date": "1954-11-27", "sha256": "c" * 64,
    "verification_state": "SOURCE_LOCATED",
    "authenticity": "ARCHIVAL_FACSIMILE_OF_OFFICIAL",
    "document_authority": "ENACTED_OR_NOTIFIED_PRIMARY",
    "carrier_provenance": "THIRD_PARTY_ARCHIVAL_FACSIMILE",
    "copy_fidelity": "HASH_ONLY", "amendment_chain_status": "NOT_CHECKED",
    "instrument_identity": "Gazette of India No.47, Part II s.4, S.R.O.484, 27 November 1954, p.300",
    "authority_rationale": "Masthead and notification provenance; independent page-image read pending",
    "content_role": "GAZETTE_TEXT",
}
FINDING = {
    "finding_id": "F-TEST", "batch_id": "TEST", "record_id": "KB-TEST",
    "original_sha256": HASH, "workstream": "STATUTORY",
    "severity": "P2", "issue_type": "OTHER",
    "claim": "Example claim", "original_location": "test-record",
    "original_text": "Original text", "proposed_text": None,
    "rationale": "Demonstration", "source_ids": ["S-LAW"],
    "verification_state": "SOURCE_VERIFIED", "review_state": "PENDING",
    "requires_legal_review": False,
    "examination_outcome": "NO_ISSUE_FOUND",
    "temporal_scope": "Historical wording only",
    "legal_review_state": "NOT_REQUIRED"
}


def patch(obj, **updates):
    x = copy.deepcopy(obj)
    x.update(updates)
    return x


def validate(sources, finding=FINDING):
    with tempfile.TemporaryDirectory() as temp:
        batch = Path(temp)
        for kind, objs in (("sources", sources), ("findings", [finding]), ("reviews", [])):
            (batch / kind).mkdir()
            (batch / kind / "items.json").write_text(json.dumps(objs), encoding="utf-8")
        manifest = batch / "frozen.json"
        manifest.write_text(json.dumps({"records": [{
            "record_id": "KB-TEST", "original_sha256": HASH}]}), encoding="utf-8")
        with redirect_stdout(StringIO()) as stream:
            result = V.validate_batch(batch, strict=True, manifest=manifest)
        return result, json.loads(stream.getvalue())["errors"]


class AuthorityVersusCarrierPolicyTests(unittest.TestCase):
    def test_archival_gazette_is_primary_document_via_archival_carrier(self):
        ok, errs = validate([OFFICIAL, GAZETTE])
        self.assertTrue(ok, errs)

    def test_gazette_scan_mislabelled_secondary_fails(self):
        src = patch(GAZETTE, authenticity="SECONDARY")
        ok, errs = validate([OFFICIAL, src])
        self.assertFalse(ok)
        self.assertTrue(any("facsimile" in e for e in errs), errs)

    def test_gazette_no_instrument_identity_fails(self):
        src = patch(GAZETTE)
        del src["instrument_identity"]
        self.assertFalse(validate([OFFICIAL, src])[0])

    def test_hash_only_cannot_claim_archival_text_verified(self):
        src = patch(GAZETTE, verification_state="SOURCE_VERIFIED")
        ok, errs = validate([OFFICIAL, src])
        self.assertFalse(ok)
        self.assertTrue(any("HASH_ONLY" in e for e in errs), errs)

    def test_image_checked_gazette_text_can_be_source_verified(self):
        src = patch(GAZETTE, verification_state="SOURCE_VERIFIED",
                    copy_fidelity="PAGE_IMAGE_CHECKED", page_image_check_id="PIC-10")
        self.assertTrue(validate([OFFICIAL, src])[0])

    def test_page_image_check_requires_check_id(self):
        src = patch(GAZETTE, verification_state="SOURCE_VERIFIED",
                    copy_fidelity="PAGE_IMAGE_CHECKED")
        self.assertFalse(validate([OFFICIAL, src])[0])

    def test_custodian_certification_requires_artifact(self):
        src = patch(GAZETTE, verification_state="SOURCE_VERIFIED",
                    copy_fidelity="CUSTODIAN_AUTHENTICATED")
        self.assertFalse(validate([OFFICIAL, src])[0])

    def test_unchecked_amendment_chain_cannot_support_current_law(self):
        finding = patch(FINDING, asserted_law_status="CURRENT_IN_FORCE")
        ok, errs = validate([OFFICIAL, GAZETTE], finding)
        self.assertFalse(ok)
        self.assertTrue(any("amendment chain" in e for e in errs), errs)

    def test_checked_amendment_chain_allows_current_law_evidence_classification(self):
        official = patch(OFFICIAL, document_authority="GOVERNMENT_COMPILATION",
                         carrier_provenance="GOVERNMENT_HOSTED_COPY",
                         copy_fidelity="PAGE_IMAGE_CHECKED", page_image_check_id="PIC-EXAMPLE",
                         amendment_chain_status="CHECKED_FOR_RELEVANT_PERIOD",
                         authority_rationale="Provenance and amendment dates checked in test fixture")
        finding = patch(FINDING, asserted_law_status="CURRENT_IN_FORCE")
        self.assertTrue(validate([official], finding)[0])

    def test_source_conflict_cannot_be_labelled_verified(self):
        finding = patch(FINDING, asserted_law_status="SOURCE_CONFLICT")
        self.assertFalse(validate([OFFICIAL, GAZETTE], finding)[0])

    def test_third_party_facsimile_cannot_be_issuing_authority_copy(self):
        src = patch(GAZETTE, authenticity="ORIGINAL_OFFICIAL")
        self.assertFalse(validate([OFFICIAL, src])[0])


if __name__ == "__main__":
    unittest.main()
