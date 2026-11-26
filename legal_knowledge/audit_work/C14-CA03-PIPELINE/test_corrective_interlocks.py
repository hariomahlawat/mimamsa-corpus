"""Corrective regression candidates; use only disposable synthetic fixtures."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import pymupdf
from pipeline import extract, judgments, records
from pipeline.__main__ import main
from pipeline.common import Paths
from pipeline.shadow_assessment import assess
from pipeline.relevance_states import decide


class CorrectiveInterlocks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.paths = Paths.default(self.root)
        self.paths.meta.mkdir(parents=True)
        self.paths.text.mkdir()
        self.raw = self.paths.data / 'raw' / 'fixture.pdf'
        self.raw.parent.mkdir()
        self.raw.write_bytes(b'%PDF synthetic invalid fixture')
        self.meta = self.paths.meta / 'fixture.json'
        self.meta.write_text(json.dumps({'doc_id': 'fixture', 'doc_type': 'judgment'}))
        (self.paths.text / 'fixture.txt').write_text('preserved old text')
        (self.paths.data / 'excluded_judgments.jsonl').write_text('{"sha256":"fixture"}\n')

    def snapshot(self):
        return {p.relative_to(self.root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in self.root.rglob('*') if p.is_file()}

    def test_direct_writers_hold(self):
        before = self.snapshot()
        for fn in (judgments.run, records.build_indiacode, extract.run):
            with self.assertRaisesRegex(RuntimeError, 'C14 corpus mutation hold'):
                fn(self.paths)
        with self.assertRaisesRegex(RuntimeError, 'C14 corpus mutation hold'):
            extract.extract_document(self.paths, {'doc_id': 'fixture'})
        self.assertEqual(before, self.snapshot())

    def test_cli_mutating_stages_hold(self):
        before = self.snapshot()
        for stage in ('records', 'extract', 'split', 'correspondence', 'relevance', 'ocr', 'report', 'all'):
            with self.assertRaises(SystemExit) as cm:
                main([stage, '--root', str(self.root)])
            self.assertEqual(cm.exception.code, 2)
        self.assertEqual(before, self.snapshot())

    def assess_pages(self, texts):
        with pymupdf.open() as pdf:
            for txt in texts:
                p = pdf.new_page()
                p.insert_textbox(pymupdf.Rect(30, 30, 550, 800), txt, fontsize=8)
            raw = pdf.tobytes()
        self.raw.write_bytes(raw)
        meta = {'doc_id': 'fixture', 'title': 'Civil case', 'raw_path': 'data/raw/fixture.pdf',
                'sha256': hashlib.sha256(raw).hexdigest(), 'page_count': len(texts)}
        return assess(self.root, meta)

    def test_default_classifier_marker_free_threshold(self):
        text = ('the court heard the appeal and the parties gave their reasons. ' * 14).split()
        text = ' '.join(text[:149])
        r = self.assess_pages([text])
        with pymupdf.open(self.raw) as doc:
            actual = doc[0].get_text('text')
        self.assertEqual(r['classifier_text_sha256'], hashlib.sha256(actual.encode()).hexdigest())
        self.assertFalse(r['research_eligible'])
        self.assertNotEqual(r['relevance'], 'IRRELEVANT')

    def test_default_classifier_cross_page(self):
        civil = 'the court heard the appeal and the parties gave their reasons. ' * 18
        r = self.assess_pages([civil + ' Armed Forces', 'Tribunal ' + civil])
        with pymupdf.open(self.raw) as doc:
            actual = '\n'.join(p.get_text('text') for p in doc)
        self.assertEqual(r['classifier_text_sha256'], hashlib.sha256(actual.encode()).hexdigest())
        expected = decide(text=actual, quality={'verdict':'TEXT_OK','unusable_pages':[],'usable_share':1.0},
                          truncated=False, ocr_done=False, ocr_quality_ok=True, title='Civil case')
        self.assertEqual(r['classifier_candidate_state'], expected['state'])
        self.assertFalse(r['research_eligible'])

if __name__ == '__main__': unittest.main()
