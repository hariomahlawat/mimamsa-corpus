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

    def test_invalid_region_shape_has_controlled_error(self):
        for region in ({}, {**self.regions[0], 'bbox': None},
                       {**self.regions[0], 'bbox': [0, 0, 10**1000, 100]}):
            with self.subTest(region=type(region.get('bbox'))):
                with self.assertRaises(ValueError):
                    validate_scope(self.sha, self.raw, [region])

    def test_candidate_rectangle_matches_rotated_crop_render(self):
        with pymupdf.open() as pdf:
            page = pdf.new_page(width=600, height=800)
            page.draw_rect(pymupdf.Rect(60, 90, 130, 160), fill=(1, 0, 0), width=0)
            page.set_cropbox(pymupdf.Rect(20, 30, 520, 730))
            page.set_rotation(90)
            raw = pdf.tobytes()
        output = validate_scope(hashlib.sha256(raw).hexdigest(), raw, [
            {'physical_page': 1, 'instrument_id': 'A', 'bbox': [570, 40, 640, 110]},
        ])
        self.assertEqual(output['coordinate_system'], 'ROTATED_DISPLAY_POINTS_TOP_LEFT')
        x0, y0, x1, y1 = map(int, output['regions'][0]['bbox'])
        with pymupdf.open(stream=raw, filetype='pdf') as pdf:
            pixels = pdf[0].get_pixmap(dpi=72, colorspace=pymupdf.csRGB, alpha=False)
        self.assertEqual(pixels.pixel((x0 + x1) // 2, (y0 + y1) // 2), (255, 0, 0))
        self.assertEqual(pixels.pixel(x0 - 5, y0 - 5), (255, 255, 255))

if __name__ == '__main__': unittest.main()
