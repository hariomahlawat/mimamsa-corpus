"""Command line: python -m crawler <command>

  config-check            validate config/sources.yaml
  init-db                 create/upgrade state/crawl.sqlite
  status                  queue counts per source, recent runs, recent failures
  dry-run [--source S]... what a run would fetch; writes reports/dry_run_<run_id>.{md,json}
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from .audit import setup_logging
from .config import DEFAULT_CONFIG, ROOT, ConfigError, check_config, load_config
from .plan import build_plan, plan_to_json, plan_to_markdown
from .state import StateDB

log = logging.getLogger("mimamsa.cli")


def _paths(args) -> tuple[Path, Path, Path]:
    root = Path(args.root)
    return root / "state" / "crawl.sqlite", root / "state" / "logs", root / "reports"


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
                print(f"  {r['run_id']}  {r['mode']:<8} {r['sources']:<20} {r['outcome'] or 'running/aborted'}")
        fails = list(db.failures(limit=10))
        if fails:
            print("\nrecent failures:")
            for f in fails:
                print(f"  [{f['last_status_code']}] x{f['attempts']} {f['url']}  {f['last_error'] or ''}")
    return 0


def cmd_dry_run(args, cfg) -> int:
    db_path, log_dir, report_dir = _paths(args)
    setup_logging(log_dir, verbose=args.verbose, console=not args.json)
    names = args.source or (list(cfg.sources) if args.all else cfg.enabled_sources())
    for n in names:
        cfg.source(n)  # raises on unknown
    with StateDB(db_path) as db:
        run_id = db.start_run("dry_run", names, {"all": args.all})
        try:
            plan = build_plan(cfg, db, names)
            report_dir.mkdir(parents=True, exist_ok=True)
            md, js = plan_to_markdown(plan), plan_to_json(plan)
            js["run_id"] = run_id
            (report_dir / f"dry_run_{run_id}.md").write_text(md, encoding="utf-8")
            (report_dir / f"dry_run_{run_id}.json").write_text(json.dumps(js, indent=2, ensure_ascii=False),
                                                              encoding="utf-8")
            db.end_run(run_id, "ok", plan["totals"])
        except Exception as e:
            db.end_run(run_id, f"error: {e}")
            raise
    if args.json:
        print(json.dumps(js, indent=2, ensure_ascii=False))
    else:
        print(md)
        log.info("dry run %s: report written to %s", run_id, report_dir / f"dry_run_{run_id}.md")
    return 1 if plan["config_errors"] else 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m crawler", description="Mimamsa corpus crawler")
    p.add_argument("--config", default=str(DEFAULT_CONFIG))
    p.add_argument("--root", default=str(ROOT), help="repository root (state/, reports/ live here)")
    p.add_argument("-v", "--verbose", action="store_true")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("config-check").set_defaults(func=cmd_config_check)
    sub.add_parser("init-db").set_defaults(func=cmd_init_db)
    sub.add_parser("status").set_defaults(func=cmd_status)
    d = sub.add_parser("dry-run", help="show what would be fetched; no network")
    d.add_argument("--source", action="append", help="limit to a source (repeatable)")
    d.add_argument("--all", action="store_true", help="include disabled sources")
    d.add_argument("--json", action="store_true", help="print JSON instead of Markdown")
    d.set_defaults(func=cmd_dry_run)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        cfg = load_config(args.config)
        return args.func(args, cfg)
    except ConfigError as e:
        print(f"config error: {e}", file=sys.stderr)
        return 2
