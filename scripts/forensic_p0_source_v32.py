"""Forensic source reconciliation for 5 unresolved Mimamsa P0 cases.

Checks immutable canonical HF raw-manifest SHA-256, report/decision-year variation,
and court-PDF case-number/name evidence. No holding or JAG status is promoted.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import fitz
from huggingface_hub import HfApi, CommitOperationAdd, hf_hub_download

REPO = "hariomahlawat/mimamsa-corpus"
INPUT = "legal_knowledge/crosswalk/v3.1/02_P0_Candidate_Details.jsonl"
MANIFEST = "data/raw_manifest.csv"
DEST = "legal_knowledge/crosswalk/v3.2"

FOCUS = {
    "DCLR-SC-1964-A11": {"distinctive": ["sarup", "swarup"], "year": 1963,
                         "secondary": "ram", "document_number": "166", "type": "UNMATCHED"},
    "DCLR-SC-2005-L01": {"distinctive": ["navjot", "afsan"], "year": 2005,
                         "secondary": "sandhu", "document_number": "373", "type": "UNMATCHED"},
    "DCLR-SC-2016-L04": {"distinctive": ["bhaira"], "year": 2016,
                         "secondary": "mani", "document_number": "4409", "type": "UNMATCHED"},
    "DCLR-SC-2008-L05": {"distinctive": ["dhingra"], "year": 2007,
                         "secondary": "s", "document_number": "106", "type": "UNMATCHED"},
    "DCLR-SC-1996-L07": {"distinctive": ["baljit", "baltit"], "year": 1996,
                         "secondary": "singh", "document_number": "13272", "type": "OCR_IDENTITY_PENDING"},
}


def get(path):
    return Path(hf_hub_download(repo_id=REPO, repo_type="dataset", filename=path, force_download=True))

def normal(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()

def raw_year(path):
    m = re.search(r"/sci/((?:19|20)\d{2})/", path or "")
    return int(m.group(1)) if m else None

def verify_pdf(row, focus):
    path = row.get("raw_path", "")
    blob = get(path).read_bytes()
    observed = hashlib.sha256(blob).hexdigest()
    if observed != row["sha256"]:
        raise RuntimeError("Immutable source SHA-256 mismatch: " + path)
    if not blob.startswith(b"%PDF-"):
        raise RuntimeError("Archived source is not PDF: " + path)
    with fitz.open(stream=blob, filetype="pdf") as doc:
        chars = " ".join(p.get_text("text") for p in doc)
        pages = len(doc)
    body = normal(chars)
    distinct = any(name in body.split() for name in focus["distinctive"])
    number = bool(re.search(r"(?<!\d)"+re.escape(focus["document_number"])+r"(?!\d)", body))
    yr = str(focus["year"]) in body or str(focus["year"]+1) in body
    # First-page/middle excerpt is documentary debugging evidence only, not a judgment excerpt.
    markers = ["baltit", "baljit", focus["document_number"]]
    present = []
    for marker in markers:
        p = body.find(marker)
        if p >= 0:
            present.append({"marker": marker, "context": body[max(0,p-65):min(len(body),p+95)]})
    return {"sha256_verified": True, "pdf_pages": pages, "pdf_bytes": len(blob),
            "character_count":len(chars.strip()), "distinctive_name_seen_in_pdf":distinct,
            "case_number_seen_in_pdf":number, "judgment_or_report_year_seen_in_pdf":yr,
            "restricted_text_evidence":present[:3]}


def main():
    api=HfApi()
    info=api.repo_info(repo_id=REPO, repo_type="dataset")
    if not info.private:
        raise RuntimeError("Private HF destination required")
    with get(MANIFEST).open(encoding="utf-8-sig", newline="") as f:
        raw=list(csv.DictReader(f))
    prev=[json.loads(s) for s in get(INPUT).read_text().splitlines() if s.strip()]
    byid={r["curated_id"]:r for r in prev}
    if len(raw)<2500 or len(prev)!=11:
        raise RuntimeError("Source manifest or curated case dimensions incorrect")
    if not set(FOCUS).issubset(byid):
        raise RuntimeError("Five focus cases not present in v3.1")

    out=[]
    for key, focus in FOCUS.items():
        old=byid[key]
        candidates=[]
        if focus["type"] == "OCR_IDENTITY_PENDING":
            # Fixed v3.1 candidate; prevent accidentally substituting other same-name cases.
            raw_by_path={r.get("raw_path"):r for r in raw}
            p=old["canonical_source_path"]
            if p not in raw_by_path:
                raise RuntimeError("Archived candidate missing from original raw manifest")
            candidates=[(999,raw_by_path[p])]
        else:
            for r in raw:
                path=r.get("raw_path","")
                y=raw_year(path)
                if y is None or abs(y-focus["year"])>2:
                    continue
                title=normal(r.get("title",""))
                title_tokens=title.split()
                if not any(x in title_tokens for x in focus["distinctive"]):
                    continue
                secondary=focus["secondary"]
                secondary_ok=secondary in title_tokens or secondary=="s"
                score=(3 if y==focus["year"] else 1)+(2 if secondary_ok else 0)
                candidates.append((score,r))
            candidates.sort(key=lambda x: (-x[0], x[1].get("raw_path","")))
            candidates=candidates[:3]

        checked=[]
        for score,row in candidates[:2]:
            check=verify_pdf(row,focus)
            positive=check["sha256_verified"] and check["distinctive_name_seen_in_pdf"]
            high=positive and (check["case_number_seen_in_pdf"] or check["judgment_or_report_year_seen_in_pdf"])
            if high:
                state="RAW_SHA_AND_CASE_IDENTITY_CLUES_CORROBORATED"
            elif positive:
                state="RAW_SHA_NAME_ONLY_FURTHER_REVIEW"
            else:
                state="RAW_SHA_CONFIRMED_IDENTIFIERS_NOT_FOUND"
            checked.append({
                "path":row["raw_path"],"manifest_title":row.get("title",""),
                "manifest_sha256":row["sha256"],"source_url":row.get("source_url",""),
                "title_search_score":score,"evidence_status":state,**check
            })
        if not checked:
            overall="NO_ADDITIONAL_SOURCE_CANDIDATE_IN_CURRENT_RAW_MANIFEST"
        elif any(x["evidence_status"]=="RAW_SHA_AND_CASE_IDENTITY_CLUES_CORROBORATED" for x in checked):
            overall="CORPUS_SOURCE_IDENTITY_CLUES_CORROBORATED_REQUIRES_HUMAN_REVIEW"
        else:
            overall="CORPUS_SOURCE_BYTE_INTEGRITY_ONLY_IDENTITY_UNRESOLVED"
        result={
            "case_id":key,"previous_status":old["source_status"],
            "candidate_year":focus["year"],"previous_pdf_path":old.get("canonical_source_path",""),
            "candidate_files_examined":len(checked),"overall_status":overall,
            "candidate_evidence":checked,
            "official_court_pdf_byte_equivalence":"NOT_TESTED",
            "full_holding_review":"NOT_COMPLETED","later_treatment_review":"NOT_COMPLETED",
            "jag_approved":False
        }
        out.append(result)
        print("V32_RESULT", key, overall, "candidates",len(checked))
        for x in checked:
            print("V32_SOURCE",key,x["path"],"sha256",x["manifest_sha256"],
                  "distinctive_name",x["distinctive_name_seen_in_pdf"],
                  "case_number",x["case_number_seen_in_pdf"],
                  "year",x["judgment_or_report_year_seen_in_pdf"])
            if key=="DCLR-SC-1996-L07":
                print("V32_BALJIT_TEXT_EVIDENCE",json.dumps(x["restricted_text_evidence"]))
    if len(out)!=5:
        raise RuntimeError("Expected 5 results")
    summ=Counter(x["overall_status"] for x in out)
    report={
        "version":"3.2","generated_utc":datetime.now(timezone.utc).isoformat(),
        "canonical_private_dataset":REPO,"raw_manifest_rows":len(raw),
        "examined_case_count":5,"status_counts":dict(summ),
        "source_identifier_verified_case_count":sum(x["overall_status"]=="CORPUS_SOURCE_IDENTITY_CLUES_CORROBORATED_REQUIRES_HUMAN_REVIEW" for x in out),
        "case_identity_legally_approved":0,
        "notes":[
            "Relaxed search is a discovery tool. Even matching name/case number/year is a candidate source-identity check, not a certified legal holding.",
            "If no candidate found, the case might still be available outside this raw-manifest snapshot.",
            "Historical reports may contain typographical/OCR errors in case party names.",
            "All original PDFs and curated cases remain unchanged."
        ]
    }
    data=("".join(json.dumps(z,ensure_ascii=False)+"\n" for z in out)).encode()
    summary=(json.dumps(report,indent=2,ensure_ascii=False)+"\n").encode()
    csvhead=["case_id","status","pdfs_examined","best_source_path","best_source_sha256",
             "pdf_name_seen","pdf_number_seen","pdf_year_seen","needs_human_review","jag_approved"]
    st=io.StringIO()
    w=csv.DictWriter(st,fieldnames=csvhead,lineterminator="\n")
    w.writeheader()
    for item in out:
        p=item["candidate_evidence"][0] if item["candidate_evidence"] else {}
        w.writerow({"case_id":item["case_id"],"status":item["overall_status"],
            "pdfs_examined":item["candidate_files_examined"],"best_source_path":p.get("path",""),
            "best_source_sha256":p.get("manifest_sha256",""),
            "pdf_name_seen":p.get("distinctive_name_seen_in_pdf",""),
            "pdf_number_seen":p.get("case_number_seen_in_pdf",""),
            "pdf_year_seen":p.get("judgment_or_report_year_seen_in_pdf",""),
            "needs_human_review":"YES","jag_approved":"NO"})
    files={
       f"{DEST}/01_Five_Case_Source_Forensics.jsonl":data,
       f"{DEST}/02_Five_Case_Forensics_Summary.json":summary,
       f"{DEST}/03_Five_Case_Review_Queue.csv":st.getvalue().encode(),
       f"{DEST}/README.md":(
          "# v3.2 source forensics — five unresolved P0 records\n\n"
          "Compared the five v3.1 problem cases to the existing private raw-source manifest, "
          "using limited party-name variants and a two-year reporting window. When a plausible "
          "candidate existed, the immutable source PDF was read from Hugging Face and its "
          "SHA-256 verified before extracting case-name/case-number/year clues. "
          "Results are discovery evidence, not authoritative judgment-byte parity or JAG approval.\n"
        ).encode()
    }
    operations=[CommitOperationAdd(path_in_repo=path,path_or_fileobj=io.BytesIO(payload)) for path,payload in files.items()]
    commit=api.create_commit(repo_id=REPO,repo_type="dataset",operations=operations,
                             commit_message="Stage five-case source forensic checks v3.2, no legal approval")
    rev=getattr(commit,"oid",None)
    if not rev:
        raise RuntimeError("No dataset revision returned")
    for name,payload in files.items():
        remote=get(name).read_bytes()
        if hashlib.sha256(remote).digest()!=hashlib.sha256(payload).digest():
            raise RuntimeError("Remote readback SHA-256 mismatch: "+name)
    print("V32_HF_VERIFIED",len(files),"revision="+rev,"SUMMARY",json.dumps(dict(summ)))


if __name__=="__main__":
    main()
