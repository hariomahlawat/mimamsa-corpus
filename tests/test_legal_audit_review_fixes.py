"""Regression tests for the four Codex P2 review findings on WS-D-owned code (PR #18 and PR #22).

Each test reproduces the defect exactly as reported; it failed on the code before the fix (evidence in
legal_knowledge/audit_work/WS-D-QUALITY/REVIEW_FIXES_2026-11-22.md) and passes after. Structural only."""
import csv
import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AW = ROOT / "legal_knowledge" / "audit_work"
WSD = AW / "WS-D-QUALITY"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


COV = load("cov_fix", WSD / "scripts" / "coverage_scorecard.py")
V = load("val_fix", ROOT / "tools" / "legal_audit" / "validate.py")
CP = load("prov_fix", ROOT / "tools" / "legal_audit" / "check_provenance.py")
INDEX = {(r["record_id"], r["seg_no"]): r for r in csv.DictReader(
    io.StringIO((WSD / "plaintext_citation_index.csv").read_text(encoding="utf-8"), newline=""))}
H = "a" * 64


def pic_render(check_id):
    rows = csv.DictReader(io.StringIO((AW / "PILOT-01/registers/page_image_checks.csv").read_text(encoding="utf-8"), newline=""))
    return next(r["render_png_sha256"] for r in rows if r["check_id"] == check_id)


# ---------------- (1) PR #18: every instrument in a plain-text segment ----------------
class Fix1InstrumentPerLocator(unittest.TestCase):
    def test_adm_jd_02_rule_14_belongs_to_army_rules_not_army_act(self):
        seg = INDEX[("ADM-JD-02", "1")]
        self.assertEqual(seg["exact_text"], "judgment discussion of AA §19, AR r14 and §122")
        res = COV.assess_plain_segment(seg, seg)
        by_doc = {}
        for a in res:
            by_doc.setdefault(a["doc"], []).extend(a["numbers"])
        self.assertEqual(by_doc.get("act-army-1950"), ["19"],
                         f"Army Act must be credited with s.19 only; got {res}")
        ar = [a for a in res if a["doc"] == "rules-army-rules-1954"]
        self.assertTrue(ar, f"Army Rules not assessed at all; got {res}")
        self.assertEqual(ar[0]["rule_numbers"], ["14"])
        amb = [x for a in res for x in a.get("ambiguous", [])]
        self.assertTrue(any("122" in x for x in amb), f"'§122' after an AR context must be recorded as ambiguous; got {res}")

    def test_v7_wf_12_every_instrument_assessed(self):
        seg = INDEX[("V7-WF-12", "1")]
        res = COV.assess_plain_segment(seg, seg)
        self.assertEqual([a["token"] for a in res], ["AFT Act", "Constitution"],
                         f"both named instruments must be assessed; got {res}")
        self.assertIsNone([a for a in res if a["token"] == "Constitution"][0]["doc"])


# ---------------- (2) PR #18: PAGE_IMAGE_READING needs a registered check id ----------------
class Fix2PageImageReadingRegisteredCheck(unittest.TestCase):
    def test_page_image_reading_with_nonexistent_check_is_rejected(self):
        it = load("integ_fix", ROOT / "tests" / "test_legal_audit_integrity_controls.py")
        src = it.edit(it.GAZ, source_type="RULE", authenticity="OFFICIAL_COMPILATION",
                      document_authority="GOVERNMENT_COMPILATION", carrier_provenance="GOVERNMENT_HOSTED_COPY",
                      copy_fidelity="HASH_ONLY", content_role="ENACTED_TEXT", instrument_identity=KeyError,
                      proof_type="PAGE_IMAGE_READING", render_sha256="b" * 64, page_image_check_id="nonexistent")
        ok, errs = it.run(sources=[src])
        self.assertFalse(ok, "PAGE_IMAGE_READING with page_image_check_id 'nonexistent' was accepted")
        self.assertTrue(any("registered" in e and "PAGE_IMAGE_READING" in e for e in errs), errs)


# ---------------- (3) PR #22: complete check IDs, no prefix stripping ----------------
def run_batch_with_register(source, register_rows):
    with tempfile.TemporaryDirectory() as root:
        d = Path(root)
        (d / "registers").mkdir()
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\n")
        w.writerow(["check_id", "document", "document_sha256", "page", "render_png_sha256"])
        w.writerows(register_rows)
        (d / "registers" / "page_image_checks_fixture.csv").write_text(buf.getvalue(), encoding="utf-8")
        for name, rows in (("sources", [source]), ("findings", []), ("reviews", [])):
            (d / name).mkdir()
            (d / name / "x.json").write_text(json.dumps(rows), encoding="utf-8")
        out = StringIO()
        with redirect_stdout(out):
            ok = V.validate_batch(d, False, None)
        return ok, json.loads(out.getvalue())["errors"]


class Fix3CompleteCheckIds(unittest.TestCase):
    SRC = {"source_id": "S-X", "source_type": "RULE", "title": "t", "issuer": "i", "locator": "l", "pinpoint": "p",
           "retrieved_on": "2026-11-22", "verification_state": "SOURCE_LOCATED", "authenticity": "OFFICIAL_COMPILATION"}

    def test_prefixed_id_not_masked_by_unprefixed_entry(self):
        ok, errs = run_batch_with_register(dict(self.SRC, page_image_check_id="WSZ-PIC-900"),
                                           [["PIC-900", "doc", H, "p.1", "c" * 64]])
        self.assertFalse(ok, "WSZ-PIC-900 was resolved through an unrelated unprefixed PIC-900")
        self.assertTrue(any("WSZ-PIC-900" in e for e in errs), errs)

    def test_prefixed_id_resolves_to_its_own_entry(self):
        ok, errs = run_batch_with_register(dict(self.SRC, page_image_check_id="WSZ-PIC-901"),
                                           [["WSZ-PIC-901", "doc", H, "p.1", "c" * 64]])
        self.assertTrue(ok, errs)

    def test_check_provenance_does_not_strip_prefixes(self):
        reg = "check_id,document,document_sha256,render_png_sha256\nPIC-5,doc,%s,%s\n" % (H, "c" * 64)
        row = "instr_id,evidence_level,sha256,evidence_locator\nAR-1,IMAGE_CHECKED,,WSD-PIC-5\n"
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "page_image_checks_x.csv").write_text(reg, encoding="utf-8")
            (Path(d) / "reg.csv").write_text(row, encoding="utf-8")
            viol, _ = CP.scan([Path(d)])
        self.assertEqual([v["rule"] for v in viol], ["IMG-2"], "WSD-PIC-5 was resolved through unrelated PIC-5")


# ---------------- (4) PR #22: manual_supported evidence bound to the check record ----------------
MML2 = "db2119182ed2e4ccca22dd225d955327f6398ee98303e1c94615ba85b4396f65"


def relation(**kw):
    rel = {"relation_id": "REL-KB-003-MML2-p152", "relation_type": "manual_supported", "from_record_id": "KB-003",
           "mml_file": "MML 2.pdf", "mml_file_sha256": MML2, "locator": "PDF p.152", "page_image_check_id": "PIC-02",
           "render_sha256": pic_render("PIC-02"), "content_role": "MANUAL_REPRODUCED_LEGAL_TEXT",
           "document_authority": "UNVERIFIED_MANUAL", "carrier_provenance": "USER_SUPPLIED",
           "legal_effect": "NOT_STATUTORY_AUTHORITY", "asserted_by": "manual-of-military-law-auditor", "asserted_on": "2026-11-23"}
    rel.update(kw)
    return rel


def run_relations(rels):
    with tempfile.TemporaryDirectory() as root:
        d = Path(root)
        for name, rows in (("sources", []), ("findings", []), ("reviews", []), ("relations", rels)):
            (d / name).mkdir()
            (d / name / "x.json").write_text(json.dumps(rows), encoding="utf-8")
        out = StringIO()
        with redirect_stdout(out):
            ok = V.validate_batch(d, False, None)
        return ok, json.loads(out.getvalue())["errors"]


class Fix4RelationBoundToCheckRecord(unittest.TestCase):
    def test_genuine_mml_check_with_its_real_render_passes(self):
        ok, errs = run_relations([relation()])
        self.assertTrue(ok, errs)

    def test_other_document_check_with_fabricated_render_is_rejected(self):
        ok, errs = run_relations([relation(page_image_check_id="PIC-10", render_sha256="f" * 64)])
        self.assertFalse(ok, "relation accepted with PIC-10 (a 1954 Gazette page) and a fabricated render hash")

    def test_fabricated_render_on_the_right_check_is_rejected(self):
        ok, errs = run_relations([relation(render_sha256="f" * 64)])
        self.assertFalse(ok)
        self.assertTrue(any("render" in e for e in errs), errs)

    def test_cross_document_check_with_its_real_render_is_rejected(self):
        ok, errs = run_relations([relation(page_image_check_id="PIC-01", render_sha256=pic_render("PIC-01"))])
        self.assertFalse(ok, "PIC-01 is an India Code compilation page, not MML 2.pdf")


if __name__ == "__main__":
    unittest.main()
