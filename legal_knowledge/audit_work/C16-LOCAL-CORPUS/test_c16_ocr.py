import sys,tempfile,unittest
from pathlib import Path
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
if __name__=="__main__":unittest.main()
