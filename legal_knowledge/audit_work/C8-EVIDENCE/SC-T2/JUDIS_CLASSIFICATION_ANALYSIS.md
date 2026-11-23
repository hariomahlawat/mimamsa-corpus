# JUDIS renditions: evidence for owner decision P-D3 (not decided here)

**What this is.** This note records the facts for the three held files in the JUDIS text-rendition format: Ranjit Thakur, S N Mukherjee and Navjot Sandhu. It sets out the two classification options and their consequences, and lists what further evidence would settle the question. It does not choose between the options. That choice is owner decision **P-D3** (AUTH-LEDGER/RULE_DECISION_PACK.md, line 102).

**Who read it.** The page readings were made by an AI agent (Claude Opus 5.5 subagent) and have not been confirmed by a person (`page_checks_sc_c8.csv`).

## 1. What the held files are
| Fact | Ranjit Thakur `ed7cf31f` | S N Mukherjee `eb442080` | Navjot Sandhu `3b753548` | Source |
| --- | --- | --- | --- | --- |
| Recorded locator | api.sci.gov.in/**jonew/judis**/8566.pdf | api.sci.gov.in/**judgment/judis**/7439.pdf | api.sci.gov.in/**jonew/judis**/27092.pdf | WS-B-JUDGMENTS/tools/held_copies.csv |
| Producer / PDF version | GNU Ghostscript 7.05 / PDF 1.2, no dates in metadata | same | same | AUTH-LEDGER/evidence/copy_structure.csv; PDF metadata |
| Bytes / pages / text chars | 37,351 / 9 / 29,538 | 92,905 / 23 / 84,851 | 464,857 / 107 / 484,329 | copy_facts.csv, copy_structure.csv |
| Embedded images / signature | 0 / none | 0 / none | 0 / none | copy_structure.csv |
| Header on every page | "http://JUDIS.NIC.IN · SUPREME COURT OF INDIA · Page X of 9" | "... Page X of 23" | "... Page X of 107" | C8-SCPIC-01, 04, 05, 07, 08, 09; text layer |
| Watermark | diagonal outline "JUDIS" | same | same | renders |
| Page-1 structure | database fields (PETITIONER, RESPONDENT, DATE OF JUDGMENT, BENCH, CITATION, CITATOR INFO, ACT, HEADNOTE) | same | database fields (CASE NO., PETITIONER, RESPONDENT, DATE OF JUDGMENT, BENCH, JUDGMENT); **no** CITATION, CITATOR or HEADNOTE | C8-SCPIC-01, 05, 08 |
| Headnote / editorial matter | HEADNOTE on pp.1-3 with "HELD:" points, bracketed report pinpoints ([518G-H]) and an editorial note on a 10.8.88 order | HEADNOTE and list of cases referred, pp.1-3 | none found in the text layer | C8-SCPIC-02, 06; text-layer search |
| Inline printed-report page numbers | 513-525, no gap (citation 1988 SCR (1) 512) | 45-76, no gap (1990 SCR Supl. (1) 44) | none | tools/inline_numbers.py |
| End of text | "N.P.V. Appeal allowed." then "525"; no signatures or date | "R.N.J. Appeal dismissed." then "76"; no signatures or date | operative paragraph; no signatures or date | C8-SCPIC-04, 07, 09 |
| Text defects | "3.?.1986" (p.3) | none noticed on the pages read | "\005" literal ×90 | text layer |

**Contrast with the other two JUDIS-path files.** Dharamvir (`/jonew/judis/40493.pdf`) and Rajbir C1 (`/jonew/judis/42379.pdf`) come from the same JUDIS path family, but they are not text renditions:
- They are court-layout word-processor PDFs: LibreOffice 3.6 and 3.5. The Dharamvir file was later modified with iText 2.1.7.
- They carry a cover, REPORTABLE, dotted signature lines with names, and place and date.
- A watermark ("SUPREME COURT OF INDIA", emblem, "JUDGMENT") and a second "Page N" series are overlaid.

So "JUDIS" names a hosting system, not a single format. P-D3 concerns the **typed-text database renditions**, not every file served from a /judis/ path.

## 2. What these facts show
- **Official dissemination.** Each file was recorded at an sci.gov.in URL with a sha256 equal to the held bytes (held_copies.csv). That supports a claim that the court's own system disseminated these bytes. The retrieval date is not evidenced for Ranjit and S N Mukherjee. For Navjot, the first-class record is SOURCE_LOCATED, not VERIFIED (provenance_recovery_register.csv; S-REVB-012).
- **Fidelity.** The files are not the court's signed judgment layout. Observable reasons:
  - database field labels;
  - a URL header;
  - a JUDIS watermark;
  - monospaced re-keyed text;
  - no signature block and no date block.
- In the 1987 and 1990 files, the inline page numbers and headnotes match the Supreme Court Reports citation printed on p.1. That pattern fits text keyed from a law report rather than from the signed original. This is an inference from page evidence. It is not established.
- **Completeness.** Two measures are complete:
  - the internal "Page X of N" sequence;
  - the inline report pagination, for Ranjit and S N Mukherjee.

  Completeness against the signed judgment cannot be measured from these files, because no signed original or signature page is held.
- **Extraneous material.** For Ranjit and S N Mukherjee, pp.1-3 up to "JUDGMENT:" are database and headnote matter, not judgment text. The Ranjit headnote contains an editorial note that bears on the judgment's later treatment ("to be read with and subject to the subsequent order dated 10.8.88").

## 3. The two options and their consequences
| | Option A: treat as court-issued copy (`PRIMARY_OFFICIAL_COURT_COPY`) | Option B: treat as court-system rendition (`COURT_SYSTEM_RENDITION`, non-primary) |
| --- | --- | --- |
| Basis | Hosted and served by the court's own system; for pre-digital judgments this may be the only form the court publishes | Fidelity table (POLICY_OPTIONS.md section D; RULE_DECISION_PACK.md lines 92-93): database or text rendition, not the court's judgment file |
| Rule-1 effect | Ranjit, S N Mukherjee and Navjot each become EFFECTIVE_PRIMARY_VERIFIED. Simulated joint EXACT_ANCHOR count is **13** (`exact_anchor_simulation.json` joint_all_8) | These 3 copies stay non-primary. Joint count with the other 5 candidates is **10** (`subsets["joint_excluding_3_judis_text_renditions ..."]`) |
| Anchors | DCLR-SC-1987-R01, DCLR-SC-1990-N02 and DCLR-SC-2005-L01 become EXACT_ANCHOR | Those 3 stay PARTIAL_MATCH |
| Pinpoint handling needed | Pinpoints must exclude pp.1-3 database and headnote matter (Ranjit, S N Mukherjee). Page pinpoints are rendition pages, not report or court pages. Navjot has no stable paragraph numbers (WS-B OI-11) | Same text remains usable as a research rendition. Anchoring waits for a court-issued copy or a decision to accept a reporter (for example SCR) |
| Risk | Headnote or editorial text could be quoted as judgment text. Rendition errors ("3.?.1986", "\005") would be carried into anchored text | No primary anchor for three historically important judgments until better evidence exists |

Rule 1 itself cannot tell the two options apart. strength.py COURT_HOSTS and COURT_PATH accept both /jonew/judis/ and /judgment/judis/ paths, and `fidelity_issue` is not applied to court copies (ledger.py `_evidence_checks`, `if not court`). The classification therefore rests entirely on the owner's decision.

## 4. Evidence that would settle it
1. A statement from the Supreme Court registry, or published JUDIS documentation, on how JUDIS texts for pre-digital judgments were produced, and whether the court treats them as its authoritative copies.
2. A certified copy, or the court's own scanned signed judgment, for any one of the three cases. A word-level comparison with the JUDIS text would measure fidelity, including whether the headnote and report pagination are additions.
3. For Navjot: a VERIFIED retrieval record, which would remove the SOURCE_LOCATED limitation (RULE_DECISION_PACK option A2/A3), and a check of this text against a reported version. The reported citation is not printed on the held copy. WS-B subsequent_treatment_cycle3.csv#WSB-T3-046 quotes it only in garbled form, so no citation is asserted here.
4. Evidence that /judgment/judis/7439.pdf and /jonew/judis/7439.pdf serve one resource, if an alias is to be recorded (POLICY_OPTIONS.md line 32).
5. A person, not only an agent, confirming the page readings above (policy B2).
