"""AFT module tests, on excerpts of listing pages saved from the live bench sites in 2023
(tests/fixtures/aft/README.md). They show the parsers fit that markup, not today's sites."""
import json
import socket
from pathlib import Path

import httpx
import pytest

from crawler import aft
from crawler.audit import AuditLog
from crawler.cli import main
from crawler.config import DEFAULT_CONFIG, load_config
from crawler.http import PoliteClient
from crawler.state import StateDB

FIX = Path(__file__).parent / "fixtures" / "aft"
CHD = "https://www.aftdelhi.nic.in/index.php/rbs/chandigarh/chandigarh-judgement"
KOL = "https://aftkolkata.nic.in/judgements/index/page:1"


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def refuse(*a, **k):
        raise AssertionError("network access attempted")
    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


@pytest.fixture
def cfg():
    return load_config(DEFAULT_CONFIG)


@pytest.fixture
def db(tmp_path):
    with StateDB(tmp_path / "state.sqlite") as d:
        yield d


def client(cfg, db, tmp_path, handler):
    def wrapped(req):
        return httpx.Response(404) if req.url.path == "/robots.txt" else handler(req)
    return PoliteClient(cfg, AuditLog(tmp_path / "logs", db, "t"), "aft", transport=httpx.MockTransport(wrapped), replay=True)


def html(name):
    return (FIX / name).read_text()


def page(body):
    return httpx.Response(200, text=body, headers={"content-type": "text/html"})


# ------------------------------------------------------------------ parsers
def test_parse_joodb_on_the_real_chandigarh_markup():
    rows, results = aft.parse_joodb(html("chandigarh_2023_excerpt.html"), CHD)
    assert results == (1, 8685, 8685) and len(rows) == 6
    r = rows[0]
    assert r.url == "https://www.aftdelhi.nic.in/benches/chandigarh_bench/judgments/court_3/november2013/OA_2183_of_2012.pdf"
    assert r.title == "OA_2183_of_2012"
    assert r.fields["court"] == "COURT_3" and r.fields["year"] == "2013" and r.fields["month"] == "11"
    assert "Prakash Krishna" in r.fields["judgment given by"] and "HS Panag" in r.fields["judgment given by"]
    assert "judgement given by" not in r.fields


def test_parse_table_on_the_real_kolkata_and_lucknow_markup():
    rows = aft.parse_table(html("kolkata_2023_page1_excerpt.html"), KOL)
    assert len(rows) == 18 and rows[0].url == "https://aftkolkata.nic.in/upload/court/Court-152.PDF"
    assert rows[0].title == "Jitendra Kumar Sharma" and rows[0].fields["case no"] == "T.A. No. 18/2013"
    rows = aft.parse_table(html("lucknow_2023_excerpt.html"), "https://aftlko.up.nic.in/judgments.htm")
    assert len(rows) == 12 and rows[0].fields == {"subject": "F Pension"}
    assert [r.title for r in rows[:3]] == ["Smt Rekha Devi", "Jyoti", "Hemanth Kumar"]      # names split by markup rejoined
    assert rows[0].url.startswith("https://aftlko.up.nic.in/Others/Judgment%20Mar%202023/")


# ---------------------------------------------------------------- discovery
def test_discover_chandigarh_asks_for_all_and_queues_judgments(cfg, db, tmp_path):
    seen = []

    def handler(req):
        seen.append(str(req.url))
        return page(html("chandigarh_2023_excerpt.html"))
    c = client(cfg, db, tmp_path, handler)
    [r] = aft.discover(cfg, db, c, only=["chandigarh"])
    assert seen == [CHD + "?limit=0"] and c.requests_made == 2                 # robots + one listing page
    assert r.status == "ok" and r.rows == 6 and r.queued == 6 and r.listed_total == 8685
    assert any("says 8685 results; 6 PDF links were read" in w for w in r.warnings)   # the excerpt is short
    row = db.conn.execute("SELECT url, meta, kind, status, doc_id_hint FROM urls WHERE kind='document' ORDER BY url").fetchone()
    meta = json.loads(row["meta"])
    assert row["status"] == "queued" and row["doc_id_hint"] is None
    assert meta["category"] == "judgment" and meta["bench"] == "chandigarh" and meta["year"] == "2013"
    assert meta["case_number"].startswith("OA_") and meta["fields"]["court"] == "COURT_3"
    [again] = aft.discover(cfg, db, client(cfg, db, tmp_path, handler), only=["chandigarh"], refresh=True)
    assert again.queued == 0 and again.already_known == 6


def test_discover_pages_on_when_the_site_does_not_return_everything(cfg, db, tmp_path):
    def rows(n0, n1):
        body = "".join(f'<div class="tr odd"><div class="td"><p>Case No.: <span style="color:blue">OA_{i}_of_2020</span> '
                       f'Judgement: <a href="/benches/x/OA_{i}_of_2020.pdf" target="_blank">ViewPDF</a></p></div></div>'
                       for i in range(n0, n1 + 1))
        return page(f"<html><body><p>Results {n0} - {n1} of 5</p><div class='table'>{body}</div></body></html>")
    seen = []

    def handler(req):
        seen.append(str(req.url))
        start = int(req.url.params.get("start", 0))
        return rows(start + 1, min(start + 2, 5))
    [r] = aft.discover(cfg, db, client(cfg, db, tmp_path, handler), only=["chandigarh"])
    assert [u.split("?")[1] for u in seen] == ["limit=0", "limit=2&start=2", "limit=2&start=4"]
    assert r.pages == 3 and r.rows == 5 and r.listed_total == 5 and r.warnings == []


def test_discover_kolkata_follows_only_its_own_page_links(cfg, db, tmp_path):
    seen = []

    def handler(req):
        seen.append(str(req.url))
        if str(req.url) == KOL:
            return page(html("kolkata_2023_page1_excerpt.html"))
        return page('<table><tr><td><a href="/upload/court/Court-900.pdf">x</a></td></tr></table>'
                    '<a href="https://example.org/judgements/index/page:99">off-site</a>')
    [r] = aft.discover(cfg, db, client(cfg, db, tmp_path, handler), only=["kolkata"])
    assert seen[0] == KOL and all(u.startswith("https://aftkolkata.nic.in/judgements/index/page:") for u in seen)
    assert r.pages == len(seen) >= 3 and r.rows == 19 and r.status == "ok"


def test_unconfigured_blocked_and_changed_layout_are_reported(cfg, db, tmp_path):
    res = {r.key: r for r in aft.discover(cfg, db, client(cfg, db, tmp_path, lambda req: httpx.Response(403)))}
    assert res["lucknow"].status == "not_configured" and res["guwahati"].status == "not_configured"
    assert res["chandigarh"].status == "blocked" and res["principal-delhi"].status == "blocked"
    [r] = aft.discover(cfg, db, client(cfg, db, tmp_path, lambda req: page("<html><body>New site</body></html>")),
                       only=["chandigarh"], refresh=True)
    assert r.rows == 0 and any("layout may have changed" in w for w in r.warnings)
    with pytest.raises(KeyError):
        aft.discover(cfg, db, client(cfg, db, tmp_path, lambda req: page("")), only=["nowhere"])


def test_offsite_pdf_links_are_not_queued(cfg, db, tmp_path):
    body = ('<div class="tr"><p>Case No.: <span style="color:blue">OA_1</span> <a href="https://example.org/a.pdf">ViewPDF</a></p></div>'
            '<div class="tr"><p>Case No.: <span style="color:blue">OA_2</span> <a href="/benches/b.pdf">ViewPDF</a></p></div>')
    [r] = aft.discover(cfg, db, client(cfg, db, tmp_path, lambda req: page(body)), only=["chandigarh"])
    assert r.queued == 1 and len(r.dropped) == 1 and "example.org" in r.dropped[0][0]


def test_cli_refuses_live_aft_outside_quiet_hours(tmp_path, monkeypatch, capsys):
    from crawler import config as cfgmod
    monkeypatch.setattr(cfgmod.Config, "in_quiet_hours", lambda self, now=None: False)
    assert main(["--root", str(tmp_path), "discover", "--source", "aft", "--only", "chandigarh"]) == 3
    assert "heavy source" in capsys.readouterr().err
