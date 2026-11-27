"""Run with the reviewed PDF runtime in a disposable checkout."""
import hashlib
import unittest
import pymupdf
from pipeline.page_ocr_evidence import receipt,DPI

HEADER='level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n'
def row(word='Court',confidence='95',x=10,n=1):
    return f'5\t1\t1\t1\t1\t{n}\t{x}\t10\t20\t20\t{confidence}\t{word}\n'
def sha(b):return hashlib.sha256(b).hexdigest()


class OcrReceiptTests(unittest.TestCase):
    def setUp(self):
        with pymupdf.open() as d:
            p=d.new_page()
            p.insert_text((30,50),'Court')
            d.new_page()
            self.raw=d.tobytes()
        with pymupdf.open(stream=self.raw,filetype='pdf') as d:
            png=d[0].get_pixmap(dpi=DPI,colorspace=pymupdf.csGRAY,alpha=False).tobytes('png')
        self.args=dict(raw=self.raw,source_sha256=sha(self.raw),physical_page=1,
                       tsv=(HEADER+row()).encode(),claimed_image_sha256=sha(png),
                       engine_version='synthetic fixture',languages='eng')

    def check(self,**changes):return receipt(**(self.args|changes))

    def test_stable_receipt_and_no_eligibility(self):
        a=self.check()
        self.assertEqual(a,self.check())
        self.assertEqual(a['word_count'],1)
        self.assertFalse(a['research_eligible'])
        self.assertFalse(a['eligible_for_exact_anchor'])
        self.assertFalse(a['usable_for_negative_evidence'])

    def test_wrong_page_render(self):
        with self.assertRaises(ValueError):self.check(physical_page=2)

    def test_wrong_raw_hash(self):
        with self.assertRaises(ValueError):self.check(source_sha256='0'*64)

    def test_low_confidence_not_hidden_by_mean(self):
        a=self.check(tsv=(HEADER+row()+row('appeal','20',n=2)).encode())
        self.assertEqual(a['minimum_word_confidence'],20)
        self.assertIn('LOW_WORD_CONFIDENCE',a['flags'])

    def test_native_mismatch(self):
        a=self.check(tsv=(HEADER+row('different')).encode())
        self.assertIn('NATIVE_OCR_TEXT_DIFFERENCE',a['flags'])
        with self.assertRaises(ValueError):self.check(native_text='not source text')

    def test_invalid_coordinates_and_confidence(self):
        for text in (row(x=-1),row(confidence='nan'),row(x=999999)):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):self.check(tsv=(HEADER+text).encode())

    def test_blank_or_unreadable(self):
        a=self.check(tsv=HEADER.encode())
        self.assertIn('BLANK_OR_UNREADABLE_UNADJUDICATED',a['flags'])

    def test_duplicate_word_identity(self):
        with self.assertRaises(ValueError):self.check(tsv=(HEADER+row()+row()).encode())


if __name__=='__main__':unittest.main()
