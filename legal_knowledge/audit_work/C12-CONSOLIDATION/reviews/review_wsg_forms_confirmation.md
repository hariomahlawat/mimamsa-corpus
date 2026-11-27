# Confirmation review: WS-G forms registry remediation (WSG-R01..R15)

**Reviewed:** 2026-11-24, commit 64412e0d on claude/c12-consolidation (tool 1.1.0)
**Reviewer:** the original independent reviewer. This is an AI documentary review, not legal validation.
**Mode:** read-only. The mutation and render experiments are in `scratchpad/rev_wsg/`. Nothing was committed.
**Per-finding table:** `review_wsg_forms_confirmation_findings.csv`

## Verdict

**ACCEPTED.**
- 12 findings are CLOSED_VERIFIED.
- 3 are PARTIAL, and each is an acceptable documented deferral:
  - R04: field lists are labelled MML-version and queued for divergence, but not yet re-transcribed from the official copies.
  - R10: 17 capped DOC ranges are marked.
  - R13: no Python 3.11 runtime run.
- No new P1 or P2.

## Checks performed

- **Rebuild and tests:** `--check` reproduces the 4 outputs byte for byte, and 27/27 tests pass (venv).
- **R01 guard, mutation test:** copied the tools and changed '(see rule 27)', or the r.27(3) quote, back to 17. The build fails with "rule number 17 in FF-AFTPR08-F3 (attributed to OCR source AFTPR08-C7) is not confirmed by a recorded page-image check".
- **VISUAL_CHECKS against my own page images:** AFT p.37, p.38 and p.46, Gazette p.2 and p.72, and 1993 p.19 all agree. I also rendered and read the new source AFTPRA11-C7 p.2 (hash fc27032f... verified). It shows S.R.O. 05(E) of 29-07-2011, inserting r.7(2) and r.12A, as recorded.
- **Counts:**
  - 39 STATUTORY_PRESCRIBED, and every one quotes 'shall'.
  - Source basis: 32 MML_ONLY / 30 BOTH / 5 OFFICIAL_COPY.
  - 8 MML-only statutory families carry NOT_CONFIRMED.
  - The AR 4(1) caveat appears on 130 of 130 appendix rows, and the boilerplate appears in 0 rows.
  - Only one INSPECTED_NO_FORMS_FOUND row remains, and it was visually checked.
  - No DOC locator runs past end of file.
- **Scope:** the scope statement and the Air Force and Navy NOT_HELD rows are present.

## Residual items, none blocking

- R04: before any template use, transcribe 1954 Gazette pp.73-86 and 1993 pp.19-21 from page images.
- R10: optionally set end boundaries for the 17 capped ranges by hand.
- R13: run once under Python 3.11.
- NEW-01: tidy the stale wording in the AR 140 uncertainty.
