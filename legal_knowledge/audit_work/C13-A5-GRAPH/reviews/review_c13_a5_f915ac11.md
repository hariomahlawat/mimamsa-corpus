# Independent review: C13-A5 graph, branch `claude/c13-a5-graph` at `f915ac11`

**Reviewer:** an independent AI agent. It is not the author, and this is an AI documentary check, not legal validation.
**Date:** 2026-11-25
**Mode:** read-only. Nothing was committed, nothing was written to HF, and no worktree file was changed.

Working files are in this folder:
- `scripts/`;
- `treatment_sample.jsonl` and `treatment_sample_verdicts.csv`;
- `page_image_reconfirmation.csv` and `text_sample_result.csv`;
- `identity_check.txt`;
- `checks_fast.log`, `treatment_check.log` and `pytest.log`;
- `img/`, the rendered pages.

## Verdict

**ACCEPT WITH CONDITIONS. No P1 findings. Four P2 findings, all in the treatment layer and the data contract.**

These parts are sound and can be relied on as stated:
- the SC case-number overlay;
- the HF overlay `844383f5`;
- the identity overlay;
- frozen-record preservation;
- restricted-material exclusion.

The treatment candidate layer has three problems:
- **What is sound.** OVERRULES and DISAPPROVES are conservative and correct in type, direction and voice.
- **What is overstated.** The in-sample precision figures overstate quality for DISTINGUISHES, APPLIES, EXPLAINS and DOUBTS. They must not be shown as measured precision.
- **What does not import.** The graph export does not match Track B contract v1.

## 1. Reproduction

| Check | Result |
| --- | --- |
| `scnum_reconfirm_c13.py --check` | OK, 3 outputs byte-identical |
| `identity_c13.py --check` | OK, 2 outputs |
| `treatment_c13.py --check` | OK, 4 outputs |
| `graph_c13.py --check` | OK, 6 outputs, schema-validated |
| `hf_overlay_c13.py --check` | OK |
| `package_c13.py --check` | OK |
| pytest: C13 graph tests plus `test_legal_audit_c12_research_isolation.py` | 38 passed (32 C13 and 6 isolation) |
| `test_legal_audit_c6_provenance.py` (frozen hashes) | 24 passed |

**Frozen records.** These hashes were recomputed and are unchanged:
- `records_658`: `9a8f0d19…`
- `cases_53`: `8b8d53cd…`
- CALIBRATION-02 register: `cfe5f408…`

**Scope of the change.** `git diff a4c0c382..f915ac11` touches only `legal_knowledge/audit_work/C13-A5-GRAPH/` and three new test files.

**Counts.** The counts reproduce: 13,406 nodes, 44,961 candidate edges and 173 reviewed edges. There are 0 APPLIES_PROVISION edges and 0 High Court OVERRULES edges. All 11,015 CITES_PROVISION edges have `legal_effect=false`.

## 2. SC case numbers

**Source bytes.** I extracted all 94 distinct PDFs behind the 99 records from `/home/user/c7` at `ad77758d`. Every file's sha256 equals its staged value.

**Page-image readings.** I rendered and read all 18 page-image records myself (17 distinct PDFs). **All 18 are RECONFIRMED** (`page_image_reconfirmation.csv`).
- CA-2450-1992 is printed as "Civil Appeal Nos. 2449 and 50 of 1992" (PDF p.3). Reading the elided "50" as 2450 is reasonable: the judgment arises from two CAT O.A.s (1513/90 and 1537/90). The author recorded the elision rather than normalising it silently.
- One page reference is wrong. For 2016insc173 the reconfirmation CSV gives anchor page 11, but the Diary numbers are printed on PDF p.12 (F09).

**Text-layer readings.** I checked a seeded sample of 22 of the 81 (seed 20261125). **22/22 are RECONFIRMED**, with an independent parser.
- In 3 cases my automatic match missed and I resolved them by hand:
  - a range "1603-1609 of 2021";
  - an OCR "I999", confirmed by page image as 1999;
  - the 745-number 2024 list, where all 745 were found after re-parsing the "Case Arising From" block.
- This check confirms that each staged value is printed. It does not confirm that the list is complete. For example, Union Carbide's lead appeal, CA 3187-88/1988, is printed but not staged (F07).

**Unreviewed candidates.** None of the 266 `APPLY_CANDIDATE_UNREVIEWED_CONFIRMED` rows or the `UNRESOLVED` rows (C11 `SC_CASE_NUMBER_REVIEWED_STATUS.csv`) appears in the C13 overlay. The 99 overlay records are:
- 73 REVIEWED_CORRECT;
- 22 USE_REVIEWER_READING;
- 4 RECHECK_LOWER_COURT_TYPE.

Their overlay values are identical to the C12 staged `proposed_value`.

## 3. HF overlay `844383f5`

- The revision resolves. Its parent is `3864faf3`. HF head has since moved to `9e3cf986`.
- File list:
  - 16,041 files at the parent and 16,044 at `844383f5`;
  - 0 removed;
  - 3 added, all under `data/meta_overlays/`.
- No blob that the two revisions share was changed.
- The `data/meta` tree has 4,345 entries at both revisions, and they are identical.
- I re-downloaded the 3 files at `844383f5`. `sha256sum -c c13_2026-11-25_SHA256SUMS` passes, and the files are byte-identical to the staged copies in git.
- All 99 rows carry:
  - status `METADATA_OVERLAY_ORIGINAL_UNCHANGED`;
  - verification `AI_DOCUMENTARY_RECONFIRMATION_NOT_LEGAL_VALIDATION`;
  - scope `METADATA_ONLY_NO_EVIDENCE_OR_AUTHENTICATION_STATUS_PROMOTED`.
- No row carries an evidence-class, authentication or ledger field.

## 4. Treatment edges

**Sample.** I drew 54 candidate edges, seeded (13405) and stratified by type: FOLLOWS 14, CONSIDERS 12, DISTINGUISHES 6, APPLIES 4, and all of EXPLAINS 4, DOUBTS 1, OVERRULES 9 and DISAPPROVES 4. Where the passage alone was not enough, I read it in the `ad77758d` text.

| Type | n | Type correct | Fully correct (type, direction, own voice, target) |
| --- | --- | --- | --- |
| FOLLOWS | 14 | 14 | 12 |
| CONSIDERS | 12 | 12 | 9 |
| DISTINGUISHES | 6 | 2 | 2 |
| APPLIES | 4 | 4 | 1 |
| EXPLAINS | 4 | 0 | 0 |
| DOUBTS | 1 | 0 | 0 |
| OVERRULES | 9 | 9 | 9 |
| DISAPPROVES | 4 | 4 | 3 |
| **All** | 54 | 45 | 36 |

Compare the author's in-sample figures: FOLLOWS 32/33, DISTINGUISHES 10/11, APPLIES 1/1.

**Error classes**

- **Quoted voice or submission recorded as the court's own voice (F02):** T09, T21, T23, T24, T34, T35 and T41. T41 is the only DOUBTS edge: Shayara Bano's "McDowell is per incuriam", quoted in the Aadhaar judgment.
- **Wrong binding (F03):**
  - footnote-number binding: T13 and T36;
  - another court's treatment reported as this court's: T28 and T32;
  - cue whose subject is not the authority: T27, T30 and T40.
- **EXPLAINS semantics.** All 4 edges are "principle explained in X". There, X explains a principle; the citing court is not explaining X. These are CONSIDERS or CITES, not EXPLAINS.
- **Found outside the sample:** GT-00548f05dc231679, "Plaque fissuring and rupture is followed by deposition of thrombus", is typed FOLLOWS.
- **Concentration:** 128 of the 246 candidate FOLLOWS edges come from one Delhi HC 2025 template.

**OVERRULES and DISAPPROVES, all 13 checked individually**
- No OVERRULES edge is inferred from adverse discussion.
- All 9 OVERRULES edges are Supreme Court judgments, in the order of the court or the lead or plurality opinion, with explicit overruling words:
  - Puttaswamy (2017): M P Sharma ×2, Kharak Singh, Bhanudas Krishna Gawde;
  - Joseph Shine: Sowmithri Vishnu, V. Revathi;
  - Mafatlal p.105 ×2, which is a duplicate pair with no identified target;
  - Sriharan: Sangeet.
- The DISAPPROVES edges are correctly declaratory: Parashotam → Shri Kant Sharma (resolved correctly), Ajmer Singh, and Mafatlal p.133 ×2.
- In T51, the disapproval of the "subsequent decisions" is anchored to Kanhaiyalal itself (F08).
- No OVERRULES edge has a resolved target node.

**Anchors.** I checked all 710 treatment edges (candidate and reviewed):
- every passage is found in the `ad77758d` text on the stated page;
- every `source_copy_sha256` equals the data/meta sha256;
- every anchor string (with 3 expected null anchors) occurs in the text.

`passage_sha256` cannot be recomputed for 125 edges because the exported passage is truncated (F06).

**In-sample figures.** `DEV_EVAL_ROWS_C13.csv` recounts to the stated figures: 56 TP, 3 FP, 10 missed, 69 correct rejections and 24 excluded rows.

## 5. Identity overlay

- The scope is the C12 `COPY_VERIFICATION_MANIFEST` rows with `DUPLICATE_IDENTITY`: 128 copies.
- The overlay holds 127 copies. The one missing is the RM-001 copy, withheld deliberately.
- Every C12 (copy, doc_id) pair except the RM-001 pair is present.
- All 439 rows are `copies_kept=ALL` with status `PROPOSED_IDENTITY_OVERLAY_ALL_COPIES_KEPT`. Nothing is deleted, merged or renamed.

I checked 15 seeded groups (`identity_check.txt`). All are plausible as classified:
- SC year-partition duplicates (1977/1978, 1981/1982, 1959/1960): same INSC suffix and bytes;
- HC common judgments (LPA 189 and 254/2010 P&H; 4- and 6-proceeding Delhi HC groups): one proceeding per doc_id;
- Hindi rendition and principal copy;
- schedule as part of an instrument;
- listing page that is not an instrument;
- notifications that are distinct instruments, separated from their parent Act;
- C5 multi-copy source groups.

## 6. Data contract against Track B (`10ae5c04`, `app/contract/`)

The A5 export is internally consistent: its schemas validate and its tests pass. It is **not** importable under Track B contract v1 as it stands (F04). The mismatches are:

| Area | A5 | Track B v1 |
| --- | --- | --- |
| Relations | 9 judicial types plus structural and forms types | CITES_JUDGMENT, FOLLOWS_PROPOSITION, DISTINGUISHES_PROPOSITION, OVERRULES_OR_LIMITS_PROPOSITION, …; no APPLIES, CONSIDERS, EXPLAINS, DOUBTS, DISAPPROVES, DECIDES_PROCEEDING, HAS_PROVISION, STATES_PROPOSITION or RAISES_QUESTION, and no FORM_* except PRESCRIBES_OR_EXEMPLIFIES_FORM |
| Status | REVIEWED_AI_DOCUMENTARY_NOT_LEGAL_VALIDATION; PROPOSED_NOT_APPLIED | DOCUMENTARY_CHECKED needs an `RV-` reviewed_record; a proposal is `capability_restriction=PROPOSAL_NOT_APPLIED` |
| Restrictions | list (CANDIDATE_DATA, UNVERIFIED_MARKER_REQUIRED, NON_OPERATIONAL_RESEARCH_ONLY, HIDDEN_FROM_USERS_THIS_CYCLE) | single enum |
| evaluation_ref | string path#fragment | object with report_commit and human_checked; the UI shows precision |
| Anchor | passage_id `PE-…`, no offsets | `^p\d+-\d+$`, char offsets |
| Extractor | version string | artefact_commit required |
| Nodes | 10 node types | no node record kind |

**Restricted material.** Both sides fail closed and scan all strings against `config/restricted_material.json`. B's `has_legal_effect` rule agrees with A5's `legal_effect` for FOLLOWS, DISTINGUISHES and OVERRULES (true) and for CITES and CITES_PROVISION (false).

## 7. Restricted material (RM-001)

- I scanned every file in the package, with `.gz` files decompressed, for RM-001's source sha256, both derived sha256 values, the doc_id, "RAF2000" and the title.
- **No hit in any data output.** The only hits are:
  - the README's description of the exclusion;
  - a safety assertion constant in `common_c13.py`;
  - the 1961 Regulations for the Air Force, a different edition, which is not restricted.
- The identity overlay withholds the copy.
- No forms node draws on the RAF2000-C7 source.
- The pinned register (`ea282cbd`, sha256 `6732065c…`) is older than the governance head (`72fe7a75`, `fc7ea07e…`). The identifiers are unchanged, but the pin should be refreshed (F05).

## Findings

See `findings_c13_a5_f915ac11.csv`.
- **P2**
  - F01: in-sample precision is not representative.
  - F02: the voice gate admits quotations.
  - F03: binding and subject errors.
  - F04: contract mismatch with Track B.
- **P3**
  - F05: stale register pin.
  - F06: passage hash on truncated passages.
  - F07: presence check only, not completeness.
  - F08: OVERRULES duplicates and raw targets.
  - F09: minor inconsistencies.
