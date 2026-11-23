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
| 1A-READY | 12 | T1-01, 03, 04, 05, 06, 07, 08, 09, 10, 12, 13, 15 | Ready for an owner decision, with each row's limitations recorded verbatim |
| 1A-CONFIRM-ID | 6 | T1-02 (S.R.O. 34/1963), T1-11 (S.R.O. 68/1985), T1-14 (S.R.O. 302/1987), T1-16 (S.R.O. 332/1989), T1-17 (S.R.O. 44 and 61/1991), T1-18 (S.R.O. 235/1991) | First, a CONFIRMED image check that transcribes the S.R.O. number and date line (see finding F-T1-1) |
| 1B-FIDELITY | 2 | T1-19 (S.R.O. 2(E)/2018), T1-20 (S.R.O. 17(E)/2019) | Hold until the owner confirms fidelity class 2. T1-19 also needs the identifier check |

**Common facts for all 20:**
- The carrier is `THIRD_PARTY_ARCHIVAL_FACSIMILE`: archive.org re-hosting of Government of India Gazette issues.
- The issuing authority recorded in the Cycle 5 master is the Central Government (Ministry of Defence).
- The first-class locator is an archive.org `/download/<item>/<file>` or `/details/<item>` URL that passes the strict parser.
- No Internet Archive derivative producer appears.
- Cycle 5 records continuation pages as `ALL_IMAGE_CHECKED`.
- No exact-string contradiction is found for any locator.

## Findings
**F-T1-1. The identifier is not transcribed for 7 rows (6 in 1A plus T1-19).**
- The builder looked for the S.R.O. number in text a person read from the page image: image-check observations and independent transcriptions. Register rows are excluded, because they restate the expected identity.
- For 13 rows the number is there, for example WSA-PIC-37: "New Delhi, the 27th March 1965 S.R.O. 116.-".
- For T1-02, T1-11, T1-14, T1-16, T1-17, T1-18 and T1-19, the recorded observations confirm the page **content** but do not record the S.R.O. number or date line. Examples:
  - PIC-39 for T1-16 records r.1, the short title "Army (Amendment) Rules, 1989", and the substitution of r.194 at printed p.736.
  - PIC-21 for T1-11 records a corrigendum to S.R.O. 55.
- For these rows the number comes from the ARMY-RULES-CHAIN-01 instrument register (`evidence_level IMAGE_CHECKED`).
- Rule 1 accepts that register row as identity evidence, so these rows are eligible. But item 4 (title and notification identifier) is **not independently evidenced** in a committed observation.
- Recommended remedy: a C6-style check with `identity_result=CONFIRMED` that transcribes the number and date line. This is offline work on held files; no download is needed.

**F-T1-2. S.R.O. 34/1963 (T1-02): uncertainty preserved.**
- The held file is the 05-01-1963 declaration under r.188(e) (PIC-15). It is a declaration, not an amendment.
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

With 1A-READY only, 12 copies and 12 sources change, documented primary copies rise from 12 to 24, and no crosswalk row changes.

## Evidence still to verify before any approval
1. F-T1-1: a CONFIRMED identifier transcription for the 7 rows.
2. The owner's position on fidelity class 2, for T1-19 and T1-20.
3. Optionally, retrieval dates for the 14 rows that lack one. This needs no download if the archive metadata snapshot dates are accepted.
4. For conversion:
   - committed D- and R- records naming each `entry_id=sha256:entry_digest`;
   - an independent review of the tranche PR;
   - a BIND line after the merge (`../../APPROVAL_CONTROLS.md`).
