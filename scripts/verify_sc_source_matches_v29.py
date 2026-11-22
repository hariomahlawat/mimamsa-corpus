"""Verify pre-existing Mimamsa SC source PDFs for two curated cases, non-destructively.

This check is *not* proof that third-party-source PDF is byte-identical with
the official JUDIS PDF; it verifies the PDF against Mimamsa's original raw manifest
and checks the text of the archived artifact for case identity.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from pathlib import Path
import fitz
from huggingface_hub import HfApi, CommitOperationAdd, hf_hub_download

REPO = "hariomahlawat/mimamsa-corpus"
DEST = "legal_knowledge/crosswalk/v2.9"
CASES = [
    {
        "case_id": "DCLR-SC-1982-001",
        "case_title": "Lt Col Prithi Pal Singh Bedi v Union of India",
        "decision_date": "1982-08-25",
        "title_tokens": ("prithi", "pal", "singh", "bedi"),
        "url_suffix": "/1983_1_393_444_EN.pdf",
        "court_original_url": "https://api.sci.gov.in/jonew/judis/9884.pdf",
    },
    {
        "case_id": "DCLR-SC-1987-R01",
        "case_title": "Ranjit Thakur v Union of India",
        "decision_date": "1987-10-15",
        "title_tokens": ("ranjit", "thakur"),
        "url_suffix": "/1988_1_512_524_EN.pdf",
        "court_original_url": "https://api.sci.gov.in/jonew/judis/8566.pdf",
    },
]


def canonical(path):
    return Path(hf_hub_download(repo_id=REPO, repo_type="dataset",
                                filename=path, force_download=True))


def main():
    api = HfApi()
    inf = api.repo_info(repo_id=REPO, repo_type="dataset")
    if not inf.private:
        raise RuntimeError("Do not operate on public dataset")
    with canonical("data/raw_manifest.csv").open("r", encoding="utf-8-sig", newline="") as fh:
        source_rows = list(csv.DictReader(fh))

    outcomes = []
    snapshots = {}
    for case in CASES:
        candidates = [r for r in source_rows
                      if (r.get("source_url") or "").endswith(case["url_suffix"])]
        if len(candidates) != 1:
            raise RuntimeError(f"Expected exactly one raw source candidate for {case['case_id']}, got {len(candidates)}")
        row = candidates[0]
        p = canonical(row["raw_path"])
        raw = p.read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        if sha != row["sha256"]:
            raise RuntimeError("Existing canonical source PDF checksum discrepancy: " + case["case_id"])
        if not raw.startswith(b"%PDF-"):
            raise RuntimeError("Archived source is not a valid PDF: " + case["case_id"])
        with fitz.open(stream=raw, filetype="pdf") as doc:
            pages = len(doc)
            extracted_text = " ".join(page.get_text("text") for page in doc).casefold()
            extractable_characters = len(extracted_text.strip())
            # Preserve a first-page render for manual case-identity review when
            # the indexed PDF has no usable case-title text.
            image_evidence = (doc[0].get_pixmap(matrix=fitz.Matrix(1.5, 1.5)).tobytes("png")
                              if not all(t in extracted_text for t in case["title_tokens"])
                              else None)
        title_checked = all(t in extracted_text for t in case["title_tokens"])
        year_observed = case["decision_date"][:4] in extracted_text
        if image_evidence is not None:
            snapshots[case["case_id"]] = image_evidence
        # Matching source URL within a dataset doesn't establish official JUDIS byte parity.
        outcomes.append({
            "curated_case_id": case["case_id"],
            "case_title": case["case_title"],
            "decision_date": case["decision_date"],
            "court": "Supreme Court of India",
            "canonical_hf_source_path": row["raw_path"],
            "existing_raw_source_url": row["source_url"],
            "official_judis_url": case["court_original_url"],
            "original_corpus_sha256": sha,
            "downloaded_bytes": len(raw),
            "pages": pages,
            "corpus_raw_manifest_sha256_match": "YES",
            "case_title_verified_in_pdf_text": "YES" if title_checked else "NO",
            "extractable_characters": extractable_characters,
            "visual_review_image": f"{DEST}/evidence_pages/{case['case_id']}_page1.png" if image_evidence else "",
            "year_found_in_pdf_opening": "YES" if year_observed else "NO",
            "official_judis_pdf_byte_match": "NOT_TESTED",
            "holding_comprehensively_verified": "NO",
            "subsequent_treatment_verified": "NO",
            "jag_approved": "NO",
            "status": ("ARCHIVED_CORPUS_PDF_TITLE_AND_SHA_VERIFIED_NOT_OFFICIAL_BYTE_MATCH"
                       if title_checked else "ARCHIVED_CORPUS_PDF_SHA_VERIFIED_CASE_IDENTITY_MANUAL_REVIEW"),
        })
        print(f"V29_CORPUS_MATCH {case['case_id']} pages={pages} sha256={sha} title_in_pdf={title_checked} extractable_characters={extractable_characters}")

    buffer = io.StringIO()
    fields = list(outcomes[0].keys())
    wr = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    wr.writeheader()
    wr.writerows(outcomes)
    csv_text = buffer.getvalue().encode("utf-8")
    report = {
        "schema_name": "Mimamsa curated-case source identity v2.9",
        "source_dataset": REPO, "source_dataset_revision_before_run": inf.sha,
        "case_count": len(outcomes),
        "result": "TWO_ARCHIVED_SOURCE_PDFS_MATCH_RAW_MANIFEST_SHA256; TITLE_MATCH_RECORDED_PER_FILE",
        "limits": [
            "No byte-for-byte comparison with official Supreme Court JUDIS download was possible in GitHub Actions.",
            "An indexed PDF with no matching extractable case title remains identity-pending; see first-page visual evidence.",
            "The source PDFs are copies already in Mimamsa's existing crawled corpus.",
            "An archived PDF/valid SHA does not prove case holdings, subsequent treatment or JAG approval.",
        ]
    }
    files = {
        f"{DEST}/01_Original_Source_Matches.csv": csv_text,
        f"{DEST}/02_Source_Match_Summary.json":
            (json.dumps(report, ensure_ascii=False, indent=2)+"\n").encode("utf-8"),
        f"{DEST}/README.md": (
            "# Canonical corpus original-PDF source identity checks v2.9\n\n"
            "Two existing Supreme Court Reports PDF copies are located through the original Mimamsa raw manifest. "
            "Each archived original's SHA-256 matches its stored manifest and its extracted PDF text contains "
            "a title check whose per-case result is recorded. Unreadable or nonmatching titles remain " 
            "in manual visual review. These are SHA-provenanced source observations, **not official JUDIS byte-match "
            "assertions**, legal holding certifications or JAG approval. "
            "No existing raw files have been altered.\n"
        ).encode("utf-8"),
    }
    for case_id, png in snapshots.items():
        files[f"{DEST}/evidence_pages/{case_id}_page1.png"] = png
    ops = [CommitOperationAdd(path_in_repo=k, path_or_fileobj=io.BytesIO(v)) for k,v in files.items()]
    res = api.create_commit(repo_id=REPO, repo_type="dataset", operations=ops,
                            commit_message="Verify two curated SC cases against canonical raw PDF identity v2.9")
    rev = getattr(res, "oid", None)
    if not rev:
        raise RuntimeError("No revision supplied for verification")
    for path, data in files.items():
        check = canonical(path)
        if check.read_bytes() != data:
            raise RuntimeError("HF readback mismatch: " + path)
    print(f"V29_CORPUS_SOURCE_MATCH_VERIFIED {len(outcomes)} revision={rev}")


if __name__ == "__main__":
    main()
