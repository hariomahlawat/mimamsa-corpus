# CALIBRATION-02: Reviewer B (Judicial verification)

**DATABASE ONLY. This is an evidence review, not legal approval.** No row here is legal-advisor or JAG validation. Curated originals were not edited. Reserved states are unchanged, and the 13 WS-B inconsistencies (OI-01 to OI-13) stay OPEN. Rows cite OI-01, OI-10, OI-11, OI-12 and OI-13 where relevant.

- Worktree `/home/user/c4-b`, branch `claude/c4-rev-b`, base `67c6e0c1`.
- Written without reading the outputs of Reviewers A, C or D.

## Method

1. **Coverage.** I read all 382 propositions in `propositions.csv`, which come from 46 records. Each proposition was classified as one of:
   - a design, heading or checklist statement;
   - a statutory or procedural statement with no judicial dependence;
   - a proposition that cites, or should cite, case law.
2. **Case identity.** I resolved every case reference against the WS-B registers: `identity_resolution*.csv`, `holdings_register*.csv`, `subsequent_treatment*.csv`, `authoritative_copy_status_cycle3.csv`, `pending_acquisition_cycle3.csv` and `open_inconsistencies_cycle3.csv`. I also used the WS-D source-code resolution (`V7-S12`, `V7-S13`, `V8-S07`, `V8-S08`, `SC_GILL`, `SC_VK`, `SRC-VIR`).
3. **Reading held texts.** I read each relied-on passage in held text only. No downloads, and no network access.
   - Official PDFs: text layer extracted with pymupdf, for example P S Gill paras 14-22 in full, PPS Bedi pp.34-35, Arjun p.27 and p.70, and Isaac para 39.
   - Text files already held in the scratchpad: Parashotam, Virendra and Isaac.
   - Intern mirrors via `git show origin/raw-data:data/text/...`: Kuldeep Yadav, Som Datt Datta, Santosh Lohar, Pandappa Kotagi and Harjeet Singh Sandhu.
   - I did not re-render page images. Where WS-B had already checked a page image, the row says so.
4. **Holding versus other material.** Each relied-on passage is classified as holding/ratio, operative direction, court observation, obiter, a party's argument as summarised by the court, or the court's summary of earlier precedent. SCR headnotes ("HELD: ...") are treated as editorial and never quoted as the court's words; this matters for Kuldeep and Harjeet.
5. **Meaning of the evidence states as B uses them:**
   - `VERIFIED_AGAINST_HELD_PRIMARY_SOURCE`: the relevant passage was read in an official court copy, with its sha256 and a page or paragraph locator. This can include propositions whose record does not cite the case; the row then carries an OMISSION defect.
   - `SUPPORTED_BY_SECONDARY_SOURCE_ONLY`: the passage was read only in an intern or SCR mirror. A mirror is never an official copy.
   - `NOT_YET_REVIEWED`, used for statutory or procedural statements: B finds no judicial dependence. B did **not** assess the statutory or procedural accuracy, which belongs to Reviewers A and C. It is not a judicial gap.
   - `NOT_A_LEGAL_PROPOSITION`: design, application, heading or checklist text.

## Judgments relied on (sha256 = identity; authenticity class)

| Judgment | Class | sha256 |
|---|---|---|
| Lt Col Prithi Pal Singh Bedi v UoI, SC 25 Aug 1982 (JUDIS 9884) | OFFICIAL_COURT_COPY | 211dbaf4e20371cc476d09c158e41b976786d57f67336ff6fc802170178b3cca |
| Union of India v P.S. Gill, SC Crl.A. 404/2013, 27 Nov 2019 | OFFICIAL_COURT_COPY | 7c32b8e87984c9f3dd52218f9030dffad3ea5aedc98d256744fd5e97d044a0ac |
| Union of India v Ex Sep Virendra Kumar, SC CA 9267/2019, 7 Jan 2020 (two versions, OI-01) | OFFICIAL_COURT_COPY | 0ff9d2fc8ef36dfebe862739e517b5ec51f4fff9b4f9b3f7b86beece5d85e819 |
| Union of India v Parashotam Dass, SC CA 447/2023, 21 Mar 2023 | OFFICIAL_COURT_COPY | fe19875b19ed5a4efa257273cd2fb1f1cbb57c4f383117cc40e9a90046568377 |
| Union of India v Col N.C. Isaac (Retd), 2026 INSC 993, 15 Sep 2026 | OFFICIAL_COURT_COPY | 3f49a31464fec174cdbff5d9e194fa888ca00529b6246eacdc8ac2368eab4653 |
| Dharamvir Singh v UoI, SC CA 4949/2013, 2 Jul 2013 (JUDIS 40493) | OFFICIAL_COURT_COPY | 3056712cc7614399f72ee19f529f91990e70dba8a317dd3bd07e76e4ac546b75 |
| Anvar P.V. v P.K. Basheer (JUDIS 41931) | OFFICIAL_COURT_COPY | 06f77a701073bc32f91ab4a67331cb4747f61214a6f3d2e6408196355dac449b |
| Arjun Panditrao Khotkar v Kailash Gorantyal, SC 2020 | OFFICIAL_COURT_COPY (as held) | 9c3d7880471fe22f5be2a501bbff40d5b93e32670a37903e04af4dcd92b4aebc |
| State of Sikkim v Jasbir Singh, SC Crl.A. 85/2022 | OFFICIAL_COURT_COPY | c23ce0e334252849ccf1d85949fc482e33071d4a04db5ae3e83c60c16a05faa2 |
| Union of India v Lt Col Kuldeep Yadav, SC CA 7603/2019 | INTERN_MIRROR_SCR (not official) | b35f7f9e73f850351ed2779f17c3f0b68044a472f3a0a14fc0e68a865e36422a |
| Som Datt Datta v UoI, SC 20 Sep 1968 | INTERN_MIRROR_SCR (not official) | c6dd21359a7e3cbd4da711d87f80536f004cf206d7970cfb5eed0fbd5d427c83 |
| Union of India v Harjeet Singh Sandhu, SC 11 Apr 2001 | INTERN_MIRROR_SCR (not official) | fc15feb56e7eaba8df31dbaf2bb8150e075516e03f595ce55339c986582737ee |
| Nk Santosh Lohar v UoI, P&H HC CWP 3118/2023 | INTERN_MIRROR, text largely garbled (OI-10) | bdcc30e45cea292770eadf30ebe4034ab0bb6fbd5baf7b102b0a97ae73ab2122 |
| Lt Col Pandappa Kotagi v UoI, Delhi HC WP(C) 5992/2026 | INTERN_MIRROR ("Signature Not Verified") | 5cc204202cdb8273c19bad4e05c62ff23ec0078bb90179eb39783a32194a0fce |
| Union of India v Maj Gen Shri Kant Sharma, SC 11 Mar 2015 | INTERN_MIRROR_SCR (identity only) | 86de3643e66ec27b0e6a2a8ee007935a161790b0054ff924506d4c81b495289d |

**Not held, so not verified:**
- Lt Col Pooja Pal v UoI (2026): identity unresolved, PQ-C3-54.
- Sodhi, Hussain and Inder Jit Kumar: citations corroborated only through Virendra's footnotes.
- L. Chandra Kumar.
- Official copies of Kuldeep, Som Datt, Harjeet and Santosh Lohar.

Ranjit Thakur's treatment of PPS Bedi is taken from WSB-T3-001 (official copy ed7cf31f..., page image p.6); B did not re-read it.

## Key judicial relationships (as far as held material allows)

- **Isaac (2026) and Dharamvir (2013).** Isaac qualifies Dharamvir for the later regime and does not overrule it.
  - Operative directions: para 39(ii) (due weight to the Medical Board, with detailed Tribunal scrutiny in pending matters) and para 39(iii) (for a claim brought after 15 years, the ER 2008 Rule 7 principle applies and the onus shifts).
  - Para 34 is expressly qualified: the court did not decide that ER 2008 has legal force.
  - Para 19.4 is the respondents' argument. Para 28 is obiter.
  - The held official text does not mention ER 2023.
- **Parashotam Dass (2023).** It held that Shri Kant Sharma (2015) "does not lay down the correct law". There is no per se restriction on Art.226 review of AFT orders (paras 29-32).
- **Navjot Sandhu (2005).** It was overruled in part, only on the ss.63/65 route for secondary electronic evidence (Anvar; Arjun para 59; OI-11). No calibration record cites Navjot, but CM-026 omits the s.65B(4) line.
- **P S Gill (2019).** It decides s.14 and s.15 jurisdiction only. It does not decide s.123 or s.122, although s.123 was invoked on its facts. SC13 risks mislinking it.

## Counts (387 rows; 382 propositions, each covered; 5 extra rows for distinct issues)

**By evidence state**

| State | Rows |
|---|---|
| NOT_A_LEGAL_PROPOSITION | 206 |
| NOT_YET_REVIEWED (statutory/procedural; no judicial dependence) | 126 |
| VERIFIED_AGAINST_HELD_PRIMARY_SOURCE | 35 |
| SUPPORTED_BY_SECONDARY_SOURCE_ONLY | 8 |
| SOURCE_NOT_HELD | 5 |
| UNSUPPORTED | 4 |
| HISTORICAL_VERSION_UNRESOLVED | 1 |
| INTERPRETATION_REQUIRES_LEGAL_ADVICE | 1 |
| CONTRADICTORY_EVIDENCE | 1 |

**By severity**

| Severity | Rows |
|---|---|
| P1 | 0 |
| P2 | 15 |
| P3 | 35 |
| NONE | 337 |

## Limitations

- I did not re-render or check any page images. Locators for official copies are text-layer PDF pages and paragraphs. JUDIS copies of PPS Bedi and Navjot are unnumbered, so their locators are PDF and SCR pages.
- Subsequent-treatment searches are **not exhaustive**. Absence of a treatment row is not proof that no treatment exists. B ran no new treatment search of the intern corpus beyond reading the WS-B registers.
- I could not establish the reasoning in Santosh Lohar: the mirror is font-garbled, and its legible passages appear to be quotations.
- Pooja Pal (2026) cannot be identified from held material.
- Mirror-only holdings (Kuldeep, Som Datt, Harjeet, Pandappa) are not official, and OI-13 applies.
- No P1 was assigned. No proposition was found materially wrong in a way that would, on its own, cause unlawful action. The most serious items are omissions and mislinks (P2) that could lead to flawed reliance.
- `NOT_YET_REVIEWED` rows carry no judicial finding. They are not statutory clearance.
