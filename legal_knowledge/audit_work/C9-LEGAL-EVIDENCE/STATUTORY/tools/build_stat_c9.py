#!/usr/bin/env python3
"""C9-STAT builder: statutory evidence packages, acquisition reconciliation, amendment graph, unresolved matters,
baseline metrics and findings for Project Mimamsa Cycle 9.

Usage:
  python3 -I build_stat_c9.py <repo> --evidence-repo <c8_evidence_repo> [--check]

<repo>           read-only snapshot (commit 2d7c02cf) containing legal_knowledge/audit_work/C8-SOURCES etc.
<evidence-repo>  read-only tree containing legal_knowledge/audit_work/C8-EVIDENCE (Cycle 8 Gazette evidence).
Inputs under tools/inputs/ (produced by extract_branch_pins.py and collect_readings_c9.py, both with --check modes):
  branch_pins.csv, held_hashes_c9.csv, c9_page_readings.csv, rawdata_statutory_holdings.csv
Writes every output next to tools/ (the STAT folder) and OUTPUT_SHA256SUMS. With --check, nothing is written;
each output is regenerated in memory and compared byte-for-byte with the file on disk (exit 1 on any difference).

Nothing here changes legal status, applicability or a commencement date; no date is inferred. Every page
reading cited was made by an AI agent (Claude Opus 5.5 subagent), not human-confirmed.
"""
import argparse, collections, csv, hashlib, io, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
INP = os.path.join(HERE, "inputs")
READER = "AI agent (Claude Opus 5.5 subagent), not human-confirmed"
STACK = ["staging (v2.5-staging)", "PR #8 (ACQ-01)", "PR #17 (ACQ-02)", "PR #23 (ACQ-03)", "PR #9 (DESW allow-list)"]
STATUSES = ("EVIDENCED", "UNRESOLVED_COMMENCEMENT", "DISPUTED_PRESERVE_BOTH", "NOT_LOCATED")


def rcsv(p):
    with open(p, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def wcsv(fields, rows):
    b = io.StringIO()
    w = csv.DictWriter(b, fields, lineterminator="\n", extrasaction="raise")
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k, "") for k in fields})
    return b.getvalue()


def sha_file(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


# ----------------------------------------------------------------------------------------------------------------
class Ctx:
    def __init__(self, repo, ev):
        self.repo, self.ev = repo, ev
        aw = os.path.join(repo, "legal_knowledge/audit_work")
        self.aw = aw
        self.c8p = os.path.join(aw, "C8-SOURCES/PRIMARY-SOURCES")
        self.c5r = os.path.join(aw, "SOURCE-LIBRARY-C5/registers")
        self.evg = os.path.join(ev, "legal_knowledge/audit_work/C8-EVIDENCE/GAZETTE-T1")
        self.copies = rcsv(os.path.join(self.c5r, "source_copy_register.csv"))
        self.copies_by_src = collections.defaultdict(list)
        self.copy_by_sha = {}
        for c in self.copies:
            self.copies_by_src[c["source_id"]].append(c)
            self.copy_by_sha.setdefault(c["sha256"], c)
        self.held = rcsv(os.path.join(INP, "held_hashes_c9.csv"))
        self.held_by_sha = {}
        self.held_by_md5 = {}
        for h in self.held:
            self.held_by_sha.setdefault(h["rehash_sha256"], h)
            self.held_by_md5.setdefault(h["md5"], h)
        self.raw = rcsv(os.path.join(INP, "rawdata_statutory_holdings.csv"))
        self.raw_by_sha = {r["sha256"]: r for r in self.raw}
        self.raw_by_url = {r["source_url"]: r for r in self.raw}
        self.raw_commit = self.raw[0]["rawdata_commit"] if self.raw else ""
        self.pins = rcsv(os.path.join(INP, "branch_pins.csv"))
        self.readings = {r["reading_id"]: r for r in rcsv(os.path.join(INP, "c9_page_readings.csv"))}
        self.gaps = {r["gap_id"]: r for r in rcsv(os.path.join(self.c8p, "source_to_record_gap_matrix.csv"))}
        self.amc = rcsv(os.path.join(self.c8p, "amendment_commencement_matrix.csv"))
        self.ssm = rcsv(os.path.join(self.c8p, "statutory_source_matrix.csv"))
        self.c602 = rcsv(os.path.join(self.c8p, "c6_02_readiness.csv"))
        self.pension = {r["pension_doc_key"]: r for r in rcsv(os.path.join(self.c8p, "pension_source_coverage.csv"))}
        self.acqreg = {r["acq_c5_id"]: r for r in rcsv(os.path.join(self.c5r, "acquisition_register.csv"))}
        self.conf = {r["conflict_id"]: r for r in rcsv(os.path.join(self.c5r, "source_conflict_register.csv"))}
        self.gaz = {r["held_sha256"]: r for r in rcsv(os.path.join(self.evg, "gazette_evidence_register.csv"))}
        self.cr8 = {r["entry_id"]: r for r in rcsv(os.path.join(self.evg, "contradiction_register_c8.csv"))}
        self.used_readings = set()

    # evidence helpers ------------------------------------------------------------------------------------------
    def rd(self, rid, pages=None):
        r = self.readings.get(rid)
        if r is None:
            raise SystemExit(f"reading {rid} missing from inputs/c9_page_readings.csv")
        if r["result"] not in ("FOUND", "IMAGE_READ", "ABSENT_ALL_PAGES"):
            raise SystemExit(f"reading {rid} has result {r['result']}; evidence cannot be cited")
        self.used_readings.add(rid)
        pg = pages or r["pages"]
        loc = r["held_path"]
        src = "corpus raw store" if loc.startswith("raw-data@") else "held"
        if r["result"] == "ABSENT_ALL_PAGES":
            return f"{rid} [{src} sha256 {r['sha256'][:16]}; absent on all pages]"
        extra = f"; render sha256 {r['render_sha256'][:16]}" if r["render_sha256"] else ""
        return f"{rid} [{src} sha256 {r['sha256'][:16]} p.{pg}{extra}]"

    def gap_records(self, gap_ids):
        recs, cases = set(), set()
        for g in gap_ids:
            row = self.gaps.get(g)
            if row is None:
                raise SystemExit(f"gap {g} not in source_to_record_gap_matrix.csv")
            recs.update(x for x in row["kb_record_ids"].split(";") if x)
            cases.update(x for x in row["case_ids"].split(";") if x)
        return sorted(recs), sorted(cases)

    def held_copies(self, source_ids=(), raw_shas=(), held_shas=()):
        out, auth = [], []
        for sid in source_ids:
            for c in self.copies_by_src.get(sid, []):
                h = self.held_by_sha.get(c["sha256"])
                hc = h["hash_check"] if h else "NOT_IN_HELD_MANIFEST"
                out.append(f"{c['copy_id']} sha256 {c['sha256']} ({c['pages']} pp.; re-hash {hc})")
                cls = c["copy_evidence_class"]
                g = self.gaz.get(c["sha256"])
                if g:
                    cls += f"; C8 GAZETTE-T1 {g['tranche_id']}: identity {g['c8_identity_result']}, {g['c8_recommendation']}"
                auth.append(f"{c['copy_id']}: {cls} (eligible_for_exact_anchor={c['eligible_for_exact_anchor']})")
        for s in held_shas:
            h = self.held_by_sha.get(s)
            if not h:
                raise SystemExit(f"held sha {s} not in held manifest")
            c = self.copy_by_sha.get(s)
            if c and any(c["copy_id"] in o for o in out):
                continue
            out.append(f"held {h['held_path']} sha256 {s} ({h['pages']} pp.; re-hash {h['hash_check']})")
            auth.append(f"{h['held_path']}: " + (c["copy_evidence_class"] if c else "NO_C5_COPY_ROW (held binary not registered)"))
        for s in raw_shas:
            r = self.raw_by_sha.get(s)
            if not r:
                raise SystemExit(f"raw sha {s} not in rawdata_statutory_holdings.csv")
            c = self.copy_by_sha.get(s)
            out.append(f"corpus raw store raw-data@{r['rawdata_commit'][:8]}:{r['raw_path']} sha256 {s} (retrieved {r['retrieved_at']} from {r['source_url']}; crawl title '{r['title']}')")
            if c:
                auth.append(f"{r['raw_path']}: byte-identical to {c['copy_id']} ({c['copy_evidence_class']}); the raw-data retrieval record is a provenance lead (owner decision; AP-C9-02)")
            else:
                auth.append(f"{r['raw_path']}: UNREGISTERED_CORPUS_RAW_COPY (no C5 copy row; no AUTH-LEDGER class assigned; retrieval record in raw-data data/raw_manifest.csv)")
        return out, auth


# ----------------------------------------------------------------------------------------------------------------
def build_metrics(ctx):
    kbp = os.path.join(ctx.repo, "legal_knowledge/curated_originals/knowledge_base/v0.9/records_658.jsonl")
    csp = os.path.join(ctx.repo, "legal_knowledge/curated_originals/case_law/v0.9/cases_53.jsonl")
    kb = [json.loads(l) for l in open(kbp, encoding="utf-8") if l.strip()]
    cs = [json.loads(l) for l in open(csp, encoding="utf-8") if l.strip()]
    frozen = json.load(open(os.path.join(ctx.aw, "SOURCE-LIBRARY-C5/baseline/frozen_baseline_manifest.json")))
    x = rcsv(os.path.join(ctx.c5r, "corpus_crosswalk.csv"))
    kbx = [r for r in x if r["knowledge_base_record_id"]]
    cites = [r for r in kbx if r["relationship_type"] == "CITES"]
    st = collections.Counter(r["evidence_status"] for r in cites)
    anchors = [r for r in kbx if r["evidence_status"] == "EXACT_ANCHOR"]
    anchor_copies = collections.Counter(r["anchor_copy_id"] for r in anchors)
    g = collections.defaultdict(list)
    for r in kbx:
        g[r["knowledge_base_record_id"]].append(r)
    noex = sorted(k for k, v in g.items() if not any(i["evidence_status"] == "EXACT_ANCHOR" for i in v))
    nocit = sorted(k for k, v in g.items() if all(i["relationship_type"] == "NO_CITATION" for i in v))
    allx = [k for k, v in g.items() if all(i["evidence_status"] == "EXACT_ANCHOR" for i in v)]
    somex = [k for k, v in g.items() if any(i["evidence_status"] == "EXACT_ANCHOR" for i in v) and k not in allx]
    cx = [r for r in x if r["case_id"]]
    cst = collections.Counter(r["evidence_status"] for r in cx)
    anchor_copy = anchor_copies.most_common(1)[0][0] if anchor_copies else ""
    anchor_sha = next((c["sha256"] for c in ctx.copies if c["copy_id"] == anchor_copy), "")
    h = ctx.held_by_sha.get(anchor_sha, {})
    eff = os.path.join(ctx.aw, "AUTH-LEDGER/effective/v0000/corpus_crosswalk.csv")
    frozen_sha = frozen.get("original_corpus_sha256", {})

    def m(name, reported, value, method):
        ok = str(reported) == str(value)
        return {"metric": name, "reported": reported, "recomputed": value, "result": "MATCH" if ok else "DIFFERENCE", "method": method}

    metrics = [
        m("kb_records", 658, len({r["id"] for r in kb}), "distinct 'id' in curated_originals/knowledge_base/v0.9/records_658.jsonl"),
        m("case_records", 53, len({r["id"] for r in cs}), "distinct 'id' in curated_originals/case_law/v0.9/cases_53.jsonl"),
        m("kb_crosswalk_rows", 1060, len(kbx), "SOURCE-LIBRARY-C5/registers/corpus_crosswalk.csv rows with knowledge_base_record_id"),
        m("kb_citation_items", 983, len(cites), "same, relationship_type=CITES"),
        m("kb_no_citation_placeholders", 77, sum(1 for r in kbx if r["relationship_type"] == "NO_CITATION"), "same, relationship_type=NO_CITATION"),
        m("kb_items_exact_anchor", 42, st["EXACT_ANCHOR"], "CITES rows, evidence_status=EXACT_ANCHOR"),
        m("kb_items_partial_match", 652, st["PARTIAL_MATCH"], "CITES rows, evidence_status=PARTIAL_MATCH"),
        m("kb_items_missing_evidence_genuine", 289, st["MISSING_EVIDENCE"], "CITES rows, evidence_status=MISSING_EVIDENCE (placeholders excluded)"),
        m("kb_records_no_exact_anchor", 618, len(noex), "records grouped by knowledge_base_record_id with no EXACT_ANCHOR row"),
        m("kb_records_no_exact_anchor_with_citations", 541, len([k for k in noex if k not in nocit]), "618 minus records whose only row is NO_CITATION"),
        m("kb_records_citing_nothing", 77, len(nocit), "records whose only crosswalk row is NO_CITATION"),
        m("kb_records_all_items_exact", 10, len(allx), "every row EXACT_ANCHOR"),
        m("kb_records_some_items_exact", 30, len(somex), "at least one but not all rows EXACT_ANCHOR"),
        m("case_records_exact_partial_missing", "6/7/40", f"{cst['EXACT_ANCHOR']}/{cst['PARTIAL_MATCH']}/{cst['MISSING_EVIDENCE']}", "crosswalk rows with case_id by evidence_status"),
        m("exact_anchor_distinct_copies", 1, len(anchor_copies), "distinct anchor_copy_id over the 42 EXACT_ANCHOR KB rows"),
        m("crosswalk_kb_records_equal_corpus_records", True, set(g) == {r["id"] for r in kb}, "set of crosswalk KB ids equals set of records_658 ids"),
        m("records_658_sha256_equals_frozen", True, sha_file(kbp) == frozen_sha.get("records_658"), "sha256 of records_658.jsonl vs frozen_baseline_manifest.json#original_corpus_sha256.records_658"),
        m("cases_53_sha256_equals_frozen", True, sha_file(csp) == frozen_sha.get("cases_53"), "sha256 of cases_53.jsonl vs frozen manifest"),
        m("auth_ledger_v0000_crosswalk_identical_to_c5", True, sha_file(eff) == sha_file(os.path.join(ctx.c5r, "corpus_crosswalk.csv")), "sha256 AUTH-LEDGER/effective/v0000/corpus_crosswalk.csv == SOURCE-LIBRARY-C5/registers/corpus_crosswalk.csv"),
    ]
    out = {
        "version": "C9-STAT-1",
        "snapshot": "repo given on the command line (expected commit 2d7c02cf)",
        "inputs_sha256": {
            "records_658.jsonl": sha_file(kbp), "cases_53.jsonl": sha_file(csp),
            "corpus_crosswalk.csv": sha_file(os.path.join(ctx.c5r, "corpus_crosswalk.csv")),
            "source_copy_register.csv": sha_file(os.path.join(ctx.c5r, "source_copy_register.csv")),
        },
        "metrics": metrics,
        "all_42_exact_anchors_on_one_copy": {
            "anchor_copy_id": anchor_copy, "anchor_copy_sha256": anchor_sha, "count": anchor_copies.get(anchor_copy, 0),
            "held_path": h.get("held_path", ""), "rehash": h.get("hash_check", ""),
            "consequence": "every exact anchor depends on the 1954 Army Rules facsimile (as notified); none establishes current text",
        },
        "all_match": all(i["result"] == "MATCH" for i in metrics),
        "reader": "computed by script; no page reading involved",
    }
    return json.dumps(out, indent=2, sort_keys=False) + "\n", out


# ----------------------------------------------------------------------------------------------------------------
def unique_pins(ctx):
    order = {lab: i for i, lab in enumerate(STACK)}
    seen = {}
    for p in ctx.pins:
        if p["pr_label"] in ("snapshot c9src", "REF_ABSENT_LOCALLY") or not p["doc_id"]:
            continue
        k = (p["source_key"], p["doc_id"])
        e = seen.setdefault(k, {"row": p, "present_in": [], "commits": {}})
        e["present_in"].append(p["pr_label"])
        e["commits"][p["pr_label"]] = p["ref_commit"]
        if order[p["pr_label"]] < order[e["row"]["pr_label"]]:
            e["row"] = p
    res = []
    for k, e in seen.items():
        intro = min(e["present_in"], key=lambda l: order[l])
        res.append((intro, k, e))
    res.sort(key=lambda t: (order[t[0]], t[1]))
    return res


def ar_id_for_sha(ctx, sha):
    c = ctx.copy_by_sha.get(sha)
    if not c:
        return ""
    m = re.match(r"C5-SRC-P0-AR-AMD-(AR-\d{3})", c["source_id"])
    if m:
        return m.group(1)
    if c["source_id"] == "C5-SRC-P0-ARMY-RULES-1954":
        return "AR-000"
    return ""


# ----------------------------------------------------------------------------------------------------------------
# Curated instrument catalogue. Every factual cell cites a register key or a reading id.
def instruments(ctx):
    rd = ctx.rd
    I = []

    def add(**k):
        k.setdefault("source_ids", [])
        k.setdefault("raw_shas", [])
        k.setdefault("held_shas", [])
        k.setdefault("gaps", [])
        k.setdefault("contradictions", "none recorded")
        I.append(k)

    # ---------------- Priority 1: Army Act 1950 ----------------
    add(id="I-AA-1950", priority="1", family="Army Act 1950",
        title="The Army Act, 1950 (Act No. 46 of 1950)", title_basis=f"compilation title page {rd('C9R-AA-01')}; enacted Gazette text not held",
        authority="Parliament", number="Act 46 of 1950", date="20-05-1950 (assent, as printed in the India Code compilation only)",
        date_basis=rd("C9R-AA-13"), commencement=f"compilation footnote to s.1(2): 22-07-1950 vide S.R.O. 120 of 22-07-1950 {rd('C9R-AA-02')}; COMMENCEMENT NOTIFICATION REQUIRED (not held; C8 D-AMC-AA-00)",
        source_ids=["C5-SRC-P0-ARMY-ACT-1950-INDIACODE", "C5-SRC-P2-MML-MML-VOL-2-AA--PDF", "C5-SRC-P2-MML-MML-VOL-2-AA--DOC"],
        raw_shas=["e47a4265813e95b491a24926428ed306cfeaae9013e7edb928cefef6e69a7c08", "42b9a2f816f635b41c8ec75bb769978e7f113bdb322e15faaec871139e1d0d68", "3a551c1f5919dd9011eed191962950d6ce3e7267dc0987785408798d8b49f87d"],
        missing="Gazette of India Extraordinary text as enacted (pinned archive.org in.gazette.e.1950.306, md5 68bcdd4e8db91eb83d1e6b92a393b2db; C5-ACQ-01 = ACQ-C3-01; in no config PR); S.R.O. 120/1950; RAA 1957 and S.O. 3912(E)/2019 not located; post-1992 amending Acts NOT_FOUND (not proof of none)",
        contradictions="none between held documents; compilation 'w.e.f.' dates are compiler statements (see I-AA-ACT37-1992, I-AA-ACT13-1975)",
        gaps=["G-AA-ENACT"], route="A-C5-1 archive.org Gazette (needs a new config PR; ACQ-C3-01); provenance registration of the India Code compilation via its raw-data retrieval record (AP-C9-02)",
        auth="A-C5-1 (download) + crawler-config PR; owner decision on raw-data provenance lead (AP-C9-02)", verification="COMPILATION_ONLY; enacted text NOT HELD")
    add(id="I-AA-SRO120-1950", priority="1", family="Army Act 1950", title="Notification S.R.O. 120 dated 22-07-1950 appointing the commencement date of the Army Act, 1950 (as named in the compilation)",
        title_basis=rd("C9R-AA-02"), authority="Central Government", number="S.R.O. 120", date="22-07-1950 (compilation footnote only)", date_basis=rd("C9R-AA-02"),
        commencement="n/a (this is the commencement instrument)", missing="the notification itself; probable candidate ACQ03-019 (PR #23, md5 c99cf489..., OCR identity only)",
        gaps=["G-AA-COMM"], route="PR #23 ACQ03-019 (archive_acq03)", auth="PR #23 approval + download-run approval (ACQ-03 scope)", verification="NOT_HELD; identity of candidate unverified")
    add(id="I-AA-ACT19-1955", priority="1", family="Army Act 1950", title="The Commanders-in-Chief (Change in Designation) Act, 1955 (Act No. 19 of 1955)", title_basis=rd("C9R-A19-01"),
        authority="Parliament", number="Act 19 of 1955", date="03-05-1955 (assent, India Code text rendering)", date_basis=rd("C9R-A19-01"),
        commencement=f"s.1(2) by notification; rendering footnote: 07-05-1955 vide S.R.O. 2(E) of 07-05-1955 {rd('C9R-A19-02')}; notification not held",
        source_ids=["C5-SRC-P0-AA-AMD-ACT19-1955"], missing=f"Gazette text with the Schedule (s.2 and Schedule repealed by Act 58/1960 {rd('C9R-A19-03')}); S.R.O. 2(E)/1955",
        gaps=["G-AA-AA-01"], route="PR #8 act-commanders-in-chief-change-designation-1955 (archive in.gazette.e.1955.613, md5 6371b6ad...) and PR #23 ACQ03-020 (S.R.O. 2(E)/1955)",
        auth="PR #8 within ACQ-01 B6 owner authorisation (execution approval pending); PR #23 for ACQ03-020", verification="INCOMPLETE_EXTRACT (text rendering, Schedule absent)")
    add(id="I-AA-SRO2E-1955", priority="1", family="Army Act 1950", title="Notification S.R.O. 2(E) dated 07-05-1955 (commencement of Act 19 of 1955), as named in the rendering",
        title_basis=rd("C9R-A19-02"), authority="Central Government", number="S.R.O. 2(E)", date="07-05-1955 (rendering only)", date_basis=rd("C9R-A19-02"),
        commencement="n/a", missing="the notification", gaps=["G-AA-AA-01"], route="PR #23 ACQ03-020", auth="PR #23 approval + download run", verification="NOT_HELD")
    for iid, title, num, gid, acq, note in [
        ("I-AA-ALO3-1956", "Adaptation of Laws (No. 3) Order, 1956", "A.L.O. (No.3) 1956", "G-AA-AA-02+AA-C3-01", "PR #23 ACQ03-021", rd("C9R-AA-11")),
        ("I-AA-RAA-1957", "Repealing and Amending Act, 1957 (36 of 1957)", "Act 36 of 1957", "G-AA-AA-C3-03", "no candidate (ACQ-C3-06 'not located')", rd("C9R-AA-12")),
        ("I-AA-RAA-1974", "Repealing and Amending Act, 1974 (56 of 1974)", "Act 56 of 1974", "G-AA-AA-04", "PR #23 ACQ03-015", "C8 D-AMC-AA-04"),
        ("I-AA-ORD3-1975", "Air Force and Army Laws (Amendment) Ordinance, 1975 (Ord. 3 of 1975)", "Ordinance 3 of 1975", "G-AA-AA-05", "PR #23 ACQ03-022 (derivative PDF only)", "C8 D-AMC-AA-05; repealed by Act 13/1975 s.4(1) " + rd("C9R-A13-02")),
        ("I-AA-SO3912E-2019", "Notification S.O. 3912(E) dated 30-10-2019 (application of the Army Act to the Union territories of Jammu and Kashmir and Ladakh, per compilation)", "S.O. 3912(E)", "G-AA-AA-C3-02", "no candidate (ACQ-C3-05; egazette unreachable)", rd("C9R-AA-08")),
    ]:
        add(id=iid, priority="1", family="Army Act 1950", title=title + " (title as recorded in compilation/registers; instrument not held)", title_basis=note,
            authority="as printed (not held)", number=num, date="not evidenced by a held instrument", date_basis="C8 amendment_commencement_matrix",
            commencement="not evidenced", missing="the instrument", gaps=[gid], route=acq,
            auth=("PR #23 approval + download run" if "PR #23" in acq else "discovery approval (no candidate in any register)"), verification="NOT_HELD")
    add(id="I-AA-ACT13-1975", priority="1", family="Army Act 1950", title="The Air Force and Army Laws (Amendment) Act, 1975 (No. 13 of 1975)", title_basis=rd("C9R-A13-01"),
        authority="Parliament", number="Act 13 of 1975", date="29-03-1975 (assent and Gazette Extraordinary Pt II s.1 No.16, 29-03-1975)", date_basis=rd("C9R-A13-01"),
        commencement=f"no commencement clause {rd('C9R-A13-03')}; s.4(2) saving deems actions under the Ordinance taken 'as if this Act had come into force on the 25th day of January, 1975' {rd('C9R-A13-02')}; compilation prints 'w.e.f. 25-1-1975' {rd('C9R-AA-09')} (compiler statement; adviser OQ-A-04)",
        source_ids=["C5-SRC-P0-AA-AMD-ACT13-1975"], missing="none for text; provenance undocumented (India Code scan, PR #8 official_instruments pin act-air-force-army-laws-amendment-1975 for a record copy)",
        gaps=["G-AA-AA-06"], route="PR #8 official_instruments (India Code bitstream; host watermarks, listing md5 not comparable)", auth="PR #8 execution approval (ACQ-01 B6 authorised)", verification="PAGE_IMAGE_CHECKED (WS-A); commencement NOT_DETERMINED")
    add(id="I-AA-ACT20-1983", priority="1", family="Army Act 1950", title="The Delegated Legislation Provisions (Amendment) Act, 1983 (20 of 1983) (title as printed in the compilation list; not verified on the Act)",
        title_basis=rd("C9R-AA-06"), authority="Parliament", number="Act 20 of 1983", date="not evidenced", date_basis="C8 D-AMC-AA-07",
        commencement=f"compilation: s.193A ins. 'w.e.f. 15-3-1984' {rd('C9R-AA-07')}; s.1(2) notification not held (candidate ACQ03-024)",
        missing="the Act (candidate ACQ03-023) and its s.1(2) notification (candidate ACQ03-024)", gaps=["G-AA-AA-07"], route="PR #23 ACQ03-023, ACQ03-024",
        auth="PR #23 approval + download run", verification="NOT_HELD")
    add(id="I-AA-ACT37-1992", priority="1", family="Army Act 1950", title="The Army (Amendment) Act, 1992 (No. 37 of 1992)", title_basis=rd("C9R-A37-01"),
        authority="Parliament", number="Act 37 of 1992", date="06-09-1992 (assent); Gazette of India Extraordinary No. 59, 07-09-1992", date_basis=f"{rd('C9R-A37-01')}; {rd('C9R-A37-02')}",
        commencement=f"no commencement clause on any of the 4 pages {rd('C9R-A37-03')}; compilation prints '(w.e.f. 6-9-1992)' ONLY at ss.75-76 (s.2), s.127 (s.11) and Chapter XVI (s.19) {rd('C9R-AA-03')}; the other Act 37/1992 footnotes carry no date {rd('C9R-AA-04')}; NOT_STATED_PENDING_ADVICE (AQ-05)",
        source_ids=["C5-SRC-P0-AA-AMD-ACT37-1992"], missing="none for text; commencement rule is a legal question (AQ-05)", gaps=[],
        route="PR #8 official_instruments act-army-amendment-1992 (record copy); ACQ03-016 archive copy optional", auth="PR #8 execution approval", verification="PAGE_IMAGE_CHECKED (PILOT-01); DOCUMENTED_PRIMARY_COPY")
    for iid, title, num, acq in [("I-AA-RAA-2001", "Repealing and Amending Act, 2001 (30 of 2001)", "Act 30 of 2001", "PR #23 ACQ03-017"),
                                 ("I-AA-RAA2-2017", "Repealing and Amending (Second) Act, 2017 (4 of 2018)", "Act 4 of 2018", "PR #23 ACQ03-025"),
                                 ("I-AA-RAA-1960", "Repealing and Amending Act, 1960 (58 of 1960)", "Act 58 of 1960", "no candidate pinned")]:
        add(id=iid, priority="1", family="Army Act 1950", title=title + " (repeals amending Acts only; per C8 matrix no direct Army Act text effect)", title_basis="C8 amendment_commencement_matrix (D-AMC-AA-03/09/10)",
            authority="Parliament", number=num, date="not evidenced", date_basis="register", commencement="not evidenced", missing="the Act", route=acq,
            auth=("PR #23 approval + download run" if "PR #23" in acq else "discovery approval"), verification="NOT_HELD")
    add(id="I-AA-NOTIFS", priority="1", family="Army Act 1950", title="Gazette notifications under the Army Act (e.g. s.4 application, s.9 active service declarations)", title_basis="C8 D-SSM-016",
        authority="Central Government", number="various", date="various", date_basis="register", commencement="per notification", missing="all (phase 6 discovery)",
        route="egazette discovery (unreachable from container: TLS)", auth="discovery approval; Indian-network run", verification="NOT_HELD")
    add(id="I-AA-POST1992", priority="1", family="Army Act 1950", title="Any Act amending the Army Act after 1992", title_basis="C8 D-SSM-015 / D-AMC-AA-13",
        authority="Parliament", number="unknown", date="unknown", date_basis="register", commencement="unknown", missing="NOT_FOUND in searched sources (not proof of none); compilation as on 21-07-2025 lists no Act after 37/1992 " + rd("C9R-AA-01"),
        gaps=["G-AA-AA-13"], route="no lawful online source known (ACQ03-027)", auth="discovery approval", verification="NOT_LOCATED")

    # ---------------- Priority 2: Army Rules 1954 ----------------
    add(id="I-AR-1954", priority="2", family="Army Rules 1954", title="The Army Rules, 1954 (S.R.O. 484)", title_basis="C5 copy C5-SRC-P0-ARMY-RULES-1954~C1 (WS-A image check); compilation p.1 " + rd("C9R-AR-04", "189"),
        authority="Central Government (Ministry of Defence), under Army Act s.191", number="S.R.O. 484", date="27-11-1954 (notification and Gazette Pt II s.4 No.47)", date_basis="C8 D-AMC-AR-000",
        commencement="no commencement clause in r.1 (WS-A image check); NOT_STATED_PENDING_ADVICE (AQ-05)",
        source_ids=["C5-SRC-P0-ARMY-RULES-1954", "C5-SRC-P0-ARMY-RULES-1954-INDIACODE", "C5-SRC-P2-MML-MML-VOL-2-AR--DOC", "C5-SRC-P2-MML-MML-VOL-2-AR--DOC-1"],
        raw_shas=["48f52219121bf74d070bc832e4573f2f512b239e0a0441ba96b1daca2983a727"],
        missing="complete amendment chain: E-7/1960 (AR-001), S.R.O. 258/2002 (AR-030), anything after 06-06-2022 (AR-036; 10 candidates C5-ACQ-06), 13 unopened hints, 5 text-layer-only instruments",
        contradictions=f"C-01 r.23(3) CONFLICTING; C-02 r.192; C-03 r.177; SC4-01 r.182 OPEN; C-08/C-04 r.193 OPEN; C-09 r.194 PROPOSAL; NEW C9-AG-AR168: compilation r.168(2) still prints field-punishment words {rd('C9R-AR-01')} which S.R.O. 17(E)/1993 item 31 omits {rd('C9R-AR-02')}",
        gaps=["G-AR-CHAIN", "G-AR-POST2022"], route="PR #8 notif-army-rules-1954-sro-484 (record copy; research copy md5-identical); C5-ACQ-06 for post-2022", auth="PR #8 execution approval; A-C5-1 + new config PR for C5-ACQ-06",
        verification="DOCUMENTED_PRIMARY_COPY (as notified); currency NOT established")
    add(id="I-AR-INTERIM-1950", priority="2", family="Army Rules 1954", title="Rules under Army Act ss.21, 102(4) and 191 (Gazette Extraordinary No.8, 1950) - historical", title_basis="C8 D-SSM-050; C5-ACQ-19",
        authority="Central Government", number="Gazette Extraordinary No.8 of 1950", date="1950 (register)", date_basis="register", commencement="not evidenced", missing="the instrument (archive md5 60ff7985...)",
        route="C5-ACQ-19 archive.org (historical; no config PR)", auth="A-C5-4", verification="NOT_HELD")
    return I


def ar_amendment_instruments(ctx, pin_by_ar, acq03_by_ar):
    """One instrument record per Army Rules amending/declaration instrument in the C8 matrix (AR-001..AR-046)."""
    rows = []
    for r in ctx.amc:
        m = re.match(r"D-AMC-(AR-(\d{3}))$", r["row_id"])
        if not m or m.group(1) == "AR-000":
            continue
        arid = m.group(1)
        sid = f"C5-SRC-P0-AR-AMD-{arid}"
        if arid in ("AR-026", "AR-027"):
            sid = "C5-SRC-P0-AR-AMD-AR-026+AR-027"
        held = r["supporting_document_held"].startswith("YES")
        # only instrument-specific gap rows; chain-wide dependents (G-AR-CHAIN) are counted once at I-AR-1954
        gap = f"G-{arid}" if f"G-{arid}" in ctx.gaps else ("G-AR-POST2022" if arid == "AR-036" else "")
        pins = pin_by_ar.get(arid, []) + acq03_by_ar.get(arid, [])
        route = "; ".join(pins) if pins else ("C5-ACQ-06 (archive metadata pins; no config PR)" if arid == "AR-036" else "no candidate (custodian or Indian-network egazette)" if arid in ("AR-001", "AR-030") else "none needed (held)" if held else "not pinned")
        auth = []
        if any(p.startswith("PR #8") for p in pins):
            auth.append("PR #8 execution approval (ACQ-01 B1 authorised)")
        if any(p.startswith("PR #17") for p in pins):
            auth.append("PR #17 approval + ACQ-02 download run")
        if any(p.startswith("PR #23") for p in pins):
            auth.append("PR #23 approval + ACQ-03 download run")
        if arid == "AR-036":
            auth.append("A-C5-1 + new config PR")
        if arid in ("AR-001", "AR-030"):
            auth.append("discovery approval / A-C5-3 custodian route")
        if held and not auth:
            auth.append("owner decision on provenance (AUTH-LEDGER T1)")
        ver = r["verification_status"] or "UNKNOWN"
        rows.append(dict(id=f"I-AR-AMD-{arid[3:]}", priority="2", family="Army Rules 1954",
                         title=r["amending_instrument"] + " (as recorded; title as printed where image-checked)",
                         title_basis=f"C8 amendment_commencement_matrix#{r['row_id']}; gazette identity: {r['gazette_identity'] or 'not captured'}",
                         authority="Central Government (Ministry of Defence)", number=r["amending_instrument"].split(" - ")[0],
                         date=r["publication_date"] + " (publication)", date_basis=f"C8 {r['row_id']}",
                         commencement=f"{r['commencement_as_printed'] or 'not captured'}; evidenced: {r['commencement_date_evidenced'] or 'none'}; C8 gap: {r['commencement_gap']}",
                         source_ids=[sid] if held else [], raw_shas=[], held_shas=[], gaps=[gap] if gap else [],
                         missing=("" if held else "the instrument") + ("" if held else f" ({ver})"),
                         contradictions=r["unresolved_conflicts"] or "none recorded",
                         route=route, auth="; ".join(auth) or "n/a", verification=ver, amc_row=r["row_id"], provision=r["provision_affected"]))
    return rows


def more_instruments(ctx):
    rd = ctx.rd
    I = []

    def add(**k):
        for d in ("source_ids", "raw_shas", "held_shas", "gaps"):
            k.setdefault(d, [])
        k.setdefault("contradictions", "none recorded")
        I.append(k)

    # ---------------- Priority 3: AFT ----------------
    add(id="I-AFT-2007", priority="3", family="AFT Act 2007", title="The Armed Forces Tribunal Act, 2007 (No. 55 of 2007)", title_basis=rd("C9R-RD-AFT07-IMG"),
        authority="Parliament", number="Act 55 of 2007", date="25-12-2007 (assent); Gazette of India Extraordinary Pt II s.1 No.66, 28-12-2007", date_basis=rd("C9R-RD-AFT07-IMG"),
        commencement=f"s.1(2) by notification {rd('C9R-RD-AFT07-IMG')}; compilation footnote 15-06-2008 vide S.O. 14(E) of 13-06-2008 {rd('C9R-AFT-04')}; notification NOT HELD",
        source_ids=["C5-SRC-P0-AFT-ACT-2007-INDIACODE"], raw_shas=["338d43addeaa14b7112298f3d460fd18bf8edd7b340b48fce0a546076cf273ef", "665863d1abb802f7488eb75f776946e30e72ccec16962da8e2b3ee8f2e023e3b"],
        missing="S.O. 14(E)/2008 (in no register; discovery needed)",
        contradictions="C8 recorded 'Gazette as enacted NOT held'; C9 finds the Gazette scan in the corpus raw store (raw-data crawl category 'rule', title 'AFT-Act2007' - mislabelled) - correction to C8 D-SSM-053",
        gaps=["G-AFT-ENACT", "G-AFT-COMM"], route="already held in corpus raw store (approved India Code run 2026-11-21); archive.org C5-ACQ-02 now optional independent copy",
        auth="owner decision on raw-data provenance lead + page-image identity review (AP-C9-02); no download needed for enacted text", verification="HELD_CORPUS_RAW_UNREGISTERED; masthead and s.1 image-read in C9")
    add(id="I-AFT-SO14E-2008", priority="3", family="AFT Act 2007", title="Notification S.O. 14(E) dated 13-06-2008 appointing 15-06-2008 under s.1(2) of the AFT Act (as named in the compilation)", title_basis=rd("C9R-AFT-04"),
        authority="Central Government", number="S.O. 14(E)", date="13-06-2008 (compilation only)", date_basis=rd("C9R-AFT-04"), commencement="n/a", missing="the notification; not in any register or PR",
        gaps=["G-AFT-COMM"], route="official-source discovery (egazette; India Code AFT item lists no s.1(2) notification among the 15 linked raw files)", auth="discovery approval", verification="NOT_HELD")
    add(id="I-AFT-RDO-2008", priority="3", family="AFT Act 2007", title="The Armed Forces Tribunal Act (Removal of Difficulties) Order, 2008 (S.R.O. 18(E))", title_basis=rd("C9R-RD-AFTRDO-IMG2"),
        authority="Central Government (Ministry of Defence), under AFT Act s.40(1)", number="S.R.O. 18(E)", date="21-07-2008 (order and Gazette Extraordinary Pt II s.4 No.13)", date_basis=rd("C9R-RD-AFTRDO-IMG1"),
        commencement=f"on publication in the Official Gazette {rd('C9R-RD-AFTRDO-IMG2')}; masthead date 21-07-2008 {rd('C9R-RD-AFTRDO-IMG1')}",
        raw_shas=["1c6db257efe5ac077d13847177a5c3706375ef92242f1d45d8f2bbabe683e849"], missing="none (NEW: not in any C5/C8 register)",
        route="already held in corpus raw store", auth="register in C5 (AP-C9-02)", verification="HELD_CORPUS_RAW_UNREGISTERED; image-read in C9")
    add(id="I-AFT-SRO9E-2009", priority="3", family="AFT Act 2007", title="Notification S.R.O. 9(E) dated 07-08-2009 establishing the Armed Forces Tribunal with effect from 10-08-2009 (appointed day under s.3(c)), issued under s.4",
        title_basis=rd("C9R-RD-AFTAPPT-IMG"), authority="Central Government (Ministry of Defence)", number="S.R.O. 9(E)", date="07-08-2009 (Gazette Extraordinary Pt II s.4 No.8)", date_basis=rd("C9R-RD-AFTAPPT-IMG"),
        commencement="establishment w.e.f. 10-08-2009 as stated in the notification (this is not the s.1(2) commencement notification)",
        raw_shas=["8d774f1fcc3358e892a288346d2cad361694abec3f4191d35b34156c29425136", "03961b02ab4567b4ad6633fe50f459936b572e2cdfeb0b846f057a49bbb8bf29"],
        missing="none (NEW: not in any C5/C8 register)", route="already held in corpus raw store (two scans)", auth="register in C5 (AP-C9-02)", verification="HELD_CORPUS_RAW_UNREGISTERED; image-read in C9")
    add(id="I-AFT-FIN-2017", priority="3", family="AFT Act 2007", title="The Finance Act, 2017 (No. 7 of 2017) - Part XIV, s.181 (inserting AFT s.9A)", title_basis=rd("C9R-RD-FIN17-03"),
        authority="Parliament", number="Act 7 of 2017", date="31-03-2017 (assent as printed)", date_basis=rd("C9R-RD-FIN17-03"),
        commencement=f"Part XIV comes into force on notified date(s), different dates allowed (s.156) {rd('C9R-RD-FIN17-02')}; compilation: s.9A 'w.e.f. 26-5-2017' {rd('C9R-AFT-05')}; notification NOT HELD",
        raw_shas=["7a5551bab08518a7f52eb60c6cb08dc775726a8b2f5b89369413af771d173766"], missing="Part XIV commencement notification",
        contradictions="C8 recorded 'Finance Act 2017 not held'; C9 finds it in the corpus raw store - correction to C8 D-SSM-057",
        gaps=["G-FIN2017"], route="Act already held (corpus raw); notification: official-source discovery", auth="AP-C9-02 (registration); discovery approval (notification)", verification=f"HELD_CORPUS_RAW_UNREGISTERED; s.181 {rd('C9R-RD-FIN17-01')}")
    add(id="I-AFT-TRA-2021", priority="3", family="AFT Act 2007", title="The Tribunals Reforms Act, 2021 (No. 33 of 2021)", title_basis=rd("C9R-RD-TRA21-IMG"),
        authority="Parliament", number="Act 33 of 2021", date="13-08-2021 (assent; Gazette Extraordinary Pt II s.1 No.45)", date_basis=rd("C9R-RD-TRA21-IMG"),
        commencement=f"s.1(2): 'deemed to have come into force on the 4th April, 2021' {rd('C9R-RD-TRA21-IMG')}",
        raw_shas=["0c2f4e9e023d5d7b72d60797e1df67a7b2d2e340da8fe493a4328940638f0451"], missing="none for text",
        contradictions=f"C8 recorded TRA 2021 'not held' and 'provisions affected unknown'; C9: held in corpus raw store, s.26 amends AFT s.9A {rd('C9R-RD-TRA21-02')}; the held compilation carries no TRA 2021 footnote {rd('C9R-AFT-03')}; PILOT-01 AMD-16 'HELD' claim now has a candidate binary",
        gaps=["G-TRA2021"], route="already held (corpus raw)", auth="AP-C9-02", verification="HELD_CORPUS_RAW_UNREGISTERED; masthead and s.1 image-read in C9")
    add(id="I-AFT-TRA-2026", priority="3", family="AFT Act 2007", title="The Tribunals Reforms Act, 2026 (No. 17 of 2026)", title_basis=rd("C9R-TRA-01"),
        authority="Parliament", number="Act 17 of 2026", date="13-08-2026 (assent; Gazette Extraordinary CG-DL-E-13082026-275447)", date_basis=f"{rd('C9R-TRA-01')}; {rd('C9R-TRA-05')}",
        commencement=f"s.1(2) by notification, different dates for different provisions {rd('C9R-TRA-02')}; compilation: s.9A substituted 'w.e.f. 25-08-2026' {rd('C9R-AFT-06')}; notification(s) NOT HELD",
        source_ids=["C5-SRC-P0-TRA-2026"], raw_shas=["be619533e45739bf8e975bd4b39c826d99e2bc7627942252020360fcc1a63423"], missing="s.1(2) notification(s)",
        gaps=["G-TRA2026-COMM"], route="Act held; notification(s): discovery (egazette 2026)", auth="discovery approval", verification=f"TEXT_LAYER (C8, C9); s.24(1) repeal of TRA 2021 {rd('C9R-TRA-03')}; Sch. II item 9 {rd('C9R-TRA-04')}")
    add(id="I-AFT-PR-2008", priority="3", family="AFT Act 2007", title="The Armed Forces Tribunal (Procedure) Rules, 2008 (S.R.O. 26(E))", title_basis=rd("C9R-RD-AFTPR08-IMG2"),
        authority="Central Government (Ministry of Defence), under AFT Act s.41(2)(f),(g),(k)", number="S.R.O. 26(E)", date="17-09-2008 (notification; Gazette Extraordinary Pt II s.4 No.19, 17-09-2008)", date_basis=f"{rd('C9R-RD-AFTPR08-IMG2')}; {rd('C9R-RD-AFTPR08-IMG1')}",
        commencement="from the date of publication in the Official Gazette (r.1(2)); masthead of the same India Code bundle dated 17-09-2008",
        raw_shas=["590cf7cd393564eacab37566d605357662429f900ea58a96f0ce0e5bb0e0e317"], missing="none for text (C8 recorded derived OCR only)",
        contradictions="C8 recorded 'no held copy'; C9 finds the India Code bundle in the corpus raw store (same bitstream URL as PR #23 ACQ03-033) - correction to C8 D-SSM-061",
        gaps=["G-AFT-PR"], route="already held (corpus raw); PR #23 ACQ03-030 archive copy optional; ACQ03-033 redundant", auth="AP-C9-02", verification="HELD_CORPUS_RAW_UNREGISTERED; r.1 and masthead image-read in C9")
    add(id="I-AFT-PR-AMD-2011", priority="3", family="AFT Act 2007", title="The Armed Forces Tribunal (Procedure) Amendment Rules, 2011 (S.R.O. 05(E))", title_basis=rd("C9R-RD-AFTPR11-IMG2"),
        authority="Central Government (Ministry of Defence), under AFT Act s.41(2)(f),(g),(k)", number="S.R.O. 05(E)", date="29-07-2011 (notification; Gazette Extraordinary Pt II s.4 No.4, 29-07-2011)", date_basis=f"{rd('C9R-RD-AFTPR11-IMG2')}; {rd('C9R-RD-AFTPR11-IMG1')}",
        commencement="on the date of publication in the Official Gazette (r.1(2)); masthead 29-07-2011",
        raw_shas=["fc27032fadfe44fdd20f899612d45b690f469bcdc96463ac8ea4ae9f82e29904"], missing="none", gaps=["G-AFT-PR"],
        route="already held (corpus raw); ACQ03-031/034 redundant", auth="AP-C9-02", verification="HELD_CORPUS_RAW_UNREGISTERED; image-read in C9")
    add(id="I-AFT-PRAC-2009", priority="3", family="AFT Act 2007", title="The Armed Forces Tribunal (Practice) Rules, 2009 (S.R.O. 6(E))", title_basis=rd("C9R-RD-AFTPRAC09-IMG"),
        authority="Central Government (Ministry of Defence), under AFT Act s.41(2)(f),(g),(k)", number="S.R.O. 6(E)", date="11-05-2009 (notification)", date_basis=rd("C9R-RD-AFTPRAC09-IMG"),
        commencement="from the date of publication in the official gazette (r.1(2)); publication date NOT printed on the held page (Gazette Extraordinary Pt II s.4, p.99)",
        raw_shas=["c57b113a310d5ec1a9c06e26a266ef7abf0e039f36cbd83977313bb0790a77ea"], missing="masthead / publication date of the Gazette issue", gaps=["G-AFT-PR"],
        route="already held (corpus raw); ACQ03-032 archive candidate may carry the masthead", auth="AP-C9-02; PR #23 if the masthead is needed", verification="HELD_CORPUS_RAW_UNREGISTERED; image-read in C9")

    # ---------------- Priority 4: BNS/BNSS/BSA and historical codes ----------------
    add(id="I-BNS-2023", priority="4", family="BNS 2023", title="The Bharatiya Nyaya Sanhita, 2023 (Act No. 45 of 2023)", title_basis=rd("C9R-RD-BNS-01"),
        authority="Parliament", number="Act 45 of 2023", date="25-12-2023 (Gazette, per C5-ACQ-20 metadata; not held)", date_basis="C8 D-SSM-063",
        commencement=f"compilation footnote: 01-07-2024 except s.106(2), vide S.O. 850(E) dated 23-02-2024 {rd('C9R-RD-BNS-02')}; notification NOT HELD",
        raw_shas=["d4449e9995b21fd52627811d08f9d21feda6a3678b7e5355b651242d152167f5", "d163e785bfb3783287a641fc81621a6f16583f3435227110e066eb9d12c9d4da"],
        missing="Gazette as enacted (C5-ACQ-20 pinned metadata, no config PR); S.O. 850(E)",
        contradictions="C8 recorded 'no reliable copy at all (derived text only)'; C9 finds the India Code compilation in the corpus raw store - correction to C8 D-SSM-063/064",
        gaps=["G-BNS-ENACT"], route="compilation already held (corpus raw); Gazette via A-C5-1 (new config PR)", auth="AP-C9-02; A-C5-1", verification=f"HELD_CORPUS_RAW_UNREGISTERED (compilation); s.358 {rd('C9R-RD-BNS-03')}")
    add(id="I-BNSS-2023", priority="4", family="BNSS 2023", title="The Bharatiya Nagarik Suraksha Sanhita, 2023 (Act No. 46 of 2023)", title_basis=rd("C9R-BNSS-01"),
        authority="Parliament", number="Act 46 of 2023", date="25-12-2023 (Gazette, per C5-ACQ-03 metadata; not held)", date_basis="C8 D-SSM-066",
        commencement=f"compilation footnote: 01-07-2024 except the First Schedule entry relating to s.106(2), vide S.O. 848(E) dated 23-02-2024 {rd('C9R-BNSS-02')}; notification NOT HELD",
        source_ids=["C5-SRC-P0-BNSS-2023-INDIACODE"], raw_shas=["572c79880b9f8effc8fa6e39b864101835a0fb5d85b194b90a99d170121a0562"], missing="Gazette as enacted (C5-ACQ-03); S.O. 848(E)",
        gaps=["G-BNSS-ENACT"], route="A-C5-1 (new config PR)", auth="A-C5-1", verification=f"COMPILATION; s.531 {rd('C9R-BNSS-03')}")
    add(id="I-BSA-2023", priority="4", family="BSA 2023", title="The Bharatiya Sakshya Adhiniyam, 2023 (Act No. 47 of 2023)", title_basis=rd("C9R-BSA-01"),
        authority="Parliament", number="Act 47 of 2023", date="25-12-2023 (Gazette, per C5-ACQ-04 metadata; not held)", date_basis="C8 D-SSM-069",
        commencement=f"compilation footnote: 01-07-2024 vide S.O. 849(E) dated 23-02-2024 {rd('C9R-BSA-02')}; notification NOT HELD",
        source_ids=["C5-SRC-P0-BSA-2023-INDIACODE"], raw_shas=["554b2b4ae3d9f09bf31e6e1ba2b2cb8a4e7f4f5ffd6f3156736752cbbce116d5"], missing="Gazette as enacted (C5-ACQ-04); S.O. 849(E)",
        contradictions="C-07 adviser question (Army Act s.133 names the Indian Evidence Act 1872)", gaps=["G-BSA-ENACT"], route="A-C5-1 (new config PR)", auth="A-C5-1", verification=f"COMPILATION; s.170 {rd('C9R-BSA-03')}")
    for iid, so, act, rid, cand, gap in [("I-BNS-COMM-SO850E", "S.O. 850(E)", "BNS", "C9R-RD-BNS-02", "C5C-023 (in.gazette.central.e.2024-02-24.252353)", "G-SAN-COMM"),
                                         ("I-BNSS-COMM-SO848E", "S.O. 848(E)", "BNSS", "C9R-BNSS-02", "C5C-021 (in.gazette.central.e.2024-02-24.252354)", "G-SAN-COMM"),
                                         ("I-BSA-COMM-SO849E", "S.O. 849(E)", "BSA", "C9R-BSA-02", "C5C-022 (in.gazette.central.e.2024-02-24.252352)", "G-SAN-COMM")]:
        add(id=iid, priority="4", family=f"{act} 2023", title=f"Notification {so} dated 23-02-2024 appointing the commencement of the {act} (as named in the compilation footnote)", title_basis=rd(rid),
            authority="Central Government (Ministry of Home Affairs, per compilation)", number=so, date="23-02-2024 (compilation footnote)", date_basis=rd(rid),
            commencement="n/a (commencement instrument); exceptions as printed in the footnote", missing="the notification",
            contradictions="archive.org candidate items are dated 24-02-2024 (item date) while the footnotes date the S.O.s 23-02-2024; which archive item carries which S.O. is not established (metadata only) - not a contradiction until held",
            gaps=[gap], route=f"C5-ACQ-05 {cand} (archive metadata pin; no config PR)", auth="A-C5-1 + new config PR", verification="NOT_HELD")
    add(id="I-IPC-1860", priority="4", family="Historical codes", title="The Indian Penal Code (45 of 1860) - repealed by BNS s.358(1)", title_basis=f"{rd('C9R-RD-IPC-01')}; repeal {rd('C9R-RD-BNS-03')}",
        authority="Legislative Council (historical)", number="Act 45 of 1860", date="1860 (crawl record year only)", date_basis="raw-data data/manifest.csv#act-ipc-1860",
        commencement="not evidenced from held primary documents", raw_shas=["fa8878e0208e0942e51bcf7e437efa7b6d25baecb04f4cd83da30df44c977f85"],
        missing="text as last amended before repeal with as-on date (the India Code Repeal Acts rendering prints no as-on date)",
        contradictions="C8 recorded 'no copy of any kind'; the corpus raw store holds the India Code Repeal Acts rendering (PROGRESS.md 2026-11-21) - correction to C8 D-SSM-072",
        gaps=["G-IPC"], route="held rendering (corpus raw); authoritative as-at-repeal text: discovery", auth="AP-C9-02; discovery approval", verification="HELD_CORPUS_RAW_UNREGISTERED (rendering, edition unknown)")
    add(id="I-CRPC-1973", priority="4", family="Historical codes", title="The Code of Criminal Procedure, 1973 (2 of 1974) - repealed by BNSS s.531(1)", title_basis=rd("C9R-BNSS-03"),
        authority="Parliament", number="Act 2 of 1974", date="not evidenced", date_basis="BNSS s.531(1) cites '(2 of 1974)'",
        commencement="not evidenced", raw_shas=["865cc3e1989536882c97d58cd16581e3409745ad53e6f359853bf7472709194b", "982059ca1f87197210a112b9120438dc79ae5bcccb80c94a39522586578214a3"],
        missing="text as last amended before repeal (India Code copy is a 1974 print; CRPF consolidated copy's latest amendment is 2014 per PROGRESS.md 2026-11-21)",
        contradictions="C8 recorded 'derived text only'; two copies are in the corpus raw store - correction to C8 D-SSM-074/075",
        gaps=["G-CRPC"], route="discovery for an as-at-30-06-2024 official text", auth="discovery approval", verification="HELD_CORPUS_RAW_UNREGISTERED (renderings; not as at repeal)")
    add(id="I-IEA-1872", priority="4", family="Historical codes", title="The Indian Evidence Act, 1872 (1 of 1872) - repealed by BSA s.170(1)", title_basis=f"{rd('C9R-RD-IEA-01')}; {rd('C9R-BSA-03')}",
        authority="Legislative Council (historical)", number="Act 1 of 1872", date="s.1: in force 01-09-1872 as printed in the rendering", date_basis=rd("C9R-RD-IEA-01"),
        commencement="01-09-1872 as printed in the rendering (rendering, not the enacted text)", raw_shas=["06729a1f84e186ae953798766696a736c344dcbd94da2b0cc2a474e7859378ce"],
        missing="text as last amended before repeal with as-on date", contradictions="C8 recorded 'derived text only'; corpus raw store holds the India Code rendering - correction to C8 D-SSM-077/078",
        gaps=["G-IEA"], route="discovery for as-at-repeal text", auth="discovery approval", verification="HELD_CORPUS_RAW_UNREGISTERED (rendering)")

    # ---------------- Priority 5: pension instruments and judgments ----------------
    for key, iid, gap in [("PRA2008-PT1", "I-PRA-2008-PT1", "G-PRA-PT1"), ("PRA2008-PT2", "I-PRA-2008-PT2", "G-PRA-PT2"), ("PRA1961", "I-PRA-1961", "G-PRA1961"),
                          ("ER1982", "I-ER-1982", "G-ER1982"), ("ER2008", "I-ER-2008", "G-ER2008"), ("ER2023-APPX-I", "I-ER-2023", "G-ER2023"),
                          ("GMO2023-APPX-II", "I-GMO-2023", "G-GMO2023"), ("GMO-2002-2008", "I-GMO-2002-2008", "G-GMO-0208"), ("CIRC-PRA-ER", "I-CIRC-PRA-ER", "G-PEN-CIRC"),
                          ("CIRC-BROADBAND-2023", "I-CIRC-BROADBAND-2023", "G-PEN-CIRC"), ("CIRC-OROP-CORR-2025", "I-CIRC-OROP-2025", "G-PEN-CIRC")]:
        p = ctx.pension[key]
        shas = [s for s in p["sha256"].split(";") if s]
        extra_held = []
        if key == "ER2023-APPX-I":
            extra_held = [ctx.pension["ER2023-HELD-INCOMPLETE"]["sha256"]]
        in_pr9 = key in ("ER2023-APPX-I", "GMO2023-APPX-II")
        add(id=iid, priority="5", family="Pension instruments", title=p["document"] + " (title as recorded in registers; no held complete copy)", title_basis=f"C8 pension_source_coverage.csv#{key}",
            authority="Ministry of Defence (Department of Ex-Servicemen Welfare) (register)", number="as recorded", date="as recorded in registers (not verified on an instrument)", date_basis=f"C8 pension_source_coverage.csv#{key}",
            commencement="not evidenced", held_shas=shas + extra_held, missing=f"{p['state']}; {p['blockers'][:200]}",
            contradictions=("C9: PR #9 local ref 97933ccf DOES list the GMO 2023 URL (desw.gov.in/sites/default/files/2026-10/GMO%202023.pdf, byte size only, no hash) - correction to C8 3a ('not in PR #9')" if key == "GMO2023-APPX-II" else "held 13 MB ER-2023 copy (29f6fa2c) matches the PR #9 '-alt' URL note sha prefix; incomplete (GMO absent)" if key == "ER2023-APPX-I" else "none recorded"),
            gaps=[gap], route=p["acquisition_route"] + ("; listed in PR #9 desw (no integrity pin)" if in_pr9 else ""),
            auth="A-C5-2 + DESW allow-list + readable robots.txt (currently 403, fail-closed)" if p["acquisition_route"].startswith("C5-ACQ") else "discovery approval / custodian (A-C5-3)",
            verification=p["state"])
    for key, iid, gap in [("J-DHARAMVIR-2013", "I-J-DHARAMVIR-2013", "G-J-SC-2013-DHARAMVIR"), ("J-RAJBIR-2015", "I-J-RAJBIR-2015", "G-J-SC-2015-RAJBIR"),
                          ("J-NSYADAV-2019", "I-J-NSYADAV-2019", "G-J-SC-2019-NS-YADAV"), ("J-RAMAVTAR-2014", "I-J-RAMAVTAR-2014", "G-JM-DCLR-SC-2014-A08"),
                          ("J-GIRISH-FEB-2026", "I-J-GIRISH-FEB-2026", "G-J-SC-2026-GIRISH-FEB"), ("J-GIRISH-OCT-2026", "I-J-GIRISH-OCT-2026", "G-JM-DCLR-SC-2026-008"),
                          ("J-MULLIKOTE-2026", "I-J-MULLIKOTE-2026", "G-J-SC-2026-MULLIKOTE")]:
        p = ctx.pension[key]
        shas = [s for s in p["sha256"].split(";") if s]
        add(id=iid, priority="5", family="Judgments (pension)", title=p["document"] + " (as recorded; see C8-EVIDENCE SC-T2 for page checks)", title_basis=f"C8 pension_source_coverage.csv#{key}",
            authority="Supreme Court of India", number="as recorded", date="as recorded", date_basis=f"C8 pension_source_coverage.csv#{key}", commencement="n/a",
            source_ids=[p["c5_source_id"]] if p["c5_source_id"] and p["c5_source_id"] != "(none)" else [], held_shas=[], missing=p["state"],
            gaps=[gap], route=p["acquisition_route"], auth=("owner decision P-D3 / AUTH-LEDGER tranche 2" if shas else "official SC copy to locate (discovery)"),
            verification=p["state"])
    add(id="I-J-ISAAC-2026", priority="5", family="Judgments (pension)", title="Union of India v Col N.C. Isaac (Retd), 2026 INSC 993 (15-09-2026) (as recorded)", title_basis="C8 source_to_record_gap_matrix.csv#G-J-SC-2026-ISAAC",
        authority="Supreme Court of India", number="2026 INSC 993", date="15-09-2026 (register)", date_basis="register", commencement="n/a", missing="see C8 review RR-06 (held copy 3f49a314 used for para 39(iii))",
        gaps=["G-J-SC-2026-ISAAC"], route="provenance registration", auth="owner decision (AUTH-LEDGER)", verification="HELD (C8 review read p.93)")

    # ---------------- Related statutory instruments ----------------
    add(id="I-CCCM-1978", priority="6", family="CCCM Rules", title="Criminal Courts and Court-martial (Adjustment of Jurisdiction) Rules, 1978 (S.O. 488) (title as recorded; not held)", title_basis="ACQ-01/batches.json#rules-adjustment-jurisdiction-1978-so-488",
        authority="Central Government (Ministry of Home Affairs) (register)", number="S.O. 488", date="09-02-1978 (register); Gazette 25-02-1978 Pt II s.3(ii) p.525 (register)", date_basis="ACQ-01 batches.json",
        commencement="not evidenced", missing="the instrument", gaps=["G-CCCM"], route="PR #8 rules-adjustment-jurisdiction-1978-so-488 (archive md5 91b0dd7a...)",
        auth="PR #8 execution approval (ACQ-01 B2 authorised)", verification="NOT_HELD")
    add(id="I-CCCM-SO4010-1986", priority="6", family="CCCM Rules", title="Criminal Courts and Court-Martial (Adjustment of Jurisdiction) Amendment Rules, 1986 - MHA Notification S.O. 4010", title_basis=rd("C9R-RS-01"),
        authority="Ministry of Home Affairs", number="S.O. 4010", date="DISPUTED_PRESERVE_BOTH: '6th December, 1986' (Rajya Sabha papers-laid record, C9 image read) vs '24-11-1986' notification date with Gazette 06-12-1986 (PILOT-01 T5-02 discovery reading of archive item, not held)", date_basis=f"{rd('C9R-RS-01')}; PILOT-01/registers/source_discovery_2026-11-22.csv#T5-02",
        commencement="not evidenced", source_ids=["C5-SRC-P2-RS-PAPERS-LAID-1987"], missing="the notification (PR #8 notif-adjustment-jurisdiction-amdt-so-4010-1986, md5 c5eaada9...)",
        contradictions="C5 review RV-01 transcribed the RS page as 'dated 8 Dec 1986'; the C9 page-image read gives '6th December, 1986' (reading discrepancy, preserve; human re-check)",
        gaps=["G-CCCM"], route="PR #8 (archive item in.gazette.central.w.1986-12-06.32435)", auth="PR #8 execution approval (ACQ-01 B2 authorised)", verification="NOT_HELD; parliamentary record held")
    add(id="I-DPP-1950", priority="6", family="DPP Act 1950", title="The Army and Air Force (Disposal of Private Property) Act, 1950 (Act No. 40 of 1950)", title_basis=rd("C9R-RD-DPP-02", "2"),
        authority="Parliament", number="Act 40 of 1950", date="28-04-1950 (as printed in compilation)", date_basis="raw-data compilation p.4 (text layer)",
        commencement=f"compilation footnote: 22-07-1950 vide S.R.O. 123 dated 22-07-1950 {rd('C9R-RD-DPP-03')}; notification not held",
        raw_shas=["0884f3b50114c71f98f9aa0dfea43aaa0d1b0eee3da276591f6d6e2051ecdfca", "6ca297a1972ed35c400caead51d2681340064dcd967cee7aeb5f8e91f322a126", "d969593bbb689144e39a406cab3d6fa806216438871ddf6321ba084e24c9b203"],
        missing="Gazette as enacted; S.R.O. 123/1950; Amendment Act 2000 (31 of 2000 per compilation list)",
        contradictions="C8 recorded 'Principal Act: no copy, India Code blocked'; the corpus raw store holds the India Code compilation (and the 1953 Rules) from the approved 2026-11-21 run - correction to C8 D-SSM-084",
        gaps=["G-DPP"], route="compilation held (corpus raw)", auth="AP-C9-02", verification="HELD_CORPUS_RAW_UNREGISTERED (compilation)")
    add(id="I-DPP-AMD-2000", priority="6", family="DPP Act 1950", title="The Army and Air Force (Disposal of Private Property) Amendment Act, 2000 (31 of 2000) (as listed in compilation)", title_basis=rd("C9R-RD-DPP-02"),
        authority="Parliament", number="Act 31 of 2000 (compilation list)", date="not evidenced (archive items dated 2000-08-25 / 2000 per C5C-026/027)", date_basis="C8 D-SSM-085/086",
        commencement="not evidenced", missing="the Act (two unpinned archive identifiers)", gaps=["G-DPP"], route="C5-ACQ-21 (P-C7-02-META metadata pin, then A-C5-1)",
        auth="P-C7-02-META + A-C5-1", verification="NOT_HELD")
    add(id="I-AFA-1950", priority="6", family="Air Force Act 1950", title="The Air Force Act, 1950 (Act No. 45 of 1950)", title_basis=rd("C9R-RD-AFA-01"), authority="Parliament", number="Act 45 of 1950",
        date="not evidenced here", date_basis="compilation", commencement="not evidenced", raw_shas=["ef50375ea0550ddc1e6414c45bd9403d3842aa395a297e71e2e627403632ebd0", "0ccc80026e30a5a50ee3b29b3b1e4bf43566509e745878670b1e41d414110bcd"],
        missing="Gazette as enacted", contradictions="C8 recorded 'derived text only'; compilation in corpus raw store", gaps=["G-AFA"], route="compilation held; Gazette: discovery", auth="AP-C9-02; discovery approval", verification="HELD_CORPUS_RAW_UNREGISTERED (compilation as on 21-07-2025)")
    add(id="I-NA-1957", priority="6", family="Navy Act 1957", title="The Navy Act, 1957 (Act No. 62 of 1957)", title_basis=rd("C9R-RD-NA-01"), authority="Parliament", number="Act 62 of 1957",
        date="not evidenced here", date_basis="compilation", commencement="not evidenced", raw_shas=["db6d2b3ef1e60d95f4d8127730430a01a3aab39637d88a39901aa20142399083", "ac7acfc758fa359c7dcaaf1faa5384c92024e3d607f46cb255faf29ba7e74f31"],
        missing="Gazette as enacted", contradictions="C8 recorded 'derived text only'; compilation in corpus raw store", gaps=["G-NAVY"], route="compilation held; Gazette: discovery", auth="AP-C9-02; discovery approval", verification="HELD_CORPUS_RAW_UNREGISTERED (compilation as on 01-06-2026)")
    add(id="I-ISO-2023", priority="6", family="ISO Act 2023", title="Inter-Services Organisations (Command, Control and Discipline) Act 2023 and Rules 2025 (as recorded; not held)", title_basis="C8 D-SSM-090",
        authority="Parliament / Central Government", number="not evidenced", date="not evidenced", date_basis="register", commencement="not evidenced", missing="Act and Rules (not searched)",
        gaps=["G-ISO"], route="official-source discovery", auth="discovery approval", verification="NOT_HELD")
    return I


# ----------------------------------------------------------------------------------------------------------------
def build_acquisition(ctx, uniq, inst_index):
    rows = []
    n = [0]

    def add(**k):
        n[0] += 1
        k["acq_row_id"] = f"C9-ACQ-{n[0]:03d}"
        rows.append(k)

    ar_pins = collections.defaultdict(list)
    acq03_ar = collections.defaultdict(list)
    for intro, (skey, doc), e in uniq:
        p = e["row"]
        md5 = p["expected_md5"] or p["md5_in_note"]
        nbytes = p["expected_bytes"] or p["bytes_in_note"]
        held = ctx.held_by_md5.get(md5) if md5 else None
        rawh = ctx.raw_by_url.get(p["url"])
        held_state, held_ev = "NOT_HELD", ""
        if held:
            held_state = "HELD_RESEARCH_COPY_MD5_IDENTICAL"
            held_ev = f"{held['held_path']} sha256 {held['rehash_sha256']} md5 {md5} (re-hash {held['hash_check']})"
            arid = ar_id_for_sha(ctx, held["rehash_sha256"])
            if arid:
                ar_pins[arid].append(f"{intro} {doc}")
        elif rawh:
            held_state = "HELD_CORPUS_RAW_SAME_URL"
            held_ev = f"raw-data@{rawh['rawdata_commit'][:8]}:{rawh['raw_path']} (same India Code bitstream URL; fetched {rawh['retrieved_at']})"
        elif p["listing_md5"] or skey == "official_instruments":
            held_state = "HELD_SERVED_COPY_NOT_COMPARABLE" if skey == "official_instruments" else "NOT_HELD"
            if skey == "official_instruments":
                c = {"act-air-force-army-laws-amendment-1975": "C5-SRC-P0-AA-AMD-ACT13-1975~C1 sha256 8358d2b3...", "act-army-amendment-1992": "C5-SRC-P0-AA-AMD-ACT37-1992~C1 sha256 f11d443e..."}.get(doc, "")
                held_ev = f"{c} (India Code watermarks served PDFs; listing md5 is not comparable)"
        m = re.search(r"closes (AR-\d{3})", p["note"])
        if m and skey == "archive_acq03":
            acq03_ar[m.group(1)].append(f"{intro} {doc}")
        if intro.startswith("staging"):
            state = "ALREADY_FETCHED_STAGING_SOURCE"
        elif held_state == "HELD_CORPUS_RAW_SAME_URL":
            state = "ALREADY_HELD (corpus raw store; pin redundant)"
        elif intro.startswith("PR #8"):
            state = "AUTHORISED_ROUTE_PENDING_EXECUTION (PR #8)" + ("; research copy already held" if held else "")
        elif intro.startswith("PR #9"):
            state = "BLOCKED (robots 403) / IN_PENDING_BRANCH (PR #9, no integrity pin)"
        else:
            state = f"IN_PENDING_BRANCH ({intro})" + ("; research copy already held" if held else "")
        approval = {"PR #8 (ACQ-01)": "ACQ-01 B1/B2/B6 owner-authorised 2026-11-22 (PR #8 branch PROGRESS.md); download awaits PR #8 approval and a logged download run",
                    "PR #17 (ACQ-02)": "none (PR #17 config approval and separate ACQ-02 download approval required)",
                    "PR #23 (ACQ-03)": "none (ACQ-03/APPROVAL_REQUEST.md: config PR, download run per source, ACQ03-016 decision)",
                    "PR #9 (DESW allow-list)": "none ('B4, not authorised for download'; A-C5-2)",
                    "staging (v2.5-staging)": "earlier approved run (official_copies, 2026-11-21)"}[intro]
        add(required_document=p["title"], doc_id=doc, source_key=skey, reconciliation_state=state, held_state=held_state, held_evidence=held_ev,
            pending_branch=intro, branch_ref_commit=e["commits"][intro][:12], present_in="; ".join(e["present_in"]), url=p["url"],
            pinned_md5=md5 or (f"listing {p['listing_md5']} (not enforced)" if p["listing_md5"] else ""), pinned_bytes=nbytes or p["listing_bytes"],
            existing_approval=approval, outstanding_authorisation="" if intro.startswith("staging") else ("PR #8 approval + download-run approval" if intro.startswith("PR #8") else approval),
            evidence=f"tools/inputs/branch_pins.csv#{skey}/{doc} (git show {p['ref']}@{e['commits'][intro][:8]}:config/sources.yaml)")

    # C5 acquisition register items not configured in any PR
    c602_by = collections.defaultdict(list)
    for r in ctx.c602:
        c602_by[r["acq_c5_id"]].append(r)
    for acq_id, reg in sorted(ctx.acqreg.items(), key=lambda kv: int(kv[1]["rank"])):
        cands = c602_by.get(acq_id) or [None]
        for c in cands:
            title = c["publication"] if c else reg["title"]
            state, held_state, held_ev = "PINNED_ARCHIVE_METADATA (no config PR)", "NOT_HELD", ""
            if acq_id == "C5-ACQ-02":
                state = "ALREADY_HELD (corpus raw store India Code Gazette scan); archive pin optional"
                held_state = "HELD_CORPUS_RAW"
                held_ev = "raw-data 338d43ad... (Gazette Extraordinary No.66, 28-12-2007; C9R-RD-AFT07-IMG)"
            elif acq_id in ("C5-ACQ-07", "C5-ACQ-08", "C5-ACQ-10", "C5-ACQ-11"):
                state = "BLOCKED (desw.gov.in robots.txt 403, fail-closed; not in PR #9)"
            elif acq_id == "C5-ACQ-09":
                state = "BLOCKED (robots 403) / IN_PENDING_BRANCH (PR #9 lists URL; bytes only, no hash)"
                held_state = "HELD_INCOMPLETE_OTHER_COPY"
                held_ev = "29f6fa2c... 13 MB ER-2023 copy (GMO absent)"
            elif acq_id in ("C5-ACQ-23", "C5-ACQ-24", "C5-ACQ-25"):
                state = "BLOCKED (India Code host BLOCKED_ACCESS this cycle; robots policy decision A-C5-6)"
            elif acq_id in ("C5-ACQ-12", "C5-ACQ-13", "C5-ACQ-14", "C5-ACQ-15"):
                state = "NEEDS_CUSTODIAN_CORRESPONDENCE (A-C5-3; scope P-C6-04-SCOPE for AOs)"
            elif acq_id == "C5-ACQ-26":
                state = "NEEDS_OWNER_DECISION (archived copy of possibly restricted publication)"
            elif acq_id == "C5-ACQ-21":
                state = "NEEDS_METADATA_PIN (P-C7-02-META) then A-C5-1"
            elif acq_id in ("C5-ACQ-17", "C5-ACQ-18") or (c is None and "md5" not in reg["integrity_pin"]):
                state = "LOCATED_NOT_PINNED (metadata md5 to record)" if acq_id in ("C5-ACQ-17", "C5-ACQ-18", "C5-ACQ-22") else state
            pin = f"{c['archive_identifier']}/{c['file_name']}" if c else reg["exact_location"][:160]
            md5 = c["expected_md5"] if c else (re.search(r"md5 ([0-9a-f]{32})", reg["integrity_pin"]).group(1) if re.search(r"md5 ([0-9a-f]{32})", reg["integrity_pin"]) else "")
            add(required_document=title, doc_id=(c["candidate_id"] if c else acq_id), source_key="(none: C5 acquisition register)", reconciliation_state=state,
                held_state=held_state, held_evidence=held_ev, pending_branch="", branch_ref_commit="", present_in="", url=pin,
                pinned_md5=md5, pinned_bytes=(c["expected_bytes"] if c else ""), existing_approval=f"none ({reg['approval_state']})",
                outstanding_authorisation=reg["required_approval"][:160], evidence=f"SOURCE-LIBRARY-C5/registers/acquisition_register.csv#{acq_id}" + (f"; C8 c6_02_readiness.csv#{c['candidate_id']}" if c else ""))

    # Items held in the corpus raw store that C8 treated as gaps, and no-candidate discovery items
    for doc, sha, state_note, evidence in [
        ("AFT (Procedure) Rules 2008 (S.R.O. 26(E))", "590cf7cd393564eacab37566d605357662429f900ea58a96f0ce0e5bb0e0e317", "ALREADY_HELD (corpus raw); PR #23 ACQ03-033 redundant", "C9R-RD-AFTPR08-IMG1/IMG2"),
        ("AFT (Procedure) Amendment Rules 2011 (S.R.O. 05(E))", "fc27032fadfe44fdd20f899612d45b690f469bcdc96463ac8ea4ae9f82e29904", "ALREADY_HELD (corpus raw); PR #23 ACQ03-034 redundant", "C9R-RD-AFTPR11-IMG1/IMG2"),
        ("AFT (Practice) Rules 2009 (S.R.O. 6(E))", "c57b113a310d5ec1a9c06e26a266ef7abf0e039f36cbd83977313bb0790a77ea", "ALREADY_HELD (corpus raw); PR #23 ACQ03-035 redundant; masthead not on held page", "C9R-RD-AFTPRAC09-IMG"),
        ("AFT Act (Removal of Difficulties) Order 2008 (S.R.O. 18(E))", "1c6db257efe5ac077d13847177a5c3706375ef92242f1d45d8f2bbabe683e849", "ALREADY_HELD (corpus raw); not in any register", "C9R-RD-AFTRDO-IMG1/IMG2"),
        ("S.R.O. 9(E)/2009 AFT establishment / appointed day", "8d774f1fcc3358e892a288346d2cad361694abec3f4191d35b34156c29425136", "ALREADY_HELD (corpus raw); not in any register", "C9R-RD-AFTAPPT-IMG"),
        ("Finance Act 2017 (7 of 2017)", "7a5551bab08518a7f52eb60c6cb08dc775726a8b2f5b89369413af771d173766", "ALREADY_HELD (corpus raw); C8 'discovery required' superseded", "C9R-RD-FIN17-01/02/03"),
        ("Tribunals Reforms Act 2021 (33 of 2021)", "0c2f4e9e023d5d7b72d60797e1df67a7b2d2e340da8fe493a4328940638f0451", "ALREADY_HELD (corpus raw); C8 'discovery required' superseded", "C9R-RD-TRA21-IMG; C9R-RD-TRA21-02"),
        ("BNS 2023 India Code compilation", "d4449e9995b21fd52627811d08f9d21feda6a3678b7e5355b651242d152167f5", "ALREADY_HELD (corpus raw) - compilation only; Gazette still C5-ACQ-20", "C9R-RD-BNS-01..03"),
        ("DPP Act 1950 India Code compilation (+ Hindi, 1953 Rules)", "0884f3b50114c71f98f9aa0dfea43aaa0d1b0eee3da276591f6d6e2051ecdfca", "ALREADY_HELD (corpus raw) - compilation only", "C9R-RD-DPP-02/03"),
        ("IPC 1860 India Code Repeal Acts rendering", "fa8878e0208e0942e51bcf7e437efa7b6d25baecb04f4cd83da30df44c977f85", "ALREADY_HELD (corpus raw) - rendering, edition unknown", "C9R-RD-IPC-01"),
        ("Indian Evidence Act 1872 India Code rendering", "06729a1f84e186ae953798766696a736c344dcbd94da2b0cc2a474e7859378ce", "ALREADY_HELD (corpus raw) - rendering", "C9R-RD-IEA-01"),
        ("CrPC 1973 India Code copy (1974 print)", "865cc3e1989536882c97d58cd16581e3409745ad53e6f359853bf7472709194b", "ALREADY_HELD (corpus raw) - not as at repeal", "raw-data manifest"),
        ("Air Force Act 1950 India Code compilation", "ef50375ea0550ddc1e6414c45bd9403d3842aa395a297e71e2e627403632ebd0", "ALREADY_HELD (corpus raw) - compilation only", "C9R-RD-AFA-01"),
        ("Navy Act 1957 India Code compilation", "db6d2b3ef1e60d95f4d8127730430a01a3aab39637d88a39901aa20142399083", "ALREADY_HELD (corpus raw) - compilation only", "C9R-RD-NA-01"),
    ]:
        r = ctx.raw_by_sha[sha]
        add(required_document=doc, doc_id=r["doc_id"] or r["title"], source_key="corpus raw store", reconciliation_state=state_note, held_state="HELD_CORPUS_RAW",
            held_evidence=f"raw-data@{r['rawdata_commit'][:8]}:{r['raw_path']} retrieved {r['retrieved_at']}", pending_branch="", branch_ref_commit="", present_in="",
            url=r["source_url"], pinned_md5="", pinned_bytes=r["bytes"], existing_approval="India Code download run (approved) 2026-11-21 (PROGRESS.md)",
            outstanding_authorisation="owner decision: C5 registration / AUTH-LEDGER rule-1 review (AP-C9-02); no download", evidence=f"tools/inputs/rawdata_statutory_holdings.csv#{sha[:12]}; {evidence}")
    for doc, state, auth, ev in [
        ("AFT Act commencement notification S.O. 14(E) of 13-06-2008", "NEEDS_OFFICIAL_SOURCE_DISCOVERY (in no register)", "discovery approval (egazette; Indian-network run)", "C9R-AFT-04"),
        ("TRA 2026 s.1(2) commencement notification(s)", "NEEDS_OFFICIAL_SOURCE_DISCOVERY", "discovery approval", "C9R-TRA-02; C9R-AFT-06"),
        ("Finance Act 2017 Part XIV commencement notification (s.156)", "NEEDS_OFFICIAL_SOURCE_DISCOVERY", "discovery approval", "C9R-RD-FIN17-02; C9R-AFT-05"),
        ("Notification S.O. 3912(E) of 30-10-2019", "NEEDS_OFFICIAL_SOURCE_DISCOVERY (egazette TLS failure; archive.org not searched)", "discovery approval", "C9R-AA-08; ACQ-C3-05"),
        ("Repealing and Amending Act 1957 (36 of 1957)", "NEEDS_OFFICIAL_SOURCE_DISCOVERY", "discovery approval", "C9R-AA-12; ACQ-C3-06"),
        ("Repealing and Amending Act 1960 (58 of 1960)", "NEEDS_OFFICIAL_SOURCE_DISCOVERY", "discovery approval", "C9R-A19-03"),
        ("Army Rules E-7 (7(E)) of 1960 (AR-001)", "NEEDS_CUSTODIAN_CORRESPONDENCE or Indian-network egazette (no lawful online source known)", "A-C5-3 or discovery approval", "C8 D-AMC-AR-001; ACQ03-026"),
        ("Army Rules S.R.O. 258 of 2002 (AR-030)", "NEEDS_CUSTODIAN_CORRESPONDENCE or Indian-network egazette", "A-C5-3 or discovery approval", "C8 D-AMC-AR-030; ACQ03-028"),
        ("'S.R.O. 34 dated 5-6-1963' listed in Gazette NOTEs (if a distinct instrument)", "NEEDS_OFFICIAL_SOURCE_DISCOVERY (identity unresolved, C8-CR-02)", "discovery approval", "C8-EVIDENCE contradiction_register_c8.csv#C8-CR-02"),
        ("Post-BNSS rules corresponding to the 1978 Adjustment of Jurisdiction Rules (if any)", "NEEDS_OFFICIAL_SOURCE_DISCOVERY", "discovery approval", "ACQ-01/EXECUTION_PLAN.md B2 gap; BNSS s.531(2)(b)"),
        ("IPC/CrPC/IEA official text as at 30-06-2024", "NEEDS_OFFICIAL_SOURCE_DISCOVERY", "discovery approval", "G-IPC/G-CRPC/G-IEA"),
        ("Air Force Act 1950 and Navy Act 1957 Gazettes as enacted", "NEEDS_OFFICIAL_SOURCE_DISCOVERY", "discovery approval", "G-AFA/G-NAVY"),
        ("ISO (Command, Control and Discipline) Act 2023 and Rules 2025", "NEEDS_OFFICIAL_SOURCE_DISCOVERY (not searched)", "discovery approval", "G-ISO"),
        ("Army Act notifications (s.4, s.9 etc.)", "NEEDS_OFFICIAL_SOURCE_DISCOVERY (phase 6)", "discovery approval", "C8 D-SSM-016"),
    ]:
        add(required_document=doc, doc_id="", source_key="(none)", reconciliation_state=state, held_state="NOT_HELD", held_evidence="", pending_branch="", branch_ref_commit="",
            present_in="", url="", pinned_md5="", pinned_bytes="", existing_approval="none", outstanding_authorisation=auth, evidence=ev)
    return rows, ar_pins, acq03_ar


# ----------------------------------------------------------------------------------------------------------------
AA_INST = {"D-AMC-AA-00": "I-AA-SRO120-1950", "D-AMC-AA-01": "I-AA-ACT19-1955", "D-AMC-AA-02": "I-AA-ALO3-1956", "D-AMC-AA-03": "I-AA-RAA-1960",
           "D-AMC-AA-04": "I-AA-RAA-1974", "D-AMC-AA-05": "I-AA-ORD3-1975", "D-AMC-AA-06": "I-AA-ACT13-1975", "D-AMC-AA-07": "I-AA-ACT20-1983",
           "D-AMC-AA-09": "I-AA-RAA-2001", "D-AMC-AA-10": "I-AA-RAA2-2017", "D-AMC-AA-11": "", "D-AMC-AA-12": "", "D-AMC-AA-13": "I-AA-POST1992",
           "D-AMC-AA-C3-01": "I-AA-ALO3-1956", "D-AMC-AA-C3-02": "I-AA-SO3912E-2019", "D-AMC-AA-C3-03": "I-AA-RAA-1957", "D-AMC-AA-C3-04": "", "D-AMC-AA-C3-05": "I-AA-1950",
           "D-AMC-AFT-00": "I-AFT-SO14E-2008", "D-AMC-AFT-01": "I-AFT-FIN-2017", "D-AMC-AFT-02": "I-AFT-TRA-2021", "D-AMC-AFT-03": "I-AFT-TRA-2026", "D-AMC-AFT-04": "I-AFT-TRA-2026",
           "D-AMC-AFT-05": "I-AFT-PR-2008", "D-AMC-BNS-COMM": "I-BNS-COMM-SO850E", "D-AMC-BNSS-COMM": "I-BNSS-COMM-SO848E", "D-AMC-BSA-COMM": "I-BSA-COMM-SO849E",
           "D-AMC-BNSS-REPEAL": "I-BNSS-2023", "D-AMC-BSA-REPEAL": "I-BSA-2023", "D-AMC-BNS-REPEAL": "I-BNS-2023"}
TARGET = {"Army Rules 1954": "I-AR-1954", "Army Act 1950": "I-AA-1950"}


def build_graph(ctx):
    rd = ctx.rd
    rows = []
    for r in ctx.amc:
        rid = r["row_id"]
        fam = r["instrument_family"]
        target = TARGET.get(fam, "")
        if rid.startswith("D-AMC-AFT"):
            target = "I-AFT-2007"
        if rid.startswith("D-AMC-BNS") or rid.startswith("D-AMC-BNSS") or rid.startswith("D-AMC-BSA"):
            target = {"D-AMC-BNS-COMM": "I-BNS-2023", "D-AMC-BNSS-COMM": "I-BNSS-2023", "D-AMC-BSA-COMM": "I-BSA-2023",
                      "D-AMC-BNSS-REPEAL": "I-CRPC-1973", "D-AMC-BSA-REPEAL": "I-IEA-1872", "D-AMC-BNS-REPEAL": "I-IPC-1860"}[rid]
        m = re.match(r"D-AMC-(AR-(\d{3}))$", rid)
        amending = f"I-AR-AMD-{m.group(2)}" if m and m.group(1) != "AR-000" else ("I-AR-1954" if rid == "D-AMC-AR-000" else AA_INST.get(rid, ""))
        if rid.startswith("D-AMC-AA-08"):
            amending = "I-AA-ACT37-1992"
        held = r["supporting_document_held"].startswith("YES")
        ev_date = r["commencement_date_evidenced"]
        detail, readings_pres, saving, partial, related, owner = "", "", "", "", "", ""
        if rid.startswith("D-AMC-RES"):
            status = "DISPUTED_PRESERVE_BOTH"
            cid = "C5-CF-" + rid.split("D-AMC-RES-")[1]
            c = ctx.conf.get(cid, {})
            # Review LG-06: readings are carried in full, never truncated; where the C5 register does not itemise the two
            # sources, say so and carry its conflict description and evidence instead of an empty cell.
            if cid == "C5-CF-C-01":
                readings_pres = ("(a) Gazette of 27-11-1954 (S.R.O. 484, archival facsimile c5ef95a9, printed p.300): 'You are not obliged to say anything unless "
                                 "you wish to do so' || (b) India Code compilation (48f52219) p.41: 'You are obliged to say anything unless you wish to do so' "
                                 "[C9-LEGAL-EVIDENCE/CORRECTIONS matter B, re-rendered pages; AI-agent reading, not human-confirmed] || "
                                 f"register source_a: {c.get('source_a', '')} || register source_b: {c.get('source_b', '')}")
            elif c and (c.get("source_a") or c.get("source_b")):
                readings_pres = f"(a) {c.get('source_a', '')} || (b) {c.get('source_b', '')}"
            elif c:
                readings_pres = (f"readings not itemised in the C5 conflict register ({cid}); conflict: {c.get('nature_of_conflict', '')}; "
                                 f"evidence: {c.get('evidence', '')}")
            else:
                readings_pres = f"{cid} not found in the C5 conflict register"
            detail = r["verification_status"]
            owner = "qualified legal adviser (conflict register: legal_adviser_required)"
        elif not held:
            status = "NOT_LOCATED"
            detail = f"instrument not held; C8: {r['commencement_gap']}; {r['verification_status']}"
        elif ev_date:
            status = "EVIDENCED"
            detail = f"commencement stated in the held instrument ({r['commencement_as_printed'][:120]})"
        else:
            status = "UNRESOLVED_COMMENCEMENT"
            detail = f"held instrument; commencement not evidenced: {r['commencement_gap']}"
        evidence = f"C8 amendment_commencement_matrix.csv#{rid}; {r['source_evidence'][:200]}"
        if r["document_sha256"]:
            evidence += f"; held sha256 {r['document_sha256'][:16]}"
        interval = "NOT EVIDENCED"
        if status == "EVIDENCED":
            h = r["historical_applicability_interval"]
            interval = f"from {ev_date} (stated commencement); end not established" + (f" | C8 note: {h[:160]}" if h and not h.startswith("NOT") else "")
        c9 = ""
        # C9 additions to C8 rows ----------------------------------------------------------------------------
        if rid.startswith("D-AMC-AA-08"):
            sec = rid.split("-s")[-1]
            dated = sec in ("2", "11", "19")
            readings_pres = (f"(a) Act 37/1992 Gazette scan: assent 06-09-1992, Gazette 07-09-1992, no commencement clause [{rd('C9R-A37-01')}; {rd('C9R-A37-03')}] || "
                             f"(b) India Code compilation: " + (f"'(w.e.f. 6-9-1992)' printed for this provision [{rd('C9R-AA-03')}]" if dated else f"footnote for this provision carries no date [{rd('C9R-AA-04')}]"))
            c9 = "C9 re-verified the compilation: 'w.e.f. 6-9-1992' appears only at pp.27, 36, 48 (s.2, s.11, s.19 of Act 37/1992)"
            owner = "legal adviser (AQ-05: date on which an Act with no commencement clause comes into force)"
        if rid == "D-AMC-AA-06":
            readings_pres = f"(a) Act 13/1975: no commencement clause [{rd('C9R-A13-03')}]; s.4(2) 'as if this Act had come into force on the 25th day of January, 1975' for actions under the Ordinance [{rd('C9R-A13-02')}] || (b) compilation 'w.e.f. 25-1-1975' [{rd('C9R-AA-09')}]"
            saving = "s.4(2): actions under the repealed Ordinance deemed taken under the Act as amended"
            owner = "legal adviser (OQ-A-04)"
        if rid == "D-AMC-AA-01":
            related = f"S.R.O. 2(E) of 07-05-1955 (rendering footnote) [{rd('C9R-A19-02')}]; candidate ACQ03-020 (PR #23)"
        if rid == "D-AMC-AA-00":
            related = f"S.R.O. 120 of 22-07-1950 [{rd('C9R-AA-02')}]; probable candidate ACQ03-019 (PR #23)"
        if rid == "D-AMC-AA-07":
            related = f"s.1(2) notification of Act 20/1983 (candidate ACQ03-024); compilation 'w.e.f. 15-3-1984' [{rd('C9R-AA-07')}]"
        if rid == "D-AMC-AFT-00":
            related = f"S.O. 14(E) of 13-06-2008 (compilation) [{rd('C9R-AFT-04')}]; distinct: S.R.O. 9(E)/2009 establishing the Tribunal w.e.f. 10-08-2009 [{rd('C9R-RD-AFTAPPT-IMG')}]"
            c9 = f"C9: principal Act as published is held in the corpus raw store [{rd('C9R-RD-AFT07-IMG')}]; the s.1(2) notification is still not held"
        if rid == "D-AMC-AFT-01":
            status, detail = "UNRESOLVED_COMMENCEMENT", "C9: Finance Act 2017 held in corpus raw store; Part XIV commencement by notification (s.156), notification not held"
            evidence += f"; {rd('C9R-RD-FIN17-01')}; {rd('C9R-RD-FIN17-02')}"
            partial = "s.156: different dates may be appointed for different provisions of Part XIV"
            readings_pres = f"(a) Act: Part XIV by notification [{rd('C9R-RD-FIN17-02')}] || (b) compilation: 'w.e.f. 26-5-2017' [{rd('C9R-AFT-05')}]"
            related = "Part XIV commencement notification (not held)"
        if rid == "D-AMC-AFT-02":
            status, ev_date = "EVIDENCED", "2021-04-04 (deemed)"
            detail = f"C9: TRA 2021 held in corpus raw store; s.26 substitutes words in AFT s.9A [{rd('C9R-RD-TRA21-02')}]; s.1(2) deemed commencement 04-04-2021 [{rd('C9R-RD-TRA21-IMG')}]"
            evidence += f"; {rd('C9R-RD-TRA21-IMG')}"
            interval = "s.9A as amended by TRA 2021 s.26: from 04-04-2021 (deemed); end: substitution of s.9A by TRA 2026 (commencement NOT EVIDENCED)"
            c9 = "C8 'provisions affected UNKNOWN' superseded: s.26 (AFT s.9A)"
        if rid in ("D-AMC-AFT-03", "D-AMC-AFT-04"):
            partial = f"s.1(2): different dates may be appointed for different provisions [{rd('C9R-TRA-02')}]"
            related = "TRA 2026 s.1(2) notification(s) (not held)"
            if rid == "D-AMC-AFT-04":
                saving = f"s.24(2)-(4) savings [{rd('C9R-TRA-03')}]"
            else:
                readings_pres = f"(a) TRA 2026: commencement by notification [{rd('C9R-TRA-02')}] || (b) compilation: s.9A 'w.e.f. 25-08-2026' [{rd('C9R-AFT-06')}]"
        if rid == "D-AMC-AFT-05":
            status = "UNRESOLVED_COMMENCEMENT"
            detail = "C9: Procedure Rules 2008, Amendment Rules 2011 and Practice Rules 2009 held in corpus raw store; split into C9-AG edges (2008, 2011 EVIDENCED; Practice Rules publication date not on held page)"
        if rid in ("D-AMC-BNS-COMM", "D-AMC-BNSS-COMM", "D-AMC-BSA-COMM"):
            rr = {"D-AMC-BNS-COMM": "C9R-RD-BNS-02", "D-AMC-BNSS-COMM": "C9R-BNSS-02", "D-AMC-BSA-COMM": "C9R-BSA-02"}[rid]
            so = {"D-AMC-BNS-COMM": "S.O. 850(E)", "D-AMC-BNSS-COMM": "S.O. 848(E)", "D-AMC-BSA-COMM": "S.O. 849(E)"}[rid]
            related = f"{so} dated 23-02-2024 (compilation footnote) [{rd(rr)}]"
            partial = {"D-AMC-BNS-COMM": "except s.106(2) (footnote)", "D-AMC-BNSS-COMM": "except the First Schedule entry relating to s.106(2) (footnote)", "D-AMC-BSA-COMM": "none printed in the footnote"}[rid]
        if rid == "D-AMC-BNSS-REPEAL":
            saving = f"s.531(2)(a) pending matters under CrPC; (b) notifications, rules etc. under CrPC deemed made under BNSS [{rd('C9R-BNSS-04')}]"
            evidence += f"; {rd('C9R-BNSS-03')}"
        if rid == "D-AMC-BSA-REPEAL":
            saving = f"s.170(2) pending matters under the IEA [{rd('C9R-BSA-04')}]"
            evidence += f"; {rd('C9R-BSA-03')}"
        if rid == "D-AMC-BNS-REPEAL":
            status = "UNRESOLVED_COMMENCEMENT"
            detail = "C9: BNS s.358 readable in the corpus raw store compilation; repeal operates from BNS commencement, whose notification is not held"
            saving = f"s.358(2) previous operation, rights, penalties, proceedings; s.358(3) things done deemed done under BNS [{rd('C9R-RD-BNS-03')}]"
            evidence += f"; {rd('C9R-RD-BNS-03')}"
        if rid == "D-AMC-AR-008":
            status = "DISPUTED_PRESERVE_BOTH"
            readings_pres = "(a) held S.R.O. 34 dated 05-01-1963 is a r.188(e) declaration (C8-PIC-03) || (b) Gazette-printed NOTEs list 'SRO 34 dated 5 Jun 63' among amendments of the Rules (C8-CR-02); S.R.O. 2(E)/2018 lists 'S.R.O. 34 dated 05th January, 1963'"
            detail = "identity relationship UNRESOLVED (C8-CR-02); no chain inference"
            owner = "owner / legal adviser after the 1963 Gazette issues are searched"
        if rid == "D-AMC-AR-034":
            detail += "; copy-fidelity caveat: CMS signature value fails integrity (C8-CR-03, NEEDS_FURTHER_EVIDENCE); Hindi footnote names S.R.O. 2(E)/2018 as last amendment, English does not (C8-CR-14)"
        if rid == "D-AMC-AR-024":
            detail += "; retrospective Explanation added to r.16A (legal review of retrospective effect needed; C8 note)"
        if rid == "D-AMC-AR-029":
            c9 = f"C9: item 31 (r.168(2) field-punishment words omitted) re-read [{rd('C9R-AR-02')}]; India Code compilation still prints them [{rd('C9R-AR-01')}] - see C9-AG-AR168"
        repeal = "YES" if re.search(r"(?i)omit|repeal", r["provision_affected"] + " " + r["amendment_type"]) else ""
        rows.append(dict(edge_id=f"C9-AG-{rid[6:]}", origin=rid, target_instrument_id=target, provision=r["provision_affected"][:200], amending_instrument_id=amending,
                         amending_instrument=r["amending_instrument"][:160], edge_kind=r["amendment_type"][:60], publication_date=r["publication_date"],
                         commencement_as_printed=r["commencement_as_printed"][:200], commencement_date_evidenced=ev_date if status == "EVIDENCED" else "",
                         partial_or_staged_commencement=partial, repeal_or_omission=repeal, saving_or_transitional=saving, supersession="", related_notification=related,
                         evidence=evidence, historical_effective_interval=interval, status=status, status_detail=detail, preserved_readings=readings_pres,
                         decision_owner=owner or ("legal adviser (AQ-05)" if "AQ-05" in r["commencement_gap"] else ""), c9_change=c9))
    # ---------------- C9 new edges ----------------
    new = [
        dict(edge_id="C9-AG-AR168", origin="C9-NEW", target_instrument_id="I-AR-1954", provision="r.168(2) (words 'or with field punishment' and 'or until the completion of the field punishment, unless such field punishment is remitted by a competent authority')",
             amending_instrument_id="I-AR-AMD-029", amending_instrument="S.R.O. 17(E) - Army (Amendment) Rules, 1993, item 31", edge_kind="omission (text discrepancy with compilation)",
             publication_date="1993-12-06", commencement_as_printed="on publication (C8 D-AMC-AR-029)", commencement_date_evidenced="",
             repeal_or_omission="YES (words omitted per Gazette)", evidence=f"{rd('C9R-AR-02')}; {rd('C9R-AR-01')}; {rd('C9R-AR-04')}; C5 provision_amendment_chain.csv#C5-PCH-PCL-93-31",
             status="DISPUTED_PRESERVE_BOTH", status_detail="NEW: the India Code compilation (48f52219) prints r.168(2) with the field-punishment words; the held 1993 Gazette item 31 omits them. Not in any conflict register. No conclusion on current text.",
             preserved_readings=f"(a) S.R.O. 17(E)/1993 item 31 omits the words [{rd('C9R-AR-02')}] || (b) compilation r.168(2) still prints them [{rd('C9R-AR-01')}]",
             decision_owner="owner (register as conflict) then legal adviser", c9_change="NEW"),
        dict(edge_id="C9-AG-AFTRDO2008", origin="C9-NEW", target_instrument_id="I-AFT-2007", provision="s.6(3)(a): 'and' at the end replaced by 'or'", amending_instrument_id="I-AFT-RDO-2008",
             amending_instrument="AFT Act (Removal of Difficulties) Order, 2008, S.R.O. 18(E), under s.40(1)", edge_kind="substitution (removal-of-difficulties order)", publication_date="2008-07-21",
             commencement_as_printed="on publication in the Official Gazette", commencement_date_evidenced="2008-07-21", evidence=f"{rd('C9R-RD-AFTRDO-IMG1')}; {rd('C9R-RD-AFTRDO-IMG2')}",
             historical_effective_interval="from 21-07-2008 (stated: on publication); end not established", status="EVIDENCED", status_detail="NEW instrument not in any C5/C8 register", c9_change="NEW"),
        dict(edge_id="C9-AG-AFTSRO9E2009", origin="C9-NEW", target_instrument_id="I-AFT-2007", provision="establishment of the Tribunal under s.4; appointed day under s.3(c)", amending_instrument_id="I-AFT-SRO9E-2009",
             amending_instrument="S.R.O. 9(E) dated 07-08-2009", edge_kind="establishment notification (not an amendment; not the s.1(2) commencement)", publication_date="2009-08-07",
             commencement_as_printed="Tribunal established with effect from 10-08-2009", commencement_date_evidenced="2009-08-10 (establishment/appointed day)", evidence=rd("C9R-RD-AFTAPPT-IMG"),
             related_notification="S.O. 14(E)/2008 (s.1(2)) remains NOT HELD", historical_effective_interval="appointed day 10-08-2009 as stated", status="EVIDENCED", status_detail="NEW instrument not in any C5/C8 register", c9_change="NEW"),
        dict(edge_id="C9-AG-AFT9A-TRA2021", origin="C9-NEW", target_instrument_id="I-AFT-2007", provision="s.9A (words referring to Part XIV/s.184 of the Finance Act 2017 replaced by reference to TRA 2021 Ch. II)",
             amending_instrument_id="I-AFT-TRA-2021", amending_instrument="Tribunals Reforms Act, 2021, s.26", edge_kind="substitution of words", publication_date="2021-08-13",
             commencement_as_printed="s.1(2): deemed in force 04-04-2021", commencement_date_evidenced="2021-04-04 (deemed)", evidence=f"{rd('C9R-RD-TRA21-02')}; {rd('C9R-RD-TRA21-IMG')}",
             supersession="s.9A later substituted as a whole by TRA 2026 s.18/Sch. II item 9 (commencement not evidenced)", historical_effective_interval="from 04-04-2021 (deemed); end NOT EVIDENCED",
             status="EVIDENCED", status_detail="the held compilation shows no TRA 2021 footnote (it reflects the later TRA 2026 substitution)", c9_change="NEW (details C8 AFT-02)"),
        dict(edge_id="C9-AG-TRA2021-REPEAL", origin="C9-NEW", target_instrument_id="I-AFT-TRA-2021", provision="whole Act (repeal)", amending_instrument_id="I-AFT-TRA-2026",
             amending_instrument="Tribunals Reforms Act, 2026, s.24(1)", edge_kind="repeal", publication_date="2026-08-13", commencement_as_printed="by notification; staged dates allowed",
             partial_or_staged_commencement=f"[{rd('C9R-TRA-02')}]", repeal_or_omission="YES", saving_or_transitional=f"s.24(2)-(4) [{rd('C9R-TRA-03')}]", evidence=rd("C9R-TRA-03"),
             related_notification="TRA 2026 s.1(2) notification(s) (not held)", status="UNRESOLVED_COMMENCEMENT", status_detail="repealing Act held; commencement notification not held", c9_change="NEW (repeal target split from C8 AFT-04)"),
        dict(edge_id="C9-AG-AFTPR2008", origin="C9-NEW", target_instrument_id="I-AFT-2007", provision="AFT (Procedure) Rules 2008 made under s.41(2)(f),(g),(k)", amending_instrument_id="I-AFT-PR-2008",
             amending_instrument="S.R.O. 26(E) dated 17-09-2008", edge_kind="implements (rules under the Act)", publication_date="2008-09-17", commencement_as_printed="from the date of publication in the Official Gazette",
             commencement_date_evidenced="2008-09-17", evidence=f"{rd('C9R-RD-AFTPR08-IMG1')}; {rd('C9R-RD-AFTPR08-IMG2')}", historical_effective_interval="from 17-09-2008 (publication); end not established",
             status="EVIDENCED", status_detail="masthead and r.1 on different pages of one India Code bundle (identity of issue inferred from the bundle)", c9_change="NEW (splits C8 AFT-05)"),
        dict(edge_id="C9-AG-AFTPR2011", origin="C9-NEW", target_instrument_id="I-AFT-PR-2008", provision="r.7 renumbered as r.7(1); r.7(2) inserted (fee payable only for OA, RA, CA, MA, AT); r.12A inserted (affidavit)",
             amending_instrument_id="I-AFT-PR-AMD-2011", amending_instrument="AFT (Procedure) Amendment Rules, 2011, S.R.O. 05(E) dated 29-07-2011", edge_kind="amendment", publication_date="2011-07-29",
             commencement_as_printed="on the date of their publication in the Official Gazette", commencement_date_evidenced="2011-07-29", evidence=f"{rd('C9R-RD-AFTPR11-IMG1')}; {rd('C9R-RD-AFTPR11-IMG2')}",
             historical_effective_interval="from 29-07-2011 (publication); end not established", status="EVIDENCED", c9_change="NEW (splits C8 AFT-05)"),
        dict(edge_id="C9-AG-AFTPRAC2009", origin="C9-NEW", target_instrument_id="I-AFT-2007", provision="AFT (Practice) Rules 2009 made under s.41(2)(f),(g),(k)", amending_instrument_id="I-AFT-PRAC-2009",
             amending_instrument="S.R.O. 6(E) dated 11-05-2009", edge_kind="implements (rules under the Act)", publication_date="not printed on the held page", commencement_as_printed="from the date of publication in the official gazette",
             evidence=rd("C9R-RD-AFTPRAC09-IMG"), status="UNRESOLVED_COMMENCEMENT", status_detail="publication date (masthead) not on the held page; ACQ03-032 archive candidate may carry it", c9_change="NEW (splits C8 AFT-05)"),
        dict(edge_id="C9-AG-CCCM-SO4010", origin="C9-NEW", target_instrument_id="I-CCCM-1978", provision="amendment of the 1978 Rules (adds 'coast guard law' per PILOT-01 discovery reading; not held)", amending_instrument_id="I-CCCM-SO4010-1986",
             amending_instrument="Criminal Courts and Court-Martial (Adjustment of Jurisdiction) Amendment Rules, 1986, MHA Notification S.O. 4010", edge_kind="amendment", publication_date="06-12-1986 (Gazette, per PILOT-01 discovery reading)",
             commencement_as_printed="not seen", evidence=f"{rd('C9R-RS-01')}; PILOT-01/registers/source_discovery_2026-11-22.csv#T5-02; SOURCE-LIBRARY-C5/review/review_findings.csv#RV-01; ACQ-01/batches.json",
             status="DISPUTED_PRESERVE_BOTH", status_detail="instrument not held; date of the notification differs between sources",
             preserved_readings=f"(a) RS papers-laid record: 'S.O. No. 4010, dated the 6th December, 1986' [{rd('C9R-RS-01')}] || (b) PILOT-01 T5-02 / ACQ-01: notification dated 24-11-1986, Gazette 06-12-1986 pp.4881-82 (archive item read during discovery; not held) || (c) C5 RV-01 transcription '8 Dec 1986' (contradicted by the C9 page-image read; human re-check)",
             decision_owner="owner after PR #8 record copy is image-checked", c9_change="NEW"),
        dict(edge_id="C9-AG-SRO240-1955", origin="C9-NEW", target_instrument_id="I-AR-1954", provision="r.188(e) declarations: date of S.R.O. 240/1955 (superseded by S.R.O. 34/1963)", amending_instrument_id="I-AR-AMD-008",
             amending_instrument="S.R.O. 34 dated 05-01-1963 (supersession recital) / S.R.O. 2(E)/2018 Note", edge_kind="supersession recital (declaration)", publication_date="1963-01-19",
             evidence="C8-EVIDENCE contradiction_register_c8.csv#C8-CR-01", status="DISPUTED_PRESERVE_BOTH", supersession="S.R.O. 34/1963 supersedes notifications 609/1950, SRO 8/1951, 210/1951, 240/1955, 399/1955, 176/1956 (gazette_evidence_register T1-02)",
             preserved_readings="(a) S.R.O. 34/1963 recites 'SRO 240, dated the 25th June, 1955' || (b) S.R.O. 2(E)/2018 Note lists 'S.R.O. 240 dated 05th June, 1955'", decision_owner="owner (documentary; low consequence)", c9_change="carried from C8-CR-01"),
        dict(edge_id="C9-AG-LASTAMD-2019", origin="C9-NEW", target_instrument_id="I-AR-1954", provision="identity of the last amendment before S.R.O. 17(E)/2019", amending_instrument_id="I-AR-AMD-034",
             amending_instrument="S.R.O. 17(E)/2019 footnotes", edge_kind="footnote discrepancy", publication_date="2019-12-28", evidence="C8-EVIDENCE contradiction_register_c8.csv#C8-CR-14 (C8-PIC-39, C8-PIC-37)",
             status="DISPUTED_PRESERVE_BOTH", preserved_readings="(a) Hindi footnote: last amended by S.R.O. 2(अ) of 20-02-2018 || (b) English footnote: 'last amended in 2018', no instrument named; S.R.O. 2(E)/2018 is on its face a r.188(e) declaration",
             decision_owner="owner (documentary)", c9_change="carried from C8-CR-14"),
    ]
    for e in new:
        rows.append(e)
    fields = ["edge_id", "origin", "target_instrument_id", "provision", "amending_instrument_id", "amending_instrument", "edge_kind", "publication_date", "commencement_as_printed",
              "commencement_date_evidenced", "partial_or_staged_commencement", "repeal_or_omission", "saving_or_transitional", "supersession", "related_notification", "evidence",
              "historical_effective_interval", "status", "status_detail", "preserved_readings", "decision_owner", "c9_change"]
    for e in rows:
        if e["status"] not in STATUSES:
            raise SystemExit(f"bad status {e['status']} on {e['edge_id']}")
        if e["status"] != "EVIDENCED" and e.get("commencement_date_evidenced"):
            raise SystemExit(f"date on non-evidenced edge {e['edge_id']}")
        if e["status"] == "DISPUTED_PRESERVE_BOTH" and not e.get("preserved_readings", "").replace("(a)", "").replace("(b)", "").replace("||", "").strip():
            raise SystemExit(f"disputed edge without readings {e['edge_id']}")
    return fields, rows


# ----------------------------------------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo")
    ap.add_argument("--evidence-repo", required=True)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    ctx = Ctx(a.repo, a.evidence_repo)
    outs = {}

    metrics_text, metrics = build_metrics(ctx)
    outs["baseline_metrics.json"] = metrics_text

    uniq = unique_pins(ctx)
    acq_rows, ar_pins, acq03_ar = build_acquisition(ctx, uniq, None)
    insts = instruments(ctx) + ar_amendment_instruments(ctx, ar_pins, acq03_ar) + more_instruments(ctx)
    ids = [i["id"] for i in insts]
    dup = [k for k, v in collections.Counter(ids).items() if v > 1]
    if dup:
        raise SystemExit(f"duplicate instrument ids {dup}")
    gfields, graph = build_graph(ctx)
    for e in graph:
        for k in ("target_instrument_id", "amending_instrument_id"):
            if e.get(k) and e[k] not in ids:
                raise SystemExit(f"graph {e['edge_id']} references unknown {e[k]}")

    # link acquisition rows to instruments
    link_rules = [
        (r"sro-484|S\.R\.O\. 484|C5-ACQ-06|C5C-00[4-9]|C5C-01[0-3]", "I-AR-1954"), (r"army-rules-amdt|r188e|acq03-0(0\d|1[0-4]|3[6-9]|4\d)", "I-AR-1954"),
        (r"adjustment-jurisdiction-1978|S\.O\. 488", "I-CCCM-1978"), (r"so-4010", "I-CCCM-SO4010-1986"), (r"commanders-in-chief", "I-AA-ACT19-1955"),
        (r"laws-amendment-1975", "I-AA-ACT13-1975"), (r"army-amendment-1992", "I-AA-ACT37-1992"), (r"acq03-015", "I-AA-RAA-1974"), (r"acq03-017", "I-AA-RAA-2001"),
        (r"acq03-018", "I-AA-POST1992"), (r"acq03-019", "I-AA-SRO120-1950"), (r"acq03-020", "I-AA-SRO2E-1955"), (r"acq03-021", "I-AA-ALO3-1956"), (r"acq03-022", "I-AA-ORD3-1975"),
        (r"acq03-02[34]", "I-AA-ACT20-1983"), (r"acq03-025", "I-AA-RAA2-2017"), (r"acq03-030|acq03-033|Procedure\) Rules 2008", "I-AFT-PR-2008"),
        (r"acq03-031|acq03-034|Amendment Rules 2011", "I-AFT-PR-AMD-2011"), (r"acq03-032|acq03-035|Practice", "I-AFT-PRAC-2009"),
        (r"entitlement-casualty-pensionary-awards-2023|C5-ACQ-09", "I-ER-2023"), (r"guide-medical-officers", "I-GMO-2023"),
        (r"crpc|CrPC", "I-CRPC-1973"), (r"bprd-comparison-bns-ipc", "I-IPC-1860"), (r"bsa-iea", "I-IEA-1872"),
        (r"C5-ACQ-01\b|C5C-001|Army Act, 1950 \(Act XLVI", "I-AA-1950"), (r"C5C-016|C5-ACQ-02\b", "I-AFT-2007"), (r"C5C-018|C5-ACQ-03\b", "I-BNSS-2023"), (r"C5C-019|C5-ACQ-04\b", "I-BSA-2023"),
        (r"C5C-021", "I-BNSS-COMM-SO848E"), (r"C5C-022", "I-BSA-COMM-SO849E"), (r"C5C-023", "I-BNS-COMM-SO850E"), (r"C5C-020|C5-ACQ-20", "I-BNS-2023"),
        (r"C5C-02[67]|C5-ACQ-21", "I-DPP-AMD-2000"), (r"C5-ACQ-07", "I-PRA-2008-PT1"), (r"C5-ACQ-08", "I-PRA-2008-PT2"), (r"C5-ACQ-10", "I-ER-2008"), (r"C5-ACQ-11", "I-CIRC-PRA-ER"),
        (r"C5-ACQ-19", "I-AR-INTERIM-1950"), (r"Removal of Difficulties", "I-AFT-RDO-2008"), (r"S\.R\.O\. 9\(E\)/2009", "I-AFT-SRO9E-2009"), (r"Finance Act 2017 \(7", "I-AFT-FIN-2017"),
        (r"Tribunals Reforms Act 2021", "I-AFT-TRA-2021"), (r"BNS 2023 India Code", "I-BNS-2023"), (r"DPP Act 1950", "I-DPP-1950"), (r"IPC 1860", "I-IPC-1860"),
        (r"Indian Evidence Act 1872", "I-IEA-1872"), (r"CrPC 1973 India", "I-CRPC-1973"), (r"Air Force Act 1950 India", "I-AFA-1950"), (r"Navy Act 1957 India", "I-NA-1957"),
        (r"S\.O\. 14\(E\)", "I-AFT-SO14E-2008"), (r"TRA 2026 s\.1", "I-AFT-TRA2026-COMM"), (r"Part XIV commencement", "I-AFT-FIN-2017"), (r"3912", "I-AA-SO3912E-2019"),
        (r"1957 \(36", "I-AA-RAA-1957"), (r"1960 \(58", "I-AA-RAA-1960"), (r"E-7", "I-AR-AMD-001"), (r"258 of 2002", "I-AR-AMD-030"), (r"S\.R\.O\. 34 dated 5-6", "I-AR-AMD-008"),
        (r"Post-BNSS", "I-CCCM-1978"), (r"as at 30-06-2024", "I-CRPC-1973"), (r"Gazettes as enacted", "I-AFA-1950"), (r"ISO", "I-ISO-2023"), (r"Army Act notifications", "I-AA-NOTIFS"),
        (r"C5-ACQ-1[2-5]|C5-ACQ-26|C5-ACQ-1[6-8]|C5-ACQ-2[2-5]", ""),
    ]
    if "I-AFT-TRA2026-COMM" not in ids:
        insts.append(dict(id="I-AFT-TRA2026-COMM", priority="3", family="AFT Act 2007", title="Commencement notification(s) of the Tribunals Reforms Act, 2026 under s.1(2) (not held)",
                          title_basis=ctx.rd("C9R-TRA-02"), authority="Central Government", number="not known", date="not known", date_basis="register", commencement="n/a",
                          source_ids=[], raw_shas=[], held_shas=[], gaps=["G-TRA2026-COMM"], missing="the notification(s)", contradictions="compilation states s.9A substitution 'w.e.f. 25-08-2026' (" + ctx.rd("C9R-AFT-06") + ")",
                          route="official-source discovery", auth="discovery approval", verification="NOT_HELD"))
        ids.append("I-AFT-TRA2026-COMM")
    for r in acq_rows:
        key = " ".join([r["doc_id"], r["required_document"], r["evidence"]])
        r["instrument_id"] = ""
        for pat, iid in link_rules:
            if re.search(pat, key):
                r["instrument_id"] = iid
                break
        # Army Rules amendment pins: link to the specific amendment instrument when identifiable
        if r["instrument_id"] == "I-AR-1954" and r["held_evidence"]:
            m = re.search(r"sha256 ([0-9a-f]{64})", r["held_evidence"])
            arid = ar_id_for_sha(ctx, m.group(1)) if m else ""
            if arid and arid != "AR-000":
                r["instrument_id"] = f"I-AR-AMD-{arid[3:]}"
        m = re.search(r"closes (AR-\d{3})", next((p["note"] for p in ctx.pins if p["doc_id"] == r["doc_id"]), ""))
        if m and f"I-AR-AMD-{m.group(1)[3:]}" in ids:
            r["instrument_id"] = f"I-AR-AMD-{m.group(1)[3:]}"
        if r["instrument_id"] and r["instrument_id"] not in ids:
            raise SystemExit(f"acq row {r['acq_row_id']} links unknown {r['instrument_id']}")
    inst_by = {i["id"]: i for i in insts}
    gap_by_inst = {i["id"]: i.get("gaps", []) for i in insts}
    for r in acq_rows:
        recs, cases = ctx.gap_records(gap_by_inst.get(r["instrument_id"], [])) if r["instrument_id"] else ([], [])
        r["dependent_kb_records"] = len(recs)
        r["dependent_case_records"] = len(cases)
        r["priority"] = inst_by[r["instrument_id"]]["priority"] if r["instrument_id"] else ""

    acq_fields = ["acq_row_id", "required_document", "instrument_id", "priority", "doc_id", "source_key", "reconciliation_state", "held_state", "held_evidence", "pending_branch",
                  "branch_ref_commit", "present_in", "url", "pinned_md5", "pinned_bytes", "existing_approval", "outstanding_authorisation", "dependent_kb_records", "dependent_case_records", "evidence"]
    outs["acquisition_reconciliation.csv"] = wcsv(acq_fields, acq_rows)

    ready = [r for r in acq_rows if r["pending_branch"] == "PR #8 (ACQ-01)"]
    ready_fields = ["acq_row_id", "doc_id", "required_document", "instrument_id", "source_key", "url", "pinned_md5", "pinned_bytes", "held_state", "held_evidence",
                    "approval_basis", "remaining_gates", "post_fetch_checks"]
    for r in ready:
        r["approval_basis"] = "owner authorisation of ACQ-01 batches B1, B2, B6 (2026-11-22), recorded in PROGRESS.md on branch claude/acq-01-config (PR #8) @ " + r["branch_ref_commit"]
        r["remaining_gates"] = "(1) owner approval/merge of PR #8 (config only); (2) logged download-run approval per docs/acquisition/ACQUISITION_RUNBOOK.md; dry-run first"
        r["post_fetch_checks"] = ("md5 and size equal to pin; record served sha256" if not r["source_key"] == "official_instruments" else "PDF type check; record served sha256 (host watermarks; listing md5 informational)") + "; page-image identity check before any finding cites it"
    outs["acquisition_manifest_ready.csv"] = wcsv(ready_fields, ready)

    outs["amendment_graph.csv"] = wcsv(gfields, graph)

    # instrument records -------------------------------------------------------------------------------------------
    edges_by_target = collections.defaultdict(list)
    edges_by_amending = collections.defaultdict(list)
    for e in graph:
        if e["target_instrument_id"]:
            edges_by_target[e["target_instrument_id"]].append(e)
        if e["amending_instrument_id"]:
            edges_by_amending[e["amending_instrument_id"]].append(e)
    acq_by_inst = collections.defaultdict(list)
    for r in acq_rows:
        if r["instrument_id"]:
            acq_by_inst[r["instrument_id"]].append(r)
    irows = []
    md = {}
    for i in insts:
        held, auth = ctx.held_copies(i.get("source_ids", []), i.get("raw_shas", []), i.get("held_shas", []))
        recs, cases = ctx.gap_records(i.get("gaps", []))
        amend = [f"{e['edge_id']} ({e['status']})" for e in edges_by_target.get(i["id"], [])]
        amends = [f"{e['edge_id']} -> {e['target_instrument_id']} ({e['status']})" for e in edges_by_amending.get(i["id"], [])]
        acq = [f"{r['acq_row_id']} {r['reconciliation_state']}" for r in acq_by_inst.get(i["id"], [])]
        row = dict(instrument_id=i["id"], priority=i["priority"], family=i["family"], exact_legal_title=i["title"], title_basis=i["title_basis"],
                   issuing_authority=i["authority"], instrument_number=i["number"], instrument_date=i["date"], date_basis=i["date_basis"],
                   commencement_evidence=i["commencement"], held_copies=" | ".join(held) or "none", authenticity_classification=" | ".join(auth) or "n/a (no held copy)",
                   applicable_amendments=("; ".join(amend) or "none in graph") + (" | amends: " + "; ".join(amends) if amends else ""),
                   missing_originals=i.get("missing", "") or "none", contradictions=i["contradictions"],
                   linked_research_records=f"{len(recs)} KB records ({';'.join(recs[:40])}{' ...' if len(recs) > 40 else ''}); {len(cases)} cases ({';'.join(cases)}); via gaps {';'.join(i.get('gaps', []))}",
                   dependent_kb_record_count=len(recs), proposed_acquisition_route=i["route"], acquisition_rows="; ".join(acq) or "none",
                   outstanding_authorisation=i["auth"], verification_status=i["verification"], reader=READER)
        irows.append(row)
        lines = [f"# {i['id']}: {i['title']}", "", f"Priority {i['priority']} - {i['family']}. Generated by `tools/build_stat_c9.py`; do not edit by hand.", "",
                 "| Field | Value |", "| --- | --- |"]
        for k, v in row.items():
            if k == "instrument_id":
                continue
            lines.append(f"| {k} | {str(v).replace('|', '/')} |")
        lines += ["", "Page readings cited here were made by an AI agent (Claude Opus 5.5 subagent) and are not human-confirmed. Nothing here states current legal status or applicability."]
        md[f"instruments/{i['id']}.md"] = "\n".join(lines) + "\n"
    ifields = list(irows[0].keys())
    outs["instrument_records.csv"] = wcsv(ifields, irows)
    outs.update(md)

    # markdown documents --------------------------------------------------------------------------------------------
    outs.update(docs(ctx, metrics, acq_rows, ready, graph, irows))

    # readings used ledger
    used = sorted(ctx.used_readings)
    unused = sorted(set(ctx.readings) - ctx.used_readings)
    outs["readings_index.csv"] = wcsv(["reading_id", "used_in_outputs", "held_path", "sha256", "result", "pages", "render_sha256", "purpose", "reader"],
                                      [dict(reading_id=k, used_in_outputs="YES" if k in ctx.used_readings else "NO", **{x: ctx.readings[k][x] for x in ("held_path", "sha256", "result", "pages", "render_sha256", "purpose", "reader")}) for k in sorted(ctx.readings)])

    sums = "".join(f"{hashlib.sha256(outs[k].encode('utf-8')).hexdigest()}  {k}\n" for k in sorted(outs))
    outs["OUTPUT_SHA256SUMS"] = sums

    bad = 0
    for k in sorted(outs):
        p = os.path.join(OUT, k)
        if a.check:
            ok = os.path.exists(p) and open(p, encoding="utf-8").read() == outs[k]
            if not ok:
                print("DIFF", k)
                bad += 1
        else:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8", newline="") as f:
                f.write(outs[k])
    if a.check:
        stale = []
        idir = os.path.join(OUT, "instruments")
        if os.path.isdir(idir):
            stale = [f for f in os.listdir(idir) if f"instruments/{f}" not in outs]
        for s in stale:
            print("STALE", s)
        print(f"CHECK {'OK' if not bad and not stale else 'FAILED'}: {len(outs)} outputs")
        sys.exit(1 if bad or stale else 0)
    print(f"wrote {len(outs)} outputs; instruments {len(insts)}; edges {len(graph)}; acquisition rows {len(acq_rows)}; ready {len(ready)}; readings used {len(used)}, unused {len(unused)}")


sys.path.insert(0, HERE)  # isolated mode (-I) does not add the script directory
from docs_c9 import docs  # noqa: E402  (document text kept in a sibling module)

if __name__ == "__main__":
    main()
