"""Protected-path benchmark (R2-N01 range endpoint, one bounded response per connection, credit ledger active).
autocannon assumes keep-alive and mis-measures `Connection: close` responses, so this client measures each request
from connect to last body byte. Run pinned away from the server: taskset -c 3 python bench_protected.py ...

python bench_protected.py --base http://127.0.0.1:5081 --path /api/v2/documents/<doc>/copies/<sha>/range --token tok-alice
       --length <file bytes> --out out.json [--runs 3 --requests 300 --concurrency 1,16 --range-bytes 64512]
"""
import argparse, asyncio, json, os, random, statistics, time

ap = argparse.ArgumentParser()
ap.add_argument("--base", required=True); ap.add_argument("--path", required=True); ap.add_argument("--token", required=True)
ap.add_argument("--length", type=int, required=True); ap.add_argument("--out", required=True)
ap.add_argument("--runs", type=int, default=3); ap.add_argument("--requests", type=int, default=300)
ap.add_argument("--concurrency", default="1,16"); ap.add_argument("--range-bytes", type=int, default=64512)
A = ap.parse_args()
host, port = A.base.split("//")[1].split(":"); port = int(port)


async def one(a):
    b = a + A.range_bytes - 1
    t = time.perf_counter()
    r, w = await asyncio.open_connection(host, port)
    w.write(f"GET {A.path} HTTP/1.1\r\nHost: x\r\nAuthorization: Bearer {A.token}\r\nRange: bytes={a}-{b}\r\n\r\n".encode())
    await w.drain()
    data = await r.read()
    w.close()
    status = int(data.split(b" ", 2)[1]) if data else 0
    body = len(data.partition(b"\r\n\r\n")[2])
    return (time.perf_counter() - t) * 1000, status, body


async def run(conc):
    rnd = random.Random(conc)
    offs = [rnd.randrange(0, A.length - A.range_bytes) for _ in range(A.requests)]
    sem = asyncio.Semaphore(conc); out = []
    async def w(a):
        async with sem:
            while True:
                lat, st, body = await one(a)
                out.append((lat, st, body))
                if st != 503: return
                await asyncio.sleep(0.05)   # honour Retry-After-style backoff like the viewer transport
    t0 = time.perf_counter()
    await asyncio.gather(*(w(a) for a in offs))
    wall = time.perf_counter() - t0
    ok = [l for l, s, b in out if s == 206 and b == A.range_bytes]
    return dict(concurrency=conc, completed_206=len(ok), responses=len(out), denied_503=sum(1 for _, s, _ in out if s == 503),
                bad=sum(1 for _, s, b in out if s == 206 and b != A.range_bytes) + sum(1 for _, s, _ in out if s not in (206, 503)),
                rps_206=round(len(ok) / wall, 1), p50_ms=round(statistics.median(ok), 2) if ok else None,
                p95_ms=round(sorted(ok)[int(0.95 * (len(ok) - 1))], 2) if ok else None, mbps=round(len(ok) * A.range_bytes / wall / 2**20, 1),
                loadavg=os.getloadavg()[0] if hasattr(os, "getloadavg") else None)


res = {"runs": []}
for i in range(A.runs):
    for c in map(int, A.concurrency.split(",")):
        r = asyncio.run(run(c)); r["run"] = i; res["runs"].append(r); print(r, flush=True)
json.dump(res, open(A.out, "w"), indent=1)
