"""Combined workflow tests: synthetic PDFs, separate local SQLite, no network."""
import hashlib
import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
import pymupdf

from pipeline.assessment_register import Journal
from pipeline.candidate_workflow import run_candidates


def sha(b):
    return hashlib.sha256(b).hexdigest()


class CandidateWorkflowTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base=Path(tmp.name)
        self.root=self.base/'inputs'
        path=self.root/'data/raw/case.pdf'
        path.parent.mkdir(parents=True)
        with pymupdf.open() as pdf:
            page=pdf.new_page()
            page.insert_textbox(pymupdf.Rect(30,30,550,800),
                'The Armed Forces Tribunal considered the appeal. The court heard the parties. '*20,
                fontsize=8)
            pdf.save(path)
        self.raw=path.read_bytes()
        self.db_path=self.base/'candidate.sqlite'
        self.db=sqlite3.connect(self.db_path)
        self.addCleanup(self.db.close)
        self.journal=Journal(self.db)
        self.row={'metadata':{'doc_id':'case-a','sha256':sha(self.raw),
                  'raw_path':'data/raw/case.pdf','page_count':1,'title':'Synthetic appeal'},
                  'declared_bytes':len(self.raw),'previous_event_id':None,
                  'recovery_state':'HISTORICALLY_EXCLUDED_CANDIDATE'}

    def run_rows(self,rows,restricted=lambda **kw:False):
        body=json.dumps({'schema':'c14-candidate-batch-v1',
                         'purpose':'ISOLATED_CANDIDATE_REVIEW','documents':rows}).encode()
        return run_candidates(self.root,body,expected_sha256=sha(body),
                              journal=self.journal,restricted=restricted)

    def test_persistence_aliases_and_idempotence(self):
        other=json.loads(json.dumps(self.row))
        other['metadata']['doc_id']='case-b'
        first=self.run_rows([self.row,other])
        self.assertEqual(first,self.run_rows([self.row,other]))
        self.assertEqual(first['journal']['events'],2)
        self.assertFalse(first['release_allowed'])
        self.assertFalse(first['research_eligible'])
        self.assertEqual((self.root/'data/raw/case.pdf').read_bytes(),self.raw)
        with closing(sqlite3.connect(self.db_path)) as second:
            self.assertEqual(Journal(second).audit()['documents'],2)

    def test_explicit_revision(self):
        first=self.run_rows([self.row])
        other=json.loads(json.dumps(self.row))
        other['metadata']['title']='Revised synthetic title'
        other['previous_event_id']=first['documents'][0]['event_id']
        self.assertEqual(self.run_rows([other])['journal']['events'],2)

    def test_restricted_never_opened(self):
        (self.root/'data/raw/case.pdf').unlink() # synthetic fixture only
        result=self.run_rows([self.row],restricted=lambda **kw:True)
        self.assertEqual(result['restricted_omitted_count'],1)
        self.assertEqual(result['documents'],[])
        self.assertEqual(result['journal']['events'],0)

    def test_scope_size_mismatch(self):
        self.row['declared_bytes']+=1
        with self.assertRaises(ValueError):self.run_rows([self.row])
        self.assertEqual(self.journal.audit()['events'],0)

    def test_late_stale_predecessor_leaves_batch_unwritten(self):
        other = json.loads(json.dumps(self.row))
        other['metadata']['doc_id'] = 'case-b'
        other['previous_event_id'] = 'f' * 64
        with self.assertRaisesRegex(ValueError, 'explicit current predecessor'):
            self.run_rows([self.row, other])
        self.assertEqual(self.journal.audit()['events'], 0)

    def test_receipt_identity_survives_unrelated_journal_growth(self):
        first = self.run_rows([self.row])
        other = json.loads(json.dumps(self.row))
        other['metadata']['doc_id'] = 'case-b'
        self.run_rows([other])
        again = self.run_rows([self.row])
        self.assertEqual(again['journal']['events'], 2)
        self.assertEqual(again['documents'], first['documents'])
        self.assertEqual(again['receipt_sha256'], first['receipt_sha256'])

    def test_observed_page_count_must_match_bounded_manifest(self):
        self.row['metadata']['page_count'] = 2
        with self.assertRaisesRegex(ValueError, 'page count'):
            self.run_rows([self.row])
        self.assertEqual(self.journal.audit()['events'], 0)

    def test_source_bytes_must_match_manifest_digest(self):
        self.row['metadata']['sha256'] = 'f' * 64
        with self.assertRaisesRegex(ValueError, 'raw size or hash mismatch'):
            self.run_rows([self.row])
        self.assertEqual(self.journal.audit()['events'], 0)

    def test_invalid_manifest_digest(self):
        with self.assertRaises(ValueError):
            run_candidates(self.root,b'{}',expected_sha256='0'*64,journal=self.journal,
                           restricted=lambda **kw:False)

    def test_duplicate_document_denied_before_processing(self):
        with self.assertRaises(ValueError):self.run_rows([self.row,self.row])
        self.assertEqual(self.journal.audit()['events'],0)

if __name__=='__main__':unittest.main()
