# Evidence-recovery requirements for the four partial copies (no download, no invented history)

## 1. Delhi High Court Rules, Chapter 6 (`C5-SRC-P2-DHC-RULES-CH6`, sha256 `f69e18be…`)
| Element | Established | Source of evidence |
| --- | --- | --- |
| Retrieval | URL `https://delhihighcourt.nic.in/files/2024-04/courtrulefile_nqapw0lk.pdf` with sha256 (PILOT-01 discovery T5-03, FULL). Only a register date (2026-11-22) | committed register |
| Chapter identity | "CHAPTER 6, Cases Against Government Servants, Part A General" on the image (C6-PIC-03/04) | page image |
| Issuing court | **not printed**; inferred only from the host | none on the copy |
| Volume, edition, date | **not printed**. PDF metadata (not image): Word 2007, author "DHC", created 2011-04-07. The editorial note "[See Section 475 of new Code]" shows post-1973 editing of unknown date | none |
| Amendment state | one footnote: Rule 1 substituted by correction slip No. 7, Rules XZ 20, 19-5-1965 | page image |
| Currency markers | p.5 cites Army Act ss.125, 126 and 127, although s.127 was omitted by Act 37/1992 (C5 RV-26); the chapter reproduces the 1952 Rules (PILOT-01 T5-03). Currency UNKNOWN: treat as historical text (Fable F-19) | page image and registers |

**Required to complete (any one route, each needing approval where it involves a request):**
- (a) the printed *Rules and Orders of the High Court of Delhi* volume containing Chapter 6, with title page, volume number and edition date, compared page by page with the held file; or
- (b) a court-registry statement identifying the file (URL and sha256) as the court's current text of the Chapter, with its volume and edition; or
- (c) a discovery-only (HTML listing) check that the court's own rules index page links this exact file under an identified volume. This needs a guarded listing request, not a download, and its sha256 would then be compared.

**Until then:** PROVENANCE_PARTIALLY_DOCUMENTED. No currency claim.

## 2. Act 13/1975 (`C5-SRC-P0-AA-AMD-ACT13-1975`, sha256 `8358d2b3…`)
| Element | Established | Source of evidence |
| --- | --- | --- |
| Retrieval | India Code item `eff2c36e-…` / bitstream `d4cb2142-…` with sha256 (PILOT-01 discovery T6-03). **No resolvable file URL and no retrieval date** in any retrieval record; register date only | committed register |
| Identity | image-checked (WSA-PIC-29/30): Pt II s.1, 29-03-1975, Act No.13 of 1975, p.81 | page image |
| Issue number | Hindi masthead No.16; English masthead reads No.15, recorded as uncertain (WSA-PIC-29) | page image |
| Unexplained marks | a handwritten '17'-like mark and a faint circular stamp to the right of the masthead on p.1 (Fable F-18; coordinator re-read 2026-11-23) | page image |

**Required to complete:**
- (a) a retrieval record with a full file URL, retrieval date and sha256 **for these exact bytes**. An approved re-acquisition from India Code, under its robots decision (C5-CRAWL-01 is still open), would produce a **new copy with a new sha256**, because India Code serves download-specific bytes. It could document the held bytes only through a defined equivalence test, for example the C5 RV-13 finding that two Act 37 copies differed only in a trailer ID (Fable F-18); or
- (b) an alternative copy of the same Gazette issue (for example an archive.org Gazette facsimile) whose masthead resolves No.15 or No.16, acquired under C6-02-style pinning. That would also settle the issue-number discrepancy.

**Not acceptable:** reconstructing a URL from the identifier and presenting it as retrieved, or assigning a retrieval date from the register date.

## 3. Rajya Sabha papers-laid record (`C5-SRC-P2-RS-PAPERS-LAID-1987`, sha256 `fa51a4b1…`): WITHHELD
- **Why partial:** the retrieval record (PILOT-01 S-REVA-021) itself marks authenticity UNCONFIRMED and gives an archive.org item page. The sitting date 03-03-1987 comes from the archive file name, not the printed page (Fable F-02).
- **S.O. 4010/1986 date:**
  - DISPUTED: the RS page reads "6th December, 1986" (C5-PIC-02; the PILOT-01 and Fable readings agree), but the Cycle 5 reviewer read 08-12-1986 (RV-01).
  - The disagreement is OPEN in C5 D7.
  - The notification's authoritative date is NOT_VERIFIED, and so is its date semantics (signing date or Gazette date).
- **Required:**
  - (a) the RS Debates file from rsdebate.nic.in, with an affirmative authenticity record and the printed sitting date;
  - (b) separately, the Gazette of S.O. 4010/1986 itself, which is the only evidence that settles the date.

## 4. Rajbir Singh copy C2 (`C5-SRC-J-SC-2015-RAJBIR~C2`, sha256 `c6ec489d…`)
- **Why partial:** its only locator is a mention inside copy C1's retrieval record. It is not a duplicate of C1: 163,859 bytes and 21 pages against 230,938 and 20. Pages 20–21 are a Record of Proceedings. Its embedded signature range does not cover the file (Fable F-01).
- **Required:**
  - its own retrieval record (URL, date, sha256 of these bytes);
  - a page-level comparison with the JUDIS copy (C1).

  Until then it is not an anchor copy. The Rajbir case is anchored by C1 alone in the simulation.
