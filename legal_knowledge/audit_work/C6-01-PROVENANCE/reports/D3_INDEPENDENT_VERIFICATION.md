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

**Outcomes at e7a10e27 (superseded below):** 34 DOCUMENTED and 2 PARTIALLY_DOCUMENTED (Delhi HC Ch.6, Act 13/1975). The 34 proposals are 21 primary Gazette facsimiles, 9 primary court copies and 4 non-primary (RS papers-laid, ER 2023 13 MB, Rajbir rendition, TRA 2026). The coverage figures are unchanged, because the Cycle 4 rule gives non-primary classes no effect.

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

## Re-review of e7a10e27..c3235312: VERDICT ACCEPT (no P1 or P2)
**Review files:** verbatim in `review/final_rereview_c3235312.md` and `review/final_rereview_findings_c3235312.csv`. The same reviewer confirmed:
- both P2s are fixed;
- no outcome or class changed: the summary JSON is byte-identical, and only limitation text differs;
- the addendum draft is deterministic, with crosswalk effects on 7 cases;
- the prep changes make no download, correspondence or legal claim; the metadata log validates, and the only GETs are robots.txt;
- the scope is limited to C6 paths, and the tests pass.

Its five P3 wording items are corrected in the following documentation-only commit:

| ID | Item | Disposition |
| --- | --- | --- |
| RR-01 | the plan named non-existent Girish/Navjot second copies | corrected: the primary entry that changes no row is N S Yadav |
| RR-02 | the draft justification claimed a Cycle 4 class for non-primary entries | corrected: non-primary entries say there is no Cycle 4 class; TRA says its class is reserved |
| RR-03 | D3 said "were re-reviewed" before the re-review existed | corrected by this section |
| RR-04 | "no GET was made" | corrected to "no GET other than robots.txt" |
| RR-05 | only internal policy letters were flagged as outside the CLAUDE.md scope | corrected: Army Orders and unpublished material, which covers AO 13/2006/PS and possibly the handbook, are flagged for an owner scope decision |

## Independent Fable 5.2 review of a165b0f3: VERDICT ACCEPT WITH CONDITIONS (no P1; 9 P2, 17 P3)
- **Reviewer:** Claude Fable 5.2 (`claude-fable-5-2`), as the model self-reported. It was requested through the Claude Code Agent tool (model `fable`, agent type `independent-reviewer`).
- **Tools:** Read, Glob and Grep only, so it had no write, shell, git or commit capability, and it was instructed not to use the network.
- **What it received:** the commit, file locations and criteria, not the coordinator's conclusions.
- **Record:** a condensed record in `review/fable_review_a165b0f3.md`, confirmed faithful in substance by the reviewer (re-review N-08).
- **What it could not do:** hash files or run code. The coordinator's gate re-hashes held files and runs the builders separately.

| ID | Sev | Finding | Disposition (commit after a165b0f3) |
| --- | --- | --- | --- |
| F-01 | P2 | Rajbir C2 proposed primary on C1's record | **Corrected by rule:** a sha256 mentioned inside another record's locator is now `L3lead` (a lead, never FULL). C2 is PARTIALLY_DOCUMENTED with a copy-level finding (ROP pages; not a duplicate; signature range not covering the file). The Rajbir case is anchored by C1 alone |
| F-02 | P2 | Disclaiming retrieval records counted as FULL; RS stayed DOCUMENTED | **Corrected by rule:** a record with `authenticity=UNCONFIRMED`, or `verification_state` NOT_FOUND/CONFLICTING, is `L3x` (a lead). The RS record is PARTIALLY_DOCUMENTED by rule and also WITHHELD; its sitting date is recorded as resting on the file name |
| F-03 | P2 | S.R.O. 34 identity inference written as fact | **Corrected:** the identity is annotated UNVERIFIED (05-01-1963 declaration versus the notes' "5-6-1963"), with a documentary finding forbidding amendment-chain inference |
| F-04 | P2 | TRA comparison omitted comparators | **Corrected:** one uniform copy-fidelity rule for born-digital copies (signature range must cover the file; archive derivatives are not the issued file), computed from `inputs/copy_structure_c6.csv`. 2018/2019 stay primary (signature covers the file). **2022 (`2bdab5b7`) moves to non-primary** (archive derivative). TRA stays non-primary. The comparison now has four comparators |
| F-05 | P2 | D3/D4/D6 contradicted the plan and architecture | **Corrected:** D4 and D6 rewritten for the overlay design; counts derived from the summary; tests assert no "relabel" and the current counts |
| F-06 | P2 | Architecture "either way" output option broke reproducibility | **Corrected:** architecture revision 2 (overlay package C′). C4/C5 files and tools are frozen and hash-pinned; outputs are versioned in `effective/vNNNN/`; the rule version is pinned per manifest line |
| F-07 | P2 | Plan, architecture and draft disagreed | **Corrected:** the architecture is the single specification. The plan covers process only. The draft follows `addendum_entry.schema.json` (entry type, first-class record, reviewer ref), validated on every build; a hash-chained manifest is specified |
| F-08 | P2 | Classification change possible without evidence | **Corrected in the design and the draft:** references must resolve (checked by the builder); an ADD needs a first-class record keyed by its own sha256; decisions are committed, hash-pinned files; carrier/class changes go only through the ledger; strength computation moves into the ledger package (no code cycle) |
| F-09 | P2 | Anchoring and withdrawal under-specified | **Corrected in the design:** copy-level anchoring with page equivalence; WITHDRAW with a mandatory reason and an optional resulting state; orphan rules; audit trail in a separate file; joint-effect diffs; a newly-withdrawn change list |
| F-10 | P3 | T rule too weak | **Corrected:** T also needs the year or case number from the title on p.1 |
| F-11 | P3 | C6-PIC-02 misreading | **Corrected** in the reading (render hash unchanged); the correlated error is noted |
| F-12 | P3 | Offline signed-revision check | **Done:** the TRA file has one %%EOF marker (a rewrite, not an incremental update), so no signed revision is extractable |
| F-13 | P3 | Item page shown instead of file URL | **Corrected:** the direct file URL is preferred |
| F-14 | P3 | "as reported" qualifier stripped | **Corrected:** kept unless a direct retrieval record exists |
| F-15 | P3 | Mullikote corrected judgment | Limitation added |
| F-16 | P3 | JUDIS headnote/citator material | Limitation added to the JUDIS rows |
| F-17 | P3 | `/judgment/judis/` locator variant | Limitation added; URL normalisation is specified for the ledger validator |
| F-18 | P3 | Re-acquisition yields a new copy; handwritten mark | **Corrected:** next steps and evidence-recovery text updated; mark recorded after the coordinator's re-read |
| F-19 | P3 | Delhi HC currency markers | Recorded; currency UNKNOWN, historical text |
| F-20 | P3 | S.O. 4010 date semantics | Recorded as UNVERIFIED (reviewer's Saturday inference noted as inference) |
| F-21 | P3 | Copy facts hashed one path; silent extraction failure | **Corrected:** every path (43) is hashed; failures stop the run |
| F-22 | P3 | build_prep docstring | **Corrected** to state that `--check` needs local git objects |
| F-23 | P3 | Hard-coded counts; no report check | **Corrected:** denominators derived from Cycle 5; reports gain `--check`; UTF-8 writes |
| F-24 | P3 | Tests keyed by prefix; collision remedy | **Corrected:** tests key by full sha256; synthetic prefix-collision test; the remedy lengthens only colliding IDs |
| F-25 | P3 | WITHHELD simulated; descriptor restore | **Corrected:** WITHHELD is never simulated; the original classmethod descriptor is restored |
| F-26 | P3 | Diff-scope and hash checks not possible for the reviewer | **Done in the coordinator's gate** (git diff scope, held-file re-hash, corpus and Cycle 4 hashes) and recorded in the PR |

**Current outcomes:** 32 DOCUMENTED and 4 PARTIALLY_DOCUMENTED. The 32 proposals are 20 primary Gazette copies, 8 primary court copies and 4 non-primary. Simulated coverage: documented-primary copies 12 to 40; sources 12 to 40; cases 6 to 13; KB unchanged. 
## Fable 5.2 re-review of 4bf0a96a: VERDICT ACCEPT WITH CONDITIONS (no P1; 1 new P2)
The same reviewer, so not independent of its first review. Condensed record: `review/fable_rereview_4bf0a96a.md`. Of F-01..F-26 it marked 17 FIXED and 9 PARTLY (F-02, F-07, F-08, F-09, F-10, F-16, F-17, F-22, F-26). Answers: no DOCUMENTED row rests on a sibling-copy or disclaimed record; the fidelity rule is applied in code to every non-judicial copy and the 2022 reclassification is supported; report counts match the summary.

| ID | Sev | Finding | Disposition |
| --- | --- | --- | --- |
| N-01 | P2 | `first_class_record_ref` took the first sorted item (snapshot rows without sha256); no own-sha256 check; substring resolution | **Corrected:** priority L3, L1, L4, ACQ-02 supplement; the referenced record is parsed and must carry the entry's own sha256; resolution is by exact row key; negative tests added. Result: 14 ACQ-02 supplement rows, 7 R23 retrieval records, 11 PILOT-01 records |
| N-02 | P3 | Rajbir C2 "signature range does not cover the file" was a 4-byte host prefix; misattributed | **Corrected:** coverage is measured from the %PDF header (`YES_AFTER_PREFIX`); the finding now says the range spans the PDF and is attributed to the coordinator |
| N-03 | P3 | JUDIS headnote limitation applied by URL pattern | **Corrected:** only where p.1 shows the markers (Ranjit, S N Mukherjee); otherwise "headnote presence not checked beyond p.1" |
| N-04 | P3 | Derivative trigger not evidentially uniform | **Corrected:** derivative also detected by an Internet Archive producer; each archive.org primary row states its producer and whether derivative status is inferred; "signed range spans the file" wording |
| N-05 | P3 | Schema could not express CORRECTION/WITHDRAW | **Corrected:** `target_entry_id`, `withdrawal_reason`, `resulting_state`; conditional non-empty/empty rules per entry type, enforced by the builder's validator; tested |
| N-06 | P3 | Architecture gaps (v0 anchoring, transition table, inputs, frozen C5) | **Corrected:** copy-level anchoring is rule version 2 (v0 uses the frozen rule 1); HELD_PRIMARY without a primary copy needs a resulting_state or is a hard error; evidence facts copied into the overlay as pinned inputs; discovery tooling not frozen; carry-over corrections become overlay correction records |
| N-07 | P3 | Stale METHOD text; tautological T test | **Corrected:** METHOD limits and class table rewritten; T decoy test and synthetic UNCONFIRMED test added |
| N-08 | P3 | Review file labelled verbatim | **Corrected:** relabelled as a condensed record |
| N-09 | INFO | Mis-decoded producer | Producer values are now ASCII-normalised |
| F-03 residual | - | C5 title still says "notes misdate" | Added as C5-CO-05 |
| F-22 residual | - | No C6-PREP rebuild test | Added (all columns except the two that need the crawler PR commits) |
| F-25 residual | - | Unlabelled 13-row block | Labelled in the summary |

## Fable 5.2 focused re-review of 2964a477: VERDICT ACCEPT WITH CONDITIONS (no P1, no P2)
Same reviewer (not independent of its earlier rounds). N-01 (the P2) FIXED: all 32 first-class references verified against the referenced records (rows 11 and 14 now name ACQ02-02 and S-REVD-003). N-02 to N-06, N-08 and the three residuals FIXED; N-07 and N-09 PARTLY. No outcome or class changed. Four new P3 items, corrected in the following commit:

| ID | Finding | Disposition |
| --- | --- | --- |
| M-01 | prefix-resolution test would pass under substring logic | **Corrected:** tests assert that true prefixes (`SRC-RANJI`, `S-BLIND-01`) do not resolve and the full key does |
| M-02 | superseded block still in METHOD | **Corrected:** duplicated sections and the old limits block removed |
| M-03 | D3 count slip; 2019 derivative status wording | **Corrected:** 17 FIXED / 9 PARTLY; the 2019 file is in the ACQ-01 snapshot (`source: original`), so only 2018 is producer-inferred |
| M-04 | carry-over corrections cannot be ledger entries; resulting_state is copy-level | **Corrected in the design:** documentary corrections go to a separate `corrections/notes.csv` (not the ledger); a source-level mapping for `resulting_state` is given |

Residual by construction: the per-type rules in the schema use custom `x-nonempty`/`x-empty` keywords that the builder enforces; a standard JSON Schema validator would not.

**Still open by design (owner options, not defects):** the affirmative-state L3 rule (F-02); external image rows without a result field (F-10); URL normalisation in the builder's contradiction test (F-17); independent, git-capable verification of diff scope and hashes (F-26), which the coordinator's gate performs but no independent reviewer with git access has repeated at this head.
