import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pymupdf

from repair import file_pair, physical_pages, sha


class RepairTest(unittest.TestCase):
    def test_page_order_scope_blank_and_offsets(self):
        with pymupdf.open() as source:
            source.new_page().insert_text((72, 72), "First physical page has sufficient native text.")
            source.new_page()
            source.new_page().insert_text((72, 72), "Third physical page has sufficient native text.")
            source.new_page().insert_text((72, 72), "Outside the receipt's documentary scope.")
            pages = list(physical_pages(source, {1, 2, 3}))
        self.assertEqual([p["physical_page"] for p in pages], [1, 2, 3, 4])
        self.assertEqual([p["method"] for p in pages], ["pdf-text", "blank-render", "pdf-text", "out-of-scope"])
        self.assertTrue(pages[0]["text"].startswith("First"))
        self.assertTrue(pages[2]["text"].startswith("Third"))
        self.assertEqual(pages[2]["text_sha256"], sha(pages[2]["text"].encode()))
        self.assertIsNone(pages[3]["text_sha256"])

    def test_local_pair_is_verified_with_both_hashes(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            digest = sha(b"pdf")
            (path / (digest + ".pdf")).write_bytes(b"pdf")
            (path / (digest + ".txt")).write_bytes(b"bad")
            self.assertIsNone(file_pair([path], digest, sha(b"text")))
            (path / (digest + ".txt")).write_bytes(b"text")
            self.assertEqual(file_pair([path], digest, sha(b"text"))[0:2], (b"pdf", b"text"))

    def test_corrupt_nonempty_embedded_text_uses_ocr(self):
        with pymupdf.open() as source:
            source.new_page().insert_textbox(pymupdf.Rect(70, 70, 500, 200), ("! @ # $ % & * " * 5 + "\n") * 4)
            with patch("repair.ocr", return_value=("Recovered legal text from the physical image.", 99.0)):
                result, = physical_pages(source, {1})
        self.assertEqual(result["method"], "tesseract-ocr")
        self.assertIn("native_encoding_review", result["quality_risks"])

    def test_image_only_page_invokes_ocr(self):
        with pymupdf.open() as scanned, pymupdf.open() as carrier:
            page = scanned.new_page()
            page.insert_text((72, 72), "OCR recovery on a physical page", fontsize=22)
            page = carrier.new_page()
            page.insert_image(page.rect, pixmap=scanned[0].get_pixmap(dpi=150))
            result, = physical_pages(carrier, {1})
        self.assertEqual(result["method"], "tesseract-ocr")
        self.assertIn("OCR recovery", result["text"])
        self.assertIn("ocr_transcription_review", result["quality_risks"])


if __name__ == "__main__":
    unittest.main()
