"""ACQ-03 acquisition-configuration guards (PROPOSED scope, separate from ACQ-01 and ACQ-02). Offline: no network.
Pins the exact 39 ACQ-03 documents (36 archive.org, 3 India Code) with expected md5/bytes, and proves ACQ-01/ACQ-02 unchanged."""
import socket

import pytest

from crawler.cli import DISCOVERERS
from crawler.config import DEFAULT_CONFIG, check_config, load_config
from tests.test_acquisition_config import EXPECTED as ACQ01_EXPECTED
from tests.test_acquisition_config_acq02 import ACQ02

ACQ03 = {
    "archive_acq03": {
        "acq03-001-b1": [
            "https://archive.org/download/in.gazette.central.w.1966-08-27.76274/76274.pdf",
            "db421593aff8a9d834387d16288f2c99",
            216518
        ],
        "acq03-002-b1": [
            "https://archive.org/download/in.gazette.central.w.1967-01-07.73211/73211.pdf",
            "b563f24104b7db4f7460a28d8eac78df",
            270581
        ],
        "acq03-003-b1": [
            "https://archive.org/download/in.gazette.central.w.1967-12-16.75707/75707.pdf",
            "fa551a7f1e5fb34697954af3b046172c",
            217120
        ],
        "acq03-004-b1": [
            "https://archive.org/download/in.gazette.central.w.1968-11-16.72289/72289.pdf",
            "d890fc7f2c663eeb103e5623d9a89a75",
            419587
        ],
        "acq03-005-b1": [
            "https://archive.org/download/in.gazette.central.w.1969-03-01.68684/68684.pdf",
            "55514cdfc31328a5a096d6d73a4d906e",
            119819
        ],
        "acq03-006-b1": [
            "https://archive.org/download/in.gazette.central.w.1970-01-17.63332/63332.pdf",
            "65222929bec3231ad4e4dda0c9965b40",
            199340
        ],
        "acq03-007-b1": [
            "https://archive.org/download/in.gazette.central.w.1972-02-19.59085/59085.pdf",
            "02d1de61bf35abe65426114ecf55824b",
            1278060
        ],
        "acq03-008-b1": [
            "https://archive.org/download/in.gazette.central.w.1974-08-17.55730/55730.pdf",
            "c2685d66ecf87a6d4e4b6b5e73bfbb21",
            881772
        ],
        "acq03-009-b1": [
            "https://archive.org/download/in.gazette.central.w.1974-11-16.55738/55738.pdf",
            "fcd50df7fd3a6bb11c2b8af7cbb2f8cc",
            963606
        ],
        "acq03-010-b2": [
            "https://archive.org/download/in.gazette.central.w.1960-10-08.88375/88375.pdf",
            "55ae76e704c63890433eb09113733d53",
            485922
        ],
        "acq03-011-b2": [
            "https://archive.org/download/in.gazette.central.w.1960-10-15.88376/88376.pdf",
            "ed9ca1f86e2f8da64945b942cdb8405a",
            214636
        ],
        "acq03-012-b2": [
            "https://archive.org/download/in.gazette.central.w.1960-10-22.88377/88377.pdf",
            "83928ad246754eaa82ef38e2dfb01c47",
            491131
        ],
        "acq03-013-b2": [
            "https://archive.org/download/in.gazette.central.w.1960-12-03.88383/88383.pdf",
            "d17443252551a276c5288e154e625c71",
            205584
        ],
        "acq03-014-b2": [
            "https://archive.org/download/in.gazette.central.w.2010-05-29.162/162.pdf",
            "23fa6e9e7fc4e1fcf0bde0edc54171e5",
            59988
        ],
        "acq03-015-b3": [
            "https://archive.org/download/in.gazette.e.1974.333/E-1272-1974-0084-56281.pdf",
            "7b057ed27bc13f8413777322f229e9f8",
            609985
        ],
        "acq03-017-b3": [
            "https://archive.org/download/in.gazette.central.e.2001-09-03.113421/113421.pdf",
            "ad667445cb12ee87f17f5fc1583434b8",
            654416
        ],
        "acq03-018-b3": [
            "https://archive.org/download/in.gazette.central.e.2018-12-28.195312/195312.pdf",
            "000aae1fe586cb369d9d40822591c9f7",
            2380441
        ],
        "acq03-019-b4": [
            "https://archive.org/download/in.gazette.1950.318/O-2345-1950-0013-108766.pdf",
            "c99cf4895e8f7d565cd739d2f411cd0e",
            130078
        ],
        "acq03-020-b4": [
            "https://archive.org/download/in.gazette.e.1955.15/E-2210-1955-0002-101603.pdf",
            "00dfb70630574c20c8a7e94be4502b57",
            21902
        ],
        "acq03-021-b4": [
            "https://archive.org/download/in.gazette.e.1956.717/E-2189-1956-0415-100172.pdf",
            "cfc5cb5cf1cdeac4cb34784b705d7639",
            1058089
        ],
        "acq03-022-b4": [
            "https://archive.org/download/in.gazette.csl_extraordinary.1975-01-25.E-1236-1975-0004-54581/E-1236-1975-0004-54581.pdf",
            "5d1011da90899da51a9c292580f1b391",
            95670
        ],
        "acq03-023-b4": [
            "https://archive.org/download/in.gazette.e.1983.330/E-0913-1983-0023-39490.pdf",
            "0f040ff6e5774797881ce86d2e46f050",
            1076879
        ],
        "acq03-024-b4": [
            "https://archive.org/download/in.gazette.e.1984.465/E-0871-1984-0057-37466.pdf",
            "6280672cd4f711d5cfc76edd381fd9ca",
            41367
        ],
        "acq03-025-b4": [
            "https://archive.org/download/in.gazette.central.e.2018-01-08.181639/181639.pdf",
            "d8e102cd6a3f83fcf16b84cfd01ee2b5",
            1489638
        ],
        "acq03-030-b5": [
            "https://archive.org/download/in.gazette.central.e.2008-09-17.2326/2326.pdf",
            "50cb5c011bf60c3b800e235061e8eb4e",
            760396
        ],
        "acq03-031-b5": [
            "https://archive.org/download/in.gazette.central.e.2011-07-29.188/188.pdf",
            "b3539b33452f645260495b00ad30fb6b",
            53537
        ],
        "acq03-032-b5": [
            "https://archive.org/download/in.gazette.central.e.2009-05-13.5014/5014.pdf",
            "e57de9958b8c03ee23530db1c4626f06",
            4805182
        ],
        "acq03-036-c2": [
            "https://archive.org/download/in.gazette.central.w.1956-04-21.100216/100216.pdf",
            "e7beb1e93861fa1675082279d642c2fe",
            301028
        ],
        "acq03-037-c2": [
            "https://archive.org/download/in.gazette.central.w.1958-12-13.95784/95784.pdf",
            "e7bc7dffabd2462806c58548ee8c68bb",
            34281
        ],
        "acq03-038-c2": [
            "https://archive.org/download/in.gazette.central.w.1958-12-27.95984/95984.pdf",
            "149cc60e8fd1ef4a99a8f5b6d9b48bc1",
            273444
        ],
        "acq03-039-c2": [
            "https://archive.org/download/in.gazette.central.w.1959-12-12.90633/90633.pdf",
            "46a839209f80079fadcf27bfa742e596",
            469276
        ],
        "acq03-040-c2": [
            "https://archive.org/download/in.gazette.central.w.1964-03-07.83271/83271.pdf",
            "95a16c6934b66e2cfa0ab54daa9655e7",
            8718476
        ],
        "acq03-041-c2": [
            "https://archive.org/download/in.gazette.central.w.1964-03-14.83272/83272.pdf",
            "1c4593472dd7bd2f862f2864ad222b45",
            105994
        ],
        "acq03-042-c2": [
            "https://archive.org/download/in.gazette.central.w.1964-03-21.83273/83273.pdf",
            "ab3e28d6ef54202463ae02082c59b083",
            439029
        ],
        "acq03-043-c2": [
            "https://archive.org/download/in.gazette.central.w.1964-03-30.83284/83284.pdf",
            "da88aeb1d88a544faa49ae47adae36fa",
            47852
        ],
        "acq03-044-c2": [
            "https://archive.org/download/in.gazette.central.w.1964-04-04.83285/83285.pdf",
            "c461bcb5629e0750444bc74c0859a633",
            236186
        ]
    },
    "official_instruments_acq03": {
        "acq03-033-b5": [
            "https://indiacode.gov.in/server/api/core/bitstreams/3a17342b-6811-4e2c-98c8-fc4954bf5a53/content",
            "c08af236bfd7c5bf79d25a858226d8f3",
            46767577
        ],
        "acq03-034-b5": [
            "https://indiacode.gov.in/server/api/core/bitstreams/5a416087-b3bd-4fa5-8fc8-e9b6768f2966/content",
            "dae2291aa84a37ea271b896340739ec6",
            163806
        ],
        "acq03-035-b5": [
            "https://indiacode.gov.in/server/api/core/bitstreams/18a102cd-fbb9-49de-9e80-b0c553ff25dd/content",
            "0fa7231285f2022db43a0150fb5817ea",
            1441674
        ]
    }
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


def test_exact_acq03_lists(cfg):
    for source, expected in ACQ03.items():
        got = {d["doc_id"]: [d["url"], d["expected_md5"], int(d["expected_bytes"])] for d in cfg.source(source)["documents"]}
        assert got == expected, source


def test_counts(cfg):
    assert len(ACQ03["archive_acq03"]) == 36 and len(ACQ03["official_instruments_acq03"]) == 3


def test_acq01_acq02_unchanged_and_disjoint(cfg):
    for source, expected in ACQ01_EXPECTED.items():
        assert {d["doc_id"]: d["url"] for d in cfg.source(source)["documents"]} == expected
    assert {d["doc_id"]: (d["url"], d["expected_sha256"]) for d in cfg.source("archive_acq02")["documents"]} == ACQ02
    acq03 = {v[0] for s in ACQ03.values() for v in s.values()}
    acq01 = {u for e in ACQ01_EXPECTED.values() for u in e.values()}
    assert not acq03 & acq01
    assert not acq03 & {u for u, _ in ACQ02.values()}


def test_https_required_disabled_and_discoverable(cfg):
    for source, docs in ACQ03.items():
        assert cfg.source(source).get("require_https") is True
        assert not cfg.source(source).get("enabled")
        assert DISCOVERERS[source].__name__.endswith("direct")
        for doc_id, (url, md5, size) in docs.items():
            assert url.startswith("https://"), doc_id
            assert cfg.is_url_allowed(source, url)[0], doc_id
            assert len(md5) == 32 and size > 0, doc_id


@pytest.mark.parametrize("url", ["http://archive.org/download/x/y.pdf", "http://103.154.2.123/x.pdf", "https://aftjabalpur.in/x",
                                 "https://archive.org.evil.com/x", "https://indiankanoon.org/x"])
def test_refusals(cfg, url):
    for source in ACQ03:
        assert not cfg.is_url_allowed(source, url)[0]


def test_india_code_source_cannot_reach_archive(cfg):
    assert not cfg.is_url_allowed("official_instruments_acq03", "https://archive.org/download/x/y.pdf")[0]
    assert not cfg.is_url_allowed("archive_acq03", "https://indiacode.gov.in/x")[0]


def test_config_has_no_errors(cfg):
    assert check_config(cfg).errors == []
