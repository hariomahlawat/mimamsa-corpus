"""C14 synthetic recovery planning controls. No corpus or network access."""
import hashlib
import json
import shutil
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from pipeline.common import Paths
from pipeline.records import plan_indiacode


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.paths = Paths.default(self.root)
        self.paths.db.parent.mkdir()
        self.paths.meta.mkdir(parents=True)
        self.paths.text.mkdir()
        (self.paths.meta / 'old.json').write_text('{"source":"sci"}')
        (self.paths.text / 'old.txt').write_text('old evidence')
        with closing(sqlite3.connect(self.paths.db)) as db, db:
            db.executescript("""
                CREATE TABLE urls (url TEXT PRIMARY KEY, source TEXT, doc_id_hint TEXT,
                  sha256 TEXT, fetched_at TEXT, meta TEXT, kind TEXT, status TEXT);
                CREATE TABLE files (sha256 TEXT PRIMARY KEY, raw_path TEXT, content_type TEXT);
                CREATE TABLE aliases (sha256 TEXT, url TEXT);
            """)
        self.history = []

    def add(self, suffix, raw, expected, *, present=True, aliases=1, relative=None, historical=True):
        sha = hashlib.sha256(expected).hexdigest()
        path = relative or 'data/raw/' + suffix + '.pdf'
        if present:
            p = self.root / path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(raw)
        meta = json.dumps({'dataset':'indian-supreme-court-judgments', 'year':2020,
                           'filename':suffix+'.pdf', 'index':{'title':'Synthetic case', 'path':suffix}})
        with closing(sqlite3.connect(self.paths.db)) as db, db:
            db.execute('INSERT INTO files VALUES (?,?,?)', (sha,path,'application/pdf'))
            for i in range(aliases):
                url = 'https://example.invalid/' + suffix + '/' + str(i)
                db.execute('INSERT INTO urls VALUES (?,?,?,?,?,?,?,?)',
                           (url,'sci',None,sha,'2026-01-01',meta,'document','fetched'))
                db.execute('INSERT INTO aliases VALUES (?,?)',(sha,url))
        if historical:
            self.history.append({'sha256':sha,'doc_id':'old-'+suffix})
        return sha

    def snapshot(self):
        return {p.relative_to(self.root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in self.root.rglob('*') if p.is_file()}

    def test_recovered_aliases_absent_and_mismatch_preserved(self):
        self.add('recovered', b'recovered', b'recovered', aliases=3)
        self.add('absent', b'', b'absent', present=False)
        self.add('mismatch', b'wrong', b'expected')
        self.add('new', b'new', b'new', historical=False)
        (self.paths.data/'excluded_judgments.jsonl').write_text(
            ''.join(json.dumps(e)+'\n' for e in self.history))
        before = self.snapshot()
        plan = plan_indiacode(self.paths)
        self.assertEqual(plan, plan_indiacode(self.paths))
        self.assertEqual(len(plan['documents']), 4)
        self.assertEqual(len(plan['recovered_path_candidates']), 3)
        self.assertEqual(len({x['doc_id'] for x in plan['recovered_path_candidates']}), 3)
        self.assertEqual(len(plan['historical_absent']), 1)
        self.assertEqual(len(plan['source_integrity_holds']), 1)
        self.assertEqual(plan['retained_stale_metadata_ids'], ['old'])
        self.assertFalse(plan['research_eligible'])
        self.assertEqual(before, self.snapshot())

    def test_unsafe_path_held(self):
        self.add('unsafe', b'', b'unsafe', present=False, relative='data/raw/../outside.pdf')
        (self.paths.data/'excluded_judgments.jsonl').write_text(
            ''.join(json.dumps(e)+'\n' for e in self.history))
        before = self.snapshot()
        plan = plan_indiacode(self.paths)
        self.assertEqual(len(plan['source_integrity_holds']), 1)
        self.assertFalse(plan['documents'])
        self.assertEqual(before, self.snapshot())

    def test_read_only_recovery_database_path_with_number_sign(self):
        paths = Paths.default(self.root / 'isolated candidate #1')
        paths.db.parent.mkdir(parents=True)
        shutil.copyfile(self.paths.db, paths.db)
        before = self.snapshot()

        plan = plan_indiacode(paths)

        self.assertEqual(plan['status'], 'PROPOSAL_NOT_ADOPTED')
        self.assertEqual(self.snapshot(), before)


if __name__ == '__main__':
    unittest.main()
