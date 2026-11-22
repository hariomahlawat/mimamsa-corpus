"""ACQ-01 (batches B1, B2, B6) acquisition-configuration guards. Offline: no test touches the network.
The owner authorised acquiring ONLY the listed documents; these tests pin that exact list and the hosts it may use."""
import socket

import pytest
import yaml

from crawler.cli import DISCOVERERS
from crawler.config import DEFAULT_CONFIG, check_config, load_config

EXPECTED = {
    "archive": {
        "notif-army-rules-1954-sro-484": "https://archive.org/download/in.gazette.central.w.1954-11-27.103686/103686.pdf",
        "notif-army-rules-amdt-sro-116-1965": "https://archive.org/download/in.gazette.central.w.1965-04-10.81813/81813.pdf",
        "notif-army-rules-amdt-sro-215-1965": "https://archive.org/download/in.gazette.central.w.1965-07-03.79361/79361.pdf",
        "notif-army-rules-amdt-sro-188-1979": "https://archive.org/download/in.gazette.central.w.1979-07-28.46533/46533.pdf",
        "notif-army-rules-amdt-sro-216-1988": "https://archive.org/download/in.gazette.central.w.1988-09-17.28081/28081.pdf",
        "notif-army-rules-amdt-sro-17e-1993": "https://archive.org/download/in.gazette.central.e.1993-12-06.16490/16490.pdf",
        "notif-army-rules-amdt-sro-8e-2003": "https://archive.org/download/in.gazette.central.e.2003-06-24.153/153.pdf",
        "notif-army-rules-amdt-sro-17e-2019": "https://archive.org/download/in.gazette.central.e.2019-12-28.214956/214956.pdf",
        "notif-army-rules-amdt-sro-6e-2022": "https://archive.org/download/in.gazette.central.e.2022-06-06.236353/236353.pdf",
        "rules-adjustment-jurisdiction-1978-so-488": "https://archive.org/download/in.gazette.central.w.1978-02-25.48290/48290.pdf",
        "notif-adjustment-jurisdiction-amdt-so-4010-1986": "https://archive.org/download/in.gazette.central.w.1986-12-06.32435/32435.pdf",
        "act-commanders-in-chief-change-designation-1955": "https://archive.org/download/in.gazette.e.1955.613/E-2210-1955-0031-101567.pdf",
    },
    "official_instruments": {
        "act-air-force-army-laws-amendment-1975": "https://indiacode.gov.in/server/api/core/bitstreams/d4cb2142-ec1d-46ca-88b1-6ae2b9c603d7/content",
        "act-army-amendment-1992": "https://indiacode.gov.in/server/api/core/bitstreams/7a05a1f5-506a-4e9c-afae-c2e4fc1e989e/content",
    },
}
# Redirect targets observed 2026-11-22 (archive.org/download -> per-item data server).
OBSERVED_REDIRECT_HOSTS = ["dn760006.eu.archive.org", "dn790000.ca.archive.org", "dn711201.ca.archive.org",
                           "dn760008.eu.archive.org", "dn721609.ca.archive.org", "dn790009.ca.archive.org",
                           "dn710901.ca.archive.org", "dn721901.ca.archive.org", "dn760002.eu.archive.org",
                           "dn790002.ca.archive.org", "dn760001.eu.archive.org"]


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def refuse(*a, **k):
        raise AssertionError("network access attempted in an offline test")
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket.socket, "connect", refuse)


@pytest.fixture
def cfg():
    return load_config(DEFAULT_CONFIG)


def write_cfg(tmp_path, mutate):
    raw = yaml.safe_load(DEFAULT_CONFIG.read_text(encoding="utf-8"))
    mutate(raw)
    p = tmp_path / "sources.yaml"
    p.write_text(yaml.safe_dump(raw), encoding="utf-8")
    return load_config(p)


def test_exact_document_list(cfg):
    for source, expected in EXPECTED.items():
        got = {d["doc_id"]: d["url"] for d in cfg.source(source)["documents"]}
        assert got == expected, source


def test_documents_are_https_named_hosts_and_allowed(cfg):
    for source, expected in EXPECTED.items():
        for doc_id, url in expected.items():
            assert url.startswith("https://"), doc_id
            ok, why = cfg.is_url_allowed(source, url)
            assert ok, (doc_id, why)


def test_documents_carry_required_curated_fields(cfg):
    for source in EXPECTED:
        for d in cfg.source(source)["documents"]:
            for k in ("doc_id", "url", "title", "doc_type", "year", "number", "issuing_authority", "note"):
                assert d.get(k), (d["doc_id"], k)


def test_observed_archive_redirect_hosts_allowed_only_for_archive(cfg):
    for h in OBSERVED_REDIRECT_HOSTS:
        assert cfg.is_url_allowed("archive", f"https://{h}/x.pdf")[0], h
        assert not cfg.is_url_allowed("official_instruments", f"https://{h}/x.pdf")[0], h


@pytest.mark.parametrize("url", ["https://evilarchive.org/x", "https://archive.org.evil.com/x", "https://archive.org@evil.com/x",
                                 "https://notarchive.org/x", "http://103.154.2.123/x.pdf", "https://aftjabalpur.in/x"])
def test_lookalikes_ip_and_blocked_refused(cfg, url):
    assert not cfg.is_url_allowed("archive", url)[0]
    assert not cfg.is_url_allowed("official_instruments", url)[0]


def test_wildcard_never_matches_bare_or_other_sources(cfg):
    # the bare domain is allowed only because it is listed explicitly
    assert cfg.host_allowed("archive", "archive.org")
    assert not cfg.host_allowed("indiacode", "dn760006.eu.archive.org")


def test_real_config_has_no_errors(cfg):
    assert check_config(cfg).errors == []


def test_malformed_wildcard_is_an_error(tmp_path):
    c = write_cfg(tmp_path, lambda r: r["sources"]["archive"]["allowed_hosts"].append("*.org"))
    assert any("wildcard host" in e for e in check_config(c).errors)


def test_wildcard_of_blocked_host_is_an_error(tmp_path):
    c = write_cfg(tmp_path, lambda r: r["sources"]["archive"]["allowed_hosts"].append("*.aftjabalpur.in"))
    assert any("blocked_hosts" in e for e in check_config(c).errors)


def test_blocked_beats_wildcard(tmp_path):
    def m(r):
        r["blocked_hosts"].append("dn999999.ca.archive.org")
    c = write_cfg(tmp_path, m)
    assert not c.is_url_allowed("archive", "https://dn999999.ca.archive.org/x")[0]


def test_sources_stay_disabled_for_explicit_runs_only(cfg):
    for source in EXPECTED:
        assert not cfg.source(source).get("enabled"), source
        assert source in DISCOVERERS, source
