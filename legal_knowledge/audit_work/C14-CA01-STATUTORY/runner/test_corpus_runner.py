import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from corpus_runner import execute, digest, git_blob, PRESERVATION, LAST_RECORDED_HEAD

BODY = b'%PDF synthetic fixture only'
SHA = hashlib.sha256(BODY).hexdigest()
PATH = 'legal_knowledge/preservation/c13_a7_acquired/' + SHA[:2] + '/' + SHA + '/fixture.pdf'
ROW = {'a7_target_id': 'fixture', 'hf_path': PATH, 'sha256': SHA,
       'md5': hashlib.md5(BODY).hexdigest(), 'bytes': len(BODY),
       'prior_integrity_result': 'PIN_MISMATCH: md5,bytes', 'registration_state': 'HOLD_PIN_MISMATCH'}

class API:
    def __init__(self, *, private=True, drift=False, missing=False):
        self.private, self.drift, self.missing, self.calls = private, drift, missing, 0
    def dataset_info(self, *a, **kw):
        self.calls += 1
        return SimpleNamespace(private=self.private, sha=('a' * 40 if self.drift and self.calls > 1 else LAST_RECORDED_HEAD))
    def list_repo_files(self, *a, **kw):
        assert kw['revision'] == LAST_RECORDED_HEAD
        return [] if self.missing else [PATH]

def downloader(*, body=BODY, fail=False, outside=False):
    def download(**kw):
        assert kw['revision'] == PRESERVATION and kw['force_download'] is True
        if fail:
            raise OSError('secret-like error string must not be logged')
        p = kw['local_dir'] / kw['filename']
        if outside:
            p = kw['local_dir'] / 'wrong-file.pdf'
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(body)
        return str(p)
    return download

class RunnerTests(unittest.TestCase):
    def job(self, api, download):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'job'
            rc = execute([ROW], 'fixture', root, api, download)
            return rc, json.loads((root / 'verification.json').read_text())
    def test_success_preserves_prior_hold(self):
        rc, r = self.job(API(), downloader())
        self.assertEqual(rc, 0)
        self.assertEqual(r['observed_file_count'], 1)
        self.assertEqual(r['records'][0]['registration_state'], 'HOLD_PIN_MISMATCH')
        self.assertFalse(r['records'][0]['eligible_for_exact_anchor'])
        self.assertEqual(r['hf_writes'], 0)
    def test_byte_mismatch(self):
        rc, r = self.job(API(), downloader(body=b'wrong'))
        self.assertEqual(rc, 1)
        self.assertEqual(r['records'][0]['status'], 'BYTE_MISMATCH_HOLD')
    def test_missing_at_head(self):
        rc, r = self.job(API(missing=True), downloader())
        self.assertEqual(rc, 1)
        self.assertFalse(r['records'][0]['present_at_observed_head'])
    def test_head_drift(self):
        rc, r = self.job(API(drift=True), downloader())
        self.assertEqual(rc, 1)
        self.assertFalse(r['head_unchanged'])
    def test_public_denied(self):
        rc, r = self.job(API(private=False), downloader())
        self.assertEqual(rc, 1)
        self.assertEqual(r['records'], [])
    def test_error_sanitized(self):
        rc, r = self.job(API(), downloader(fail=True))
        self.assertEqual(rc, 1)
        self.assertNotIn('secret-like', json.dumps(r))
    def test_wrong_path(self):
        rc, r = self.job(API(), downloader(outside=True))
        self.assertEqual(rc, 1)
        self.assertEqual(r['records'][0]['status'], 'DOWNLOAD_OR_VERIFICATION_FAILED')
    def test_git_blob(self):
        self.assertEqual(git_blob(b'hello\n'), 'ce013625030ba8dba906f756967f9e9ca394464a')

if __name__ == '__main__':
    unittest.main()
