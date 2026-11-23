# Gazette tranche 1: identity and provenance findings (prepared, NOT active)

**Status.** These 20 rows are a preparation only. They are **not** in the ledger, have **no** decision or review record, and change nothing. `proposed_entries_PENDING.csv` leaves `owner_decision` empty on purpose, so the rows fail the ledger schema if copied in unchanged. No legal status, currency, applicability or amendment chain is asserted.

**Generated files.** Every file here is rebuilt by `../tools/build_tranche1.py`; `--check` confirms they reproduce byte-for-byte.
- `tranche1_source_register.csv`: one row per candidate, with sub-tranche and recommendation.
- `evidence_verification_matrix.csv`: the 14 verification items (v01..v14) per candidate.
- `contradiction_register.csv`
- `proposed_entries_PENDING.csv`: ledger-format rows, inactive.
- `simulated_joint_impact.json`

**How rule-1 eligibility was determined (item 14).** Each entry was run, alone, through the actual AUTH-LEDGER rule-1 pipeline in a temporary directory with synthetic approval records. The temporary directory and records were deleted after the run.

The checks run were:
- schema and association;
- evidence references bound to the sha256;
- the first-class record, with the AUTH-LEDGER-02 strict locator and class path rules;
- class compatibility, completeness and copy fidelity;
- identity and exact-string contradiction;
- the copy-status rule, with the frozen Cycle 5 consistency check.

**All 20 pass rule 1.**

## Summary
| Group | Count | Rows | Recommendation |
| --- | --- | --- | --- |
| 1A-READY | 18 | T1-01 to T1-18 | Ready for an owner decision, with each row's limitations recorded verbatim. T1-02 (S.R.O. 34/1963) is for copy provenance only (F-T1-2) |
| 1B-FIDELITY | 2 | T1-19 (S.R.O. 2(E)/2018), T1-20 (S.R.O. 17(E)/2019) | Hold until the owner confirms fidelity class 2 |

**Correction after independent review (Fable F-02).** The first build of this tranche (commit 924047b1) reported a "1A-CONFIRM-ID" group of 6 rows, plus T1-19. It said their S.R.O. number and date line were not transcribed in any committed observation. That was wrong. The builder scanned only `identity_refs`. Each of those entries also cites, as L5 evidence, an R23 amendment-search record (`R23-VERIFY-01/registers/amendment_search_2026-11-22.csv`, status `LOCATED_IMAGE_CHECKED`, with a render hash) that quotes the masthead and the S.R.O. line from the page image. An example, for T1-16: "'New Delhi, the 26th September, 1989 S.R.O. 332... Army (Amendment) Rules, 1989'". The builder now reads those records too. All 20 have the number read from the image, and the split is 18 / 2.

**Common facts for all 20:**
- The carrier is `THIRD_PARTY_ARCHIVAL_FACSIMILE`: archive.org re-hosting of Government of India Gazette issues.
- The issuing authority recorded in the Cycle 5 master is the Central Government (Ministry of Defence).
- The first-class locator is an archive.org `/download/<item>/<file>` or `/details/<item>` URL that passes the strict parser.
- No Internet Archive derivative producer appears.
- Cycle 5 records continuation pages as `ALL_IMAGE_CHECKED`.
- No exact-string contradiction is found for any locator.

## Findings
**F-T1-1. Notification identifiers (corrected).** For all 20 rows, the S.R.O. number(s) in the identity appear in text that a person read from the page image. That text comes from image-check observations, independent transcriptions, or the L5 R23 records' quoted identity evidence. Register rows are excluded, so the check is not circular. Rule 1 itself accepts these rows on their image checks and ARMY-RULES-CHAIN-01 register rows. See the correction note above.

**F-T1-2. S.R.O. 34/1963 (T1-02): uncertainty preserved.**
- The held file is the 05-01-1963 declaration under r.188(e) (PIC-15). It is a declaration, not an amendment.
- The C5 master title and the C6-01 draft say "notes misdate as 05-06-1963". That wording asserts something unverified. The prepared files therefore use neutral wording (`build_tranche1.neutral_identity`): the notes list an 'S.R.O. 34 dated 5-6-1963', and whether that is this instrument is UNVERIFIED. The frozen C5 and C6-01 files are not changed.
- The government notes' "S.R.O. 34 dated 5-6-1963" is **not** shown to be this instrument, and the identity of the instrument that the notes list stays **UNVERIFIED** (Fable F-03 in C6-01).
- Any entry for this copy authenticates **copy provenance only**. Its limitation must say that no amendment-chain inference may rest on it. Nothing in this tranche infers a chain.

**F-T1-3. Born-digital Gazettes (T1-19, T1-20).**
- Producer GPL Ghostscript 8.15. Each file has an embedded signature byte range that spans the file (`signed_range_covers_file=YES`).
- This is **structural only**. No signature has been cryptographically validated, and no signer certificate or trust chain has been checked.
- Rule 1 treats the class as primary, provisionally (`POLICY_OPTIONS.md` D). The recommendation is to hold both until the owner confirms that position.

**F-T1-4. Retrieval dates.** 14 rows have no retrieval date in a retrieval record, only a register date (2026-11-22). Provenance therefore rests on the archive identifier plus size, MD5 and SHA-1 matching archive.org metadata (ARC records), or on the record's own sha256. The limitation is carried in each row.

**F-T1-5. A legacy identity basis (POLICY_OPTIONS B).** All 20 rely on legacy image checks with render hashes and no `identity_result` field, plus register rows. None creates an exact anchor, so option B2 would not require a fresh check for this tranche. Option B3 would require one for all 20.

**F-T1-6. One copy, two sources.** T1-17 is one file carrying S.R.O. 44/1991 and S.R.O. 61/1991, registered as a single source (`C5-SRC-P0-AR-AMD-AR-026+AR-027`). The entry covers the copy, not each instrument separately.

## Excluded, as directed
- **S.R.O. 6(E)/2022** stays non-primary: the held file is an archive.org derivative.
- **Tribunals Reforms Act 2026** stays non-primary: the born-digital file was rewritten (signature range does not span it), and authority or fidelity evidence is still missing.

Neither is among the 20.

## Simulated joint coverage impact (`simulated_joint_impact.json`)
This is a simulation only, with synthetic records in a temporary directory; it is not an approval. If all 20 were approved and bound:
- 20 copies would move from `PROVENANCE_UNKNOWN` to `EFFECTIVE_PRIMARY_VERIFIED`;
- 20 sources would move from `HELD_OFFICIAL_PUBLICATION_PROVENANCE_UNDOCUMENTED` to `HELD_PRIMARY_GAZETTE_FACSIMILE`;
- documented primary copies would rise from 12 to 32;
- **no crosswalk row would change.**

With 1A-READY only (18), 18 copies and 18 sources change, documented primary copies rise from 12 to 30, and no crosswalk row changes.

## Evidence still to verify before any approval
1. The owner's position on fidelity class 2, for T1-19 and T1-20.
2. Optionally, retrieval dates for the 14 rows that lack one. This needs no download if the archive metadata snapshot dates are accepted.
3. For conversion:
   - committed D- and R- records naming each `entry_id=sha256:entry_digest`;
   - an independent review of the tranche PR;
   - a BIND line after the merge (`../../APPROVAL_CONTROLS.md`).
