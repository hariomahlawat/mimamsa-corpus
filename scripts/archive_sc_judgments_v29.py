"""Archive two original SCI JUDIS military law precedents to the private canonical corpus.

Transports only official court PDFs, with source/title checks and remote SHA-256 readback.
Legal interpretation and post-decision treatment remain pending JAG review.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path

import fitz
import requests
from huggingface_hub import HfApi, CommitOperationAdd, hf_hub_download

REPO = "hariomahlawat/mimamsa-corpus"
META = "legal_knowledge/judgment_originals/sci/pilot_sources_v2.9.json"
TARGETS = [
    {
        "case_id": "DCLR-SC-1982-001",
        "case": "Lt Col Prithi Pal Singh Bedi v Union of India",
        "date": "1982-08-25",
        "source_url": "https://api.sci.gov.in/jonew/judis/9884.pdf",
        "title_tokens": ("prithi", "bedi"),
        "path": "legal_knowledge/judgment_originals/sci/1982/prithi_pal_singh_bedi_1982.pdf",
    },
    {
        "case_id": "DCLR-SC-1987-R01",
        "case": "Ranjit Thakur v Union of India",
        "date": "1987-10-15",
        "source_url": "https://api.sci.gov.in/jonew/judis/8566.pdf",
        "title_tokens": ("ranjit", "thakur"),
        "path": "legal_knowledge/judgment_originals/sci/1987/ranjit_thakur_1987.pdf",
    },
]


def main():
    api = HfApi()
    repo_info = api.repo_info(repo_id=REPO, repo_type="dataset")
    if not repo_info.private:
        raise RuntimeError("Private destination required for restricted research corpus")

    if api.file_exists(repo_id=REPO, repo_type="dataset", filename=META):
        remote_meta = hf_hub_download(repo_id=REPO, repo_type="dataset",
                                     filename=META, force_download=True)
        existing = json.loads(Path(remote_meta).read_text(encoding="utf-8"))
        indexed = {e.get("path"): e for e in existing}
        if all(t["path"] in indexed for t in TARGETS):
            for t in TARGETS:
                e = indexed[t["path"]]
                if not api.file_exists(repo_id=REPO, repo_type="dataset", filename=t["path"]):
                    raise RuntimeError("Metadata exists but source PDF is missing: " + t["path"])
                p = Path(hf_hub_download(repo_id=REPO, repo_type="dataset",
                                         filename=t["path"], force_download=True))
                if hashlib.sha256(p.read_bytes()).hexdigest() != e["sha256"]:
                    raise RuntimeError("Archived PDF failed SHA-256 readback: " + t["case"])
            print(f"V29_SC_ARCHIVE_ALREADY_VERIFIED {len(TARGETS)}")
            return

    operations, evidence = [], []
    for t in TARGETS:
        response = requests.get(t["source_url"], timeout=45,
                                headers={"User-Agent": "Mimamsa-legal-archive/1.0"})
        response.raise_for_status()
        data = response.content
        if len(data) < 8000 or not data.startswith(b"%PDF-"):
            raise RuntimeError("Invalid PDF or unexpected response for " + t["case"])
        with fitz.open(stream=data, filetype="pdf") as doc:
            count = len(doc)
            first = " ".join(doc[i].get_text() for i in range(min(2, count))).lower()
        if "supreme court" not in first or not all(z in first for z in t["title_tokens"]):
            raise RuntimeError("Case identity not confirmed in source PDF: " + t["case"])
        digest = hashlib.sha256(data).hexdigest()
        evidence.append({
            "case_id": t["case_id"],
            "case_name": t["case"],
            "decision_date": t["date"],
            "court": "Supreme Court of India",
            "official_source_url": t["source_url"],
            "final_retrieval_url": response.url,
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_path": t["path"],
            "bytes": len(data), "pages": count,
            "sha256": digest,
            "source_authenticated_to_court_domain": True,
            "identity_checked_against_pdf_title": True,
            "full_holding_review_complete": False,
            "subsequent_treatment_verified": False,
            "jag_approved": False,
        })
        operations.append(CommitOperationAdd(path_in_repo=t["path"], path_or_fileobj=io.BytesIO(data)))
        print(f"V29_SOURCE_IDENTIFIED {t['case_id']} pages={count} bytes={len(data)} SHA256={digest}")
    metadata = json.dumps(evidence, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
    operations.append(CommitOperationAdd(path_in_repo=META, path_or_fileobj=io.BytesIO(metadata)))
    res = api.create_commit(repo_id=REPO, repo_type="dataset", operations=operations,
                            commit_message="Archive two SCI JUDIS source judgments with provenance (v2.9)")
    rev = getattr(res, "oid", None)
    if not rev:
        raise RuntimeError("Hugging Face response has no committed revision")
    for e in evidence:
        downloaded = Path(hf_hub_download(repo_id=REPO, repo_type="dataset", filename=e["source_path"],
                                          revision=rev, force_download=True))
        if hashlib.sha256(downloaded.read_bytes()).hexdigest() != e["sha256"]:
            raise RuntimeError("Remote checksum mismatch after upload: " + e["case_id"])
    m = Path(hf_hub_download(repo_id=REPO, repo_type="dataset", filename=META,
                             revision=rev, force_download=True))
    if m.read_bytes() != metadata:
        raise RuntimeError("Uploaded metadata differs from original")
    print(f"V29_SC_ARCHIVE_VERIFIED {len(evidence)} revision={rev}")


if __name__ == "__main__":
    main()
