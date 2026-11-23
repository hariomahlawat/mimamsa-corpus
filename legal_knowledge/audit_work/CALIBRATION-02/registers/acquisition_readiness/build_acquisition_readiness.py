#!/usr/bin/env python3
"""CALIBRATION-02 / Cycle 4 planning: acquisition-readiness matrix (DATABASE ONLY; planning, not execution).

Builds acquisition_readiness.csv from repository registers only. Stdlib only, no network, no download, no
config change. Rows are sorted and nothing carries a timestamp, so two runs give byte-identical output.

A located source is NOT an acquired source, and an acquired source is NOT an authenticated source. Every
candidate still needs owner approval of its download run; configuration branches exist for some batches,
but no repository file records approval of any download.

Inputs (read-only):
  COORDINATION/CYCLE3-PLANNING/acquisition_schedule.csv, source_authentication_queue.csv,
    affected_records_priority.csv (record -> acq_id links computed by CYCLE3-PLANNING)
  WS-A-STATUTORY/gaps_register.csv, acquisition_requests*.csv, acq03_pinned_candidates.csv,
    army_act_amendment_chain.csv
  WS-B-JUDGMENTS/pending_acquisition_cycle3.csv
  ARMY-RULES-CHAIN-01/army_rules_instrument_register.csv
  COORDINATION/CALIBRATION-01/calibration_package.csv; CALIBRATION-02/propositions.csv
  CALIBRATION-02/registers/held_sources_scratchpad.csv
  git (read-only): <branch>:config/sources.yaml for the four config branches; origin/raw-data data/meta.
Usage: python3 build_acquisition_readiness.py [--out DIR]
"""
from __future__ import annotations
import argparse, csv, io, json, re, subprocess, sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import unquote, urlparse

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
AW = ROOT / "legal_knowledge" / "audit_work"
PLAN = AW / "COORDINATION" / "CYCLE3-PLANNING"
WSA = AW / "WS-A-STATUTORY"
WSB = AW / "WS-B-JUDGMENTS"
ARC = AW / "ARMY-RULES-CHAIN-01"
CAL1 = AW / "COORDINATION" / "CALIBRATION-01" / "calibration_package.csv"
CAL2 = AW / "CALIBRATION-02"
HELD = CAL2 / "registers" / "held_sources_scratchpad.csv"
RAW_REF = "origin/raw-data"
# Config branches (read-only) and the PR that carries each, as recorded in NEXT_STAGE_PLAN.md,
# COORDINATION/PROGRESS_REGISTER.md and CYCLE3-PLANNING/README.md.
CONFIG_BRANCHES = [("claude/acq-01-config", "PR #8"), ("claude/desw-allowlist", "PR #9"),
                   ("claude/acq-02-config", "PR #17"), ("claude/acq-03-config", "PR #23")]
COMMERCIAL_RX = re.compile(r"(?:https?://)?(?:www\.)?(?:indiankanoon\.org|casemine\.com|scconline\.com|"
                           r"manupatrafast\.com|manupatra\.com)\S*", re.I)
WITHHELD = "[commercial legal database reference withheld; never a source]"
URL_RX = re.compile(r"https?://[^\s,;|)\"']+")
UUID_RX = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b")
SHA_RX = re.compile(r"(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])")
UNVERIFIED_AR_LEVELS = ("TEXT_LAYER_ONLY", "HINT_ONLY", "NOT_FOUND", "NOT_SEARCHED_AUTHORITATIVELY")
ARMY_ACT_ENACTED_ITEM = "in.gazette.e.1950.306"
LEGAL_QUESTIONS = ["r.23(3)", "C-08", "C-09", "r.15", "r.187(1)", "s.129", "AQ-05", "AQ-06", "OQ-A-13"]
LQ_RX = {
    "r.23(3)": re.compile(r"\br\.\s?23(?![0-9A-Za-z])|\bC-01\b|\bR23\b|R23-VERIFY"),
    "C-08": re.compile(r"\br\.\s?193(?![0-9A-Za-z])|\bC-08\b"),
    "C-09": re.compile(r"\br\.\s?194(?![0-9A-Za-z])|\bC-09\b"),
    "r.15": re.compile(r"\br\.\s?15(?![0-9A-Za-z])|\bOQ-A-10\b|\bGAP-15\b|\bXC-03\b"),
    "r.187(1)": re.compile(r"\br\.\s?187(?![0-9A-Za-z])|\bOQ-A-11\b|\bGAP-14\b|\bOQ-C-06\b"),
    "s.129": re.compile(r"\bs\.\s?129(?![0-9A-Za-z])|\bCC-17\b|\bFID-03\b"),
    "AQ-05": re.compile(r"\bAQ-05\b"),
    "AQ-06": re.compile(r"\bAQ-06\b|\bOQ-A-12\b|retrospect|deemed effect", re.I),
    "OQ-A-13": re.compile(r"\bOQ-A-13\b|\bAA-01\b|\bGAP-07\b|\b19/1955\b|\b19 of 1955\b"),
}
COMMENCEMENT_GAPS = {"GAP-06", "GAP-07", "GAP-12"}
# Corpus documents (origin/raw-data doc_id) that a candidate is an instrument copy of, by its recorded title.
# Used only to link candidates to KB records whose citations WS-D canonical_coverage.csv resolves to that doc.
DOC_TITLE_MAP = [(re.compile(r"Procedure\)? Rules,? 2008|Procedure-Rules-2008", re.I), "rules-aft-procedure-rules-2008"),
                 (re.compile(r"Procedure\)? Amendment Rules,? 2011|Amendment Procedure Rules 2011|S\.R\.O\. 5\(E\) 29-07-2011", re.I),
                  "rules-aft-amendment-procedure-rules-2011"),
                 (re.compile(r"Practice\)? Rules,? 2009|Practice Rules-2009", re.I), "rules-aft-practice-rules-2009")]
KB_RANGE_RX = re.compile(r"\b([A-Z0-9]+-[A-Z]+)(\d+)\.\.(?:\1)?(\d+)\b")
TIERS = [("T1", "Army Act 1950 as enacted"),
         ("T2", "unverified Army Rules amendment instruments and Gazette issues (OCR-only, hints, NOT_FOUND, "
                "post-2022 search, S.R.O. 484/1954 original)"),
         ("T3", "instruments bearing on commencement or retrospective dates (AQ-05, AQ-06, OQ-A-13)"),
         ("T4", "authenticity and edition of the 8 MML copies"),
         ("T5", "official judgments needed to replace mirror citations"),
         ("T6", "sources needed for the 46 calibration records"),
         ("T7", "other pending acquisition items"),
         ("EXCLUDED", "route excluded (bare-IP HTTP or aftjabalpur.in); never contact")]
COLUMNS = ["priority_rank", "recommended_priority", "acq_id", "aliases", "candidate_scope", "source_identity",
           "official_issuing_authority", "proposed_host", "proposed_url", "integrity_values", "integrity_pinned",
           "authority_class", "restrictions", "located_acquired_authenticated", "already_held", "held_sha256",
           "configured", "owner_approval_outstanding", "records_unblocked", "records_unblocked_count",
           "calibration_records_unblocked", "calibration_records_count", "legal_questions_unblocked",
           "unblock_count", "authentication_queue_ids", "cycle3_priority", "priority_rule_basis",
           "source_file_rows"]


def rows(p: Path):
    return list(csv.DictReader(io.StringIO(p.read_text(encoding="utf-8"), newline="")))


def git(*args) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *args], check=True, capture_output=True).stdout.decode("utf-8")


def clean(v: str) -> str:
    v = COMMERCIAL_RX.sub(WITHHELD, v or "")
    return re.sub(r"\s+", " ", v).strip()


def rel(p: Path) -> str:
    return str(p.relative_to(ROOT))


def host_of(u: str) -> str:
    try:
        return (urlparse(u).hostname or "").lower()
    except ValueError:
        return ""


def norm_url(u: str) -> str:
    return unquote(u.strip()).rstrip("/")


def archive_ident(u: str) -> str:
    m = re.search(r"archive\.org/(?:download|details)/([^/\s]+)", u or "")
    return m.group(1) if m else ""


# ---------------------------------------------------------------- config branches (read-only)
def load_configs():
    """branch -> {'urls': {url: (source, enabled)}, 'docs': {doc_id: (source, enabled)}, 'hosts': {host: [sources]},
    'commit': sha}. Line-based reading of the YAML (stdlib only); the structure is the crawler's own."""
    out = {}
    for br, _pr in CONFIG_BRANCHES:
        text = git("show", f"{br}:config/sources.yaml")
        commit = git("rev-parse", br).strip()
        src, enabled, in_sources = None, {}, False
        urls, docs, hosts, uuids = {}, {}, defaultdict(set), {}
        pending = []
        for line in text.splitlines():
            if re.match(r"^sources:\s*$", line):
                in_sources = True
                continue
            if re.match(r"^\S", line) and not line.startswith("#"):
                in_sources = line.startswith("sources:")
                src = None
            if not in_sources:
                continue
            m = re.match(r"^  ([a-z_0-9]+):\s*$", line)
            if m:
                src = m.group(1)
                continue
            if src is None:
                continue
            m = re.match(r"^\s+enabled:\s*(true|false)", line)
            if m:
                enabled[src] = m.group(1)
            for d in re.findall(r"doc_id:\s*([A-Za-z0-9_.-]+)", line):
                pending.append(("doc", d, src))
            for u_ in UUID_RX.findall(line):
                pending.append(("uuid", u_.lower(), src))
            for u in re.findall(r"url:\s*\"?(https?://[^\"\s,}]+)", line):
                pending.append(("url", u, src))
            m = re.match(r"^\s+allowed_hosts:\s*\[(.*)\]", line)
            if m:
                for h in re.findall(r"[\"']?([A-Za-z0-9*.-]+)[\"']?", m.group(1)):
                    hosts[h.lower()].add(src)
            m = re.match(r"^\s+base_url:\s*(https?://\S+)", line)
            if m:
                hosts[host_of(m.group(1))].add(src)
        for kind, v, s in pending:
            tgt = {"url": urls, "doc": docs, "uuid": uuids}[kind]
            tgt.setdefault(norm_url(v) if kind == "url" else v, (s, enabled.get(s, "unknown")))
        out[br] = {"urls": urls, "docs": docs, "uuids": uuids, "hosts": hosts, "commit": commit}
    return out


def configured_state(cfg, url: str, doc_id: str, host: str, uuid_ids=()) -> str:
    hits, host_hits = [], []
    nu = norm_url(url) if url else ""
    for br, pr in CONFIG_BRANCHES:
        c = cfg[br]
        hit = c["urls"].get(nu) if nu else None
        if hit is None and doc_id:
            hit = c["docs"].get(doc_id)
        if hit is None:
            for x in sorted(uuid_ids):
                if x in c["uuids"]:
                    hit = c["uuids"][x]
                    break
        if hit:
            hits.append(f"{pr} ({br}; source {hit[0]}, enabled: {hit[1]})")
        elif host and (host in c["hosts"] or any(h.startswith("*.") and host.endswith(h[1:]) for h in c["hosts"])):
            host_hits.append(br)
    if hits:
        return "YES (document listed): " + "; ".join(hits) + ". Configured is not approved; download needs owner approval"
    if host_hits:
        return f"NO (document not listed; host {host} appears in {', '.join(host_hits)})"
    return "NO"


# ---------------------------------------------------------------- held copies
def load_held():
    by_sha, by_path = {}, []
    for r in rows(HELD):
        by_sha[r["sha256"]] = r["scratchpad_relative_path"]
        by_path.append((r["scratchpad_relative_path"], r["sha256"]))
    return by_sha, by_path


def load_raw_meta():
    """source_url -> (doc_id, sha256) for non-judgment crawler documents on origin/raw-data (read-only)."""
    try:
        names = [n for n in git("ls-tree", "--name-only", RAW_REF, "data/meta/").split()
                 if n.endswith(".json") and not re.match(r"data/meta/(sc|hc)-", n)]
    except subprocess.CalledProcessError:
        return {}, ""
    commit = git("rev-parse", RAW_REF).strip()
    out = {}
    for n in sorted(names):
        try:
            m = json.loads(git("show", f"{RAW_REF}:{n}"))
        except (subprocess.CalledProcessError, ValueError):
            continue
        for u in [m.get("source_url")] + list(m.get("source_aliases") or []):
            if u:
                out[norm_url(u)] = (m.get("doc_id") or Path(n).stem, m.get("sha256") or "")
    return out, commit


# ---------------------------------------------------------------- helpers over registers
def provisions_from_text(text: str) -> set:
    """'AA s.2;AR r.15' tokens plus 'r.N' / 'rr.N,M' in Army Rules register text."""
    out = set()
    for kind, n in re.findall(r"\b(AA s|AR r)\.\s?(\d+[A-Z]*)", text):
        out.add(f"{kind}.{n}")
    return out


def ar_provisions(text: str) -> set:
    out = set()
    for m in re.finditer(r"\brr\.\s?([^;]+)", text):
        seg = m.group(1)
        for a_, b_ in re.findall(r"(?<![0-9A-Za-z.(])(\d{1,3})-(\d{1,3})(?![0-9])", seg):
            out |= {f"AR r.{n}" for n in range(int(a_), int(b_) + 1)} if int(a_) < int(b_) <= int(a_) + 20 else set()
        for n in re.findall(r"(?:^|[,\s])(\d{1,3}[A-Z]?)(?=[\s,(]|$)", seg):
            out.add(f"AR r.{n}")
    for n in re.findall(r"(?<![A-Za-z])r\.\s?(\d+[A-Z]?)", text):
        out.add(f"AR r.{n}")
    return out


def aa_sections(text: str) -> set:
    out = set()
    for m in re.finditer(r"\bss?\.\s?(\d+[A-Z]?(?:\s*(?:,|and)\s*\d+[A-Z]?)*)", text):
        for n in re.findall(r"\d+[A-Z]?", m.group(1)):
            out.add(f"AA s.{n}")
    return out


def split_ids(v: str) -> list:
    return [x.strip() for x in re.split(r"[;|,]", v or "") if x.strip()]


def scope_of(acq_id: str, batch: str) -> str:
    if acq_id.startswith("ACQ-01"):
        return "ACQ-01"
    if acq_id.startswith("ACQ02"):
        return "ACQ-02"
    if acq_id.startswith("ACQ03"):
        return "ACQ-03"
    if acq_id.startswith("ACQ-C3"):
        return "WS-A cycle 3"
    if acq_id.startswith("PQ-"):
        return "WS-B judgments"
    if acq_id.startswith("AUTH-MML"):
        return "MML authentication"
    return batch or "OTHER"


def issuing_authority(scope: str, item: str, court: str) -> str:
    """Identity of the issuing body as a planning label; read from the page image on acquisition."""
    it = item.lower()
    if scope == "WS-B judgments":
        return court or "court as recorded (NOT_RECORDED)"
    if scope == "MML authentication":
        return "UNVERIFIED (manual edition not authenticated; custodian route named in WS-C evidence rows)"
    if "listing" in it:
        return "Armed Forces Tribunal (as recorded)"
    if "entitlement rules" in it or "guide to medical officers" in it:
        return "Ministry of Defence, Department of Ex-Servicemen Welfare (as recorded in claude/desw-allowlist config)"
    if "regulations for the army" in it:
        return "Government of India, Ministry of Defence (as recorded; edition not verified)"
    if "bill" in it:
        return "Parliament (Bill; legislative history only, not enacted text)"
    if "ordinance" in it:
        return "President of India (Ordinance, Gazette of India; as recorded)"
    if "adaptation of laws" in it:
        return "Government of India (Order, Gazette of India; as recorded)"
    if re.search(r"\bact\b", it) and "rules" not in it and "notification" not in it:
        return "Parliament (Act published in the Gazette of India; as recorded)"
    return "Central Government (Gazette of India notification; issuing ministry to be read from the page image)"


def restrictions(scope: str, host: str, authority_class: str, exclusion: str) -> str:
    if exclusion:
        return "EXCLUDED: bare-IP HTTP or aftjabalpur.in route; never contact"
    base = "owner approval of the download run required; no login, CAPTCHA or anti-bot bypass; no commercial legal database"
    if scope == "MML authentication":
        return ("UNVERIFIED_MANUAL / USER_SUPPLIED / HASH_ONLY (as recorded): a manual is not authority and never "
                "overrides Acts, Rules, amendments or binding judgments; authentication needs the owner or a custodian; "
                "agents send no correspondence")
    if scope == "WS-B judgments":
        return ("official court copy only (issuing court's own host); mirrors and commercial references are never "
                "sources; cover-page identity and pinpoints to be re-read from the official copy; " + base)
    if host.endswith("archive.org"):
        return ("THIRD_PARTY_ARCHIVAL_FACSIMILE of an official Gazette: copy_fidelity HASH_ONLY until page-image "
                "checked; establishes historical wording only, not current operative text; HTTPS only; " + base)
    if "indiacode" in host:
        if "Gazette scan" in authority_class:
            return "government-hosted Gazette scan (as recorded); page-image check required; HTTPS only; " + base
        return ("GOVERNMENT_COMPILATION: comparison text, never Gazette authority (SOURCE_AUTHORITY_POLICY v1); "
                "HTTPS only; " + base)
    if "desw.gov.in" in host:
        return "government-issued document on the issuing department's host; HTTPS only (require_https); " + base
    if host.startswith("none") or host.startswith("not_recorded") or not host:
        return "no lawful online source recorded; acquisition route to be identified by the owner; " + base
    return base


# ---------------------------------------------------------------- build
def build():
    sched = rows(PLAN / "acquisition_schedule.csv")
    authq = rows(PLAN / "source_authentication_queue.csv")
    arp = rows(PLAN / "affected_records_priority.csv")
    gaps = {g["gap_id"]: g for g in rows(WSA / "gaps_register.csv")}
    arreg = {r["instr_id"]: r for r in rows(ARC / "army_rules_instrument_register.csv")}
    aachain = defaultdict(list)
    for r in rows(WSA / "army_act_amendment_chain.csv"):
        aachain[re.sub(r"-s\d+$", "", r["chain_id"])].append(r)
    pend = {r["queue_id"]: r for r in rows(WSB / "pending_acquisition_cycle3.csv")}
    cal = rows(CAL1)
    cal_ids = {c["record_id"] for c in cal}
    props = rows(CAL2 / "propositions.csv")
    doc_records = defaultdict(set)
    for r in rows(AW / "WS-D-QUALITY" / "canonical_coverage.csv"):
        for d in re.findall(r"=>([a-z0-9-]+)\[", r["items"]):
            doc_records[d].add(r["record_id"])
    prop_records = {p["record_id"] for p in props}
    wsa_reqs = []
    for f in sorted(WSA.glob("acquisition_requests*.csv")) + [WSA / "acq03_pinned_candidates.csv"]:
        for r in rows(f):
            rid = r.get("request_id") or r.get("acq03_id")
            u = r.get("url") or r.get("download_url") or ""
            wsa_reqs.append((rid, norm_url(u) if u.startswith("http") else "", f.name))
    cfg = load_configs()
    held_sha, held_paths = load_held()
    raw_meta, raw_commit = load_raw_meta()

    # T2 gap set: Army Rules gaps whose instrument/issue is not held or not verified.
    t2_gaps = set()
    for gid, g in gaps.items():
        armyrules = "AR-" in g["affected_ids"] or "Army Rules" in g["subject"] or "Pt II-Sec 4" in g["subject"] \
            or re.search(r"\br\.\s?\d", g["subject"] + g["affected_ids"])
        st = g["state"]
        if armyrules and (st.startswith(("NOT_FOUND", "LOCATED_UNVERIFIED", "NOT_SEARCHED")) or "not held" in st):
            t2_gaps.add(gid)

    # record -> acq links computed by CYCLE3-PLANNING (inverted)
    acq_records = defaultdict(set)
    rec_provs = {}
    for r in arp:
        for a in split_ids(r["unblocked_by_acq_ids"]):
            if a != "NONE_RECORDED":
                acq_records[a].add(r["record_id"])
        rec_provs[r["record_id"]] = provisions_from_text(r["provisions"])
    cal_provs, cal_cases = {}, {}
    for c in cal:
        p = {f"AA s.{n.strip()}" for n in c["army_act_sections"].split(";") if n.strip()}
        p |= {f"AR r.{n.strip()}" for n in c["army_rules"].split(";") if n.strip()}
        cal_provs[c["record_id"]] = p
        cal_cases[c["record_id"]] = c["linked_cases"]

    # fold rows naming the same file and cross-aliased to each other (ACQ03-029 = ACQ-C3-01)
    by_id = {s["acq_id"]: s for s in sched}
    folded = {}
    for s in sched:
        u = s["url_as_recorded"].strip()
        for a in split_ids(s["aliases"]):
            o = by_id.get(a)
            if o and o is not s and u.startswith("http") and o["url_as_recorded"].strip() == u \
                    and s["acq_id"] in split_ids(o["aliases"]):
                keep, drop = sorted([s["acq_id"], a])
                folded[drop] = keep

    auth_by_queue = defaultdict(list)
    for a in authq:
        for q in re.findall(r"PQ-C3-\d+", a["acquisition_request"]):
            auth_by_queue[q].append(a["auth_id"])

    cands = []
    for s in sched:
        if s["acq_id"] in folded:
            continue
        group = [s] + [by_id[d] for d, k in sorted(folded.items()) if k == s["acq_id"]]
        cands.append(("SCHED", s, group))
    for a in authq:
        if a["item_type"] == "MML_EDITION":
            cands.append(("MML", a, [a]))

    out = []
    for kind, s, group in cands:
        if kind == "SCHED":
            acq_id = s["acq_id"]
            aliases = set()
            for g in group:
                aliases |= set(split_ids(g["aliases"]))
                aliases.add(g["acq_id"])
            aliases.discard(acq_id)
            scope = scope_of(acq_id, s["batch"])
            pq = pend.get(acq_id, {})
            item = clean(s["item"])
            url = s["url_as_recorded"].strip()
            if scope == "WS-B judgments":
                offs = [u for u in URL_RX.findall(pq.get("official_target", "")) if host_of(u).endswith((".gov.in", ".nic.in"))]
                url = offs[0] if offs else ""
            if not url.startswith("http"):
                url = ""
            host = clean(s["host"])
            integrity = clean(s["pinned_integrity"])
            pinned = "YES" if re.search(r"(sha256|md5)=[0-9a-f]{32,64}", integrity) and "bytes=" in integrity else "NO"
            auth_class = clean(s["authority_class"])
            blob = " ".join(clean(g[k]) for g in group for k in ("item", "blocking_dependents", "priority_basis", "notes", "aliases"))
            exclusion = clean(s["exclusion"])
            located = s["source_located"]
            court = pq.get("court", "")
            srcrows = sorted({clean(g["source_file_row"]) for g in group} | {f"{rel(PLAN / 'acquisition_schedule.csv')}:{g['acq_id']}" for g in group})
            cyc = s["priority"]
        else:
            acq_id = s["auth_id"]
            aliases = set()
            scope = "MML authentication"
            item = clean(f"Manual of Military Law copy '{s['item']}': authentication of edition and publication (custodian route)")
            url, host = "", "NONE (custodian route; no online host recorded)"
            m = re.search(r"sha256=([0-9a-f]{64}); bytes=(\d+)", s["evidence_held"])
            integrity = f"held user-supplied copy: sha256={m.group(1)}; bytes={m.group(2)}" if m else "NOT_PINNED"
            pinned = "NO (byte hash of the held copy; no authenticated edition to pin against)"
            st = s["current_state"]
            auth_class = "; ".join(x.strip() for x in st.split(";") if re.match(r"\s*(document_authority|carrier_provenance|copy_fidelity)", x)) or clean(st)
            blob = clean(s["priority_basis"]) + " " + clean(s["contradictions"])
            exclusion = ""
            located = "n/a (held; authentication outstanding)"
            court = ""
            srcrows = [f"{rel(PLAN / 'source_authentication_queue.csv')}:{acq_id}", clean(s["source_file_row"])]
            cyc = s["priority"]

        # expansions
        exp = []
        ar_ids = sorted(set(re.findall(r"\bAR-\d{3}\b", blob)))
        aa_ids = sorted(set(re.findall(r"\bAA-(?:C3-)?\d{2}\b", blob)))
        gap_ids = sorted(set(re.findall(r"\bGAP-\d{2}\b", blob))) if scope != "ACQ-01" else []
        provs = provisions_from_text(blob)
        principal_ar = principal_aa = False
        aq05 = aq06 = r23_unknown = False
        for i in ar_ids:
            r = arreg.get(i)
            if not r:
                continue
            exp.append(r["provisions_affected"])
            if r["provisions_affected"].strip() == "all":
                principal_ar = True
            elif not r["provisions_affected"].strip().lower().startswith("unknown"):
                provs |= ar_provisions(r["provisions_affected"])
            if "AQ-05" in r["effective_date_status"] or r["effective_date_status"].startswith("NOT_DETERMINED"):
                aq05 = True
            if r["retrospective_deemed_effect_from"].strip() or "deemed" in (r["provisions_affected"] + r["commencement_as_printed"]).lower():
                aq06 = True
            if r["amends_r23"].strip().lower() in ("enacts", "yes", "unknown"):
                r23_unknown = True
        for i in aa_ids:
            for r in aachain.get(i, []):
                if r["sections_affected"].strip() == "all":
                    principal_aa = True
                else:
                    provs |= aa_sections(r["sections_affected"])
                if "AQ-05" in r["effective_date_status"] or r["effective_date_status"].startswith("NOT_DETERMINED"):
                    aq05 = True
        for gid in (gap_ids if not ar_ids else []):  # a gap lists several instruments: expand only without an AR id
            g = gaps.get(gid)
            if g:
                exp.append(g["affected_ids"] + " " + g["subject"])
        full = blob + " " + " ".join(exp)
        lq = {q for q, rx in LQ_RX.items() if rx.search(full)}
        if aq05 or COMMENCEMENT_GAPS & set(gap_ids):
            lq.add("AQ-05")
        if aq06:
            lq.add("AQ-06")
        if r23_unknown or principal_ar:
            lq.add("r.23(3)")
        if principal_ar:
            lq |= {"C-08", "C-09", "r.15", "r.187(1)"}
        if principal_aa:
            lq.add("s.129")
        for p in provs:
            for q, rx in (("r.23(3)", r"AR r\.23$"), ("C-08", r"AR r\.193$"), ("C-09", r"AR r\.194$"),
                          ("r.15", r"AR r\.15$"), ("r.187(1)", r"AR r\.187$"), ("s.129", r"AA s\.129$")):
                if re.match(rx, p):
                    lq.add(q)

        # records unblocked
        recs, basis = set(), []
        for a in sorted({acq_id} | aliases):
            if acq_records.get(a):
                recs |= acq_records[a]
                basis.append(f"CYCLE3 affected_records_priority via {a}")
        m = re.search(r"KB records:\s*([^|]+)", s.get("blocking_dependents", "") if kind == "SCHED" else "")
        if m and "NONE_LINKED" not in m.group(1):
            recs |= set(split_ids(m.group(1)))
        if kind == "MML":
            recs |= set(split_ids(s["linked_records"]))
        for rx, d in DOC_TITLE_MAP:
            if scope != "WS-B judgments" and rx.search(item):
                recs |= doc_records.get(d, set())
        for gid in (gap_ids if not ar_ids else []):
            for pre, a_, b_ in KB_RANGE_RX.findall(gaps.get(gid, {}).get("affected_ids", "")):
                w_ = len(a_)
                recs |= {f"{pre}{str(n).zfill(w_)}" for n in range(int(a_), int(b_) + 1)}

        def touches(rp: set) -> bool:
            if principal_ar and any(x.startswith("AR r.") for x in rp):
                return True
            if principal_aa and any(x.startswith("AA s.") for x in rp):
                return True
            return bool(provs & rp)
        for rid, rp in rec_provs.items():
            if touches(rp):
                recs.add(rid)
        for rid, rp in cal_provs.items():
            if touches(rp):
                recs.add(rid)
        if scope == "WS-B judgments" and pq:
            keys = {pq.get("spec_key", ""), pq.get("case53_id", "")} - {"", "n/a"}
            for rid, lc in cal_cases.items():
                if any(re.search(r"(?<![A-Za-z0-9_-])" + re.escape(k) + r"(?![A-Za-z0-9_-])", lc) for k in keys):
                    recs.add(rid)
        recs = {r for r in recs if re.match(r"^[A-Z0-9][A-Z0-9-]*$", r)}
        calrecs = sorted(recs & cal_ids)
        lqs = [q for q in LEGAL_QUESTIONS if q in lq]

        # held?
        held, held_sha_v = "NO", ""
        shas = SHA_RX.findall(integrity)
        ident = archive_ident(url)
        if kind == "MML":
            held = "YES (user-supplied copy held; authentication outstanding)"
            held_sha_v = shas[0] if shas else ""
        elif any(x in held_sha for x in shas):
            h = [x for x in shas if x in held_sha]
            held, held_sha_v = "YES (scratchpad copy; same SHA-256 as pinned)", ";".join(sorted(h))
        elif ident and any(f"/{ident}/" in "/" + p or p.endswith(f"{ident}.pdf") for p, _ in held_paths):
            hs = sorted({sh for p, sh in held_paths if f"/{ident}/" in "/" + p or p.endswith(f"{ident}.pdf")})
            held, held_sha_v = ("YES (scratchpad copy of the same archive.org item; pinned md5/bytes not re-verified "
                                "here)"), ";".join(hs)
        elif url and norm_url(url) in raw_meta:
            d, sh = raw_meta[norm_url(url)]
            held, held_sha_v = f"YES (crawler corpus {RAW_REF} data/meta/{d}.json; same source URL)", sh
        elif scope == "WS-B judgments":
            ms = SHA_RX.findall(pq.get("mirror_copy", ""))
            if ms and any(x in held_sha for x in ms):
                held, held_sha_v = "MIRROR_ONLY_HELD (not an official copy)", ";".join(sorted(x for x in ms if x in held_sha))
            elif ms:
                held = "NO (mirror copy recorded in WS-B, not an official copy)"
        if held.startswith("YES (crawler"):
            acquired = "CORPUS_COPY_ONLY"
        elif held.startswith("YES") and kind != "MML":
            acquired = "SCRATCHPAD_COPY_ONLY"
        else:
            acquired = "NO"
        if kind == "MML":
            lab = f"located=n/a; acquired=user-supplied copy; authenticated=NO"
        else:
            lab = f"located={located}; acquired={acquired} (no record copy from an approved run); authenticated=NO"
        if kind == "SCHED":
            for rid_, u_, f_ in wsa_reqs:
                if u_ and url and u_ == norm_url(url) and rid_ != acq_id:
                    aliases.add(rid_)

        doc_id = acq_id.split(":", 1)[1] if acq_id.startswith("ACQ-01:") else ""
        uu = set()
        if kind == "SCHED" and scope != "WS-B judgments":
            for g in group:
                uu |= {x.lower() for x in UUID_RX.findall(" ".join(v for k, v in g.items() if k != "source_file_row"))}
        conf = configured_state(cfg, url, doc_id, host_of(url) if url else "", uu)
        if exclusion:
            approval = "NOT_APPLICABLE (EXCLUDED route; never contact)"
        else:
            approval = ("YES (no repository file records owner approval of a download run; CYCLE3-PLANNING "
                        "approval_status NOT_APPROVED)")
            if kind == "MML":
                approval = "YES (owner or custodian authentication outstanding; no request recorded)"

        # tier
        is_t1 = ARMY_ACT_ENACTED_ITEM in url
        is_484 = "AR-000" in ar_ids and "484" in item
        is_t2 = is_484 or any(arreg.get(i, {}).get("evidence_level", "") in UNVERIFIED_AR_LEVELS for i in ar_ids) \
            or bool(t2_gaps & set(gap_ids))
        aa_undetermined = any(r["effective_date_status"].startswith("NOT_DETERMINED") for i in aa_ids for r in aachain.get(i, []))
        is_t3 = bool({"AQ-05", "AQ-06", "OQ-A-13"} & lq) or bool(COMMENCEMENT_GAPS & set(gap_ids)) or aa_undetermined
        mirror = scope == "WS-B judgments" and pq.get("mirror_copy", "none").strip().lower() not in ("", "none")
        if exclusion:
            tier, why = "EXCLUDED", "exclusion recorded in CYCLE3 schedule"
        elif is_t1:
            tier, why = "T1", f"proposed file is the Army Act 1950 as enacted ({ARMY_ACT_ENACTED_ITEM})"
        elif is_t2:
            w = []
            if is_484:
                w.append("S.R.O. 484/1954 original")
            w += [f"{i} {arreg[i]['evidence_level']}" for i in ar_ids if arreg.get(i, {}).get("evidence_level", "") in UNVERIFIED_AR_LEVELS]
            w += sorted(t2_gaps & set(gap_ids))
            tier, why = "T2", "; ".join(w)
        elif is_t3:
            w = sorted({"AQ-05", "AQ-06", "OQ-A-13"} & lq) + sorted(COMMENCEMENT_GAPS & set(gap_ids))
            if aa_undetermined:
                w.append("Army Act chain commencement NOT_DETERMINED")
            tier, why = "T3", "; ".join(w)
        elif kind == "MML":
            tier, why = "T4", "MML edition authentication (UNVERIFIED_MANUAL)"
        elif mirror:
            tier, why = "T5", "WS-B records a mirror copy only; official copy needed"
        elif calrecs:
            tier, why = "T6", f"{len(calrecs)} calibration record(s)"
        else:
            tier, why = "T7", "no higher tier applies"
        unblock = len(recs) + len(lqs)
        heldflag = 1 if (held.startswith("YES") and kind != "MML") else 0
        sortkey = ([t for t, _ in TIERS].index(tier), -len(lqs), heldflag, -unblock, -len(calrecs),
                   0 if located == "YES" else 1, 0 if pinned == "YES" else 1, acq_id)
        out.append((sortkey, {
            "acq_id": acq_id, "aliases": ";".join(sorted(aliases)), "candidate_scope": scope,
            "source_identity": item, "official_issuing_authority": issuing_authority(scope, item, court),
            "proposed_host": ("WITHHELD (listing pages link PDFs on a bare-IP HTTP host; excluded route)" if exclusion
                              else (host or "NOT_RECORDED")),
            "proposed_url": "WITHHELD (excluded route; never contact)" if exclusion else (url or "NOT_RECORDED"),
            "integrity_values": integrity or "NOT_PINNED", "integrity_pinned": pinned,
            "authority_class": auth_class or "NOT_RECORDED",
            "restrictions": restrictions(scope, (host or "").lower(), auth_class, exclusion),
            "located_acquired_authenticated": lab, "already_held": held, "held_sha256": held_sha_v,
            "configured": conf, "owner_approval_outstanding": approval,
            "records_unblocked": ";".join(sorted(recs)), "records_unblocked_count": str(len(recs)),
            "calibration_records_unblocked": ";".join(calrecs), "calibration_records_count": str(len(calrecs)),
            "legal_questions_unblocked": ";".join(lqs), "unblock_count": str(unblock),
            "authentication_queue_ids": ";".join(sorted(auth_by_queue.get(acq_id, []))) if kind == "SCHED" else acq_id,
            "cycle3_priority": cyc, "priority_rule_basis": f"{tier}: {why}",
            "source_file_rows": " | ".join(x for x in srcrows if x),
            "recommended_priority": tier,
            "_batches": [(g["acq_id"], g["batch"]) for g in group] if kind == "SCHED" else [],
        }))
    out.sort(key=lambda x: x[0])
    result, mism = [], []
    for n, (_, r) in enumerate(out, 1):
        r["priority_rank"] = f"{n:03d}"
        for gid_, b in r["_batches"]:
            if re.search(r"configured in PR|\(PR #\d+, unmerged\)", b) and not re.search(r"not pinned|not configured", b) \
                    and r["configured"].startswith("NO"):
                mism.append(f"{gid_}: schedule batch '{clean(b)}' but the document is not listed in any config branch")
            if re.search(r"not configured|not pinned", b) and r["configured"].startswith("YES"):
                mism.append(f"{gid_}: schedule batch '{clean(b)}' but a config branch lists the document")
        result.append({k: clean(r[k]) for k in COLUMNS})
    covered = {x for r in result for x in split_ids(r["calibration_records_unblocked"])}
    meta = {"config_commits": {br: cfg[br]["commit"] for br, _ in CONFIG_BRANCHES}, "raw_commit": raw_commit,
            "folded": folded, "t2_gaps": sorted(t2_gaps), "n_prop_records": len(prop_records & cal_ids),
            "config_mismatch": sorted(mism), "cal_uncovered": sorted(cal_ids - covered), "n_cal": len(cal_ids)}
    return result, meta


def write(out_dir: Path, result, meta):
    out_dir.mkdir(parents=True, exist_ok=True)
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=COLUMNS, lineterminator="\n")
    w.writeheader()
    w.writerows(result)
    (out_dir / "acquisition_readiness.csv").write_text(buf.getvalue(), encoding="utf-8")
    cnt = defaultdict(int)
    for r in result:
        cnt[r["recommended_priority"]] += 1
    summ = {
        "rows": len(result),
        "by_tier": {t: cnt.get(t, 0) for t, _ in TIERS},
        "by_scope": dict(sorted(_count(result, "candidate_scope").items())),
        "integrity_pinned_yes": sum(r["integrity_pinned"] == "YES" for r in result),
        "already_held_yes": sum(r["already_held"].startswith("YES") for r in result),
        "configured_yes": sum(r["configured"].startswith("YES") for r in result),
        "owner_approval_outstanding_yes": sum(r["owner_approval_outstanding"].startswith("YES") for r in result),
        "with_calibration_records": sum(r["calibration_records_count"] != "0" for r in result),
        "calibration_records_covered": len({x for r in result for x in split_ids(r["calibration_records_unblocked"])}),
        "legal_question_counts": {q: sum(q in r["legal_questions_unblocked"].split(";") for r in result) for q in LEGAL_QUESTIONS},
        "folded_duplicates": meta["folded"],
        "t2_gap_ids": meta["t2_gaps"],
        "config_branch_commits": meta["config_commits"],
        "raw_data_commit": meta["raw_commit"],
        "config_label_mismatches": meta["config_mismatch"],
        "calibration_records_without_candidate": meta["cal_uncovered"],
        "calibration_records_total": meta["n_cal"],
    }
    (out_dir / "acquisition_readiness_summary.json").write_text(json.dumps(summ, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "README.md").write_text(readme(result, summ), encoding="utf-8")


def readme(result, summ) -> str:
    L = []
    a = L.append
    a("# Acquisition-readiness matrix (Cycle 4 planning; DATABASE ONLY)")
    a("")
    a("**Planning only. Nothing was downloaded, fetched, configured or approved.** No host was contacted and no config "
      "was activated. No legal determination is made here. A located source is not an acquired source, and an acquired "
      "source is not an authenticated source. Configuration branches exist for some batches, but no repository file "
      "records owner approval of any download run, so `owner_approval_outstanding` is YES on every row except the "
      "excluded route. The AFT bare-IP HTTP route and aftjabalpur.in are never proposed. Commercial legal databases are "
      "never a source.")
    a("")
    a("Reserved states are quoted, not changed: r.23(3) CONFLICTING (C-01); r.193 C-08 OPEN; r.194 C-09 PROPOSAL; "
      "r.15, r.187(1) and s.129 OPEN; AQ-05, AQ-06 and OQ-A-13 reserved.")
    a("")
    a("## Files")
    a("| File | Content |")
    a("| --- | --- |")
    a(f"| `acquisition_readiness.csv` | {summ['rows']} candidates, one row each, in recommended order |")
    a("| `acquisition_readiness_summary.json` | Counts, folded duplicates, config-label mismatches, branch commits |")
    a("| `build_acquisition_readiness.py` | Generator (stdlib; deterministic; `--out DIR` writes elsewhere) |")
    a("| `README.md` | This file (generated) |")
    a("")
    a("## Method")
    a("- **Candidates.** Every row of `COORDINATION/CYCLE3-PLANNING/acquisition_schedule.csv` (140), which already "
      "consolidates ACQ-01 `batches.json`, ACQ-02, WS-A `acq03_pinned_candidates.csv` and `acquisition_requests*.csv`, "
      "WS-A cycle-3 requests and the WS-B queue `pending_acquisition_cycle3.csv`; plus the 8 MML editions in "
      "`source_authentication_queue.csv` (authentication, not download). The 55 judgment rows of that queue map onto "
      "the WS-B queue rows (`authentication_queue_ids`). Two schedule rows that name the same file and alias each other "
      "are folded into one (" + ", ".join(f"{k} into {v}" for k, v in sorted(summ["folded_duplicates"].items())) + ").")
    a("- **Coverage checks.** Every Army Rules register row with evidence TEXT_LAYER_ONLY, HINT_ONLY, NOT_FOUND or "
      "NOT_SEARCHED_AUTHORITATIVELY, and every WS-A gap with an acquisition request, resolves to a candidate. GAP-10 "
      "(Hindi text of a held instrument) and GAP-12 (legal advice on silent instruments) need no acquisition.")
    a("- **Integrity values** are copied as recorded (`sha256`/`md5`/`bytes`), else NOT_PINNED. For MML rows they are the "
      "hash of the held user-supplied copy, which proves byte identity only.")
    a("- **authority_class** copies the SOURCE_AUTHORITY_POLICY v1 values as recorded in the schedule or queue. "
      "**restrictions** are derived from the carrier: archival facsimile (HASH_ONLY until page-image check; historical "
      "wording only), government compilation (comparison text, never Gazette authority), official court copy only, "
      "UNVERIFIED_MANUAL, HTTPS only, owner approval, no bypass.")
    a("- **already_held** checks, in order: the pinned SHA-256 in `registers/held_sources_scratchpad.csv`; the same "
      "archive.org item in a held path (pinned md5/bytes not re-verified); the same source URL in an `origin/raw-data` "
      "`data/meta` record (crawler corpus copy); for judgments, a held mirror (never official). A held scratchpad or "
      "corpus copy is not a record copy from an approved run.")
    a("- **configured** reads `git show <branch>:config/sources.yaml` for claude/acq-01-config (PR #8), "
      "claude/desw-allowlist (PR #9), claude/acq-02-config (PR #17) and claude/acq-03-config (PR #23), and matches the "
      "candidate's URL, ACQ-01 doc_id or India Code item UUID. Every listed source is `enabled: false`. "
      "Configured is never approved.")
    a("- **records_unblocked** is the union of: the CYCLE3-PLANNING `affected_records_priority.csv` record-to-acq links "
      "(by ID or alias); WS-B `KB records` lists; MML `linked_records`; KB records whose cited Army Act sections or "
      "Army Rules intersect the candidate's provisions (schedule `provisions:` list, Army Rules register "
      "`provisions_affected`, Army Act chain `sections_affected`; a principal instrument covers every section or rule "
      "of its instrument); WS-D `canonical_coverage.csv` citations of the corpus document the candidate is a copy of "
      "(AFT rules); KB ID ranges in a gap's `affected_ids`; and calibration `linked_cases` naming the judgment. "
      "**calibration_records_unblocked** is the subset in `CALIBRATION-01/calibration_package.csv` (46).")
    a("- **legal_questions_unblocked** marks evidence that bears on a reserved question; it never answers it. Tokens in "
      "the candidate's own row and in the register rows it names: r.23(3) (r.23, C-01, R23; or an Army Rules register "
      "row with `amends_r23` enacts/YES/UNKNOWN); C-08 (r.193); C-09 (r.194); r.15 (r.15, OQ-A-10, GAP-15, XC-03); "
      "r.187(1) (r.187, OQ-A-11, GAP-14, OQ-C-06); s.129 (s.129, CC-17, FID-03); AQ-05 (named register row with "
      "commencement NOT_STATED_PENDING_ADVICE (AQ-05) or NOT_DETERMINED, or GAP-06/07/12); AQ-06 (a register row with "
      "`retrospective_deemed_effect_from` or deemed effect; OQ-A-12); OQ-A-13 (AA-01, GAP-07, Act 19/1955). "
      "A gap's text is expanded only when the row names no Army Rules register ID, because one gap lists several "
      "instruments. `unblock_count` = records_unblocked + legal questions.")
    a("")
    a("## Priority rule (mechanical)")
    a("`recommended_priority` is the first tier that applies:")
    for t, d in TIERS:
        a(f"- **{t}**: {d}.")
    a("")
    a("Tier tests: T1 = the proposed file is `in.gazette.e.1950.306`. T2 = the row names an Army Rules register ID "
      "whose evidence is TEXT_LAYER_ONLY, HINT_ONLY, NOT_FOUND or NOT_SEARCHED_AUTHORITATIVELY, or is the S.R.O. 484/1954 "
      "original (AR-000), or names an Army Rules gap that is NOT_FOUND, LOCATED_UNVERIFIED, NOT_SEARCHED or not held "
      f"({', '.join(summ['t2_gap_ids'])}). T3 = AQ-05, AQ-06 or OQ-A-13 in `legal_questions_unblocked`, a commencement "
      "gap (GAP-06/07/12), or an Army Act chain row with commencement NOT_DETERMINED. T4 = MML edition. T5 = WS-B row "
      "with a mirror copy recorded. T6 = at least one calibration record. T7 = the rest. EXCLUDED = exclusion recorded.")
    a("")
    a("Within a tier, `priority_rank` sorts by: more reserved questions; not yet held before held; higher "
      "`unblock_count`; more calibration records; source located; integrity pinned; `acq_id`.")
    a("")
    a("## Counts")
    a(f"- Rows: {summ['rows']}. By scope: " + "; ".join(f"{k} {v}" for k, v in summ["by_scope"].items()) + ".")
    a("- By tier: " + "; ".join(f"{k} {v}" for k, v in summ["by_tier"].items()) + ".")
    a(f"- Integrity pinned (hash + bytes): {summ['integrity_pinned_yes']}. Already held in some form: "
      f"{summ['already_held_yes']} (scratchpad, corpus or user-supplied MML; none is a record copy from an approved run). "
      f"Document listed in a config branch: {summ['configured_yes']}. Owner approval outstanding: "
      f"{summ['owner_approval_outstanding_yes']} (the remaining row is the excluded route).")
    a(f"- Calibration: {summ['calibration_records_covered']} of {summ['calibration_records_total']} records are linked "
      f"to at least one candidate; {summ['with_calibration_records']} candidates link a calibration record. Without a "
      "candidate: " + (", ".join(summ["calibration_records_without_candidate"]) or "none") + ".")
    a("- Reserved questions (candidates bearing on each): " + "; ".join(f"{k} {v}" for k, v in summ["legal_question_counts"].items()) + ".")
    if summ["config_label_mismatches"]:
        a("- **Config-label mismatches** (schedule batch label vs. the config branches as read):")
        for m_ in summ["config_label_mismatches"]:
            a(f"  - {m_}")
    a("")
    a("## Top 20")
    a("| Rank | Tier | acq_id | Source | Held | Configured | Records (calib.) | Reserved questions |")
    a("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for r in result[:20]:
        src = r["source_identity"][:70].replace("|", "/")
        a(f"| {r['priority_rank']} | {r['recommended_priority']} | {r['acq_id']} | {src} | "
          f"{r['already_held'].split(' ')[0]} | {r['configured'].split(' ')[0]} | {r['records_unblocked_count']} "
          f"({r['calibration_records_count']}) | {r['legal_questions_unblocked'] or '-'} |")
    a("")
    a("## Rebuild")
    a("```")
    a("python3 legal_knowledge/audit_work/CALIBRATION-02/registers/acquisition_readiness/build_acquisition_readiness.py")
    a("```")
    a("Inputs are read from the working tree and from the git refs named above; two runs give byte-identical files "
      "while those refs are unchanged.")
    return "\n".join(L) + "\n"


def _count(result, k):
    c = defaultdict(int)
    for r in result:
        c[r[k]] += 1
    return c


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=HERE)
    a = ap.parse_args(argv)
    result, meta = build()
    write(a.out, result, meta)
    print(f"rows={len(result)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
