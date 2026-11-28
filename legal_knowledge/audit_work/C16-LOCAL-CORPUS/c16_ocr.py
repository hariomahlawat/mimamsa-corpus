"""Restartable exact-hash OCR for C16 DOCX images and rendered PDF pages."""
from __future__ import annotations
import argparse, csv, hashlib, io, json, os, subprocess, tempfile, time, uuid, zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from PIL import Image, ImageOps, __version__ as PILLOW_VERSION
import c16_reconcile as core

def load_jsonl(path):
    path=Path(path)
    return [] if not path.exists() else [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]

def write_jsonl_atomic(path, rows):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_suffix(path.suffix+".tmp")
    atomic_write(tmp,"".join(json.dumps(r,ensure_ascii=False,sort_keys=True)+"\n" for r in rows).encode("utf-8")); os.replace(tmp,path)

def atomic_write(path,payload):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+f".{os.getpid()}.{uuid.uuid4().hex}.tmp")
    with temporary.open("wb") as handle:
        handle.write(payload);handle.flush();os.fsync(handle.fileno())
    os.replace(temporary,path)

def write_state_record(root, record):
    digest=record["image_sha256"]; cfg=record.get("configuration_sha256","unversioned")
    root=Path(root);payload=json.dumps(record,ensure_ascii=False,sort_keys=True).encode("utf-8")
    attempt_id=hashlib.sha256(payload+str(time.time_ns()).encode()).hexdigest()
    attempt=root/"attempts"/cfg[:12]/digest[:2]/digest/f"{attempt_id}.json"
    atomic_write(attempt,payload)
    if record.get("access_disposition")=="HELD_ACCESS_MARKING_REVIEW":
        atomic_write(root/"holds"/cfg/digest[:2]/digest/f"{attempt_id}.json",payload)
    dst=root/"state"/cfg[:12]/digest[:2]/f"{digest}.json";atomic_write(dst,payload);return dst

def load_state_records(root):
    state=Path(root)/"state"
    return [] if not state.exists() else [json.loads(p.read_text(encoding="utf-8")) for p in sorted(state.rglob("*.json"))]

def load_attempt_records(root):
    attempts=Path(root)/"attempts"
    return [] if not attempts.exists() else [json.loads(p.read_text(encoding="utf-8")) for p in sorted(attempts.rglob("*.json"))]

def validate_record_artifacts(root,record):
    if record.get("state")!="COMPLETE":return False
    paths=record.get("artifact_paths",{});hashes=record.get("artifact_sha256",{})
    if set(paths)!=set(hashes):return False
    held=record.get("unreadable") is True or record.get("access_disposition") in ("HELD_ACCESS_MARKING_REVIEW","HELD_UNREADABLE_OR_PROCESSING_ERROR")
    if held:
        return not paths and all(record.get(f"{key}_path") is None for key in ("raw_text","normalised_text","word_boxes"))
    required={"raw_text","normalised_text","word_boxes"}
    if set(paths)!=required:return False
    root=Path(root).resolve()
    for key,relative in paths.items():
        if not isinstance(relative,str) or Path(relative).is_absolute() or record.get(f"{key}_path")!=relative:return False
        path=(root/relative).resolve()
        try:path.relative_to(root)
        except ValueError:return False
        if not path.is_file() or core.file_sha256(path)!=hashes[key]:return False
    return True

def intersect_current_jobs(cached,current_keys):return {key:value for key,value in cached.items() if key in current_keys}

def batch_completion(total_jobs,records):
    successful=sum(r.get("state")=="COMPLETE" for r in records);errors=sum(r.get("state")=="ERROR" for r in records)
    summary={"completed":successful,"errors":errors,"pending":max(0,total_jobs-successful)}
    return summary,(1 if errors else 2 if summary["pending"] else 0)

def processing_key(digest,cfg): return hashlib.sha256(f"{digest}:{cfg}".encode("ascii")).hexdigest()
def pdf_processing_key(source_sha256,physical_page,configuration_sha256,render_sha256):
    return hashlib.sha256(f"{source_sha256}:pdf-page-{physical_page}:{configuration_sha256}:{render_sha256}".encode("ascii")).hexdigest()

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

def persist_result(output,digest,result,restricted=False,namespace="",configuration_sha256=None):
    cfg=configuration_sha256 or "unversioned"
    base=Path(output)/(namespace or f"artifacts/{cfg[:12]}/{digest[:2]}/{digest}")
    unreadable=not bool(result.get("raw_text","").strip())
    disposition=("HELD_ACCESS_MARKING_REVIEW" if restricted else
                 "HELD_UNREADABLE_OR_PROCESSING_ERROR" if unreadable else
                 "SCREENED_NO_MARKING_DETECTED")
    record={"image_sha256":digest,"access_disposition":disposition,"raw_text_path":None,"normalised_text_path":None,"word_boxes_path":None,"artifact_paths":{},"artifact_sha256":{},"mean_confidence":result.get("mean_confidence"),"word_count":len(result.get("words",[])),"unreadable":unreadable,"evidence_verified":True}
    if restricted or unreadable:return record
    payloads={"raw_text":result.get("raw_text","").encode("utf-8"),
              "normalised_text":result.get("normalised_text","").encode("utf-8"),
              "word_boxes":json.dumps(result.get("words",[]),ensure_ascii=False,sort_keys=True).encode("utf-8")}
    extensions={"raw_text":"txt","normalised_text":"txt","word_boxes":"json"}
    paths={}
    for key,payload in payloads.items():
        artifact_sha=hashlib.sha256(payload).hexdigest();path=base/f"{key}-{artifact_sha}.{extensions[key]}"
        if not path.exists() or core.file_sha256(path)!=artifact_sha:atomic_write(path,payload)
        paths[key]=path;record["artifact_paths"][key]=path.relative_to(output).as_posix();record["artifact_sha256"][key]=artifact_sha
    record.update(raw_text_path=record["artifact_paths"]["raw_text"],normalised_text_path=record["artifact_paths"]["normalised_text"],word_boxes_path=record["artifact_paths"]["word_boxes"])
    if not validate_record_artifacts(output,{**record,"state":"COMPLETE"}):raise ValueError("persisted OCR artifact validation failed")
    return record

def model_hashes(tessdata,languages): return {x:core.file_sha256(Path(tessdata)/f"{x}.traineddata") for x in languages}

def ocr_configuration(tesseract,tessdata,mode="primary"):
    version=subprocess.run([str(tesseract),"--version"],check=True,capture_output=True,text=True).stdout.splitlines()[0]
    psm={"primary":[1],"second-pass":[6,11],"pdf-pages":[1]}[mode]
    preprocessing=["exif_transpose","grayscale","autocontrast"]
    if mode=="second-pass": preprocessing += ["upscale_2x","threshold_180"]
    cfg={"engine":"tesseract","engine_version":version,"languages":["eng","hin"],"language_model_sha256":model_hashes(tessdata,["eng","hin"]),"tsv_config_sha256":core.file_sha256(Path(tessdata)/"configs"/"tsv"),"mode":mode,"psm":psm,"preprocessing":preprocessing,"preprocessing_implementation":"c16-ocr/2.1","pillow_version":PILLOW_VERSION,"renderer":"PyMuPDF","renderer_version":core.pymupdf.VersionBind,"render_dpi":300 if mode=="pdf-pages" else None,"output":"tsv-word-boxes"}
    cfg["configuration_sha256"]=hashlib.sha256(json.dumps(cfg,sort_keys=True,separators=(",",":")).encode()).hexdigest(); return cfg

def load_verified_configuration(root):
    path=Path(root)/"OCR_CONFIGURATION.json";cfg=json.loads(path.read_text(encoding="utf-8"))
    declared=cfg.get("configuration_sha256");body={k:v for k,v in cfg.items() if k!="configuration_sha256"}
    actual=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    if declared!=actual:raise ValueError(f"OCR configuration digest mismatch: {path}")
    return cfg

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

def select_and_screen_attempts(attempts):
    for attempt in attempts:
        attempt["access_marking_detected"]=core.has_restriction_marking(attempt.get("raw_text",""))
    return best_attempt(attempts),any(x["access_marking_detected"] for x in attempts)

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

def _effective_access(records,expected_configurations=None):
    if any(r.get("access_disposition")=="HELD_ACCESS_MARKING_REVIEW" for r in records):
        return "HELD_ACCESS_MARKING_REVIEW"
    eligible=[r for r in records if (expected_configurations is None or r.get("configuration_sha256") in expected_configurations)]
    if any(r.get("state")=="COMPLETE" and r.get("evidence_verified") is True and not r.get("unreadable") and
           r.get("access_disposition")=="SCREENED_NO_MARKING_DETECTED" for r in eligible):
        return "SCREENED_NO_MARKING_DETECTED"
    return "HELD_UNREADABLE_OR_PROCESSING_ERROR"

def propagate_access_holds(inventory,image_records,pdf_records,expected_image_configurations=None,expected_pdf_configurations=None):
    images={}
    for record in image_records: images.setdefault(record.get("image_sha256"),[]).append(record)
    pages={}
    for record in pdf_records:pages.setdefault((record.get("source_sha256"),record.get("physical_page")),[]).append(record)
    rows=[]
    for doc in inventory:
        reasons=[]
        if doc.get("restricted"):
            reasons.append({"kind":"DOCUMENT_NATIVE_OR_REGISTER","access_disposition":"HELD_ACCESS_MARKING_REVIEW"})
        for image in doc.get("embedded_images",[]):
            digest=image["image_sha256"];disposition=_effective_access(images.get(digest,[]),expected_image_configurations)
            if disposition!="SCREENED_NO_MARKING_DETECTED":
                reasons.append({"kind":"EMBEDDED_IMAGE","image_sha256":digest,
                                "occurrence_id":image.get("occurrence_id"),"access_disposition":disposition})
        for page in doc.get("ocr_required_pages",[]):
            records=pages.get((doc["sha256"],page),[]);disposition=_effective_access(records,expected_pdf_configurations)
            record=next((r for r in records if expected_pdf_configurations is None or r.get("configuration_sha256") in expected_pdf_configurations),None)
            if disposition!="SCREENED_NO_MARKING_DETECTED":
                reasons.append({"kind":"PDF_PAGE","physical_page":page,"page_key":record.get("page_key") if record else None,
                                "access_disposition":disposition})
        if any(x["access_disposition"]=="HELD_ACCESS_MARKING_REVIEW" for x in reasons):
            document_disposition="HELD_ACCESS_MARKING_REVIEW"
        elif reasons: document_disposition="HELD_UNREADABLE_OR_PROCESSING_ERROR"
        else: document_disposition="SCREENED_NO_MARKING_DETECTED"
        rows.append({"inventory_id":doc["inventory_id"],"source_sha256":doc["sha256"],
                     "relative_path":doc["relative_path"],"document_access_disposition":document_disposition,
                     "derivative_access_disposition":"WITHHOLD_ALL_DERIVATIVES" if reasons else "ELIGIBLE_AFTER_OTHER_GATES",
                     "hold_reasons":reasons})
    return rows

def verified_pdf_snapshot(job):
    path=Path(job["source_path"])
    with path.open("rb") as handle:payload=handle.read()
    digest=hashlib.sha256(payload).hexdigest()
    if digest!=job["source_sha256"]:raise ValueError("source hash mismatch before PDF render")
    return {"payload":payload,"source_sha256":digest,"source_size_bytes":len(payload),"source_path":str(path)}

def render_verified_pdf_page(snapshot,physical_page,dpi=300):
    document=core.pymupdf.open(stream=snapshot["payload"],filetype="pdf")
    try:
        page_number=int(physical_page)
        if page_number<1 or page_number>len(document):raise ValueError("physical page outside verified PDF snapshot")
        page=document.load_page(page_number-1)
        pixmap=page.get_pixmap(dpi=dpi,alpha=False)
        payload=pixmap.tobytes("png")
        return {"payload":payload,"source_sha256":snapshot["source_sha256"],
                "source_size_bytes":snapshot["source_size_bytes"],"render_sha256":hashlib.sha256(payload).hexdigest(),
                "render_width":pixmap.width,"render_height":pixmap.height,"render_dpi":dpi}
    finally: document.close()

def render_pdf_page(job,dpi=300):
    return render_verified_pdf_page(verified_pdf_snapshot(job),job["physical_page"],dpi)["payload"]

def process_second_pass_job(job,tesseract,tessdata,output,cfg):
    digest=job["image_sha256"]
    try:
        payload=read_job_payload(job);attempts=[]
        for psm in cfg["psm"]:
            result=run_tesseract(payload,tesseract,tessdata,psm=psm,second_pass=True)
            result.update(configuration=f"psm-{psm}",psm=psm,word_count=len(result.get("words",[])))
            attempts.append(result)
        result,restricted=select_and_screen_attempts(attempts)
        record=persist_result(output,digest,result,restricted,configuration_sha256=cfg["configuration_sha256"])
        record.update(state="COMPLETE",processing_key=processing_key(digest,cfg["configuration_sha256"]),
                      configuration_sha256=cfg["configuration_sha256"],selected_psm=result["psm"],
                      attempts=[{"psm":x["psm"],"word_count":x["word_count"],
                                 "mean_confidence":x.get("mean_confidence"),
                                 "access_marking_detected":x["access_marking_detected"]} for x in attempts],
                      decorative_nomination=likely_decorative(job),error=None)
        return record
    except Exception as exc:
        return {"image_sha256":digest,"state":"ERROR","processing_key":processing_key(digest,cfg["configuration_sha256"]),
                "configuration_sha256":cfg["configuration_sha256"],"access_disposition":"HELD_UNREADABLE_OR_PROCESSING_ERROR",
                "unreadable":True,"error":f"{type(exc).__name__}: {exc}"[:500]}

def process_pdf_page_job(job,tesseract,tessdata,output,cfg):
    key=job["page_key"]
    try:
        snapshot=verified_pdf_snapshot(job);rendered=render_verified_pdf_page(snapshot,job["physical_page"],dpi=cfg["render_dpi"])
        result=run_tesseract(rendered["payload"],tesseract,tessdata,psm=1,second_pass=False)
        restricted=core.has_restriction_marking(result["raw_text"])
        record=persist_result(output,key,result,restricted,configuration_sha256=cfg["configuration_sha256"])
        record.update(state="COMPLETE",page_key=key,inventory_id=job["inventory_id"],
                      source_sha256=job["source_sha256"],relative_path=job["relative_path"],
                      physical_page=job["physical_page"],page_classification=job["page_classification"],
                      processing_key=pdf_processing_key(job["source_sha256"],job["physical_page"],cfg["configuration_sha256"],rendered["render_sha256"]),
                      configuration_sha256=cfg["configuration_sha256"],render_dpi=cfg["render_dpi"],
                      render_sha256=rendered["render_sha256"],render_width=rendered["render_width"],
                      render_height=rendered["render_height"],verified_source_sha256=rendered["source_sha256"],
                      verified_source_size_bytes=rendered["source_size_bytes"],evidence_verified=True,error=None)
        return record
    except Exception as exc:
        return {"image_sha256":key,"page_key":key,"inventory_id":job["inventory_id"],
                "source_sha256":job["source_sha256"],"relative_path":job["relative_path"],
                "physical_page":job["physical_page"],"page_classification":job["page_classification"],
                "state":"ERROR","processing_key":processing_key(key,cfg["configuration_sha256"]),
                "configuration_sha256":cfg["configuration_sha256"],
                "access_disposition":"HELD_UNREADABLE_OR_PROCESSING_ERROR","unreadable":True,
                "error":f"{type(exc).__name__}: {exc}"[:500]}

def validate_cached_job(output,record,job,cfg):
    if record.get("configuration_sha256")!=cfg["configuration_sha256"] or not record.get("evidence_verified"):
        return False
    if not validate_record_artifacts(output,record):return False
    try:
        if cfg["mode"]=="pdf-pages":
            snapshot=verified_pdf_snapshot(job)
            rendered=render_verified_pdf_page(snapshot,job["physical_page"],dpi=cfg["render_dpi"])
            return (record.get("verified_source_sha256")==snapshot["source_sha256"] and
                    record.get("render_sha256")==rendered["render_sha256"] and
                    record.get("processing_key")==pdf_processing_key(job["source_sha256"],job["physical_page"],cfg["configuration_sha256"],rendered["render_sha256"]))
        return hashlib.sha256(read_job_payload(job)).hexdigest()==job["image_sha256"]
    except Exception:
        return False

def validate_evidence_population(root,records,jobs,cfg,identifier,workers=1):
    expected={j[identifier] if identifier in j else j["image_sha256"]:j for j in jobs}
    supplied={}
    for record in records:
        key=record.get(identifier) or record.get("image_sha256")
        if key in supplied:raise ValueError(f"duplicate evidence record: {key}")
        supplied[key]=record
    if set(supplied)!=set(expected):raise ValueError("evidence population does not equal the current job set")
    keys=sorted(expected)
    def check(key):return key,validate_cached_job(Path(root),supplied[key],expected[key],cfg)
    results={}
    with ThreadPoolExecutor(max_workers=max(1,workers)) as executor:
        futures=[executor.submit(check,key) for key in keys]
        for number,future in enumerate(as_completed(futures),1):
            key,valid=future.result();results[key]=valid
            if number%500==0:print(f"validated {number}/{len(keys)} {cfg['mode']} records",flush=True)
    invalid=[key for key in keys if not results[key]]
    if invalid:raise ValueError(f"unverifiable evidence records ({len(invalid)}): {invalid[:5]}")
    valid=[supplied[key] for key in keys]
    positives=[]
    for record in load_attempt_records(root):
        key=record.get(identifier) or record.get("image_sha256")
        if key in expected and record.get("access_disposition")=="HELD_ACCESS_MARKING_REVIEW":positives.append(record)
    return valid+positives

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
        result=run_tesseract(read_job_payload(job),tesseract,tessdata); restricted=core.has_restriction_marking(result["raw_text"]); record=persist_result(output,d,result,restricted,configuration_sha256=cfg["configuration_sha256"])
        record.update(state="COMPLETE",processing_key=processing_key(d,cfg["configuration_sha256"]),configuration_sha256=cfg["configuration_sha256"],error=None);return record
    except Exception as exc:
        return {"image_sha256":d,"state":"ERROR","processing_key":processing_key(d,cfg["configuration_sha256"]),"configuration_sha256":cfg["configuration_sha256"],"access_disposition":"HELD_UNREADABLE_OR_PROCESSING_ERROR","raw_text_path":None,"normalised_text_path":None,"word_boxes_path":None,"mean_confidence":None,"word_count":0,"unreadable":True,"error":f"{type(exc).__name__}: {exc}"[:500]}

def run_primary(args):
    source,inventory,output=Path(args.source),Path(args.inventory),Path(args.output); tess,tdata=Path(args.tesseract),Path(args.tessdata); cfg=ocr_configuration(tess,tdata);output.mkdir(parents=True,exist_ok=True);(output/"OCR_CONFIGURATION.json").write_text(json.dumps(cfg,indent=2),encoding="utf-8")
    jobs,occ=image_jobs(load_jsonl(inventory),source); previous={r["image_sha256"]:r for r in load_jsonl(output/"OCR_PROCESSING_REGISTER.jsonl")+load_state_records(output) if r.get("configuration_sha256")==cfg["configuration_sha256"]}; [write_state_record(output,r) for r in previous.values()]
    completed={d:r for d,r in previous.items() if d in jobs and validate_cached_job(output,r,jobs[d],cfg)};pending=[j for d,j in jobs.items() if d not in completed];pending=pending[:args.limit] if args.limit else pending
    with ThreadPoolExecutor(max_workers=max(1,args.workers)) as ex:
        fut={ex.submit(process_job,j,tess,tdata,output,cfg):j for j in pending}
        for f in as_completed(fut):r=f.result();completed[r["image_sha256"]]=r;write_state_record(output,r)
    reg=output/f"OCR_PROCESSING_REGISTER-{cfg['configuration_sha256'][:12]}.jsonl";write_jsonl_atomic(reg,[completed[k] for k in sorted(completed)])
    for o in occ:
        r=completed.get(o["image_sha256"],{});o.update(ocr_processing_key=r.get("processing_key"),ocr_state=r.get("state"),access_disposition=r.get("access_disposition"))
    write_jsonl_atomic(output/"OCR_IMAGE_OCCURRENCES.jsonl",occ);errors=sum(r.get("state")!="COMPLETE" for r in completed.values());successful=sum(r.get("state")=="COMPLETE" for r in completed.values());pending_after=len(jobs)-successful;summary={"distinct_image_jobs":len(jobs),"completed":successful,"errors":errors,"pending":pending_after,"occurrences":len(occ),"reused_occurrences":len(occ)-len(jobs),"restricted":sum(r.get("access_disposition")=="HELD_ACCESS_MARKING_REVIEW" for r in completed.values()),"configuration_sha256":cfg["configuration_sha256"]};(output/"OCR_SUMMARY.json").write_text(json.dumps(summary,indent=2),encoding="utf-8");return 1 if errors else 2 if pending_after else 0

def run_restartable_batch(jobs,output,cfg,worker,workers,limit=None):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    (output/"OCR_CONFIGURATION.json").write_text(json.dumps(cfg,indent=2),encoding="utf-8")
    identifier="page_key" if cfg["mode"]=="pdf-pages" else "image_sha256"
    job_by_key={(j[identifier] if identifier in j else j["image_sha256"]):j for j in jobs}
    previous={r.get(identifier) or r.get("image_sha256"):r for r in load_state_records(output)
              if r.get("configuration_sha256")==cfg["configuration_sha256"]}
    completed={key:r for key,r in previous.items() if key in job_by_key and validate_cached_job(output,r,job_by_key[key],cfg)}
    pending=[j for j in jobs if (j[identifier] if identifier in j else j["image_sha256"]) not in completed]
    if limit: pending=pending[:limit]
    with ThreadPoolExecutor(max_workers=max(1,workers)) as ex:
        futures={ex.submit(worker,j):j for j in pending}
        for future in as_completed(futures):
            record=future.result();key=record.get(identifier) or record["image_sha256"]
            completed[key]=record;write_state_record(output,record)
    register=output/f"OCR_PROCESSING_REGISTER-{cfg['configuration_sha256'][:12]}.jsonl"
    write_jsonl_atomic(register,[completed[k] for k in sorted(completed)])
    rows=list(completed.values());errors=sum(r.get("state")!="COMPLETE" for r in rows);successful=sum(r.get("state")=="COMPLETE" for r in rows)
    pending_after=len(jobs)-successful
    summary={"mode":cfg["mode"],"jobs":len(jobs),"completed":successful,"errors":errors,"pending":pending_after,
             "unreadable_held":sum(r.get("access_disposition")=="HELD_UNREADABLE_OR_PROCESSING_ERROR" for r in rows),
             "access_marking_holds":sum(r.get("access_disposition")=="HELD_ACCESS_MARKING_REVIEW" for r in rows),
             "screened_no_marking":sum(r.get("access_disposition")=="SCREENED_NO_MARKING_DETECTED" for r in rows),
             "configuration_sha256":cfg["configuration_sha256"]}
    (output/"OCR_SUMMARY.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    return 1 if errors else 2 if pending_after else 0

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

def run_access_register(args):
    inventory=load_jsonl(args.inventory);source=Path(args.source)
    image_jobs_by_hash,_=image_jobs(inventory,source);all_image_jobs=list(image_jobs_by_hash.values())
    primary_cfg=load_verified_configuration(args.primary_root)
    primary=validate_evidence_population(args.primary_root,load_jsonl(args.primary_register),all_image_jobs,primary_cfg,"image_sha256",args.workers)
    image_rows=list(primary)
    if args.secondary_register:
        secondary_cfg=load_verified_configuration(args.secondary_root)
        secondary_jobs=second_pass_candidates(image_jobs_by_hash,primary)
        image_rows+=validate_evidence_population(args.secondary_root,load_jsonl(args.secondary_register),secondary_jobs,secondary_cfg,"image_sha256",args.workers)
    pdf_rows=[]
    if args.pdf_register:
        pdf_cfg=load_verified_configuration(args.pdf_root);jobs=pdf_page_jobs(inventory,source)
        pdf_rows=validate_evidence_population(args.pdf_root,load_jsonl(args.pdf_register),jobs,pdf_cfg,"page_key",args.workers)
    rows=propagate_access_holds(
        inventory, image_rows, pdf_rows,
        expected_image_configurations=set(args.image_config or []),
        expected_pdf_configurations=set(args.pdf_config or []),
    )
    output=Path(args.output);output.mkdir(parents=True,exist_ok=True)
    write_jsonl_atomic(output/"DOCUMENT_ACCESS_REGISTER.jsonl",rows)
    summary={"documents":len(rows),"screened":sum(r["document_access_disposition"]=="SCREENED_NO_MARKING_DETECTED" for r in rows),
             "access_marking_holds":sum(r["document_access_disposition"]=="HELD_ACCESS_MARKING_REVIEW" for r in rows),
             "unreadable_or_incomplete_holds":sum(r["document_access_disposition"]=="HELD_UNREADABLE_OR_PROCESSING_ERROR" for r in rows),
             "derivatives_withheld":sum(r["derivative_access_disposition"]=="WITHHOLD_ALL_DERIVATIVES" for r in rows)}
    atomic_write(output/"DOCUMENT_ACCESS_SUMMARY.json",json.dumps(summary,indent=2).encode("utf-8"))
    return 0

def parse_args(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--mode",choices=("primary","second-pass","pdf-pages","access-register"),default="primary");p.add_argument("--source");p.add_argument("--inventory",required=True);p.add_argument("--output",required=True);p.add_argument("--tesseract",default=r"C:\Program Files\Tesseract-OCR\tesseract.exe");p.add_argument("--tessdata");p.add_argument("--primary-register");p.add_argument("--secondary-register");p.add_argument("--pdf-register");p.add_argument("--primary-root");p.add_argument("--secondary-root");p.add_argument("--pdf-root");p.add_argument("--workers",type=int,default=2);p.add_argument("--limit",type=int)
    p.add_argument("--image-config",action="append",default=[],help="Accepted image OCR configuration SHA-256; repeat for each required configuration")
    p.add_argument("--pdf-config",action="append",default=[],help="Accepted PDF OCR configuration SHA-256; repeat for each required configuration")
    return p.parse_args(argv)

def main(argv=None):
    args=parse_args(argv)
    if args.mode=="access-register":return run_access_register(args)
    if args.mode=="second-pass":
        if not args.primary_register:raise SystemExit("--primary-register is required for second-pass")
        return run_second_pass(args)
    if args.mode=="pdf-pages":return run_pdf_pages(args)
    return run_primary(args)
if __name__=="__main__":raise SystemExit(main())
