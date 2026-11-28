# Cycle 16 local corpus reconciliation implementation plan

## Goal

Inventory `E:\Judgements` without modifying it, reconcile its documents against the pinned private canonical corpus, preserve subject provenance, and produce a restartable external candidate/evidence package plus minimized Git-tracked scripts and reports. No artifact is promoted, uploaded, or legally approved.

## Baselines and constraints

- Git corpus-engineering base: `9837bb3827c091d823ea0bfa28448b9343b69a2d`.
- Hugging Face canonical: `f8a46dfaec55a13f2aaac2fde4139ca0acd5cff9`.
- Hugging Face Cycle 15 candidate v7: `217020dbd969e14c2373697f4094fa00557962a6`.
- Source is read-only; outputs go to `E:\Mimamsa-Data\local-corpus-reconciliation`.
- RM-001/restriction controls fail closed. No AUTH-LEDGER, acceptance-oracle, application, database, or production-ingestion changes.
- Candidate bodies and bulky artifacts stay outside Git.

## Approach

Use one deterministic Python CLI with checkpointed JSONL state. It inventories and hashes first, extracts native PDF/DOCX text into a separate derivative store, computes normalized-text hashes, applies restriction indicators, indexes canonical SHA-256 values from Hugging Face metadata and repository manifests, reconciles exact and text-level identities, and produces all mandatory reports from one state register. Near-duplicate and legal-identity signals never establish identity automatically. A validator independently checks counts, hashes, paths, dispositions, and report presence.

Alternatives rejected: filename-only reconciliation is insufficient evidence; downloading the full canonical corpus would waste space and increase restricted-data exposure; AI classification would expose content and be non-deterministic; OCR of all files would repeat reliable extraction and exceed the bounded run.

## Tasks

### Task 1: Core deterministic primitives

**Files:** `legal_knowledge/audit_work/C16-LOCAL-CORPUS/c16_reconcile.py`, `legal_knowledge/audit_work/C16-LOCAL-CORPUS/test_c16_reconcile.py`

- [ ] Test stable inventory IDs, subject preservation, normalized-text hashing, safe archive member handling, and disposition precedence.
- [ ] Implement the minimal pure functions and run focused tests red then green.

### Task 2: Restartable inventory and extraction

- [ ] Test PDF/DOCX fixture inventory, duplicate grouping, corrupt-file recording, and checkpoint resume.
- [ ] Implement read-only recursive hashing, format detection, native extraction, page records, sparse-page OCR flags, and processing state.
- [ ] Run a bounded pilot and inspect its artifacts before the full run.

### Task 3: Canonical reconciliation and restrictions

- [ ] Test exact canonical matches, normalized-text alternates, unresolved near matches, and fail-closed restriction matches.
- [ ] Implement Hugging Face metadata indexing without document downloads plus local manifest/recovery/restriction overlay discovery.
- [ ] Pin comparison scope and limitations in coverage evidence.

### Task 4: Candidate package and mandatory reports

- [ ] Test mutually reconcilable dispositions, content-addressed candidate copies, manifest hashes, and all 17 mandatory deliverables.
- [ ] Implement report/package generation and independent validation.
- [ ] Run the full local collection, then independently verify the generated package.

### Task 5: Evidence and delivery

- [ ] Re-run focused tests, validation, source before/after manifest comparison, and Git diff review.
- [ ] Commit only scripts, tests, minimized summaries, instructions, and audit evidence.
- [ ] Push the dedicated branch and open a draft PR; do not merge.

## Review focus

- Two filenames with identical bytes retain all subject/path provenance but one candidate byte sequence.
- Similar texts from different orders or editions remain unresolved unless deterministic identity evidence is complete.
- Encrypted, corrupt, unsupported, and restricted files remain represented and never enter candidate originals.
- Resume after interruption does not re-hash or re-extract unchanged files.
- Canonical coverage states exactly which revisions and manifest/path classes were compared.

