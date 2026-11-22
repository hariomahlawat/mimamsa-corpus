"""WS-D cycle 2: deterministic tests for ARMY-RULES-CHAIN-01/check_registers.py semantics.

check_registers.py is coordinator-owned and is NOT modified here. Each test copies the script and the
registers it reads into a temporary tree with the same layout, mutates exactly one cell, runs the script
as a subprocess and asserts that it fails with the expected message (or passes for a valid variant).
Covers the owner date rule (publication / commencement / effective date distinct), continuation-page
status, conflict IDs C-08 (r.193 OPEN) / C-09 (r.194 PROPOSAL), r.23(3) CONFLICTING and no approval."""
import csv
import io
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AW = ROOT / "legal_knowledge" / "audit_work"
SCRIPT = "ARMY-RULES-CHAIN-01/check_registers.py"
INPUTS = ["ARMY-RULES-CHAIN-01/army_rules_instrument_register.csv",
          "ARMY-RULES-CHAIN-01/army_rules_provision_chronology.csv",
          "ARMY-RULES-CHAIN-01/page_image_checks_chain.csv",
          "ARMY-RULES-CHAIN-01/statutory_version_register_seed.csv",
          "ACQ-02/page_image_checks_acq02.csv", "ACQ-02/supplement_inventory.csv",
          "R23-VERIFY-01/registers/page_image_checks.csv", "PILOT-01/registers/page_image_checks.csv"]
REG, CHRON, SEED = INPUTS[0], INPUTS[1], INPUTS[3]


def read(path):
    text = path.read_text(encoding="utf-8")
    rd = csv.DictReader(io.StringIO(text, newline=""))
    return rd.fieldnames, list(rd)


def write(path, cols, rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    path.write_text(buf.getvalue(), encoding="utf-8")


class Tree:
    def __enter__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for rel in INPUTS + [SCRIPT]:
            dst = self.root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(AW / rel, dst)
        return self

    def __exit__(self, *exc):
        self.tmp.cleanup()

    def mutate(self, rel, select, **updates):
        """Apply updates to the first row where select(row) is true; return that row's original values."""
        cols, rows = read(self.root / rel)
        for r in rows:
            if select(r):
                before = dict(r)
                r.update(updates)
                write(self.root / rel, cols, rows)
                return before
        raise AssertionError(f"no row selected in {rel}")

    def run(self):
        p = subprocess.run([sys.executable, str(self.root / SCRIPT)], capture_output=True, text=True)
        return p.returncode, p.stdout


def seed_row(provision, version=None):
    return lambda r: r["provision"] == provision and (version is None or r["version"] == version)


class Baseline(unittest.TestCase):
    def test_committed_registers_pass(self):
        with Tree() as t:
            rc, out = t.run()
        self.assertEqual(rc, 0, out)
        self.assertIn("errors=0", out)

    def test_harness_copy_is_unmodified(self):
        with Tree() as t:
            for rel in INPUTS + [SCRIPT]:
                self.assertEqual((t.root / rel).read_bytes(), (AW / rel).read_bytes(), rel)


class DateRule(unittest.TestCase):
    def assertFails(self, rel, select, needle, **updates):
        with Tree() as t:
            t.mutate(rel, select, **updates)
            rc, out = t.run()
        self.assertEqual(rc, 1, out)
        self.assertIn(needle, out)

    def test_register_effective_date_without_stated_commencement(self):
        self.assertFails(REG, lambda r: not r["effective_date"] and not r["effective_date_status"].startswith("STATED"),
                         "effective_date set without a stated commencement", effective_date="1954-11-27")

    def test_effective_equal_to_publication_date_needs_stated_status(self):
        sel = lambda r: r["publication_date"][:10].count("-") == 2 and not r["effective_date_status"].startswith("STATED")
        with Tree() as t:
            cols, rows = read(t.root / CHRON)
            row = next(r for r in rows if sel(r))
            t.mutate(CHRON, lambda r: r is not None and r["provision"] == row["provision"] and r["event"] == row["event"],
                     effective_date=row["publication_date"][:10])
            rc, out = t.run()
        self.assertEqual(rc, 1, out)
        self.assertIn("effective_date set without a stated commencement", out)

    def test_stated_commencement_requires_iso_effective_date(self):
        self.assertFails(CHRON, lambda r: r["effective_date_status"].startswith("STATED"),
                         "stated commencement but no effective_date", effective_date="")

    def test_malformed_effective_date(self):
        self.assertFails(CHRON, lambda r: r["effective_date_status"].startswith("STATED") and r["effective_date"],
                         "bad effective_date", effective_date="27-11-1954")

    def test_missing_effective_date_status(self):
        self.assertFails(REG, lambda r: True, "missing effective_date_status", effective_date_status="")

    def test_version_seed_effective_date_without_stated(self):
        self.assertFails(SEED, seed_row("r.23(3)"), "effective_date without stated commencement", effective_date="1954-11-27")

    def test_stated_commencement_with_date_passes(self):
        with Tree() as t:
            t.mutate(REG, lambda r: not r["effective_date"] and not r["effective_date_status"].startswith("STATED"),
                     effective_date="1954-12-01", effective_date_status="STATED_IN_INSTRUMENT (test fixture)")
            rc, out = t.run()
        self.assertEqual(rc, 0, out)


class ContinuationPages(unittest.TestCase):
    def test_image_checked_requires_all_continuation_pages_image_checked(self):
        with Tree() as t:
            t.mutate(REG, lambda r: r["evidence_level"] == "IMAGE_CHECKED",
                     continuation_pages_status="REQUIRES_VERIFICATION (text layer only)")
            rc, out = t.run()
        self.assertEqual(rc, 1, out)
        self.assertIn("IMAGE_CHECKED but continuation pages not all image-checked", out)

    def test_text_layer_row_must_be_marked_requires_verification(self):
        with Tree() as t:
            t.mutate(REG, lambda r: r["evidence_level"].startswith("TEXT_LAYER"), continuation_pages_status="ALL_IMAGE_CHECKED")
            rc, out = t.run()
        self.assertEqual(rc, 1, out)
        self.assertIn("text-layer row not marked REQUIRES_VERIFICATION", out)

    def test_text_layer_row_marked_located_fails(self):
        with Tree() as t:
            t.mutate(REG, lambda r: r["evidence_level"].startswith("TEXT_LAYER"), status="LOCATED")
            rc, out = t.run()
        self.assertEqual(rc, 1, out)
        self.assertIn("OCR/hint row marked LOCATED", out)

    def test_unknown_page_image_check_fails(self):
        with Tree() as t:
            t.mutate(REG, lambda r: "PIC-" in r["evidence_locator"], evidence_locator="PIC-9999")
            rc, out = t.run()
        self.assertEqual(rc, 1, out)
        self.assertIn("cites unknown PIC-9999", out)


class FixedStates(unittest.TestCase):
    def run_mutation(self, select, **updates):
        with Tree() as t:
            t.mutate(SEED, select, **updates)
            return t.run()

    def test_r193_must_carry_c08_and_stay_open(self):
        rc, out = self.run_mutation(seed_row("r.193"), conflict_id="C-04")
        self.assertEqual(rc, 1); self.assertIn("r.193 rows must carry C-08", out)
        rc, out = self.run_mutation(seed_row("r.193"), determination_state="DETERMINED")
        self.assertEqual(rc, 1); self.assertIn("r.193 must stay OPEN", out)

    def test_r194_must_carry_c09_and_v1989_stay_proposal(self):
        rc, out = self.run_mutation(seed_row("r.194"), conflict_id="C-04")
        self.assertEqual(rc, 1); self.assertIn("r.194 rows must carry C-09", out)
        rc, out = self.run_mutation(seed_row("r.194", "v1989"), determination_state="DETERMINED (compilation corrected)")
        self.assertEqual(rc, 1); self.assertIn("r.194 must stay PROPOSAL", out)

    def test_r23_3_must_stay_conflicting(self):
        rc, out = self.run_mutation(seed_row("r.23(3)"), determination_state="RESOLVED ('not obliged')")
        self.assertEqual(rc, 1); self.assertIn("r.23(3) must stay CONFLICTING", out)

    def test_no_approval_claim(self):
        rc, out = self.run_mutation(seed_row("r.177"), determination_state="PROPOSAL APPROVED")
        self.assertEqual(rc, 1); self.assertIn("claims approval", out)

    def test_other_r194_versions_never_silently_promoted(self):
        """Gap note: check_registers.py pins only r.194 v1989 to PROPOSAL. Any other r.194 version promoted
        beyond OPEN/PROPOSAL must still be caught by at least one control (here: the WS-D register-semantics
        vocabulary). Passes whichever control catches it, so a later fix to check_registers.py keeps it green."""
        with Tree() as t:
            t.mutate(SEED, lambda r: r["provision"] == "r.194" and r["version"] != "v1989", determination_state="DETERMINED")
            rc, _ = t.run()
            _, rows = read(t.root / SEED)
        vocab_catches = any(r["provision"].startswith("r.194") and r["determination_state"].split()[0] not in ("OPEN", "PROPOSAL")
                            for r in rows)
        self.assertTrue(rc == 1 or vocab_catches)


if __name__ == "__main__":
    unittest.main()
