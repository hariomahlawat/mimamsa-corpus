# JUDIS renditions: classification policy paper for owner decision P-D3 (Cycle 9)

**Status.** This paper is a proposal for the owner. It changes no status, creates no ledger entry, and approves or authenticates nothing. It says nothing about whether any of the four judgments is good law. Page readings cited here were made by an AI agent (Claude Opus 5.5 subagent) and are not human-confirmed. Rule version 1 remains in force.

## 1. The question
- **Four held files** are JUDIS typed-text database renditions served from Supreme Court hosts (`judis_scan_c9.csv`, a scan of every held PDF):

  | Copy | sha256 | Status today |
  | --- | --- | --- |
  | PPS Bedi (1982) | `211dbaf4` | Classed `PRIMARY_OFFICIAL_COURT_COPY` in the frozen Cycle 4 register; one of the 6 exact anchors at version 0 |
  | Ranjit Thakur (1987) | `ed7cf31f` | C6-01 draft, proposed for that same class |
  | S N Mukherjee (1990) | `eb442080` | C6-01 draft, proposed for that same class |
  | Navjot Sandhu (2005) | `3b753548` | C6-01 draft, proposed for that same class |

- **The question for P-D3:** should all four be treated as the court's own copies of the judgment, or as the court system's renditions of it? If something in between, what exactly may such a file anchor?
- **Not part of the question:** Dharamvir (`3056712c`), Rajbir C1 (`970b9680`) and the baseline anchor Anvar (`06f77a70`) are also served from `/jonew/judis/` paths, but they are court-layout PDFs. "JUDIS" names a hosting system, not one format. P-D3 concerns only the typed-text rendition profile.

## 2. Seven things that must be kept apart
| Concept | What it is | What the four files show | Who can establish it |
| --- | --- | --- | --- |
| **Official hosting** | The bytes were served by a court-controlled host and path | All four recorded at `api.sci.gov.in/(jonew\|judgment)/judis/<n>.pdf` with a recorded sha256 equal to the held bytes (`WS-B-JUDGMENTS/tools/held_copies.csv`). Retrieval dates are not evidenced for Ranjit and S N Mukherjee. Navjot's first-class record is SOURCE_LOCATED. S N Mukherjee's path `/judgment/judis/` is a second path shape whose identity with `/jonew/judis/` is unverified | Retrieval records (rule 1 already tests host and path shape: `strength.COURT_PATH`) |
| **Official dissemination** | The court publishes this text as its public version of the judgment | Supported in part by hosting: the court's system serves these renditions. It is **not** shown that the court treats JUDIS text as its authoritative copy. No registry statement or JUDIS documentation is held | Registry statement or published JUDIS documentation (C8 analysis, section 4, item 1) |
| **Fidelity to the judgment** | How closely the words and layout follow the signed judgment | Not measurable from the files. No signature block, no date block, monospaced re-keyed text, database field labels, URL header and watermark. The 1982, 1987 and 1990 files carry continuous law-report page numbers (394-445, 513-525, 45-76), which fits keying from a law report (inference, not established). No signed original is held for any of the four | Comparison with a certified copy or the court's scanned signed judgment |
| **Database headnotes** | Fields added by the database: CITATION, CITATOR INFO, ACT, HEADNOTE, cases-referred list | Present in PPS Bedi (pp.1-7 up to "JUDGMENT:"), Ranjit (pp.1-3) and S N Mukherjee (pp.1-3). Absent from Navjot, which has database fields only (CASE NO., PETITIONER, RESPONDENT, DATE, BENCH) | The files themselves (checked: `judis_scan_c9.csv`, C8/C9 renders) |
| **Editorial additions** | Notes written by an editor, not the court | Ranjit's headnote note on the order of 10.8.88. Reporter end tags ("P.B.R. Petitions dismissed.", "N.P.V. Appeal allowed.", "R.N.J. Appeal dismissed."). The citator codes (F, R, RF, D), which are not defined on the copy | The files; their meaning needs the publisher's key |
| **Transcription defects** | Characters lost or mis-keyed in the rendition | Navjot: `\005` x90, `\027` x127, `\026` x22. Ranjit: "3.?.1986". PPS Bedi: "2S" where a rule number is expected (p.7), and the BENCH field repeats a name | The files; a defect list per copy |
| **Judgment pinpoints** | Locators into the court's own text (page, paragraph) | Rendition pages are not court pages. Ranjit is partly numbered; S N Mukherjee and PPS Bedi are unnumbered; Navjot has no paragraph numbers (OI-11). Report pages give a second locator. Five WS-B SCR pinpoints check out; one does not (WSB-H-053: pp.19-21 stated, SCR 426-427 printed on pp.25-27; `scr_pinpoint_check_c9.csv`). WS-B OI-06 treats the PPS Bedi cases-referred list (headnote matter) as "official" | Pinpoint validator against the rendition's own markers |

Rule 1 does not separate these concepts for court copies:
- `strength.COURT_PATH` accepts both JUDIS path shapes.
- `ledger._evidence_checks` skips `fidelity_issue` for court copies (`if not court`).
- Identity can rest on the page-1 text rule.
- A case row becomes EXACT_ANCHOR from the case-to-source mapping alone.

So under rule 1 the classification is decided entirely by the class an owner approves.

## 3. Options, applied to all four renditions alike
Effects come from `exact_anchor_simulations_c9.json` (actual reader, temporary ledgers, joint runs). Counts are distinct cases with EXACT_ANCHOR.

### (a) Court-system dissemination counts as official: all four are primary court copies
- **Ledger effect:** ADD the three drafts as `PRIMARY_OFFICIAL_COURT_COPY`. PPS Bedi is unchanged.
- **Anchors:**
  - with all 8 candidates: 6 → **13**;
  - with the C8 keep-PARTIAL recommendations for Navjot and Mullikote: **11**.
  - New JUDIS anchors: DCLR-SC-1987-R01, -1990-N02 and -2005-L01, plus PPS Bedi as at present.
- **Risks:**
  - Headnote or editorial text can be quoted or pinpointed as judgment text (PPS Bedi pp.1-7; Ranjit and S N Mukherjee pp.1-3).
  - The Ranjit anchor ignores a known later order (10.8.88) that is not held.
  - Rendition defects are carried into anchored text.
  - The Navjot anchor attaches to a citation lead that has no date or case number.
- **Rule-2 support needed:** none, which is the problem.

### (b) Court-system rendition: all four are non-primary
- **Ledger effect:**
  - Do not add the drafts as primary. They may be added as `NON_PRIMARY_OFFICIAL_COURT_RENDITION`, which validates (run b4).
  - Demote PPS Bedi's baseline row by a ledger transaction, with records, review and binding. Its timing depends on O-5.
- **Anchors:**
  - with the other 5 candidates: 6 → **9** (b2, b3, b4);
  - with Mullikote also kept PARTIAL: **8** (b5);
  - PPS Bedi demotion alone: 6 → **5** (b0).
- **Exact effect today (new in C9):**
  - Rule 1 cannot record PPS Bedi as a *documented* non-primary rendition. That CORRECTION fails the identity check, because PPS Bedi has no `copy_facts.csv` row and no accepted image check (b1, FAIL).
  - The only demotions that validate set it to `AUTHENTICATION_PENDING`, by CORRECTION or by WITHDRAW. That misstates documented provenance as pending, and the source becomes `HELD_AUTHENTICATION_PENDING`.
  - The three drafts, if added as documented non-primary, still show their sources as "provenance undocumented" (a `derive_holding` artefact).
- **Risks:** older judgments with no court-layout copy cannot anchor at all, including a current baseline anchor whose identity is not in doubt.

### (c) Primary for identity; anchors limited to the judgment text
- **Ledger effect under rule 1:** none possible. Rule 1 has no scope for anchors.
- **Count proxies** (rule 1, with Ranjit withheld under "no later order known"; headnote exclusion not modelled):
  - 12 with all other candidates;
  - 10 with the C8 recommendations.
- **What rule-2 support (c) requires:**
  1. **A scoped class or entry field**, for example `anchor_scope` (PDF page range and start marker, such as "from 'JUDGMENT:' on p.k") and `excluded_ranges` (database and headnote pages). This needs a schema change. Frozen rule-1 history and version 0 must stay reproducible.
  2. **A pinpoint validator:**
     - it refuses KB or holdings pinpoints inside excluded ranges;
     - it expresses rendition pinpoints as rendition page plus printed-report page;
     - it checks the two agree, as `tools/scr_pinpoint_check.py` does in prototype.
  3. **Case-row identity for JUDIS anchors:** the case record must carry the printed date and case number, and they must match. This blocks Navjot until its record is corrected; today case rows rely on the mapping input alone.
  4. **A later-order condition:** no anchor where a later order in the same case is known but not held. This withholds Ranjit until the 10.8.88 order is held. The condition needs a field in the case record or an evidence register.
  5. **A per-copy defect register** (escape literals, "3.?.1986", "2S"), shown wherever anchored text is quoted.
  6. **Identity evidence for PPS Bedi.** Re-expressing its baseline row under (c) is a CORRECTION, so it needs an identity record the validator accepts: a `copy_facts.csv` row (a frozen-input change) or a human-confirmed image check (B2).
  7. **B2 for every anchor-creating entry:** a human-confirmed identity check (`HUMAN_VERIFICATION_PACK.md`). AI readings alone do not count.
  8. **Reproducibility:** rule version 2 in its own reviewed PR, with `--as-of` diffs and tests for each condition above.

## 4. Recommended owner decision (preparer's recommendation; not adopted)
**Principle, the same for all four.**
- A JUDIS typed-text rendition is officially hosted and well evidenced for **identity**.
- Its **fidelity** to the signed judgment is unknown.
- Its database, headnote and editorial matter is **not judgment text**.
- Adopt **(c) as the end state** for PPS Bedi, Ranjit, S N Mukherjee and Navjot alike, with the eight rule-2 elements above.

**Until rule 2 exists, no status change in either direction.**
- Do not add the three drafts.
- Do not demote PPS Bedi.
- Reasons:
  1. Under rule 1, a demotion can only record PPS Bedi as *pending*, which is less accurate than its present documented state (b1 vs b2).
  2. Any demotion depends on O-5.
  3. A promotion of the drafts would expose headnote matter as anchored text.
- **The resulting asymmetry is a frozen-baseline artefact, not a different classification.** One rendition is anchored; three are not. Record it as a known limitation on the PPS Bedi row, and in exports:
  - pinpoints into pp.1-7 are refused;
  - WSB-H-053 needs re-checking;
  - the Cycle 4 description "Historic JUDIS scan" is inaccurate, since the file has no images.

**If the owner finds the asymmetry unacceptable before rule 2:**
- The consistent interim alternative is (b) via a CORRECTION to `AUTHENTICATION_PENDING`. Anchors go 6 → 9 with the other 5 candidates (b2).
- It is reversible later by a CORRECTION to the scoped class.
- It should be taken only after O-5 is decided.

**Option (a) is not recommended.**

**Evidence that would change this recommendation:**
- a registry statement that JUDIS texts are the court's authoritative copies;
- a certified or court-layout copy of any one of the four, which would allow a fidelity measurement;
- for Navjot, a VERIFIED retrieval record and a corrected case record.

## 5. Sources
- `exact_anchor_simulations_c9.json`, `EXACT_ANCHOR_C9.md`
- `judis_scan_c9.csv`, `scr_pinpoint_check_c9.csv`, `citation_completeness_c9.csv` (CC9-02, -11, -23 to -29)
- C8 `SC-T2/JUDIS_CLASSIFICATION_ANALYSIS.md`
- `c9src` `C8-SOURCES/RULE_VERSION_DECISION_PACK_C8.md` (P-D3; Fable RC-03, RR-INFO-02)
- `AUTH-LEDGER/RULE_DECISION_PACK.md` fidelity table; `POLICY_OPTIONS.md` section D
