"""Rebuild the package-v5 skipped records from receipt-verified PDF originals."""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import quote
from urllib.request import Request, urlopen

import pymupdf

CARRIER_LAYOUTS = {110: "side-notes", 111: "statutory-schedule-table"}
VISIBLE_GRAY_MASK = bytes(int(level < 210) for level in range(256))

DATASET = "hariomahlawat/mimamsa-corpus"
MARKINGS = re.compile(
    r"\b(?:top secret|confidential|classified|restricted|secret|sealed|in camera|"
    r"not for (?:publication|circulation)|for official use only)\b", re.I)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def json_rows(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def receipts(collection, consolidation, targets):
    result = defaultdict(list)
    independent = defaultdict(dict)
    for row in json_rows(collection / "independent.jsonl"):
        if row["status"] == "verified" and row["expected"] == row["actual"]:
            parent, file = row["path"].rsplit("/", 1)
            independent[(parent.rsplit("/", 1)[1], row["revision"])][file] = row
    with (collection / "PHHC_T1_RECOVERY_534_EXECUTION.csv").open(newline="") as stream:
        for row in csv.DictReader(stream):
            doc_id = row["doc_id"]
            if doc_id not in targets:
                continue
            for (digest, revision), files in independent.items():
                if digest == row["expected_sha256"] and files.keys() >= {"original.pdf", "text.txt"}:
                    result[doc_id].append(pair(revision, {f["path"]: f["actual"] for f in files.values()},
                                               digest, row["derived_text_sha256"], "independent.jsonl"))
    for row in json_rows(collection / "C14_EXTENDED_JUDICIAL.jsonl"):
        if row["doc_id"] in targets and row["status"] == "uploaded-verified" and row["hf"]["verified"]:
            digest = row["expected_sha256"]
            prefix = f"legal_knowledge/preservation/c14_tier1_extension/v1/{digest[:2]}/{digest}"
            files = {f"{prefix}/original.pdf": digest, f"{prefix}/text.txt": row["derived_sha256"]}
            result[row["doc_id"]].append(pair(row["hf"]["revision"], files, digest,
                                              row["derived_sha256"], "C14_EXTENDED_JUDICIAL.jsonl",
                                              source_url=row["source_url"]))
    journal_path = consolidation / "judicial-retry/extended.jsonl"
    if journal_path.is_file():
        journal = json_rows(journal_path)
        verified = {r["revision"] for r in journal if r.get("verified")}
        attempted = {item[2]: item[0] for batch in journal for item in batch.get("result", [])
                     if item[1] == "verified-local"}
        for batch in journal:
            if batch.get("revision") not in verified:
                continue
            files = batch.get("files", {})
            for path, digest in files.items():
                if path.endswith("/text.txt"):
                    original = path.split("/")[-2]
                    doc_id = attempted.get(original)
                    if doc_id in targets:
                        result[doc_id].append(pair(batch["revision"], files, original, digest,
                                                   "judicial-retry/extended.jsonl"))
    summary = json.loads((collection / "C14_EXTENDED_EXECUTION.json").read_bytes())
    sources = [("C14_EXTENDED_EXECUTION.json", r) for r in summary["official_uploads"]]
    sources.extend((str(p.relative_to(consolidation)), json.loads(p.read_bytes()))
                   for p in sorted(consolidation.glob("staged-upload*/official-upload.json")))
    for receipt_name, receipt in sources:
        if not receipt["verified"]:
            continue
        for row in receipt["entries"]:
            doc_id = row.get("doc_id") or row["id"]
            if doc_id not in targets or row["status"] != "queued-for-upload":
                continue
            digest = row["sha256"]
            text_path, = [p for p in receipt["files"] if p.endswith(f"/{digest}/text.txt")]
            result[doc_id].append(pair(receipt["revision"], receipt["files"], digest,
                                       receipt["files"][text_path], receipt_name,
                                       scope=row.get("derivative_physical_pages"), source_url=row.get("url")))
    return result


def pair(revision, files, pdf_hash, text_hash, receipt, scope=None, source_url=None):
    paths = {name: next(path for path, digest in files.items()
                        if path.endswith(f"/{pdf_hash}/{name}") and digest == expected)
             for name, expected in (("original.pdf", pdf_hash), ("text.txt", text_hash))}
    return dict(hf_revision=revision, original_sha256=pdf_hash, legacy_derivative_sha256=text_hash,
                hf_paths=paths, receipt=receipt, documentary_physical_pages=scope, source_url=source_url)


def file_pair(folders, pdf_hash, text_hash):
    for folder in folders:
        pdf = folder / (pdf_hash + ".pdf")
        txt = folder / (pdf_hash + ".txt")
        if pdf.is_file() and txt.is_file():
            raw, legacy = pdf.read_bytes(), txt.read_bytes()
            if sha(raw) == pdf_hash and sha(legacy) == text_hash:
                return raw, legacy, str(folder)
    return None


def pinned_pair(provenance, caches):
    revision = provenance["hf_revision"]
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Hugging Face input must use a full commit hash")
    paths = provenance["hf_paths"]
    expected = [provenance["original_sha256"], provenance["legacy_derivative_sha256"]]
    for cache in caches:
        snapshot = cache / "datasets--hariomahlawat--mimamsa-corpus" / "snapshots" / revision
        files = [snapshot / paths[name] for name in ("original.pdf", "text.txt")]
        if all(f.is_file() for f in files):
            raw, legacy = (f.read_bytes() for f in files)
            if [sha(raw), sha(legacy)] == expected:
                return raw, legacy, str(snapshot)
    token = os.environ.get("HF_TOKEN")
    if token is None:
        raise ValueError("Receipt-verified pair unavailable locally and HF_TOKEN is unset")
    contents = []
    for name, digest in zip(("original.pdf", "text.txt"), expected, strict=True):
        url = f"https://huggingface.co/datasets/{DATASET}/resolve/{revision}/{quote(paths[name])}"
        request = Request(url, method="GET")
        request.add_unredirected_header("Authorization", f"Bearer {token}")
        with urlopen(request, timeout=60) as response:
            data = response.read(80_000_001)
        if len(data) > 80_000_000 or sha(data) != digest:
            raise ValueError("Pinned read exceeded size limit or failed receipt verification")
        contents.append(data)
    return *contents, "authenticated-pinned-hf-get"


def count_words(text):
    return len(re.findall(r"\b[^\W_]+\b", text))


def line_layout(page, text):
    horizontal = vertical = 0
    for path in page.get_drawings():
        for item in path["items"]:
            if item[0] == "re" and item[1].width > 20 and item[1].height > 6:
                horizontal += 2
                vertical += 2
            elif item[0] == "l":
                first, last = item[1:]
                if abs(first.y - last.y) <= 1 and abs(first.x - last.x) >= 25:
                    horizontal += 1
                if abs(first.x - last.x) <= 1 and abs(first.y - last.y) >= 12:
                    vertical += 1
    spaced_rows = sum(bool(re.search(r"\S {4,}\S", line)) for line in text.splitlines())
    multi_column_rows = sum(bool(re.search(r"\w{3,} {10,}\w{3,}", line)) for line in text.splitlines())
    return dict(grid_horizontal_rules=horizontal, grid_vertical_rules=vertical,
                wide_gap_rows=spaced_rows, likely_multi_column_rows=multi_column_rows,
                table_or_columns_possible=(horizontal >= 4 and vertical >= 4) or multi_column_rows >= 6)


def text_coverage(page):
    page_area = page.rect.width * page.rect.height
    image_area = max((pymupdf.Rect(image["bbox"]).get_area()
                      for image in page.get_image_info()), default=0)
    return round(min(image_area / page_area, 1), 4)


def rendered(page, dpi):
    if page.rect.width * page.rect.height * (dpi / 72) ** 2 > 16_000_000:
        raise ValueError("Physical page exceeds the extraction render limit")
    return page.get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY, alpha=False)


def ocr(page):
    png = rendered(page, 200).tobytes("png")
    environment = {name: os.environ[name] for name in ("PATH", "TESSDATA_PREFIX", "LANG", "LC_ALL")
                   if name in os.environ}
    environment["OMP_THREAD_LIMIT"] = "1"
    result = subprocess.run(["tesseract", "stdin", "stdout", "-l", "eng", "--psm", "3", "tsv"],
                            input=png, capture_output=True, timeout=90, check=True, env=environment)
    lines = defaultdict(list)
    confidences = []
    for row in csv.DictReader(result.stdout.decode().splitlines(), delimiter="\t", quoting=csv.QUOTE_NONE):
        if row["level"] == "5" and row["text"].strip():
            group = tuple(row[key] for key in ("block_num", "par_num", "line_num"))
            lines[group].append(row["text"])
            confidences.append(float(row["conf"]))
    text = "\n".join(" ".join(words) for words in lines.values())
    return text, round(sum(confidences) / len(confidences), 2) if confidences else None


def physical_pages(source, scope):
    for page in source:
        number = page.number + 1
        data = dict(physical_page=number, pdf_page_label=page.get_label(), rotation=page.rotation)
        if number not in scope:
            yield dict(data, method="out-of-scope", state="out-of-scope", text=None,
                       text_sha256=None, quality_risks=[])
            continue
        native = page.get_text(sort=True).replace("\f", "\n").strip()
        image_fraction = text_coverage(page)
        layout = line_layout(page, native)
        risks = []
        confidence = None
        visible = None
        nonwhite = None
        method = "pdf-text"
        state = "text-present"
        text = native
        invalid_chars = native.count("\ufffd") + len(re.findall(r"[\ue000-\uf8ff]", native))
        nonspace = sum(not char.isspace() for char in native)
        alphabetic_fraction = sum(char.isalpha() for char in native) / max(nonspace, 1)
        corrupted = bool(invalid_chars) or (nonspace >= 65 and alphabetic_fraction < 0.68)
        image_backed_layer = image_fraction >= 0.65
        if corrupted:
            risks.append("native_encoding_review")
        if count_words(native) < 8 or corrupted or image_backed_layer:
            raster = rendered(page, 144)
            pixels = raster.samples
            visible = pixels.translate(VISIBLE_GRAY_MASK).count(b"\x01")
            nonwhite = len(pixels) - pixels.count(255)
            if not native and nonwhite == 0:
                method, state = "blank-render", "visually-blank-at-144-dpi"
            else:
                try:
                    scan, confidence = ocr(page)
                except (ValueError, subprocess.SubprocessError, OSError):
                    scan = ""
                    risks.append("ocr_execution_failed")
                if scan and (not native or count_words(scan) > count_words(native) or corrupted or image_backed_layer):
                    text, method = scan, "tesseract-ocr"
                    risks.append("ocr_transcription_review")
                    if confidence is not None and confidence < 80:
                        risks.append("low_ocr_confidence")
                if not text or (corrupted and method == "pdf-text"):
                    text = ""
                    method, state = "ocr-no-text", "visual-review-required"
                    risks.append("visible_content_without_text")
                elif count_words(text) < 8:
                    risks.append("sparse_page_text")
                if MARKINGS.search(scan) and not MARKINGS.search(text):
                    risks.append("handling_language_review")
        if layout["table_or_columns_possible"]:
            risks.append("table_or_column_reading_order_review")
        if image_fraction >= 0.30:
            risks.append("substantial_image_content")
        if MARKINGS.search(native) or MARKINGS.search(text):
            if "handling_language_review" not in risks:
                risks.append("handling_language_review")
        yield dict(data, method=method, state=state, text=text, text_sha256=sha(text.encode()),
                   native_words=count_words(native), native_text_sha256=sha(native.encode()),
                   native_alphabetic_fraction=round(alphabetic_fraction, 4),
                   words=count_words(text), largest_image_page_fraction=image_fraction,
                   ocr_mean_word_confidence=confidence, rendered_pixels_below_gray_210=visible,
                   rendered_nonwhite_pixels=nonwhite, layout=layout, quality_risks=risks)


def repair_record(skip, proof, blocked, folders, caches, out):
    doc_id = skip["doc_id"]
    row = dict(doc_id=doc_id, prior_status=skip["status"], active_import_allowed=False)
    try:
        identities = {(p["original_sha256"], p["legacy_derivative_sha256"], p["hf_revision"],
                       tuple(p["documentary_physical_pages"] or ())) for p in proof}
        if len(identities) != 1:
            raise ValueError(f"Expected one verified source pair, found {len(identities)}")
        provenance = sorted(proof, key=lambda p: ("/v2/" not in p["hf_paths"]["original.pdf"],
                                                    p["hf_paths"]["original.pdf"]))[0].copy()
        provenance["equivalent_receipts"] = proof
        row["provenance"] = provenance
        pdf_hash, text_hash = provenance["original_sha256"], provenance["legacy_derivative_sha256"]
        identities = [doc_id, pdf_hash, text_hash, *provenance["hf_paths"].values()]
        if blocked.intersection(x.casefold() for x in identities):
            return dict(row, status="restriction-hold")
        raw, legacy, location = file_pair(folders, pdf_hash, text_hash) or pinned_pair(provenance, caches)
        row["verified_input_location"] = location
        with pymupdf.open(stream=raw, filetype="pdf") as source:
            if source.is_repaired or source.needs_pass or not raw.rstrip().endswith(b"%%EOF"):
                return dict(row, status="source-integrity-hold")
            if len(source) != skip.get("physical_pages", len(source)) or not len(source):
                return dict(row, status="physical-page-count-mismatch")
            physical = set(range(1, len(source) + 1))
            scope = set(provenance["documentary_physical_pages"] or physical)
            if not scope <= physical:
                return dict(row, status="receipt-page-scope-invalid")
            pages = list(physical_pages(source, scope))
        if doc_id == "CA01-ACT19-1955-CARRIER":
            for page in pages:
                known_layout = CARRIER_LAYOUTS.get(page["physical_page"])
                if known_layout and page["text"] is not None:
                    page["layout"]["documentary_layout"] = known_layout
                    page["layout"]["table_or_columns_possible"] = True
                    risk = "table_or_column_reading_order_review"
                    if risk not in page["quality_risks"]:
                        page["quality_risks"].append(risk)
        derivative = "\n\f\n".join(p["text"] or "" for p in pages).encode()
        derivative_sha = sha(derivative)
        if derivative_sha in blocked:
            return dict(row, status="restriction-hold")
        filename = f"documents/{doc_id}"
        methods = Counter(p["method"] for p in pages)
        risks = Counter(risk for p in pages for risk in p["quality_risks"])
        status = "mapped-scope-limited" if scope != physical else "mapped"
        if risks["visible_content_without_text"] or risks["ocr_execution_failed"]:
            status = "mapped-with-open-page-review" if scope == physical else "mapped-scope-limited-with-open-page-review"
        row.update(status=status, page_count=len(pages), in_scope_page_count=len(scope),
                   legacy_segment_count=len(legacy.decode().split("\n\f\n")),
                   derivative_sha256=derivative_sha, method_counts=dict(methods), quality_risk_counts=dict(risks),
                   pages_file=filename + ".json", derivative_file=filename + ".txt",
                   publication_review_required=True)
        (out / row["derivative_file"]).write_bytes(derivative)
        data = dict(row, schema="mimamsa-c15-physical-page-repair-v1", pages=pages,
                    anchor_unit="one-based physical page and zero-based Unicode offsets")
        raw_record = (json.dumps(data, ensure_ascii=False, sort_keys=True) + "\n").encode()
        (out / row["pages_file"]).write_bytes(raw_record)
        row["pages_file_sha256"] = sha(raw_record)
        return row
    except (OSError, ValueError, RuntimeError) as exc:
        return dict(row, status="blocked", error_type=type(exc).__name__,
                    reason=str(exc) if isinstance(exc, ValueError) else None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collection", type=Path, default=Path("/workspace/c14-collection"))
    parser.add_argument("--consolidation", type=Path, default=Path("/workspace/c14-consolidation"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    collection, consolidation = args.collection.resolve(), args.consolidation.resolve()
    manifest = (consolidation / "package-v5/manifest.json").read_bytes()
    skips = [r for r in json.loads(manifest)["skips"]
             if r["status"] in {"local_pair_missing", "unbound_or_partial_page_map"}]
    targets = {r["doc_id"] for r in skips}
    if len(targets) != len(skips):
        raise ValueError("Duplicated package-v5 skipped identity")
    if any(not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*", doc_id) for doc_id in targets):
        raise ValueError("Invalid package-v5 skipped identity")
    proofs = receipts(collection, consolidation, targets)
    register = (collection / "register.json").read_bytes()
    if sha(register) != json.loads(manifest)["restriction_register_sha256"]:
        raise ValueError("Restriction register differs from the pinned candidate manifest")
    blocked = {value.casefold() for item in json.loads(register)["items"]
               for value in (item["doc_id"], item["source_sha256"], *item.get("derived_sha256", []),
                             *item.get("hosted_paths", [])) if value}
    folders = [collection / name for name in ("extended-files", "batch-files", "official-files", "pilot")]
    folders.extend([consolidation / "judicial-retry/extended-files",
                    *sorted(consolidation.glob("staged-upload*/official-files"))])
    caches = [collection / "verify-cache", collection / "cache", Path("/tmp/c14-independent-hf"),
              *sorted(consolidation.glob("*/verify-cache"))]
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False, mode=0o700)
    (out / "documents").mkdir(mode=0o700)
    with ProcessPoolExecutor(args.workers) as executor:
        futures = [executor.submit(repair_record, r, proofs[r["doc_id"]], blocked, folders, caches, out)
                   for r in skips]
        records = [future.result() for future in futures]
    write_summary(out, records, manifest, register)


def write_summary(out, records, manifest, register):
    register_path = out / "repair-register.jsonl"
    register_path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in records))
    methods = Counter()
    risks = Counter()
    for row in records:
        methods.update(row.get("method_counts", {}))
        risks.update(row.get("quality_risk_counts", {}))
    tesseract = subprocess.run(["tesseract", "--version"], capture_output=True, check=True, text=True)
    language_config = subprocess.run(["tesseract", "--list-langs"], capture_output=True,
                                     check=True, text=True).stdout
    tessdata = re.search(r'in "([^"]+)"', language_config.partition("\n")[0])
    english = Path(tessdata.group(1)) / "eng.traineddata" if tessdata else None
    summary = dict(schema="mimamsa-c15-physical-page-repair-run-v1",
                   source_manifest_sha256=sha(manifest), restriction_register_sha256=sha(register),
                   register_sha256=sha(register_path.read_bytes()), active_import_allowed=False,
                   input_count=len(records), prior_status_counts=dict(Counter(r["prior_status"] for r in records)),
                   status_counts=dict(Counter(r["status"] for r in records)),
                   method_counts=dict(methods), quality_risk_counts=dict(risks),
                   pymupdf_version=pymupdf.VersionBind, tesseract_version=tesseract.stdout.splitlines()[0],
                   tesseract_english_model_sha256=sha(english.read_bytes()) if english and english.is_file() else None,
                   ocr_render_dpi=200, blank_check_render_dpi=144)
    (out / "manifest.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
