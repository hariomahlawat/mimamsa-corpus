"""Fetch-time integrity enforcement (PR #17 review): pinned expected values must reject a changed or wrong file
BEFORE it is stored or marked fetched; India Code watermarked files (listing values only) must still be accepted.
Offline (httpx mock transport via the test_indiacode helpers)."""
import hashlib

import httpx

from crawler.fetch import fetch_documents
from tests.test_indiacode import API, cfg, db, make_client, no_network, site  # noqa: F401  (fixtures)

GOOD = b"%PDF-1.4 genuine gazette scan"
BAD = b"%PDF-1.4 substituted or truncated file"


def _md5(b):
    return hashlib.md5(b).hexdigest()


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def _run(cfg, db, tmp_path, served, direct):
    url = f"{API}/core/bitstreams/t/content"
    db.enqueue(url, "indiacode", "indiacode.gov.in", "document",
               meta={"filename": "t.pdf", "year": "1965", "category": "notification", "direct": direct})
    c = make_client(cfg, db, tmp_path, site({url: httpx.Response(200, content=served, headers={"content-type": "application/pdf"})},
                                            robots="User-agent: *\nDisallow:\n"))
    stats = fetch_documents(cfg, db, c, "indiacode", tmp_path)
    return url, stats


def _stored(tmp_path):
    return sorted(p.name for p in (tmp_path / "data" / "raw").rglob("*") if p.is_file()) if (tmp_path / "data" / "raw").exists() else []


def test_expected_sha256_mismatch_is_rejected_and_not_stored(cfg, db, tmp_path):
    url, stats = _run(cfg, db, tmp_path, BAD, {"doc_id": "x", "expected_sha256": _sha(GOOD)})
    assert stats["downloaded"] == 0 and stats["failed"] == 1, stats
    assert db.get(url)["status"] == "failed" and "integrity" in db.get(url)["last_error"]
    assert _stored(tmp_path) == []


def test_expected_md5_and_bytes_mismatch_is_rejected(cfg, db, tmp_path):
    url, stats = _run(cfg, db, tmp_path, BAD, {"doc_id": "x", "expected_md5": _md5(GOOD), "expected_bytes": len(GOOD)})
    assert stats["downloaded"] == 0 and stats["failed"] == 1, stats
    assert _stored(tmp_path) == []


def test_acq01_note_md5_size_mismatch_is_rejected(cfg, db, tmp_path):
    note = f"Gazette ...; expected md5 {_md5(GOOD)}, {len(GOOD)} bytes"
    url, stats = _run(cfg, db, tmp_path, BAD, {"doc_id": "x", "note": note})
    assert stats["downloaded"] == 0 and stats["failed"] == 1, stats


def test_matching_expected_values_are_accepted(cfg, db, tmp_path):
    url, stats = _run(cfg, db, tmp_path, GOOD, {"doc_id": "x", "expected_sha256": _sha(GOOD),
                                                "expected_md5": _md5(GOOD), "expected_bytes": len(GOOD)})
    assert stats["downloaded"] == 1 and stats["failed"] == 0, stats
    assert db.get(url)["status"] == "fetched"


def test_india_code_watermarked_file_with_listing_values_is_accepted(cfg, db, tmp_path):
    url, stats = _run(cfg, db, tmp_path, BAD, {"doc_id": "x", "listing_md5": _md5(GOOD), "listing_bytes": len(GOOD),
                                               "served_bytes_policy": "HOST_WATERMARKS_PDF"})
    assert stats["downloaded"] == 1 and stats["failed"] == 0, stats


def test_pinned_served_sha256_mismatch_is_rejected(cfg, db, tmp_path):
    url, stats = _run(cfg, db, tmp_path, BAD, {"doc_id": "x", "served_bytes_policy": "HOST_WATERMARKS_PDF",
                                               "expected_served_sha256": _sha(GOOD)})
    assert stats["downloaded"] == 0 and stats["failed"] == 1, stats
