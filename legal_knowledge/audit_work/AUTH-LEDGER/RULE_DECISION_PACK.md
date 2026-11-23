# Rule-version decision pack (prepared by the implementer; independently challenged in `review/`)

**Nothing here is adopted.** Rule 1 stays the effective rule. Any change in eligibility needs a separately reviewed and owner-approved rule version, with `--as-of` diffs; historical versions keep rule 1.

**Data.** Counts come from `RULE_DECISION_PACK_data.json`, rebuilt by `tranches/tools/policy_impact.py`; `--check` confirms it reproduces. They cover the 32 C6-01 draft entries.

## A. Retrieval provenance versus content verification
**What rule 1 does.** A retrieval record (JSON, kind RET) is first-class at FULL strength unless:
- it disclaims authenticity (`UNCONFIRMED`);
- it reports `NOT_FOUND` or `CONFLICTING`;
- its authenticity value is not on the allow-list.

`SOURCE_LOCATED` and `SOURCE_VERIFIED` count the same.

**Records affected.** Of the 32 drafts, 13 use a RET record as first-class evidence: 10 are `SOURCE_VERIFIED` and 3 are `SOURCE_LOCATED`. The 3 are:
- 3b753548: Navjot, a primary court copy;
- 4acdb1a8: S.R.O. 34/1963, a primary Gazette;
- 6b495f14: the Rajbir rendition, non-primary.

| Option | Changes | Newly ineligible | Newly eligible | False-positive risk | False-negative risk | Reproducibility | Tests needed |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A1 keep | nothing | 0 | 0 | a located-but-unverified record counts as FULL | none added | unchanged | none |
| A2 require SOURCE_VERIFIED | first-class RET must be VERIFIED | **2**: Navjot (3b753548) and the Rajbir rendition (6b495f14). S.R.O. 34/1963 (4acdb1a8) can be re-pointed to its second FULL record, `ACQ-02/supplement_inventory.csv#ACQ02-03`, and stays eligible (corrected after Fable F-13) | 0 | lowest | the 2 lose FULL, although byte identity is proven by their own sha256 | rule 2; history keeps rule 1 | per-state acceptance, one test per affected record, and a test of the re-pointing |
| **A3 (recommended)** separate questions | entry gains `retrieval_verification_state`; a LOCATED record supports retrieval provenance only, and content identity must come from an identity check | 0 | 0 | low: identity is already mandatory | none | rule 2 with a new column; v0000 unchanged | column presence; limitation text for LOCATED; identity still required; state copied from the record, not typed |

**Safest rule.** A3 keeps every eligibility decision rule 1 makes, and makes the evidence gap explicit. A2 is stricter, but would demote records whose bytes are hash-proven.

**A3 is safe only together with B2** (Fable F-13). Navjot (3b753548) has a `SOURCE_LOCATED` record as its only first-class evidence and page-1 text as its only identity evidence, yet on its own it creates the EXACT_ANCHOR for DCLR-SC-2005-L01. Under A3 with B1, that anchor would rest on a located-but-unverified record plus a text-layer match. A3 must therefore not be adopted without B2, or without an equivalent requirement for a CONFIRMED image check on anchor-creating entries.

## B. Legacy page-image evidence (no `identity_result` field)
**What rule 1 does.** Each of the following counts as identity evidence:
- an older image-check row naming the sha256, with a render hash;
- an ARMY-RULES-CHAIN-01 register row at `IMAGE_CHECKED`;
- for a court copy only, the page-1 text rule.

Only C6 checks carry `identity_result`, and only CONFIRMED counts.

**Records affected.**
- 22 drafts rest on legacy image checks or register rows only. These are all 20 tranche-1 Gazettes and 2 non-primary publications.
- 9 court drafts rest on the page-1 text rule only.
- 1 draft (TRA) has a C6 CONFIRMED check.
- 7 drafts would create an exact anchor alone. All 7 are court copies that rest on the text rule: 10e1954f, 3056712c, 3b753548, 4f7ea3a4, 970b9680, eb442080, ed7cf31f.

| Option | Changes | Newly ineligible (until new evidence) | Newly eligible | False-positive risk | False-negative risk | Reproducibility | Tests needed |
| --- | --- | --- | --- | --- | --- | --- | --- |
| B1 accept as now | nothing | 0 | 0 | an old row that read something other than the identity elements still counts. For the 20 Gazettes, the S.R.O. number and date line are quoted from the page image: for 13, in image checks or WS-A transcriptions; for 7, only in the L5 R23 register, which is agent-produced and not approved (Fable R-03). So the risk is low for 13, and for 7 it is lower than "none recorded" but not human-confirmed. For the 9 court entries, identity is text-layer only | none | unchanged | none |
| **B2 (recommended)** fresh check where an anchor is created | an entry whose approval creates an EXACT_ANCHOR needs a CONFIRMED check or a reviewer statement naming the identity elements | 7 court entries | 0 | low where it matters; Gazette rows without crosswalk effect still rely on legacy evidence, with a limitation | low | rule 2; anchors computed by the reader, never typed | anchor-creating entry without a CONFIRMED check is rejected; non-anchoring entry is accepted with the limitation |
| B3 fresh check for all legacy | every legacy-only or text-only entry needs a CONFIRMED check | 31 | 0 | lowest | high: 31 entries wait, 22 of which have no coverage effect | rule 2 | same as B2, for all |

**Safest rule.** B2. B3 is safest in isolation but delays entries with no coverage effect. The "creates exact anchor" figures come from the C6-01 draft column. They were independently recomputed with the reader by the Fable reviewer, and agree (R-08). The first tranche-1 build wrongly reported 7 Gazette rows as lacking an identifier transcription. Fable F-02 showed that the cited L5 records quote it, so the earlier text here has been withdrawn.

## C. URL normalisation for contradiction detection
**What rule 1 does.** Exact-string comparison of a locator with every committed (URL, sha256) pair.

**Interaction with AUTH-LEDGER-02.** The strict parser rejects the common second spellings of a first-class locator:
- case variants, explicit ports and fragments;
- escapes of unreserved characters, and lower-case escapes;
- archive.org queries;
- trailing-slash directory paths.

It does **not** reject every equivalent spelling (Fable F-03). Still accepted are:
- reserved-character escapes such as `@` versus `%40`;
- query-parameter order;
- different paths that serve one resource, notably archive.org `/details/<item>` versus `/download/<item>/<file>`.

So the RFC-safe normalisations in C2 no longer change a first-class locator, but aliasing remains a real question.

**Records affected.**
- 75 committed pairs, 74 distinct URLs.
- No committed URL changes under C2 normalisation.
- One existing exact-string contradiction: India Code bitstream `7a05a1f5-…/content`, recorded with two sha256 values (the known TRA 2026 case). It is unchanged under C2 and under a `/jonew/judis/` ↔ `/judgment/judis/` alias.
- No new contradiction appears under any option.
- **10 archive.org items** are recorded under both `/details/<item>` and `/download/<item>/<file>`. None of them carries differing sha256 values today, but an alias table would have real content now.

| Option | Changes | Newly ineligible | Newly eligible | False-positive risk | False-negative risk | Reproducibility | Tests needed |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C1 exact string (rule 1) | nothing | 0 | 0 | none | a differently spelled or aliased URL (e.g. `/details/` versus `/download/`) escapes matching | unchanged | none |
| **C2 (recommended)** RFC-safe normalisation of the comparison set, plus a decision-referenced alias table (archive.org `/details/<item>` ↔ `/download/<item>/<file>` first); matches are reported as candidates | committed variants compared in normal form; aliases only with a decision record | 0 on current data | 0 | low: equivalence-preserving only | low | rule 2; the alias table is a pinned, versioned input | each safe normalisation; each unsafe one (trailing slash, http↔https, query drop) is NOT applied; alias needs a decision reference; a match is reported, never merged |
| C3 broad normalisation (trailing slash, http→https, query drop) | merges distinct resources | unpredictable | unpredictable | high: false contradictions, and false identity of distinct documents | — | poor | — (not recommended) |

**Safest rule.** C2, with the archive.org item alias as its first table entry. On current data it changes no outcome, but 10 items already appear in both forms. The earlier recommendation to defer C2 rested on an over-broad claim about the parser and is withdrawn (Fable F-03).

## Copy-fidelity table: independent assessment
Fidelity describes **how the held bytes relate to the official publication**. It is not legal validity (in force, applicable), not source authority (who issued it), and not cryptographic signature verification.

| Class | Primary at rule 1 | Assessment | Recommendation |
| --- | --- | --- | --- |
| Scanned facsimile | yes | page images of the printed Gazette; identity read from the image | keep primary |
| Born-digital, signed range spans the file | yes, provisionally | structurally unaltered after signing, **if** the signature were valid; validity is unknown | keep primary provisionally, with the limitation "signature not validated" on every entry; revisit when offline validation with trust evidence exists; hold tranche 1B until the owner confirms |
| Born-digital, rewritten | no | bytes changed after signing; no claim to the issued file | keep non-primary |
| Archive derivative | no | re-rendered by archive.org | keep non-primary |
| Official court-issued copy | yes | the court's own judgment file on the court host | keep primary, **but define it**: does a JUDIS rendition on a court host count (R-T2-1)? |
| Court-system rendition | no | database or text rendition with an unknown carrier | keep non-primary; decide whether JUDIS falls here |
| Incomplete | no | parts missing | keep non-primary; the ER 2023 13 MB copy stays distinguishable from the full publication |

## Owner decisions required
- **P-A.** Adopt A3 as part of a rule-2 transition, or keep rule 1. Recommended: A3, **only together with B2**.
- **P-B.** Adopt B2, or keep rule 1. Recommended: B2.
- **P-C.** Adopt C2, with the archive.org `/details` ↔ `/download` item alias, in the rule-2 transition. Recommended: adopt; candidates are reported, never merged.
- **P-D1.** Confirm the fidelity table.
- **P-D2.** Confirm that born-digital files with a spanning signed range stay primary provisionally, without cryptographic validation (tranche 1B).
- **P-D3.** Classify JUDIS renditions on a court host as court-issued or as court-system renditions. This must be decided before tranche 2.
- **P-R2.** Any adopted option is built as rule version 2, in its own PR with an independent review. No rule-2 code is written here.
