"""Offline regressions for the one-use isolated cloud execution boundary."""
from contextlib import redirect_stdout
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sys

AREA = Path(__file__).resolve().parents[1] / 'legal_knowledge/audit_work/C14-CA01-STATUTORY'
sys.path.insert(0, str(AREA / 'runner'))
import hf_metadata_cloud as cloud


@unittest.skipUnless(sys.platform == 'linux', 'isolated Linux host')
class CloudBoundaryTests(unittest.TestCase):
    def test_approval_is_consumed_once_before_work_begins(self):
        with tempfile.TemporaryDirectory() as root:
            jobs = Path(root).resolve()
            with self.assertRaises(RuntimeError):
                with cloud.claim(jobs, 'wp1-fixture'):
                    raise RuntimeError('synthetic work failure')
            with self.assertRaises(FileExistsError):
                with cloud.claim(jobs, 'wp1-fixture'):
                    self.fail('second use reached execution')

    def test_interrupted_write_never_publishes_final_name(self):
        native = os.fdopen

        class Interrupted:
            def __init__(self, fd, mode):
                self.file = native(fd, mode)

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                self.file.close()

            def write(self, data):
                self.file.write(data[:3])
                raise OSError('synthetic write interruption')

        with tempfile.TemporaryDirectory() as root:
            jobs = Path(root).resolve()
            with cloud.claim(jobs, 'wp1-fixture') as job:
                with patch.object(os, 'fdopen', side_effect=Interrupted), self.assertRaises(OSError):
                    cloud.publish(job, b'{"fixture":true}\n')
                self.assertEqual(list((jobs / 'wp1-fixture').iterdir()), [])

    def test_publish_keeps_existing_receipt(self):
        with tempfile.TemporaryDirectory() as root:
            jobs = Path(root).resolve()
            original = b'{"fixture":1}\n'
            with cloud.claim(jobs, 'wp1-fixture') as job:
                cloud.publish(job, original)
                with self.assertRaises(FileExistsError):
                    cloud.publish(job, b'{"fixture":2}\n')
            receipt = jobs / 'wp1-fixture' / 'metadata_inventory.json'
            self.assertEqual(receipt.read_bytes(), original)
            self.assertEqual(receipt.stat().st_mode & 0o777, 0o600)

    def test_action_context_is_refused_before_token_prompt(self):
        with patch.dict(os.environ, {'GITHUB_ACTIONS':'true'}), \
             patch('hf_metadata_cloud.read_token') as prompt, redirect_stdout(io.StringIO()):
            self.assertEqual(cloud.main(['--execute']), 2)
            prompt.assert_not_called()

    def test_actions_definition_has_no_live_service_or_environment(self):
        workflow = AREA.parents[2] / '.github/workflows/c14-cloud-wp1.yml'
        text = workflow.read_text()
        for item in ('secrets.', 'environment:', '--execute', 'id-token:', 'upload-artifact', 'runs-on: self-hosted'):
            self.assertNotIn(item, text)

    def test_only_signed_cloud_approval_enters_once(self):
        import importlib.util
        if importlib.util.find_spec('cryptography') is None:
            self.skipTest('requires reviewed Ed25519 runtime')
        from datetime import datetime, timezone
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

        owner = Ed25519PrivateKey.generate()
        public = owner.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
        expected = dict(revision=cloud.REVISION, code_commit='b'*40, runtime_sha256='c'*64,
                        plan_sha256='d'*64, register_blob='e'*40, guard_blob='f'*40,
                        jobs_root_sha256='7'*64, job_name='wp1-signed', deployment_sha256='8'*64)
        now = datetime.now(timezone.utc)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            jobs = root / 'jobs'
            jobs.mkdir(mode=0o700)
            approval = root / 'approval.json'
            signature = root / 'approval.sig'
            argv = ['--execute', '--code-commit', expected['code_commit'], '--job-name', expected['job_name'],
                    '--approval', str(approval), '--signature', str(signature)]

            def sign(scope):
                raw = cloud.canonical(cloud.approval_payload(**scope, now=now))
                approval.write_bytes(raw)
                signature.write_bytes(owner.sign(raw))

            with patch.object(cloud, 'host_settings', return_value=(jobs, public, expected['deployment_sha256'])),                  patch.object(cloud, 'scope', return_value=expected),                  patch.object(cloud, 'run', return_value=0) as run, redirect_stdout(io.StringIO()):
                windows = dict(expected)
                del windows['deployment_sha256']
                sign(windows)
                self.assertEqual(cloud.main(argv), 2)
                sign(dict(expected, deployment_sha256='1'*64))
                self.assertEqual(cloud.main(argv), 2)
                self.assertFalse(list(jobs.iterdir()))
                sign(expected)
                self.assertEqual(cloud.main(argv), 0)
                self.assertEqual(cloud.main(argv), 2)
                run.assert_called_once()
