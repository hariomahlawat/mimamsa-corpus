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
 def test_state(self):
  with tempfile.TemporaryDirectory() as td:
   row={"image_sha256":"a"*64,"configuration_sha256":"c"*64,"state":"COMPLETE"};o.write_state_record(td,row);self.assertEqual(o.load_state_records(td),[row])
 def test_decorative(self):
  self.assertTrue(o.likely_decorative({"width":100,"height":80,"size_bytes":4000}));self.assertFalse(o.likely_decorative({"width":800,"height":1000,"size_bytes":4000}))
 def test_best_attempt(self):
  self.assertEqual(o.best_attempt([{"configuration":"a","word_count":2,"mean_confidence":90},{"configuration":"b","word_count":5,"mean_confidence":50}])["configuration"],"b")
if __name__=="__main__":unittest.main()
