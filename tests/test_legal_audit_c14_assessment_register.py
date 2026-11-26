"""C14 candidate journal regressions: isolated SQLite, no network or corpus."""
import hashlib
import json
import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from pipeline.assessment_register import Journal


def fixture(doc='fixture-a', source='a', metadata='b', relevance='MANUAL_REVIEW_REQUIRED', **changes):
    a = dict(version='c14-shadow-v2', doc_id=doc, source_sha256=source*64,
             metadata_sha256=metadata*64, relevance=relevance, research_eligible=False,
             eligible_for_documentary_review=False, complete_native_evidence=False,
             pages=[dict(physical_page=1, text_sha256='c'*64, usable_for_negative_evidence=False)])
    a.update(changes)
    a['assessment_id'] = hashlib.sha256(json.dumps(a, sort_keys=True, ensure_ascii=False,
                                                 allow_nan=False).encode()).hexdigest()
    return a


class JournalTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.addCleanup(self.db.close)
        self.journal = Journal(self.db)

    def test_idempotent_rerun(self):
        a = fixture()
        first = self.journal.append(a)
        self.assertEqual(first, self.journal.append(a))
        self.assertEqual(self.journal.audit()['events'], 1)

    def test_explicit_supersession_and_retention(self):
        first = self.journal.append(fixture())
        second = self.journal.append(fixture(metadata='d'), previous_event_id=first)
        self.assertNotEqual(first, second)
        self.assertEqual(self.journal.audit()['events'], 2)
        self.assertEqual(self.journal.append(fixture(), previous_event_id=None), first)

    def test_missing_or_stale_predecessor(self):
        first = self.journal.append(fixture())
        with self.assertRaises(ValueError): self.journal.append(fixture(metadata='d'))
        self.journal.append(fixture(metadata='d'), previous_event_id=first)
        with self.assertRaises(ValueError): self.journal.append(fixture(metadata='e'), previous_event_id=first)
        self.assertEqual(self.journal.audit()['events'], 2)

    def test_cross_document_predecessor_denied(self):
        first = self.journal.append(fixture())
        with self.assertRaises(ValueError): self.journal.append(fixture(doc='fixture-b'), previous_event_id=first)
        self.assertEqual(self.journal.audit()['documents'], 1)

    def test_shared_source_different_aliases(self):
        first = self.journal.append(fixture())
        second = self.journal.append(fixture(doc='fixture-b'))
        self.assertNotEqual(first, second)
        self.assertEqual(self.journal.audit()['documents'], 2)

    def test_tampered_assessment(self):
        a = fixture()
        a['source_sha256'] = 'd'*64
        with self.assertRaises(ValueError): self.journal.append(a)

    def test_eligibility_denied_even_with_valid_identity(self):
        for flag in ('research_eligible', 'eligible_for_documentary_review', 'complete_native_evidence'):
            with self.subTest(flag=flag):
                with self.assertRaises(ValueError): self.journal.append(fixture(**{flag: True}))
        with self.assertRaises(ValueError): self.journal.append(fixture(relevance='IRRELEVANT'))

    def test_invalid_page_evidence(self):
        a = fixture(pages=[dict(physical_page=2, text_sha256='c'*64, usable_for_negative_evidence=False)])
        with self.assertRaises(ValueError): self.journal.append(a)

    def test_boolean_is_not_a_physical_page_number(self):
        a = fixture(pages=[dict(physical_page=True, text_sha256='c'*64,
                                usable_for_negative_evidence=False)])
        with self.assertRaisesRegex(ValueError, 'candidate page evidence'):
            self.journal.append(a)

    def test_constructor_does_not_commit_existing_transactions(self):
        self.db.execute('BEGIN')
        with self.assertRaisesRegex(ValueError, 'transaction'):
            Journal(self.db)
        self.assertTrue(self.db.in_transaction)
        self.db.rollback()

    @unittest.skipUnless(hasattr(sqlite3, 'LEGACY_TRANSACTION_CONTROL'), 'Python 3.12 SQLite API')
    def test_explicit_sqlite_autocommit_persists_batch_before_close(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'journal.sqlite'
            db = sqlite3.connect(path, autocommit=True)
            reader = sqlite3.connect(path)
            try:
                journal = Journal(db)
                journal.append(fixture())
                self.assertFalse(db.in_transaction)
                self.assertEqual(Journal(reader).audit()['events'], 1)
            finally:
                reader.close()
                db.close()

    @unittest.skipUnless(hasattr(sqlite3, 'LEGACY_TRANSACTION_CONTROL'), 'Python 3.12 SQLite API')
    def test_explicit_sqlite_autocommit_rolls_back_whole_batch(self):
        db = sqlite3.connect(':memory:', autocommit=True)
        self.addCleanup(db.close)
        journal = Journal(db)
        journal.append(fixture())
        with self.assertRaisesRegex(ValueError, 'current predecessor'):
            journal.append_batch([(fixture(doc='fixture-b'), None), (fixture(metadata='d'), None)])
        self.assertFalse(db.in_transaction)
        self.assertEqual(journal.audit()['events'], 1)

    def test_update_delete_replace_denied(self):
        eid = self.journal.append(fixture())
        row = self.db.execute('SELECT * FROM candidate_events').fetchone()
        for sql, params in (
            ('UPDATE candidate_events SET doc_id=? WHERE event_id=?', ('changed', eid)),
            ('DELETE FROM candidate_events WHERE event_id=?', (eid,)),
            ('INSERT OR REPLACE INTO candidate_events VALUES (?,?,?,?,?)', row),
        ):
            with self.subTest(sql=sql):
                with self.assertRaises(sqlite3.IntegrityError): self.db.execute(sql, params)
                self.db.rollback()
        self.assertEqual(self.journal.audit()['events'], 1)

    def test_unrelated_database_denied(self):
        other = sqlite3.connect(':memory:')
        self.addCleanup(other.close)
        other.execute('CREATE TABLE source_records (id TEXT)')
        with self.assertRaises(ValueError): Journal(other)
        self.assertEqual(other.execute('SELECT name FROM sqlite_master WHERE type="table"').fetchall(),
                         [('source_records',)])


if __name__ == '__main__':
    unittest.main()
