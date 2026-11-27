# Mimamsa data authority and storage policy

**Primary canonical data store:** the PRIVATE Hugging Face dataset `hariomahlawat/mimamsa-corpus`.

**Secondary development store:** private GitHub `hariomahlawat/mimamsa-corpus`, `main` for code, schemas and audit reports; `raw-data` for a size-limited backup of crawler products.

## Required datasets
1. `data/raw/`, `data/meta/`, `data/text/`, `data/sections/`, `data/correspondence/`, `data/relations.jsonl`, `data/manifest.csv` and checksums produced by the existing crawler.
2. `schema/` and source/version manifests.
3. `legal_knowledge/reconciliation/` containing KB and case-law reconciliation queues, NOT certified legal truths.
4. `legal_knowledge/verification_batches/` containing atomic legal claims, rule-source comparisons and unresolved escalations.
5. `legal_knowledge/manual_sources/originals/` containing the eight owner-supplied MML source binaries, preserving SHA-256, edition and access markings; do not treat these as current binding law.
6. Future authenticated judgments, verified claims, Gazette amendments and JAG review records, maintained as independently versioned layers.

## Publication and release rules
- Never mark a source `legally_verified` based only on a valid file checksum or a successful upload.
- Original document bytes are immutable; corrections go into derivatives and discrepancy records.
- Manual uploads are private-only. Verify any official-use and copyright restrictions before wider distribution.
- Do not modify, remove or replace crawler-generated `data/` when publishing `legal_knowledge/`.
- The private HF dataset, rather than a GitHub branch, is the target of all production snapshots.
- For every attempted transfer, retain upload log, commit identity, per-file SHA-256 and a **read-back check** from HF.
- A dataset is not considered synchronized until the required paths have been read back from HF and checksums match.

## Current state (22 Nov 2026)
- GitHub draft PR #1 stages the curated review tables and standalone upload scripts.
- The eight MML binary source files were prepared as a local ZIP with SHA-256 manifest; **they are not presently uploaded to HF**.
- HF access has `contribute-repos`, but tool-hosted sandbox/compute attempts returned 402 Payment Required, and no direct file upload action is exposed.
- The corpus checkpoint in `scripts/push_hf.py` requires the intern's full local crawler workspace. The standalone script below uploads curated text only from source-control checkout, without altering `data/`.

## Safe text-layer upload
From a GitHub checkout containing `legal_knowledge/`, after a Hugging Face write login:

```sh
python scripts/push_legal_knowledge.py --dry-run
python scripts/push_legal_knowledge.py
```

Original binary upload requires the separately generated `Mimamsa_MML_Original_Sources_2026-11-22.zip` and `scripts/push_mml_originals.py`.

There is no claim that HF synchronization has happened until the destination is independently checked.
