"""Work through the open-data judgment sets slice by slice: discover -> download -> keep only the
armed-forces judgments. One court-year at a time, so disk use stays bounded (rejected judgments are
deleted as each slice is processed) and a stopped run continues where it left off.

    python scripts/collect_judgments.py sci hc:delhi hc:jkl hc:ph hc:allahabad

Progress: state/logs/collect.log and state/collect_progress.json. The kept judgments are pushed to the
`raw-data` branch after every few court-years and when each court finishes (scripts/push_data.py).  Stop cleanly: create state/collect.stop
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable
LOG = ROOT / "state" / "logs" / "collect.log"
PROGRESS = ROOT / "state" / "collect_progress.json"
STOP = ROOT / "state" / "collect.stop"
YEARS = range(2026, 1949, -1)              # newest first
WORKERS = "8"
PUSH_EVERY = 8                             # court-years with downloads between checkpoint pushes


def say(msg: str) -> None:
    line = f"{datetime.now(timezone.utc).isoformat(timespec='seconds')} {msg}"
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    print(line, flush=True)


def run(*args: str) -> tuple[int, str]:
    p = subprocess.run([PY, "-W", "ignore", "-m", *args], cwd=ROOT, capture_output=True, text=True)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def last_json(out: str) -> dict:
    i = out.rfind("\n{")
    try:
        return json.loads(out[i:] if i >= 0 else out[out.index("{"):])
    except (ValueError, json.JSONDecodeError):
        return {}


def process(tag: str) -> dict:
    """records -> extract -> relevance for whatever has been downloaded."""
    for stage in ("records", "extract"):
        rc, out = run("pipeline", stage)
        if rc != 0:
            say(f"{tag}: pipeline {stage} failed: {out[-400:]}")
            return {}
    rc, out = run("pipeline", "relevance")
    line = next((l for l in out.splitlines() if l.startswith("relevance:")), "")
    return json.loads(line.split(":", 1)[1]) if line else {}


def checkpoint(label: str) -> None:
    """Push what the corpus holds now to the raw-data branch."""
    p = subprocess.run([PY, str(ROOT / "scripts" / "push_data.py"), label], cwd=ROOT, capture_output=True, text=True)
    say(f"checkpoint push ({label}): rc={p.returncode} {(p.stdout or p.stderr).strip().splitlines()[-1:] or ''}")


def collect(source: str, slices: list[str], done: dict) -> None:
    since_push = 0
    for s in slices:
        key = f"{source}:{s}"
        if STOP.exists():
            say("stop file found; stopping")
            return
        if done.get(key, {}).get("finished"):
            continue
        rc, out = run("crawler", "discover", "--source", source, "--only", s, "--json")
        info = last_json(out) if rc == 0 else {}
        status = next(iter(info.get("targets", {}).values()), None) if info else None
        if rc != 0 or status in ("failed", "blocked", "skipped"):
            say(f"{key}: discover did not complete (rc={rc}, {status}); will retry on the next run: {out[-300:]!r}")
            continue
        queued = info.get("plan", {}).get("totals", {}).get("would_fetch", 0)
        fetched = {}
        if queued:
            rc, out = run("crawler", "fetch", "--source", source, "--yes-download", "--limit", "200000", "--workers", WORKERS)
            fetched = last_json(out)
        rel = process(key) if queued else {}
        done[key] = {"finished": True, "index_status": status, "queued": queued,
                     "downloaded": fetched.get("downloaded"), "failed": fetched.get("failed"),
                     "retry_later": fetched.get("retry_later"), "kept_relevant": rel.get("relevant"),
                     "kept_borderline": rel.get("borderline"), "removed_total": rel.get("removed_as_not_military_total"),
                     "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        PROGRESS.write_text(json.dumps(done, indent=1), encoding="utf-8")
        since_push += 1 if queued else 0
        if since_push >= PUSH_EVERY:
            checkpoint(f"after {key}")
            since_push = 0
        say(f"{key}: index {status}; downloaded {fetched.get('downloaded', 0)} "
            f"(failed {fetched.get('failed', 0)}); corpus now relevant={rel.get('relevant')} "
            f"borderline={rel.get('borderline')} removed={rel.get('removed_as_not_military_total')}")


def main(argv: list[str]) -> int:
    done = json.loads(PROGRESS.read_text(encoding="utf-8")) if PROGRESS.exists() else {}
    t0 = time.time()
    for target in argv or ["sci"]:
        if STOP.exists():
            break
        if target == "sci":
            collect("sci", ["1950-2026"], done)
        elif target.startswith("hc:"):
            court = target.split(":", 1)[1]
            collect("hc", [f"{court}:{y}" for y in YEARS], done)
        else:
            say(f"unknown target {target!r}")
            continue
        rc, out = run("pipeline", "all")                 # full rebuild, validation and report after each court
        checkpoint(f"{target} finished")
        say(f"{target}: finished; pipeline all rc={rc}; " + " | ".join(l for l in out.splitlines() if l.startswith(("validate", "relevance"))))
    say(f"done in {(time.time() - t0) / 3600:.1f} h")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
