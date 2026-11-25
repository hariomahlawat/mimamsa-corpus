"""F07: no sensitive response or client storage persists on shared desktops."""
from __future__ import annotations

import json
from pathlib import Path

P = json.loads((Path(__file__).resolve().parents[1] / "policies" / "client_state_and_cache.json").read_text(encoding="utf-8"))
SENSITIVE = ["original_pdf", "working_document", "search_results", "snippets_and_text", "document_metadata",
             "notes_and_workspace", "admin"]


def test_sensitive_responses_are_no_store():
    for cls in SENSITIVE:
        assert P["response_classes"][cls]["cache_control"] == "no-store", cls


def test_only_hashed_static_assets_may_be_cached():
    cached = [k for k, v in P["response_classes"].items() if v["cache_control"] != "no-store"]
    assert cached == ["static_assets_hashed"]


def test_logout_purges_browser_cache_and_storage():
    assert "cache" in P["logout"]["clear_site_data"] and "storage" in P["logout"]["clear_site_data"]
    assert P["logout"]["server_session_invalidated"] is True


def test_no_persistent_client_storage():
    cs = P["client_storage"]
    for k in ("localStorage", "indexedDB", "service_worker", "cache_storage_api"):
        assert cs[k] == "forbidden", k
    assert set(cs["sessionStorage_allowed_keys"]).isdisjoint(cs["never_on_client"])
    for k in ("search_query_text", "notes", "working_document_content", "tabs_with_document_ids"):
        assert k in cs["never_on_client"]


def test_no_offline_cached_view():
    assert "no cached content" in P["offline_behaviour"]


def test_pdfjs_safe_flags():
    assert P["pdfjs"]["isEvalSupported"] is False and P["pdfjs"]["enableScripting"] is False


def test_pdfjs_uses_bounded_authenticated_ranges():
    """PR #53 Serving §6/§10: no unbounded initial GET; bounded single ranges from the first byte."""
    pj = P["pdfjs"]
    assert pj["disableStream"] is True and pj["disableAutoFetch"] is True
    assert 0 < pj["max_range_bytes"] <= 65536 and "custom range transport" in pj["transport"]


def test_protected_responses_not_conditional_compressed_or_static():
    pr = P["protected_responses"]
    assert "no ETag" in pr["conditional_requests"] and "304" in pr["conditional_requests"]
    assert pr["compression"].startswith("disabled") and pr["static_or_sendfile"].startswith("forbidden")
    assert "polling" in pr["progress_events"]
