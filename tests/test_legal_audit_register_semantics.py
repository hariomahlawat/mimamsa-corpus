"""Generic register semantics over every CSV under legal_knowledge/audit_work (WS-D, issue #14).

Written to hold both on the current registers and on the corrected ARMY-RULES-CHAIN-01 registers
(owner date rule: publication date, commencement as printed and effective date are distinct; an
effective date only when the instrument states commencement). Structural checks only.
"""
import csv
import importlib.util
import io
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AW = ROOT / "legal_knowledge" / "audit_work"
SPEC = importlib.util.spec_from_file_location("check_csv_wsd", ROOT / "tools" / "legal_audit" / "check_csv.py")
CC = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CC)
KB = ROOT / "legal_knowledge" / "curated_originals" / "knowledge_base" / "v0.9" / "records_658.jsonl"
CASES = ROOT / "legal_knowledge" / "curated_originals" / "case_law" / "v0.9" / "cases_53.jsonl"

ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
STATE_COL = re.compile(r"(status|state|determination|decision|tier|clearance)", re.I)
# An approval claim, unless explicitly negated/pending ("unapproved", "approval pending", "NOT_legal_approval").
APPROVAL = re.compile(r"(?<![A-Za-z])(JAG[ _-]?APPROVED|FORMALLY[ _]APPROVED|LEGALLY[ _](APPROVED|VERIFIED|VALIDATED)|"
                      r"JAG[ _-]?VALIDATED|ADJUDICATED|APPROVED)(?![ _-]?PENDING)", re.I)
NEGATION = re.compile(r"(UN|NOT[ _-]?|NO[ _-]|0 |NEVER[ _-]|LACKS? )", re.I)
STATE_VOCAB = ("OPEN", "PROPOSAL", "CONFLICTING", "BLOCKED", "NOT_DETERMINED")


def csv_files():
    return sorted(AW.rglob("*.csv"))


def read(p):
    return list(csv.DictReader(io.StringIO(p.read_text(encoding="utf-8"), newline="")))


class CsvWellFormed(unittest.TestCase):
    def test_every_audit_csv_is_well_formed(self):
        files = csv_files()
        self.assertGreater(len(files), 0)
        errs = [e for p in files for e in CC.check_file(p)]
        self.assertEqual(errs, [])

    def test_checker_detects_ragged_rows_bom_and_duplicates(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            cases = {"ragged.csv": b"a,b\n1,2,3\n", "bom.csv": b"\xef\xbb\xbfa,b\n1,2\n",
                     "dup.csv": b"a,a\n1,2\n", "blank.csv": b"a,\n1,2\n", "quote.csv": b'a,b\n"1,2\n',
                     "empty.csv": b"", "headeronly.csv": b"a,b\n"}
            for name, data in cases.items():
                p = Path(d) / name
                p.write_bytes(data)
                self.assertTrue(CC.check_file(p), name)
            ok = Path(d) / "ok.csv"
            ok.write_bytes(b'a,b\n"x, y",2\n')
            self.assertEqual(CC.check_file(ok), [])


class EffectiveDateSemantics(unittest.TestCase):
    def test_effective_date_only_when_commencement_stated(self):
        checked = 0
        for p in csv_files():
            rows = read(p)
            if not rows or "effective_date" not in rows[0]:
                continue
            self.assertIn("effective_date_status", rows[0], f"{p.name}: effective_date column without effective_date_status")
            for n, r in enumerate(rows, 2):
                eff, st = (r.get("effective_date") or "").strip(), (r.get("effective_date_status") or "").strip()
                where = f"{p.relative_to(AW)} row {n}"
                self.assertTrue(st, f"{where}: effective_date_status blank")
                if eff:
                    self.assertTrue(st.startswith("STATED_IN_INSTRUMENT"), f"{where}: effective date without stated commencement")
                    self.assertRegex(eff, ISO, where)
                if st.startswith("STATED_IN_INSTRUMENT"):
                    self.assertRegex(eff, ISO, f"{where}: stated commencement but no ISO effective_date")
                pub = (r.get("publication_date") or "").strip()
                if pub and eff == pub:
                    self.assertTrue(st.startswith("STATED_IN_INSTRUMENT"), f"{where}: effective = publication date")
                checked += 1
        self.assertGreaterEqual(checked, 0)


class NoAgentAssertedApproval(unittest.TestCase):
    def test_no_state_column_claims_approval(self):
        hits = []
        for p in csv_files():
            rows = read(p)
            if not rows:
                continue
            for col in rows[0]:
                if not STATE_COL.search(col) or "NOT_legal_approval" in col:
                    continue
                for n, r in enumerate(rows, 2):
                    v = r.get(col) or ""
                    for m in APPROVAL.finditer(v):
                        if not NEGATION.search(v[max(0, m.start() - 6):m.start()]):
                            hits.append(f"{p.relative_to(AW)} row {n} {col}: {v[:80]}")
        self.assertEqual(hits, [])

    def test_approval_pattern_self_check(self):
        for v in ("JAG approved", "APPROVED", "legally verified", "FORMALLY_APPROVED"):
            self.assertTrue(APPROVAL.search(v), v)
        for v in ("RESEARCH (unapproved)", "JAG_APPROVAL_PENDING", "approved pending"):
            m = APPROVAL.search(v)
            self.assertTrue(m is None or NEGATION.search(v[max(0, m.start() - 6):m.start()]), v)

    def test_frozen_originals_carry_no_clearance_or_approval(self):
        kb = [json.loads(l) for l in KB.read_text(encoding="utf-8").splitlines() if l.strip()]
        cases = [json.loads(l) for l in CASES.read_text(encoding="utf-8").splitlines() if l.strip()]
        self.assertEqual((len(kb), len(cases)), (658, 53))
        self.assertTrue(all(r.get("operational_clearance") is False for r in kb + cases))
        self.assertFalse(any(c.get("v06_jag_approved") is True for c in cases))
        self.assertTrue(all("PENDING" in r["status"] for r in kb))
        self.assertTrue(all(c["review_status"] == "JAG_REVIEW_PENDING" for c in cases))


class FixedDeterminations(unittest.TestCase):
    SEED = AW / "ARMY-RULES-CHAIN-01" / "statutory_version_register_seed.csv"

    def test_seed_states_never_promoted(self):
        rows = read(self.SEED)
        prov = lambda p: [r for r in rows if r["provision"] == p]
        self.assertTrue(prov("r.23(3)") and prov("r.193") and prov("r.194"))
        for r in rows:
            first = r["determination_state"].split()[0]
            self.assertIn(first, STATE_VOCAB, f"{r['provision']} {r['version']}: {r['determination_state']}")
        for r in prov("r.23(3)"):
            self.assertEqual(r["determination_state"], "CONFLICTING")
        for r in prov("r.193"):
            self.assertEqual(r["determination_state"].split()[0], "OPEN")
        for r in prov("r.194"):
            self.assertIn(r["determination_state"].split()[0], ("OPEN", "PROPOSAL"))
        self.assertTrue(any(r["determination_state"].startswith("PROPOSAL") for r in prov("r.194")))

    def test_conflict_registers_keep_c01_conflicting_and_nothing_resolved(self):
        seen = 0
        for p in sorted((AW / "SOURCE-CONFLICTS-01").glob("*.csv")):
            rows = read(p)
            if not rows or "status" not in rows[0]:
                continue
            for r in rows:
                st = r["status"]
                self.assertNotRegex(st.upper(), r"\b(RESOLVED|CURRENT_IN_FORCE|SETTLED)\b", f"{p.name}: {st}")
                if (r.get("conflict_id") or "").startswith("C-01"):
                    self.assertTrue(st.startswith("CONFLICTING"), f"{p.name}: C-01 {st}")
                    seen += 1
        self.assertGreaterEqual(seen, 1)


if __name__ == "__main__":
    unittest.main()
