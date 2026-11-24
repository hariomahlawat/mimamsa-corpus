"""HF corpus sync must be additive: no remote deletion and no overwrite of protected originals (ADR-0004)."""
import hashlib
import importlib.util
import re
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("hf_protect", ROOT / "scripts" / "hf_protect.py")
HP = importlib.util.module_from_spec(spec)
spec.loader.exec_module(HP)
UPLOAD_SCRIPTS = [ROOT / "scripts" / "push_hf.py", ROOT / "scripts" / "push_legal_knowledge.py"]


class StaticNoDeletion(unittest.TestCase):
    def test_no_deletion_calls_in_upload_scripts(self):
        for p in UPLOAD_SCRIPTS:
            src = p.read_text(encoding="utf-8")
            code = "\n".join(l.split("#", 1)[0] for l in src.splitlines())
            for pat in (r"delete_patterns\s*=", r"CommitOperationDelete", r"\.delete_file\(", r"\.delete_folder\(",
                        r"\.delete_repo\(", r"update_repo_settings|update_repo_visibility"):
                self.assertIsNone(re.search(pat, code), f"{p.name}: forbidden pattern {pat}")

    def test_upload_scripts_call_the_guard(self):
        for p in UPLOAD_SCRIPTS:
            self.assertIn("assert_additive(", p.read_text(encoding="utf-8"), p.name)

    def test_preserved_tree_is_never_synced(self):
        self.assertTrue(HP.is_protected("legal_knowledge/preservation/c5_working_store/ab/x.pdf"))
        self.assertTrue(HP.is_protected("data/raw/sci/2009/abc.pdf"))
        self.assertFalse(HP.is_protected("legal_knowledge/audit_work/C12/x.csv"))
        self.assertIn("NEVER_SYNC_PATTERNS", (ROOT / "scripts" / "push_hf.py").read_text(encoding="utf-8"))


class AdditiveCheck(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.f = Path(self.tmp.name) / "a.pdf"
        self.f.write_bytes(b"%PDF-1.4 original")
        self.sha = hashlib.sha256(self.f.read_bytes()).hexdigest()

    def tearDown(self):
        self.tmp.cleanup()

    def test_identical_bytes_pass(self):
        remote = {"data/raw/sci/2009/a.pdf": (self.sha, None)}
        self.assertEqual(HP.check_additive([(self.f, "data/raw/sci/2009/a.pdf")], remote), [])

    def test_different_bytes_under_protected_prefix_fail(self):
        remote = {"legal_knowledge/preservation/c5/a.pdf": ("0" * 64, None)}
        self.assertEqual(HP.check_additive([(self.f, "legal_knowledge/preservation/c5/a.pdf")], remote),
                         ["legal_knowledge/preservation/c5/a.pdf"])

    def test_non_lfs_compared_by_git_oid_and_unknown_fails_closed(self):
        oid = HP.git_blob_sha1(self.f)
        self.assertEqual(HP.check_additive([(self.f, "data/raw/x/1/a.pdf")], {"data/raw/x/1/a.pdf": (None, oid)}), [])
        self.assertEqual(HP.check_additive([(self.f, "data/raw/x/1/a.pdf")], {"data/raw/x/1/a.pdf": (None, None)}),
                         ["data/raw/x/1/a.pdf"])

    def test_new_paths_and_unprotected_paths_pass(self):
        self.assertEqual(HP.check_additive([(self.f, "data/raw/x/1/new.pdf")], {}), [])
        self.assertEqual(HP.check_additive([(self.f, "legal_knowledge/audit_work/a.pdf")],
                                           {"legal_knowledge/audit_work/a.pdf": ("0" * 64, None)}), [])

    def test_assert_additive_raises_with_fake_api(self):
        class FakeApi:
            def list_repo_tree(self, repo_id, **kw):
                return [SimpleNamespace(path="data/raw/sci/2009/a.pdf", size=5,
                                        lfs=SimpleNamespace(sha256="f" * 64), blob_id="x")]
        with self.assertRaises(HP.ProtectedPathError):
            HP.assert_additive(FakeApi(), "o/r", [(self.f, "data/raw/sci/2009/a.pdf")])

    def test_listing_failure_fails_closed(self):
        class BrokenApi:
            def list_repo_tree(self, *a, **kw):
                raise RuntimeError("500 server error")
        with self.assertRaises(RuntimeError):
            HP.assert_additive(BrokenApi(), "o/r", [(self.f, "data/raw/sci/2009/a.pdf")])


if __name__ == "__main__":
    unittest.main()
