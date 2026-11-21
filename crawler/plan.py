"""Dry-run planning: what a run would fetch, per source, without touching the network.

Step 2 plans from config + crawl state only. Source modules added later (step 3 onwards)
can register a `planner(cfg, db, name) -> list[PlannedItem]` that also reads listing
pages; until then every source uses `config_planner`.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from .config import Config, check_config
from .state import StateDB, iso, utcnow


@dataclass
class PlannedItem:
    kind: str                  # target | seed | queued | retry
    doc_id: str | None = None
    title: str | None = None
    url: str | None = None
    state: str | None = None   # status in crawl.sqlite, None = never seen
    action: str = ""           # what the real run would do
    notes: list[str] = field(default_factory=list)


@dataclass
class SourcePlan:
    name: str
    enabled: bool
    phase: int | None
    heavy: bool
    may_run_now: bool
    allowed_hosts: list[str]
    discovery: str | None
    items: list[PlannedItem]
    state_counts: dict[str, int]
    due_now: int
    waiting_backoff: int
    warnings: list[str]

    @property
    def would_fetch(self) -> int:
        """Requests the run would make, excluding listing-page discovery not yet modelled."""
        return sum(1 for i in self.items if i.action.startswith("fetch"))


Planner = Callable[[Config, StateDB, str], list[PlannedItem]]
PLANNERS: dict[str, Planner] = {}


def register_planner(source: str):
    def deco(fn: Planner) -> Planner:
        PLANNERS[source] = fn
        return fn
    return deco


def _url_state(db: StateDB, url: str | None) -> str | None:
    if not url:
        return None
    row = db.get(url)
    return row["status"] if row else None


def config_planner(cfg: Config, db: StateDB, name: str) -> list[PlannedItem]:
    src = cfg.source(name)
    items: list[PlannedItem] = []

    for key in ("seeds", "benches"):
        for s in src.get(key, []) or []:
            url = s.get("url")
            notes = ["verify: true"] if s.get("verify") else []
            if not url:
                items.append(PlannedItem("seed", title=s.get("name") or s.get("key"), url=None,
                                         action="skip: no URL configured", notes=notes))
                continue
            ok, why = cfg.is_url_allowed(name, url)
            st = _url_state(db, url)
            action = ("refuse: " + why) if not ok else (
                "fetch listing" if st in (None, "queued") else f"none ({st})")
            items.append(PlannedItem("seed", title=s.get("name") or s.get("key"), url=url, state=st,
                                     action=action, notes=notes))

    for key in ("targets", "also_search"):
        for t in src.get(key, []) or []:
            notes = []
            if t.get("verify"):
                notes.append("verify: true")
            if t.get("status_hint"):
                notes.append(f"status_hint: {t['status_hint']}")
            if key == "also_search":
                notes.append("search only; fallback source exists")
            known = db.conn.execute(
                "SELECT url, status FROM urls WHERE doc_id_hint=? AND kind='document' AND source=?",
                (t["doc_id"], name)).fetchall()
            if known:
                for r in known:
                    action = "fetch document" if r["status"] == "queued" else f"none ({r['status']})"
                    items.append(PlannedItem("target", t["doc_id"], t.get("title"), r["url"], r["status"],
                                             action, notes))
            else:
                items.append(PlannedItem("target", t["doc_id"], t.get("title"), None, None,
                                         "discover: resolve URL from listing/search (needs source module)",
                                         notes))

    # Anything already queued in state that isn't covered above (e.g. discovered links, retries).
    covered = {i.url for i in items if i.url}
    for r in db.conn.execute("SELECT url, kind, doc_id_hint, attempts, next_attempt_at, meta FROM urls "
                             "WHERE source=? AND status='queued' ORDER BY priority, first_seen_at", (name,)):
        if r["url"] in covered:
            continue
        waiting = r["next_attempt_at"] and r["next_attempt_at"] > iso(utcnow())
        meta = json.loads(r["meta"]) if r["meta"] else {}
        notes = [f"{k}: {meta[k]}" for k in ("category", "date_raw", "parent_doc_id") if meta.get(k)]
        if r["attempts"]:
            notes.append(f"attempt {r['attempts'] + 1}")
        items.append(PlannedItem(
            "retry" if r["attempts"] else "queued", r["doc_id_hint"], meta.get("title"), r["url"], "queued",
            f"wait until {r['next_attempt_at']}" if waiting else f"fetch {r['kind']}", notes))
    return items


def plan_source(cfg: Config, db: StateDB, name: str, now: datetime | None = None) -> SourcePlan:
    src = cfg.source(name)
    planner = PLANNERS.get(name, config_planner)
    items = planner(cfg, db, name)
    counts = db.counts(name).get(name, {"queued": 0, "fetched": 0, "failed": 0, "skipped": 0})
    now_s = iso(now or utcnow())
    due = db.conn.execute("SELECT COUNT(*) FROM urls WHERE source=? AND status='queued' "
                          "AND (next_attempt_at IS NULL OR next_attempt_at<=?)", (name, now_s)).fetchone()[0]
    warnings = []
    may_run = cfg.may_run_now(name, now)
    if not may_run:
        q = cfg.defaults["quiet_hours_ist"]
        warnings.append(f"heavy source: a real run now would wait for quiet hours {q['start']}-{q['end']} IST")
    if src.get("verify"):
        warnings.append("marked verify: true; confirm URLs on the live site")
    return SourcePlan(
        name=name, enabled=bool(src.get("enabled")), phase=src.get("phase"), heavy=bool(src.get("heavy")),
        may_run_now=may_run, allowed_hosts=sorted(cfg.allowed_hosts(name)), discovery=src.get("discovery"),
        items=items, state_counts=counts, due_now=due, waiting_backoff=counts.get("queued", 0) - due,
        warnings=warnings)


def build_plan(cfg: Config, db: StateDB, sources: list[str], now: datetime | None = None) -> dict[str, Any]:
    report = check_config(cfg)
    plans = [plan_source(cfg, db, n, now) for n in sources]
    return {
        "generated_at": iso(now or datetime.now(timezone.utc)),
        "config": str(cfg.path),
        "config_errors": report.errors,
        "config_warnings": report.warnings,
        "user_agent_placeholder": cfg.user_agent_is_placeholder(),
        "sources": plans,
        "totals": {
            "sources": len(plans),
            "targets": sum(1 for p in plans for i in p.items if i.kind == "target"),
            "targets_unresolved": sum(1 for p in plans for i in p.items
                                      if i.kind == "target" and i.url is None),
            "would_fetch": sum(p.would_fetch for p in plans),
            "refused": sum(1 for p in plans for i in p.items if i.action.startswith("refuse")),
        },
    }


def plan_to_json(plan: dict[str, Any]) -> dict[str, Any]:
    out = dict(plan)
    out["sources"] = [{**asdict(p), "would_fetch": p.would_fetch} for p in plan["sources"]]
    return out


def plan_to_markdown(plan: dict[str, Any]) -> str:
    t = plan["totals"]
    lines = [f"# Dry run — {plan['generated_at']}", "",
             f"{t['sources']} source(s), {t['targets']} target(s) "
             f"({t['targets_unresolved']} still need URL discovery), "
             f"{t['would_fetch']} request(s) would be made from known URLs, {t['refused']} refused.", ""]
    if plan["config_errors"]:
        lines += ["**Config errors (a real run would refuse to start):**", ""]
        lines += [f"- {e}" for e in plan["config_errors"]] + [""]
    if plan["config_warnings"]:
        lines += ["**Config warnings:**", ""] + [f"- {w}" for w in plan["config_warnings"]] + [""]
    for p in plan["sources"]:
        c = p.state_counts
        lines += [f"## {p.name} (phase {p.phase}, {'enabled' if p.enabled else 'disabled'}"
                  f"{', heavy' if p.heavy else ''})", "",
                  f"Hosts: {', '.join(p.allowed_hosts) or '—'}  ",
                  f"State: {c.get('queued', 0)} queued ({p.due_now} due now, {p.waiting_backoff} in backoff), "
                  f"{c.get('fetched', 0)} fetched, {c.get('failed', 0)} failed, {c.get('skipped', 0)} skipped  ",
                  f"Would fetch now: {p.would_fetch}", ""]
        if p.discovery:
            lines += [f"Discovery: {p.discovery.strip()}", ""]
        lines += [f"- ⚠ {w}" for w in p.warnings]
        if p.warnings:
            lines.append("")
        if p.items:
            lines += ["| Kind | doc_id / name | URL | State | Action | Notes |", "| --- | --- | --- | --- | --- | --- |"]
            for i in p.items:
                lines.append(f"| {i.kind} | {i.doc_id or i.title or ''} | {i.url or ''} | {i.state or '—'} | "
                             f"{i.action} | {'; '.join(i.notes)} |")
            lines.append("")
    return "\n".join(lines)
