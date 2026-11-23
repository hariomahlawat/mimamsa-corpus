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


if __name__ == "__main__":
    unittest.main()
