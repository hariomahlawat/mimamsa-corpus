import hashlib
import io
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import c16_reconcile as c16


class PrimitiveTests(unittest.TestCase):
    def _docx(self, path: Path, *, image_payloads: list[bytes]) -> None:
        document = ['<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
                    'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
                    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><w:body>',
                    '<w:p><w:r><w:t>Shared heading</w:t></w:r></w:p>']
        rels = []
        for index, _ in enumerate(image_payloads, 1):
            document.append(f'<w:p><w:r><w:drawing><a:blip r:embed="rId{index}"/></w:drawing></w:r></w:p>')
            rels.append(f'<Relationship Id="rId{index}" Target="media/image{index}.png" '
                        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"/>')
        document.append('</w:body></w:document>')
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("word/document.xml", "".join(document))
            archive.writestr("word/_rels/document.xml.rels",
                             '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                             + "".join(rels) + '</Relationships>')
            for index, payload in enumerate(image_payloads, 1):
                archive.writestr(f"word/media/image{index}.png", payload)

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
                                               canonical_exact=False, text_match=True), "IDENTITY_UNRESOLVED")
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

    def test_canonical_sibling_hashes_are_typed_and_lfs_oid_is_separate(self):
        sibling = type("S", (), {"rfilename": "preservation/originals/" + "a" * 64 + ".pdf",
                                  "lfs": {"sha256": "b" * 64}})()
        typed = c16.typed_hashes_from_repository_siblings([sibling])
        self.assertEqual(typed["original_source_sha256"], {"a" * 64})
        self.assertEqual(typed["lfs_object_sha256"], {"b" * 64})
        self.assertEqual(typed["derivative_sha256"], set())

    def test_docx_with_embedded_images_requires_image_ocr_not_fake_page_ocr(self):
        self.assertEqual(c16.ocr_required_pages(".docx", ["short"], embedded_image_count=2), [])
        self.assertEqual(c16.ocr_required_images(".docx", 2), [1, 2])
        self.assertEqual(c16.ocr_required_pages(".pdf", ["short", "x" * 100]), [1])

    def test_docx_image_inventory_resolves_relationships_and_preserves_order(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "screenshots.docx"
            self._docx(path, image_payloads=[b"first-image", b"second-image"])
            result = c16.extract_docx(path)
            self.assertEqual(result.native_text, "Shared heading")
            self.assertEqual([image.sequence for image in result.images], [1, 2])
            self.assertEqual([image.occurrence_id for image in result.images], ["body:rId1:1", "body:rId2:2"])
            self.assertEqual(result.images[0].sha256, hashlib.sha256(b"first-image").hexdigest())
            self.assertNotEqual(result.images[0].sha256, result.images[1].sha256)

    def test_docx_inspection_accounts_for_header_vml_unresolved_and_unreferenced_media(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "structures.docx"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("word/document.xml",
                    '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
                    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                    '<w:body><w:p><w:r><w:t>Body</w:t></w:r></w:p><w:headerReference r:id="rHeader"/></w:body></w:document>')
                archive.writestr("word/_rels/document.xml.rels",
                    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                    '<Relationship Id="rHeader" Target="header1.xml" Type="header"/></Relationships>')
                archive.writestr("word/header1.xml",
                    '<w:hdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
                    'xmlns:v="urn:schemas-microsoft-com:vml" '
                    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                    '<v:imagedata r:id="rImg"/><v:imagedata r:id="rMissing"/></w:hdr>')
                archive.writestr("word/_rels/header1.xml.rels",
                    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                    '<Relationship Id="rImg" Target="media/header.png" Type="image"/></Relationships>')
                archive.writestr("word/media/header.png", b"header-image")
                archive.writestr("word/media/orphan.png", b"orphan-image")
            result = c16.extract_docx(path)
            self.assertEqual([(i.part, i.relationship_id) for i in result.images], [("word/header1.xml", "rImg")])
            self.assertEqual(result.unresolved_image_references[0]["relationship_id"], "rMissing")
            self.assertEqual(result.unreferenced_media[0]["archive_path"], "word/media/orphan.png")

    def test_mixed_pdf_page_with_native_heading_and_image_body_requires_ocr(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "mixed.pdf"
            image = io.BytesIO()
            Image.new("RGB", (800, 900), "white").save(image, format="PNG")
            doc = c16.pymupdf.open()
            page = doc.new_page(width=800, height=1000)
            page.insert_text((30, 30), "JUDGMENT HEADING")
            page.insert_image(c16.pymupdf.Rect(0, 100, 800, 1000), stream=image.getvalue())
            doc.save(path); doc.close()
            inspection = c16.inspect_pdf(path)
            self.assertEqual(inspection[0]["classification"], "MIXED_NATIVE_AND_IMAGE")
            self.assertTrue(inspection[0]["ocr_required"])
            self.assertGreaterEqual(inspection[0]["image_coverage_ratio"], 0.8)

    def test_identical_native_headings_with_different_screenshots_are_not_text_duplicates(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            first, second = root / "a.docx", root / "b.docx"
            self._docx(first, image_payloads=[b"judgment-a"])
            self._docx(second, image_payloads=[b"judgment-b"])
            a, b = c16.extract_docx(first), c16.extract_docx(second)
            self.assertEqual(a.native_text, b.native_text)
            self.assertNotEqual(c16.document_content_hash(a.native_text, a.images),
                                c16.document_content_hash(b.native_text, b.images))

    def test_image_metadata_records_dimensions_format_and_perceptual_nomination_hash(self):
        stream = io.BytesIO()
        Image.new("RGB", (16, 9), "white").save(stream, format="PNG")
        metadata = c16.image_metadata(stream.getvalue())
        self.assertEqual((metadata["width"], metadata["height"], metadata["format"]), (16, 9, "PNG"))
        self.assertEqual(len(metadata["perceptual_dhash"]), 16)

    def test_filename_provision_list_creates_candidates_but_range_stays_unresolved(self):
        parsed = c16.parse_filename_legal_metadata("AR 22, 23, 30 - Lt Col PPS Bedi v UOI.docx")
        self.assertEqual(parsed["instrument_abbreviation"], "AR")
        self.assertEqual(parsed["provisions"], ["22", "23", "30"])
        self.assertEqual(parsed["case_name_candidate"], "Lt Col PPS Bedi v UOI")
        ranged = c16.parse_filename_legal_metadata("AR 22-30 - Chapter notes.docx")
        self.assertEqual(ranged["provisions"], [])
        self.assertEqual(ranged["ambiguity"], "PROVISION_RANGE_NOT_EXPANDED")

    def test_filename_parser_supports_collection_separator_variants_and_subsections(self):
        cases = {
            "AR 22-Maj S K Sharma v UOI.docx": ("AR", ["22"]),
            "AR 22, 23, 30 Lt Col PPS Bedi v UOI.docx": ("AR", ["22", "23", "30"]),
            "AR 30 Maj G S Sodhi v Union of India.docx": ("AR", ["30"]),
            "AA sec 191 Ranjit Singh vs U of I.docx": ("AA", ["191"]),
            "AA 19(1)(a) Example v UOI.docx": ("AA", ["19(1)(a)"]),
        }
        for filename, expected in cases.items():
            with self.subTest(filename=filename):
                parsed = c16.parse_filename_legal_metadata(filename)
                self.assertEqual((parsed["instrument_abbreviation"], parsed["provisions"]), expected)

    def test_docx_is_flow_document_without_physical_page_count(self):
        self.assertIsNone(c16.physical_page_count(".docx", ["native text"]))
        self.assertEqual(c16.physical_page_count(".pdf", ["p1", "p2"]), 2)

    def test_restriction_marking_does_not_quarantine_ordinary_legal_words(self):
        self.assertFalse(c16.has_restriction_marking("The confidential witness gave secret evidence."))
        self.assertTrue(c16.has_restriction_marking("FOR OFFICIAL USE ONLY\nArmy document"))
        self.assertTrue(c16.has_restriction_marking("RM-001"))

    def test_restriction_screening_scans_beyond_first_5000_characters(self):
        self.assertTrue(c16.has_restriction_marking("x" * 6000 + "\nFOR OFFICIAL USE ONLY"))

    def test_normalized_text_identity_is_candidate_not_verified_alternate(self):
        self.assertEqual(c16.choose_disposition(restricted=False, integrity_failure=False,
                                               canonical_exact=False, text_match=True),
                         "IDENTITY_UNRESOLVED")

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
