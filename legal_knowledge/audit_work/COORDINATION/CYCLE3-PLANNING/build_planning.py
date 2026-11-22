#!/usr/bin/env python3
"""CYCLE3-PLANNING: deterministic coordinator planning deliverables (stdlib only; DATABASE ONLY).

Reads repository registers (read-only) and writes, in this folder:
  acquisition_schedule.csv         every pending acquisition item (ACQ-01, ACQ-02, ACQ-03, WS-A ACQ-C3-*, WS-B queues)
  affected_records_priority.csv    KB/case records affected by missing statutory history or unresolved case law
  source_authentication_queue.csv  MML editions and official judgment copies needing authentication
  consistency_findings.csv         data inconsistencies detected while building (no source file is edited)

These are PLANNING PROPOSALS ONLY. Nothing is fetched, contacted, approved or determined. Every approval_status is
NOT_APPROVED because no repository file records owner approval of any acquisition run. Coverage or searchability is
never legal correctness. Reserved states are quoted, never changed: r.23(3) CONFLICTING (C-01); r.193 C-08 OPEN;
r.194 C-09 PROPOSAL; r.15 OPEN; r.187(1) OPEN; s.129 OPEN.

Output is byte-identical on re-run: rows are sorted, no timestamps, LF line endings.

  python3 legal_knowledge/audit_work/COORDINATION/CYCLE3-PLANNING/build_planning.py
"""
from __future__ import annotations
import argparse, csv, io, json, re, sys
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
AW = HERE.parents[1]                      # legal_knowledge/audit_work
PFX = "legal_knowledge/audit_work/"

# ---------------------------------------------------------------- constants (copied from repository files)
# ACQ-C3-01 values to verify (task brief) against WS-A-STATUTORY/acquisition_requests_cycle3.csv and s129_trace_cycle3.csv
C3_01_EXPECTED = {"identifier": "in.gazette.e.1950.306", "bytes": "6491633", "md5": "68bcdd4e8db91eb83d1e6b92a393b2db"}
EXCLUDED_HOSTS = {"aftjabalpur.in", "www.aftjabalpur.in"}          # never contact (PILOT-01 T4-03; ACQUISITION_MATRIX blocked_hosts)
COMMERCIAL_HOSTS = {"indiankanoon.org", "www.indiankanoon.org", "www.casemine.com", "casemine.com",
                    "www.scconline.com", "scconline.com", "www.manupatrafast.com", "www.manupatra.com"}
IPV4 = re.compile(r"^\d{1,3}(?:\.\d{1,3}){3}$")
# Reserved items (fixed states; quoted only). Pattern -> label.
RESERVED = [
    (re.compile(r"(?<![A-Z])C-01|R23-VERIFY|\br\.23\(3\)|(?<![\d.])r\.23(?![\dA-Z])|\bAR r\.23$"), "r.23(3) CONFLICTING (C-01)"),
    (re.compile(r"(?<![A-Z])C-08|\br\.193(?![\dA-Z])"), "r.193 C-08 OPEN"),
    (re.compile(r"(?<![A-Z])C-09|\br\.194(?![\dA-Z])"), "r.194 C-09 PROPOSAL"),
    (re.compile(r"OQ-A-10|GAP-15|XC-03|(?<![\d.])r\.15(?![\dA-Z])"), "r.15 OPEN"),
    (re.compile(r"r\.187|OQ-A-11|GAP-14|OQ-C-06"), "r.187(1) OPEN"),
    (re.compile(r"(?<![\d.])s\.129(?![\dA-Z])|CC-17|FID-03"), "s.129 OPEN"),
]
RESERVED_PROVISIONS = {"AR r.23": "r.23(3) CONFLICTING (C-01)", "AR r.193": "r.193 C-08 OPEN",
                       "AR r.194": "r.194 C-09 PROPOSAL", "AR r.15": "r.15 OPEN",
                       "AR r.187": "r.187(1) OPEN", "AA s.129": "s.129 OPEN"}
PRANK = {"P0": 0, "P1": 1, "P2": 2, "EXCLUDED": 9}
SCOPE_ORDER = {"ACQ-01": 0, "ACQ-02": 1, "ACQ-03": 2, "WS-A-C3": 3, "WS-B": 4}
W_STAT, W_UNSTATED, W_CASE, W_RESERVED, W_CAL = 2, 1, 3, 5, 4

FINDINGS: list[dict] = []


def finding(fid, kind, detail, files):
    FINDINGS.append({"finding_id": fid, "kind": kind, "detail": detail, "source_files": files})


def rows(rel):
    with open(AW / rel, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def cite(rel, rid, idx=None):
    return f"{PFX}{rel}:{rid}" + (f" (data row {idx})" if idx is not None else "")


def host_of(url):
    u = (url or "").strip()
    if not u.lower().startswith(("http://", "https://")):
        return ""
    return (urlparse(u).hostname or "").lower()


def tokens(text):
    return set(re.findall(r"\b(?:AR|AA|GAP|OQ|CC|FID|XC|PG|C)-[A-Z0-9]+(?:-[A-Z0-9]+)*\b", text or ""))


def expand_ranges(text):
    """Expand register shorthand such as 'AR-002..005' / 'AR-037..046' / 'AR-012/013/015' into AR ids."""
    out = set()
    for m in re.finditer(r"AR-(\d{3})((?:/\d{3})+|\.\.(\d{3}))?", text or ""):
        a = int(m.group(1))
        if m.group(3):
            out |= {f"AR-{i:03d}" for i in range(a, int(m.group(3)) + 1)}
        else:
            out.add(f"AR-{a:03d}")
            if m.group(2):
                out |= {f"AR-{int(x):03d}" for x in m.group(2).strip("/").split("/")}
    return out


def reserved_hits(text):
    return sorted({lab for rx, lab in RESERVED if rx.search(text or "")})


def norm_priority(v):
    v = (v or "").strip()
    if v in ("P0",):
        return "P0"
    if v in ("P1", "1"):
        return "P1"
    if v.startswith("P0/"):
        return "P0"
    if v in ("P2", "P3", "2", "3"):
        return "P2"
    return ""


OUT = HERE
COMMERCIAL_RX = re.compile(r"(?:https?://)?(?:www\.)?(?:indiankanoon\.org|casemine\.com|scconline\.com|manupatrafast\.com|"
                           r"manupatra\.com)\S*", re.I)
COMMERCIAL_WITHHELD = "[commercial legal database reference withheld; never a source]"


def sanitize(v):
    """No commercial legal database is ever shown as a host, holder or source in a planning output."""
    return COMMERCIAL_RX.sub(COMMERCIAL_WITHHELD, v) if isinstance(v, str) else v


def write_csv(name, header, data, clean=True):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    for r in data:
        w.writerow([sanitize(r.get(h, "")) if clean else r.get(h, "") for h in header])
    (OUT / name).write_text(buf.getvalue(), encoding="utf-8")
    return len(data)


# ---------------------------------------------------------------- shared registers
COMPL_REL = "WS-A-STATUTORY/statutory_version_completeness_cycle3.csv"
COMPL = rows(COMPL_REL)
COMPL_BY = {r["provision"]: r for r in COMPL}
ARREG_REL = "ARMY-RULES-CHAIN-01/army_rules_instrument_register.csv"
ARREG = rows(ARREG_REL)
CHAIN_REL = "WS-A-STATUTORY/army_act_amendment_chain.csv"
CHAIN = rows(CHAIN_REL)
CHAIN_ADD_REL = "WS-A-STATUTORY/army_act_amendment_chain_addendum_cycle3.csv"
CHAIN_ADD = rows(CHAIN_ADD_REL)
CAL_REL = "COORDINATION/CALIBRATION-01/calibration_package.csv"
CAL = {r["record_id"] for r in rows(CAL_REL)}
XW_REL = "WS-B-JUDGMENTS/crosswalk_cases53_kb658.csv"
XW = rows(XW_REL)
LINKS_REL = "WS-B-JUDGMENTS/kb658_case_name_links_cycle3.csv"
LINKS = rows(LINKS_REL)


def chain_short(number_year):
    m = re.match(r"(\d+) of (\d{4})$", (number_year or "").strip())
    return f"Act {m.group(1)}/{m.group(2)}" if m else None


def provisions_for_tokens(dep_text, extra_ids=(), item_text=""):
    """Completeness provisions mechanically linked to an acquisition item's dependents.
    (a) AR ids named in a provision's located_amending_instruments; (b) Act number/year of an AA chain id named in
    located_amending_instruments; (c) OQ/CC/FID/XC/C ids named in conflict_or_review_state; (d) the acquisition id
    itself named anywhere in the completeness row (e.g. ACQ-C3-01); (e) for an item whose target is the Army Act 1950
    'as enacted' (chain id AA-00), every provision whose enacted text is recorded as not held."""
    toks = tokens(dep_text) | expand_ranges(dep_text)
    ar_ids = {t for t in toks if re.fullmatch(r"AR-\d{3}", t)}
    acts = set()
    for c in CHAIN + CHAIN_ADD:
        base = c["chain_id"]
        if any(base == t or base.startswith(t + "-") for t in toks if t.startswith("AA-")):
            s = chain_short(c["number_year"])
            if s:
                acts.add(s)
    other = {t for t in toks if re.match(r"(OQ|CC|FID|XC|C)-", t)}
    out = set()
    for r in COMPL:
        lai = r["located_amending_instruments"]
        if ar_ids & set(re.findall(r"AR-\d{3}", lai)):
            out.add(r["provision"])
        if any(re.search(re.escape(a) + r"(?!\d)", lai) for a in acts):
            out.add(r["provision"])
        if other & tokens(r["conflict_or_review_state"]):
            out.add(r["provision"])
        whole = " ".join(r.values())
        if any(x and x in whole for x in extra_ids):
            out.add(r["provision"])
        if "AA-00" in toks and "as enacted" in item_text and "enacted text not held" in r["base_text_image_checked"]:
            out.add(r["provision"])
    return out


def prov_sort_key(p):
    m = re.match(r"(AA|AR) [rs]\.(\d+)([A-Z]*)", p)
    return (m.group(1), int(m.group(2)), m.group(3)) if m else (p, 0, "")


# ---------------------------------------------------------------- 1. acquisition schedule
def build_acquisitions():
    items = []
    # ---- ACQ-01 (batches.json)
    rel = "ACQ-01/batches.json"
    b = json.loads((AW / rel).read_text(encoding="utf-8"))
    configured = {"ACQ-01-B1", "ACQ-01-B2", "ACQ-01-B6"}   # acq3wt docs/acquisition/inventory_match_2026-11-22.txt
    act_by_doc = {"act-commanders-in-chief-change-designation-1955": "AA-01",   # number/year matched to
                  "act-air-force-army-laws-amdt-1975": "AA-06",                  # army_act_amendment_chain.csv
                  "act-army-amendment-1992": "AA-08"}
    for bt in b["batches"]:
        for i, it in enumerate(bt.get("items", [])):
            doc = it["doc_id"]
            url = it.get("url") or ""
            acq_id = "ACQ-01:" + (doc if not doc.startswith("(") else "B5-aft-static-listings")
            h = host_of(url)
            note = it.get("note") or ""
            excl = ""
            if bt["batch"] == "ACQ-01-B5":
                hosts = "aft.gov.in; 103.154.2.123 (bare IP, HTTP PDF host)"
                excl = ("EXCLUDED: bare-IP AFT PDF route 103.154.2.123 over HTTP "
                        f"({PFX}ACQ-01/AFT_ROUTE_ASSESSMENT.md); never contact")
            elif h:
                hosts = h
            elif it.get("source") == "indiacode":
                hosts = "indiacode.gov.in (item ID recorded; bitstream resolved at run time)"
            elif it.get("source") == "manual_upload":
                hosts = "NONE (owner-supplied copy)"
            else:
                hosts = "NOT_RECORDED"
            if it.get("expected_md5") and it.get("expected_size"):
                pin = f"md5={it['expected_md5']}; bytes={it['expected_size']}"
            elif it.get("source") == "indiacode" and bt["batch"] == "ACQ-01-B6":
                pin = "NOT_PINNED (India Code serves download-specific bytes; SHA-256 to be recorded after an approved fetch)"
            else:
                pin = "NOT_PINNED"
            located = "YES" if (url.startswith("http") or it.get("source") == "indiacode"
                                or bt["batch"] == "ACQ-01-B5") else "NO"
            deps = list(it.get("feeds") or [])
            ar = []
            num, yr = (it.get("number") or ""), it.get("year")
            for r in ARREG:
                if num and r["instrument"].split(" (")[0] == num and str(yr) and (r["instrument_date"] or "")[:4] == str(yr):
                    ar.append(r["instr_id"])
            if doc in act_by_doc:
                ar.append(act_by_doc[doc])
            deps += ar
            scope = ("configured in PR #8 (unmerged)" if bt["batch"] in configured else "not configured")
            items.append(dict(
                acq_id=acq_id, scope="ACQ-01", aliases="",
                batch=f"{bt['batch']} ({scope})", item=it.get("title") or doc, host=hosts, url_as_recorded=url or note[:160],
                authority_class=f"provenance_class={it.get('provenance_class') or 'NOT_RECORDED'} (as recorded)",
                pinned_integrity=pin, source_located=located,
                status_as_recorded=b.get("status", ""), deps=deps, recorded_priority=f"batch priority {bt['priority']}",
                rec_norm=norm_priority(str(bt["priority"])), exclusion=excl,
                notes="; ".join(x for x in ["approval_needed: " + " | ".join(bt.get("approval_needed", [])), note] if x)[:400],
                source_file_row=f"{PFX}{rel}:batches[{bt['batch']}].items[{i}] doc_id={doc}"))
    # ---- ACQ-02 (supplement_inventory.csv)
    rel = "ACQ-02/supplement_inventory.csv"
    for i, r in enumerate(rows(rel), 1):
        ar = [a["instr_id"] for a in ARREG if a["sha256"][:64] == r["sha256"]
              and a["instrument"].split(" (")[0] == r["instrument"]]
        shared = [x["supp_id"] for x in rows(rel) if x["sha256"] == r["sha256"] and x["supp_id"] != r["supp_id"]]
        items.append(dict(
            acq_id=r["supp_id"], scope="ACQ-02", aliases="",
            batch="ACQ-02 archive_acq02 (configured in PR #17, unmerged)",
            item=f"{r['instrument']} dated {r['instrument_date']} {r['short_title_as_printed']}".strip(),
            host=host_of(r["url"]) or "NOT_RECORDED", url_as_recorded=r["url"],
            authority_class=(f"document_authority={r['document_authority']}; carrier_provenance={r['carrier_provenance']}; "
                             f"authenticity={r['authenticity']} (as recorded)"),
            pinned_integrity=f"sha256={r['sha256']}; md5={r['md5']}; bytes={r['bytes']}",
            source_located="YES", status_as_recorded="PROPOSAL (not executed; ACQ-02/README.md)",
            deps=ar, recorded_priority="NOT_RECORDED", rec_norm="", exclusion="",
            notes=("same file as " + ",".join(shared)) if shared else "",
            source_file_row=cite(rel, r["supp_id"], i)))
    # ---- ACQ-03 (WS-A acq03_pinned_candidates.csv) with aliases from acquisition_requests*.csv and ACQ-C3-03/04
    prio = {}
    for rel2, pcol in (("WS-A-STATUTORY/acquisition_requests.csv", "priority"),
                       ("WS-A-STATUTORY/acquisition_requests_cycle2.csv", "priority")):
        for r in rows(rel2):
            prio[r["request_id"]] = (r[pcol], r, rel2)
    c3 = {r["request_id"]: r for r in rows("WS-A-STATUTORY/acquisition_requests_cycle3.csv")}
    rel = "WS-A-STATUTORY/acq03_pinned_candidates.csv"
    for i, r in enumerate(rows(rel), 1):
        aid = r["acq03_id"]
        n = int(aid.split("-")[1])
        prior = r["prior_request_id"]
        aliases = [prior] if prior else []
        extra_deps = []
        if 1 <= n <= 9:
            aliases.append("ACQ-C3-03")
            extra_deps.append(c3["ACQ-C3-03"]["closes"])
        if 40 <= n <= 44:
            aliases.append("ACQ-C3-04")
            extra_deps.append(c3["ACQ-C3-04"]["closes"])
        h = r["host"]
        if aid == "ACQ03-016":
            scope = "not pinned in PR #23 config (owner keep/drop decision)"
        elif not h:
            scope = "not configured (no lawful online source known)"
        elif h == "indiacode.gov.in":
            scope = "official_instruments_acq03 (PR #23, unmerged)"
        else:
            scope = "archive_acq03 (PR #23, unmerged)"
        if h == "indiacode.gov.in":
            pin = (f"NOT_PINNED (listing md5={r['expected_md5']}, bytes={r['expected_bytes']} informational only: "
                   "host watermarks PDFs; served SHA-256 to be recorded)")
            auth = "carrier GOVERNMENT_HOSTED_COPY (as recorded in acquisition_requests_cycle2.csv source column)"
        elif r["expected_md5"] and r["expected_bytes"]:
            pin = f"md5={r['expected_md5']}; bytes={r['expected_bytes']}"
            if aid == "ACQ03-016":
                pin += " (recorded; NOT pinned in PR #23 config)"
            auth = f"NOT_RECORDED in row (file_source_per_metadata={r['file_source_per_metadata']})"
        else:
            pin = "NOT_PINNED"
            auth = "NOT_RECORDED"
        rp = prio.get(prior, ("", None, None))[0]
        items.append(dict(
            acq_id=aid, scope="ACQ-03", aliases=";".join(aliases), batch=f"ACQ-03 {r['batch']} ({scope})",
            item=r["target_instruments"], host=h or "NOT_RECORDED", url_as_recorded=r["download_url"],
            authority_class=auth, pinned_integrity=pin, source_located="YES" if r["download_url"] else "NO",
            status_as_recorded=r["status"], deps=[r["closes"]] + extra_deps,
            recorded_priority=f"{prior} priority {rp}" if rp else "NOT_RECORDED", rec_norm=norm_priority(rp),
            exclusion="", notes=r["notes"][:300], source_file_row=cite(rel, aid, i)))
        # integrity cross-check against the prior request row
        if prior in prio and prio[prior][1] is not None:
            pr = prio[prior][1]
            pm, pb = pr.get("expected_md5", ""), pr.get("expected_bytes", "")
            if (pm or pb) and r["expected_md5"] and (pm != r["expected_md5"] or pb != r["expected_bytes"]):
                finding(f"CF-ACQ03-{aid}", "INTEGRITY_VALUE_MISMATCH",
                        f"{aid} md5/bytes {r['expected_md5']}/{r['expected_bytes']} differ from {prior} {pm}/{pb}",
                        f"{PFX}{rel}; {PFX}{prio[prior][2]}")
    # ---- WS-A cycle 3 (ACQ-C3-01/02/05/06; 03/04 are REFERENCE rows folded into ACQ-03 aliases)
    rel = "WS-A-STATUTORY/acquisition_requests_cycle3.csv"
    s129 = rows("WS-A-STATUTORY/s129_trace_cycle3.csv")
    for i, r in enumerate(rows(rel), 1):
        rid = r["request_id"]
        if r["status"].startswith("REFERENCE"):
            continue
        auth = "NOT_RECORDED"
        if rid == "ACQ-C3-01":
            s1 = [x for x in s129 if x["step"] == "1"][0]
            auth = (f"{s1['authority_class']} (as recorded: {PFX}WS-A-STATUTORY/s129_trace_cycle3.csv:step 1)")
        pin = (f"md5={r['expected_md5']}; bytes={r['expected_bytes']}" if r["expected_md5"] and r["expected_bytes"]
               else "NOT_PINNED")
        items.append(dict(
            acq_id=rid, scope="WS-A-C3", aliases="", batch="WS-A cycle 3 (not configured; no config PR exists)",
            item=r["target"], host=host_of(r["url"]) or "NOT_RECORDED", url_as_recorded=r["url"] or r["source"],
            authority_class=auth, pinned_integrity=pin, source_located="YES" if r["url"] else "NO",
            status_as_recorded=r["status"], deps=[r["closes"], r["reason"]], recorded_priority="NOT_RECORDED",
            rec_norm="", exclusion="", notes=r["overlap"], source_file_row=cite(rel, rid, i)))
    # ---- WS-B judgment queues
    xw_by_case, xw_by_spec = {}, {}
    for x in XW + LINKS:
        kb = x.get("kb_record_id", "")
        if not kb:
            continue
        if x.get("case53_id"):
            xw_by_case.setdefault(x["case53_id"], set()).add(kb)
        xw_by_spec.setdefault(x["spec_key"], set()).add(kb)
    rel = "WS-B-JUDGMENTS/pending_acquisition_cycle3.csv"
    c3rows = rows(rel)
    c3_specs = {r["spec_key"] for r in c3rows}
    queue_rows = [(rel, i, r, "WS-B pending_acquisition_cycle3 (cycle C3 queue)") for i, r in enumerate(c3rows, 1)]
    rel1 = "WS-B-JUDGMENTS/pending_source_queue.csv"
    for i, r in enumerate(rows(rel1), 1):
        specs = [s for s in r["spec_key"].split(";") if s]
        if specs and all(s in c3_specs for s in specs):
            continue          # restated by a cycle-3 queue row (same spec_key)
        queue_rows.append((rel1, i, r, f"WS-B pending_source_queue (cycle {r['cycle']} queue; not restated in C3)"))
    for rel_, i, r, batch in queue_rows:
        u = r["official_url_or_holder_if_known"].strip()
        h = host_of(u)
        excl, notes = "", r["note"]
        if h in COMMERCIAL_HOSTS:
            excl = (f"COMMERCIAL_HOLDER_NOT_A_SOURCE: recorded holder {h} is a commercial legal database; never evidence, "
                    "never contacted; an official court copy is still required")
            finding(f"CF-WSB-{r['queue_id']}", "COMMERCIAL_DATABASE_RECORDED_AS_HOLDER",
                    f"{r['queue_id']} official_url_or_holder_if_known is {u}; must not be used as a source",
                    f"{PFX}{rel_}")
        located = "YES" if (h and h not in COMMERCIAL_HOSTS and h not in EXCLUDED_HOSTS and not IPV4.match(h)) else "NO"
        specs = [s for s in r["spec_key"].split(";") if s]
        cases = [c for c in (r.get("case53_id") or "").split(";") if c]
        deps = set()
        for c in cases:
            deps |= xw_by_case.get(c, set())
        for s in specs:
            deps |= xw_by_spec.get(s, set())
        chk = r.get("official_url_http_check", "")
        items.append(dict(
            acq_id=r["queue_id"], scope="WS-B", aliases="", batch=batch,
            item=" ".join(x for x in [r["spec_key"], r.get("case53_id", ""), r["court"], r["case_number"], r["decision_date"]] if x),
            host=(f"NONE (commercial holder {h} recorded upstream; not a source, never contacted)" if h in COMMERCIAL_HOSTS
                  else (h if h else "NOT_RECORDED")), url_as_recorded=u,
            authority_class="NOT_RECORDED (target: official court copy)",
            pinned_integrity="NOT_PINNED (no expected hash recorded)", source_located=located,
            status_as_recorded=r["action"] + (f"; downloaded_by_ws_b={r['downloaded_by_ws_b']}" if r.get("downloaded_by_ws_b") else ""),
            deps=sorted(deps), recorded_priority=r["priority"] or "NOT_RECORDED", rec_norm=norm_priority(r["priority"]),
            exclusion=excl, notes="; ".join(x for x in [notes, (f"official_url_http_check={chk}" if chk else "")] if x)[:400],
            source_file_row=cite(rel_, r["queue_id"], i)))
    # ---- derive provisions, reserved hits, priority, sequence
    for it in items:
        dep_text = " ".join(it["deps"])
        extra = [it["acq_id"]] + [a for a in it["aliases"].split(";") if a]
        provs = sorted(provisions_for_tokens(dep_text, extra, it["item"]) if it["scope"] != "WS-B" else set(),
                       key=prov_sort_key)
        it["provisions"] = provs
        recs = ""
        if it["scope"] == "WS-B":
            recs = "KB records: " + ";".join(it["deps"]) if it["deps"] else "KB records: NONE_LINKED"
            bd = recs
        else:
            bd = "; ".join(x for x in [dep_text.strip(), ("provisions: " + ";".join(provs)) if provs else ""] if x)
        it["blocking_dependents"] = bd or "NOT_RECORDED"
        hosts_all = [x.strip().split(" ")[0] for x in it["host"].split(";")]
        if not it["exclusion"] and any(x in EXCLUDED_HOSTS or IPV4.match(x) for x in hosts_all):
            it["exclusion"] = "EXCLUDED: aftjabalpur.in or bare-IP route; never contact"
        hits = reserved_hits(" ".join([dep_text, it["item"], " ".join(provs)])) if it["scope"] != "WS-B" else []
        cal_hit = sorted(set(it["deps"]) & CAL) if it["scope"] == "WS-B" else []
        pinned = not it["pinned_integrity"].startswith("NOT_PINNED")
        basis = []
        if it["exclusion"].startswith("EXCLUDED"):
            pr = "EXCLUDED"
            basis.append("excluded route (never contact)")
        else:
            cands = []
            if hits:
                cands.append("P0"); basis.append("unblocks reserved item(s): " + ", ".join(hits))
            if it["rec_norm"] == "P0":
                cands.append("P0"); basis.append(f"recorded priority {it['recorded_priority']}")
            if it["rec_norm"] == "P1":
                cands.append("P1"); basis.append(f"recorded priority {it['recorded_priority']}")
            if it["source_located"] == "YES" and pinned:
                cands.append("P1"); basis.append("source located and integrity pinned")
            if cal_hit:
                cands.append("P1"); basis.append("unblocks calibration-sample record(s): " + ";".join(cal_hit))
            pr = min(cands, key=lambda p: PRANK[p]) if cands else "P2"
            if not cands:
                basis.append("default (no P0/P1 condition met)")
            if "optional" in it["status_as_recorded"].lower() and pr != "P2":
                pr = "P2"
                basis.append("capped at P2: recorded as optional")
        it["priority"] = pr
        it["priority_basis"] = "; ".join(basis)
        it["approval_status"] = "NOT_APPROVED"
        it["_reserved"] = hits
    order = sorted(items, key=lambda x: (PRANK[x["priority"]], 0 if x["source_located"] == "YES" else 1,
                                         0 if not x["pinned_integrity"].startswith("NOT_PINNED") else 1,
                                         SCOPE_ORDER[x["scope"]], x["acq_id"]))
    seq = 0
    for it in order:
        if it["priority"] == "EXCLUDED":
            it["proposed_sequence"] = "NOT_SEQUENCED (EXCLUDED)"
        else:
            seq += 1
            it["proposed_sequence"] = f"{seq:03d}"
    return order


# ---------------------------------------------------------------- 2. affected records
def build_affected(acq):
    inv_rel = "WS-C-MML/kb658_source_coverage_inventory.csv"
    inv = rows(inv_rel)
    edges_rel = "WS-D-QUALITY/relation_graph_versioned_edges.csv"
    edges = rows(edges_rel)
    pend_rel = "WS-B-JUDGMENTS/pending_acquisition_cycle3.csv"
    pend = rows(pend_rel)
    pend_cases = {r["case53_id"] for r in pend if r["case53_id"]}
    # provision -> acquisition ids; case -> queue ids
    prov_acq, case_acq, spec_acq = {}, {}, {}
    for it in acq:
        if it["priority"] == "EXCLUDED":
            continue
        for p in it["provisions"]:
            prov_acq.setdefault(p, set()).add(it["acq_id"])
    for rel in ("WS-B-JUDGMENTS/pending_acquisition_cycle3.csv", "WS-B-JUDGMENTS/pending_source_queue.csv"):
        for r in rows(rel):
            for c in (r.get("case53_id") or "").split(";"):
                if c:
                    case_acq.setdefault(c, set()).add(r["queue_id"])
            for s in r["spec_key"].split(";"):
                if s:
                    spec_acq.setdefault(s, set()).add(r["queue_id"])
    # case links per record
    case_links = {}
    case_records = {}
    for src_rel, data in ((XW_REL, XW), (LINKS_REL, LINKS)):
        for x in data:
            kb = x.get("kb_record_id", "")
            if not kb:
                continue
            cid = x["case53_id"] or f"spec:{x['spec_key']}"
            unresolved = ("OFFICIAL_COPY_HELD" not in x["identity_state"]) or (x["case53_id"] in pend_cases)
            if not unresolved:
                continue
            case_links.setdefault(kb, {})[cid] = (x["spec_key"], x["identity_state"], src_rel)
            case_records.setdefault(cid, set()).add(kb)
    unst = {}
    for e in edges:
        st = e["effective_date_status"]
        if "EFFECTIVE_DATE_UNSTATED" in e["flags"] or st.startswith(("NOT_", "UNKNOWN")):
            pre = "AR " if e["instrument"].startswith("Army Rules") else "AA " if e["instrument"].startswith("Army Act") else e["instrument"] + " "
            unst.setdefault(e["record_id"], set()).add(pre + e["provision"])
    edge_provs = {}
    for e in edges:
        pre = "AR " if e["instrument"].startswith("Army Rules") else "AA " if e["instrument"].startswith("Army Act") else e["instrument"] + " "
        edge_provs.setdefault(e["record_id"], set()).add(pre + e["provision"])
    out = []
    no_queue_cases = set()
    for r in inv:
        rid = r["record_id"]
        cited = {f"AA s.{s}" for s in r["aa_sections"].split(";") if s} | {f"AR r.{s}" for s in r["ar_rules"].split(";") if s}
        stat = sorted((p for p in cited if p in COMPL_BY and
                       COMPL_BY[p]["completeness_status"].startswith(("NOT_ESTABLISHED", "PARTIALLY_ESTABLISHED"))),
                      key=prov_sort_key)
        uns = sorted(unst.get(rid, set()), key=prov_sort_key)
        res = sorted({RESERVED_PROVISIONS[p] for p in (cited | edge_provs.get(rid, set())) if p in RESERVED_PROVISIONS})
        cases = case_links.get(rid, {})
        cal = rid in CAL
        score = W_STAT * len(stat) + W_UNSTATED * len(uns) + W_CASE * len(cases) + W_RESERVED * len(res) + W_CAL * cal
        if not (stat or uns or cases):
            continue
        breadth = sum(int(COMPL_BY[p]["kb_records_citing"] or 0) for p in stat) + sum(len(case_records[c]) for c in cases)
        acq_ids = set()
        for p in set(stat) | set(uns):
            acq_ids |= prov_acq.get(p, set())
        for cid, (spec, _, _) in cases.items():
            q = case_acq.get(cid, set()) | spec_acq.get(spec, set())
            if not q:
                no_queue_cases.add(f"{cid} ({spec})")
            acq_ids |= q
        reasons = []
        if stat:
            reasons.append(f"STATUTORY_HISTORY_INCOMPLETE({len(stat)})")
        if uns:
            reasons.append(f"EFFECTIVE_DATE_UNSTATED({len(uns)})")
        if cases:
            reasons.append(f"CASE_LAW_UNRESOLVED({len(cases)})")
        if res:
            reasons.append("RESERVED_ITEM(" + "; ".join(res) + ")")
        if cal:
            reasons.append("CALIBRATION_SAMPLE")
        srcs = [f"{PFX}{inv_rel}:{rid}"]
        if stat:
            srcs.append(f"{PFX}{COMPL_REL}:" + ";".join(stat))
        if uns:
            srcs.append(f"{PFX}{edges_rel}:record_id={rid}")
        if cases:
            srcs.append(f"{PFX}{XW_REL}|{LINKS_REL}:kb_record_id={rid}")
        if cal:
            srcs.append(f"{PFX}{CAL_REL}:{rid}")
        out.append(dict(
            record_id=rid, module=r["module"], kind=r["kind"], in_calibration_sample="YES" if cal else "NO",
            reasons="; ".join(reasons), provisions=";".join(stat), provisions_effective_date_unstated=";".join(uns),
            reserved_items="; ".join(res),
            cases=";".join(f"{c}[{v[0]}:{v[1]}]" for c, v in sorted(cases.items())),
            n_provisions=len(stat), n_unstated=len(uns), n_cases=len(cases), n_reserved=len(res),
            unblocked_by_acq_ids=";".join(sorted(acq_ids)) or "NONE_RECORDED",
            score=score, score_components=(f"{W_STAT}*{len(stat)}+{W_UNSTATED}*{len(uns)}+{W_CASE}*{len(cases)}"
                                           f"+{W_RESERVED}*{len(res)}+{W_CAL}*{int(cal)}"),
            breadth_tiebreak=breadth, source_file_rows=" | ".join(srcs)))
    out.sort(key=lambda x: (-x["score"], -x["breadth_tiebreak"], x["record_id"]))
    for i, x in enumerate(out, 1):
        x["rank"] = i
    if no_queue_cases:
        finding("CF-WSB-NOQUEUE", "UNRESOLVED_CASE_WITHOUT_ACQUISITION_REQUEST",
                "unresolved/mirror-only cases linked to KB records with no queue row in pending_acquisition_cycle3.csv "
                "or pending_source_queue.csv: " + "; ".join(sorted(no_queue_cases)),
                f"{PFX}{XW_REL}; {PFX}WS-B-JUDGMENTS/pending_acquisition_cycle3.csv; {PFX}WS-B-JUDGMENTS/pending_source_queue.csv")
    return out


# ---------------------------------------------------------------- 3. authentication queue
MML_FILES = ["MML 1.doc", "MML 2.pdf", "MML vol 2(AA).doc.doc", "MML vol 2(AA).pdf", "MML vol 2(AR).doc-1.doc",
             "MML vol 2(AR).doc.doc", "MML vol 3.doc.doc", "MML vol 3.pdf.pdf"]


def mml_files_named(text):
    """Mechanical mapping of procedural_contradictions_cycle3.csv mml_file text to edition files."""
    t = text or ""
    if "all MML" in t:
        return set(MML_FILES)
    out = {f for f in MML_FILES if f in t}
    if "doc-1" in t:
        out.add("MML vol 2(AR).doc-1.doc")
    if "MML vol 2(AR) DOCs" in t:
        out |= {"MML vol 2(AR).doc-1.doc", "MML vol 2(AR).doc.doc"}
    if "MML vol 2(AA).pdf; DOC" in t:
        out.add("MML vol 2(AA).doc.doc")
    if re.search(r"MML vol 3(?![.\w])", t):
        out |= {"MML vol 3.doc.doc", "MML vol 3.pdf.pdf"}
    return out


def build_auth(acq):
    out = []
    es_rel, ev_rel, pc_rel = ("WS-C-MML/mml_edition_status.csv", "WS-C-MML/mml_edition_evidence_cycle3.csv",
                              "WS-C-MML/procedural_contradictions_cycle3.csv")
    ev = rows(ev_rel)
    pcs = rows(pc_rel)
    for i, e in enumerate(rows(es_rel), 1):
        f = e["file"]
        evs = [x for x in ev if x["file"] == f]
        if any(x["file_sha256"] != e["sha256"] for x in evs):
            finding(f"CF-WSC-{e['es_id']}", "SHA256_MISMATCH", f"{f}: edition status sha256 differs from evidence rows",
                    f"{PFX}{es_rel}; {PFX}{ev_rel}")
        reqs = sorted({x["what_would_authenticate_this_edition"] for x in evs if x["what_would_authenticate_this_edition"]})
        pcf = [p for p in pcs if f in mml_files_named(p["mml_file"])]
        res = sorted({lab for p in pcf for lab in reserved_hits(p["provision"] + " " + p["related_ids"])})
        p1 = [p["pc_id"] for p in pcf if p["severity"] == "P1"]
        recs = sorted({t for p in pcf for t in re.findall(r"\b[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+\b|\bSC\d+\b", p["kb_records_citing"])
                       if not re.match(r"(PG|FID|CC|XC|OQ|PX|C)-", t)})
        if res:
            pr, basis = "P0", "named in procedural contradiction(s) touching reserved item(s): " + ", ".join(res)
        elif p1:
            pr, basis = "P1", "named in P1 procedural contradiction(s): " + ";".join(p1)
        else:
            pr, basis = "P2", "default (no reserved or P1 contradiction names this file)"
        out.append(dict(
            auth_id=f"AUTH-MML-{e['es_id']}", item_type="MML_EDITION", item=f, case_key="n/a (manual edition)",
            case53_id="n/a", official_copy="n/a (manual; see current_state)", mirror_copy="n/a",
            http_availability="n/a (user-supplied file; no online source recorded)", identity_status="n/a",
            identification_uncertainty="edition undated; see current_state", acquisition_request="NO_ACQUISITION_REQUEST",
            current_state=(f"edition_status={e['edition_status']}; authentication_evidence={e['authentication_evidence']}; "
                           f"document_authority={e['document_authority']}; carrier_provenance={e['carrier_provenance']}; "
                           f"copy_fidelity={e['copy_fidelity']} (all as recorded)"),
            evidence_held=(f"sha256={e['sha256']}; bytes={e['bytes']}; evidence rows "
                           + ";".join(f"{x['ev_id']}[{x['check_id'] or 'no check id'}]" for x in evs)
                           + f"; access_marking_observed={e['access_marking_observed'][:120]}"),
            authentication_requires=(" || ".join(reqs) if reqs else "NOT_RECORDED"),
            who_or_acquisition=("Owner (custodian route named in the evidence rows); no acquisition ID recorded in the "
                                "repository; agents send no correspondence"),
            linked_records=";".join(recs), contradictions=";".join(p["pc_id"] for p in pcf),
            priority=pr, priority_basis=basis,
            source_file_row=f"{cite(es_rel, e['es_id'], i)} | {PFX}{ev_rel}:file={f} | {PFX}{pc_rel}:" + (";".join(p["pc_id"] for p in pcf) or "none")))
    # judgments: seeded from EVERY WS-B register that can mark a judgment as needing an official copy, keyed by the
    # stable WS-B identity spec_key (never a display name). Nothing is hard-coded: a regenerated register is picked up.
    idr_rel = "WS-B-JUDGMENTS/identity_resolution.csv"
    idr3_rel = "WS-B-JUDGMENTS/identity_resolution_cycle3.csv"
    acs_rel = "WS-B-JUDGMENTS/authoritative_copy_status_cycle3.csv"
    hr_rel = "WS-B-JUDGMENTS/holdings_register_cycle3.csv"
    pq3_rel = "WS-B-JUDGMENTS/pending_acquisition_cycle3.csv"
    pq_rel = "WS-B-JUDGMENTS/pending_source_queue.csv"
    idr = {r["spec_key"]: (i, r) for i, r in enumerate(rows(idr_rel), 1)}
    held = {k for k, (_, r) in idr.items() if "OFFICIAL_COPY_HELD" in r["identity_state"]}
    xw = {}
    for x in XW + LINKS:
        if x.get("kb_record_id"):
            xw.setdefault(x["spec_key"], set()).add(x["kb_record_id"])
    J = {}

    def entry(spec):
        return J.setdefault(spec, {"case53": set(), "label": "", "src": [], "official": [], "mirror": [], "http": [],
                                   "identity": [], "uncert": [], "queues": {}, "notes": [], "ev": []})

    def needs(spec):
        return bool(spec) and spec not in held

    for k, (i, r) in idr.items():
        if not needs(k):
            continue
        d = entry(k)
        d["case53"].add(r["case53_id"])
        d["label"] = r["ws_b_label"] or r["curated_title"] or k
        d["identity"].append(f"{r['identity_state']} (identity_resolution.csv)")
        d["official"].append("NO (no WS-B-held court copy; identity_resolution.csv held_copy_url blank)"
                             if not r["held_copy_url"] else f"held_copy_url={r['held_copy_url']} "
                             f"carrier={r['held_copy_carrier_provenance'] or 'NOT_RECORDED'} (identity_resolution.csv)")
        if r["intern_sha256"]:
            d["mirror"].append(f"intern copy sha256={r['intern_sha256']} (identity_resolution.csv)")
        for col in ("discrepancies", "note"):
            if r[col].strip():
                d["uncert"].append(f"{col}: {r[col].strip()[:300]}")
        d["src"].append(cite(idr_rel, k, i))
    for i, r in enumerate(rows(idr3_rel), 1):
        if not needs(r["spec_key"]) or "OFFICIAL_COPY_HELD" in r["cycle3_state"]:
            continue
        d = entry(r["spec_key"])
        d["case53"].add(r["case53_id"])
        d["label"] = d["label"] or r["spec_key"]
        d["identity"].append(f"cycle3: {r['cycle3_state']} (identity_resolution_cycle3.csv)")
        d["uncert"].append(f"cycle3 evidence_strength: {r['evidence_strength']}; next_action: {r['next_action']}")
        d["src"].append(cite(idr3_rel, r["spec_key"], i))
    for i, r in enumerate(rows(acs_rel), 1):
        if not needs(r["spec_key"]) or not r["official_copy_held"].upper().startswith("NO"):
            continue
        d = entry(r["spec_key"])
        d["case53"].add(r["case53_id"])
        d["label"] = d["label"] or r["case"]
        d["official"].append(f"{r['official_copy_held']} (authoritative_copy_status_cycle3.csv; state {r['state']})")
        if r["intern_mirror_sha256"]:
            d["mirror"].append(f"intern mirror sha256={r['intern_mirror_sha256']} (authoritative_copy_status_cycle3.csv)")
        if r["official_url_located"] or r["read_only_lookup_result"]:
            d["http"].append(f"url={r['official_url_located'] or 'none located'}; lookup={r['read_only_lookup_result'] or 'none'}"
                             " (authoritative_copy_status_cycle3.csv)")
        d["src"].append(cite(acs_rel, r["spec_key"], i))
    for i, h in enumerate(rows(hr_rel), 1):
        if not needs(h["spec_key"]) or h["copy_role"] == "OFFICIAL_COURT_COPY":
            continue
        d = entry(h["spec_key"])
        d["case53"].add(h["case53_id"])
        d["label"] = d["label"] or h["judgment"]
        if h["copy_role"] == "NOT_HELD":
            d["official"].append(f"NOT_HELD (holdings {h['row_id']}: {h['technical_review_state']})")
        else:
            d["mirror"].append(f"holdings {h['row_id']} copy_role={h['copy_role']} copy_sha256={h['copy_sha256'] or 'NOT_RECORDED'}")
            d["ev"].append(f"holdings {h['row_id']} page_render_sha256={h['page_render_sha256'] or 'NOT_RECORDED'}"
                           f" pinpoint={h['para_pinpoint'] or 'NOT_RECORDED'}")
        d["src"].append(cite(hr_rel, h["row_id"], i))
    for rel_, has_check in ((pq3_rel, True), (pq_rel, False)):
        for i, r in enumerate(rows(rel_), 1):
            ks = [k for k in r["spec_key"].split(";") if k]
            ps = r["priority"].split("/")
            for k in ks:
                if not needs(k):
                    continue
                d = entry(k)
                for c in (r.get("case53_id") or "").split(";"):
                    if c and (len(ks) == 1 or c in {x for x in d["case53"]}):
                        d["case53"].add(c)
                d["label"] = d["label"] or k
                pk = ps[ks.index(k)] if len(ks) == len(ps) and len(ps) > 1 else r["priority"]
                d["queues"][r["queue_id"]] = pk
                if has_check and r.get("official_url_http_check"):
                    d["http"].append(f"{r['official_url_http_check']} (pending_acquisition_cycle3.csv {r['queue_id']})")
                if r["note"].strip():
                    d["notes"].append(f"{r['queue_id']}: {r['note'].strip()[:200]}")
                d["src"].append(cite(rel_, r["queue_id"], i))
    for spec, d in sorted(J.items()):
        c53 = sorted(c for c in d["case53"] if c)
        if len(c53) > 1:
            finding(f"CF-WSB-ID-{spec}", "CASE53_ID_DIFFERS_ACROSS_REGISTERS", f"{spec}: {';'.join(c53)}",
                    f"{PFX}{idr_rel}; {PFX}{pq3_rel}; {PFX}{pq_rel}")
        qids = sorted(d["queues"])
        rec_p = [norm_priority(v) for _, v in sorted(d["queues"].items())]
        recs = sorted(xw.get(spec, set()))
        cal = sorted(set(recs) & CAL)
        mirror = bool(d["mirror"])
        if "P0" in rec_p:
            pr, basis = "P0", "recorded WS-B priority P0"
        elif cal:
            pr, basis = "P0", "linked calibration-sample record(s): " + ";".join(cal)
        elif "P1" in rec_p:
            pr, basis = "P1", "recorded WS-B priority P1"
        elif mirror:
            pr, basis = "P1", "only a mirror copy is recorded"
        else:
            pr, basis = "P2", "default"
        uniq = lambda xs: list(dict.fromkeys(xs))
        out.append(dict(
            auth_id=f"AUTH-J-{spec}", item_type="JUDGMENT_OFFICIAL_COPY", case_key=spec, case53_id=";".join(c53) or "NOT_RECORDED",
            item=f"{d['label']} ({';'.join(c53) or 'no case53_id'})",
            current_state="NEEDS_OFFICIAL_COPY_AUTHENTICATION (dimensions in separate columns)",
            official_copy=" | ".join(uniq(d["official"])) or "NOT_RECORDED",
            mirror_copy=" | ".join(uniq(d["mirror"])) or "NONE_RECORDED",
            http_availability=" | ".join(uniq(d["http"])) or "NOT_CHECKED (no HTTP check recorded)",
            identity_status=" | ".join(uniq(d["identity"])) or "NOT_RECORDED",
            identification_uncertainty=" | ".join(uniq(d["uncert"])) or "NONE_RECORDED",
            evidence_held=" | ".join(uniq(d["ev"])) or "see official_copy / mirror_copy",
            authentication_requires=("Official court copy from the issuing court's own host, fetched only after owner approval; "
                                     "SHA-256 recorded at fetch; cover-page identity (parties, case number, date, bench) "
                                     "checked on the page image; any mirror-based pinpoints re-read from the official copy"
                                     + (". WS-B notes: " + " ; ".join(uniq(d["notes"])) if d["notes"] else "")),
            acquisition_request=";".join(qids) if qids else "NO_ACQUISITION_REQUEST",
            who_or_acquisition="Owner approval required for any fetch; acquisition per acquisition_request column",
            linked_records=";".join(recs), contradictions="", priority=pr, priority_basis=basis,
            source_file_row=" | ".join(uniq(d["src"]))))
    out.sort(key=lambda x: (PRANK[x["priority"]], x["item_type"] != "MML_EDITION", x["auth_id"]))
    return out


# ---------------------------------------------------------------- checks
def verify_c3_01():
    rel = "WS-A-STATUTORY/acquisition_requests_cycle3.csv"
    r = [x for x in rows(rel) if x["request_id"] == "ACQ-C3-01"][0]
    got = {"identifier": "in.gazette.e.1950.306" if "in.gazette.e.1950.306" in (r["source"] + r["url"]) else "MISSING",
           "bytes": r["expected_bytes"], "md5": r["expected_md5"]}
    s1 = [x for x in rows("WS-A-STATUTORY/s129_trace_cycle3.csv") if x["step"] == "1"][0]
    s129_ok = all(v in s1["source"] for v in (C3_01_EXPECTED["identifier"], C3_01_EXPECTED["bytes"], C3_01_EXPECTED["md5"]))
    mism = {k: (got[k], v) for k, v in C3_01_EXPECTED.items() if got[k] != v}
    return mism, s129_ok


def consistency_checks():
    # AA-C3-01 acquisition_request vs acq03 candidate identity
    acq03 = {r["acq03_id"]: r for r in rows("WS-A-STATUTORY/acq03_pinned_candidates.csv")}
    for r in CHAIN_ADD:
        a = r["acquisition_request"].strip()
        if a in acq03 and not any(w in acq03[a]["target_instruments"] for w in r["instrument"].split(",")[0:1]):
            finding(f"CF-CHAIN-{r['chain_id']}", "ACQUISITION_ID_POINTS_TO_DIFFERENT_INSTRUMENT",
                    f"{r['chain_id']} ({r['instrument']}) cites {a}, but {a} is '{acq03[a]['target_instruments']}'; "
                    f"matching candidate(s): " + ";".join(k for k, v in sorted(acq03.items())
                                                          if r["instrument"].split(",")[0] in v["target_instruments"]),
                    f"{PFX}{CHAIN_ADD_REL}; {PFX}WS-A-STATUTORY/acq03_pinned_candidates.csv")
    # Army Act as enacted: ACQ03-029 NO_LAWFUL_ONLINE_SOURCE_KNOWN vs ACQ-C3-01 located
    if "NO_LAWFUL" in acq03["ACQ03-029"]["status"]:
        finding("CF-ACQ03-029", "SOURCE_STATUS_SUPERSEDED_NOT_PROPAGATED",
                "ACQ03-029 (Army Act 1950 as enacted) is NO_LAWFUL_ONLINE_SOURCE_KNOWN, while ACQ-C3-01 records the archive.org "
                "item in.gazette.e.1950.306 with md5/bytes; the ACQ-03 approval request and acquisition matrix (acq3wt, PR #23 "
                "stack) still list 'Army Act 1950 as enacted' as having no lawful online source; AA-00 chain row cites only "
                "ACQ-03-B4-03",
                f"{PFX}WS-A-STATUTORY/acq03_pinned_candidates.csv; {PFX}WS-A-STATUTORY/acquisition_requests_cycle3.csv; "
                f"{PFX}{CHAIN_REL}")
    # S.R.O. 34/1963: excluded from ACQ-01 as misidentified, present in ACQ-02 as a declaration (recorded, consistent)
    b = json.loads((AW / "ACQ-01/batches.json").read_text(encoding="utf-8"))
    ex = [x["doc_id"] for bt in b["batches"] for x in bt.get("excluded_items", [])]
    if ex:
        finding("CF-ACQ01-EXCLUDED", "NOTE_EXCLUDED_ITEM",
                "ACQ-01 excluded item(s) " + ";".join(ex) + " not scheduled from ACQ-01; the same file is scheduled once as "
                "ACQ02-03 (r.188 declaration), as recorded in ACQ-02/supplement_inventory.csv",
                f"{PFX}ACQ-01/batches.json; {PFX}ACQ-02/supplement_inventory.csv")


def main(argv=None):
    global OUT
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=HERE, help="output directory (default: this folder)")
    OUT = ap.parse_args(argv).out
    mism, s129_ok = verify_c3_01()
    if mism or not s129_ok:
        finding("CF-C3-01", "ACQ_C3_01_VALUE_MISMATCH", f"mismatch={mism}; s129_trace_agrees={s129_ok}",
                f"{PFX}WS-A-STATUTORY/acquisition_requests_cycle3.csv; {PFX}WS-A-STATUTORY/s129_trace_cycle3.csv")
    acq = build_acquisitions()
    consistency_checks()
    aff = build_affected(acq)
    auth = build_auth(acq)
    n1 = write_csv("acquisition_schedule.csv",
                   ["acq_id", "aliases", "batch", "item", "host", "url_as_recorded", "authority_class", "pinned_integrity",
                    "source_located", "status_as_recorded", "approval_status", "blocking_dependents", "recorded_priority",
                    "priority", "priority_basis", "proposed_sequence", "exclusion", "notes", "source_file_row"],
                   sorted(acq, key=lambda x: (x["proposed_sequence"], x["acq_id"])))
    n2 = write_csv("affected_records_priority.csv",
                   ["rank", "record_id", "module", "kind", "in_calibration_sample", "reasons", "provisions",
                    "provisions_effective_date_unstated", "reserved_items", "cases", "n_provisions", "n_unstated",
                    "n_cases", "n_reserved", "unblocked_by_acq_ids", "score", "score_components", "breadth_tiebreak",
                    "source_file_rows"], aff)
    n3 = write_csv("source_authentication_queue.csv",
                   ["auth_id", "item_type", "case_key", "case53_id", "item", "current_state", "official_copy", "mirror_copy",
                    "http_availability", "identity_status", "identification_uncertainty", "evidence_held",
                    "authentication_requires", "acquisition_request", "who_or_acquisition", "linked_records",
                    "contradictions", "priority", "priority_basis", "source_file_row"],
                   auth)
    FINDINGS.append({"finding_id": "CF-C3-01-VERIFY", "kind": "VERIFICATION_RESULT",
                     "detail": ("ACQ-C3-01 identifier/bytes/md5 equal the brief values "
                                f"({C3_01_EXPECTED['identifier']}, {C3_01_EXPECTED['bytes']}, {C3_01_EXPECTED['md5']}) in "
                                "acquisition_requests_cycle3.csv; s129_trace_cycle3.csv step 1 agrees="
                                f"{s129_ok}" if not mism else f"MISMATCH {mism}"),
                     "source_files": f"{PFX}WS-A-STATUTORY/acquisition_requests_cycle3.csv; {PFX}WS-A-STATUTORY/s129_trace_cycle3.csv"})
    n4 = write_csv("consistency_findings.csv", ["finding_id", "kind", "detail", "source_files"],
                   sorted(FINDINGS, key=lambda x: x["finding_id"]))
    pc = {}
    for a in acq:
        pc[a["priority"]] = pc.get(a["priority"], 0) + 1
    summary = {"acquisition_schedule": n1, "acq_by_priority": dict(sorted(pc.items())),
               "acq_by_scope": {s: sum(1 for a in acq if a["scope"] == s) for s in SCOPE_ORDER},
               "acq_source_located_yes": sum(1 for a in acq if a["source_located"] == "YES"),
               "acq_pinned": sum(1 for a in acq if not a["pinned_integrity"].startswith("NOT_PINNED")),
               "affected_records": n2, "affected_in_calibration": sum(1 for x in aff if x["in_calibration_sample"] == "YES"),
               "affected_with_reserved": sum(1 for x in aff if x["n_reserved"]),
               "affected_with_cases": sum(1 for x in aff if x["n_cases"]),
               "authentication_queue": n3, "auth_mml": sum(1 for x in auth if x["item_type"] == "MML_EDITION"),
               "auth_judgments": sum(1 for x in auth if x["item_type"] != "MML_EDITION"),
               "auth_by_priority": {p: sum(1 for x in auth if x["priority"] == p) for p in ("P0", "P1", "P2")},
               "consistency_findings": n4, "acq_c3_01_mismatch": mism, "top10": [x["record_id"] for x in aff[:10]]}
    (OUT / "planning_summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
