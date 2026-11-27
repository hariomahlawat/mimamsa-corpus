import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import c16_reconcile as c16


class PrimitiveTests(unittest.TestCase):
    def test_inventory_id_is_stable_and_path_sensitive(self):
        self.assertEqual(c16.inventory_id("Army Act/a.pdf"), c16.inventory_id("Army Act/a.pdf"))
        self.assertNotEqual(c16.inventory_id("Army Act/a.pdf"), c16.inventory_id("CrPC/a.pdf"))

    def test_subjects_preserve_all_parent_folders(self):
        self.assertEqual(c16.subjects_for("Army Act/Appeals/a.pdf"), ["Army Act", "Appeals"])

    def test_normalized_text_hash_ignores_layout_noise_but_not_words(self):
        a = c16.normalized_text_hash("The  Army\nAct\t1950")
        b = c16.normalized_text_hash("the army act 1950")
        self.assertEqual(a, b)
        self.assertNotEqual(a, c16.normalized_text_hash("the air force act 1950"))

    def test_archive_member_rejects_traversal_and_absolute_paths(self):
        self.assertTrue(c16.safe_archive_member("folder/file.pdf"))
        self.assertFalse(c16.safe_archive_member("../secret.pdf"))
        self.assertFalse(c16.safe_archive_member("C:/secret.pdf"))

    def test_restriction_precedes_duplicate_and_new(self):
        self.assertEqual(c16.choose_disposition(restricted=True, integrity_failure=False,
                                               canonical_exact=True, text_match=False), "ACCESS_RESTRICTED")
        self.assertEqual(c16.choose_disposition(restricted=False, integrity_failure=False,
                                               canonical_exact=True, text_match=False), "EXACT_DUPLICATE")
        self.assertEqual(c16.choose_disposition(restricted=False, integrity_failure=False,
                                               canonical_exact=False, text_match=True), "VERIFIED_ALTERNATE_COPY")
        self.assertEqual(c16.choose_disposition(restricted=False, integrity_failure=False,
                                               canonical_exact=False, text_match=False), "NEW_DOCUMENT")

    def test_write_candidate_is_content_addressed_and_idempotent(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source.pdf"
            source.write_bytes(b"candidate")
            digest = hashlib.sha256(b"candidate").hexdigest()
            first = c16.copy_candidate(source, root / "package", digest)
            second = c16.copy_candidate(source, root / "package", digest)
            self.assertEqual(first, second)
            self.assertEqual(first.read_bytes(), b"candidate")

    def test_retry_call_recovers_from_transient_transport_failure(self):
        attempts = []
        def flaky():
            attempts.append(1)
            if len(attempts) < 3:
                raise ConnectionError("reset")
            return "ok"
        self.assertEqual(c16.retry_call(flaky, attempts=3, delay=0), "ok")
        self.assertEqual(len(attempts), 3)

    def test_hashes_from_repository_paths_collects_only_full_sha256(self):
        siblings = [type("S", (), {"rfilename": "preservation/" + "a" * 64 + "/original.pdf"})(),
                    type("S", (), {"rfilename": "short/deadbeef.pdf"})()]
        self.assertEqual(c16.hashes_from_repository_paths(siblings), {"a" * 64})

    def test_ocr_pages_are_only_assigned_to_page_image_formats(self):
        self.assertEqual(c16.ocr_required_pages(".docx", ["short"]), [])
        self.assertEqual(c16.ocr_required_pages(".pdf", ["short", "x" * 100]), [1])

    def test_restriction_marking_does_not_quarantine_ordinary_legal_words(self):
        self.assertFalse(c16.has_restriction_marking("The confidential witness gave secret evidence."))
        self.assertTrue(c16.has_restriction_marking("FOR OFFICIAL USE ONLY\nArmy document"))
        self.assertTrue(c16.has_restriction_marking("RM-001"))

    def test_text_identity_selects_one_deterministic_primary(self):
        rows = [{"relative_path": "B/copy.docx"}, {"relative_path": "A/original.docx"}]
        self.assertEqual(c16.text_primary(rows)["relative_path"], "A/original.docx")

    def test_prune_candidate_originals_removes_only_unmanifested_files(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            keep = root / "originals" / "aa" / "keep.pdf"
            stale = root / "originals" / "bb" / "stale.pdf"
            keep.parent.mkdir(parents=True); stale.parent.mkdir(parents=True)
            keep.write_bytes(b"keep"); stale.write_bytes(b"stale")
            c16.prune_candidate_originals(root, {"originals/aa/keep.pdf"})
            self.assertTrue(keep.exists())
            self.assertFalse(stale.exists())


if __name__ == "__main__":
    unittest.main()
