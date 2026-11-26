"""Signed WP1 scope and supervised worker controls on inert fixtures."""
import hashlib
import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

RUNNER = Path(__file__).resolve().parents[1] / 'legal_knowledge/audit_work/C14-CA01-STATUTORY/runner'
sys.path.insert(0, str(RUNNER))


class MetadataOperationTests(unittest.TestCase):
    @unittest.skipUnless(importlib.util.find_spec("cryptography"), "requires reviewed Ed25519 runtime")
    def test_approval_binds_revision_scope_code_and_expiry(self):
        from hf_metadata_approval import approval_payload, verify_approval
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

        key = Ed25519PrivateKey.generate()
        public = key.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
        pin = hashlib.sha256(key.public_key().public_bytes_raw()).hexdigest()
        now = datetime(2026, 11, 26, tzinfo=timezone.utc)
        expected = dict(revision='a'*40, code_commit='b'*40, runtime_sha256='c'*64,
                        plan_sha256='d'*64, register_blob='e'*40, guard_blob='f'*40,
                        jobs_root_sha256='7'*64, job_name='wp1-fixture')
        payload = approval_payload(**expected, now=now)
        raw = json.dumps(payload, sort_keys=True).encode()
        signature = key.sign(raw)
        verify_approval(raw, signature, public, pin, expected=expected, now=now)

        for field, value in [('revision', '2'*40), ('code_commit', '3'*40),
                             ('runtime_sha256', '4'*64), ('plan_sha256', '5'*64),
                             ('register_blob', '6'*40), ('roots', ['unapproved']),
                             ('credential_scope_attested', False)]:
            altered = json.dumps(dict(payload, **{field: value})).encode()
            with self.subTest(field=field), self.assertRaises(ValueError):
                verify_approval(altered, key.sign(altered), public, pin, expected=expected, now=now)

        with self.assertRaises(ValueError):
            verify_approval(raw, signature, public, '0'*64, expected=expected, now=now)
        with self.assertRaises(ValueError):
            verify_approval(raw, signature, public, pin, expected=expected, now=now + timedelta(days=1))

    def test_invalid_gate_never_prompts_for_credentials(self):
        from hf_metadata_job import main
        with patch('hf_metadata_job.approved_scope', side_effect=ValueError('synthetic private detail')), \
             patch('hf_metadata_job.read_token') as prompt, patch('builtins.print') as console:
            status = main(['--execute-metadata-only', '--revision', 'a'*40,
                           '--code-commit', 'b'*40, '--approval', 'synthetic.json',
                           '--signature', 'synthetic.sig', '--owner-key', 'synthetic.pem',
                           '--owner-key-sha256', 'c'*64, '--jobs-root', 'synthetic', '--job-name', 'fixture'])
        self.assertEqual(status, 2)
        prompt.assert_not_called()
        self.assertNotIn('synthetic private detail', str(console.call_args_list))

    def test_supervisor_bounds_stdout_and_redacts_worker_output(self):
        from hf_metadata_job import supervise
        with patch('hf_metadata_job.MAX_RECEIPT', 128):
            with self.assertRaisesRegex(ValueError, 'unexpected output'):
                supervise([sys.executable, '-c', 'print("fixture" * 10000)'], seconds=4)

    def test_credential_preflight_precedes_tree_requests(self):
        from hf_metadata_job import collect_receipt
        from hf_metadata_credential import CredentialScopeError
        requests = []

        def exchange(url, cap, remaining):
            requests.append(url)
            return b'{"auth":{"type":"access_token","accessToken":{"role":"write"}}}', None

        with self.assertRaises(CredentialScopeError):
            collect_receipt('a'*40, exchange, lambda **_: False, verify_credential=True)
        self.assertEqual(requests, ['https://huggingface.co/api/whoami-v2'])

    def test_approved_entry_writes_sanitized_incomplete_receipt(self):
        from contextlib import contextmanager
        from types import SimpleNamespace
        from hf_metadata_job import execute

        receipts = []
        states = []

        @contextmanager
        def private_job(root, name):
            states.append('private-open')
            yield SimpleNamespace(write_receipt=receipts.append)

        def prompt():
            self.assertEqual(states, ['private-open'])
            return 'hf_synthetic_fixture'

        def synthetic_supervisor(command, *, worker_input, env):
            self.assertIn(b'hf_synthetic_fixture', worker_input)
            self.assertNotIn('hf_synthetic_fixture', str(command))
            self.assertNotIn('hf_synthetic_fixture', str(env))
            raise TimeoutError('fixture error detail must stay private')

        scope = dict(revision='a'*40, code_commit='b'*40, runtime_sha256='c'*64, plan_sha256='d'*64)
        args = SimpleNamespace(jobs_root='local fixture', job_name='wp1-fixture')
        with patch('hf_metadata_windows.private_receipt_job', private_job), \
             patch('hf_metadata_job.bind_restriction', return_value=lambda **_: False), \
             patch('hf_metadata_job.read_token', prompt), \
             patch('hf_metadata_job.supervise', synthetic_supervisor), \
             patch('builtins.print') as console:
            self.assertEqual(execute(args, scope, b'synthetic approval', {}), 1)
        self.assertEqual(len(receipts), 1)
        result = json.loads(receipts[0])
        self.assertEqual(result['failure'], 'HARD_WORKER_DEADLINE')
        self.assertEqual(result['status'], 'METADATA_INCOMPLETE')
        self.assertIsNone(result['inventory'])
        self.assertFalse(result['acquisition_eligible'])
        self.assertNotIn('hf_synthetic_fixture', receipts[0].decode())
        self.assertNotIn('fixture error detail', str(console.call_args_list))

    @unittest.skipUnless(importlib.util.find_spec("cryptography"), "requires reviewed Ed25519 runtime")
    def test_worker_valid_approval_and_complete_synthetic_round_trip(self):
        import base64
        import io
        from types import SimpleNamespace
        from urllib.parse import unquote, urlsplit
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
        from hf_metadata_approval import approval_payload, canonical, sha256
        from hf_metadata_job import _worker
        from hf_inventory_metadata import REPO, STORES

        revision = 'a'*40
        expected = dict(revision=revision, code_commit='b'*40, runtime_sha256='c'*64,
                        plan_sha256='d'*64, register_blob='e'*40, guard_blob='f'*40,
                        jobs_root_sha256='7'*64, job_name='wp1-fixture')
        approval = canonical(approval_payload(**expected, now=datetime.now(timezone.utc)))
        key = Ed25519PrivateKey.generate()
        public = key.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
        inputs = {
            'signature': base64.b64encode(key.sign(approval)).decode(),
            'approval': base64.b64encode(approval).decode(),
            'owner_key': base64.b64encode(public).decode(),
            'owner_key_sha256': sha256(key.public_key().public_bytes_raw()),
            'code_commit': expected['code_commit'], 'revision': revision,
            'job_name': expected['job_name'], 'jobs_root': 'synthetic', 'token': 'hf_synthetic',
        }
        calls = []

        def exchange(url, cap, remaining):
            path = urlsplit(url).path
            calls.append(path)
            if path == '/api/whoami-v2':
                grants = {'entity': {'type': 'dataset', 'name': REPO, '_id': '1'*24},
                          'permissions': ['repo.content.read']}
                data = {'auth': {'type': 'access_token', 'accessToken': {
                    'role': 'fineGrained', 'fineGrained': {
                        'global': [], 'canReadGatedRepos': False, 'scoped': [grants],
                    },
                }}}
            elif '/revision/' in path:
                data = {'id': REPO, 'sha': revision, 'private': True}
            else:
                store = unquote(path.split('/tree/' + revision + '/', 1)[1])
                if store in STORES:
                    data = [{'path': store+'/synthetic.pdf', 'type': 'file', 'size': 10,
                             'lfs': {'oid': 'd'*64, 'size': 10}}]
                else:
                    data = [{'path': name, 'type': 'directory'}
                            for name in STORES if name.rsplit('/', 1)[0] == store]
            return canonical(data), None

        output = io.BytesIO()
        with patch('hf_metadata_job._scope', return_value=expected), \
             patch('hf_metadata_job.bind_restriction', return_value=lambda **_: False), \
             patch('hf_metadata_job.DirectMetadataHTTPS', return_value=exchange), \
             patch('sys.stdin', SimpleNamespace(buffer=io.BytesIO(canonical(inputs)))), \
             patch('sys.stdout', SimpleNamespace(buffer=output)):
            self.assertEqual(_worker(), 0)
        result = json.loads(output.getvalue())
        self.assertEqual(calls[0], '/api/whoami-v2')
        self.assertEqual(len(calls), result['metadata_requests'])
        self.assertTrue(result['coverage_of_supplied_scope'])
        self.assertFalse(result['acquisition_eligible'])
        self.assertNotIn(b'hf_synthetic', output.getvalue())

    def test_checkout_scope_binds_tracked_file_bytes(self):
        import shutil
        import subprocess
        import tempfile
        from hf_metadata_approval import RUNTIME_PATHS
        from hf_metadata_job import _scope, git_blob

        if not shutil.which('git'):
            self.skipTest('requires Git')
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary).resolve()
            root = fixture / 'checkout'
            jobs = fixture / 'jobs'
            root.mkdir()
            jobs.mkdir()
            raw = b'synthetic pinned runtime file\n'

            def git(*args):
                return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.DEVNULL)

            git('init', '-q')
            git('config', 'core.autocrlf', 'false')
            for name in RUNTIME_PATHS:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
            git('add', '.')
            git('-c', 'user.name=fixture', '-c', 'user.email=fixture@example.invalid',
                'commit', '-qm', 'synthetic runtime')
            head = git('rev-parse', 'HEAD').decode().strip()

            with patch('hf_metadata_job.REGISTER_BLOB', git_blob(raw)), \
                 patch('hf_metadata_job.GUARD_BLOB', git_blob(raw)):
                expected = _scope(root, 'a'*40, head, jobs, 'wp1-fixture', verify_git=True)
                observed = _scope(root, 'a'*40, head, jobs, 'wp1-fixture', verify_git=False)
                self.assertEqual(observed, expected)
                (root/RUNTIME_PATHS[-1]).write_bytes(raw+b'changed')
                with self.assertRaisesRegex(ValueError, 'reviewed commit'):
                    _scope(root, 'a'*40, head, jobs, 'wp1-fixture', verify_git=True)
