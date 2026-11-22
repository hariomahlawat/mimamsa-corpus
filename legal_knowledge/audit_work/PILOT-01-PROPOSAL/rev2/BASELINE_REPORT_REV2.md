# PILOT-01 revised assessment (rev2)

**DATABASE ONLY. NO APPLICATION WORK.** As of 2026-11-22. Status: PROPOSED, awaiting owner approval.
Nothing in the originals, source documents, crawler data or earlier batches was modified. No substantive audit has started.
Rev1 (`../BASELINE_REPORT.md`) still stands except where corrected below (`corrections_register.csv`).

Labels used throughout:
- **[V] verified**: checked deterministically or by reading the passage this session, with the locator given.
- **[P] preliminary**: a heuristic or keyword result. It needs agent or advisor confirmation.
- **[A] assumption**: needs owner confirmation.

Files in `rev2/`:
- `source_inventory.csv`
- `mml_structure.json`
- `mml_provision_crosswalk.csv`
- `corrections_register.csv`
- `missing_records_register.csv`
- `missing_relationships_register.csv`
- `unresolved_questions_register.csv`
- `PROPOSED_AGENT_mml-source-auditor.md`

The build script is `build_v2.py` in this folder. Running it needs the MML text, which is not committed (see §2).

## 1. Source inventory: access vs examination

| Source | Count | Access | Examined? |
| --- | --- | --- | --- |
| MML originals | 8 | **Full bytes [V].** Rebuilt from the base64 transfer parts still in the history of `legal-knowledge/v2.5-staging` (commit `0240341^`). ZIP SHA `9d82b9c5…` matches the upload receipt, and all 8 file SHA-256 values match the manifest. | Structure profiled for all 8. Targeted passages read (listed in §2). **Not read in full.** |
| KB records | 658 | Full | Inventoried and hashed; about 30 read in full. **0 legally verified.** |
| Curated cases | 53 | Full | Inventoried and hashed. **Holdings not examined.** |
| Judgment corpus | **4,259** (Delhi HC 1,957; P&H HC 1,215; J&K HC 410; SC 368; Allahabad HC 309) [V] | Manifest only (`raw-data@ad77758`; 1,312,382 bytes, same as the HF size) | Counts only. Includes 1,035 borderline and 47 not-checked judgments (from PROGRESS.md). **0 AFT judgments [V].** |
| Statutes in corpus | 23 acts; 11 split into section records | Metadata | Army Rules r.23(3) passage read [V] |
| Rules / regulations | 15 / 6 | Listed | Inventoried only |
| Gazette notifications | 16 (AFT benches only) | Listed | **No Army Act/Rules S.R.O. or amending Act originals held [V]** |
| Prior batches | about 25 folders | Read | Read as leads only; not re-verified |
| Golden test set | 0 | — | Not supplied |

Missing from the corpus [V]:
- Regulations for the Army 1987
- Air Force Rules 1969
- Pension Regulations for the Army
- Entitlement Rules 1982, 2008 and 2023
- ISO Act 2023 and ISO Rules 2025 (cited by KB-001 and KB-021)
- AFSPA 1958 (only the MML Part III copy exists)
- The Constitution
- Act 37 of 1992
- The S.R.O.s for the Army Rules
- Rule-level records for the Army Rules (only Acts are split into sections)

## 2. MML coverage and source-to-record cross-reference

**Structure and versions [V]** (`mml_structure.json`)

| File(s) | What it is | Latest year in text* | Version relationship |
| --- | --- | --- | --- |
| MML 1.doc | Part I commentary. 8 chapters: origin; outline of AA; arrest and investigation; courts-martial; evidence; civil offences; aid to civil power; service privileges | 1976 | Single copy |
| MML 2.pdf (339 pp, iText 2012) | **Army Act and Army Rules combined**, with notes and appendices (forms, specimen charges). The v2.3 inventory calls it "Army Act" only (COR-001). | 2008 | A distinct edition. About 91% of the vol 2 AA text appears in it. |
| vol 2(AA) .doc / .pdf | Army Act with notes; 16 chapters, 172 notes blocks | 1993 | **99.7% the same**: the PDF was produced from the DOC (Word 2010, Mar 2017) |
| vol 2(AR) .doc / .doc-1 | Army Rules with notes; 159 notes blocks | 2000 | **Two revisions** (95.5–97.7% overlap). DOC-1 adds the arrangement table. |
| vol 3 .doc / .pdf | Part III: about 18 other enactments (AFSPA Ordinance 1942 and Act 1958, Emergency Duties Act 1947, Disposal of Private Property Act/Rules, Assam Rifles Act 1941, Bankers' Books Evidence Act, **Indian Evidence Act 1872**, MNS Ordinance, **Official Secrets Act 1923**, IPC extracts, Soldiers (Litigation) Act/Rules, TA Act/Rules, Tolls Act 1901, Unlawful Activities Act 1967) | 1990 | **99.3% the same** |

\*The latest year in the text is a proxy, not an edition date. No edition statement or correction-slip list was found (UQ-02).

- **Case law [V]:** the manuals contain almost no case citations. Only one was detected: AIR 1976 SC 1797 in Part I. The judicial layer must therefore come from the corpus and the 53 cases, not from the MML.
- **Out of date [V]:**
  - **No mention of the AFT Act 2007 or of BNS/BNSS/BSA in any MML file.**
  - Part I Ch. II para 13 describes AA s.75 field punishment as live law. The vol 2 AA copies mark ss.75, 76 and 127 "Omitted" (Act 37 of 1992, w.e.f. 6-9-1992 per its footnotes).
  - Part III reproduces the IEA 1872 and IPC (including s.124A), both now replaced.
- **Rule 23(3) [V]:** "You are **not** obliged to say anything" appears in MML 2.pdf p.152, AR .doc and AR .doc-1. The corpus Army Rules (India Code bitstream `48f52219…`, text line 1785) reads "You are obliged to say anything". These are a third and a fourth copy; all are secondary or compilations. **This does not resolve the Gazette question (UQ-01).**
- **Access markings [P]:** no document marking was detected in the extracted text; the hits were ordinary prose. Covers and watermarks were not inspected visually (UQ-03).

**Cross-reference to records [V unless marked]**
- **No KB record cites an MML file, page or paragraph** (REL-01). The only MML-to-record links are 79 regex candidates for AR 22, 23 and 180 (v2.5).
- In `mml_provision_crosswalk.csv`, the MML vol 2 copies give 187–191 Act sections and 194–198 Rules. Of those that are present, **93 Act sections and 154 Rules have no citing KB record** [P, heuristic citation parser].
- The largest uncited blocks:
  - Ch VI offences (ss.38–56)
  - ss.89–100
  - ss.166–190 (execution of sentences, pardons, remissions)
  - AR ~41–176 (court-martial and SCM trial procedure)
- The `OMITTED_BUT_CITED` flags (s.127, AR 25) mark records that correctly *discuss* an omission. They are not errors.

The MML text extracted for this assessment is held only in the session scratchpad. It is not committed, pending a rights and access-marking decision (UQ-03).

## 3. Record coverage and missing subjects

The 658 records concentrate on these areas:
- CoI and Rule 180
- Hearing of charge and Summary of Evidence (Rules 22–24)
- AFT forum and limitation
- Pensions
- The civil-military interface and the 2024 transition
- Evidence

The missing-subject candidates are in `missing_records_register.csv`. Each gives the legal relevance, the authority to verify, related records and MML coverage:

| Gap | Subject | Label |
| --- | --- | --- |
| GAP-01 | Substantive military offences (AA Ch VI) | [P] |
| GAP-02 | Court-martial trial procedure | [P] |
| GAP-03 | SCM procedure rules | [P] |
| GAP-04 | Execution of sentences, suspension, pardon, remission | [P] |
| GAP-05 | Deductions and collective fines | [P] |
| GAP-06 | Regulations for the Army | [P] |
| GAP-07 | Service privileges and Soldiers (Litigation) Act | [P] |
| GAP-08 | Aid to civil power under BNSS | [P] |
| GAP-09 | Air Force Act, Navy Act and ISO cross-service law | [P] |
| GAP-10 | Official Secrets Act, Disposal of Private Property, TA Act | [P] |
| GAP-11 | Agniveer | [A] |
| GAP-12 | AFT case law | [V] |

A zero keyword hit is not proof that a subject is absent. Each gap needs confirmation before any new record is drafted.

## 4. Revised responsibilities of the seven agents

Six agents are defined. **I propose a seventh, `mml-source-auditor`** (draft in `rev2/`; it is **not installed**), because no current agent owns MML structure, edition lineage or completeness. If you count me (the lead orchestrator) as the seventh, say so and I will drop the proposal.

| Agent | Owns | Must not |
| --- | --- | --- |
| statutory-auditor | Current and historical official text, amendment chain, commencement, Gazette; r.23(3) recorded as CONFLICTING only | Use the MML as proof of law |
| judgment-auditor | 53 case rows, linked judgments, holdings, later treatment; sampled relevance check of borderline corpus judgments | Rely on headnotes or commercial databases |
| procedure-auditor | Disciplinary and administrative step-to-authority chains | Write commander checklists |
| cross-volume-auditor | Contradictions and duplicates across the 9 families (e.g. the REL-07 overlaps) | Resolve conflicts by majority |
| **mml-source-auditor (new)** | MML index, version diffs, MML↔statute↔KB crosswalk, outdated-material and missing-subject registers | Treat the MML as current law |
| database-validator | Hashes, schemas, the hashed page-marked **derived text layer** (the other agents have no Bash and cannot read DOC/PDF), corpus deduplication and manifest checks, register validation | Judge legal correctness |
| independent-reviewer | Blind first pass on the assigned IDs, then adversarial review of all P0/P1 findings and the controls | Endorse a finding without its own retrieval |

**Independence safeguards (new)**
1. The blind reviewer runs in a separate git worktree pinned to a commit that has no `findings/` folder. Its prompt contains only the record IDs and source pointers.
2. A review that SUPPORTS a finding must cite at least one source the reviewer retrieved itself (own `source_id`, `retrieved_on`, SHA). I propose a validator rule to enforce this.
3. Every agent runs on the same model family, so their errors may be correlated. This limitation is logged in every review. The human legal advisor samples the blind results.
4. The same evidence standard applies whatever the origin of the content: original records, MML text and agent output are all checked the same way.

**Coverage check.** Every domain now has an owner:
- Statutes: statutory-auditor
- Rules and regulations: statutory-auditor and procedure-auditor
- MML: mml-source-auditor
- 53 cases: judgment-auditor
- Judgment corpus: database-validator (deduplication and metadata) and judgment-auditor (relevance sample)
- Gazette: statutory-auditor
- Pensions: judgment-auditor and statutory-auditor
- Administrative action: procedure-auditor
- Cross-volume: cross-volume-auditor
- Completeness: mml-source-auditor and cross-volume-auditor

## 5. Pilot: the same 25 KB record IDs, plus two companion packets

The 25 IDs and their hashes are unchanged from rev1 (`../pilot-selection.json`); they already exercise the MML-heavy provisions:
- **Statutory:** HCE-010, CM-013, HCE-017, CIV-033, CM-025, EV-002
- **Procedure:** HCE-004, COI-025, CM-011, ADM-009, AFT-011
- **Judgment:** KB-026, PEN-043, CIV-019, KB-028, PEN-J-01
- **Command authority:** KB-003, CM-003, COI-008, CIV-008
- **Cross-volume:** EV-016, CIV-034, AFT-004
- **Controls:** V9-CL-02, COI-039

Two packets are added; neither counts toward the 25:
- **MML packet (12 provisions).**
  - AR 22, 23(3), 25, 180, 182
  - AA ss.75–76, 80–82, 122, 125–126, 127
  - Part I Ch. II paras 13–14
  - Each traced MML (every version) → official text → KB records → judgments.
- **Completeness probes (2):** GAP-01 (offences) and GAP-04 (sentences, pardons). These test whether the gap is real and what records it would need.

The 6 linked case rows stay as before.

## 6. Major unresolved legal and source-authentication risks

1. **P0, Rule 23(3):** the government copies and the manuals disagree, and the original S.R.O. 484 is not held.
2. **P1, amendment chain:** none of the amending instruments for the Act or the Rules is held (Act 37/1992, S.R.O. 17(E)/1993, 258/2002, 17(E)/2019).
3. **P1, MML editions:** the editions are undated and 15–50 years old. Rights and markings are unassessed.
4. **P1, record citations:** the 76 internal source IDs are undefined, so no KB citation can be traced.
5. **P1, case authentication:** 11 rows are citation-only and 8 lack official byte parity; later treatment is incomplete.
6. **P1, corpus gaps:** Regulations for the Army and AFT judgments are missing; 1,082 judgments are unresolved in relevance.
7. **P1, earlier evidence:** Indian Kanoon and Legitquest were used as evidence.
8. **P2, completeness:** the subject gaps in §3.

## 7. Recommended next stage and acceptance criteria

**Before the pilot starts:**
- Advisor decisions on AQ-01, AQ-02, AQ-07, AQ-10 and AQ-11 (rev1).
- Owner decisions on UQ-03 (whether MML-derived text may be committed to the private repo or HF), UQ-07 (scope) and UQ-08 (agent count and volume mapping).

**Stage 1 (pilot):**
- database-validator builds the hashed, page-marked derived text layer for the MML and the pilot statutes.
- Then come the first pass, the blind review and the advisor disposition, as set out in rev1 §4 with the seventh agent added.

**Acceptance criteria.** Rev1 §6 applies, plus:
- Every MML-sourced statement is tagged SECONDARY, edition-specific and file-SHA-specific.
- 100% of the 12 MML packet provisions are traced across every version present, and any version differences are logged.
- Each of the four registers holds evidence-backed entries, with no proposed addition lacking an authority.
- 0 claims of current law rest on the MML alone.
- Both completeness probes are resolved as confirmed gap, false gap or needs advisor.

## Recommendation

**Conditional GO for the controlled 25-record pilot. NO-GO for the full audit or for any claim that the database is complete.**

The source inventory is now complete enough to *run* the pilot. Every source class is accounted for, its access and examination status is explicit, the MML bytes are verified, and the gaps are registered.

The database itself is **not** complete: Gazette originals, Regulations for the Army, AFT case law and whole statutory subject areas are missing. Those gaps will appear in the pilot as NOT_FOUND or BLOCKED results; they will not be papered over.

Start once the advisor and owner pre-decisions above are recorded.

**DATABASE ONLY. NO APPLICATION WORK.**
