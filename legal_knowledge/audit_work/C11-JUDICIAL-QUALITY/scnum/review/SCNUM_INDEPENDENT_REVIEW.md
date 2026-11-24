# C11 SC case-number proposals - independent documentary review

Reviewer: Fable 5.2 (claude-fable-5-2). Independent AI documentary review; **not legal validation**. Date: 2026-11-24.
Detail per record: `SCNUM_INDEPENDENT_REVIEW.csv` (98 rows; column `sample_set` = UNCERTAIN_48, CONFIRMED_SAMPLE_20 or MULTI_SAMPLE_2). The first 68 rows are in `outputs/REVIEW_QUEUE.csv` order; the last 30 are the second multi-matter sample in selection order.

## What was done

- All 68 queued rows (63 distinct source PDFs) were extracted with `git -C /home/user/c7 show ad77758d:<source_path>`; every file's sha256 equals the queued sha256 (68/68 `sha256_verified=YES`).
- For every row the jurisdiction heading (and the p.1 cause title where one is printed) was read from a rendered page image (pymupdf `get_pixmap`), not from the stored OCR text. For the four very long modern lists (rows for 2022insc850, 2022insc757, 2024insc754, 2026insc149) the born-digital text layer was re-parsed with a separate script and spot-checked against the image.
- Host = the Supreme Court's own matter numbers in the heading, including WITH / AND connected matters. Impugned lower-court numbers and parent matters ("IN ...") were not counted as hosts.
- Second sample (added at the coordinator's request): the 95 CONFIRMED_MULTIPLE_CONNECTED rows of `SC_CASE_NUMBER_PROPOSALS.csv` not already in the queue were ordered by sha256('C11-SCNUM-MULTI-v1' + doc_id) ascending and the first 30 reviewed the same way (all 30 PDFs re-extracted, sha256 verified, heading read on a page image; next page rendered wherever the heading reached the foot of the page; long lists counted and first/last items checked).
- Nothing outside this folder was modified; no metadata was changed; nothing was committed.

## Verdicts

### 48 uncertain rows (45 PARTIALLY_CONFIRMED + 3 AMBIGUOUS)

| verdict | PARTIALLY_CONFIRMED | AMBIGUOUS | total |
| --- | --- | --- | --- |
| CORRECT | 24 | 0 | 24 |
| PARTLY_CORRECT | 21 | 2 | 23 |
| WRONG | 0 | 0 | 0 |
| UNVERIFIABLE | 0 | 1 | 1 |
| total | 45 | 3 | 48 |

Rows are per doc_id; five source files appear twice (Raghubar Dayal, Achudan Nair, Bhim Singhji, S.P. Gupta, Sampath Kumar), so the 48 rows are 43 distinct documents (CORRECT 22, PARTLY_CORRECT 20, UNVERIFIABLE 1).

Of the 24 CORRECT rows, 13 are "etc." headings (all flagged `connected_matters_elided_by_etc`): the proposal reproduces everything the heading prints, but the heading itself elides connected matters, so the record stays incomplete by source, not by parser. The other 11 are OCR repairs, separator fixes or inherited types that the page image confirms (e.g. `I 099` -> 1099, `82 I` -> 821, `200L` -> 2001, `I 0623` -> 10623, `!988` -> 1988, `879 1209`).

No proposal was wholly wrong. In the PARTLY_CORRECT rows the lead number is right in every case except where noted below; the defects are missing years, missing connected matters, and a handful of wrong individual elements.

AMBIGUOUS rows:
- S.P. Gupta (2 doc_ids): the page supports the HOST reading for T.C. 19-22/1981; the later "In Transferred Cases Nos. 19, 20, 21 & 22/81" is a counsel-appearance sub-heading. But `WP-2-YEAR?` is wrong (page: Writ Petition No. 274 of 1981) and SLP(C) 1509 is of 1981.
- Veerendra Kumar Dubey: the document contradicts itself in clear print - heading p.6 "Civil Appeal D. No. 32135 of 2013", cause title p.1 "D.No. 32135 of 2015". Diary number confirmed; year cannot be decided from the document (UNVERIFIABLE).

### 20 sampled CONFIRMED rows

| verdict | CONFIRMED_FROM_SOURCE | CONFIRMED_MULTIPLE_CONNECTED | total |
| --- | --- | --- | --- |
| CORRECT | 14 | 6 | 20 |
| PARTLY_CORRECT / WRONG / UNVERIFIABLE | 0 | 0 | 0 |

All 20 match the page image in type, number and year, including WITH matters that continue on the next page (S.R. Tewari, P. Chandramouly).

### 30 further CONFIRMED_MULTIPLE_CONNECTED rows (MULTI_SAMPLE_2)

| verdict | rows |
| --- | --- |
| CORRECT | 29 |
| PARTLY_CORRECT | 1 |
| WRONG / UNVERIFIABLE | 0 |

- The one defect: **sc-2026-baksish-ahmad-2026insc630**. Hosts CA 8452 and 8453 of 2026 are right, but the proposal adds `RP-38-2025` as a third host. The page prints it inside the arising-from sentence ("From the Judgment and Order dated 10.01.2025, 29.08.2025 of the High Court of Delhi ... in WP (C) No. 229 of 2025 and RP No. 38 of 2025, respectively") - it is the impugned High Court review petition, not a Supreme Court matter. The "and" inside the From-sentence was read as a connected-matter marker.
- Completeness held in every list checked, including the page-crossing ones: R. Gandhi (WITH matter on the next page), Manish Kumar (41 matters across pp.33-34), Anuj Kumar Dey, Rupajan Begum, In Re Construction of Park at Noida. Long lists counted and matched: Dinesh Kumar 62, Manish Kumar 41, Supriyo 21, Tamil Nadu Medical Officers 17, SCAORA 16, Kudrat Sandhu 14, Swiss Ribbons 11.
- One source caveat on a CORRECT row: Union of India v. Dinesh Kumar (2010insc99) prints "1255, 1556, 1257" in clear type; `CA-1556-2010` reproduces the page but is almost certainly a misprint for 1256.
- No year was lost and no number was truncated in this sample. The failure modes seen in the uncertain set (year at end of list, truncation at page turns) did not recur among records the tool marked CONFIRMED, which suggests its flags are routing those cases to review as intended.

## Precision estimate for CONFIRMED

"Correct" = every host number, type and year equals what the SCR rendition prints in the jurisdiction heading / cause title, with nothing missing and nothing extra.

| stratum | population | reviewed | fully correct | observed precision | one-sided 95% lower bound |
| --- | --- | --- | --- | --- | --- |
| CONFIRMED_MULTIPLE_CONNECTED (6 from first sample + 30 from second) | 101 | 36 | 35 | 97.2% | 87.5% |
| CONFIRMED_FROM_SOURCE (first sample only) | 219 | 14 | 14 | 100% | 80.7% |
| all CONFIRMED, weighted by stratum size | 320 | 50 | 49 | 99.1% | about 87% (see note) |

- **Multi-matter records: 35/36 = 97.2%; exact binomial (Clopper-Pearson) one-sided 95% lower bound 87.5%** (two-sided 95% interval about 85.5%-99.9%). Before the second sample the bound for this class was about 61% (6/6). The bound is conservative: 36 of the 101 have now been read, so the uncertainty applies only to the remaining 65; at the observed rate that is about 2 further defective records, and at the lower bound about 8.
- The one error is an extra, wrong element (an impugned-matter number promoted to host), not a wrong or missing host number. Counted per element rather than per record, the 36 multi-matter records carry 280 proposed host numbers, of which 279 are correct.
- Single-matter records: still only 14 reviewed (14/14, lower bound 80.7%). This is now the weaker of the two strata statistically, although it is also the structurally simpler case and no single-number CONFIRMED proposal has failed.
- Note on the overall figure: the 50 reviewed rows are not one simple random sample (multi-matter rows are over-sampled), so 49/50 should not be read directly as the overall rate. The weighted point estimate is (219 x 100% + 101 x 97.2%) / 320 = 99.1%; a cautious overall lower bound is governed by the two stratum bounds above (roughly 80%-88%), not by the pooled 49/50 figure (which would give 90.9%).
- Limits unchanged: this tests agreement with the SCR heading only - not connected matters mentioned only in the body, and not the official SC record.

## Patterns of error (uncertain set; item 9 from the second multi-matter sample)

1. **Year lost when it is printed once at the end of a list, or on the next line/page** (most frequent). Single-number cases: Achudan Nair (1974), Chief of Army Staff 1985 (1978), K.D. Gupta (1987), Vijay Shankar Mishra (2016). Lists: Rajbir Singh 2015 (14 appeals, all 2011), Vishay Priya Singh 2016 (4 appeals, 2011), Virender Singh 2022 (12 SLPs), Vijay Madanlal (31 writ petitions; source prints "OF OF 2021"), Rajeev Bansal 2024 (169 appeals, 2024). In every such case the year was recoverable from the page.
2. **List truncated - connected matters dropped.** Raghubar Dayal ("22 to 26 and 42 of 1959" -> only 22), R. Viswan (16 writ petitions dropped), Raghunathrao (WP(C) 798/1992 dropped), Rajbir Singh (6 dropped), Vishay Priya Singh (CA 10104/2011), Vijay Shankar Mishra (12180), Amit Kumar Sharma (17 appeals after a parenthesis), Virender Singh (6 at the page turn), Rajeev Bansal (379 appeals after the list crosses pages - the largest single gap; proposal has 367 of 746). Causes seen: page break / running header inside the list, parenthetical alias "(@ ...)", OCR-broken digits, and the fixed block length.
3. **Number truncated to its first digits.** S.P. Gupta `WP-2` (274 of 1981), Virender Kumar `CRLMP-5` (5726 of 1993), Union Carbide `UNK-29` (C.M.P. 29377-A/88), Bommai `CA-14627` (printed "4627-30 of 1993", i.e. 4627-4630). These are the only outright wrong elements and all are already flagged `YEAR?`/unrecognised except Bommai's `CA-14627-YEAR?`.
4. **Case type lost or misread.** R. Viswan "P. (CRL)" = W.P. (CRL); Union Carbide type on the previous page ("Civil Miscellaneous Petition" at the foot of p.24); Puttaswamy `PET-844-2017` = Contempt Petition (C) 844/2017; bare "Diary Nos." given an inherited CADIARY type (Amit Kumar Sharma, Girish Kumar 2026) - an inference the page does not state.
5. **Host vs parent / connected confusion.** Virender Kumar: W.P.(Crl.) 1741/81, 1344/85, 1604/85 are parents ("IN") but listed as hosts. Union Carbide: the "(With W.P. Nos. ...)" connected matters were filed under arising_from. Amit Kumar Sharma: `CA-846-YEAR?` duplicates CA-846-2022.
6. **Abbreviated second number.** Union of India 1992: page prints "2449 and 50 of 1992"; reading as 2449 and 2450 is the natural one, `CA-50-1992` should not be applied as it stands.
7. **Defects in the source itself** (not parser errors): Veerendra Kumar Dubey year conflict 2013 vs 2015; VKC Footsteps range "4769-4744"; Pavitra "879 1209" without comma; Vijay Madanlal "OF OF 2021"; Virender Singh "D.No.15702 SLP of 2021". These need the official SC record, not more parsing.
8. **"etc." elisions** (13 rows): correctly flagged; nothing further is printed in the heading. Bodies sometimes give a count ("These four appeals", "the two Special Leave Petitions") but not numbers.

9. **Impugned matter promoted to host** (second sample, CONFIRMED row): Baksish Ahmad `RP-38-2025`, joined by "and" inside the From-sentence. Worth a targeted re-check of other CONFIRMED rows whose host list contains a type that normally belongs to a lower court (RP, OA, TA, MA without a parent) or whose host year predates the lead matter by more than the usual gap.

Side observations outside the host-number question: K.D. Gupta impugned writ is printed 5702 of 1985 (queue note shows WP-5302-1980); Mafatlal impugned matter is F.A. 1681/1980 (queue: PA-1681-1980); Vijay Madanlal impugned "Criminal Application 1132/2012" is coded `CA-1132-2012`, colliding with the Civil Appeal code; Nand Kishor heading also names TA 157 of 2009.

## Limits of this review

- One reviewer, one pass, reading page images; no second reader. Small or broken type was zoomed where needed (Raghubar Dayal, Bommai), but a misread digit by the reviewer is possible.
- Year assignment inside mixed lists such as "815, 843, 632/80, 844, 5116/81, ..." follows the trailing-year convention and is marked as inference in the CSV notes.
- The three largest lists were checked by independent re-parse of the born-digital text plus image spot checks, not digit-by-digit against the image.
- Source is the SCR rendition in the corpus; no official SC judgment or external database was consulted.
