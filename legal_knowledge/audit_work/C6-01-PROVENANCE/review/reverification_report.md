# C6-01 re-verification (commit d58894c4)

Scope: only the material that changed between 9b4ad44d and d58894c4 in the C6-01 package and its test file. The work was read-only, with no network access. Python ran with PYTHONDONTWRITEBYTECODE=1, and the worktree is still clean.

**VERDICT: ACCEPT WITH CONDITIONS (P3 documentation items only; no P1 or P2 remains)**

| # | Check | Result |
| --- | --- | --- |
| 1 | AP-22 / Act 13/1975 | **Confirmed.** Sha 8358d2b3 has no proposal. The D1 row reads PROVENANCE_PARTIALLY_DOCUMENTED, strength IDENTIFIER_SHA, and the copy is listed in the unresolved register. |
| 2 | The six Gazettes (AR-010/011/016/024/034/035) | **Confirmed.** All six are FULL. Each now cites R23-VERIFY-01/sources/independent-reviewer-D.json S-REVD-003/004/005/006/009/010. For every record, I recomputed the sha256 of the held file and it equals the record's sha256. The locator contains the exact archive.org download URL, local_path names the held file, and retrieved_on is 2026-11-22 (SOURCE_VERIFIED). The evidence text now reads "MD5 and size equal to archive.org metadata; retrieval record with URL and sha256", which is accurate. AR-035 carries the "derivative" limitation. |
| 3 | Only FULL reaches DOCUMENTED | **Confirmed.** The builder condition is `strength == "FULL" and (I or t_ok)`, and the test asserts FULL. MD5_SIZE, IDENTIFIER_SHA and MD5 can reach PARTIAL at most. Two FULL routes remain that are weaker than a copy's own retrieval record, and both carry a limitation: (a) L1 alone, the PPS Bedi precedent with its caveat; (b) the L3 "(locator)" note used for the Rajbir rop copy. |
| 4 | Rajbir bosir copy, Cycle 4 caveat and non-primary reasons | **Confirmed.** The bosir copy (6b495f14) is NON_PRIMARY_OFFICIAL_COURT_RENDITION, with its reason in the limitations. The Cycle 4 caveat appears on all four rows that rest on L1 alone (Girish, Mullikote, Ranjit, S N Mukherjee). The RS and ER 2023 rows give their non-primary reasons. |
| 5 | Counts | **Confirmed.** 33 documented and 3 partial; 33 proposals, 30 of them primary class (21 Gazette + 9 court). D4: cases 6/7/40 → 13/0/40, KB figures unchanged, documented-primary copies 12→42, sources 12→41, pending 1. `--check` returns rc 0. The tests pass 12/12 (9 C6-01 tests plus 3 new C6-PREP tests; none removed). The Cycle 5 and CALIBRATION-02 registers are unchanged in the commit, and a test re-derives Cycle 5 byte-for-byte. |

## New defects (all P3)
- **N-1 Proposal ID drift.** Dropping Act 13 renumbered the proposals: the old AP-23..34 are now AP-22..33. D3_INDEPENDENT_VERIFICATION.md and review/verification_findings.csv still use the old numbering, so "AP-22" now names the Rajya Sabha row. Fix: add an old→new mapping, or key the findings by sha256.
- **N-2 Act 13/1975 gap text.** The unresolved row repeats the date gap ("no retrieval date; no retrieval date in a retrieval record"). Its next_step is generic ("page-image identity check ... or a byte-level locator record"), but identity is already image-checked. The real step is a retrieval record with the resolvable URL, or an owner decision.
- **N-3 Wider sources glob.** The sources glob is now `*/sources/*.json`. Today that matches only PILOT-01 and R23-VERIFY-01, but any future package with a `sources/` folder would be picked up silently. Fix: list the directories explicitly.
- **N-4 Unaddressed earlier P3 items.** Two remain: the Act 13/1975 masthead number (No.15/No.16) is not in its identity text, and the class rule still keys on the word "Gazette" in the title. Neither affects any current proposal.
