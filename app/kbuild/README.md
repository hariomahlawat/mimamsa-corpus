# mimamsa_kbuild: central knowledge build (C16 Tranche B, stream B02 skeleton)

One command builds an MKR-1 knowledge release from a pinned build spec, in stages S0-S9 with chained stage manifests
(`docs/architecture/c16/interfaces/B02_CENTRAL_BUILD_SPEC.md`, `mimamsa_contract.c16.build_spec`).

**Stage 2 scope.** The skeleton runs end to end on fixtures and produces a **development-signed, explicitly degraded
(lexical-only)** release for the CP-1 vertical slice. It never claims FULL service, never embeds, never uses an
operational key and never touches Hugging Face. The full pipeline is Stage 3.

## Run

```
cd app/kbuild
python -m mimamsa_kbuild prepare-fixture-mirror --out E:/Mimamsa-Data/c16b02/mirror
python -m mimamsa_kbuild build --spec specs/cp1-fixture.spec.json --out-root E:/Mimamsa-Data/c16b02/out \
       --source-mirror E:/Mimamsa-Data/c16b02/mirror [--dry-run] [--from S6]
python -m mimamsa_kbuild budget --spec specs/cp1-fixture.spec.json      # apply the budget and print what the OS reports
python -m mimamsa_kbuild measure-host                                    # figures for the spec's resources block
python -m pytest tests --basetemp E:/Mimamsa-Data/c16b02/pytest          # needs the .NET 10 SDK (S6 helper)
```

Outputs go under `--out-root` only: `build/<build_id>/S0..S9/` (each with `STAGE.json`), the signed bundle at
`S8/bundle/`, its development trust list at `S8/dev-trust/trust_list.json`, and `BUILD_RECORD.json` (timings and the
budget as applied; not part of the release). The development key is created at `<out-root>/dev-keys/` unless `--dev-key`
names one. The .NET helper (`accel/KBuildAccel.csproj`) is built on first use into `<out-root>/tools/dotnet`.

## Stage 3 (stream S3-A): the real canonical corpus

```
cd app/kbuild
python -m mimamsa_kbuild build --spec specs/real-sample-290.spec.json --out-root E:/Mimamsa-Data/c16s3a/out \
       --fetch-plan specs/real-sample-290.fetch.json --hf-cache E:/Mimamsa-Data/c16s3a/cache [--dry-run]
python -m mimamsa_kbuild stage-import --bundle <out>/build/<id>/S8/bundle --trust <out>/build/<id>/S8/dev-trust/trust_list.json \
       --site E:/Mimamsa-Data/c16s3a/sites/<new dir>        # B01 stage_only into an ISOLATED site (ACTIVE untouched)
python -m mimamsa_kbuild build --spec <delta spec> ... --base-bundle <FULL base S8/bundle>   # DELTA release
```

- **S1 real fetch** (`hf_fetch.py`, `real_corpus.py`): read-only, pinned 40-hex revisions only; every file verified
  against the pinned tree (git blob id or LFS sha256) and, where known, a manifest sha256 (the canonical
  `data/manifest.csv`, the v7 receipt held in git); restricted material is skipped **before** any request; bounded
  workers, byte rate and a free-disk floor; content-addressed cache; a resume re-reads the cache with no network.
  What is fetched is named by a **fetch plan** (`specs/<name>.fetch.json`, made by `specs/make_fetch_plan.py`) whose
  sha256 the spec pins as the `config_sha256` of the tool `mimamsa_kbuild.fetch_plan` (the spec schema is closed).
- **S2 conversion**: the canonical layout becomes v1 records with `app/b1/build/build_sample.py`'s own record logic;
  the Cycle 15 v7 package becomes `v7/candidate_sets/<name>.txt` (2.1 CS3 bytes) and a V7_REFERENCE accounting
  source. `adapters.from_v7_record` anchors and relationships are produced and counted, never shipped. A canonical copy
  whose bytes are a v7 candidate is emitted **not servable** (publication STAGED, SG-1) and accounted quarantined.
- **S3** re-derives `[[page N]]` derivatives from existing text only (`page_format.py`, config
  `config/page_rederive.json`, pinned as tool `mimamsa_kbuild.page_rederive`; `ocr: NONE`). v7 page text is
  re-derived for reference (page hashes and anchor spans checked), never shipped.
- **Producer generations**: none (v1-only), one, or a succession whose last member ships; earlier ones govern
  (SG-1 across generations; a hold is never lifted by omission). See `generations.py` for why the build never merges
  two exchanges.
- **DELTA** (`delta.py`): kind-specific transport against a verified FULL base; full-state digests; S9 applies base +
  delta, compares with the full state byte for byte and verifies the reconstructed state like a FULL release.

## Stages

| Stage | Does (Stage 2) |
| --- | --- |
| S0 spec | `spec_issues` plus what the skeleton refuses (DELTA, PRODUCTION signing, more than one producer generation) |
| S1 fetch | offline mirror of the pinned HF revision (no network in Stage 2); every file re-hashed; GENERATION.json against its pin; register against its pin; committed inputs and code digests; content-addressed cache |
| S2 validate | strict C16 exchange; 2.1 receipts (item-level); v1 validator on a scratch tree; SG-1 legacy check |
| S3 text | v1 `[[page N]]` derivatives verified; re-derivation refused (Stage 3); held C16 items never promoted |
| S4 bundle | unsigned tree: v1 records, originals, text, research, `corpus-v2/`, receipts, integrity register, admission accounting |
| S5 ref-import | the tree, dev-signed, imported into a scratch site by `app/importer` |
| S6 accelerate | knowledge rows (reference derivation), lexical index, text store and graph (B1 builders via `KBuildAccel`, pinned build time) |
| S7 assemble | `KNOWLEDGE_RELEASE.json` (refused unless it passes the contract rules), `SHA256SUMS` |
| S8 sign | development signature over `SHA256SUMS` (WD-11) |
| S9 verify | v1 validation (dev accepted, production refused), MKR-1 rules and inventory, digests, accounting and rows recomputed, fresh-site import and accelerator rebuild parity, expected outcome ACTIVE_DEGRADED |
