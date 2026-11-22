"""Reconcile curated research queues against the canonical PRIVATE Mimamsa HF corpus.

Writes an independently versioned, conservative v2.7 source-provenance crosswalk.
This operation NEVER edits originals, machine-crawled corpus, or claims verification.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urlsplit

from huggingface_hub import CommitOperationAdd, HfApi, hf_hub_download

DATASET = "hariomahlawat/mimamsa-corpus"
DEST = "legal_knowledge/crosswalk/v2.7"
OUT = Path("crosswalk_v27_artifacts")


def grab(name: str) -> Path:
    return Path(hf_hub_download(repo_id=DATASET, repo_type="dataset", filename=name))


def rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def norm_url(s: str) -> str:
    # Trim ONLY leading/trailing whitespace. Never silently conflate distinct URLs.
    return (s or "").strip()


def norm_title(s: str) -> str:
    s = (s or "").casefold()
    s = re.sub(r"\b(vs?\.?|versus|the|and|ors|others|petitioner|respondent)\b", " ", s)
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def court_ok(curated: str, row: dict) -> bool:
    c = (curated or "").casefold()
    p = (row.get("raw_path") or "").casefold()
    if "supreme" in c:
        return "/sci/" in p or "/sc/" in p
    if "high court" in c:
        return "/hc/" in p
    if "tribunal" in c:
        return "/aft/" in p
    return False


def best_candidates(case: dict, raw: list[dict]) -> list[dict]:
    base = norm_title(case["case_title"])
    if not base:
        return []
    answers = []
    for x in raw:
        if not court_ok(case["court"], x):
            continue
        title = norm_title(x.get("title", ""))
        if len(title) < 12:
            continue
        ratio = SequenceMatcher(None, base, title).ratio()
        # Suggested-only, never an established source identity.
        if ratio >= 0.80:
            answers.append({
                "candidate_title": x.get("title", ""),
                "candidate_source_url": x.get("source_url", ""),
                "candidate_sha256": x.get("sha256", ""),
                "candidate_score": round(ratio, 4),
            })
    answers.sort(key=lambda z: z["candidate_score"], reverse=True)
    return answers[:2]


def write_csv(name: str, header: list[str], data: list[dict]) -> Path:
    p = OUT / name
    with p.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=header, extrasaction="ignore")
        w.writeheader()
        w.writerows(data)
    return p


def main() -> None:
    api = HfApi()
    info = api.repo_info(repo_id=DATASET, repo_type="dataset")
    if not info.private:
        raise RuntimeError("Refusing to operate on a non-private dataset")
    input_rev = info.sha

    manifest = rows(grab("data/manifest.csv"))
    raw = rows(grab("data/raw_manifest.csv"))
    cases = rows(grab("legal_knowledge/reconciliation/v2.3/04_Case_53_Reconciliation_Queue.csv"))
    kb = rows(grab("legal_knowledge/reconciliation/v2.3/03_KB_658_Reconciliation_Queue.csv"))
    if len(cases) != 53 or len(kb) != 658:
        raise RuntimeError(f"Unexpected input dimensions: {len(cases)} curated cases, {len(kb)} KB records")

    by_url = defaultdict(list)
    for x in manifest:
        url = norm_url(x.get("source_url", ""))
        if url:
            by_url[url].append(("manifest", x))
    for x in raw:
        url = norm_url(x.get("source_url", ""))
        if url:
            by_url[url].append(("raw_manifest", x))

    outcomes = []
    for case in cases:
        url = norm_url(case.get("curated_source_url", ""))
        hits = by_url.get(url, []) if url else []
        same_file = {}
        for origin, x in hits:
            signature = (x.get("sha256") or "", x.get("doc_id") or "")
            if signature not in same_file:
                same_file[signature] = x
        signatures = list(same_file.values())
        candidates = best_candidates(case, raw) if not signatures else []
        state = ("EXACT_SOURCE_URL_CANDIDATE" if len(signatures) == 1 else
                 "AMBIGUOUS_SOURCE_URL" if signatures else
                 "TITLE_CANDIDATES_ONLY" if candidates else
                 "NO_SOURCE_MATCH")
        one = signatures[0] if len(signatures) == 1 else {}
        outcomes.append({
            "curated_case_id": case.get("curated_case_id", ""),
            "case_title": case.get("case_title", ""),
            "court": case.get("court", ""),
            "curated_source_url": url,
            "comparison_status": state,
            "mimamsa_doc_id": one.get("doc_id", ""),
            "mimamsa_sha256_from_manifest": one.get("sha256", ""),
            "matching_raw_source_url": one.get("source_url", ""),
            "candidate_count": len(candidates),
            "candidate_1_title": candidates[0]["candidate_title"] if candidates else "",
            "candidate_1_url": candidates[0]["candidate_source_url"] if candidates else "",
            "candidate_1_score": candidates[0]["candidate_score"] if candidates else "",
            "candidate_2_title": candidates[1]["candidate_title"] if len(candidates)>1 else "",
            "candidate_2_url": candidates[1]["candidate_source_url"] if len(candidates)>1 else "",
            "candidate_2_score": candidates[1]["candidate_score"] if len(candidates)>1 else "",
            "judgment_pdf_byte_match": "NOT_TESTED",
            "legal_holding_verified": "NO",
            "needs_human_review": "YES",
        })

    OUT.mkdir(parents=True, exist_ok=True)
    output_files = [
        write_csv("01_Curated_53_Case_Source_Crosswalk.csv", list(outcomes[0].keys()), outcomes)
    ]
    summary = {
        "title": "Mimamsa legal-source reconciliation v2.7",
        "source_data": "Private Hugging Face dataset",
        "source_dataset": DATASET,
        "source_revision_before_run": input_rev,
        "raw_manifest_rows": len(raw),
        "document_manifest_rows": len(manifest),
        "kb_research_records_in_curated_queue": len(kb),
        "curated_cases_checked": len(cases),
        "case_match_status_counts": dict(Counter(x["comparison_status"] for x in outcomes)),
        "claims_and_case_holding_verified": 0,
        "source_pdf_byte_matches_tested": 0,
        "important_limitations": [
            "The 658-record queue does not carry sufficient individual source locators to verify original propositions.",
            "A matching source URL does not prove that the judgment PDFs are byte-for-byte identical.",
            "Title similarity is a candidate-discovery aid and is never an authoritative link.",
            "Cases not matched against the present manifest are not proven absent from the underlying corpus.",
            "No JAG approval or current-law determination is inferred."
        ]
    }
    report_path = OUT / "02_Reconciliation_Summary.json"
    report_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    output_files.append(report_path)
    readme = OUT / "README.md"
    readme.write_text(
        "# Curated military-law source crosswalk v2.7\n\n"
        "Generated against the current PRIVATE Mimamsa data manifest and raw-source manifest. "
        "Exact URL matches are **candidates for source identity**, not checksums of curated original PDFs. "
        "Fuzzy title suggestions cannot be used to establish a precedent link without human confirmation. "
        "No existing records are overwritten, and legal review status is unchanged.\n",
        encoding="utf-8",
    )
    output_files.append(readme)

    operations = [
        CommitOperationAdd(path_in_repo=f"{DEST}/{p.name}", path_or_fileobj=str(p))
        for p in output_files
    ]
    result = api.create_commit(
        repo_id=DATASET, repo_type="dataset", operations=operations,
        commit_message="Add v2.7 legal research source crosswalk (unverified)",
    )
    commit = result.oid
    print("COMMIT", commit)
    for p in output_files:
        remote = Path(hf_hub_download(repo_id=DATASET, repo_type="dataset",
                                      filename=f"{DEST}/{p.name}", revision=commit, force_download=True))
        if hashlib.sha256(p.read_bytes()).hexdigest() != hashlib.sha256(remote.read_bytes()).hexdigest():
            raise RuntimeError(f"HF read-back checksum mismatch: {p.name}")
    print("VERIFIED", len(output_files), "crosswalk files")
    print("COUNTS", json.dumps(summary["case_match_status_counts"], sort_keys=True))
    print("INPUTS", json.dumps({"manifest":len(manifest),"raw":len(raw),"KB":len(kb),"cases":len(cases)}))


if __name__ == "__main__":
    main()
