"""Native private receipt checks use an isolated local synthetic job only."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

RUNNER = Path(__file__).resolve().parents[1] / 'legal_knowledge/audit_work/C14-CA01-STATUTORY/runner'
sys.path.insert(0, str(RUNNER))
import hf_metadata_windows as windows


class ReceiptValidationTests(unittest.TestCase):
    def test_accepts_a_local_job_location(self):
        root, name = windows._location(r'E:\Mimamsa-Corpus-Runner\jobs', 'wp1-synthetic-01')
        self.assertEqual(root.drive, 'E:')
        self.assertEqual(name, 'wp1-synthetic-01')

    def test_requires_an_absolute_local_windows_job_root(self):
        for root in ('jobs', 'E:jobs', 'E:\\', r'\\server\share\jobs'):
            with self.subTest(root=root), self.assertRaises(ValueError):
                windows._location(root, 'wp1-synthetic-01')

    def test_requires_a_single_fresh_child_name(self):
        for name in ('', '.', 'job one', 'job/next', 'job\\next', 'NUL', 'ab:cd'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                windows._location(r'E:\Mimamsa-Corpus-Runner\jobs', name)

    @unittest.skipIf(os.name == 'nt', 'native implementation is available on Windows')
    def test_no_portable_permissions_fallback(self):
        with self.assertRaisesRegex(OSError, 'Windows'):
            with windows.private_receipt_job(r'E:\Mimamsa-Corpus-Runner\jobs', 'offline'):
                self.fail('unsupported platform must remain closed')


@unittest.skipUnless(os.name == 'nt', 'requires a native Windows NTFS test volume')
class NativeReceiptTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix='c14-metadata-win-')
        self.addCleanup(tmp.cleanup)
        # Windows CI may express TEMP using its 8.3 alias.
        self.base = Path(tmp.name).resolve()
        self.root = self.base / 'jobs'
        self.native = windows._Windows()
        self.native.create_private_directory(self.root)

    def test_creates_private_receipt_with_no_replacement(self):
        raw = b'{"fixture":"synthetic"}\n'
        job_dir = self.root / 'synthetic-01'
        target = job_dir / windows.RECEIPT_NAME
        with windows.private_receipt_job(self.root, job_dir.name) as job:
            self.assertEqual(list(job_dir.iterdir()), [])
            job.write_receipt(raw)
            with self.assertRaises(FileExistsError):
                job.write_receipt(b'different')
        self.assertEqual(target.read_bytes(), raw)
        self.assertEqual(list(job_dir.iterdir()), [target])
        with self.assertRaises(FileExistsError):
            with windows.private_receipt_job(self.root, job_dir.name):
                self.fail('an existing job must be refused')
        self.assertEqual(target.read_bytes(), raw)

    def test_refuses_a_root_without_its_own_protected_acl(self):
        direct = self.base / 'ordinary-folder'
        direct.mkdir()
        with self.assertRaises(PermissionError):
            with windows.private_receipt_job(direct, 'synthetic-02'):
                self.fail('an inheriting root must be refused')
        self.assertEqual(list(direct.iterdir()), [])

    def test_native_publish_leaves_existing_receipt_intact(self):
        job_dir = self.root / 'synthetic-rename'
        target = job_dir / windows.RECEIPT_NAME
        raw = b'{"fixture":"existing"}\n'
        with windows.private_receipt_job(self.root, job_dir.name) as job:
            target.write_bytes(raw)
            with self.assertRaises(FileExistsError):
                job.write_receipt(b'{"fixture":"new"}\n')
        self.assertEqual(target.read_bytes(), raw)
        self.assertEqual(list(job_dir.iterdir()), [target])

    def test_rejects_invalid_payload_and_closes_job_handle(self):
        with windows.private_receipt_job(self.root, 'synthetic-03') as job:
            with self.assertRaises(ValueError):
                job.write_receipt(b'')
        with self.assertRaisesRegex(RuntimeError, 'closed'):
            job.write_receipt(b'{"fixture":true}\n')
        self.assertEqual(list((self.root / 'synthetic-03').iterdir()), [])
