# C13 B-PoC: measurement environment and deviations

## Hardware and OS (measured host, Linux)

| Item | Value |
| --- | --- |
| CPU | Intel Xeon @ 2.10 GHz (Sapphire Rapids class: AVX-512, AVX-512 VNNI, AMX), 4 vCPUs |
| RAM | 15.7 GiB, no swap |
| OS | Ubuntu 24.04.5 LTS, kernel 6.18 (VM) |
| Disk | ext4 virtual disk |
| **Contention** | **The host was shared with other Cycle 13 workstreams.** The 1-minute load average was **9 to 23** on 4 vCPUs for most runs; each result file records it. **Absolute latency and throughput numbers are therefore pessimistic and noisy. Treat only same-run ratios as indicative.** |
| VM clock | The VM appears to be suspended between agent turns, so wall-clock elapsed times of background jobs are not meaningful. Every timing reported here was taken inside a single foreground or background process run. |

## Toolchain (exact versions)

| Component | Version | How installed |
| --- | --- | --- |
| .NET SDK / runtime | SDK 10.0.404, runtime 10.0.15 (LTS channel) | Official `dotnet-install.sh --channel LTS` into `scratchpad/c13/tools/dotnet` (user space). Script sha256 `082f7685e156738a1b2e2ed8381a621870d4ce8e8c59278034556f05c186eb2e` |
| ASP.NET Core packages | Npgsql 10.0.4, Microsoft.Extensions.Hosting.WindowsServices 10.0.15 | NuGet |
| Python | 3.12.3 (system), venv `scratchpad/c13/venvs/bpoc` | Full pin list: `data/p7/python-bpoc-freeze.txt` |
| Key Python packages | Django 6.1.3, uvicorn 0.54.0, Hypercorn 0.18.0, psycopg 3.3.9, psycopg-pool 3.3.3, tantivy 0.27.0, faiss-cpu 1.16.0, onnxruntime 1.32.0, tokenizers 0.23.3, numpy 2.5.5, pypdfium2 5.15.2, pdfminer.six 20260107, pdfplumber 0.11.11, PyMuPDF 2.1 | pip |
| PostgreSQL | 16.15 (Ubuntu build), extensions available: pg_trgm 1.6, unaccent 1.1 | Pre-installed server binaries; `initdb` as the existing `postgres` OS user |
| Node / npm | Node 22.23.5; pdfjs-dist 6.5.438, vite 8.3.8, autocannon 8.0.0 | npm (project-local) |
| Playwright | 1.63.0 (pre-installed global; `chromium.launch()` with no options) | not reinstalled |

## Deviations from the brief (with reasons)

1. **PGDATA location.** The brief asked for `initdb` into `scratchpad/c13/pg`. PostgreSQL refuses to run as root,
   so it runs as the existing `postgres` OS user. The scratchpad parent directories are mode 0700 and owned by
   root, and something on the host periodically resets them to 0700. The first cluster (in `scratchpad/c13/pg/data`)
   crashed with `PANIC: could not open file .../global/pg_control: Permission denied` when that happened.
   The cluster was re-initialised at **`/var/tmp/c13-bpoc-pg/data`**, owned by `postgres` with mode 0700. It is
   bound to 127.0.0.1:55432 only, uses trust auth for local TCP, and has Unix sockets disabled. No system
   package was installed and no system config was changed.
2. **pgvector: BLOCKED locally.** `pg_config --includedir-server` reports `/usr/include/postgresql/16/server`, but
   that directory does not exist (the server headers package is not installed, and apt is not allowed). pgvector
   could not be built. **Vector measurements use FAISS `IndexFlatIP` (exact inner product) in-process, labelled
   "dense_faiss (NOT pgvector)".** The Windows CI workflow tries a real pgvector build (v0.8.1, `nmake /F
   Makefile.win`) against the runner's PostgreSQL. Unverified workaround, not attempted: build pgvector against
   headers from the matching PostgreSQL 16.15 source tarball and run a relocated copy of the server tree.
3. **Sandbox runtime location.** The P5 sandbox child runs as `nobody` and cannot traverse the 0700 scratchpad.
   Its parser runtime (pypdfium2 5.15.2 only) was installed with `pip --target` into the world-readable
   `/var/tmp/c13-bpoc-sbx/site`, and it uses `/usr/bin/python3.12`.
4. **Embedding scope reduced (compute-bound).** One BGE-small forward pass over a 256-token chunk is about 11 GFLOP.
   On this contended 4-vCPU host, fp32 throughput was about 2 to 6 chunks/s, so the planned 21,701-chunk dense
   index (all models) would have taken many hours. The dense index uses **3,367 chunks**: the first 180-word chunk
   of each of the 2,400 judgments, plus all chunks of the six core military statutes (Army Act, Air Force Act,
   Navy Act, AFT Act, Army Rules 1954, AFT Procedure Rules 2008). A lexical index over the same units
   (`bm25_denseunits+abbr`) gives a like-for-like comparison. See P2/P3 in the results file.
5. **Load generator on the same host.** autocannon (Node) shared the 4 vCPUs with the servers and PostgreSQL. This
   understates achievable throughput for all servers. It does not favour either framework systematically.

## Restricted material

All corpora, indexes, embeddings, PDF stores and fixtures were built through `app/poc/common/restricted.py`. That
module loads `config/restricted_material.json` from branch `claude/c13-gov` (commit **dfce9140**, the branch head when
the corpus was built; the file content is unchanged since ea282cbd). It excludes any item that matches the doc_id,
the source sha256, the meta/text blob sha256 (derived_sha256), or the hosted path. Build log: 1 item excluded
(`regs-regulations-for-the-air-force-reprinted-edition-2000`, by doc_id), recorded in `data/p2_corpus_stats.json`.
No restricted material was sent to any external service. The only external calls were model downloads from
huggingface.co, package registries, and vulnerability databases (pip-audit/OSV, npm, NuGet). None of them carried
corpus content.
