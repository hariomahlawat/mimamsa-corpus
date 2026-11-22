# Controlled acquisition runbook: ACQ-01 and ACQ-02 (prepared 2026-11-22; NOT executed)

Each batch is a **separate approval scope**. Run a batch only after the owner has approved (1) its configuration PR and (2) a download run for that batch. Never combine batches in one approval.

| Batch | Config | Source key(s) | Documents | Pre-committed integrity |
| --- | --- | --- | --- | --- |
| ACQ-01 (B1, B2, B6) | PR #8 | `archive` (12), `official_instruments` (2) | 14 | 12 archive.org: md5 + bytes (in `note`). 2 India Code: URL + item identity only (download-specific bytes); SHA-256 recorded after the fetch |
| ACQ-02 | PR #17 | `archive_acq02` | 16 files / 17 instruments | sha256 + md5 + bytes (`expected_*`) |
| ACQ-03 | not yet configured (separate PR after approval) | – | 40 with URL (+4 with no online source) | md5 + bytes from metadata (WS-A `acq03_pinned_candidates.csv`) |

**Controls in force:**
- allow-list per source, applied on every redirect hop;
- `require_https: true` on all three sources (a plain-HTTP URL or hop is refused);
- `blocked_hosts` includes aftjabalpur.in and commercial legal databases;
- robots.txt is obeyed, at most 1 request per 2 s per host;
- sources stay `enabled: false` and are run only explicitly with `--yes-download`.

Evidence of the pre-run checks: `docs/acquisition/inventory_match_2026-11-22.txt` (config vs approved inventories: all match; the 3 flagged items are explained there) and `legal_knowledge/audit_work/ACQ-02/config_pr_evidence/`.

## Exact commands (run from the repository root, on a NEW data branch off the merged crawler config)
```bash
git switch -c claude/acq-01-data            # or claude/acq-02-data; never on main or staging
python -m pip install -r requirements.txt
python -m crawler config-check
python -m crawler init-db
# ACQ-01
python -m crawler dry-run --source archive
python -m crawler dry-run --source official_instruments
python -m crawler fetch --source archive --yes-download
python -m crawler fetch --source official_instruments --yes-download
python -m pipeline all
python tools/acquisition/verify_batch.py --source archive --out reports/acq01_archive_verify.tsv
python tools/acquisition/verify_batch.py --source official_instruments --out reports/acq01_indiacode_verify.tsv
python legal_knowledge/audit_work/ACQ-01/verify_acquisition.py        # audit-branch checker (archive md5/size), after integration
# ACQ-02 (separate approval)
python -m crawler dry-run --source archive_acq02
python -m crawler fetch --source archive_acq02 --yes-download
python -m pipeline all
python tools/acquisition/verify_batch.py --source archive_acq02 --out reports/acq02_verify.tsv
```

**Fetch-time integrity (added after the PR #17 review):** `crawler/fetch.py` rejects a file before storing it or marking it fetched if it differs from pinned `expected_sha256` / `expected_md5` / `expected_bytes`, the ACQ-01 `note` md5/size, or a pinned `expected_served_sha256`. India Code `listing_*` values are informational only. `verify_batch.py` then re-checks the stored copies offline.

**Stop conditions:**
- Any FAIL from `verify_batch.py` (size, md5 or sha256 differs from the pre-committed value): do not commit the file; report it.
- Any refused URL, redirect off the allow-list, HTTP hop, login page, CAPTCHA or 4xx/5xx after retries: stop and report.

## After a successful batch (still no HF upload)
1. Commit `data/raw`, `data/meta`, `data/text`, `state` logs and the verify report on the data branch, and open a PR. CI runs.
2. Page-image re-check on the **record copies**: same pages and DPI as PIC-10..36 (ACQ-01 items) or PIC-12..36 (ACQ-02 items). Record render SHA-256 in a new register; the source SHA-256 must equal the pre-verified value.
3. Acquisition register: one row per document with doc_id, URL, retrieved_at, sha256, md5, bytes, verify status, PIC ids, and policy-v1 fields (`document_authority`, `carrier_provenance`, `authenticity`, `copy_fidelity`).
4. Separate review proposals for any changed legal finding. The Rule 23(3) CONFLICTING, C-08 OPEN and C-09 PROPOSAL states change only by legal review.
