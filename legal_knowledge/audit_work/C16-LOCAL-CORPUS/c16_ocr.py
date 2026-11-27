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
    unreadable=not bool(result.get("raw_text","").strip())
    disposition=("HELD_ACCESS_MARKING_REVIEW" if restricted else
                 "HELD_UNREADABLE_OR_PROCESSING_ERROR" if unreadable else
                 "SCREENED_NO_MARKING_DETECTED")
    record={"image_sha256":digest,"access_disposition":disposition,"raw_text_path":None,"normalised_text_path":None,"word_boxes_path":None,"mean_confidence":result.get("mean_confidence"),"word_count":len(result.get("words",[])),"unreadable":unreadable}
    if restricted or unreadable:return record
    paths=[base/k/digest[:2]/f"{digest}.{ext}" for k,ext in (("raw","txt"),("normalised","txt"),("boxes","json"))]
    for p in paths:p.parent.mkdir(parents=True,exist_ok=True)
    paths[0].write_text(result.get("raw_text",""),encoding="utf-8"); paths[1].write_text(result.get("normalised_text",""),encoding="utf-8"); paths[2].write_text(json.dumps(result.get("words",[]),ensure_ascii=False,sort_keys=True),encoding="utf-8")
    record.update(raw_text_path=paths[0].relative_to(output).as_posix(),normalised_text_path=paths[1].relative_to(output).as_posix(),word_boxes_path=paths[2].relative_to(output).as_posix()); return record

def model_hashes(tessdata,languages): return {x:core.file_sha256(Path(tessdata)/f"{x}.traineddata") for x in languages}

def ocr_configuration(tesseract,tessdata,mode="primary"):
    version=subprocess.run([str(tesseract),"--version"],check=True,capture_output=True,text=True).stdout.splitlines()[0]
    psm={"primary":[1],"second-pass":[6,11],"pdf-pages":[1]}[mode]
    preprocessing=["exif_transpose","grayscale","autocontrast"]
    if mode=="second-pass": preprocessing += ["upscale_2x","threshold_180"]
    cfg={"engine":"tesseract","engine_version":version,"languages":["eng","hin"],"language_model_sha256":model_hashes(tessdata,["eng","hin"]),"tsv_config_sha256":core.file_sha256(Path(tessdata)/"configs"/"tsv"),"mode":mode,"psm":psm,"preprocessing":preprocessing,"output":"tsv-word-boxes"}
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

def second_pass_candidates(jobs,primary_rows):
    unresolved={r.get("image_sha256") for r in primary_rows
                if r.get("state")=="COMPLETE" and r.get("unreadable") is True}
    return [jobs[d] for d in sorted(unresolved) if d in jobs]

def pdf_page_jobs(inventory,source):
    jobs=[]
    for doc in inventory:
        if doc.get("extension")!=".pdf": continue
        inspection={x.get("physical_page"):x for x in doc.get("pdf_page_inspection",[])}
        for page in sorted(set(doc.get("ocr_required_pages",[]))):
            jobs.append({"inventory_id":doc["inventory_id"],"source_sha256":doc["sha256"],
                         "source_path":Path(source)/Path(doc["relative_path"]),
                         "relative_path":doc["relative_path"],"physical_page":page,
                         "page_classification":inspection.get(page,{}).get("classification","UNSPECIFIED"),
                         "page_key":processing_key(doc["sha256"],f"pdf-page-{page}")})
    return jobs

def render_pdf_page(job,dpi=300):
    document=core.pymupdf.open(job["source_path"])
    try:
        page=document.load_page(int(job["physical_page"])-1)
        pixmap=page.get_pixmap(dpi=dpi,alpha=False)
        return pixmap.tobytes("png")
    finally: document.close()

def process_second_pass_job(job,tesseract,tessdata,output,cfg):
    digest=job["image_sha256"]
    try:
        payload=read_job_payload(job);attempts=[]
        for psm in cfg["psm"]:
            result=run_tesseract(payload,tesseract,tessdata,psm=psm,second_pass=True)
            result.update(configuration=f"psm-{psm}",psm=psm,word_count=len(result.get("words",[])))
            attempts.append(result)
        result=best_attempt(attempts);restricted=core.has_restriction_marking(result["raw_text"])
        record=persist_result(output,digest,result,restricted,namespace=f"results/{cfg['configuration_sha256'][:12]}")
        record.update(state="COMPLETE",processing_key=processing_key(digest,cfg["configuration_sha256"]),
                      configuration_sha256=cfg["configuration_sha256"],selected_psm=result["psm"],
                      attempts=[{"psm":x["psm"],"word_count":x["word_count"],
                                 "mean_confidence":x.get("mean_confidence")} for x in attempts],
                      decorative_nomination=likely_decorative(job),error=None)
        return record
    except Exception as exc:
        return {"image_sha256":digest,"state":"ERROR","processing_key":processing_key(digest,cfg["configuration_sha256"]),
                "configuration_sha256":cfg["configuration_sha256"],"access_disposition":"HELD_UNREADABLE_OR_PROCESSING_ERROR",
                "unreadable":True,"error":f"{type(exc).__name__}: {exc}"[:500]}

def process_pdf_page_job(job,tesseract,tessdata,output,cfg):
    key=job["page_key"]
    try:
        result=run_tesseract(render_pdf_page(job),tesseract,tessdata,psm=1,second_pass=False)
        restricted=core.has_restriction_marking(result["raw_text"])
        record=persist_result(output,key,result,restricted,namespace=f"results/{cfg['configuration_sha256'][:12]}")
        record.update(state="COMPLETE",page_key=key,inventory_id=job["inventory_id"],
                      source_sha256=job["source_sha256"],relative_path=job["relative_path"],
                      physical_page=job["physical_page"],page_classification=job["page_classification"],
                      processing_key=processing_key(key,cfg["configuration_sha256"]),
                      configuration_sha256=cfg["configuration_sha256"],render_dpi=300,error=None)
        return record
    except Exception as exc:
        return {"image_sha256":key,"page_key":key,"inventory_id":job["inventory_id"],
                "source_sha256":job["source_sha256"],"relative_path":job["relative_path"],
                "physical_page":job["physical_page"],"page_classification":job["page_classification"],
                "state":"ERROR","processing_key":processing_key(key,cfg["configuration_sha256"]),
                "configuration_sha256":cfg["configuration_sha256"],
                "access_disposition":"HELD_UNREADABLE_OR_PROCESSING_ERROR","unreadable":True,
                "error":f"{type(exc).__name__}: {exc}"[:500]}

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

def run_restartable_batch(jobs,output,cfg,worker,workers,limit=None):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    (output/"OCR_CONFIGURATION.json").write_text(json.dumps(cfg,indent=2),encoding="utf-8")
    identifier="page_key" if cfg["mode"]=="pdf-pages" else "image_sha256"
    previous={r.get(identifier) or r.get("image_sha256"):r for r in load_state_records(output)
              if r.get("configuration_sha256")==cfg["configuration_sha256"]}
    completed={key:r for key,r in previous.items() if r.get("state")=="COMPLETE"}
    pending=[j for j in jobs if (j[identifier] if identifier in j else j["image_sha256"]) not in completed]
    if limit: pending=pending[:limit]
    with ThreadPoolExecutor(max_workers=max(1,workers)) as ex:
        futures={ex.submit(worker,j):j for j in pending}
        for future in as_completed(futures):
            record=future.result();key=record.get(identifier) or record["image_sha256"]
            completed[key]=record;write_state_record(output,record)
    register=output/f"OCR_PROCESSING_REGISTER-{cfg['configuration_sha256'][:12]}.jsonl"
    write_jsonl_atomic(register,[completed[k] for k in sorted(completed)])
    rows=list(completed.values());errors=sum(r.get("state")!="COMPLETE" for r in rows)
    summary={"mode":cfg["mode"],"jobs":len(jobs),"completed":len(rows)-errors,"errors":errors,
             "unreadable_held":sum(r.get("access_disposition")=="HELD_UNREADABLE_OR_PROCESSING_ERROR" for r in rows),
             "access_marking_holds":sum(r.get("access_disposition")=="HELD_ACCESS_MARKING_REVIEW" for r in rows),
             "screened_no_marking":sum(r.get("access_disposition")=="SCREENED_NO_MARKING_DETECTED" for r in rows),
             "configuration_sha256":cfg["configuration_sha256"]}
    (output/"OCR_SUMMARY.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    return 1 if errors else 0

def run_second_pass(args):
    source,inventory,output=Path(args.source),Path(args.inventory),Path(args.output)
    tess,tdata=Path(args.tesseract),Path(args.tessdata);cfg=ocr_configuration(tess,tdata,"second-pass")
    jobs,_=image_jobs(load_jsonl(inventory),source)
    selected=second_pass_candidates(jobs,load_jsonl(args.primary_register))
    worker=lambda job:process_second_pass_job(job,tess,tdata,output,cfg)
    return run_restartable_batch(selected,output,cfg,worker,args.workers,args.limit)

def run_pdf_pages(args):
    output=Path(args.output);tess,tdata=Path(args.tesseract),Path(args.tessdata)
    cfg=ocr_configuration(tess,tdata,"pdf-pages")
    jobs=pdf_page_jobs(load_jsonl(args.inventory),Path(args.source))
    worker=lambda job:process_pdf_page_job(job,tess,tdata,output,cfg)
    return run_restartable_batch(jobs,output,cfg,worker,args.workers,args.limit)

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--mode",choices=("primary","second-pass","pdf-pages"),default="primary");p.add_argument("--source",required=True);p.add_argument("--inventory",required=True);p.add_argument("--output",required=True);p.add_argument("--tesseract",default=r"C:\Program Files\Tesseract-OCR\tesseract.exe");p.add_argument("--tessdata",required=True);p.add_argument("--primary-register");p.add_argument("--workers",type=int,default=2);p.add_argument("--limit",type=int);args=p.parse_args(argv)
    if args.mode=="second-pass":
        if not args.primary_register:p.error("--primary-register is required for second-pass")
        return run_second_pass(args)
    if args.mode=="pdf-pages":return run_pdf_pages(args)
    return run_primary(args)
if __name__=="__main__":raise SystemExit(main())
