# C6-01 provenance package: final independent review

- **Reviewed commit:** `e7a10e27bde9cc6889740350b21f59cdd7c906c1` (`git rev-parse HEAD` in /home/user/c6).
- **Baseline:** `04665eb17d2a1e4c8626d38346f17fa76b417548`.
- **Reviewer:** independent and read-only. I did not produce this package.
- **Constraints kept:**
  - no network access;
  - Python ran with PYTHONDONTWRITEBYTECODE=1 / `-B`;
  - all outputs are under this folder only;
  - `git status --short` was empty at the end.
- **Not relied on:** the earlier `review/` reports.
- **Scope of judgement:** I make no legal determination. A byte or provenance match does not establish that an instrument is current or applicable.

## VERDICT: ACCEPT WITH CONDITIONS

**No P1 was found:**
- no wrong promotion;
- no data-integrity break;
- every evidence reference holds;
- every held hash matches.

**Two P2 documentation and incorporation-path defects must be fixed before incorporation:**
- **R-01:** D3 and D6 report stale counts and a stale TRA status.
- **R-02:** a real incorporation also needs a Cycle 5 holding-state relabel, which the D4 simulation switches off.

**The TRA 2026 class stays an owner decision (R-04).**

## Method and results per check

### 1. Scope and denominators
**Method:** I counted directly from the C5 master and copy registers (holding_state in the two `*_PROVENANCE_UNDOCUMENTED` official states) and from `provenance_recovery_register.csv`.

**Counts:**
- 34 sources and 36 copies: 26 publication/record sources with 26 copies, and 8 SC sources with 10 copies.
- Publication types: 21 GAZETTE_NOTIFICATION, 10 JUDICIAL, 2 STATUTE, 1 PARLIAMENTARY_RECORD, 1 SUBORDINATE_LEGISLATION, 1 REGULATION.
- C5 has 67 unique copies and 54 copies with NO_REGISTER_ROW.

**Agreement:** README, summary JSON, D1, D2, D4, D5 and the tests agree (34 DOCUMENTED / 2 PARTIAL; 34 proposals = 21 Gazette + 9 court primary + 4 non-primary).

**Disagreement:** D3 and D6 still say 33/3, 33 proposals, 3 non-primary and "TRA partial". D2's non-primary list omits TRA. See **R-01 (P2)**.

### 2. FULL-only rule
**Code:** `classify()` returns DOCUMENTED only when `strength == "FULL" and identity_ok`, with a contradiction checked first. `identity_ok = I or t_ok`, and `t_ok` requires `publication_type == JUDICIAL`.

**How `strength` is set:** it is FULL only if one of these holds:
- L1 or L3 is present;
- L4 is present and its detail starts with `http`;
- L2 is present and its detail contains "size/md5/sha1 OK", or contains "sha1" but not "no sha1".

The MD5+size fallback always writes "(no sha1 in snapshot)", so it cannot become FULL. The ACQ-02 supplement row needs all three booleans true.

**Tests:** `classify()` was probed through the tests and by hand. MD5_SIZE, IDENTIFIER_SHA, MD5 and NONE never yield DOCUMENTED. A partial check (Ip) does not set I.

**Docs:** the docstring, METHOD and comments match the code.

**Looser routes:** I found three routes that are looser than they look. Each was checked by hand and is correct for the current rows:
- the L3 "locator-embedded sha256" route (Rajbir C2 only);
- L3 taking the first URL in a locator (the RS record gives an item page, not the file);
- L4 taking the first URL in a multi-candidate field (Delhi HC).

See **R-05 (P3)**. No case was found where weaker evidence becomes FULL by accident.

### 3. Proposal-ID stability
- **Uniqueness:** the IDs are `C6-01-AP-<sha256[:8]>`, unique across the 34 proposals and also across all 67 C5 copies. None overlaps the C4 register.
- **Duplicate rejection:** monkeypatching a 1-hex prefix makes `outputs()` raise `SystemExit("duplicate proposal_id ...")`.
- **Legacy map:** I parsed `git show 9b4ad44d:` (34 rows) and `git show d58894c4:` (33 rows) of the proposals CSV. Every legacy ID in `review/legacy_proposal_id_map.csv` maps to the right sha (0 mismatches), and all old IDs are covered. AP-22@9b4ad44d is Act 13/1975, with no current proposal. TRA is new.
- **Test gaps:** see **R-10 (P3)**.

### 4. Evidence references (all 34 proposals)
**Method:** a script resolved every `provenance_references` entry to its row and compared it with the copy's sha256 and with `held_copy_facts` md5, sha1 and bytes:
- PILOT-01 code register;
- ACQ-02 supplement;
- ACQ-01/02 metadata snapshots;
- source_discovery;
- R23 amendment_search;
- PILOT-01 and R23 `sources/*.json`;
- WS-B held_copies.

**Hashes:**
- I re-hashed every held path of every proposal (sha256, md5, sha1, bytes): 0 mismatches.
- I recomputed `held_copy_facts.csv` for all 36 copies (md5, sha1, bytes, pages, p.1 text excerpt) with pymupdf: 0 differences.

**Results:**
- **L1:** official_sha256 equals the copy for all 7 L1 rows.
- **L2:**
  - 15 ACQ-02 snapshot matches on md5, sha1 and size;
  - 7 ACQ-01 matches on md5 and size (no sha1), each paired with an R23 reviewer-D retrieval record (L3) whose sha256 equals the copy;
  - the AR-035 match is a derivative file, as stated.
- **L3:** the record's sha256 equals the copy in every case except the one marked "(locator)" (Rajbir C2). For that row the locator explicitly pairs the rop URL with sha c6ec489d.
- **L4:** ER 2023 (T3-01: URL, 13,011,188 bytes, sha) and Delhi HC (T5-03) match.
- **L5:** md5_ok=YES and the sha matches.
- **Contradictions:** a grep of every committed CSV, JSON and MD file outside C6-01 for each proposal's locator found no line pairing it with another sha. The one hit is the S-BLIND-013 locator that names the sibling rop copy, which is not a contradiction.

### 5. Class and source-copy consistency
- **Gazettes:** all 21 have master and copy carrier THIRD_PARTY_ARCHIVAL_FACSIMILE, mapped to PRIMARY_GAZETTE_ARCHIVAL_FACSIMILE.
- **Court copies:** the 9 primary court copies have carrier ISSUING_AUTHORITY and an api.sci.gov.in locator. The Rajbir bosir copy has carrier UNKNOWN and is mapped to NON_PRIMARY_OFFICIAL_COURT_RENDITION.
- **Held paths:** `held_paths` equals the set in CALIBRATION-02 `held_sources_scratchpad.csv` for every proposal (also tested).
- **Identity and issuer:** document_identity and issuer equal the C5 master title and authority.
- **Presentation differences:** see **R-09 (P3)**.

### 6. Unresolved and newly checked copies

**(a) TRA 2026 (be619533)**

*Renders:*
- I rendered pp.1 and 15 at 110 dpi. The PNG sha256 equal the committed C6-PIC-01/02 values (0504c954…, 08d59428…). I also viewed 160-dpi renders.
- p.1 shows CG-DL-E-13082026-275447, EXTRAORDINARY Part II s.1, No.31 of 13-08-2026, M/o Law and Justice (Legislative Dept), "THE TRIBUNALS REFORMS ACT, 2026 No. 17 OF 2026 [13th August, 2026.]" and an IndiaCode watermark.
- p.15 shows s.14 (Income-tax Act 2025 s.361), Dr Rajiv Mani, the GoI Press "UPLOADED BY … " line, MGIPMRND-508GI(S4)-13-08-2026 and a digital-signature stamp (Gorakha Nath Yadava, 2026.08.13 23:12:51). Printed p.15 of 15.
- The readings in C6-PIC-01/02 are accurate and agree with the C5 master title.

*DOCUMENTED is justified under the package's own rule:*
- FULL L3: S-REVA-016 has the India Code bitstream URL, sha256 equal to the held file and retrieved_on 2026-11-22;
- I: CONFIRMED page images;
- no contradiction.

*Class question.* I set out the arguments and do not decide them.

For **NON_PRIMARY_OFFICIAL_PUBLICATION_COPY** (as proposed):
- the copy is born-digital: vector text and embedded fonts on every page, producer iTextSharp. It is not a scan, and the only C4 India Code class is named and was given for a scan;
- the authoritative carrier of an e-Gazette is the signed egazette file;
- the embedded signature's ByteRange `[0 577400 600412 8230]` ends at byte 608,642 of a 637,026-byte file with a single `%%EOF`. So the signature cannot cover the held bytes as a whole, which is consistent with a rewrite after signing (watermarking). This is a structural observation; I did no cryptographic check;
- the class is conservative and has no coverage effect.

For **PRIMARY_GAZETTE_GOVERNMENT_HOSTED_SCAN**:
- Cycle 4 gave this class to the India Code copy of Act 37/1992 (f11d443e), and expressly noted "India Code watermarks served PDFs, so bytes are host-specific". The watermark argument in the C6 rationale therefore does not separate the two cases;
- both copies are page-faithful Gazette renditions served by the same official Government host;
- the retrieval record itself calls the TRA file a "Gazette scan".

*Rationale gap:* the C6 rationale should name born-digital/signature as the real distinguishing factor and mention the C4 watermark precedent (**R-04 P3**).

*Impact if the owner chooses primary:* documented-primary copies and sources become 43 and 42. Cases (13/0/40) and KB (42/652/366) do not change (my in-memory simulation).

**(b) Delhi HC Rules Ch.6 (f69e18be)**
- I rendered all 5 pages. The p.1 and p.5 render hashes equal C6-PIC-03/04.
- No court name, volume, edition or date is printed on any page; a text search of all pages also found none. The only volume mention is "Under Chapter VI Volume III" inside a COMMENTS paragraph.
- The PDF metadata (author DHC, Word 2007, 2011) is not printed matter. The note "[See Section 475 of new Code]" confirms later editing.
- Recording the check as PARTIAL, not counting it as I, and keeping the copy PROVENANCE_PARTIALLY_DOCUMENTED (FULL L4 locator, identity elements absent) is correct. The next step (an external record for authority and volume) is apt.

**(c) Act 13/1975 (8358d2b3)**
- It stays PROVENANCE_PARTIALLY_DOCUMENTED with strength IDENTIFIER_SHA. T6-03 gives only an India Code item ID and bitstream ID; no URL was reconstructed from them.
- retrieval_url is the identifier text. retrieval_date is "register dated 2026-11-22", not a retrieval date. No proposal exists.
- Masthead: on my render the Hindi number reads 16 and the English number reads old-style 15. The text layer says "No. 16".
- The finding is carried correctly, except that the source's "uncertain" qualifier is dropped (**R-07 P3**).
- I did not reproduce the WS-A render hashes (a different renderer or settings); this is not relied on.

### 7. Primary and non-primary classification
**21 Gazette facsimiles:** each has a recorded image-checked identity (S.R.O. number, date, Gazette part) that matches the C5 title. Each has FULL L2 (md5+sha1+size) or FULL L3. This is the same basis as the C4 rows for S.R.O. 205/1961 and S.R.O. 17(E)/1993.

**9 primary court copies:**
- Each has an api.sci.gov.in URL with an equal sha256 (L1 and/or L3).
- Its p.1 text shows the right case number, parties and date. I read every excerpt; the automated T rule is weak, see R-06.
- Four rest on L1 alone, with the C4 PPS Bedi caveat carried.
- The Rajbir rop copy rests on the locator statement, with its limitation carried.

**4 non-primary:**

| Copy | Class basis | Note |
| --- | --- | --- |
| RS papers-laid | non-primary record | R-08: its retrieval record says authenticity UNCONFIRMED |
| ER 2023 | incomplete: GMO-2023 absent | |
| Rajbir bosir | UNKNOWN carrier | |
| TRA | conservative class | see 6a |

### 8. Reproducibility
- `build_provenance.py --check` returns rc 0, and the printed summary equals the committed JSON.
- `python -m unittest tests.test_legal_audit_c6_provenance`: 16 tests OK.
- The simulated figures are what the code produces:
  - documented-primary copies 12→42 and sources 12→41;
  - cases 6/7/40 → 13/0/40;
  - KB 42/652/366 and 10/30/618 unchanged;
  - pending 1.
- The figures are the same without the TRA proposal and with only the 30 PRIMARY_* rows (verified in memory). The reason is that the C4 shared rule maps NON_PRIMARY_* classes to PROVENANCE_UNKNOWN ("row incomplete"), so non-primary proposals are inert (**R-03 P3**).
- The simulation disables the C5 holding-state consistency check. With the check on, the C5 builder stops (**R-02 P2**).

### 9. No unintended promotion
- No in-force, currency or applicability claim appears in the proposals or reports.
- Isaac (3f49a314…) is absent.
- The C6-PREP adviser pack keeps the reserved states and makes 0 determinations. Downloads are NOT_APPROVED and no correspondence was sent (tests pass).
- Every proposal says "C6-01 PROPOSAL - not incorporated".

### 10. No modification of earlier data
- `git diff --name-only 04665eb1..e7a10e27` touches only C6-01-PROVENANCE/, C6-PREP/ and tests/test_legal_audit_c6_provenance.py.
- `git diff --quiet` is clean for CALIBRATION-02, SOURCE-LIBRARY-C5 and curated_originals.
- `records_658.jsonl` = 9a8f0d19…fcc1 and `cases_53.jsonl` = 8b8d53cd…f89a, both as required.
- The C4 register still has 13 rows and is byte-unchanged.
- Untracked, git-ignored `__pycache__` folders exist under tools/ and tests/. They are timestamped 06:33:55 UTC. I could not confirm that my bytecode-suppressed runs created them. They are not part of the commit.

## Findings

| ID | Sev | Finding |
| --- | --- | --- |
| R-01 | P2 | D3/D6 (and D2's non-primary list) contradict the registers: 33/3, TRA partial "no page-image check", 33 proposals |
| R-02 | P2 | Incorporation is presented as a C4 addendum only; the D4 simulation disables the C5 holding check, which otherwise fails |
| R-03 | P3 | The C4 rule does not know NON_PRIMARY_* classes ("row incomplete"); the simulated summary counts 4 proposed-DOCUMENTED copies as undocumented |
| R-04 | P3 | The TRA non-primary rationale misses the C4 watermark precedent; the real distinguisher is born-digital / broken signature ByteRange |
| R-05 | P3 | The L3 locator-embedded route and the first-URL picks in L3/L4 are looser than documented (current rows checked by hand) |
| R-06 | P3 | The I rule accepts any rendered check row; the T rule needs only 1–2 title tokens; the Bedi precedent attribution is inexact |
| R-07 | P3 | The Act 13/1975 "No.15" English masthead drops the source's "uncertain" |
| R-08 | P3 | RS papers-laid is DOCUMENTED although its retrieval record says authenticity UNCONFIRMED and the locator is an item page |
| R-09 | P3 | Carrier and locator vocabulary differ from C4; "as reported" is stripped on the L1-only rows |
| R-10 | P3 | Tests: tautological ID-stability check; no duplicate-rejection test; C4 register checked by row count only; no report-count test |
| R-11 | P3 | The TRA proposal and C6-PIC checks had no independent verification before this review |
| R-12 | P3 | The C5 ER-2023 master cites discovery T3-02 instead of T3-01; not in the C5 carry-over list |

## Residual risks
- **Byte identity is not authority.** No signature was verified. The archive.org facsimiles are third-party carriers, and four court rows rest on register corroboration without a retrieval record (the PPS Bedi precedent).
- **India Code bytes cannot be re-checked at the host.** India Code serves watermarked, apparently download-specific bytes (WSA-PIC-29, T6-03), so the TRA and Act 13 sha256 can never be re-confirmed against the host. The retrieval record is the only link.
- **Some evidence rests on recorded readings.** The I evidence for the Gazettes rests on readings recorded in earlier cycles; I checked them for consistency, not by re-rendering all of them.
- **Real incorporation changes two registers** (C4 addendum and C5 holding states). The NON_PRIMARY class handling must be decided first.

## Conditions for acceptance
1. Fix R-01 and R-02 in D2, D3, D4 and D6.
2. The owner decides the TRA class with the R-04 arguments in front of them, and decides R-08.
3. Record this review as the verification of AP-be619533 and C6-PIC-01..04.
4. Treat the P3 items before or at incorporation.
