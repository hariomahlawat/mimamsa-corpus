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

**Result after corrections:** 33 copies DOCUMENTED and 3 PARTIALLY_DOCUMENTED (TRA 2026, Delhi HC rules, Act 13/1975). The 33 proposals are 21 primary Gazette facsimiles, 9 primary court copies and 3 non-primary.

**Coverage:**
- Documented-primary copies would rise from 12 to 42, and sources from 12 to 41.
- Cases (53) with exact anchors would rise from 6 to 13.
- The KB figures are unchanged.

The re-verification of the corrected material is recorded in `review/reverification_report.md`.
