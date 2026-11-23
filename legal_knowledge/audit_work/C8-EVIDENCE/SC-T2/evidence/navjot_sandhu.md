# State (NCT of Delhi) v Navjot Sandhu (copy C5-SRC-J-SC-2005-NAVJOT~C1)

Reader: AI agent (Claude Opus 5.5 subagent), not human-confirmed. Checked 2026-11-23. Renders: 150 dpi, grayscale, PyMuPDF, full page; PNG hashes in `../page_checks_sc_c8.csv`. Held file re-hashed before use: MATCH. Evidence only; no approval, no statement of legal status.

**Copy:** sha256 `3b75354869ffb928f73532f475f5f920e2f2a1f8817163caba2f7fb5e1eb215d`, 464,857 bytes, 107 pages, at `downloads/independent-reviewer-B/navjot_sandhu_2005.pdf` and `downloads/orchestrator/navjot_2005.pdf` (same bytes).
- Recorded locator: `https://api.sci.gov.in/jonew/judis/27092.pdf` (held_copies.csv#NAVJOT).
- First-class record: PILOT-01/sources/independent-reviewer-B.json#S-REVB-012, verification_state **SOURCE_LOCATED**.
- Producer GNU Ghostscript 7.05.

## What the pages show
| Item | Reading | Source |
| --- | --- | --- |
| Case numbers | Appeal (crl.) 373-375 of 2004; with Criminal Appeal Nos. 376-378, 379-380 and 381 of 2004 | C8-SCPIC-08 p.1 |
| Parties | STATE (N.C.T. OF DELHI) v NAVJOT SANDHU@ AFSAN GURU (connected: Syed Abdul Rehman Gilani; Shaukat Hussain Guru; Mohd. Afzal) | p.1 |
| **Judgment date** | **"DATE OF JUDGMENT: 04/08/2005"** (printed database field) | p.1 |
| Bench / author | P. VENKATARAMA REDDI & P.P. NAOLEKAR; opinion by P. VENKATARAMA REDDI, J. | p.1 |
| Citations printed | none (no CITATION block) | p.1 |
| Pagination | "Page 1 of 107" to "Page 107 of 107" complete | text layer |
| Last page | No signature, names or date. Ends with para "22. IN THE RESULT ..." and "... are hereby dismissed." | C8-SCPIC-09 p.107 |
| Extraneous material | Database field labels on p.1. No CITATION, CITATOR or HEADNOTE label anywhere in the text layer. "\005" artefact appears 90 times | text layer |

## Comparison with corpus identity
- **Discrepancy (known issue):**
  - The C6-01 identity reads only "SC 2005".
  - cases_53 `DCLR-SC-2005-L01` has an empty `decision_date` and an empty `case_number` (approx_year 2005).
  - The document prints 04/08/2005 and Appeal (crl.) 373-375 of 2004.
  - S-REVB-012 records the date as 2005-08-04 and the same case numbers.
  - The record is a CITATION_LEAD with an empty holding.
- WS-B T3-046 quotes a later judgment citing "(2005) 11 SCC 919" / "2005 (2) Suppl. SCR 79". This copy does not print those citations, so they cannot be confirmed from it.
- The C6-01 limitation "headnote/citator presence not checked beyond p.1" is now answered: no such labels appear in the whole text layer. That is a text-layer search, not an image check of every page.

## Classification observations
- JUDIS rendition: URL header, "JUDIS" watermark, field labels and no signature block.
- Unlike the 1987/1990 files, it has no report pagination and no headnote.

## Identity result
**CONFIRMED** (case identity), with the date taken from the image of p.1. See `../EXACT_ANCHOR_FINDINGS.md` for why the anchor still rests on thin evidence.
