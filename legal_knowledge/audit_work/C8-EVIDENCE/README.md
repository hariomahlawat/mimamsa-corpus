# C8-EVIDENCE: Gazette tranche 1 and Supreme Court tranche 2 documentary verification (Cycle 8)

**Status:** evidence preparation only.
- **Nothing is approved or active.** The AUTH-LEDGER stays at version 0. No decision or review record exists, and no BIND line.
- **No legal status, currency, applicability or precedent treatment is determined.**
- **Revision:** corrected after independent review 5212a95b (verdict ACCEPT WITH CONDITIONS). The review and the disposition of each finding are in `review/`.
- **Who read the pages:** all page readings were made by AI agents (Claude Opus 5.5 subagents) and are **not human-confirmed**. Each reading carries the sha256 of the exact page render, so a person can re-check it.

## Contents
| Path | What it is |
| --- | --- |
| `GAZETTE-T1/gazette_evidence_register.csv`, `evidence/T1-NN.md` | 18-item evidence record for each of the 20 primary Gazette candidates |
| `GAZETTE-T1/page_image_checks_c8.csv` | 40 fresh page-image checks (C8-PIC-01..40; C8-PIC-40, T1-20 PDF p.6, added after review) |
| `GAZETTE-T1/render_log.csv`, `crop_log.csv` | Render settings and hashes: PyMuPDF, 150 dpi grayscale; a re-render gave identical hashes |
| `GAZETTE-T1/contradiction_register_c8.csv` | All 20 earlier rows carried forward with content and status unchanged but restructured (three columns merged into `description`; the original locator in `original_locator`), plus C8-CR-01..14 (C8-CR-07 unused; C8-CR-14 added after review) |
| `GAZETTE-T1/born_digital_structure.csv`, `BORN_DIGITAL_FINDINGS.md`, `born_digital/` | Signature-structure and integrity results for S.R.O. 2(E)/2018 and 17(E)/2019 |
| `GAZETTE-T1/eligibility_recommendations.csv`, `GAZETTE_C8_FINDINGS.md` | Per-candidate recommendation and summary |
| `GAZETTE-T1/APPROVAL_PACKAGE.md`, `approval_package/` | Package 1, with one **unsigned** proposed-decision template per candidate (built by `tools/build_packages.py`) |
| `SC-T2/sc_copy_evidence_register.csv`, `page_checks_sc_c8.csv`, `evidence/` | Supreme Court copy identity evidence: 28 page checks, C8-SCPIC-01..28. The register also carries the C6-01 retrieval record and the limitations for each copy |
| `SC-T2/JUDIS_CLASSIFICATION_ANALYSIS.md` | Facts and options for owner decision P-D3. It is not decided here |
| `SC-T2/exact_anchor_simulation.json`, `EXACT_ANCHOR_FINDINGS.md` | Anchor recalculation with the real reader, under synthetic approval in temporary directories |
| `SC-T2/subsequent_treatment_leads.csv` | 20 research leads, all RESEARCH_LEAD_UNVERIFIED |
| `SC-T2/APPROVAL_PACKAGE.md`, `approval_package/` | Package 2, with unsigned templates |
| `*/tools/` | The offline scripts that produced the registers. They take the held-file directory as an argument. Renders, signature byte dumps and page text layers are **not** committed: they contain document bytes, and page text can carry personal data. The render log keeps only hashes, page numbers and settings (`SC-T2/tools/render_facts.jsonl`) |
| `review/` | Independent review 5212a95b (report and findings, copied verbatim) and `DISPOSITIONS_5212a95b.md` |

## Principal results
- **Gazette identities.**
  - All 20 identities are CONFIRMED on fresh page images: S.R.O. number, date line, issue number and date, Part II-Section 4. Of the 40 checks, 37 are CONFIRMED and 3 are PARTIAL (C8-PIC-40 is a context check of T1-20's last page); the PARTIAL ones have a partly illegible running header, but the identity elements are legible.
  - The 7 rows whose number was previously quoted only in the agent-produced R23 register now have their own render-hashed reading.
- **S.R.O. 34/1963.** The held instrument is the 05-01-1963 declaration under r.188(e). Its relationship to the "S.R.O. 34 dated 5 June 1963" listed in government notes stays **UNRESOLVED** (C8-CR-02), and no amendment chain is inferred. The notes in the 1982–1991 Gazettes list the June date, while S.R.O. 2(E)/2018 cites "S.R.O. 34 dated 05th January, 1963".
- **Born-digital copies.** Both have one signature whose signed ranges cover the whole file except the signature value, and no incremental update.
  - **S.R.O. 2(E)/2018 (T1-19):** the CMS signature verifies against its embedded certificate. This is integrity only. No trust chain, validity time or revocation was checked, and authenticity is not established.
  - **S.R.O. 17(E)/2019 (T1-20):** the CMS signature does **not** verify, although the message digest matches the signed bytes. The visible appearance "Digitally signed by MANOJ KUMAR VERMA" is on PDF p.6, the last page. The copy carries five instruments: S.R.O. 17(E) to 21(E)/2019, the last four being Navy and Air Force instruments.
  - **Reproduction:** the coordinator reproduced both results independently with `openssl cms -verify -noverify`, using separately written extraction code. T1-19 returned "CMS Verification successful" (rc 0). T1-20 returned `CMS_SignerInfo_verify: verification failure` (rc 4).
  - **Recommendation for T1-20:** NEEDS_FURTHER_EVIDENCE, not merely a fidelity hold.
- **Supreme Court identities.**
  - All 8 case identities are CONFIRMED from page 1 and the last page.
  - Discrepancies are recorded rather than resolved:
    - the Navjot judgment date 04/08/2005 is printed but missing from the C6-01 identity and cases_53;
    - the S N Mukherjee case number is missing in cases_53;
    - the Girish neutral citation 2026 INSC 149 is missing in cases_53;
    - the printed name is Narsingh Yadav;
    - the Rajbir C1 identity string names other copies;
    - the Mullikote file holds two versions of the judgment (pp.1-31 CORRECTED, pp.32-62 unmarked).
- **JUDIS renditions.** Ranjit Thakur, S N Mukherjee and Navjot are JUDIS-header text renditions with no signature block. The 1987 and 1990 files contain headnotes. Classification is owner decision P-D3.
- **Limitations in the templates.** Each unsigned template now carries the decisive limitations from the registers: the T1-20 signature failure, T1-19 integrity-only, T1-02 copy provenance only with S.R.O. 34 UNRESOLVED, the pending-entry and C6-01 addendum limitations verbatim, and, for the Supreme Court, the missing retrieval dates (Ranjit, S N Mukherjee, Girish, Mullikote), P-D3 and the Mullikote two versions.
- **Exact anchors.** The earlier "6 → 13" result **reproduces**. Excluding the three JUDIS renditions gives 10; excluding Navjot and Mullikote, which the preparer recommends keeping PARTIAL, gives 11.

## Rebuild
- The `--check` builders (`tools/build_packages.py`) reproduce the packages from the committed registers.
- The Gazette registers rebuild from committed files plus the pinned registers: `python GAZETTE-T1/tools/build_c8b.py --base <repo root> --out GAZETTE-T1`.
- The registers themselves were produced by the scripts in `*/tools/`. Re-running those needs the held binaries; their sha256 values are in `SOURCE-LIBRARY-C5/baseline/held_binaries_manifest.csv`.
