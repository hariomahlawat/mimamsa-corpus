"""Release import with source-fidelity verification (ASR-E05; contract README §8 assigns this to the importer).

Sequence:
  1 Contract validation of the whole bundle (signature first, checksums, schema, rules, restricted register).
    Any error refuses the import; nothing is written to the vault or generations; the active generation is untouched.
  2 Source verification for every document, against the bundled bytes (not the declared metadata):
    an `original` file must exist in the bundle whose SHA-256 equals source_copy.sha256, whose size equals
    source_copy.bytes, whose canonical vault key equals source_copy.vault_path, and whose measured physical page
    count equals source_copy.page_count (PDF via pypdfium2; text/plain = form-feed separated pages). Any document
    failure refuses activation of the whole generation (a release never activates with a missing or mismatched
    claimed copy).
  3 Derivative verification for every derived_text record: its source copy must be a verified document copy of the
    same doc_id; its text file must be bundled with SHA-256 equal to text_sha256; every declared page must be a
    physical page of the original and its char_count must equal the measured page text length; every passage must
    lie inside its page ([char_start, char_end] within the page text) and hash to its text_sha256.
  4 Anchor verification for every candidate: each anchor's copy must be the source document's own copy (or a
    declared alternate) and verified; its page must be a physical page of that copy; a span bound to a derivative
    (pipeline name, version, derivative_text_sha256) must resolve to a verified derivative and passage with offsets
    inside it. Unbound spans are kept page-only.
  Items failing 3 or 4 get disposition UNRESOLVED (quarantined with reasons) and are never servable.
  5 Only then: write verified originals to the content-addressed vault (write-once, verify-if-present), write the
    generation (servable + quarantine lists) and switch the ACTIVE pointer atomically. The previous generation is
    retained.

Derived text page format: the text file uses `[[page N]]` marker lines; page N's text is everything after its marker
line up to the next marker line, with the single newline that precedes the next marker (or ends the file) removed.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from mimamsa_contract.bundle import validate_bundle

_MARKER = re.compile(r"^\[\[page (\d+)\]\]\n", re.M)


@dataclass
class ImportResult:
    release_id: str | None
    activated: bool
    refused_reasons: list = field(default_factory=list)
    verified: dict = field(default_factory=lambda: {"documents": [], "derived_text": [], "candidates": []})
    unresolved: list = field(default_factory=list)   # [{kind, id, reasons}]
    contract_errors: list = field(default_factory=list)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _page_count(data: bytes, mime: str) -> int | None:
    if mime == "application/pdf":
        try:
            import pypdfium2 as pdfium
            pdf = pdfium.PdfDocument(data)
            try:
                return len(pdf)
            finally:
                pdf.close()
        except Exception:  # unopenable PDF
            return None
    if mime == "text/plain":
        return data.count(b"\f") + 1
    return None  # no verified page counter for this type: cannot serve


def _split_pages(text: str) -> dict[int, str] | None:
    marks = list(_MARKER.finditer(text))
    if not marks or marks[0].start() != 0:
        return None
    pages = {}
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        body = text[m.end():end]
        if body.endswith("\n"):
            body = body[:-1]
        n = int(m.group(1))
        if n in pages:
            return None
        pages[n] = body
    return pages


def _jsonl(path: Path):
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _records(root: Path, manifest: dict, kind: str):
    out = []
    for f in manifest.get("files", []):
        if f.get("kind") == kind:
            out += _jsonl(root / f["path"])
    return out


def active_generation(site: Path) -> dict | None:
    p = Path(site) / "ACTIVE"
    if not p.exists():
        return None
    gen = p.read_text(encoding="utf-8").strip()
    return json.loads((Path(site) / "generations" / gen / "generation.json").read_text(encoding="utf-8"))


def servable(site: Path, kind: str, item_id: str) -> bool:
    """True only for items verified in the ACTIVE generation. Quarantined or unknown items are never servable."""
    gen = active_generation(site)
    return bool(gen) and item_id in gen["servable"].get(kind, [])


def import_release(bundle: Path, site: Path, *, trust_list=None, trusted_public_key=None, mode="production",
                   register=None, current_release_sequence=None, rollback=False, today=None) -> ImportResult:
    bundle, site = Path(bundle), Path(site)
    rep = validate_bundle(bundle, trust_list=trust_list, trusted_public_key=trusted_public_key, mode=mode,
                          register=register, current_release_sequence=current_release_sequence, rollback=rollback,
                          today=today)
    manifest = {}
    try:
        manifest = json.loads((bundle / "RELEASE.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    res = ImportResult(release_id=manifest.get("release_id"), activated=False)
    if not rep.ok:
        res.contract_errors = sorted({i.code for i in rep.errors})
        res.refused_reasons.append("contract validation failed: " + ", ".join(res.contract_errors))
        return res

    # Bundled originals by actual content hash (recomputed, not taken from the manifest).
    originals = {}
    for f in manifest.get("files", []):
        if f.get("kind") == "original":
            data = (bundle / f["path"]).read_bytes()
            originals.setdefault(_sha(data), data)
    texts = {}
    for f in manifest.get("files", []):
        if f.get("kind") == "text":
            data = (bundle / f["path"]).read_bytes()
            texts[f["path"]] = data

    docs = _records(bundle, manifest, "documents_jsonl")
    derived = _records(bundle, manifest, "derived_text_jsonl")
    cands = _records(bundle, manifest, "candidates_jsonl")

    # 2 documents
    copy_pages: dict[str, int] = {}
    doc_by_id = {}
    for d in docs:
        sc = d["source_copy"]
        h, reasons = sc["sha256"], []
        data = originals.get(h)
        if data is None:
            reasons.append("claimed original not present in the bundle (no bundled bytes with this SHA-256)")
        else:
            if len(data) != sc["bytes"]:
                reasons.append(f"size mismatch: declared {sc['bytes']}, bundled {len(data)}")
            if sc["vault_path"] != f"vault/sha256/{h[:2]}/{h}":
                reasons.append("vault key does not match the content hash")
            pages = _page_count(data, sc["mime_type"])
            if pages is None:
                reasons.append(f"physical page count cannot be verified for {sc['mime_type']} (unopenable or unsupported)")
            elif sc.get("page_count") is not None and pages != sc["page_count"]:
                reasons.append(f"page count mismatch: declared {sc['page_count']}, measured {pages}")
            if pages is not None and not reasons:
                copy_pages[h] = pages
        if reasons:
            res.refused_reasons.append(f"document {d['doc_id']}: " + "; ".join(reasons))
            res.unresolved.append({"kind": "document", "id": d["doc_id"], "reasons": reasons})
        else:
            res.verified["documents"].append(d["doc_id"])
            doc_by_id[d["doc_id"]] = d
    if res.refused_reasons:
        return res  # a release never activates with a missing or mismatched claimed copy

    # 3 derivatives
    verified_derivs = {}  # (sha, name, version, text_sha) -> pages dict + passages
    for t in derived:
        key = (t["source_copy_sha256"], t["pipeline"]["name"], t["pipeline"]["version"], t["text_sha256"])
        reasons = []
        doc = doc_by_id.get(t["doc_id"])
        if doc is None or doc["source_copy"]["sha256"] != t["source_copy_sha256"]:
            reasons.append("declared source is not the verified copy of this doc_id")
        raw = texts.get(t["text_path"])
        pages_txt = None
        if raw is None:
            reasons.append("derived text file not bundled")
        elif _sha(raw) != t["text_sha256"]:
            reasons.append("derived text SHA-256 mismatch")
        else:
            pages_txt = _split_pages(raw.decode("utf-8"))
            if pages_txt is None:
                reasons.append("derived text lacks well-formed [[page N]] markers")
        phys = copy_pages.get(t["source_copy_sha256"])
        for pg in t["pages"]:
            if phys is None or not (1 <= pg["page"] <= phys):
                reasons.append(f"page {pg['page']} is not a physical page of the original")
            elif pages_txt is not None:
                if pg["page"] not in pages_txt:
                    reasons.append(f"page {pg['page']} absent from the derived text")
                elif len(pages_txt[pg["page"]]) != pg["char_count"]:
                    reasons.append(f"page {pg['page']} char_count {pg['char_count']} != measured {len(pages_txt[pg['page']])}")
        for ps in t["passages"]:
            body = (pages_txt or {}).get(ps["page"])
            if body is None:
                reasons.append(f"passage {ps['passage_id']} on a page without verified text")
            elif not (0 <= ps["char_start"] <= ps["char_end"] <= len(body)):
                reasons.append(f"passage {ps['passage_id']} offsets outside its page")
            elif _sha(body[ps["char_start"]:ps["char_end"]].encode("utf-8")) != ps["text_sha256"]:
                reasons.append(f"passage {ps['passage_id']} text hash mismatch")
        did = f"{t['doc_id']}@{t['pipeline']['name']}/{t['pipeline']['version']}"
        if reasons:
            res.unresolved.append({"kind": "derived_text", "id": did, "reasons": reasons})
        else:
            res.verified["derived_text"].append(did)
            verified_derivs[key] = {p["passage_id"]: p for p in t["passages"]}

    # 4 candidate anchors
    evidence = {}
    for c in cands:
        reasons = []
        doc = doc_by_id.get(c["source_doc_id"])
        own = {doc["source_copy"]["sha256"], *doc.get("alternate_copy_sha256", [])} if doc else set()
        for a in c["anchors"]:
            h = a["source_copy_sha256"]
            if h not in own:
                reasons.append("anchor copy is not the source document's copy")
            if h not in copy_pages:
                reasons.append("anchor copy not verified")
            elif not (1 <= a["page"] <= copy_pages[h]):
                reasons.append(f"anchor page {a['page']} is not a physical page of the copy")
            bound = all(a.get(k) for k in ("pipeline_name", "pipeline_version", "derivative_text_sha256"))
            if bound:
                passages = verified_derivs.get((h, a["pipeline_name"], a["pipeline_version"], a["derivative_text_sha256"]))
                if passages is None:
                    reasons.append("span bound to an unverified or absent derivative")
                else:
                    p = passages.get(a.get("passage_id")) if a.get("passage_id") else None
                    if a.get("passage_id") and p is None:
                        reasons.append("span passage not in the derivative")
                    if p is not None and a.get("char_start") is not None and not (
                            p["char_start"] <= a["char_start"] <= (a.get("char_end") or a["char_start"]) <= p["char_end"]):
                        reasons.append("span offsets outside the passage")
        if reasons:
            res.unresolved.append({"kind": "candidate", "id": c["candidate_id"], "reasons": sorted(set(reasons))})
        else:
            res.verified["candidates"].append(c["candidate_id"])
            evidence[c["candidate_id"]] = {
                "artefact_commit": c["extractor"]["artefact_commit"],
                "anchors": [{"source_copy_sha256": a["source_copy_sha256"], "page": a["page"],
                             "text_sha256": a.get("text_sha256")} for a in c["anchors"]]}

    # 5 vault, generation, atomic activation
    vault = site / "vault" / "sha256"
    for h in copy_pages:
        target = vault / h[:2] / h
        if target.exists():
            if _sha(target.read_bytes()) != h:
                res.refused_reasons.append(f"vault object {h[:12]} exists with different bytes; halt")
                return res
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(".tmp")
        with open(tmp, "wb") as fh:
            fh.write(originals[h])
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, target)
        os.chmod(target, 0o444)
    gen_id = res.release_id
    gdir = site / "generations" / gen_id
    gdir.mkdir(parents=True, exist_ok=True)
    generation = {"release_id": gen_id, "release_sequence": manifest.get("release_sequence"),
                  "servable": res.verified, "quarantine": res.unresolved, "candidate_evidence": evidence}
    (gdir / "generation.json").write_text(json.dumps(generation, indent=1, sort_keys=True), encoding="utf-8")
    tmp = site / "ACTIVE.tmp"
    tmp.write_text(gen_id, encoding="utf-8")
    os.replace(tmp, site / "ACTIVE")
    res.activated = True
    return res
