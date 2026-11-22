"""DESW allow-list guards (prepared; downloads not yet authorised). Offline."""
import socket

import pytest

from crawler.cli import DISCOVERERS
from crawler.config import DEFAULT_CONFIG, check_config, load_config

EXPECTED = {
    "rules-entitlement-casualty-pensionary-awards-2023": "https://desw.gov.in/sites/default/files/Entitlement%20Rules%202023.pdf",
    "rules-entitlement-casualty-pensionary-awards-2023-alt": "https://desw.gov.in/sites/default/files/2026-10/Entitlement%20Rules%202023.pdf",
    "manual-guide-medical-officers-military-pensions-2023": "https://desw.gov.in/sites/default/files/2026-10/GMO%202023.pdf",
}


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def refuse(*a, **k):
        raise AssertionError("network access attempted in an offline test")
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket.socket, "connect", refuse)


@pytest.fixture
def cfg():
    return load_config(DEFAULT_CONFIG)


def test_exact_documents(cfg):
    assert {d["doc_id"]: d["url"] for d in cfg.source("desw")["documents"]} == EXPECTED


def test_https_exact_host_only(cfg):
    assert cfg.allowed_hosts("desw") == {"desw.gov.in"}
    for url in EXPECTED.values():
        assert url.startswith("https://desw.gov.in/")
        assert cfg.is_url_allowed("desw", url)[0]
    for bad in ["http://desw.gov.in/x.pdf", "ftp://desw.gov.in/x.pdf", "https://www.desw.gov.in/x", "https://desw.gov.in.evil.com/x",
                "https://pcdapension.nic.in/x", "http://103.154.2.123/x.pdf"]:
        assert not cfg.is_url_allowed("desw", bad)[0], bad


def test_require_https_blocks_plain_http_and_is_per_source(cfg):
    assert cfg.source("desw").get("require_https") is True
    ok, why = cfg.is_url_allowed("desw", "http://desw.gov.in/sites/default/files/x.pdf")
    assert not ok and "HTTPS" in why


def test_no_plain_http_document(cfg):
    assert all(not d["url"].startswith("http://") for d in cfg.source("desw")["documents"])


def test_disabled_and_mapped(cfg):
    assert not cfg.source("desw").get("enabled")
    assert DISCOVERERS["desw"].__name__.endswith("direct")


def test_config_ok(cfg):
    assert check_config(cfg).errors == []
