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
