# Release importer (source fidelity)

The first piece of application code, written in response to ASR-E05 from PR #54. It is build-side and site-side Python. It imports a contract-v1 release bundle into a content-addressed vault and a release generation. Nothing becomes servable until it has been verified against the **bundled bytes**; schema validation alone is not enough.

| Step | Check | On failure |
| --- | --- | --- |
| 1 | Contract validation: signature, checksums, schema, rules, restricted register (RM-001 and others) | Import refused. Nothing is written; the active generation is unchanged |
| 0 | Replay protection: the active generation's `release_sequence` is read from the site (older or equal refused unless rollback); an identical re-import is a no-op; an existing generation is never rewritten | Refused, no write |
| 2 | Each document's original: bundled bytes exist with the claimed SHA-256; size equals `bytes`; vault key equals `vault/sha256/<2>/<sha>`; content type **detected from the bytes** equals the declared MIME type; measured physical page count equals `page_count` (PDF via pypdfium2; text/plain as form-feed pages; other types unverifiable) | **Activation refused** for the whole generation; previous generation keeps serving; vault untouched |
| 3 | Each derivative: declared source is the verified copy of its doc_id; text file bundled with matching SHA-256; declared pages are physical pages of the original with matching `char_count`; passages lie inside their page and hash to `text_sha256` | Item **UNRESOLVED** (quarantined with reasons); never servable |
| 4 | Each candidate anchor: copy is the source document's own copy (or declared alternate) and verified; page is a physical page of that copy; a bound span's offsets (either or both, with or without passage id) lie inside the verified page/passage and its declared text hash equals the hash recomputed from the verified text; unbound spans are served page-only with their fields stripped | Item **UNRESOLVED**; never servable |
| 5 | Verified originals are written once into the vault and **retained across generations**; the append-only held-copies index is updated; the generation is built in a temporary directory (fsync) and renamed into place; `ACTIVE` is switched by temp file, fsync, rename and directory fsync (directory fsync is skipped on Windows, where NTFS durability is proven in P8) | Previous generations retained |

**Page text format.** Page N is the text after its `[[page N]]` marker line, up to the next marker line. The single newline before the next marker, or at the end of the file, is removed.

**Serving decision (fail closed).** `servable(site, kind, id, exclusions=store.effective_state(trust))` returns true only if two conditions hold: the item is verified in the ACTIVE generation, and it is not withdrawn or restricted. `cite()` uses the same guard.

`exclusions=None` is accepted only when all three hold:
- the site was installed with `configure_site(site, exclusion_channel="none")`;
- the active generation recorded that mode;
- no exclusion store directory exists.

Every other `None` path denies: unconfigured site (default `"signed"`), empty store, pending-only store, lost acceptance record, or a mode flipped after the generation was written. A supplied state must be a real `ExclusionState`.

**One-way exclusion-mode latch (review N4).** The first accepted exclusion writes `EXCLUSION_LATCH` beside the store. From then on, and also once any generation records `"signed"`, the site is permanently in exclusion-store mode:
- later generations inherit that mode;
- `configure_site(..., "none")` is refused;
- edits to `SITE_CONFIG` are ignored;
- a missing or unreadable store on a latched site raises `ImporterError` (integrity failure) and refuses the import, while serving keeps denying anything that depends on exclusions.

**Crash recovery.** Held copies are derived from activated generations: those at or below the ACTIVE sequence. A copy is therefore never citable before its generation activates.

On the next import:
- a generation renamed into place but never activated is resumed (`resumed=True`) if it is the identical bundle (same release id and SHA256SUMS digest), and quarantined otherwise;
- stale `.tmp-*` directories are quarantined under `quarantine/generations/`, never deleted;
- storage failures raise `ImporterError`.

Crash points tested: after a vault write, before the generation rename, and before the ACTIVE switch. **Citations:** `cite()` implements `app/design/policies/citation_resolution.json`.

## C16 signed import (Tranche B B01, contract 2.0 with 2.1 receipts)

`mimamsa_importer/c16.py` runs after steps 1–4 and before anything is written. It is **active** when the bundle carries `corpus-v2/` or `registers/` files or a `KNOWLEDGE_RELEASE.json`, or when the site is already C16-aware (one-way latch: `C16_DECISION_INDEX.json` or any generation with a `c16` section). A pure v1 bundle on a site that never saw C16 is imported exactly as before.

| Level | Check | On failure |
| --- | --- | --- |
| Bundle | `corpus-v2/` and `registers/` files are RELEASE.json files of kind `other` (`C16_TRANSPORT`; an unlisted receipt is `C16_RECEIPT_NOT_IN_INVENTORY`) | Whole bundle refused; site byte-identical |
| Bundle | `rules.exchange_issues(mode="strict")` with the site register and the bundle's ledger version. Partial exchanges are refused by construction (no `GENERATION.json`, a missing population). Contract 2.0 and 2.1 only (`C16_CONTRACT_UNSUPPORTED`) | Refused |
| Bundle | Any C16 record naming a copy the site holds as restricted (register or exclusion-state restriction) (`C16_RESTRICTED_IN_EXCHANGE`) | Refused |
| Bundle | Label readings: every folder and file-name classification recomputed with `adapters.classify_path` and compared byte for byte (`C16_CLASSIFICATION_MISMATCH`); explicit D1/D2 checks (`C16_READING_AR`, `C16_READING_AFT`), including taxonomy aliases | Refused |
| Bundle | Malformed receipt artefact anywhere under `registers/` (path, inventory, hash, parse, schema, payload semantics, canonical form, revision chain) | Refused |
| Bundle | `KNOWLEDGE_RELEASE.json`, when present: release-manifest rules and component inventory against `SHA256SUMS` | Refused |
| Bundle | Per-source accounting: `registers/source_accounting.json` is required on every C16-aware import and must reconcile with the importer's own counts (`C16_SOURCE_ACCOUNTING`, `C16_SOURCE_ACCOUNTING_MISSING`) | Refused |
| Item | Typed receipt resolution for every eligible effective admission (`receipts.resolve_receipts`) with facts the site recomputes from the bundled bytes: hash and size, format, register scan, identity and copy-record validation, derivative units, DOCX image inventory (safe archive reader). G04, G08 and G09 are recorded `ASSERTED_BOUND`, never site-verified | Copy `QUARANTINED`, not served |
| Item | Byte checks (I4): size, format, PDF page count, DOCX images in the container, derivative units and coverage, reconstructed-page mapping origin | Copy not served |
| Item | Anchors (I8): `evidence.verify_anchor_bytes` against the verified derivative bytes; the verdict is recorded per anchor | Span not verified |

**Serving (I7, I-5, SG-1).** A v1 document stays servable only if it has a C16 identity whose effective admission is eligible **and** resolves at the site, or it has no sidecar and is an independently established legacy copy (`legacy.legacy_issues`: published, eligible for all users, pinned HF revision or acquisition record, not governed by C16 in this or any earlier import, not a declared v7 candidate or a hash seen in a C16 exchange, not excluded). Everything else is removed from `servable` and `item_document`, with its derivatives and candidates; NAVIGATION_ONLY admissions keep the document but not its text. `held_copies()` and the B1 `GenerationStore` skip copies the active generation lists in `c16.denied`, so an earlier generation never resurrects a held copy. Restricted copies are never written to the vault and never named in anything the import writes.

**Written into the generation** (inside the temporary directory, before the atomic rename): `corpus-v2/*` verbatim (`materialized.corpus_v2` lists each hash), `c16/verdicts.json` (per copy, per anchor, legacy), `c16/resolved_receipts.json` plus the resolved artefacts under `registers/receipts/`, `registers/source_accounting.json` (the importer's counts) beside `registers/source_accounting.declared.json` (the signed declaration), and a `c16` section in `generation.json`. The site-level `C16_DECISION_INDEX.json` is rewritten atomically before the generation is built, so a crash can only leave the site stricter.

**Accounting register (proposed contract 2.1 additive item).** `{"record_kind": "source_admission_accounting", "contract": "mimamsa-corpus-contract/2.1", "release_id", "sources": [{"source", "path": "V1"|"C16"|"V7_REFERENCE", "input", "identities", "held", "rejected", "quarantined", "eligible", "served", "candidate_sha256" (V7 only)}]}`. Sources are `c16:<corpus_generation_id>`, `v1:hf:<repo>@<revision>` or `v1:<acquisition_channel>`, and `v7:<name>`. Input, identities, held and rejected must match exactly; the site may only lower eligibility and service.

Tests: `tests/test_c16_importer.py` (contract fixtures NR01–NR18, N01–N54, X01–X35; real-bytes bundles from `c16_cases.py`). The B1 end-to-end fixture site is rebuilt and checked with `python -I c16_cases.py ../b1/tests/Mimamsa.Tests/fixtures/c16_b01 --check`.

**Not covered yet:** page-image comparison for OCR (see DA-04), database and index loading, the UI and the Windows service wrapper (P5/P6).

```
pip install -r app/importer/requirements.txt
cd app/importer && python -m pytest -q tests
python da_cases.py --observations obs.json     # observations for PR #54's comparator
```

PR #54 case results are in [RESULTS_DA.md](RESULTS_DA.md).
