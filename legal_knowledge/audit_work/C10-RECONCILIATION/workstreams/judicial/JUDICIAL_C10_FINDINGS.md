# Cycle 10, workstream C: judicial evidence findings

**Status.** Evidence findings only.
- Nothing is authenticated, registered, merged or corrected.
- No legal status is changed. Every proposal is `PROPOSAL_NOT_APPLIED`.
- Page readings are text-layer readings by an AI agent (Claude Opus 5.5 subagent), **not human-confirmed**. Each reading gives its PDF page.
- No page images were rendered in C10.
- No network download was made. HF small text files were read through the HF connector, read-only.

**Reproduce.**
```
python -I tools/build_judicial_c10.py --repo <clone> --c10 <C10-RECONCILIATION> --store <scratchpad>/downloads --check
```
- Result at writing: `CHECK OK: 10 outputs reproduce byte-identically`.
- Pinned inputs:
  - raw-data `ad77758d`;
  - staging `21e73b83`;
  - PR #40 head `9a6f9366` (C8 SC-T2, C9 SC-C9);
  - PR #41 head `cfc52d57` (C9 CORRECTIONS);
  - the C10 inventory, hash-checked against `RECONCILIATION_MANIFEST.json`;
  - `inputs/hf_lk_text_readings.json`;
  - 18 working-store PDFs, each re-hashed before use (all MATCH).
- Every quotation is checked verbatim (whitespace-insensitive) by the builder, and the build fails on any miss.
- Input and output hashes are in `JUDICIAL_C10_MANIFEST.json`.

## 1. Deterministic judgment reconciliation (`JUDGMENT_RECONCILIATION.csv`)

**Copy universe.** One row per distinct judgment copy (SHA-256): **3,973 copies**.
- 3,951 crawler copies, held on both HF and GitHub raw-data: 3,605 HC and 346 SC.
- 14 copies held only in the C5 working store.
- 8 HF `legal_knowledge` binaries.

**Grouping keys.** Copies are grouped only on deterministic keys:
- neutral citation;
- normalised SCR report citation;
- case type + number + year **together with** the decision date.

Title similarity is never used.

**3,961 groups.**

| Group class | SC | HC |
| --- | --- | --- |
| EXACT_DUPLICATE (one sha, several locations; mostly the HF/GitHub mirror) | 338 (336 also MISSING_OFFICIAL_ORIGINAL) | 3,605 |
| DIFFERENT_RENDITION | 9 (3 also MISSING_OFFICIAL_ORIGINAL) | 0 |
| SINGLE_COPY | 8 (2 MISSING_OFFICIAL_ORIGINAL, 1 CORRECTED_JUDGMENT) | 0 |
| MULTIPLE_COPIES_SAME_JUDGMENT | 0 | 0 |
| SAME_KEY_DIFFERENT_DECISION_DATES_REVIEW | 1 | 0 |
| INCOMPLETE_COPY | 0 determined | 0 |

**The 9 DIFFERENT_RENDITION groups:**
- PPS Bedi, Ranjit Thakur and S N Mukherjee: JUDIS typed text + SCR. No signed original is held.
- Dharamvir: JUDIS-path court layout + SCR.
- Rajbir: C1 JUDIS-path + C2 ROP + C3 bosir + SCR. Its case-number keys include the connected C.A. 10105/2011.
- Girish: official PDF + SCR.
- Parashotam: official PDF + SCR.
- N S (Narsingh) Yadav: official PDF + SCR.
- P S Gill: official PDF (also on HF `legal_knowledge`) + SCR.

**Other group findings:**
- **CORRECTED_JUDGMENT.** Mullikote `10e1954f` is one file that carries the corrected second version (pp.32-62; C9 Q-MULLIKOTE-VERSION).
- **Review case (Kudrat Sandhu).** Two SCR records share the neutral citation `2018 INSC 185` but have different dates (22-02-2018 and 21-08-2018) and different SCR citations. This is an index inconsistency. The records are not merged.
- **INCOMPLETE_COPY.** No copy was shown to be incomplete on deterministic evidence. Girish SCR (12 pp.) against the official copy (17 pp.) is a repagination, not a truncation.
- **Duplicate metadata.** 22 SC copies carry two crawler metadata records each (year-prefix duplicates such as `sc-1982-…` and `sc-1983-…`). This is flagged `ONE_COPY_2_CRAWLER_META_RECORDS`.
- **HC copies.** No HC copies were grouped across different shas.

## 2. The 53 curated cases (`CURATED_CASE_COPY_STATUS.csv`)

**Held status.**

| Held status (C10) | Cases |
| --- | --- |
| HELD (deterministic key, or declared C5-crosswalk / HF-sidecar case id) | 33 |
| CANDIDATE_HELD_DATE+PARTY_ONLY | 3: N04 Hussain, N14 Charanjit Gill (SCR page conflict: curated 244, copy 245), L11 Naga People's Movement |
| CANDIDATE_HELD_WSB_DECLARED_LINK_ONLY (curated record has no date, case number or citation) | 6: L02, L03, L07, L08, L09, L10 |
| NOT_HELD_EXCLUDED_FROM_CRAWLER_STORE | 2: N07 L. Chandra Kumar (1997-03-18) and L05 S.R. Dhingra (2007-12-14), both removed as "no military keyword" |
| NOT_HELD | 9: 008 clarification, N03, A01, A04, A05, A06, A08 Ram Avtar, A10, R02 |

**Copy type and register status.**
- **Official court PDF held:** 6 cases (Virendra, Jasbir, Girish, Parashotam, Arjun, Mullikote).
- **Court-hosted JUDIS-path layout:** 3 cases (Dharamvir, Rajbir, Anvar).
- **All other held cases** have only JUDIS renditions, SCR renditions or a third-party mirror.
- **C5 status:** 12 REGISTERED, 17 HELD_UNREGISTERED, 24 NOT_HELD. The NOT_HELD count includes the candidate and excluded rows.

**Held-status changes against WS-B.**
- **DCLR-SC-1964-A11, Ram Sarup: HELD_UNREGISTERED.**
  - WS-B recorded `CITATION_METADATA_CONFLICTS_WITH_OFFICIAL_RECORD_NO_COPY`.
  - HF `legal_knowledge` holds JUDIS 3387 (`88f84411`, 10 pp.).
  - Its HF working text, p.1, prints "RAM SARUP", "DATE OF JUDGMENT: 12/12/1963" and "1964 SCR (5) 931". The SCR citation equals the curated reporter_citation.
  - There is no C5 source-register row. Confirmed.
- **DCLR-SC-2016-L04, Mani Ram Bhaira: HELD_UNREGISTERED.**
  - WS-B recorded `…NO_COPY`.
  - HF holds a third-party mirror (`cce64004`, host virendersinghkadian.com) that prints "CIVIL APPEAL No. 4409 OF 2011".
  - The page also carries a digital signature dated 2016.02.26 (HF text p.1).
  - There is no C5 row. Confirmed.
  - It is not an official court copy, so the case is also recorded under `MISSING_OFFICIAL_ORIGINAL`.
- Navjot, Isaac, Virendra and P S Gill: the HF `legal_knowledge` bytes are declared with the same sha as the registered C5 copies, so they are EXACT_DUPLICATE. HF bytes are NOT_CHECKED.

**Recorded inconsistencies:**
- curated date empty but printed: A11 (1963-12-12), L01 (2005-08-04);
- curated case number empty but printed: N02 (C.A. 417/1984), L01 (Crl.A. 373-375/2004 etc.), L04 (C.A. 4409/2011);
- SCR page conflict: N14 (244 vs 245);
- title spelling: A11 ("Ram Swarup" vs printed "RAM SARUP").

## 3. The Supreme Court eight and PPS Bedi: other copies, and SCR comparators

**Other copies (`SCR_COPY_IDENTITY.csv`).**
- **SCR-format copies in the raw store:**

  | Case | Copy | Citation |
  | --- | --- | --- |
  | Ranjit | `35b9c948` | [1988] 1 SCR 512 |
  | S N Mukherjee | `239c4e38` | [1990] Supp 1 SCR 44 |
  | Dharamvir | `a9ccc45c` | [2013] 8 SCR 1119 |
  | Rajbir | `c1ecdaee` | [2015] 2 SCR 183 |
  | Girish | `da030473` | [2026] 2 SCR 615 : 2026 INSC 149 |
  | N S Yadav | `d031a88d` | [2019] 13 SCR 260 |
  | PPS Bedi | `ebb86d4b` | [1983] 1 SCR 393 |

- **Navjot and Mullikote:** no other copy. The HF Navjot file is the same sha as the C5 copy.
- **Also recorded:** Tarsem `f8a14181`, Parashotam `483b70cb`, Shri Kant Sharma `86de3643`, S P Rathore `2f89730f` and P S Gill `009ea86c`.

**Identity and provenance of the SCR copies.** Recorded first:
- Every SCR copy has `source_url` on the host `indian-supreme-court-judgments.s3.ap-south-1.amazonaws.com`. This is the AWS Open Data copy of e-SCR records, retrieved 2026-11-21.
- All are UNREGISTERED_HELD, a third-party mirror, and **not a signed court original**.
- The printed date, case number, bench and report start page agree with the crawler metadata, except for these limits:
  - The S N Mukherjee date is not legible in the text layer ("AUGUST 28. 199ti").
  - The Girish start page is not printed as a standalone number.
  - The older reports (Ranjit, S N Mukherjee, PPS Bedi) print no bracketed citation on p.1.

**Comparator results (`SCR_COMPARATOR_RESULTS.csv`).** The SCR copies were used only as comparators.

| Case | Body word-sequence ratio | Headnote ratio |
| --- | --- | --- |
| Ranjit | 0.958 | 0.925 |
| S N Mukherjee | 0.947 | 0.869 |
| PPS Bedi | 0.922 | 0.897 |
| Dharamvir | 0.972 | |
| N S Yadav | 0.972 | |
| P S Gill | 0.978 | |
| Rajbir | 0.914 | |
| Parashotam | 0.901 | |
| Girish | 0.722 | |

- The ratios are indicative only: the SCR text layer carries OCR noise.
- The high headnote ratios support reading the JUDIS "HEADNOTE" as the reporter's editorial headnote, not judgment text.
- The Girish ratio is low because whole texts were compared, including the SCR headnote.

**Targeted checks.**
- **SCR-C01:** The Ranjit JUDIS date "3.?.1986" (p.3) is confirmed as a defect. The comparator reads "3. 7.1986" (SCR p.5).
- **SCR-C02:** The Ranjit editorial note on the 10.8.88 order appears before "delivered by" in both renditions. It is reporter matter.
- **SCR-C03:** The PPS Bedi JUDIS "rules 22, 23, 2S and 40" (p.7) is confirmed as a defect. The SCR copy prints "25" (SCR p.7).
- **SCR-C04 (new; resolves CC9-26):**
  - The WSB-H-053 passage ("subject to the overriding consideration…") is on JUDIS p.20, within the stated pp.19-21, between inline report pages 418 and 419.
  - In the SCR copy it is on PDF p.26, printed report page 418.
  - So the wrong locator is "SCR p.426-427". Proposal C10J-CP-04.
- **SCR-C05 and SCR-C06:** The crawler `judges` field holds one name only.
  - PPS Bedi: printed bench Chandrachud CJ, Desai and A.N. Sen JJ; author Desai J.
  - Ranjit: printed bench A.P. Sen and Venkatachaliah JJ; author Venkatachaliah J.
- **SCR-C07 to SCR-C10:**
  - S N Mukherjee: C.A. 417 (of 1984) agrees.
  - Dharamvir: (2013) 7 SCC 316 is printed in neither held rendition.
  - N S Yadav: C.A. 7672/2019 agrees.
  - Girish: the para 22 wording agrees.

Existing historical classifications are preserved. That includes the C5 class of PPS Bedi and the C9 "exactly four JUDIS typed-text renditions" finding. With Ram Sarup on HF, that becomes five held JUDIS typed-text files; Ram Sarup is unregistered.

## 4. Judicial treatment (`JUDICIAL_TREATMENT_C10.csv`, `TREATMENT_CITATION_HITS.csv`)

**Method.**
- A deterministic search ran over 4,250 held SC/HC judgment texts (of 4,259 metadata records), covering decisions up to 2026-11-03.
- It found 2,034 hits: 1,958 after the cited decision and 76 before it, which cannot be citations of that judgment.
- Hits are split into CITATION_STRING and NAME_ONLY_REVIEW_REQUIRED. Name-only hits include false positives; one example is a party's father named Tarsem Singh.
- 32 quoted readings were made: 21 treatment readings and 11 holding readings.
- Hits that were not read are `NOT_DETERMINED (not read)`.

**Treatment readings by class:** APPLIED 12, DISTINGUISHED 5, CLARIFIED 2, OVERRULED 1, NOT_DETERMINED 1.

**Priority cases:**
- **Tarsem Singh** (C.A. 5151-52/2008, 13-08-2008; SCR copy only).
  - Holding, SCR p.5 para 5 and p.6 para 6: arrears normally restricted to three years.
  - DISTINGUISHED by Girish para 22 on two grounds (official copy pp.15-16).
  - NOT_DETERMINED: Mullikote para 43 left the question open (official copy p.27).
  - APPLIED after Girish by the Delhi HC: W.P.(C) 16771/2025, 11-03-2026, p.9.
  - DISTINGUISHED by the Delhi HC: W.P.(C) 2053/2026 (ACP claim).
  - **Not overruled** on the held documents.
- **Girish Kumar** (2026 INSC 149).
  - Holding, p.16 para 22: s.22(1)(c) bar inapplicable.
  - 24 held HC judgments cite it after decision. Of the 3 read, all APPLY it to non-party claimants (P&H HC CWP 7955/2026 p.3: "has been settled").
- **The 12-10-2026 clarification (2026 INSC 1113).** NOT HELD and NOT CITED anywhere in the held stores:
  - 0 hits for "2026 INSC 1113";
  - 0 Girish-related "clarif*" passages;
  - the only held judgment dated 12-10-2026 does not mention Girish.
- **Parashotam** (2023 INSC 265).
  - Holding, official copy p.22 para 32.
  - APPLIED by SC 2023 INSC 1074 (SCR p.16).
  - DISTINGUISHED by the Allahabad HC, WRIA 2923/2026 p.5.
- **Shri Kant Sharma** (2015 INSC 206; SCR copy only; two Judges).
  - **OVERRULED in documentary wording** by Parashotam para 32: "does not lay down the correct law". That Bench had three Judges.
  - The typed edge still needs human verification (ESC-06). No status is changed.
  - It was still APPLIED by the J&K HC on 06-10-2025 (WP(C) 2370/2025 p.2).
- **Ram Avtar** (C.A. 418/2012, order of 10-12-2014). NOT HELD.
  - APPLIED by Girish as in rem.
  - CLARIFIED by S P Rathore para 8 (SCR pp.4-5): it "only held" that rounding off applies under para 8.2, and "did not deal with" entitlement.
- **S P Rathore.** Only the SCR copy is held, and it is the same sha as the WS-B "intern mirror".
  - Holding, para 9 (SCR p.5).
  - APPLIED by the J&K HC on 18-08-2026.
- **N C Isaac** (2026 INSC 993; official copy).
  - Holding, p.93 para 39(iii): Rule 7 burden-shift after 15 years.
  - It CLARIFIES Dharamvir for the 2008 Rules (p.91 para 34).
  - APPLIED by the J&K HC on 28-09-2026.
- **Dharamvir:** APPLIED by Rajbir para 15; CLARIFIED by Isaac.
- **Rajbir:** APPLIED by Mani Ram Bhaira. That reading is from HF mirror text; the order prints "2015 (12) SCC 264".

## 5. Correction proposals and escalations

**Correction proposals (`CORRECTION_PROPOSALS_C10.csv`).** 9 proposals, all `PROPOSAL_NOT_APPLIED`.
- The current text of each was verified verbatim or as empty.
- Proposals:
  - A11: date and party name;
  - L04: case number;
  - WSB-H-053: SCR locator;
  - three crawler-metadata fixes (judges ×2, a polluted title);
  - V7-JD-04: optional wording (depends on ESC-01);
  - DCLR-SC-2026-007: SCR citation (conditional on registration).

**Escalations (`ADVISER_ESCALATIONS_C10.csv`).** 6 open questions:
- ESC-C10-01: Tarsem after Girish.
- ESC-C10-02: acquire or confirm the clarification.
- ESC-C10-03: what survives of Shri Kant Sharma; edge type.
- ESC-C10-04: Isaac against Dharamvir.
- ESC-C10-05: whether SCR renditions can be registered as comparators.
- ESC-C10-06: re-acquire Chandra Kumar and S.R. Dhingra.

## 6. Effect on the C9 CORRECTIONS findings (`C9_FINDING_STATUS_C10.csv`)

**No C9-F status changes.** All 23 keep their C9 status (`PROPOSAL_NOT_APPLIED`, or `RECORDED_ELSEWHERE` for D05).

| Effect | Findings |
| --- | --- |
| Evidence added | A01, A02, A05, A07, E01, E02 |
| Strengthened | A04 (deterministic negative search for the clarification) |
| Confirmed | A03, E04 |
| Clarified | E06 (the S P Rathore "intern mirror" is the raw-store e-SCR rendition) |
| Unchanged | A06, E03, E05 |
| Not affected (statutory matters) | 10 |

## 7. Exact-anchor note (C9 simulations 6/7/13/10/11/9)

**No change expected.** This is stated qualitatively; no simulation was re-run.
- The newly identified held copies are the SCR-format raw-store copies and the HF-only Ram Sarup and Mani Ram Bhaira files.
- They have no C5 source-register or copy-register row, no `copy_facts.csv` row and no accepted image check, so the rule-1 reader cannot create an anchor from them.
- Navjot on HF is byte-declared identical to the C5 copy that is already in the simulations.
- The PPS Bedi option (b) asymmetry (CC9-28) is unaffected.

## 8. Limitations

- **HF bytes NOT_CHECKED.** HF `legal_knowledge` identities rest on HF sidecars and HF working-text excerpts. The HF revision is not pinned.
- **AI readings only.** All readings are AI agent text-layer readings, not human-confirmed. No signatures were validated.
- **Mirrors and renditions.** Held HC judgments come from the AWS eCourts mirror; parity with court-hosted copies was not checked. SCR copies are third-party renditions.
- **Treatment search is not exhaustive.** It covers only the crawler corpus, and most hits are unread (`NOT_DETERMINED`). The absence of a hit is not proof that no treatment exists.
- **Declared links.** The 6 WS-B-declared and 3 date+party links are candidates, not deterministic matches.
- **Comparator ratios** are indicative only.
