"""Step 3 tests: polite client, India Code discovery and document fetch, all against
SYNTHETIC saved pages (tests/fixtures/indiacode/README.md). They prove the crawler's
behaviour, not that the parsers fit the real site."""
import json
import socket
from pathlib import Path

import httpx
import pytest
import yaml

from crawler import indiacode
from crawler.audit import AuditLog
from crawler.cli import main
from crawler.config import DEFAULT_CONFIG, load_config
from crawler.fetch import fetch_documents
from crawler.http import (Blocked, FetchError, NotAllowed, PoliteClient, RobotsDisallowed, UserAgentNotSet,
                          replay_transport)
from crawler.state import StateDB

FIX = Path(__file__).parent / "fixtures" / "indiacode"
BASE = "https://www.indiacode.nic.in"
ACT_URL = f"{BASE}/handle/123456789/99991?view_type=browse"
ACT_PDF = f"{BASE}/bitstream/123456789/99991/1/synthetic_army_act_1950.pdf"


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


class Clock:
    def __init__(self):
        self.t, self.sleeps = 1000.0, []

    def now(self):
        return self.t

    def sleep(self, s):
        self.sleeps.append(s)
        self.t += s


def make_client(cfg, db, tmp_path, handler=None, clock=None, source="indiacode"):
    transport = httpx.MockTransport(handler) if handler else replay_transport(FIX)
    kw = dict(sleep=clock.sleep, clock=clock.now) if clock else {}
    return PoliteClient(cfg, AuditLog(tmp_path / "logs", db, "test-run"), source, transport=transport,
                        replay=True, **kw)


def site(pages, robots="User-agent: *\nDisallow: /private/\n"):
    def handler(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(200, text=robots) if robots is not None else httpx.Response(404)
        r = pages.get(str(req.url))
        return r if r is not None else httpx.Response(404)
    return handler


# ------------------------------------------------------------ polite client
def placeholder_config(tmp_path) -> Path:
    raw = yaml.safe_load(DEFAULT_CONFIG.read_text(encoding="utf-8"))
    raw["defaults"]["user_agent"] = "MimamsaCorpusBot/0.1 (contact: CHANGE-ME@example.org)"
    p = tmp_path / "placeholder.yaml"
    p.write_text(yaml.safe_dump(raw), encoding="utf-8")
    return p


def test_live_client_refuses_placeholder_user_agent(db, tmp_path):
    with pytest.raises(UserAgentNotSet):
        PoliteClient(load_config(placeholder_config(tmp_path)), AuditLog(tmp_path / "logs", db, None), "indiacode")


def test_rate_limit_per_host(cfg, db, tmp_path):
    clock = Clock()
    c = make_client(cfg, db, tmp_path, site({f"{BASE}/a": httpx.Response(200, text="a"),
                                             f"{BASE}/b": httpx.Response(200, text="b")}), clock)
    c.get(f"{BASE}/a")
    c.get(f"{BASE}/b")
    # robots.txt, /a, /b: two waits of the 2 s minimum
    assert clock.sleeps == [2.0, 2.0]
    assert c.requests_made == 3


def test_robots_crawl_delay_raises_the_delay(cfg, db, tmp_path):
    clock = Clock()
    c = make_client(cfg, db, tmp_path, site({f"{BASE}/a": httpx.Response(200, text="a")},
                                            robots="User-agent: *\nCrawl-delay: 7\n"), clock)
    c.get(f"{BASE}/a")
    assert clock.sleeps == [7.0]


def test_robots_disallow_and_unreachable_robots(cfg, db, tmp_path):
    c = make_client(cfg, db, tmp_path, site({f"{BASE}/private/x": httpx.Response(200, text="x")}))
    with pytest.raises(RobotsDisallowed):
        c.get(f"{BASE}/private/x")

    def robots_down(req):
        return httpx.Response(503) if req.url.path == "/robots.txt" else httpx.Response(200, text="x")
    c2 = make_client(cfg, db, tmp_path, robots_down)
    with pytest.raises(RobotsDisallowed):
        c2.get(f"{BASE}/a")


def test_missing_robots_allows(cfg, db, tmp_path):
    c = make_client(cfg, db, tmp_path, site({f"{BASE}/a": httpx.Response(200, text="a")}, robots=None))
    assert c.get(f"{BASE}/a").status == 200


def test_offsite_and_blocked_hosts_never_requested(cfg, db, tmp_path):
    seen = []

    def handler(req):
        seen.append(str(req.url))
        return httpx.Response(200, text="x")
    c = make_client(cfg, db, tmp_path, handler)
    for url in ("https://indiankanoon.org/doc/1", "https://www.mod.gov.in/x", "https://example.org/"):
        with pytest.raises(NotAllowed):
            c.get(url)
    assert seen == []


def test_redirect_offsite_is_refused(cfg, db, tmp_path):
    c = make_client(cfg, db, tmp_path, site({
        f"{BASE}/a": httpx.Response(302, headers={"location": "https://example.org/a"})}))
    with pytest.raises(NotAllowed):
        c.get(f"{BASE}/a")


def test_redirect_onsite_is_followed(cfg, db, tmp_path):
    c = make_client(cfg, db, tmp_path, site({
        f"{BASE}/a": httpx.Response(301, headers={"location": "/b"}),
        f"{BASE}/b": httpx.Response(200, text="b")}))
    r = c.get(f"{BASE}/a")
    assert r.url == f"{BASE}/b" and r.text() == "b"


def test_login_redirect_and_403_stop(cfg, db, tmp_path):
    c = make_client(cfg, db, tmp_path, site({
        f"{BASE}/a": httpx.Response(302, headers={"location": "/user/login?next=/a"}),
        f"{BASE}/b": httpx.Response(403)}))
    with pytest.raises(Blocked):
        c.get(f"{BASE}/a")
    with pytest.raises(Blocked):
        c.get(f"{BASE}/b")


def test_5xx_and_timeouts_are_retryable(cfg, db, tmp_path):
    def handler(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        if req.url.path == "/slow":
            raise httpx.ReadTimeout("slow", request=req)
        return httpx.Response(503)
    c = make_client(cfg, db, tmp_path, handler)
    for path in ("/slow", "/down"):
        with pytest.raises(FetchError) as e:
            c.get(BASE + path)
        assert e.value.retryable
    rows = db.conn.execute("SELECT url, status_code, error FROM requests ORDER BY id").fetchall()
    assert [r["url"] for r in rows] == [f"{BASE}/robots.txt", f"{BASE}/slow", f"{BASE}/down"]
    assert "ReadTimeout" in rows[1]["error"] and rows[2]["status_code"] == 503


def test_size_cap(tmp_path, db):
    raw = yaml.safe_load(DEFAULT_CONFIG.read_text(encoding="utf-8"))
    raw["defaults"]["max_file_mb"] = 0.001
    p = tmp_path / "s.yaml"
    p.write_text(yaml.safe_dump(raw), encoding="utf-8")
    c = make_client(load_config(p), db, tmp_path, site({f"{BASE}/big": httpx.Response(200, content=b"x" * 5000)},
                                                       robots=None))
    with pytest.raises(FetchError) as e:
        c.get(f"{BASE}/big")
    assert not e.value.retryable


# ------------------------------------------------------------------ parsers
def test_normalise_title():
    assert indiacode.normalise_title("The Army Act, 1950") == indiacode.normalise_title("ARMY ACT 1950")
    assert indiacode.normalise_title("The Indian Army Act, 1911") != indiacode.normalise_title("The Army Act, 1950")


def test_parse_search_results():
    res = indiacode.parse_search_results((FIX / "search_army_act.html").read_text(), BASE + "/simple-search")
    assert ("The Army Act, 1950", ACT_URL) in res
    assert len([u for _, u in res]) == len({u for _, u in res})


def test_parse_act_page(cfg):
    page = indiacode.parse_act_page((FIX / "act_army_1950.html").read_text(), ACT_URL,
                                    lambda u: cfg.is_url_allowed("indiacode", u))
    assert page.metadata["act_number"] == "46" and page.metadata["short_title"] == "The Army Act, 1950"
    assert [d.url for d in page.act_pdfs] == [ACT_PDF]            # '#page=1' variant de-duplicated
    cats = sorted(d.category for d in page.subordinate)
    assert cats == ["notifications", "notifications", "regulations", "regulations", "rules"]
    rules = [d for d in page.subordinate if d.category == "rules"][0]
    assert rules.title == "The Army Rules, 1954" and rules.date_raw == "01-01-1900"
    assert page.section_links == 3
    assert {urlhost for urlhost, _ in [(u.split('/')[2], w) for u, w in page.dropped]} == \
        {"indiankanoon.org", "www.example.org"}
    assert page.warnings == []


def test_parse_act_page_warns_on_unexpected_layout(cfg):
    page = indiacode.parse_act_page("<html><body><p>Something else entirely</p></body></html>", ACT_URL,
                                    lambda u: (True, "ok"))
    assert any("metadata" in w for w in page.warnings) and any("Act PDF" in w for w in page.warnings)


# ---------------------------------------------------------------- discovery
def test_discover_army_act(cfg, db, tmp_path):
    c = make_client(cfg, db, tmp_path)
    [r] = indiacode.discover(cfg, db, c, only=["act-army-1950"])
    assert r.status == "resolved" and r.act_url == ACT_URL
    assert r.act_pdfs == 1 and r.subordinate == {"rules": 1, "notifications": 2, "regulations": 2}
    assert r.newly_queued == 6 and len(r.dropped) == 2
    assert r.warnings == []                                       # the expected Army Rules, 1954 are listed
    assert c.requests_made == 3                                   # robots, search, act page: no documents
    assert db.get(ACT_PDF)["doc_id_hint"] == "act-army-1950" and db.get(ACT_PDF)["status"] == "queued"
    assert db.counts()["indiacode"] == {"queued": 6, "fetched": 2, "failed": 0, "skipped": 0}
    # second run: nothing re-fetched
    c2 = make_client(cfg, db, tmp_path)
    [r2] = indiacode.discover(cfg, db, c2, only=["act-army-1950"])
    assert r2.status == "already_known" and c2.requests_made == 0


def test_discover_warns_when_expected_rules_missing(cfg, db, tmp_path):
    html = (FIX / "act_army_1950.html").read_text().replace("The Army Rules, 1954", "Something else")
    search = f"{BASE}/simple-search?query=The+Army+Act%2C+1950"
    c = make_client(cfg, db, tmp_path, site({
        search: httpx.Response(200, text=(FIX / "search_army_act.html").read_text(),
                               headers={"content-type": "text/html"}),
        ACT_URL: httpx.Response(200, text=html, headers={"content-type": "text/html"})}, robots=None))
    [r] = indiacode.discover(cfg, db, c, only=["act-army-1950"])
    assert r.status == "resolved" and any("Army Rules, 1954" in w for w in r.warnings)


def test_discover_never_guesses(cfg, db, tmp_path):
    # Not in the replay set: search answers 404 -> failed, nothing queued.
    c = make_client(cfg, db, tmp_path)
    [r] = indiacode.discover(cfg, db, c, only=["act-navy-1957"])
    assert r.status == "failed" and db.counts()["indiacode"]["queued"] == 0

    # Search works but has no exact title match -> unresolved, candidates listed.
    search = f"{BASE}/simple-search?query=The+Air+Force+Act%2C+1950"
    html = '<a href="/handle/1/2">The Air Force Rules, 1969</a><a href="/handle/1/3">Air Force Act</a>'
    c = make_client(cfg, db, tmp_path, site({search: httpx.Response(200, text=html)}, robots=None))
    [r] = indiacode.discover(cfg, db, c, only=["act-air-force-1950"])
    assert r.status == "unresolved" and len(r.candidates) == 2
    assert db.conn.execute("SELECT COUNT(*) FROM urls WHERE kind='document'").fetchone()[0] == 0


def test_discover_stops_when_blocked(cfg, db, tmp_path):
    def handler(req):
        return httpx.Response(404) if req.url.path == "/robots.txt" else httpx.Response(403)
    c = make_client(cfg, db, tmp_path, handler)
    results = indiacode.discover(cfg, db, c)
    assert [r.status for r in results] == ["blocked"]            # stopped at the first target
    assert c.requests_made == 2
    assert db.counts()["indiacode"]["skipped"] == 1


def test_unknown_target_rejected(cfg, db, tmp_path):
    with pytest.raises(KeyError):
        indiacode.discover(cfg, db, make_client(cfg, db, tmp_path), only=["act-nope-1900"])


# -------------------------------------------------------------------- fetch
def test_fetch_documents(cfg, db, tmp_path):
    c = make_client(cfg, db, tmp_path)
    indiacode.discover(cfg, db, c, only=["act-army-1950"])
    stats = fetch_documents(cfg, db, c, "indiacode", tmp_path)
    assert stats["downloaded"] == 3 and stats["duplicate"] == 1   # two notification URLs, same bytes
    assert stats["failed"] == 1 and stats["skipped"] == 1         # HTML error page; robots-disallowed
    row = db.get(ACT_PDF)
    raw = tmp_path / "data" / "raw" / "indiacode" / "1950" / f"{row['sha256']}.pdf"
    assert raw.read_bytes() == (FIX / "synthetic_act.pdf").read_bytes()
    sha = db.get(f"{BASE}/ViewFileUploaded?path=AC_CEN_SYNTH/notifications/&file=synthetic_sro_1.pdf")["sha256"]
    assert db.aliases(sha) == [f"{BASE}/ViewFileUploaded?path=AC_CEN_SYNTH/notifications/&file=synthetic_sro_1_copy.pdf"]
    assert "expected a PDF" in list(db.failures())[0]["last_error"]
    assert db.counts()["indiacode"]["queued"] == 0
    # nothing left: a second run makes no requests
    n = c.requests_made
    assert fetch_documents(cfg, db, c, "indiacode", tmp_path)["downloaded"] == 0 and c.requests_made == n


def test_fetch_retries_then_resumes(cfg, db, tmp_path):
    url = f"{BASE}/doc.pdf"
    db.enqueue(url, "indiacode", "www.indiacode.nic.in", "document", meta={"year": "1950"})
    c = make_client(cfg, db, tmp_path, site({}, robots=None) if False else
                    (lambda req: httpx.Response(404) if req.url.path == "/robots.txt" else httpx.Response(503)))
    assert fetch_documents(cfg, db, c, "indiacode", tmp_path)["retry_later"] == 1
    row = db.get(url)
    assert row["status"] == "queued" and row["attempts"] == 1 and row["next_attempt_at"]


# ---------------------------------------------------------------------- CLI
def test_cli_discover_replay_keeps_live_state_clean(tmp_path, capsys):
    rc = main(["--root", str(tmp_path), "discover", "--source", "indiacode", "--only", "act-army-1950",
               "--replay", str(FIX), "--json"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0 and out["targets"] == {"act-army-1950": "resolved"} and out["requests"] == 3
    assert out["plan"]["totals"]["would_fetch"] == 6
    assert (tmp_path / "state" / "replay.sqlite").exists()
    assert not (tmp_path / "state" / "crawl.sqlite").exists()


def test_cli_live_discover_refused_with_placeholder_email(tmp_path, capsys):
    assert main(["--config", str(placeholder_config(tmp_path)), "--root", str(tmp_path),
                 "discover", "--source", "indiacode"]) == 3
    assert "contact email" in capsys.readouterr().err


def test_cli_fetch_needs_confirmation(tmp_path, capsys):
    assert main(["--root", str(tmp_path), "fetch", "--source", "indiacode", "--replay", str(FIX)]) == 3
    main(["--root", str(tmp_path), "discover", "--source", "indiacode", "--only", "act-army-1950",
          "--replay", str(FIX), "--json"])
    capsys.readouterr()
    assert main(["--root", str(tmp_path), "fetch", "--source", "indiacode", "--replay", str(FIX),
                 "--yes-download"]) == 0
    assert json.loads(capsys.readouterr().out)["downloaded"] == 3
    assert not (tmp_path / "data").exists()                       # replay files stay out of data/
    assert list((tmp_path / "state" / "replay_data" / "data" / "raw" / "indiacode" / "1950").glob("*.pdf"))


def test_cli_discover_unbuilt_source(tmp_path, capsys):
    assert main(["--root", str(tmp_path), "discover", "--source", "mod", "--replay", str(FIX)]) == 2
