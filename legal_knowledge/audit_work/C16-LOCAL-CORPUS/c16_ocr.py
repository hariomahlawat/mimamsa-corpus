"""Restartable exact-hash OCR for C16 DOCX images and rendered PDF pages."""
from __future__ import annotations
import argparse, csv, hashlib, io, json, os, subprocess, tempfile, zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from PIL import Image, ImageOps
import c16_reconcile as core

def load_jsonl(path):
    path=Path(path)
    return [] if not path.exists() else [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]

def write_jsonl_atomic(path, rows):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text("".join(json.dumps(r,ensure_ascii=False,sort_keys=True)+"\n" for r in rows),encoding="utf-8"); tmp.replace(path)

def write_state_record(root, record):
    digest=record["image_sha256"]; cfg=record.get("configuration_sha256","unversioned")
    dst=Path(root)/"state"/cfg[:12]/digest[:2]/f"{digest}.json"; dst.parent.mkdir(parents=True,exist_ok=True)
    if dst.exists(): return dst
    tmp=dst.with_name(dst.name+f".{os.getpid()}.tmp"); tmp.write_text(json.dumps(record,ensure_ascii=False,sort_keys=True),encoding="utf-8"); tmp.replace(dst); return dst

def load_state_records(root):
    state=Path(root)/"state"
    return [] if not state.exists() else [json.loads(p.read_text(encoding="utf-8")) for p in sorted(state.rglob("*.json"))]

def processing_key(digest,cfg): return hashlib.sha256(f"{digest}:{cfg}".encode("ascii")).hexdigest()

def parse_tsv(value):
    lines=value.splitlines(); header=lines[0].split("\t") if lines else []
    required={"left","top","width","height","conf","text"}
    if not required.issubset(header): raise ValueError("Tesseract output does not contain the required TSV header")
    words=[]; confidences=[]
    for row in csv.DictReader(io.StringIO(value),delimiter="\t"):
        text=(row.get("text") or "").strip()
        try: confidence=float(row.get("conf") or -1)
        except ValueError: confidence=-1
        if not text or confidence<0: continue
        words.append({"text":text,"confidence":round(confidence,4),"bbox":[int(row["left"]),int(row["top"]),int(row["width"]),int(row["height"])]}); confidences.append(confidence)
    raw=" ".join(w["text"] for w in words)
    return {"raw_text":raw,"normalised_text":core.normalize_text(raw),"mean_confidence":round(sum(confidences)/len(confidences),4) if confidences else None,"words":words}

def persist_result(output,digest,result,restricted=False,namespace=""):
    base=Path(output)/namespace if namespace else Path(output)
    record={"image_sha256":digest,"access_disposition":"HELD_ACCESS_MARKING_REVIEW" if restricted else "SCREENED_NO_MARKING_DETECTED","raw_text_path":None,"normalised_text_path":None,"word_boxes_path":None,"mean_confidence":result.get("mean_confidence"),"word_count":len(result.get("words",[])),"unreadable":not bool(result.get("raw_text","").strip())}
    if restricted:return record
    paths=[base/k/digest[:2]/f"{digest}.{ext}" for k,ext in (("raw","txt"),("normalised","txt"),("boxes","json"))]
    for p in paths:p.parent.mkdir(parents=True,exist_ok=True)
    paths[0].write_text(result.get("raw_text",""),encoding="utf-8"); paths[1].write_text(result.get("normalised_text",""),encoding="utf-8"); paths[2].write_text(json.dumps(result.get("words",[]),ensure_ascii=False,sort_keys=True),encoding="utf-8")
    record.update(raw_text_path=paths[0].relative_to(output).as_posix(),normalised_text_path=paths[1].relative_to(output).as_posix(),word_boxes_path=paths[2].relative_to(output).as_posix()); return record

def model_hashes(tessdata,languages): return {x:core.file_sha256(Path(tessdata)/f"{x}.traineddata") for x in languages}

def ocr_configuration(tesseract,tessdata,mode="primary"):
    version=subprocess.run([str(tesseract),"--version"],check=True,capture_output=True,text=True).stdout.splitlines()[0]
    cfg={"engine":"tesseract","engine_version":version,"languages":["eng","hin"],"language_model_sha256":model_hashes(tessdata,["eng","hin"]),"tsv_config_sha256":core.file_sha256(Path(tessdata)/"configs"/"tsv"),"mode":mode,"psm":[1] if mode=="primary" else [6,11],"preprocessing":["exif_transpose","grayscale","autocontrast"],"output":"tsv-word-boxes"}
    cfg["configuration_sha256"]=hashlib.sha256(json.dumps(cfg,sort_keys=True,separators=(",",":")).encode()).hexdigest(); return cfg

def _tesseract(image,tesseract,tessdata,psm):
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/"input.png"; image.save(p,"PNG")
        cmd=[str(tesseract),str(p),"stdout","--tessdata-dir",str(tessdata),"-l","eng+hin","--psm",str(psm),"tsv"]
        done=subprocess.run(cmd,check=True,capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=180)
    return parse_tsv(done.stdout)

def run_tesseract(payload,tesseract,tessdata,psm=1,second_pass=False):
    with Image.open(io.BytesIO(payload)) as src:
        img=ImageOps.autocontrast(ImageOps.exif_transpose(src).convert("L"))
        if second_pass:
            img=img.resize((max(1,img.width*2),max(1,img.height*2)),Image.Resampling.LANCZOS)
            img=img.point(lambda x:255 if x>180 else 0)
        result=_tesseract(img,tesseract,tessdata,psm); result.update(width=img.width,height=img.height); return result

def likely_decorative(meta): return int(meta.get("width") or 0)<200 and int(meta.get("height") or 0)<200 and int(meta.get("size_bytes") or 0)<20000
def best_attempt(attempts): return max(attempts,key=lambda x:(x.get("word_count",0),x.get("mean_confidence") or -1))

def image_jobs(inventory,source):
    jobs={};occ=[]
    for doc in inventory:
        for image in doc.get("embedded_images",[]):
            d=image["image_sha256"]; o={"inventory_id":doc["inventory_id"],"source_sha256":doc["sha256"],"relative_path":doc["relative_path"],"occurrence_id":image["occurrence_id"],"sequence":image["sequence"],"placement":image["placement"],"archive_path":image["archive_path"],"image_sha256":d};occ.append(o)
            jobs.setdefault(d,{"source_path":Path(source)/Path(doc["relative_path"]),"archive_path":image["archive_path"],"image_sha256":d,"width":image.get("width"),"height":image.get("height"),"size_bytes":image.get("size_bytes")})
    return jobs,occ

def read_job_payload(job):
    with zipfile.ZipFile(job["source_path"]) as z: payload=z.read(job["archive_path"])
    if hashlib.sha256(payload).hexdigest()!=job["image_sha256"]: raise ValueError("embedded image hash mismatch")
    return payload

def process_job(job,tesseract,tessdata,output,cfg):
    d=job["image_sha256"]
    try:
        result=run_tesseract(read_job_payload(job),tesseract,tessdata); restricted=core.has_restriction_marking(result["raw_text"]); record=persist_result(output,d,result,restricted)
        record.update(state="COMPLETE",processing_key=processing_key(d,cfg["configuration_sha256"]),configuration_sha256=cfg["configuration_sha256"],error=None);return record
    except Exception as exc:
        return {"image_sha256":d,"state":"ERROR","processing_key":processing_key(d,cfg["configuration_sha256"]),"configuration_sha256":cfg["configuration_sha256"],"access_disposition":"HELD_UNREADABLE_OR_PROCESSING_ERROR","raw_text_path":None,"normalised_text_path":None,"word_boxes_path":None,"mean_confidence":None,"word_count":0,"unreadable":True,"error":f"{type(exc).__name__}: {exc}"[:500]}

def run_primary(args):
    source,inventory,output=Path(args.source),Path(args.inventory),Path(args.output); tess,tdata=Path(args.tesseract),Path(args.tessdata); cfg=ocr_configuration(tess,tdata);output.mkdir(parents=True,exist_ok=True);(output/"OCR_CONFIGURATION.json").write_text(json.dumps(cfg,indent=2),encoding="utf-8")
    jobs,occ=image_jobs(load_jsonl(inventory),source); previous={r["image_sha256"]:r for r in load_jsonl(output/"OCR_PROCESSING_REGISTER.jsonl")+load_state_records(output) if r.get("configuration_sha256")==cfg["configuration_sha256"]}; [write_state_record(output,r) for r in previous.values()]
    completed={d:r for d,r in previous.items() if r.get("state")=="COMPLETE"};pending=[j for d,j in jobs.items() if d not in completed];pending=pending[:args.limit] if args.limit else pending
    with ThreadPoolExecutor(max_workers=max(1,args.workers)) as ex:
        fut={ex.submit(process_job,j,tess,tdata,output,cfg):j for j in pending}
        for f in as_completed(fut):r=f.result();completed[r["image_sha256"]]=r;write_state_record(output,r)
    reg=output/f"OCR_PROCESSING_REGISTER-{cfg['configuration_sha256'][:12]}.jsonl";write_jsonl_atomic(reg,[completed[k] for k in sorted(completed)])
    for o in occ:
        r=completed.get(o["image_sha256"],{});o.update(ocr_processing_key=r.get("processing_key"),ocr_state=r.get("state"),access_disposition=r.get("access_disposition"))
    write_jsonl_atomic(output/"OCR_IMAGE_OCCURRENCES.jsonl",occ);errors=sum(r.get("state")!="COMPLETE" for r in completed.values());summary={"distinct_image_jobs":len(jobs),"completed":len(completed)-errors,"errors":errors,"occurrences":len(occ),"reused_occurrences":len(occ)-len(jobs),"restricted":sum(r.get("access_disposition")=="HELD_ACCESS_MARKING_REVIEW" for r in completed.values()),"configuration_sha256":cfg["configuration_sha256"]};(output/"OCR_SUMMARY.json").write_text(json.dumps(summary,indent=2),encoding="utf-8");return 1 if errors else 0

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--source",required=True);p.add_argument("--inventory",required=True);p.add_argument("--output",required=True);p.add_argument("--tesseract",default=r"C:\Program Files\Tesseract-OCR\tesseract.exe");p.add_argument("--tessdata",required=True);p.add_argument("--workers",type=int,default=2);p.add_argument("--limit",type=int);return run_primary(p.parse_args(argv))
if __name__=="__main__":raise SystemExit(main())
