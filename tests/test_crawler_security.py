"""Crawler security guards (offline). The compromised host formerly configured for AFT Jabalpur must
never be allowed, listed or fetched, and must not be reintroduced silently. No test touches the network."""
import socket
from pathlib import Path

import pytest
import yaml

from crawler.config import DEFAULT_CONFIG, _config_urls, check_config, load_config

BAD = "aftjabalpur.in"
BAD_URLS = [f"https://{BAD}/", f"http://{BAD}/judgements", f"https://www.{BAD}/x.pdf", f"https://sub.{BAD}/a"]


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def refuse(*a, **k):
        raise AssertionError("network access attempted in an offline security test")
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


def test_host_is_blocked(cfg):
    assert BAD in cfg.blocked_hosts and f"www.{BAD}" in cfg.blocked_hosts


def test_host_not_allowed_by_any_source(cfg):
    for name in cfg.sources:
        assert not any(cfg.is_blocked_host(h) for h in cfg.allowed_hosts(name)), name


def test_no_configured_url_uses_host(cfg):
    for name, src in cfg.sources.items():
        for path, url in _config_urls(src, f"sources.{name}"):
            assert BAD not in url.lower(), path


def test_host_only_appears_in_blocked_hosts():
    raw = yaml.safe_load(DEFAULT_CONFIG.read_text(encoding="utf-8"))
    raw.pop("blocked_hosts")
    assert BAD not in yaml.safe_dump(raw).lower()


def test_is_url_allowed_refuses_host_and_subdomains_for_every_source(cfg):
    for name in cfg.sources:
        for url in BAD_URLS:
            ok, reason = cfg.is_url_allowed(name, url)
            assert not ok and "blocked" in reason, (name, url, reason)


def test_real_config_has_no_errors(cfg):
    assert check_config(cfg).errors == []


def test_reintroduction_in_allowed_hosts_is_an_error(tmp_path):
    c = write_cfg(tmp_path, lambda r: r["sources"]["aft"]["allowed_hosts"].append(BAD))
    assert any("blocked_hosts" in e and BAD in e for e in check_config(c).errors)


def test_reintroduction_as_bench_listing_url_is_an_error(tmp_path):
    def m(r):
        jb = next(b for b in r["sources"]["aft"]["benches"] if b["key"] == "jabalpur")
        jb["listing_urls"] = [f"https://{BAD}/judgements"]
    c = write_cfg(tmp_path, m)
    assert any("listing_urls" in e and BAD in e for e in check_config(c).errors)


def test_reintroduction_of_subdomain_or_base_url_is_an_error(tmp_path):
    def m(r):
        r["sources"]["aft"]["allowed_hosts"].append(f"cdn.{BAD}")
        r["sources"]["aft"]["base_url"] = f"https://{BAD}"
    errs = check_config(write_cfg(tmp_path, m)).errors
    assert any(f"cdn.{BAD}" in e for e in errs) and any("base_url" in e for e in errs)


def test_removing_host_from_blocked_hosts_is_detected(tmp_path):
    # If someone deletes the block, the guard tests above (and this one) must fail.
    c = write_cfg(tmp_path, lambda r: r.__setitem__("blocked_hosts", [h for h in r["blocked_hosts"] if BAD not in h]))
    assert BAD not in c.blocked_hosts  # sanity: mutation applied
    assert BAD in load_config(DEFAULT_CONFIG).blocked_hosts  # the committed config keeps the block
