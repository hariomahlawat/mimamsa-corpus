# Cycle 7 source and legal-evidence workstreams: readiness and authorisations required

**Status:** preparation only. No download, no crawler or configuration change, no correspondence, no HF upload, no legal determination. This document updates `C6-PREP/` (merged in PR #33) and changes none of its files.

## C6-02 Public Gazette sources (20 archive.org files)
**Priority order for a future approved acquisition:**
1. Army Act 1950 as enacted (`in.gazette.e.1950.306`).
2. AFT Act 2007 (`in.gazette.central.e.2007-12-28.020`).
3. BNS, BNSS and BSA 2023 (`…2023-12-25.250883/250884/250882`).
4. The three 2024 commencement notifications (`…2024-02-24.252352/252353/252354`).
5. The 10 possible Army Rules S.R.O.s from 2022 to 2026, whose subject is **not confirmed**.
6. The 2 DPP Amendment Act 2000 items (unpinned).

**State:**
- 18 of 20 files are pinned with md5 and bytes from archive.org metadata.
- None overlaps PRs #8, #17 or #23.
- Downloads redirect to `dn*.archive.org`, which PR #8's `*.archive.org` entry permits; staging's config lists only `archive.org`.

**Metadata-only access proposal P-C7-02-META** (supersedes P-C6-02-META; to be implemented, if approved, as a separately reviewed change to `SOURCE-LIBRARY-C5/tools/discovery_guard.py`; the crawler is not touched):

| Control | Rule |
| --- | --- |
| Host and path | only `https://archive.org/metadata/<identifier>`, with the identifier matching `^[A-Za-z0-9._-]+$` and on an explicit list (the two DPP items) |
| Robots | archive.org robots.txt must be RULES_PARSED and must allow `/metadata/`; otherwise there is no request |
| Method | a GET without a prior 200 HEAD, allowed for this route only, because archive.org answers HEAD with 405 there |
| Response gates (before reading the body) | status 200; `content-type` exactly `application/json`; no `content-disposition: attachment`; identity encoding; declared length 512 KB or less |
| Body gates | first 1 KiB has no document signature (`%PDF`, ZIP, OLE, RTF), no NUL byte and parses as JSON when complete; body cap 512 KB; any read error discards everything |
| Redirects | not followed. A 3xx is logged with its `Location` and the run stops for that identifier |
| What is kept | only `files[]` entries whose `name` equals the expected PDF: `name`, `size`, `md5`, `sha1`. No document body is ever requested |
| Ambiguity | zero matching files, more than one, or missing md5 or size: **fail closed** and record `PIN_AMBIGUOUS` |
| Logging | every decision in log format v2, including `NONE` rows for requests not made |
| Tests | mocked tests cover: HEAD 405 then JSON is allowed; a non-listed identifier is refused; a body that is a PDF is refused by the prefix gate; a redirect is not followed; a robots disallow wins; an ambiguous `files[]` fails closed |

**Authorisations required:**
- owner approval of P-C7-02-META;
- a reviewed guard PR;
- a logged run;
- separately, **A-C5-1** for any download, through a config PR stacked on #8. Unpinned downloads are **not** acceptable.

## C6-03 Pension and entitlement publications (DESW)
- **Targets:** PRA 2008 Parts I and II; Entitlement Rules 2008 (two non-identical files); the complete Entitlement Rules 2023 + GMO 2023 file; amending circulars.
- **Held copy:** the incomplete ER 2023 copy (`29f6fa2c…`) stays separately identified, and its C6-01 proposal stays non-primary.
- **Blockers, unchanged:**
  - only the ER/GMO 2023 URL is in draft PR #9; the others need an allow-list extension;
  - desw.gov.in robots.txt returned 403, so the fail-closed rule applies and there is no bypass.
- **Authorisations required:** A-C5-2; an allow-list extension PR; and either a later successful robots read or an owner-side manual retrieval with sha256 recorded.

## C6-04 DSR and administrative publications (custodian route)
- **Inventory:** RA 1987 Vols I and II with correction slips; RA 1962; RMSAF 2010 and 1983; AO 45/2001; AO 13/2006/PS; the Army Orders cited by category (the owner must name them); and the D&V Staff Officers' Handbook of May 2014.
- **D&V handbook:**
  - It remains an **unverified discovery lead**. The Scribd upload was not opened.
  - Its reported references (Army Act ss.26, 27 and 164; RA 1987 paras 364, 365 and 368; AO 13/2006/PS) remain unverified until checked against an authorised copy.
  - It is guidance, not governing authority.
- **Scope:** CLAUDE.md excludes Army Orders, internal policy letters and unpublished material. Proposal P-C6-04-SCOPE (`C6-PREP/reports/C6_PROPOSALS_SCOPE_AND_METADATA.md`) is a narrow extension to named publications only, with access-marking handling. It is **not** adopted.
- **Authorisations required:** owner approval of a scope extension; approval of the request text and of access-marking handling (A-C5-3); a decision on the archived CDA copies. No correspondence is authorised now.

## C6-05 Legal adviser package
- **Preserved unchanged:** 13 adviser topics, 29 calibration escalations, 9 reserved items and 13 open WS-B inconsistencies. Reserved states: r.23(3) CONFLICTING; r.182 SC4-01 OPEN; r.193 OPEN; r.194 PROPOSAL.
- **Effect of AUTH-LEDGER:** it records **authentication** only. An EXACT_ANCHOR created by a future approved entry means a documented copy is held. It does not settle statutory interpretation, subsequent judicial treatment (for example Navjot Sandhu after Anvar) or applicability. Those remain adviser questions.

## Authentication tranche proposal (for owner decision; nothing is approved here)
- **Tranche 1, Gazette:** the 20 primary Gazette entries. They have no crosswalk effect, so they test the ledger mechanics at zero coverage risk. If the owner adopts policy B2, legacy image checks are allowed with a recorded limitation; rule 1 currently accepts them (B1).
- **Tranche 2, Supreme Court:** the 8 primary court entries, which carry 7 case anchors. If the owner adopts policy B2, each needs a C6-style CONFIRMED identity check or a reviewer statement.
- **Non-primary entries** (4) are recorded only after the owner adopts the fidelity table, and they never anchor.
- **Not entries:** the RS papers-laid record (WITHHELD) and Rajbir C2.

## Update for AUTH-LEDGER-02 (hardening branch; still preparation only)
- **C6-02.**
  - Unchanged: 18 of 20 files pinned; the 2 DPP Amendment Act 2000 files unpinned.
  - **P-C7-02-META** stays as proposed above: metadata-only access for the two named identifiers; JSON only; size cap; no redirects followed; fail closed. It is **not** executed.
  - No download, no crawler or robots change, and no `config/` or security change was made.
  - Locators of any future acquisition must pass the AUTH-LEDGER-02 strict parser before they can be first-class evidence.
- **C6-03.** Unchanged. The DESW package and its blockers (allow-list, robots 403) are preserved. The incomplete ER 2023 copy (`29f6fa2c…`) stays non-primary and distinct from the full publication. No DESW download is authorised.
- **C6-04.** Unchanged:
  - The acquisition planning covers RA 1987, RA 1962, RMSAF, the named Army Orders and the D&V handbook.
  - The handbook stays an unverified discovery lead, and the Scribd copy is not imported.
  - Nothing unpublished or access-controlled is requested without an approved scope and an authorised custodian route.
  - No correspondence.
- **C6-05.** Unchanged. `AUTH-LEDGER/tranches/T2-SUPREME-COURT/EVIDENCE_REVIEW_PLAN.md` adds R-T2-7: provenance of a judgment copy never settles subsequent treatment. One example is Dharamvir Singh (2013) and the later ruling on the 2008 Rules. That stays an adviser question.
- **Tranches.**
  - Tranche 1 is now prepared in `AUTH-LEDGER/tranches/T1-GAZETTE/`: 18 ready (S.R.O. 34/1963 for copy provenance only) and 2 born-digital rows held for the fidelity decision. The first build's "6 needing an identifier transcription" was corrected after Fable review F-02.
  - Tranche 2 has a review plan with an open owner decision on JUDIS renditions (P-D3 in `AUTH-LEDGER/RULE_DECISION_PACK.md`).
