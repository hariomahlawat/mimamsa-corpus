# Consolidated acquisition matrix (prepared 2026-11-22; NO download authorised)

Each batch is a separate approval scope: (1) its configuration PR, then (2) a download run for that source key only. This applies across the whole stack PR #7 → #8 → #17 → #23. Common controls for all batches:
- `require_https: true`;
- the per-source allow-list, applied on **every redirect hop** (archive.org `/download` redirects to `dnNNNNNN.*.archive.org`);
- `blocked_hosts` (aftjabalpur.in, commercial legal databases);
- robots.txt obeyed, at most 1 request per 2 s per host;
- sources `enabled: false` and run only with `--yes-download`;
- **fetch-time integrity enforcement** (`crawler/fetch.py::integrity_problem`, PR #17): a mismatch is rejected before storage;
- an offline re-check (`tools/acquisition/verify_batch.py`);
- page-image identity re-check on the record copies;
- no HF upload.

| Batch / source key | PR | Docs | Host and authority (policy v1) | Integrity controls | Est. volume | Verification after fetch | Unresolved access issues | Research gaps it closes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ACQ-01 `archive` | #8 | 12 | archive.org (Public.Resource.Org Gazette scans): `ENACTED_OR_NOTIFIED_PRIMARY`, carried as `THIRD_PARTY_ARCHIVAL_FACSIMILE`, authenticity `ARCHIVAL_FACSIMILE_OF_OFFICIAL` | md5 + size (archive.org metadata) enforced at fetch | 20.9 MB | `verify_batch --source archive`, ACQ-01 `verify_acquisition.py`, page-image checks PIC-10..36 on the record copies | none | Record copies of S.R.O. 484/1954 (r.23(3) C-01 evidence), 8 amending S.R.O.s, S.O. 488/1978, S.O. 4010/1986, Act 19/1955 Gazette |
| ACQ-01 `official_instruments` | #8 | 2 | indiacode.gov.in (Gazette scans on India Code): `ENACTED_OR_NOTIFIED_PRIMARY`, carried as `GOVERNMENT_HOSTED_COPY` | Served bytes are download-specific: SHA-256 recorded; identity by page image (listing values informational) | 0.2 MB | `verify_batch` (CHECKSUM_RECORDED_ONLY) + page image | none | Act 13/1975, Act 37/1992 (ss.75–76, 127 omitted) |
| ACQ-02 `archive_acq02` | #17 | 16 files / 17 instruments | archive.org: as ACQ-01 archive | sha256 + md5 + size enforced at fetch | 10.5 MB | `verify_batch --source archive_acq02` + re-check PIC-12..36 on the record copies | none | Record copies for the Army Rules instrument register (r.193 C-08, r.194 C-09, r.13A, r.15A, r.16A, r.147, r.184, r.187(1)) |
| ACQ-03 `archive_acq03` | #23 | 36 | archive.org (one item has a derivative PDF only, flagged) | md5 + size enforced at fetch | 29.8 MB | `verify_batch --source archive_acq03` + **first** page-image identity checks (OCR identities are locators only) | none for these 36 | 13 amendment hints 1956–1974 (AR-012/013/015, AR-037..046); 5 OCR-only amendments (AR-002..005, AR-032); Mar–Apr 1964 issues (r.187(1), OQ-C-06); commencement and adaptation instruments; Acts in the Army Act chain |
| ACQ-03 `official_instruments_acq03` | #23 | 3 | indiacode.gov.in: AFT rules, `GOVERNMENT_HOSTED_COPY` | **Listing md5/size informational only** (host watermark); served SHA-256 recorded; must be a PDF; optional `expected_served_sha256` pin | 48.4 MB (listing sizes) | `verify_batch` + page image | none | "Rule 4-12" in V7-T01..07 (OQ-D-005): AFT (Procedure) Rules 2008, Amendment 2011, Practice Rules 2009 |
| Not configured | – | 4 | none known | – | – | – | **No lawful online source:** E-7/1960; anything after 06-06-2022 (egazette.gov.in fails TLS verification; never bypassed); S.R.O. 258/2002; Army Act 1950 as enacted | Custodian letter (signed by the owner) or an Indian-network egazette search |
| Not configured | – | 1 | archive.org `19490.pdf` (ACQ03-016) | – | – | – | **Owner decision:** duplicate (by md5) of the ACQ-01 India Code Act 37/1992 bitstream | – |

**Totals for configured batches:** 69 files, about 110 MB:
- ACQ-01: 14 files, 21.1 MB;
- ACQ-02: 16 files, 10.5 MB;
- ACQ-03: 39 files, 78.2 MB.

**Approvals needed, each separately:**
1. ACQ-01: merge #7 and #8, then a download run for `archive` and one for `official_instruments`.
2. ACQ-02: #17, then a download run for `archive_acq02`.
3. ACQ-03: #23, then a download run for `archive_acq03` and one for `official_instruments_acq03`; plus keep or drop ACQ03-016.
