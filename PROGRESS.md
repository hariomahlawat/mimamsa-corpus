# Progress

## 2026-11-21 — Phase 1, step 2 (done, awaiting review)

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
