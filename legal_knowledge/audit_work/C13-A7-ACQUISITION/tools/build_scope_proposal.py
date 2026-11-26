#!/usr/bin/env python3
"""C13 A7 Part 2: build the PROPOSED config/sources.yaml (not applied) and its unified diff against staging.

Inputs (no network): staging config/sources.yaml (git a4c0c382), allowlist/PROBE_RESULTS.csv,
allowlist/ARCHIVE_ITEM_NODES.csv, acquisition/fetch_results_c13.json (observed archive.org redirect hosts),
acquisition/TARGETS_C13.csv.

Outputs: proposed/sources.yaml.proposed, proposed/sources.yaml.diff, allowlist/ARCHIVE_REDIRECT_SCOPES.csv.
The proposal needs the code in proposed/crawler_revision/0003 (redirect_scopes, ca_extra_pem).

Usage:  python -I build_scope_proposal.py            # write
        python -I build_scope_proposal.py --check    # rebuild in memory and compare
"""
from __future__ import annotations

import argparse
import csv
import difflib
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
REPO = HERE.parents[3]
PROP = BASE / "proposed"
SCOPES = BASE / "allowlist" / "ARCHIVE_REDIRECT_SCOPES.csv"
EGZ_PINS = ["13949634d99cd6fd6aa80bc034fefacceb1969feef986586713ecdbb05758d3f",
            "072639d0b140d5bffae16ad9c3f6cc6086040621f51ee61a6d46a8915c07cf76"]
ER2023_13MB_SHA256 = "29f6fa2cfcd961aadce490679a686b5a3b7b2e683a0eaceb42bc2cd2ebb70dad"   # C5-SRC-P1-ER-2023-HELD-13MB


def build() -> dict[str, str]:
    staging = subprocess.run(["git", "-C", str(REPO), "show", "a4c0c382:config/sources.yaml"], check=True,
                             capture_output=True, text=True).stdout
    s = staging
    # 1. PR #7 security change (re-targeted to staging).
    s = s.replace("allowed_hosts: [www.aftdelhi.nic.in, aftdelhi.nic.in, aftlko.up.nic.in, aftkolkata.nic.in, aftjabalpur.in]",
                  "allowed_hosts: [www.aftdelhi.nic.in, aftdelhi.nic.in, aftlko.up.nic.in, aftkolkata.nic.in]")
    s = s.replace("# Explicitly forbidden: never fetch, even if linked.\nblocked_hosts:\n",
                  "# Explicitly forbidden: never fetch, even if linked. Subdomains of a blocked host are blocked too.\n"
                  "blocked_hosts:\n"
                  "  # Formerly configured for AFT Regional Bench Jabalpur; serves unrelated (betting) content (2026-11-22).\n"
                  "  # Not an official Tribunal host. Never visit (PR #7; C13 A7 re-targeted to staging).\n"
                  "  - aftjabalpur.in\n  - www.aftjabalpur.in\n")
    # 2. egazette: pinned intermediates (strict chain to ISRG Root X1), HTTPS only.
    s = s.replace('''    allowed_hosts: [egazette.gov.in]
    verify: true
    discovery: "Notifications under the Army Act (active service declarations, s.12, etc.)."''',
                  '''    allowed_hosts: [egazette.gov.in]
    require_https: true
    # The server sends only its leaf certificate (issuer Let's Encrypt YR1). The two public intermediates below were
    # fetched from the leaf's AIA chain (yr1.i.lencr.org, yr.i.lencr.org) and verified to chain to ISRG Root X1 in
    # the trust store; partial-chain trust is disabled (crawler/http.py::tls_verify_for). If the site changes its
    # issuing intermediate, the pins stop matching the served chain and requests fail closed. Re-verify then.
    # Evidence: legal_knowledge/audit_work/C13-A7-ACQUISITION/allowlist/EGAZETTE_TLS_C13.md
    ca_extra_pem: config/ca/egazette_intermediates.pem
    ca_extra_sha256:
      - 13949634d99cd6fd6aa80bc034fefacceb1969feef986586713ecdbb05758d3f   # C=US, O=Let's Encrypt, CN=YR1 (to 2028-09-02)
      - 072639d0b140d5bffae16ad9c3f6cc6086040621f51ee61a6d46a8915c07cf76   # C=US, O=ISRG, CN=Root YR, cross-signed by ISRG Root X1 (to 2032-09-02)
    verify: true
    discovery: "Notifications under the Army Act (active service declarations, s.12, etc.). Exact WriteReadData file URLs only; the interactive search pages are not used (their CAPTCHA status was not checked)."''')
    # 3. archive.org: item-scoped redirect scopes for the pins still needed.
    nodes = {r["identifier"]: r for r in csv.DictReader(open(BASE / "allowlist" / "ARCHIVE_ITEM_NODES.csv"))}
    res = json.loads((BASE / "acquisition" / "fetch_results_c13.json").read_text())
    targets = {t["target_id"]: t for t in csv.DictReader(open(BASE / "acquisition" / "TARGETS_C13.csv"))}
    scope_rows = []
    for tid, t in targets.items():
        if t["group"] != "G2":
            continue
        r = res.get(tid, {})
        if r.get("status") == "DOWNLOADED" and r.get("integrity", "").startswith("PIN_VERIFIED"):
            continue                                        # obtained from the government host; no scope needed
        m = re.match(r"https://archive\.org/download/([^/]+)/", t["fallback_url"] or t["url"])
        if not m:
            continue
        ident = m.group(1)
        n = nodes.get(ident, {})
        pairs = set()
        for h in {n.get("d1"), n.get("d2"), n.get("server")} - {None, ""}:
            pairs.add((h, n["dir"].rstrip("/") + "/"))
        loc = r.get("url", "")
        mm = re.match(r"https://([^/]+)(/\d+/items/" + re.escape(ident) + "/)", loc)
        observed = ""
        if mm:
            pairs.add((mm.group(1), mm.group(2)))
            observed = f"{mm.group(1)}{mm.group(2)}"
        for h, p in sorted(pairs):
            scope_rows.append({"target_id": tid, "identifier": ident, "host": h, "path_prefix": p,
                               "basis": "observed redirect 2026-11-25" if f"{h}{p}" == observed else "item metadata API (d1/d2/server) 2026-11-25",
                               "pinned_md5": t["expected_md5"], "pinned_bytes": t["expected_bytes"],
                               "justification": t["description"][:160]})
    lines = ["    # Item-scoped redirect destinations (C13 A7 proposal, replacing the \"*.archive.org\" wildcard of PRs #8/#17/#23).",
             "    # Each entry allows ONE storage-node host for ONE item directory. Every hop must still be HTTPS and pass robots.",
             "    # Redirects for one item were seen to go to nodes not named in its metadata, so the set can go stale; a",
             "    # redirect elsewhere fails closed and needs a new reviewed entry. Source: allowlist/ARCHIVE_REDIRECT_SCOPES.csv",
             "    require_https: true",
             "    redirect_scopes:"]
    for r in scope_rows:
        lines.append(f"      - {{ host: {r['host']}, path_prefix: \"{r['path_prefix']}\" }}   # {r['target_id'][7:]}")
    s = s.replace('''    allowed_hosts: [archive.org]
    verify: true
    discovery: "Digital Library of India items; record the archive.org item identifier in metadata."''',
                  '''    allowed_hosts: [archive.org]
''' + "\n".join(lines) + '''
    verify: true
    discovery: "Digital Library of India items; record the archive.org item identifier in metadata."''')
    # 4. New sources: DESW (exact URLs) and the SC document host (exact pinned URLs, conditional).
    new = '''
  # ---------------------------------------------------------------- C13 A7 PROPOSAL (not applied; owner decision D-04)
  # DESW (Department of Ex-Servicemen Welfare, MoD). Validated 2026-11-25: TLS chain OK (Sectigo DV R36), robots.txt
  # answers 403 (= no robots file, RFC 9309), no CAPTCHA marker or password field on the landing page.
  # Exact document URLs only; nothing is discovered by following links.
  desw:
    phase: 2
    enabled: false
    priority: 3
    heavy: false
    allowed_hosts: [desw.gov.in]
    require_https: true
    documents:
      - doc_id: rules-entitlement-casualty-pensionary-awards-2023
        url: "https://desw.gov.in/sites/default/files/Entitlement%20Rules%202023.pdf"
        title: "Entitlement Rules for Casualty Pensionary Awards to the Armed Forces Personnel, 2023"
        doc_type: rules
        year: 2023
        issuing_authority: "Ministry of Defence (Department of Ex-Servicemen Welfare)"
        note: "PR #9; 49,925,674 bytes per HEAD of 2026-11-22; no hash pin yet (first fetch records it for review)"
      - doc_id: rules-entitlement-casualty-pensionary-awards-2023-alt
        url: "https://desw.gov.in/sites/default/files/2026-10/Entitlement%20Rules%202023.pdf"
        title: "Entitlement Rules 2023 with MoD letter of 21-09-2023 (second official DESW copy)"
        doc_type: rules
        year: 2023
        issuing_authority: "Ministry of Defence (Department of Ex-Servicemen Welfare)"
        parent_doc_id: rules-entitlement-casualty-pensionary-awards-2023
        expected_sha256: "''' + ER2023_13MB_SHA256 + '''"
        note: "PR #9; already preserved as C5-SRC-P1-ER-2023-HELD-13MB (HF 5524c3d9); a re-fetch must be byte-identical"
      - doc_id: manual-guide-medical-officers-military-pensions-2023
        url: "https://desw.gov.in/sites/default/files/2026-10/GMO%202023.pdf"
        title: "Guide to Medical Officers (Military Pensions), 2023"
        doc_type: manual
        year: 2023
        issuing_authority: "Ministry of Defence (Department of Ex-Servicemen Welfare)"
        note: "PR #9; 36,908,350 bytes per HEAD of 2026-11-22; no hash pin yet"

  # Supreme Court official document host. CONDITIONAL. sci.gov.in and www.sci.gov.in are EXCLUDED: the judgment search
  # (www.sci.gov.in/judgements-judgement-date/) carries a CAPTCHA (probe 2026-11-25). api.sci.gov.in validated
  # 2026-11-25: TLS chain OK (GlobalSign GCC R46 DV), robots.txt 200 with no rules, landing page 200 and empty.
  # Use only for exact PDF URLs that a person has recorded after a manual search. The crawler never searches and
  # never handles a CAPTCHA. Whether a file URL itself is CAPTCHA-free is not yet verified (no URL known).
  sci_official:
    phase: 4
    enabled: false
    priority: 2
    heavy: false
    allowed_hosts: [api.sci.gov.in]
    require_https: true
    documents: []
'''
    s = s.replace("\n# Explicitly forbidden: never fetch, even if linked.", new + "\n# Explicitly forbidden: never fetch, even if linked.")
    diff = "".join(difflib.unified_diff(staging.splitlines(True), s.splitlines(True),
                                        "a/config/sources.yaml (staging a4c0c382)", "b/config/sources.yaml (C13 A7 proposal)"))
    import io
    buf = io.StringIO()
    cols = ["target_id", "identifier", "host", "path_prefix", "basis", "pinned_md5", "pinned_bytes", "justification"]
    w = csv.DictWriter(buf, cols, lineterminator="\n")
    w.writeheader()
    w.writerows(scope_rows)
    return {"sources.yaml.proposed": s, "sources.yaml.diff": diff, "SCOPES": buf.getvalue()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    out = build()
    paths = {"sources.yaml.proposed": PROP / "sources.yaml.proposed", "sources.yaml.diff": PROP / "sources.yaml.diff",
             "SCOPES": SCOPES}
    if a.check:
        ok = all(paths[k].read_text() == v for k, v in out.items())
        print("CHECK", "OK" if ok else "FAIL")
        return 0 if ok else 1
    PROP.mkdir(exist_ok=True)
    for k, v in out.items():
        paths[k].write_text(v)
    print(f"wrote proposal; redirect scopes: {out['SCOPES'].count(chr(10)) - 1}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
