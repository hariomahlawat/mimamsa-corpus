# ACQ-01: prioritised source-acquisition execution plan (for owner review)

**DATABASE ONLY. Status: EXECUTION-READY, NOT EXECUTED.** Nothing has been downloaded into `data/`, uploaded, or sent. Original records are unchanged.

Files:
- `batches.json`: 6 batches, 21 items, with doc_id, URL, provenance class, metadata fields and the findings each item feeds.
- `archive_org_metadata_snapshot.json`: archive.org file names, MD5 and size for 14 items, captured read-only before the run.
- `proposed_archive_documents.yaml`: `documents:` entries for `sources.archive`, **not applied**.
- `verify_acquisition.py`: offline post-run check. Currently `PENDING=14 SKIP=7`.
- `AFT_ROUTE_ASSESSMENT.md`.

The evidence rule throughout is `docs/legal-audit/SOURCE_AUTHORITY_POLICY.md (v1)` (owner rule, 2026-11-22). An archival reproduction of an official Gazette is a **copy of the primary instrument** (`ARCHIVAL_FACSIMILE_OF_OFFICIAL`), weighed by its custody checks and never treated as commentary.

## Preservation rules (every batch)
- Raw bytes are stored unmodified at `data/raw/archive/<yyyy>/<sha256>.pdf` (or the source's own folder), named by SHA-256 and never edited.
- The metadata record (`schema/document.schema.json`) holds:
  - `source: archive`
  - `source_url`: the exact archive.org download URL
  - `source_aliases`: the archive.org details URL
  - `retrieved_at`, `sha256`, `raw_path`, `page_count`
  - `issue_date`: the notification date
  - `effective_date`: null unless stated in the instrument
  - `number` (S.R.O./S.O./Act no.), `issuing_authority`
  - `status: unknown` until reviewed
  - `access_marking`: as printed, else null
  - `field_provenance`: curated fields marked as curated
  - a note with the Gazette issue, Part and pages, uploader and collection
- After fetch, `verify_acquisition.py` must show MD5 and size equal to the pre-committed archive.org values, and SHA-256 equal to the metadata record.
- A page-image check of the operative provisions is recorded in a `page_image_checks` register (render SHA-256) before any finding cites the item.
- No legal finding changes status because a document was acquired; delta reviews follow, then legal review.

## Batches in priority order
| Batch | Content | Items | Route | Ready now? | Approval / action needed |
| --- | --- | --- | --- | --- | --- |
| **B1** | **S.R.O. 484 (27-11-1954)** and 8 amending S.R.O.s: 116/1965, **215/1965**, 188/1979, 216/1988, 17(E)/1993, 8(E)/2003, 17(E)/2019, 6(E)/2022 | 9 | archive.org (host already allow-listed under `sources.archive`) | **Yes**, from this container | (1) Approve the run. (2) Approve a config PR adding the `documents` list to `sources.archive` and enabling it. **Gap:** S.R.O. 258/2002 not located (egazette or custodian) |
| **B2** | **Adjustment of Jurisdiction Rules 1978** (S.O. 488 of 09-02-1978, Gazette 25-02-1978 p.525) and **S.O. 4010** (dated 24-11-1986, Gazette 06-12-1986) | 2 | archive.org | **Yes** | Same as B1. **Gap:** post-BNSS rules (egazette) |
| **B3** | **Regulations for the Army 1987**: Ch V extract (India Code); complete copy; 1927 historical edition | 3 | India Code / owner upload / archive.org | Extract and historical: yes. Complete: **no** | You supply the complete official copy and **state its access marking**. If restricted, it gets the same controls as the MML (private; derived text not committed) |
| **B4** | **Entitlement Rules 2023** and **GMO 2023** (DESW) | 2 | desw.gov.in | After allow-list change | Approve adding `desw.gov.in` (official MoD/DESW host) to an official-copies source. **Gap:** ER 1982, ER 2008 and GMO 2008 not found on reachable hosts (Indian-network run, or owner copy) |
| **B5** | AFT static listings on `aft.gov.in` (about 44 PDFs: reportable judgments, larger-bench references, RB review cases) | ~44 | aft.gov.in (HTTP) plus PDF host `103.154.2.123` (bare IP, HTTP) | After decision | Decide whether the bare-IP PDF host and HTTP transport are acceptable, with provenance from the referring official page. The portal's judgment search is **CAPTCHA-gated and will not be used.** Bulk AFT judgments still need an Indian-network bench run |
| **B6** | Army Act amending Acts: 19/1955 (Gazette Extraordinary), 13/1975, 37/1992 | 3 | archive.org / India Code | **Yes** | Approve the run |

## Run sequence after approval (commands, all dry-run first)
1. Config PR (separate, needs approval): apply `proposed_archive_documents.yaml` to `sources.archive`, set `enabled: true`, **and map `"archive": direct` in `DISCOVERERS` (`crawler/cli.py` line 32)**, which currently has no `archive` entry. CI: `check_config` and the crawler security tests.
2. `python -m crawler config-check`, then `python -m crawler dry-run --source archive`: what would be fetched; no network. Review the output.
3. `python -m crawler discover --source archive`: for a `documents` list this queues each address after the allow-list check, with no network requests (`crawler/direct.py`). Then `python -m crawler status`.
4. `python -m crawler fetch --source archive --yes-download`: at most 1 request every 2 s; resumable; every request in the audit log.
5. `python -m pipeline all` for metadata, text and OCR (OCR will be needed for older Gazette scans).
6. `python legal_knowledge/audit_work/ACQ-01/verify_acquisition.py`: must report 0 FAIL.
7. Page-image checks for each operative provision; then delta reviews of affected findings (UQ-01, F-STAT-001/006/010/019/022, F-REM-001, F-PROC-018, MMLPKT-01/03/04/05).
8. No HF upload and no push to `raw-data` without your separate approval.

## Interaction with the Rule 23(3) review
B1 brings the 1954 instrument and its amending S.R.O.s into the corpus with verified bytes. R23-VERIFY-01 (second independent examination and amendment chain) works from research copies in the scratchpad and is independent of this run. **CONFLICTING status is retained until legal review** (owner instruction).

## Correction (2026-11-22, from R23-VERIFY-01)
The archive.org item first listed as "S.R.O. 34/1963" (`in.gazette.central.w.1963-01-19.84713`) carries S.R.O. 34 of 05-01-1963, a **declaration under r.188, not an amendment**. It is excluded from B1 (`batches.json` → `excluded_items`; removed from `proposed_archive_documents.yaml`). The amending **S.R.O. 34 of 05-06-1963** cited in official notes is not located. Further amendment-chain gaps are added to B1: 17 amending S.R.O.s of 1960–1991, S.R.O. 2(E)/2018, and anything after 06-06-2022. B1 therefore holds **9 items** (S.R.O. 484 plus 8 amendments) and 13 archive documents in total across batches.
