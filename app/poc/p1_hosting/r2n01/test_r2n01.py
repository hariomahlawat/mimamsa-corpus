"""R2-N01 transport tests against the running ASP.NET Core PoC (Linux now; same script on Windows CI).

python test_r2n01.py --server-cmd "<dotnet> MimamsaPocApi.dll" --server-cwd <publish dir> --db "<libpq dsn>" \
       --big <pdf> --small <pdf> --out <result.json> [--port 5181]

Each scenario starts the server with its own configuration (env vars), so caps and buffers are explicit.
Independent observation: the test reads the PostgreSQL ledger tables directly and checks HTTP bytes against the
source file; it does not trust the server's own success flags.
"""
import argparse, hashlib, json, os, shlex, signal, socket, struct, subprocess, sys, threading, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import psycopg

ap = argparse.ArgumentParser()
ap.add_argument("--server-cmd", required=True); ap.add_argument("--server-cwd", required=True)
ap.add_argument("--db", required=True); ap.add_argument("--npgsql", required=True)
ap.add_argument("--big", required=True); ap.add_argument("--small", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--port", type=int, default=5181); ap.add_argument("--work", default=None)
A = ap.parse_args()
BASE = f"http://127.0.0.1:{A.port}"
WORK = Path(A.work or Path(A.out).parent / "r2n01_work"); WORK.mkdir(parents=True, exist_ok=True)
KiB = 1024
MAXR = 128 * KiB
RESULTS = {"platform": sys.platform, "checks": [], "scenarios": {}}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


BIG, SMALL = Path(A.big).read_bytes(), Path(A.small).read_bytes()
BIG_SHA, SMALL_SHA = hashlib.sha256(BIG).hexdigest(), hashlib.sha256(SMALL).hexdigest()
SEED = {
    "sessions": [{"token": "tok-alice", "user": "alice", "session": "s-alice"},
                 {"token": "tok-bob", "user": "bob", "session": "s-bob"},
                 {"token": "tok-admin", "user": "admin", "session": "s-admin", "admin": True}],
    "copies": [{"doc_id": "doc-big", "source": str(Path(A.big).resolve()), "sha256": BIG_SHA},
               {"doc_id": "doc-small", "source": str(Path(A.small).resolve()), "sha256": SMALL_SHA}],
    "grants": [{"user": "alice", "doc_id": "doc-big"}, {"user": "alice", "doc_id": "doc-small"},
               {"user": "bob", "doc_id": "doc-small"}],
}
(WORK / "seed.json").write_text(json.dumps(SEED))


def check(name, ok, **detail):
    RESULTS["checks"].append({"name": name, "pass": bool(ok), **detail})
    print(("PASS " if ok else "FAIL ") + name, detail if not ok else "", flush=True)


def start(scenario, reset=True, **cfg):
    env = dict(os.environ)
    env.update({"ASPNETCORE_URLS": BASE, "Urls": BASE, "Mimamsa__Db": A.npgsql, "Mimamsa__SeedFile": str(WORK / "seed.json"),
                "Mimamsa__VaultRoot": str(WORK / "vault"), "Mimamsa__Test__ResetLedger": "true" if reset else "false",
                "Mimamsa__Test__Enabled": "true", "Mimamsa__Test__ReconcileMinAgeSec": "3"})
    for k, v in cfg.items():
        env["Mimamsa__" + k.replace(".", "__")] = str(v)
    log = open(WORK / f"server-{scenario}.log", "ab")
    p = subprocess.Popen(shlex.split(A.server_cmd, posix=os.name != "nt"), cwd=A.server_cwd, env=env, stdout=log, stderr=log)
    for _ in range(300):
        try:
            if urllib.request.urlopen(BASE + "/health", timeout=1).status == 200:
                return p
        except Exception:
            time.sleep(0.1)
    raise RuntimeError("server did not start")


def stop(p, hard=False):
    if hard:
        p.kill()
    else:
        p.terminate()
    try:
        p.wait(15)
    except subprocess.TimeoutExpired:
        p.kill(); p.wait()


def req(path, token=None, rng=None, method="GET", extra=None, timeout=30):
    """Minimal HTTP/1.1 client (raw socket) so that headers and exact body bytes are observed independently."""
    s = socket.create_connection(("127.0.0.1", A.port), timeout=timeout)
    h = [f"{method} {path} HTTP/1.1", f"Host: 127.0.0.1:{A.port}", "Connection: close"]
    if token: h.append(f"Authorization: Bearer {token}")
    if rng: h.append(f"Range: {rng}")
    for k, v in (extra or {}).items(): h.append(f"{k}: {v}")
    s.sendall(("\r\n".join(h) + "\r\n\r\n").encode())
    data = b""
    while True:
        try:
            c = s.recv(65536)
        except (ConnectionResetError, socket.timeout):
            break
        if not c: break
        data += c
    s.close()
    head, _, body = data.partition(b"\r\n\r\n")
    lines = head.decode("latin-1").split("\r\n")
    status = int(lines[0].split()[1]) if lines and lines[0] else 0
    hdrs = {}
    for l in lines[1:]:
        k, _, v = l.partition(":"); hdrs[k.strip().lower()] = v.strip()
    if hdrs.get("transfer-encoding", "").lower() == "chunked":
        out, rest = b"", body
        while rest:
            size_line, _, rest = rest.partition(b"\r\n")
            n = int(size_line.split(b";")[0] or b"0", 16)
            if n == 0: break
            out += rest[:n]; rest = rest[n + 2:]
        body = out
    return status, hdrs, body


def ledger():
    with psycopg.connect(A.db) as c:
        site = c.execute("SELECT cap, reserved, charged FROM credit_pools WHERE pool_id='site'").fetchone()
        states = dict(c.execute("SELECT state, count(*) FROM credit_reservations GROUP BY state").fetchall())
    return {"cap": site[0], "reserved": site[1], "charged": site[2], "states": states}


def rows(where="true"):
    with psycopg.connect(A.db) as c:
        cur = c.execute(f"SELECT res_id, state, amount, charged, accepted_bytes, reason, range_start, instance_id FROM credit_reservations WHERE {where} ORDER BY created_at")
        return [dict(zip(["res_id", "state", "amount", "charged", "accepted", "reason", "start", "instance"], r)) for r in cur.fetchall()]


RANGE = lambda d, sh: f"/api/v2/documents/{d}/copies/{sh}/range"
META = lambda d: f"/api/v2/documents/{d}/pdf-meta"

# =============================================================== A. functional + negative
p = start("A")
try:
    st, h, b = req(META("doc-big"), "tok-alice")
    m = json.loads(b or b"{}")
    check("meta_authorized_ok", st == 200 and m.get("copy_sha256") == BIG_SHA and m.get("length") == len(BIG) and "no-store" in h.get("cache-control", ""), status=st)
    for name, tok in [("meta_unauthenticated_401", None), ("meta_bad_token_401", "nope")]:
        st, h, b = req(META("doc-big"), tok); check(name, st == 401 and not b, status=st)
    st, h, b = req(META("doc-big"), "tok-bob"); check("meta_other_users_doc_404_no_size", st == 404 and not b and "content-range" not in h, status=st)

    st, h, b = req(RANGE("doc-big", BIG_SHA), "tok-alice", "bytes=0-65535")
    check("range_first_chunk_exact_206", st == 206 and b == BIG[:65536] and h.get("content-range") == f"bytes 0-65535/{len(BIG)}"
          and h.get("content-length") == "65536" and "etag" not in h and "last-modified" not in h
          and "no-store" in h.get("cache-control", "") and h.get("connection", "").lower() == "close" and "content-encoding" not in h, status=st, headers=h)
    a0 = len(BIG) - 1000
    st, h, b = req(RANGE("doc-big", BIG_SHA), "tok-alice", f"bytes={a0}-{len(BIG) - 1}")
    check("range_near_end_exact_206", st == 206 and b == BIG[a0:], status=st)
    st, h, b = req(RANGE("doc-big", BIG_SHA), "tok-alice", f"bytes=1000-{1000 + MAXR - 1}")
    check("range_max_size_exact_206", st == 206 and b == BIG[1000:1000 + MAXR], status=st, got=len(b))
    negatives = [("range_missing_400", None, 400), ("range_multi_400", "bytes=0-10,20-30", 400), ("range_open_ended_400", "bytes=0-", 400),
                 ("range_suffix_400", "bytes=-500", 400), ("range_oversized_400", f"bytes=0-{MAXR}", 400),
                 ("range_malformed_400", "items=0-10", 400), ("range_reversed_400", "bytes=10-5", 400),
                 ("range_start_out_of_bounds_416", f"bytes={len(BIG)}-{len(BIG) + 10}", 416),
                 ("range_end_out_of_bounds_416", f"bytes={len(BIG) - 10}-{len(BIG) + 10}", 416)]
    for name, rg, want in negatives:
        st, h, b = req(RANGE("doc-big", BIG_SHA), "tok-alice", rg)
        ok = st == want and not b and (want != 416 or h.get("content-range") == f"bytes */{len(BIG)}")
        check(name, ok, status=st, body_len=len(b))
    for name, tok, doc, sh in [("range_unauthenticated_401", None, "doc-big", BIG_SHA), ("range_bad_token_401", "forged", "doc-big", BIG_SHA),
                               ("range_other_users_session_404", "tok-bob", "doc-big", BIG_SHA),
                               ("range_wrong_copy_for_doc_404", "tok-alice", "doc-small", BIG_SHA),
                               ("range_non_hex_address_404", "tok-alice", "doc-big", "../../etc/passwd")]:
        st, h, b = req(RANGE(doc, sh), tok, "bytes=0-1023")
        check(name, st in ((401,) if "401" in name else (404, 400)) and not b and "content-range" not in h, status=st)
    for name, extra in [("conditional_if_none_match_no_304", {"If-None-Match": "*"}), ("conditional_if_modified_since_no_304", {"If-Modified-Since": "Wed, 01 Jan 2031 00:00:00 GMT"}),
                        ("conditional_if_range_ignored", {"If-Range": '"x"'})]:
        st, h, b = req(RANGE("doc-big", BIG_SHA), "tok-alice", "bytes=0-99", extra=extra)
        check(name, st == 206 and b == BIG[:100], status=st)
    st, h, b = req(f"/api/documents/doc-big/pdf", None); check("v1_static_route_not_a_vault_bypass", st in (401, 404), status=st)
    # withdrawal fence: small doc withdrawn; unrelated eligible doc keeps working (positive control)
    st, h, b = req(RANGE("doc-small", SMALL_SHA), "tok-bob", "bytes=0-99"); check("small_doc_before_withdrawal_206", st == 206 and b == SMALL[:100], status=st)
    st, h, b = req(f"/admin/withdraw?doc=doc-small&sha={SMALL_SHA}", "tok-alice", method="POST"); check("withdraw_requires_admin", st == 401, status=st)
    def ep_now(): return json.loads(req("/admin/ledger", "tok-admin")[2])["epoch"]
    e0 = ep_now()
    st, h, b = req(f"/admin/withdraw?doc=doc-small&sha={'0' * 64}", "tok-admin", method="POST")
    check("F01_withdraw_unknown_copy_404_typed_no_epoch_bump", st == 404 and b"unknown_copy" in b and ep_now() == e0, status=st, body=b[:80])
    st, h, b = req(f"/admin/withdraw?doc=doc-nope&sha={SMALL_SHA}", "tok-admin", method="POST")
    check("F01_withdraw_unknown_doc_404_no_epoch_bump", st == 404 and ep_now() == e0, status=st)
    st, h, b = req("/admin/withdraw?doc=doc-small&sha=xyz", "tok-admin", method="POST")
    check("F01_withdraw_invalid_sha_400", st == 400 and b"invalid_copy_identity" in b and ep_now() == e0, status=st)
    # wrong-case sha is canonicalised: the right copy is withdrawn and is no longer served
    st, h, b = req(f"/admin/withdraw?doc=doc-small&sha={SMALL_SHA.upper()}", "tok-admin", method="POST")
    wj = json.loads(b or b"{}")
    check("withdraw_admin_ok", st == 200 and wj.get("changed") is True and ep_now() == e0 + 1, status=st, body=b[:120])
    st, h, b = req(f"/admin/withdraw?doc=doc-small&sha={SMALL_SHA}", "tok-admin", method="POST")
    check("F01_repeat_withdraw_idempotent_no_epoch_bump", st == 200 and b'"already_withdrawn"' in b and ep_now() == e0 + 1, status=st)
    st, h, b = req(RANGE("doc-small", SMALL_SHA), "tok-bob", "bytes=0-99"); check("after_withdrawal_range_404_no_bytes", st == 404 and not b, status=st)
    st, h, b = req(META("doc-small"), "tok-bob"); check("after_withdrawal_meta_404", st == 404, status=st)
    st, h, b = req(RANGE("doc-big", BIG_SHA), "tok-alice", "bytes=0-99"); check("unrelated_eligible_doc_still_206", st == 206 and b == BIG[:100], status=st)
    time.sleep(1.0)
    L = ledger(); check("ledger_balances_after_functional_suite", L["reserved"] == 0 and L["charged"] == 0, ledger=L)
    RESULTS["scenarios"]["A_functional"] = {"ledger_end": L}
finally:
    stop(p)
# F04: restart with the SAME seed file configured (no reset): durable withdrawal must stay authoritative
p = start("A2", reset=False)
try:
    st, h, b = req(RANGE("doc-small", SMALL_SHA), "tok-bob", "bytes=0-99")
    check("F04_seed_on_restart_does_not_revert_withdrawal", st == 404 and not b, status=st)
    st, h, b = req(RANGE("doc-big", BIG_SHA), "tok-alice", "bytes=0-99")
    check("F04_unrelated_copy_after_restart_206", st == 206 and b == BIG[:100], status=st)
finally:
    stop(p)

# =============================================================== B. concurrency: never overcommit
def sampler(stop_ev, out):
    mx, n, viol = 0, 0, 0
    with psycopg.connect(A.db, autocommit=True) as c:
        while not stop_ev.is_set():
            for pid, cap, r, ch in c.execute("SELECT pool_id, cap, reserved, charged FROM credit_pools").fetchall():
                if r + ch > cap or r < 0 or ch < 0: viol += 1
                if pid == "site": mx = max(mx, r + ch)
            n += 1
    out.update(max_site_outstanding=mx, samples=n, violations=viol)


# B1 = Serving §10 synthetic oracle over HTTP: site credit for exactly one 64 KiB attempt, 40 simultaneous contenders
for label, site_cap, nreq, threads, maxr in [("B1_site_cap_one_64KiB_attempt", 64 * KiB, 40, 40, 63 * KiB),
                                             ("B2_site_cap_1MiB", 1024 * KiB, 400, 32, MAXR)]:
    p = start(label, **{"Credit.SiteCap": site_cap, "Delivery.DrainGraceMs": 50, "Delivery.MaxRange": maxr,
                        "Delivery.SlotGate": "false" if label.startswith("B1") else "true"})
    try:
        stop_ev, samp = threading.Event(), {}
        th = threading.Thread(target=sampler, args=(stop_ev, samp)); th.start()
        import random
        rnd = random.Random(7)
        specs = []
        for i in range(nreq):
            ln = maxr if label.startswith("B1") else rnd.randint(1, maxr)
            a0 = rnd.randint(0, len(BIG) - ln); specs.append((a0, a0 + ln - 1))
        def one(sp):
            st, h, b = req(RANGE("doc-big", BIG_SHA), "tok-alice", f"bytes={sp[0]}-{sp[1]}")
            return st, (st != 206 or b == BIG[sp[0]:sp[1] + 1]), (st == 503 and not b) or st == 206
        t0 = time.perf_counter()
        with ThreadPoolExecutor(threads) as ex:
            out = list(ex.map(one, specs))
        wall = time.perf_counter() - t0
        time.sleep(1.0); stop_ev.set(); th.join()
        L = ledger()
        n206 = sum(1 for s, _, _ in out if s == 206); n503 = sum(1 for s, _, _ in out if s == 503)
        res = dict(requests=nreq, threads=threads, site_cap=site_cap, ok_206=n206, denied_503=n503, other=nreq - n206 - n503,
                   all_206_bodies_exact=all(x for _, x, _ in out), wall_s=round(wall, 2), ledger_end=L, **samp)
        RESULTS["scenarios"][label] = res
        check(f"{label}_never_overcommits", samp["violations"] == 0 and samp["max_site_outstanding"] <= site_cap and res["other"] == 0
              and res["all_206_bodies_exact"] and n206 > 0 and L["reserved"] == 0 and L["charged"] == 0, **res)
    finally:
        stop(p)

# =============================================================== C. killed connections: conservative settlement
def slow_then_kill(rng, read_bytes, pause):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4096)
    s.connect(("127.0.0.1", A.port))
    s.sendall((f"GET {RANGE('doc-big', BIG_SHA)} HTTP/1.1\r\nHost: x\r\nAuthorization: Bearer tok-alice\r\nRange: {rng}\r\n\r\n").encode())
    got = b""
    while len(got) < read_bytes:
        c = s.recv(min(1024, read_bytes - len(got)))
        if not c: break
        got += c
    time.sleep(pause)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("HH" if os.name == "nt" else "ii", 1, 0))   # RST on close
    s.close()
    return len(got)


p = start("C", **{"Transport.ListenSendBufferBytes": 4096, "Delivery.DrainGraceMs": 3000})
try:
    trials = []
    for i in range(8):
        a0 = 100_000 + i * 7
        got = slow_then_kill(f"bytes={a0}-{a0 + MAXR - 1}", 2048, 1.0)
        time.sleep(0.5)                     # after the kill, before the drain grace expires
        r = rows(f"range_start = {a0}")
        L_mid = ledger()
        time.sleep(3.5)                     # grace (3 s) + margin
        r2 = rows(f"range_start = {a0}")
        L_end = ledger()
        trials.append(dict(received=got, mid_state=r[0]["state"] if r else None, mid_charged=r[0]["charged"] if r else None,
                           amount=r[0]["amount"] if r else None, mid_site_charged=L_mid["charged"], mid_site_reserved=L_mid["reserved"],
                           end_state=r2[0]["state"] if r2 else None, end_reason=(r2[0]["reason"] or "")[-160:] if r2 else None,
                           end_site=dict(reserved=L_end["reserved"], charged=L_end["charged"])))
    ok = all(t["mid_state"] in ("UNCERTAIN", "RESERVED", "ACCEPTED") and t["mid_site_charged"] + t["mid_site_reserved"] >= t["amount"]
             and t["end_state"] == "DRAINED" and "drained:" in (t["end_reason"] or "") and t["end_site"] == {"reserved": 0, "charged": 0}
             for t in trials)
    RESULTS["scenarios"]["C_killed_connections"] = {"trials": trials, "uncertain_count": sum(t["mid_state"] == "UNCERTAIN" for t in trials)}
    check("killed_connection_charge_retained_until_termination_then_drained", ok, uncertain=sum(t["mid_state"] == "UNCERTAIN" for t in trials), n=len(trials))
    check("killed_connection_never_refunded_as_zero_transfer", not rows("state = 'RELEASED'"), released=len(rows("state = 'RELEASED'")))
    with psycopg.connect(A.db) as c_:
        unc_rows = c_.execute("SELECT count(*) FROM credit_reservations WHERE reason LIKE 'uncertain:%%'").fetchone()[0]
    RESULTS["scenarios"]["C_killed_connections"]["uncertain_rows_total"] = unc_rows
    check("F05_real_uncertain_transfer_over_http", unc_rows >= 1, uncertain_rows=unc_rows)

    # withdrawal between slices of one response: the second slice must not be handed off after the fence
    s = socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4096); s.connect(("127.0.0.1", A.port))
    a0 = 300_000
    s.sendall((f"GET {RANGE('doc-big', BIG_SHA)} HTTP/1.1\r\nHost: x\r\nAuthorization: Bearer tok-alice\r\nX-Mimamsa-Test-Pause: after-first-slice\r\nRange: bytes={a0}-{a0 + MAXR - 1}\r\n\r\n").encode())
    first = s.recv(1024)
    time.sleep(0.5)                          # server is in the deterministic pause after slice 1
    st, h, b = req(f"/admin/withdraw?doc=doc-big&sha={BIG_SHA}", "tok-admin", method="POST")
    fence_at = time.time()
    total = len(first); s.settimeout(5)
    try:
        while True:
            c = s.recv(65536)
            if not c: break
            total += c and len(c)
    except (ConnectionResetError, socket.timeout):
        pass
    s.close()
    time.sleep(0.5)
    with psycopg.connect(A.db) as c:
        stream_rows = c.execute("""SELECT state, accepted_bytes, extract(epoch from created_at)*1000, range_len FROM credit_reservations
                                   WHERE range_start >= %s AND range_start < %s ORDER BY created_at""", (a0, a0 + MAXR)).fetchall()
    admitted_ms = json.loads(b or b"{}").get("admitted_ms", 0)
    hdr_len = first.find(b"\r\n\r\n") + 4 if b"\r\n\r\n" in first else 0
    body_received = total - hdr_len
    after = req(RANGE("doc-big", BIG_SHA), "tok-alice", "bytes=0-99")
    handed = [r for r in stream_rows if r[0] in ("ACCEPTED", "UNCERTAIN", "DRAINED") and r[1] > 0]
    post_fence_handoffs = [r for r in handed if r[2] >= admitted_ms]
    payload_handed = sum(r[3] for r in handed)
    RESULTS["scenarios"]["C_withdraw_mid_response"] = dict(withdraw_status=st, admitted_ms=admitted_ms, body_received=body_received, content_length=MAXR,
                                                          slices=[list(map(lambda x: float(x) if not isinstance(x, str) else x, r)) for r in stream_rows],
                                                          post_fence_handoffs=len(post_fence_handoffs), post_fence_request_status=after[0])
    check("withdrawal_between_slices_stops_handoff", st == 200 and not post_fence_handoffs and body_received <= payload_handed < MAXR and after[0] == 404,
          body_received=body_received, payload_handed=payload_handed, post_fence=len(post_fence_handoffs))
finally:
    stop(p)

# =============================================================== D. crash mid-transfer (F02): default buffers, no override
p = start("D", **{"Delivery.DrainGraceMs": 300})
s = socket.socket(); s.connect(("127.0.0.1", A.port))
a0 = 500_000
s.sendall((f"GET {RANGE('doc-big', BIG_SHA)} HTTP/1.1\r\nHost: x\r\nAuthorization: Bearer tok-alice\r\nRange: bytes={a0}-{a0 + MAXR - 1}\r\n\r\n").encode())
got = s.recv(1024)
time.sleep(0.7)
stop(p, hard=True)                      # kill -9 / TerminateProcess while bytes are still queued for the stalled reader
before = rows(f"range_start >= {a0} AND range_start < {a0 + MAXR}")
p = start("D2", reset=False, **{"Delivery.DrainGraceMs": 300})
try:
    L_restart = ledger()
    time.sleep(5.0)                     # > test minimum age (3 s); reconcile loop runs every 1 s
    st_, _, bdy = req("/admin/reconcile-prior", "tok-admin", method="POST")
    L_held = ledger()
    # now the client drains the orphaned socket (these bytes were queued before the crash and stay charged until gone)
    s.settimeout(5)
    try:
        while True:
            c = s.recv(65536)
            if not c: break
            got += c
    except (ConnectionResetError, socket.timeout):
        pass
    s.close()
    deadline = time.time() + 15
    while time.time() < deadline and (ledger()["reserved"] + ledger()["charged"]) > 0:
        time.sleep(0.5)
    L_late = ledger()
    after = rows(f"range_start >= {a0} AND range_start < {a0 + MAXR}")
    charged_before = sum(r_["amount"] for r_ in before)
    RESULTS["scenarios"]["D_crash_restart"] = dict(before=before, ledger_after_restart=L_restart, reconcile_while_socket_alive=bdy.decode(),
                                                  ledger_while_socket_alive=L_held, bytes_client_received_total=len(got),
                                                  ledger_after_client_drained=L_late, after=after)
    check("crash_charge_survives_restart", before and L_restart["reserved"] + L_restart["charged"] >= charged_before, ledger=L_restart)
    check("F02_no_release_while_orphan_socket_may_deliver", before and L_held["reserved"] + L_held["charged"] >= charged_before, ledger=L_held, reconcile=bdy[:80])
    check("F02_release_only_after_os_socket_evidence", after and all(r_["state"] == "DRAINED" and "prior instance reconciled" in (r_["reason"] or "") for r_ in after)
          and L_late["reserved"] == 0 and L_late["charged"] == 0, ledger=L_late)
finally:
    stop(p)

# =============================================================== E. post-ack residual with DEFAULT buffers (F03)
p = start("E", **{"Delivery.DrainGraceMs": 300})
try:
    s = socket.socket(); s.connect(("127.0.0.1", A.port))
    a0 = 700_000
    s.sendall((f"GET {RANGE('doc-big', BIG_SHA)} HTTP/1.1\r\nHost: x\r\nAuthorization: Bearer tok-alice\r\nRange: bytes={a0}-{a0 + MAXR - 1}\r\n\r\n").encode())
    pre = s.recv(1024)
    time.sleep(0.5)
    queued_at_ack = None
    st, h, b = req(f"/admin/withdraw?doc=doc-big&sha={BIG_SHA}", "tok-admin", method="POST")
    if hasattr(socket, "SO_RCVBUF") and os.name != "nt":
        import fcntl, termios, array
        buf = array.array("i", [0]); fcntl.ioctl(s.fileno(), termios.FIONREAD, buf, True); queued_at_ack = buf[0]
    post = b""; s.settimeout(3)
    try:
        while True:
            c = s.recv(65536)
            if not c: break
            post += c
    except (ConnectionResetError, socket.timeout):
        pass
    s.close()
    wj = json.loads(b or b"{}")
    res = dict(withdraw_status=st, reset_streams=wj.get("reset_streams"), bytes_before_ack=len(pre), bytes_read_after_ack=len(post),
               client_queue_at_ack=queued_at_ack, platform=sys.platform)
    RESULTS["scenarios"]["E_post_ack_residual_default_buffers"] = res
    # bytes already in the client's receive queue at ack time were delivered before the ack; only the remainder can
    # have left the server after the ack. Bound: effective server SO_SNDBUF (32 KiB requested -> 64 KiB on Linux).
    new_after_ack = None if queued_at_ack is None else max(0, len(post) - queued_at_ack)
    res["new_bytes_after_ack"] = new_after_ack
    res["bound_bytes"] = 65536
    ok = st == 200 and (new_after_ack is None or new_after_ack <= 65536)
    check("F03_post_ack_egress_bounded_by_send_buffer", ok, **res)
finally:
    stop(p)

RESULTS["all_pass"] = all(c["pass"] for c in RESULTS["checks"])
RESULTS["n_checks"] = len(RESULTS["checks"])
Path(A.out).write_text(json.dumps(RESULTS, indent=1, default=str))
print("ALL PASS" if RESULTS["all_pass"] else "SOME FAILED", RESULTS["n_checks"])
sys.exit(0 if RESULTS["all_pass"] else 1)
