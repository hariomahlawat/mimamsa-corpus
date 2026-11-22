# ACQ-03 approval request (separate scope; NOT executed)

**What:** 39 files pinned in two disabled crawler sources, prepared from WS-A `acq03_pinned_candidates.csv` (commit 4930b181; copied here unchanged).
- `archive_acq03`: 36 archive.org files (Gazette issues and Acts). md5 and bytes come from archive.org `/metadata` (`source=original` except where noted).
- `official_instruments_acq03`: 3 India Code files (AFT rules). India Code watermarks PDFs when serving them, so the ORIGINAL-bundle md5/size are kept only as `listing_md5`/`listing_bytes` (informational, never enforced). After an approved fetch the **served SHA-256** is recorded; identity is established by a page-image check of the record copy; once reviewed, the served SHA-256 may be pinned (`expected_served_sha256`) so any later change is rejected.
- Total about 78.2 MB. HTTPS is required, the allow-list applies on every redirect hop, and blocked hosts are refused.

| Batch | Files | Purpose (register rows closed) |
| --- | --- | --- |
| B1 | 9 | Army Rules amendment hints 1966–1974 (AR-012/013/015, AR-041..046) |
| B2 | 5 | OCR-only amendments: S.R.O. 331/348/351/404 of 1960, S.R.O. 22/2010 (AR-002..005, AR-032) |
| B3 | 3 | Acts in the Army Act chain (Act 37/1992 archive copy excluded; see below) |
| B4 | 7 | Commencement and adaptation instruments found on archive.org (S.R.O. 2(E)/1955, Adaptation Order 1956, Ordinance 3/1975 [derivative PDF only], Act 20/1983 and its commencement notification, Act 4/2018, probable 1950 Army Act commencement notification) |
| B5 | 6 | AFT rules ("Rule 4-12", OQ-D-005): AFT (Procedure) Rules 2008, Amendment 2011, Practice Rules 2009 |
| C2 | 9 | Pre-1960 amendments (AR-037..040) and the Mar–Apr 1964 issues for r.187(1) (OQ-C-06) |

**Not pinned:**
- ACQ03-016 (archive.org `19490.pdf`, Act 37/1992): byte-identical by md5 to the India Code bitstream already in ACQ-01. Optional; owner decision.
- 4 items with no known lawful online source: E-7/1960, post-06-06-2022 (egazette fails TLS verification; not bypassed), S.R.O. 258/2002, Army Act 1950 as enacted. Routes: custodian letter or an Indian-network egazette search.

**Evidence:** `config_pr_evidence/` holds config-check OK; discover with 0 network requests; dry-run queuing 36 + 3; pytest 180 passed. `tests/test_acquisition_config_acq03.py` pins all 39 entries (URL, md5, bytes) and proves ACQ-01 and ACQ-02 unchanged and disjoint.

**Approvals requested (each separate):**
1. This configuration PR.
2. A download run for `archive_acq03`, and separately for `official_instruments_acq03`, per `docs/acquisition/ACQUISITION_RUNBOOK.md` with `verify_batch.py --source <key>`.
3. Keep or drop ACQ03-016.

After a run: reject any archive.org file whose md5 or bytes differ, reject any India Code file that is not a PDF or that differs from a pinned served SHA-256, re-run page-image checks on the record copies, and keep every OCR/FTS identity as a locator until then.
