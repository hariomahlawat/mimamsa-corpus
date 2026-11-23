# D3. Independent verification of the C6-01 proposals

**How it was done:**
- **Verifier:** a separate read-only agent with no network access. Outputs are verbatim in `review/verification_report.md` and `review/verification_findings.csv`.
- **Hashes:** re-hashed every held file.
- **Evidence:** opened every cited reference.
- **Identity:** read page 1 and the last page of every court copy, and rendered the masthead and notification pages of the Gazettes.
- **Contradictions:** searched the committed registers.

## First verification (commit 9b4ad44d): VERDICT ACCEPT WITH CONDITIONS
**Results:** of 34 proposals, 19 were VERIFIED, 14 VERIFIED_WITH_LIMITATION and 1 NOT_VERIFIED.

**Confirmed:**
- all hashes match;
- every evidence reference exists;
- no contradiction was found;
- Isaac is absent and pending;
- the builder and tests reproduce;
- the D4 figures are exact, and the 7 named case records are exactly the ones that change.

| Finding | Sev | Disposition |
| --- | --- | --- |
| AP-22 Act 13/1975: promoted on a download record that gives an India Code identifier, not a URL, with no date (NOT_VERIFIED) | P2 | **Corrected.** L4 now counts as FULL only with a URL. Act 13/1975 is now PROVENANCE_PARTIALLY_DOCUMENTED (strength IDENTIFIER_SHA) and has no proposal. |
| F-01 six Gazettes (AR-010/011/016/024/034/035) described as matching size, MD5 and SHA-1, when only MD5 and size were cited; stronger R23 reviewer-D retrieval records existed but were not collected | P2 | **Corrected.** The collector now reads every `*/sources/*.json`, which picks up the R23-VERIFY-01 reviewer-D records (URL + sha256). Those six are now FULL on retrieval records. The provenance-evidence text is derived from the actual match, not a fixed label. |
| F-02 MD5 plus size could reach DOCUMENTED, below the Cycle 4 bar | P2 | **Corrected.** Only FULL strength reaches DOCUMENTED; MD5_SIZE, IDENTIFIER_SHA and MD5 do not. Tests enforce this. |
| ACQ-02 supplement route never fired (the register records True/False) | P3 | **Corrected** (accepts yes/true) |
| AP-28 Rajbir rendition with UNKNOWN carrier classed as primary | P3 | **Corrected.** Now NON_PRIMARY_OFFICIAL_COURT_RENDITION, with the reason in its limitations |
| Rows resting on a register corroboration alone lacked the Cycle 4 caveat | P3 | **Corrected.** The caveat "accepted because uncontradicted (Cycle 4 PPS Bedi precedent)" is added automatically |
| AP-23/24 limitations did not say why they are non-primary | P3 | **Corrected.** Reasons added |
| AP-27 Rajbir rop copy evidenced only inside another record's locator | P3 | Kept as DOCUMENTED, with the limitation stated on the row. The retrieval record states the URL and sha256 for this exact file. |
| AP-21 archive.org derivative file | P3 | Recorded as a limitation where the snapshot marks a derivative |
| Statute class assigned from title text | P3 | No longer used: the only statute candidate, Act 13/1975, is no longer proposed |
| Act 13/1975 title "No.16" vs English issue No.15 | P3 | Noted for the C5 master title. The Cycle 5 register is not edited here; the correction is carried to the next C5 maintenance |

**Result after corrections (as of d58894c4; superseded by the closeout below):** 33 copies DOCUMENTED and 3 PARTIALLY_DOCUMENTED (TRA 2026, Delhi HC rules, Act 13/1975). The 33 proposals are 21 primary Gazette facsimiles, 9 primary court copies and 3 non-primary.

**Coverage:**
- Documented-primary copies would rise from 12 to 42, and sources from 12 to 41.
- Cases (53) with exact anchors would rise from 6 to 13.
- The KB figures are unchanged.

The re-verification of the corrected material is recorded in `review/reverification_report.md`.

## Re-verification (9b4ad44d..d58894c4): VERDICT ACCEPT WITH CONDITIONS, no P1 or P2
Verbatim: `review/reverification_report.md`. The verifier confirmed all six correction points: AP-22 downgraded; the six Gazettes FULL on the S-REVD retrieval records; FULL-only promotion; the non-primary rendition and the caveats; reproducible counts; Cycle 5 unaffected.

Its four P3 conditions were corrected:

| ID | Item | Disposition |
| --- | --- | --- |
| N-1 | Proposal IDs were sequential, so dropping Act 13 renumbered them | Proposal IDs are now stable: `C6-01-AP-<first 8 hex of sha256>`. **The AP-nn numbers in the first verification files refer to the 9b4ad44d numbering.** |
| N-2 | Act 13's next step asked for an identity check that had already been done | The next step is now derived from the actual gaps |
| N-3 | The sources glob would pick up future packages | Evidence folders are listed explicitly (PILOT-01, R23-VERIFY-01) |
| N-4 | Title-keyword statute-class rule; Act 13 masthead number | The rule is removed (statutes fall to the conservative non-primary default). The masthead number is recorded in `C6-PREP/C5_CARRYOVER_CORRECTIONS.md` (C5-CO-03). |

These are documentation and ID-stability changes only: at f0cd16a7 the outcomes (33 documented, 3 partial) and the coverage figures were unchanged.

## Closeout changes (e7a10e27)
- README denominators corrected (26 publication/record sources with 26 copies; 8 judgment sources with 10 copies).
- Method and builder comment now state the executable rule: DOCUMENTED needs FULL only.
- Page-image identity checks C6-PIC-01..04 on held copies (no download):
  - **TRA 2026:** CONFIRMED, so it is now DOCUMENTED, conservatively non-primary.
  - **Delhi HC Ch.6:** PARTIAL, because no court name or volume is printed. It stays PARTIALLY_DOCUMENTED.
- Act 13/1975 is unchanged, and its masthead finding is carried on the row.
- Legacy AP-nn to sha256 map added.

**Current outcomes:** 34 DOCUMENTED and 2 PARTIALLY_DOCUMENTED (Delhi HC Ch.6, Act 13/1975). The 34 proposals are 21 primary Gazette facsimiles, 9 primary court copies and 4 non-primary (RS papers-laid, ER 2023 13 MB, Rajbir rendition, TRA 2026). The coverage figures are unchanged, because the Cycle 4 rule gives non-primary classes no effect.

## Final independent review of e7a10e27: VERDICT ACCEPT WITH CONDITIONS (no P1; 2 P2)
**Review files:** verbatim in `review/final_review_e7a10e27.md` and `review/final_findings_e7a10e27.csv`. It was a separate read-only reviewer with no network access.

**What the reviewer checked:**
- re-hashed all held copies and recomputed all 36 copy facts;
- opened every evidence reference for all 34 proposals;
- confirmed the legacy ID map against 9b4ad44d and d58894c4;
- forced a duplicate ID and confirmed the builder stops;
- rendered TRA pp.1 and 15 and Delhi HC pp.1 and 5, which reproduced the C6-PIC render hashes;
- re-ran the coverage simulation.

**This review is the verification of the TRA proposal and the four C6-PIC checks (R-11).**

| ID | Sev | Finding | Disposition |
| --- | --- | --- | --- |
| R-01 | P2 | D2, D3 and D6 still gave 33/3/33 and "TRA partial" | **Corrected:** D2 lists 4 non-primary entries; D3 labels the earlier figures with their commit and adds this section; D6 is rewritten; a test ties report counts to the summary |
| R-02 | P2 | Incorporation was described as a Cycle 4 addendum only, but the simulation switches off the Cycle 5 holding-state check | **Corrected:** D4, D6 and the addendum plan state that a reviewed Cycle 5 holding-state relabel is also required, and that the build must run with the check on |
| R-03 | P3 | The Cycle 4 rule has no NON_PRIMARY_* class | Stated in D2 and D4; the addendum plan requires a resolution at incorporation |
| R-04 | P3 | TRA rationale omitted the Cycle 4 watermark precedent | **Corrected:** the rationale now gives born-digital plus signature byte range as the distinction; the class is an owner decision |
| R-05 | P3 | Three locator routes are looser than documented | Documented in METHOD "Known rule limits"; current rows were checked by hand |
| R-06 | P3 | Identity rules are broad; T was attributed to PPS Bedi | Attribution corrected; limits documented |
| R-07 | P3 | "English No.15" lost its "uncertain" qualifier | **Corrected** on the row and in C5-CO-03 |
| R-08 | P3 | RS papers-laid authenticity UNCONFIRMED; item-page URL | Stated in its limitations; listed as an owner decision |
| R-09 | P3 | Carrier and locator vocabulary differs from Cycle 4 | Normalisation is required at incorporation (addendum plan) |
| R-10 | P3 | Test gaps | **Corrected:** duplicate-rejection test, non-tautological ID-stability test, Cycle 4 register sha256 pinned, report counts tied to the summary |
| R-11 | P3 | TRA and C6-PIC not covered by earlier reviews | Covered by this review |
| R-12 | P3 | C5 ER 2023 master cites T3-02 rather than T3-01 | Added as C5-CO-04 |

The corrections after e7a10e27 were re-reviewed (see the re-review section, added once that review completes).
