import hashlib
import unittest
import pymupdf
from pipeline.instrument_scope import validate_scope


class ScopeTests(unittest.TestCase):
    def setUp(self):
        with pymupdf.open() as d:
            p = d.new_page(width=600, height=800)
            p.set_cropbox(pymupdf.Rect(20, 30, 520, 730))
            p.set_rotation(90)
            d.new_page()
            self.raw = d.tobytes()
        self.sha = hashlib.sha256(self.raw).hexdigest()
        self.regions = [dict(physical_page=1, instrument_id='A', bbox=[0, 0, 100, 100], printed_page='1')]

    def check(self):
        return validate_scope(self.sha, self.raw, self.regions)

    def test_source_frame(self):
        a = self.check()
        self.assertEqual(a['page_frames'][0]['rotation'], 90)
        self.assertEqual(a['page_frames'][0]['viewport'], [0, 0, 700, 500])
        self.assertEqual(a['unassigned_full_pages'], [2])
        self.assertFalse(a['research_eligible'])
        self.assertFalse(a['regions'][0]['eligible_for_exact_anchor'])

    def test_wrong_source(self):
        self.sha = '0' * 64
        with self.assertRaises(ValueError): self.check()

    def test_old_geometry_api_denied(self):
        with self.assertRaises(ValueError): validate_scope(self.sha, [[700, 500]], self.regions)

    def test_normalized_numbers(self):
        a = self.check()
        self.regions[0]['bbox'] = [-0.0, 0.0, 100.0, 100.0]
        self.assertEqual(a['scope_id'], self.check()['scope_id'])

    def test_mutable_label_denied(self):
        self.regions[0]['printed_page'] = ['1']
        with self.assertRaises(ValueError): self.check()

    def test_adjacent_regions(self):
        self.regions.append(dict(physical_page=1, instrument_id='B', bbox=[100, 0, 200, 100]))
        a = self.check()
        self.regions.reverse()
        self.assertEqual(a['scope_id'], self.check()['scope_id'])

    def test_overlap(self):
        self.regions.append(dict(physical_page=1, instrument_id='B', bbox=[99, 0, 200, 100]))
        with self.assertRaises(ValueError): self.check()

    def test_rotated_bounds(self):
        self.regions[0]['bbox'] = [0, 0, 100, 501]
        with self.assertRaises(ValueError): self.check()

    def test_nan(self):
        self.regions[0]['bbox'] = [0, 0, float('nan'), 100]
        with self.assertRaises(ValueError): self.check()

if __name__ == '__main__': unittest.main()
