"""WS-D cycle 2: provenance controls (tools/legal_audit/check_provenance.py) and the optional
'manual_supported' relation layer (relation.schema.json + validate.py relation_checks).

Each rule is exercised with a minimal synthetic register that violates it and a variant that satisfies it.
The real audit tree must have no violation outside the pinned baseline. Structural only."""
import copy
import importlib.util
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AW = ROOT / "legal_knowledge" / "audit_work"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


CP = load("check_provenance_wsd", ROOT / "tools" / "legal_audit" / "check_provenance.py")
V = load("validate_rel_wsd", ROOT / "tools" / "legal_audit" / "validate.py")
H = "a" * 64
R = "b" * 64


def scan(files):
    with tempfile.TemporaryDirectory() as d:
        for name, text in files.items():
            p = Path(d) / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8")
        viol, _ = CP.scan([Path(d)])
    return viol


def rules(files):
    return sorted({v["rule"] for v in scan(files)})


PIC = "check_id,document,document_sha256,render_png_sha256\nPIC-1,Gazette,%s,%s\n" % (H, R)


class RealTree(unittest.TestCase):
    def test_no_violation_outside_baseline(self):
        with redirect_stdout(StringIO()):
            self.assertEqual(CP.main([]), 0)

    def test_baseline_entries_are_explained_and_not_wsd_files(self):
        base = json.loads(CP.BASELINE.read_text(encoding="utf-8"))["known_violations"]
        self.assertTrue(base)
        for b in base:
            for k in ("rule", "file", "row", "reason", "route_to"):
                self.assertTrue(b.get(k), (k, b))
            self.assertFalse(b["file"].startswith("WS-D-QUALITY/"), b)
        self.assertEqual(len({(b["rule"], b["file"], b["row"]) for b in base}), len(base))


class ImageRules(unittest.TestCase):
    def test_img1_page_image_register_needs_render_hash(self):
        self.assertEqual(rules({"page_image_checks_x.csv": PIC}), [])
        self.assertEqual(rules({"page_image_checks_x.csv": PIC.replace(R, "not recorded")}), ["IMG-1"])

    def test_img2_image_checked_row_needs_resolvable_render(self):
        bad = "instr_id,evidence_level,sha256,evidence_locator\nAR-1,IMAGE_CHECKED,,see text\n"
        self.assertEqual(rules({"reg.csv": bad}), ["IMG-2"])
        via_pic = "instr_id,evidence_level,sha256,evidence_locator\nAR-1,IMAGE_CHECKED,,PIC-1\n"
        self.assertEqual(rules({"reg.csv": via_pic, "page_image_checks_x.csv": PIC}), [])
        via_doc = "instr_id,evidence_level,sha256,evidence_locator\nAR-1,IMAGE_CHECKED,%s,R23 chain\n" % H
        self.assertEqual(rules({"reg.csv": via_doc, "page_image_checks_x.csv": PIC}), [])
        unresolved = "instr_id,evidence_level,sha256,evidence_locator\nAR-1,IMAGE_CHECKED,,PIC-99\n"
        self.assertEqual(rules({"reg.csv": unresolved, "page_image_checks_x.csv": PIC}), ["IMG-2"])

    def test_img2_resolves_through_foreign_key(self):
        reg = "instr_id,evidence_level,sha256,evidence_locator\nAR-1,IMAGE_CHECKED,,PIC-1\n"
        chron = "provision,event,instrument_id,evidence_level\nr.1,amended,AR-1,IMAGE_CHECKED\nr.2,amended,AR-404,IMAGE_CHECKED\n"
        v = scan({"reg.csv": reg, "chron.csv": chron, "page_image_checks_x.csv": PIC})
        self.assertEqual([(x["rule"], x["row"]) for x in v], [("IMG-2", "provision=r.2@amended")])

    def test_img3_page_image_wording_needs_render(self):
        bad = "row_id,wording_read_from,page_render_sha256\nH-1,PAGE_IMAGE,\nH-2,PDF_TEXT_LAYER,\n"
        self.assertEqual([x["row"] for x in scan({"holdings.csv": bad})], ["row_id=H-1"])
        ok = "row_id,wording_read_from,page_render_sha256\nH-1,PAGE_IMAGE,%s\n" % R
        self.assertEqual(rules({"holdings.csv": ok}), [])


class VerificationAndAuthority(unittest.TestCase):
    def test_rv1_requires_verification_never_with_image_checked_claim(self):
        bad = "instr_id,evidence_level,continuation_pages_status,status,sha256\nAR-1,IMAGE_CHECKED,REQUIRES_VERIFICATION (text layer),LOCATED,%s\n" % H
        self.assertIn("RV-1", rules({"reg.csv": bad, "page_image_checks_x.csv": PIC}))
        bad2 = "instr_id,evidence_level,copy_fidelity,status\nAR-2,TEXT_LAYER_ONLY,PAGE_IMAGE_CHECKED,LOCATED\n"
        self.assertIn("RV-1", rules({"reg.csv": bad2}))
        ok = "instr_id,evidence_level,copy_fidelity,status\nAR-3,TEXT_LAYER_ONLY,NOT_CHECKED,LOCATED_UNVERIFIED\n"
        self.assertEqual(rules({"reg.csv": ok}), [])

    def test_ca1_policy_enumerations(self):
        ok = ("row_id,document_authority,carrier_provenance,copy_fidelity,amendment_chain_status\n"
              "1,ENACTED_OR_NOTIFIED_PRIMARY (declaration),GOVERNMENT_HOSTED_COPY,HASH_ONLY,n/a\n")
        self.assertEqual(rules({"x.csv": ok}), [])
        for col, val in (("copy_fidelity", "ARCHIVAL_FACSIMILE_OF_OFFICIAL"), ("carrier_provenance", "archive.org"),
                         ("document_authority", "LAW"), ("amendment_chain_status", "DONE")):
            text = f"row_id,{col}\n1,{val}\n"
            self.assertEqual(rules({"x.csv": text}), ["CA-1"], col)
        self.assertEqual(rules({"x.csv": "row_id,held_copy_carrier_provenance\n1,WEBSITE\n"}), ["CA-1"])

    def test_ca2_user_supplied_cannot_be_custodian_authenticated(self):
        self.assertEqual(rules({"x.csv": "row_id,carrier_provenance,copy_fidelity\n1,USER_SUPPLIED,CUSTODIAN_AUTHENTICATED\n"}), ["CA-2"])


class AcquisitionRequests(unittest.TestCase):
    HDR = "request_id,target,status,approval_ref\n"

    def test_proposed_rows_pass(self):
        self.assertEqual(rules({"acquisition_requests.csv": self.HDR + "AQ-1,x,PROPOSED (not executed),\n"}), [])

    def test_fetched_without_approval_fails_and_with_approval_passes(self):
        self.assertEqual(rules({"acquisition_requests.csv": self.HDR + "AQ-1,x,FETCHED 2026-11-23,\n"}), ["ACQ-1"])
        self.assertEqual(rules({"acquisition_requests.csv": self.HDR + "AQ-1,x,FETCHED 2026-11-23,owner approval in PR #21\n"}), [])
        self.assertEqual(rules({"acquisition_requests.csv": "request_id,target,status\nAQ-1,x,DOWNLOADED\n"}), ["ACQ-1"])

    def test_downloaded_flag_column(self):
        q = "queue_id,case,downloaded_by_ws_b\nQ-1,x,NO\nQ-2,y,YES\n"
        self.assertEqual([x["row"] for x in scan({"pending_source_queue.csv": q})], ["queue_id=Q-2"])


class NoApprovalStates(unittest.TestCase):
    def test_csv_state_columns(self):
        self.assertEqual(rules({"x.csv": "row_id,status\n1,JAG_APPROVED\n"}), ["APR-1"])
        self.assertEqual(rules({"x.csv": "row_id,LEGAL_advisor_decision\n1,ADVISOR_ACCEPTED\n"}), ["APR-1"])
        for ok in ("JAG_APPROVAL_PENDING", "RESEARCH (unapproved)", "not legally validated", "PROPOSAL (pending legal review)"):
            self.assertEqual(rules({"x.csv": f"row_id,status\n1,{ok}\n"}), [], ok)
        self.assertEqual(rules({"x.csv": "row_id,notes\n1,JAG approved\n"}), [], "free-text columns are not states")

    def test_quoted_source_text_ignored_and_explicit_tokens_caught(self):
        wsc = ("cc_id,current_state\nCC-17,\"MML 2 p.93 reads 'any person approved of by the Judge Advocate General'; "
               "vol 2(AA) and India Code read 'an officer approved of'\"\n")
        self.assertEqual(rules({"candidate_corrections.csv": wsc}), [])
        for bad in ("ADVISOR_APPROVED", "approved by JAG", "APPROVED", "LEGAL_APPROVAL"):
            self.assertEqual(rules({"x.csv": f"row_id,status\n1,{bad}\n"}), ["APR-1"], bad)
        self.assertEqual(rules({"f.json": json.dumps({"status": "'APPROVED' as printed on the Gazette form"})}), [])
        self.assertEqual(rules({"f.json": json.dumps({"status": "APPROVED"})}), ["APR-1"])

    def test_json_state_keys(self):
        self.assertEqual(rules({"f.json": json.dumps([{"finding_id": "F", "review_state": "ACCEPTED_FOR_CANDIDATE"}])}), ["APR-1"])
        self.assertEqual(rules({"f.json": json.dumps({"x": {"legal_status": "legally approved"}})}), ["APR-1"])
        self.assertEqual(rules({"f.json": json.dumps({"review_state": "PENDING", "rationale": "JAG approved?"})}), [])


# ---------------- manual_supported relation layer ----------------
SRC = {"source_id": "S-AR", "source_type": "RULE", "title": "Army Rules 1954", "issuer": "MoD", "locator": "x",
       "pinpoint": "r.22", "retrieved_on": "2026-11-22", "version_or_decision_date": "1954-11-27",
       "verification_state": "SOURCE_LOCATED", "authenticity": "OFFICIAL_COMPILATION", "retrieved_by": "statutory-auditor"}
FIND = {"finding_id": "F1", "batch_id": "T", "record_id": "KB-003", "original_sha256": H, "workstream": "PROCEDURE",
        "severity": "P3", "issue_type": "OTHER", "claim": "c", "original_location": "l", "original_text": "t",
        "proposed_text": None, "rationale": "r", "source_ids": ["S-AR"], "verification_state": "SOURCE_LOCATED",
        "review_state": "PENDING", "requires_legal_review": False}
# Genuine evidence: PILOT-01 PIC-02 is a page-image check of MML 2.pdf (manifest hash db211918...) p.152, and
# render_sha256 is that check's registered render hash (review fix PR #22: evidence must match the check record).
PIC02_RENDER = "6f9054d335f11143af613adb9232665924d89c8d01da9f983267aca15be58cd9"
REL = {"relation_id": "REL-KB-003-MML2-p152", "relation_type": "manual_supported", "from_record_id": "KB-003",
       "mml_file": "MML 2.pdf", "mml_file_sha256": "db2119182ed2e4ccca22dd225d955327f6398ee98303e1c94615ba85b4396f65",
       "locator": "PDF p.152", "page_image_check_id": "PIC-02", "render_sha256": PIC02_RENDER,
       "content_role": "MANUAL_REPRODUCED_LEGAL_TEXT", "document_authority": "UNVERIFIED_MANUAL",
       "carrier_provenance": "USER_SUPPLIED", "legal_effect": "NOT_STATUTORY_AUTHORITY",
       "asserted_by": "manual-of-military-law-auditor", "asserted_on": "2026-11-23"}


def edit(o, **kw):
    out = copy.deepcopy(o)
    for k, v in kw.items():
        if v is KeyError:
            out.pop(k, None)
        else:
            out[k] = v
    return out


def run_batch(relations=(REL,), findings=(FIND,), sources=(SRC,)):
    with tempfile.TemporaryDirectory() as root:
        d = Path(root)
        for name, rows in (("sources", sources), ("findings", findings), ("reviews", ()), ("relations", relations)):
            (d / name).mkdir()
            (d / name / "x.json").write_text(json.dumps(list(rows)), encoding="utf-8")
        buf = StringIO()
        with redirect_stdout(buf):
            ok = V.validate_batch(d, False, None)
        out = json.loads(buf.getvalue())
        return ok, out["errors"], out["counts"]


class ManualSupportedRelation(unittest.TestCase):
    def test_valid_relation_passes_and_is_counted(self):
        ok, errs, counts = run_batch()
        self.assertTrue(ok, errs)
        self.assertEqual(counts.get("relation"), 1)

    def test_batches_without_relations_unchanged(self):
        with redirect_stdout(StringIO()) as buf:
            V.validate_batch(AW / "R23-VERIFY-01", True, AW / "R23-VERIFY-01" / "pilot-manifest.json")
        self.assertNotIn("relation", json.loads(buf.getvalue())["counts"])

    def test_never_statutory_authority(self):
        for bad in (edit(REL, legal_effect="STATUTORY_AUTHORITY"), edit(REL, relation_type="statutory_source"),
                    edit(REL, verification_state="SOURCE_VERIFIED"), edit(REL, document_authority="ENACTED_OR_NOTIFIED_PRIMARY"),
                    edit(REL, legal_effect=KeyError)):
            self.assertFalse(run_batch(relations=[bad])[0], bad)

    def test_relation_cannot_be_finding_evidence(self):
        ok, errs, _ = run_batch(findings=[edit(FIND, source_ids=["S-AR", REL["relation_id"]])])
        self.assertFalse(ok)
        self.assertTrue(any("cannot be cited as finding evidence" in e for e in errs))

    def test_relation_id_cannot_collide_with_source(self):
        src = edit(SRC, source_id=REL["relation_id"])
        self.assertFalse(run_batch(sources=[src], findings=[edit(FIND, source_ids=[REL["relation_id"]])])[0])

    def test_provenance_requirements(self):
        cases = {"wrong manual hash": edit(REL, mml_file_sha256="c" * 64),
                 "unknown manual": edit(REL, mml_file="MML 99.pdf"),
                 "check without render (PIC-08 not recorded)": edit(REL, page_image_check_id="PIC-08"),
                 "unknown check": edit(REL, page_image_check_id="PIC-9999"),
                 "unknown record": edit(REL, from_record_id="KB-999999"),
                 "official manual without edition ref": edit(REL, document_authority="GOVERNMENT_ISSUED_MANUAL"),
                 "bad id pattern": edit(REL, relation_id="X1")}
        for name, rel in cases.items():
            self.assertFalse(run_batch(relations=[rel])[0], name)

    def test_duplicate_relation_ids_fail(self):
        self.assertFalse(run_batch(relations=[REL, REL])[0])


if __name__ == "__main__":
    unittest.main()
