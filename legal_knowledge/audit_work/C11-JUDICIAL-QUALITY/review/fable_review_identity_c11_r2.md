# Confirmation review of the C11 judgment-identity workstream, revision 2

Reviewer: Fable 5.2 (claude-fable-5-2), AI documentary review. Not a legal verification.
Date: 2026-11-24. Reviewed at commit 9bd2629f on `claude/c11-judicial-quality` (identity folder clean), tool `c11-identity/2`. Bytes from `/home/user/c7` at `ad77758d`, re-hashed before use.
The reviewed worktree was not changed; work ran in a disposable copy under `scratchpad/rev_id2/`. `holdout/` was not opened. Nothing was downloaded or committed.

## Verdict

**ACCEPT.** The claimed count of **3,625** distinct judgments (3,631 if the six pointer orders are counted) is supported by the PDFs, and I found no wrong merge anywhere in the register.

Three P3 items remain. None changes the count.

## Count arithmetic

`IDENTITY_SUMMARY.json` adds up, and the register agrees with it.

| Step | Change | Count |
| --- | --- | --- |
| Files | | 3,959 |
| Exact same-text groups | -230 | |
| Normalised text (12 earlier groups -61, seven-copy Delhi order -6, J&K -1) | -68 | |
| Incomplete copies, all-page match | -3 | |
| Scanned copies by lead case (three sets -27, two tail-cut pairs -2) | -29 | |
| Pointer orders linked to the lead judgment | -6 | |
| **Judgment keys in the register** | | **3,623** |
| Judgments inside composite files | +2 | |
| **Distinct judgments** | | **3,625** |
| Without the pointer rule | | 3,631 |

- The register has 3,623 distinct keys over 3,959 rows.
- Every multi-copy key is explained by a group in `SAME_TEXT_GROUPS.csv`, and each has exactly one representative.
- Group changes sum to -336.

## Dispositions checked

| ID | Disposition claimed | Checked against | Result |
| --- | --- | --- | --- |
| F1 | Scan-aware step; three sets merged (-27); 081a8b226793 order keyed (+1) | The 30 files, read in the first review; group rows and keys now | **Confirmed.** Jamna 20 files → one key; Bikram Singh 4 → one; Puttan Lal batch 6 → one. |
| F1 | No wrong merge by the new rule | All five scanned-copy groups (the rule merged nothing else in the corpus) | **Confirmed.** The other two groups are the complete copies ce55eaab30f4 and e1eafb46003e joined to their tail-cut copies; every page matches apart from the signature stamp. |
| F1 | 8 date-differing matches left apart | Text of all 10 files involved | **Correct to leave apart.** None is a duplicate; details below. |
| F1 | W.P.(C) 18383/2025 vs 18333/2025 kept apart | Both files | **Correct.** Two different judgments of 03.12.2025 (6 and 5 pages, different respondents); 18333's page header wrongly prints 18383. |
| F2 | Seven-copy Delhi order merged (-6), dates routed | Group row, keys, routed list | **Confirmed.** One key, 7 copies; the seven metadata dates are listed for the metadata workstream. |
| F3 | J&K 34 + 10 merged (-1); P&H pair apart | Keys | **Confirmed.** One key, 44 copies. CWP-21348-2026 and CWP-21336-2026 keep separate keys. |
| F4 | Wording "86 of 87" | README | **Confirmed.** |
| F5 | Composite keys | Register and summary | **Confirmed.** `JK-0f65307432d16f74#p16-25` (Adarsh, SCI:WPC-129-2018) and `JK-081a8b22679359ab#p9-10` (order of 13.11.2009, C.M. 11902/2009 in WP(C) 2881/2008) match the pages I read. |
| F6 | Fuller cause-title parsing, still partial | J&K row | **Confirmed.** 35 proceedings listed (was 6) of 46 printed; column is named partial. |
| F7 | Six pointer orders linked (-6) | Group rows; files read in the first review | **Confirmed.** Five P&H sheets of 18.05.2015 → CWP 6958/2012; CACP 69/2025 → CWP 1947/2025. c1a83ee07b70 is linked on its printed date, not its wrong metadata date. |
| F8 | First-page rule retired; 3 merges remain | Group rows; all-page comparison from the first review | **Confirmed.** 38bd54/928d53 (76 common pages), 9809fa/d992ac (12), ed1344/f841d3 (4 full pages and a header). The two tail-cut pairs moved to the scanned-copy step and are still merged. |
| F9 | Split verdict flagged | Register row b64df349c9f5 | **Confirmed.** Flag carries both page ranges and judges. |
| F11 | Routed | Summary | **Confirmed.** |

## The eight date-differing matches

All eight pairs are different decisions, so leaving them apart is right.

| Files | What they are |
| --- | --- |
| 105f115e1ba1 / 9e46f07d096f | RSA 184/2016 order of 17.10.2016 quotes the RSA 26/2016 judgment of 05.09.2016 (*Ishwar Singh*) at length |
| 29d1295728c1, 5548cadbeca3, 6b311ccb6be6 (three pairs among them) | Three different BSF petitioners' orders (W.P.(C) 824, 904, 1376/2026; 21.01, 22.01, 02.02.2026), each citing *Kalu Ram* in the prayer |
| 29d1295728c1 / 3cc4e478e570 | W.P.(C) 824/2026 order against the *Kalu Ram* (W.P.(C) 4350/2025) extension-of-time order of 09.12.2025 |
| 7d566f898e51 / 8cdf53b311e2 (two rows) | W.P.(C) 6717/2018 final order of 08.12.2020 quotes the interim order of 24.07.2020 |
| b939e753e635 / ee32d6f13bf3 | Two different judgments (W.P.(C) 5759/2019, 15.12.2020; W.P.(C) 8002/2020, 12.01.2021), same bench and counsel |

## Reproducibility

- `--check` in the venv: "OK, all outputs reproduced byte for byte", exit 0, 4m38s.
- Tests in the venv: 16 run, OK, 1 skipped by design (the no-PyMuPDF path). Includes five new tests for F1, F2/F3, F5/F9 and F7.
- Tests on python3.11: 16 run, OK, 1 skipped (the rebuild, with reason). `--check` prints the skip reason and verifies checksums and accounting, exit 0.

## Remaining findings

| ID | Severity | Finding | Requested action |
| --- | --- | --- | --- |
| R2-1 | P3 | The scanned-copy content test is loose: it reports a full match for different orders that only share boilerplate. Only the date guard kept them apart. No wrong merge resulted. | Tighten the per-page threshold or strip portal boilerplate first; add a test with two different same-day orders that cite the same lead case. |
| R2-2 | P3 | The representative copy is always the lowest sha, so some judgments are represented by a poor copy. | Prefer a complete, born-digital, non-pointer copy as representative. |
| R2-3 | P3 | The candidate rows describe the 8 date-differing matches as "a later order carrying a copy of the judgment, or a metadata date error". Six of the eight are neither: they are different cases. | Reword; mark the eight as reviewed and distinct. |
| R2-4 | INFO | All F1-F11 dispositions verified; count arithmetic and reproduction confirmed. | None. |

Evidence for R2-1: the tool records "text pages matched 1.0 of 2 / 1.0 of 2" for 29d1295728c1 against 3cc4e478e570, 5548cadbeca3 and 6b311ccb6be6, which are four different two-page orders. A page counts as matched at 30% shared three-word sequences, which Delhi portal footers and bench boilerplate reach on their own.

Evidence for R2-2:
- `JK-479005fadfeb6c65` (CWP 6958/2012, 9 pages) is represented by a one-page pointer order.
- `JK-455c9c7517c140c0` (Bikram Singh) is represented by a scan although a born-digital copy (75f7c670d822) exists.
- `JK-03439ba04b14…` and `JK-9f299cc2467f…` are represented by tail-cut copies although complete copies exist.

## Limits

- The first review's limit still holds in part: scanned duplicates with poor OCR and no footer or pointer could remain undetected. The new step now runs corpus-wide on the lead case rather than within a metadata date, and found nothing beyond the three sets.
- I re-read the files for the new or changed decisions (the eight pairs, the 18383/18333 pair, key and flag rows). For merges already verified page by page in the first review I checked that the groups and keys are unchanged in membership, not the PDFs again.
- Nothing was checked against official court sources.

## Files

- `fable_review_identity_c11_r2.md` (this file)
- `fable_review_identity_c11_r2_findings.csv`
