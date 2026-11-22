"""Validate v3.6 preliminary legal authority register against preserved sources.

This gate does NOT independently approve judicial holdings. It rejects untraceable
case IDs, missing source dossiers, accidental legal release and changed originals.
"""
from __future__ import annotations

import csv,hashlib,io,json,re
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
from huggingface_hub import HfApi,CommitOperationAdd,hf_hub_download

DATASET="hariomahlawat/mimamsa-corpus"
ROOT="legal_knowledge/legal_review/v3.6"
REPORT="legal_knowledge/quality_audit/v3.6"
SOURCES={
    "legal_knowledge/curated_originals/case_law/v0.9/cases_53.jsonl":
      "8b8d53cd1434f7c1c6eaebe77f1fe295fb8b81b755e93276999b4b40b3c8f89a",
    "legal_knowledge/curated_originals/knowledge_base/v0.9/records_658.jsonl":
      "9a8f0d193065762ffa987116dc761bcb734008d2a87a946f5591741f5befcfc1",
}
P0="legal_knowledge/quality_audit/v3.0/01_Case_Metadata_Findings.jsonl"
ORIGINS="legal_knowledge/holding_review/v3.4/01_P0_PDF_Provenance.jsonl"
FULL="legal_knowledge/full_text_working/v3.5/01_Extraction_Manifest.json"
OLD_V35="legal_knowledge/quality_audit/v3.5/01_Integrity_Treatment_NonRelease_Result.json"
SC_META="legal_knowledge/judgment_originals/sci/2026/nc_isaac_2026.json"
SC_PDF="legal_knowledge/judgment_originals/sci/2026/nc_isaac_2026.pdf"

def dl(p,revision=None):
    return Path(hf_hub_download(repo_id=DATASET,repo_type="dataset",
                                filename=p,revision=revision,force_download=True))
def records(p):
    return [json.loads(s) for s in dl(p).read_text(encoding="utf-8").splitlines() if s.strip()]
def row_csv(rows,fields):
    out=io.StringIO()
    writer=csv.DictWriter(out,fieldnames=fields,lineterminator="\n")
    writer.writeheader();writer.writerows(rows)
    return out.getvalue().encode("utf-8")

def main():
    api=HfApi()
    info=api.repo_info(repo_id=DATASET,repo_type="dataset")
    if not info.private:
        raise RuntimeError("Legal data destination is not private")
    for path,expected in SOURCES.items():
        if hashlib.sha256(dl(path).read_bytes()).hexdigest()!=expected:
            raise RuntimeError("Immutable original changed: "+path)
    original_p0={x["case_id"] for x in records(P0) if x.get("metadata_priority")=="P0"}
    sources={x["case_id"]:x for x in records(ORIGINS)}
    if len(original_p0)!=11 or set(sources)!=original_p0:
        raise RuntimeError("P0 evidence source set differs from canonical eleven")
    full=json.loads(dl(FULL).read_text(encoding="utf-8"))
    if full["source_pdf_verified"]!=10 or full["source_pdf_missing"]!=1:
        raise RuntimeError("Missing cases or wrong archived evidence count")
    by_full={x["case_id"]:x for x in full["manifest"]}
    if set(by_full)!=original_p0:
        raise RuntimeError("Full-text working set does not cover same cases")

    case_dossiers={}
    for path in api.list_repo_files(repo_id=DATASET,repo_type="dataset"):
        if not path.startswith(ROOT+"/case_dossiers/") or not path.endswith(".md"):
            continue
        t=dl(path).read_text(encoding="utf-8")
        if "BLOCKED_JAG_PENDING" not in t or "independent JAG" not in t.lower():
            raise RuntimeError("Dossier missing release or reviewer warning "+path)
        m=re.search(r"\*\*Curated ID:\*\* \`([^\`]+)\`",t)
        if not m:
            raise RuntimeError("Dossier missing original curated ID "+path)
        cid=m.group(1)
        if cid in case_dossiers:
            raise RuntimeError("Duplicate source dossier for "+cid)
        if cid not in original_p0:
            raise RuntimeError("Unapproved extraneous case dossier "+cid)
        evidence=sources[cid]
        source_path=evidence.get("pdf_path")
        if source_path:
            if source_path not in t:
                raise RuntimeError("Dossier does not identify original checked source "+cid)
            file=dl(source_path).read_bytes()
            if hashlib.sha256(file).hexdigest()!=evidence["sha256"]:
                raise RuntimeError("Dossier linked PDF checksum conflict "+cid)
        else:
            if cid!="DCLR-SC-2008-L05" or "Original court PDF not archived" not in t:
                raise RuntimeError("Unverified court source was incorrectly implied")
        case_dossiers[cid]={"path":path,"source_sha":evidence.get("sha256"),
                            "source_tier":evidence.get("source_tier"),
                            "source_status":"SHA_VERIFIED" if source_path else "NOT_ARCHIVED"}
    if len(case_dossiers)!=11 or set(case_dossiers)!=original_p0:
        raise RuntimeError("Expected 11 unique source dossiers in private HF")

    props=records(ROOT+"/01_Proposition_Authority_Register.jsonl")
    if len(props)!=28 or len({x["proposition_id"] for x in props})!=28:
        raise RuntimeError("28 unique authority records required")
    counts=Counter(x["case_id"] for x in props)
    if any(counts[c]!=2 for c in original_p0) or counts["EXTERNAL-2026-INSC-993"]!=6:
        raise RuntimeError("Incorrect original case/proposition coverage")
    for prop in props:
        if prop["jag_approved"] is not False or prop["commander_operational_clearance"] is not False:
            raise RuntimeError("Proposition inadvertently approved for operational use")
        if prop["full_opinion_second_review"] or prop["subsequent_treatment_exhaustive"] or prop["temporal_applicability_verified"]:
            raise RuntimeError("Unperformed merits/temporal/later-case review asserted complete")
        if prop["ratio_status"] not in ("ANALYST_CANDIDATE_UNAPPROVED","SOURCE_TEXT_REVIEWED_BUT_JAG_UNAPPROVED"):
            raise RuntimeError("Invalid nonapproved proposition status")
        if not prop["pdf_page_or_secondary_locator"] or not prop["statutory_scope"]:
            raise RuntimeError("Untraceable proposed authority record")

    exceptions=records(ROOT+"/02_Contradiction_And_Release_Exception_Register.jsonl")
    if len(exceptions)!=7 or len({x["exception_id"] for x in exceptions})!=7:
        raise RuntimeError("Seven distinct source/legal exception tickets required")
    if not any(x["exception_id"]=="EX36-001" and
               x["original_gazette_authenticated"] is False for x in exceptions):
        raise RuntimeError("Army Rule23 original Gazette must remain a red-line exception")
    sc=json.loads(dl(SC_META).read_text())
    if sc.get("source_tier")!="OFFICIAL_SUPREME_COURT_API" or (
       hashlib.sha256(dl(SC_PDF).read_bytes()).hexdigest()!=sc.get("sha256")):
        raise RuntimeError("Official Supreme Court 2026 source checksum changed")
    v35=json.loads(dl(OLD_V35).read_text())
    if v35["commander_facing_release"] or v35["case_treatment_jag_approved"]!=0:
        raise RuntimeError("Inherited v3.5 legal release gate not satisfied")

    queue=[]
    for cid in sorted(original_p0):
        obj=case_dossiers[cid]
        queue.append({
         "case_id":cid,"dossier_path":obj["path"],
         "case_source_tier":obj["source_tier"] or "ORIGINAL_MISSING",
         "case_source_sha256":obj["source_sha"] or "",
         "proposed_propositions":counts[cid],
         "reviewer1_primary_opinion":"","reviewer1_date":"",
         "reviewer2_legal_treatment":"","reviewer2_date":"",
         "original_gazette_and_statute_version_checked":"NO",
         "subsequent_case_treatment_exhaustive":"NO",
         "JAG_decision":"PENDING",
         "operational_release":"NO"
        })
    result={
       "batch":"v3.6","generated_utc":datetime.now(timezone.utc).isoformat(),
       "result":"TECHNICAL_SOURCE_PROVENANCE_AND_RELEASE_INVARIANTS_PASSED",
       "source_dataset":DATASET,"source_originals_preserved":True,
       "p0_dossiers":len(case_dossiers),
       "archived_sha_verified":sum(x["source_status"]=="SHA_VERIFIED" for x in case_dossiers.values()),
       "case_original_missing":sum(x["source_status"]=="NOT_ARCHIVED" for x in case_dossiers.values()),
       "proposition_records":len(props),"p0_proposition_candidates":22,
       "isaac_2026_paragraph_source_observations":6,
       "legal_exceptions":len(exceptions),
       "independent_primary_legal_reviews_completed":0,
       "independent_subsequent_treatment_reviews_completed":0,
       "gazette_rule23_1954_authenticated":False,
       "jag_approved_propositions":0,"operational_releases":0,
       "note":"All case dossiers and authority records are source-grounded preliminary analyst research; no independent second-reader or JAG judgment was performed by this technical gate."
    }
    files={
      REPORT+"/01_V36_Source_And_NonRelease_Gate.json":
        (json.dumps(result,ensure_ascii=False,indent=2)+"\n").encode(),
      REPORT+"/02_JAG_Reviewer_Queue.csv":
        row_csv(queue,list(queue[0].keys())),
      REPORT+"/README.md":
        ("# v3.6 independent-review package integrity\n\n"
         "Source SHAs, dossier inventory, 28 non-approved proposition candidates, 7 exceptions, "
         "11 review queue entries and no operational release are automatically checked. "
         "Independent full judicial-opinion review and formal JAG decisions are **not** certified "
         "by passing technical checks.\n").encode()
    }
    commit=api.create_commit(repo_id=DATASET,repo_type="dataset",
       operations=[CommitOperationAdd(path_in_repo=p,path_or_fileobj=io.BytesIO(data))
                   for p,data in files.items()],
       commit_message="Validate v3.6 P0 dossiers and authority register and produce JAG reviewer queue (not approved)")
    revision=getattr(commit,"oid",None)
    if not revision:
        raise RuntimeError("No Hugging Face commit revision")
    for p,data in files.items():
        if hashlib.sha256(dl(p,revision).read_bytes()).digest()!=hashlib.sha256(data).digest():
            raise RuntimeError("HF v3.6 report SHA readback mismatch "+p)
    print("V36_TECHNICAL_SOURCE_GATE_VERIFIED",len(files),"files",
          "cases",len(case_dossiers),"propositions",len(props),"exceptions",len(exceptions),
          "revision",revision)

if __name__=="__main__":
    main()
