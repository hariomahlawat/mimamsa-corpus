# Independent adversarial review: C6-01-PROVENANCE and C6-PREP (PR #33, commit a165b0f3)

Reviewer: Claude Fable 5.2 (`claude-fable-5-2`, self-reported; requested through the Claude Code Agent tool with model `fable`), agent type `independent-reviewer`. Tools: Read, Glob, Grep only (WebFetch/WebSearch instructed off and unused). It could not write, run code, hash or use git. **Condensed record, not verbatim** (corrected after Fable re-review N-08). The coordinator (Claude Opus 5.5) condensed the reviewer's hand-back: all 26 findings, their severities, the verdict and the five conditions are kept; the consequence and verification-procedure columns are omitted, and the methodology and 'not performed' sections are shortened. The reviewer confirmed it as faithful in substance (re-review N-08).

RESEARCH ONLY. This is not legal advice, not a legal determination and not a sign-off for the legal adviser, JAG or the project owner.

**Verdict in one line: ACCEPT WITH CONDITIONS as a proposals-only package; no entry should be approved and no architecture implemented until the P2 items below are closed.** No P1; 9 P2 and 17 P3 items.

## 1. Methodology (summary of the reviewer's statement)
- Commit a165b0f35c2f9bd0636013923d1a07b4c809d68b (branch ref). Could not run git status/diff.
- Read in full: build_provenance.py, build_addendum_plan.py, build_reports.py, compute_copy_facts.py; all 34 proposal rows; unresolved register; summary; page_image_checks_c6.csv; held_copy_facts.csv; README; METHOD; D1-D6; TRA2026_CLASS_COMPARISON.md; EVIDENCE_RECOVERY_REQUIREMENTS.md; INTEGRATION_ARCHITECTURE.md; AUTHENTICATION_ADDENDUM_PLAN.md; earlier review files (after forming its own view). Partly: recovery register, addendum draft, legacy map. C6-PREP README, carry-over, both reports, build_prep.py, metadata log, D&V candidates; the C6 test file.
- Upstream opened: CALIBRATION-02 register and evidence_classification.py; SOURCE-LIBRARY-C5 page_image_checks_c5.csv, D7, RV-01, master rows 72-73, copy rows, build_registers.py 288-477; PILOT-01 S-REVA-016/021, S-BLIND-012/013/014, S-JUD-003/004/005, S-REVB-002/003/012; code-resolution rows SC_PPS, SRC-RANJIT, V6-S14/15/16/18/20, V7-S10; discovery T3-01, T5-03, T6-03; R23 independent-reviewer-D.json, amendment_search; ACQ-02 supplement and PIC; ACQ-01 snapshot 236353; ARMY-RULES-CHAIN-01 AR-007/008/010/020/026/027/033/034/035; WS-A WSA-PIC-29/30/45/46; WS-B held_copies, identity_resolution RAJBIR; SOURCE_AUTHORITY_POLICY.md.
- Images/PDFs viewed: the four C6 renders; tra2026.pdf pp.1, 11-15; rs_313431.pdf p.1 and C5 zoom; indiacode_1975-13.pdf p.1; rop_275403.pdf pp.20-21; snmukherjee_judis7439.pdf p.1.
- 34 of 34 proposals checked at some level (13 non-Gazette fully; 21 Gazette md5/bytes: 0 disagreements).
- Independence limit: same model family and filesystem as earlier agents; F-11 shows correlated error.

## 2. Findings

### P2
- **F-01** Rajbir copy C2 (`C6-01-AP-c6ec489d`) proposed primary on another copy's evidence: its only locator is a parenthesis inside C1's retrieval record S-BLIND-013; retrieved_on/by belong to C1; C2 is 163,859 bytes / 21 pp. vs 230,938 / 20 pp.; pp.20-21 are a Record of Proceedings ending "(Signed reportable judgment is placed on the file)"; C5 copy register: page equivalence NOT established; identity rests on two name tokens. Draft says this entry alone moves DCLR-SC-2015-N09 to EXACT_ANCHOR. Correction: sha256 inside another record's locator = lead, not FULL; C2 to PARTIALLY_DOCUMENTED (or at most non-primary) until its own retrieval record and page comparison; describe as "judgment text + ROP of 13-02-2015". Verify: rebuild; C2 absent; classify test; Rajbir effect only from C1.
- **F-02** Retrieval records disclaiming authenticity still count as FULL; RS row stays DOCUMENTED (L3 ignores verification_state/authenticity; S-REVA-021 SOURCE_LOCATED, authenticity UNCONFIRMED, item page; sitting date/volume/session not printed, "03-03-1987" from the file name only; external image rows lack a result field; withholding by a source-id constant). Correction: require an affirmative verification state for FULL; identity elements claimed must be printed, else Ip; RS falls to PARTIALLY_DOCUMENTED by rule, keep WITHHELD note. Verify: counts change; synthetic UNCONFIRMED test.
- **F-03** S.R.O. 34 identity written as fact (`C6-01-AP-4acdb1a8` "(notes misdate as 05-06-1963)"); S-REVD-002 SOURCE_LOCATED with "IDENTITY MISMATCH WITH TARGET"; notes of 1988/1993/2003 list "S.R.O. 34 dated 5-6-1963"; R23 calls the misdating "apparent", "absence not proven". Correction: annotate UNVERIFIED as for S.O. 4010. Verify: test.
- **F-04** TRA comparison omits closest comparators: three archive.org e-Gazette copies (2018, 2019, 2022; `7c12a7ec`, `138c1da0`, `2bdab5b7`) proposed PRIMARY_GAZETTE_ARCHIVAL_FACSIMILE; 2022 file `source: derivative`; no signature verified on any. Correction: add them; one rule for born-digital Gazette copies applied to all four or reasons recorded; report document authority, carrier and copy fidelity separately (policy v1).
- **F-05** D3, D4, D6 contradict the plan/architecture (still "relabel"; D6 asks whether to add the WITHHELD RS record; "34 additions" without WITHHELD; D4 says 4 non-primary simulated when only 3 are). Correction: regenerate/rewrite; derive counts. Verify: tests.
- **F-06** Architecture "either way" output option breaks reproducibility (§2.5 replace current outputs; §2.4 edits C5 inputs; §2.3 edits C4 tool; §2.2 addenda inside C4 folder; no rule/code version pin). Correction: versioned folders only; ledger, reader, outputs in a new package; C4/C5 byte-identical; pin rule version and output hashes per manifest version.
- **F-07** Plan, architecture and draft disagree (paths; CORRECTION/WITHDRAW vs refusal of same key; `superseded_by` in an immutable file; draft lacks entry type, reviewer_ref, evidence_refs; free text in owner_decision; mutable manifest; no immutability CI). Correction: one spec, JSON Schema, chained manifest, immutability check.
- **F-08** Classification change possible without evidence or authenticated decision (refs presence-only; APPROVED a free cell; draft records an owner instruction with no committed artefact; carrier hand-authored and gating primary; strength not in schema, validator would import C6-01 builder: code cycle). Correction: resolvable refs, ADD needs a first-class record with the same sha256; committed hash-pinned decision records; carrier/class changes in the ledger; strength computed in the ledger package.
- **F-09** Anchoring and withdrawal under-specified (source-level first-eligible-copy anchoring; WITHDRAW to "no row" loses adverse facts; undefined interactions; round-trip byte-identity vs `effective_from_entry`; per-entry simulations do not compose). Correction: copy-level anchoring with page equivalence or pinpoint check; WITHDRAW with mandatory reason and optional resulting state; orphan rules; audit trail in a separate file; joint effect of the approved subset; "newly withdrawn" change list.

### P3
| ID | Location | Evidence | Correction |
| --- | --- | --- | --- |
| F-10 | METHOD identity rule; build_provenance identity collection | any external image row with a render hash counts; chain route needs no render hash; T is one surname for N S Yadav and S N Mukherjee | T must also match case number or decision date; external checks must name identity elements |
| F-11 | C6-PIC-02 | "s.14 amends s.361 of the Income-tax Act 2025 (last section)" is entry 14 of THE SECOND SCHEDULE "(See section 18)"; earlier reviewer repeated it | correct the reading; note correlated error |
| F-12 | TRA comparison | ByteRange confirmed; untested whether trailing 28,384 bytes are an incremental update whose signed revision can be validated offline | add offline revision check as option 0; soften claim |
| F-13 | proposals `official_locator_recorded`, 21 Gazette rows | item page shown though file URLs are evidenced (`sorted()[0]`) | prefer the /download/ URL |
| F-14 | build_provenance carrier | strips "(as reported; retrieval record not documented)" incl. 4 court rows on corroboration only and ER 2023 | keep the qualifier when no direct L3 |
| F-15 | `10e1954f` Mullikote | CORRECTED judgment at a re-servable URL; corroboration only, no retrieval date | state in limitations; require dated retrieval record |
| F-16 | `ed7cf31f`, `eb442080` | JUDIS re-typed rendition with CITATION, CITATOR INFO, HEADNOTE | limitation: headnote/citator not judgment; pinpoints exclude them |
| F-17 | `eb442080` | `/judgment/judis/7439.pdf` vs `/jonew/judis/`; V7-S10 locator_consistency NOT_CHECKED; exact-string contradiction test | normalise URLs; mark locator unconfirmed |
| F-18 | evidence recovery §2 | India Code serves download-specific bytes, so re-acquisition yields a new sha256; a handwritten "17"-like mark beside the masthead on held p.1 not recorded | say re-acquisition creates a new copy; define equivalence; record the mark |
| F-19 | C6-PIC-04 | p.5 cites Army Act ss.125-127 though s.127 omitted by Act 37/1992 (RV-26); chapter reproduces 1952 Rules (T5-03) | currency markers; historical/unknown currency |
| F-20 | SO4010 text | 6 Dec 1986 was a Saturday (Gazette day) by the reviewer's reckoning: "dated" may be the Gazette date (inference) | add "date semantics UNVERIFIED" |
| F-21 | compute_copy_facts.py | hashes first held path only; extraction failure exits 0 | hash every path; fail on extraction error |
| F-22 | build_prep.py | docstring promises a partial check the code lacks; needs local git objects; no rebuild test | fix docstring or implement; add test |
| F-23 | build_reports.py etc. | no report --check; write_text without encoding; hard-coded denominators and counts | derive; add report check |
| F-24 | tests | proposals keyed by 8-hex prefix; duplicate test repeats one sha; remedy "lengthen the display prefix" renumbers all | key by full sha; synthetic collision; lengthen only colliding IDs |
| F-25 | build_addendum_plan / coverage_impact | WITHHELD simulated then labelled "not applied"; monkeypatch restores a bound method; proposed C4 block unchanged at 13 rows | skip WITHHELD simulation; restore descriptor; label |
| F-26 | whole package | reviewer could not run diff/hash checks at a165b0f3; network requests in the branch not evidenced as owner-authorised | reviewer with git access repeats diff-scope and hash checks |

### 2a. S.O. 4010/1986 (F-20)
The reviewer read "S.O. No. 4010, dated the 6th December, 1986 ... [Placed in Library. See No. LT-3868/87]" on the held PDF and the C5 zoom, agreeing with C5-PIC-02 and PILOT-01, not RV-01. This does not resolve the dispute (third reading of a secondary record; notification not held). The package handles it correctly. Unrecorded ambiguity: 6 Dec 1986 was a Saturday (inference). Sitting date rests on the file name only.

### 2b. Integration safety (F-26)
Checked by reading: C4 register 13 rows; C5 D7 OPEN; no in-force or currency claim. Not checked: diff scope, 658/53 and C4 hashes at a165b0f3. Network: 4 robots GETs and 6 HEADs to archive.org on 2026-11-23, data GETs refused; owner authorisation not evidenced in the package. Untracked __pycache__ ignored by .gitignore.

### Confirmations
TRA renders match (except F-11); ByteRange confirmed. Delhi HC PARTIAL correct. Act 13/1975 uncertainty carried; nothing invented. classify() excludes weaker evidence except via F-01/F-02 routes. Non-primary cannot anchor at copy level (because the C4 rule tests `startswith("PRIMARY_")`; accidental; source-level inheritance remains). Isaac absent. No legal conclusion promoted except F-03.

## 3. Architecture assessment
Reproducibility only with versioned folders and untouched C4/C5 (F-06). Not yet append-only (F-07). Classification change without evidence possible (F-08). One copy authenticating another: formally no, practically yes via sibling refs (F-01) and source-level anchoring (F-09). Withdrawal works for a simple ADD only (F-09). Counts derived in design, hard-coded in package (F-23). Data flow acyclic; code cycle risk (F-08) and C6-01 scope dependency (F-06). Offline-testable for the ledger.
Alternatives: A rejected; B superseded; C right direction but mutates C4/C5; **C′ recommended**: overlay package (new ledger, schema, reader outside C4/C5; effective holding state by an explicit transition table from the version-0 state; outputs in effective/vN/ with hash-pinned manifests; C4/C5 pinned in CI); D deferred. Sequencing: vocabulary, validator and immutability tests first with zero entries; then tranches.

## 4. Residual risks
Byte identity is not authenticity; no signature verified. Four court rows rest on corroboration only. EXACT_ANCHOR says nothing about later treatment (Anvar overruled Navjot on s.65B per S-JUD-006). TRA commencement by notification not evidenced. ER 2023 incomplete; Delhi HC currency unknown. Correlated error. C6-PREP scope flagged.

## 5. Verdict
**ACCEPT WITH CONDITIONS** (proposals-only; nothing incorporated). Conditions: (1) fix F-01, F-02, F-03; (2) complete the TRA comparison (F-04, F-12); (3) reconcile D3/D4/D6 (F-05); (4) one consistent overlay architecture spec with schema, immutability and withdrawal rules (F-06 to F-09); (5) git-capable diff-scope and hash check at the reviewed commit (F-26). P3s before or at incorporation.

## 6. Not performed
Hashing; running builders/tests; git; signature validation; pixel comparison; full read of the recovery register, addendum draft, legacy map; re-rendering 21 Gazette pages; online URL checks; ACQ-02 SHA-1 check; EVIDENCE_STANDARD.md, PROGRESS.md, two READMEs; any legal analysis.
