"""C13 A1: committed records are internally consistent (fast; no PDFs, no network)."""
from __future__ import annotations

import unittest

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "legal_knowledge" / "audit_work" / "C13-A1-OCR"
sys.path.insert(0, str(OUT / "tools"))

import c13_a1_ocr as tool  # noqa: E402

FOUO = "4284820e5bc2fb7f52ae9fbe8a61650f1579e9b6389ba206a916a69fed016b14"
FOUO_ID = "regs-regulations-for-the-air-force-reprinted-edition-2000"


def rows(name):
    with open(OUT / name, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


class C13OcrRecordsTests(unittest.TestCase):
    def test_population_counts(self):
        pop = rows("RECOVERY_POPULATION.csv")
        c11 = [r for r in pop if r["group"] == "C11_EXCLUDED_FLAGGED"]
        assert len(c11) == 8077
        assert sum(r["held"] == "YES" for r in c11) == 71   # 18 + 7 (C12) + 46 (C13 A7), review A1-01
        ph_t1 = [r for r in c11 if r["c11_tier"] == "T1" and r["court"] == "High Court of Punjab and Haryana"]
        assert len(ph_t1) == 562 and sum(r["held"] == "YES" for r in ph_t1) == 28
        assert all(r["priority_tranche"] == "P0" for r in ph_t1)
        # every not-held row is a dry-run re-acquisition plan, never marked acquired
        assert {r["acquisition_status"] for r in c11 if r["held"] == "NO"} == {
            "REACQUIRE_FROM_SOURCE_URL_PENDING_OWNER_APPROVAL_FOR_DOWNLOAD_RUN"}
        assert not any("aftjabalpur.in" in r["host"] for r in pop)
        held = {r["held_as"] for r in c11 if r["held"] == "YES"}
        assert held == {"INGESTED_C12_DATA_RAW", "PRESERVED_NOT_INGESTED", "PRESERVED_C13_A7"}
        assert all(r["sha256"] in r["held_hf_path"] for r in c11 if r["held_as"] != "INGESTED_C12_DATA_RAW" and r["held"] == "YES")

    def test_population_matches_builder(self):
        built = tool.build_population()
        for name, text in built.items():
            assert (OUT / name).read_text(encoding="utf-8") == text, name

    def test_restricted_item_absent_everywhere(self):
        for p in OUT.rglob("*"):
            if p.is_file() and p.name != "restricted_material.snapshot.json":
                t = p.read_text(encoding="utf-8", errors="ignore")
                assert FOUO not in t and FOUO_ID not in t, p
        shas, ids = tool.restricted()
        assert FOUO in shas and FOUO_ID in ids

    def test_detector_validation_is_reproducible_and_v1_frozen(self):
        built = tool.build_detector_eval()
        for name, text in built.items():
            assert (OUT / name).read_text(encoding="utf-8") == text
        v1 = json.loads((OUT / "detector_v1" / "DETECTOR_VALIDATION_v1.json").read_text())
        assert v1["labels"]["UNUSABLE_NEEDS_OCR"] == 82

    def test_no_irrelevant_row_with_unread_or_low_quality_pages(self):
        # review A1-02/A1-03: every IRRELEVANT verdict rests on usable text on every page and adequate OCR quality
        for r in rows("RELEVANCE_RERUN.csv"):
            if r["state"] == "IRRELEVANT":
                assert float(r["usable_share_after"]) == 1.0 and not r["ocr_incomplete"]
                assert r["ocr_min_dict_ratio"] == "" or float(r["ocr_min_dict_ratio"]) >= 0.35

    def test_candidates_are_relevant_and_verified(self):
        dec = [r for r in rows("INGESTION_DECISIONS.csv") if r["action"] == "INGEST_AS_CANDIDATE"]
        assert len(dec) == 12 and all(r["state"] == "RELEVANT" for r in dec)
        ver = rows("HF_CANDIDATES_VERIFICATION.csv")
        assert all(v["result"] in ("MATCH", "ONLY_STAGED_PATHS_ADDED_NONE_REMOVED") for v in ver)

    def test_levenshtein_and_norm(self):
        assert tool.lev("kitten", "sitting") == 3
        assert tool.lev("a b c".split(), "a c".split()) == 1
        assert tool.norm("‘Unfit’  – x") == "'Unfit' - x"

    def test_old_rule_untouched_new_rule_documented(self):
        # the C13 module supersedes, but does not edit, the deleting stage
        src = (ROOT / "pipeline" / "judgments.py").read_text(encoding="utf-8")
        assert "path.unlink()" in src
        new = (ROOT / "pipeline" / "relevance_states.py").read_text(encoding="utf-8")
        assert "Supersedes the deletion rule" in new


if __name__ == "__main__":
    unittest.main()
