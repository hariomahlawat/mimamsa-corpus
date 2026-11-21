"""Supreme Court / High Court collection from the open-data buckets, against in-memory indexes."""
import io
import json
import socket

import httpx
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from crawler import opendata
from crawler.audit import AuditLog
from crawler.config import DEFAULT_CONFIG, check_config, load_config
from crawler.http import PoliteClient
from crawler.state import StateDB

SC = "https://indian-supreme-court-judgments.s3.ap-south-1.amazonaws.com"
HC = "https://indian-high-court-judgments.s3.ap-south-1.amazonaws.com"


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


def parquet(rows):
    buf = io.BytesIO()
    pq.write_table(pa.Table.from_pylist(rows), buf)
    return httpx.Response(200, content=buf.getvalue(), headers={"content-type": "binary/octet-stream"})


def client(cfg, db, tmp_path, source, pages):
    seen = []

    def handler(req):
        seen.append(str(req.url))
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        return pages.get(str(req.url), httpx.Response(404))
    c = PoliteClient(cfg, AuditLog(tmp_path / "logs", db, "t"), source, transport=httpx.MockTransport(handler), replay=True)
    return c, seen


SC_ROWS = [
    {"title": "DHARAMVIR SINGH versus UNION OF INDIA & ORS.", "petitioner": "DHARAMVIR SINGH", "respondent": "UNION OF INDIA & ORS.",
     "judge": "A.K. PATNAIK", "citation": "[2013] 8 S.C.R. 1119", "case_id": "2013 INSC 408", "cnr": "ESCR010007152013",
     "decision_date": "02-07-2013", "disposal_nature": "Appeal(s) allowed", "path": "2013_8_1119_1148", "nc_display": "2013INSC408",
     "raw_html": "<select>big</select>"},
    {"title": "NOVARTIS AG versus STATE OF X", "petitioner": "NOVARTIS AG", "respondent": "STATE OF X", "judge": "AFTAB ALAM",
     "citation": "", "case_id": "2013 INSC 198", "cnr": "ESCR1", "decision_date": "01-04-2013", "disposal_nature": "Dismissed",
     "path": "2013_13_148_290", "nc_display": "2013INSC198", "raw_html": ""},
    {"title": "EX. NAIK RAM versus STATE", "petitioner": "EX. NAIK RAM", "respondent": "STATE", "judge": "X", "citation": "",
     "case_id": "", "cnr": "ESCR2", "decision_date": "", "disposal_nature": "", "path": None, "nc_display": "", "raw_html": ""},
]


def test_parse_years_and_config_rules(cfg, tmp_path):
    assert opendata.parse_years("2013") == [2013] and opendata.parse_years("2009-2011") == [2009, 2010, 2011]
    assert opendata.parse_years([2022, 2023]) == [2022, 2023]
    assert check_config(cfg).errors == []
    assert cfg.setting("sci", "min_delay_seconds") < 1 and cfg.setting("indiacode", "min_delay_seconds") >= 2
    import yaml
    raw = yaml.safe_load(DEFAULT_CONFIG.read_text(encoding="utf-8"))
    raw["sources"]["indiacode"]["min_delay_seconds"] = 0.3            # a government site may not go below the floor
    raw["sources"]["sci"]["party_terms"] = ["(unclosed"]
    p = tmp_path / "s.yaml"
    p.write_text(yaml.safe_dump(raw), encoding="utf-8")
    errs = check_config(load_config(p)).errors
    assert any("indiacode.min_delay_seconds" in e for e in errs) and any("party_terms[0]" in e for e in errs)


def test_supreme_court_year_is_preselected_by_parties(cfg, db, tmp_path):
    c, seen = client(cfg, db, tmp_path, "sci", {f"{SC}/metadata/parquet/year=2013/metadata.parquet": parquet(SC_ROWS)})
    [r] = opendata.discover(cfg, db, c, "sci", only=["2013"])
    assert (r.status, r.index_rows, r.candidates, r.queued, r.no_pdf) == ("ok", 3, 2, 1, 1)
    url = f"{SC}/data/pdf/year=2013/english/2013_8_1119_1148_EN.pdf"
    row = db.get(url)
    meta = json.loads(row["meta"])
    assert row["kind"] == "document" and row["status"] == "queued"
    assert meta["dataset"] == "indian-supreme-court-judgments" and meta["year"] == "2013"
    assert meta["index"]["case_id"] == "2013 INSC 408" and "raw_html" not in meta["index"]
    assert db.get(f"{SC}/data/pdf/year=2013/english/2013_13_148_290_EN.pdf") is None      # not a defence party
    c2, seen2 = client(cfg, db, tmp_path, "sci", {})
    [again] = opendata.discover(cfg, db, c2, "sci", only=["2013"])
    assert again.status == "already_known" and seen2 == []
    [none] = opendata.discover(cfg, db, c2, "sci", only=["1949"])
    assert none.status == "no_index"


def test_high_court_slice_reads_every_bench(cfg, db, tmp_path):
    listing = ("<ListBucketResult><Prefix>metadata/parquet/year=2023/court=7_26/</Prefix>"
               "<CommonPrefixes><Prefix>metadata/parquet/year=2023/court=7_26/bench=dhcdb/</Prefix></CommonPrefixes>"
               "<CommonPrefixes><Prefix>metadata/parquet/year=2023/court=7_26/bench=other/</Prefix></CommonPrefixes></ListBucketResult>")
    rows = [{"title": "W.P.(C)/7395/2023 of NIKHIL MANDAL Vs UNION OF INDIA & ORS.", "cnr": "DLHC010210552023",
             "pdf_link": "court/cnrorders/dhcdb/orders/DLHC010210552023_1_2023-05-26.pdf", "decision_date": "2023-05-26 00:00:00",
             "judge": "A,B", "pdf_exists": "False", "court": "High Court of Delhi", "raw_html": "x"},
            {"title": "CS/1/2023 of A LTD Vs B LTD", "cnr": "DLHC2", "pdf_link": "x/DLHC2_1_2023-01-01.pdf",
             "decision_date": "2023-01-01 00:00:00", "judge": "", "pdf_exists": "True", "court": "High Court of Delhi", "raw_html": ""}]
    c, seen = client(cfg, db, tmp_path, "hc", {
        f"{HC}/?list-type=2&prefix=metadata/parquet/year=2023/court=7_26/&delimiter=/": httpx.Response(200, text=listing),
        f"{HC}/metadata/parquet/year=2023/court=7_26/bench=dhcdb/metadata.parquet": parquet(rows)})
    [r] = opendata.discover(cfg, db, c, "hc", only=["delhi:2023"])
    assert (r.index_rows, r.candidates, r.queued) == (2, 1, 1) and any("bench other" in w for w in r.warnings)
    row = db.get(f"{HC}/data/pdf/year=2023/court=7_26/bench=dhcdb/DLHC010210552023_1_2023-05-26.pdf")
    meta = json.loads(row["meta"])
    assert meta["court_key"] == "delhi" and meta["bench"] == "dhcdb" and meta["court_name"] == "High Court of Delhi"
    with pytest.raises(KeyError):
        opendata.discover(cfg, db, c, "hc", only=["nowhere:2023"])


def test_parallel_fetch_is_only_for_buckets_and_keeps_the_audit_trail(cfg, db, tmp_path):
    from crawler.fetch import fetch_documents
    from crawler.http import CrawlError
    pdf = b"%PDF-1.4 judgment "
    urls = [f"{SC}/data/pdf/year=2013/english/j{i}_EN.pdf" for i in range(7)]
    for u in urls:
        db.enqueue(u, "sci", "indian-supreme-court-judgments.s3.ap-south-1.amazonaws.com", "document",
                   meta={"year": "2013", "filename": u.rsplit("/", 1)[-1], "dataset": "indian-supreme-court-judgments"})
    pages = {u: httpx.Response(200, content=pdf + str(i).encode(), headers={"content-type": "application/pdf"})
             for i, u in enumerate(urls[:5])}
    pages[urls[5]] = httpx.Response(503)
    c, seen = client(cfg, db, tmp_path, "sci", pages)                      # urls[6] is not in the bucket: 404
    stats = fetch_documents(cfg, db, c, "sci", tmp_path, limit=50, workers=4)
    assert stats["downloaded"] == 5 and stats["retry_later"] == 1 and stats["failed"] == 1
    assert len(list((tmp_path / "data" / "raw" / "sci" / "2013").glob("*.pdf"))) == 5
    assert db.conn.execute("SELECT COUNT(*) FROM requests").fetchone()[0] == 8       # robots.txt + 7 files, all logged
    assert db.get(urls[5])["status"] == "queued" and db.get(urls[6])["status"] == "failed"
    gov, _ = client(cfg, db, tmp_path, "indiacode", {})
    with pytest.raises(CrawlError):
        gov.get_many(["https://indiacode.gov.in/a"], 4)
    # a government source asked for workers still goes one at a time
    db.enqueue("https://indiacode.gov.in/a.pdf", "indiacode", "indiacode.gov.in", "document", meta={})
    assert fetch_documents(cfg, db, gov, "indiacode", tmp_path, workers=8)["failed"] == 1
