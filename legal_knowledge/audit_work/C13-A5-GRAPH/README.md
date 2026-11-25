# C13-A5: judicial treatment and the legal knowledge graph (candidate layer)

**Status.** Candidate data and AI documentary checks only. Nothing here is legally validated. No evidence class, authentication state or AUTH-LEDGER entry was changed (the ledger stays at version 0). The treatment extractor is **not frozen**: it waits for the coordinator to confirm that A0 has been accepted.

Branch `claude/c13-a5-graph`. Inputs are pinned: text and metadata at raw-data commit `ad77758d` (read as git objects from `/home/user/c7`), C10/C11/C12 audit files at staging `a4c0c382`, and HF corpus revision `3864faf3`.

## Deliverables

| # | Deliverable | Where | Tool (`--check`) |
| --- | --- | --- | --- |
| 1 | Graph schema and data contract (IC-01) | `schema/graph_node.schema.json`, `schema/graph_edge.schema.json`, this README, `graph/IC01_EXPORT_MANIFEST.json` | n/a |
| 2 | Passage-level treatment extraction | `treatment/` | `tools/treatment_c13.py` |
| 3 | Identity-resolution overlay for duplicate legal identities | `identity/` | `tools/identity_c13.py` |
| 4 | Reconfirmation of the 99 staged SC case-number corrections, the overlay, and the HF application | `scnum/`, `hf/` | `tools/scnum_reconfirm_c13.py`, `tools/hf_overlay_c13.py` |
| 5 | Candidate graph and IC-01 export | `graph/` | `tools/graph_c13.py` |
| 6 | Packaging | `SHA256SUMS`, tests `tests/test_legal_audit_c13_graph_*.py` | `tools/package_c13.py` |

## Reproduce

```
PY=scratchpad/venv/bin/python        # Python 3.13 with PyMuPDF and jsonschema; tools also need git
$PY -I -B tools/scnum_reconfirm_c13.py --check      # needs PyMuPDF (MuPDF 1.28.6) and /home/user/c7
$PY -I -B tools/identity_c13.py --check
$PY -I -B tools/treatment_c13.py --check            # about 4 minutes
$PY -I -B tools/treatment_c13.py --dev-only         # in-sample score only; writes nothing
$PY -I -B tools/graph_c13.py --check                # validates every node and edge against the schemas
$PY -I -B tools/hf_overlay_c13.py --check [--online]
$PY -I -B tools/package_c13.py --check
$PY -B -m pytest -q tests/test_legal_audit_c13_graph_*.py   # C13_SKIP_SLOW=1 skips the --check subprocess test
```

Order of a full rebuild: scnum, identity, treatment, graph, package. The `.gz` outputs are gzip with mtime 0. `--check` compares their decompressed content. Standard library only, except PyMuPDF (scnum) and jsonschema (validation, optional in the build, used by the tests).

## Restricted material

`config/restricted_material.json` (RM-001) is read from the worktree when present. Otherwise it is read from governance commit `ea282cbd` (`claude/c13-gov`) as a git object; its sha256 is recorded in every summary.
- The FOUO Regulations for the Air Force 2000 copy (`4284820e…`) and its derived text and metadata (`regs-regulations-for-the-air-force-reprinted-edition-2000`) are excluded from every node, edge and export.
- `graph_c13.py` fails the build if any restricted sha256 or doc_id appears in its serialised output. The identity overlay withholds that one copy and counts it.
- A test scans every output file in this package.

## 1. Data contract (IC-01)

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
| `EDGE_TYPE_EVALUATION_C13.json` | Per-type measured precision, or NOT_MEASURED. Each edge's `evaluation_ref` points into it |
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

45,134 edges: 44,961 candidate or proposed, and 173 reviewed.

| Edge type | Total | Reviewed (AI documentary) |
| --- | --- | --- |
| CITES | 23,222 | 69 (target-correct review rows: 69 of 70) |
| CITES_PROVISION | 11,076 | 61 |
| DECIDES_PROCEEDING | 5,555 | 0 |
| STATES_PROPOSITION / RAISES_QUESTION | 2,325 / 258 | 0 |
| HAS_PROVISION | 1,008 | 0 |
| CONSIDERS | 368 | 0 |
| FOLLOWS | 278 | 32 |
| DISTINGUISHES | 34 | 10 |
| APPLIES | 12 | 1 |
| OVERRULES | 9 | 0 (always candidate) |
| DISAPPROVES | 4 | 0 (always candidate) |
| EXPLAINS | 4 | 0 |
| DOUBTS | 1 | 0 (always candidate) |
| APPLIES_PROVISION | 0 | – |
| Amendment (C10 graph, 99 entries) | 99 | 0 (82 PROPOSED_NOT_APPLIED) |
| Forms (4 types) | 881 | 0 |

The full breakdown by type and state is in `graph/GRAPH_SUMMARY_C13.json`.

**The 9 OVERRULES candidates:**
- Puttaswamy (2017) pp.167, 275, 276 and 432;
- Joseph Shine p.74 (×2);
- Mafatlal p.105 (×2: "decisions of this Court saying to the contrary"; raw target only);
- V. Sriharan p.99 ("we specifically overrule", Sangeet).

Most have raw-text targets with `binding = RAW_TARGET_ONLY_BINDING_NOT_ESTABLISHED`. An adviser must confirm every one.

**DISAPPROVES (declaratory):**
- Parashotam (2023) p.17 → Shri Kant Sharma, resolved;
- Ajmer Singh p.9;
- Mafatlal p.133 (×2).

## 2. Treatment extraction (`treatment/`)

**Method.**
- **Passages.** One per C11 citation-graph anchor in the judgment body (23,222 edges), plus every C11 treatment-candidate passage (2,595), located in the full text. 24,532 passages after merging cues that share a sentence (V13-04).
- **Voice gate.** Quotation is tested on curly-quote balance bounded to the paragraph, odd straight quotes, "(emphasis supplied)" and "held thus:" lead-ins (V13-01). The gate also tests for submissions (sentence, or a submission lead earlier in the paragraph; a court rejecting a party's reliance counts as court voice), reports of another forum, reporter matter, interrogatives and "no one has said" negations (V13-01).
- **Binding.** No other authority between the anchor and the cue, and FOLLOWS/APPLIES only with one authority in the sentence. For "has no application" or "does not apply", the authority must be the subject. A demonstrative target ("these two decisions") carries the preceding sentences in `target_raw_context` (V13-04).
- **Targets.** Unbound leads keep a raw-text target and never adopt a page-header candidate (V13-03 class).
- **Opinion.** Separate and dissenting opinions give no strong proposal. V13-02 (footer-based author) is not fixed: labels still come from C11.

**Development and measurement.** All figures are **in-sample**: the rules were developed on these rows.
- Labels: C11 review rounds 1 and 2 (treatment rows) and the v13 adviser-row verdicts (`DEV_LABELS_C13.csv`); 162 labels, one per row (the later review round wins).
- 24 labels are excluded because their rows were withdrawn before C11 rev. 1.3.

| Measure | Result |
| --- | --- |
| Typed-treatment precision | 56 / 59 = **94.9%** |
| Recall on reviewer-supported rows | 56 / 66 = 84.8% |
| Correct rejections | 69 |

Per type: FOLLOWS 32/33, DISTINGUISHES 10/11, OVERRULES 9/9, DISAPPROVES 4/4, APPLIES 1/1, DOUBTS 0/1.

C11 rev. 1.3 had no typed proposal on many of these rows, and its adviser tier carried the 4 V13-01 noise rows. All 4 are now rejected.

**This is not an independent estimate.** Independent precision and recall per type need A0's H-REL-C13 evaluation.
- Only the identifier columns of `SAMPLE.csv` (rep_doc_id, rep_sha256, page) at `5e07e010` are read, to flag passages on those 160 pages (`in_a0_holdout_page`, 333 passages) and to keep them out of development scoring.
- No H-REL-C13 passage was read.
- None of the development labels fall on a holdout page.

**Known residual noise.** A reading of a non-holdout sample of the full build found:
- reported holdings that contain "does not apply";
- "applying the ratio" said of the Tribunal;
- boilerplate "covered by" sentences with inline footnotes.

These stay candidates. CONSIDERS (368) is unmeasured.

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
- **81 by the text layer alone**, extracted independently with PyMuPDF from cover pages 1-3 and every jurisdiction-heading block. Every staged number, year and type label had to be printed. This includes the 745-number 2024 list once a stray control character and the digital-SCR running header were handled.
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

## Limits and what needs independent review

- **Treatment precision and recall are in-sample.** The extractor is not frozen; it waits for A0 acceptance and the GA4 evaluation.
- **Overruling.** Every OVERRULES, DISAPPROVES and DOUBTS candidate needs a human legal adviser. Raw-text targets need binding.
- **Instrument identity.** Instruments are not yet tied to source copies. ProvisionVersion is an interface only, pending A4.
- **Judgment identity** relies on C10 rendition groups and is PROVISIONAL.
- **Page-image readings** (18 records) were made by this agent from rendered pages. An independent check is advised.
- **Forms and holdings layers** are research-restricted and must not drive any operational output.
