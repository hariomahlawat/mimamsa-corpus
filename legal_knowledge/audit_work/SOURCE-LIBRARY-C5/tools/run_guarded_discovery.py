"""Guarded read-only discovery runner (Cycle 5 corrections). Uses curl (system proxy and CA; TLS verification on) and
discovery_guard for every decision. Never downloads a document:
- robots.txt is fetched first for each host and must be ESTABLISHED (fail closed);
- every target is probed with HEAD; GET is used only when HEAD shows a listing/metadata content type and the
  target is marked kind=listing; a GET body that turns out to be a document is discarded unread and logged;
- redirects are followed hop by hop, each hop host needing its own robots decision.
Usage: python run_guarded_discovery.py targets.tsv out_log.tsv out_dir
targets.tsv columns: target_id<TAB>kind(listing|head)<TAB>url"""
import csv, datetime, os, subprocess, sys, tempfile, time
from urllib.parse import urljoin

sys.path.insert(0, os.path.dirname(__file__))
import discovery_guard as G  # noqa: E402

UA = "Mimamsa-legal-research-discovery/1.0 (non-commercial research; read-only)"
DELAY = 2.0
_last = {}


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def curl(method, url, body_path=None, max_bytes=3_000_000):
    h = G.host_of(url)
    wait = DELAY - (time.time() - _last.get(h, 0))
    if wait > 0:
        time.sleep(wait)
    _last[h] = time.time()
    hdr = tempfile.NamedTemporaryFile(delete=False).name
    cmd = ["curl", "-sS", "--max-time", "40", "-A", UA, "-D", hdr, "-o", body_path or os.devnull,
           "--max-filesize", str(max_bytes), "-w", "%{http_code}"]
    cmd += ["-I"] if method == "HEAD" else []
    cmd.append(url)
    p = subprocess.run(cmd, capture_output=True, text=True)
    status = (p.stdout or "").strip()[-3:] or "000"
    heads = {}
    try:
        for line in open(hdr, encoding="latin-1"):
            if ":" in line:
                k, v = line.split(":", 1)
                heads[k.strip().lower()] = v.strip()
            elif line.startswith("HTTP/"):
                heads = {}  # keep only the last response block (proxy CONNECT block discarded)
    finally:
        os.unlink(hdr)
    return status, heads, (p.stderr or "").strip()[:200]


def main(targets, log_path, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    robots, rows = {}, []

    def log(**k):
        r = {c: "" for c in G.LOG_V2_COLUMNS}
        r.update(utc_time=now(), **k)
        rows.append(r)

    def ensure_robots(host):
        if host in robots:
            return
        if G.host_blocked(host):
            robots[host] = ("UNAVAILABLE", None)
            log(method="NONE", url=f"https://{host}/", robots_state="UNAVAILABLE", purpose="robots", note="blocked host: no request made")
            return
        url = f"https://{host}/robots.txt"
        bp = os.path.join(out_dir, f"robots_{host}.txt")
        st, hd, err = curl("GET", url, bp, 200_000)
        body = open(bp, "rb").read() if os.path.exists(bp) else b""
        loc = hd.get("location", "")
        final_host = G.host_of(urljoin(url, loc)) if st.startswith("3") and loc else host
        state, rp = G.robots_decision(st if not st.startswith("3") else 0, body, hd.get("content-type", ""), final_host, host, err or None)
        robots[host] = (state, rp)
        log(method="GET", url=url, final_url=urljoin(url, loc) if loc else url, http_status=st, content_type=hd.get("content-type", ""),
            content_length=str(len(body)), payload_class="METADATA_OR_LISTING" if state == "RULES_PARSED" else "", robots_state=state,
            purpose="robots", note=err)

    for t in csv.DictReader(open(targets, encoding="utf-8"), delimiter="\t"):
        url, chain = t["url"], []
        for _hop in range(6):
            h = G.host_of(url)
            ensure_robots(h)
            ok, why = G.may_request(url, robots)
            chain.append(url)
            if not ok:
                log(method="NONE", url=url, robots_state=robots.get(h, ("", None))[0] or why, purpose=t["target_id"],
                    note=f"not requested: {why}")
                break
            st, hd, err = curl("HEAD", url)
            pc, _ = G.classify_response("HEAD", st, hd.get("content-type", ""), hd.get("content-disposition", ""))
            loc = hd.get("location", "")
            log(method="HEAD", url=url, final_url=urljoin(url, loc) if loc else url, redirect_hosts=";".join(sorted({G.host_of(c) for c in chain})),
                http_status=st, content_type=hd.get("content-type", ""), content_disposition=hd.get("content-disposition", ""),
                content_length=hd.get("content-length", ""), payload_class=pc, robots_state=robots[h][0], purpose=t["target_id"], note=err)
            if st.startswith("3") and loc:
                url = urljoin(url, loc)
                continue
            if t["kind"] == "listing" and st == "200" and pc == "HEADERS_ONLY":
                bp = os.path.join(out_dir, f"{t['target_id']}.html")
                st2, hd2, err2 = curl("GET", url, bp)
                first = open(bp, "rb").read(8) if os.path.exists(bp) else b""
                pc2, sig = G.classify_response("GET", st2, hd2.get("content-type", ""), hd2.get("content-disposition", ""), None, first)
                if pc2 != "METADATA_OR_LISTING" and os.path.exists(bp):
                    os.unlink(bp)  # discarded unread
                log(method="GET", url=url, final_url=url, http_status=st2, content_type=hd2.get("content-type", ""),
                    content_disposition=hd2.get("content-disposition", ""), content_length=hd2.get("content-length", ""),
                    payload_class=pc2, file_signature=sig, robots_state=robots[h][0], purpose=t["target_id"],
                    note=err2 + ("" if pc2 == "METADATA_OR_LISTING" else " body discarded unread"))
            break
    with open(log_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=G.LOG_V2_COLUMNS, delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    errs = G.validate_log_v2(rows)
    print(f"requests_logged={len(rows)} log_errors={len(errs)}")
    for e in errs:
        print("LOG_ERROR", e)
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))
