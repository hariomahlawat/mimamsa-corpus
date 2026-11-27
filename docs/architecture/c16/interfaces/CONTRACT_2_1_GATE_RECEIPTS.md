# Contract 2.1: typed gate-receipt artefacts (I-1; FG-RECEIPTS interface)

**Schema:** `GATE_RECEIPT_ARTEFACT_SCHEMA.json`. **Reference:** `receipts.py`. **Fixtures:** `fixtures/c16/v2_1/`.

## 1. Why

Contract 2.0 (frozen) types the receipt **reference** on an admission gate: kind, copy, derivative, rule, config, register, outcome and `receipt_sha256`. What that hash points at was untyped, so a matching file hash proved nothing about the gate. Contract 2.1 types the **artefact** and defines how the signed importer resolves it. **Hash existence alone is never proof.**

## 2. The artefact

| Field | Meaning |
| --- | --- |
| `contract` | `mimamsa-corpus-contract/2.1` |
| `gate_id`, `receipt_kind` | one fixed pairing per gate (G01 ↔ HASH_REDOWNLOAD … G10 ↔ SCHEMA_VALIDATION; schema) |
| `verification_class` | SITE_RECOMPUTABLE (G01, G02, G03, G05, G06, G07, G10) or ASSERTED_BOUND (G04, G08, G09); fixed by the schema |
| `subject` | exact `doc_id` and `source_copy_sha256` |
| `corpus_generation_id` | the generation the admission belongs to |
| `derivative_sha256` | required for G06; null otherwise |
| `rule {id, version}`, `config_sha256` | the producing rule and configuration identity |
| `register_sha256` | required for G03: the restricted-register revision checked |
| `outcome` | PASS or FAIL; must follow from the payload (`artefact_issues`) |
| `revision`, `supersedes_receipt_sha256` | append-only chain per (generation, copy, gate) |
| `producer` | tool, version, commit |
| `payload` | kind-specific, re-verifiable (table below) |

**Location.** `registers/receipts/<sha256 of canonical bytes>.json`, owned by the ADMISSION_REGISTER component and listed in its signed inventory.

| Kind | Payload | Site re-verification |
| --- | --- | --- |
| HASH_REDOWNLOAD | HF repo, 40-hex revision, path; measured sha256 and bytes | re-hash the vault bytes; must equal the measured hash and the subject |
| FORMAT_DETECTION | magic bytes, detected format, MIME type | re-read the magic bytes and re-detect |
| REGISTER_CHECK | fields checked; match count (PASS iff 0) | re-run the pinned register over hash, doc_id, paths and every record string |
| MARKING_SCREEN (asserted) | pages and images screened, markings found, method, OCR config | typed consistency only; recorded ASSERTED_BOUND |
| IDENTITY_VALIDATION | identity record sha256, issue count | re-validate; the record hash must be the exchange's identity |
| DERIVATIVE_VERIFICATION | units total and with text, per-unit text sha256 | re-hash, re-split `[[page N]]`, recompute the per-unit hashes and coverage |
| IMAGE_ACCOUNTING | every occurrence (id, image hash, OCR state, OCR derivative) | re-read the container (safe zip); compare exactly with the identity inventory |
| RELEVANCE_DECISION (asserted) | decided by (owner or operator), basis | typed consistency only |
| DUPLICATE_RESOLUTION (asserted) | scope, method, result | typed consistency only |
| SCHEMA_VALIDATION | `copy_records_sha256`, issue count | recompute the digest of the copy's own records and re-run strict validation |

**Why G10 is copy-scoped.** Binding G10 to `GENERATION.json` would be circular: the manifest hashes `admissions.jsonl`, which contains this receipt's hash. G10 therefore binds to `copy_records_digest` (the identity, its anchors and its relationships, canonical and sorted).

## 3. Resolution at signed import (`resolve_receipts`), fail closed

This applies to every **eligible effective** admission (the 2.0 chain head):
0. **Version.** The exchange must be contract 2.1, otherwise `C16_RECEIPTS_REQUIRE_2_1`.
1. **Locate.**
   - The path is `registers/receipts/<sha>.json` (`C16_RECEIPT_PATH`) and in the component inventory (`C16_RECEIPT_NOT_IN_INVENTORY`).
   - The bytes hash to the name (`C16_RECEIPT_HASH`), parse (`C16_RECEIPT_UNPARSEABLE`) and are canonical (`C16_RECEIPT_NOT_CANONICAL`).
2. **Validate.** Schema, and the payload's own semantics (`C16_RECEIPT_PAYLOAD`). An invalid artefact counts as absent.
3. **Chain.** One linear chain per (generation, copy, gate) (`C16_RECEIPT_SUPERSESSION`). The admission must reference the head (`C16_RECEIPT_SUPERSEDED`).
4. **Bind** (`C16_RECEIPT_FIELD_MISMATCH`). These must equal the admission's receipt and gate result:
   - gate and kind;
   - copy, doc and generation;
   - derivative;
   - rule id and version;
   - config;
   - register;
   - outcome.

   Every PASS gate of an eligible admission needs a resolvable receipt (`C16_RECEIPT_UNRESOLVED`).
5. **Register.** A G03 receipt's register must equal the generation's **and** the site's pinned register (`C16_RECEIPT_REGISTER`).
6. **Relate.** The payload must agree with the exchange (`C16_RECEIPT_PAYLOAD`): hash and size of the copy; format; identity record hash; derivative and coverage; image inventory; copy-records digest.
7. **Recompute.**
   - SITE_RECOMPUTABLE kinds need the site's own recomputed fact (`C16_RECEIPT_UNVERIFIABLE` when missing) that agrees (`C16_RECEIPT_SITE_MISMATCH`). `recompute_site_facts` is the reference.
   - ASSERTED_BOUND kinds are recorded as such and **never** reported as site-verified.

Any issue makes the admission ineligible at the site. The importer (B01) refuses to serve it.

The result also gives, per gate, SITE_VERIFIED or ASSERTED_BOUND, which the import report and activation record carry.

## 4. Supersession and revision

- A re-run of a gate is a **new artefact** (revision n+1, `supersedes_receipt_sha256` = the previous artefact's hash), never an overwrite.
- The admission's receipt (a 2.0 field) is updated to the new head **by a new admission revision** (2.0 rules: the admission id includes decision and gate results, and receipts are excluded, so a receipt-only change keeps the admission id). The importer always resolves the chain head.
- Forks, cycles, self-supersession and skipped revisions are rejected.

## 5. Fixtures and tests

**Positive.** `v2_1/exchange/` is the 2.0 fixture exchange with contract 2.1 declared. Its eligible admission (`sc-2019-example-…`) points at nine real artefacts in `v2_1/registers/receipts/`. G07 is NOT_APPLICABLE because the image list is empty. `site_facts.json` stands in for the site's recomputation.

**Negative.** `v2_1/negative_receipts/NR01–NR18` cover:

| Case | What is wrong |
| --- | --- |
| NR01 | artefact missing |
| NR02 | kind inconsistent with the gate |
| NR03 | another copy |
| NR04 | another derivative |
| NR05 | stale register revision |
| NR06 | FAIL under a PASS gate |
| NR07 | rule version differs |
| NR08 | config differs |
| NR09 | another gate's artefact reused |
| NR10 | measured hash not the copy's |
| NR11 | outside `registers/receipts/` |
| NR12 | not in the inventory |
| NR13 | contract 2.0 exchange |
| NR14 | site recomputation differs |
| NR15 | site fact missing |
| NR16 | superseded revision referenced |
| NR17 | non-canonical artefact |
| NR18 | identity receipt for another record |

**Tests** (`test_c16_interfaces.py`): every negative raises its code and fails closed, and with no site facts nothing site-recomputable verifies.

## 6. Producer adoption

Codex adopts 2.1 at its own pace (plan §2.6). Until then:
- its exchanges stay 2.0;
- every admission is held or ineligible at the site (fail closed);
- the build still carries the items, but they are not served.
