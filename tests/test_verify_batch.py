"""verify_batch.py regression tests (offline, temporary repo).

Defect (PR #23 review): India Code watermarks PDFs when serving them, so the ORIGINAL-bundle listing MD5/size are not
expectations for the downloaded bytes. A valid watermarked download must not FAIL; its served SHA-256 is recorded and
its identity must still be page-image checked. Archive.org pinned bytes must still be rejected on any change, and a
served-SHA-256 pin (set after the first approved fetch) must reject later unexpected changes."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "tools" / "acquisition" / "verify_batch.py"


def make_repo(tmp_path, source, doc, raw_bytes):
    cfg = {"sources": {source: {"documents": [doc]}}}
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "sources.yaml").write_text(yaml.safe_dump(cfg), encoding="utf-8")
    raw = tmp_path / "data" / "raw" / "x" / "f.pdf"
    raw.parent.mkdir(parents=True)
    raw.write_bytes(raw_bytes)
    meta = tmp_path / "data" / "meta" / f"{doc['doc_id']}.json"
    meta.parent.mkdir(parents=True)
    meta.write_text(json.dumps({"raw_path": "data/raw/x/f.pdf", "sha256": hashlib.sha256(raw_bytes).hexdigest(),
                                "source_url": doc["url"], "retrieved_at": "2026-11-22T00:00:00Z"}), encoding="utf-8")
    return tmp_path


def run(repo, source):
    p = subprocess.run([sys.executable, str(TOOL), "--source", source, "--repo", str(repo)], capture_output=True, text=True)
    rows = [l.split("\t") for l in p.stdout.splitlines()[1:] if "\t" in l]
    return p.returncode, {r[0]: r for r in rows}


LISTED = b"%PDF-1.4 stored bitstream"
SERVED = b"%PDF-1.4 stored bitstream + India Code watermark"


def india_doc(**extra):
    d = {"doc_id": "ic-doc", "url": "https://indiacode.gov.in/server/api/core/bitstreams/x/content", "title": "t", "doc_type": "rules",
         "listing_md5": hashlib.md5(LISTED).hexdigest(), "listing_bytes": len(LISTED),
         "served_bytes_policy": "HOST_WATERMARKS_PDF"}
    d.update(extra)
    return d


def test_watermarked_india_code_download_is_not_rejected(tmp_path):
    repo = make_repo(tmp_path, "official_instruments_acq03", india_doc(), SERVED)
    rc, rows = run(repo, "official_instruments_acq03")
    assert rc == 0, rows
    status = rows["ic-doc"][1]
    assert status == "CHECKSUM_RECORDED_ONLY", rows
    assert rows["ic-doc"][3] == hashlib.sha256(SERVED).hexdigest()
    assert "listing md5 differs" in rows["ic-doc"][2] and "page-image identity check required" in rows["ic-doc"][2]


def test_served_sha256_pin_rejects_unexpected_change(tmp_path):
    doc = india_doc(expected_served_sha256=hashlib.sha256(SERVED).hexdigest())
    repo = make_repo(tmp_path, "official_instruments_acq03", doc, SERVED + b" changed")
    rc, rows = run(repo, "official_instruments_acq03")
    assert rc == 1 and rows["ic-doc"][1] == "FAIL", rows


def test_served_sha256_pin_passes_identical_bytes(tmp_path):
    doc = india_doc(expected_served_sha256=hashlib.sha256(SERVED).hexdigest())
    repo = make_repo(tmp_path, "official_instruments_acq03", doc, SERVED)
    rc, rows = run(repo, "official_instruments_acq03")
    assert rc == 0 and rows["ic-doc"][1] == "PASS", rows


def test_archive_pinned_bytes_still_rejected_on_change(tmp_path):
    good = b"%PDF-1.4 archive original"
    doc = {"doc_id": "ia-doc", "url": "https://archive.org/download/i/f.pdf", "title": "t", "doc_type": "notification",
           "expected_md5": hashlib.md5(good).hexdigest(), "expected_bytes": len(good)}
    repo = make_repo(tmp_path, "archive_acq03", doc, good + b"x")
    rc, rows = run(repo, "archive_acq03")
    assert rc == 1 and rows["ia-doc"][1] == "FAIL", rows


def test_non_pdf_served_file_is_rejected(tmp_path):
    repo = make_repo(tmp_path, "official_instruments_acq03", india_doc(), b"<html>login</html>")
    rc, rows = run(repo, "official_instruments_acq03")
    assert rc == 1 and rows["ic-doc"][1] == "FAIL", rows


def test_real_acq03_india_code_entries_use_listing_fields_not_strict_expectations():
    cfg = yaml.safe_load((ROOT / "config" / "sources.yaml").read_text(encoding="utf-8"))
    docs = cfg["sources"]["official_instruments_acq03"]["documents"]
    assert len(docs) == 3
    for d in docs:
        assert "expected_md5" not in d and "expected_bytes" not in d, d["doc_id"]
        assert len(d["listing_md5"]) == 32 and int(d["listing_bytes"]) > 0, d["doc_id"]
        assert d["served_bytes_policy"] == "HOST_WATERMARKS_PDF", d["doc_id"]


def test_real_config_india_code_entry_accepts_watermarked_download(tmp_path):
    """Faithful reproduction of the review defect using each real ACQ-03 India Code entry: served bytes differ from
    the listing (watermark) and must not be rejected; they must be recorded and flagged for page-image identity."""
    cfg = yaml.safe_load((ROOT / "config" / "sources.yaml").read_text(encoding="utf-8"))
    for i, d in enumerate(cfg["sources"]["official_instruments_acq03"]["documents"]):
        sub = tmp_path / str(i)
        sub.mkdir()
        repo = make_repo(sub, "official_instruments_acq03", d, b"%PDF-1.5 watermarked served copy " + d["doc_id"].encode())
        rc, rows = run(repo, "official_instruments_acq03")
        assert rc == 0 and rows[d["doc_id"]][1] == "CHECKSUM_RECORDED_ONLY", (d["doc_id"], rows)
