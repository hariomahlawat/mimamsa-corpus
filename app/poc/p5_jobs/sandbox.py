"""Run an untrusted PDF parse in a separate low-privilege subprocess with a wall-clock timeout, an address-space
cap, a CPU-time cap, no network namespace (when available), an empty environment and an empty working dir.

Linux implementation (measured here). Windows equivalent (design only): CreateProcessAsUser with a restricted
token or AppContainer, assigned to a Job Object with JOB_OBJECT_LIMIT_PROCESS_MEMORY, JOB_OBJECT_LIMIT_JOB_TIME,
JOB_OBJECT_LIMIT_ACTIVE_PROCESS=1 and KILL_ON_JOB_CLOSE; outbound network blocked by a firewall rule for the
sandbox executable; the worker service itself runs as a dedicated virtual account (NT SERVICE\\MimamsaWorker).
"""
from __future__ import annotations

import json
import os
import resource
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

CHILD = Path(__file__).resolve().parent / "parse_child.py"
NOBODY_UID = 65534
# The sandbox runtime is a separate, world-readable, read-only deployment (interpreter + parser library only).
SANDBOX_PYTHON = os.environ.get("MIMAMSA_SANDBOX_PYTHON", "/usr/bin/python3.12")
SANDBOX_SITE = os.environ.get("MIMAMSA_SANDBOX_SITE", "/var/tmp/c13-bpoc-sbx/site")


def run_sandboxed(pdf_path: str, timeout_s: float = 20, mem_mb: int = 768, cpu_s: int = 30, mode: str = "parse"):
    work = tempfile.mkdtemp(prefix="mimamsa-sbx-")
    src = Path(work) / "input.pdf"
    if pdf_path:
        shutil.copyfile(pdf_path, src)
    os.chmod(work, 0o755); os.chmod(src, 0o644) if src.exists() else None
    child_copy = Path(work) / "parse_child.py"
    shutil.copyfile(CHILD, child_copy); os.chmod(child_copy, 0o644)

    def limits():
        resource.setrlimit(resource.RLIMIT_AS, (mem_mb * 2**20, mem_mb * 2**20))
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_s, cpu_s))
        resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
        resource.setrlimit(resource.RLIMIT_FSIZE, (50 * 2**20, 50 * 2**20))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        os.setsid()
        if os.geteuid() == 0 and hasattr(os, "unshare"):
            os.unshare(os.CLONE_NEWNET)  # empty network namespace (no interfaces): no network at all
        if os.geteuid() == 0:            # drop root -> nobody
            os.setgroups([]); os.setgid(NOBODY_UID); os.setuid(NOBODY_UID)

    cmd = [SANDBOX_PYTHON, "-S", str(child_copy), str(src), mode]
    try:
        p = subprocess.run(cmd, cwd=work, env={"PATH": "/usr/bin:/bin", "PYTHONPATH": SANDBOX_SITE, "PYTHONNOUSERSITE": "1"},
                           stdin=subprocess.DEVNULL, capture_output=True, timeout=timeout_s, preexec_fn=limits)
        out = dict(returncode=p.returncode, stderr_tail=p.stderr.decode("utf-8", "replace")[-300:])
        if p.returncode == 0:
            out["result"] = json.loads(p.stdout[:5_000_000])
        elif p.returncode < 0:
            out["killed_by_signal"] = -p.returncode
        return out
    except subprocess.TimeoutExpired:
        return dict(returncode=None, timeout=True)
    finally:
        shutil.rmtree(work, ignore_errors=True)
