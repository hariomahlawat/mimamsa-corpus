"""Build owner-navigation taxonomy and candidate provision relationships."""
import argparse,hashlib,json,re,unicodedata
from pathlib import Path
INSTRUMENTS={"AA":("Army Act","AA-1950","section",[]),"AR":("Army Rules","AR-1954","rule",["Regulations for the Army"]),"AFA":("Air Force Act","AFA-1950","section",[]),"NA":("Navy Act","NA-1957","section",["Other NA expansion"]),"AFT":("Armed Forces Tribunal","AFT-TRIBUNAL",None,["Armed Forces Tribunal Act, 2007"])}
FP=re.compile(r"(?i)^\s*(AA|AR|AFA|NA)\s+(?:(?:sec(?:tion)?|rule|r|s)\.?\s*)?(\d+(?:\([A-Za-z0-9]+\))*)\s*$");FR=re.compile(r"(?i)\b(AA|AR|AFA|NA)\s+\d+\s*(?:-|\u2013|\u2014|to)\s*\d+")
def slug(v):return re.sub(r"[^a-z0-9]+","-",unicodedata.normalize("NFKC",v).casefold()).strip("-") or "unlabelled"
def sid(prefix,*parts):return prefix+"-"+hashlib.sha256(json.dumps([prefix,*parts],ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()[:24]
def prov(row,abbr,num,label,basis):
 n,c,k,a=INSTRUMENTS[abbr];target=f"PROV:{c}:{'r' if k=='rule' else 's'}.{num}"
 return {"relationship_id":sid("REL",row["inventory_id"],target,basis,label),"category":"associated_with_provision","inventory_id":row["inventory_id"],"source_copy_sha256":row["sha256"],"target_node_id":target,"basis":basis,"source_label":label,"relative_path":row["relative_path"],"verification":"CANDIDATE","is_finding":False,"abbreviation_expansion":{"abbreviation":abbr,"reading":n,"alternatives":a},"rule":"C16-PROVISION-NAVIGATION/2.0"}
def build(rows):
 nodes={};rels=[];unresolved=[];files=[]
 for row in rows:
  parent=None
  for depth,label in enumerate(row.get("original_folder_classification",[]),1):
   node="SUBJ:local:"+slug("/".join(row["original_folder_classification"][:depth]));nodes.setdefault(node,{"node_id":node,"kind":"subject","label":label,"parent_ids":[parent] if parent else [],"verification":"CURATED_NAVIGATION","original_label":label})
   rels.append({"relationship_id":sid("REL",row["inventory_id"],node,depth),"category":"classified_under_subject","inventory_id":row["inventory_id"],"source_copy_sha256":row["sha256"],"target_node_id":node,"basis":"FOLDER_PATH","source_label":label,"relative_path":row["relative_path"],"verification":"CURATED_NAVIGATION","is_finding":False,"rule":"C16-FOLDER-SUBJECT/2.0"})
   if FR.search(label):unresolved.append({"inventory_id":row["inventory_id"],"source_label":label,"reason":"PROVISION_RANGE_NOT_EXPANDED_FROM_FOLDER"})
   else:
    m=FP.match(label)
    if m:rels.append(prov(row,m.group(1).upper(),m.group(2),label,"FOLDER_PATH"))
   parent=node
  md=row.get("filename_legal_metadata",{});files.append({"inventory_id":row["inventory_id"],"relative_path":row["relative_path"],**md});abbr=md.get("instrument_abbreviation")
  if md.get("ambiguity"):unresolved.append({"inventory_id":row["inventory_id"],"source_label":md.get("source_label"),"reason":md["ambiguity"]})
  if abbr in INSTRUMENTS:
   n,c,k,a=INSTRUMENTS[abbr];inst="INST:"+c;nodes.setdefault(inst,{"node_id":inst,"kind":"statutory_instrument","label":n,"parent_ids":[],"verification":"CURATED_NAVIGATION","abbreviation":abbr,"alternative_readings":a})
   for num in md.get("provisions",[]):
    r=prov(row,abbr,num,md.get("source_label"),"FILENAME_PATTERN");rels.append(r);nodes.setdefault(r["target_node_id"],{"node_id":r["target_node_id"],"kind":k,"label":f"{k} {num}","parent_ids":[inst],"verification":"CANDIDATE","original_label":num})
 return {"nodes":sorted(nodes.values(),key=lambda x:x["node_id"]),"relationships":sorted(rels,key=lambda x:x["relationship_id"]),"unresolved":unresolved,"filename_metadata":files}
def load(p):return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]
def write(p,rows):Path(p).write_text("".join(json.dumps(x,ensure_ascii=False,sort_keys=True)+"\n" for x in rows),encoding="utf-8")
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument("--inventory",required=True);p.add_argument("--output",required=True);a=p.parse_args(argv);out=Path(a.output);out.mkdir(parents=True,exist_ok=True);r=build(load(a.inventory));(out/"LEGAL_TAXONOMY.json").write_text(json.dumps({"nodes":r["nodes"],"unresolved":r["unresolved"]},ensure_ascii=False,indent=2),encoding="utf-8");write(out/"PROVISION_JUDGMENT_CROSSWALK.jsonl",[x for x in r["relationships"] if x["category"]=="associated_with_provision"]);write(out/"SUBJECT_RELATIONSHIPS.jsonl",r["relationships"]);write(out/"FILENAME_LEGAL_METADATA.jsonl",r["filename_metadata"]);return 0
if __name__=="__main__":raise SystemExit(main())
