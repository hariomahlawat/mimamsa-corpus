# C13-A5: judicial treatment and the legal knowledge graph (candidate layer)

**Status.** Candidate data and AI documentary checks only. Nothing here is legally validated. No evidence class, authentication state or AUTH-LEDGER entry was changed (the ledger stays at version 0). **The treatment extractor is FROZEN** (GA3): `treatment-c13/0.9.0-dev` at commit **`e15af208`**, under PROTOCOL_C13 v1.1. The freeze record is `freeze/FREEZE_RECORD_C13_A5.md`. Later commits change only post-freeze tooling, tests and documentation. They do not change the classifier, its rules or the frozen predictions; `test_frozen_tool_hashes_unchanged` guards this.

**Blind GA4 result (H-REL-C13; descriptive only, no owner target).** Source: `RESULTS_C13.md` §1.4 and §4.3, branch `claude/c13-eval`, commit `20a4e55d`.

| Measure | Result |
| --- | --- |
| relation_type precision | **0.340 [0.161, 0.560]** weighted; 58/176 unweighted |
| target precision | 0.620 [0.467, 0.758] |
| Coverage | weighted 0.26; unweighted 0.50 |
| `follows` recall | **0.032** (5/154) |
| `distinguishes` identified | 0/53 |
| Dominant error | units the coders labelled `follows` (69) or `distinguishes` (31) predicted as `cites` |
| Without PRIMARY and the 4 author-exposed judgments | 0.341 |

**What the result means.** The frozen extractor rarely captures treatment.
- Every FOLLOWS and OVERRULES edge, in the native graph and in the contract-v1 export, stays an **unverified candidate**.
- The absence of a treatment edge says nothing about how the cited decision was treated.

**Review.** An independent review of `f915ac11` returned ACCEPT WITH CONDITIONS (`reviews/`, copied unchanged). This revision addresses its P2 findings F01-F04 and its P3 findings F05, F06, F08 and F09. F07 is addressed in wording (`scnum/ERRATA_C13.md`).

Branch `claude/c13-a5-graph`. Inputs are pinned: text and metadata at raw-data commit `ad77758d` (read as git objects from `/home/user/c7`), C10/C11/C12 audit files at staging `a4c0c382`, and HF corpus revision `3864faf3`.

## Deliverables

| # | Deliverable | Where | Tool (`--check`) |
| --- | --- | --- | --- |
| 1 | Graph schema and native data format (the earlier "IC-01" outline is superseded for import by Track B contract v1; see 1a) | `schema/graph_node.schema.json`, `schema/graph_edge.schema.json`, this README, `graph/IC01_EXPORT_MANIFEST.json` | n/a |
| 2 | Passage-level treatment extraction | `treatment/` | `tools/treatment_c13.py` |
| 3 | Identity-resolution overlay for duplicate legal identities | `identity/` | `tools/identity_c13.py` |
| 4 | Reconfirmation of the 99 staged SC case-number corrections, the overlay, and the HF application | `scnum/`, `hf/` | `tools/scnum_reconfirm_c13.py`, `tools/hf_overlay_c13.py` |
| 5 | Candidate graph (native) | `graph/` | `tools/graph_c13.py` |
| 5a | Track B contract v1 export (review F04) | `contract_v1/` | `tools/contract_v1_export_c13.py` |
| 5b | Re-check of the reviewer's 54-edge sample (F01-F03) | `treatment/REVIEW_SAMPLE_RECHECK_C13.*` | `tools/review_recheck_c13.py` |
| 6 | Packaging | `SHA256SUMS`, tests `tests/test_legal_audit_c13_graph_*.py` | `tools/package_c13.py` |

## Reproduce

```
PY=scratchpad/venv/bin/python        # Python 3.13 with PyMuPDF and jsonschema; tools also need git
$PY -I -B tools/scnum_reconfirm_c13.py --check      # full re-extraction needs PyMuPDF (AGPL; MuPDF 1.28.6); without it: CHECK PARTIAL artefact check (see below)
$PY -I -B tools/identity_c13.py --check
$PY -I -B tools/run_check_c13.py treatment_c13.py --check         # frozen tool: run through the provenance pin; about 4 minutes
$PY -I -B tools/run_check_c13.py predict_hrel_c13.py --check      # frozen predictions reproduce
$PY -I -B tools/treatment_c13.py --dev-only         # in-sample score only; writes nothing
$PY -I -B tools/graph_c13.py --check                # validates every node and edge against the schemas
$PY -I -B tools/review_recheck_c13.py --check
$PY -I -B tools/contract_v1_export_c13.py --check   # pins Track B contract commit 5f4b8071
$PY -I -B tools/hf_overlay_c13.py --check [--online]
$PY -I -B tools/package_c13.py --check
$PY -B -m unittest discover -s tests -p "test_legal_audit_c13_graph_*.py"   # C13_SKIP_SLOW=1 skips the --check subprocess test
```

**Integration notes (post-freeze; pre-integration review A5-01/A5-02).**
- **Register provenance.** `provenance_pin_c13.py` makes the restricted-register provenance label deterministic. When the register bytes hash to the pinned `fc7ea07e…`, the label is always `git:72fe7a75:config/restricted_material.json`, whether the file was read from the worktree or from git. Any other bytes keep their real label, so every `--check` fails loudly. The non-frozen tools apply the pin themselves. The two frozen tools (`treatment_c13.py`, `predict_hrel_c13.py`) are run through `run_check_c13.py`, which applies the same pin without editing them.
- **scnum without PyMuPDF.** `scnum_reconfirm_c13.py --check` prints **CHECK PARTIAL (PyMuPDF absent)**. It skips the PDF text-layer re-extraction and the text-layer matching. It still verifies the 99 overlay rows against the pinned C12 input, the reconfirmation verdicts and page-image coverage, the overlay hash against the HF staged manifest, and (when `/home/user/c7` exists) the PDF byte hashes.
- **Test skips.** Tests that need `/home/user/c7` or jsonschema skip with an explicit reason when those are absent.

Order of a full rebuild: scnum, identity, treatment, graph, review_recheck, then commit the tools (the contract export records each extractor's artefact commit), then contract_v1_export and package. The `.gz` outputs are gzip with mtime 0. `--check` compares their decompressed content. Standard library only, except PyMuPDF (scnum) and jsonschema (validation, optional in the build, used by the tests).

## Restricted material

`config/restricted_material.json` (RM-001) is read from the worktree when present. Otherwise it is read from governance commit `72fe7a75` (`claude/c13-gov` head; re-pinned from `ea282cbd` after review F05, sha256 `fc7ea07e…`; RM-001 identifiers unchanged) as a git object. Its sha256 is recorded in every summary.
- The FOUO Regulations for the Air Force 2000 copy (`4284820e…`) and its derived text and metadata (`regs-regulations-for-the-air-force-reprinted-edition-2000`) are excluded from every node, edge and export.
- `graph_c13.py` fails the build if any restricted sha256 or doc_id appears in its serialised output. The identity overlay withholds that one copy and counts it.
- A test scans every output file in this package.

## 1. Native graph format (schemas; superseded for Track B import by contract v1, section 1a)

### Nodes

`schema/graph_node.schema.json`. Every node has these fields:
- `node_id`, `node_type`, `label`;
- `source_copy_sha256[]`, every byte copy behind it;
- `anchor`;
- `extractor_version`;
- `verification_axes`, axis-qualified per Architecture §6;
- `evaluation_ref`, `restrictions`, `attributes`.

| Type | id | Source | Notes |
| --- | --- | --- | --- |
| INSTRUMENT | `INS:<C11 instrument id>`, `INS:<C10 I-id>`, `INS:NAME:<slug>` | C11 statute links, C10 amendment graph, forms registry | The mapping from instrument to source copy is not established in this build (`copy_mapping`) |
| PROVISION | `PROV:<instrument>:<unit>` | C11 normalised provision ids | `provision_version` = NOT_ESTABLISHED |
| PROVISION_VERSION | `PV:<provision_id>@<valid_from>` | interface only | 0 nodes. The A4 branch has no commits, and no evidenced ProvisionVersion dataset exists. A4 rows can attach here without a schema change |
| JUDGMENT | `JUD:<C10 rendition group>` | data/meta judgments and orders, C10 JUDGMENT_RECONCILIATION | Hash ≠ judgment: copies are listed. Doc_id aliases come from the identity overlay |
| PROCEEDING | `PROC:<court>\|<case number>` | metadata `case_numbers` + SC overlay C13-v1 | Connected proceedings (common judgments) are flagged on DECIDES_PROCEEDING |
| QUESTION_OF_LAW, PROPOSITION | `QL:`/`PROP:<C12 item id>` | C12 holdings (`question_of_law`, `holding` items only) | NON_OPERATIONAL_RESEARCH_ONLY and HIDDEN_FROM_USERS_THIS_CYCLE (C11 F06/F07) |
| FORM, COMPETENT_AUTHORITY, PROCEDURE, ADMINISTRATIVE_REQUIREMENT | `FORM:`/`AUTH:`/`PROCEDURE:`/`REQ:` | C12 forms registry, values **as printed** (placeholders such as "(n/a)" and "As printed in the form" are skipped) | NON_OPERATIONAL_RESEARCH_ONLY (WSG-R04) |

### Edges

`schema/graph_edge.schema.json`. Every edge carries:
- `edge_type`, `edge_class`, `source`, and `target` (or `target_raw` when only raw text is known);
- `direction`, read in plain language;
- `court`, `date`;
- `evidence`: source copy sha256, doc_id, page, paragraph, passage, passage sha256 and anchor text;
- `extraction_method`, `extractor_version`;
- `verification_state` and `verification_axes`;
- `legal_effect`, `reviews[]`, `evaluation_ref`, `restrictions`, `attributes`.

**Edge types.**

| Group | Types |
| --- | --- |
| Judicial | CITES, FOLLOWS, APPLIES, DISTINGUISHES, CONSIDERS, EXPLAINS, DOUBTS, DISAPPROVES, OVERRULES |
| Statutory reference | CITES_PROVISION (mention), APPLIES_PROVISION (application) |
| Amendment | AMENDS_PROVISION_VERSION, SUBSTITUTES_PROVISION_TEXT, INSERTS_PROVISION, OMITS_PROVISION, REPEALS_INSTRUMENT, COMMENCES, SAVES_OR_TRANSITIONS, IMPLEMENTS, AMENDMENT_GRAPH_ENTRY_UNTYPED |
| Structure | DECIDES_PROCEEDING, HAS_PROVISION, RAISES_QUESTION, STATES_PROPOSITION |
| Forms | PRESCRIBES_OR_EXEMPLIFIES_FORM, FORM_COMPETENT_AUTHORITY, FORM_PROCEDURE, REQUIREMENT_FROM_SOURCE |

**Verification states.**

| State | Meaning |
| --- | --- |
| `AUTOMATED_CANDIDATE_NOT_VERIFIED` | Default |
| `PROPOSED_NOT_APPLIED` | C10 amendment-graph entries that are not EVIDENCED |
| `REVIEWED_AI_DOCUMENTARY_NOT_LEGAL_VALIDATION` | Only where an independent C11 review row confirmed this exact edge (target correct, or treatment SUPPORTED with the same type family). This is an AI documentary check, never legal validation |

**Contract rules enforced by schema, build and tests.**
- OVERRULES, DISAPPROVES, DOUBTS and every amendment type are **always candidates**. They never go in `edges_reviewed.jsonl`.
- **OVERRULES requires all of the following:**
  - explicit overruling words ("overrule(d)", "stand(s) overruled");
  - the court's own voice, bound to the authority;
  - a Supreme Court judgment;
  - not a separate or dissenting opinion;
  - not a plea, objection or argument;
  - not a question or a negation;
  - not a report of another decision.
  It is never inferred from criticism, adverse discussion or distinguishing.
- **Declaratory wording without "overrule"** ("does not lay down the correct law", "wrongly decided", "not in agreement with") becomes DISAPPROVES with `overruling_language = DECLARATORY_ONLY_NOT_EXPLICIT_OVERRULING`.
- **High Court overruling words** are not routed, because competence and bench strength are not established. This matches the C11 probe and the v13 review finding.
- **Statutory citation is separate from applicability.** Every statute mention is CITES_PROVISION with `applicability = NOT_INFERRED` and `legal_effect = false`.
  - There are **0 APPLIES_PROVISION edges**: C11 withdrew PROVISION_APPLIED, and no reliable extractor distinguishes application from mention.
  - The C11 label (PARTY_INVOKED, CHARGED_OR_CONVICTED_UNDER and so on) is kept in `attributes.link_label`.
- Every edge other than CITES, CITES_PROVISION, DECIDES_PROCEEDING and HAS_PROVISION carries `UNVERIFIED_MARKER_REQUIRED` (B8 label test).
- Citation, treatment and statutory edges must carry a 64-hex copy sha256, an integer page and a passage.
- **Absence of an edge never means absence of adverse authority.** This is stated in the manifest and in the evaluation file.

### Export files (`graph/`)

| File | Content |
| --- | --- |
| `nodes.jsonl.gz` | Nodes |
| `edges_candidate.jsonl.gz` | Candidate and proposed edges |
| `edges_reviewed.jsonl` | Reviewed edges |
| `EDGE_TYPE_EVALUATION_C13.json` | Per type: `displayable_measured_precision` (null for every type, because no figure is human-checked and independent of the current extractor), the development/in-sample counts (`displayable: false`), and the independent AI review figures for the f915ac11 version. Each edge's `evaluation_ref` points into it |
| `GRAPH_SUMMARY_C13.json` | Counts and input hashes |
| `IC01_EXPORT_MANIFEST.json` | Schema hashes, file sha256 (uncompressed content), pins (text commit, HF revision, HF overlay commit) and semantics |

A Track B release pins the git commit containing the manifest.

### Counts (this build)

13,406 nodes.

| Node type | Count |
| --- | --- |
| JUDGMENT | 3,950 |
| PROCEEDING | 5,552 |
| PROPOSITION | 2,325 |
| PROVISION | 1,008 |
| QUESTION_OF_LAW | 258 |
| INSTRUMENT | 101 |
| COMPETENT_AUTHORITY | 75 |
| FORM | 67 |
| ADMINISTRATIVE_REQUIREMENT | 36 |
| PROCEDURE | 34 |

44,997 edges: 44,826 candidate or proposed, and 171 reviewed (AI documentary).

| Edge type | Total | Reviewed (AI documentary) | Reliability |
| --- | --- | --- | --- |
| CITES | 23,222 | 69 | |
| CITES_PROVISION | 11,076 | 61 | |
| DECIDES_PROCEEDING | 5,555 | 0 | |
| STATES_PROPOSITION / RAISES_QUESTION | 2,325 / 258 | 0 | research-restricted |
| HAS_PROVISION | 1,008 | 0 | |
| CONSIDERS | 272 | 0 | candidate |
| FOLLOWS | 257 | 31 | candidate; 159 of 257 come from one Delhi HC 2025 template ("covered by ... Gawas Anil Madso", F09) |
| DISTINGUISHES | 25 | 9 | **LOW_RELIABILITY_CANDIDATE** |
| APPLIES | 7 | 1 | **LOW_RELIABILITY_CANDIDATE** |
| OVERRULES | 8 | 0 (always candidate) | candidate |
| DISAPPROVES | 4 | 0 (always candidate) | candidate |
| EXPLAINS | 0 | – | **LOW_RELIABILITY_CANDIDATE** |
| DOUBTS | 0 | – | **LOW_RELIABILITY_CANDIDATE** |
| APPLIES_PROVISION | 0 | – | |
| Amendment (C10 graph, 99 entries) | 99 | 0 (82 PROPOSED_NOT_APPLIED) | |
| Forms (4 types) | 881 | 0 | research-restricted |

`LOW_RELIABILITY_CANDIDATE` appears in both `restrictions` and `attributes.reliability`, so consumers can filter these edges out. They are not exported under contract v1. The full breakdown by type and state is in `graph/GRAPH_SUMMARY_C13.json`.

**The 8 OVERRULES candidates.** The two Mafatlal p.105 lead rows were merged (F08).
- Puttaswamy (2017) pp.167, 275, 276 and 432;
- Joseph Shine p.74 (×2: Sowmithri Vishnu and V. Revathi, each with its anchor citation appended to the raw target);
- Mafatlal p.105 ("decisions of this Court saying to the contrary"; raw target only);
- V. Sriharan p.99 ("we specifically overrule", Sangeet).

None has a resolved target node. Raw targets carry `binding = RAW_TARGET_ONLY_BINDING_NOT_ESTABLISHED`, and leading word fragments are cleaned. An adviser must confirm every one.

**DISAPPROVES (declaratory):**
- Parashotam (2023) p.17 → Shri Kant Sharma, resolved;
- Ajmer Singh p.9;
- Mafatlal p.133 ×2. One of these is now targeted at "the subsequent decisions ... following Kanhaiyalal" as raw text, not at Kanhaiyalal (F08 / T51).

**Evidence anchors (F06).**
- `evidence.passage` is the exported text (≤600 characters), and `passage_sha256` hashes exactly that text.
- Treatment edges also carry `char_start`/`char_end`. These are page-relative offsets into `data/text/<doc_id>.txt` at `ad77758d`, counted from the character after the `[[page N]]` marker. They come with `passage_full_sha256` (the whitespace-collapsed full passage) and `passage_truncated`.

### 1a. Track B contract v1 export (`contract_v1/`, review F04)

`candidates_graph_edges.jsonl.gz` holds 34,567 v1 `candidate` records (`candidate_type = graph_edge`), conforming to `app/contract/` at `claude/c13-b-app` head `5f4b8071`. That is revision R2, with optional span binding on `page_anchor`; the candidate schema is unchanged since R2. B's own validator (`python -m mimamsa_contract record candidate`) accepts every record with **0 errors and 0 warnings**. `tests/test_legal_audit_c13_graph_contract_v1.py` re-runs it from a `git archive` of the pinned commit.

| A5 type | v1 relation | Records | capability_restriction |
| --- | --- | --- | --- |
| CITES | CITES_JUDGMENT | 23,222 | NONE_RECORDED |
| CITES_PROVISION | CITES_PROVISION | 10,936 | NONE_RECORDED |
| CITES_PROVISION (label PROVISION_QUOTED) | QUOTES_PROVISION | 140 | NONE_RECORDED |
| FOLLOWS | FOLLOWS_PROPOSITION | 257 | NON_OPERATIONAL_RESEARCH_ONLY |
| OVERRULES | OVERRULES_OR_LIMITS_PROPOSITION | 8 | NON_OPERATIONAL_RESEARCH_ONLY |
| DISAPPROVES | OVERRULES_OR_LIMITS_PROPOSITION | 4 | NON_OPERATIONAL_RESEARCH_ONLY. The id prefix `a5.disapproves.` marks declaratory wording, not explicit overruling |
| CONSIDERS | none in v1 | not exported (272) | – |
| DISTINGUISHES, APPLIES, EXPLAINS, DOUBTS | LOW_RELIABILITY_CANDIDATE | not exported (32) | – |
| Amendment, forms, structural, holdings | no page anchor in a source copy, or another workstream's record kind | not exported | – |

**Fixed fields on every record.**
- `status = AUTOMATED_CANDIDATE_NOT_VERIFIED` and `review_ref = null`: there are no RV- reviewed_records, and AI documentary reviews of C11 rows are not reviews of this extractor's commit.
- `confidence = extracted`.
- `evaluation_ref = null`, so the UI shows "not evaluated" (F01).
- `extractor.artefact_commit` is the last commit of the extractor tool.

**Anchors.**
- Treatment rows bind their span with `pipeline_name = corpus-data-text`, `pipeline_version = ad77758d` and `derivative_text_sha256` = sha256 of `data/text/<doc_id>.txt`, using the offsets above. B's derived_text import must use the same page-relative convention, or the span falls back to page-only, as the contract specifies.
- Citation and statute rows are page-only anchors, with the C11 excerpt as the quote.
- Targets are A5 node ids (`JUD:…`) or a raw reference.
- The native `graph/IC01_EXPORT_MANIFEST.json` name is historical. Track B should import `contract_v1/`.

## 2. Treatment extraction (`treatment/`)

**Method.**
- **Passages.** One per C11 citation-graph anchor in the judgment body (23,222 edges), plus every C11 treatment-candidate passage (2,595), located in the full text. Cues that share a sentence are merged (V13-04).
- **Voice gate, revised for F02.**
  - Quotation is tracked **across paragraphs and pages**:
    - an unclosed curly quote within 6,000 characters;
    - reproduction lead-ins ("reproduced hereinbelow:", "reads as under:", "observed as under:" …) and elision markers ("xx xx xx"), each with no unbalanced closing quote since;
    - a closing quote right after the sentence.
  - The paragraph-bounded checks remain: curly balance, straight quotes, "(emphasis supplied)", "held thus:".
  - Party contentions count as submissions: "the petitioner (primarily) contended/contented that ... wherein it was held"; counsel "would submit that the reliance ... is misplaced".
  - In a High Court judgment, "this Court held/considered" next to a Supreme Court report is treated as the Supreme Court's quoted voice.
  - Reports of another forum, reporter matter, interrogatives and "no one has said" negations are excluded as before.
- **Binding and subject, revised for F03.**
  - A cue whose authority carries a glued footnote marker ("Madso4", "UOI11") binds only to footnote N's own citation. An anchor that is a footnote entry with no binding body marker is rejected.
  - C11's parallel citation strings (`||`) are split correctly when locating the anchor. This was a bug: the anchor previously fell back to the middle of the excerpt.
  - Past passive treatment ("was distinguished/followed") is treated as reported, as in lists of earlier decisions.
  - "Does not apply" / "not applicable" is rejected when a statute, rule, amendment or circular is the subject.
  - "X has been explained/clarified in <case>" is CONSIDERS, not EXPLAINS.
  - "is followed by" is not FOLLOWS.
  - Two named "… case" authorities in one sentence count as several authorities.
- **Targets.**
  - Unbound leads keep a raw-text target with leading fragments cleaned. A demonstrative carries the preceding sentences.
  - "the subsequent decisions ... following X" becomes the raw target, not X (F08).
  - Duplicate leads on one span merge.
- **Opinion.** Separate and dissenting opinions give no strong proposal. V13-02 (footer-based author) is not fixed.

**Quality figures (F01).** These are not measured performance, and none may be displayed as precision.

| Figure | Basis | Result |
| --- | --- | --- |
| **Independent AI review of the f915ac11 version** (`reviews/`, seeded stratified sample of 54, not human-checked) | fully correct: type, direction, own voice and target | FOLLOWS 12/14, CONSIDERS 9/12, DISTINGUISHES 2/6, APPLIES 1/4, EXPLAINS 0/4, DOUBTS 0/1, OVERRULES 9/9, DISAPPROVES 3/4. All: 36/54 |
| Development / in-sample, current version (C11 reviewed rows; rules were tuned on them). **SUPERSEDED: development evidence only.** The blind GA4 figure is relation_type precision 0.340 and `follows` recall 0.032 | typed-treatment agreement | 54/55 (98.2%); recall on supported rows 54/66 (81.8%); 71 correct rejections; 162 labels, 24 excluded as withdrawn before C11 rev. 1.3 |
| Re-check of the reviewer's 54 edges against the current version (`treatment/REVIEW_SAMPLE_RECHECK_C13.csv`); **not independent**, because the fixes were written after reading these verdicts | per edge | 34 kept and correct; 14 reviewer-found errors withdrawn; 1 target corrected (T51); 3 EXPLAINS retyped to CONSIDERS (the reviewer's suggested type); 2 correct edges lost (T16, T31) |

**What remains.**
- DISTINGUISHES, APPLIES, EXPLAINS and DOUBTS are marked `LOW_RELIABILITY_CANDIDATE`. After the revision, EXPLAINS and DOUBTS have no edges.
- The independent H-REL-C13 evaluation (GA4) is complete; see the blind result at the top of this README.
  - Only the identifier columns of `SAMPLE.csv` (rep_doc_id, rep_sha256, page) at `5e07e010` are read, to flag passages on those 160 pages (`in_a0_holdout_page`) and to keep them out of development scoring.
  - No H-REL-C13 passage was read.
  - No development label falls on a holdout page.
- Known residual noise is listed in the review and in `REVIEW_SAMPLE_RECHECK_C13.csv`.

## 3. Identity overlay (`identity/`)

The scope is the C12 `DUPLICATE_IDENTITY` copies: 128 copies, 439 membership rows. The RM-001 copy is withheld and counted, so 127 copies appear.

- **42 files under several doc_ids:**
  - 22 Supreme Court files are year-partition duplicates of one judgment (ONE_JUDGMENT_DUPLICATE_DOC_ID_YEAR_PARTITION, 44 rows);
  - 19 High Court files are common judgments or orders disposing several proceedings (ONE_JUDGMENT_SEVERAL_PROCEEDINGS, 305 rows): one judgment, one proceeding per doc_id;
  - 1 file is listed as both an Act and a notification (Tribunals Reforms Act 2021): REVIEW.
- **11 groups where one id carries several sha256 values:**
  - principal copies 8;
  - Hindi renditions 5;
  - alternate India Code copies 3 (version not established);
  - schedules 4;
  - India Code listing pages 21 (not instruments);
  - distinct subordinate instruments grouped under the parent Act id 39;
  - C5 multi-copy sources 8.
- 117 logical identities in all.

Every copy and doc_id is kept, and nothing is deleted, merged or renamed. Status: `PROPOSED_IDENTITY_OVERLAY_ALL_COPIES_KEPT`.

## 4. SC case numbers (`scnum/`, `hf/`)

All 99 staged records (1,747 case numbers) were reconfirmed against the PDF bytes. Each PDF was read at `ad77758d` and its sha256 re-hashed against the staged value.
- **81 by the text layer alone**, extracted independently with PyMuPDF from cover pages 1-3 and every jurisdiction-heading block. Every staged number and year, and a type label of each staged type, had to be present. OCR digit repair is applied. The type label is not bound to the number. This is a **presence** check, not a completeness check (F07, `scnum/ERRATA_C13.md`). This includes the 745-number 2024 list once a stray control character and the digital-SCR running header were handled.
- **18 by a page-image reading** where OCR garbled the text layer (`PAGE_IMAGE_CHECKS_C13.csv`, page cited). One note to flag: CA-2450-1992 is printed as "Civil Appeal Nos. 2449 and 50 of 1992". It was read as 2450, as the C11 reviewer did, and the elision is recorded.

**Overlay.** `SC_CASE_NUMBER_OVERLAY_C13.jsonl` (C13-v1): 99 records, values identical to the C12 staged values. Metadata only; no evidence or authentication status is promoted.

**What was not applied.** The 266 unreviewed candidates and the 3 unresolved records were not read and not applied.

**HF.** Applied as new additive files under `data/meta_overlays/` (README, overlay JSONL, SHA256SUMS), following the `data/manifest_additions/` convention. `data/meta` was not touched.

| Field | Value |
| --- | --- |
| HF commit | `844383f55d3b8e61068c3c786a69e8160061cc32` |
| Parent | `3864faf3` (pinned) |
| Pre-upload checks | Target folder absent at the parent; `hf_protect.assert_additive` passed |
| Verification | 3/3 files re-downloaded at the new commit, SHA-256 MATCH. The tree under the new folder equals the staged set, and nothing was removed |

Records: `hf/HF_COMMIT.csv`, `hf/VERIFICATION.csv`, `hf/STAGED_MANIFEST.csv`.

**Erratum E1 (F09).** The overlay's `evidence.anchor_page` for `sc-2016-union-of-india-and-anr-2016insc173` reads 11; the Diary numbers are on PDF page 12. The value itself is correct. The published HF file is not rewritten; see `scnum/ERRATA_C13.md`.

**Independent confirmation.** The reviewer re-read all 18 page-image records and a seeded sample of 22 of the 81 text-layer records: all RECONFIRMED (`reviews/`).

## Limits and what needs independent review

- **The only independent figures for the frozen extractor are the blind GA4 results at the top of this README** (descriptive). The development/in-sample figures are superseded.
- **Overruling.** Every OVERRULES, DISAPPROVES and DOUBTS candidate needs a human legal adviser. Raw-text targets need binding.
- **Instrument identity.** Instruments are not yet tied to source copies. ProvisionVersion is an interface only, pending A4.
- **Judgment identity** relies on C10 rendition groups and is PROVISIONAL.
- **Page-image readings** (18 records) were made by this agent from rendered pages. An independent check is advised.
- **Forms and holdings layers** are research-restricted and must not drive any operational output.
