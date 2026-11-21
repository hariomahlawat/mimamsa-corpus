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

FIX = Path(__file__).parent / "fixtures" / "indiacode_api"     # recorded from the live API
BASE = "https://indiacode.gov.in"
API = f"{BASE}/server/api"
ACT_URL = f"{API}/core/items/60fd2882-1df9-4b4d-8a70-3add0a9f5b6b"


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
    raw["defaults"]["contact_email"] = "CHANGE-ME@example.org"
    p = tmp_path / "placeholder.yaml"
    p.write_text(yaml.safe_dump(raw), encoding="utf-8")
    return p


def test_live_client_refuses_placeholder_user_agent(db, tmp_path):
    with pytest.raises(UserAgentNotSet):
        PoliteClient(load_config(placeholder_config(tmp_path)), AuditLog(tmp_path / "logs", db, None), "indiacode")


def test_identifies_itself_with_from_header_not_email_in_user_agent(cfg, db, tmp_path):
    seen = []

    def handler(req):
        seen.append((req.headers.get("user-agent"), req.headers.get("from")))
        return httpx.Response(404) if req.url.path == "/robots.txt" else httpx.Response(200, text="x")
    make_client(cfg, db, tmp_path, handler).get(f"{BASE}/a")
    assert len(seen) == 2
    for ua, sender in seen:
        assert ua == cfg.defaults["user_agent"] and "@" not in ua and "Mozilla" not in ua
        assert sender == cfg.defaults["contact_email"] and "@" in sender


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
    c2 = make_client(cfg, db, tmp_path, robots_down, source="archive")
    with pytest.raises(RobotsDisallowed):
        c2.get("https://archive.org/a")


def _robots_times_out(req):
    if req.url.path == "/robots.txt":
        raise httpx.ReadTimeout("hang", request=req)
    return httpx.Response(200, text="x")


def test_unreachable_robots_exception_is_per_source(cfg, db, tmp_path):
    # indiacode has robots_unreachable: allow -> proceeds, and says so
    c = make_client(cfg, db, tmp_path, _robots_times_out)
    assert c.get(f"{BASE}/a").status == 200 and c.robots_exception_used
    # archive has no exception -> still refuses
    c2 = make_client(cfg, db, tmp_path, _robots_times_out, source="archive")
    with pytest.raises(RobotsDisallowed):
        c2.get("https://archive.org/a")


def test_exception_does_not_cover_served_rules_or_5xx(cfg, db, tmp_path):
    c = make_client(cfg, db, tmp_path, site({f"{BASE}/private/x": httpx.Response(200, text="x")}))
    with pytest.raises(RobotsDisallowed):
        c.get(f"{BASE}/private/x")

    def robots_500(req):
        return httpx.Response(500) if req.url.path == "/robots.txt" else httpx.Response(200, text="x")
    # indiacode also has robots_5xx: allow; a source without it still refuses on a 5xx
    c5 = make_client(cfg, db, tmp_path, robots_500)
    assert c5.get(f"{BASE}/a").status == 200 and c5.robots_exception_used
    with pytest.raises(RobotsDisallowed):
        make_client(cfg, db, tmp_path, robots_500, source="archive").get("https://archive.org/a")


def test_exception_needs_a_reason(tmp_path):
    from crawler.config import check_config
    raw = yaml.safe_load(DEFAULT_CONFIG.read_text(encoding="utf-8"))
    raw["sources"]["archive"]["robots_unreachable"] = "allow"
    p = tmp_path / "s.yaml"
    p.write_text(yaml.safe_dump(raw), encoding="utf-8")
    assert any("robots_unreachable_reason" in e for e in check_config(load_config(p)).errors)


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


# ------------------------------------------------------- API answer helpers
def test_normalise_title():
    assert indiacode.normalise_title("The Army Act, 1950") == indiacode.normalise_title("ARMY ACT 1950")
    assert indiacode.normalise_title("The Indian Army Act, 1911") != indiacode.normalise_title("The Army Act, 1950")


def test_file_language_by_name():
    assert indiacode.file_language("a1950-46.pdf") == "en" and indiacode.file_language("A2007-55.pdf") == "en"
    assert indiacode.file_language("H195046.pdf") == "hi" and indiacode.file_language("h195045.pdf") == "hi"
    assert indiacode.file_language("armyrules1954.pdf") is None and indiacode.file_language(None) is None


def _search_answer(*records):
    objs = [{"_embedded": {"indexableObject": {"uuid": u, "name": name, "metadata": {
        "dc.identifier.collection": [{"value": "ACT"}], "dc.date.act_year": [{"value": yr}],
        "dc.identifier.state_name": [{"value": state}]}}}} for u, name, yr, state in records]
    return {"_embedded": {"searchResult": {"page": {}, "_embedded": {"objects": objs}}}}


def test_central_copy_is_chosen_over_state_copies_and_number_year_is_tolerated(cfg, db, tmp_path):
    # act_year on the record is the year of the Act number, which can differ from the year in the title
    answer = _search_answer(("u-mh", "The Bharatiya Nagarik Suraksha Sanhita, 2023", "2024", "MAHARASHTRA"),
                            ("u-central", "THE BHARATIYA NAGARIK SURAKSHA SANHITA, 2023", "2024", "CENTRAL"),
                            ("u-up", "Bharatiya Nagarik Suraksha Sanhita, 2023", "2024", "UTTAR PRADESH"))
    seen = []

    def item(req):
        seen.append(str(req.url))
        return httpx.Response(404)
    c = make_client(cfg, db, tmp_path, _replay_with({"/discover/search/objects?query=": httpx.Response(200, json=answer),
                                                     "/core/items/": item}))
    [r] = indiacode.discover(cfg, db, c, only=["act-bnss-2023"])
    assert seen and "/core/items/u-central" in seen[0]            # went on to the CENTRAL record
    assert r.status == "failed"                                   # (that record is not in the test data)


def test_two_central_copies_stay_unresolved(cfg, db, tmp_path):
    answer = _search_answer(("u1", "The Bharatiya Nyaya Sanhita, 2023", "2023", "CENTRAL"),
                            ("u2", "The Bharatiya Nyaya Sanhita, 2023", "2023", "CENTRAL"))
    c = make_client(cfg, db, tmp_path, _replay_with({"/discover/search/objects?query=": httpx.Response(200, json=answer)}))
    [r] = indiacode.discover(cfg, db, c, only=["act-bns-2023"])
    assert r.status == "unresolved" and len(r.candidates) == 2


def test_original_bitstreams_ignores_other_bundles():
    bs = lambda name: {"name": name, "uuid": "u-" + name, "sizeBytes": 5,
                       "checkSum": {"checkSumAlgorithm": "MD5", "value": "abc"},
                       "_links": {"content": {"href": f"{API}/core/bitstreams/u-{name}/content"}}}
    wrap = lambda name, files: {"name": name, "_embedded": {"bitstreams": {"_embedded": {"bitstreams": files}}}}
    payload = {"_embedded": {"bundles": [wrap("ORIGINAL", [bs("a.pdf")]), wrap("TEXT", [bs("a.pdf.txt")]),
                                         wrap("THUMBNAIL", [bs("a.pdf.jpg")])]}}
    files = indiacode.original_bitstreams(payload)
    assert [f["filename"] for f in files] == ["a.pdf"] and files[0]["md5"] == "abc"


# ------------------------------------------- discovery (recorded real pages)
def test_discover_army_act_from_recorded_api(cfg, db, tmp_path):
    c = make_client(cfg, db, tmp_path)
    [r] = indiacode.discover(cfg, db, c, only=["act-army-1950"])
    assert r.status == "resolved" and r.act_url == ACT_URL
    assert r.metadata["dc.identifier.act_number"] == "46" and r.metadata["dc.date.enact_date"] == "1950-05-20"
    assert r.act_pdfs == 2
    assert r.linked == {"ACT": 1, "RULE": 1, "SCHEDULE": 1, "SECTION": 198} and r.linked_pages == 3
    assert r.subordinate_files == {"RULE": 1, "SCHEDULE": 1}
    assert r.newly_queued == 7 and r.warnings == []               # expected Army Rules, 1954 are linked
    # the Act text (a1950-46.pdf, named after the record's givenid) carries the doc_id; the other file does not
    tagged = db.conn.execute("SELECT url, meta FROM urls WHERE doc_id_hint='act-army-1950' AND kind='document'").fetchall()
    assert len(tagged) == 1 and json.loads(tagged[0]["meta"])["filename"] == "a1950-46.pdf"
    assert json.loads(tagged[0]["meta"])["md5"] == "0ae0daa20971e6d3e95dd6055c4f01f0"
    kinds = dict(db.conn.execute("SELECT json_extract(meta,'$.category'), COUNT(*) FROM urls "
                                 "WHERE kind='document' GROUP BY 1").fetchall())
    assert kinds == {"act": 2, "linked_records": 3, "rule": 1, "schedule": 1}
    assert db.counts()["indiacode"]["queued"] == 7 and db.counts()["indiacode"]["failed"] == 0
    # second run: nothing re-fetched
    c2 = make_client(cfg, db, tmp_path)
    [r2] = indiacode.discover(cfg, db, c2, only=["act-army-1950"])
    assert r2.status == "already_known" and c2.requests_made == 0


def _replay_with(overrides):
    """The recorded pages, with some answers replaced."""
    inner = replay_transport(FIX)

    def handler(req):
        for needle, resp in overrides.items():
            if needle in str(req.url):
                return resp(req) if callable(resp) else resp
        return inner.handler(req)
    return handler


def test_discover_warns_when_expected_rules_missing(cfg, db, tmp_path):
    def no_rules(req):
        body = replay_transport(FIX).handler(req).content.replace(b"Army Rules,1954", b"Something else")
        return httpx.Response(200, content=body, headers={"content-type": "application/hal+json"})
    c = make_client(cfg, db, tmp_path, _replay_with({"f.act_id=": no_rules}))
    [r] = indiacode.discover(cfg, db, c, only=["act-army-1950"])
    assert r.status == "resolved" and any("Army Rules, 1954" in w for w in r.warnings)


def test_discover_never_guesses(cfg, db, tmp_path):
    # Not in the replay set: the search answers 404 -> failed, nothing queued.
    c = make_client(cfg, db, tmp_path)
    [r] = indiacode.discover(cfg, db, c, only=["act-navy-1957"])
    assert r.status == "failed" and db.counts()["indiacode"]["queued"] == 0

    # The search answers, but with no exact title match -> unresolved, candidates listed.
    rec = lambda name, uuid: {"_embedded": {"indexableObject": {
        "uuid": uuid, "name": name, "metadata": {"dc.identifier.collection": [{"value": "ACT"}],
                                                  "dc.date.act_year": [{"value": "1950"}]}}}}
    answer = {"_embedded": {"searchResult": {"page": {"totalElements": 2}, "_embedded": {"objects": [
        rec("The Air Force (Amendment) Act, 1950", "u1"), rec("Air Force Act", "u2")]}}}}
    c = make_client(cfg, db, tmp_path, _replay_with({"/discover/search/objects?query=": httpx.Response(200, json=answer)}))
    [r] = indiacode.discover(cfg, db, c, only=["act-air-force-1950"])
    assert r.status == "unresolved" and len(r.candidates) == 2
    assert db.conn.execute("SELECT COUNT(*) FROM urls WHERE kind='document'").fetchone()[0] == 0


def test_discover_wrong_year_is_not_a_match(cfg, db, tmp_path):
    # Only applies when the target's title has no year in it (here: "Regulations for the Army", 1987).
    answer = _search_answer(("u1", "Regulations for the Army", "1962", "CENTRAL"))
    c = make_client(cfg, db, tmp_path, _replay_with({"/discover/search/objects?query=": httpx.Response(200, json=answer)}))
    [r] = indiacode.discover(cfg, db, c, only=["regs-army-1987"])
    assert r.status == "unresolved"


def test_discover_stops_when_login_is_required(cfg, db, tmp_path):
    def handler(req):
        return httpx.Response(404) if req.url.path == "/robots.txt" else httpx.Response(401)
    c = make_client(cfg, db, tmp_path, handler)
    results = indiacode.discover(cfg, db, c)
    assert [r.status for r in results] == ["blocked"]            # stopped at the first target
    assert c.requests_made == 2
    assert db.counts()["indiacode"]["skipped"] == 1


def test_discover_reports_unexpected_api_shape(cfg, db, tmp_path):
    c = make_client(cfg, db, tmp_path, _replay_with({"/discover/search/objects?query=": httpx.Response(200, json={"x": 1})}))
    [r] = indiacode.discover(cfg, db, c, only=["act-army-1950"])
    assert r.status == "failed" and "expected shape" in r.reason


def test_unknown_target_rejected(cfg, db, tmp_path):
    with pytest.raises(KeyError):
        indiacode.discover(cfg, db, make_client(cfg, db, tmp_path), only=["act-nope-1900"])


# -------------------------------------------------------------------- fetch
PDF_A = b"%PDF-1.4 test file A"
PDF_B = b"%PDF-1.4 test file B"


def _md5(b):
    import hashlib
    return hashlib.md5(b).hexdigest()


def _queue(db, url, **meta):
    db.enqueue(url, "indiacode", "indiacode.gov.in", "document", meta=meta)


def test_fetch_documents(cfg, db, tmp_path):
    u = lambda n: f"{API}/core/bitstreams/{n}/content"
    pages = {u("a"): httpx.Response(200, content=PDF_A, headers={"content-type": "application/pdf"}),
             u("a2"): httpx.Response(200, content=PDF_A, headers={"content-type": "application/pdf"}),
             u("bad-md5"): httpx.Response(200, content=PDF_B, headers={"content-type": "application/pdf"}),
             u("html"): httpx.Response(200, text="<html>error</html>", headers={"content-type": "text/html"}),
             f"{API}/discover/search/objects?page=0": httpx.Response(200, json={"ok": 1},
                                                                     headers={"content-type": "application/hal+json"}),
             f"{API}/private/x": httpx.Response(200, content=PDF_A)}
    _queue(db, u("a"), filename="a1950-46.pdf", md5=_md5(PDF_A), year="1950", category="act")
    _queue(db, u("a2"), filename="copy.pdf", md5=_md5(PDF_A), category="rule")           # same bytes, no year
    _queue(db, u("bad-md5"), filename="b.pdf", md5=_md5(PDF_A), year="1954")
    _queue(db, u("html"), filename="c.pdf", md5=None, year="1954")
    _queue(db, f"{API}/discover/search/objects?page=0", category="linked_records", year="1950")
    _queue(db, f"{API}/private/x", filename="p.pdf")
    c = make_client(cfg, db, tmp_path, site(pages, robots="User-agent: *\nDisallow: /server/api/private/\n"))
    stats = fetch_documents(cfg, db, c, "indiacode", tmp_path)
    assert stats["downloaded"] == 3 and stats["duplicate"] == 1
    assert stats["failed"] == 1 and stats["skipped"] == 1
    assert stats["checksum_differs_from_listing"] == 1            # kept, counted (site watermarks PDFs)
    sha = db.get(u("a"))["sha256"]
    assert (tmp_path / "data" / "raw" / "indiacode" / "1950" / f"{sha}.pdf").read_bytes() == PDF_A
    assert db.aliases(sha) == [u("a2")]
    jsha = db.get(f"{API}/discover/search/objects?page=0")["sha256"]
    assert (tmp_path / "data" / "raw" / "indiacode" / "1950" / f"{jsha}.json").exists()
    assert ["expected a PDF" in f["last_error"] for f in db.failures()] == [True]
    assert db.counts()["indiacode"]["queued"] == 0
    n = c.requests_made
    assert fetch_documents(cfg, db, c, "indiacode", tmp_path)["downloaded"] == 0 and c.requests_made == n


def test_fetch_retries_then_resumes(cfg, db, tmp_path):
    url = f"{API}/core/bitstreams/x/content"
    _queue(db, url, filename="x.pdf", year="1950")
    c = make_client(cfg, db, tmp_path,
                    lambda req: httpx.Response(404) if req.url.path == "/robots.txt" else httpx.Response(503))
    assert fetch_documents(cfg, db, c, "indiacode", tmp_path)["retry_later"] == 1
    row = db.get(url)
    assert row["status"] == "queued" and row["attempts"] == 1 and row["next_attempt_at"]


# ---------------------------------------------------------------------- CLI
def test_cli_discover_replay_keeps_live_state_clean(tmp_path, capsys):
    rc = main(["--root", str(tmp_path), "discover", "--source", "indiacode", "--only", "act-army-1950",
               "--replay", str(FIX), "--json"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0 and out["targets"] == {"act-army-1950": "resolved"} and out["requests"] == 9
    assert out["plan"]["totals"]["would_fetch"] == 7
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
    out = json.loads(capsys.readouterr().out)
    # the three recorded pages of linked records are saved; the PDFs are not in the recording (404)
    assert out["downloaded"] == 3 and out["failed"] == 4
    assert not (tmp_path / "data").exists()                       # replay files stay out of data/
    assert len(list((tmp_path / "state" / "replay_data" / "data" / "raw" / "indiacode" / "1950").glob("*.json"))) == 3


def test_cli_discover_unbuilt_source(tmp_path, capsys):
    assert main(["--root", str(tmp_path), "discover", "--source", "mod", "--replay", str(FIX)]) == 2


def test_repealed_record_target_goes_straight_to_its_record(cfg, db, tmp_path):
    uuid = "972afbe0-a2de-415d-9df5-8d70038056ad"
    item = {"uuid": uuid, "name": "The Indian Penal Code, 45 of 1860 (Rep., Act 45 of 2023)", "handle": "123456789/488475",
            "metadata": {"dc.date.issued": [{"value": "1860"}]}}
    bundles = {"_embedded": {"bundles": [{"name": "ORIGINAL", "_embedded": {"bitstreams": {"_embedded": {"bitstreams": [
        {"name": "A1860-45.pdf", "uuid": "b1", "sizeBytes": 10, "checkSum": {"checkSumAlgorithm": "MD5", "value": "x"},
         "_links": {"content": {"href": f"{API}/core/bitstreams/b1/content"}}}]}}}}]}}
    seen = []

    def handler(req):
        url = str(req.url)
        seen.append(url)
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        if url.endswith("/owningCollection"):
            return httpx.Response(200, json={"name": "Repeal Acts"})
        if "/bundles" in url:
            return httpx.Response(200, json=bundles)
        if url.endswith(uuid):
            return httpx.Response(200, json=item)
        return httpx.Response(404)
    c = make_client(cfg, db, tmp_path, handler)
    [r] = indiacode.discover(cfg, db, c, only=["act-ipc-1860"])
    assert r.status == "resolved" and r.warnings == [] and r.act_pdfs == 1 and r.newly_queued == 1
    assert not any("discover/search" in u for u in seen)          # no title search, no linked-record pages
    row = db.get(f"{API}/core/bitstreams/b1/content")
    assert row["doc_id_hint"] == "act-ipc-1860"
    assert json.loads(row["meta"])["repeal_record"]["collection_name"] == "Repeal Acts"


# ------------------------------------------------ hand-listed documents
def test_direct_documents_are_queued_without_any_request(tmp_path, db):
    from crawler import direct
    raw = yaml.safe_load(DEFAULT_CONFIG.read_text(encoding="utf-8"))
    raw["sources"]["official_copies"]["documents"] = [
        {"doc_id": "act-x-1900", "url": "https://crpf.mha.gov.in/a/x%20y.pdf", "title": "X Act", "doc_type": "act", "year": 1900},
        {"doc_id": "ref-off-list", "url": "https://example.org/t.pdf", "title": "T", "doc_type": "reference"},
        {"doc_id": "ref-bad", "url": "https://crpf.mha.gov.in/b.pdf", "doc_type": "reference"}]
    p = tmp_path / "s.yaml"
    p.write_text(yaml.safe_dump(raw), encoding="utf-8")
    cfg = load_config(p)
    res = {r.doc_id: r for r in direct.discover(cfg, db, None, "official_copies")}
    assert res["act-x-1900"].status == "queued" and res["ref-off-list"].status == "refused"
    assert res["ref-bad"].status == "invalid" and "title" in res["ref-bad"].reason
    row = db.get("https://crpf.mha.gov.in/a/x%20y.pdf")
    meta = json.loads(row["meta"])
    assert row["doc_id_hint"] == "act-x-1900" and meta["filename"] == "x y.pdf" and meta["year"] == "1900"
    assert meta["direct"]["title"] == "X Act" and "url" not in meta["direct"]
    assert db.counts()["official_copies"]["queued"] == 1
    assert direct.discover(cfg, db, None, "official_copies", only=["act-x-1900"])[0].status == "already_known"
