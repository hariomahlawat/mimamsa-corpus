"""Provision-level evidence in canonical coverage (P2 on PR #29, Codex thread PRRT_kwDOV2o5I866mW1q).

An identified statutory citation with section or rule references is searchable only when the corresponding
provision files exist in the corpus. A missing or empty provision index never yields ALL. ABSENT evidence
(corpus available, provision files missing) makes the source not searchable; an UNAVAILABLE corpus (ref absent)
yields NOT_CHECKED, never ALL. Coded and plain-text citations are treated identically.
Every test runs on committed in-file fixtures: none depends on the crawler-corpus ref, so none is skipped in CI.
Structural only; not legal correctness."""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WSD = ROOT / "legal_knowledge" / "audit_work" / "WS-D-QUALITY"
SPEC = importlib.util.spec_from_file_location("cc_secev", WSD / "scripts" / "canonical_coverage.py")
CC = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CC)

META = {"act-army-1950", "rules-army-rules-1954"}
AA_FULL = {f"s{n}" for n in (19, 79, 80, 81, 82)}
AR_FULL = {"r14", "r22"}


def corpus(sections):
    return {"ref": "fixture", "commit": "fixture-no-raw-data", "meta": set(META), "sections": sections, "sc_urls": {}}


def build(c):
    """Canonical coverage rows with the crawler corpus replaced by fixture c (None = corpus unavailable)."""
    orig = CC.load

    def patched(name, path):
        mod = orig(name, path)
        if name == "cov_cc":
            mod.corpus = lambda ref: c
        return mod
    CC.load = patched
    try:
        out, _ = CC.build("fixture")
    finally:
        CC.load = orig
    return {r["record_id"]: r for r in out}


class ProvisionEvidence(unittest.TestCase):
    def assertNotAll(self, row):
        self.assertNotEqual(row["source_searchable"], "ALL", row)
        self.assertEqual(row["anchored_full"], "NO", row)

    def test_empty_index_never_all(self):
        """Reported case: Army Act and Army Rules metadata present, section index EMPTY -> KB-003 must not be ALL."""
        rows = build(corpus({"act-army-1950": set(), "rules-army-rules-1954": set()}))
        self.assertNotAll(rows["KB-003"])
        self.assertEqual(rows["KB-003"]["source_searchable"], "NONE")
        self.assertIn("PROVISION_FILES_ABSENT", rows["KB-003"]["quality_flags"].split(";"))

    def test_missing_index_key_never_all(self):
        rows = build(corpus({}))
        self.assertNotAll(rows["KB-003"])
        self.assertEqual(rows["KB-003"]["source_searchable"], "NONE")

    def test_missing_section_files(self):
        rows = build(corpus({"act-army-1950": {"s79", "s80"}, "rules-army-rules-1954": set(AR_FULL)}))
        self.assertNotAll(rows["KB-003"])
        self.assertEqual(rows["KB-003"]["source_searchable"], "PARTLY")

    def test_partial_index(self):
        """Army Act sections indexed, Army Rules index empty: the rule-cited source is not searchable."""
        rows = build(corpus({"act-army-1950": set(AA_FULL), "rules-army-rules-1954": set()}))
        self.assertEqual(rows["KB-003"]["source_searchable"], "PARTLY")
        self.assertEqual(rows["KB-003"]["source_searchable_instrument_level"], "ALL")

    def test_fully_populated_index(self):
        rows = build(corpus({"act-army-1950": set(AA_FULL), "rules-army-rules-1954": set(AR_FULL)}))
        self.assertEqual(rows["KB-003"]["source_searchable"], "ALL")
        self.assertRegex(rows["KB-003"]["items"], r"code:SRC-AA=>act-army-1950\[id\]#s79,s80,s81,s82")
        self.assertRegex(rows["KB-003"]["items"], r"code:SRC-AR=>rules-army-rules-1954\[id\]#r22")

    def test_unavailable_corpus_is_not_checked(self):
        rows = build(None)
        self.assertEqual(rows["KB-003"]["source_searchable"], "NOT_CHECKED")
        self.assertEqual(rows["KB-003"]["anchored_full"], "NO")

    def test_plain_text_parity(self):
        """ADM-JD-02 (plain text: 'AA §19, AR r14 and §122') follows the same rules as coded KB-003."""
        full = build(corpus({"act-army-1950": set(AA_FULL), "rules-army-rules-1954": set(AR_FULL)}))
        self.assertEqual(full["ADM-JD-02"]["source_searchable"], "ALL")
        empty = build(corpus({"act-army-1950": set(), "rules-army-rules-1954": set()}))
        self.assertEqual(empty["ADM-JD-02"]["source_searchable"], "NONE")
        partial = build(corpus({"act-army-1950": set(AA_FULL), "rules-army-rules-1954": set()}))
        self.assertEqual(partial["ADM-JD-02"]["source_searchable"], "PARTLY")


if __name__ == "__main__":
    unittest.main()
