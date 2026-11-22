"""Regression tests for the PILOT-01 extended audit controls (stdlib only)."""
import copy
import importlib.util
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("legal_audit_validator", ROOT / "tools" / "legal_audit" / "validate.py")
V = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(V)

H = "a" * 64
MML2 = "db2119182ed2e4ccca22dd225d955327f6398ee98303e1c94615ba85b4396f65"

SOURCES = [
    {"source_id": "S-AR", "source_type": "RULE", "title": "Army Rules 1954", "issuer": "Ministry of Defence",
     "locator": "https://indiacode.nic.in/x", "pinpoint": "r.22(1) proviso, PDF p.12", "retrieved_on": "2026-11-22",
     "version_or_decision_date": "1954-11-27", "effective_date": None, "verification_state": "SOURCE_VERIFIED",
     "authenticity": "OFFICIAL_COMPILATION", "retrieved_by": "statutory-auditor", "content_role": "ENACTED_TEXT"},
    {"source_id": "S-MML", "source_type": "MANUAL", "title": "MML Part II", "issuer": "unconfirmed",
     "locator": "legal_knowledge/manual_sources/originals/MML 2.pdf", "pinpoint": "PDF p.150", "retrieved_on": "2026-11-22",
     "sha256": MML2, "verification_state": "SOURCE_LOCATED", "authenticity": "USER_SUPPLIED_REFERENCE",
     "retrieved_by": "manual-of-military-law-auditor", "content_role": "MANUAL_REPRODUCED_LEGAL_TEXT"},
    {"source_id": "S-REV", "source_type": "RULE", "title": "Army Rules 1954", "issuer": "Ministry of Defence",
     "locator": "https://indiacode.nic.in/y", "pinpoint": "r.22(1), PDF p.12", "retrieved_on": "2026-11-22",
     "version_or_decision_date": "1954-11-27", "verification_state": "SOURCE_VERIFIED",
     "authenticity": "OFFICIAL_COMPILATION", "retrieved_by": "independent-reviewer", "content_role": "ENACTED_TEXT"},
]
FINDING = {"finding_id": "F1", "batch_id": "PILOT-01", "record_id": "KB-1", "original_sha256": H,
           "workstream": "PROCEDURE", "severity": "P2", "issue_type": "OTHER", "claim": "c",
           "original_location": "records_658.jsonl:1", "original_text": "t", "proposed_text": None,
           "rationale": "r", "source_ids": ["S-AR"], "verification_state": "SOURCE_VERIFIED",
           "review_state": "PENDING", "requires_legal_review": False, "examination_outcome": "NO_ISSUE_FOUND",
           "pinpoint": "r.22(1)", "temporal_scope": "1954 text as compiled; amendments to 2019 unverified",
           "mml_anchor_ids": ["S-MML"], "legal_review_state": "NOT_REQUIRED"}
REVIEW = {"review_id": "R1", "finding_id": "F1", "reviewer_id": "independent-reviewer", "reviewer_role": "INDEPENDENT_AGENT",
          "decision": "SUPPORTS", "decision_date": "2026-11-22", "rationale": "own check", "source_ids": ["S-REV"],
          "independent_source_ids": ["S-REV"], "blind": True}


IDENT = {"first_pass_agents": ["statutory-auditor", "manual-of-military-law-auditor", "procedure-auditor"],
         "reviewers": {"independent-reviewer": {"stage": "blind", "source_prefixes": ["S-REV"], "finding_prefixes": ["F-BLIND-"]}}}


def run(sources=SOURCES, findings=(FINDING,), reviews=(REVIEW,), manifest=None, strict=True, identities=IDENT):
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
            m.write_text(json.dumps({"records": manifest}), encoding="utf-8")
        with redirect_stdout(StringIO()) as out:
            ok = V.validate_batch(d, strict=strict, manifest=m)
        return ok, json.loads(out.getvalue())["errors"]


def edit(obj, **kw):
    o = copy.deepcopy(obj); o.update(kw); return o


class ExtendedControls(unittest.TestCase):
    MAN = [{"record_id": "KB-1", "original_sha256": H}]

    def test_valid_batch_passes(self):
        ok, errs = run(manifest=self.MAN)
        self.assertTrue(ok, errs)

    def test_record_not_in_manifest(self):
        self.assertFalse(run(manifest=[{"record_id": "KB-2", "original_sha256": H}])[0])

    def test_input_hash_mismatch(self):
        self.assertFalse(run(manifest=[{"record_id": "KB-1", "original_sha256": "b" * 64}])[0])

    def test_manifest_record_without_outcome(self):
        ok, errs = run(manifest=self.MAN + [{"record_id": "KB-9", "original_sha256": H}])
        self.assertFalse(ok); self.assertTrue(any("KB-9" in e for e in errs))

    def test_missing_pinpoint_on_verified_source(self):
        src = [edit(SOURCES[0], pinpoint=None)] + SOURCES[1:]
        self.assertFalse(run(sources=src)[0])

    def test_missing_effective_date_on_rule(self):
        src = [edit(SOURCES[0], version_or_decision_date=None, effective_date=None)] + SOURCES[1:]
        self.assertFalse(run(sources=src)[0])

    def test_reviewer_reusing_first_pass_source_fails(self):
        r = edit(REVIEW, source_ids=["S-AR"], independent_source_ids=["S-AR"])
        self.assertFalse(run(reviews=[r])[0])

    def test_reviewer_without_own_source_fails(self):
        self.assertFalse(run(reviews=[edit(REVIEW, independent_source_ids=[])])[0])

    def test_independent_agent_cannot_accept(self):
        self.assertFalse(run(reviews=[edit(REVIEW, decision="ACCEPTED_FOR_CANDIDATE")])[0])

    def test_mml_hash_mismatch(self):
        src = SOURCES[:1] + [edit(SOURCES[1], sha256="c" * 64)] + SOURCES[2:]
        self.assertFalse(run(sources=src)[0])

    def test_mml_unknown_file(self):
        src = SOURCES[:1] + [edit(SOURCES[1], locator="MML 9.pdf")] + SOURCES[2:]
        self.assertFalse(run(sources=src)[0])

    def test_mml_official_authenticity_rejected(self):
        src = SOURCES[:1] + [edit(SOURCES[1], authenticity="ORIGINAL_OFFICIAL")] + SOURCES[2:]
        self.assertFalse(run(sources=src)[0])

    def test_manual_only_verification_blocked_for_cross_volume(self):
        f = edit(FINDING, workstream="CROSS_VOLUME", source_ids=["S-MML"])
        self.assertFalse(run(findings=[f])[0])

    def test_no_issue_requires_verified(self):
        self.assertFalse(run(findings=[edit(FINDING, verification_state="SOURCE_LOCATED")])[0])

    def test_conflict_state_agreement(self):
        f = edit(FINDING, verification_state="CONFLICTING", examination_outcome="DISCREPANCY",
                 requires_legal_review=True, legal_review_state="QUEUED_ADVISOR_NOT_NOMINATED")
        self.assertFalse(run(findings=[f])[0])

    def test_blocked_requires_blocked_review_state(self):
        f = edit(FINDING, verification_state="NOT_FOUND", examination_outcome="BLOCKED")
        self.assertFalse(run(findings=[f])[0])

    def test_advisor_reviewed_without_record(self):
        f = edit(FINDING, severity="P1", requires_legal_review=True, legal_review_state="ADVISOR_REVIEWED")
        self.assertFalse(run(findings=[f])[0])

    def test_p1_must_require_review(self):
        self.assertFalse(run(findings=[edit(FINDING, severity="P1")])[0])

    def test_strict_needs_outcome(self):
        f = copy.deepcopy(FINDING); del f["examination_outcome"]
        self.assertFalse(run(findings=[f])[0])


class IdentityControls(unittest.TestCase):
    TWO = {"first_pass_agents": ["statutory-auditor", "procedure-auditor"],
           "reviewers": {"independent-reviewer-A": {"stage": "adversarial", "source_prefixes": ["S-REVA-"]},
                         "independent-reviewer-B": {"stage": "adversarial", "source_prefixes": ["S-REVB-"]}}}

    def srcs(self):
        a = edit(SOURCES[2], source_id="S-REVA-1"); b = edit(SOURCES[2], source_id="S-REVB-1")
        return SOURCES[:2] + [a, b]

    def rev(self, **kw):
        base = dict(reviewer_id="independent-reviewer-A", source_ids=["S-REVA-1"],
                    independent_source_ids=["S-REVA-1"], blind=False)
        base.update(kw)
        return edit(REVIEW, **base)

    def test_bound_reviewer_passes(self):
        ok, errs = run(sources=self.srcs(), reviews=[self.rev()], identities=self.TWO)
        self.assertTrue(ok, errs)

    def test_strict_requires_identity_file(self):
        self.assertFalse(run(identities=None)[0])

    def test_undeclared_reviewer(self):
        self.assertFalse(run(sources=self.srcs(), reviews=[self.rev(reviewer_id="independent-reviewer-Z")], identities=self.TWO)[0])

    def test_reviewer_using_other_reviewers_source(self):
        r = self.rev(source_ids=["S-REVB-1"], independent_source_ids=["S-REVB-1"])
        self.assertFalse(run(sources=self.srcs(), reviews=[r], identities=self.TWO)[0])

    def test_unbound_reviewer_source(self):
        src = self.srcs() + [edit(SOURCES[2], source_id="S-XYZ-1")]
        self.assertFalse(run(sources=src, reviews=[self.rev()], identities=self.TWO)[0])

    def test_prefix_squatting_by_first_pass_agent(self):
        src = self.srcs() + [edit(SOURCES[0], source_id="S-REVA-9", retrieved_by="statutory-auditor")]
        self.assertFalse(run(sources=src, reviews=[self.rev()], identities=self.TWO)[0])

    def test_first_pass_citing_reviewer_source(self):
        f = edit(FINDING, source_ids=["S-AR", "S-REVA-1"])
        self.assertFalse(run(sources=self.srcs(), findings=[f], reviews=[self.rev()], identities=self.TWO)[0])

    def test_reviewing_own_finding(self):
        f = edit(FINDING, agent="independent-reviewer-A")
        self.assertFalse(run(sources=self.srcs(), findings=[f], reviews=[self.rev()], identities=self.TWO)[0])

    def test_blind_flag_requires_blind_stage(self):
        self.assertFalse(run(sources=self.srcs(), reviews=[self.rev(blind=True)], identities=self.TWO)[0])

    def test_exact_retrieved_by_enforced(self):
        ident = dict(self.TWO, require_exact_retrieved_by=True)
        self.assertFalse(run(sources=self.srcs(), reviews=[self.rev()], identities=ident)[0])
        src = [edit(x, retrieved_by="independent-reviewer-A") if x["source_id"] == "S-REVA-1" else
               edit(x, retrieved_by="independent-reviewer-B") if x["source_id"] == "S-REVB-1" else x for x in self.srcs()]
        ok, errs = run(sources=src, reviews=[self.rev()], identities=ident)
        self.assertTrue(ok, errs)


if __name__ == "__main__":
    unittest.main()
