"""C16 signed-import stage (Tranche B, B01): contract 2.0 exchanges with contract 2.1 typed receipts, carried in a
signed v1 bundle under `corpus-v2/` (contract section 13).

The stage runs after the v1 steps 1-4 (signature, checksums, v1 rules, original/derivative/candidate byte checks) and
before anything is written to the site. It returns either bundle-level refusals (the whole bundle is refused and the
site is left untouched, consumer requirement I2) or per-copy verdicts that decide which v1 documents may be served.

Bundle level (refuse the whole bundle):
  - transport: every `corpus-v2/` and `registers/` file is listed in RELEASE.json as kind `other`;
  - strict exchange only (I2): `rules.exchange_issues(mode="strict")` with the site register and the bundle's
    AUTH-LEDGER version; a partial exchange (no GENERATION.json, missing population) is refused by construction;
  - contract: 2.0 or 2.1 only; an unknown major or minor is refused (consumer section 4);
  - restricted material (site register or the exclusion state's restriction tombstones) in any C16 record;
  - label readings (D1, D2): every folder and file-name classification is recomputed with the pinned adapter
    (`adapters.classify_path`) and must be byte-identical; explicit AR and AFT reading checks; taxonomy aliases;
  - malformed receipt artefacts anywhere under `registers/` (path, inventory, hash, parse, schema, payload
    semantics, canonical form, revision chain);
  - KNOWLEDGE_RELEASE.json (when present): release-manifest rules and component inventory against SHA256SUMS;
  - per-source admission accounting: the signed register `registers/source_accounting.json` is required once the
    site is C16-aware, and the importer's own counts must reconcile with it (I-5, SG-1).

Item level (the copy is kept out of service and counted, never guessed or repaired):
  - receipt resolution for every eligible effective admission (`receipts.resolve_receipts`, I-1, FG-RECEIPTS)
    with facts the site recomputes from the bundled bytes (hash, format, register scan, identity and copy-record
    validation, derivative units, DOCX image inventory); marking, relevance and duplicate receipts are recorded
    ASSERTED_BOUND, never site-verified;
  - byte checks (I4): size, format, PDF page count, DOCX images through the safe archive reader, derivative units
    and coverage, reconstructed-page mapping origin;
  - anchors (I8): `evidence.verify_anchor_bytes` against the verified derivative bytes;
  - I7: a C16 copy is served only when its effective admission is eligible, its receipts resolve, its byte checks
    pass, it has a verified v1 record for the same (doc_id, sha256), and it is not excluded;
  - I-5 legacy: a v1 document without a C16 sidecar is served only when independently established
    (`legacy.legacy_issues`) against the site's C16 decision index (every copy any generation ever governed), the
    candidate hashes declared in the accounting register, every hash in the exchange, and the exclusion state.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from mimamsa_contract.c16 import adapters, canonical, evidence, legacy, receipts
from mimamsa_contract.c16.rules import component_inventory_issues, exchange_issues, record_issues
from mimamsa_contract.issues import Issue

from . import safe_archive

C16_PREFIX = "corpus-v2/"
REGISTERS_PREFIX = "registers/"
ACCOUNTING_PATH = "registers/source_accounting.json"
KNOWLEDGE_MANIFEST = "KNOWLEDGE_RELEASE.json"
DECISION_INDEX = "C16_DECISION_INDEX.json"
SUPPORTED_CONTRACTS = ("mimamsa-corpus-contract/2.0", "mimamsa-corpus-contract/2.1")
LABEL_BASES = ("FOLDER_PATH", "FILENAME_PATTERN")
ACCOUNTING_KIND = "source_admission_accounting"
ACCOUNTING_PATHS = ("V1", "C16", "V7_REFERENCE")
COUNT_FIELDS = ("input", "identities", "held", "rejected", "quarantined", "eligible", "served")
MIME_FORMAT = {"application/pdf": "PDF", "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "DOCX",
               "image/png": "PNG", "image/jpeg": "JPEG"}
RECOMPUTABLE_FORMATS = ("PDF", "DOCX", "PNG", "JPEG")


class C16SiteError(RuntimeError):
    """The site's C16 state (decision index) is missing or unreadable where it must exist: fail closed."""


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _e(code: str, msg: str, where: str = "") -> Issue:
    return Issue(code, msg, where)


@dataclass
class C16Result:
    active: bool = False
    refusals: list = field(default_factory=list)
    contract: str | None = None
    corpus_generation_id: str | None = None
    exchange_files: dict = field(default_factory=dict)      # name -> bytes (verbatim, verified)
    copies: list = field(default_factory=list)              # per identity verdicts
    anchors: list = field(default_factory=list)             # per anchor byte verdicts
    legacy: list = field(default_factory=list)              # v1 documents without a sidecar
    allowed_docs: set = field(default_factory=set)          # v1 doc ids that may be served
    search_docs: set = field(default_factory=set)           # allowed docs whose text may be indexed
    denied: list = field(default_factory=list)              # (doc_id, sha256) governed or checked and not served
    restricted_shas: set = field(default_factory=set)       # never written anywhere (vault, page counts, reports)
    accounting: list = field(default_factory=list)
    declared_accounting: bytes | None = None
    resolved_receipts: list = field(default_factory=list)
    receipt_files: dict = field(default_factory=dict)       # path -> bytes of artefacts resolved for served copies
    index_entries: list = field(default_factory=list)
    codes: Counter = field(default_factory=Counter)

    def report(self) -> dict:
        """Import report section (numbers, ids and hashes only; no paths, no text)."""
        return {"active": self.active, "contract": self.contract, "corpus_generation_id": self.corpus_generation_id,
                "refusal_codes": sorted({i.code for i in self.refusals}), "codes": dict(sorted(self.codes.items())),
                "copies": self.copies, "legacy": self.legacy, "accounting": self.accounting}


# ----------------------------------------------------------------------------------------------- site decision index

def load_decision_index(site: Path) -> list[dict]:
    """Every C16 governance fact the site has ever accepted (append-only, rewritten atomically). Missing file means
    no fact from the index itself; an unreadable file fails closed."""
    p = Path(site) / DECISION_INDEX
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        entries = data["entries"]
        if data.get("format") != 1 or not isinstance(entries, list):
            raise ValueError("format")
        for e in entries:
            if not (isinstance(e, dict) and isinstance(e.get("doc_id"), str) and isinstance(e.get("sha256"), str)):
                raise ValueError("entry")
        return entries
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise C16SiteError("C16 decision index unreadable: integrity failure; import refused") from exc


def _generation_governance(site: Path) -> list[dict]:
    """Copies governed by C16 in any generation present on the site (belt and braces beside the index)."""
    out = []
    gens = Path(site) / "generations"
    if not gens.exists():
        return out
    for g in sorted(gens.iterdir()):
        f = g / "generation.json"
        if g.name.startswith(".") or not f.is_file():
            continue
        try:
            c16 = json.loads(f.read_text(encoding="utf-8")).get("c16") or {}
        except ValueError as exc:
            raise C16SiteError("a generation record is unreadable: integrity failure; import refused") from exc
        for c in c16.get("governed", []):
            out.append({"doc_id": c[0], "sha256": c[1]})
    return out


def merged_index(site: Path, new_entries: list[dict]) -> bytes:
    old = load_decision_index(site)
    seen, out = set(), []
    for e in old + new_entries:
        key = canonical.canonical_bytes(e)
        if key not in seen:
            seen.add(key)
            out.append(e)
    out.sort(key=lambda e: (e["doc_id"], e["sha256"], e.get("release_id") or "", e.get("admission_id") or ""))
    return json.dumps({"format": 1, "entries": out}, indent=1, sort_keys=True).encode()


# ----------------------------------------------------------------------------------------------- label readings (D1, D2)

def classification_issues(identities: list[dict], relationships: list[dict], taxonomy: list[dict]) -> list[Issue]:
    """Recompute every owner folder and file-name classification with the pinned adapter rules and refuse any
    difference; then check the owner decisions explicitly (defence in depth):
    D1 AR = Army Rules, 1954, only in the local classified collection, only as a CANDIDATE association;
    D2 AFT = the Armed Forces Tribunal (no provision); only an explicit 'AFT Act' reference reads AFT-2007."""
    out: list[Issue] = []
    groups: dict[tuple, list[dict]] = {}
    for r in relationships:
        if r["evidentiary_basis"] not in LABEL_BASES:
            continue
        cp = r.get("classification_provenance")
        s = r["subject"]
        if not cp:
            out.append(_e("C16_CLASSIFICATION_MISMATCH", "label-based relationship without classification provenance", s["doc_id"]))
            continue
        groups.setdefault((s["doc_id"], s["source_copy_sha256"], s.get("graph_node_ref"), cp["collection"], cp["relative_path"],
                           cp.get("inventory_id")), []).append(r)
    for d in identities:
        for o in d["provenance"].get("observations") or []:
            if str(o.get("collection", "")).startswith("local:"):
                groups.setdefault((d["doc_id"], d["source_copy"]["sha256"], d["work_identity"].get("graph_node_ref"), o["collection"],
                                   o["relative_path"], o.get("inventory_id")), [])
    for (doc, sha, node, coll, path, inv), rs in sorted(groups.items(), key=lambda kv: [str(x) for x in kv[0]]):
        want = adapters.classify_path(path, doc_id=doc, sha=sha, subject_node=node, collection=coll, inventory_id=inv)
        if sorted(canonical.canonical_bytes(x) for x in want) != sorted(canonical.canonical_bytes(x) for x in rs):
            out.append(_e("C16_CLASSIFICATION_MISMATCH", "folder or file-name classifications differ from the pinned adapter rules", doc))
    ar = adapters.ABBREVIATIONS["AR"]
    for r in relationships:
        if r["evidentiary_basis"] not in LABEL_BASES or not r.get("classification_provenance"):
            continue
        cp, tgt = r["classification_provenance"], r["target"]
        node = tgt.get("node_id") or ""
        exp = cp.get("abbreviation_expansion") or {}
        abbr = exp.get("abbreviation")
        doc = r["subject"]["doc_id"]
        if abbr == "AR" or node.startswith("PROV:AR-"):
            if (abbr != "AR" or exp.get("expansion") != ar["expansion"] or (node and not node.startswith("PROV:AR-1954:r."))
                    or r["verification"] != "CANDIDATE" or r.get("is_finding") or not str(cp.get("collection", "")).startswith("local:")):
                out.append(_e("C16_READING_AR", "AR must read as Army Rules, 1954, in the local collection, as a candidate only", doc))
        if abbr == "AFT":
            out.append(_e("C16_READING_AFT", "bare AFT is the Armed Forces Tribunal (the forum): it has no provision reading", doc))
        if node.startswith(("PROV:AFT-2007", "CHAP:AFT-2007")) or abbr == "AFT ACT":
            m = cp.get("matched_text") or ""
            explicit = bool(adapters._AFT_ACT.match(m) or adapters._AFT_ACT_OF.match(m)) or abbr == "AFT ACT"
            if not explicit or abbr != "AFT ACT":
                out.append(_e("C16_READING_AFT", "only an explicit 'AFT Act' reference may point to the Armed Forces Tribunal Act, 2007", doc))
    for t in taxonomy:
        aliases = {a.strip().casefold() for a in t.get("aliases") or []}
        node, code = t["node_id"], t.get("instrument_code")
        if "aft" in aliases and (code == "AFT-2007" or ":AFT-2007" in node):
            out.append(_e("C16_READING_AFT", "taxonomy gives bare 'AFT' as an alias of the AFT Act, 2007", node))
        if "ar" in aliases and code != "AR-1954":
            out.append(_e("C16_READING_AR", "taxonomy gives 'AR' as an alias of something other than Army Rules, 1954", node))
    return out


# ----------------------------------------------------------------------------------------------- byte checks and facts

def _detect(data: bytes) -> str:
    return receipts.recompute_site_facts(original=data)["FORMAT_DETECTION"]["detected_format"]


def _pdf_pages(data: bytes) -> int | None:
    try:
        import pypdfium2 as pdfium
        pdf = pdfium.PdfDocument(data)
        try:
            return len(pdf)
        finally:
            pdf.close()
    except Exception:  # unopenable PDF
        return None


def _container_images(ident: dict, original: bytes) -> dict[str, bytes]:
    parts = {i["location"].get("container_part") for i in ident["embedded_images"]
             if i.get("location", {}).get("kind") == "DOCX_PART" and i["location"].get("container_part")}
    return safe_archive.read_members(original, parts)


def byte_issues(ident: dict, original: bytes | None, derivatives: dict[str, bytes]) -> list[str]:
    """Item-level byte checks the importer can do itself (I4). Empty list = nothing contradicted by the bytes."""
    codes: list[str] = []
    sc = ident["source_copy"]
    imgs = ident["embedded_images"] if isinstance(ident["embedded_images"], list) else None
    if original is not None:
        if len(original) != sc["bytes"]:
            codes.append("C16_BYTES_SIZE")
        fmt = _detect(original)
        if (fmt in RECOMPUTABLE_FORMATS or sc["detected_format"] in RECOMPUTABLE_FORMATS) and fmt != sc["detected_format"]:
            codes.append("C16_FORMAT_MISMATCH")
        if fmt == "PDF" and sc.get("page_count") is not None and _pdf_pages(original) != sc["page_count"]:
            codes.append("C16_PAGE_COUNT_MISMATCH")
        if imgs and fmt == "DOCX":
            try:
                members = _container_images(ident, original)
                for i in imgs:
                    loc = i.get("location") or {}
                    if loc.get("kind") == "DOCX_PART":
                        body = members.get(loc.get("container_part"))
                        if body is None or _sha(body) != i["image_sha256"]:
                            codes.append("C16_IMAGE_NOT_IN_CONTAINER")
                            break
            except safe_archive.UnsafeArchive:
                codes.append("C16_UNSAFE_CONTAINER")
    for i in imgs or []:
        if i["ocr_state"] == "DONE" and i.get("ocr_derivative_sha256") not in derivatives:
            codes.append("C16_IMAGE_OCR_DERIVATIVE_MISSING")
            break
    for d in ident["text_derivatives"]:
        b = derivatives.get(d["derivative_text_sha256"])
        if b is None:
            continue
        try:
            pages = evidence.split_pages(b.decode("utf-8"))
        except UnicodeDecodeError:
            pages = None
        if pages is None:
            codes.append("C16_DERIVATIVE_MARKERS_MALFORMED")
        elif len(pages) != d["coverage"]["units_total"] or sum(1 for t in pages.values() if t.strip()) < d["coverage"]["units_with_text"]:
            codes.append("C16_DERIVATIVE_COVERAGE")
    return sorted(set(codes))


def site_facts(ident: dict, *, original: bytes | None, derivative: bytes | None, derivatives: dict[str, bytes], register,
               exclusion_register, ledger: int, anchors: list[dict], relationships: list[dict], admissions: list[dict],
               exchange_issue_count: int) -> dict:
    """The site's own recomputation for one copy, keyed (sha256, receipt_kind) as `receipts.resolve_receipts` takes it.
    Nothing is recomputed without the copy's own bytes (fail closed: the receipt is then UNVERIFIABLE)."""
    if original is None:
        return {}
    sha, doc = ident["source_copy"]["sha256"], ident["doc_id"]
    matches = 0
    for reg in (register, exclusion_register):
        if reg is None:
            continue
        matches += 1 if reg.match(sha256=sha, doc_id=doc) else 0
        matches += sum(1 for o in ident["provenance"].get("observations") or [] if reg.match(path=o.get("relative_path")))
        matches += sum(1 for rec in [ident, *anchors, *relationships, *admissions] if reg.deep_match(rec))
    occ = None
    imgs = ident["embedded_images"]
    if imgs == []:
        occ = []
    elif isinstance(imgs, list) and _detect(original) == "DOCX":
        try:
            members = _container_images(ident, original)
            occ = []
            for i in imgs:
                part = (i.get("location") or {}).get("container_part")
                body = members.get(part) if (i.get("location") or {}).get("kind") == "DOCX_PART" else None
                od = i.get("ocr_derivative_sha256")
                occ.append({"image_sequence_id": i["image_sequence_id"], "image_sha256": _sha(body) if body is not None else None,
                            "ocr_state": i["ocr_state"],
                            "ocr_derivative_sha256": (od if od in derivatives else None) if i["ocr_state"] == "DONE" else od})
        except safe_archive.UnsafeArchive:
            occ = None
    facts = receipts.recompute_site_facts(
        original=original, derivative=derivative, register_matches=matches,
        identity_issues=len(record_issues(ident, auth_ledger_version=ledger, register=register)),
        exchange_issues=exchange_issue_count, occurrences=occ)
    return {(sha, k): v for k, v in facts.items()}


# ----------------------------------------------------------------------------------------------- accounting

def _v1_source(doc: dict) -> str:
    prov = doc.get("provenance") or {}
    hf = prov.get("hf") or {}
    if hf.get("repo") and hf.get("revision"):
        return f"v1:hf:{hf['repo']}@{hf['revision']}"
    return f"v1:{prov.get('acquisition_channel') or 'UNKNOWN'}"


def declared_accounting_issues(decl, release_id: str | None) -> list[Issue]:
    if not isinstance(decl, dict) or decl.get("record_kind") != ACCOUNTING_KIND or decl.get("contract") not in SUPPORTED_CONTRACTS[1:]:
        return [_e("C16_SOURCE_ACCOUNTING", "accounting register is not a contract 2.1 source_admission_accounting record", ACCOUNTING_PATH)]
    if decl.get("release_id") != release_id:
        return [_e("C16_SOURCE_ACCOUNTING", "accounting register belongs to another release", ACCOUNTING_PATH)]
    srcs = decl.get("sources")
    if not isinstance(srcs, list):
        return [_e("C16_SOURCE_ACCOUNTING", "accounting register has no source list", ACCOUNTING_PATH)]
    out, seen = [], set()
    for s in srcs:
        if not (isinstance(s, dict) and isinstance(s.get("source"), str) and s.get("path") in ACCOUNTING_PATHS
                and all(isinstance(s.get(f), int) and not isinstance(s.get(f), bool) and s[f] >= 0 for f in COUNT_FIELDS)):
            out.append(_e("C16_SOURCE_ACCOUNTING", "malformed accounting source entry", ACCOUNTING_PATH))
            continue
        if s["source"] in seen:
            out.append(_e("C16_SOURCE_ACCOUNTING", "source accounted twice", s["source"]))
        seen.add(s["source"])
        if s["path"] == "V7_REFERENCE":
            c = s.get("candidate_sha256")
            if not (isinstance(c, list) and all(isinstance(x, str) and len(x) == 64 for x in c) and len(c) == s["input"]) \
                    or s["eligible"] or s["served"]:
                out.append(_e("C16_SOURCE_ACCOUNTING", "v7 reference source must list its candidate hashes and is never eligible or served", s["source"]))
    out += legacy.accounting_issues([s for s in srcs if isinstance(s, dict) and all(isinstance(s.get(f), int) for f in COUNT_FIELDS)
                                     and isinstance(s.get("source"), str)])
    return out


def reconcile_accounting(declared: list[dict], computed: list[dict]) -> list[Issue]:
    """The producer's signed counts must match what the importer counted itself on every fact the producer can know
    (inputs and decisions); the site may only lower eligibility and service (site checks, exclusions)."""
    out = []
    d = {s["source"]: s for s in declared}
    c = {s["source"]: s for s in computed}
    if set(d) != set(c):
        out.append(_e("C16_SOURCE_ACCOUNTING", "accounted sources differ from the sources in the bundle"))
    for k in sorted(set(d) & set(c)):
        a, b = d[k], c[k]
        if any(a[f] != b[f] for f in ("input", "identities", "held", "rejected")) or b["eligible"] > a["eligible"] or a["path"] != b["path"]:
            out.append(_e("C16_SOURCE_ACCOUNTING", "per-source counts do not reconcile with the signed accounting register", k))
    return out


# ----------------------------------------------------------------------------------------------- the stage

def _effective(admissions: list[dict]) -> dict[tuple, dict]:
    superseded = {a.get("supersedes_admission_id") for a in admissions}
    return {(a["subject"]["doc_id"], a["subject"]["source_copy_sha256"]): a for a in admissions if a["admission_id"] not in superseded}


def _outcome(adm: dict | None) -> str:
    if adm is None:
        return "MISSING"
    if adm["decision"].startswith("HELD"):
        return "HELD"
    if adm["decision"].startswith("REJECTED"):
        return "REJECTED"
    return "ELIGIBLE_CLAIMED" if adm["application_eligible"] else "NOT_ELIGIBLE"


def _excluded(exclusions, doc_id, sha) -> bool:
    if exclusions is None:
        return False
    return bool(exclusions.register.is_restricted(sha256=sha, doc_id=doc_id)
                or doc_id in exclusions.withdrawn_doc_ids or sha in exclusions.withdrawn_shas
                or doc_id in exclusions.tombstone_doc_ids or sha in exclusions.tombstone_shas
                or doc_id in exclusions.restricted_tombstone_doc_ids or sha in exclusions.restricted_tombstone_shas)


def _restricted(exclusions, register, doc_id, sha) -> bool:
    if register is not None and register.is_restricted(sha256=sha, doc_id=doc_id):
        return True
    if exclusions is None:
        return False
    return bool(exclusions.register.is_restricted(sha256=sha, doc_id=doc_id)
                or doc_id in exclusions.restricted_tombstone_doc_ids or sha in exclusions.restricted_tombstone_shas)


def run(*, bundle: Path, manifest: dict, sums: dict[str, str], site: Path, docs: list[dict], verified_docs: dict[str, dict],
        originals: dict[str, bytes], copy_pages: dict[str, int], register, exclusions=None, site_facts_override=None) -> C16Result:
    """The C16 stage. `site_facts_override` replaces the importer's own recomputation and exists ONLY for the
    contract fixtures, which carry no original bytes; the import path never passes it."""
    res = C16Result()
    bundle = Path(bundle)
    listed = {f.get("path"): f for f in manifest.get("files", [])}
    on_disk = {p.relative_to(bundle).as_posix() for p in bundle.rglob("*") if p.is_file()}
    ours = sorted(p for p in set(listed) | on_disk if p and p.startswith((C16_PREFIX, REGISTERS_PREFIX)))
    governed_before = load_decision_index(site) + _generation_governance(site)
    res.active = bool(ours) or (bundle / KNOWLEDGE_MANIFEST).is_file() or bool(governed_before) or (Path(site) / DECISION_INDEX).exists()
    if not res.active:
        return res
    refuse = res.refusals.append

    for p in ours:
        if p not in listed and receipts.RECEIPT_PATH.match(p):
            refuse(_e("C16_RECEIPT_NOT_IN_INVENTORY", "receipt artefact not in the signed file inventory (RELEASE.json)", p))
        elif p not in listed or listed[p].get("kind") != "other":
            refuse(_e("C16_TRANSPORT", "C16 and register files travel as RELEASE.json files of kind 'other'", p))
    if res.refusals:
        return res
    data = {p: (bundle / p).read_bytes() for p in ours}

    # knowledge release manifest (optional in a v1 transport bundle): rules and inventory against SHA256SUMS
    inventory = {p for p in listed}
    km = bundle / KNOWLEDGE_MANIFEST
    if km.is_file():
        try:
            kmanifest = json.loads(km.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, ValueError):
            kmanifest = None
        if not isinstance(kmanifest, dict) or kmanifest.get("record_kind") != "knowledge_release_manifest":
            refuse(_e("KR_MANIFEST", "KNOWLEDGE_RELEASE.json is not a knowledge release manifest", KNOWLEDGE_MANIFEST))
            return res
        ki = record_issues(kmanifest, auth_ledger_version=manifest.get("auth_ledger_version") or 0, register=register)
        if not ki:
            ki = component_inventory_issues(kmanifest, sums)
        if ki:
            res.refusals += ki
            return res
        inventory = {f["path"] for c in kmanifest["components"] if c["kind"] == "ADMISSION_REGISTER" for f in c["files"]}

    # per-source accounting register: required on a C16-aware import
    decl = None
    if ACCOUNTING_PATH in data:
        res.declared_accounting = data[ACCOUNTING_PATH]
        try:
            decl = json.loads(data[ACCOUNTING_PATH].decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            decl = None
        ai = declared_accounting_issues(decl, manifest.get("release_id"))
        if ai:
            res.refusals += ai
            return res
    else:
        refuse(_e("C16_SOURCE_ACCOUNTING_MISSING", "a C16-aware import needs the signed per-source accounting register", ACCOUNTING_PATH))
        return res

    ledger = manifest.get("auth_ledger_version") or 0
    files = {p[len(C16_PREFIX):]: b for p, b in data.items() if p.startswith(C16_PREFIX)}
    idents, anchors, rels, tax, adms = [], [], [], [], []
    gen_manifest = None
    if files:
        try:
            gen_manifest = json.loads(files.get("GENERATION.json", b"null").decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            gen_manifest = None
        contract = gen_manifest.get("contract") if isinstance(gen_manifest, dict) else None
        if gen_manifest is not None and contract not in SUPPORTED_CONTRACTS:
            refuse(_e("C16_CONTRACT_UNSUPPORTED", "unknown contract version (only 2.0 and 2.1 are importable)", "GENERATION.json"))
            return res
        # I2: strict only. exchange_issues refuses a missing manifest, a missing population and any record problem.
        issues = [i for i in exchange_issues(files, mode="strict", auth_ledger_version=ledger, register=register) if i.severity == "error"]
        if issues:
            res.refusals += issues
            return res
        res.contract, res.corpus_generation_id = contract, gen_manifest["corpus_generation_id"]
        res.exchange_files = files

        def pop(stem):
            out = []
            for name in sorted(files):
                if name.split(".")[0] == stem:
                    out += [json.loads(x) for x in files[name].decode("utf-8").split("\n") if x]
            return out
        idents, anchors, rels, tax, adms = pop("identities"), pop("anchors"), pop("relationships"), pop("taxonomy"), pop("admissions")
        for rec in idents + adms + anchors:
            doc = rec.get("doc_id") or rec.get("subject", {}).get("doc_id")
            sha = (rec.get("source_copy") or {}).get("sha256") or rec.get("original_sha256") or rec.get("subject", {}).get("source_copy_sha256")
            if _restricted(exclusions, register, doc, sha):
                refuse(_e("C16_RESTRICTED_IN_EXCHANGE", "the exchange carries a copy the site holds as restricted"))
                return res
        ci = classification_issues(idents, rels, tax)
        if ci:
            res.refusals += ci
            return res

    # receipt artefacts: everything under registers/ except the accounting register is a candidate artefact
    artefacts = {p: b for p, b in data.items() if p.startswith(REGISTERS_PREFIX) and p != ACCOUNTING_PATH}
    eff = _effective(adms)
    eligible_ids = {a["admission_id"] for a in eff.values() if a["application_eligible"]}
    texts = {}
    for p, f in listed.items():
        if f.get("kind") == "text" and (bundle / p).is_file():
            b = (bundle / p).read_bytes()
            texts[_sha(b)] = b

    def original_of(sha):
        if sha in originals:
            return originals[sha]
        v = Path(site) / "vault" / "sha256" / sha[:2] / sha
        if v.is_file():
            b = v.read_bytes()
            if _sha(b) == sha:
                return b
        return None

    by_key = {(d["doc_id"], d["source_copy"]["sha256"]): d for d in idents}
    byte_codes = {key: byte_issues(d, original_of(key[1]), texts) for key, d in by_key.items()}
    verified_copies = set(copy_pages) | {k[1] for k, codes in byte_codes.items() if not codes and original_of(k[1]) is not None}
    for key, d in by_key.items():
        pm = d["representation"].get("page_mapping")
        if pm and pm.get("original_sha256") and pm["original_sha256"] not in verified_copies:
            byte_codes[key] = sorted(set(byte_codes[key]) | {"C16_PAGE_MAPPING_UNVERIFIED"})

    facts = {}
    if site_facts_override is not None:
        facts = dict(site_facts_override)
    else:
        for key, d in by_key.items():
            a = eff.get(key)
            if not (a and a["application_eligible"]):
                continue
            g6 = next((g for g in a["gates"] if g["gate_id"] == "G06_TEXT_DERIVATIVE_VERIFIED"), {})
            der_sha = (g6.get("receipt") or {}).get("derivative_sha256")
            mine_a = [x for x in anchors if (x["doc_id"], x["original_sha256"]) == key]
            mine_r = [x for x in rels if (x["subject"]["doc_id"], x["subject"]["source_copy_sha256"]) == key]
            mine_m = [x for x in adms if (x["subject"]["doc_id"], x["subject"]["source_copy_sha256"]) == key]
            facts.update(site_facts(d, original=original_of(key[1]), derivative=texts.get(der_sha) if der_sha else None,
                                    derivatives=texts, register=register,
                                    exclusion_register=exclusions.register if exclusions is not None else None, ledger=ledger,
                                    anchors=mine_a, relationships=mine_r, admissions=mine_m,
                                    exchange_issue_count=0))  # strict re-validation above found none (else refused)
    site_register = getattr(register, "config_sha256", None)
    manifest_register = (gen_manifest or {}).get("pinned_inputs", {}).get("restricted_register_sha256")
    r_issues, verification = receipts.resolve_receipts(
        admissions=adms, identities=idents, anchors=anchors, relationships=rels, artefacts=artefacts,
        exchange_contract=res.contract or "", manifest_register_sha256=manifest_register, site_register_sha256=site_register,
        site_facts=facts, inventory_paths=inventory)
    item_issues: dict[str, list[str]] = {}
    for i in r_issues:
        head = i.where.split(":")[0]
        if head in eligible_ids:
            item_issues.setdefault(head, []).append(i.code)
        elif i.code != "C16_RECEIPTS_REQUIRE_2_1":
            refuse(i)               # a malformed artefact in the signed admission register refuses the bundle
    if res.refusals:
        return res

    # anchors (I8): byte-verified spans against the verified derivative bytes
    for a in sorted(anchors, key=lambda x: x["anchor_id"]):
        if a["original_sha256"] not in verified_copies:
            codes = ["C16_ANCHOR_COPY_NOT_VERIFIED"]
        elif a.get("text_span") is None:
            codes = []
        else:
            b = texts.get(a.get("derivative_text_sha256") or "")
            codes = ["C16_DERIVATIVE_NOT_BUNDLED"] if b is None else evidence.verify_anchor_bytes(a, b)
        res.anchors.append({"anchor_id": a["anchor_id"], "doc_id": a["doc_id"], "original_sha256": a["original_sha256"],
                            "span_verified": a.get("text_span") is not None and not codes, "codes": codes})
        for c in codes:
            res.codes[c] += 1

    # per-copy verdicts (I6, I7)
    v1_by_key = {(d["doc_id"], d["source_copy"]["sha256"]): d for d in verified_docs.values()}
    c16_keys = set(by_key)
    for key in sorted(by_key):
        d, a = by_key[key], eff.get(key)
        outcome, codes = _outcome(a), list(byte_codes[key])
        gates = {}
        if outcome == "ELIGIBLE_CLAIMED":
            codes += item_issues.get(a["admission_id"], [])
            gates = verification.get(a["admission_id"], {})
            outcome = "QUARANTINED" if codes else "ELIGIBLE"
        has_v1 = key in v1_by_key
        excluded = _excluded(exclusions, *key)
        served = outcome == "ELIGIBLE" and has_v1 and not excluded
        if outcome == "ELIGIBLE" and not has_v1:
            codes.append("C16_ONLY_NOT_SERVABLE")
        if not served:
            codes.append("C16_SUBJECT_NOT_SERVABLE")
        if excluded:
            codes.append("C16_EXCLUDED")
        if served:
            res.allowed_docs.add(key[0])
            if a.get("service_scope") == "SEARCHABLE":
                res.search_docs.add(key[0])
            for g, cls in sorted(gates.items()):
                r = next(x["receipt"] for x in a["gates"] if x["gate_id"] == g)
                res.resolved_receipts.append({"admission_id": a["admission_id"], "doc_id": key[0], "sha256": key[1], "gate_id": g,
                                              "receipt_sha256": r["receipt_sha256"], "verification": cls})
                path = f"registers/receipts/{r['receipt_sha256']}.json"
                res.receipt_files[path] = artefacts[path]
        for c in sorted(set(codes)):
            res.codes[c] += 1
        res.copies.append({"doc_id": key[0], "sha256": key[1], "admission_id": a["admission_id"] if a else None,
                           "decision": a["decision"] if a else None, "service_scope": a.get("service_scope") if a else None,
                           "outcome": outcome, "served": served, "has_v1_record": has_v1, "codes": sorted(set(codes)),
                           "gates": dict(sorted(gates.items()))})

    # I-5 legacy: v1 documents without a sidecar
    governed = {(e["doc_id"], e["sha256"]) for e in governed_before} | c16_keys
    eligible_c16 = {(c["doc_id"], c["sha256"]) for c in res.copies if c["outcome"] == "ELIGIBLE"}
    v7_shas = set()
    for s in (decl or {}).get("sources", []):
        if s["path"] == "V7_REFERENCE":
            v7_shas |= set(s["candidate_sha256"])
    candidate_shas = v7_shas | {k[1] for k in governed}
    excl = set()
    if exclusions is not None:
        excl = set(exclusions.withdrawn_doc_ids | exclusions.withdrawn_shas | exclusions.tombstone_doc_ids | exclusions.tombstone_shas
                   | exclusions.restricted_tombstone_doc_ids | exclusions.restricted_tombstone_shas)
    comp_restricted: dict[str, int] = {}
    for doc_id in sorted(verified_docs):
        doc = verified_docs[doc_id]
        key = (doc_id, doc["source_copy"]["sha256"])
        if key in c16_keys:
            continue
        if _restricted(exclusions, register, *key):
            # restricted copies are never served and never named in anything the import writes (ids, paths, hashes)
            res.restricted_shas.add(key[1])
            res.codes["C16_RESTRICTED_OMITTED"] += 1
            comp_restricted[_v1_source(doc)] = comp_restricted.get(_v1_source(doc), 0) + 1
            continue
        li = legacy.legacy_issues(doc, c16_governed=governed, eligible_c16=eligible_c16, candidate_shas=candidate_shas, excluded=excl)
        ok = not li
        if ok:
            res.allowed_docs.add(doc_id)
            res.search_docs.add(doc_id)
        else:
            res.codes["C16_LEGACY_NOT_ESTABLISHED"] += 1
        res.legacy.append({"doc_id": doc_id, "sha256": key[1], "source": _v1_source(doc), "established": ok,
                           "reasons": sorted({i.message for i in li})})
    served_keys = {(c["doc_id"], c["sha256"]) for c in res.copies if c["served"]}
    served_keys |= {(lg["doc_id"], lg["sha256"]) for lg in res.legacy if lg["established"]}
    res.denied = sorted((governed | {(lg["doc_id"], lg["sha256"]) for lg in res.legacy}) - served_keys)

    # per-source accounting, reconciled with the signed register
    comp: dict[str, dict] = {}

    def row(src, path):
        return comp.setdefault(src, {"source": src, "path": path, **{f: 0 for f in COUNT_FIELDS}})
    for c in res.copies:
        r = row(f"c16:{res.corpus_generation_id}", "C16")
        r["input"] += 1
        r["identities"] += 1
        bucket = {"HELD": "held", "REJECTED": "rejected", "ELIGIBLE": "eligible"}.get(c["outcome"], "quarantined")
        r[bucket] += 1
        r["served"] += 1 if c["served"] else 0
    for lg in res.legacy:
        r = row(lg["source"], "V1")
        r["input"] += 1
        r["identities"] += 1
        r["eligible" if lg["established"] else "quarantined"] += 1
        r["served"] += 1 if lg["established"] else 0
    for src, n in comp_restricted.items():
        r = row(src, "V1")
        r["input"] += n
        r["identities"] += n
        r["quarantined"] += n
    for s in (decl or {}).get("sources", []):
        if s["path"] == "V7_REFERENCE":
            comp[s["source"]] = {f: s[f] for f in ("source", "path", *COUNT_FIELDS)}
    res.accounting = [comp[k] for k in sorted(comp)]
    acc = legacy.accounting_issues(res.accounting) + reconcile_accounting(decl["sources"], res.accounting)
    if acc:
        res.refusals += acc
        return res

    release_id = manifest.get("release_id")
    for c in res.copies:
        res.index_entries.append({"doc_id": c["doc_id"], "sha256": c["sha256"], "corpus_generation_id": res.corpus_generation_id,
                                  "admission_id": c["admission_id"], "decision": c["decision"], "site_outcome": c["outcome"],
                                  "release_id": release_id})
    return res


def materialize(res: C16Result) -> dict:
    """Files written into the temporary generation (before the atomic rename) and the generation.json sections."""
    files: dict[str, bytes] = {}
    for name, b in res.exchange_files.items():
        files[C16_PREFIX + name] = b
    files["c16/verdicts.json"] = json.dumps({"copies": res.copies, "anchors": res.anchors, "legacy": res.legacy},
                                            indent=1, sort_keys=True).encode()
    files["c16/resolved_receipts.json"] = json.dumps(sorted(res.resolved_receipts, key=lambda r: (r["doc_id"], r["gate_id"])),
                                                     indent=1, sort_keys=True).encode()
    files.update(res.receipt_files)
    acct = {"record_kind": "site_source_admission_accounting", "corpus_generation_id": res.corpus_generation_id,
            "declared_register_sha256": _sha(res.declared_accounting) if res.declared_accounting else None,
            "sources": res.accounting}
    files["registers/source_accounting.json"] = json.dumps(acct, indent=1, sort_keys=True).encode()
    if res.declared_accounting is not None:
        files["registers/source_accounting.declared.json"] = res.declared_accounting
    section = {"contract": res.contract, "corpus_generation_id": res.corpus_generation_id,
               "served_copies": sorted([c["doc_id"], c["sha256"]] for c in res.copies if c["served"]),
               "governed": sorted([c["doc_id"], c["sha256"]] for c in res.copies),
               "denied": [list(k) for k in res.denied], "codes": dict(sorted(res.codes.items())),
               "accounting_sha256": _sha(files["registers/source_accounting.json"]),
               "files": {p: _sha(b) for p, b in sorted(files.items())}}
    return {"files": files, "section": section,
            "materialized": {"dir": C16_PREFIX, "files": {n: _sha(b) for n, b in sorted(res.exchange_files.items())}}}
