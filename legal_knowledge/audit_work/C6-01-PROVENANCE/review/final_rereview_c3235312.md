# C6-01 / C6-PREP corrections: re-review

- **Reviewed:** `git diff e7a10e27..c3235312`. HEAD is `c3235312f924748a8194430cb8c9353bc48c3ac8`.
- **Constraints kept:**
  - read-only;
  - no network access;
  - PYTHONDONTWRITEBYTECODE=1 / `-B`;
  - outputs only in this folder;
  - `git status --short` empty before and after.
- **Scope of judgement:** I make no legal determination.

## VERDICT: ACCEPT

There is no P1 and no P2. Both earlier P2s are fixed. Five P3 wording items remain (RR-01 to RR-05); none changes an outcome, class, count or legal status.

## Checks

### (a) The P2s are fixed, and no report count contradicts the summary
**R-01 is fixed:**
- D6 now gives 34 DOCUMENTED, 2 PARTIAL, 34 additions (21 + 9 + 4 non-primary), the Delhi HC gap correctly described, and TRA resolved.
- D2 lists TRA among the non-primary entries.
- D3 labels the old 33/3 figures with the commit they came from and adds "Current outcomes: 34 DOCUMENTED and 2 PARTIALLY_DOCUMENTED".
- A new test, `test_report_counts_match_summary`, ties D2, D3 and D6 to `c6_01_summary.json`.
- A grep of all reports, README and addendum for 33 / "3 non-primary" / "3 partial" finds only the commit-labelled historical lines and the R-01 disposition row.

**R-02 is fixed:** D4, D6 and the addendum plan state the two-register requirement: the addendum plus a reviewed Cycle 5 holding-state relabel, with the build re-run with `check_holding_vs_copies` on.

**Wording:** the D3 dispositions for R-03 to R-12 match the changes made. The exception is a past-tense re-review claim (RR-03).

### (b) No outcome or class changed
- `c6_01_summary.json` is byte-identical to e7a10e27.
- A column-by-column comparison of all three registers (36 / 34 / 2 rows, same keys) finds only these changes:
  - the Act 13/1975 "uncertain" qualifier, in the gaps and missing-items text;
  - the TRA limitation, rewritten per R-04 ("no signature verified" is still present);
  - the RS papers-laid limitation, per R-08.
- No outcome, class, locator strength or evidence item changed.

### (c) Addendum draft
- **Deterministic:** `build_addendum_plan.py --check` prints OK, and the test re-derives the file.
- **Entries:** 34 entries, 30 primary and 4 non-primary. All are FULL, all have reviewer and owner decision PENDING, and none duplicates a Cycle 4 row.
- **Crosswalk effects:** 8 SC primary entries each change exactly one case row from PARTIAL_MATCH to EXACT_ANCHOR. They cover 7 distinct cases: Ranjit, S N Mukherjee, Navjot, Dharamvir, Rajbir (via both copies), Girish and Mullikote. This equals the joint simulation (cases 6/7/40 → 13/0/40). N S Yadav, the 21 Gazette entries and the 4 non-primary entries change nothing.
- **Plan text:** it states the relabel requirement correctly: about 29 sources, which is 21 Gazette plus 8 SC sources, matching the simulated 12→41. It also says the relabel goes through a correction register, with the holding check on and the PR diff equal to the simulation.
- **Wording errors:** two small ones (RR-01, RR-02).

### (d) Prep changes
**Metadata log:** `c6_02_metadata_requests_v2.tsv` has 14 rows in the v2 columns: 10 requests and 4 refusal decisions.
- `discovery_guard.validate_log_v2` returns [].
- The only GETs are robots.txt.
- The HEAD requests that got 302s record the redirect Location in final_url. The runner does not follow redirects (run_guarded_discovery.py l.162), and each data node got its own robots decision before its HEAD.

**Batch A:** 18 files PINNED and 2 NOT_PINNED (C5C-026/027), all NOT_APPROVED.

**D&V handbook lead:**
- The Scribd upload is marked "not opened or downloaded".
- Authenticity, completeness, currency and redistribution are NOT_ESTABLISHED.
- The references are UNVERIFIED_EXTRACTION_CANDIDATE.
- The custodian rows say correspondence "NONE SENT".

**Legal claims:** the readiness report makes none, and it keeps the reserved states.

**Wording and scope:** the readiness report's "no GET was made" is imprecise (RR-04). The CLAUDE.md scope note on Army Orders and handbooks is incomplete (RR-05).

### (e) Diff scope and tests
- The diff touches only C6-01-PROVENANCE/, C6-PREP/ and tests/test_legal_audit_c6_provenance.py.
- CALIBRATION-02, SOURCE-LIBRARY-C5 and curated_originals are unchanged.
- The Cycle 4 register sha256 is cfe5f408…, identical to the baseline and now pinned by a test.
- The 658/53 hashes are unchanged.
- `build_provenance.py --check` returns rc 0, `build_prep.py --check` prints ok, and the unit tests pass (20 tests). The new tests cover duplicate rejection, the non-tautological ID-stability check and the report counts.
- `review/final_review_e7a10e27.md` and `final_findings_e7a10e27.csv` are verbatim copies of my earlier outputs.

## Findings
| ID | Sev | Finding |
| --- | --- | --- |
| RR-01 | P3 | The addendum plan says "Girish/Navjot second copies change no row"; the entry with no effect is actually N S Yadav |
| RR-02 | P3 | The draft justification claims a "Cycle 4 class" for the non-primary entries and the reserved TRA entry |
| RR-03 | P3 | D3 says the corrections "were re-reviewed" before the re-review existed |
| RR-04 | P3 | The readiness report says "no GET was made"; 4 robots.txt GETs were made (no non-robots GET) |
| RR-05 | P3 | C6-04 flags only policy letters as out of the CLAUDE.md scope; Army Orders and the non-public handbook also fall under it |

## Residual risks
The earlier residual risks still apply:
- byte identity is not authority;
- India Code bytes are download-specific;
- incorporation touches two registers;
- the TRA and RS decisions are reserved for the owner.

The addendum is a draft, and its reader and validator changes are not yet written.
