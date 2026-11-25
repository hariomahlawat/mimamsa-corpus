"""R2-N01 checks against an INSTALLED, supervisor-managed service (Windows Service under NT SERVICE\\... in CI).
The service must already run in test mode with a seed (see install step). Crash = kill the service process and let
the supervisor (SCM failure actions) restart it.

python test_service_r2n01.py --base http://127.0.0.1:5081 --db "<libpq>" --pid-cmd "<command printing service PID>"
       --seed <seed.json used by the service> --out result.json
"""
import argparse, hashlib, json, os, shlex, signal, socket, struct, subprocess, sys, time, urllib.request
from pathlib import Path
import psycopg

ap = argparse.ArgumentParser()
ap.add_argument("--base", required=True); ap.add_argument("--db", required=True); ap.add_argument("--pid-cmd"); ap.add_argument("--service-name")
ap.add_argument("--seed", required=True); ap.add_argument("--out", required=True)
A = ap.parse_args()
HOST, PORT = A.base.split("//")[1].split(":"); PORT = int(PORT)
seed = json.loads(Path(A.seed).read_text())
cp = {c["doc_id"]: c for c in seed["copies"]}
BIG = Path(cp["doc-svc-big"]["source"]).read_bytes(); BIG_SHA = cp["doc-svc-big"]["sha256"]
W = Path(cp["doc-svc-w"]["source"]).read_bytes(); W_SHA = cp["doc-svc-w"]["sha256"]
R = {"platform": sys.platform, "checks": []}


def check(name, ok, **d):
    R["checks"].append({"name": name, "pass": bool(ok), **d}); print(("PASS " if ok else "FAIL ") + name, "" if ok else d, flush=True)


def req(path, token=None, rng=None, method="GET", extra=None, timeout=20):
    s = socket.create_connection((HOST, PORT), timeout=timeout)
    h = [f"{method} {path} HTTP/1.1", "Host: x", "Connection: close"]
    if token: h.append(f"Authorization: Bearer {token}")
    if rng: h.append(f"Range: {rng}")
    for k, v in (extra or {}).items(): h.append(f"{k}: {v}")
    s.sendall(("\r\n".join(h) + "\r\n\r\n").encode())
    data = b""
    try:
        while True:
            c = s.recv(65536)
            if not c: break
            data += c
    except (ConnectionResetError, socket.timeout):
        pass
    s.close()
    head, _, body = data.partition(b"\r\n\r\n")
    lines = head.decode("latin-1").split("\r\n")
    st = int(lines[0].split()[1]) if lines and lines[0] else 0
    hd = {l.split(":", 1)[0].strip().lower(): l.split(":", 1)[1].strip() for l in lines[1:] if ":" in l}
    if hd.get("transfer-encoding", "").lower() == "chunked":
        out, rest = b"", body
        while rest:
            sz, _, rest = rest.partition(b"\r\n"); n = int(sz.split(b";")[0] or b"0", 16)
            if n == 0: break
            out += rest[:n]; rest = rest[n + 2:]
        body = out
    return st, hd, body


def ledger():
    with psycopg.connect(A.db) as c:
        return c.execute("SELECT reserved, charged FROM credit_pools WHERE pool_id='site'").fetchone()


def pid():
    if A.service_name:   # Windows: ask the Service Control Manager
        out = subprocess.run(["sc", "queryex", A.service_name], capture_output=True, text=True).stdout
        for line in out.splitlines():
            if line.strip().upper().startswith("PID"):
                return int(line.split(":")[1].strip())
        return 0
    return int(subprocess.run(shlex.split(A.pid_cmd), capture_output=True, text=True).stdout.strip() or 0)


def healthy(timeout=60):
    t = time.time()
    while time.time() - t < timeout:
        try:
            if urllib.request.urlopen(A.base + "/health", timeout=1).status == 200: return True
        except Exception: time.sleep(0.2)
    return False


RANGE = lambda d, sh: f"/api/v2/documents/{d}/copies/{sh}/range"
assert healthy()
# protected delivery + negatives under the service account
st, h, b = req(RANGE("doc-svc-big", BIG_SHA), "tok-alice", "bytes=0-131071")
check("svc_exact_206", st == 206 and b == BIG[:131072] and h.get("content-range") == f"bytes 0-131071/{len(BIG)}", status=st)
st, h, b = req(RANGE("doc-svc-big", BIG_SHA), "tok-alice", f"bytes={len(BIG) - 500}-{len(BIG) - 1}")
check("svc_near_end_206", st == 206 and b == BIG[-500:], status=st)
for name, tok, rng, want in [("svc_unauth_401", None, "bytes=0-9", 401), ("svc_other_user_404", "tok-bob", "bytes=0-9", 404),
                             ("svc_oversize_400", "tok-alice", "bytes=0-131072", 400), ("svc_oob_416", "tok-alice", f"bytes={len(BIG)}-{len(BIG)+5}", 416)]:
    st, h, b = req(RANGE("doc-svc-big", BIG_SHA), tok, rng); check(name, st == want and not b, status=st)
st, h, b = req("/api/search?q=disability%20pension", "dev-token"); check("svc_positive_control_search_200", st == 200, status=st)

# F01 under the service
e0 = json.loads(req("/admin/ledger", "tok-admin")[2])["epoch"]
st, h, b = req(f"/admin/withdraw?doc=doc-svc-w&sha={'f' * 64}", "tok-admin", method="POST")
check("svc_F01_unknown_copy_404_no_epoch_bump", st == 404 and json.loads(req("/admin/ledger", "tok-admin")[2])["epoch"] == e0, status=st)

# F05: real UNCERTAIN over HTTP (client abort mid-body with a blocked flush; service has a 4 KiB send buffer)
s = socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4096); s.connect((HOST, PORT))
s.sendall((f"GET {RANGE('doc-svc-big', BIG_SHA)} HTTP/1.1\r\nHost: x\r\nAuthorization: Bearer tok-alice\r\nRange: bytes=200000-331071\r\n\r\n").encode())
s.recv(1024); time.sleep(1.0)
s.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("HH" if os.name == "nt" else "ii", 1, 0)); s.close()
time.sleep(2.0)
with psycopg.connect(A.db) as c:
    unc = c.execute("SELECT count(*) FROM credit_reservations WHERE range_start >= 200000 AND range_start < 331072 AND reason LIKE 'uncertain:%%'").fetchone()[0]
    released = c.execute("SELECT count(*) FROM credit_reservations WHERE range_start >= 200000 AND range_start < 331072 AND state='RELEASED'").fetchone()[0]
check("svc_F05_uncertain_transfer_recorded", unc >= 1 and released == 0, uncertain=unc, released=released)

# withdrawal with egress cut, then crash + SCM restart: durable fence + charges + F04 seed does not revert
s = socket.socket(); s.connect((HOST, PORT))
s.sendall((f"GET {RANGE('doc-svc-big', BIG_SHA)} HTTP/1.1\r\nHost: x\r\nAuthorization: Bearer tok-alice\r\nRange: bytes=400000-531071\r\n\r\n").encode())
s.recv(1024); time.sleep(0.7)
st, h, b = req(f"/admin/withdraw?doc=doc-svc-w&sha={W_SHA}", "tok-admin", method="POST")
check("svc_withdraw_ok", st == 200 and json.loads(b).get("changed") is True, status=st)
st, h, b = req(RANGE("doc-svc-w", W_SHA), "tok-alice", "bytes=0-99"); check("svc_withdrawn_404", st == 404, status=st)
p0 = pid(); charged_before = sum(ledger())
os.kill(p0, signal.SIGTERM if os.name == "nt" else signal.SIGKILL)   # TerminateProcess on Windows
t0 = time.time(); p1 = 0
while time.time() - t0 < 60:
    p1 = pid()
    if p1 and p1 != p0 and healthy(2): break
    time.sleep(0.5)
check("svc_crash_supervisor_restart", p1 and p1 != p0, pid_before=p0, pid_after=p1, seconds=round(time.time() - t0, 2))
held = sum(ledger())
check("svc_F02_charge_survives_crash_restart", held > 0 and held >= charged_before - 1, charged_before=charged_before, held=held)
st, h, b = req(RANGE("doc-svc-w", W_SHA), "tok-alice", "bytes=0-99"); check("svc_F04_withdrawal_survives_restart_with_seed", st == 404, status=st)
st, h, b = req(RANGE("doc-svc-big", BIG_SHA), "tok-alice", "bytes=0-99"); check("svc_unrelated_after_restart_206", st == 206 and b == BIG[:100], status=st)
s.settimeout(5)
try:
    while s.recv(65536): pass
except (ConnectionResetError, socket.timeout): pass
s.close()
t0 = time.time()
while time.time() - t0 < 30 and sum(ledger()) > 0: time.sleep(0.5)
check("svc_F02_release_after_socket_evidence", sum(ledger()) == 0, remaining=ledger(), seconds=round(time.time() - t0, 2))
R["all_pass"] = all(c["pass"] for c in R["checks"])
Path(A.out).write_text(json.dumps(R, indent=1, default=str))
print("ALL PASS" if R["all_pass"] else "SOME FAILED", len(R["checks"]))
sys.exit(0 if R["all_pass"] else 1)
