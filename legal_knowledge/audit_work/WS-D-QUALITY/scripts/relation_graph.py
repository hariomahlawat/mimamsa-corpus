#!/usr/bin/env python3
"""WS-D deliverable 6: relation-graph integrity, duplicate detection and orphan references.

Read-only, stdlib only, deterministic. Graph nodes: 658 KB records, 53 cases, citation codes
(PILOT-01 v3 register), audit sources/findings/reviews (every batch with sources/findings/reviews
directories), page-image checks, conflict IDs. Edges are typed and checked for dangling targets.
Duplicates: exact (raw text), normalised-text hash (case/punctuation/whitespace-insensitive) and
near-duplicate (word 5-gram shingle Jaccard >= 0.85) for KB bodies; identity-field collisions for cases.

Optional: --corpus-ref REF (e.g. origin/raw-data) lists crawler doc_ids from data/meta/*.json of a
LOCAL git ref (`git ls-tree`, no network) to check register targets such as 'act-army-1950'.
Writes relation_graph_summary.json and relation_graph_report.md into WS-D-QUALITY/.
A resolved edge is a reference-integrity fact only; it never says the cited law is correct.
"""
import argparse, collections, csv, hashlib, io, itertools, json, re, subprocess, sys
from pathlib import Path

WSD = Path(__file__).resolve().parents[1]
ROOT = WSD.parents[2]
AW = ROOT / "legal_knowledge/audit_work"
KB = ROOT / "legal_knowledge/curated_originals/knowledge_base/v0.9/records_658.jsonl"
CASES = ROOT / "legal_knowledge/curated_originals/case_law/v0.9/cases_53.jsonl"
REG = AW / "PILOT-01/registers/source_code_resolution_v3.csv"
NEAR = 0.85
SIMILAR = 0.6
CASE_ID = re.compile(r"\bDCLR-[A-Z]+-\d{4}-[A-Z]?\d+\b")
DOC_ID = re.compile(r"^((?:act|rules|regs?|manual|notification|sc|hc|aft)-[a-z0-9-]+)")


def jl(p):
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def norm(t):
    return " ".join(re.findall(r"[a-z0-9]+", (t or "").lower()))


def sha(t):
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def shingles(t, k=5):
    w = t.split()
    return {" ".join(w[i:i + k]) for i in range(max(1, len(w) - k + 1))}


def load_batches():
    out = {}
    for b in sorted(p for p in AW.iterdir() if p.is_dir()):
        if not all((b / d).is_dir() for d in ("sources", "findings", "reviews")):
            continue
        kinds = {}
        for d in ("sources", "findings", "reviews"):
            rows = []
            for p in sorted((b / d).glob("*.json")):
                o = json.loads(p.read_text(encoding="utf-8"))
                rows += o if isinstance(o, list) else [o]
            kinds[d] = rows
        man = b / "pilot-manifest.json"
        kinds["manifest"] = json.loads(man.read_text(encoding="utf-8")) if man.is_file() else {}
        out[b.name] = kinds
    return out


def pic_ids():
    ids = {}
    for p in sorted(AW.rglob("page_image_checks*.csv")):
        for r in csv.DictReader(io.StringIO(p.read_text(encoding="utf-8"), newline="")):
            ids.setdefault(r["check_id"], []).append(str(p.relative_to(AW)))
    return ids


def corpus_doc_ids(ref):
    if not ref:
        return None, None
    try:
        names = subprocess.run(["git", "-C", str(ROOT), "ls-tree", "-r", "--name-only", ref, "data/meta"],
                               check=True, capture_output=True, text=True).stdout.split()
        commit = subprocess.run(["git", "-C", str(ROOT), "rev-parse", ref], check=True, capture_output=True,
                                text=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None, None
    return {Path(n).stem for n in names if n.endswith(".json")}, commit


def build(corpus_ref=None):
    kb, cases = jl(KB), jl(CASES)
    kb_ids, case_ids = [r["id"] for r in kb], [c["id"] for c in cases]
    reg = list(csv.DictReader(io.StringIO(REG.read_text(encoding="utf-8"), newline="")))
    batches = load_batches()
    pics = pic_ids()
    docs, corpus_commit = corpus_doc_ids(corpus_ref)
    known = set(kb_ids) | set(case_ids)
    S = {"nodes": {}, "edges": {}, "dangling": {}, "orphans": {}, "duplicates": {}, "notes": []}
    edges = collections.Counter(); dangling = collections.defaultdict(list)

    def edge(kind, src, dst, ok):
        edges[kind] += 1
        if not ok:
            dangling[kind].append(f"{src} -> {dst}")

    # ID uniqueness
    S["duplicates"]["kb_id_collisions"] = sorted(k for k, n in collections.Counter(kb_ids).items() if n > 1)
    S["duplicates"]["case_id_collisions"] = sorted(k for k, n in collections.Counter(case_ids).items() if n > 1)
    S["duplicates"]["kb_case_id_overlap"] = sorted(set(kb_ids) & set(case_ids))
    # cases -> cases
    rel = {c["id"]: set(c.get("related_cases") or []) for c in cases}
    for a, bs in rel.items():
        for b in sorted(bs):
            edge("case.related_cases", a, b, b in rel)
    S["orphans"]["case_related_asymmetric"] = sorted(f"{a} -> {b}" for a, bs in rel.items() for b in bs
                                                     if b in rel and a not in rel[b])
    # KB -> case IDs mentioned verbatim
    kb_case_links = collections.defaultdict(set)
    for r in kb:
        for cid in sorted(set(CASE_ID.findall(json.dumps(r, ensure_ascii=False)))):
            edge("kb.mentions_case_id", r["id"], cid, cid in rel)
            kb_case_links[cid].add(r["id"])
    # KB -> code -> register target
    spec = __import__("importlib.util").util.spec_from_file_location("bci", AW / "PILOT-01/build_code_inventory.py")
    bci = __import__("importlib.util").util.module_from_spec(spec); spec.loader.exec_module(bci)
    inv, uncoded, _ = bci.inventory()
    regd = {r["code"]: r for r in reg}
    target_case, target_doc, gaps = {}, {}, []
    for c, recs in sorted(inv.items()):
        for r in sorted(recs):
            edge("kb.uses_code", r, c, c in regd)
        t = (regd.get(c, {}).get("corpus_target_or_gap") or "").strip()
        m_case = CASE_ID.search(t)
        if m_case and not t.upper().startswith("GAP"):
            target_case[c] = m_case.group(0)
            edge("code.target_case", c, m_case.group(0), m_case.group(0) in rel)
            for r in recs:
                kb_case_links[m_case.group(0)].add(r)
        elif DOC_ID.match(t):
            d = DOC_ID.match(t).group(1)
            target_doc[c] = d
            if docs is not None:
                edge("code.target_corpus_doc", c, d, d in docs)
        else:
            gaps.append(c)
    S["notes"].append(f"{len(target_case)} codes target a cases_53 row, {len(target_doc)} a crawler doc_id, "
                      f"{len(gaps)} declare a GAP/unresolved/non-legal target")
    if docs is None:
        S["notes"].append("code.target_corpus_doc NOT_CHECKED: no --corpus-ref given or ref unavailable")
    else:
        S["notes"].append(f"crawler doc_ids read from {corpus_ref}@{corpus_commit[:12]} data/meta ({len(docs)} files)")
    S["orphans"]["cases_with_no_kb_link"] = sorted(set(case_ids) - set(kb_case_links))
    # audit batches
    src_index = collections.defaultdict(list)
    for bname, k in batches.items():
        sids = [s["source_id"] for s in k["sources"]]
        for s in sids:
            src_index[s].append(bname)
        sset, fset = set(sids), {f["finding_id"] for f in k["findings"]}
        mrec = {r["record_id"] for r in k["manifest"].get("records", [])}
        used = set()
        for f in k["findings"]:
            edge("finding.record_id", f["finding_id"], f["record_id"], f["record_id"] in known | mrec)
            for x in f.get("related_record_ids", []) or []:
                edge("finding.related_record", f["finding_id"], x, x in known | mrec)
            for x in (f.get("source_ids") or []) + (f.get("contrary_source_ids") or []) + (f.get("mml_anchor_ids") or []):
                edge("finding.source", f["finding_id"], x, x in sset); used.add(x)
        for r in k["reviews"]:
            edge("review.finding", r["review_id"], r["finding_id"], r["finding_id"] in fset)
            for x in (r.get("source_ids") or []) + (r.get("independent_source_ids") or []):
                edge("review.source", r["review_id"], x, x in sset); used.add(x)
        for s in k["sources"]:
            for tok in re.findall(r"PIC-\d+", s.get("page_image_check_id") or ""):
                edge("source.page_image_check", s["source_id"], tok, tok in pics)
        S["orphans"][f"{bname}.sources_unreferenced"] = sorted(sset - used)
        S["orphans"][f"{bname}.findings_without_sources"] = sorted(
            f"{f['finding_id']} ({f.get('verification_state')}/{f.get('examination_outcome')})"
            for f in k["findings"] if not f.get("source_ids"))
        S["nodes"][f"{bname}.sources"] = len(k["sources"]); S["nodes"][f"{bname}.findings"] = len(k["findings"])
        S["nodes"][f"{bname}.reviews"] = len(k["reviews"])
    S["duplicates"]["source_id_in_multiple_batches"] = sorted(f"{s}: {','.join(b)}" for s, b in src_index.items() if len(b) > 1)
    S["duplicates"]["page_image_check_id_in_multiple_registers"] = sorted(f"{k}: {','.join(v)}" for k, v in pics.items() if len(v) > 1)
    # register internal duplicates
    S["duplicates"]["register_codes_declared_same_instrument"] = sorted(r["code"] for r in reg if r["duplicate_of"].strip())
    # KB text duplicates
    exact, normh, title = collections.defaultdict(list), collections.defaultdict(list), collections.defaultdict(list)
    sh = {}
    for r in kb:
        exact[sha(r.get("body") or "")].append(r["id"])
        n = norm(r.get("body")); normh[sha(n)].append(r["id"]); sh[r["id"]] = shingles(n)
        title[norm(r.get("title"))].append(r["id"])
    S["duplicates"]["kb_body_exact"] = sorted(sorted(v) for v in exact.values() if len(v) > 1)
    S["duplicates"]["kb_body_normalised"] = sorted(sorted(v) for v in normh.values() if len(v) > 1)
    S["duplicates"]["kb_title_normalised"] = sorted(sorted(v) for v in title.values() if len(v) > 1)
    near = []
    ids = sorted(sh)
    for a, b in itertools.combinations(ids, 2):
        A, B = sh[a], sh[b]
        if not A or not B or min(len(A), len(B)) / max(len(A), len(B)) < SIMILAR:
            continue
        j = len(A & B) / len(A | B)
        if j >= SIMILAR:
            near.append([a, b, round(j, 3)])
    exact_pairs = {tuple(sorted(p)) for g in S["duplicates"]["kb_body_normalised"] for p in itertools.combinations(g, 2)}
    near = [p for p in near if (p[0], p[1]) not in exact_pairs]
    S["duplicates"]["kb_body_near_duplicates"] = [p for p in near if p[2] >= NEAR]
    S["duplicates"]["kb_body_similar_leads_0_6"] = [p for p in near if p[2] < NEAR]
    # case identity collisions
    for field in ("case_number", "reporter_citation", "primary_source_url", "title"):
        g = collections.defaultdict(list)
        for c in cases:
            v = norm(c.get(field)) if field == "title" else (c.get(field) or "").strip()
            if v:
                g[v].append(c["id"])
        S["duplicates"][f"case_{field}_collision"] = sorted(sorted(v) for v in g.values() if len(v) > 1)
    g = collections.defaultdict(list)
    for c in cases:
        if norm(c.get("holding")):
            g[sha(norm(c.get("holding")))].append(c["id"])
    S["duplicates"]["case_holding_normalised"] = sorted(sorted(v) for v in g.values() if len(v) > 1)
    S["orphans"]["cases_with_empty_holding"] = sorted(f"{c['id']} ({c.get('record_type')})" for c in cases
                                                      if not norm(c.get("holding")))
    S["nodes"].update({"kb_records": len(kb), "cases": len(cases), "codes": len(inv), "page_image_checks": len(pics),
                       "kb_records_without_codes": len(uncoded)})
    S["edges"] = dict(sorted(edges.items()))
    S["dangling"] = {k: sorted(v) for k, v in sorted(dangling.items())}
    S["inputs"] = {"kb_sha256": hashlib.sha256(KB.read_bytes()).hexdigest(),
                   "cases_sha256": hashlib.sha256(CASES.read_bytes()).hexdigest(),
                   "corpus_ref": corpus_ref, "corpus_commit": corpus_commit}
    return S


def render(S):
    L = ["# Relation graph integrity report", "",
         "Generated by `scripts/relation_graph.py` (read-only, deterministic). Reference integrity only: a resolved edge does not mean the cited law is correct or current.", "",
         f"Inputs: KB sha `{S['inputs']['kb_sha256'][:12]}…`, cases sha `{S['inputs']['cases_sha256'][:12]}…`, crawler corpus ref `{S['inputs']['corpus_ref']}` @ `{(S['inputs']['corpus_commit'] or 'n/a')[:12]}`.", "",
         "## Nodes", "", "| Node set | Count |", "| --- | --- |"]
    L += [f"| {k} | {v} |" for k, v in sorted(S["nodes"].items())]
    L += ["", "## Edges and dangling references", "", "| Edge type | Edges | Dangling |", "| --- | --- | --- |"]
    L += [f"| {k} | {v} | {len(S['dangling'].get(k, []))} |" for k, v in S["edges"].items()]
    for k, v in S["dangling"].items():
        if v:
            L += ["", f"Dangling `{k}`: " + "; ".join(v[:40]) + (" …" if len(v) > 40 else "")]
    L += ["", "## Orphans", ""]
    for k, v in sorted(S["orphans"].items()):
        L.append(f"- **{k}** ({len(v)}): " + (", ".join(v[:60]) + (" …" if len(v) > 60 else "") if v else "none"))
    L += ["", "## Duplicates", ""]
    for k, v in sorted(S["duplicates"].items()):
        shown = "; ".join(" / ".join(map(str, x)) if isinstance(x, list) else str(x) for x in v[:40])
        L.append(f"- **{k}** ({len(v)}): " + (shown + (" …" if len(v) > 40 else "") if v else "none"))
    L += ["", "## Notes", ""] + [f"- {n}" for n in S["notes"]]
    L += ["", "Near-duplicate threshold: word 5-gram shingle Jaccard >= 0.85 (similar leads: 0.60-0.85), excluding pairs already identical after normalisation. Near-duplicates and shared titles are leads for review, not proof of redundancy (templates legitimately share wording).", ""]
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument("--corpus-ref"); ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args(argv)
    S = build(a.corpus_ref)
    if not a.no_write:
        (WSD / "relation_graph_summary.json").write_text(json.dumps(S, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        (WSD / "relation_graph_report.md").write_text(render(S), encoding="utf-8")
    bad = {k: len(v) for k, v in S["dangling"].items() if v}
    ids = [k for k in ("kb_id_collisions", "case_id_collisions", "kb_case_id_overlap", "source_id_in_multiple_batches")
           if S["duplicates"][k]]
    print(json.dumps({"edges": sum(S["edges"].values()), "dangling": bad, "id_collisions": ids}, indent=1))
    return 1 if bad or ids else 0


if __name__ == "__main__":
    sys.exit(main())
