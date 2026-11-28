"""Release import with source-fidelity verification (ASR-E05; contract README §8 assigns this to the importer).

Sequence:
  0 Replay/no-op: the active generation's release_sequence is read from the site (never trusted from the caller).
    Re-importing the exact active bundle (same release_id and SHA256SUMS digest) is a no-op. Any other bundle whose
    release_id already has a generation is refused (generations are never rewritten).
  1 Contract validation of the whole bundle (signature first, checksums, schema, rules, restricted register), with
    current_release_sequence = the site's active sequence (older or equal refused unless the explicit rollback path).
    Any error refuses the import; nothing is written.
  2 Source verification for every document against the bundled bytes: an `original` exists whose SHA-256 equals
    source_copy.sha256; size equals `bytes`; vault key matches; the content type is detected from the bytes
    (`%PDF-` magic -> application/pdf; strict UTF-8 without PDF magic -> text/plain) and must equal the declared
    mime_type; the physical page count is measured from the bytes (pypdfium2 for PDF; form-feed pages for text)
    and must equal page_count. Any failure refuses activation of the whole generation.
  3 Derivatives: declared source is the verified copy of the doc_id; text file bundled with matching SHA-256;
    declared pages are physical pages of the original with matching char_count; passages lie inside their page and
    hash to text_sha256. Failures -> UNRESOLVED (quarantined, never servable).
  4 Candidate anchors: copy is the source document's own copy (or declared alternate) and verified; page is a
    physical page. A span bound to a derivative (pipeline name, version, derivative_text_sha256) must resolve to a
    verified derivative page; offsets (either or both) are range-checked against the page (and the passage when a
    passage_id is given); a declared text_sha256 is recomputed from the verified page text. Unbound spans are served
    page-only: their unverified passage_id/offsets/hash are stripped from the served evidence and flagged.
  5 Write verified originals to the content-addressed vault (write-once, retained across generations), update the
    append-only held-copies index, build the generation in a temporary directory (fsync), rename it into place,
    then switch ACTIVE (temp file, fsync, rename, directory fsync where the OS supports it).

Derived text page format: `[[page N]]` marker lines; page N's text runs to the next marker line, with the single
newline before the next marker (or the end of file) removed.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

from mimamsa_contract.bundle import validate_bundle

_MARKER = re.compile(r"^\[\[page (\d+)\]\]\n", re.M)


class ImporterError(RuntimeError):
    """Typed failure of the importer's site storage (never a raw OSError/FileExistsError)."""


def _crashpoint(name: str):
    """Test hook for crash injection; no-op in normal operation."""


SITE_CONFIG = "SITE_CONFIG.json"


LATCH = "EXCLUSION_LATCH"


JOURNAL_MARKERS = ("journal/journal.jsonl", "activation-state/SITE_INIT.json")   # B06 SiteLayout paths


def journal_managed(site: Path) -> bool:
    """True once the B06 activation journal manages the site (initialised or any journal entry). One-way."""
    return any((Path(site) / p).exists() for p in JOURNAL_MARKERS)


def _latched(site: Path) -> bool:
    """True once the site has ever been in exclusion-store mode: the store's latch exists (any exclusion accepted),
    or any generation recorded mode "signed". One-way: nothing clears it."""
    site = Path(site)
    if (site / LATCH).exists():
        return True
    gens = site / "generations"
    if gens.exists():
        for g in gens.iterdir():
            f = g / "generation.json"
            if f.is_file():
                try:
                    if json.loads(f.read_text(encoding="utf-8")).get("exclusion_channel") == "signed":
                        return True
                except ValueError:
                    return True  # unreadable generation: assume the stricter mode
    return False


def _site_mode(site: Path) -> str:
    return "signed" if _latched(site) else _site_channel(site)


def configure_site(site: Path, *, exclusion_channel: str):
    """Install-time site configuration. exclusion_channel is "signed" (an ExclusionStore accepted state must be
    supplied to every serving decision) or "none" (explicitly no exclusion channel; only then may serving decisions
    run with exclusions=None). The value is recorded in every generation the importer writes."""
    if exclusion_channel not in ("signed", "none"):
        raise ImporterError("exclusion_channel must be 'signed' or 'none'")
    if exclusion_channel == "none" and (_latched(site) or (Path(site) / "exclusions").exists()):
        raise ImporterError("site is latched to exclusion-store mode; it can never be downgraded to 'none'")
    Path(site).mkdir(parents=True, exist_ok=True)
    _write_atomic(Path(site) / SITE_CONFIG, json.dumps({"exclusion_channel": exclusion_channel}).encode())


def _site_channel(site: Path) -> str:
    try:
        return json.loads((Path(site) / SITE_CONFIG).read_text(encoding="utf-8"))["exclusion_channel"]
    except (OSError, ValueError, KeyError):
        return "signed"


@dataclass
class ImportResult:
    release_id: str | None
    activated: bool
    noop: bool = False
    resumed: bool = False
    refused_reasons: list = field(default_factory=list)
    verified: dict = field(default_factory=lambda: {"documents": [], "derived_text": [], "candidates": []})
    unresolved: list = field(default_factory=list)   # [{kind, id, reasons}]
    contract_errors: list = field(default_factory=list)
    c16: dict = field(default_factory=dict)          # C16 stage report: codes, per-copy outcomes, accounting
    staged: bool = False                             # stage_only: generation written, ACTIVE left to the journal (B06)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _detect_type(data: bytes) -> str | None:
    if data.startswith(b"%PDF-"):
        return "application/pdf"
    try:
        data.decode("utf-8", errors="strict")
        return "text/plain"
    except UnicodeDecodeError:
        return None


def _page_count(data: bytes, detected: str) -> int | None:
    if detected == "application/pdf":
        try:
            import pypdfium2 as pdfium
            pdf = pdfium.PdfDocument(data)
            try:
                return len(pdf)
            finally:
                pdf.close()
        except Exception:  # unopenable PDF
            return None
    if detected == "text/plain":
        return data.count(b"\f") + 1
    return None


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


def _fsync_dir(path: Path):
    try:  # POSIX; Windows does not allow opening a directory this way (NTFS durability proven in P8)
        fd = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def _write_atomic(path: Path, data: bytes):
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "wb") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)
    _fsync_dir(path.parent)


def active_generation(site: Path) -> dict | None:
    p = Path(site) / "ACTIVE"
    if not p.exists():
        return None
    gen = p.read_text(encoding="utf-8").strip()
    return json.loads((Path(site) / "generations" / gen / "generation.json").read_text(encoding="utf-8"))


def _generations(site: Path):
    gens = Path(site) / "generations"
    if not gens.exists():
        return []
    out = []
    for g in sorted(gens.iterdir()):
        if g.name.startswith(".") or not (g / "generation.json").is_file():
            continue
        out.append(json.loads((g / "generation.json").read_text(encoding="utf-8")))
    return out


def held_copies(site: Path) -> dict:
    """Copies held by activated generations only: generations whose release_sequence is at or below the ACTIVE one
    (a generation renamed into place but never activated has a higher sequence and is excluded). Derived on demand,
    so no separate index can get ahead of activation after a crash."""
    active = active_generation(site)
    if not active:
        return {}
    held = {}
    # SG-1: a copy the ACTIVE generation governs and does not serve is not held from an earlier generation either.
    denied = {tuple(k) for k in (active.get("c16") or {}).get("denied", [])}
    for g in sorted(_generations(site), key=lambda x: x.get("release_sequence") or 0):
        if (g.get("release_sequence") or 0) > (active.get("release_sequence") or 0):
            continue
        for did, h in g.get("item_document", {}).get("documents", {}).values():
            if (did, h) in denied:
                continue
            held.setdefault(h, {"doc_id": did, "page_count": g.get("page_counts", {}).get(h), "first_release": g["release_id"]})
    return held


def _excluded(exclusions, doc_id: str | None, sha: str | None) -> bool:
    if exclusions is None:
        return False
    return bool(exclusions.register.is_restricted(sha256=sha, doc_id=doc_id)
                or doc_id in exclusions.withdrawn_doc_ids or sha in exclusions.withdrawn_shas
                or doc_id in exclusions.tombstone_doc_ids or sha in exclusions.tombstone_shas
                or doc_id in exclusions.restricted_tombstone_doc_ids or sha in exclusions.restricted_tombstone_shas)


def _exclusions_usable(site: Path, exclusions, gen: dict | None) -> bool:
    """One fail-closed guard for every serving decision. A supplied state must be a real ExclusionState. None is
    allowed only when the site was configured at install with exclusion_channel "none", the active generation recorded
    that mode, and no exclusion store directory exists. Anything else (missing, empty, unreadable or pending-only
    store, unknown mode) denies."""
    from mimamsa_contract.exclusions import ExclusionState
    if exclusions is not None:
        return isinstance(exclusions, ExclusionState)
    return (_site_mode(site) == "none" and bool(gen) and gen.get("exclusion_channel") == "none"
            and not (Path(site) / "exclusions").exists())


def servable(site: Path, kind: str, item_id: str, *, exclusions) -> bool:
    """Serving decision: the item is verified in the ACTIVE generation AND not withdrawn or restricted under the
    current exclusion state (`ExclusionStore.effective_state`). Fails closed (see _exclusions_usable)."""
    site = Path(site)
    gen = active_generation(site)
    if not _exclusions_usable(site, exclusions, gen):
        return False
    if not gen or item_id not in gen["servable"].get(kind, []):
        return False
    owner = gen["item_document"].get(kind, {}).get(item_id)  # [doc_id, copy sha]
    return bool(owner) and not _excluded(exclusions, owner[0], owner[1])


MATERIALIZED_FORMAT = 1
# C16 CP-1: a generation imported with stage_only=True is written completely but ACTIVE is not switched; the B06
# activation journal switches it. Recovery neither resumes nor quarantines such a generation.
ACTIVATION_JOURNAL = "JOURNAL"
RESEARCH_PREFIX = "research/"


def _research_files(bundle: Path, manifest: dict, register) -> tuple[dict[str, bytes], list[tuple[str, str]]]:
    """Signed, checksummed `report` files under research/ (JSONL research aids such as A4 provision versions).
    They are not source evidence: the importer only re-checks the restricted register on every line (fail closed for
    the whole file) and copies them verbatim; the application resolves any copy/page they name against the verified
    copies of the active generation and labels them AUTOMATED_CANDIDATE_NOT_VERIFIED."""
    from mimamsa_contract.restricted import load_register
    reg = register or load_register()
    keep, rejected = {}, []
    for f in manifest.get("files", []):
        rel = f.get("path", "")
        if f.get("kind") != "report" or not rel.startswith(RESEARCH_PREFIX) or not rel.endswith(".jsonl"):
            continue
        data = (bundle / rel).read_bytes()
        try:
            lines = [json.loads(x) for x in data.decode("utf-8").splitlines() if x.strip()]
        except (UnicodeDecodeError, ValueError):
            rejected.append((rel, "research file is not valid UTF-8 JSONL"))
            continue
        if reg.match(path=rel) or any(reg.deep_match(x) for x in lines):
            rejected.append((rel, "research file references restricted material"))
            continue
        keep[rel] = data
    return keep, rejected


def _materialize(gdir: Path, manifest: dict, docs, derived, cands, texts: dict, verified: dict, research: dict, extra=None):
    """Write the verified records and verified derivative text into the (temporary) generation directory, so that a
    serving process reads only importer-verified evidence from the ACTIVE generation (plus vault originals). Items
    that are UNRESOLVED are never written. Same fsync discipline as generation.json; the directory is renamed into
    place as a whole, so a crash leaves either nothing or a complete generation."""
    ok_docs = set(verified["documents"])
    ok_der = set(verified["derived_text"])
    ok_cand = set(verified["candidates"])

    def did(t):
        return f"{t['doc_id']}@{t['pipeline']['name']}/{t['pipeline']['version']}"

    out = {
        "records/documents.jsonl": [d for d in docs if d["doc_id"] in ok_docs],
        "records/derived_text.jsonl": [t for t in derived if did(t) in ok_der],
        "records/candidates.jsonl": [c for c in cands if c["candidate_id"] in ok_cand],
    }
    files = {rel: "".join(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n" for r in recs).encode("utf-8")
             for rel, recs in out.items()}
    for t in out["records/derived_text.jsonl"]:
        files[f"derived/{t['text_sha256']}.txt"] = texts[t["text_path"]]
    files["release/RELEASE.json"] = json.dumps({k: manifest.get(k) for k in (
        "release_id", "release_sequence", "created_at", "pinned", "candidate_banner", "auth_ledger_version",
        "restricted_material", "schema_versions")}, indent=1, sort_keys=True).encode()
    for rel, data in research.items():
        files[rel] = data
    for rel, data in (extra or {}).items():  # C16: corpus-v2/, c16/, registers/ (verified, see c16.materialize)
        files[rel] = data
    for rel, data in files.items():
        p = gdir / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
    for sub in {p.parent for p in gdir.rglob("*") if p.is_file()}:
        _fsync_dir(sub)


def import_release(bundle: Path, site: Path, *, trust_list=None, trusted_public_key=None, mode="production",
                   register=None, rollback=False, today=None, exclusions=None, stage_only=False) -> ImportResult:
    """exclusions: the site's current ExclusionState (optional). The C16 stage uses it for I-5 legacy establishment
    and to keep withdrawn or restricted copies out of service; serving still applies the current state per request."""
    bundle, site = Path(bundle), Path(site)
    try:
        manifest = json.loads((bundle / "RELEASE.json").read_text(encoding="utf-8"))
        sums_digest = _sha((bundle / "SHA256SUMS").read_bytes())
    except (OSError, ValueError):
        manifest, sums_digest = {}, None
    res = ImportResult(release_id=manifest.get("release_id"), activated=False)

    # C16 CP-1: on a site managed by the activation journal (B06), only the journal switches ACTIVE. A direct
    # activation is refused before anything is written; the import must be stage_only (rollbacks go through the journal).
    if journal_managed(site) and not stage_only:
        res.refused_reasons.append("ACTIVATION_JOURNAL_MANAGED: this site is activated through the journal; import with stage_only")
        return res

    # 0a exclusion-mode latch and store integrity (review N4)
    exclusion_mode = _site_mode(site)
    if (site / LATCH).exists():
        acc = site / "exclusions" / "ACCEPTED.json"
        try:
            json.loads(acc.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ImporterError("exclusion store missing or unreadable on a latched site: integrity failure; "
                                "import refused (restore the store from custody)") from exc

    # 0 recovery, replay / no-op
    try:
        active = active_generation(site)
        gens = site / "generations"
        if gens.exists():
            for g in list(gens.iterdir()):
                pending = g.name.startswith(".tmp-")
                if not pending and (g / "generation.json").is_file():
                    meta = json.loads((g / "generation.json").read_text(encoding="utf-8"))
                    if meta.get("activation") == ACTIVATION_JOURNAL:
                        continue   # staged for the activation journal (B06): neither residue nor resumable here
                    if (meta.get("release_sequence") or 0) > ((active or {}).get("release_sequence") or 0):
                        if meta["release_id"] == res.release_id and meta.get("sums_sha256") == sums_digest:
                            # crash after the rename, before ACTIVE: resume activation of the identical bundle
                            _write_atomic(site / "ACTIVE", meta["release_id"].encode())
                            res.activated = res.resumed = True
                            return res
                        pending = True
                if pending:  # never-activated residue: quarantined, not deleted
                    q = site / "quarantine" / "generations"
                    q.mkdir(parents=True, exist_ok=True)
                    os.replace(g, q / f"{g.name.lstrip('.')}-{time.time_ns()}")
    except OSError as exc:
        raise ImporterError(f"site generation recovery failed: {type(exc).__name__}") from exc
    gdir = site / "generations" / str(res.release_id)
    if active and active["release_id"] == res.release_id and active.get("sums_sha256") == sums_digest:
        res.noop = True
        return res
    if res.release_id and gdir.exists():
        res.refused_reasons.append("a generation with this release_id already exists; generations are never rewritten")
        return res
    current = active["release_sequence"] if active else 0

    # 1 contract
    rep = validate_bundle(bundle, trust_list=trust_list, trusted_public_key=trusted_public_key, mode=mode,
                          register=register, current_release_sequence=current, rollback=rollback, today=today)
    if not rep.ok:
        res.contract_errors = sorted({i.code for i in rep.errors})
        res.refused_reasons.append("contract validation failed: " + ", ".join(res.contract_errors))
        return res

    originals, texts = {}, {}
    for f in manifest.get("files", []):
        if f.get("kind") == "original":
            data = (bundle / f["path"]).read_bytes()
            originals.setdefault(_sha(data), data)
        elif f.get("kind") == "text":
            texts[f["path"]] = (bundle / f["path"]).read_bytes()
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
            detected = _detect_type(data)
            if detected != sc["mime_type"]:
                reasons.append(f"content type mismatch: declared {sc['mime_type']}, detected {detected or 'unverifiable'}")
            pages = _page_count(data, detected) if detected == sc["mime_type"] else None
            if detected == sc["mime_type"] and pages is None:
                reasons.append(f"physical page count cannot be verified for {detected} (unopenable)")
            elif pages is not None and sc.get("page_count") is not None and pages != sc["page_count"]:
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
        return res

    # 3 derivatives
    verified_derivs = {}
    item_document = {"documents": {d: [d, doc_by_id[d]["source_copy"]["sha256"]] for d in doc_by_id},
                     "derived_text": {}, "candidates": {}}
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
            item_document["derived_text"][did] = [t["doc_id"], t["source_copy_sha256"]]
            verified_derivs[key] = {"passages": {p["passage_id"]: p for p in t["passages"]}, "pages": pages_txt}

    # 4 candidate anchors
    evidence = {}
    for c in cands:
        reasons, served_anchors = [], []
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
            has_span = any(a.get(k) is not None for k in ("passage_id", "char_start", "char_end"))
            bound = all(a.get(k) for k in ("pipeline_name", "pipeline_version", "derivative_text_sha256"))
            served = {"source_copy_sha256": h, "page": a["page"], "page_only": True, "text_sha256": None}
            if bound:
                dv = verified_derivs.get((h, a["pipeline_name"], a["pipeline_version"], a["derivative_text_sha256"]))
                body = (dv or {}).get("pages", {}).get(a["page"]) if dv else None
                if dv is None:
                    reasons.append("span bound to an unverified or absent derivative")
                elif body is None:
                    reasons.append("span page has no verified derivative text")
                else:
                    lo, hi = 0, len(body)
                    if a.get("passage_id") is not None:
                        p = dv["passages"].get(a["passage_id"])
                        if p is None or p["page"] != a["page"]:
                            reasons.append("span passage not on this page of the derivative")
                        else:
                            lo, hi = p["char_start"], p["char_end"]
                    cs = a["char_start"] if a.get("char_start") is not None else lo
                    ce = a["char_end"] if a.get("char_end") is not None else hi
                    if not (lo <= cs <= ce <= hi):
                        reasons.append("span offsets outside the verified page/passage")
                    elif a.get("text_sha256") and _sha(body[cs:ce].encode("utf-8")) != a["text_sha256"]:
                        reasons.append("anchor text hash does not match the verified derivative text")
                    else:
                        served.update(page_only=False, passage_id=a.get("passage_id"), char_start=cs, char_end=ce,
                                      text_sha256=_sha(body[cs:ce].encode("utf-8")),
                                      derivative_text_sha256=a["derivative_text_sha256"])
            elif has_span:
                served["span_stripped"] = "unbound span: passage id, offsets and hash not verified, not served"
            served_anchors.append(served)
        if reasons:
            res.unresolved.append({"kind": "candidate", "id": c["candidate_id"], "reasons": sorted(set(reasons))})
        else:
            res.verified["candidates"].append(c["candidate_id"])
            item_document["candidates"][c["candidate_id"]] = [c["source_doc_id"], doc["source_copy"]["sha256"]]
            evidence[c["candidate_id"]] = {"artefact_commit": c["extractor"]["artefact_commit"], "anchors": served_anchors}

    # C16 (Tranche B B01): strict exchange, typed receipts, byte checks, label readings, I-5 legacy, accounting.
    # Runs before anything is written: a refusal leaves the site untouched.
    from mimamsa_contract.bundle import parse_sums
    from mimamsa_contract.restricted import load_register
    from . import c16 as c16mod
    try:
        sums, _ = parse_sums((bundle / "SHA256SUMS").read_text(encoding="utf-8"))
        c16res = c16mod.run(bundle=bundle, manifest=manifest, sums=sums, site=site, docs=docs, verified_docs=doc_by_id,
                            originals=originals, copy_pages=copy_pages, register=register or load_register(),
                            exclusions=exclusions)
    except c16mod.C16SiteError as exc:
        raise ImporterError(str(exc)) from exc
    res.c16 = c16res.report()
    if c16res.refusals:
        res.contract_errors = sorted({i.code for i in c16res.refusals})
        res.refused_reasons.append("C16 exchange refused: " + ", ".join(res.contract_errors))
        return res
    if c16res.active:
        allowed, search = c16res.allowed_docs, c16res.search_docs
        res.verified["documents"] = [d for d in res.verified["documents"] if d in allowed]
        item_document["documents"] = {k: v for k, v in item_document["documents"].items() if k in allowed}
        keep_der = {k for k, v in item_document["derived_text"].items() if v[0] in search}
        res.verified["derived_text"] = [d for d in res.verified["derived_text"] if d in keep_der]
        item_document["derived_text"] = {k: v for k, v in item_document["derived_text"].items() if k in keep_der}
        item_document["candidates"] = {k: v for k, v in item_document["candidates"].items() if v[0] in allowed}
        res.verified["candidates"] = [x for x in res.verified["candidates"] if x in item_document["candidates"]]
        evidence = {k: v for k, v in evidence.items() if k in item_document["candidates"]}
        # restricted copies are not written to the vault and not named in the generation (page counts by hash)
        copy_pages = {h: n for h, n in copy_pages.items() if h not in c16res.restricted_shas}

    # 5 vault (retained across generations), held-copies index, generation, atomic activation
    vault = site / "vault" / "sha256"
    for h in copy_pages:
        target = vault / h[:2] / h
        if target.exists():
            if _sha(target.read_bytes()) != h:
                res.refused_reasons.append(f"vault object {h[:12]} exists with different bytes; halt")
                return res
            continue
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            _write_atomic(target, originals[h])
            os.chmod(target, 0o444)
        except OSError as exc:
            raise ImporterError(f"vault write failed: {type(exc).__name__}") from exc
        _crashpoint("after_vault_object")
    research, research_rejected = _research_files(bundle, manifest, register)
    for rel, why in research_rejected:
        res.unresolved.append({"kind": "research_file", "id": rel, "reasons": [why]})
    generation = {"release_id": res.release_id, "release_sequence": manifest.get("release_sequence"),
                  "sums_sha256": sums_digest, "servable": res.verified, "quarantine": res.unresolved,
                  "item_document": item_document, "candidate_evidence": evidence,
                  "page_counts": copy_pages, "exclusion_channel": exclusion_mode,
                  "materialized": {"format": MATERIALIZED_FORMAT, "records": "records/",
                                   "derived": "derived/<text_sha256>.txt", "research": sorted(research)}}
    # C16-CP1-04: the verification mode is recorded so staging can refuse a development-signed release in production
    generation["import_mode"] = "production" if mode == "production" else "development"
    if stage_only:
        generation["activation"] = ACTIVATION_JOURNAL
    c16files = None
    if c16res.active:
        c16out = c16mod.materialize(c16res)
        c16files = c16out["files"]
        generation["c16"] = c16out["section"]
        generation["materialized"]["corpus_v2"] = c16out["materialized"]
        try:  # governance is recorded before the generation exists: a crash can only leave the site stricter
            _write_atomic(site / c16mod.DECISION_INDEX, c16mod.merged_index(site, c16res.index_entries))
        except (OSError, c16mod.C16SiteError) as exc:
            raise ImporterError(f"C16 decision index write failed: {type(exc).__name__}") from exc
        _crashpoint("after_c16_index")
    try:
        gens = site / "generations"
        gens.mkdir(parents=True, exist_ok=True)
        tmpdir = gens / f".tmp-{res.release_id}"
        tmpdir.mkdir()
        _materialize(tmpdir, manifest, docs, derived, cands, texts, res.verified, research, extra=c16files)
        with open(tmpdir / "generation.json", "wb") as fh:
            fh.write(json.dumps(generation, indent=1, sort_keys=True).encode())
            fh.flush()
            os.fsync(fh.fileno())
        _fsync_dir(tmpdir)
        _crashpoint("before_rename")
        os.replace(tmpdir, gdir)
        _fsync_dir(gens)
        if stage_only:   # C16 CP-1: the activation journal (B06), not the importer, switches ACTIVE
            res.staged = True
            return res
        _crashpoint("before_active")
        _write_atomic(site / "ACTIVE", str(res.release_id).encode())
    except OSError as exc:
        raise ImporterError(f"generation activation failed: {type(exc).__name__}") from exc
    res.activated = True
    return res


def cite(site: Path, sha12: str, doc_id: str, page: int, *, exclusions) -> dict:
    """Resolve a citation permalink per app/design/policies/citation_resolution.json (ASR-E06).

    Returns {"state": ..., "copy": full sha or None, "page": page or None}. Opens only the exact cited copy; the
    current edition is never substituted. Withdrawn, restricted and not-held copies return one indistinguishable
    state (non-disclosure, security architecture §7.3)."""
    unavailable = {"state": "CITED_COPY_UNAVAILABLE", "copy": None, "page": None}
    if not _exclusions_usable(Path(site), exclusions, active_generation(site)):
        return unavailable
    held = held_copies(site)
    # Excluded copies are removed before disambiguation, so an ambiguity never reveals an excluded copy (N3).
    matches = [h for h in held if h.startswith(sha12.lower()) and not _excluded(exclusions, held[h]["doc_id"], h)]
    if len(matches) > 1:
        return {"state": "AMBIGUOUS_REFERENCE", "copy": None, "page": None}
    if not matches:
        return unavailable
    h = matches[0]
    if held[h]["doc_id"] != doc_id:
        return {"state": "REFERENCE_MISMATCH", "copy": None, "page": None}
    if not held[h]["page_count"] or not (1 <= page <= held[h]["page_count"]):
        return {"state": "CITED_PAGE_NOT_IN_COPY", "copy": None, "page": None}
    gen = active_generation(site) or {}
    docs_now = gen.get("item_document", {}).get("documents", {})
    current = docs_now.get(doc_id, [None, None])[1]
    # The permalink's release_id records where the citation was made; resolution uses the full copy hash only.
    if current == h:
        return {"state": "CITED_COPY_ELIGIBLE", "copy": h, "page": page, "current_copy": h}
    # Held and verified in an earlier generation, not withdrawn or restricted: still opened exactly as cited.
    current_ok = current is not None and not _excluded(exclusions, doc_id, current)
    return {"state": "CITED_COPY_ELIGIBLE_NOT_CURRENT", "copy": h, "page": page,
            "current_copy": current if current_ok else None}
