# Progress

## 2026-11-21 — Phase 1, step 3 (built against SYNTHETIC pages; NOT verified on the live site)

Done
- `crawler/http.py`: PoliteClient, the only HTTP path. Allow-list on every hop (redirects included),
  robots.txt (unreachable robots = disallow; Crawl-delay honoured), per-host delay, size cap, audit of
  every request, stop on 401/403/login redirects, refuses live requests while the contact email is the
  placeholder. Replay mode (`--replay DIR`) serves saved pages; `--record DIR` saves live pages.
- `crawler/indiacode.py`: search -> Act page -> queue Act PDF + subordinate legislation PDFs.
  Resolves a target only on exactly one exact title match; otherwise reports candidates.
- `crawler/fetch.py` + `fetch --yes-download`: downloads queued documents to
  `data/raw/<source>/<yyyy>/<sha256>.<ext>`; duplicates become aliases; non-PDF answers for PDF links fail.
- CLI: `discover`, `fetch`; replay runs use separate state (`state/replay.sqlite`, `state/replay_data/`).
- Crawl-state schema v2 (`urls.meta`: listing title, category, printed date, parent doc).
- 65 tests passing.

Unverified (needs the live site or real saved pages)
- India Code page layout, link shapes (`/handle/`, `/bitstream/`, `ViewFileUploaded`) and the
  `search_url_template` come from memory. `tests/fixtures/indiacode/` is hand-written, with invented
  handles, dates and robots rules.
- First real check: `python -m crawler discover --source indiacode --only act-army-1950 --record <dir>`
  (listing pages only, 3 requests), then review the output before any `fetch`.

Open points
- Subordinate documents have no doc_id or year at download time (stored under `/0000/`); the metadata
  stage assigns them.
- Section pages (`show-data` links) are counted but not queued; decide in Phase 2 whether section
  splitting uses them or the PDF.
- Listing pages are not saved to data/raw (only their hash is kept).

## 2026-11-21 — Phase 1, step 2 (approved)

Done
- `crawler/state.py`: SQLite crawl state (`state/crawl.sqlite`, WAL, schema v1): URL queue with
  queued/fetched/failed/skipped, attempts + exponential backoff with jitter (give up after max_retries),
  ETag/Last-Modified, sha256 file registry with duplicate-URL aliases, runs table, request audit table.
  Every change commits immediately, so a killed crawler resumes where it stopped.
- `crawler/audit.py`: console + rotating `state/logs/crawl.log`; every request goes to
  `state/logs/requests-YYYYMMDD.jsonl` and the `requests` table.
- `crawler/config.py`: loads and checks sources.yaml (politeness floor, robots on, no off-site links,
  exact-host allow-list, blocked hosts, doc_id format, quiet hours in IST for heavy sources).
- `crawler/plan.py` + `python -m crawler dry-run`: per-source plan from config + crawl state, written to
  `reports/dry_run_<run_id>.{md,json}`. Makes no network requests (tested). Commands: `config-check`,
  `init-db`, `status`, `dry-run [--source S] [--all] [--json]`.
- 40 tests passing.

Notes
- Targets show "discover: needs source module" until step 3 adds the India Code module, which
  will plug in via `plan.register_planner("indiacode")`.
- The polite HTTP client (robots.txt, per-host rate limit, retries, User-Agent guard) is built in step 3
  with its first user, the India Code fetcher.

## 2026-11-21 — Phase 1, step 1 (approved)

Done
- Project skeleton per CLAUDE.md layout; CLAUDE.md = brief exported from the Claude Docs doc.
- `schema/document.schema.json`, `section.schema.json`, `relation.schema.json` (JSON Schema 2020-12, v0.1.0).
- `pipeline/schemas.py` loader + `tests/test_schemas.py` (18 tests passing).
- `config/sources.yaml` with Phase 2 seeds (India Code, MoD) enabled; later phases stubbed and disabled.
- `.venv` + pinned `requirements.txt` (from `requirements.in`).

Not done / blocked
- Seed hosts (indiacode.nic.in, mod.gov.in, aftdelhi.nic.in, sci.gov.in, egazette.gov.in, archive.org,
  delhihighcourt.nic.in) are blocked by this cloud environment's network policy (proxy 403).
  Nothing in sources.yaml has been checked against the live sites; entries are marked `verify: true`.
- User-Agent contact email is a placeholder; crawler will refuse to start until it is set.

Next (after approval)
- Step 3: India Code fetcher for the Army Act 1950 only, dry run.
