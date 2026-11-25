"""Run a command against a disposable B1 service on loopback.

  python app/b1/tests/b1server.py --site <importer site> --db "<npgsql dsn>" [--port 5299] [--dll path] -- <command...>

Starts Mimamsa.Web in TEST mode (state reset, seeded test accounts admin/reader with fixed test passwords, test
hooks enabled), waits for /health, runs the command with B1_URL set, then stops the service. Exit code is the
command's. Test accounts and hooks exist only in test mode; the service refuses seeded accounts otherwise.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_DLL = HERE.parent / "src" / "Mimamsa.Web" / "bin" / "Release" / "net10.0" / "Mimamsa.Web.dll"
USERS = ["admin:Admin:admin-password-1", "reader:User:reader-password-1"]


def start(site: str, db: str, port: int, dll: Path, log: Path, trace: str | None = None) -> subprocess.Popen:
    env = dict(os.environ)
    env.update({"ASPNETCORE_URLS": f"http://127.0.0.1:{port}", "Mimamsa__Site": site, "Mimamsa__Db": db,
                "Mimamsa__Test__Enabled": "true", "Mimamsa__Test__ResetLedger": "true", "Mimamsa__Test__ResetState": "true",
                "DOTNET_CLI_TELEMETRY_OPTOUT": "1", "DOTNET_NOLOGO": "1"})
    for i, u in enumerate(USERS):
        env[f"Mimamsa__Test__Users__{i}"] = u
    if trace:
        env["Mimamsa__Trace__Path"] = trace
    dotnet = os.environ.get("DOTNET", "dotnet")
    cwd = dll.parent if (dll.parent / "wwwroot").exists() else dll.parent.parent.parent.parent
    proc = subprocess.Popen([dotnet, str(dll)], cwd=str(cwd), env=env,
                            stdout=open(log, "w"), stderr=subprocess.STDOUT)
    for _ in range(240):
        try:
            if urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1).status == 200:
                return proc
        except Exception:
            pass
        if proc.poll() is not None:
            raise RuntimeError(f"service exited early; see {log}")
        time.sleep(0.5)
    proc.kill()
    raise RuntimeError(f"service did not become healthy; see {log}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True)
    ap.add_argument("--db", required=True)
    ap.add_argument("--port", type=int, default=5299)
    ap.add_argument("--dll", type=Path, default=DEFAULT_DLL)
    ap.add_argument("--log", type=Path, default=Path("b1-service.log"))
    ap.add_argument("--trace")
    ap.add_argument("cmd", nargs=argparse.REMAINDER)
    a = ap.parse_args()
    cmd = a.cmd[1:] if a.cmd and a.cmd[0] == "--" else a.cmd
    proc = start(a.site, a.db, a.port, a.dll, a.log, a.trace)
    try:
        env = dict(os.environ, B1_URL=f"http://127.0.0.1:{a.port}")
        return subprocess.call(cmd, env=env) if cmd else 0
    finally:
        proc.terminate()
        try:
            proc.wait(10)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    sys.exit(main())
