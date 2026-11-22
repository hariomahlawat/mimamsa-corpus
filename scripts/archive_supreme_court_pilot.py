"""Pilot: archive two official Supreme Court judgment PDFs in the private Mimamsa dataset.

The private dataset is a provenance store. An archived judgment is NOT a verified holding.
This script neither edits crawler data nor modifies any previously uploaded originals.
"""
from __future__ import annotations

import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path

import fitz
import requests
from huggingface_hub import HfApi, CommitOperationAdd, hf_hub_download

DATASET = "hariomahlawat/mimamsa-corpus"
CASES = [
    {
        "record_id": "DCLR-SC-2020-002",
        "case_name": "Union of India v Ex Sep Virendra Kumar",
        "decision_date": "2020-01-07",
        "source_url": "https://api.sci.gov.in/supremecourt/2018/10621/10621_2018_11_1501_19310_Judgement_07-Jan-2020.pdf",
        "title_token": "virendra",
        "path": "legal_knowledge/judgment_originals/sci/2020/virendra_kumar_2020.pdf",
    },
    {
        "record_id": None,
        "case_name": "Union of India v P S Gill",
        "decision_date": "2019-11-27",
        "source_url": "https://api.sci.gov.in/supremecourt/2012/26169/26169_2012_11_1501_18538_Judgement_27-Nov-2019.pdf",
        "title_token": "gill",
        "path": "legal_knowledge/judgment_originals/sci/2019/p_s_gill_2019.pdf",
    },
]

def main():
    api = HfApi()
    info = api.repo_info(repo_id=DATASET, repo_type="dataset")
    if not info.private:
        raise RuntimeError("Refusing transfer to public Hugging Face dataset")
    # Avoid repeated requests to Supreme Court servers on routine legal-layer commits.
    # Reuse already archived, checksum-verified PDFs when all source metadata is present.
    remote_register = "legal_knowledge/judgment_originals/sci/pilot_sources_2026-11-22.json"
    if api.file_exists(repo_id=DATASET, filename=remote_register, repo_type="dataset"):
        remote_meta = hf_hub_download(repo_id=DATASET, filename=remote_register,
                                      repo_type="dataset", force_download=True)
        existing = json.loads(Path(remote_meta).read_text(encoding="utf-8"))
        by_path = {e.get("path"): e for e in existing}
        if all(c["path"] in by_path for c in CASES):
            matched = True
            for case in CASES:
                item = by_path[case["path"]]
                if not api.file_exists(repo_id=DATASET, filename=case["path"], repo_type="dataset"):
                    matched = False
                    break
                local = hf_hub_download(repo_id=DATASET, filename=case["path"],
                                        repo_type="dataset", force_download=True)
                if hashlib.sha256(Path(local).read_bytes()).hexdigest() != item.get("sha256"):
                    raise RuntimeError("Previously archived official PDF failed hash verification")
            if matched:
                print(f"SC_PILOT_ALREADY_VERIFIED {len(CASES)} existing official judgments")
                return
    ops = []
    evidence = []
    for case in CASES:
        response = requests.get(case["source_url"], timeout=40,
                                headers={"User-Agent": "Mimamsa legal-research/1.0 (private archival verification)"})
        response.raise_for_status()
        content = response.content
        if not content.startswith(b"%PDF-") or len(content) < 8000:
            raise RuntimeError(f"Invalid/short PDF from official URL for {case['case_name']}")
        with fitz.open(stream=content, filetype="pdf") as document:
            count = len(document)
            title_text = " ".join(document[p].get_text() for p in range(min(4, count))).lower()
        if "supreme court" not in title_text or case["title_token"] not in title_text:
            raise RuntimeError(f"Official source/title mismatch for {case['case_name']}; do not archive")
        digest = hashlib.sha256(content).hexdigest()
        ops.append(CommitOperationAdd(path_in_repo=case["path"], path_or_fileobj=io.BytesIO(content)))
        evidence.append({
            "case_id": case["record_id"], "title": case["case_name"],
            "decision_date": case["decision_date"], "issuing_authority": "Supreme Court of India",
            "source_url": case["source_url"], "final_url": response.url,
            "retrieved_at": datetime.now(timezone.utc).isoformat(), "sha256": digest,
            "bytes": len(content), "pages": count, "path": case["path"],
            "source_tier": "official_court_domain", "legal_holding_verified": False,
            "jag_approved": False, "subsequent_treatment_checked": False,
        })
        print(f'VALIDATED_SOURCE {case["case_name"]}: pages={count} bytes={len(content)} sha256={digest}')

    path_meta = "legal_knowledge/judgment_originals/sci/pilot_sources_2026-11-22.json"
    meta_data = json.dumps(evidence, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"
    ops.append(CommitOperationAdd(path_in_repo=path_meta, path_or_fileobj=io.BytesIO(meta_data)))
    commit = api.create_commit(repo_id=DATASET, repo_type="dataset", operations=ops,
                               commit_message="Archive two official SC judgment originals (legal review pending)")
    revision = getattr(commit, "oid", None)
    if not revision:
        raise RuntimeError("Hugging Face commit returned without revision")
    for item, original in zip(evidence, ops):
        downloaded = hf_hub_download(repo_id=DATASET, repo_type="dataset",
                                     filename=item["path"], revision=revision, force_download=True)
        if hashlib.sha256(Path(downloaded).read_bytes()).hexdigest() != item["sha256"]:
            raise RuntimeError("Read-back hash mismatch: " + item["path"])
    remote_meta = hf_hub_download(repo_id=DATASET, repo_type="dataset",
                                  filename=path_meta, revision=revision, force_download=True)
    if Path(remote_meta).read_bytes() != meta_data:
        raise RuntimeError("Metadata read-back mismatch")
    print(f"SC_PILOT_VERIFIED {len(evidence)} judgments commit={revision}")

if __name__ == "__main__":
    main()
