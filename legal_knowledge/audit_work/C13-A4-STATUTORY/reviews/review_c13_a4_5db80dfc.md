# Independent review: C13 A4 statutory (`claude/c13-a4-statutory` @ `5db80dfc`)

Reviewer: independent agent. The reviewer did not author this work. The review was read-only, with no commits and no HF writes, and was done in a `git clone --shared` copy at `scratchpad/c13/reviews/a4/src`.
Date: 2026-11-25.

## Verdict: ACCEPT WITH CONDITIONS

The evidence work is accepted as proposals: the 21 page readings, the 10 promotions, the acquisition requests and the adviser packet. The version records are acceptable as data.
The **date resolver is not accepted for use**. It fails the claimed property ("return every version a date cannot exclude; never assume the latest") at pre-commencement and retrospective boundaries (R-01 P1, R-02 P2). It is also uninformatively over-inclusive for the 1992 omissions (R-03 P2).

**Conditions.** Before any downstream use of `candidates_at`:
- fix R-01 to R-03;
- add the boundary tests (R-04);
- get a focused re-review of the resolver.

The promotions still need legal-adviser sign-off before they are applied.

## 1. Reproduction

I downloaded my own copies of all 48 HF preservation files at `5524c3d9`, and 48/48 sha256 values matched. I then ran every tool against them.

| Check | Result |
| --- | --- |
| `build_evidence_c13.py --check` | OK, 5 outputs |
| `build_versions_c13.py --check` | OK, 4 outputs |
| `build_packets_c13.py --check` | OK, 3 outputs |
| `validate_versions_c13.py` | OK, 488 records |
| `render_pages_c13.py --verify` | 21/21 |
| `sha256sums_c13.py --check` | OK, 22 files |
| pytest | 24 passed; the C12 research-isolation test also passes |

- **Frozen records:** `records_658` `9a8f0d19…` and `cases_53` `8b8d53cd…` are unchanged.
- **Branch scope:** the branch is purely additive over staging `a4c0c382`. It touches only `C13-A4-STATUTORY/` and two test files, so the C12F outputs are unchanged.
- **Evidence matrix:** the only change is 10 items moving PARTIAL to EXACT. All 99 C12F EXACT items are retained, and MISSING stays at 289.
- **Minor:** the commit message says 490 records, but there are 488 (R-05).

## 2. Page readings: 21 of 21 confirmed

I rendered each page independently with PyMuPDF from the verified HF copies:
- 1954 Gazette, sha256 `c5ef95a9…`, PDF pp.17-26 and 33-40;
- S.R.O. 17(E)/1993, sha256 `e9bf2114…`, PDF pp.15-17.

My 110 dpi render hashes are identical to all 21 recorded `render_png_sha256` values. I read every page at 150 dpi (1954) or 120 dpi (1993).

On each page, every listed rule heading, or amending item, and every printed page number is where the row says it is. Continuations are correct: r.44, 46, 52, 56, 58, 62, 97, 104, 107, 110 and 123 in 1954, and r.58 in 1993 at pp.15-16.

The two image-over-text-layer corrections are confirmed:
- 1993 item 11 reads "rule 52 (2)" (checked at 300 dpi);
- 1993 item 24 reads "118".

One unrecorded scan artefact is on 1993 p.16, item 22 (R-10).

## 3. The 10 promotions: all 10 upheld at citation level

| Proposal | Item (record) | Verdict |
| --- | --- | --- |
| EP001 | 0232 (CM-005) rr.106-109 | UPHELD, locator only |
| EP002 | 0259 (CM-018) rr.96-101 | UPHELD, locator only; r.95 correctly stays PARTIAL |
| EP003 | 0268 (CM-023) rr.51-55 | UPHELD, record level correct |
| EP004 | 0269 (CM-024) rr.56-64 | UPHELD, locator only; r.58 1993 pp.15-16 both cited |
| EP005 | 0279 (CM-029) rr.110-127 | UPHELD, record level correct |
| EP006 | 0280 (CM-029) rr.115-118 | UPHELD, record level correct |
| EP007 | 0317 (CM-SC-08) rr.52, 54, 115-116 | UPHELD, record level correct |
| EP008 | 0337 (CM-CL-04) rr.106-133 | UPHELD, locator only |
| EP009 | 0340 (CM-CL-06) rr.41-55 | UPHELD, locator only |
| EP010 | 0341 (CM-CL-07) rr.52, 54, 115-116 | UPHELD, record level correct |

I checked each of the C12 failure modes:

- **Open alleged amendment.** None was found. The `open_items` and `conflicts` are empty for all these rules, and WS-A `open_questions`/`gaps` registers have no hits for rr.41-64 or 96-133.
- **Missing commencement.** S.R.O. 17(E)/1993 r.1(2), "come into force on the date of their publication", is confirmed on the image at printed p.12. The silent 1954 principal stays under AQ-05 in the conditions.
- **Start-page-only anchors.** All 97 rule-page ranges in the proposals match my independent reads.
- **Record-level propagation.** Only records whose every citation item is now EXACT are given record scope. The others are `CITATION_LOCATOR_ONLY`.
- **Phantom notes.** No record cites a note.

S.R.O. 246/1982, which inserted r.59A, is modelled in the version chain. Generic chain gaps remain disclosed in the conditions.

## 4. Version model

**Sample.** I sampled 30 random records plus the 45 S.R.O. 17(E)/1993 records, the AA s.75/s.76/s.127/Chapter XVI records, IPC/CrPC/IEA/BNS, and r.15, r.16A and r.2.

**Effective dates.** All 67 stated dates trace to commencement wording in the instrument: "on publication", "with effect from", or a deemed date. Compilation dates sit only in `reported_date`. Silent instruments, including Act 37/1992, are recorded as `NOT_STATED_PENDING_ADVICE`.

There is one qualification (R-07): two AFT dates rely on a masthead whose issue identity was inferred.

**Page evidence.** The page evidence I checked in the sample is correct: r.33 and 1993 item 8 at p.15; r.54 at p.312; r.58 at pp.313-314; r.121 at p.329; r.179(5A) at 1993 p.18 (the row cites it).

**Temporal axes.** The four axes are separate slots, all `NOT_DETERMINED`, with question ids. No legal conclusions were found. `currency` is always `NOT_ESTABLISHED`.

**Resolver boundaries.** These are the problems.

- **Pre-commencement (R-01, P1).** BNS/BNSS on 2024-06-30, and even in 1990, return only BNS v01. Other examples:
  - AFT s.9A in 1950 returns s.9A v01;
  - AA s.169A in 1950 returns v01;
  - rr.59A, 13A and 15A in 1950 return v01.

  There is no "not yet in force" candidate. On the IPC side, both v01 and the repeal are returned on 2024-06-30 and 2024-07-01. That is safe, but see R-03.
- **Retrospective deemed effect (R-02, P2).** For r.16A and r.2 in 1985, v03 is omitted, even though S.R.O. 216/1988 deems it effective from 04-06-1979.
- **1992 omissions (R-03, P2).** For s.75, s.76 and s.127, v01 and the omission are both returned for every date, including 1960. The 1992 Act's date is never used as an exclusion floor.
- **Working cases.**
  - r.22, r.52 and r.58 are correct at 1993-12-05 (v01) and from 1993-12-06 (v02).
  - r.15 in 2000 returns v01 and v02, matching the README.

## 5. Restricted material

`regs-regulations-for-the-air-force-reprinted-edition-2000` and `4284820e…` occur only in the guard denylist in `tools/c13a4_common.py`. They are absent from all records, inputs, outputs, the schema, the README and the tests.

## 6. Adviser packet

The packet has 96 entries, matching the claim. Every `exact_question` is phrased as a question. Words such as "governs" or "applies" appear only inside questions or competing readings. No conclusions are drawn, and the C13 promotions are marked NOT_YET_REVIEWED.

Gaps (R-06):
- ADV-077 omits the date-of-assent reading for Act 37/1992.
- The "conflict stay reserved" boilerplate is used on entries that are not conflicts.

The acquisition requests number 45. All are `REQUESTED_FOR_A7_NOT_EXECUTED`, and the only host is archive.org. The word "aftjabalpur" appears only in the constraint text "never aftjabalpur.in".

Findings: `review_c13_a4_5db80dfc_findings.csv`. That file has 13 rows: 1 P1, 2 P2, 5 P3 and 5 INFO.
