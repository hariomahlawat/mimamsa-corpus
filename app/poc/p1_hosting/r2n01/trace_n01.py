"""Capture an R2-N01 evidence trace from the ASP.NET Core implementation and normalise it for the PR #54
transport oracle (docs/architecture/reviews/c13-assurance/transport_oracle.py --trace ... --http-cases ...).

python trace_n01.py --server-cmd ... --server-cwd ... --db <libpq> --npgsql <npgsql> --out-dir <dir> [--port 5191]

Sources:
  server JSONL (in-process instrumentation: ledger/policy_probe/terminal/witness/drain_probe events)
  client JSONL (this script: http, receive, cancel, ack, restart)
  occupancy (Linux only): kernel Send-Q per server-side socket from `ss -tnH`, an observation independent of the app
Ledger cross-check: every reserve/settle in the trace is compared with credit_reservations rows.
"""
import argparse, hashlib, json, os, shlex, shutil, socket, struct, subprocess, sys, threading, time, urllib.request
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent))
import codex_fixture  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--server-cmd", required=True); ap.add_argument("--server-cwd", required=True)
ap.add_argument("--db", required=True); ap.add_argument("--npgsql", required=True)
ap.add_argument("--out-dir", required=True); ap.add_argument("--port", type=int, default=5191)
A = ap.parse_args()
OUT = Path(A.out_dir); OUT.mkdir(parents=True, exist_ok=True)
BASE = f"http://127.0.0.1:{A.port}"
KiB = 1024
CFG = {"Credit.SiteCap": 196608, "Credit.ConnCap": 196608, "Delivery.MaxRange": 131072, "Delivery.DrainGraceMs": 300,
       "Transport.ListenSendBufferBytes": 4096, "Delivery.SlotGate": "false",
       "Test.PauseAfterFirstSliceMs": 1500}

TARGET = codex_fixture.make_pdf()
assert hashlib.sha256(TARGET).hexdigest() == codex_fixture.EXPECTED_SHA256
UNRELATED = TARGET + b"\n%unrelated-copy\n"
T_SHA, U_SHA = hashlib.sha256(TARGET).hexdigest(), hashlib.sha256(UNRELATED).hexdigest()
(OUT / "target.pdf").write_bytes(TARGET); (OUT / "unrelated.pdf").write_bytes(UNRELATED)
COPY_LABEL = {T_SHA: "target", U_SHA: "unrelated"}
SEED = {"sessions": [{"token": "tok-alice", "user": "alice", "session": "s-alice"}, {"token": "tok-bob", "user": "bob", "session": "s-bob"},
                     {"token": "tok-admin", "user": "admin", "session": "s-admin", "admin": True}],
        "copies": [{"doc_id": "doc-target", "source": str((OUT / "target.pdf").resolve()), "sha256": T_SHA},
                   {"doc_id": "doc-unrelated", "source": str((OUT / "unrelated.pdf").resolve()), "sha256": U_SHA}],
        "grants": [{"user": "alice", "doc_id": "doc-target"}, {"user": "alice", "doc_id": "doc-unrelated"}]}
(OUT / "seed.json").write_text(json.dumps(SEED))
SERVER_TRACE, CLIENT_TRACE = OUT / "server_trace.jsonl", OUT / "client_trace.jsonl"
for f in (SERVER_TRACE, CLIENT_TRACE):
    if f.exists(): f.unlink()
CLIENT = []
LOCK = threading.Lock()


def now_ns(): return time.time_ns()
def cemit(kind, source="client", **f):
    with LOCK: CLIENT.append(dict(f, kind=kind, source=source, t_ns=now_ns()))


def start(reset):
    env = dict(os.environ)
    env.update({"ASPNETCORE_URLS": BASE, "Urls": BASE, "Mimamsa__Db": A.npgsql, "Mimamsa__SeedFile": str(OUT / "seed.json") if reset else "",
                "Mimamsa__VaultRoot": str(OUT / "vault"), "Mimamsa__Test__ResetLedger": "true" if reset else "false",
                "Mimamsa__Trace__Path": str(SERVER_TRACE)})
    for k, v in CFG.items(): env["Mimamsa__" + k.replace(".", "__")] = str(v)
    log = open(OUT / "server.log", "ab")
    p = subprocess.Popen(shlex.split(A.server_cmd, posix=os.name != "nt"), cwd=A.server_cwd, env=env, stdout=log, stderr=log)
    for _ in range(300):
        try:
            if urllib.request.urlopen(BASE + "/health", timeout=1).status == 200: return p
        except Exception: time.sleep(0.1)
    raise RuntimeError("server did not start")


RANGE = lambda d, sh: f"/api/v2/documents/{d}/copies/{sh}/range"


def raw(path, token=None, rng=None, extra=None, method="GET", rcvbuf=None, read_limit=None):
    s = socket.socket(); s.settimeout(10)
    if rcvbuf: s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, rcvbuf)
    s.connect(("127.0.0.1", A.port))
    h = [f"{method} {path} HTTP/1.1", "Host: x", "Connection: close"]
    if token: h.append(f"Authorization: Bearer {token}")
    if rng: h.append(f"Range: {rng}")
    for k, v in (extra or {}).items(): h.append(f"{k}: {v}")
    s.sendall(("\r\n".join(h) + "\r\n\r\n").encode())
    return s


def read_all(s):
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


RETRIES_503 = {}


def http_case(case, path, token, rng=None, extra=None, copy="target", phase=None, expect_body=None):
    # like the viewer's range transport: honour 503 + Retry-After (credit not yet drained) with a bounded retry
    for attempt in range(60):
        st, hd, body = read_all(raw(path, token, rng, extra))
        if st != 503: break
        RETRIES_503[case] = attempt + 1
        time.sleep(0.1)
    ev = dict(case=case, authenticated=token in ("tok-alice", "tok-bob"), copy=copy, status=st, length=len(body),
              content_range=hd.get("content-range"))
    if rng: ev["range"] = rng
    if extra and "If-Range" in extra: ev["conditional"] = "If-Range"
    if phase: ev["phase"] = phase
    ev["body_sha256"] = hashlib.sha256(body).hexdigest()
    ev["body_matches_fixture"] = (expect_body is None) or body == expect_body
    cemit("http", **ev)
    return st, hd, body


def server_port_streams():
    """Linux: kernel tx_queue bytes per server-side socket on our port, read from /proc/net/tcp{,6} by this client
    process (an observation independent of the application). None on other platforms."""
    if not os.path.exists("/proc/net/tcp"): return None
    res = {}
    for f in ("/proc/net/tcp", "/proc/net/tcp6"):
        if not os.path.exists(f): continue
        for line in open(f).read().splitlines()[1:]:
            p = line.split()
            lp = int(p[1].rsplit(":", 1)[1], 16); rp = int(p[2].rsplit(":", 1)[1], 16)
            if lp != A.port or p[3] == "0A": continue          # 0A = LISTEN
            res[f"c{rp}"] = res.get(f"c{rp}", 0) + int(p[4].split(":")[0], 16)
    return res


def occupancy_sample(label):
    m = server_port_streams()
    if m is None: return
    cemit("occupancy", source="drain_probe", connections=m, site=sum(m.values()), note=label, probe="/proc/net/tcp tx_queue")


def slow_open(path, rng, rcvbuf=4096, first=1024):
    s = raw(path, "tok-alice", rng, rcvbuf=rcvbuf)
    got = b""
    while len(got) < first:
        c = s.recv(first - len(got))
        if not c: break
        got += c
    return s, got


def finish_slow(s, got, stream_note):
    try:
        while True:
            c = s.recv(65536)
            if not c: break
            got += c
    except (ConnectionResetError, socket.timeout):
        pass
    s.close()
    return got


def rst(s):
    s.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("HH" if os.name == "nt" else "ii", 1, 0)); s.close()


notes = {}
# ------------------------------------------------------------------ boot 1
p = start(reset=True)
L = len(TARGET)
http_case("metadata", "/api/v2/documents/doc-target/pdf-meta", "tok-alice")
http_case("first_chunk", RANGE("doc-target", T_SHA), "tok-alice", "bytes=0-131071", expect_body=TARGET[:131072])
http_case("near_end", RANGE("doc-target", T_SHA), "tok-alice", "bytes=393216-396870", expect_body=TARGET[393216:])
http_case("conditional", RANGE("doc-target", T_SHA), "tok-alice", "bytes=0-65535", extra={"If-Range": '"x"'}, expect_body=TARGET[:65536])
http_case("anonymous", RANGE("doc-target", T_SHA), None, "bytes=0-65535")
http_case("other_user", RANGE("doc-target", T_SHA), "tok-bob", "bytes=0-65535")
http_case("oversize", RANGE("doc-target", T_SHA), "tok-alice", "bytes=0-131072")
http_case("multi_range", RANGE("doc-target", T_SHA), "tok-alice", "bytes=0-1,3-4")
http_case("no_range", RANGE("doc-target", T_SHA), "tok-alice")
http_case("out_of_bounds", RANGE("doc-target", T_SHA), "tok-alice", f"bytes={L}-{L + 9}")
time.sleep(1.0)   # drains (grace 300 ms)

# slow drain with independent kernel occupancy samples
s1, g1 = slow_open(RANGE("doc-target", T_SHA), "bytes=0-131071")
time.sleep(0.6); occupancy_sample("slow reader holding, after 1 KiB")
time.sleep(0.6); occupancy_sample("slow reader holding, +0.6 s")
g1 = finish_slow(s1, g1, "s1")
notes["slow_drain_body_ok"] = g1.split(b"\r\n\r\n", 1)[1] == TARGET[:131072] if b"\r\n\r\n" in g1 else False
time.sleep(1.0); occupancy_sample("after slow reader finished and drain grace")

# cap race at the ledger: two holders keep 2 x 64 KiB charged, two contenders race for the final 64 KiB of site credit
h1, _ = slow_open(RANGE("doc-target", T_SHA), "bytes=0-64511")
h2, _ = slow_open(RANGE("doc-target", T_SHA), "bytes=64512-129023")
time.sleep(0.5); occupancy_sample("two holders")
race_res = [None, None]; barrier = threading.Barrier(2)
def contender(i):
    barrier.wait()
    st, hd, body = read_all(raw(RANGE("doc-target", T_SHA), "tok-alice", "bytes=200000-264511"))
    race_res[i] = (st, len(body), body == TARGET[200000:264512])
ts = [threading.Thread(target=contender, args=(i,)) for i in range(2)]
[t.start() for t in ts]; [t.join() for t in ts]
notes["race_results"] = race_res
finish_slow(h1, b"", "h1"); finish_slow(h2, b"", "h2")
time.sleep(1.0)

# uncertain: client resets mid-transfer; the client records cancellation before the reset
u, _ = slow_open(RANGE("doc-target", T_SHA), "bytes=0-131071")
time.sleep(0.8)
uport = u.getsockname()[1]
rst(u)
time.sleep(0.15)   # after the server observed the reset (it cannot hand off further slices), before drain grace ends
cemit("cancel_stream_hint", note="uncertain stream (client RST)", client_port=uport)
time.sleep(1.2)

# withdrawal between chunks
w, gw = slow_open(RANGE("doc-target", T_SHA), "bytes=0-131071")
wport = w.getsockname()[1]
time.sleep(0.5)
t_adm = int(time.time() * 1000)
st, hd, body = read_all(raw(f"/admin/withdraw?doc=doc-target&sha={T_SHA}", "tok-admin", method="POST"))
ackj = json.loads(body)
cemit("ack", operation=ackj["operation"], epoch=ackj["epoch"], digest=ackj["digest"], monotonic_ms=int(time.time() * 1000))
gw = finish_slow(w, gw, "w")
cemit("cancel_stream_hint", note="withdrawn stream ended early; viewer cancels", client_port=wport,
      body_received=len(gw.split(b"\r\n\r\n", 1)[1]) if b"\r\n\r\n" in gw else 0)
notes["withdraw_mid_body_received"] = len(gw.split(b"\r\n\r\n", 1)[1]) if b"\r\n\r\n" in gw else 0
http_case("withdrawn", RANGE("doc-target", T_SHA), "tok-alice", "bytes=0-65535", phase="withdrawn")
time.sleep(1.0)

# crash mid-transfer on the unrelated copy
k, _ = slow_open(RANGE("doc-unrelated", U_SHA), "bytes=0-131071")
kport = k.getsockname()[1]
time.sleep(0.8)
p.kill(); p.wait()
cemit("restart", source="fault_driver")
cemit("cancel_stream_hint", note="stream lost in crash", client_port=kport)
try: k.close()
except OSError: pass
time.sleep(4.0)
# ------------------------------------------------------------------ boot 2 (no reset: durable ledger + witness)
p = start(reset=False)
st, hd, body = read_all(raw("/admin/reconcile-prior?evidence=prior-process-killed-by-fault-driver;grace-4s&minAgeSec=3", "tok-admin", method="POST"))
notes["reconcile"] = body.decode()
st, hd, body = read_all(raw("/api/v2/documents/doc-target/pdf-meta", "tok-alice"))
notes["withdrawn_meta_after_restart"] = st
http_case("unrelated_after_restart", RANGE("doc-unrelated", U_SHA), "tok-alice", "bytes=0-1023", copy="unrelated", expect_body=UNRELATED[:1024])
time.sleep(1.0)
p.terminate(); p.wait(15)
time.sleep(0.3)

# ------------------------------------------------------------------ merge and normalise
server = [json.loads(l) for l in SERVER_TRACE.read_text().splitlines() if l.strip()]
events = sorted(server + CLIENT, key=lambda e: (e["t_ns"], 0 if e.get("source") != "client" else 1))
# stream <-> client port mapping from reserve events (connection = "c<client port>")
port_streams = {}
for e in server:
    if e["kind"] == "reserve":
        port_streams.setdefault(e["connection"], set()).add(e["stream"])
boots = [e for e in server if e["kind"] == "boot"]
norm, attempts_bytes, seen_conns = [], {}, set()
initial = {"epoch": boots[0]["epoch"], "digest": boots[0]["digest"]}
for e in events:
    k = e["kind"]
    if k == "boot":
        if e is boots[0]: continue
        norm.append({"kind": "recover", "source": "witness", "epoch": e["epoch"], "digest": e["digest"]}); continue
    if k == "cancel_stream_hint":
        for st_id in sorted(port_streams.get(f"c{e['client_port']}", ())):
            norm.append({"kind": "cancel", "source": "client", "stream": st_id, "note": e["note"]})
        continue
    if k in ("reserve", "admit", "fence"):
        e = dict(e, copy=COPY_LABEL[e["copy"]])      # sha256 -> fixture copy label used by the HTTP cases
    if k == "reserve":
        seen_conns.add(e["connection"])
    if k == "occupancy":
        # a connection absent from the kernel socket table has no queued bytes: record it explicitly as 0
        conns = {c: 0 for c in seen_conns}; conns.update(e["connections"])
        e = dict(e, connections=conns, site=sum(conns.values()))
    out = {x: y for x, y in e.items() if x not in ("t_ns", "boot", "local_seq")}
    norm.append(out)
for i, e in enumerate(norm, 1):
    e["seq"] = i
trace = {"limits": {"site": CFG["Credit.SiteCap"], "connection": CFG["Credit.ConnCap"]}, "initial_witness": initial, "events": norm,
         "provenance": {"server_events": "in-process instrumentation (not independent probes)", "client_events": "trace_n01.py raw-socket client",
                        "occupancy": "Linux /proc/net/tcp tx_queue read by the client process, when available", "platform": sys.platform}}
(OUT / "normalized_trace.json").write_text(json.dumps(trace, indent=1))

# ledger cross-check
with psycopg.connect(A.db) as c:
    rows = {str(r[0]): r[1:] for r in c.execute("SELECT res_id, amount, state, charged FROM credit_reservations").fetchall()}
mism = []
for e in norm:
    if e["kind"] == "reserve":
        r = rows.get(e["attempt"])
        if not r or r[0] != e["size"]: mism.append(("reserve", e["attempt"], r))
    if e["kind"] == "settle" and e["attempt"] not in rows: mism.append(("settle", e["attempt"], None))
notes["retries_after_503"] = RETRIES_503
summary = dict(notes=notes, events=len(norm), kinds={k: sum(1 for e in norm if e["kind"] == k) for k in sorted({e["kind"] for e in norm})},
               ledger_crosscheck_mismatches=mism, ledger_rows=len(rows))
(OUT / "capture_summary.json").write_text(json.dumps(summary, indent=1, default=str))
print(json.dumps(summary, default=str)[:2000])
