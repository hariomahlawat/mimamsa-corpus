"""Cycle 16 read-only local corpus reconciliation and evidence packaging."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import unicodedata
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree

import pymupdf

DISPOSITIONS = (
    "EXACT_DUPLICATE", "VERIFIED_ALTERNATE_COPY", "PROBABLE_DUPLICATE",
    "NEW_DOCUMENT", "IMPROVED_SOURCE_COPY", "HISTORICAL_RECOVERY_MATCH",
    "IDENTITY_UNRESOLVED", "RELEVANCE_UNRESOLVED", "NON_RELEVANT",
    "ACCESS_RESTRICTED", "INTEGRITY_FAILURE", "UNSUPPORTED_FORMAT",
)
SUPPORTED = {".pdf", ".docx", ".doc", ".txt", ".rtf", ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".zip", ".7z", ".rar"}
TEXT_EXTENSIONS = {".pdf", ".docx", ".txt"}
HEX64 = re.compile(r"(?i)(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])")
CASE_NUMBER = re.compile(r"(?i)\b(?:CWP|CRWP|CRM-M|RSA|LPA|FAO|CRR|CRA|OA|TA|MA|CA|WP(?:\(C\))?|SLP)[\s./-]*\d+[\s./-]+\d{4}\b")
CITATION = re.compile(r"(?i)\b(?:20\d{2}\s+(?:INSC|PHHC|DHC|AHC|KHC|BHC|KAR)\s+\d+|\(\d{4}\)\s*\d+\s+SCC\s+\d+)\b")
DATE = re.compile(r"\b(?:0?[1-9]|[12]\d|3[01])[./-](?:0?[1-9]|1[0-2])[./-](?:19|20)\d{2}\b")
MILITARY = re.compile(r"(?i)\b(army|air force|navy|armed forces|court[ -]?martial|military|aft|pension|service|discipline|evidence|criminal|ipc|crpc|bns|bnss|human rights)\b")
RESTRICTED_MARKERS = re.compile(r"(?im)\b(?:for official use only|rm-001)\b|^\s*(?:security classification\s*:\s*)?restricted\s*$")
MANDATORY = [
    "LOCAL_INVENTORY.jsonl", "LOCAL_DUPLICATES.csv", "CANONICAL_DUPLICATES.csv",
    "ALTERNATE_COPIES.csv", "NEW_DOCUMENTS.csv", "IMPROVED_SOURCE_COPIES.csv",
    "HISTORICAL_RECOVERY_MATCHES.csv", "OCR_REQUIREMENTS.csv",
    "SUBJECT_CLASSIFICATION.jsonl", "UNRESOLVED_DOCUMENTS.csv",
    "RESTRICTED_AND_QUARANTINED.csv", "CANONICAL_INVENTORY_COVERAGE.json",
    "CANDIDATE_PACKAGE_MANIFEST.json", "PROCESSING_STATE_REGISTER.jsonl",
    "VALIDATION_REPORT.md", "RECONCILIATION_REPORT.md",
    "C16_LOCAL_CORPUS_COMPLETION_REPORT.md",
]


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def retry_call(operation, *, attempts: int = 4, delay: float = 1.0):
    """Retry a complete idempotent metadata operation after transient failures."""
    for number in range(1, attempts + 1):
        try:
            return operation()
        except Exception:
            if number == attempts:
                raise
            time.sleep(delay * (2 ** (number - 1)))


def jdump(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def inventory_id(relative_path: str) -> str:
    norm = unicodedata.normalize("NFC", relative_path.replace("\\", "/")).casefold()
    return "L-" + hashlib.sha256(norm.encode()).hexdigest()[:20]


def subjects_for(relative_path: str) -> list[str]:
    return list(PurePosixPath(relative_path.replace("\\", "/")).parts[:-1])


def normalize_text(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def normalized_text_hash(text: str) -> str | None:
    normalized = normalize_text(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest() if normalized else None


def safe_archive_member(name: str) -> bool:
    name = name.replace("\\", "/")
    path = PurePosixPath(name)
    return not path.is_absolute() and ".." not in path.parts and not re.match(r"^[A-Za-z]:", name)


def choose_disposition(*, restricted: bool, integrity_failure: bool,
                       canonical_exact: bool, text_match: bool,
                       supported: bool = True, relevant: bool | None = True) -> str:
    if restricted:
        return "ACCESS_RESTRICTED"
    if integrity_failure:
        return "INTEGRITY_FAILURE"
    if not supported:
        return "UNSUPPORTED_FORMAT"
    if canonical_exact:
        return "EXACT_DUPLICATE"
    if text_match:
        return "VERIFIED_ALTERNATE_COPY"
    if relevant is False:
        return "NON_RELEVANT"
    if relevant is None:
        return "RELEVANCE_UNRESOLVED"
    return "NEW_DOCUMENT"


def text_primary(rows: list[dict]) -> dict:
    return min(rows, key=lambda row: unicodedata.normalize("NFC", row["relative_path"]).casefold())


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def copy_candidate(source: Path, package: Path, digest: str) -> Path:
    destination = package / "originals" / digest[:2] / f"{digest}{source.suffix.lower()}"
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if file_sha256(destination) != digest:
            raise ValueError(f"candidate collision at {destination}")
    else:
        shutil.copyfile(source, destination)
    return destination


def prune_candidate_originals(package: Path, manifested: set[str]) -> None:
    originals = package / "originals"
    if not originals.exists():
        return
    for path in originals.rglob("*"):
        if path.is_file() and path.relative_to(package).as_posix() not in manifested:
            path.unlink()


def detect_format(path: Path) -> str:
    header = path.read_bytes()[:16]
    if header.startswith(b"%PDF-"):
        return "PDF"
    if header.startswith(b"PK\x03\x04") and path.suffix.lower() == ".docx":
        return "DOCX"
    if header.startswith((b"\xff\xd8\xff", b"\x89PNG", b"II*\x00", b"MM\x00*")):
        return "IMAGE"
    return path.suffix.lower().lstrip(".").upper() or "UNKNOWN"


def extract_pdf(path: Path) -> tuple[list[str], bool]:
    document = pymupdf.open(path)
    encrypted = bool(document.needs_pass)
    if encrypted:
        document.close()
        return [], True
    pages = [page.get_text("text", sort=True) for page in document]
    document.close()
    return pages, False


def extract_docx(path: Path) -> tuple[list[str], bool]:
    with zipfile.ZipFile(path) as archive:
        bad = next((name for name in archive.namelist() if not safe_archive_member(name)), None)
        if bad:
            raise ValueError("unsafe archive member")
        root = ElementTree.fromstring(archive.read("word/document.xml"))
        chunks = [node.text or "" for node in root.iter() if node.tag.endswith("}t")]
        return [" ".join(chunks)], False


def extract_text(path: Path) -> tuple[list[str], bool, str]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        pages, encrypted = extract_pdf(path)
        return pages, encrypted, "pymupdf-native"
    if suffix == ".docx":
        pages, encrypted = extract_docx(path)
        return pages, encrypted, "docx-xml"
    if suffix == ".txt":
        return [path.read_text(encoding="utf-8", errors="replace")], False, "utf8-replace"
    return [], False, "not-extracted"


def candidate_type(path: Path, text: str) -> str:
    value = f"{path.name} {text[:4000]}".casefold()
    for token, kind in (("judgment", "judgment"), ("order", "order"), ("rules", "rules"),
                        ("act", "act"), ("manual", "manual"), ("policy", "policy"),
                        ("notification", "notification")):
        if token in value:
            return kind
    return "legal_reference"


def language_for(text: str) -> str:
    if not text.strip():
        return "und"
    devanagari = sum("\u0900" <= char <= "\u097f" for char in text)
    latin = sum(char.isascii() and char.isalpha() for char in text)
    return "hi" if devanagari > latin else "en"


def ocr_required_pages(extension: str, pages: list[str]) -> list[int]:
    if extension not in {".pdf", ".jpg", ".jpeg", ".png", ".tif", ".tiff"}:
        return []
    return [i for i, value in enumerate(pages, 1) if len(normalize_text(value)) < 80]


def has_restriction_marking(text: str) -> bool:
    return bool(RESTRICTED_MARKERS.search(text[:5000]))


def metadata_signals(text: str) -> dict:
    head = text[:30000]
    return {
        "case_numbers": sorted(set(CASE_NUMBER.findall(head)))[:20],
        "citations": sorted(set(CITATION.findall(head)))[:20],
        "dates": sorted(set(DATE.findall(head)))[:20],
        "verification_status": "AUTOMATED_CANDIDATE_NOT_LEGALLY_VERIFIED",
    }


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows) -> None:
    path.write_text("".join(jdump(row) + "\n" for row in rows), encoding="utf-8")


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def local_control_values(repo: Path) -> tuple[set[str], set[str]]:
    restricted, recovery = set(), set()
    roots = list((repo / "legal_knowledge" / "audit_work").rglob("*"))
    for path in roots:
        if not path.is_file() or path.suffix.lower() not in {".json", ".jsonl", ".csv", ".md", ".txt"}:
            continue
        lower = str(path).casefold()
        if not any(word in lower for word in ("restrict", "marking", "hold", "recovery", "reacquisition")):
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        values = {match.casefold() for match in HEX64.findall(content)}
        (recovery if any(word in lower for word in ("recovery", "reacquisition")) else restricted).update(values)
    return restricted, recovery


def hashes_from_repository_paths(siblings) -> set[str]:
    hashes = set()
    for sibling in siblings or []:
        hashes.update(match.casefold() for match in HEX64.findall(getattr(sibling, "rfilename", "")))
    return hashes


def repository_manifest_hashes(repo: Path) -> set[str]:
    hashes = set()
    for path in (repo / "legal_knowledge").rglob("*"):
        if (not path.is_file() or path.suffix.lower() not in {".json", ".jsonl", ".csv", ".txt", ".md"}
                or path.stat().st_size > 25 * 1024 * 1024):
            continue
        hashes.update(match.casefold() for match in HEX64.findall(path.read_text(encoding="utf-8", errors="ignore")))
    return hashes


def canonical_index(output: Path, repo: Path) -> dict:
    from huggingface_hub import HfApi
    api = HfApi()
    revisions = {}
    hashes, paths = set(), 0
    remote_error = None
    try:
        for label, revision in (("canonical", "main"), ("cycle15", "cycle15-candidates")):
            info = retry_call(lambda revision=revision: api.repo_info(
                "hariomahlawat/mimamsa-corpus", repo_type="dataset", revision=revision))
            revisions[label] = info.sha
            paths += len(info.siblings or [])
            hashes.update(hashes_from_repository_paths(info.siblings))
    except Exception as exc:
        remote_error = f"{type(exc).__name__}: {exc}"
        revisions = {"canonical": "f8a46dfaec55a13f2aaac2fde4139ca0acd5cff9",
                     "cycle15": "217020dbd969e14c2373697f4094fa00557962a6"}
    hashes.update(repository_manifest_hashes(repo))
    record = {"generated_at": utcnow(), "repository": "hariomahlawat/mimamsa-corpus",
              "revisions": revisions, "metadata_paths_examined": paths,
              "distinct_sha256_values": len(hashes), "sha256": sorted(hashes),
              "method": ("Hugging Face repository paths containing full SHA-256 identifiers plus Git-tracked manifests; no document bodies downloaded"
                         if paths else "Git-tracked canonical manifests and audit records; live Hugging Face revisions pinned but path enumeration unavailable"),
              "remote_error": remote_error,
              "limitations": ["LFS object hashes not embedded in repository paths are not represented in this bounded index.",
                              "Git-tracked corpus manifests and audit records supplement the path index; a hash match proves byte knowledge but not legal identity."]}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, indent=2), encoding="utf-8")
    return record


def inventory(source: Path, output: Path, repo: Path, limit: int | None = None) -> list[dict]:
    output.mkdir(parents=True, exist_ok=True)
    derivatives = output / "derivatives"
    derivatives.mkdir(exist_ok=True)
    checkpoint_path = output / "inventory-checkpoint.jsonl"
    previous = {row["relative_path"]: row for row in load_jsonl(checkpoint_path)}
    restricted_hashes, recovery_hashes = local_control_values(repo)
    paths = sorted((path for path in source.rglob("*") if path.is_file()), key=lambda p: str(p).casefold())
    if limit:
        paths = paths[:limit]
    rows = []
    for number, path in enumerate(paths, 1):
        relative = path.relative_to(source).as_posix()
        stat = path.stat()
        cached = previous.get(relative)
        if cached and cached.get("size_bytes") == stat.st_size and cached.get("mtime_ns") == stat.st_mtime_ns:
            if cached.get("classification_version") != 2:
                derivative = cached.get("derivative_relative_path")
                cached_text = (output / derivative).read_text(encoding="utf-8", errors="ignore") if derivative and (output / derivative).exists() else ""
                cached["restricted"] = cached.get("sha256", "").casefold() in restricted_hashes or has_restriction_marking(cached_text)
                cached["classification_version"] = 2
            rows.append(cached)
            continue
        digest, pages, encrypted, error, method = "", [], False, None, "not-extracted"
        try:
            digest = file_sha256(path)
            if path.suffix.lower() in TEXT_EXTENSIONS:
                pages, encrypted, method = extract_text(path)
        except Exception as exc:  # evidence record, never silent
            error = f"{type(exc).__name__}: {exc}"[:500]
        text = "\n\n".join(pages)
        text_hash = normalized_text_hash(text)
        derivative_path = None
        derivative_hash = None
        if text:
            derivative_path = derivatives / f"{digest}.txt"
            derivative_path.write_text("".join(f"\n\n--- PHYSICAL PAGE {i} ---\n{text}" for i, text in enumerate(pages, 1)), encoding="utf-8")
            derivative_hash = file_sha256(derivative_path)
        sparse = ocr_required_pages(path.suffix.lower(), pages)
        relevant = bool(MILITARY.search(" ".join(subjects_for(relative)) + " " + text[:20000])) if text else None
        supported = path.suffix.lower() in SUPPORTED
        restricted = digest.casefold() in restricted_hashes or has_restriction_marking(text)
        row = {
            "inventory_id": inventory_id(relative), "relative_path": relative, "filename": path.name,
            "extension": path.suffix.lower(), "detected_format": detect_format(path),
            "size_bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns, "sha256": digest,
            "page_count": len(pages) or None, "language": language_for(text),
            "text_available": bool(text.strip()), "normalized_text_sha256": text_hash,
            "derivative_relative_path": str(derivative_path.relative_to(output)).replace("\\", "/") if derivative_path else None,
            "derivative_sha256": derivative_hash, "extraction_method": method,
            "encrypted": encrypted, "parsing_error": error, "candidate_document_type": candidate_type(path, text),
            "original_folder_classification": subjects_for(relative), "processing_status": "ERROR" if error else "INVENTORIED",
            "ocr_required_pages": sparse, "relevance": relevant, "restricted": restricted,
            "historical_recovery_hash_match": digest.casefold() in recovery_hashes, "classification_version": 2,
            "metadata_candidate": metadata_signals(text), "source_provenance": "owner local collection; external source unverified",
        }
        rows.append(row)
        if number % 25 == 0:
            write_jsonl(checkpoint_path, rows + [previous[p] for p in previous.keys() - {r["relative_path"] for r in rows}])
    write_jsonl(checkpoint_path, rows)
    return rows


def reconcile(rows: list[dict], canonical: dict, output: Path, source: Path) -> list[dict]:
    canonical_hashes = set(canonical.get("sha256", []))
    by_binary, by_text = defaultdict(list), defaultdict(list)
    for row in rows:
        if row["sha256"]:
            by_binary[row["sha256"]].append(row)
        if row["normalized_text_sha256"]:
            by_text[row["normalized_text_sha256"]].append(row)
    canonical_text = set(canonical.get("normalized_text_sha256", []))
    text_primaries = {digest: text_primary(group)["inventory_id"] for digest, group in by_text.items() if len(group) > 1}
    for row in rows:
        internal_text_match = len(by_text.get(row["normalized_text_sha256"], [])) > 1 if row["normalized_text_sha256"] else False
        row["canonical_exact"] = row["sha256"].casefold() in canonical_hashes
        row["canonical_text_match"] = row["normalized_text_sha256"] in canonical_text
        row["internal_binary_group_size"] = len(by_binary.get(row["sha256"], []))
        row["internal_text_group_size"] = len(by_text.get(row["normalized_text_sha256"], [])) if row["normalized_text_sha256"] else 0
        row["disposition"] = choose_disposition(
            restricted=row["restricted"], integrity_failure=bool(row["parsing_error"] or row["encrypted"]),
            canonical_exact=row["canonical_exact"], text_match=row["canonical_text_match"],
            supported=row["extension"] in SUPPORTED, relevant=row["relevance"])
        if row["historical_recovery_hash_match"] and row["disposition"] not in {"ACCESS_RESTRICTED", "INTEGRITY_FAILURE"}:
            row["secondary_flags"] = ["HISTORICAL_RECOVERY_HASH_MATCH_REQUIRES_IDENTITY_REVIEW"]
        else:
            row["secondary_flags"] = []
        if internal_text_match and row["internal_binary_group_size"] == 1:
            row["secondary_flags"].append("INTERNAL_NORMALIZED_TEXT_IDENTITY")
            if (row["disposition"] == "NEW_DOCUMENT" and
                    text_primaries.get(row["normalized_text_sha256"]) != row["inventory_id"]):
                row["disposition"] = "VERIFIED_ALTERNATE_COPY"
    return rows


def package_and_reports(rows: list[dict], output: Path, source: Path, canonical: dict) -> dict:
    reports, package = output / "reports", output / "candidate-package"
    reports.mkdir(exist_ok=True)
    package.mkdir(exist_ok=True)
    write_jsonl(reports / "LOCAL_INVENTORY.jsonl", rows)
    write_jsonl(reports / "PROCESSING_STATE_REGISTER.jsonl", ({"inventory_id": r["inventory_id"], "status": r["processing_status"], "disposition": r["disposition"]} for r in rows))
    write_jsonl(reports / "SUBJECT_CLASSIFICATION.jsonl", ({"inventory_id": r["inventory_id"], "subjects": r["original_folder_classification"], "basis": "source folder provenance; not an established legal fact"} for r in rows))
    common = ["inventory_id", "relative_path", "sha256", "normalized_text_sha256", "disposition", "secondary_flags"]
    def emit(name, predicate):
        selected = []
        for row in rows:
            if predicate(row):
                item = dict(row)
                item["secondary_flags"] = ";".join(item["secondary_flags"])
                selected.append(item)
        write_csv(reports / name, selected, common)
    emit("LOCAL_DUPLICATES.csv", lambda r: r["internal_binary_group_size"] > 1 or r["internal_text_group_size"] > 1)
    emit("CANONICAL_DUPLICATES.csv", lambda r: r["disposition"] == "EXACT_DUPLICATE")
    emit("ALTERNATE_COPIES.csv", lambda r: r["disposition"] in {"VERIFIED_ALTERNATE_COPY", "PROBABLE_DUPLICATE"})
    emit("NEW_DOCUMENTS.csv", lambda r: r["disposition"] == "NEW_DOCUMENT")
    emit("IMPROVED_SOURCE_COPIES.csv", lambda r: r["disposition"] == "IMPROVED_SOURCE_COPY")
    emit("HISTORICAL_RECOVERY_MATCHES.csv", lambda r: r["historical_recovery_hash_match"])
    emit("OCR_REQUIREMENTS.csv", lambda r: bool(r["ocr_required_pages"]))
    emit("UNRESOLVED_DOCUMENTS.csv", lambda r: r["disposition"] in {"IDENTITY_UNRESOLVED", "RELEVANCE_UNRESOLVED", "PROBABLE_DUPLICATE"})
    emit("RESTRICTED_AND_QUARANTINED.csv", lambda r: r["disposition"] in {"ACCESS_RESTRICTED", "INTEGRITY_FAILURE", "UNSUPPORTED_FORMAT"})
    unique_candidates = {}
    for row in rows:
        if row["disposition"] in {"NEW_DOCUMENT", "IMPROVED_SOURCE_COPY"} and row["sha256"] not in unique_candidates:
            candidate = copy_candidate(source / Path(row["relative_path"]), package, row["sha256"])
            unique_candidates[row["sha256"]] = str(candidate.relative_to(package)).replace("\\", "/")
    prune_candidate_originals(package, set(unique_candidates.values()))
    counts = Counter(r["disposition"] for r in rows)
    duplicate_savings = sum(r["size_bytes"] for r in rows if r["disposition"] == "VERIFIED_ALTERNATE_COPY" and "INTERNAL_NORMALIZED_TEXT_IDENTITY" in r["secondary_flags"])
    coverage = {"generated_at": utcnow(), "canonical_repository": canonical.get("repository"),
                "revisions": canonical.get("revisions"), "metadata_paths_examined": canonical.get("metadata_paths_examined"),
                "distinct_canonical_sha256_values": canonical.get("distinct_sha256_values"),
                "comparison_method": canonical.get("method"),
                "remote_error": canonical.get("remote_error"),
                "limitations": canonical.get("limitations", []) + ["Canonical text derivatives were not downloaded; normalized-text matches are limited to locally available overlays.", "Legal-document and near-duplicate identity remain review candidates unless exact evidence is present.", "Legacy paths without trusted SHA-256 cannot support exact binary absence claims."]}
    (reports / "CANONICAL_INVENTORY_COVERAGE.json").write_text(json.dumps(coverage, indent=2), encoding="utf-8")
    manifest = {"package_version": "c16-local-candidate-v1", "generated_at": utcnow(), "application_eligible": False,
                "active_ingestion_authorized": False, "source_root": str(source), "source_files": len(rows),
                "unique_candidate_originals": len(unique_candidates), "candidate_originals": unique_candidates,
                "disposition_counts": dict(sorted(counts.items())), "canonical_revisions": canonical.get("revisions")}
    (reports / "CANDIDATE_PACKAGE_MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    summary = {"total_files": len(rows), "total_bytes": sum(r["size_bytes"] for r in rows),
               "pdf_files": sum(r["extension"] == ".pdf" for r in rows), "non_pdf_files": sum(r["extension"] != ".pdf" for r in rows),
               "unique_binary_hashes": len({r["sha256"] for r in rows if r["sha256"]}),
               "internal_duplicate_files": sum(r["internal_binary_group_size"] > 1 or r["internal_text_group_size"] > 1 for r in rows),
               "internal_binary_duplicate_files": sum(r["internal_binary_group_size"] > 1 for r in rows),
               "internal_normalized_text_duplicate_files": sum(r["internal_text_group_size"] > 1 for r in rows),
               "confirmed_canonical_duplicates": counts["EXACT_DUPLICATE"], "alternate_source_copies": counts["VERIFIED_ALTERNATE_COPY"],
               "improved_source_copies": counts["IMPROVED_SOURCE_COPY"], "new_document_candidates": counts["NEW_DOCUMENT"],
               "historical_recovery_hash_matches": sum(r["historical_recovery_hash_match"] for r in rows),
               "documents_requiring_ocr": sum(bool(r["ocr_required_pages"]) for r in rows),
               "successfully_processed": sum(not r["parsing_error"] for r in rows),
               "unresolved": sum(counts[d] for d in ("IDENTITY_UNRESOLVED", "RELEVANCE_UNRESOLVED", "PROBABLE_DUPLICATE")),
               "restricted_or_quarantined": sum(counts[d] for d in ("ACCESS_RESTRICTED", "INTEGRITY_FAILURE", "UNSUPPORTED_FORMAT")),
               "net_proposed_addition": len(unique_candidates), "deduplication_storage_savings_bytes": duplicate_savings}
    table = "\n".join(f"- {key.replace('_', ' ')}: {value}" for key, value in summary.items())
    (reports / "RECONCILIATION_REPORT.md").write_text(f"# Cycle 16 reconciliation report\n\n{table}\n\nAutomated identity never establishes legal authority. See coverage limitations and unresolved queues.\n", encoding="utf-8")
    (reports / "C16_LOCAL_CORPUS_COMPLETION_REPORT.md").write_text(f"# Cycle 16 local corpus completion report\n\n{table}\n\nStatus: candidate preparation only; no ingestion, upload, approval, or promotion was performed.\n", encoding="utf-8")
    return summary


def validate(output: Path) -> list[str]:
    reports = output / "reports"
    errors = [f"missing {name}" for name in MANDATORY if not (reports / name).exists() and name != "VALIDATION_REPORT.md"]
    rows = load_jsonl(reports / "LOCAL_INVENTORY.jsonl")
    if len({row.get("inventory_id") for row in rows}) != len(rows):
        errors.append("inventory IDs are not unique")
    if any(row.get("disposition") not in DISPOSITIONS for row in rows):
        errors.append("invalid disposition")
    manifest_path = reports / "CANDIDATE_PACKAGE_MANIFEST.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for digest, relative in manifest.get("candidate_originals", {}).items():
            path = output / "candidate-package" / relative
            if not path.exists() or file_sha256(path) != digest:
                errors.append(f"candidate hash mismatch: {relative}")
        actual = {path.relative_to(output / "candidate-package").as_posix() for path in (output / "candidate-package" / "originals").rglob("*") if path.is_file()}
        expected = set(manifest.get("candidate_originals", {}).values())
        if actual != expected:
            errors.append("candidate originals do not exactly match manifest")
    status = "PASS" if not errors else "FAIL"
    report = f"# Cycle 16 validation report\n\n- status: {status}\n- inventory records: {len(rows)}\n- mandatory artifacts: {len(MANDATORY)}\n- errors: {len(errors)}\n" + "".join(f"  - {error}\n" for error in errors)
    (reports / "VALIDATION_REPORT.md").write_text(report, encoding="utf-8")
    return errors


def run(args) -> int:
    source, output, repo = Path(args.source).resolve(), Path(args.output).resolve(), Path(args.repo).resolve()
    canonical_path = output / "canonical-index.json"
    if args.refresh_canonical or not canonical_path.exists():
        canonical = canonical_index(canonical_path, repo)
    else:
        canonical = json.loads(canonical_path.read_text(encoding="utf-8"))
    rows = inventory(source, output, repo, args.limit)
    rows = reconcile(rows, canonical, output, source)
    package_and_reports(rows, output, source, canonical)
    errors = validate(output)
    return 1 if errors else 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--repo", default=Path(__file__).resolve().parents[3])
    parser.add_argument("--limit", type=int)
    parser.add_argument("--refresh-canonical", action="store_true")
    args = parser.parse_args(argv)
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
