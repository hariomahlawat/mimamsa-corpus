# C13 A7: review of open crawler PRs #7, #8, #9, #17 and #23

Reviewed 2026-11-25 from git objects only (`refs/pull/N/head` fetched into local `pr-N` refs). Nothing was merged,
closed or commented on. Staging baseline: `legal-knowledge/v2.5-staging` = `a4c0c382`. Corpus baseline: 4,121
distinct source copies (HF `3864faf3`). This review is one input. It is not the sole review: the coordinator arranges
independent review.

Evidence files (all in this folder):
- `pr_review/PR_PIN_CHECK_C13.csv` and `PR_PIN_CHECK_SUMMARY.txt`: every pinned document in the PRs compared with the corpus. Rebuild with `tools/pr_pin_check.py --check`.
- `pr_review/CORPUS_BYTE_INDEX.csv.gz`: sha256, md5 and size of 4,087 corpus copies hashed locally, plus 41 copies listed with sha256 only from the C12 registers. Rebuild with `tools/corpus_md5_index.py --check`.
- `allowlist/ARCHIVE_ITEM_NODES.csv`: live archive.org metadata for every PR pin not held in the corpus.
- `proposed/crawler_revision/*.patch`: the proposed revision (section 4).

## 1. Structure and dependency order

| PR | Head | Base branch (GitHub) | Draft | Commits beyond staging | Purpose |
|---|---|---|---|---|---|
| #7 | `feec0103` | `main` (`21de3531`) | yes | 3 (incl. main's `21de3531`) | Remove `aftjabalpur.in` from the AFT allow-list. Block it and every subdomain (`is_blocked_host`). Report URLs to blocked hosts anywhere in a source as config errors. Guard tests and a CI workflow on Python 3.13 |
| #8 | `1b948727` | `claude/crawler-security-aftjabalpur` (#7) | yes | +2 | ACQ-01: 12 archive.org Gazette pins (md5 and size in `note`) and 2 India Code Acts (`official_instruments`). `require_https` per source and per redirect hop. `host_allowed` with `"*.archive.org"` wildcard support. Registers `archive` and `official_instruments` in the CLI |
| #9 | `97933ccf` | `claude/acq-01-config` (#8) | yes | +2 (one is a merge of #8) | DESW source (`desw.gov.in`), 3 exact HTTPS URLs, disabled, no hash pins |
| #17 | `b8ee3176` | `claude/acq-01-config` (#8) | no | +4 | ACQ-02: 16 archive.org pins (sha256, md5 and bytes). **Fetch-time integrity check** (`crawler/fetch.py::integrity_problem`) applied before a file is stored or marked fetched. `tools/acquisition/verify_batch.py` and a runbook |
| #23 | `60715342` | `claude/acq-02-config` (#17) | no | +5 | ACQ-03: 36 archive.org pins and 3 India Code pins (listing md5 and size, `HOST_WATERMARKS_PDF`). Acquisition matrix and docs |

The order is **#7 → #8 → {#9, #17 → #23}**. #9 and #17 are siblings on #8; #9 is not on the #17 line.

Two structural problems:
1. **#7 targets `main`, not staging.** `21de3531` (main) is not an ancestor of `a4c0c382`. Merging the stack into
   staging therefore also brings main's commit `21de3531` ("Log the filter fix…"): `PROGRESS.md`, a 242-line
   rewrite of `reports/ocr_review.md`, and a 1.1 MB `state/wider_terms_hits.json`. None of that is crawler security.
2. All five PRs branch from `ee5aa586`, before the Cycle 7–12 work. Staging has not touched `config/`, `crawler/`
   or the crawler tests since then: `git diff ee5aa586 a4c0c382 -- config crawler` is empty. So the PRs still
   merge without **textual** conflicts (`git merge-tree --write-tree a4c0c382 pr-N` is clean for all five). A trial
   merge of the full #23 stack onto staging (scratch commit `c2449b30`, not a branch) passes:
   - 123 crawler, acquisition and HF-guard tests;
   - `crawler config-check`;
   - the C12 research-isolation test and the C5/C6 source tests (76 passed).

   The #9 trial merge passes 58 tests.

## 2. Are the security changes already in staging `a4c0c382`?

**No.** None of the 13 PR commits is in staging by patch identity (`git cherry -v a4c0c382 pr-23`: all `+`).

| Control | Staging `a4c0c382` | Where it exists |
|---|---|---|
| `aftjabalpur.in` removed from `sources.aft.allowed_hosts` | **Still listed** (`config/sources.yaml` line 193). The `aft` source is `enabled: false`, so the crawler does not contact it today | PR #7 |
| `aftjabalpur.in` (and subdomains) on `blocked_hosts` | No | PR #7 |
| Subdomain-aware blocking (`is_blocked_host`) and config error for a blocked URL anywhere in a source | No (exact host match only) | PR #7 |
| `NEVER_CONTACT` | Only inside C12 audit tools (`C12-CONSOLIDATION/acquisition/tools/acquire.py`, `build_targets.py`, `judicial_recovery_c12`). These are not used by `crawler/` | C12 audit tools; this workstream's `tools/a7net.py` |
| `require_https` per source and per redirect hop | No | PR #8 |
| Fetch-time integrity pins | No | PR #17 |
| HTTP `From` header only when `MIMAMSA_CONTACT_EMAIL` is set | **No.** `crawler/http.py` always sends `defaults.contact_email`. No PR changes this | C12 `acquire.py` only; proposed revision patch 0003 |
| Crawler security CI workflow | No (staging has `hf-sync-guard-ci`, `legal-audit-kit-ci` and `sync-legal-knowledge-hf`) | PR #7 |

The security fix of #7 is still needed on staging. This is the main finding of this review.

## 3. Are the acquisition manifests still accurate against the corpus?

72 pinned documents were compared with the 4,121-copy corpus (`PR_PIN_CHECK_C13.csv`).

| PR / source | Pinned | Already in corpus, byte-identical (sha256 or md5) | Already in corpus, other match | Not in corpus |
|---|---|---|---|---|
| #8 `archive` (ACQ-01) | 12 | **9**: the C5 working-store copies preserved at HF `5524c3d9`, among them S.R.O. 484/1954, 116/1965, 215/1965, 188/1979, 216/1988, 17(E)/1993, 8(E)/2003, 17(E)/2019 and 6(E)/2022 | 1: Act 19/1955 is held as the India Code copy (different carrier, manual identity) | 2: S.O. 488/1978 (Adjustment of Jurisdiction Rules) and S.O. 4010/1986 |
| #8 `official_instruments` | 2 | 0 | 2: Acts 13/1975 and 37/1992 are held as India Code copies in the C5 register (watermarked download, so no byte pin is possible) | 0 |
| #9 `desw` | 3 | 0 | 1: the 13 MB ER 2023 copy. Its note gives sha256 prefix `29f6fa2c`, which equals C5-SRC-P1-ER-2023-HELD-13MB (preserved). This is a prefix match only | 2: the 49.9 MB ER 2023 copy and GMO 2023 (no hash pins in the PR) |
| #17 `archive_acq02` (ACQ-02) | 16 | **16 of 16** (sha256 equal) | 0 | 0 |
| #23 `archive_acq03` (ACQ-03) | 36 | 0 | 0 | **36**. All 36 pins equal live archive.org metadata (md5 and size, 2026-11-25) |
| #23 `official_instruments_acq03` | 3 | 0 | **3**: the same India Code bitstream URL is already a crawler copy in `data/raw/indiacode` (AFT Procedure Rules 2008, the 2011 amendment, Practice Rules 2009) | 0 |
| **Total** | **72** | **25** | **7** | **40** |

Conclusions:
- **ACQ-02 (#17) is fully superseded as an acquisition manifest.** Every file is already preserved byte-identically.
- **ACQ-01 (#8) is mostly superseded.** 9 of 12 are byte-identical in the corpus and 3 more are held as other carriers. Only 2 Gazette issues remain.
- **ACQ-03 (#23) is still valid for its 36 archive.org pins.** Pin accuracy is confirmed against live metadata. Its 3 India Code entries duplicate existing crawler copies and should be dropped.
- This workstream's acquisition run (`acquisition/`) fetched part of the ACQ-03 set directly from the **government host
  egazette.gov.in**, which is allow-listed. These are byte-identical to the archive.org pins (`PIN_VERIFIED`). See the README for counts. Those items no longer need archive.org at all.

## 4. Conflicts with later crawler and corpus changes

| Later change | Interaction |
|---|---|
| `scripts/hf_protect.py`, `push_hf.py` additive guard (C12, ADR-0004) | No file overlap. **Process conflict:** the #17 runbook (`docs/acquisition/ACQUISITION_RUNBOOK.md`) commits `data/raw` on a git data branch and says "still no HF upload". That predates ADR-0004. Under current governance, originals go to HF additively with `parent_commit` pinned, re-downloaded and verified, and recorded in git. The runbook must be revised or dropped |
| C12 acquisition tool (`C12-CONSOLIDATION/acquisition/tools/acquire.py`) | It reads an exact-host allow-list from a sources.yaml snapshot. A `"*.archive.org"` entry from #8, #17 or #23 would be carried as a literal string. It is harmless there, but it is the broad redirect trust the C13 brief rejects |
| C13 A1 relevance states (`claude/c13-a1-ocr`) | The branch is still at `a4c0c382` (no commits; checked 2026-11-25). No state names exist to conflict with. The PRs do not add relevance states. Their runbook sends fetched files straight to `python -m pipeline all`, which bypasses any A1 relevance or duplicate gate. Recommendation: no ingestion from these PRs without the A1 gate |
| C13 directive: no broad trust of redirect destinations | #8, #17 and #23 all add `allowed_hosts: [archive.org, "*.archive.org"]`, which trusts every archive.org subdomain for any path. **Not acceptable.** This workstream observed that redirects for the same item go to nodes not named in the item metadata, e.g. `dn790002.ca.archive.org/0/items/…` while metadata lists `ia902803/ia802803` (`acquisition/ACQUISITION_MANIFEST_C13.csv`). A static list therefore needs per-item host sets. The replacement is `redirect_scopes` (exact host plus one `/<n>/items/<identifier>/` prefix); see `AUTHORISED_SCOPE_C13.md` |
| `From` header policy (C12 §10 item 7) | Not addressed by any PR; fixed in revision patch 0003 |
| egazette.gov.in TLS | Not addressed by any PR. Root cause and fix are in `allowlist/EGAZETTE_TLS_C13.md`. Patch 0003 adds `ca_extra_pem` with SHA-256 pins and strict chain building |

## 5. Code review notes (beyond the scope questions)

- #7 `is_blocked_host`: correct suffix match on a dot boundary (`x.aftjabalpur.in` is blocked; `notaftjabalpur.in` is not). The CI step's string search for "aftjabalpur" outside `blocked_hosts` is a useful belt-and-braces guard.
- #8 `host_allowed` wildcard: the suffix test is correct (look-alike domains are refused), but the design is the problem. `check_config` uses `h.lstrip("*.")`, which strips characters, not a prefix. It is harmless for current values but fragile; patch 0003 replaces it.
- #17 `integrity_problem`: sound. It runs before `store` and before `mark_fetched`. It parses the ACQ-01 `note` pins and treats India Code `listing_*` as informational, which is right for watermarked serving.
- #9: no `expected_sha256` for any of its 3 documents, although the 13 MB copy is held and its full sha256 is known (C5 register). Robots: `desw.gov.in/robots.txt` answers 403, treated as "no robots file" (RFC 9309), as #9 states. Probed again 2026-11-25 with the same result.

## 6. Recommendations

| PR | Recommendation | Reason |
|---|---|---|
| **#7** | **Integrate, revised:** re-target to staging as the two security commits only (`8394f041`, `feec0103`), without main's `21de3531` | Security fix still missing on staging: `aftjabalpur.in` is still in `sources.aft.allowed_hosts`. A clean replay onto `a4c0c382` is `proposed/crawler_revision/0001` and `0002`. `PROGRESS.md` conflicts with main's log, so staging's copy was kept |
| **#8** | **Revise** (code), **close as superseded** (manifest) | Keep `require_https` and the per-hop check. Replace `"*.archive.org"` with item-scoped `redirect_scopes` (patch 0003). Of the 14 pins, 12 are held. Carry the 2 remaining (S.O. 488/1978, S.O. 4010/1986) into a fresh, reviewed target list |
| **#9** | **Revise**, keep as draft until the allow-list decision (D-04) | `desw.gov.in` validates: TLS chain OK (Sectigo), robots 403 (= none), no CAPTCHA or password field on the landing page. Add `expected_sha256` for the held 13 MB copy. Scope as exact URLs only (`AUTHORISED_SCOPE_C13.md`) |
| **#17** | **Close as superseded** for ACQ-02; **salvage** the fetch-time integrity code and tests (included in patch 0003) and `verify_batch.py` | All 16 ACQ-02 files are already preserved byte-identically. The runbook conflicts with ADR-0004 |
| **#23** | **Revise** | Drop the 3 India Code entries (already crawler copies). Drop the wildcard. Route items that egazette.gov.in serves byte-identically via the government host. Keep the remaining archive.org pins (which match live metadata) for a reviewed `redirect_scopes` decision |

The proposed replacement (patches `0001`–`0003`, applied to a scratch worktree from `a4c0c382`) passes:
- the PR #7 security tests;
- the #17 fetch-integrity tests;
- new `tests/test_crawler_c13_hardening.py`;
- `test_crawler_foundation`, `test_aft` and `test_indiacode` (updated for the `From` opt-in);
- `crawler config-check`.

Across the crawler-related test selection, 201 passed, 1 skipped and 0 failed after the `test_indiacode` update. One collection error, in `tests/test_legal_audit_retrospective_deemed.py`, is pre-existing on staging (`ModuleNotFoundError: test_legal_audit_check_registers`) and unrelated.

The patches change code only. The live `config/sources.yaml` changes are a separate proposal (`proposed/sources.yaml.diff`) for coordinator acceptance.
