# C13-A5 review: confirmation of d09b7d91 (copy)

> **Copy note (C13-A9).** The confirmation section of the reviewer's original `scratchpad/c13/reviews/a5/review_c13_a5_f915ac11.md`, copied without changes. Kept here, not in `C13-A5-GRAPH/reviews/`, because the A5 package SHA256SUMS covers every file in that folder.

## Confirmation review of `d09b7d91` (`git log f915ac11..d09b7d91`)

**Mode:** read-only. The branch was not modified. Working files are in `r2/`.

### Reproduction

- All 8 `--check` commands reproduce byte-identically: scnum, identity, treatment, graph, contract_v1_export, review_recheck, hf_overlay and package.
- pytest passes 81 tests:
  - 51 C13 tests;
  - 6 in `test_legal_audit_c12_research_isolation.py`;
  - 24 in `test_legal_audit_c6_provenance.py`, which covers the frozen hashes of records_658, cases_53 and CALIBRATION-02.
- The author's "57" is the 51 C13 tests plus the 6 isolation tests.

### Case numbers, unchanged

- `SC_CASE_NUMBER_OVERLAY_C13.jsonl` and the staged HF files are unchanged since `f915ac11`. My earlier 18/18 page-image and 22/22 text-layer reconfirmations therefore still hold.
- Overlap between the overlay and the 266 `APPLY_CANDIDATE_UNREVIEWED_CONFIRMED` rows (and the UNRESOLVED rows): **0**.

### Contract v1 export, validated by the reviewer

I ran B's validator (`python -m mimamsa_contract --register <claude/c13-gov register, sha256 fc7ea07e…> record candidate`) on the decompressed `candidates_graph_edges.jsonl.gz`: 34,567 records.

| Track B version | Result |
| --- | --- |
| `5f4b8071` (git archive) | ok, **0 issues** |
| current `claude/c13-b-app` head `a56e1e5f` | ok, **0 issues** |

What the export contains:
- **Relations:** CITES_JUDGMENT 23,222; CITES_PROVISION 10,936; QUOTES_PROVISION 140; FOLLOWS_PROPOSITION 257; OVERRULES_OR_LIMITS_PROPOSITION 12.
- **Status and references:** every record is `AUTOMATED_CANDIDATE_NOT_VERIFIED`, with `evaluation_ref=null` and `review_ref=null`.
- **Restrictions:** FOLLOWS and OVERRULES records carry `NON_OPERATIONAL_RESEARCH_ONLY`.
- **Excluded types:** no LOW_RELIABILITY type is present, and neither are CONSIDERS, EXPLAINS or DOUBTS.
- **Span anchors:** all 269 resolve to the quoted text. They use page-relative offsets in `data/text` at `ad77758d`, and `derivative_text_sha256` matches.
- **Extractor:** `artefact_sha256` equals `treatment_c13.py` at both `fb8aac7f` and the current head.

### RM-001

I scanned every file in the package, with `.gz` files decompressed and the new export included. I searched for RM-001's source sha256, both derived sha256 values, the doc_id, "RAF2000" and the title.
- There is no hit in any data output, graph or export.
- The only hits are in the README, this review (copied into the branch) and the safety-assertion constant.
- The register is re-pinned to `72fe7a75` (`fc7ea07e…`).

### H-REL-C13 exclusion

The holdout handling still holds:
- `treatment_c13.py` reads only `rep_doc_id`, `rep_sha256` and `page` from A0's `SAMPLE.csv` at `5e07e010`.
- 333 passages are flagged `in_a0_holdout_page`.
- No development row falls on a holdout page.
- None of my first-round 54 sample edges, on which the fixes were developed, lies on a holdout page.
- One edge in the fresh sample below (U20) lies on a holdout page. I read only A5's own passage for it, not A0 material.

### Fresh independent sample

The first-round sample is now development data, so it cannot measure the fixes. I drew a new sample of 50 edges from the new build (seed 20261126), excluding first-round passages (`r2/sample2_verdicts.csv`).

| Type | Fully correct | Exported? |
| --- | --- | --- |
| FOLLOWS | 19/20 | yes |
| OVERRULES | 8/8 | yes |
| DISAPPROVES | 4/4 | yes |
| CONSIDERS | 7/10 | no |
| DISTINGUISHES | 3/5 | no (LOW_RELIABILITY) |
| APPLIES | 0/3 | no (LOW_RELIABILITY) |

- The exported treatment types score **31/32**.
- The single exported error is U11, a FOLLOWS edge. It comes from a counsel statement: "Mrs. Sharma, learned ASGI states that in view of the decision …".
- The footnote binding is fixed:
  - U03 and U12 bind to the correct footnote.
  - The Plaque, T13, T27, T28, T30, T32, T34, T35, T40 and T41 errors no longer produce edges.
  - T51 now carries the raw target "subsequent decisions".

### Disposition

| Finding | Status | Note |
| --- | --- | --- |
| F01 | CLOSED | No displayable precision anywhere. In-sample figures are marked `displayable:false`. The export carries a null evaluation_ref. |
| F02 | CLOSED | A residual is noted: U11 (counsel voice), and reported lower-forum CONSIDERS edges (U22, U29, U30). |
| F03 | CLOSED | DISTINGUISHES and APPLIES remain weak but are marked LOW_RELIABILITY and not exported. |
| F04 | CLOSED | See the P3 note below on what the relations target. |
| F05 | CLOSED | |
| F06 | CLOSED | |
| F07 | CLOSED | Errata E2. |
| F08 | CLOSED | Cosmetic: U43's raw target still begins with "… of in the following terms". |
| F09 | CLOSED | Erratum E1. The published HF file is left as is (additive policy). |

**New findings: none at P1 or P2.** Three P3 notes:
- **N1.** FOLLOWS_PROPOSITION and OVERRULES_OR_LIMITS_PROPOSITION target judgment nodes (`JUD:`), not propositions. DISAPPROVES is merged into OVERRULES_OR_LIMITS and told apart only by the id prefix. Track B should not present these as proposition-level edges.
- **N2.** FOLLOWS is concentrated in templates: 159 of 257 come from Gawas Anil Madso and many from Ram Avtar. The FOLLOWS figure is not representative of varied prose.
- **N3.** The voice gate still misses counsel statements introduced by "learned ASGI states" or "She also states" (U11, U33 and U34).

**Freeze.** The candidate layer and the contract v1 export are ready to freeze. They remain candidate data, not validated, and independent per-type figures await A0's H-REL-C13.
