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


class StrengthenedChecks(unittest.TestCase):
    """Review R50-01/02/04: coverage of every protected prefix, non-LFS identity, 404 handling, call sites."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.f = Path(self.tmp.name) / "a.pdf"
        self.f.write_bytes(b"%PDF-1.4 original")

    def tearDown(self):
        self.tmp.cleanup()

    def test_every_protected_prefix_blocks_a_different_lfs_file(self):
        for pre in HP.PROTECTED_PREFIXES:
            rp = pre + "x/a.pdf"
            with self.subTest(prefix=pre):
                self.assertEqual(HP.check_additive([(self.f, rp)], {rp: ("0" * 64, None)}), [rp])

    def test_expected_prefixes_are_protected(self):
        for pre in ("data/raw/", "legal_knowledge/preservation/", "legal_knowledge/manual_sources/",
                    "legal_knowledge/judgment_originals/", "legal_knowledge/curated_originals/",
                    "legal_knowledge/judgment_sources/"):
            self.assertIn(pre, HP.PROTECTED_PREFIXES)

    def test_non_lfs_mismatch_is_blocked_and_known_oid_matches(self):
        rp = "data/raw/x/1/a.pdf"
        self.assertEqual(HP.check_additive([(self.f, rp)], {rp: (None, "1" * 40)}), [rp])
        empty = Path(self.tmp.name) / "empty"
        empty.write_bytes(b"")
        self.assertEqual(HP.git_blob_sha1(empty), "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391")  # git's empty blob

    def test_every_copy_manifest_path_is_protected(self):
        man = (ROOT / "legal_knowledge/audit_work/C12-CONSOLIDATION/copy_verification_c12/COPY_VERIFICATION_MANIFEST.csv")
        import csv as _csv
        paths = [r["hosted_path"] for r in _csv.DictReader(open(man, encoding="utf-8")) if r["hosted_path"]]
        self.assertGreater(len(paths), 4000)
        self.assertEqual([p for p in paths if not HP.is_protected(p)], [])

    def test_only_missing_folder_is_treated_as_empty(self):
        def api_raising(name):
            exc = type(name, (Exception,), {})("404 Client Error")
            class A:
                def list_repo_tree(self, *a, **kw):
                    raise exc
            return A()
        self.assertEqual(HP.remote_sha256_index(api_raising("EntryNotFoundError"), "o/r", "data/raw/x/"), {})
        for name in ("RepositoryNotFoundError", "RevisionNotFoundError", "HfHubHTTPError"):
            with self.subTest(name=name), self.assertRaises(Exception):
                HP.remote_sha256_index(api_raising(name), "o/r", "data/raw/x/")

    def test_each_upload_call_site_is_guarded_and_pinned(self):
        src = (ROOT / "scripts" / "push_hf.py").read_text(encoding="utf-8")
        body = src[src.index("def main("):]
        for m in re.finditer(r"api\.upload_folder\(", body):
            call = body[m.start():body.index(")\n", m.start())]
            before = body[max(0, m.start() - 600):m.start()]
            if "folder_path=str(folder)" in call or "legal_dir" in call:
                self.assertIn("parent_commit=base", call)
                self.assertIn("assert_additive(", before)
        lk = (ROOT / "scripts" / "push_legal_knowledge.py").read_text(encoding="utf-8")
        self.assertIn("parent_commit=base", lk)
        self.assertIn("revision=base", lk)


if __name__ == "__main__":
    unittest.main()
