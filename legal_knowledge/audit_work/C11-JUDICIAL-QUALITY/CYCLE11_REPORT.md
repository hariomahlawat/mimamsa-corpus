# Cycle 11 consolidated report: judicial corpus quality, source preservation and legal knowledge

Branch `claude/c11-judicial-quality`, stacked on #43 (`554c46cc`). Every workstream below was independently reviewed by Fable 5.2 (`claude-fable-5-2`). That review is **AI documentary review, not legal validation**. Nothing is merged, uploaded or downloaded, and no protected original, register or ledger entry has changed.

## A. Source preservation (`preservation/`)
- **48 working-store-only copies:**
  - all present, all re-hashed equal to the register, 37,312,132 bytes;
  - none in any git object of the local store, none in the HF listing.
- **Exact-anchor rows:** 47, including all 42 Army Rules 1954 anchors (`c5ef95a9`).
- **Markings:** no restriction marking was found on text pages. **73 pages without a text layer were not scanned**, including 3 image-only copies, and need a visual check before any publication.
- **NOT PRESERVED:** no authorised persistent destination was available to this session. The owner-action package, `stage_and_verify.sh` (tested: 48 copies byte-identical), and the recovery procedure are provided.

## B. Hugging Face verification (`hf_verification/`)
- **INCOMPLETE.** The connector is read-only: no binary read, no LFS object id, no revision id. The shell has no credential, and none was requested in chat.
- **Revision:** unpinned; the latest logged commit is `e1a7fa47`.
- **HF `SHA256SUMS`:** sample-matched to GitHub at three offsets (size equal).

**Per-copy status:**

| Status | Copies |
| --- | --- |
| DECLARED_HASH_ONLY | 4,047 |
| PATH_SIZE_MATCH_ONLY | 8 |
| UNAVAILABLE | 48 |
| BYTE_VERIFIED on HF | 0 |

GitHub `raw-data`: 4,039 of 4,039 copies BYTE_VERIFIED.

## C. Judicial identity (`identity/`, `scnum/`)
- **Distinct judgments: 3,625**, or 3,631 counting 6 pointer orders, from 3,959 files. Each step is evidenced, and scanned duplicates and composites are handled.
- **Supreme Court case numbers, 368 records without one:**
  - 320 confirmed from the source text;
  - 98 independently reviewed against page images: multi-matter 35/36 (lower bound 87.5%), single 14/14;
  - application status recorded for every record, and **nothing applied**.

## D. Judicial outcomes (`extraction/`, `evaluation/`)
- **Frozen extractor `c11-extract-v2/1.0.0`** (structural zoning, per-proceeding, abstention), run on all 3,936 processed judgments.
- **Blinded 56-judgment holdout:**
  - strict precision 37/44 = **84.1%** (95% interval 70.6% to 92.1%; about 79% population-weighted), coverage 80%;
  - crawler 75.0%, C10 extractor 64.6% (by outcome family).
- **Below the 95% bar:** every outcome stays `AUTOMATED_CANDIDATE_NOT_VERIFIED`.
- **Release file** `extraction/release/OUTCOMES_V2_RELEASE.csv` withholds 578 risky rows (shared batch text, multi-copy judgments, multi-case labels).

## E. Legal propositions (`extraction/outputs/PROPOSITIONS_V2.jsonl`)
- 51,250 attributed candidates, all excerpts verbatim.
- **Origin-label precision:**

  | Label | Precision |
  | --- | --- |
  | Court holding | 92.5% |
  | Court reasoning | 85% |
  | Quoted precedent | 73% |
  | Submission | 80% |
  | Headnote | 100% |
  | Lower court | 60% |

- **Recall of reviewer-identified holdings is 12%.** These are leads, not a holdings index, and nothing is a verified holding.

## F. Judicial relationships and statute links (`relations/`, rev. 1.3)
- **Citations:** 23,222 edges, 13.0% resolved to corpus judgments; resolved edges independently 30/30 correct.
- **Treatment proposals:** APPLIES 195, DISTINGUISHES 9, FOLLOWS 4, OVERRULES 16, all candidates. Fresh-sample precision: APPLIES/FOLLOWS 29/30, DISTINGUISHES 6/6.
- **Adviser queue: 30 rows.** 16 are own-voice overruling statements: 1 bound (Parashotam on Shri Kant Sharma) and 15 leads, including Ajmer Singh 1987, Mafatlal, Puttaswamy 2017 and Joseph Shine. 14 are separate opinions or dissents, which carry no proposal. **4 known noise rows** are listed in `review/DISPOSITIONS_relations_c11.md`.
- **Statute links:** 11,076, every one VERSION_NOT_ESTABLISHED. Labels say what the text shows (party invoked, charged under, jurisdiction referenced, and so on).
- **Dossier (all quotations verified on the source page):**
  - Tarsem is distinguished by Girish para 22, not overruled; a later Delhi High Court judgment still applies Tarsem.
  - Parashotam para 32 says Shri Kant Sharma "does not lay down the correct law", without using "overruled".
  - The Girish clarification and Ram Avtar are **not held**.

## G. Incomplete and excluded judgments (`identity/outputs/INCOMPLETE_23_RECOVERY_PLAN.csv`, `excluded/`)
- **23 unresolved files:**
  - none contains an earlier complete revision;
  - 1 has a complete copy elsewhere in the corpus;
  - 22 need recovery with approval: 18 re-acquired from official or recorded sources, 4 from the HF copy or the working store.
- **8,077 flagged excluded titles** ranked for owner consideration. Nothing was acquired; every logged SHA-256 allows exact verification.

| Tier | Titles |
| --- | --- |
| T1 | 1,790 |
| T2 | 1,570 |
| T3 | 706 |
| T4 | 317 |
| T5 | 3,694 |

## H. Curated knowledge (`curated/`)
- **53 curated cases:** C10 reproduces (33 held, 9 candidates, 11 not held; 6 official PDFs). 25 have a Supreme Court case-number proposal.
- **32 research records** depend on cases with verified treatment findings, matched by name, by the C5 crosswalk or by the C8 gap matrix. Each is queued as an adviser question.
- **Citation baseline unchanged:** 983 items, of which 42 exact anchors, 652 partial and 289 missing evidence. No registration, preservation or authentication occurred.

## I. Authentication and integration
- **#40, #41, #42, #43:** accepted heads (`e4d59196`, `a61c0e57`, `2ba7b0a4`, `554c46cc`).
- **#45 integration candidate:** accepted. It merges the four PRs cleanly, and its combined-tree tests pass. TXN-DEMO is regenerated (22 tool-derived values; behaviour unchanged). The gate and CI do not run TXN-DEMO `--check`.
- **#44 ledger file-type hardening:** accepted at `bdc23f11`. The FIFO, symlink and special-file fixes fail closed.
- **Ledger:** version 0, HEAD `0 443c4bdf…6b6b`.
- **Protected hashes:** `records_658` `9a8f0d19…` and `cases_53` `8b8d53cd…` unchanged.

## J. Development record
- **Gate on this branch** at `cc798a33`: 30/30 checks; warnings at the 188 baseline.
- **Every tool reproduces under `--check`.** Tests pass on the venv; on Python 3.11, skips state their reason (no PyMuPDF, jsonschema or httpx).
- **Reviews and dispositions:** every P1 and P2 is closed; P3 items are carried to a follow-up. See `review/` (`DISPOSITIONS_*`).
- **Owner decisions required:**
  1. a preservation destination for the 48 copies;
  2. Hugging Face byte access, through a platform-injected token or an owner-run download;
  3. merge approval for #40 → #41 → #42 (→ #44) → #43, with TXN-DEMO regenerated after the ledger PRs;
  4. acquisition approvals: the 22 incomplete-file replacements, the Girish clarification, Ram Avtar, and the excluded-log tiers;
  5. legal-adviser review of the 30-row adviser queue, the 32 research records and the Parashotam/Shri Kant Sharma question;
  6. the access decision for the For Official Use Only Air Force Regulations copy;
  7. whether to apply the reviewed SC case-number proposals.
- **Next cycle:**
  - extractor v3 (per-proceeding batch splitting; printed and substantive outcome fields), measured on a new, double-coded holdout;
  - the P3 follow-ups;
  - TXN-DEMO `--check` in CI.
