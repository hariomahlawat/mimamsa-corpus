# Independent review: C8-EVIDENCE at 5212a95b (Gazette tranche 1, Supreme Court tranche 2)

RESEARCH ONLY. This review inspects evidence; it approves nothing and signs off for nobody. Page readings below are mine, an AI agent's, and are not human-confirmed. A matching hash shows bit integrity, not authenticity or legal correctness.

## Result

The identity, signature and anchor claims hold against the held documents. Three P2 defects need correction before an owner uses the packages: a false statement about a pinned register (B-01), templates that drop the decisive limitations (B-02), and committed page-text dumps with personal data (B-03). No P1 finding.

## What was checked

| Task | Result |
| --- | --- |
| Render hashes | All 39 Gazette and all 28 Supreme Court renders reproduced with PyMuPDF 2.1 / MuPDF 1.28.6, 150 dpi gray, full page: 67 of 67 identical. Every held file re-hashed MATCH. |
| Gazette readings | Read from my own renders: T1-02 (pp.13, 14), T1-11 (141, 142), T1-14 (347, 367), T1-16 (725, 736), T1-17 (213, 214, 217), T1-18 (613, 614), T1-19 (1, 2), T1-20 (1, 2). S.R.O. number, date line, issue number and date, Part II-Section 4 and signatory agree with the recorded readings in every case. The three PARTIAL headers are as described. |
| S.R.O. 34 notes | Also read the NOTE lists on T1-08 p.413, T1-09 p.60, T1-10 p.97, T1-13 p.197, T1-15 p.617, T1-17 p.214: each lists S.R.O. 34 with a 5 June 1963 date. |
| S.R.O. 34/1963 | The held page 14 is 'New Delhi, the 5th January 1963 / S.R.O. 34', a declaration under r.188(e) in supersession of six earlier notifications, signed S. DEVANATH, Dy. Secy. No document in the package identifies it with the '5-6-1963' listing or infers a chain; C8-CR-02 stays UNRESOLVED. The 2018 note's '05th January, 1963' and the '05th June, 1955' date for S.R.O. 240 (C8-CR-01) are as printed. |
| CMS, S.R.O. 2(E)/2018 | One ByteRange [0 260473 1699735 7652] ending at file length; hole is exactly the /Contents hex string; messageDigest equals SHA-256 of signed bytes (7785d388...); RSA PKCS#1 v1.5 over signedAttrs verifies with the embedded RAKESH SUKUL certificate (serial 5352d5f2 = sid); openssl rc 0. Described throughout as integrity only; I found no wording calling T1-19 authenticated. |
| CMS, S.R.O. 17(E)/2019 | One ByteRange [0 324995 332029 7495] ending at file length; messageDigest matches (739566ad...); the RSA value does not decode to a PKCS#1 block with the only embedded certificate (serial 5391176f = sid); openssl rc 4, invalid padding. I also tried the byte-reversed signature, PSS, SHA-1/SHA-512 and signing over content: none verifies. The failure is characterised accurately and the cause is rightly left UNCERTAIN. |
| Supreme Court pages | Read Navjot p.1, Mullikote pp.1 and 32, Rajbir C1 p.20, Ranjit p.1 (JUDIS); text layer for the rest. Navjot date 04/08/2005 and Appeal (crl.) 373-375 of 2004; S N Mukherjee Civil Appeal No. 417 of 1984 on p.3; Girish 2026 INSC 149; 'NARSINGH YADAV'; all as recorded. cases_53 gaps (Navjot date and number, Mukherjee number, Girish citation, no Narsingh Yadav record) confirmed against the immutable file (sha256 8b8d53cd...). |
| JUDIS facts | Ghostscript 7.05, PDF 1.2, no images, no signature, header on every page, HEADNOTE in the 1987 and 1990 files, inline report pages 513-525 and 45-76 without gap, '\\005' x90 and '3.?.1986' all confirmed. P-D3 is set out and not decided. |
| Mullikote | Two versions confirmed: pp.32-62 lack CORRECTED, the neutral citation and the signature appearance; service number 256812 M against 2568912 M; 'Balakrishanan'; renumbering (see B-07). |
| Rajbir | C1 20 pp. (no signature), C2 21 pp. (judgment pp.1-18 plus ROP), C3 15 pp. enscript rendition of C2: mapping confirmed. The claim that C2 lacks a copy_structure row is wrong (B-01). |
| Anchors | My own harness on an extracted copy of the commit, synthetic approval in a temp dir: 6 at version 0 (byte-identical to the frozen C5 registers), 13 with all 8, 10 without the JUDIS three, 11 without Navjot and Mullikote, 9 without both groups. Changed rows are exactly DCLR-SC-1987-R01, 1990-N02, 2005-L01, 2013-N08, 2015-N09, 2026-007, 2026-N16; no KB row changes. Their script regenerates exact_anchor_simulation.json byte-identically. |
| Packages | No owner decision, no D-/R- record, ledger still version 0, decisions/ holds only README. A template placed as a decision record is rejected by the ledger in four variants. `build_packages.py --check` passes. Recommendations follow the evidence (T1-20 NEEDS_FURTHER_EVIDENCE, T1-19 HOLD, Navjot and Mullikote keep PARTIAL), subject to B-02. Leads draw no good-law conclusion. AI-reader caveat is present in every document. No absolute path or binary in the commit; see B-03 for page text. |
| Contradiction register | All 20 earlier rows present with identical status and content, restructured (B-09). New entries C8-CR-01 to 13 are supported by the pages I read, except the quoting in B-06. |

## Not checked

- Gazette rows T1-01, 03-07, 12 beyond render-hash reproduction; I read only the S.R.O. 34 note lines on 08, 09, 10, 13, 15.
- Supreme Court pages other than the five read as images; Hindi text only loosely.
- Certificate chain, trust anchor, revocation, signing time: not validated by anyone. No comparison with an egazette.gov.in or court-served copy; no network was used.
- The canonical private Hugging Face snapshot was not consulted; coverage against it is unknown.
- Rule-1 results for the Gazette rows were not recomputed.

## Findings

| id | sev | title |
| --- | --- | --- |
| B-01 | P2 | False statement that Rajbir C2 has no AUTH-LEDGER copy_structure row |
| B-02 | P2 | Unsigned templates omit the decisive limitations from the text 'to be recorded verbatim in the entry' |
| B-03 | P2 | Full page text-layer dumps of 28 judgment pages are committed, including personal data |
| B-04 | P3 | T1-20 visible signature appearance exists on PDF p.6 and was not recorded; other instruments in the file not noted |
| B-05 | P3 | Dangling and stale references to preparation-time paths |
| B-06 | P3 | Quoted note strings in C8-CR-02 are not exact for four instruments |
| B-07 | P3 | Mullikote second-version paragraph numbering described inexactly |
| B-08 | P3 | Truncated text in the Supreme Court approval package |
| B-09 | P3 | Carry-forward is content-equivalent, not unchanged |
| B-10 | P3 | Unsourced status wording inside lead and register cells |
| B-11 | P3 | Hindi/English footnote difference in S.R.O. 17(E)/2019 is read but not registered |
| B-12 | INFO | Glyph-level reading variances (low confidence) |
| B-13 | INFO | What matched |

Detail, evidence, reproduction and required correction for each are in `fable_review_c8_evidence_5212a95b_findings.csv`.

## Conditions for acceptance

1. Correct the Rajbir C2 copy_structure statements and withdraw the related correction proposal (B-01).
2. Carry the decisive limitations into the templates and rebuild (B-02).
3. Remove page text from the committed render logs (B-03).
4. Fix B-04 to B-11 in the same revision; they are small.

## False-pass limitations

Agreement between my readings and the preparers' is agreement between two AI readers using the same renderer on the same bytes. It does not show the archive.org or court-host files are what the Government or the Court issued, and it says nothing about currency or applicability of any instrument or judgment.

VERDICT: ACCEPT WITH CONDITIONS

Reviewer model: Fable 5.2 (claude-fable-5-2)
