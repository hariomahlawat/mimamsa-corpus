import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import c16_conversion_evidence as evidence


class Tests(unittest.TestCase):
    def test_image_document_requires_render_and_manual_fidelity_review(self):
        self.assertEqual(evidence.assessment(3, 2, 1000),
                         "RENDERED_IMAGE_EVIDENCE_MANUAL_FIDELITY_REVIEW_REQUIRED")

    def test_missing_pdf_images_is_held_even_when_text_is_searchable(self):
        self.assertEqual(evidence.assessment(3, 0, 1000),
                         "HELD_IMAGE_EVIDENCE_NOT_RECOVERED")

    def test_native_only_searchable_representation(self):
        self.assertEqual(evidence.assessment(0, 0, 1000),
                         "SEARCHABLE_NATIVE_TEXT_REPRESENTATION")


if __name__ == "__main__":
    unittest.main()
