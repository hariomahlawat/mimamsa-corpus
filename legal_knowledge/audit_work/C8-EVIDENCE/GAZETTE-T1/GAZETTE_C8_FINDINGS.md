# Gazette tranche 1: C8 evidence verification (Workstream B)

**Status.** This is evidence preparation only. It creates no ledger entry, decision record or approval. The repository snapshot (`c8base`, commit bb1f0971) was not modified. No legal status, currency, applicability or amendment chain is asserted. Every page reading here is by an **AI agent (Claude Opus 5.5 subagent), not human-confirmed**. A human can re-check each reading from the recorded render hash.

## Method
1. **Copy identity.** Each held file was mapped through `SOURCE-LIBRARY-C5/baseline/held_binaries_manifest.csv` and re-hashed before use (`tools/rehash_and_render.py`, `render_log.csv`). All 20 match their expected sha256, so no file was set aside.
2. **Fresh page inspection.**
   - Renders: PyMuPDF 1.28.6 (MuPDF), `page.get_pixmap(dpi=150, colorspace=csGRAY, alpha=False)`, full page, saved as PNG under `renders/` (not committed). Each PNG sha256 is in `page_image_checks_c8.csv` and `render_log.csv`. Re-rendering is deterministic: a second run gave identical hashes.
   - Crops: where small type needed it, crops of the hashed render were made, enlarged with Lanczos ×2 (`tools/crop_png.py`, hashes in `crop_log.csv`). Enlargement adds no information.
   - Each PNG was viewed with the image tool and transcribed (working notes in `tools/readings_notes.txt`).
   - Pages read:
     - T1-02, 11, 14, 16, 17, 18 and 19 (the seven L5-only rows): the masthead page and the S.R.O. page(s), including the signature block.
     - The other 13 rows: the S.R.O. heading page, plus the masthead page whenever the S.R.O. page did not carry it, so that every row has a fresh read of the issue number, date and Part/Section.
3. **Born-digital structure.** T1-19 and T1-20 were parsed with `tools/born_digital.py` and `tools/rsa_diag.py`, using installed OpenSSL 3.0.13 and Python `cryptography`; nothing was installed. See `BORN_DIGITAL_FINDINGS.md`.
4. **Registers.**
   - Rule-1 results were copied from `tranche1_source_register.csv#rule1_result` without recomputation.
   - The contradiction register carries forward all 20 earlier rows unchanged and adds new entries.
   - Everything is rebuilt by `tools/build_c8b.py --base <c8base> --out <c8out/B>`.

## Results
| Measure | Count |
| --- | --- |
| Candidates examined | 20 |
| Page-image checks | 39 (C8-PIC-01 to C8-PIC-39) |
| CONFIRMED checks | 36 |
| PARTIAL checks | 3 |
| UNCERTAIN checks | 0 |
| Candidate-level identity CONFIRMED | 20 of 20 |

- **What a candidate-level CONFIRMED means.** The S.R.O. number, the date line, the issue number, the issue date and Part II-Section 4 are all legible in the same held file, and they are consistent with the register identity.
- **The three PARTIAL checks.** Each is a partly illegible running header on the S.R.O. page; the S.R.O. number and date line on those pages are legible. In each case the issue date comes from the CONFIRMED masthead check of the same file:
  - C8-PIC-26 (T1-14, p.367): the Saka year is degraded and no Gregorian year is legible;
  - C8-PIC-32 (T1-17, p.214): the day digits are illegible;
  - C8-PIC-35 (T1-18, p.614): the month and day are faint.
- **Advisory F-T1-1.** For all seven `L5_DISCOVERY_REGISTER_ONLY` rows, the S.R.O. number and date line are now transcribed in a C8 check that has its own render hash. They no longer rest only on the R23 discovery register. This is still an AI-agent reading.
- **Issue numbers the register omits.** The register leaves out the issue number for 12 rows. The C8 readings add them:
  - T1-03: No. 13;
  - T1-08: No. 45;
  - T1-09: No. 6;
  - T1-10: No. 9;
  - T1-11: No. 14;
  - T1-12: No. 50;
  - T1-13: No. 21;
  - T1-14: No. 38;
  - T1-16: No. 46;
  - T1-17: No. 8;
  - T1-18: No. 41;
  - T1-19: Extraordinary No. 02.

  None of these conflicts with the register.

### S.R.O. 34/1963 (T1-02)
- **What the held instrument is.** The page image (C8-PIC-03, PDF p.2, printed p.14) shows "New Delhi, the 5th January 1963 / S.R.O. 34.—In pursuance of clause (e) of rule 188 of the Army Rules, 1954, and in supersession of ...". It is a **declaration** that officers of the Navy and Air Force exercise command over persons subject to the Army Act. It is signed "[No. 25003|PSI.] S. DEVANATH, Dy. Secy.". It appears in No. 3 of 19-01-1963, Part II-Section 4 (C8-PIC-02).
- **The 'S.R.O. 34 dated 5-6-1963'.** It is **not** equated with this instrument; the relationship is **UNRESOLVED** (C8-CR-02).
  - New context: the "SRO 34 dated 5 Jun 63" listing also appears in Gazette-printed NOTEs to Army Rules amendments from 1982 to 1991, inside this tranche's own files, not only in the 1988, 1993 and 2003 Government notes.
  - S.R.O. 2(E)/2018 lists "S.R.O. 34 dated 05th January, 1963".
  - No held document proves whether the NOTEs refer to this instrument.
- No amendment-chain inference is made.

## New discrepancies (`contradiction_register_c8.csv`)
- **C8-CR-01 (UNRESOLVED).** The S.R.O. 2(E)/2018 Note dates S.R.O. 240 as "05th June, 1955". The held S.R.O. 34/1963 recites "SRO 240, dated the 25th June, 1955". This is document-to-document; it affects none of the 20 identities.
- **C8-CR-02 (UNRESOLVED).** S.R.O. 34 relationship, as described above.
- **C8-CR-03 (OPEN).** The T1-20 CMS signature value fails the RSA integrity check against the embedded signer certificate, although the ByteRange spans the file and messageDigest matches.
- **C8-CR-04.** The T1-19 CMS integrity check passes; no chain validation was done. This is recorded for completeness.
- **Observations, not identity discrepancies:**
  - C8-CR-05: S.R.O. 246 has no printed signatory.
  - C8-CR-06: T1-02's running header is truncated.
  - C8-CR-08: the corrigendum's file number is "4(2)/884" where S.R.O. 55 has "84".
  - C8-CR-09: S.R.O. 169 has no printed file number or signatory.
  - C8-CR-10: the 10-10-1987 masthead sub-heading differs.
  - C8-CR-11: the 1991 instruments carry 1990 short titles.
  - C8-CR-12: S.R.O. 61/1991 prints "Army Act 1960 (46 of 1950)".
  - C8-CR-13: S.R.O. 235/1991 prints "Military Secretory", and the Hindi note list has misprints.
  - C8-CR-07 is not used.

## Recommendations (`eligibility_recommendations.csv`)
- **READY_FOR_OWNER_CONSIDERATION (18): T1-01 to T1-18.**
  - Each has rule 1 PASS and a freshly CONFIRMED identity, with its limitations recorded.
  - T1-02 is for **copy provenance only**: C8-CR-02 stays UNRESOLVED and no chain inference may rest on it.
  - T1-17 is one copy carrying two instruments.
  - 13 of these 18 rows still have only a register date, not a retrieval date in a retrieval record: T1-01, 03, 06, 08, 09, 10, 11, 12, 13, 14, 16, 17 and 18. T1-19 has the same gap, which makes 14 in total.
- **HOLD_FIDELITY_DECISION (1): T1-19 (S.R.O. 2(E)/2018).** It waits on owner decision P-D2. Its structure is clean and the CMS integrity check passes, but the chain has not been validated.
- **NEEDS_FURTHER_EVIDENCE (1): T1-20 (S.R.O. 17(E)/2019).**
  - The signature value fails integrity (C8-CR-03).
  - Needed: an independent copy (egazette.gov.in, or one with recorded provenance), or an explicit owner acceptance of the failure.
  - After that, it is still subject to P-D2.

## Limitations
- **AI-agent readings.** All transcriptions are by an AI agent, not human-confirmed. Hindi text was transcribed less reliably than English. Some 1980s pages have broken glyphs; where a character was unclear it is shown in [brackets] or with "?".
- **Pages not re-rendered.** Only identity pages were rendered (39 renders). These continuation and signature pages rest on earlier records and were not re-read in C8:
  - p.97 of T1-04;
  - p.10 of T1-06;
  - pp.259-261 of T1-07;
  - p.532 of T1-12;
  - pp.3-6 of T1-20.
- **Discovery, retrieval and completeness not re-established.** Retrieval provenance and completeness (page counts) are taken from the cited registers. C8 did not re-establish them. No network access was used.
- **Concepts kept separate.** Copy identity and copy fidelity are evidenced here. Documentary authenticity, current legal status and applicability are **not** established by anything in C8.
- **No cryptographic validation of trust.** No certificate chain, trust anchor or revocation was validated for either born-digital file. The CMS checks are integrity-only.
- **Contradiction register IDs.** The IDs "T1-CR-NN" were assigned in C8 to carry forward the 20 rows of `T1-GAZETTE/contradiction_register.csv`. Their content is unchanged.

## Output files (c8out/B/)
- `gazette_evidence_register.csv`
- `evidence/T1-01.md` to `evidence/T1-20.md`
- `page_image_checks_c8.csv`
- `contradiction_register_c8.csv`
- `eligibility_recommendations.csv`
- `born_digital_structure.csv`
- `BORN_DIGITAL_FINDINGS.md`
- `GAZETTE_C8_FINDINGS.md`
- `render_log.csv`
- `crop_log.csv`
- `tools/`: `rehash_and_render.py`, `crop_png.py`, `born_digital.py`, `rsa_diag.py`, `build_c8b.py`, `render_plan.csv`, `readings_notes.txt`
- `bd_work/`: JSON outputs, plus intermediate DER, PEM and signed-content `.bin` files (about 10 MB). The `.bin` files are copies of document bytes; commit only the JSON and `cms_print` files.
- `renders/`: PNGs and crops (not to be committed; their hashes are recorded)
