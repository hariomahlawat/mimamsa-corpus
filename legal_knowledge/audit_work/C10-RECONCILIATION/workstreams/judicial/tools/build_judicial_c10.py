#!/usr/bin/env python3
"""C10 workstream C (judicial evidence): deterministic builder.

Regenerates the workstream CSVs and JUDICIAL_C10_MANIFEST.json from pinned inputs:
  * git objects by commit in --repo (raw-data ad77758d, staging 21e73b83,
    PR #40 head 9a6f9366, PR #41 head cfc52d57);
  * C10 reconciliation outputs (UNIFIED_CORPUS_INVENTORY.csv, hash-checked against
    RECONCILIATION_MANIFEST.json) and inputs/hf_snapshot/lk_declared_sidecars.tsv;
  * this workstream's inputs/hf_lk_text_readings.json;
  * held working copies under --store (re-hashed before any use).

Usage:
  python -I build_judicial_c10.py --repo /home/user/c7 --c10 <C10-RECONCILIATION> --store <scratchpad>/downloads [--check]

--check rebuilds in memory and fails if any output differs from the file on disk.
Matching uses deterministic keys only (neutral citation; normalised SCR report
citation; case type+number+year together with decision date). Title similarity is
never used for grouping; a date plus party-token test is reported only as a
candidate for curated records that carry no other key.
Nothing here authenticates a copy or changes a legal status.
"""
import argparse, csv, difflib, hashlib, io, json, os, re, subprocess, sys
from collections import defaultdict, Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import judicial_c10_data as D  # noqa: E402

RAW = "ad77758d4569ba6aafa955cc7843d874489e10f7"
STG = "21e73b8348767d5f1524167fcec538e1aad6e732"
PR40 = "9a6f9366a0de45b8443287040421d65ac550f11e"
PR41 = "cfc52d5792796050dcae351afda5609f7db41a5f"
C5 = "legal_knowledge/audit_work/SOURCE-LIBRARY-C5/registers/"
WSB = "legal_knowledge/audit_work/WS-B-JUDGMENTS/"
C8 = "legal_knowledge/audit_work/C8-EVIDENCE/SC-T2/"
C9SC = "legal_knowledge/audit_work/C9-EVIDENCE-CLEAN/SC-C9/"
C9C = "legal_knowledge/audit_work/C9-LEGAL-EVIDENCE/CORRECTIONS/"


# ----------------------------------------------------------------- io helpers
class Git:
    def __init__(self, repo):
        self.repo = repo
        self.p = subprocess.Popen(["git", "-C", repo, "cat-file", "--batch"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)

    def blob(self, commit, path):
        self.p.stdin.write(f"{commit}:{path}\n".encode()); self.p.stdin.flush()
        hdr = self.p.stdout.readline().split()
        if len(hdr) < 3 or hdr[1] != b"blob":
            raise SystemExit(f"missing git object {commit[:8]}:{path}")
        n = int(hdr[2]); data = self.p.stdout.read(n); self.p.stdout.read(1)
        return data

    def text(self, commit, path):
        return self.blob(commit, path).decode("utf-8")

    def ls(self, commit, path):
        out = subprocess.run(["git", "-C", self.repo, "ls-tree", "-r", "--name-only", commit, path], capture_output=True, text=True, check=True).stdout
        return out.split("\n")[:-1]


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def rows(text):
    return list(csv.DictReader(io.StringIO(text)))


def nows(s):
    return re.sub(r"\s+", "", s or "")


def csv_bytes(header, data):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    for r in data:
        w.writerow([r.get(h, "") if isinstance(r, dict) else r[i] for i, h in enumerate(header)])
    return buf.getvalue().encode("utf-8")


# ------------------------------------------------------------- key parsing
MONTHS = {m: i + 1 for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august",
                                          "september", "october", "november", "december"])}
TYPE_MAP = [
    (r"civil\s*appeals?|c\.\s*a\.", "CA"),
    (r"criminal\s*appeals?|appeal\s*\(crl\.?\)|crl\.\s*a\.", "CRLA"),
    (r"writ\s*petitions?\s*\(\s*c(?:ivil)?\s*\)|w\.\s*p\.\s*\(\s*c\s*\)", "WPC"),
    (r"writ\s*petitions?\s*\(\s*(?:crl\.?|criminal)\s*\)|w\.\s*p\.\s*\(\s*(?:crl\.?|criminal)\s*\)", "WPCRL"),
    (r"writ\s*petitions?|w\.\s*p\.", "WP"),
]
CASE_RE = re.compile(r"(" + "|".join(p for p, _ in TYPE_MAP) + r")\s*(?:nos?\s*\.*|no\s*\(s\)\.?|nos\(s\)\.?)?\s*(\d+)(?:\s*[-–]\s*\d+)?\s*(?:of|/)\s*(\d{4})", re.I)


def case_keys(text):
    out = []
    for m in CASE_RE.finditer(text or ""):
        t = m.group(1)
        typ = next(code for p, code in TYPE_MAP if re.fullmatch(p, t, re.I) or re.match(p, t, re.I))
        k = f"{typ}|{int(m.group(2))}|{m.group(3)}"
        if k not in out:
            out.append(k)
    return out


def hc_case_key(cn):
    parts = cn.split("/")
    if len(parts) < 3:
        return None
    typ = re.sub(r"[^A-Z]", "", parts[0].upper())
    try:
        return f"HC:{typ}|{int(parts[-2])}|{parts[-1][:4]}"
    except ValueError:
        return None


def neutral_keys(text):
    return sorted({f"{a} INSC {int(b)}" for a, b in re.findall(r"\b(\d{4})\s+INSC\s+(\d+)\b", text or "")})


SCR_PATTERNS = [
    re.compile(r"\[(\d{4})\]\s*(SUPP\.?|Suppl\.?|Supp\.?)?\s*(\d+)\s*S\.?\s?C\.?\s?R\.?\s*(\d+)", re.I),          # [1990] SUPP. 1 S.C.R. 44 ; [2013] 16 SCR 495
    re.compile(r"(\d{4})\s+SCR\s+(Supl\.?|Supp\.?)?\s*\((\d+)\)\s*(\d+)", re.I),                                # 1988 SCR (1) 512 ; 1990 SCR Supl. (1) 44
    re.compile(r"(\d{4})\s+(Supp\.?|Suppl\.?)\s*\((\d+)\)\s*SCR\s*(\d+)", re.I),                                # 1990 Supp (1) SCR 44
    re.compile(r"\(?(\d{4})\)?\s+()\(?(\d+)\)?\s+SCR\s+(\d+)", re.I),                                           # 1983 1 SCR 393 ; (2020) 3 SCR 833 ; 2003 (3) SCR 881
    re.compile(r"(\d{4})\s+SCR\s+()\((\d+)\)\s*(\d+)", re.I),
]


def scr_keys(text):
    out = []
    for pat in SCR_PATTERNS:
        for m in pat.finditer(text or ""):
            y, supp, v, p = m.group(1), m.group(2), m.group(3), m.group(4)
            k = f"SCR|{y}|{'S' if supp else ''}{int(v)}|{int(p)}"
            if k not in out:
                out.append(k)
    return out


def date_from_text(text, last=True):
    found = []
    for m in re.finditer(r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})\s*,?\s*(\d{4})", text or "", re.I):
        found.append(f"{m.group(3)}-{MONTHS[m.group(1).lower()]:02d}-{int(m.group(2)):02d}")
    for m in re.finditer(r"DATE OF JUDGMENT:?\s*(\d{2})/(\d{2})/(\d{4})", text or ""):
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    if not found:
        return ""
    return found[-1] if last else found[0]


STOP = set("union india others other and the of state lt col colonel major general maj gen ex sep hav havildar sgt wing commander cdr "
           "secretary ministry defence anr ors etc main judgment clarification order review through its connected cases retd "
           "sub naik sepoy cfn sri shri smt mr dr v vs versus singh kumar".split())


def party_tokens(title):
    return [t for t in re.findall(r"[A-Za-z]{4,}", title or "") if t.lower() not in STOP]


# ------------------------------------------------------------------ build
def build(args):
    g = Git(args.repo)
    W = args.out
    inputs = {}

    # C10 outputs, hash-checked
    c10 = args.c10
    man = json.load(open(os.path.join(c10, "outputs", "RECONCILIATION_MANIFEST.json")))
    inv_b = open(os.path.join(c10, "outputs", "UNIFIED_CORPUS_INVENTORY.csv"), "rb").read()
    if sha256(inv_b) != man["outputs"]["UNIFIED_CORPUS_INVENTORY.csv"]:
        raise SystemExit("C10 inventory hash differs from RECONCILIATION_MANIFEST.json")
    inputs["c10/outputs/UNIFIED_CORPUS_INVENTORY.csv"] = sha256(inv_b)
    side_b = open(os.path.join(c10, "inputs", "hf_snapshot", "lk_declared_sidecars.tsv"), "rb").read()
    inputs["c10/inputs/hf_snapshot/lk_declared_sidecars.tsv"] = sha256(side_b)
    hfr_b = open(os.path.join(W, "inputs", "hf_lk_text_readings.json"), "rb").read()
    inputs["workstream/inputs/hf_lk_text_readings.json"] = sha256(hfr_b)
    hfr = json.loads(hfr_b)
    hf_pages = {p["ref"]: p for p in hfr["pages"]}

    inv = [r for r in rows(inv_b.decode()) if r["category"] in ("judgment", "JUDICIAL")]

    # git inputs
    def gtext(commit, path):
        b = g.blob(commit, path); inputs[f"git:{commit[:8]}:{path}"] = sha256(b); return b.decode("utf-8")

    cases = [json.loads(l) for l in gtext(STG, "legal_knowledge/curated_originals/case_law/v0.9/cases_53.jsonl").splitlines() if l.strip()]
    kb = {json.loads(l)["id"]: json.loads(l) for l in gtext(STG, "legal_knowledge/curated_originals/knowledge_base/v0.9/records_658.jsonl").splitlines() if l.strip()}
    c5master = rows(gtext(STG, C5 + "source_master_register.csv"))
    c5copy = rows(gtext(STG, C5 + "source_copy_register.csv"))
    wsb_id = rows(gtext(STG, WSB + "identity_resolution.csv"))
    wsb_hold = rows(gtext(STG, WSB + "holdings_register.csv"))
    c8reg = rows(gtext(PR40, C8 + "sc_copy_evidence_register.csv"))
    c9scan = rows(gtext(PR40, C9SC + "judis_scan_c9.csv"))
    c9find = rows(gtext(PR41, C9C + "consolidated_finding_register.csv"))
    rawman = {r["sha256"]: r for r in rows(gtext(RAW, "data/raw_manifest.csv"))}
    excluded = [json.loads(l) for l in gtext(RAW, "data/excluded_judgments.jsonl").splitlines() if l.strip()]

    meta_paths = [p for p in g.ls(RAW, "data/meta") if p.startswith("data/meta/sc-") or p.startswith("data/meta/hc-")]
    metas = {}
    h = hashlib.sha256()
    for p in meta_paths:
        b = g.blob(RAW, p); h.update(p.encode() + b"\0" + b); metas[p[10:-5]] = json.loads(b)
    inputs[f"git:{RAW[:8]}:data/meta/(sc-*,hc-*) [{len(metas)} files, path+bytes digest]"] = h.hexdigest()
    texts = {}
    h = hashlib.sha256()
    for did in sorted(metas):
        p = f"data/text/{did}.txt"
        try:
            b = g.blob(RAW, p)
        except SystemExit:
            continue
        h.update(p.encode() + b"\0" + b); texts[did] = b.decode("utf-8", "replace")
    inputs[f"git:{RAW[:8]}:data/text (judgment texts) [{len(texts)} files, path+bytes digest]"] = h.hexdigest()

    def pages_of(text):
        parts = re.split(r"\[\[page (\d+)\]\]", text)
        return {int(parts[i]): parts[i + 1] for i in range(1, len(parts) - 1, 2)}

    # working store, re-hashed
    import pymupdf  # PyMuPDF; required for working-store readings
    wt_pages = {}
    for s8, (rel, full) in sorted(D.WT_FILES.items()):
        b = open(os.path.join(args.store, rel), "rb").read()
        if sha256(b) != full:
            raise SystemExit(f"working copy {rel} does not re-hash to {full}")
        doc = pymupdf.open(stream=b, filetype="pdf")
        wt_pages[s8] = {i + 1: pg.get_text() for i, pg in enumerate(doc)}
        inputs[f"store:{rel}"] = full

    def page_text(ref, page):
        if ref.startswith("gh:"):
            pg = pages_of(texts[ref[3:]])
            return "\n".join(pg.values()) if page is None else pg.get(page, "")
        if ref.startswith("wt:"):
            pg = wt_pages[ref[3:]]
            return "\n".join(pg.values()) if page is None else pg.get(page, "")
        if ref.startswith("hf:"):
            return hf_pages[ref]["excerpt"]
        raise SystemExit(f"bad ref {ref}")

    def verify(ref, page, quote, rid):
        if nows(quote) not in nows(page_text(ref, page)):
            raise SystemExit(f"{rid}: quotation not found in {ref} page {page}: {quote[:80]}")

    # ------------------------------------------------------ copy universe
    c5_by_sha = defaultdict(list)
    for r in c5copy:
        c5_by_sha[r["sha256"]].append(r)
    c8_by_sha = {r["sha256"]: r for r in c8reg}
    c9_scan_sha = {r["sha256"] for r in c9scan}
    sidecars = {r["declared_sha256"]: r for r in rows(side_b.decode().replace("\t", ","))} if False else {}
    for line in side_b.decode().splitlines()[1:]:
        f = line.split("\t")
        sidecars[f[1]] = {"path": f[0], "source_url": f[3], "tier": f[4]}
    meta_by_sha = defaultdict(list)
    for did, m in metas.items():
        meta_by_sha[m["sha256"]].append(did)

    copies = {}
    for r in inv:
        s = r["sha256"]
        c = dict(sha=s, bytes=r["bytes"], presence=r["presence"], hf_paths=r["hf_paths"], gh_paths=r["gh_raw_data_paths"],
                 wt_paths=r["c5_working_store_paths"], source_url=r["source_url"] or sidecars.get(s, {}).get("source_url", ""),
                 retrieved_at=r["retrieved_at"], register_state=r["register_state"], c5_copy_ids=r["c5_copy_ids"],
                 c5_status=r["c5_copy_evidence_class"], doc_ids=sorted(meta_by_sha.get(s, [])), keys=defaultdict(list),
                 key_evidence=[], flags=[], court="", title=r["title"])
        s8 = s[:8]
        if c["doc_ids"]:
            m = metas[c["doc_ids"][0]]
            c["court"] = m.get("court") or ""
            c["rendition"] = "SCR_REPORT_RENDITION_AWS_ESCR_MIRROR" if m["source"] == "sci" else "HC_COURT_PDF_AWS_ECOURTS_MIRROR"
            c["title"] = m.get("title", "")
            for did in c["doc_ids"]:
                m = metas[did]
                for n in [m.get("neutral_citation")] if m.get("neutral_citation") else []:
                    c["keys"]["neutral"] += [k for k in neutral_keys(n) if k not in c["keys"]["neutral"]]
                for rc in m.get("reported_citations") or []:
                    c["keys"]["scr"] += [k for k in scr_keys(rc) if k not in c["keys"]["scr"]]
                if m.get("issue_date") and m["issue_date"] not in c["keys"]["date"]:
                    c["keys"]["date"].append(m["issue_date"])
                if m["source"] == "sci":
                    pg = pages_of(texts.get(did, ""))
                    for k in case_keys(pg.get(1, "") + pg.get(2, "")):
                        if k not in c["keys"]["case"]:
                            c["keys"]["case"].append(k)
                else:
                    for cn in m.get("case_numbers") or []:
                        k = hc_case_key(cn)
                        if k and k not in c["keys"]["case"]:
                            c["keys"]["case"].append(k)
            c["key_evidence"].append("crawler meta (e-SCR / eCourts index fields) + SCR p.1-2 text for SC case numbers")
            if len(c["doc_ids"]) > 1:
                c["flags"].append(f"ONE_COPY_{len(c['doc_ids'])}_CRAWLER_META_RECORDS")
        else:
            c["court"] = "Supreme Court of India"
            c["rendition"] = D.NONCRAWLER_RENDITION.get(s8, "UNCLASSIFIED")
            src_pages = None
            if s8 in wt_pages:
                src_pages = wt_pages[s8]; ev = "held working copy text (PyMuPDF)"
            elif s8 == "88f84411":
                src_pages = {1: hf_pages["hf:DCLR-SC-1964-A11:1"]["excerpt"]}; ev = "HF working text p.1 (bytes NOT_CHECKED)"
            elif s8 == "cce64004":
                src_pages = {1: hf_pages["hf:DCLR-SC-2016-L04:1"]["excerpt"]}; ev = "HF working text p.1 (bytes NOT_CHECKED)"
            if src_pages:
                first = "\n".join(src_pages[i] for i in sorted(src_pages)[:4])
                lastp = "\n".join(src_pages[i] for i in sorted(src_pages)[-2:])
                c["keys"]["neutral"] = neutral_keys(src_pages[sorted(src_pages)[0]])
                c["keys"]["case"] = case_keys(first)
                c["keys"]["scr"] = scr_keys(src_pages[sorted(src_pages)[0]]) if c["rendition"] == "JUDIS_TYPED_TEXT_RENDITION" else []
                d = date_from_text(first) if c["rendition"] == "JUDIS_TYPED_TEXT_RENDITION" else date_from_text(lastp)
                c["keys"]["date"] = [d] if d else []
                c["key_evidence"].append(ev)
            for kname, (val, ev2) in D.DECLARED_KEYS.get(s8, {}).items():
                if not c["keys"][kname]:
                    c["keys"][kname] = [val]; c["key_evidence"].append(f"{kname}: {ev2}")
            if s8 == "10e1954f":
                c["flags"].append("CONTAINS_CORRECTED_SECOND_VERSION_PP32-62 (C9 Q-MULLIKOTE-VERSION)")
            if s8 in sidecars:
                c["flags"].append(f"HF_LEGAL_KNOWLEDGE_SIDECAR_TIER={sidecars[s8]['tier']}")
        copies[s] = c

    # ------------------------------------------------------------ grouping
    parent = {s: s for s in copies}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x

    def union(a, b, basis):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)
        edges.append((a, b, basis))

    edges = []
    idx = defaultdict(list)
    for s, c in copies.items():
        sc = "SC" if "Supreme" in c["court"] else "HC"
        for k in c["keys"]["neutral"]:
            idx[("N", k)].append(s)
        for k in c["keys"]["scr"]:
            idx[("S", k)].append(s)
        for k in c["keys"]["case"]:
            for d in c["keys"]["date"]:
                idx[("CD", sc, k, d)].append(s)
    for key, ss in sorted(idx.items()):
        for other in ss[1:]:
            basis = {"N": "NEUTRAL_CITATION", "S": "SCR_REPORT_CITATION", "CD": "CASE_NUMBER+DECISION_DATE"}[key[0]]
            union(ss[0], other, f"{basis}={key[-1] if key[0] != 'CD' else key[2] + '@' + key[3]}")
    groups = defaultdict(list)
    for s in copies:
        groups[find(s)].append(s)
    basis_by_group = defaultdict(set)
    for a, b, basis in edges:
        basis_by_group[find(a)].add(basis)

    OFFICIAL = {"SC_OFFICIAL_COURT_PDF": "YES_OFFICIAL_COURT_PDF", "JUDIS_PATH_COURT_LAYOUT_PDF": "YES_COURT_HOSTED_JUDIS_PATH_LAYOUT",
                "SC_ROP_PATH_COPY": "YES_COURT_HOSTED_ROP_PATH", "OTHER_COURT_SYSTEM_COPY_BOSIR": "YES_COURT_SYSTEM_BOSIR"}
    group_info = {}
    for root, ss in groups.items():
        ss.sort()
        gid = "JG-" + root[:12]
        rends = sorted({copies[s]["rendition"] for s in ss})
        locs = sum(len([p for p in (copies[s]["hf_paths"] + ";" + copies[s]["gh_paths"] + ";" + copies[s]["wt_paths"]).split(";") if p]) for s in ss)
        if len(ss) == 1:
            cls = "EXACT_DUPLICATE" if (locs > 1 or len(copies[ss[0]]["doc_ids"]) > 1) else "SINGLE_COPY"
        else:
            cls = "MULTIPLE_COPIES_SAME_JUDGMENT" if len(rends) == 1 else "DIFFERENT_RENDITION"
            if len({d for s in ss for d in copies[s]["keys"]["date"]}) > 1 and len(rends) == 1:
                cls = "SAME_KEY_DIFFERENT_DECISION_DATES_REVIEW"
        extra = []
        if any("CORRECTED" in f for s in ss for f in copies[s]["flags"]):
            extra.append("CORRECTED_JUDGMENT")
        is_sc = any("Supreme" in copies[s]["court"] for s in ss)
        off = sorted({OFFICIAL[r] for r in rends if r in OFFICIAL})
        if is_sc:
            official = ";".join(off) if off else ("NO_" + "+".join(r.split("_")[0] + "_" + r.split("_")[1] for r in rends))
            if not off:
                extra.append("MISSING_OFFICIAL_ORIGINAL")
        else:
            official = "HC_COURT_PDF_VIA_THIRD_PARTY_MIRROR (parity with court-hosted copy NOT checked)"
        incon = []
        for kname in ("date", "neutral", "scr"):
            vals = sorted({v for s in ss for v in copies[s]["keys"][kname]})
            if len(ss) > 1 and len(vals) > 1:
                incon.append(f"{kname.upper()}_DIFFERS:{'|'.join(vals)}")
        group_info[root] = dict(gid=gid, cls=";".join([cls] + extra), basis=";".join(sorted(basis_by_group[root])) or ("SAME_SHA256" if cls == "EXACT_DUPLICATE" else "-"),
                                official=official, incon=incon, n=len(ss), is_sc=is_sc)

    # ------------------------------------------------------ curated linking
    c5cross = defaultdict(list)
    for r in rows(gtext(STG, C5 + "corpus_crosswalk.csv")):
        if r["source_id"].startswith("C5-SRC-J") and r["case_id"] and r["source_id"] not in c5cross[r["case_id"]]:
            c5cross[r["case_id"]].append(r["source_id"])
    hf_side_case = {v["sha256"]: v["case_id"] for v in hfr["sidecars"].values()}
    case_link = {}
    for cs in cases:
        cid = cs["id"]
        keys = dict(neutral=neutral_keys(cs.get("reporter_citation") or ""), scr=scr_keys(cs.get("reporter_citation") or ""),
                    case=case_keys(cs.get("case_number") or ""), date=[cs["decision_date"]] if cs.get("decision_date") else [])
        hits = defaultdict(set)
        for s, c in copies.items():
            if "Supreme" not in c["court"]:
                continue
            for k in keys["neutral"]:
                if k in c["keys"]["neutral"]:
                    hits[find(s)].add("NEUTRAL_CITATION=" + k)
            for k in keys["scr"]:
                if k in c["keys"]["scr"]:
                    hits[find(s)].add("SCR_REPORT_CITATION=" + k)
            for k in keys["case"]:
                if k in c["keys"]["case"] and set(keys["date"]) & set(c["keys"]["date"]):
                    hits[find(s)].add("CASE_NUMBER+DECISION_DATE=" + k)
        for s, c in copies.items():
            for cx in c5cross.get(cid, []):
                if cx in c["c5_copy_ids"].split(";") or any(x.split("~")[0] == cx for x in c["c5_copy_ids"].split(";") if x):
                    hits[find(s)].add("C5_CROSSWALK_DECLARED=" + cx)
            sc_case = hf_side_case.get(s)
            if sc_case == cid:
                hits[find(s)].add("HF_SIDECAR_CASE_ID_DECLARED")
        cands = defaultdict(set)
        toks = party_tokens(cs["title"])
        for s, c in copies.items():
            if "Supreme" not in c["court"] or find(s) in hits:
                continue
            if set(keys["date"]) & set(c["keys"]["date"]) and any(t.upper() in (c["title"] or "").upper() for t in toks):
                cands[find(s)].add("DATE+PARTY_TOKEN (candidate only)")
        exhits = [e for e in excluded if "Supreme" in (e.get("court") or "") and e.get("decided") in keys["date"]
                  and any(t.upper() in e["title"].upper() for t in toks)]
        case_link[cid] = dict(keys=keys, hits=hits, cands=cands, excluded=exhits, toks=toks)

    copy_cases = defaultdict(set)
    for cid, L in case_link.items():
        for root in L["hits"]:
            for s in groups[root]:
                copy_cases[s].add(cid)
    wsb_by_sha = defaultdict(set)
    wsb_by_case = {}
    for r in wsb_id:
        for col in ("intern_sha256", "held_copy_sha256"):
            if r[col]:
                wsb_by_sha[r[col]].add(r["spec_key"])
        if r["case53_id"]:
            wsb_by_case[r["case53_id"]] = r

    # ------------------------------------------------ JUDGMENT_RECONCILIATION
    rec = []
    for root in sorted(groups, key=lambda r: group_info[r]["gid"]):
        gi = group_info[root]
        for s in groups[root]:
            c = copies[s]
            host = re.sub(r"^https?://([^/]+)/.*$", r"\1", c["source_url"]) if c["source_url"] else ""
            ev = []
            if s in c8_by_sha:
                ev.append("C8 sc_copy_evidence_register")
            if s in c9_scan_sha:
                ev.append("C9 judis_scan")
            rec.append(dict(
                group_id=gi["gid"], group_class=gi["cls"], group_size=gi["n"], group_match_basis=gi["basis"],
                copy_sha256=s, bytes=c["bytes"], court=c["court"], rendition_type=c["rendition"],
                official_court_copy_in_group=gi["official"], presence=c["presence"],
                hf_paths=c["hf_paths"], github_raw_data_paths=c["gh_paths"], working_store_paths=c["wt_paths"],
                source_url=c["source_url"], source_host=host, retrieved_at=c["retrieved_at"],
                crawler_doc_ids=";".join(c["doc_ids"]), title=c["title"],
                neutral_citations=";".join(c["keys"]["neutral"]), scr_report_citations=";".join(c["keys"]["scr"]),
                case_number_keys=";".join(c["keys"]["case"]), decision_dates=";".join(c["keys"]["date"]),
                key_evidence=" | ".join(c["key_evidence"]),
                c5_copy_ids=c["c5_copy_ids"], c5_copy_evidence_class=c["c5_status"], register_state=c["register_state"],
                cases53_ids=";".join(sorted(copy_cases.get(s, []))), wsb_spec_keys=";".join(sorted(wsb_by_sha.get(s, []))),
                c8_c9_evidence=";".join(ev), copy_flags=";".join(c["flags"]), group_inconsistencies=";".join(gi["incon"]),
                hf_byte_verification="NOT_CHECKED" if c["hf_paths"] else "", authentication="NOT_AUTHENTICATED_BY_THIS_WORKSTREAM"))
    rec_header = list(rec[0].keys())

    # ------------------------------------------------- per curated case table
    cur = []
    for cs in cases:
        cid = cs["id"]; L = case_link[cid]
        roots = sorted(L["hits"])
        ss = [s for r in roots for s in groups[r]]
        hfp = sorted({p for s in ss for p in copies[s]["hf_paths"].split(";") if p})
        hf_raw = [p for p in hfp if p.startswith("data/raw/")]
        hf_lk = [p for p in hfp if p.startswith("legal_knowledge/")]
        ghp = sorted({p for s in ss for p in copies[s]["gh_paths"].split(";") if p})
        wtp = sorted({p for s in ss for p in copies[s]["wt_paths"].split(";") if p})
        rends = sorted({copies[s]["rendition"] for s in ss})
        off = sorted({OFFICIAL[r] for r in rends if r in OFFICIAL})
        c5ids = sorted({x for s in ss for x in copies[s]["c5_copy_ids"].split(";") if x})
        if not ss:
            c5state = "NOT_HELD"
        elif c5ids:
            c5state = "REGISTERED (" + ";".join(c5ids) + ")" + ("; ALSO_HELD_UNREGISTERED_COPIES" if any(not copies[s]["c5_copy_ids"] for s in ss) else "")
        else:
            c5state = "HELD_UNREGISTERED"
        w = wsb_by_case.get(cid, {})
        wstate = w.get("identity_state", "")
        held_now = "HELD" if ss else "NOT_HELD"
        cand_ss = sorted({s for r in L["cands"] for s in groups[r]})
        wsb_decl = [w[col] for col in ("intern_sha256", "held_copy_sha256") if w.get(col) in copies and w[col] not in ss]
        if not ss and cand_ss:
            held_now = "CANDIDATE_HELD_DATE+PARTY_ONLY (curated record has no other deterministic key matching)"
        elif not ss and wsb_decl:
            held_now = "CANDIDATE_HELD_WSB_DECLARED_LINK_ONLY (curated record carries no date, case number or citation)"
        change = ""
        if wstate and ("NO_COPY" in wstate or wstate.startswith("UNRESOLVED")) and ss:
            change = f"HELD_STATUS_CHANGED: WS-B '{wstate}' but C10 finds held copies ({';'.join(sorted(set(copies[s]['presence'] for s in ss)))})"
        elif wstate.endswith("NOT_IN_INTERN") and any(copies[s]["doc_ids"] for s in ss):
            change = "HELD_STATUS_CHANGED: crawler copy found"
        # inconsistencies
        inc = []
        kd = L["keys"]["date"]
        cdates = sorted({d for s in ss for d in copies[s]["keys"]["date"]})
        if ss and not kd and cdates:
            inc.append("CURATED_DATE_EMPTY; copies give " + "|".join(cdates))
        elif kd and cdates and kd[0] not in cdates:
            inc.append(f"DATE_MISMATCH curated {kd[0]} vs copies {'|'.join(cdates)}")
        cscr = sorted({k for s in ss for k in copies[s]["keys"]["scr"]})
        if L["keys"]["scr"] and cscr and not set(L["keys"]["scr"]) & set(cscr):
            inc.append(f"SCR_MISMATCH curated {'|'.join(L['keys']['scr'])} vs copies {'|'.join(cscr)}")
        for root in L["cands"]:
            for s in groups[root]:
                cscr2 = copies[s]["keys"]["scr"]
                if L["keys"]["scr"] and cscr2 and not set(L["keys"]["scr"]) & set(cscr2):
                    inc.append(f"CANDIDATE_SCR_CONFLICT curated {'|'.join(L['keys']['scr'])} vs {copies[s]['title'][:40]} {'|'.join(cscr2)}")
        if not (cs.get("case_number") or "").strip() and any(copies[s]["keys"]["case"] for s in ss):
            inc.append("CURATED_CASE_NUMBER_EMPTY; copies print " + "|".join(sorted({k for s in ss for k in copies[s]["keys"]["case"]})))
        cand_desc = ";".join(f"{group_info[r]['gid']}({copies[groups[r][0]]['title'][:50]})" for r in sorted(L["cands"]))
        exc = ";".join(f"{e['decided']}|{e['sha256'][:16]}|{e['doc_id']}" for e in L["excluded"])
        if exc and not ss:
            held_now = "NOT_HELD_EXCLUDED_FROM_CRAWLER_STORE"
        cur.append(dict(
            case_id=cid, title=cs["title"], curated_decision_date=cs.get("decision_date") or "", curated_case_number=cs.get("case_number") or "",
            curated_reporter_citation=cs.get("reporter_citation") or "",
            deterministic_keys=" ".join(f"{k}:{'|'.join(v)}" for k, v in L["keys"].items() if v),
            linked_groups=";".join(group_info[r]["gid"] for r in roots),
            link_basis=";".join(sorted(b for r in roots for b in L["hits"][r])),
            held_status_c10=held_now, copies_held=len(ss), renditions=";".join(rends),
            official_court_copy_held=";".join(off) if off else (("NO_SIGNED_OR_OFFICIAL_COURT_PDF; held: " + "+".join(rends)) if ss else "NO_COPY_HELD"),
            candidate_or_declared_copies=";".join(f"{x[:8]}:{copies[x]['rendition']}:{copies[x]['presence']}" for x in sorted(set(cand_ss) | set(wsb_decl))),
            hf_data_raw_paths=";".join(hf_raw), hf_legal_knowledge_paths=";".join(hf_lk), github_raw_data_paths=";".join(ghp),
            working_store_paths=";".join(wtp), c5_register_status=c5state, wsb_spec_key=w.get("spec_key", ""), wsb_identity_state=wstate,
            change_vs_wsb=change,
            wsb_shas_in_c10_link=("YES" if w and all((not w.get(col)) or any(x == w[col] for x in ss) for col in ("intern_sha256", "held_copy_sha256")) else ("NO" if w else "")),
            date_party_candidates=cand_desc, excluded_log_hits=exc, inconsistencies=";".join(inc),
            hf_byte_verification="NOT_CHECKED" if hfp else ""))
    cur_header = list(cur[0].keys())

    # ------------------------------------------------- SCR identity rows
    scr_targets = {"RANJIT": "35b9c948", "SN_MUKHERJEE": "239c4e38", "DHARAMVIR": "a9ccc45c", "RAJBIR": "c1ecdaee", "GIRISH": "da030473",
                   "NS_YADAV": "d031a88d", "PPS_BEDI": "ebb86d4b", "TARSEM": "f8a14181", "PARASHOTAM": "483b70cb", "SHRIKANT": "86de3643",
                   "SPRATHORE": "2f89730f", "PS_GILL": "009ea86c"}
    eight = {"RANJIT", "SN_MUKHERJEE", "DHARAMVIR", "RAJBIR", "GIRISH", "NS_YADAV", "PPS_BEDI"}
    s8map = {s[:8]: s for s in copies}
    scr_rows = []
    for key in ["RANJIT", "SN_MUKHERJEE", "NAVJOT", "DHARAMVIR", "RAJBIR", "GIRISH", "MULLIKOTE", "NS_YADAV", "PPS_BEDI", "TARSEM",
                "PARASHOTAM", "SHRIKANT", "SPRATHORE", "PS_GILL"]:
        if key not in scr_targets:
            scr_rows.append(dict(case_key=key, scope="C8/C9 eight" if key in ("NAVJOT", "MULLIKOTE") else "", scr_sha256="",
                                 other_copies_found="NONE in crawler raw store or HF legal_knowledge beyond the C5 copy" + (" (HF legal_knowledge holds the same sha 3b753548 as the C5 copy: exact duplicate)" if key == "NAVJOT" else ""),
                                 printed_report_citation="", escr_filename_start_page="", start_page_printed_p1="", printed_case_number="", printed_date="", printed_bench="", printed_author="",
                                 crawler_meta_neutral="", crawler_meta_judges="", crawler_title="", pages="", raw_path="", source_url="", source_host="",
                                 retrieved_at="", provenance_class="", register_state="", identity_consistency=""))
            continue
        s = s8map[scr_targets[key]]; c = copies[s]; did = c["doc_ids"][0]; m = metas[did]
        pg = pages_of(texts[did]); p1 = pg.get(1, "") + "\n" + pg.get(2, "")
        cit = scr_keys(p1[:3000])[:1]
        fn = re.match(r"(S_)?(\d{4})_(\d+)_(\d+)_(\d+)_EN\.pdf", m.get("original_filename", "") or "")
        start_pg = fn.group(4) if fn else ""
        start_printed = "YES" if start_pg and re.search(r"(?m)^\s*" + start_pg + r"\s*$", pg.get(1, "")) else "NO"
        bench = re.search(r"\[([^\[\]]{5,160}?JJ?\.?)\]", p1.replace("\n", " "))
        author = re.search(r"delivered\s*_?\s*by\s*:?\s*\n*\s*([A-Z][A-Z .,]{2,40}?J\.)", texts[did])
        MON = r"(?:JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)"
        head = pg.get(1, "")[:350]
        dt = re.search(MON + r"\s*\d{1,2}\s*[,.]?\s*\d{4}", head, re.I) or re.search(r"\b\d{1,2}\s+" + MON + r"\s+\d{4}", head, re.I)
        cn = case_keys(p1)
        rm = rawman.get(s, {})
        same = []
        def _iso(x):
            mm = re.search(r"([A-Za-z]+)\s*(\d{1,2})\s*[,.]?\s*(\d{4})", x) or None
            if mm and mm.group(1).lower() in MONTHS:
                return f"{mm.group(3)}-{MONTHS[mm.group(1).lower()]:02d}-{int(mm.group(2)):02d}"
            mm = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", x)
            return f"{mm.group(3)}-{MONTHS[mm.group(2).lower()]:02d}-{int(mm.group(1)):02d}" if mm and mm.group(2).lower() in MONTHS else ""
        same.append("DATE_OK" if dt and _iso(dt.group(0)) in c["keys"]["date"] else ("DATE_NOT_LEGIBLE_IN_TEXT_LAYER" if not dt else "DATE_DIFFERS"))
        same.append("START_PAGE_OK" if start_printed == "YES" else "START_PAGE_NOT_FOUND")
        same.append("SCR_OK" if set(cit) & set(c["keys"]["scr"]) else ("SCR_NOT_PRINTED_BRACKETED_P1" if not cit else "SCR_DIFFERS"))
        grp = group_info[find(s)]
        others = [copies[o] for o in groups[find(s)] if o != s]
        scr_rows.append(dict(
            case_key=key, scope="C8/C9 eight" if key in eight else ("PPS Bedi" if key == "PPS_BEDI" else "priority/other"),
            scr_sha256=s, other_copies_found=";".join(f"{o['sha'][:8]}:{o['rendition']}:{o['presence']}" for o in others) or "NONE",
            printed_report_citation=";".join(cit) or "(no bracketed citation on p.1-2)",
            escr_filename_start_page=start_pg, start_page_printed_p1=start_printed, printed_case_number=";".join(cn), printed_date=dt.group(0) if dt else "",
            printed_bench=bench.group(1).strip() if bench else "", printed_author=author.group(1).strip() if author else "",
            crawler_meta_neutral=m.get("neutral_citation") or "", crawler_meta_judges=";".join(m.get("judges") or []), crawler_title=m.get("title", ""),
            pages=m.get("page_count", ""), raw_path=rm.get("raw_path", ""), source_url=rm.get("source_url", ""),
            source_host=re.sub(r"^https?://([^/]+)/.*$", r"\1", rm.get("source_url", "")), retrieved_at=rm.get("retrieved_at", ""),
            provenance_class="THIRD_PARTY_MIRROR (AWS Open Data 'indian-supreme-court-judgments', copy of e-SCR records; CC-BY-4.0 per crawler curation_note); NOT a signed court original",
            register_state=c["register_state"] + ("; group " + grp["gid"] + " " + grp["cls"]), identity_consistency=";".join(same)))
    scr_header = list(scr_rows[0].keys())

    # ------------------------------------------------- comparator metrics + checks
    def words(t):
        t = re.sub(r"\[\[page \d+\]\]", " ", t)
        return [w for w in re.findall(r"[a-z0-9]+", t.lower()) if len(w) > 1]

    def split_at_delivered(t):
        m = re.search(r"delivered\s*_?\s*by", t, re.I)
        return (t[:m.start()], t[m.end():]) if m else ("", t)

    pairs = [("RANJIT", "ed7cf31f", "35b9c948"), ("SN_MUKHERJEE", "eb442080", "239c4e38"), ("PPS_BEDI", "211dbaf4", "ebb86d4b"),
             ("DHARAMVIR", "3056712c", "a9ccc45c"), ("RAJBIR", "970b9680", "c1ecdaee"), ("GIRISH", "4f7ea3a4", "da030473"),
             ("NS_YADAV", "3c50cdb7", "d031a88d"), ("PARASHOTAM", "fe19875b", "483b70cb"), ("PS_GILL", "7c32b8e8", "009ea86c")]
    comp = []
    for key, a8, b8 in pairs:
        at = "\n".join(wt_pages[a8][i] for i in sorted(wt_pages[a8]))
        bs = s8map[b8]; bt = texts[copies[bs]["doc_ids"][0]]
        ah, ab = split_at_delivered(at); bh, bb = split_at_delivered(bt)
        dflag = f"delivered_by_found a={'Y' if ah else 'N'} b={'Y' if bh else 'N'}"
        wa, wb = words(ab), words(bb)
        sm = difflib.SequenceMatcher(None, wa, wb, autojunk=False)
        ratio = sm.ratio()
        ha, hb = words(ah), words(bh)
        hr = difflib.SequenceMatcher(None, ha, hb, autojunk=False).ratio() if ha and hb else None
        comp.append(dict(check_id=f"SCR-M-{key}", case_key=key, kind="METRIC", copy_a=s8map.get(a8, a8) if a8 in s8map else D.WT_FILES[a8][1],
                         copy_a_rendition=D.NONCRAWLER_RENDITION.get(a8, ""), copy_b=bs, copy_b_rendition="SCR_REPORT_RENDITION_AWS_ESCR_MIRROR",
                         question="Word-sequence similarity of judgment body (after 'delivered by') and of pre-judgment matter",
                         a_ref="", a_page="", a_quote="", b_ref="", b_page="", b_quote="",
                         result=f"{dflag}; body_words a={len(wa)} b={len(wb)} ratio={ratio:.3f}; pre_judgment_words a={len(ha)} b={len(hb)} ratio={'' if hr is None else f'{hr:.3f}'}",
                         interpretation=("JUDIS headnote vs SCR headnote similarity measures whether the JUDIS 'HEADNOTE' is the reporter's editorial headnote" if D.NONCRAWLER_RENDITION.get(a8) == "JUDIS_TYPED_TEXT_RENDITION"
                                         else "official PDF has no reporter headnote; pre-judgment ratio not meaningful") + "; where 'delivered by' is absent in a copy the whole text is compared (so SCR headnote matter lowers the ratio, e.g. Girish); indicative only: the SCR text layer carries OCR noise (margin letters A-H, running heads)",
                         reader="deterministic (difflib)"))
    for ck in D.SCR_CHECKS:
        verify(ck["a_ref"], ck["a_page"], ck["a_quote"], ck["cid"] + "a")
        verify(ck["b_ref"], ck["b_page"], ck["b_quote"], ck["cid"] + "b")
        comp.append(dict(check_id=ck["cid"], case_key=ck["case"], kind="TARGETED_CHECK", copy_a=D.WT_FILES[ck["a_ref"][3:]][1] if ck["a_ref"].startswith("wt:") else ck["a_ref"],
                         copy_a_rendition=D.NONCRAWLER_RENDITION.get(ck["a_ref"][3:], ""),
                         copy_b=metas[ck["b_ref"][3:]]["sha256"], copy_b_rendition="SCR_REPORT_RENDITION_AWS_ESCR_MIRROR",
                         question=ck["question"], a_ref=ck["a_ref"], a_page=ck["a_page"] or "", a_quote=ck["a_quote"],
                         b_ref=ck["b_ref"], b_page=ck["b_page"] or "", b_quote=ck["b_quote"], result=ck["result"],
                         interpretation="SCR rendition used as comparator only; not a signed court original; existing historical classifications preserved",
                         reader=D.READER))
    comp_header = list(comp[0].keys())

    # ------------------------------------------------- treatment hits
    PATS = {
        "TARSEM": ("2008-08-13", [r"\(2008\)\s*8\s*SCC\s*648", r"2008\s+INSC\s+930", r"\[2008\]\s*12\s*S\.?C\.?R\.?\s*104"], [r"Tarsem\s+Singh"]),
        "GIRISH": ("2026-02-12", [r"2026\s+INSC\s+149\b", r"2026\s+SCC\s+OnLine\s+SC\s+194\b", r"6820\s*[-–]\s*6824\s+of\s+2018"], [r"Girish\s+Kumar"]),
        "CLAR": ("2026-10-12", [r"2026\s+INSC\s+1113\b"], [r"clarif\w+[^.]{0,120}Girish", r"Girish[^.]{0,200}clarif\w+"]),
        "PARASHOTAM": ("2023-03-21", [r"2023\s+INSC\s+265\b", r"2023\s+SCC\s+OnLine\s+(?:SC\s+)?314\b"], [r"Paras?hotam\s+Dass?"]),
        "SHRIKANT": ("2015-03-11", [r"\(2015\)\s*6\s*SCC\s*773", r"2015\s+INSC\s+206\b", r"\[2015\]\s*4\s*S\.?C\.?R\.?\s*676"], [r"Shri\s*Kant\s+Sharma"]),
        "RAMAVTAR": ("2014-12-10", [r"418\s+of\s+2012", r"418/2012"], [r"Ram\s+Avtar"]),
        "SPRATHORE": ("2019-12-11", [r"2019\s+INSC\s+1359\b", r"\(2019\)\s*19\s*SCC\s*84\b", r"10870\s+of\s+2018"], [r"S\.?\s*P\.?\s*Rathore"]),
        "ISAAC": ("2026-09-15", [r"2026\s+INSC\s+993\b"], [r"N\.?\s*C\.?\s*Isaac"]),
        "DHARAMVIR": ("2013-07-02", [r"\(2013\)\s*7\s*SCC\s*316", r"2013\s*\(7\)\s*SCC\s*316", r"2013\s+INSC\s+408\b"], [r"Dharam\s*vir\s+Singh"]),
        "RAJBIR": ("2015-02-13", [r"\(2015\)\s*12\s*SCC\s*264", r"2015\s*\(12\)\s*SCC\s*264", r"2015\s+INSC\s+114\b"], [r"Rajbir\s+Singh"]),
        "MULLIKOTE": ("2026-03-24", [r"2026\s+INSC\s+286\b"], [r"Mullikote"]),
    }
    self_docs = {"TARSEM": "sc-2008-union-of-india-ors-2008insc930", "GIRISH": "sc-2026-union-of-india-through-its-sec-2026insc149",
                 "PARASHOTAM": "sc-2023-union-of-india-ors-2023insc265", "SHRIKANT": "sc-2015-union-of-india-ors-2015insc206",
                 "SPRATHORE": "sc-2019-g-h-union-of-india-ors-2019insc1359", "DHARAMVIR": "sc-2013-dharamvir-singh-2013insc408",
                 "RAJBIR": "sc-2015-union-of-india-anr-2015insc114"}
    hits = []
    for did in sorted(texts):
        t = texts[did]; m = metas[did]
        pg = pages_of(t)
        norm = {p: re.sub(r"\s+", " ", x) for p, x in pg.items()}
        alltxt = " ".join(norm.values())
        for key, (ddate, strong, name) in PATS.items():
            if self_docs.get(key) == did:
                continue
            sp = [p for p in strong if re.search(p, alltxt, re.I)]
            npat = [p for p in name if re.search(p, alltxt, re.I)]
            if not sp and not npat:
                continue
            pages_hit = sorted({p for p, x in norm.items() for pat in sp + npat if re.search(pat, x, re.I)})
            idate = m.get("issue_date") or ""
            hits.append(dict(cited_case=key, citing_doc_id=did, citing_court=m.get("court", ""), citing_date=idate, citing_sha256=m["sha256"],
                             match_strength="CITATION_STRING" if sp else "NAME_ONLY_REVIEW_REQUIRED",
                             matched_patterns=";".join(sp + npat), pages=";".join(map(str, pages_hit[:12])),
                             timing="AFTER_DECISION" if idate >= ddate else ("SAME_DAY" if idate == ddate else "BEFORE_DECISION_NOT_A_CITATION_OF_THIS_JUDGMENT"),
                             treatment="NOT_DETERMINED (not read)" if not any(r["kind"] == "TREATMENT" and r["case"] == key and r["ref"] == "gh:" + did for r in D.READINGS)
                             else ";".join(r["cls"] for r in D.READINGS if r["kind"] == "TREATMENT" and r["case"] == key and r["ref"] == "gh:" + did) + " (see JUDICIAL_TREATMENT_C10.csv)"))
    hits_header = list(hits[0].keys())

    # ------------------------------------------------- treatment readings
    trt = []
    for r in D.READINGS:
        verify(r["ref"], r["page"], r["quote"], r["rid"])
        pr = next((p for p in D.PRIORITY if p["key"] == r["case"]), {})
        trt.append(dict(reading_id=r["rid"], cited_case=r["case"], cases53_id=pr.get("case53", ""), kind=r["kind"],
                        classification=r.get("cls", "") if r["kind"] == "TREATMENT" else "OPERATIVE_HOLDING",
                        citing_or_source=r.get("citing", ""), doc_ref=r["ref"], pdf_page=r["page"] if r["page"] is not None else "(text without page check)",
                        paragraph=r["para"], quote_verbatim=r["quote"], note=r["note"], reader=D.READER, quote_check="VERBATIM_FOUND (whitespace-insensitive)"))
    for p in D.PRIORITY:
        cnt = Counter(h["match_strength"] for h in hits if h["cited_case"] == p["key"] and h["timing"] == "AFTER_DECISION")
        trt.append(dict(reading_id=f"P-{p['key']}", cited_case=p["key"], cases53_id=p["case53"], kind="CASE_SUMMARY",
                        classification=p["overall"], citing_or_source=p["held"], doc_ref="", pdf_page="", paragraph="",
                        quote_verbatim="", note=f"IDENTITY: {p['identity']} | STATUTORY CONTEXT: {p['statutory']} | KB AFFECTED: {p['kb']} | C9: {p['c9']} | "
                                                f"held citing judgments after decision: {cnt.get('CITATION_STRING', 0)} by citation string, {cnt.get('NAME_ONLY_REVIEW_REQUIRED', 0)} by name only",
                        reader="summary of the readings above; not human-confirmed", quote_check=""))
    trt_header = list(trt[0].keys())

    # ------------------------------------------------- proposals (verbatim current text)
    props = []
    for p in D.PROPOSALS:
        tgt = p["target"]
        chk = "NOT_A_CORPUS_RECORD_FIELD (register or crawler metadata)"
        cur_txt = p["current_text"] if p["current_text"] is not None else "(empty/null)"
        if tgt.startswith("cases_53 "):
            cs = next(c for c in cases if c["id"] == tgt.split()[1])
            val = cs.get(p["field"])
            if p["current_text"] is None:
                chk = "VERIFIED_EMPTY" if not val else f"MISMATCH (value {val!r})"
            else:
                chk = "VERIFIED_VERBATIM" if (val or "") == p["current_text"] or (p["current_text"] and p["current_text"] in (val or "")) else f"MISMATCH (value {val!r})"
        elif tgt.startswith("records_658 "):
            val = kb[tgt.split()[1]].get(p["field"], "")
            chk = "VERIFIED_VERBATIM" if p["current_text"] in val else "MISMATCH"
        elif tgt.startswith("WS-B holdings_register.csv#"):
            row = next(r for r in wsb_hold if r["row_id"] == tgt.split("#")[1])
            chk = "VERIFIED_VERBATIM" if row[p["field"]] == p["current_text"] else f"MISMATCH ({row[p['field']]!r})"
        elif tgt.startswith("raw-data data/meta "):
            did = tgt.split()[2]
            val = metas[did].get(p["field"])
            cur_txt = json.dumps(val, ensure_ascii=False) if val not in (None, "", []) else "(empty/null)"  # review WS-05: verbatim current value
            chk = "VERBATIM_FROM_PINNED_RAW_DATA_META"
        if chk.startswith("MISMATCH"):
            raise SystemExit(f"{p['pid']}: current text check failed: {chk}")
        props.append(dict(proposal_id=p["pid"], target=tgt, field=p["field"], current_text=cur_txt,
                          current_text_check=chk, proposed_change=p["proposed"], priority=p["priority"], evidence=p["evidence"],
                          condition=p["condition"], status="PROPOSAL_NOT_APPLIED"))
    props_header = list(props[0].keys())
    if len(cur) != len(cases) or len(cases) != 53:  # fail closed: every curated case must have a status row
        raise SystemExit(f"curated status rows {len(cur)} != curated cases {len(cases)} (expected 53)")

    # ------------------------------------------------- C9 finding status
    c9rows = []
    for f in c9find:
        eff, why = D.C9_EFFECT.get(f["finding_id"], ("NOT_ASSESSED", ""))
        c9rows.append(dict(finding_id=f["finding_id"], matter=f["matter"], c9_priority=f["priority_evidence_standard"], c9_status=f["status"],
                           c10_effect=eff, c10_basis=why, c9_status_after_c10=f["status"]))
    missing = set(D.C9_EFFECT) - {f["finding_id"] for f in c9find}
    if missing:
        raise SystemExit(f"C9 effect rows for unknown findings: {missing}")
    c9_header = list(c9rows[0].keys())

    esc = [dict(escalation_id=e["eid"], matter=e["matter"], question=e["question"], relates_to=e["relates"], status="OPEN_FOR_ADVISER") for e in D.ESCALATIONS]
    esc_header = list(esc[0].keys())

    outputs = {
        "JUDGMENT_RECONCILIATION.csv": csv_bytes(rec_header, rec),
        "CURATED_CASE_COPY_STATUS.csv": csv_bytes(cur_header, cur),
        "SCR_COPY_IDENTITY.csv": csv_bytes(scr_header, scr_rows),
        "SCR_COMPARATOR_RESULTS.csv": csv_bytes(comp_header, comp),
        "TREATMENT_CITATION_HITS.csv": csv_bytes(hits_header, hits),
        "JUDICIAL_TREATMENT_C10.csv": csv_bytes(trt_header, trt),
        "CORRECTION_PROPOSALS_C10.csv": csv_bytes(props_header, props),
        "C9_FINDING_STATUS_C10.csv": csv_bytes(c9_header, c9rows),
        "ADVISER_ESCALATIONS_C10.csv": csv_bytes(esc_header, esc),
    }
    # counts
    gcls = Counter()
    for root, gi in group_info.items():
        for part in gi["cls"].split(";"):
            gcls[part] += 1
    sc_groups = Counter(p for gi in group_info.values() if gi["is_sc"] for p in gi["cls"].split(";"))
    summary = dict(
        copies=len(copies), groups=len(groups), groups_by_class=dict(sorted(gcls.items())), sc_groups_by_class=dict(sorted(sc_groups.items())),
        copies_by_rendition=dict(sorted(Counter(c["rendition"] for c in copies.values()).items())),
        curated_cases=len(cur), curated_held_status=dict(sorted(Counter(r["held_status_c10"] for r in cur).items())),
        curated_c5_status=dict(sorted(Counter(r["c5_register_status"].split(" (")[0] for r in cur).items())),
        curated_official_copy=dict(sorted(Counter(r["official_court_copy_held"] for r in cur).items())),
        curated_changes_vs_wsb=[r["case_id"] for r in cur if r["change_vs_wsb"]],
        treatment_hits=len(hits),
        treatment_hits_after_decision={f"{k[0]}|{k[1]}": v for k, v in sorted(Counter(
            (h["cited_case"], h["match_strength"]) for h in hits if h["timing"] == "AFTER_DECISION").items())},
        readings=len(D.READINGS), treatment_classes=dict(sorted(Counter(r["cls"] for r in D.READINGS if r["kind"] == "TREATMENT").items())),
        proposals=len(props), escalations=len(esc),
        c9_effects=dict(sorted(Counter(r["c10_effect"] for r in c9rows).items())))
    manifest = dict(schema="c10-judicial-manifest/1",
                    pinned=dict(raw_data=RAW, staging=STG, pr40_head=PR40, pr41_head=PR41),
                    inputs=dict(sorted(inputs.items())),
                    outputs={k: sha256(v) for k, v in sorted(outputs.items())},
                    summary=summary,
                    limits=["HF bytes NOT_CHECKED (no download access); HF legal_knowledge identities rest on HF sidecars and HF working-text excerpts",
                            "No page images rendered in C10; readings are text-layer readings, AI agent, not human-confirmed",
                            "Treatment search is deterministic over held crawler texts only (to 2026-11-03); absence of a hit is not proof of no treatment",
                            "SCR-format copies are third-party mirror renditions; used as comparators only"])
    outputs["JUDICIAL_C10_MANIFEST.json"] = (json.dumps(manifest, indent=1, sort_keys=True, ensure_ascii=False) + "\n").encode()
    # review E2-01: the checksum file is emitted (and so --check-ed) by the builder; it also covers the findings, input and tool sources
    sums = [(sha256(outputs[k]), k) for k in sorted(k for k in outputs if k != "JUDICIAL_C10_MANIFEST.json")]
    sums.append((sha256(outputs["JUDICIAL_C10_MANIFEST.json"]), "JUDICIAL_C10_MANIFEST.json"))
    for rel in ("JUDICIAL_C10_FINDINGS.md", "inputs/hf_lk_text_readings.json", "tools/build_judicial_c10.py", "tools/judicial_c10_data.py"):
        sums.append((sha256(open(os.path.join(W, rel), "rb").read()), rel))
    outputs["OUTPUT_SHA256SUMS"] = "".join(f"{h}  {k}\n" for h, k in sums).encode()
    return outputs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="/home/user/c7")
    ap.add_argument("--c10", required=True)
    ap.add_argument("--store", required=True)
    ap.add_argument("--out", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    outs = build(a)
    bad = []
    for name, data in outs.items():
        path = os.path.join(a.out, name)
        if a.check:
            if not os.path.exists(path) or open(path, "rb").read() != data:
                bad.append(name)
        else:
            open(path, "wb").write(data)
    if a.check:
        if bad:
            print("CHECK FAILED:", ", ".join(bad)); sys.exit(1)
        print(f"CHECK OK: {len(outs)} outputs reproduce byte-identically")
    else:
        print("wrote", ", ".join(sorted(outs)))


if __name__ == "__main__":
    main()
