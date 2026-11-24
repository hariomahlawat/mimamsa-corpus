# Independent review of 30 high-risk judgments: findings and measured reliability

**Reviewers:** Fable 5.2 (`claude-fable-5-2`), sample A (rows 1-15) and sample B (rows 16-30) of `REVIEW_SAMPLE.csv`.
- Each PDF was checked against its SHA-256: 30 of 30 matched.
- Results are in `review_A.csv` and `review_B.csv`, with method notes in `review_A.md` and `review_B.md`.
- These are reviewer readings, not legal advice.

## Measured reliability of the automated extraction (this sample; high-risk and mostly Supreme Court, so not representative of the corpus)
| Field | Result in the sample | Consequence |
| --- | --- | --- |
| SHA-256 / file identity | 30 of 30 match | file integrity holds |
| `issue_date` (crawler metadata) | 29 of 30 right. One wrong: Sudip Biswas, P&H HC, where 29.09.2010 is an adjournment; the decision is 06.10.2010 | metadata dates are largely reliable; the queue flags differences |
| `decision_date_candidates` (extractor) | wrong wherever it was populated on the Supreme Court judgments: dates of cited cases, impugned orders, promotions | **not reliable for the Supreme Court layout.** `date_status = DIFFERS` on SC records is an extractor signal, not a metadata error |
| Case numbers (crawler metadata) | blank on every Supreme Court record. Corpus-wide check: **368 of 368 SC metadata records have no case number**, although each document prints one | a systemic metadata gap from the open-data source; a correction proposal is needed |
| Outcome (phrase candidate) | 13 confirmed, **15 wrong**, 2 ambiguous | **unusable without review** for multi-appeal or mixed disposals. Failure modes: last-phrase picks a pending-application line; quoted rule or third-party text ("remanded to police custody", Army Rule 25); disposals for the Union and the accused reversed |
| Candidate propositions | about 15 of 28 extracted are the court's own reasoning. The rest are quotations of other judgments, headnotes, footnotes or recitals, and **2 are misleading out of context** (for example a Delhi HC footnote stating the opposite of the Supreme Court's holding in Nitisha) | **leads only.** Never store one as a holding without reading the host paragraph |
| Relevance class | 19 agree, 11 disagree, mostly a boundary between direct military law and service/pension, all within scope. A CRPF Act case and an SSB (CCS CCA) case belong to general law | the classes are usable for triage, not for exclusion |
| Statute tagging | one judgment's sub-heading reads "Army Act" over AFT Act text | tags are mention counts, not determinations |

## Document-level findings for the corpus record
- **Composite file.** `Vijaynath Jha` (SC, C.A. 2020/2013) shares its PDF with an unrelated Delhi HC film case (pp.16-25). One file holds two judgments.
- **Two versions in one file.** Virendra Kumar (SC, C.A. 9267/2019, 07-01-2020): pp.1-21 are marked CORRECTED; pp.22-42 are the earlier version. The operative paragraphs differ.
- **Common judgments** whose metadata lists only one case: Nargolkar (W.P.(C) 13360 and 13367/2009), and the companion case numbers missing in Sandeep Kumar, Nitisha, S.K. Sahni and Metri.
- **Relation worth recording.** Major R. Metri (para 29) explains and confines Sandeep Kumar.
- **Printed inconsistencies inside source documents:**
  - Sahni: the court-martial date differs between headnote and para 47;
  - S.P. Sharma: the headnote prints "Army Act, 1959";
  - S.P. Gupta: prints 28-12-1981, while the reviewer recalls citations giving 30-12-1981 (not verified).
- **Treatment caution (reviewer recollection, not from the document).** Shri Kant Sharma, on High Court writs against AFT orders, was reconsidered in 2023. The C10 judicial workstream documents Parashotam para 32 ("does not lay down the correct law"). Any use of Shri Kant Sharma needs that check.

## What follows
1. The automated outcome and proposition fields stay labelled `AUTOMATED_CANDIDATE_NOT_VERIFIED`, and are now described as unreliable for the Supreme Court in the summary.
2. The reviewed values are recorded per judgment in `review_A.csv` and `review_B.csv`, and the verification queue marks these 30 as reviewed. The automated outputs are not overwritten, so history is preserved.
3. **Proposals (not applied):**
   - supply case numbers for the 368 Supreme Court records from the printed cover pages;
   - correct the Sudip Biswas date;
   - record the composite-file and two-version cases;
   - add companion case numbers;
   - record the Metri to Sandeep Kumar relation.
4. A better outcome extractor, for example a cue for "disposal in respect of each appeal", would need its own reviewed change. No such change was made in this cycle.

## Addendum: ordinary-judgment sample (workstream review of 3257ebb9, finding WS-04)
The 30-judgment sample above is risk-ranked: 28 of the 30 are Supreme Court judgments. The workstream reviewer separately drew 20 judgments at random from those not sampled, mostly High Court orders, and read each against its PDF. Per-row results are in `WS_REVIEW_SAMPLE20_3257ebb9.csv`.
- **Outcome candidate:** right 12, wrong 3, missed 4, not applicable 1. All three wrong ones took "pending applications stand disposed of" as the result of a petition that was in fact dismissed or allowed.
- **Crawler metadata (case number, date, outcome) was more reliable than the extractor on every field measured.** Where the two outcomes disagreed, the crawler was right 3 times out of 4.
- Corpus-wide, crawler outcome and text candidate disagree in 549 of the 1,775 records that have both; 349 of these are dismissed against disposed. Each now carries a contradiction note and raises the record in the verification queue.
- **How to use the outputs:** prefer the crawler metadata, and treat the text candidates as review signals only. This is now stated in the summary.
