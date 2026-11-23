"""CALIBRATION-02: propositions are deterministic and the findings validator rejects each defect it guards."""
import csv, importlib.util, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
C2 = ROOT / "legal_knowledge/audit_work/CALIBRATION-02"


def load(name):
    spec = importlib.util.spec_from_file_location(name, C2 / "tools" / f"{name}.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


class Propositions(unittest.TestCase):
    def test_byte_identical_and_complete(self):
        bp = load("build_propositions")
        with tempfile.TemporaryDirectory() as t:
            out = Path(t) / "p.csv"; bp.main(out)
            self.assertEqual(out.read_bytes(), (C2 / "propositions.csv").read_bytes())
        rows = list(csv.DictReader(open(C2 / "propositions.csv", newline="", encoding="utf-8")))
        self.assertEqual(len({r["record_id"] for r in rows}), 46)
        self.assertEqual(len({r["proposition_id"] for r in rows}), len(rows))


class Validator(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory(); base = Path(self.t.name) / "CALIBRATION-02"
        (base / "tools").mkdir(parents=True); (base / "reviews" / "A").mkdir(parents=True)
        shutil.copy(C2 / "tools/check_calibration02.py", base / "tools")
        shutil.copy(C2 / "propositions.csv", base / "propositions.csv")
        self.base = base
        cv = load("check_calibration02"); self.cols = cv.COLS
        self.props = list(csv.DictReader(open(C2 / "propositions.csv", newline="", encoding="utf-8")))

    def tearDown(self): self.t.cleanup()

    def write(self, mutate=None, drop=0):
        rows = []
        for i, p in enumerate(self.props[drop:], 1):
            d = {c: "" for c in self.cols}
            d.update(finding_id=f"A-{i:04d}", reviewer="A", record_id=p["record_id"], proposition_id=p["proposition_id"],
                     dimension="STATUTORY", evidence_state="SOURCE_NOT_HELD", defect_class="NONE", severity="NONE")
            rows.append(d)
        if mutate: mutate(rows[0])
        with open(self.base / "reviews/A/findings.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=self.cols, lineterminator="\n"); w.writeheader(); w.writerows(rows)

    def run_check(self):
        p = subprocess.run([sys.executable, str(self.base / "tools/check_calibration02.py")], capture_output=True, text=True)
        return p.returncode, p.stdout

    def test_valid_passes(self):
        self.write(); self.assertEqual(self.run_check()[0], 0)

    def test_missing_coverage_fails(self):
        self.write(drop=1); rc, out = self.run_check(); self.assertEqual(rc, 1); self.assertIn("not covered", out)

    def test_verified_without_hash_fails(self):
        self.write(lambda d: d.update(evidence_state="VERIFIED_AGAINST_HELD_PRIMARY_SOURCE", locator="p.1"))
        rc, out = self.run_check(); self.assertEqual(rc, 1); self.assertIn("without full source_sha256", out)

    def test_p1_without_correction_fails(self):
        self.write(lambda d: d.update(severity="P1", defect_class="OMISSION"))
        rc, out = self.run_check(); self.assertEqual(rc, 1); self.assertIn("without correction", out)

    def test_p2_with_defect_none_fails(self):
        self.write(lambda d: d.update(severity="P2", proposed_correction="x"))
        rc, out = self.run_check(); self.assertEqual(rc, 1); self.assertIn("defect_class NONE", out)

    def test_bad_state_fails(self):
        self.write(lambda d: d.update(evidence_state="LEGALLY_VERIFIED"))
        rc, out = self.run_check(); self.assertEqual(rc, 1); self.assertIn("bad evidence_state", out)

    def test_wrong_reviewer_fails(self):
        self.write(lambda d: d.update(reviewer="B")); rc, out = self.run_check(); self.assertEqual(rc, 1)

    def _held(self, path, sha):
        (self.base / "registers").mkdir(exist_ok=True)
        (self.base / "registers/held_sources_scratchpad.csv").write_text(
            f"scratchpad_relative_path,bytes,sha256,note\n{path},10,{sha},\n", encoding="utf-8")

    def test_verified_sha_not_held_fails(self):
        self._held("downloads/x.pdf", "b" * 64)
        self.write(lambda d: d.update(evidence_state="VERIFIED_AGAINST_HELD_PRIMARY_SOURCE", source_sha256="0" * 64, locator="p.1"))
        rc, out = self.run_check(); self.assertEqual(rc, 1); self.assertIn("not in the held-source index", out)

    def test_verified_derived_text_fails(self):
        self._held("derived/vk.txt", "c" * 64)
        self.write(lambda d: d.update(evidence_state="VERIFIED_AGAINST_HELD_PRIMARY_SOURCE", source_sha256="c" * 64, locator="p.1"))
        rc, out = self.run_check(); self.assertEqual(rc, 1); self.assertIn("derived or secondary", out)

    def test_verified_primary_pdf_passes(self):
        self._held("downloads/judgment.pdf", "d" * 64)
        self.write(lambda d: d.update(evidence_state="VERIFIED_AGAINST_HELD_PRIMARY_SOURCE", source_sha256="d" * 64, locator="p.1"))
        self.assertEqual(self.run_check()[0], 0)

    def test_trivial_missing_evidence_fails(self):
        self.write(lambda d: d.update(severity="P2", defect_class="OMISSION", missing_evidence="."))
        rc, out = self.run_check(); self.assertEqual(rc, 1); self.assertIn("without correction", out)

    def test_approval_claim_in_free_text_fails(self):
        self.write(lambda d: d.update(finding="status JAG_VALIDATED by reviewer"))
        rc, out = self.run_check(); self.assertEqual(rc, 1); self.assertIn("approval claim", out)

    def test_negated_approval_text_passes(self):
        self.write(lambda d: d.update(finding="NOT_LEGALLY_APPROVED; no JAG approval claimed"))
        self.assertEqual(self.run_check()[0], 0)

    def test_unknown_proposition_fails(self):
        self.write(lambda d: d.update(proposition_id="ZZ-999#P1")); rc, out = self.run_check(); self.assertEqual(rc, 1); self.assertIn("unknown proposition_id", out)

    def test_record_mismatch_fails(self):
        self.write(lambda d: d.update(record_id="KB-001" if d["record_id"] != "KB-001" else "KB-002")); rc, out = self.run_check(); self.assertEqual(rc, 1); self.assertIn("record_id mismatch", out)

    def test_duplicate_finding_id_fails(self):
        cols = self.cols
        self.write()
        rows = list(csv.DictReader(open(self.base / "reviews/A/findings.csv", newline="", encoding="utf-8")))
        rows[1]["finding_id"] = rows[0]["finding_id"]
        with open(self.base / "reviews/A/findings.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n"); w.writeheader(); w.writerows(rows)
        rc, out = self.run_check(); self.assertEqual(rc, 1); self.assertIn("duplicate finding_id", out)

    def test_wrong_header_fails(self):
        self.write()
        p = self.base / "reviews/A/findings.csv"; t = p.read_text(encoding="utf-8").split("\n", 1)
        p.write_text(t[0].replace("locator", "location") + "\n" + t[1], encoding="utf-8")
        rc, out = self.run_check(); self.assertEqual(rc, 1); self.assertIn("header must be exactly", out)



class Reconciliation(unittest.TestCase):
    """Fixture tests for reconcile.py classification rules (QC-07)."""
    COLS = None

    def _tree(self, findings, n=12):
        t = tempfile.TemporaryDirectory(); base = Path(t.name) / "CALIBRATION-02"
        (base / "tools").mkdir(parents=True); (base / "registers").mkdir()
        shutil.copy(C2 / "tools/reconcile.py", base / "tools")
        (base / "registers/held_sources_scratchpad.csv").write_text(
            "scratchpad_relative_path,bytes,sha256,note\ndownloads/official.pdf,10," + "e" * 64 + ",\nderived/x.txt,10," + "f" * 64 + ",\n", encoding="utf-8")
        props = [["1", "R-1", f"R-1#P{i}", "body_sentence", f"text {i}", "M", "T", "K", "S", "0" * 64] for i in range(1, n + 1)]
        with open(base / "propositions.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(["calibration_rank", "record_id", "proposition_id", "proposition_kind", "text_verbatim", "module", "title", "kind", "status_as_recorded", "record_canonical_sha256"])
            w.writerows(props)
        cols = load("check_calibration02").COLS
        for rv in "ABCD":
            (base / "reviews" / rv).mkdir(parents=True)
            rows = []
            for i in range(1, n + 1):
                d = {c: "" for c in cols}
                d.update(finding_id=f"{rv}-{i}", reviewer=rv, record_id="R-1", proposition_id=f"R-1#P{i}", dimension="STATUTORY",
                         evidence_state="NOT_YET_REVIEWED", defect_class="NONE", severity="NONE")
                d.update(findings.get((rv, i), {}))
                rows.append(d)
            with open(base / "reviews" / rv / "findings.csv", "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n"); w.writeheader(); w.writerows(rows)
        subprocess.run([sys.executable, str(base / "tools/reconcile.py")], check=True, capture_output=True)
        m = {r["proposition_id"]: r for r in csv.DictReader(open(base / "reconciliation/proposition_matrix.csv", newline="", encoding="utf-8"))}
        p = list(csv.DictReader(open(base / "proposals/correction_proposals.csv", newline="", encoding="utf-8")))
        d = list(csv.DictReader(open(base / "reconciliation/disagreements.csv", newline="", encoding="utf-8")))
        return t, m, p, d

    def test_classes(self):
        H, PR, DV = "a" * 64, "e" * 64, "f" * 64
        P2 = dict(severity="P2", defect_class="OMISSION", evidence_state="UNSUPPORTED", proposed_correction="fix the text here", source_sha256=H, locator="p.1")
        VER = dict(evidence_state="VERIFIED_AGAINST_HELD_PRIMARY_SOURCE", source_sha256=PR, locator="p.2")
        f = {("A", 1): P2, ("B", 1): VER,                                                                 # DISAGREE (verified as stated)
             ("A", 2): P2, ("C", 2): dict(severity="P3", defect_class="OMISSION", evidence_state="SUPPORTED_BY_SECONDARY_SOURCE_ONLY"),  # SEVERITY_SPLIT
             ("A", 3): P2, ("D", 3): P2,                                                                  # CORROBORATED, no spread
             ("A", 4): P2,                                                                                # SINGLE (others silent)
             ("A", 5): dict(P2, evidence_state="CONTRADICTORY_EVIDENCE"), ("C", 5): dict(P2, **VER), ("B", 5): VER,  # source conflict beats dispute
             ("A", 6): dict(evidence_state="NOT_A_LEGAL_PROPOSITION"),                                    # non-legal
             ("A", 7): P2, ("B", 7): dict(evidence_state="NOT_A_LEGAL_PROPOSITION"),                      # dissent by non-legal classification
             ("A", 8): dict(P2, severity="P1"), ("C", 8): P2, ("B", 8): dict(severity="P3", defect_class="OMISSION", evidence_state="SUPPORTED_BY_SECONDARY_SOURCE_ONLY"),  # corroborated + spread
             ("A", 9): dict(evidence_state="SUPPORTED_BY_SECONDARY_SOURCE_ONLY"),                         # no material defect
             ("A", 10): dict(P2, **VER, proposed_correction="primary-backed correction"),                 # PRIMARY
             ("A", 11): dict(P2, proposed_correction="", missing_evidence="needs Gazette page", source_sha256="", locator=""),  # GAP
             ("A", 12): dict(P2, evidence_state="VERIFIED_AGAINST_HELD_PRIMARY_SOURCE", source_sha256=DV)}  # derived file is not primary
        t, m, p, d = self._tree(f)
        try:
            ag = {k: v["agreement"] for k, v in m.items()}
            self.assertEqual(ag["R-1#P1"], "DISAGREE")
            self.assertEqual(ag["R-1#P2"], "SEVERITY_SPLIT")
            self.assertEqual(ag["R-1#P3"], "CORROBORATED_DEFECT")
            self.assertEqual(ag["R-1#P4"], "SINGLE_REVIEWER_DEFECT")
            self.assertEqual(ag["R-1#P6"], "ALL_NON_LEGAL_OR_OUT_OF_SCOPE")
            self.assertEqual(ag["R-1#P7"], "DISAGREE")
            self.assertEqual(ag["R-1#P8"], "CORROBORATED_DEFECT")
            self.assertEqual(ag["R-1#P9"], "NO_MATERIAL_DEFECT_RAISED")
            kinds = {x["proposition_id"]: x["kind"] for x in d}
            self.assertEqual(kinds.get("R-1#P8"), "SEVERITY_SPLIT")       # corroborated spread is escalated
            self.assertNotIn("R-1#P3", kinds)
            self.assertIn("not a legal proposition", [x for x in d if x["proposition_id"] == "R-1#P7"][0]["reason"])
            st = {(x["proposition_id"], x["reviewer"]): x["support_status"] for x in p}
            self.assertEqual(st[("R-1#P1", "A")], "DISPUTED_ESCALATED")
            self.assertEqual(st[("R-1#P3", "A")], "SECONDARY_EVIDENCE_ONLY")
            self.assertEqual(st[("R-1#P5", "C")], "SOURCE_CONFLICT_OPEN")
            self.assertEqual(st[("R-1#P10", "A")], "PRIMARY_EVIDENCE_SUPPORTED")
            self.assertEqual(st[("R-1#P11", "A")], "EVIDENCE_GAP")
            self.assertEqual(st[("R-1#P12", "A")], "SECONDARY_EVIDENCE_ONLY")
            for x in p:
                self.assertEqual(x["incorporation_state"], "PROPOSED_NOT_INCORPORATED (original record unchanged)")
        finally:
            t.cleanup()

    def test_committed_outputs_reproduce(self):
        names = ["reconciliation/proposition_matrix.csv", "reconciliation/disagreements.csv", "reconciliation/record_scorecard.csv",
                 "reconciliation/scorecard.json", "proposals/correction_proposals.csv", "proposals/proposed_versions.jsonl",
                 "registers/cross_volume_register.csv", "adviser/legal_adviser_questions.csv", "reconciliation/rule_sensitivity.json"]
        before = {n: (C2 / n).read_bytes() for n in names}
        try:
            subprocess.run([sys.executable, str(C2 / "tools/reconcile.py")], check=True, capture_output=True)
            subprocess.run([sys.executable, str(C2 / "tools/build_packages.py")], check=True, capture_output=True)
            subprocess.run([sys.executable, str(C2 / "tools/rule_sensitivity.py")], check=True, capture_output=True)
            for n in names:
                self.assertEqual((C2 / n).read_bytes(), before[n], n)
        finally:
            for n, b in before.items():
                (C2 / n).write_bytes(b)


if __name__ == "__main__":
    unittest.main()
