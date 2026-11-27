# Cycle 14 corrective tranche 03 — development receipt

26 November 2026. Corpus coordinator development only. No corpus mutation, new source acquisition, authenticated blob read, HF write, legal promotion, merge or rebase.

## Reviewed integration baseline

Staging ee17b0660511b66fdd5307833e11d1268de35b56 at start. Prior PR58 d6a633984fe5873f027769447cfa238152b6f00b and PR59 7fcdb6b7273d8c2e26cffd080afba97359478ea1 passed configured audit CI. New substantive heads: PR58 ccece4c1e08f441d44b9012994a61be808ed51ab; PR59 cf2c8e8ac43a5b76d4d6077462706585815255f5. Both remain draft. New tests not yet verified by the coordinator.

## 1. Candidate export boundary

Inspected current staging app/importer/mimamsa_importer/importer.py (blob 74a97a247a9462d3d46f84ff67c34e9a71a198db), app/contract/mimamsa_contract/bundle.py (blob c2ab18dc99caf3d773ae47b34d7cd696cdd1e834), and app/b1/src/Mimamsa.Core/Generation/GenerationStore.cs. The importer verifies bundle, original, derivative and anchor integrity before materialization. The separate research-report channel copies signed/checksummed JSONL after restriction checking; B1 loads named research files. No C14 journal, candidate geometry, recovery proposal or OCR evidence may be exported through either route. Retain existing release semantics and authority ledger.

pipeline/candidate_release_guard.py is a negative-only C14 build-side preflight: all known, unknown and ordinary-looking record kinds denied, even on claimed approval or when marker fields are stripped. Seven tests added to normal audit CI. It is not wired to existing release builders, importer, signer or B1 retrieval, and cannot prove provenance itself. No app code changed. Actual integration must prevent candidate outputs from reaching bundle generation at all, verify exact approved export inputs at the importer, and enforce active-generation/exclusion rules at retrieval. Require independently tested adversarial bundle and stale-generation cases on synthetic copies; coordinate app-contract changes separately with the application owner. Never relax the existing restricted-material or authority checks.

## 2. OCR page evidence

pipeline/page_ocr_evidence.py rehashes bounded raw PDF bytes, renders a designated physical page using a fixed 150-dpi grayscale configuration, compares the claimed PNG hash, binds source/native text/TSV/OCR text hashes, captures frame and engine claims, validates TSV word identifiers and bounds, and records minimum confidence and disagreement flags. No OCR execution, independent engine provenance, full process isolation or visual adjudication. Text equality is not proof of fidelity. Identical rendered pages may have identical image hashes; physical page and source identities remain in the receipt. All eligibility flags remain false. Eight synthetic tests committed under C14-CA03-PIPELINE; require reviewed PDF runtime, not covered by default dependency-free audit CI.

## 3. Hash inventory

Live HF connector directory listings confirmed seven known store roots (four under data/raw and three under legal_knowledge/preservation). Connector metadata does not expose a revision pin or complete digest inventory; no current-head byte verification claimed. hf_inventory_metadata.py implements an inert-callback collector for exact revision, path scope, LFS SHA-256/size metadata, restriction predicate and missing hashes. Unknown-hash paths are not exported. Coverage of permitted local stores is not attested. No HF SDK provider wired; CLI live enumeration interlocked. LFS digest claims are not independently rehashed source bytes. Scope list and restriction-register binding must be reviewed, including omitted roots/aliases and unknown identities, before an approved metadata-only runner execution. No inventory acquisition eligibility.

## 4. Acquisition transport

transport_policy.py provides a deliberately narrow robots grammar (single wildcard user-agent group, literal ASCII paths, longest rule and allow-on-tie; unsupported syntax denies), aggregate byte/attempt budget and monotonic deadline checks. It is NOT an RFC 9309-conformant general parser. Deadline polling cannot interrupt blocking DNS, TLS or read calls; supervised process-wide timeout, safe per-attempt receipts, OS egress/ACL and native Windows tests remain mandatory. This helper is not integrated into downloader; acquisition interlock remains. Nine inventory/policy tests added to normal audit CI.

## Gates

16 new dependency-free tests queued via audit CI; eight PDF fixture tests require separate execution. Do not report them passed until actual results are obtained. The earlier interlock and default-classifier tests, approval tests on the reviewed runtime, native path tests, end-to-end non-destructive persisted processing, source provenance and actual importer/retrieval integration remain separate. All 15 Codex findings stay open until independent acceptance. Six-source, 23 archive and 534 judgment batches remain disabled; no new Codex review until the remaining corrective implementation and test evidence are coherent.
