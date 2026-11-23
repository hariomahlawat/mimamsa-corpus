#!/usr/bin/env python3
"""Cycle 8 / WS-E deterministic cross-reference checks (offline, stdlib only, read-only).

Usage:
    python3 xref_checks.py <repo_root> <held_root> <out_csv>

<repo_root>  repository snapshot (contains legal_knowledge/)
<held_root>  directory that the held_binaries_manifest held_path values are relative to
<out_csv>    candidate observations (one row per observation); never edits inputs.

Each check emits rows: check_id, object_id, field, observed, expected_or_rule, evidence.
The rows are CANDIDATES. They are triaged by hand (NEW/EXISTING, priority) in
cross_reference_findings.csv; a candidate is not a finding until triaged.
"""
import csv
import hashlib
import json
import os
import re
import sys
from collections import defaultdict, Counter

COMMERCIAL = ("indiankanoon.org", "casemine.com", "scconline.com", "manupatra.com",
              "voxjuris.org", "courtsandcases.com", "order.law", "livelaw.in")


def rcsv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def rjsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def main(repo, held_root, out):
    lk = os.path.join(repo, "legal_knowledge")
    aw = os.path.join(lk, "audit_work")
    kb = rjsonl(os.path.join(lk, "curated_originals/knowledge_base/v0.9/records_658.jsonl"))
    cases = rjsonl(os.path.join(lk, "curated_originals/case_law/v0.9/cases_53.jsonl"))
    kbid = {r["id"]: r for r in kb}
    cid = {c["id"]: c for c in cases}
    c5 = os.path.join(aw, "SOURCE-LIBRARY-C5/registers")
    master = rcsv(os.path.join(c5, "source_master_register.csv"))
    copies = rcsv(os.path.join(c5, "source_copy_register.csv"))
    xwalk = rcsv(os.path.join(c5, "corpus_crosswalk.csv"))
    amend = rcsv(os.path.join(c5, "amendment_register.csv"))
    chain = rcsv(os.path.join(c5, "provision_amendment_chain.csv"))
    prov = rcsv(os.path.join(c5, "provision_register.csv"))
    conflicts = rcsv(os.path.join(c5, "source_conflict_register.csv"))
    held = rcsv(os.path.join(aw, "SOURCE-LIBRARY-C5/baseline/held_binaries_manifest.csv"))
    casemap = rcsv(os.path.join(aw, "SOURCE-LIBRARY-C5/inputs/case_source_map.csv"))
    ident = rcsv(os.path.join(aw, "WS-B-JUDGMENTS/identity_resolution.csv"))
    hold3 = rcsv(os.path.join(aw, "WS-B-JUDGMENTS/holdings_register_cycle3.csv"))
    st3 = rcsv(os.path.join(aw, "WS-B-JUDGMENTS/subsequent_treatment_cycle3.csv"))
    vedges = rcsv(os.path.join(aw, "WS-D-QUALITY/relation_graph_versioned_edges.csv"))
    codes = rcsv(os.path.join(aw, "WS-D-QUALITY/registers/source_code_resolution_v4_proposed.csv"))
    xw53 = rcsv(os.path.join(aw, "WS-B-JUDGMENTS/crosswalk_cases53_kb658.csv"))

    rows = []

    def emit(check, obj, field, observed, rule, evidence):
        rows.append(dict(check_id=check, object_id=obj, field=field, observed=str(observed)[:600],
                         expected_or_rule=rule, evidence=evidence))

    held_sha = {h["rehashed_sha256"] for h in held}
    held_bad = [h for h in held if h["hash_check"] != "MATCH"]
    for h in held_bad:
        emit("X00", h["held_path"], "hash_check", h["hash_check"], "MATCH", "held_binaries_manifest.csv")
    master_ids = {m["source_id"] for m in master}
    copies_by_source = defaultdict(list)
    for c in copies:
        copies_by_source[c["source_id"]].append(c)

    # ---------------- X01 case record archive flags vs held official copies -------------
    case2src = {m["key"]: m["source_id"] for m in casemap}
    for k, sid in case2src.items():
        c = cid.get(k)
        if c is None:
            emit("X01", k, "case_source_map.key", k, "key resolves to cases_53 id", "case_source_map.csv")
            continue
        cps = copies_by_source.get(sid, [])
        if cps and not c.get("original_pdf_archived") and not c.get("original_pdf_sha256"):
            emit("X01", k, "original_pdf_archived/original_pdf_sha256",
                 f"archived={c.get('original_pdf_archived')} sha256='{c.get('original_pdf_sha256')}'",
                 "held official copy exists -> case record should reference it",
                 f"source_copy_register {sid}: " + ";".join(x['sha256'] for x in cps))
    # WS-B identity: held copy sha but case record empty
    for r in ident:
        k = r.get("case53_id")
        if k and r.get("held_copy_sha256") and k in cid and not cid[k].get("original_pdf_sha256"):
            if k not in case2src:
                emit("X01b", k, "original_pdf_sha256", "empty",
                     "WS-B identity_resolution records a held copy not mapped in C5 case_source_map",
                     f"WS-B identity_resolution.csv spec_key={r['spec_key']} held_copy_sha256={r['held_copy_sha256']}"
                     f" in_held_manifest={r['held_copy_sha256'] in held_sha}")

    # ---------------- X02 commercial-database URLs ---------------------------------------
    for c in cases:
        for f in ("primary_source_url", "accessible_source_url"):
            u = c.get(f) or ""
            if any(d in u for d in COMMERCIAL):
                emit("X02", c["id"], f, u, "official source only (CLAUDE.md scope); commercial mirror = discovery lead",
                     f"cases_53.jsonl {c['id']}.{f}; source_status={c.get('source_status')}")
    for r in kb:
        u = r.get("url") or ""
        if any(d in u for d in COMMERCIAL):
            emit("X02", r["id"], "url", u, "official source only", "records_658.jsonl")

    # ---------------- X03 one URL attached to several distinct cases ---------------------
    byurl = defaultdict(list)
    for c in cases:
        for f in ("primary_source_url", "accessible_source_url"):
            u = c.get(f) or ""
            if u and "search/?" not in u:
                byurl[u].append((c["id"], f))
    for u, lst in byurl.items():
        ids = sorted({i for i, _ in lst})
        if len(ids) > 1:
            emit("X03", ";".join(ids), "primary/accessible_source_url", u,
                 "a source URL should identify the judgment of the record it is attached to",
                 "cases_53.jsonl")

    # ---------------- X04 id year / decision date / missing identity ---------------------
    for c in cases:
        m = re.match(r"DCLR-SC-(\d{4})-", c["id"])
        d = c.get("decision_date") or ""
        if m and d and m.group(1) != d[:4]:
            emit("X04", c["id"], "id vs decision_date", f"id year {m.group(1)} / decision_date {d}",
                 "id year normally = decision year", "cases_53.jsonl")
        if not d:
            emit("X04b", c["id"], "decision_date", "empty",
                 "decision date needed for chronology/treatment ordering", f"source_status={c.get('source_status')}")
    # related_cases referential integrity / symmetry
    for c in cases:
        for rc in c.get("related_cases") or []:
            if rc not in cid:
                emit("X05", c["id"], "related_cases", rc, "related id must exist", "cases_53.jsonl")
            elif c["id"] not in (cid[rc].get("related_cases") or []):
                emit("X05b", c["id"], "related_cases", f"{c['id']}->{rc} not reciprocated",
                     "relation should be symmetric or typed", "cases_53.jsonl")

    # ---------------- X06 KB references to provisions omitted in 1992 ---------------------
    omitted = {"75": "Act 37/1992 s.2", "76": "Act 37/1992 s.2", "127": "Act 37/1992 s.11",
               "195": "Act 37/1992 s.19", "196": "Act 37/1992 s.19"}
    pat = re.compile(r"(?:AA|Army Act)[^;\]\n]{0,40}?(?:§§?|ss?\.?|[Ss]ections?)\s*([0-9][0-9A-Z,–\- ]*)")
    for r in kb:
        txt = r["body"] + " " + r["references"]
        for m in pat.finditer(txt):
            nums = set()
            for part in re.split(r"[ ,]+", m.group(1)):
                rg = re.match(r"(\d+)[–-](\d+)$", part)
                if rg and int(rg.group(2)) - int(rg.group(1)) < 60:
                    nums.update(str(n) for n in range(int(rg.group(1)), int(rg.group(2)) + 1))
                elif re.match(r"\d+$", part):
                    nums.add(part)
            for n in nums & set(omitted):
                ctx = txt[max(0, m.start() - 80): m.end() + 120]
                if not re.search(r"omit", ctx, re.I):
                    emit("X06", r["id"], "body/references", ctx.replace("\n", " "),
                         f"AA s.{n} omitted ({omitted[n]}); range citation includes it without an omission marker",
                         "records_658.jsonl; Army Act consolidation e47a4265 p.7 ('127. [Omitted.]')")

    # ---------------- X07 legacy criminal statutes without transition marker -------------
    legacy = re.compile(r"\bIPC\b|Indian Penal Code|CrPC|Cr\.P\.C|Code of Criminal Procedure|\bIEA\b|Evidence Act|s\s?65B")
    marker = re.compile(r"BNS|BNSS|BSA|Sakshya|Nyaya|Nagarik|1 July 2024|2024|repeal|former|historic|legacy|pre-",
                        re.I)
    for r in kb:
        txt = r["title"] + " " + r["body"] + " " + r["references"]
        if legacy.search(txt) and not marker.search(txt):
            emit("X07", r["id"], "body", legacy.search(txt).group(0),
                 "legacy code reference without a 2024 transition marker", "records_658.jsonl")

    # ---------------- X08 KB citation codes unresolved -----------------------------------
    codeinfo = {c["code"]: c for c in codes}
    for c in codes:
        if c["resolution_class"] in ("UNRESOLVED", "UNKNOWN") or c["corpus_target_or_gap"].startswith("UNRESOLVED"):
            emit("X08", c["code"], "resolution_class", f"{c['resolution_class']} / {c['corpus_target_or_gap']}",
                 "citation code should resolve to an identified source",
                 f"WS-D source_code_resolution_v4_proposed.csv records={c['records_using'][:200]}")

    # ---------------- X09 crosswalk referential integrity --------------------------------
    provids = set()
    for p in prov:
        provids.add(p["provision_id"])
    for i, x in enumerate(xwalk, start=2):
        if x["knowledge_base_record_id"] and x["knowledge_base_record_id"] not in kbid:
            emit("X09", f"corpus_crosswalk.csv#L{i}", "knowledge_base_record_id", x["knowledge_base_record_id"],
                 "must exist in records_658", "corpus_crosswalk.csv")
        if x["case_id"] and x["case_id"] not in cid:
            emit("X09", f"corpus_crosswalk.csv#L{i}", "case_id", x["case_id"], "must exist in cases_53",
                 "corpus_crosswalk.csv")
        if x["source_id"] not in master_ids and x["source_id"] not in ("UNMAPPED", "NONE"):
            emit("X09", f"corpus_crosswalk.csv#L{i}", "source_id", x["source_id"], "must exist in master",
                 "corpus_crosswalk.csv")
    cnt_kb_in_xw = {x["knowledge_base_record_id"] for x in xwalk if x["knowledge_base_record_id"]}
    for r in kb:
        if r["id"] not in cnt_kb_in_xw:
            emit("X09b", r["id"], "crosswalk", "no corpus_crosswalk row",
                 "every KB record should have >=1 crosswalk row (CITES or explicit NO_CITATION)",
                 "corpus_crosswalk.csv")
    cnt_case_in_xw = {x["case_id"] for x in xwalk if x["case_id"]}
    for c in cases:
        if c["id"] not in cnt_case_in_xw:
            emit("X09c", c["id"], "crosswalk", "no corpus_crosswalk row", "every case record should be mapped",
                 "corpus_crosswalk.csv")

    # ---------------- X10 copies vs held manifest / master -------------------------------
    for c in copies:
        if c["source_id"] not in master_ids:
            emit("X10", c["copy_id"], "source_id", c["source_id"], "must exist in master", "source_copy_register.csv")
        if c["sha256"] and c["sha256"] not in held_sha:
            emit("X10b", c["copy_id"], "sha256", c["sha256"], "copy sha256 should appear in held_binaries_manifest",
                 "source_copy_register.csv vs held_binaries_manifest.csv")
        if c.get("held_paths") and held_root:
            for p in c["held_paths"].split(";"):
                fp = os.path.join(held_root, p)
                if not os.path.exists(fp):
                    emit("X10c", c["copy_id"], "held_paths", p, "held path should exist", "filesystem")
    for m in master:
        ms = [s for s in (m.get("sha256") or "").replace(",", ";").split(";") if s.strip()]
        cs = {c["sha256"] for c in copies_by_source.get(m["source_id"], [])}
        for s in ms:
            s = s.strip()
            if re.fullmatch(r"[0-9a-f]{64}", s) and cs and s not in cs:
                emit("X10d", m["source_id"], "sha256", s, "master sha256 should be one of its copies",
                     "source_master_register.csv vs source_copy_register.csv")

    # ---------------- X11 amendment register chronology ----------------------------------
    def d(s):
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s or "")
        return m.group(0) if m else None
    amend_ids = set()
    for a in amend:
        amend_ids.add(a["origin_id"])
        nd, pd, ed = d(a["notification_date"]), d(a["publication_date"]), d(a["effective_date"])
        if nd and pd and pd < nd:
            emit("X11", a["amendment_id"], "publication_date<notification_date", f"{nd} / {pd}",
                 "publication on/after notification", "amendment_register.csv")
        if a["sha256"] and a["sha256"] not in held_sha and re.fullmatch(r"[0-9a-f]{64}", a["sha256"]):
            emit("X11b", a["amendment_id"], "sha256", a["sha256"], "register sha should be held",
                 "amendment_register.csv")
        if a["verification_status"] in ("IMAGE_CHECKED",) and not a["sha256"]:
            emit("X11c", a["amendment_id"], "sha256", "empty", "IMAGE_CHECKED evidence should carry a sha256",
                 "amendment_register.csv")
    for ch in chain:
        ir = ch["instrument_ref"]
        if ir and re.match(r"AR-\d{3}$", ir) and ir not in amend_ids:
            emit("X12", ch["chain_row_id"], "instrument_ref", ir, "instrument must be in amendment register",
                 "provision_amendment_chain.csv")

    # ---------------- X13 versioned edges -------------------------------------------------
    for i, e in enumerate(vedges, start=2):
        vf, vt = d(e["valid_from"]), d(e["valid_to"])
        if vf and vt and vt < vf:
            emit("X13", f"{e['record_id']}#{e['version_id']}", "valid_to<valid_from", f"{vf}..{vt}",
                 "valid_to >= valid_from", f"relation_graph_versioned_edges.csv#L{i}")
        if e["record_id"] not in kbid:
            emit("X13b", e["record_id"], "record_id", e["record_id"], "must exist in KB",
                 f"relation_graph_versioned_edges.csv#L{i}")

    # ---------------- X14 WS-B registers --------------------------------------------------
    for reg, nm in ((hold3, "holdings_register_cycle3.csv"), (st3, "subsequent_treatment_cycle3.csv")):
        for r in reg:
            for k in (r.get("case53_id") or r.get("earlier_case53_ids") or "").split(";"):
                k = k.strip()
                if k and k not in cid:
                    emit("X14", r["row_id"], "case53_id", k, "must exist in cases_53", nm)
            for kbx in re.split(r"[;, ]+", r.get("affected_kb_ids") or ""):
                if kbx and re.match(r"[A-Z]", kbx) and kbx not in kbid:
                    emit("X14b", r["row_id"], "affected_kb_ids", kbx, "must exist in records_658", nm)
            for f in ("copy_sha256", "later_copy_sha256"):
                s = r.get(f) or ""
                if re.fullmatch(r"[0-9a-f]{64}", s) and s not in held_sha:
                    emit("X14c", r["row_id"], f, s, "copy sha should be in held manifest", nm)
    for r in xw53:
        if r["kb_record_id"] and r["kb_record_id"] not in kbid:
            emit("X14d", r["spec_key"], "kb_record_id", r["kb_record_id"], "must exist", "crosswalk_cases53_kb658.csv")

    # ---------------- X15 neutral citation held in WS-B identity register but absent from case record
    held_case = {r["case53_id"] for r in ident if r.get("held_copy_sha256")}
    for r in ident:
        k = r.get("case53_id")
        if not k or k not in cid:
            continue
        nc = r.get("expected_neutral_citation_spec") or r.get("intern_neutral_citation")
        if nc and nc not in (cid[k].get("reporter_citation") or ""):
            emit("X15", k, "reporter_citation (neutral citation)", f"case '{cid[k].get('reporter_citation')}' lacks '{nc}'",
                 "neutral_citation is a schema field; WS-B identity evidence carries it",
                 f"WS-B identity_resolution.csv spec_key={r['spec_key']} spec={r.get('expected_neutral_citation_spec')}"
                 f" intern={r.get('intern_neutral_citation')} official_copy_held={k in held_case}")

    # ---------------- X16 duplicate KB titles ----------------------------------------------
    t = defaultdict(list)
    for r in kb:
        t[re.sub(r"\W+", " ", r["title"].lower()).strip()].append(r["id"])
    for k, v in t.items():
        if len(v) > 1:
            emit("X16", ";".join(v), "title", k, "duplicate concept candidate", "records_658.jsonl")

    # ---------------- X19 later-treatment propagation to linked KB records ---------------------
    xw_by_case = defaultdict(set)
    for r in xw53:
        if r["case53_id"] and r["kb_record_id"] in kbid:
            xw_by_case[r["case53_id"]].add(r["kb_record_id"])
    neg = re.compile(r"OVERRULED|NOT_GOOD_LAW|QUALIFIED|DISTINGUISHED|LIMITED|NO APPLICATION", re.I)
    st1 = rcsv(os.path.join(aw, "WS-B-JUDGMENTS/subsequent_treatment.csv"))
    for nm, reg in (("subsequent_treatment.csv", st1), ("subsequent_treatment_cycle3.csv", st3)):
        for r in reg:
            if not neg.search(r.get("treatment") or ""):
                continue
            listed = set(re.split(r"[;, ]+", r.get("affected_kb_ids") or ""))
            for k in (r.get("earlier_case53_ids") or "").split(";"):
                k = k.strip()
                linked = xw_by_case.get(k, set())
                missing = sorted(linked - listed)
                if missing:
                    emit("X19", r["row_id"], "affected_kb_ids",
                         f"{k} treated '{r['treatment'][:60]}' by {r['later_judgment'][:60]}; crosswalk-linked KB not listed: "
                         + ";".join(missing),
                         "every KB record linked to the treated case should be assessed for the later treatment",
                         f"{nm} {r['row_id']} (copy {r.get('later_copy_role')} {r.get('later_copy_sha256','')[:12]} p.{r.get('pdf_page')} para {r.get('para')}) vs crosswalk_cases53_kb658.csv")

    # ---------------- X20 chain effective-date status vs amendment register -------------------
    am_by_origin = {a["origin_id"]: a for a in amend}
    for ch in chain:
        a = am_by_origin.get(ch["instrument_ref"])
        if not a:
            continue
        cs, rs = ch["effective_date_status"].split(" ")[0], a["effective_date_status"].split(" ")[0]
        if cs != rs and "STATED" in rs and "NOT_DETERMINED" in cs:
            emit("X20", ch["chain_row_id"], "effective_date_status",
                 f"chain '{ch['effective_date_status'][:60]}' vs amendment_register {a['amendment_id']} '{a['effective_date_status'][:60]}'",
                 "same instrument -> same commencement status", "provision_amendment_chain.csv vs amendment_register.csv")

    # ---------------- X21 conflict split without parent pointer --------------------------------
    for cf in conflicts:
        if cf["origin_id"] == "C-04" and "OPEN" in cf["status"]:
            kids = [c["conflict_id"] for c in conflicts if c["origin_id"] in ("C-08", "C-09")]
            if kids and "split" not in (cf["status"] + cf["reserved_status"] + cf["nature_of_conflict"]).lower():
                emit("X21", cf["conflict_id"], "status", cf["status"],
                     "parent conflict split into children should point to them / be marked superseded",
                     "source_conflict_register.csv children: " + ";".join(kids))

    # ---------------- X18 conflict register referencing unknown sources -----------------
    for cf in conflicts:
        for f in ("source_a", "source_b"):
            for s in re.findall(r"C5-SRC-[A-Z0-9\-+]+", cf.get(f) or ""):
                s = s.rstrip("-")
                if s not in master_ids and s.split("~")[0] not in master_ids:
                    emit("X18", cf["conflict_id"], f, s, "source must exist in master", "source_conflict_register.csv")

    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["check_id", "object_id", "field", "observed", "expected_or_rule",
                                          "evidence"])
        w.writeheader()
        w.writerows(rows)
    c = Counter(r["check_id"] for r in rows)
    for k in sorted(c):
        print(k, c[k])
    print("total", len(rows))


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(*sys.argv[1:])
