"""ACQ-02 acquisition-configuration guards (PROPOSED scope, separate from ACQ-01). Offline: no network.
Pins the exact 16 ACQ-02 documents with expected hashes, and proves the ACQ-01 list (PR #8) is unchanged."""
import re
import socket

import pytest

from crawler.cli import DISCOVERERS
from crawler.config import DEFAULT_CONFIG, check_config, load_config
from tests.test_acquisition_config import EXPECTED as ACQ01_EXPECTED

ACQ02 = {
    "notif-army-rules-amdt-sro-205-1961": ("https://archive.org/download/in.gazette.central.w.1961-07-22.87578/87578.pdf", "0b4c5b72ea3de650a97d573af317ed6147c62539a1890a64c5797eaf4f60da6d"),
    "notif-army-rules-amdt-sro-1-1961": ("https://archive.org/download/in.gazette.central.w.1962-01-06.85365/85365.pdf", "b76bf4aac230f922b472a8ce69fb6f75bfe67f311591c39c21fca10996d8b778"),
    "notif-army-rules-r188e-sro-34-1963": ("https://archive.org/download/in.gazette.central.w.1963-01-19.84713/84713.pdf", "4acdb1a8bc6430db30edb1046d839c177f90f97e82466d7373039d0f5289c935"),
    "notif-army-rules-amdt-sro-126-1964": ("https://archive.org/download/in.gazette.central.w.1964-03-28.83274/83274.pdf", "cce0d06e8624cc677eb3165e5cb9dd569766286175013323398e2dd8490ca07a"),
    "notif-army-rules-amdt-sro-5-1968": ("https://archive.org/download/in.gazette.central.w.1969-01-11.68677/68677.pdf", "5126efa258a7e7502d20d1539618aba549a4a5977068480eac0ceb00b780e3c3"),
    "notif-army-rules-amdt-sro-246-1982": ("https://archive.org/download/in.gazette.central.w.1982-11-13.41015/41015.pdf", "d283767e91508eb9239ca8291904d381a94dc27abb5275a3870b318b57d3d868"),
    "notif-army-rules-amdt-sro-44-1985": ("https://archive.org/download/in.gazette.central.w.1985-02-16.34755/34755.pdf", "dd6978db8cf47f2f7b3c9ea1fecaeaf462f03d6562a20268edc68d5d0514c7b7"),
    "notif-army-rules-amdt-sro-55-1985": ("https://archive.org/download/in.gazette.central.w.1985-03-09.34758/34758.pdf", "d8ce1958a9bf8fd1581e665190b245a7dd0f265f91ebb4330813728a00e1e1f1"),
    "notif-army-rules-amdt-sro-68-1985": ("https://archive.org/download/in.gazette.central.w.1985-04-20.34763/34763.pdf", "225f624b866c8ab0931492e245b5cb3dbfb9b996bad627a9acbe8dff89e5392b"),
    "notif-army-rules-amdt-sro-278-1985": ("https://archive.org/download/in.gazette.central.w.1985-12-28.34794/34794.pdf", "972e5aa18dda6f41737f1d726451ad231b13adf79c297f1f2aeb096230efbc67"),
    "notif-army-rules-amdt-sro-169-1987": ("https://archive.org/download/in.gazette.central.w.1987-05-30.30211/30211.pdf", "eaa233f8c70ae0b9ba15b7fc26154f98d61a4c3812e87a4779d0838c9befa682"),
    "notif-army-rules-amdt-sro-302-1987": ("https://archive.org/download/in.gazette.central.w.1987-10-10.30228/30228.pdf", "4392f326c1b9bbc906b99e9b811c95d99f5e8887ee229848af148bef3f82b0da"),
    "notif-army-rules-amdt-sro-44-and-61-1991": ("https://archive.org/download/in.gazette.central.w.1991-02-23.21285/21285.pdf", "0e4b8e47e299867f8a8ead184cd88dfe2b2a0e08ea8faca70bec42be58e12a18"),
    "notif-army-rules-amdt-sro-235-1991": ("https://archive.org/download/in.gazette.central.w.1991-11-09.21312/21312.pdf", "dc67b628878ea4c5ac11b4013fecd6bf29d852ab5d6c7601f4d58a6f3ac3ac24"),
    "notif-army-rules-r188e-sro-2e-2018": ("https://archive.org/download/in.gazette.central.e.2018-02-20.183010/183010.pdf", "7c12a7ecc849c8f6df96830b093fda3c16bf9e943a5cb5d331ae3352b9455551"),
    "notif-army-rules-amdt-sro-332-1989": ("https://archive.org/download/in.gazette.central.w.1989-12-02.25809/25809.pdf", "31fedb68e25a1ffa999b8d809b6138b272275c0acc1abd9f5da502564b485147"),
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


def test_exact_acq02_list(cfg):
    got = {x["doc_id"]: (x["url"], x["expected_sha256"]) for x in cfg.source("archive_acq02")["documents"]}
    assert got == ACQ02


def test_acq01_scope_unchanged(cfg):
    for source, expected in ACQ01_EXPECTED.items():
        assert {x["doc_id"]: x["url"] for x in cfg.source(source)["documents"]} == expected, source


def test_scopes_do_not_overlap(cfg):
    acq01 = {u for exp in ACQ01_EXPECTED.values() for u in exp.values()}
    assert not acq01 & {u for u, _ in ACQ02.values()}


def test_integrity_fields_and_dates(cfg):
    for x in cfg.source("archive_acq02")["documents"]:
        assert re.fullmatch(r"[0-9a-f]{64}", x["expected_sha256"]), x["doc_id"]
        assert re.fullmatch(r"[0-9a-f]{32}", x["expected_md5"]), x["doc_id"]
        assert int(x["expected_bytes"]) > 0, x["doc_id"]
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", x["issue_date"]), x["doc_id"]
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", x["gazette_publication_date"]), x["doc_id"]
        assert "effective_date" not in x, "no effective date may be asserted from a publication date"


def test_https_allowed_and_disabled(cfg):
    assert not cfg.source("archive_acq02").get("enabled")
    assert DISCOVERERS["archive_acq02"].__name__.endswith("direct")
    for doc_id, (url, _) in ACQ02.items():
        assert url.startswith("https://archive.org/download/"), doc_id
        assert cfg.is_url_allowed("archive_acq02", url)[0], doc_id


@pytest.mark.parametrize("url", ["http://103.154.2.123/x.pdf", "https://aftjabalpur.in/x", "https://archive.org.evil.com/x", "https://evilarchive.org/x"])
def test_refusals(cfg, url):
    assert not cfg.is_url_allowed("archive_acq02", url)[0]


def test_config_has_no_errors(cfg):
    assert check_config(cfg).errors == []


@pytest.mark.parametrize("host", ["dn760006.eu.archive.org", "dn790000.ca.archive.org", "ia800000.us.archive.org"])
def test_archive_redirect_hosts_allowed_for_acq02(cfg, host):
    assert cfg.is_url_allowed("archive_acq02", f"https://{host}/x/y.pdf")[0]


@pytest.mark.parametrize("url", ["http://dn760006.eu.archive.org/x.pdf", "https://archive.org.attacker.net/x.pdf",
                                 "https://www.indiankanoon.org/x", "https://indiacode.gov.in/x"])
def test_acq02_refuses_http_offsite_and_other_sources(cfg, url):
    assert not cfg.is_url_allowed("archive_acq02", url)[0]


def test_acq02_requires_https(cfg):
    assert cfg.source("archive_acq02").get("require_https") is True
