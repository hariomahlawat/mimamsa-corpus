import hashlib,io,json,sys,tempfile,unittest
from pathlib import Path
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parent));import c16_ocr as o
class Tests(unittest.TestCase):
 def test_tsv(self):
  v="level\tleft\ttop\twidth\theight\tconf\ttext\n5\t1\t2\t3\t4\t90\tArmy\n";r=o.parse_tsv(v);self.assertEqual(r["raw_text"],"Army");self.assertEqual(r["mean_confidence"],90)
 def test_plain_rejected(self):
  with self.assertRaises(ValueError):o.parse_tsv("plain")
 def test_keys(self): self.assertNotEqual(o.processing_key("a"*64,"b"*64),o.processing_key("a"*64,"c"*64))
 def test_restricted_not_materialised(self):
  with tempfile.TemporaryDirectory() as td:
   r=o.persist_result(Path(td),"a"*64,{"raw_text":"FOR OFFICIAL USE ONLY","words":[]},True);self.assertIsNone(r["raw_text_path"]);self.assertEqual(list(Path(td).rglob("*.txt")),[])
 def test_empty_ocr_is_held_and_not_materialised(self):
  with tempfile.TemporaryDirectory() as td:
   r=o.persist_result(Path(td),"a"*64,{"raw_text":"","normalised_text":"","words":[]},False)
   self.assertEqual(r["access_disposition"],"HELD_UNREADABLE_OR_PROCESSING_ERROR")
   self.assertTrue(r["unreadable"])
   self.assertIsNone(r["raw_text_path"])
   self.assertEqual(list(Path(td).rglob("*.txt")),[])
 def test_state(self):
  with tempfile.TemporaryDirectory() as td:
   row={"image_sha256":"a"*64,"configuration_sha256":"c"*64,"state":"COMPLETE"};o.write_state_record(td,row);self.assertEqual(o.load_state_records(td),[row])
 def test_decorative(self):
  self.assertTrue(o.likely_decorative({"width":100,"height":80,"size_bytes":4000}));self.assertFalse(o.likely_decorative({"width":800,"height":1000,"size_bytes":4000}))
 def test_best_attempt(self):
  self.assertEqual(o.best_attempt([{"configuration":"a","word_count":2,"mean_confidence":90},{"configuration":"b","word_count":5,"mean_confidence":50}])["configuration"],"b")
 def test_second_pass_candidates_only_include_unreadable_primary_results(self):
  jobs={"a"*64:{"image_sha256":"a"*64},"b"*64:{"image_sha256":"b"*64}}
  primary=[{"image_sha256":"a"*64,"state":"COMPLETE","unreadable":True},
           {"image_sha256":"b"*64,"state":"COMPLETE","unreadable":False}]
  self.assertEqual([x["image_sha256"] for x in o.second_pass_candidates(jobs,primary)], ["a"*64])
 def test_pdf_page_jobs_preserve_mixed_content_page_numbers(self):
  rows=[{"inventory_id":"i1","sha256":"a"*64,"relative_path":"mixed.pdf","extension":".pdf",
         "ocr_required_pages":[3,1],"pdf_page_inspection":[
          {"physical_page":1,"classification":"MIXED_NATIVE_AND_IMAGE"},
          {"physical_page":3,"classification":"IMAGE_DOMINANT"}]}]
  jobs=o.pdf_page_jobs(rows,Path("S:/source"))
  self.assertEqual([x["physical_page"] for x in jobs],[1,3])
  self.assertEqual(jobs[0]["page_classification"],"MIXED_NATIVE_AND_IMAGE")
  self.assertEqual(jobs[0]["page_key"],o.processing_key("a"*64,"pdf-page-1"))
 def test_unreadable_image_propagates_hold_to_document_and_derivatives(self):
  inventory=[{"inventory_id":"d1","sha256":"a"*64,"relative_path":"x.docx","restricted":False,
              "embedded_images":[{"image_sha256":"b"*64}],"ocr_required_pages":[]}]
  image=[{"image_sha256":"b"*64,"state":"COMPLETE","unreadable":True,
          "access_disposition":"HELD_UNREADABLE_OR_PROCESSING_ERROR"}]
  row=o.propagate_access_holds(inventory,image,[])[0]
  self.assertEqual(row["document_access_disposition"],"HELD_UNREADABLE_OR_PROCESSING_ERROR")
  self.assertEqual(row["derivative_access_disposition"],"WITHHOLD_ALL_DERIVATIVES")
  self.assertEqual(row["hold_reasons"][0]["image_sha256"],"b"*64)
 def test_missing_pdf_page_result_remains_held(self):
  inventory=[{"inventory_id":"d1","sha256":"a"*64,"relative_path":"x.pdf","restricted":False,
              "embedded_images":[],"ocr_required_pages":[2]}]
  row=o.propagate_access_holds(inventory,[],[])[0]
  self.assertEqual(row["document_access_disposition"],"HELD_UNREADABLE_OR_PROCESSING_ERROR")
  self.assertEqual(row["hold_reasons"][0]["physical_page"],2)
 def test_pdf_snapshot_rejects_changed_source_bytes(self):
  with tempfile.TemporaryDirectory() as td:
   path=Path(td)/"x.pdf";path.write_bytes(b"first")
   job={"source_path":path,"source_sha256":hashlib.sha256(b"first").hexdigest(),"physical_page":1}
   path.write_bytes(b"changed")
   with self.assertRaisesRegex(ValueError,"source hash mismatch"):
    o.verified_pdf_snapshot(job)
 def test_pdf_render_is_from_verified_snapshot_and_records_render_hash(self):
  with tempfile.TemporaryDirectory() as td:
   path=Path(td)/"x.pdf";doc=o.core.pymupdf.open();doc.new_page().insert_text((30,30),"original");doc.save(path);doc.close()
   digest=hashlib.sha256(path.read_bytes()).hexdigest();job={"source_path":path,"source_sha256":digest,"physical_page":1}
   snapshot=o.verified_pdf_snapshot(job);path.write_bytes(b"mutated after snapshot")
   rendered=o.render_verified_pdf_page(snapshot,1,dpi=120)
   self.assertEqual(rendered["source_sha256"],digest)
   self.assertEqual(rendered["render_sha256"],hashlib.sha256(rendered["payload"]).hexdigest())
 def test_any_ocr_attempt_marking_holds_even_when_clean_attempt_wins(self):
  attempts=[{"raw_text":"FOR OFFICIAL USE ONLY","words":[{"text":"x"}],"word_count":1,"mean_confidence":10,"psm":6},
            {"raw_text":"ordinary clean text with more words","words":[{"text":"x"}]*6,"word_count":6,"mean_confidence":90,"psm":11}]
  selected,restricted=o.select_and_screen_attempts(attempts)
  self.assertEqual(selected["psm"],11)
  self.assertTrue(restricted)
  self.assertTrue(attempts[0]["access_marking_detected"])
 def test_state_error_then_complete_retry_updates_effective_head(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);base={"image_sha256":"a"*64,"configuration_sha256":"c"*64}
   o.write_state_record(root,{**base,"state":"ERROR"})
   o.write_state_record(root,{**base,"state":"COMPLETE","artifact_sha256":{}})
   heads=o.load_state_records(root)
   self.assertEqual(len(heads),1);self.assertEqual(heads[0]["state"],"COMPLETE")
   self.assertEqual(len(list((root/"attempts").rglob("*.json"))),2)
 def test_tampered_artifact_invalidates_cached_complete_record(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);artifact=root/"artifact.txt";artifact.write_text("valid",encoding="utf-8")
   record={"state":"COMPLETE","artifact_paths":{"raw_text":artifact.relative_to(root).as_posix()},
           "artifact_sha256":{"raw_text":hashlib.sha256(b"valid").hexdigest()}}
   self.assertTrue(o.validate_record_artifacts(root,record))
   artifact.write_text("tampered",encoding="utf-8")
   self.assertFalse(o.validate_record_artifacts(root,record))
 def test_access_rejects_clean_record_from_wrong_configuration(self):
  inventory=[{"inventory_id":"d1","sha256":"a"*64,"relative_path":"x.docx","restricted":False,
              "embedded_images":[{"image_sha256":"b"*64}],"ocr_required_pages":[]}]
  clean={"image_sha256":"b"*64,"state":"COMPLETE","unreadable":False,"evidence_verified":True,
         "configuration_sha256":"wrong","access_disposition":"SCREENED_NO_MARKING_DETECTED"}
  row=o.propagate_access_holds(inventory,[clean],[],expected_image_configurations={"current"})[0]
  self.assertEqual(row["document_access_disposition"],"HELD_UNREADABLE_OR_PROCESSING_ERROR")
 def test_positive_marking_survives_cross_configuration_clean_record(self):
  inventory=[{"inventory_id":"d1","sha256":"a"*64,"relative_path":"x.docx","restricted":False,
              "embedded_images":[{"image_sha256":"b"*64}],"ocr_required_pages":[]}]
  rows=[{"image_sha256":"b"*64,"state":"COMPLETE","unreadable":False,"evidence_verified":True,
         "configuration_sha256":"old","access_disposition":"HELD_ACCESS_MARKING_REVIEW"},
        {"image_sha256":"b"*64,"state":"COMPLETE","unreadable":False,"evidence_verified":True,
         "configuration_sha256":"current","access_disposition":"SCREENED_NO_MARKING_DETECTED"}]
  row=o.propagate_access_holds(inventory,rows,[],expected_image_configurations={"current"})[0]
  self.assertEqual(row["document_access_disposition"],"HELD_ACCESS_MARKING_REVIEW")
 def test_pdf_cache_key_changes_with_render_or_configuration(self):
  base=o.pdf_processing_key("a"*64,1,"b"*64,"c"*64)
  self.assertNotEqual(base,o.pdf_processing_key("a"*64,1,"d"*64,"c"*64))
  self.assertNotEqual(base,o.pdf_processing_key("a"*64,1,"b"*64,"e"*64))
 def test_stale_inventory_record_is_excluded_from_current_population(self):
  cached={"current":{"state":"COMPLETE"},"stale":{"state":"COMPLETE"}}
  self.assertEqual(o.intersect_current_jobs(cached,{"current"}),{"current":{"state":"COMPLETE"}})
 def test_partial_limit_never_reports_complete(self):
  summary,code=o.batch_completion(10,[{"state":"COMPLETE"} for _ in range(3)])
  self.assertEqual(summary["pending"],7);self.assertEqual(code,2)
 def test_interruption_before_state_does_not_create_reusable_head(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);artifact=root/"artifacts"/"orphan.txt";o.atomic_write(artifact,b"orphan")
   self.assertEqual(o.load_state_records(root),[])
if __name__=="__main__":unittest.main()
