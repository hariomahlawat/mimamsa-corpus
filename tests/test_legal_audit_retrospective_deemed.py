"""Coordinator (baseline-register PR): check_registers.py semantics for retrospective_deemed_effect_from.

Commencement (effective_date) and a retrospective deemed effect stated in the instrument are distinct values.
A deemed date may be recorded only on a row whose commencement is STATED_IN_INSTRUMENT, must be an ISO date,
and must precede the stated commencement. Reuses the WS-D temporary-tree harness without modifying it."""
import unittest

from test_legal_audit_check_registers import CHRON, REG, Tree


def ar024(r):
    return r.get("instr_id", r.get("instrument_id")) == "AR-024"


class RetrospectiveDeemed(unittest.TestCase):
    def test_committed_deemed_rows_pass(self):
        with Tree() as t:
            rc, out = t.run()
        self.assertEqual(rc, 0, out)

    def test_column_present_and_ar024_populated(self):
        from test_legal_audit_check_registers import AW, read
        for rel in (REG, CHRON):
            cols, rows = read(AW / rel)
            self.assertIn("retrospective_deemed_effect_from", cols, rel)
            hits = [r for r in rows if ar024(r)]
            self.assertTrue(hits, rel)
            for r in hits:
                self.assertEqual(r["retrospective_deemed_effect_from"], "1979-06-04", rel)
                self.assertEqual(r["effective_date"], "1988-09-17", rel)

    def test_bad_deemed_date_fails(self):
        with Tree() as t:
            t.mutate(REG, ar024, retrospective_deemed_effect_from="4 June 1979")
            rc, out = t.run()
        self.assertEqual(rc, 1, out)
        self.assertIn("bad retrospective_deemed_effect_from", out)

    def test_deemed_without_stated_commencement_fails(self):
        with Tree() as t:
            t.mutate(CHRON, lambda r: r["instrument_id"] == "AR-010", retrospective_deemed_effect_from="1960-01-01")
            rc, out = t.run()
        self.assertEqual(rc, 1, out)
        self.assertIn("deemed effect without a stated commencement", out)

    def test_deemed_not_before_commencement_fails(self):
        with Tree() as t:
            t.mutate(REG, ar024, retrospective_deemed_effect_from="1988-09-17")
            rc, out = t.run()
        self.assertEqual(rc, 1, out)
        self.assertIn("deemed effect not earlier than commencement", out)

    def test_deemed_date_must_not_be_written_into_effective_date(self):
        # Regression for the review condition: effective_date holds the stated commencement, not the deemed date.
        with Tree() as t:
            t.mutate(REG, ar024, effective_date="1979-06-04")
            rc, out = t.run()
        self.assertEqual(rc, 1, out)


if __name__ == "__main__":
    unittest.main()
