# Mimamsa next stage: source acquisition and database completeness (consolidated plan, 2026-11-22)

**DATABASE FIRST. NO APPLICATION WORK.** This is a plan with supporting review proposals. Nothing has been merged, uploaded, ingested or sent, and no legal finding has changed status. The 46-record calibration batch and the full 658-record audit are **not** started.

Supporting proposals, all new and in separate folders (nothing existing was edited):
- `ACQ-02/`: supplement for the 16 archival PDFs (integrity, identity and page-image checks)
- `ARMY-RULES-CHAIN-01/`: amendment-instrument register, provision chronology, official-note discrepancies, version-register seed
- `SOURCE-CONFLICTS-01/conflict_determinations_update_2026-11-22c.csv`: U-04 (r.193 new discrepancy), U-05 (unlisted amendments), U-06 (correction of an R23 register note)

---

## 1. PR dependency and integration sequence

### Current state (fetched 2026-11-22)
| PR | Head → base | Content | CI | Touches HF-sync trigger paths? |
| --- | --- | --- | --- | --- |
| #1 (owner) | `legal-knowledge/v2.5-staging` (cdd11c2d) → `main` | Curated reconciliation data | – | **Yes** (`legal_knowledge/**`) |
| #5 | `legal-knowledge/claude-audit-agents-v1` (a2570484) → `legal-knowledge/v2.5-staging` | Seven agents, docs, schemas, validator | green | No (`.claude`, `docs`, `tools`, `tests`, `.github/workflows/legal-audit-kit-ci.yml`) |
| #6 | `claude/audit-pilot-01` (11834fc8) → #5 branch | PILOT-01, R23-VERIFY-01, ACQ-01 plans, SOURCE-CONFLICTS-01, policy v1 | green (run on 11834fc8) | **Yes**: adds `legal_knowledge/audit_work/**` |
| #7 | `claude/crawler-security-aftjabalpur` → `main` | aftjabalpur.in removed and blocked | green | No |
| #8 | `claude/acq-01-config` → #7 branch | 14 pinned documents, `*.archive.org` wildcard, sources disabled | green | No |
| #9 | `claude/desw-allowlist` → #8 branch | DESW HTTPS-only allow-list (3 documents), disabled | green | No |

Merge checks (`git merge-tree`): #6 into current staging is clean; the #9 stack into staging is clean; staging into main (#1) is clean. **No cross-stack conflicts.**

### The Hugging Face sync risk
`.github/workflows/sync-legal-knowledge-hf.yml` runs on **any push to `legal-knowledge/v2.5-staging` or `main`** that touches `legal_knowledge/**`, listed scripts, `.mml_transfer/**` or the workflow file itself.
- `push_legal_knowledge.py` uploads only six curated subfolders. `audit_work/` is **not** among them, so audit files would not be uploaded.
- But merging #5+#6 into staging **would still start a full sync run**: it re-uploads curated data, runs the acquisition and archive scripts (network fetches), and runs the MML-originals step. That is an unintended synchronisation.

### Recommended sequence (the owner performs every merge)
**Stack B (crawler), independent and with no sync trigger:**
1. Merge #7 into `main`. Use a merge commit and confirm crawler-security CI is green.
2. Retarget #8 to `main` and re-run CI. Merge #8 only when you approve the ACQ-01 configuration (approval A2). Merging the config does not download anything: the sources stay `enabled: false` and a fetch needs `--yes-download`.
3. Retarget #9 to `main`. Merging it is harmless because its source is disabled, but keep it unmerged until B4 is authorised if you prefer.
4. Acquisition data from any run goes on a **new data branch** off `main` (for example `claude/acq-01-data`). It is never pushed to `main` or staging directly. `data/` is not uploaded by the sync script.

**Stack A (audit), sync guard first:**
1. **Guard (approval A3).** A one-line owner-approved change to `sync-legal-knowledge-hf.yml` on staging, adding `- "!legal_knowledge/audit_work/**"` directly after `- "legal_knowledge/**"`. That change itself touches a trigger path, so merge it with **`[skip ci]` in the merge-commit message**; GitHub skips push-triggered workflows for such commits. Then confirm in Actions that no "Sync curated legal research" run started.
2. Merge #6 into the #5 branch (`legal-knowledge/claude-audit-agents-v1`). That branch is not a sync branch, so nothing runs.
3. Merge #5 into staging, again with `[skip ci]` in the merge message as a second safeguard. Confirm in Actions that no sync run started, and that `legal-audit-kit-ci` (run on the PR) was green on the final head.
4. Use **merge commits, not squash**, so that the owner's commits (b315347b..2256e1ad) and the CI evidence SHAs cited in `PILOT-01/CI_EVIDENCE.md` stay traceable.

**PR #1 (staging → main) is the owner's deliberate sync path, not this audit's.** It would carry the audit work into `main` and **will** trigger a sync. Before merging it, decide on the MML base64 transport parts in staging's history (outstanding owner decision).

**This proposal (`ACQ-02`, `ARMY-RULES-CHAIN-01`, update c):** committed on `claude/gifted-bardeen-byeim6` only. It is **not** yet integrated into #6, to keep #6 stable for review. Options: (a) integrate into #6 after the usual upstream check, or (b) a separate stacked PR on #6. Approval A8.

---

## 2. Source-acquisition inventory

### 2A. Approved scope: PR #8 pinned list (unchanged, 14 URLs)
| Batch | Items | Host |
| --- | --- | --- |
| ACQ-01-B1 | S.R.O. 484/1954; S.R.O. 116/1965, 215/1965, 188/1979, 216/1988, 17(E)/1993, 8(E)/2003, 17(E)/2019, 6(E)/2022 (9) | archive.org (and `*.archive.org` redirect servers) |
| ACQ-01-B2 | S.O. 488/1978 (Adjustment of Jurisdiction Rules); S.O. 4010/1986 (2) | archive.org |
| ACQ-01-B6 | Act 19/1955 Gazette (archive.org); Act 13/1975 and Act 37/1992 (India Code bitstreams) (3) | archive.org, indiacode.gov.in |

Status: configuration ready (PR #8, CI green); **download awaiting approval**.

### 2B. NEW, separately identified: ACQ-02 (16 files, 17 instruments), not in PR #8
S.R.O. 205/1961, 1/1961, 34/1963*, 126/1964, 5/1968, 246/1982, 44/1985, 55/1985, 68/1985 (corrigendum), 278/1985, 169/1987, 302/1987, 332/1989, 44/1991 + 61/1991 (one issue), 235/1991, 2(E)/2018*. (*r.188(e) declaration, not an amendment.)

All have been pre-verified: size, MD5 and SHA-1 match archive.org; SHA-256 agrees with the agent; identity and operative page were checked on the image (PIC-12 to PIC-28); no access marking. See `ACQ-02/README.md`.

They still need **their own config PR and download approval** (A4). They will be re-fetched through the crawler with expected hashes pinned.

### 2C. NEW discovery targets (not yet verified; would become ACQ-03)
| Item | State | Route |
| --- | --- | --- |
| S.R.O. 331, 348, 351, 404 of 1960; S.R.O. 22/2010 | Located on archive.org by OCR text only | Download the 5 issues, then image-check (A5) |
| Full-text-search hints 1966 (w.1966-08-27.76274), 1967 (w.1967-01-07.73211), 1974 (in.gazette.1974.243) | Unopened | Download and read (A5) |
| E-7 of 17-06-1960 | Not found (issue never digitised) | Custodian letter; egazette or archive from an Indian network (A6) |
| S.R.O. 258 of 27-11-2002 | Not found | egazette from an Indian network; custodian letter |
| Anything after 06-06-2022 | Not searched authoritatively | egazette.gov.in from an Indian network (A6) |

### 2D. Other pending (unchanged from earlier decisions)
| Item | Status |
| --- | --- |
| PR #9 DESW (Entitlement Rules 2023 ×2, GMO 2023) | Prepared; B4 not authorised |
| AFT static-listing PDFs through verified HTTPS on `aft.gov.in` (pinned Sectigo intermediate) | Crawler change not written; needs approval. The bare-IP HTTP route stays rejected and no CAPTCHA is used |
| Regulations for the Army (full) | Pending owner copy and access-marking confirmation |
| Work-order items | WO-2.1 RA Ch.V extract; WO-6.3 Acts 56/1974, 20/1983; Priority-7 judgments (sci.gov.in). Each needs its own pinned config |

---

## 3. Amendment-chain completeness and outstanding evidence (Army Rules 1954)
From `ARMY-RULES-CHAIN-01/army_rules_instrument_register.csv` (37 rows):

| State | Count |
| --- | --- |
| Located, operative page image-checked | 26 (including 2 r.188(e) declarations that are not amendments) |
| Located, OCR text only | 5 |
| Unopened hints | 3 |
| Not found | 2 (E-7/1960, S.R.O. 258/2002) |
| Not searched authoritatively | 1 (after 06-06-2022) |

- **Rule 23:** no amendment in any of the 31 located instruments; the 5 OCR-only ones show none either. **CONFLICTING** is retained: the 1954 Gazette reads "not obliged", the compilation reads "obliged".
- **Rule 194:** S.R.O. 332/1989 adds "or the Officer Commanding an Army". MML 2 agrees; the compilation lacks the words. **PROPOSAL, legal review required.**
- **Rule 193 (new, U-04):** S.R.O. 302/1987 covers s.91(i) only. The compilation covers s.90(i) **and** s.91(i). No located instrument explains the s.90(i) words. **OPEN.**
- **Official notes are not a reliable index (U-05).** They omit S.R.O. 205/1961 (in 1982–85), S.R.O. 278/1985 (in 1987), S.R.O. 1/1961 (in 1991), every 1960 S.R.O. except E-7, and S.R.O. 22/2010. They misdate S.R.O. 34 and treat two r.188(e) declarations as amendments.
- **Outstanding evidence:**
  - itemise S.R.O. 17(E)/1993 rule by rule;
  - image-check the 5 OCR-only instruments;
  - open the 3 hints;
  - E-7/1960, S.R.O. 258/2002 and anything after 2022;
  - transcribe the 1954 text of rr.193/194 from S.R.O. 484 (already in B1) for the version register;
  - certified copies (custodian letter, not sent).

---

## 4. Proposed authoritative statutory-version register
**Purpose:** for every provision, an auditable sequence of text versions, so that a knowledge-base record can be checked against the law in force on its relevant date.

**Columns** (seed: `ARMY-RULES-CHAIN-01/statutory_version_register_seed.csv`):

`provision | version | text_source_instrument | valid_from | valid_to | text_evidence | wording_status | compilation_agrees | determination_state | legal_review_required`

plus, when implemented: `wording_sha256` (normalised text), `page_image_check_id` and `source_authority_policy_version`.

**Rules:**
1. A version's text comes **only** from an image-checked Gazette instrument (`ENACTED_OR_NOTIFIED_PRIMARY`; a facsimile is acceptable with custody checks; a certified copy prevails if the two differ). OCR text can locate a version but cannot establish it.
2. Compilation text (India Code, dmamod) is recorded in `compilation_agrees`, never as the source of a version.
3. `valid_from` is the commencement printed in the instrument. Where the instrument is silent, `valid_from` is left unset with the note "publication date; commencement not stated", pending the advisor's rule (AQ-05). Retrospective effect (e.g. S.R.O. 216/1988, w.e.f. 04-06-1979) is recorded explicitly.
4. A corrigendum creates a correction entry on the version it corrects, not a new version.
5. `determination_state` is one of `VERIFIED_TEXT`, `PROPOSAL`, `OPEN`, `CONFLICTING`. Only a named human legal reviewer can move a row to an approved state; no agent can.

**Scope order:**
1. Army Rules provisions cited by the knowledge base;
2. Army Act sections, using amending Acts 19/1955, 13/1975 and 37/1992 (B6) for ss.75–76 and s.127;
3. Air Force and Navy equivalents;
4. the IPC/CrPC/Evidence Act → BNS/BNSS/BSA transition, effective 01-07-2024.

---

## 5. Knowledge-base coverage methodology and acceptance gates
**Baseline (frozen originals unchanged):**
- 658 records (`records_658.jsonl`, sha 9a8f0d19…) and 53 cases.
- 87 source codes: 39 resolved explicitly, 33 corroborated officially, 9 probable, 3 resolved by co-citation, 2 category-only, 1 unresolvable.
- 269 records carry no source code.
- Pilot MML crosswalk: 63 rows. PILOT-01 outcomes cover 43 items.

**Method (deterministic, no legal judgment, built by script and checked in CI):**

One row per record in `coverage_matrix_658.csv`:

`record_id | record_sha | provisions_cited (parsed) | source_codes | resolved_doc_ids | instrument/version applicable at record date | MML anchors | citation_resolution_state | coverage_state`

`coverage_state` is one of `FULL`, `PARTIAL`, `SOURCE_GAP`, `NO_CITATION`, `UNRESOLVED`.

Supporting registers:
- `citation_resolution_register.csv`: every unresolved, probable or category-only code, with candidate identities and evidence;
- `mml_crosswalk_full.csv`: an MML paragraph for each record, or an explicit "no MML paragraph", with edition and manifest SHA.

**Acceptance gates (measurable):**
| Gate | Criterion |
| --- | --- |
| G1 Denominator | 658/658 records and 53/53 cases have a row; originals' SHA-256 unchanged (CI `sha256sum -c`) |
| G2 Citation parse | 100% of records classified; each `NO_CITATION` record listed with its reason |
| G3 Code resolution | 87/87 codes classified; every `PROBABLE` has a second independent reading; `UNRESOLVABLE` items carry an acquisition or advisor route |
| G4 Source presence | Every cited instrument is in the corpus with a SHA-256 **or** in the gap register with an acquisition route and approval status |
| G5 Version mapping | Every cited Army Rules or Army Act provision maps to a version-register row (or is flagged `NO_VERSION_ROW`); 0 versions sourced from compilations or OCR alone |
| G6 MML | 100% of records in MML-covered modules have a crosswalk row or an explicit "none"; inferred volume mapping never treated as authoritative |
| G7 Page image | Every legally significant wording relied on has a `page_image_check_id` |
| G8 Independent sample | A blind reviewer re-derives the structural fields for a stratified random 10% sample (≥66 records); agreement ≥95%; every disagreement dispositioned |
| G9 Validation | Validator strict passes; all audit tests pass; CI green on the final head |

The matrix **measures** coverage. It does not audit legal correctness: that remains the calibration batch and the full audit, which are **not** started.

---

## 6. Legal-advisor decision queue (new items; the existing 32-item packet stands)
| ID | Question | Basis |
| --- | --- | --- |
| AQ-01 | r.23(3): authoritative wording ("not obliged" in the 1954 Gazette vs "obliged" in the compilation); effect of no located amendment | F-R23-001/002, U-01; custodian letter |
| AQ-02 | r.194: accept S.R.O. 332/1989 as the operative text, so that the compilation is defective | C-04, U-02, PIC-12, PIC-29 |
| AQ-03 | r.193: how to treat the compilation's s.90(i) words, which no located instrument supports | U-04, PIC-24, PIC-29 |
| AQ-04 | Weight of archival Gazette facsimiles against certified copies, under policy v1, for version-register entries | SOURCE_AUTHORITY_POLICY v1 |
| AQ-05 | Effective date where an amending instrument states no commencement (publication date?) | Chronology (many "not stated") |
| AQ-06 | Effect of the retrospective omission in r.2 by S.R.O. 216/1988 (w.e.f. 04-06-1979) on records dated 1979–1988 | AR-024 |
| AQ-07 | Effect of a corrigendum (S.R.O. 68/1985) on the text from first publication | AR-020 |
| AQ-08 | Whether r.188(e) declarations (S.R.O. 34/1963, 2(E)/2018) belong in the Rules' amendment chain or in a separate notification layer | AR-008, AR-033 |
| AQ-09 | Citation form for instruments whose printed short titles bear the wrong year ("Rules, 1990" for 1991 S.R.O.s) | AR-026, AR-027 |
| AQ-10 | Unchanged from before: C-07 (AA s.133 vs BSA); Regulations for the Army access marking | Earlier packet |

No item is advisor-approved. Advisor nomination is still outstanding.

---

## 7. Exact approvals required before execution
| # | Approval | Effect |
| --- | --- | --- |
| A1 | Merge #7 into `main` (owner merges) | Security fix live; unblocks #8 retarget |
| A2 | Approve the PR #8 configuration **and** a real download run for exactly the 14 pinned URLs | Fetch B1/B2/B6, then pipeline, checksums, page-image checks, CI, separate proposals |
| A3 | Sync guard: the workflow negation line plus `[skip ci]` merge messages, before any Stack A merge | Prevents an unintended HF sync |
| A4 | Prepare an ACQ-02 crawler-config PR (16 pinned URLs with expected hashes), then a separate download approval | Turns the supplement into record copies |
| A5 | ACQ-03 discovery: download and image-check 8 archive.org issues (5 OCR-only instruments, 3 hints), as pinned config or scratchpad discovery (choose) | Completes the archive.org part of the chain |
| A6 | Owner or Indian-network egazette search: E-7/1960, S.R.O. 258/2002, post-06-06-2022 | Closes gaps that cannot be closed from here |
| A7 | Sign and send the custodian letter (`R23-VERIFY-01/correspondence/…`, NOT SENT; verify addresses) | Certified copies |
| A8 | Where to integrate this proposal: into #6, or a stacked PR | Review routing |
| A9 | Nominate the legal advisor | Unblocks AQ-01..10 |
| A10 | B4 (DESW download); AFT HTTPS crawler change; supply the Regulations for the Army with its marking | Other acquisitions |
| A11 | Decide on the MML base64 parts in staging history before #1 | Main/HF hygiene |
| A12 | Approve building the coverage matrix and registers (section 5, deterministic scripts only) | Coverage work; not the calibration or full audit |

**Not requested and not to start:** the 46-record calibration batch, the full 658-record audit, any HF upload, any change to original records, any application work.
