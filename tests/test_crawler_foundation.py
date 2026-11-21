import json
import socket
from datetime import datetime, time, timedelta, timezone
from pathlib import Path

import pytest
import yaml

from crawler.audit import AuditLog, read_audit
from crawler.cli import main
from crawler.config import DEFAULT_CONFIG, IST, check_config, in_window, load_config
from crawler.state import StateDB, backoff_delay, utcnow

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def no_network(monkeypatch):
    def refuse(*a, **k):
        raise AssertionError("network access attempted")
    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


@pytest.fixture
def db(tmp_path):
    with StateDB(tmp_path / "crawl.sqlite") as d:
        yield d


@pytest.fixture
def cfg():
    return load_config(DEFAULT_CONFIG)


def write_cfg(tmp_path, mutate):
    raw = yaml.safe_load(DEFAULT_CONFIG.read_text(encoding="utf-8"))
    mutate(raw)
    p = tmp_path / "sources.yaml"
    p.write_text(yaml.safe_dump(raw), encoding="utf-8")
    return load_config(p)


# ------------------------------------------------------------------ config
def test_real_config_has_no_errors(cfg):
    r = check_config(cfg)
    assert r.errors == []
    assert not cfg.user_agent_is_placeholder()


def test_placeholder_email_is_flagged(tmp_path):
    def m(r):
        r["defaults"]["contact_email"] = "CHANGE-ME@example.org"
    c = write_cfg(tmp_path, m)
    assert c.user_agent_is_placeholder()
    assert any("placeholder" in w for w in check_config(c).warnings)


def test_allow_list(cfg):
    assert cfg.is_url_allowed("indiacode", "https://www.indiacode.nic.in/handle/x")[0]
    assert cfg.is_url_allowed("indiacode", "https://WWW.IndiaCode.nic.in./x")[0]
    assert not cfg.is_url_allowed("indiacode", "https://www.mod.gov.in/x")[0]
    assert not cfg.is_url_allowed("indiacode", "https://evil.indiacode.nic.in.attacker.com/")[0]
    assert not cfg.is_url_allowed("indiacode", "ftp://www.indiacode.nic.in/x")[0]
    assert not cfg.is_url_allowed("indiacode", "https://indiankanoon.org/doc/1")[0]


def test_blocked_host_in_allow_list_is_an_error(tmp_path):
    c = write_cfg(tmp_path, lambda r: r["sources"]["indiacode"]["allowed_hosts"].append("indiankanoon.org"))
    assert any("blocked_hosts" in e for e in check_config(c).errors)


def test_seed_off_allow_list_is_an_error(tmp_path):
    c = write_cfg(tmp_path, lambda r: r["sources"]["mod"]["seeds"].append({"url": "https://example.com/"}))
    assert any("not in allowed_hosts" in e for e in check_config(c).errors)


def test_impolite_settings_are_errors(tmp_path):
    def m(r):
        r["defaults"]["min_delay_seconds"] = 0.2
        r["defaults"]["obey_robots_txt"] = False
    errs = check_config(write_cfg(tmp_path, m)).errors
    assert any("min_delay" in e for e in errs) and any("robots" in e for e in errs)


def test_quiet_hours_window():
    assert in_window(time(23, 0), time(20, 0), time(8, 0))
    assert in_window(time(3, 0), time(20, 0), time(8, 0))
    assert not in_window(time(12, 0), time(20, 0), time(8, 0))


def test_heavy_sources_wait_for_quiet_hours(cfg):
    noon_ist = datetime(2026, 11, 23, 12, 0, tzinfo=IST)
    night_ist = datetime(2026, 11, 23, 22, 0, tzinfo=IST)
    assert not cfg.may_run_now("aft", noon_ist)
    assert cfg.may_run_now("aft", night_ist)
    assert cfg.may_run_now("indiacode", noon_ist)  # not heavy


# ------------------------------------------------------------------- state
def test_enqueue_is_idempotent(db):
    assert db.enqueue("https://a/1", "indiacode", "a", "document")
    assert not db.enqueue("https://a/1", "indiacode", "a", "document")
    assert db.counts()["indiacode"]["queued"] == 1


def test_fetched_urls_are_not_resurrected(db):
    db.enqueue("https://a/1", "s", "a", "document")
    db.mark_fetched("https://a/1", status_code=200, sha256="x" * 64, nbytes=10, content_type="application/pdf",
                    etag='"e1"')
    assert not db.enqueue("https://a/1", "s", "a", "document")
    row = db.get("https://a/1")
    assert row["status"] == "fetched" and row["etag"] == '"e1"'


def test_retry_with_backoff_then_give_up(db):
    url = "https://a/flaky"
    db.enqueue(url, "s", "a", "document")
    now = utcnow()
    for attempt in range(1, 5):
        assert db.mark_attempt_failed(url, error="timeout", status_code=None, max_retries=5,
                                      backoff_base=4, now=now) == "queued"
        assert db.due("s", now=now) == []                       # in backoff
        assert len(db.due("s", now=now + timedelta(hours=2))) == 1  # due later
    assert db.mark_attempt_failed(url, error="503", status_code=503, max_retries=5, backoff_base=4) == "failed"
    row = db.get(url)
    assert row["attempts"] == 5 and row["status"] == "failed"
    assert [f["url"] for f in db.failures()] == [url]


def test_non_retryable_fails_immediately(db):
    db.enqueue("https://a/404", "s", "a", "document")
    assert db.mark_attempt_failed("https://a/404", error="404", status_code=404, max_retries=5,
                                  backoff_base=4, retryable=False) == "failed"


def test_backoff_grows_and_caps():
    assert backoff_delay(1, 4, jitter=False) == 4
    assert backoff_delay(3, 4, jitter=False) == 16
    assert backoff_delay(30, 4, jitter=False) == 3600


def test_state_survives_restart(tmp_path):
    p = tmp_path / "crawl.sqlite"
    with StateDB(p) as d:
        d.enqueue("https://a/1", "s", "a", "document")
        d.enqueue("https://a/2", "s", "a", "document")
        d.mark_fetched("https://a/1", status_code=200, sha256=None, nbytes=1, content_type=None)
    with StateDB(p) as d:  # "killed and restarted"
        assert [q.url for q in d.due("s")] == ["https://a/2"]


def test_duplicate_bytes_become_alias(db):
    h = "a" * 64
    assert db.record_file(sha256=h, raw_path="data/raw/s/2020/x.pdf", url="https://a/1", nbytes=5,
                          content_type="application/pdf")
    assert not db.record_file(sha256=h, raw_path="ignored", url="https://mirror/1", nbytes=5,
                              content_type="application/pdf")
    assert db.aliases(h) == ["https://mirror/1"]
    assert db.has_file(h)


def test_skipped(db):
    db.enqueue("https://a/login", "s", "a", "listing")
    db.mark_skipped("https://a/login", "requires login")
    assert db.get("https://a/login")["skip_reason"] == "requires login"
    assert db.due("s") == []


# ------------------------------------------------------------------- audit
def test_audit_writes_jsonl_and_db(tmp_path, db):
    a = AuditLog(tmp_path / "logs", db, run_id="r1")
    a.request(method="GET", url="https://a/1", status_code=200, nbytes=123, elapsed_ms=45, source="s")
    lines = read_audit(tmp_path / "logs")
    assert lines[0]["url"] == "https://a/1" and lines[0]["bytes"] == 123 and lines[0]["run_id"] == "r1"
    row = db.conn.execute("SELECT * FROM requests").fetchone()
    assert row["status_code"] == 200 and row["run_id"] == "r1"


# --------------------------------------------------------------------- CLI
def test_cli_config_check(capsys):
    assert main(["config-check"]) == 0
    assert "config OK" in capsys.readouterr().out


def test_cli_dry_run_makes_no_requests(tmp_path, no_network, capsys):
    assert main(["--root", str(tmp_path), "dry-run", "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    names = [s["name"] for s in out["sources"]]
    assert names == ["indiacode"]  # only enabled sources (mod is disabled: blocked, see PROGRESS.md)
    ic = out["sources"][0]
    assert {i["doc_id"] for i in ic["items"] if i["kind"] == "target"} >= {"act-army-1950", "act-bns-2023"}
    assert out["totals"]["targets_unresolved"] == out["totals"]["targets"]
    reports = list((tmp_path / "reports").glob("dry_run_*.md"))
    assert len(reports) == 1
    with StateDB(tmp_path / "state" / "crawl.sqlite") as d:
        run = d.last_runs(1)[0]
        assert run["mode"] == "dry_run" and run["outcome"] == "ok"
        assert d.conn.execute("SELECT COUNT(*) FROM requests").fetchone()[0] == 0
        assert d.counts() == {}  # dry run does not touch the queue


def test_dry_run_reflects_existing_state(tmp_path, no_network, capsys):
    with StateDB(tmp_path / "state" / "crawl.sqlite") as d:
        d.enqueue("https://www.indiacode.nic.in/army.pdf", "indiacode", "www.indiacode.nic.in", "document",
                  doc_id_hint="act-army-1950")
        d.enqueue("https://www.indiacode.nic.in/retry.pdf", "indiacode", "www.indiacode.nic.in", "document")
        d.mark_attempt_failed("https://www.indiacode.nic.in/retry.pdf", error="timeout", status_code=None,
                              max_retries=5, backoff_base=4)
    assert main(["--root", str(tmp_path), "dry-run", "--source", "indiacode", "--json"]) == 0
    src = json.loads(capsys.readouterr().out)["sources"][0]
    army = [i for i in src["items"] if i["doc_id"] == "act-army-1950"][0]
    assert army["action"] == "fetch document" and army["url"].endswith("army.pdf")
    retry = [i for i in src["items"] if i["kind"] == "retry"][0]
    assert retry["action"].startswith("wait until")
    assert src["due_now"] == 1 and src["waiting_backoff"] == 1


def test_dry_run_all_includes_disabled_and_flags_heavy(tmp_path, no_network, capsys):
    assert main(["--root", str(tmp_path), "dry-run", "--all", "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    aft = [s for s in out["sources"] if s["name"] == "aft"][0]
    assert aft["enabled"] is False and aft["heavy"] is True
    assert any(i["action"] == "skip: no URL configured" for i in aft["items"])


def test_unknown_source_is_rejected(tmp_path, capsys):
    assert main(["--root", str(tmp_path), "dry-run", "--source", "nope"]) == 2


def test_status_runs(tmp_path, capsys):
    assert main(["--root", str(tmp_path), "init-db"]) == 0
    assert main(["--root", str(tmp_path), "status"]) == 0
    assert "indiacode" in capsys.readouterr().out
