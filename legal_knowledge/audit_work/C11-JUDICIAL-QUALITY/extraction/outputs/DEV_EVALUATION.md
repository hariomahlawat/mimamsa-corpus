# DEV evaluation: `c11-extract-v2/1.0.0` outcome extraction

**Read this first.** The 50 judgments below are the Cycle 10 reviewed samples, and they are the set the extractor was **tuned on**: 30 high-risk judgments in `review_A.csv`/`review_B.csv`, plus 20 random ones in `WS_REVIEW_SAMPLE20_3257ebb9.csv`. Every rule was written or adjusted while looking at these judgments, and at about 380 other unreviewed judgments read during development. The 100% dev precision below is therefore an **optimistic, in-sample number**. It is not evidence for automatic promotion. Only the coordinator's blinded holdout (`C11-JUDICIAL-QUALITY/holdout/`, which this workstream never opened) can measure out-of-sample precision. Holdout precision is likely to be lower.

## Gold labels
- The gold labels are in `tools/dev_gold.json`. They are the reviewers' readings (`outcome_as_printed`, `outcome_read_by_reviewer`), mapped by this workstream to the v2 vocabulary.
- Where a reviewer marked a reading AMBIGUOUS, every defensible label is accepted:
  - J-937ee988: allowed or disposed_of_with_directions;
  - J-dc60fe00: allowed or disposed_of_with_directions;
  - J-72a623bb: allowed or set_aside_and_remanded;
  - J-cc2c318a: transferred or disposed_of_with_directions for the host case.
- Six judgments have mixed per-proceeding gold: J-3a4ed1ab, J-86de3643, J-a8793e00, J-2e72a6e9, J-9a20470d and J-cc2c318a. These count as correct only if v2 emits a separate row per proceeding and every row matches.
  - J-cc2c318a is a common order. Its second case (OWP 1933/2014, 'dismissed') was read by this workstream from the text layer, not by the C10 reviewer.

## Result (final frozen version)
| Set | n | non-abstained | correct | precision (non-abstained) | coverage |
| --- | --- | --- | --- | --- | --- |
| All dev | 50 | 41 | 41 | 100% (41/41) | 82% |
| Review A+B (high-risk, mostly Supreme Court) | 30 | 24 | 24 | 100% | 80% |
| WS random 20 (mostly High Court) | 20 | 17 | 17 | 100% | 85% |

Excluding the 2 judgments with no text file at the commit, coverage is 41 of 48 (85%). J-3a4ed1ab now abstains with DISPOSITION_WITH_EXCEPTION_OR_CARVE_OUT. One expected abstention (J-b43240e4, 'For orders see LA.APP. 784/2005') abstained correctly. Per-row results are in `DEV_EVALUATION_ROWS.csv`.

**Old signals on the same 50**, scored by outcome family against the same gold; mixed judgments count as incompatible:
| Signal | labelled | compatible with gold |
| --- | --- | --- |
| Crawler `outcome_meta` | 37 | 30 |
| Old phrase extractor (C10 `jextract`) | 38 | 24 |

## Tuning trajectory (in-sample)
The first complete version, before any dev-driven change, predicted 36 of 50 judgments with 31 correct: **86.1% precision, 72% coverage**. Each error was a structural failure, and each was fixed structurally, not by adding a phrase:

| Judgment | First-version error | Structural fix |
| --- | --- | --- |
| J-3a4ed1ab (SC, mixed) | a single `dismissed` taken from the last paragraph | The operative part now extends back over adjacent disposition paragraphs. Straight quotes are paired by direction (a mispaired quote had hidden paragraphs 32-38). The judgment now **abstains** on conflicting dispositions without a mapping, because the Delhi-appeal result is printed as a participle ('allowing the appeals … we remit'), which is not parsed. |
| J-9a20470d, J-a8793e00 (SC, mixed) | collapsed to one outcome | The clause-boundary regex was case-insensitive, so 'and others' and 'and Sandeep Kumar' were cut as clauses. It is now case-sensitive, and 'whereas' and ', and the' are boundaries. Per-proceeding rows come from case numbers (Diary Nos., Criminal Appeal Nos.) or party descriptors. |
| J-2e72a6e9 (SC, mixed) | conflict / extra row | 'Transferred Case' is no longer read as the verb 'transferred'. A blank-line sentence split at page breaks was removed. Modal 'deserves to be dismissed' is dropped once plain dispositions exist. |
| J-cc2c318a (J&K common order) | one `dismissed` for two cases | Block headings (a case-number line followed by paragraph 1) scope each block's disposition. 'deems it proper to transfer' is parsed. |
| J-ddf835f6 (S.P. Gupta, 7 opinions) | `transferred` from a wrong segment | A final ORDER heading containing 'majority' is chosen. A trailing ORDER after the last signature is kept as its own segment. |
| J-7d526d8a (J&K) | `dismissed`, gold withdrawn | A withdrawal sought in the operative part, followed by 'dismissed … as prayed', maps to dismissed_as_withdrawn. A guard stops this for non-prosecution, merit, in limine and maintainability. |
| J-1de6c12b, J-ed2a29d1 (S.C.R.) | spurious segments | The author line ('DR. D.Y. CHANDRACHUD, J.' followed by the text) and place names in quoted letters are no longer counted as signatures. |
| J-76a1a41c (SC) | `not_final` from 'listed for judgment today' | Not-final cues now need imperative or future forms ('List on…', 'be listed'). The judgment now abstains, because the last part is a separate opinion with no disposition. |
| J-0f65307432 (composite file) | took the disposition of the unrelated Delhi HC judgment on pp.16-25; the label matched by coincidence | A page that opens with a court header and a cause title for a foreign case starts an ignored document. The SC disposition at p.15 is now used. |

## Remaining abstentions on dev (9)
| Judgment | Reason | Comment |
| --- | --- | --- |
| J-0ff9d2fc, J-3f49a314 | NO_TEXT_FILE_FOR_THIS_SHA_AT_COMMIT | No text layer at ad77758d for these shas |
| J-3a4ed1ab | DISPOSITION_WITH_EXCEPTION_OR_CARVE_OUT | Mixed result; one group of appeals is disposed of by a participle; correct to abstain |
| J-76a1a41c | NO_DISPOSITION_IN_OPERATIVE_PART | The file ends with a separate opinion; the majority's disposal is earlier |
| J-8a2bafba | NO_DISPOSITION_IN_OPERATIVE_PART | 'we do not deem it … and dismiss the petition': a coordinated active verb without an adjacent subject is not parsed |
| J-b159ba17 | EXTENT_QUALIFIED_ALLOWANCE… | 'allowed to the extent indicated above' (gold: partly allowed). This is a deliberate precision-first rule, because the same wording also means a full allowance in other judgments (seen in non-dev samples) |
| J-b43240e4 | NO_OPERATIVE_CUE_IN_FINAL_PART | Expected abstention: the order refers to another file |
| J-db5d2083 | NO_DISPOSITION_IN_OPERATIVE_PART | The disposal is followed by a postscript longer than the 9,000-character window |
| J-eb24633d | NO_DISPOSITION_IN_OPERATIVE_PART | No explicit disposal phrase ('no ground is made out for any interference'); correct to abstain |

## Developer spot checks outside the dev set (not independent)
The developer ran three successive random checks on judgments outside the dev set. The first two were used to fix defects, so they are in-sample too. Only the third was taken after the final freeze.

| Check | Sample | Non-abstained rows | Clear errors | Used for tuning? |
| --- | --- | --- | --- | --- |
| A (seed 4242) | 60 random, mostly High Court | 53 | 1 | yes |
| B (seeds 777/778) | 30 SC + 30 HC | 51 | 4 (+1 uncertain) | yes |
| C (seeds 31337/31338), **after the final freeze** | 25 SC + 25 HC, unseen | 36 (14 abstained; coverage 72%) | 0 (1 uncertain, 1 borderline) | **no** |

The errors in checks A and B, all fixed before the final freeze, were:
- J-671bb4b3: 'dismissed except to the extent mentioned above'. Fix: an exception or carve-out before or after the disposal verb now leads to abstention.
- J-1c1d91b1: 'all the appeals – except the appeal filed by VOICE [SLP 2805/1999] – are dismissed'. The exception's number was mapped to the dismissed group. Fix: `DISPOSITION_WITH_EXCEPTION_OR_CARVE_OUT`.
- J-db759e27: 'except for the enhancement of compensation …, the appeal fails and is dismissed'. Same fix.
- J-4b49e5aa (SC): 'The Writ Petition filed by the Respondent shall stand dismissed' was taken as the appeal's result. Fix: the respondent's writ petition is treated as the proceeding below.
- J-898ad432: 'amounts … deposited and allowed to be withdrawn' was read as a withdrawal. Fix: 'contempt' counts as a proceeding noun only in 'contempt petition' or 'contempt case'.
- J-0e53c235: the evidence came from the S.C.R. reporter's note ('Civil Appeal Nos. … allowed.'). Fix: reporter's notes that contain case numbers are now editorial. The judgment now emits only 'CA 2670/2002 = dismissed', because 'the other appeals are allbwed' is OCR-garbled. A numbered disposition is no longer generalised to all host proceedings.
- J-0f653074 (dev): the outcome came from an unrelated S.C.R. report bound in the same file (p.25). Fix: S.C.R. case-head detection ('X v. Y (Writ Petition (Civil) No. …) MONTH DD, YYYY') at the top of a page starts a foreign document. The outcome now comes from p.15.

Check C items:
- Uncertain: J-4fc7f931 is `not_final`. It is a reference judgment followed by a listing direction, which is plausibly correct.
- Borderline: J-a2593fdc is `disposed_of_with_directions` where 'Let the record be transferred to the AFT' precedes 'disposed of'. Strong forms beat the subjunctive, so the output is the literal printed disposal.

These checks were read by the developer from excerpts with about 450 characters of context before and 300 after. They are weak signals, not measurements. Supreme Court coverage is clearly lower than High Court coverage.

## Error analysis and residual risks for the holdout
1. **Extent and exception qualifiers** ('dismissed except to the extent', 'allowed in the above terms' combined with partial relief). The literal disposal word is reported, but in substance the relief may be partial.
2. **Literal 'disposed of'** where the relief is granted in substance (J-f50df131, J-937ee988): v2 reports `disposed_of_with_directions` as printed. A reviewer who records the substance would call these 'allowed'.
3. **Inferred allowance** (`inferred_from_set_aside_of_impugned_decision`) is used only when the impugned order is set aside and no disposal sentence exists. It is a weaker method and can be filtered out through `method`.
4. **Mixed SC judgments.** Per-proceeding mapping needs case numbers or 'filed by' party descriptors in the subject of the disposal clause. Anything else abstains.
5. **Quoted context without quotation marks or an intro colon** can still be read as the court's own words if it sits in the final window.
6. **OCR-garbled S.C.R. and two-column P&H first pages.** Garbled operative text abstains (`GARBLED_TEXT_IN_OPERATIVE_PART`). Lightly garbled text can still pass.

Recommendation: apply the 95% promotion bar to holdout precision on non-abstained rows, optionally per `method` family. Until then, treat v2 as a third reading next to the crawler and the old extractor. It does not replace either.
