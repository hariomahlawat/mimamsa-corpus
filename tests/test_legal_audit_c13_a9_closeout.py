"""C13-A9 closeout records: the findings register reproduces, statuses are valid, no restriction is lifted."""
import csv
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PKG = REPO / "legal_knowledge" / "audit_work" / "C13-A9-CLOSEOUT"
STATUSES = {"CLOSED", "OPEN", "DEFERRED", "ACCEPTED_DEVIATION"}


def read_csv(p):
    with open(p, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def git_available():
    return subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True).returncode == 0


class A9Closeout(unittest.TestCase):
    @unittest.skipUnless(git_available(), "git history not available")
    def test_register_reproduces(self):
        r = subprocess.run([sys.executable, "-I", "-B", str(PKG / "tools" / "build_findings_c13.py"), "--check"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_statuses_and_carry_overs(self):
        rows = read_csv(PKG / "FINDINGS_REGISTER_C13.csv")
        self.assertTrue(rows)
        self.assertTrue({r["status"] for r in rows} <= STATUSES)
        carry = {r["review_finding_id"]: r["status"] for r in rows if r["workstream"] == "C12 carry-over"}
        self.assertEqual(set(carry), {"C11-extraction F05", "C11-extraction F06", "C11-extraction F07",
                                      "C11-extraction F08", "WSG-R04"})
        self.assertEqual(set(carry.values()), {"DEFERRED"})
        self.assertFalse([r for r in rows if r["severity"] == "P1" and r["status"] == "OPEN"])

    def test_no_restriction_lifted(self):
        rows = read_csv(PKG / "RESEARCH_RESTRICTIONS_C13.csv")
        cap = read_csv(REPO / "legal_knowledge/audit_work/C12-CONSOLIDATION/CAPABILITY_RESTRICTIONS.csv")
        self.assertEqual({r["capability"] for r in rows}, {r["capability"] for r in cap})
        self.assertEqual({r["c13_decision"] for r in rows}, {"NOT_LIFTED_STILL_RESTRICTED"})

    def test_rm001_absent_from_records(self):
        for p in PKG.glob("*"):
            if p.is_file():
                t = p.read_text(encoding="utf-8").lower()
                self.assertNotIn("4284820e", t, p.name)
                self.assertNotIn("regs-regulations-for-the-air-force", t, p.name)


if __name__ == "__main__":
    unittest.main()
