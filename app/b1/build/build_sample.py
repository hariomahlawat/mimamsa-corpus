"""B1 offline sample bundle: select a few hundred public documents from the private HF corpus master, build a
contract-v1 release bundle (development-signed, disposable key), and import it through app/importer into a site.

Corpus bytes never enter git. Everything downloaded or built lives under --work (default: the session scratchpad).
Only app/b1/sample/SAMPLE_MANIFEST.json (hashes, ids, counts, import result) is committed.

Rules applied here (C13 agent brief, hard rules):
- RM-001 and anything else on config/restricted_material.json is excluded before download (scripts/restricted_material.py)
  and again by the contract validator and importer.
- HF reads only (hf_hub_download at a pinned revision, no token passed: the proxy injects auth; nothing is printed).
- Candidate data (A2 outcomes, A5 graph edges, A4 provision versions) stays AUTOMATED_CANDIDATE_NOT_VERIFIED.
- No production signing key: a disposable development key is generated in memory; only its public half is kept.

Usage:
  python -I app/b1/build/build_sample.py --work <dir> [--revision <hf sha>] [--select-only]
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO / "app" / "contract"), str(REPO / "app" / "importer"), str(REPO / "scripts")]

from mimamsa_contract.devbundle import new_dev_keypair, write_bundle  # noqa: E402
from mimamsa_contract.restricted import load_register  # noqa: E402
from mimamsa_importer import configure_site, import_release  # noqa: E402
from mimamsa_importer.importer import _split_pages  # noqa: E402  (same page-format reader as the importer)
import restricted_material  # noqa: E402

HF_REPO = "hariomahlawat/mimamsa-corpus"
DEFAULT_REVISION = "3864faf3bb24edef4bfb18fa0916cc788eb68d79"
PIPELINE = {"name": "mimamsa-corpus-text", "version": "1.0.0"}
SEED = "mimamsa-b1-sample-v1"
N_SC, N_HC_PER_COURT = 80, 36
HC_COURTS = ("hc-delhi", "hc-ph", "hc-jkl", "hc-allahabad")
FORCE_INCLUDE = ("sc-2013-dharamvir-singh-2013insc408",)
A2_CSV = REPO / "legal_knowledge/audit_work/C13-A2-OUTCOME/outputs/OUTCOMES_V4.csv"
A5_GZ = REPO / "legal_knowledge/audit_work/C13-A5-GRAPH/contract_v1/candidates_graph_edges.jsonl.gz"
A4_JSONL = REPO / "legal_knowledge/audit_work/C13-A4-STATUTORY/records/PROVISION_VERSIONS_C13.jsonl"
A2_EVAL = {
    "printed_disposal": (0.898, 0.833, "weighted strict precision CP95 [0.838, 0.941]; weighted coverage CP95 [0.743, 0.902]; "
                                       "AI-coded reference set (two coders + adjudicator, no human annotator); targets NOT_MET; "
                                       "Supreme Court weakest: precision 0.576, coverage 0.391"),
}
A2_LABELS = {"allowed", "dismissed", "partly_allowed", "remanded", "disposed", "transferred", "withdrawn"}
LEXICON = "legal_knowledge/reference_data/abbreviations/v1.0/army_abbreviations_versioned_union_v1.0.json"
# Legal-procedure codes absent from the Army lexicon v1.0 (P2 PoC supplement, app/poc/p2_search/engines.py; not lexicon data).
SUPPLEMENT = {
    "AFT": ["Armed Forces Tribunal"], "OA": ["Original Application"], "MA": ["Miscellaneous Application"],
    "SOE": ["Summary of Evidence"], "COI": ["Court of Inquiry"], "AR": ["Army Rule", "Army Rules"],
    "AA": ["Army Act"], "HC": ["High Court"], "SC": ["Supreme Court"], "WP": ["Writ Petition"],
    "ROE": ["Record of Evidence"], "PCP": ["Post Confirmation Petition"],
}
BANNER = "Research and candidate data. Not legally verified. AUTH-LEDGER version 0: no legal approval exists."
PARA = re.compile(r"^\s*(\d{1,3})\.\s+\S")


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def git_blob_sha(b: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()


class HF:
    def __init__(self, revision: str, cache: Path):
        from huggingface_hub import hf_hub_download
        self._dl, self.revision, self.cache = hf_hub_download, revision, cache

    def get(self, path: str) -> Path:
        return Path(self._dl(HF_REPO, path, repo_type="dataset", revision=self.revision, cache_dir=str(self.cache)))


def rank(doc_id: str) -> str:
    return sha(f"{SEED}|{doc_id}".encode())


def select(manifest_rows):
    """Deterministic selection: every non-judgment document, N_SC Supreme Court and N_HC_PER_COURT per High Court,
    ordered by sha256(seed|doc_id). Restricted material is removed before anything is downloaded."""
    rows = [r for r in manifest_rows
            if not restricted_material.is_restricted(sha256=r["sha256"], doc_id=r["doc_id"])]
    # identities of restricted items are not repeated here: only the count (the register is the single source of truth)
    excluded = [{"reason": "restricted_material_register", "count": len(manifest_rows) - len(rows)}]
    pick = [r for r in rows if r["type"] != "judgment"]
    sc = sorted((r for r in rows if r["doc_id"].startswith("sc-")), key=lambda r: rank(r["doc_id"]))
    forced = [r for r in sc if r["doc_id"] in FORCE_INCLUDE]
    pick += forced + [r for r in sc if r not in forced][: N_SC - len(forced)]
    for court in HC_COURTS:
        hc = sorted((r for r in rows if r["doc_id"].startswith(court + "-")), key=lambda r: rank(r["doc_id"]))
        pick += hc[:N_HC_PER_COURT]
    return pick, excluded


def pdf_pages(data: bytes) -> int | None:
    import pypdfium2 as pdfium
    try:
        pdf = pdfium.PdfDocument(data)
        try:
            return len(pdf)
        finally:
            pdf.close()
    except Exception:
        return None


def passages_for(page: int, body: str, scale: int = 1):
    """Paragraph-sized spans with exact offsets into the page text (blank-line blocks, merged to >= 500 chars,
    split at line ends above 2,400 chars; sized so a 1,000-page judgment stays under the contract's 1 MiB record cap)."""
    blocks, pos = [], 0
    for m in re.finditer(r"(?:[^\n]+\n?)+", body):
        s, e = m.start(), m.end()
        while e > s and body[e - 1] in " \n\t":
            e -= 1
        if e > s:
            blocks.append([s, e])
        pos = m.end()
    merged = []
    for b in blocks:
        if merged and (merged[-1][1] - merged[-1][0] < 500 * scale) and (b[1] - merged[-1][0] <= 2400 * scale):
            merged[-1][1] = b[1]
        else:
            merged.append(b)
    out = []
    for s, e in merged:
        while e - s > 2400 * scale:
            cut = body.rfind("\n", s + 600 * scale, s + 2400 * scale)
            cut = cut if cut > s else s + 2400 * scale
            out.append((s, cut))
            s = cut
            while s < e and body[s] in " \n\t":
                s += 1
        if e > s:
            out.append((s, e))
    res = []
    for i, (s, e) in enumerate(out, 1):
        text = body[s:e]
        m = PARA.match(text)
        res.append({"passage_id": f"p{page}-{i}", "page": page, "char_start": s, "char_end": e,
                    "paragraph_label": m.group(1) if m else None, "kind": "body",
                    "text_sha256": sha(text.encode("utf-8"))})
    return res


def axes(meta, carrier, authority):
    rec = "2026-11-25T00:00:00Z"
    return {
        "source_integrity": {"value": "BYTE_VERIFIED", "recorded_at": rec,
                             "basis": "SHA-256 recomputed over the bytes downloaded from the HF corpus master at the pinned "
                                      "revision during the B1 sample build; re-verified by the importer from bundled bytes",
                             "evidence_ref": "app/b1/sample/SAMPLE_MANIFEST.json"},
        "source_authenticity": {"value": "UNKNOWN", "basis": "no documentary or custodian check in B1",
                                "policy_v1": {"document_authority": authority, "carrier_provenance": carrier,
                                              "copy_fidelity": "HASH_ONLY", "amendment_chain_status": "NOT_CHECKED",
                                              "instrument_identity": None, "authority_rationale": None}},
        "evidence_fidelity": {"value": "AUTOMATED_CANDIDATE_NOT_VERIFIED", "basis": "corpus text layer / OCR, not checked"},
        "legal_applicability": {"value": "NOT_ESTABLISHED", "basis": "no temporal or legal review in Cycle 13"},
        "legal_approval": {"value": "T0_RESEARCH_ONLY", "basis": "AUTH-LEDGER version 0; no Legal Reviewer appointed"},
        "publication": {"value": "PUBLISHED", "basis": "B1 development sample; released for the prototype only"},
        "dependency_freshness": {"value": "NOT_EVALUATED", "basis": "not evaluated in B1"},
    }


def listify(v):
    if v is None:
        return None
    if isinstance(v, list):
        return "; ".join(str(x) for x in v) or None
    return str(v)


def document_record(meta, data: bytes, pages: int, hf_path: str, revision: str):
    src = meta.get("source") or ""
    if src in ("indiacode", "mod", "official_copies", "aft"):
        carrier, authority = "GOVERNMENT_HOSTED_COPY", "GOVERNMENT_COMPILATION"
    else:
        carrier, authority = "THIRD_PARTY_ARCHIVAL_FACSIMILE", "UNKNOWN"
    h = sha(data)
    doc_type = meta.get("doc_type")
    doc_type = {"schedule": "act", "reference": "other", "executive_order": "order"}.get(doc_type, doc_type)
    tm = meta.get("text_method") if meta.get("text_method") in ("pdf_text", "ocr", "html", "mixed", "none") else "pdf_text"
    rec = {
        "contract_version": "1.0.0", "record_kind": "document", "doc_id": meta["doc_id"], "doc_type": doc_type,
        "source_copy": {"sha256": h, "bytes": len(data), "mime_type": "application/pdf",
                        "vault_path": f"vault/sha256/{h[:2]}/{h}", "page_count": pages, "completeness": "NOT_CHECKED"},
        "alternate_copy_sha256": [], "parent_doc_id": meta.get("parent_doc_id"),
        "title": meta.get("title"), "number": meta.get("number"), "issuing_authority": meta.get("issuing_authority"),
        "issue_date": meta.get("issue_date"), "effective_date": meta.get("effective_date"),
        "language": meta.get("language") or "en",
        "corpus_status": meta.get("status") if meta.get("status") in (
            "in_force", "amended", "partly_repealed", "repealed", "superseded", "overruled", "unknown") else "unknown",
        "corpus_status_note": meta.get("status_note"), "corpus_status_as_of": meta.get("status_as_of"),
        "text_method": tm, "ocr_confidence": meta.get("ocr_confidence"),
        "provenance": {
            "acquisition_channel": "CRAWLER", "source_url": meta.get("source_url"), "retrieved_at": meta.get("retrieved_at"),
            "source_system": (meta.get("source_record") or {}).get("system") or src or None,
            "source_record_id": (meta.get("source_record") or {}).get("record_id"),
            "original_filename": meta.get("original_filename"),
            "aliases": [{"source_url": a if isinstance(a, str) else a.get("source_url"),
                         "retrieved_at": None if isinstance(a, str) else a.get("retrieved_at")}
                        for a in meta.get("source_aliases") or []],
            "hf": {"repo": HF_REPO, "revision": revision, "path": hf_path},
            "git": None, "acquisition_record_ref": None, "admin_submission_id": None},
        "status_axes": axes(meta, carrier, authority),
        "restriction": {"access_marking": meta.get("access_marking"), "marking_page": None,
                        "eligibility": "ELIGIBLE_ALL_USERS", "restriction_id": None, "decided_by": None,
                        "basis": None},
        "field_origin": {k: v for k, v in (meta.get("field_provenance") or {}).items()
                         if k in ("title", "number", "issuing_authority", "issue_date", "effective_date", "language",
                                  "court", "bench", "case_numbers", "neutral_citation", "reported_citations",
                                  "parties", "judges")
                         and v in ("crawler", "rule", "llm", "human", "release_import", "admin_entered", "unknown")},
    }
    if doc_type in ("judgment", "order"):
        parties = meta.get("parties") or {}
        rec["judicial"] = {"court": meta.get("court"), "bench": meta.get("bench"),
                           "case_numbers": [str(x) for x in meta.get("case_numbers") or []],
                           "neutral_citation": meta.get("neutral_citation"),
                           "reported_citations": [str(x) for x in meta.get("reported_citations") or []],
                           "parties": {"petitioner": listify(parties.get("petitioner")),
                                       "respondent": listify(parties.get("respondent"))},
                           "judges": [str(x) for x in meta.get("judges") or []], "judgment_identity_id": None}
    if rec["restriction"]["access_marking"]:
        rec["restriction"].update(eligibility="NOT_ASSESSED")
        rec["status_axes"]["publication"] = {"value": "STAGED", "basis": "printed access marking: eligibility not decided"}
    return rec


def derived_record(meta, h: str, text: bytes, pages_txt: dict, phys: int, text_path: str, scale: int = 1):
    low = set(meta.get("ocr_low_confidence_pages") or [])
    ocr = meta.get("text_method") == "ocr"
    pages, passages = [], []
    for n in sorted(pages_txt):
        body = pages_txt[n]
        pages.append({"page": n, "method": ("ocr" if ocr else "pdf_text") if body.strip() else "none",
                      "char_count": len(body), "ocr_engine": None,
                      "ocr_mean_confidence": None, "low_confidence": n in low, "has_word_boxes": False,
                      "text_sha256": sha(body.encode("utf-8"))})
        passages += passages_for(n, body, scale)
    return {"contract_version": "1.0.0", "record_kind": "derived_text", "source_copy_sha256": h, "doc_id": meta["doc_id"],
            "pipeline": {"name": PIPELINE["name"], "version": PIPELINE["version"],
                         "tools": {"corpus_text_method": str(meta.get("text_method"))}},
            "text_path": text_path, "text_sha256": sha(text), "page_marker": "[[page N]]",
            "quoting_permitted": not ocr, "evidence_fidelity": "AUTOMATED_CANDIDATE_NOT_VERIFIED",
            "pages": pages, "passages": passages}


def a2_candidates(sample, derived_by_doc, commit):
    """A2 V4 printed_disposal outcomes for sampled judgments. A span is bound to the B1 derivative only when the A2
    excerpt is found verbatim at the A2 offsets on that page of the same text (A2 read c7 ad77758d; the HF text at
    the pinned revision is compared by git blob id); otherwise the anchor is page-only."""
    out = []
    by_sha = {s["sha256"]: s for s in sample}
    with open(A2_CSV, newline="", encoding="utf-8") as fh:
        for i, row in enumerate(csv.DictReader(fh)):
            s = by_sha.get(row["sha256"])
            if not s or not row.get("page"):
                continue
            label = (row.get("printed_disposal") or "").strip()
            if label and label not in A2_LABELS:
                continue
            d = derived_by_doc[s["doc_id"]]
            page = int(row["page"])
            anchor = {"source_copy_sha256": s["sha256"], "page": page, "passage_id": None, "char_start": None,
                      "char_end": None, "paragraph_label": row.get("paragraph") or None, "text_sha256": None,
                      "pipeline_version": None, "quote": (row.get("excerpt") or None) and row["excerpt"][:500],
                      "pipeline_name": None, "derivative_text_sha256": None}
            body = d["_pages"].get(page)
            blob = (row.get("text_source") or "").rsplit("@blob:", 1)[-1]
            if body is not None and row.get("char_start") and row.get("excerpt") and blob == d["_blob"]:
                cs, ce = int(row["char_start"]), int(row["char_end"])
                if 0 <= cs <= ce <= len(body) and body[cs:ce] == row["excerpt"]:
                    anchor.update(char_start=cs, char_end=ce, text_sha256=sha(body[cs:ce].encode("utf-8")),
                                  pipeline_name=PIPELINE["name"], pipeline_version=PIPELINE["version"],
                                  derivative_text_sha256=d["text_sha256"], quote=None)
            if not 1 <= page <= s["pages"]:
                continue
            ev = A2_EVAL["printed_disposal"]
            out.append({
                "contract_version": "1.0.0", "record_kind": "candidate",
                "candidate_id": f"a2v4.{row['judgment_id']}.{i}", "candidate_type": "outcome",
                "source_doc_id": s["doc_id"], "anchors": [anchor],
                "extractor": {"name": "c13-extract-v4", "version": "1.0.0", "artefact_commit": "9cdd5008",
                              "artefact_path": "legal_knowledge/audit_work/C13-A2-OUTCOME/outputs/OUTCOMES_V4.csv",
                              "artefact_sha256": None, "author_id": "claude-agent-c13-a2"},
                "status": "AUTOMATED_CANDIDATE_NOT_VERIFIED", "review_ref": None,
                "capability_restriction": "NON_OPERATIONAL_RESEARCH_ONLY",
                "deferred_findings": ["C11-extraction F05", "C11-extraction F08"],
                "evaluation_ref": {"report_path": "legal_knowledge/audit_work/C13-EVAL/eval/RESULTS_C13.md",
                                   "report_commit": "20a4e55d", "precision": ev[0], "coverage_or_recall": ev[1],
                                   "ci_note": ev[2], "human_checked": False},
                "payload": {"field": "printed_disposal", "label": label or "abstained",
                            "proceeding_ref": row.get("proceeding") or None, "party_scope": row.get("party_specific") or None,
                            "abstain_reason": (row.get("abstain_reason") or None) if not label else None}})
    return out


def a5_candidates(sample):
    ids = {s["doc_id"]: s for s in sample}
    out = []
    with gzip.open(A5_GZ, "rt", encoding="utf-8") as fh:
        for line in fh:
            c = json.loads(line)
            s = ids.get(c["source_doc_id"])
            if not s or any(a["source_copy_sha256"] != s["sha256"] or not 1 <= a["page"] <= s["pages"] for a in c["anchors"]):
                continue
            for a in c["anchors"]:
                # A5 treatment spans are bound to the c7 'corpus-data-text@ad77758d' derivative with file-level offsets;
                # B1 does not carry that derivative, so the span is reduced to a page-only anchor (quote kept, labelled).
                if a.get("pipeline_name") or a.get("derivative_text_sha256"):
                    a.update(pipeline_name=None, pipeline_version=None, derivative_text_sha256=None,
                             passage_id=None, char_start=None, char_end=None, text_sha256=None)
            out.append(c)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--revision", default=DEFAULT_REVISION)
    ap.add_argument("--select-only", action="store_true")
    ap.add_argument("--manifest-out", type=Path, default=REPO / "app/b1/sample/SAMPLE_MANIFEST.json")
    a = ap.parse_args()
    work = a.work.resolve()
    hf = HF(a.revision, work / "hfcache")
    register = load_register(REPO / "config" / "restricted_material.json")
    rows = list(csv.DictReader(open(hf.get("data/manifest.csv"), encoding="utf-8")))
    raw_rows = {r["sha256"]: r for r in csv.DictReader(open(hf.get("data/raw_manifest.csv"), encoding="utf-8"))}
    picked, excluded = select(rows)
    print(f"selected {len(picked)} of {len(rows)} manifest rows; {excluded[0]['count']} restricted rows excluded before download")
    if a.select_only:
        for r in picked:
            print(r["doc_id"])
        return 0

    docs, derived, texts, originals, sample, dropped = [], [], {}, {}, [], []
    derived_by_doc = {}
    for r in picked:
        did = r["doc_id"]
        meta = json.loads(hf.get(f"data/meta/{did}.json").read_text(encoding="utf-8"))
        raw_path = meta.get("raw_path") or (raw_rows.get(r["sha256"]) or {}).get("raw_path")
        why = None
        if meta.get("sha256") != r["sha256"] or not raw_path:
            why = "meta/manifest sha256 disagree or raw path missing"
        elif register.is_restricted(sha256=r["sha256"], doc_id=did, path=raw_path) or meta.get("access_marking"):
            why = "restricted register or printed access marking"
        elif meta.get("mime_type") != "application/pdf":
            why = f"mime {meta.get('mime_type')} not in B1 scope"
        if why:
            dropped.append({"doc_id": did, "reason": why})
            continue
        data = hf.get(raw_path).read_bytes()
        if sha(data) != r["sha256"]:
            dropped.append({"doc_id": did, "reason": "downloaded bytes do not match the manifest sha256"})
            continue
        phys = pdf_pages(data)
        tpath = meta.get("text_path") or f"data/text/{did}.txt"
        try:
            text = hf.get(tpath).read_bytes()
            pages_txt = _split_pages(text.decode("utf-8"))
        except Exception:
            text, pages_txt = None, None
        if phys is None or pages_txt is None or not pages_txt or max(pages_txt) > phys or min(pages_txt) < 1:
            dropped.append({"doc_id": did, "reason": "unopenable PDF or derived text pages outside the physical pages"})
            continue
        h = r["sha256"]
        doc = document_record(meta, data, phys, raw_path, a.revision)
        text_path = f"text/{did}.txt"
        d = derived_record(meta, h, text, pages_txt, phys, text_path)
        scale = 1
        while len(json.dumps(d, sort_keys=True, ensure_ascii=False).encode()) > 950_000 and scale < 8:
            scale *= 2   # contract cap: one JSONL record <= 1 MiB; very long judgments get proportionally longer passages
            d = derived_record(meta, h, text, pages_txt, phys, text_path, scale)
        docs.append(doc)
        derived.append(d)
        texts[text_path] = (text, "text")
        originals[f"originals/{h}.pdf"] = (data, "original")
        s = {"doc_id": did, "sha256": h, "bytes": len(data), "pages": phys, "doc_type": doc["doc_type"],
             "hf_path": raw_path, "text_sha256": d["text_sha256"], "text_hf_path": tpath}
        sample.append(s)
        derived_by_doc[did] = dict(d, _pages=pages_txt, _blob=git_blob_sha(text))
    print(f"documents built: {len(docs)}; dropped: {len(dropped)}")

    cands = a2_candidates(sample, derived_by_doc, None) + a5_candidates(sample)
    cands = [c for c in cands if not register.deep_match(c)]
    a4 = [json.loads(x) for x in A4_JSONL.read_text(encoding="utf-8").splitlines() if x.strip()]
    a4 = [x for x in a4 if not register.deep_match(x)]
    a4_bytes = "".join(json.dumps(x, sort_keys=True, ensure_ascii=False) + "\n" for x in a4).encode()

    lex = json.loads(hf.get(LEXICON).read_text(encoding="utf-8"))["abbreviations"]
    abbr = []
    for code, v in sorted(lex.items()):
        if code.isupper() and code.isalpha() and 2 <= len(code) <= 6 and v.get("preferred"):
            abbr.append({"code": code, "preferred": v["preferred"][:2], "origin": "Army abbreviations lexicon v1.0 (HF reference "
                         "data; structurally checked, not certified; " + str(v.get("preferred_basis")) + ")"})
    have = {x["code"] for x in abbr}
    abbr += [{"code": k, "preferred": v, "origin": "P2 legal-procedure supplement (not lexicon data)"}
             for k, v in sorted(SUPPLEMENT.items()) if k not in have]
    abbr = [x for x in abbr if not register.deep_match(x)]
    abbr_bytes = "".join(json.dumps(x, sort_keys=True, ensure_ascii=False) + "\n" for x in abbr).encode()

    head = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    stamp = datetime.now(timezone.utc)
    reg_sha = sha((REPO / "config/restricted_material.json").read_bytes())
    content = sha(json.dumps(sorted((s["doc_id"], s["sha256"]) for s in sample)).encode())[:8]
    release_id = f"R13-b1-sample-{stamp:%Y%m%d}-{content}"
    manifest = json.loads((REPO / "app/contract/examples/release_manifest.example.json").read_text())
    manifest.update(release_id=release_id, created_at=stamp.strftime("%Y-%m-%dT%H:%M:%SZ"), release_sequence=1)
    manifest["pinned"] = {"hf_repo": HF_REPO, "hf_revision": a.revision, "tools_commit": head[:12],
                          "artefact_commits": {"a2_outcome_v4": "9cdd5008", "a5_graph": "e15af208", "a4_statutory": head[:12]},
                          "model_bundles": []}
    manifest["restricted_material"] = {"config_path": "config/restricted_material.json", "config_sha256": reg_sha,
                                       "restriction_ids_applied": ["RM-001"]}
    manifest["candidate_banner"] = {"required": True, "text": BANNER}
    key, pub = new_dev_keypair()
    bundle = work / "bundle" / release_id
    if bundle.exists():
        import shutil
        shutil.rmtree(bundle)
    extra = dict(originals)
    extra.update(texts)
    extra["research/a4_provision_versions.jsonl"] = (a4_bytes, "report")
    extra["research/abbreviations_v1.0.jsonl"] = (abbr_bytes, "report")
    clean = [{k: v for k, v in d.items()} for d in derived]
    write_bundle(bundle, manifest, documents=docs, derived=clean, candidates=cands, extra_files=extra,
                 signing_key=key, public_key_raw=pub)
    (work / "bundle" / f"{release_id}.dev-public-key.hex").write_text(pub.hex())
    del key  # disposable development key: never persisted

    site = work / "site"
    if not (site / "SITE_CONFIG.json").exists():
        configure_site(site, exclusion_channel="none")
    res = import_release(bundle, site, trusted_public_key=pub, mode="development", register=register)
    unresolved = {}
    for u in res.unresolved:
        unresolved[u["kind"]] = unresolved.get(u["kind"], 0) + 1
    print(f"import: activated={res.activated} noop={res.noop} refused={res.refused_reasons[:3]} "
          f"verified docs={len(res.verified['documents'])} derived={len(res.verified['derived_text'])} "
          f"candidates={len(res.verified['candidates'])} unresolved={unresolved}")
    out = {
        "description": "B1 offline sample bundle manifest. Corpus bytes are NOT in git; they live under the scratchpad "
                       "work directory and can be rebuilt from the HF revision with app/b1/build/build_sample.py.",
        "release_id": release_id, "hf_repo": HF_REPO, "hf_revision": a.revision, "built_at": manifest["created_at"],
        "tools_commit": head, "selection": {"seed": SEED, "supreme_court": N_SC, "high_court_per_court": N_HC_PER_COURT,
                                            "high_courts": list(HC_COURTS), "non_judgment": "all except restricted",
                                            "force_include": list(FORCE_INCLUDE)},
        "restricted_material": {"config_sha256": reg_sha, "excluded_before_download": excluded},
        "signing": "development key generated in memory and discarded; public key beside the bundle; NOT a production key",
        "counts": {"documents": len(docs), "dropped": len(dropped), "candidates": len(cands),
                   "a2_outcomes": sum(c["candidate_type"] == "outcome" for c in cands),
                   "a5_graph_edges": sum(c["candidate_type"] == "graph_edge" for c in cands),
                   "a4_provision_versions": len(a4), "abbreviations": len(abbr),
                   "by_type": {t: sum(s["doc_type"] == t for s in sample) for t in sorted({s["doc_type"] for s in sample})},
                   "pages": sum(s["pages"] for s in sample), "bytes": sum(s["bytes"] for s in sample)},
        "import": {"activated": res.activated, "noop": res.noop, "refused_reasons": res.refused_reasons,
                   "verified": {k: len(v) for k, v in res.verified.items()}, "unresolved_by_kind": unresolved,
                   "contract_errors": res.contract_errors},
        "dropped": dropped,
        "documents": sorted(sample, key=lambda s: s["doc_id"]),
    }
    a.manifest_out.parent.mkdir(parents=True, exist_ok=True)
    a.manifest_out.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    return 0 if res.activated or res.noop else 1


if __name__ == "__main__":
    sys.exit(main())
