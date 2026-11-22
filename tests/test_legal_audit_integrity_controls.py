"""Regression tests for WS-D integrity controls in tools/legal_audit/validate.py (issue #14).

Covers: proof type, document authority vs carrier provenance, source dates (owner date rule:
publication / commencement as printed / effective date are distinct), cross-record relations,
register cross-references, and legal-review-state separation (no agent-asserted approval).
Each negative test mutates exactly one thing in a valid controls-v2 batch. Structural only.
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
SPEC = importlib.util.spec_from_file_location("legal_audit_validator_wsd", ROOT / "tools" / "legal_audit" / "validate.py")
V = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(V)
AW = ROOT / "legal_knowledge" / "audit_work"

H = "a" * 64
R = "b" * 64
GAZ = {"source_id": "S-G1", "source_type": "GAZETTE", "title": "Gazette of India Part II-4, S.R.O. 484",
       "issuer": "Ministry of Defence", "locator": "archive.org item x", "pinpoint": "printed p.300",
       "retrieved_on": "2026-11-22", "version_or_decision_date": "1954-11-27", "effective_date": None,
       "publication_date": "1954-11-27", "commencement_as_printed": "not stated",
       "effective_date_status": "NOT_STATED (no commencement clause on the page)",
       "sha256": H, "verification_state": "SOURCE_VERIFIED", "authenticity": "ARCHIVAL_FACSIMILE_OF_OFFICIAL",
       "retrieved_by": "statutory-auditor", "content_role": "GAZETTE_TEXT",
       "document_authority": "ENACTED_OR_NOTIFIED_PRIMARY", "carrier_provenance": "THIRD_PARTY_ARCHIVAL_FACSIMILE",
       "copy_fidelity": "PAGE_IMAGE_CHECKED", "amendment_chain_status": "PARTIAL",
       "instrument_identity": "Gazette of India 27-11-1954 Part II-4, S.R.O. 484, pp.291-300",
       "authority_rationale": "archival facsimile of the issued Gazette", "page_image_check_id": "PIC-01",
       "proof_type": "PAGE_IMAGE_READING", "render_sha256": R}
FIND = {"finding_id": "F1", "batch_id": "T-01", "record_id": "KB-001", "original_sha256": H,
        "workstream": "STATUTORY", "severity": "P2", "issue_type": "OTHER", "claim": "c",
        "original_location": "records_658.jsonl:1", "original_text": "t", "proposed_text": None, "rationale": "r",
        "source_ids": ["S-G1"], "verification_state": "SOURCE_VERIFIED", "review_state": "PENDING",
        "requires_legal_review": False, "examination_outcome": "NO_ISSUE_FOUND", "pinpoint": "p.300",
        "temporal_scope": "1954 notified text", "legal_review_state": "NOT_REQUIRED",
        "related_record_ids": ["KB-002"], "agent": "statutory-auditor"}
HUMAN_REVIEW = {"review_id": "R1", "finding_id": "F1", "reviewer_id": "adv-001", "reviewer_role": "LEGAL_ADVISOR",
                "decision": "ACCEPTED_FOR_CANDIDATE", "decision_date": "2026-11-23", "rationale": "advice",
                "source_ids": ["S-G1"], "approval_artifact": "advice-letter-2026-11-23.pdf sha256 " + H,
                "reviewed_original_sha256": H}
IDENT = {"first_pass_agents": ["statutory-auditor"], "reviewers": {},
         "human_reviewers": {"adv-001": {"role": "LEGAL_ADVISOR", "binding_evidence": "owner nomination record"}}}
MAN = {"batch_id": "T-01", "source_authority_policy_version": "v1", "audit_controls_version": "v2",
       "records": [{"record_id": "KB-001", "original_sha256": H}]}


def edit(obj, **kw):
    out = copy.deepcopy(obj)
    for k, v in kw.items():
        if v is KeyError:
            out.pop(k, None)
        else:
            out[k] = v
    return out


def run(sources=(GAZ,), findings=(FIND,), reviews=(), manifest=MAN, identities=IDENT, strict=True):
    with tempfile.TemporaryDirectory() as root:
        d = Path(root)
        if identities is not None:
            (d / "reviewer_identities.json").write_text(json.dumps(identities), encoding="utf-8")
        for name, rows in (("sources", sources), ("findings", findings), ("reviews", reviews)):
            (d / name).mkdir()
            (d / name / "x.json").write_text(json.dumps(list(rows)), encoding="utf-8")
        m = None
        if manifest is not None:
            m = d / "manifest.json"
            m.write_text(json.dumps(manifest), encoding="utf-8")
        buf = StringIO()
        with redirect_stdout(buf):
            ok = V.validate_batch(d, strict, m)
        return ok, json.loads(buf.getvalue())["errors"]


class Baseline(unittest.TestCase):
    def test_valid_v2_batch_passes(self):
        ok, errs = run()
        self.assertTrue(ok, errs)

    def test_valid_v2_batch_with_bound_human_acceptance_passes(self):
        ok, errs = run(findings=[edit(FIND, review_state="ACCEPTED_FOR_CANDIDATE")], reviews=[HUMAN_REVIEW])
        self.assertTrue(ok, errs)

    def test_unknown_controls_version_fails_closed(self):
        ok, errs = run(manifest=edit(MAN, audit_controls_version="v9"))
        self.assertFalse(ok)
        self.assertTrue(any("Unknown audit_controls_version" in e for e in errs))

    def test_v2_requires_policy_v1(self):
        self.assertFalse(run(manifest=edit(MAN, source_authority_policy_version=KeyError))[0])

    def test_frozen_batches_are_not_v2_and_still_pass(self):
        for b in ("PILOT-01", "R23-VERIFY-01"):
            man = json.loads((AW / b / "pilot-manifest.json").read_text(encoding="utf-8"))
            self.assertNotIn("audit_controls_version", man, f"{b} must not be silently migrated to v2")
            with redirect_stdout(StringIO()):
                self.assertTrue(V.validate_batch(AW / b, True, AW / b / "pilot-manifest.json"), b)


class ProofType(unittest.TestCase):
    def test_v2_requires_proof_type_but_legacy_does_not(self):
        self.assertFalse(run(sources=[edit(GAZ, proof_type=KeyError, render_sha256=KeyError)])[0])
        legacy = edit(MAN, audit_controls_version=KeyError)
        ok, errs = run(sources=[edit(GAZ, proof_type=KeyError, render_sha256=KeyError)], manifest=legacy)
        self.assertTrue(ok, errs)

    def test_ocr_search_metadata_never_verify(self):
        for p in ("OCR_TEXT", "SEARCH_RESULT_ONLY", "METADATA_ONLY"):
            ok, errs = run(sources=[edit(GAZ, proof_type=p)], manifest=None, strict=False)
            self.assertFalse(ok, p)
            self.assertTrue(any("cannot support SOURCE_VERIFIED" in e for e in errs), p)

    def test_page_image_reading_needs_render_hash(self):
        self.assertFalse(run(sources=[edit(GAZ, render_sha256=KeyError)])[0])

    def test_schema_rejects_unknown_proof_type(self):
        self.assertFalse(run(sources=[edit(GAZ, proof_type="HUNCH")])[0])


class AuthorityVsCarrier(unittest.TestCase):
    def test_contradictory_combinations_fail(self):
        base_rule = edit(GAZ, source_type="RULE", authenticity="OFFICIAL_COMPILATION",
                         document_authority="GOVERNMENT_COMPILATION", carrier_provenance="GOVERNMENT_HOSTED_COPY",
                         content_role="ENACTED_TEXT", instrument_identity=KeyError)
        self.assertTrue(run(sources=[base_rule])[0], run(sources=[base_rule])[1])
        bad = {
            "judicial on rule": edit(base_rule, document_authority="OFFICIAL_JUDICIAL_DECISION"),
            "commentary on rule": edit(base_rule, document_authority="THIRD_PARTY_COMMENTARY"),
            "compilation claimed original": edit(base_rule, authenticity="ORIGINAL_OFFICIAL"),
            "user copy custodian-authenticated": edit(base_rule, carrier_provenance="USER_SUPPLIED",
                                                      copy_fidelity="CUSTODIAN_AUTHENTICATED",
                                                      custodian_evidence_ref="x"),
            "original via transcription": edit(base_rule, authenticity="ORIGINAL_OFFICIAL",
                                               document_authority="ENACTED_OR_NOTIFIED_PRIMARY",
                                               carrier_provenance="THIRD_PARTY_TRANSCRIPTION"),
            "primary on secondary": edit(base_rule, source_type="SECONDARY",
                                         document_authority="ENACTED_OR_NOTIFIED_PRIMARY"),
        }
        for name, src in bad.items():
            self.assertFalse(run(sources=[src])[0], name)


class Dates(unittest.TestCase):
    def test_effective_date_requires_stated_commencement(self):
        ok, errs = run(sources=[edit(GAZ, effective_date="1954-11-27")])
        self.assertFalse(ok)
        self.assertTrue(any("effective_date" in e for e in errs))

    def test_effective_equal_to_publication_needs_stated_status_even_without_v2(self):
        src = edit(GAZ, effective_date="1954-11-27", effective_date_status=KeyError)
        ok, errs = run(sources=[src], manifest=None, strict=False)
        self.assertFalse(ok)
        self.assertTrue(any("equals publication_date" in e for e in errs))

    def test_stated_commencement_passes_and_needs_iso(self):
        stated = edit(GAZ, effective_date="1954-12-01", effective_date_status="STATED_IN_INSTRUMENT (r.1(2))",
                      commencement_as_printed="shall come into force on 1 December 1954")
        self.assertTrue(run(sources=[stated])[0], run(sources=[stated])[1])
        self.assertFalse(run(sources=[edit(stated, effective_date="on publication")])[0])

    def test_v2_requires_status_and_iso_leading_date(self):
        self.assertFalse(run(sources=[edit(GAZ, effective_date_status=KeyError)])[0])
        self.assertFalse(run(sources=[edit(GAZ, version_or_decision_date="India Code consolidation")])[0])

    def test_impossible_calendar_date_fails(self):
        self.assertFalse(run(sources=[edit(GAZ, version_or_decision_date="1954-02-30")], manifest=None, strict=False)[0])

    def test_schema_rejects_unknown_effective_date_status(self):
        self.assertFalse(run(sources=[edit(GAZ, effective_date_status="PROBABLY")])[0])

    def test_judgment_decided_after_retrieval_fails(self):
        j = {"source_id": "S-J", "source_type": "JUDGMENT", "title": "X v UOI", "issuer": "Supreme Court of India",
             "locator": "https://api.sci.gov.in/x.pdf", "pinpoint": "para 4", "retrieved_on": "2026-11-22",
             "version_or_decision_date": "2027-01-05", "verification_state": "SOURCE_LOCATED",
             "authenticity": "OFFICIAL_COURT_ARCHIVE", "retrieved_by": "judgment-auditor"}
        self.assertFalse(run(sources=[GAZ, j], manifest=None, strict=False)[0])


class RelationsAndRegisters(unittest.TestCase):
    def test_unknown_page_image_check_fails(self):
        ok, errs = run(sources=[edit(GAZ, page_image_check_id="PIC-9999")])
        self.assertFalse(ok)
        self.assertTrue(any("PIC-9999" in e for e in errs))

    def test_v2_requires_exact_registered_check_id(self):
        self.assertFalse(run(sources=[edit(GAZ, page_image_check_id="PIC-01 (orchestrator) / render in pinpoint")])[0])

    def test_source_both_supporting_and_contrary_fails(self):
        self.assertFalse(run(findings=[edit(FIND, contrary_source_ids=["S-G1"])])[0])

    def test_batch_id_must_match_manifest(self):
        self.assertFalse(run(findings=[edit(FIND, batch_id="OTHER")])[0])

    def test_related_record_must_exist(self):
        ok, errs = run(findings=[edit(FIND, related_record_ids=["KB-999999"])])
        self.assertFalse(ok)
        self.assertTrue(any("KB-999999" in e for e in errs))

    def test_review_hash_must_match_finding(self):
        rev = edit(HUMAN_REVIEW, reviewed_original_sha256="c" * 64)
        self.assertFalse(run(findings=[edit(FIND, review_state="ACCEPTED_FOR_CANDIDATE")], reviews=[rev])[0])


class NoAgentAssertedApproval(unittest.TestCase):
    def test_agent_identity_cannot_hold_human_role_even_non_strict(self):
        for rid in ("statutory-auditor", "independent-reviewer-Z", "orchestrator", "claude-helper", "ws-d"):
            for role in ("LEGAL_ADVISOR", "PROJECT_DIRECTOR", "FORMAL_AUTHORITY"):
                rev = edit(HUMAN_REVIEW, reviewer_id=rid, reviewer_role=role, decision="INCONCLUSIVE")
                ok, errs = run(reviews=[rev], manifest=None, strict=False)
                self.assertFalse(ok, (rid, role))
                self.assertTrue(any("cannot assert human role" in e for e in errs), (rid, role))

    def test_v2_human_reviewer_must_be_bound(self):
        unbound = edit(IDENT, human_reviewers={})
        self.assertFalse(run(findings=[edit(FIND, review_state="ACCEPTED_FOR_CANDIDATE")],
                             reviews=[HUMAN_REVIEW], identities=unbound)[0])
        wrong_role = edit(IDENT, human_reviewers={"adv-001": {"role": "PROJECT_DIRECTOR", "binding_evidence": "x"}})
        self.assertFalse(run(findings=[edit(FIND, review_state="ACCEPTED_FOR_CANDIDATE")],
                             reviews=[HUMAN_REVIEW], identities=wrong_role)[0])

    def test_v2_acceptance_requires_approval_artifact(self):
        self.assertFalse(run(findings=[edit(FIND, review_state="ACCEPTED_FOR_CANDIDATE")],
                             reviews=[edit(HUMAN_REVIEW, approval_artifact=None)])[0])

    def test_declared_human_reviewer_cannot_be_an_agent(self):
        bad = edit(IDENT, human_reviewers={"statutory-auditor": {"role": "LEGAL_ADVISOR", "binding_evidence": "x"}})
        self.assertFalse(run(identities=bad)[0])
        no_evidence = edit(IDENT, human_reviewers={"adv-001": {"role": "LEGAL_ADVISOR"}})
        self.assertFalse(run(identities=no_evidence)[0])

    def test_v2_candidate_needs_human_acceptance_even_without_legal_review_flag(self):
        ok, errs = run(findings=[edit(FIND, review_state="ACCEPTED_FOR_CANDIDATE")])
        self.assertFalse(ok)
        self.assertTrue(any("human acceptance review" in e for e in errs))

    def test_v2_legal_review_state_required(self):
        self.assertFalse(run(findings=[edit(FIND, legal_review_state=KeyError)])[0])

    def test_no_existing_batch_claims_human_review_or_current_law(self):
        for b in ("PILOT-01", "R23-VERIFY-01"):
            errors = []
            recs = {k: V.read_kind(AW / b / d, errors) for k, (d, _) in V.KINDS.items()}
            self.assertEqual(errors, [])
            for _, f in recs["finding"]:
                self.assertNotEqual(f.get("legal_review_state"), "ADVISOR_REVIEWED", f["finding_id"])
                self.assertNotEqual(f.get("review_state"), "ACCEPTED_FOR_CANDIDATE", f["finding_id"])
                self.assertNotEqual(f.get("asserted_law_status"), "CURRENT_IN_FORCE", f["finding_id"])
            for _, r in recs["review"]:
                self.assertNotIn(r.get("reviewer_role"), V.HUMAN_ROLES, r["review_id"])


class FixedDeterminations(unittest.TestCase):
    def test_r23_3_findings_stay_conflicting(self):
        errors = []
        finds = [f for _, f in V.read_kind(AW / "R23-VERIFY-01" / "findings", errors)]
        self.assertEqual(errors, [])
        self.assertTrue(finds)
        for f in finds:
            self.assertEqual(f["verification_state"], "CONFLICTING", f["finding_id"])
            self.assertEqual(f["examination_outcome"], "CONFLICTING_SOURCES", f["finding_id"])
            self.assertIn(f.get("asserted_law_status"), (None, "SOURCE_CONFLICT"), f["finding_id"])
            self.assertTrue(f["requires_legal_review"], f["finding_id"])


if __name__ == "__main__":
    unittest.main()
