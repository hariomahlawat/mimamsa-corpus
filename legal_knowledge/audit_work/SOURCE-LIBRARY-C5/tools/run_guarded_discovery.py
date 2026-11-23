"""Guarded read-only discovery runner (stdlib only; TLS verification always on). Every decision goes through
discovery_guard. Revised after the independent review of 8e4e9dfe (F-01..F-05): the curl path is withdrawn.

Request discipline (DISCOVERY_SAFETY_POLICY.md):
- robots.txt is fetched first for each origin (scheme + host + port) and must be ESTABLISHED; otherwise no
  further request is made to that origin (fail closed). Redirects are never followed automatically: each hop is
  logged, and the next hop's origin needs its own robots decision.
- every target is probed with HEAD. A GET is attempted only when the target is kind=listing AND HEAD returned
  200 with an explicit listing/metadata content type.
- the GET decision is re-made on the GET response's OWN status and headers before any body byte is read:
  status must be 200; content type an explicit listing type; no attachment disposition; no content encoding
  other than identity (Accept-Encoding: identity is sent); declared Content-Length, if any, within the cap.
  Otherwise the connection is closed without reading the body.
- then only the first 1024 bytes are read and must look like text (no document signature anywhere in them, no
  NUL bytes, decodable). Otherwise the connection is closed; at most 1 KiB was received and nothing is written.
- the rest is read into memory up to the cap (2 MB); a body that exceeds the cap, or a read error / timeout,
  discards everything. A listing body is written to disk only after the whole response passed these checks.
Remaining limits (stated, not hidden): up to 1 KiB of a disguised document can be received in memory before
the abort; a document disguised as plain text beyond the first 1 KiB (e.g. a text file that is itself the
publication) is not distinguishable from a listing and would be kept. Use the runner for listing/metadata URLs
only. Mocked tests cover these paths; no live run has been made with this revision.
Usage: python run_guarded_discovery.py targets.tsv out_log.tsv out_dir
targets.tsv columns: target_id<TAB>kind(listing|head)<TAB>url"""
import csv, datetime, os, socket, ssl, sys, time, urllib.error, urllib.request
from urllib.parse import urljoin

sys.path.insert(0, os.path.dirname(__file__))
import discovery_guard as G  # noqa: E402

UA = "Mimamsa-legal-research-discovery/1.0 (non-commercial research; read-only)"
DELAY = 2.0
TIMEOUT = 40
CAP = 2_000_000
_last = {}


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None  # never follow; the caller handles each hop


def http_open(method, url):
    """Open a request without reading the body. Returns (status, headers_lower_dict, response_or_None, error).
    Tests replace this function."""
    cafile = os.environ.get("SSL_CERT_FILE") or os.environ.get("REQUESTS_CA_BUNDLE") or None
    ctx = ssl.create_default_context(cafile=cafile)  # verification on; never disabled
    opener = urllib.request.build_opener(urllib.request.ProxyHandler(), urllib.request.HTTPSHandler(context=ctx), _NoRedirect)
    req = urllib.request.Request(url, method=method, headers={"User-Agent": UA, "Accept-Encoding": "identity"})
    try:
        resp = opener.open(req, timeout=TIMEOUT)
        return resp.status, {k.lower(): v for k, v in resp.headers.items()}, resp, ""
    except urllib.error.HTTPError as e:  # includes 3xx (not followed) and 4xx/5xx; body is not read
        heads = {k.lower(): v for k, v in (e.headers or {}).items()}
        e.close()
        return e.code, heads, None, ""
    except (urllib.error.URLError, socket.timeout, ssl.SSLError, ConnectionError, OSError) as e:
        return 0, {}, None, f"{type(e).__name__}: {e}"[:200]


def _pace(url):
    k = G.origin_key(url)
    wait = DELAY - (time.time() - _last.get(k, 0))
    if wait > 0:
        time.sleep(wait)
    _last[k] = time.time()


def guarded_get(url, cap=CAP):
    """GET with header gate, 1 KiB prefix gate and size cap. Returns (status, headers, body_or_None, payload_class,
    signature, note). body is returned only for METADATA_OR_LISTING responses that passed every gate."""
    _pace(url)
    st, hd, resp, err = http_open("GET", url)
    if resp is None:
        return st, hd, None, "", "", err or "no body read"
    try:
        ok, why = G.get_response_gate(st, hd, cap)
        if not ok:
            pc = G.classify_response("GET", st, hd.get("content-type", ""), hd.get("content-disposition", ""))[0]
            return st, hd, None, pc, "", f"body not read: {why}"
        try:
            first = resp.read(1024)
        except Exception as e:  # noqa: BLE001
            return st, hd, None, "UNKNOWN", "", f"read error: {type(e).__name__}"
        ok, why, sig = G.body_prefix_gate(first)
        if not ok:
            return st, hd, None, "DOCUMENT_PAYLOAD" if sig else "UNKNOWN", sig, f"aborted after <=1 KiB: {why}"
        chunks, total = [first], len(first)
        while True:
            try:
                b = resp.read(65536)
            except Exception as e:  # noqa: BLE001
                return st, hd, None, "UNKNOWN", "", f"read error mid-body ({type(e).__name__}); discarded"
            if not b:
                break
            total += len(b)
            if total > cap:
                return st, hd, None, "UNKNOWN", "", f"exceeded cap {cap} bytes; discarded"
            chunks.append(b)
        return st, hd, b"".join(chunks), "METADATA_OR_LISTING", "", ""
    finally:
        resp.close()


def main(targets, log_path, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    robots, rows = {}, []

    def log(**k):
        r = {c: "" for c in G.LOG_V2_COLUMNS}
        r.update(utc_time=now(), **k)
        rows.append(r)

    def ensure_robots(url):
        key = G.origin_key(url)
        if key in robots:
            return
        host = G.host_of(url)
        rurl = f"https://{G.netloc_of(url)}/robots.txt"
        if G.host_blocked(host):
            robots[key] = ("UNAVAILABLE", None)
            log(method="NONE", url=rurl, robots_state="UNAVAILABLE", purpose="robots", note="blocked host: no request made")
            return
        if G.urlsplit(url).scheme != "https":
            robots[key] = ("UNAVAILABLE", None)
            log(method="NONE", url=rurl, robots_state="UNAVAILABLE", purpose="robots", note="non-HTTPS origin: no request made")
            return
        st, hd, body, pc, _sig, note = guarded_get(rurl, cap=200_000)
        loc = hd.get("location", "")
        final_host = G.host_of(urljoin(rurl, loc)) if 300 <= st < 400 and loc else host
        state, rp = G.robots_decision(st if not (300 <= st < 400) else 0, body or b"", hd.get("content-type", ""), final_host, host,
                                      None if st else (note or "no response"))
        if st == 200 and body is None:
            state, rp = "UNAVAILABLE", None  # a robots body that failed the gates is not an established policy
        robots[key] = (state, rp)
        log(method="GET", url=rurl, final_url=urljoin(rurl, loc) if loc else rurl, http_status=str(st or "000"),
            content_type=hd.get("content-type", ""), content_length=str(len(body or b"")),
            payload_class=pc if state == "RULES_PARSED" else "", robots_state=state, purpose="robots", note=note)

    with open(targets, encoding="utf-8") as tf:
        tlist = list(csv.DictReader(tf, delimiter="\t"))
    for t in tlist:
        url, chain = t["url"], []
        for _hop in range(6):
            ensure_robots(url)
            ok, why = G.may_request(url, robots, UA)  # UA-specific robots groups apply, else '*' (review F-10)
            chain.append(url)
            key = G.origin_key(url)
            if not ok:
                log(method="NONE", url=url, robots_state=robots.get(key, ("", None))[0] or why, purpose=t["target_id"],
                    note=f"not requested: {why}")
                break
            _pace(url)
            st, hd, resp, err = http_open("HEAD", url)
            if resp is not None:
                resp.close()
            pc, _ = G.classify_response("HEAD", st, hd.get("content-type", ""), hd.get("content-disposition", ""))
            loc = hd.get("location", "")
            log(method="HEAD", url=url, final_url=urljoin(url, loc) if loc else url,
                redirect_hosts=";".join(sorted({G.host_of(c) for c in chain})), http_status=str(st or "000"),
                content_type=hd.get("content-type", ""), content_disposition=hd.get("content-disposition", ""),
                content_length=hd.get("content-length", ""), payload_class=pc, robots_state=robots[key][0],
                purpose=t["target_id"], note=err)
            if 300 <= st < 400:
                if not loc:
                    log(method="NONE", url=url, robots_state=robots[key][0], purpose=t["target_id"], note="redirect without Location: stopped")
                    break
                url = urljoin(url, loc)
                continue
            if t["kind"] == "listing" and st == 200 and pc == "HEADERS_ONLY" and G.head_allows_get(hd.get("content-type", "")):
                st2, hd2, body, pc2, sig, note = guarded_get(url)
                if body is not None:
                    with open(os.path.join(out_dir, f"{t['target_id']}.html"), "wb") as f:
                        f.write(body)
                log(method="GET", url=url, final_url=url, http_status=str(st2 or "000"), content_type=hd2.get("content-type", ""),
                    content_disposition=hd2.get("content-disposition", ""), content_length=hd2.get("content-length", ""),
                    payload_class=pc2, file_signature=sig, robots_state=robots[key][0], purpose=t["target_id"], note=note)
            elif t["kind"] == "listing":
                log(method="NONE", url=url, robots_state=robots[key][0], purpose=t["target_id"],
                    note="GET refused: HEAD did not return 200 with an explicit listing content type")
            break
        else:
            log(method="NONE", url=url, purpose=t["target_id"], note="more than 5 redirects: stopped")
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
