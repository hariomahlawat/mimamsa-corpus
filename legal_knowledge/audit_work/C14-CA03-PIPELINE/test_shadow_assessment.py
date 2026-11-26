import hashlib
import tempfile
import unittest
from pathlib import Path
import pymupdf
from pipeline.shadow_assessment import assess


def quality(text):
    return {'usable': len(text.strip()) > 80, 'flags': [] if len(text.strip()) > 80 else ['few_chars']}


def irrelevant(**kwargs):
    return {'state': 'IRRELEVANT', 'reasons': ['synthetic classifier']}


def relevant(**kwargs):
    return {'state': 'RELEVANT', 'reasons': ['synthetic classifier']}


class ShadowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.raw = self.root / 'data/raw/case.pdf'
        self.raw.parent.mkdir(parents=True)
        with pymupdf.open() as doc:
            p = doc.new_page()
            p.insert_text((40, 50), 'The court heard the appeal and the parties submitted their arguments. ' * 4, fontsize=6)
            doc.save(self.raw)
        self.original = self.raw.read_bytes()
        self.meta = {'doc_id': 'a', 'title': 'Civil fixture', 'raw_path': 'data/raw/case.pdf',
                     'sha256': hashlib.sha256(self.original).hexdigest(), 'page_count': 1}

    def run_assess(self, fn=irrelevant):
        return assess(self.root, self.meta, decide_fn=fn, quality_fn=quality)

    def test_valid_native_negative_and_immutability(self):
        r = self.run_assess()
        self.assertEqual(r['relevance'], 'MANUAL_REVIEW_REQUIRED')
        self.assertEqual(r['classifier_candidate_state'], 'IRRELEVANT')
        self.assertFalse(r['research_eligible'])
        self.assertEqual(self.raw.read_bytes(), self.original)
        self.assertEqual(r, self.run_assess())

    def test_positive_is_not_release(self):
        r = self.run_assess(relevant)
        self.assertFalse(r['eligible_for_documentary_review'])
        self.assertFalse(r['research_eligible'])

    def test_page_count_mismatch(self):
        self.meta['page_count'] = 2
        self.assertEqual(self.run_assess()['relevance'], 'INSUFFICIENT_TEXT')
        self.assertFalse(self.run_assess(relevant)['eligible_for_documentary_review'])

    def test_hash_mismatch(self):
        self.meta['sha256'] = '0' * 64
        self.assertEqual(self.run_assess()['relevance'], 'EXTRACTION_FAILED')

    def test_traversal(self):
        self.meta['raw_path'] = 'data/raw/../case.pdf'
        self.assertEqual(self.run_assess()['relevance'], 'EXTRACTION_FAILED')

    def test_blank_not_negative(self):
        with pymupdf.open() as d:
            d.new_page()
            body = d.tobytes()
        self.raw.write_bytes(body)
        self.meta['sha256'] = hashlib.sha256(body).hexdigest()
        r = self.run_assess()
        self.assertEqual(r['relevance'], 'INSUFFICIENT_TEXT')
        self.assertIn('blank_or_unreadable_not_validated', r['pages'][0]['flags'])

    def test_shared_raw_alias(self):
        a = self.run_assess()
        self.meta['doc_id'] = 'b'
        b = self.run_assess()
        self.assertNotEqual(a['assessment_id'], b['assessment_id'])
        self.assertEqual(a['source_sha256'], b['source_sha256'])
        self.assertEqual(self.raw.read_bytes(), self.original)

    def test_bad_metadata_controlled(self):
        r = assess(self.root, {}, decide_fn=irrelevant, quality_fn=quality)
        self.assertEqual(r['relevance'], 'EXTRACTION_FAILED')
        self.assertFalse(r['research_eligible'])
        self.assertTrue(r['assessment_id'])

    def test_marker_free_classifier_input(self):
        seen = []
        def capture(**kwargs):
            seen.append(kwargs['text'])
            return irrelevant(**kwargs)
        self.run_assess(capture)
        self.assertNotIn('[[page', seen[0])

    def test_vector_content_abstains(self):
        with pymupdf.open() as d:
            p = d.new_page()
            p.insert_text((40, 50), 'The court heard the appeal and the parties submitted their arguments. ' * 4, fontsize=6)
            p.draw_rect(pymupdf.Rect(20, 20, 100, 30))
            body = d.tobytes()
        self.raw.write_bytes(body)
        self.meta['sha256'] = hashlib.sha256(body).hexdigest()
        r = self.run_assess()
        self.assertIn('vector_content_not_validated', r['pages'][0]['flags'])
        self.assertEqual(r['relevance'], 'INSUFFICIENT_TEXT')

    def test_invisible_content_abstains(self):
        with pymupdf.open() as d:
            p = d.new_page()
            p.insert_text((40, 50), 'The court heard the appeal and the parties submitted their arguments. ' * 4, fontsize=6, render_mode=3)
            body = d.tobytes()
        self.raw.write_bytes(body)
        self.meta['sha256'] = hashlib.sha256(body).hexdigest()
        r = self.run_assess(relevant)
        self.assertIn('hidden_or_transparent_text', r['pages'][0]['flags'])
        self.assertFalse(r['complete_native_evidence'])
        self.assertFalse(r['eligible_for_documentary_review'])


if __name__ == '__main__':
    unittest.main()
