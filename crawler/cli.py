"""Command line: python -m crawler <command>

  config-check            validate config/sources.yaml
  init-db                 create/upgrade state/crawl.sqlite
  status                  queue counts per source, recent runs, recent failures
  dry-run [--source S]... what a run would fetch, from config + crawl state; no network
  discover --source S     fetch LISTING pages only, queue the documents they list, show the plan
  fetch --source S        download queued documents (needs --yes-download)

`--replay DIR` (discover, fetch, dry-run, status) serves saved pages from DIR instead of the
network and keeps everything in separate replay state (state/replay.sqlite, state/logs/replay,
data/replay_raw), so made-up test URLs never mix with the real crawl state.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from . import aft, direct, indiacode, opendata, probe
from .audit import AuditLog, setup_logging
from .config import DEFAULT_CONFIG, ROOT, ConfigError, check_config, load_config
from .fetch import fetch_documents
from .http import CrawlError, PoliteClient, UserAgentNotSet, replay_transport
from .plan import build_plan, plan_to_json, plan_to_markdown
from .state import StateDB

log = logging.getLogger("mimamsa.cli")

DISCOVERERS = {"indiacode": indiacode, "aft": aft, "sci": opendata, "hc": opendata, "official_copies": direct, "legislative": direct, "bprd": direct}


def _replay(args) -> str | None:
    return getattr(args, "replay", None)


def _paths(args) -> tuple[Path, Path, Path]:
    root = Path(args.root)
    if _replay(args):
        return root / "state" / "replay.sqlite", root / "state" / "logs" / "replay", root / "reports"
    return root / "state" / "crawl.sqlite", root / "state" / "logs", root / "reports"


def _data_root(args) -> Path:
    root = Path(args.root)
    return root / "state" / "replay_data" if _replay(args) else root


def _client(args, cfg, db, run_id, source, log_dir) -> PoliteClient:
    audit = AuditLog(log_dir, db, run_id)
    if _replay(args):
        return PoliteClient(cfg, audit, source, transport=replay_transport(args.replay), replay=True)
    record = Path(args.record) if getattr(args, "record", None) else None
    return PoliteClient(cfg, audit, source, record_dir=record)


def _write_plan(args, cfg, db, names, run_id, report_dir, prefix="dry_run") -> tuple[dict, str, dict]:
    plan = build_plan(cfg, db, names)
    md, js = plan_to_markdown(plan), plan_to_json(plan)
    js["run_id"] = run_id
    report_dir.mkdir(parents=True, exist_ok=True)
    tag = f"{prefix}_replay" if _replay(args) else prefix
    (report_dir / f"{tag}_{run_id}.md").write_text(md, encoding="utf-8")
    (report_dir / f"{tag}_{run_id}.json").write_text(json.dumps(js, indent=2, ensure_ascii=False), encoding="utf-8")
    return plan, md, js


def cmd_config_check(args, cfg) -> int:
    r = check_config(cfg)
    for e in r.errors:
        print(f"ERROR   {e}")
    for w in r.warnings:
        print(f"WARNING {w}")
    print("config OK" if r.ok else f"config has {len(r.errors)} error(s)")
    return 0 if r.ok else 1


def cmd_init_db(args, cfg) -> int:
    db_path, _, _ = _paths(args)
    with StateDB(db_path):
        pass
    print(f"crawl state ready: {db_path}")
    return 0


def cmd_status(args, cfg) -> int:
    db_path, _, _ = _paths(args)
    with StateDB(db_path) as db:
        if _replay(args):
            print("REPLAY STATE (saved pages, not the live crawl)\n")
        counts = db.counts()
        print(f"{'source':<12}{'queued':>8}{'fetched':>9}{'failed':>8}{'skipped':>9}")
        for name in cfg.sources:
            c = counts.get(name, {})
            print(f"{name:<12}{c.get('queued', 0):>8}{c.get('fetched', 0):>9}"
                  f"{c.get('failed', 0):>8}{c.get('skipped', 0):>9}")
        files = db.conn.execute("SELECT COUNT(*), COALESCE(SUM(bytes),0) FROM files").fetchone()
        aliases = db.conn.execute("SELECT COUNT(*) FROM aliases").fetchone()[0]
        print(f"\nfiles stored: {files[0]} ({files[1] / 1e6:.1f} MB), duplicate-URL aliases: {aliases}")
        runs = db.last_runs(5)
        if runs:
            print("\nrecent runs:")
            for r in runs:
                print(f"  {r['run_id']}  {r['mode']:<9} {r['sources']:<20} {r['outcome'] or 'running/aborted'}")
        fails = list(db.failures(limit=10))
        if fails:
            print("\nrecent failures:")
            for f in fails:
                print(f"  [{f['last_status_code']}] x{f['attempts']} {f['url']}  {f['last_error'] or ''}")
        skipped = db.conn.execute("SELECT url, skip_reason FROM urls WHERE status='skipped' LIMIT 10").fetchall()
        if skipped:
            print("\nskipped:")
            for s in skipped:
                print(f"  {s['url']}  {s['skip_reason']}")
    return 0


def cmd_dry_run(args, cfg) -> int:
    db_path, log_dir, report_dir = _paths(args)
    setup_logging(log_dir, verbose=args.verbose, console=not args.json)
    names = args.source or (list(cfg.sources) if args.all else cfg.enabled_sources())
    for n in names:
        cfg.source(n)  # raises on unknown
    with StateDB(db_path) as db:
        run_id = db.start_run("dry_run", names, {"all": args.all, "replay": _replay(args)})
        try:
            plan, md, js = _write_plan(args, cfg, db, names, run_id, report_dir)
            db.end_run(run_id, "ok", plan["totals"])
        except Exception as e:
            db.end_run(run_id, f"error: {e}")
            raise
    if args.json:
        print(json.dumps(js, indent=2, ensure_ascii=False))
    else:
        print(md)
    return 1 if plan["config_errors"] else 0


def cmd_discover(args, cfg) -> int:
    db_path, log_dir, report_dir = _paths(args)
    setup_logging(log_dir, verbose=args.verbose, console=not args.json)
    cfg.source(args.source)
    module = DISCOVERERS.get(args.source)
    if module is None:
        print(f"no crawler module for {args.source!r} yet (have: {', '.join(DISCOVERERS)})", file=sys.stderr)
        return 2
    report = check_config(cfg)
    if report.errors:
        print("config errors; run config-check", file=sys.stderr)
        return 1
    if not _replay(args) and not cfg.may_run_now(args.source):
        q = cfg.defaults["quiet_hours_ist"]
        print(f"{args.source} is a heavy source; it only runs {q['start']}-{q['end']} IST.", file=sys.stderr)
        return 3
    with StateDB(db_path) as db:
        run_id = db.start_run("discover", [args.source],
                              {"only": args.only, "refresh": args.refresh, "replay": _replay(args)})
        try:
            client = _client(args, cfg, db, run_id, args.source, log_dir)
        except UserAgentNotSet as e:
            db.end_run(run_id, f"refused: {e}")
            print(f"refused: {e}", file=sys.stderr)
            return 3
        try:
            results = module.discover(cfg, db, client, args.source, only=args.only, refresh=args.refresh)
        except KeyError as e:
            db.end_run(run_id, f"error: {e}")
            print(e.args[0], file=sys.stderr)
            return 2
        finally:
            client.close()
        summary = {"targets": {r.doc_id: r.status for r in results}, "requests": client.requests_made,
                   "politeness_wait_seconds": round(client.waited_seconds, 1)}
        plan, plan_md, js = _write_plan(args, cfg, db, [args.source], run_id, report_dir, prefix="discover")
        db.end_run(run_id, "ok", summary)
    blocked = any(r.status == "blocked" for r in results)
    if args.json:
        print(json.dumps({"run_id": run_id, **summary, "plan": js}, indent=2, ensure_ascii=False))
    else:
        if _replay(args):
            print(f"> REPLAY from {args.replay}: responses come from saved pages, not from the live site.\n")
        print(f"# Discovery — {args.source} — run {run_id}\n")
        print(f"{client.requests_made} listing request(s); politeness delay "
              f"{'that a live run would add' if _replay(args) else 'spent'}: {client.waited_seconds:.0f} s. "
              "No documents were downloaded.\n")
        print(module.results_to_markdown(results))
        print(plan_md)
    return 4 if blocked else 0


def cmd_probe(args, cfg) -> int:
    db_path, log_dir, report_dir = _paths(args)
    setup_logging(log_dir, verbose=args.verbose)
    src = cfg.source(args.source)
    if check_config(cfg).errors:
        print("config errors; run config-check", file=sys.stderr)
        return 1
    if not _replay(args) and not cfg.may_run_now(args.source):
        q = cfg.defaults["quiet_hours_ist"]
        print(f"{args.source} is a heavy source; it only runs {q['start']}-{q['end']} IST.", file=sys.stderr)
        return 3
    urls = args.url or [s["url"] for s in src.get("seeds", []) if s.get("url")] or \
        ([src["base_url"]] if src.get("base_url") else [])
    if not urls:
        print(f"no --url given and {args.source} has no seeds or base_url", file=sys.stderr)
        return 2
    if len(urls) > args.max_pages:
        print(f"probe is limited to {args.max_pages} pages per run", file=sys.stderr)
        return 2
    with StateDB(db_path) as db:
        run_id = db.start_run("probe", [args.source], {"urls": urls, "replay": _replay(args)})
        try:
            client = _client(args, cfg, db, run_id, args.source, log_dir)
        except UserAgentNotSet as e:
            db.end_run(run_id, f"refused: {e}")
            print(f"refused: {e}", file=sys.stderr)
            return 3
        results = []
        try:
            for u in urls:
                results.append(probe.probe_url(cfg, db, client, args.source, u))
                if results[-1].outcome == "blocked":
                    break
        finally:
            client.close()
        db.end_run(run_id, "blocked" if results[-1].outcome == "blocked" else "ok",
                   {"pages": {r.url: r.outcome for r in results}, "requests": client.requests_made})
    md = probe.results_to_markdown(args.source, results)
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / f"probe_{args.source}_{run_id}.md").write_text(md, encoding="utf-8")
    print(md)
    print(f"({client.requests_made} request(s), robots.txt included; no documents downloaded)")
    return 4 if results[-1].outcome == "blocked" else 0


def cmd_fetch(args, cfg) -> int:
    db_path, log_dir, _ = _paths(args)
    setup_logging(log_dir, verbose=args.verbose)
    cfg.source(args.source)
    if not args.yes_download:
        print("fetch downloads documents. Review `dry-run` first, then re-run with --yes-download.", file=sys.stderr)
        return 3
    if check_config(cfg).errors:
        print("config errors; run config-check", file=sys.stderr)
        return 1
    if not _replay(args) and not cfg.may_run_now(args.source):
        q = cfg.defaults["quiet_hours_ist"]
        print(f"{args.source} is a heavy source; it only runs {q['start']}-{q['end']} IST.", file=sys.stderr)
        return 3
    with StateDB(db_path) as db:
        run_id = db.start_run("fetch", [args.source], {"limit": args.limit, "replay": _replay(args)})
        try:
            client = _client(args, cfg, db, run_id, args.source, log_dir)
        except UserAgentNotSet as e:
            db.end_run(run_id, f"refused: {e}")
            print(f"refused: {e}", file=sys.stderr)
            return 3
        try:
            stats = fetch_documents(cfg, db, client, args.source, _data_root(args), limit=args.limit)
        except CrawlError as e:
            db.end_run(run_id, f"error: {e}")
            raise
        finally:
            client.close()
        stats["requests"] = client.requests_made
        db.end_run(run_id, "blocked" if stats["blocked"] else "ok", stats)
    print(json.dumps({"run_id": run_id, **stats}, indent=2))
    return 4 if stats["blocked"] else 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m crawler", description="Mimamsa corpus crawler")
    p.add_argument("--config", default=str(DEFAULT_CONFIG))
    p.add_argument("--root", default=str(ROOT), help="repository root (state/, reports/, data/ live here)")
    p.add_argument("-v", "--verbose", action="store_true")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("config-check").set_defaults(func=cmd_config_check)
    sub.add_parser("init-db").set_defaults(func=cmd_init_db)
    s = sub.add_parser("status")
    s.add_argument("--replay", metavar="DIR")
    s.set_defaults(func=cmd_status)

    d = sub.add_parser("dry-run", help="show what would be fetched; no network")
    d.add_argument("--source", action="append", help="limit to a source (repeatable)")
    d.add_argument("--all", action="store_true", help="include disabled sources")
    d.add_argument("--json", action="store_true", help="print JSON instead of Markdown")
    d.add_argument("--replay", metavar="DIR", help="show the replay state instead of the live crawl state")
    d.set_defaults(func=cmd_dry_run)

    v = sub.add_parser("discover", help="fetch listing pages only and queue what they list")
    v.add_argument("--source", required=True)
    v.add_argument("--only", action="append", metavar="NAME", help="limit to a target, bench or slice, e.g. act-army-1950, chandigarh, 2013, delhi:2023 (repeatable)")
    v.add_argument("--refresh", action="store_true", help="re-read listing pages already fetched")
    v.add_argument("--replay", metavar="DIR", help="serve saved pages from DIR instead of the network")
    v.add_argument("--record", metavar="DIR", help="live runs: also save each page to DIR for later replay")
    v.add_argument("--json", action="store_true")
    v.set_defaults(func=cmd_discover)

    pr = sub.add_parser("probe", help="first checks: read robots.txt and a few listing pages; no downloads")
    pr.add_argument("--source", required=True)
    pr.add_argument("--url", action="append", help="page to read (repeatable); default: the source's seeds")
    pr.add_argument("--max-pages", type=int, default=8)
    pr.add_argument("--replay", metavar="DIR")
    pr.add_argument("--record", metavar="DIR", help="also save each page to DIR for later replay")
    pr.set_defaults(func=cmd_probe)

    f = sub.add_parser("fetch", help="download queued documents")
    f.add_argument("--source", required=True)
    f.add_argument("--limit", type=int, default=50)
    f.add_argument("--yes-download", action="store_true", help="required: confirms a real download run")
    f.add_argument("--replay", metavar="DIR")
    f.set_defaults(func=cmd_fetch)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        cfg = load_config(args.config)
        return args.func(args, cfg)
    except ConfigError as e:
        print(f"config error: {e}", file=sys.stderr)
        return 2
