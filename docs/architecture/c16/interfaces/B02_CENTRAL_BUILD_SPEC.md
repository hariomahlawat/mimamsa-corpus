# B02 central build specification

**Schemas:** `BUILD_SPEC_SCHEMA.json`, `BUILD_STAGE_MANIFEST_SCHEMA.json`. **Reference:** `build_spec.py`. **Fixtures:** `v2_1/build/`.

## 1. One command

```
python -m mimamsa_kbuild build --spec <spec.json> [--from <stage>] [--dry-run]
```

- **The spec is the only input.** It pins producer generations (by GENERATION.json sha256 and HF revision), HF and git inputs, the register sha256, contract versions, models by sha256, tools, the release identity, `pinned_build_time` (no wall clock in any output), the stage list and the resource budget.
- **Dry run.** `--dry-run` lists what would be fetched and built, with counts per source, and writes nothing.

## 2. Stages

| Stage | Inputs | Outputs | Determinism | Network |
| --- | --- | --- | --- | --- |
| S0 spec | spec file | spec sha256; validated spec (`spec_issues`) | pure | no |
| S1 fetch | pinned HF revisions and paths; git commits | content-addressed cache; every file re-hashed against its pin | pinned revisions; re-hash | **yes (only stage)** |
| S2 validate | cache | v1 validator report; strict C16 validation per exchange; register check | pure | no |
| S3 text | v1-path items needing `[[page N]]` re-derivation | derivatives with pinned `ocr_config`; never promotes a held C16 item | pinned tools and models; ordered | no |
| S4 bundle | records, `corpus-v2/`, originals, text, research, registers, receipts | unsigned v1 bundle tree | canonical JSONL; sorted paths | no |
| S5 ref-import | S4 tree | a scratch reference site generation, imported by B01 exactly as a site would | same code as the site | no |
| S6 accelerate | reference generation, models | rows, graph, text store, index, vectors, each with digests | same assembly as the site; vectors per §5 | no |
| S7 assemble | S4 and S6 | `KNOWLEDGE_RELEASE.json`, `registers/source_accounting.json` (DECLARED_BY_BUILD, in ADMISSION_REGISTER; B01 §5a), inventory, `SHA256SUMS`; component digests per B04 §4 | `rules._release_manifest`; `pending_future_gates` from the committed gate-status file | no |
| S8 sign | `SHA256SUMS` | development signature, or prepared for the owner's **offline** signature | — | no |
| S9 verify | signed bundle | fresh scratch site through B01, B03, B04 and B06; outcome recorded | — | no |

Network use is confined to S1. Later stages run with networking disabled for the process where the OS allows, and are tested offline.

## 3. Stage manifest and resume

Each stage ends by writing `build/<build_id>/<stage>/STAGE.json` atomically (`.partial`, flush, rename). The manifest records:
- the spec sha256;
- the previous stage manifest's sha256 (the chain);
- `input_digest` = sha256(spec, stage, previous output digest);
- every output with path, sha256 and bytes;
- `output_digest`;
- tools;
- `network_used`, which may be true only for S1.

**Resume rule** (`stages_to_run`):
- The first stage that has no valid COMPLETE manifest, whose input digest changed, or whose outputs fail re-hashing, reruns together with every later stage. Earlier stages are reused.
- A killed stage leaves only `.partial` content, which is discarded on restart.
- A changed pin changes the spec hash, so the whole chain reruns. A finer-grained invalidation per input may be added later without changing the manifest format.

## 4. Resource budget (shared host)

The build host is shared with Codex's OCR. The spec carries a **measured** budget:
- logical CPUs and memory as measured on the host;
- `max_workers`, `max_memory_bytes` and `max_disk_bytes`;
- CPU and I/O priorities.

When `shared_host` is true (`spec_issues`):
- workers ≤ half the measured logical CPUs (at least 1);
- memory ≤ half the measured memory;
- CPU and I/O priority below normal.

No stage may exceed the build-wide worker budget.

**Memory and disk limits are hard stops.** The build pauses or fails; it never starves the co-tenant. These are development defaults and configurable, not final production decisions.

## 5. Determinism

- **Reproducibility.** Two clean builds from the same spec give byte-identical `SHA256SUMS`, except VECTOR_PACK if measurement shows ONNX non-determinism (plan §5.5). In that case vectors are compared within the calibrated tolerance and the difference is reported.
- **Sources of variation removed:** there is no wall clock (`pinned_build_time`), parallel output is ordered, and every serialisation is canonical.

## 6. Fixtures and tests

- **Positive:** `v2_1/build/spec.json` and a chained `stages/S0–S9.json`.
- **Negatives** (tests):
  - network outside S1;
  - wrong stage order;
  - too many workers on a shared host;
  - normal priority on a shared host;
  - memory over budget;
  - a DELTA without a base;
  - a missing pinned time;
  - a stage manifest using the network, with a wrong output digest, or broken from its chain.
- **Resume** recomputes the right stages.
