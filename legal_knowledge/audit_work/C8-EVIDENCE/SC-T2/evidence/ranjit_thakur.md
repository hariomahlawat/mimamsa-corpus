# Ranjit Thakur v Union of India (copy C5-SRC-J-SC-1987-RANJIT-THAKUR~C1)

Reader: AI agent (Claude Opus 5.5 subagent), not human-confirmed. Checked 2026-11-23. Renders: 150 dpi, grayscale, PyMuPDF, full page; PNG hashes in `../page_checks_sc_c8.csv`. Held file re-hashed before use: MATCH. Evidence only; no approval, no statement of legal status.

**Copy:** sha256 `ed7cf31fd8fbe50822e0a60f80b96ed1187dcd465dc4ae2649424c58001ff399`, 37,351 bytes, 9 pages, `downloads/citation-codes/ranjit_judis8566.pdf`. Recorded locator: `https://api.sci.gov.in/jonew/judis/8566.pdf` (WS-B-JUDGMENTS/tools/held_copies.csv#RANJIT). Producer GNU Ghostscript 7.05 (AUTH-LEDGER/evidence/copy_structure.csv).

## What the pages show
| Item | Reading | Source |
| --- | --- | --- |
| Court | "SUPREME COURT OF INDIA" (database header) | C8-SCPIC-01, p.1 |
| Parties | PETITIONER: RANJIT THAKUR Vs. RESPONDENT: UNION OF INDIA AND ORS. | p.1 |
| Case number | Civil Appeal No. 2630 of 1987 (from Patna HC C.W.J.C. No. 2823 of 1986) | C8-SCPIC-02 p.3; C8-SCPIC-03 p.4 |
| Date | "DATE OF JUDGMENT15/10/1987" (database field only) | p.1 |
| Bench | VENKATACHALLIAH, M.N. (J); SEN, A.P. (J); judgment delivered by VENKATACHALIAH, J. | p.1, p.4 |
| Citations printed | Database CITATION block: 1987 AIR 2386; 1988 SCR (1) 512; 1987 SCC (4) 611; JT 1987 (4) 93; 1987 SCALE (2)773 | p.1 |
| Reportable / corrected | none / none | p.1 |
| Pagination | "Page 1 of 9" to "Page 9 of 9": all present; inline report page numbers 513 to 525 run without a gap | text layer, all pages |
| Last page | No signatures, no judges' names, no date. Ends "N.P.V. Appeal allowed." and "525" | C8-SCPIC-04, p.9 |
| Extraneous material | pp.1-3: CITATION, CITATOR INFO, ACT, HEADNOTE ("HELD:" points with bracketed report pinpoints) and an editorial note: "(Note: on point 1.3 the finding is to be read with and subject to the subsequent order dated 10.8.88)". The judgment starts at "JUDGMENT:" on p.3 | p.1-3 |

## Comparison with corpus identity
- C6-01 identity "Ranjit Thakur v Union of India, SC 15-10-1987 (JUDIS 8566)": matches.
- cases_53 `DCLR-SC-1987-R01` (1987-10-15; Civil Appeal 2630 of 1987; (1987) 4 SCC 611; [1988] 1 SCR 512): matches the document. The document also prints AIR 1987 SC 2386, which the record does not list.
- **Discrepancy:** the C6-01 limitation (Fable F-16) names only CITATION/CITATOR INFO. The rendition also carries a full HEADNOTE across pp.1-3, plus an editorial note pointing to the 10.8.88 order. That order is cases_53 `DCLR-SC-1988-R02`; it is not held, and WS-B identity_resolution_cycle3 lists it as RANJIT_REVIEW UNRESOLVED.
- Defect in the rendition text: "3.?.1986" on p.3. p.4 reads "July 3, 1986".

## Classification observations (P-D3: owner decision, not decided here)
- The layout is a JUDIS database rendition: a typed-text frame, field labels, a "JUDIS" watermark and a URL header.
- The text carries the printed report's page numbers and headnote, which suggests it was keyed from a law report rather than from the court's signed judgment.
- See `../JUDIS_CLASSIFICATION_ANALYSIS.md`.

## Completeness
- All 9 of 9 pages are present, and the report pagination runs without a break.
- The rendition has no signature or date block, so it cannot show completeness against a signed original.

## Identity result
**CONFIRMED.** This covers case identity only. Any pinpoint must exclude pp.1-3 up to "JUDGMENT:".

## Retrieval record and limitations (added after review 5212a95b, B-02)
- Retrieval (C6-01): url https://api.sci.gov.in/jonew/judis/8566.pdf; date NOT_EVIDENCED; method official URL corroborated by recorded sha256; remaining gaps: no retrieval date in a retrieval record (C6-01-PROVENANCE/registers/provenance_recovery_register.csv#C5-SRC-J-SC-1987-RANJIT-THAKUR~C1)
- Limitations to be carried into any entry, verbatim: see `../sc_copy_evidence_register.csv#C5-SRC-J-SC-1987-RANJIT-THAKUR~C1` column `limitations` (it includes: retrieval date NOT_EVIDENCED).
