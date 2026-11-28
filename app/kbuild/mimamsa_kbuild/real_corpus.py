"""Real-corpus adapter (B02 Stage 3): the canonical HF dataset layout and the Cycle 15 v7 candidate package.

S1 (`fetch_sources`, network): fetches exactly what the pinned fetch plan names, at pinned revisions, through
`hf_fetch.PinnedRepo` (verified, content-addressed, restricted material never downloaded):
    canonical  data/manifest.csv, data/raw_manifest.csv (sha256 pinned in the plan), data/meta/<doc_id>.json, the raw
               original named by the meta (sha256 = the manifest's), data/text/<doc_id>.txt, research inputs
    v7         <namespace>/<file> at the receipt revision, each sha256 equal to the receipt held in git
S2 (`convert_canonical`, `convert_v7`, offline): converts the cached files into the v1 layout the later stages read
    v1/data/documents.jsonl, derived_text.jsonl, candidates.jsonl, v1/text/<doc_id>.txt, v1/originals/<sha>.pdf,
    v1/research/*.jsonl                     (app/b1/build/build_sample.py record logic, reused unchanged)
    v7/candidate_sets/<name>.txt            (contract 2.1 CS3 bytes: the candidate original sha256 values)
and reports the v7 anchors and relationships produced by `adapters.from_v7_record` (reference only: v7 candidates
stay candidates, are never admitted, never shipped as servable records and never served).

The fetch plan (`specs/<name>.fetch.json`, format mimamsa-kbuild-fetch-plan/1) is pinned by the spec as the
`config_sha256` of the tool `mimamsa_kbuild.fetch_plan` (the spec schema is closed; this keeps the spec the one input
without a schema change). Its content and sha256 are recorded in the S1 inventory.
"""
from __future__ import annotations

import csv
import gzip
import io
import json
import sys
from collections import Counter
from pathlib import Path

from . import REPO
from .errors import BuildRefused
from .fsutil import sha256_bytes

PLAN_TOOL = "mimamsa_kbuild.fetch_plan"
PLAN_FORMAT = "mimamsa-kbuild-fetch-plan/1"
V7_SET_PREFIX = "v7/candidate_sets/"
# committed inputs the canonical conversion reads (build_sample's candidate and research sources), hashed into S1
CONVERSION_LOCAL_INPUTS = [
    ("a2_outcomes_v4", "legal_knowledge/audit_work/C13-A2-OUTCOME/outputs/OUTCOMES_V4.csv"),
    ("a5_graph_edges", "legal_knowledge/audit_work/C13-A5-GRAPH/contract_v1/candidates_graph_edges.jsonl.gz"),
    ("a4_provision_versions", "legal_knowledge/audit_work/C13-A4-STATUTORY/records/PROVISION_VERSIONS_C13.jsonl"),
]


def _refuse(code, msg, stage="S1", details=None):
    raise BuildRefused(code, msg, stage, details)


# ===================================================================================== plan

def plan_pin(spec: dict, tool: str = PLAN_TOOL) -> str | None:
    for t in spec["inputs"]["tools"]:
        if t["name"] == tool:
            return t.get("config_sha256")
    return None


def load_plan(path: Path | None, spec: dict) -> tuple[dict | None, bytes | None]:
    """(plan, bytes) when the spec pins a fetch plan, else (None, None). Refuses an unpinned or mismatching plan."""
    pin = plan_pin(spec)
    if pin is None:
        if path is not None:
            _refuse("BUILD_INPUT_UNPINNED", "a fetch plan was given but the spec pins none (tool mimamsa_kbuild.fetch_plan)", "S0")
        return None, None
    if path is None or not Path(path).is_file():
        _refuse("BUILD_INPUT_MISSING", "the spec pins a fetch plan; pass --fetch-plan with that file", "S0")
    data = Path(path).read_bytes()
    if sha256_bytes(data) != pin:
        _refuse("BUILD_PIN_MISMATCH", "fetch plan does not hash to the spec pin (tool mimamsa_kbuild.fetch_plan config_sha256)", "S0")
    plan = json.loads(data)
    issues = plan_issues(plan, spec)
    if issues:
        _refuse("BUILD_FETCH_PLAN", issues[0], "S0", [{"message": m} for m in issues])
    return plan, data


def plan_issues(plan: dict, spec: dict) -> list[str]:
    out = []
    if plan.get("record_kind") != "kbuild_fetch_plan" or plan.get("format") != PLAN_FORMAT:
        return ["not a mimamsa-kbuild-fetch-plan/1 document"]
    pins = {(h["repo"], h["revision"]) for h in spec["inputs"]["hf"]}
    c = plan.get("canonical") or {}
    if (c.get("repo"), c.get("revision")) not in pins:
        out.append("the canonical repo@revision is not among the spec's pinned HF inputs")
    if c.get("layout") != "HF_CANONICAL_V1":
        out.append("canonical layout must be HF_CANONICAL_V1")
    ids = c.get("doc_ids") or []
    if ids != sorted(set(ids)) or not ids:
        out.append("doc_ids must be a non-empty sorted unique list")
    if any(v is None for v in (c.get("manifests") or {}).values()) or set(c.get("manifests") or {}) != {"data/manifest.csv", "data/raw_manifest.csv"}:
        out.append("both canonical manifests need a pinned sha256")
    names = set()
    for v in plan.get("v7") or []:
        if (v.get("repo"), v.get("revision")) not in pins:
            out.append(f"v7 package {v.get('name')} is not at a pinned HF input")
        if set(v.get("expected_sha256") or {}) != set(v.get("files") or []):
            out.append(f"v7 package {v.get('name')}: every file needs its receipt sha256")
        if "records.jsonl" not in (v.get("files") or []):
            out.append(f"v7 package {v.get('name')}: records.jsonl is required")
        if v.get("name") in names:
            out.append("v7 package names must be unique")
        names.add(v.get("name"))
    return out


def transfer_from_plan(plan: dict, spec: dict, budget_workers: int):
    from .hf_fetch import Transfer
    t = plan.get("transfer") or {}
    return Transfer(max_workers=max(1, min(int(t.get("max_workers", 1)), budget_workers)),
                    max_bytes_per_second=int(t.get("max_bytes_per_second", 8 << 20)),
                    min_free_disk_bytes=int(t.get("min_free_disk_bytes", 10 << 30)),
                    timeout_seconds=int(t.get("timeout_seconds", 120)), retries=int(t.get("retries", 4)))


# ===================================================================================== S1 fetch

def _csv_rows(data: bytes) -> list[dict]:
    return list(csv.DictReader(io.StringIO(data.decode("utf-8"))))


def plan_counts(plan: dict) -> list[dict]:
    """Dry run: what the plan would fetch, per source, without any network or write."""
    c = plan["canonical"]
    out = [{"repo": c["repo"], "revision": c["revision"], "layout": c["layout"], "documents": len(c["doc_ids"]),
            "files_max": 2 + 3 * len(c["doc_ids"]) + len(c.get("research", [])),
            "note": "per document: meta, raw original, [[page N]] text; restricted items are skipped before download"}]
    for v in plan.get("v7") or []:
        out.append({"repo": v["repo"], "revision": v["revision"], "layout": "V7_CANDIDATE_PACKAGE", "name": v["name"],
                    "files_max": len(v["files"]), "note": "reference only (V7_REFERENCE); never served"})
    return out


def fetch_sources(plan: dict, *, cache_root: Path, register, transfer, stats=None, lister=None, opener=None) -> dict:
    """Fetch everything the plan names. Returns {"hf": {(repo, rev): {path: {sha256, bytes}}}, "repos": {...},
    "restricted_skipped": n, "dropped": [...], "stats": FetchStats}."""
    from .hf_fetch import FetchStats, PinnedRepo
    stats = stats or FetchStats()
    restricted_at_start = stats.restricted_skipped
    repos: dict[tuple[str, str], PinnedRepo] = {}

    def repo(r, rev):
        key = (r, rev)
        if key not in repos:
            repos[key] = PinnedRepo(r, rev, cache_root, transfer=transfer, stats=stats, lister=lister, opener=opener)
        return repos[key]

    got: dict[tuple[str, str], dict[str, dict]] = {}
    c = plan["canonical"]
    cr = repo(c["repo"], c["revision"])
    files = got.setdefault((c["repo"], c["revision"]), {})
    files.update(cr.fetch(sorted(c["manifests"]), expected_sha256=c["manifests"], register=register))
    rows = {r["doc_id"]: r for r in _csv_rows(cr.read("data/manifest.csv"))}
    raw_rows = {r["sha256"]: r for r in _csv_rows(cr.read("data/raw_manifest.csv"))}
    dropped = []
    wanted = []
    for did in c["doc_ids"]:
        r = rows.get(did)
        if r is None:
            dropped.append({"doc_id": did, "reason": "NOT_IN_CANONICAL_MANIFEST"})
            continue
        if register.is_restricted(sha256=r["sha256"], doc_id=did):
            stats.restricted_skipped += 1     # counted only: the register is the single source of truth
            continue
        wanted.append(did)
    metas = cr.fetch([f"data/meta/{d}.json" for d in wanted], register=register, doc_ids={f"data/meta/{d}.json": d for d in wanted})
    files.update(metas)
    raw_paths, text_paths, expect, ids = [], [], {}, {}
    for did in wanted:
        mp = f"data/meta/{did}.json"
        if mp not in metas:
            continue
        meta = json.loads(cr.read(mp))
        sha = rows[did]["sha256"]
        raw = meta.get("raw_path") or (raw_rows.get(sha) or {}).get("raw_path")
        if meta.get("sha256") != sha or not raw:
            dropped.append({"doc_id": did, "reason": "META_MANIFEST_DISAGREE_OR_NO_RAW_PATH"})
            continue
        raw_paths.append(raw)
        expect[raw] = sha
        ids[raw] = did
        tp = meta.get("text_path") or f"data/text/{did}.txt"
        text_paths.append(tp)
        ids[tp] = did
    files.update(cr.fetch(raw_paths, expected_sha256=expect, register=register, doc_ids=ids))
    files.update(cr.fetch(text_paths, register=register, doc_ids=ids))
    files.update(cr.fetch([x["path"] for x in c.get("research", [])], register=register))
    for v in plan.get("v7") or []:
        vr = repo(v["repo"], v["revision"])
        paths = {f"{v['namespace']}/{f}": v["expected_sha256"][f] for f in v["files"]}
        got.setdefault((v["repo"], v["revision"]), {}).update(vr.fetch(sorted(paths), expected_sha256=paths, register=register))
    return {"hf": got, "repos": repos, "restricted_skipped": stats.restricted_skipped - restricted_at_start, "dropped": dropped, "stats": stats}


# ===================================================================================== S2 conversion

def _build_sample():
    p = str(REPO / "app" / "b1" / "build")
    if p not in sys.path:
        sys.path.insert(0, p)
    import build_sample   # noqa: E402  (record logic reused unchanged)
    return build_sample


def convert_canonical(plan: dict, read, local_path, *, register, v7_shas: set[str]) -> tuple[dict[str, bytes | str], dict]:
    """Canonical HF layout -> v1 layout files {v1 path: bytes, or the sha256 of bytes already in the S1 cache}, plus a report. `read(path)` returns the cached bytes
    of a canonical path (None when it was not fetched); `local_path(name)` the S1-cached path of a committed input.

    Drops (reported, never silently): restricted (by register, again), a printed access marking, non-PDF media, an
    unopenable PDF, a derivative not in [[page N]] format or with pages outside the physical pages. A copy whose
    sha256 is a v7 candidate is emitted NOT servable (publication STAGED, SG-1: never relabelled as a servable v1
    record); its accounting then shows it quarantined, exactly as the site's I-5 check will."""
    bs = _build_sample()
    from mimamsa_importer.importer import _split_pages
    c = plan["canonical"]
    rev = c["revision"]
    rows = {r["doc_id"]: r for r in _csv_rows(read("data/manifest.csv"))}
    raw_rows = {r["sha256"]: r for r in _csv_rows(read("data/raw_manifest.csv"))}
    out: dict[str, bytes] = {}
    docs, derived, sample, dropped, staged_v7 = [], [], [], [], []
    derived_by_doc = {}
    for did in c["doc_ids"]:
        r = rows.get(did)
        mb = read(f"data/meta/{did}.json") if r else None
        if r is None or mb is None:
            continue   # not in the manifest or restricted: accounted in S1 (counts only)
        meta = json.loads(mb)
        raw = meta.get("raw_path") or (raw_rows.get(r["sha256"]) or {}).get("raw_path")
        why = None
        if meta.get("sha256") != r["sha256"] or not raw:
            why = "META_MANIFEST_DISAGREE_OR_NO_RAW_PATH"
        elif register.is_restricted(sha256=r["sha256"], doc_id=did, path=raw):
            why = None   # never named: counted in the restricted total only
            continue
        elif meta.get("access_marking"):
            why = "PRINTED_ACCESS_MARKING"
        elif meta.get("mime_type") != "application/pdf":
            why = "MIME_NOT_IN_SCOPE"
        data = read(raw) if not why else None
        if not why and (data is None or sha256_bytes(data) != r["sha256"]):
            why = "ORIGINAL_NOT_FETCHED_OR_HASH"
        text = None
        if not why:
            tpath = meta.get("text_path") or f"data/text/{did}.txt"
            text = read(tpath)
            phys = bs.pdf_pages(data)
            try:
                pages_txt = _split_pages(text.decode("utf-8")) if text is not None else None
            except UnicodeDecodeError:
                pages_txt = None
            if phys is None:
                why = "PDF_UNOPENABLE"
            elif not pages_txt or max(pages_txt) > phys or min(pages_txt) < 1:
                why = "TEXT_NOT_PAGE_FORMAT_OR_PAGES_OUTSIDE_PDF"
        if why:
            dropped.append({"doc_id": did, "reason": why})
            continue
        h = r["sha256"]
        doc = bs.document_record(meta, data, phys, raw, rev)
        if h in v7_shas:
            doc["status_axes"]["publication"] = {"value": "STAGED", "basis": "SG-1 (I-5): the copy is a Cycle 15 v7 candidate "
                                                 "original; it is not independently established and is never served on the v1 path"}
            staged_v7.append(did)
        text_path = f"text/{did}.txt"
        d = bs.derived_record(meta, h, text, pages_txt, phys, text_path)
        scale = 1
        while len(json.dumps(d, sort_keys=True, ensure_ascii=False).encode()) > 950_000 and scale < 8:
            scale *= 2
            d = bs.derived_record(meta, h, text, pages_txt, phys, text_path, scale)
        docs.append(doc)
        derived.append(d)
        # already in the S1 cache: referenced by sha256 (not held in memory for the whole selection)
        out[f"v1/{text_path}"] = d["text_sha256"]
        out[f"v1/originals/{h}.pdf"] = h
        data = None
        s = {"doc_id": did, "sha256": h, "bytes": len(data), "pages": phys, "doc_type": doc["doc_type"]}
        sample.append(s)
        derived_by_doc[did] = dict(d, _pages=pages_txt, _blob=bs.git_blob_sha(text))
    # candidates and research (build_sample logic; committed inputs read from the S1 cache, not the working tree)
    bs.A2_CSV, bs.A5_GZ, bs.A4_JSONL = local_path("a2_outcomes_v4"), local_path("a5_graph_edges"), local_path("a4_provision_versions")
    cands = bs.a2_candidates(sample, derived_by_doc, None) + bs.a5_candidates(sample)
    cands = [x for x in cands if not register.deep_match(x)]
    a4 = [json.loads(x) for x in Path(bs.A4_JSONL).read_text(encoding="utf-8").splitlines() if x.strip()]
    a4 = [x for x in a4 if not register.deep_match(x)]
    out["v1/research/a4_provision_versions.jsonl"] = "".join(json.dumps(x, sort_keys=True, ensure_ascii=False) + "\n" for x in a4).encode()
    for res in c.get("research", []):
        if res["as"] == "abbreviations":
            out["v1/research/abbreviations_v1.0.jsonl"] = _abbreviations(bs, read(res["path"]), register)
    j = lambda recs: "".join(json.dumps(x, sort_keys=True, ensure_ascii=False) + "\n" for x in recs).encode()  # noqa: E731
    out["v1/data/documents.jsonl"] = j(sorted(docs, key=lambda x: x["doc_id"]))
    out["v1/data/derived_text.jsonl"] = j(sorted(derived, key=lambda x: x["doc_id"]))
    out["v1/data/candidates.jsonl"] = j(cands)
    rep = {"selected": len(c["doc_ids"]), "converted": len(docs), "dropped": sorted(dropped, key=lambda x: x["doc_id"]),
           "dropped_by_reason": dict(sorted(Counter(x["reason"] for x in dropped).items())),
           "v7_overlap_staged_not_servable": sorted(staged_v7),
           "candidates": {"total": len(cands), "a2_outcomes": sum(x["candidate_type"] == "outcome" for x in cands),
                          "a5_graph_edges": sum(x["candidate_type"] == "graph_edge" for x in cands)},
           "research": {"a4_provision_versions": len(a4)},
           "by_type": dict(sorted(Counter(s["doc_type"] for s in sample).items())),
           "pages": sum(s["pages"] for s in sample), "original_bytes": sum(s["bytes"] for s in sample),
           "logic": "app/b1/build/build_sample.py document_record / derived_record / a2_candidates / a5_candidates (unchanged)"}
    return out, rep


def _abbreviations(bs, raw: bytes | None, register) -> bytes:
    if raw is None:
        return b""
    lex = json.loads(raw)["abbreviations"]
    abbr = []
    for code, v in sorted(lex.items()):
        if code.isupper() and code.isalpha() and 2 <= len(code) <= 6 and v.get("preferred"):
            abbr.append({"code": code, "preferred": v["preferred"][:2], "origin": "Army abbreviations lexicon v1.0 (HF reference "
                         "data; structurally checked, not certified; " + str(v.get("preferred_basis")) + ")"})
    have = {x["code"] for x in abbr}
    abbr += [{"code": k, "preferred": v, "origin": "P2 legal-procedure supplement (not lexicon data)"}
             for k, v in sorted(bs.SUPPLEMENT.items()) if k not in have]
    abbr = [x for x in abbr if not register.deep_match(x)]
    return "".join(json.dumps(x, sort_keys=True, ensure_ascii=False) + "\n" for x in abbr).encode()


def v7_records(read, pkg: dict) -> list[dict]:
    data = read(f"{pkg['namespace']}/records.jsonl")
    return [json.loads(x) for x in data.decode("utf-8").split("\n") if x.strip()]


def v7_pages(read, pkg: dict) -> dict[str, dict[int, str]]:
    """pages.jsonl.gz rows [doc_id, physical page, text] -> {doc_id: {page: text}} (empty when not in the plan)."""
    p = f"{pkg['namespace']}/pages.jsonl.gz"
    if "pages.jsonl.gz" not in pkg["files"]:
        return {}
    out: dict[str, dict[int, str]] = {}
    with gzip.open(io.BytesIO(read(p)), "rt", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                did, page, text = json.loads(line)
                out.setdefault(did, {})[int(page)] = text
    return out


def convert_v7(read, pkg: dict, *, register) -> tuple[dict[str, bytes], dict]:
    """v7 package -> {v7/candidate_sets/<name>.txt: canonical 2.1 bytes} plus a reference report. Every v7 candidate
    original is in the set, application_eligible must be false on every record (refused otherwise), and the
    from_v7_record anchors and relationships are produced and counted, never shipped (they would only enter a
    future producer exchange through admission)."""
    from mimamsa_contract.c16 import accounting, adapters
    recs = v7_records(read, pkg)
    if any(r.get("application_eligible") is not False for r in recs):
        _refuse("BUILD_INPUT_V7", "a v7 record claims application eligibility; v7 candidates stay candidates", "S2")
    if not all(isinstance(r.get("original_sha256"), str) and len(r["original_sha256"]) == 64
               and all(ch in "0123456789abcdef" for ch in r["original_sha256"]) for r in recs):
        _refuse("BUILD_INPUT_V7", "a v7 original_sha256 is not lower-case 64-hex", "S2")
    # a restricted copy is never named in a release (its hash would be restricted content); it is never served anyway
    restricted = {r["original_sha256"] for r in recs if register.is_restricted(sha256=r["original_sha256"], doc_id=r["doc_id"])}
    shas = sorted({r["original_sha256"] for r in recs} - restricted)
    restricted = len(restricted)
    anchors = rels = 0
    a_ids = set()
    for r in recs:
        a, rl = adapters.from_v7_record(r, corpus_generation_id=f"CG-V7-REFERENCE-{pkg['name']}")
        anchors += len(a)
        rels += len(rl)
        a_ids |= {x["anchor_id"] for x in a}
    data = accounting.candidate_set_bytes(shas)
    rep = {"name": pkg["name"], "source": f"v7:{pkg['name']}", "records": len(recs), "candidate_originals": len(shas),
           "candidate_set_sha256": sha256_bytes(data), "restricted_omitted_from_set": restricted,
           "from_v7_record": {"anchors": anchors, "unique_anchor_ids": len(a_ids), "relationships": rels,
                              "use": "reference only: not shipped, not admitted, not served"},
           "application_eligible_true": 0}
    return {f"{V7_SET_PREFIX}{pkg['name']}.txt": data}, rep
