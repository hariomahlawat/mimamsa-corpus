# B01 producer / consumer interface (Codex → central build → site importer)

**Normative base:** contract 2.0 (frozen): C16_CORPUS_INTEGRATION_CONTRACT §9.3, §10, §13; producer R1–R19; consumer I1–I9. This document fixes the **interface** both sides build against; it adds the 2.1 receipts and the I-5 legacy rules.

## 1. Exchange directory layout (producer output, preserved to HF under ADR-0004)

```
<exchange root>/                          one corpus generation, immutable once preserved
  GENERATION.json                         corpus_generation_manifest (2.0 schema); contract "…/2.1" when receipts are carried
  identities.jsonl | identities.NNNN.jsonl         document_identity
  anchors.jsonl                           evidence_anchor
  relationships.jsonl                     corpus_relationship
  taxonomy.jsonl                          taxonomy_node
  admissions.jsonl                        corpus_admission (revision chains)
  reviewed_records.jsonl                  v1 reviewed_record (when any review_binding exists)
  registers/receipts/<sha256>.json        gate_receipt_artefact (2.1), canonical bytes
  derivatives/<sha256>.txt                [[page N]] derivatives and image OCR derivatives, by hash
```

**Rules for the layout:**
- **Canonical files.** Names are canonical, or declared shards `<stem>.<nnnn>.jsonl`. Every JSONL file is canonical (contract §9.1).
- **What GENERATION.json lists.** It lists the JSONL files with kind, sha256 and record count. Receipt artefacts and derivatives are listed with sha256 in the release component inventory at bundle time (S4).
- **Nothing else** is read from the producer: no worktree paths, no `E:\` paths, no logs.

**In the release bundle (S4)** the exchange travels as:
- `corpus-v2/` (records and `GENERATION.json`);
- `registers/receipts/` (ADMISSION_REGISTER component);
- `text/` (derivatives).

## 2. GENERATION.json

This is the contract 2.0 schema `CORPUS_GENERATION_MANIFEST_SCHEMA.json`. It declares:
- **contract version:** 2.1 when artefacts are carried;
- **pinned inputs:** HF revisions with their purpose, full git commits, local collections with inventory hash and count, the register sha256, tools;
- **every file** with kind, sha256 and record count;
- **registries:** instrument codes and external judgments.

The central build pins the exchange by the **sha256 of GENERATION.json** (build spec `producer_generations`).

## 3. Validation levels

| Level | Who runs it | Call | Accepts |
| --- | --- | --- | --- |
| Record | producer tooling, adapters | `rules.record_issues` | one object |
| Partial | producer work in progress, adapter output | `rules.exchange_issues(mode="partial")` | present populations only; **never importable**, and refused at S2 and by the importer |
| Strict | producer hand-over; central build S2 | `rules.exchange_issues(mode="strict")` | complete generation; manifest counts and hashes; registries |
| Signed import | site importer B01 | v1 bundle checks (signature first) + strict + `receipts.resolve_receipts` (2.1) + byte checks (I4, I8) | only this level can make a copy servable |

## 4. Error codes

The codes come from the contracts and reference code; no new meaning is introduced here:
- **2.0:** contract §11 and the `KR_*` codes. These include C16_ADMISSION_*, C16_GATE_EVIDENCE, C16_ELIGIBLE_IDENTITY_NOT_READY, C16_RECEIPT_MISMATCH, C16_SEARCH_WITHOUT_COVERAGE, C16_ANCHOR_*, C16_REVIEW_*, C16_MANIFEST*, C16_FILE_*, C16_DUPLICATE_KEY, C16_GENERATION_MISMATCH, C16_TARGET_UNREGISTERED and C16_QUOTE_*.
- **2.1 receipts:** C16_RECEIPTS_REQUIRE_2_1, C16_RECEIPT_PATH, C16_RECEIPT_NOT_IN_INVENTORY, C16_RECEIPT_HASH, C16_RECEIPT_UNPARSEABLE, C16_RECEIPT_NOT_CANONICAL, C16_RECEIPT_PAYLOAD, C16_RECEIPT_SUPERSESSION, C16_RECEIPT_SUPERSEDED, C16_RECEIPT_UNRESOLVED, C16_RECEIPT_FIELD_MISMATCH, C16_RECEIPT_REGISTER, C16_RECEIPT_UNVERIFIABLE, C16_RECEIPT_SITE_MISMATCH.
- **Importer outcome codes** (consumer I6, I7): C16_SUBJECT_NOT_SERVABLE, C16_LEGACY_NOT_ESTABLISHED (section 5).

**Error handling.**
- Any **bundle-level** error (signature, checksums, strict validation, register) refuses the **whole** bundle, and the site is left untouched.
- **Item-level** outcomes (receipt resolution, byte checks) quarantine the item and leave it unserved. They are counted in the import report by code.

## 5. I-5 legacy and v1 compatibility (binding)

1. **Scope of v1 compatibility.** v1 compatibility covers only copies **independently established as v1-eligible**: a v1 document record in a signed v1 bundle, publication PUBLISHED, restriction ELIGIBLE_ALL_USERS, verified by the existing v1 importer steps and the current exclusion state. It never comes from C16 data.
2. **No bypass by omission.** A missing or removed C16 sidecar **never bypasses** a hold, withdrawal, provenance gap or admission:
   - If any generation (current or retained) holds a C16 identity or admission for a (doc_id, sha256), that copy is governed by C16 rules from then on. Dropping the sidecar in a later bundle does not revert it to v1 rules; the importer refuses it (`C16_LEGACY_NOT_ESTABLISHED`).
   - Withdrawals and restrictions come from the monotone exclusion channel. No release can lift them.
   - A v1 record with incomplete provenance (no pinned HF revision or acquisition record) is not established.
3. **No relabelling.** v7 candidates (`legal_knowledge/candidates/cycle15/v7`) and any other unadmitted original **cannot be relabelled as v1 documents** to be served. A v1 record whose sha256 appears in a candidate package or a C16 exchange without an eligible admission is refused (`C16_LEGACY_NOT_ESTABLISHED`). v7 derivatives may be re-derived (S3) only for copies that are already established v1 items.
4. **Per-source admission accounting.** The import report and the release manifest record, per source:
   - v1-path canonical corpus;
   - each C16 producer generation;
   - v7 (reference only, never served);
   - local Admin uploads (site only).

   For each source the counts are: identities, effective admissions by decision, eligible, served, held, rejected and quarantined. Each source is reconciled to its input count. A source whose counts do not reconcile refuses the bundle.

## 6. Producer obligations (Codex), additive to R1–R19

- **Receipts.** Emit receipt artefacts (2.1) for every PASS gate of an eligible admission, with re-verifiable payloads. Never claim SITE_RECOMPUTABLE facts the bytes cannot support.
- **Re-runs.** A re-run gate gets a new artefact revision and a new admission revision referencing it.
- **Hand-over.** Hand over only strict exchanges; partial output is for work in progress only.

## 7. Consumer obligations (site importer B01), additive to I1–I9

- **Validation.** Call the reference validators; never re-implement them. Resolve receipts at signed import with the site's own recomputed facts.
- **Serving.** A copy is servable only if:
  - it is in `servable` (v1);
  - its effective admission is eligible;
  - its receipts resolve (2.1);
  - its byte checks pass;
  - it is not excluded.

  A legacy copy additionally needs the I-5 establishment above.
- **Import report.** Carry per-gate SITE_VERIFIED or ASSERTED_BOUND, and per-source accounting.
