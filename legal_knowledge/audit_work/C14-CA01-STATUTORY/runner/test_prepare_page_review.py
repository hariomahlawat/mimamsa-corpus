"""Exercise the candidate renderer with disposable synthetic PDFs only."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

try:
    import pymupdf
except ImportError:
    pymupdf = None

import prepare_page_review as review


@unittest.skipUnless(pymupdf is not None, "requires PyMuPDF")
class CandidatePageRendererTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.job = Path(tmp.name)
        self.out = self.job / "page-review"

    def original(self, name, rotation=0):
        path = self.job / (name + ".pdf")
        with pymupdf.open() as doc:
            page = doc.new_page(width=72, height=144)
            page.insert_text((11, 30), "Synthetic")
            page.set_rotation(rotation)
            doc.save(path)
        raw = path.read_bytes()
        return {
            "a7_target_id": name, "sha256": hashlib.sha256(raw).hexdigest(),
            "md5": hashlib.md5(raw, usedforsecurity=False).hexdigest(), "bytes": len(raw),
            "registration_state": "HOLD_PIN_MISMATCH",
        }, path

    def receipt(self):
        return json.loads((self.out / "page_manifest.json").read_text(encoding="utf-8"))

    def test_owner_render_stays_held_before_opening_any_job(self):
        self.assertEqual(review.prepare(self.job / "unknown", execute=True), 2)
        self.assertFalse(self.out.exists())

    def test_rotated_page_receipt_binds_runtime_geometry_and_image(self):
        row, source = self.original("fixture", rotation=90)
        self.assertEqual(review.render_candidate_images([(row, source)], self.out), 0)
        receipt = self.receipt()
        record, = receipt["records"]
        page, = record["pages"]
        self.assertEqual(record["source_sha256"], row["sha256"])
        self.assertEqual(record["registration_state"], "HOLD_PIN_MISMATCH")
        self.assertEqual((page["physical_page"], page["printed_page"]), (1, None))
        self.assertEqual((page["rotation_degrees"], page["width_pixels"], page["height_pixels"]),
                         (90, 300, 150))
        self.assertEqual(page["image_sha256"],
                         hashlib.sha256((self.out / page["image"]).read_bytes()).hexdigest())
        self.assertEqual(record["renderer"]["binding_version"], pymupdf.VersionBind)
        self.assertGreater(len(record["renderer"]["binding_sha256"]), 0)
        self.assertFalse(receipt["eligible_for_exact_anchor"])

    def test_aggregate_pixel_budget_holds_partial_derivatives(self):
        first = self.original("first")
        second = self.original("second", rotation=90)
        before = [source.read_bytes() for _, source in (first, second)]
        self.assertEqual(review.render_candidate_images([first, second], self.out,
                         decoded_byte_limit=140_000), 1)
        receipt = self.receipt()
        self.assertEqual(receipt["status"], "REVIEW_REQUIRED")
        self.assertEqual([record["status"] for record in receipt["records"]],
                         ["RENDERED_NOT_REVIEWED", "REVIEW_REQUIRED"])
        self.assertEqual([source.read_bytes() for _, source in (first, second)], before)

    def test_timeout_marks_manifest_incomplete_and_preserves_original(self):
        row, source = self.original("fixture")
        before = source.read_bytes()
        self.assertEqual(review.render_candidate_images([(row, source)], self.out,
                         wall_seconds=0.001), 1)
        receipt = self.receipt()
        self.assertEqual(receipt["status"], "REVIEW_REQUIRED")
        self.assertEqual(receipt["records"][0]["error_type"], "TimeoutExpired")
        self.assertEqual(source.read_bytes(), before)
