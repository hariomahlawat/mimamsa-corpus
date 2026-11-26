"""Regression checks against tracked documentary and source metadata."""
import csv
import json
from pathlib import Path
import re
import unittest


AUDIT = Path(__file__).resolve().parents[1] / "legal_knowledge" / "audit_work"
REVIEW = AUDIT / "C14-CA01-STATUTORY"


def load(name):
    return json.loads((REVIEW / (name + ".json")).read_text(encoding="utf-8"))


class DocumentaryCoverageTest(unittest.TestCase):
    def test_all_c5_constituents_trace_to_the_source_and_disposition(self):
        with (AUDIT / "C13-A4-STATUTORY/outputs/ACQUISITION_REQUESTS_A4.csv").open(
            encoding="utf-8", newline=""
        ) as stream:
            a4 = next(row for row in csv.DictReader(stream) if row["request_id"] == "A4-ACQ-013")
        first, last = map(int, re.search(r"C5C-(\d+)\.\.(\d+)", a4["target_instrument"]).groups())
        expected = {f"C5C-{number:03}" for number in range(first, last + 1)}
        with (AUDIT / "SOURCE-LIBRARY-C5/discovery/C_candidates.csv").open(
            encoding="utf-8", newline=""
        ) as stream:
            sources = {row["candidate_id"]: row for row in csv.DictReader(stream)}
        coverage = load("COMPOUND_REQUEST_COVERAGE")
        self.assertEqual(coverage["status"], "OPEN")
        items = coverage["constituents"]
        self.assertEqual(len(items), len(expected))
        self.assertEqual({row["candidate_id"] for row in items}, expected)
        reviews = {row["target_id"]: row for row in load("DOCUMENTARY_REVIEW_BATCH_02")["records"]}
        unresolved = set()
        for item in items:
            candidate = item["candidate_id"]
            self.assertIn("documentary_target_id", item)
            pins = re.search(r"\(file (\d+\.pdf), md5 ([0-9a-f]{32}), size (\d+)\)",
                             sources[candidate]["url_or_identifier"])
            self.assertEqual((item["filename"], item["archive_metadata_md5"],
                              str(item["archive_metadata_bytes"])), pins.groups())
            self.assertIs(item["enabled"], False)
            self.assertIs(item["eligible_for_exact_anchor"], False)
            if item["disposition"] == "UNRESOLVED_NOT_ACQUIRED":
                unresolved.add(candidate)
                self.assertIsNone(item["documentary_target_id"])
            else:
                row = reviews[item["documentary_target_id"]]
                self.assertEqual(row["filename"], item["filename"])
                self.assertEqual(row["source_url"], item["reviewed_source_url"])
                self.assertEqual(row["identity"]["subject_domain"], item["subject_domain"])
                self.assertEqual(row["registration_state"], item["registration_state"])
                if row["registration_state"] == "HOLD_PIN_MISMATCH":
                    self.assertNotEqual(row["source_md5"], item["archive_metadata_md5"])
                    self.assertNotEqual(row["bytes"], item["archive_metadata_bytes"])
        self.assertEqual(unresolved, {"C5C-006", "C5C-009", "C5C-010", "C5C-011", "C5C-012"})

    def test_documentary_rehash_is_dated_and_binds_preservation_digests(self):
        for suffix in ("01", "02"):
            batch = load("DOCUMENTARY_REVIEW_BATCH_" + suffix)
            self.assertIn("preserved_copy_rehash", batch)
            evidence = batch["preserved_copy_rehash"]
            self.assertEqual(evidence["compared_digests"], ["SHA-256", "MD5"])
            self.assertEqual(evidence["performer"], "ChatGPT corpus coordinator")
            self.assertEqual(evidence["evidence_date"], "2026-11-26")
            self.assertIs(evidence["independent_reviewer_rehash"], False)
            for row in batch["records"]:
                self.assertEqual(row["hf_revision"], evidence["preservation_revision"])
                self.assertIs(row["uploaded_preserved_copy_matches_inventory_digests"], True)
                self.assertIs(row["eligible_for_exact_anchor"], False)

    def test_partial_locator_is_visible_in_reconciliation(self):
        coverage = load("COMPOUND_REQUEST_COVERAGE")["compound_request_033"]
        request = next(row for row in load("ACQUISITION_RECONCILIATION")["requests"]
                       if row["request_id"] == "A4-ACQ-033")
        self.assertEqual(coverage.get("request_id"), request["request_id"])
        self.assertEqual(coverage["status"], "PARTIAL_LOCATOR_ONLY")
        self.assertEqual({item["status"] for item in coverage["components"]}, {
            "GOVERNMENT_REPRODUCTION_LEAD_NOT_ACQUIRED", "UNRESOLVED_NO_VERIFIED_LOCATOR",
        })
        self.assertEqual([item["url"] for item in coverage["components"] if "url" in item],
                         [item["url"] for item in request["new_locators"]])
