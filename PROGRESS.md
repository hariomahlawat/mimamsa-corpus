# Progress

## 2026-11-21 — Phase 1, step 1 (proposal, awaiting review)

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
- Step 2: crawl-state SQLite DB, request logging, `dry-run` command.
- Step 3: India Code fetcher for the Army Act 1950 only, dry run.
