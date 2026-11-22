"""Coordinator (baseline-register PR #28): short_title_as_printed must match the page-image record.

For every instrument-register row whose evidence_locator cites a chain page-image check (PIC-37..PIC-40), the
short title recorded as printed must appear verbatim, in quotes, in that check's observed_on_image text."""
import csv
import re
import unittest
from pathlib import Path

AW = Path(__file__).resolve().parents[1] / "legal_knowledge" / "audit_work" / "ARMY-RULES-CHAIN-01"


def rows(name):
    with open(AW / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class ShortTitleAsPrinted(unittest.TestCase):
    def test_short_title_matches_page_image(self):
        pics = {r["check_id"]: r for r in rows("page_image_checks_chain.csv")}
        checked = 0
        for r in rows("army_rules_instrument_register.csv"):
            for pid in re.findall(r"PIC-(?:3[7-9]|40)\b", r["evidence_locator"]):
                obs = pics[pid]["observed_on_image"]
                quoted = re.findall(r"'([^']*Rules, \d{4})", obs)
                if not quoted:
                    continue  # this check does not quote the short title (e.g. PIC-40)
                checked += 1
                self.assertIn(r["short_title_as_printed"], [q.split("called the ")[-1] for q in quoted],
                              f"{r['instr_id']} short title differs from {pid}")
        self.assertGreaterEqual(checked, 3)


if __name__ == "__main__":
    unittest.main()
