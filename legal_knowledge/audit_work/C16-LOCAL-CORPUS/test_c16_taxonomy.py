import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent));import c16_taxonomy as t
class Tests(unittest.TestCase):
 def test_paths_preserved(self):
  d="a"*64;rows=[{"inventory_id":"1","sha256":d,"relative_path":"Army Rules/AR 22 Case.docx","original_folder_classification":["Army Rules"],"filename_legal_metadata":{"instrument_abbreviation":"AR","provisions":["22"],"source_label":"AR 22 Case","ambiguity":None}},{"inventory_id":"2","sha256":d,"relative_path":"Discipline/AR 22 Case.docx","original_folder_classification":["Discipline"],"filename_legal_metadata":{"instrument_abbreviation":"AR","provisions":["22"],"source_label":"AR 22 Case","ambiguity":None}}];r=t.build(rows);self.assertEqual(len([x for x in r["relationships"] if x["basis"]=="FOLDER_PATH"]),2);self.assertEqual(len([x for x in r["relationships"] if x["category"]=="associated_with_provision"]),2)
 def test_range_unresolved(self):
  row={"inventory_id":"1","sha256":"b"*64,"relative_path":"Army Rules/AR 22-30/x.docx","original_folder_classification":["Army Rules","AR 22-30"],"filename_legal_metadata":{}};r=t.build([row]);self.assertTrue(any("RANGE" in x["reason"] for x in r["unresolved"]))
if __name__=="__main__":unittest.main()
