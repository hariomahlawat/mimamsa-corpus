# Cycle 9: Supreme Court judicial-evidence findings (summary)

**Status.**
- These are evidence findings only. Nothing is approved or authenticated.
- No ledger entry, decision record, BIND line or correction was created. The AUTH-LEDGER stays at version 0.
- No precedent status is stated.
- AI readings are by "AI agent (Claude Opus 5.5 subagent), not human-confirmed".

**Inputs.**
- The reviewed C8 package: tip files only; no git history was read.
- Snapshot `c9src` (2d7c02cf), read-only; `git status` was empty before and after.
- The held binaries: 11 copies were re-hashed (8 candidates, Rajbir C2 and C3, and PPS Bedi), and all 11 MATCH.

## 1. Renders
- `tools/render_c9.py` rendered 36 pages, with settings identical to C8 (PyMuPDF 2.1 / MuPDF 1.28.6, 150 dpi, grayscale).
- **All 28 C8 pages were reproduced byte-identically**, so the C8 readings attach to the same images.
- 8 pages are new:
  - S N Mukherjee p.4;
  - Navjot p.2;
  - Girish p.3;
  - Mullikote pp.4 and 35;
  - PPS Bedi pp.1, 7 and 38.
- The PNGs stay under `renders/` and are not to be committed. Their hashes are in `tools/render_facts_c9.jsonl`.

## 2. Human page-verification pack
`HUMAN_VERIFICATION_PACK.md` and `human_verification_checklist.csv` hold 52 items. There is one sheet for each anchor-creating copy, plus an optional PPS Bedi context sheet. Each sheet gives:
- the sha256 to re-hash;
- the PDF pages to open, each with its render sha256;
- identity elements, with the AI reading shown as a proposal;
- discrepancy questions;
- blank reviewer fields (name, date, CONFIRMED / NOT CONFIRMED, notes).

| Copy | Pages | Key question |
| --- | --- | --- |
| Ranjit | 1, 3, 4, 9 | JUDIS rendition; headnote pp.1-3; editorial note on the 10.8.88 order |
| S N Mukherjee | 1, 3, 4, 23 | CA 417/1984 printed, but the case record has no case number |
| Navjot | 1, 2, 107 | Q-NAVJOT-DATE: "04/08/2005". The sibling JUDIS files print day first (15/10/1987, 28/08/1990, 25/08/1982), which supports 4 August 2005 |
| Dharamvir | 1, 36 | (2013) 7 SCC 316 is not printed on the copy |
| Rajbir C1 | 1, 2, 20, plus C2 p.18 and C3 p.1 | Q-RAJBIR-C1: the merged identity string is the C5 source-level title; pinpoints are copy-specific |
| Girish | 1, 3, 17 | 2026 INSC 149 printed; the case record is empty |
| Mullikote | 1, 4, 31, 32, 35, 62 | Q-MULLIKOTE-VERSION: pp.1-31 against pp.32-62; correction date; any anchor must name pp.1-31 |

Narsingh Yadav is excluded: it has no case record, so its approval creates no anchor.

## 3. Exact-anchor simulations
Source: `EXACT_ANCHOR_C9.md` and `exact_anchor_simulations_c9.json`, produced with the actual reader; `--check` reproduces the output.

| Run | Exact anchors |
| --- | --- |
| Version 0 | **6** |
| Each candidate alone | 7 (Narsingh Yadav: 6) |
| All 8 jointly | **13** |
| Without the 3 JUDIS drafts | **10** |
| Without Navjot and Mullikote | **11** |
| Without the JUDIS drafts and Mullikote | **9** |
| Option (b) applied consistently | **9** |

**6 / 13 / 10 / 11 / 9 are confirmed.** The two 9s are different sets of cases.

New in C9:
- The documented demotion of PPS Bedi to `NON_PRIMARY_OFFICIAL_COURT_RENDITION` **fails** under rule 1, because PPS Bedi has no `copy_facts.csv` row and no accepted image check.
- Option (b) is expressible only as a demotion to `AUTHENTICATION_PENDING`.
- Option (c) cannot be simulated. Count proxies give 12, or 10 with the C8 recommendations.

## 4. JUDIS policy (P-D3)
`JUDIS_POLICY_DECISION.md` separates seven things for the four renditions:
- official hosting;
- official dissemination;
- fidelity to the judgment;
- database headnotes;
- editorial additions;
- transcription defects;
- judgment pinpoints.

It gives the exact effects of options (a), (b) and (c), and the eight rule-2 elements that (c) needs.

**Recommendation (not adopted):**
- **(c) as the end state** for all four renditions alike.
- Until rule 2 exists, **no status change in either direction**: do not add the three drafts and do not demote PPS Bedi.
- Record the asymmetry as a frozen-baseline limitation on PPS Bedi.
- If the owner finds the asymmetry unacceptable, the alternative is (b) via `AUTHENTICATION_PENDING` (6 → 9), after O-5 is decided.

## 5. Citation and completeness findings
`citation_completeness_c9.csv` has 29 rows:
- 18 carried forward from C8, of which 3 are refined;
- 11 new.

The new and refined findings:
- **Navjot:** besides `\005` x90, the text layer has escape literals `\027` x127 and `\026` x22 (CC9-11).
- **Dharamvir:** the garbled producer decodes from UTF-16BE as "LibreOffice 3.6; modified using iText 2.1.7 by 1T3XT". The baseline Anvar copy has the same encoding (CC9-13).
- **Rajbir:** the merged C1 identity originates in the frozen C5 source-master title and is repeated in C8-SOURCES (CC9-14).
- **Narsingh Yadav:**
  - C5 publication_date is NOT_DETERMINED although the date is printed (CC9-16).
  - **Privacy:** WS-B `WSB-T3-011` stores a mirror document identifier that embeds the appellant's service number (CC9-17, masked here).
- **Mullikote:**
  - Version 2 also re-letters the questions (A/B becomes C/D). The author line is the same in both versions (CC9-21).
  - The C5 completeness status cannot see the duplication (CC9-22).
- **PPS Bedi:**
  - The Cycle 4 description "Historic JUDIS scan" is inaccurate: the file has 0 images and is a typed-text rendition (CC9-23).
  - Headnote matter runs pp.1-7 (CC9-24).
  - Probable defect "2S" (CC9-25).
  - **WSB-H-053 pinpoint inconsistent:** pp.19-21 are stated, but SCR 426-427 are on pp.25-27 (CC9-26).
  - WS-B OI-06 calls the headnote cases-referred list "official" (CC9-27).
  - There is no identity evidence row for PPS Bedi (CC9-28).
- **Classification:** exactly four held files are JUDIS typed-text renditions. Anvar shows that a JUDIS path does not imply a rendition (CC9-29).

## 6. Subsequent-treatment leads
`subsequent_treatment_leads_c9.csv` has 29 leads: the 20 C8 leads carried forward (verbatim except masked service numbers) and 9 new ones. All are RESEARCH_LEAD_UNVERIFIED. The new leads:
- PPSBEDI-1 to 4:
  - Ranjit (WSB-T3-001) reported as following PPS Bedi, which the JUDIS citator "F 1987 SC2386 (5)" corroborates only as database matter;
  - the 1993 rule changes;
  - mirror citations;
  - OI-12.
- RANJIT-4: the unidentified "1991 SC1617".
- SNM-4.
- NAVJOT-4: rendition fidelity of quotations.
- GIRISH-3: proposals E8-CP-01 to 03.
- MULLIKOTE-4: the PEN records that depend on the version.

No good-law conclusions are drawn.

## 7. Files (all in this `SC-C9/` folder; originally produced under `c9out/SC/` in the working area; review FR-04)
- `HUMAN_VERIFICATION_PACK.md`, `human_verification_checklist.csv`
- `JUDIS_POLICY_DECISION.md`
- `EXACT_ANCHOR_C9.md`, `exact_anchor_simulations_c9.json`
- `citation_completeness_c9.csv`, `subsequent_treatment_leads_c9.csv`
- `judis_scan_c9.csv`, `scr_pinpoint_check_c9.csv`
- `SC_C9_FINDINGS.md`
- `tools/`: each script takes paths as arguments and supports `--check`:
  - `sim_anchor_c9.py`
  - `render_c9.py` (writes `render_facts_c9.jsonl`)
  - `judis_scan.py`
  - `scr_pinpoint_check.py`
  - `build_c9_pack.py`
- `renders/`: 36 PNGs; **never commit**.

## 8. Limitations
- **What was read.** Only the listed pages were image-read. Everything else was examined through the text layer (counts, markers and labels only).
- **Signatures.** No signature was validated.
- **Network.** No network access was used.
- **Option (c).** It is not simulable under rule 1.
- **Human confirmation.** None of the readings is human-confirmed. The pack exists to obtain that.
