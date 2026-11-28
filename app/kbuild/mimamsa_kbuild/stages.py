"""Stages S0-S9 (B02 spec section 2), Stage 2 skeleton depth: enough of each stage to run end to end on the CP-1
fixtures and produce a development-signed, explicitly DEGRADED (lexical-only) MKR-1 release.

Every stage reads only the spec and earlier stages' outputs (S1 is the only stage that reads sources) and writes only
into its own work directory. Nothing reads the wall clock, the host name or an absolute path into an output.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from mimamsa_contract.bundle import parse_sums, strict_loads, validate_bundle
from mimamsa_contract.c16 import build_spec as bs
from mimamsa_contract.c16 import accounting, canonical, components, digests, knowledge_rows, receipts
from mimamsa_contract.c16 import rules as c16rules
from mimamsa_contract.restricted import register_from_bytes
from mimamsa_contract.trust import parse_trust_list

from . import REPO, VERSION
from .devkeys import dev_key_id, dev_trust_list, load_dev_key
from .engine import BuildContext
from .errors import BuildRefused
from .fixture_mirror import revision_root
from .fsutil import copy_file, files_under, json_pretty, link_or_copy, rmtree, sha256_bytes, sha256_file, write_bytes
from .release import (SIG, SUMS, concat_digest, file_entries, hashset_digest, integrity_rows, legacy_issues, parse_jsonl,
                      rows_component_digest, source_accounting, sums_bytes, write_release_tree)
from .resources import child_creationflags, child_env, stage_workers

KB = REPO / "app" / "kbuild"
V2_1 = REPO / "app" / "contract" / "fixtures" / "c16" / "v2_1"
LOCAL_INPUTS = [   # committed inputs (git) the stages read; their content is part of the S1 inventory
    ("restricted_register", "config/restricted_material.json"),
    ("gate_status", "app/kbuild/config/GATE_STATUS.json"),
    ("release_defaults", "app/kbuild/config/RELEASE_DEFAULTS.json"),
    ("release_manifest_template", "app/contract/examples/release_manifest.example.json"),
    # B03 ships the application allowlist; until then the contract 2.1 fixture allowlist stands in (flagged).
    ("knowledge_rows_allowlist", "app/contract/fixtures/c16/v2_1/knowledge_rows/allowlist.json"),
    # B04 owns the component verification contracts; the 2.1 interface fixtures stand in (flagged).
    *[(f"component_contract:{k}", f"app/contract/fixtures/c16/v2_1/component_contracts/{k}.json")
      for k in ("GRAPH", "KNOWLEDGE_ROWS", "LEXICAL_INDEX", "TEXT_STORE", "VECTOR_PACK")],
]
CODE_INPUTS = [   # code the stages execute: aggregate digests (LF-normalised), so a code change re-runs from S1
    ("code:mimamsa_kbuild", "app/kbuild/mimamsa_kbuild", "*.py"),
    ("code:kbuild_accel", "app/kbuild/accel", "*.cs*"),
    ("code:mimamsa_contract", "app/contract/mimamsa_contract", "*.py"),
    ("code:contract_schemas", "app/contract/schemas", "*.json"),
    ("code:mimamsa_importer", "app/importer/mimamsa_importer", "*.py"),
    ("code:b1_core", "app/b1/src/Mimamsa.Core", "*.cs"),
]
ACCOUNTING_FILE = accounting.FILE    # registers/source_accounting.json (contract 2.1, DECLARED_BY_BUILD)
CANDIDATE_SET_DIR = accounting.CANDIDATE_SET_PREFIX.rstrip("/")   # registers/candidate_sets (ADMISSION_REGISTER)
V7_PREFIX = "v7/candidate_sets/"     # v7 candidate sets in the pinned revision (input); shipped under accounting.CANDIDATE_SET_PREFIX
DEFERRED_RECEIPT_CODES = {"C16_RECEIPT_UNVERIFIABLE", "C16_RECEIPT_SITE_MISMATCH"}   # site-recomputable facts: B01 at import


def _refuse(code, msg, stage, details=None):
    raise BuildRefused(code, msg, stage, details)


def _code_digest(rel_dir: str, pattern: str) -> dict:
    base = REPO / rel_dir
    parts = []
    for p in sorted(base.rglob(pattern), key=lambda x: x.relative_to(base).as_posix()):
        if not p.is_file() or any(s in ("bin", "obj", "__pycache__") for s in p.relative_to(base).parts):
            continue
        parts.append(f"{p.relative_to(base).as_posix()} {sha256_bytes(p.read_bytes().replace(b'\r\n', b'\n'))}")
    return {"files": len(parts), "sha256": sha256_bytes("\n".join(parts).encode("utf-8"))}


# ===================================================================================== S0 spec

def spec_support_issues(spec: dict) -> list[dict]:
    """What the Stage 2 skeleton refuses to build (fail closed; each is Stage 3/4 work)."""
    out = []
    if spec["release"]["base_mode"] != "FULL":
        out.append({"code": "BUILD_UNSUPPORTED", "message": "DELTA releases are Stage 3/4 work (B05); the skeleton builds FULL only"})
    if spec["release"]["signing_mode"] != "DEVELOPMENT":
        out.append({"code": "BUILD_UNSUPPORTED", "message": "PRODUCTION signing (owner offline signature) is Stage 4 (B05/B10)"})
    if len(spec["inputs"]["producer_generations"]) != 1:
        out.append({"code": "BUILD_UNSUPPORTED", "message": "the skeleton takes exactly one producer generation (corpus-v2/)"})
    hf = {(h["repo"], h["revision"]) for h in spec["inputs"]["hf"]}
    for g in spec["inputs"]["producer_generations"]:
        if (g["hf_repo"], g["hf_revision"]) not in hf:
            out.append({"code": "BUILD_INPUT_UNPINNED", "message": "a producer generation's HF revision is not among the pinned HF inputs"})
    return out


def s0_spec(ctx: BuildContext, work: Path) -> None:
    issues = [{"code": i.code, "message": i.message, "where": i.where} for i in bs.spec_issues(ctx.spec)]
    issues += spec_support_issues(ctx.spec)
    if issues:
        _refuse(issues[0]["code"], issues[0]["message"], "S0", issues)
    write_bytes(work / "spec.json", canonical.canonical_bytes(ctx.spec))
    write_bytes(work / "SPEC_REPORT.json", json_pretty({
        "spec_sha256": bs.spec_sha256(ctx.spec), "build_id": ctx.spec["build_id"], "release_id": ctx.spec["release"]["release_id"],
        "spec_issues": [], "stages": [s["stage_id"] + ":" + s["name"] for s in ctx.spec["stages"]],
        "network_stage": bs.NETWORK_STAGE, "pinned_build_time": ctx.spec["pinned_build_time"]}))


# ===================================================================================== S1 fetch

def collect_inventory(ctx: BuildContext, *, dry_run: bool = False) -> tuple[dict, dict[str, Path]]:
    """Enumerate and re-hash every pinned input. Returns (inventory, {sha256: source path})."""
    spec = ctx.spec
    if ctx.mirror is None:
        _refuse("BUILD_FETCH_NOT_IMPLEMENTED", "fetching pinned HF revisions over the network is Stage 3; pass --source-mirror", "S1")
    blobs: dict[str, Path] = {}
    hf_out = []
    listing: dict[tuple[str, str], dict[str, dict]] = {}
    for h in sorted(spec["inputs"]["hf"], key=lambda x: (x["repo"], x["revision"])):
        root = revision_root(ctx.mirror, h["repo"], h["revision"])
        if not root.is_dir():
            _refuse("BUILD_INPUT_MISSING", f"pinned revision of {h['repo']} not available in the source mirror", "S1")
        files = []
        for p in files_under(root):
            sha = sha256_file(p)
            files.append({"path": p.relative_to(root).as_posix(), "sha256": sha, "bytes": p.stat().st_size})
            blobs.setdefault(sha, p)
        listing[(h["repo"], h["revision"])] = {f["path"]: f for f in files}
        hf_out.append({"repo": h["repo"], "revision": h["revision"], "purpose": h["purpose"], "files": files})
    gens = []
    for g in spec["inputs"]["producer_generations"]:
        lst = listing.get((g["hf_repo"], g["hf_revision"]), {})
        gm = lst.get(g["path"])
        if gm is None:
            _refuse("BUILD_INPUT_MISSING", "pinned GENERATION.json absent from its revision", "S1")
        if gm["sha256"] != g["generation_manifest_sha256"]:
            _refuse("BUILD_PIN_MISMATCH", "GENERATION.json does not hash to its pin (generation_manifest_sha256)", "S1")
        base = g["path"].rsplit("/", 1)[0] + "/" if "/" in g["path"] else ""
        try:
            man = strict_loads(blobs[gm["sha256"]].read_text(encoding="utf-8"))
        except ValueError as exc:
            _refuse("C16_MANIFEST", f"GENERATION.json unreadable: {type(exc).__name__}", "S1")
        declared = []
        for f in man.get("files", []):
            have = lst.get(base + f["path"])
            if have is None:
                _refuse("BUILD_INPUT_MISSING", f"declared exchange file {f['path']} absent", "S1")
            if have["sha256"] != f["sha256"]:
                _refuse("BUILD_INPUT_HASH", f"exchange file {f['path']} does not hash to GENERATION.json", "S1")
            declared.append({"name": f["path"], "path": base + f["path"], "sha256": f["sha256"]})
        rec = sorted(({"name": p[len(base):], "path": p, "sha256": x["sha256"]} for p, x in lst.items()
                      if p.startswith(base + "registers/receipts/")), key=lambda x: x["path"])
        gens.append({"corpus_generation_id": g["corpus_generation_id"], "hf_repo": g["hf_repo"], "hf_revision": g["hf_revision"],
                     "path": g["path"], "generation_manifest_sha256": gm["sha256"], "declared_files": declared, "receipts": rec})
    local = []
    for name, rel in LOCAL_INPUTS:
        p = REPO / rel
        if not p.is_file():
            _refuse("BUILD_INPUT_MISSING", f"committed input {rel} missing", "S1")
        sha = sha256_file(p)
        blobs.setdefault(sha, p)
        local.append({"name": name, "path": rel, "sha256": sha, "bytes": p.stat().st_size})
    reg = next(x for x in local if x["name"] == "restricted_register")
    if reg["sha256"] != spec["inputs"]["restricted_register_sha256"]:
        _refuse("BUILD_REGISTER_PIN", "restricted-material register does not hash to the spec pin", "S1")
    code = [{"name": n, "path": d, **_code_digest(d, pat)} for n, d, pat in CODE_INPUTS]
    if dry_run and (ctx.dev_key_path is None or not Path(ctx.dev_key_path).is_file()):
        dev = None   # a dry run never creates a key
    else:
        _sk, pub = load_dev_key(ctx.dev_key_path)
        dev = {"key_id": dev_key_id(pub), "public_key_hex": pub.hex(), "holder": "DEVELOPMENT"}
    inv = {"record_kind": "kbuild_fetch_inventory", "mode": "OFFLINE_MIRROR", "network_used": False, "hf": hf_out,
           "producer_generations": gens, "local_inputs": local, "code_inputs": code,
           "git": spec["inputs"]["git"], "dev_signing": dev}
    return inv, blobs


def s1_fetch(ctx: BuildContext, work: Path) -> None:
    inv, blobs = collect_inventory(ctx)
    for sha, src in sorted(blobs.items()):
        dst = work / "cache" / sha
        copy_file(src, dst)
        if sha256_file(dst) != sha:   # every file re-hashed against its pin after the copy
            _refuse("BUILD_INPUT_HASH", "cached copy does not hash to its source", "S1")
    write_bytes(work / "INVENTORY.json", json_pretty(inv))


def s1_fresh(ctx: BuildContext) -> bool:
    try:
        inv, _ = collect_inventory(ctx)
    except BuildRefused:
        return False
    return json_pretty(inv) == (ctx.stage_dir("S1") / "INVENTORY.json").read_bytes()


# ------------------------------------------------------------------ inputs from the S1 cache

class Inputs:
    def __init__(self, ctx: BuildContext):
        self.ctx = ctx
        self.inv = ctx.stage_json("S1", "INVENTORY.json")
        cache = ctx.stage_dir("S1") / "cache"
        self.blob = lambda sha: (cache / sha).read_bytes()
        loc = {x["name"]: x for x in self.inv["local_inputs"]}
        self.local = lambda name: self.blob(loc[name]["sha256"])
        self.register = register_from_bytes(self.local("restricted_register"), "config/restricted_material.json")
        self.allowlist = json.loads(self.local("knowledge_rows_allowlist"))
        self.gate_status = json.loads(self.local("gate_status"))
        self.defaults = json.loads(self.local("release_defaults"))
        self.template = json.loads(self.local("release_manifest_template"))
        self.contracts = {k.split(":", 1)[1]: json.loads(self.local(k)) for k in loc if k.startswith("component_contract:")}
        v1 = [h for h in self.inv["hf"] if any(f["path"] == "v1/data/documents.jsonl" for f in h["files"])]
        if len(v1) != 1:
            _refuse("BUILD_INPUT_MISSING", "exactly one pinned HF input must carry the v1 canonical corpus (v1/)", None)
        self.v1_source = {"hf_repo": v1[0]["repo"], "hf_revision": v1[0]["revision"]}
        self.v1_files = {f["path"][3:]: f["sha256"] for f in v1[0]["files"] if f["path"].startswith("v1/")}
        # v7 candidate sets (reference only, never served) at the same pinned revision: v7/candidate_sets/<name>.txt
        self.v7_files = {f["path"][len(V7_PREFIX):-4]: f["sha256"] for f in v1[0]["files"]
                         if f["path"].startswith(V7_PREFIX) and f["path"].endswith(".txt")}
        g = self.inv["producer_generations"][0]
        self.generation = g
        self.exchange = {"GENERATION.json": self.blob(g["generation_manifest_sha256"])}
        self.exchange.update({f["name"]: self.blob(f["sha256"]) for f in g["declared_files"]})
        self.receipts = {f["name"]: self.blob(f["sha256"]) for f in g["receipts"]}
        self.gen_manifest = json.loads(self.exchange["GENERATION.json"])

    def v1_records(self) -> dict[str, list[dict]]:
        out = {}
        for name in ("documents", "derived_text", "candidates", "reviewed_records", "appointments", "approvals", "publication_records"):
            sha = self.v1_files.get(f"data/{name}.jsonl")
            out[name] = parse_jsonl(self.blob(sha)) if sha else []
        return out

    def v1_group(self, prefix: str) -> dict[str, bytes]:
        return {p: self.blob(s) for p, s in sorted(self.v1_files.items()) if p.startswith(prefix)}

    def v7_sets(self) -> dict[str, list[str]]:
        """name -> candidate hashes; each input file must already be the canonical 2.1 bytes (CS3), else refused."""
        out = {}
        for name, sha in sorted(self.v7_files.items()):
            b = self.blob(sha)
            hs = b.decode("ascii").split("\n") if b else []
            if accounting.candidate_set_bytes(hs) != b or not all(len(h) == 64 for h in hs):
                _refuse("BUILD_INPUT_V7", f"v7 candidate set {name} is not canonical (sorted unique lower-case sha256, LF, no final LF)", None)
            out[name] = hs
        return out

    def originals(self) -> dict[str, bytes]:
        out = {}
        for p, data in self.v1_group("originals/").items():
            out[sha256_bytes(data)] = data
        return out

    def population(self) -> dict[str, list[dict]]:
        pop = {}
        for name, data in self.exchange.items():
            if name.endswith(".jsonl"):
                stem = name.split(".", 1)[0]
                pop.setdefault(stem, []).extend(parse_jsonl(data))
        return pop

    def hf_pins(self) -> set[tuple[str, str]]:
        return {(h["repo"], h["revision"]) for h in self.ctx.spec["inputs"]["hf"]}

    def dev_pub(self) -> bytes:
        return bytes.fromhex(self.inv["dev_signing"]["public_key_hex"])


# ===================================================================================== S2 validate

def _issue_list(issues) -> list[dict]:
    return [{"code": i.code, "message": i.message, "where": i.where, "severity": i.severity} for i in issues]


def receipt_resolution(pop: dict, gen_manifest: dict, receipt_files: dict[str, bytes], register) -> dict:
    """2.1 receipt resolution at build time (reference resolver, no site facts). Item-level: returns the admissions
    whose receipts do not resolve, with codes; facts only the site can recompute are counted as deferred."""
    issues, ver = receipts.resolve_receipts(
        admissions=pop.get("admissions", []), identities=pop.get("identities", []), anchors=pop.get("anchors", []),
        relationships=pop.get("relationships", []),
        artefacts={f"registers/receipts/{k.split('/')[-1]}": v for k, v in receipt_files.items()},
        exchange_contract=gen_manifest["contract"], manifest_register_sha256=gen_manifest["pinned_inputs"]["restricted_register_sha256"],
        site_register_sha256=register.config_sha256, site_facts={})
    unresolved: dict[str, set] = {}
    artefact_codes: dict[str, int] = {}
    deferred: dict[str, int] = {}
    adm_ids = {a["admission_id"] for a in pop.get("admissions", [])}
    for i in issues:
        if i.code in DEFERRED_RECEIPT_CODES:
            deferred[i.code] = deferred.get(i.code, 0) + 1
            continue
        aid = (i.where or "").split(":", 1)[0]
        if aid in adm_ids:
            unresolved.setdefault(aid, set()).add(i.code)
        else:
            artefact_codes[i.code] = artefact_codes.get(i.code, 0) + 1
    return {"resolved_admissions": sorted(ver), "unresolved_admissions": {k: sorted(v) for k, v in sorted(unresolved.items())},
            "artefact_issues": dict(sorted(artefact_codes.items())), "deferred_to_site_importer": dict(sorted(deferred.items()))}


def s2_validate(ctx: BuildContext, work: Path) -> None:
    inp = Inputs(ctx)
    # strict C16 exchange (a partial exchange is refused here: strict mode requires every population)
    ex = c16rules.exchange_issues(inp.exchange, mode="strict", register=inp.register)
    ex_err = [i for i in ex if i.severity == "error"]
    if ex_err:
        _refuse(ex_err[0].code, "strict exchange validation failed: " + ex_err[0].message, "S2", _issue_list(ex_err))
    pop = inp.population()
    rr = receipt_resolution(pop, inp.gen_manifest, inp.receipts, inp.register)
    # v1 path: the existing v1 validator over a scratch unsigned tree (development mode, unsigned allowed)
    recs = inp.v1_records()
    scratch = ctx.build_root / ".tmp-S2-v1"
    rmtree(scratch)
    try:
        write_release_tree(scratch, release_manifest_template=inp.template, spec=ctx.spec, defaults=inp.defaults, register=inp.register,
                           key_id=inp.inv["dev_signing"]["key_id"], v1_source=inp.v1_source, records=recs, originals=inp.originals(),
                           texts={"text/" + p[5:]: b for p, b in inp.v1_group("text/").items()}, research=inp.v1_group("research/"), c16_files={})
        write_bytes(scratch / SUMS, sums_bytes(scratch))
        rep = validate_bundle(scratch, mode="development", allow_unsigned_dev=True, register=inp.register)
    finally:
        rmtree(scratch)
    v1_err = [i for i in rep.issues if i.severity == "error"]
    if v1_err:
        _refuse(v1_err[0].code, "v1 validation failed: " + v1_err[0].message, "S2", _issue_list(v1_err))
    v7_shas = set().union(*inp.v7_sets().values()) if inp.v7_files else set()
    legacy = legacy_issues(recs["documents"], pop.get("identities", []), pop.get("admissions", []), inp.hf_pins(), v7_shas)
    if legacy:
        _refuse(legacy[0]["code"], legacy[0]["reason"], "S2", legacy)
    write_bytes(work / "VALIDATION.json", json_pretty({
        "exchange": {"corpus_generation_id": inp.generation["corpus_generation_id"], "contract": inp.gen_manifest["contract"],
                     "mode": "strict", "errors": 0, "warnings": len(ex) - len(ex_err), "records": {k: len(v) for k, v in sorted(pop.items())}},
        "receipts": {"artefacts": len(inp.receipts), **rr,
                     "note": "receipt resolution is item-level (B01 section 4): an eligible admission whose receipts do not resolve "
                             "is accounted not servable and the site quarantines it; SITE_RECOMPUTABLE facts need the copy's bytes "
                             "and are re-checked by the site importer (B01)"},
        "v1": {"checked_files": rep.checked_files, "checked_records": rep.checked_records,
               "warnings": sorted({i.code for i in rep.issues if i.severity != "error"})},
        "legacy_sg1": {"v1_documents": len(recs["documents"]), "issues": 0,
                       "v7_inventory": "not an input of this build (legal_knowledge/candidates/cycle15/v7 absent); v7 relabel check not exercised"},
        "register": {"config_sha256": inp.register.config_sha256, "restriction_ids": sorted(inp.register.restriction_ids)}}))


# ===================================================================================== S3 text

def _marker_pages(text: str) -> list[int] | None:
    import re
    pages = [int(m) for m in re.findall(r"^\[\[page (\d+)\]\]$", text, flags=re.M)]
    return pages or None


def s3_text(ctx: BuildContext, work: Path) -> None:
    inp = Inputs(ctx)
    recs = inp.v1_records()
    checked, rederive = 0, []
    for t in sorted(recs["derived_text"], key=lambda r: r["text_path"]):
        sha = inp.v1_files.get("text/" + t["text_path"][5:]) if t["text_path"].startswith("text/") else None
        if sha is None:
            _refuse("BUILD_INPUT_MISSING", "a v1 derivative's text file is not in the pinned revision", "S3")
        data = inp.blob(sha)
        if sha256_bytes(data) != t["text_sha256"]:
            _refuse("BUILD_INPUT_HASH", "a v1 derivative does not hash to its record", "S3")
        pages = _marker_pages(data.decode("utf-8"))
        declared = sorted(p["page"] for p in t["pages"])
        if pages is None or sorted(pages) != declared:
            rederive.append(t["doc_id"])
            continue
        write_bytes(work / t["text_path"], data)
        checked += 1
    if rederive:
        _refuse("BUILD_S3_REDERIVE_NOT_IMPLEMENTED", "v1 items need [[page N]] re-derivation with a pinned ocr_config (Stage 3)", "S3",
                [{"doc_id": d} for d in rederive])
    pop = inp.population()
    held = sum(1 for a in pop.get("admissions", []) if a["decision"].startswith("HELD_"))
    write_bytes(work / "TEXT_REPORT.json", json_pretty({
        "v1_derivatives_verified": checked, "v1_rederived": 0, "ocr_config": None,
        "c16_items_promoted": 0, "c16_held_admissions_seen": held,
        "rule": "the central build never promotes a held C16 item; OCR of the local collection stays with the producer (R3, R4)"}))


# ===================================================================================== S4 bundle

def _accounting(ctx: BuildContext, inp: "Inputs", docs: list[dict], pop: dict, shipped: set[str], unresolved: set[str], sid: str) -> bytes:
    """registers/source_accounting.json bytes (accounting.register_bytes); refuses if it does not reconcile (R1-R7)."""
    g = inp.generation
    try:
        reg = source_accounting(
            release_id=ctx.spec["release"]["release_id"], v1_docs=docs, shipped_original_shas=shipped,
            generations=[{**{k: g[k] for k in ("corpus_generation_id", "generation_manifest_sha256", "hf_repo", "hf_revision")},
                          "identities": pop.get("identities", []), "admissions": pop.get("admissions", []), "receipts_unresolved": unresolved}],
            v7_sets=inp.v7_sets())
    except ValueError as exc:
        _refuse("BUILD_ACCOUNTING", str(exc), sid)
    return accounting.register_bytes(reg)


def s4_bundle(ctx: BuildContext, work: Path) -> None:
    inp = Inputs(ctx)
    recs = inp.v1_records()
    pop = inp.population()
    originals = inp.originals()
    texts = {p.relative_to(ctx.stage_dir("S3")).as_posix(): p.read_bytes() for p in files_under(ctx.stage_dir("S3") / "text")}
    c16 = {f"corpus-v2/{name}": data for name, data in inp.exchange.items()}
    c16.update({f"registers/receipts/{k.split('/')[-1]}": v for k, v in inp.receipts.items()})
    src = f"hf:{inp.v1_source['hf_repo']}@{inp.v1_source['hf_revision']}"
    c16["registers/integrity.jsonl"] = integrity_rows(recs["documents"], originals, src)
    unresolved = set(ctx.stage_json("S2", "VALIDATION.json")["receipts"]["unresolved_admissions"])
    c16[ACCOUNTING_FILE] = _accounting(ctx, inp, recs["documents"], pop, set(originals), unresolved, "S4")
    for name, hashes in inp.v7_sets().items():   # 2.1 CS1-CS5: one file per declared V7_REFERENCE source
        c16[accounting.candidate_set_path(f"v7:{name}")] = accounting.candidate_set_bytes(hashes)
    write_release_tree(work / "tree", release_manifest_template=inp.template, spec=ctx.spec, defaults=inp.defaults, register=inp.register,
                       key_id=inp.inv["dev_signing"]["key_id"], v1_source=inp.v1_source, records=recs, originals=originals,
                       texts=texts, research=inp.v1_group("research/"), c16_files=c16)


# ===================================================================================== S5 reference import

def _sign_copy(tree: Path, dst: Path, key_path) -> bytes:
    rmtree(dst)
    for p in files_under(tree):
        copy_file(p, dst / p.relative_to(tree))
    sums = sums_bytes(dst)
    write_bytes(dst / SUMS, sums)
    sk, pub = load_dev_key(key_path)
    write_bytes(dst / SIG, sk.sign(sums))
    return pub


def s5_ref_import(ctx: BuildContext, work: Path) -> None:
    from mimamsa_importer import configure_site, import_release
    inp = Inputs(ctx)
    scratch = ctx.build_root / ".tmp-S5-bundle"
    try:
        pub = _sign_copy(ctx.stage_dir("S4") / "tree", scratch, ctx.dev_key_path)
        if pub != inp.dev_pub():
            _refuse("BUILD_DEV_KEY_CHANGED", "development key differs from the S1 inventory", "S5")
        site = work / "site"
        configure_site(site, exclusion_channel="none")
        res = import_release(scratch, site, trusted_public_key=pub, mode="development", register=inp.register)
    finally:
        rmtree(scratch)
    if not res.activated:
        _refuse("BUILD_REF_IMPORT_REFUSED", "the reference site refused the bundle: " + "; ".join(res.refused_reasons), "S5")
    c16 = res.c16 or {}
    write_bytes(work / "REF_IMPORT.json", json_pretty({
        "importer": "app/importer (v1 path plus the B01 C16 stage, development mode, dev key)", "activated": True,
        "release_id": res.release_id, "verified": {k: len(v) for k, v in sorted(res.verified.items())}, "unresolved": len(res.unresolved),
        "unresolved_kinds": sorted({u["kind"] for u in res.unresolved}),
        "c16_import": {"active": c16.get("active"), "contract": c16.get("contract"), "codes": c16.get("codes"),
                       "served_copies": sorted(c["doc_id"] for c in c16.get("copies", []) if c["served"]),
                       "accounting_digests": c16.get("accounting_digests")}}))


# ===================================================================================== S6 accelerate

def _run_accel(ctx: BuildContext, site: Path, tmp: Path, sid: str) -> dict:
    tool = ctx.accel_tool
    if tool is None or not Path(tool).is_file():
        _refuse("BUILD_TOOL_MISSING", "KBuildAccel.dll not built (python -m mimamsa_kbuild build-accel)", sid)
    workers = stage_workers(ctx.spec, "S6", ctx.budget)
    summary = tmp / "summary.json"
    cmd = ["dotnet", str(tool), "--site", str(site), "--text-dir", str(tmp / "text"), "--index-dir", str(tmp / "index"),
           "--graph-out", str(tmp / "graph"), "--build-time", ctx.spec["pinned_build_time"], "--out", str(summary)]
    p = subprocess.run(cmd, env=child_env(ctx.budget, workers), creationflags=child_creationflags(ctx.budget),
                       capture_output=True, text=True, timeout=3600)
    if p.returncode != 0:
        _refuse("BUILD_ACCEL_FAILED", f"KBuildAccel exited {p.returncode}: {(p.stderr or '')[-400:]}", sid)
    return json.loads(summary.read_text(encoding="utf-8"))


def _canonical_rows(raw: Path, table: str, allowlist: dict, sid: str) -> bytes:
    spec = next(t for t in allowlist["tables"] if t["table"] == table)
    rows = [json.loads(x) for x in raw.read_text(encoding="utf-8").split("\n") if x.strip()]
    data = knowledge_rows.row_file_bytes(rows, spec["primary_key"])
    issues = knowledge_rows.row_file_issues(table, data, allowlist)
    if issues:
        _refuse(issues[0].code, f"{table}: {issues[0].message}", sid, _issue_list(issues))
    return data


def _single_dir(root: Path, sid: str) -> Path:
    subs = [p for p in root.iterdir() if p.is_dir() and not p.name.startswith(".")]
    if len(subs) != 1:
        _refuse("BUILD_ACCEL_LAYOUT", f"expected one published generation under {root.name}", sid)
    return subs[0]


def text_store_source_inputs(site: Path) -> tuple[str, list[dict], list[dict]]:
    """(generation id, documents, derived) of the site's ACTIVE generation, as `digests.text_store_source_digest` takes
    them and as the B1 DiskTextStore (TextStoreSourceDigest.ForGeneration) selects them: documents the generation
    serves whose copy matches item_document; derivatives listed servable for such a document's copy."""
    gid = (site / "ACTIVE").read_text(encoding="utf-8").strip()
    gdir = site / "generations" / gid
    gen = json.loads((gdir / "generation.json").read_text(encoding="utf-8"))
    ok_docs, ok_der = set(gen["servable"]["documents"]), set(gen["servable"]["derived_text"])
    item = gen["item_document"]["documents"]
    docs = {}
    for d in parse_jsonl((gdir / "records" / "documents.jsonl").read_bytes()):
        sha = d["source_copy"]["sha256"]
        if d["doc_id"] in ok_docs and (item.get(d["doc_id"]) or [None, None])[1] == sha:
            docs[d["doc_id"]] = sha
    derived = []
    for t in parse_jsonl((gdir / "records" / "derived_text.jsonl").read_bytes()):
        did = f"{t['doc_id']}@{t['pipeline']['name']}/{t['pipeline']['version']}"
        if did in ok_der and docs.get(t["doc_id"]) == t["source_copy_sha256"]:
            derived.append(t)
    return gid, [{"doc_id": k, "copy_sha256": v} for k, v in docs.items()], derived


def text_store_source_digest(site: Path) -> str:
    gid, docs, derived = text_store_source_inputs(site)
    return digests.text_store_source_digest(gid, docs, derived)


def build_accelerators(ctx: BuildContext, site: Path, out: Path, sid: str, pop: dict, allowlist: dict) -> dict:
    """Rows (Python reference derivation), then text store, lexical index and graph (B1 builders through KBuildAccel).
    Every result digest is computed with mimamsa_contract.c16.digests (2.1 byte definitions)."""
    tables = []
    derived = knowledge_rows.derive_rows(pop)
    for t in sorted(allowlist["tables"], key=lambda t: t["table"]):
        if t["derivation"] != "PYTHON_REFERENCE":
            continue
        data = knowledge_rows.row_file_bytes(derived[t["table"]], t["primary_key"])
        issues = knowledge_rows.row_file_issues(t["table"], data, allowlist) + knowledge_rows.rederive_compare(t["table"], data, pop, allowlist)
        if issues:
            _refuse(issues[0].code, f"{t['table']}: {issues[0].message}", sid, _issue_list(issues))
        write_bytes(out / "accelerators" / "rows" / f"{t['table']}.jsonl", data)
        tables.append({"table": t["table"], "row_count": len(derived[t["table"]]), "rows_sha256": knowledge_rows.rows_sha256(data)})
    tmp = ctx.build_root / f".tmp-{sid}-accel"
    rmtree(tmp)
    tmp.mkdir(parents=True)
    try:
        summary = _run_accel(ctx, site, tmp, sid)
        manifests = {}
        # TEXT_STORE ships prebuilt (B04 section 5): its source digest is the bundle-independent 2.1 digest, which the
        # site recomputes from its own generation records before adopting the store (DiskTextStore.AdoptShipped).
        for kind, sub, dst in (("TEXT_STORE", "text", "accelerators/text-store"), ("LEXICAL_INDEX", "index", "accelerators/search-index")):
            gdir = _single_dir(tmp / sub, sid)
            names = sorted(p.name for p in gdir.iterdir())
            if not set(names) <= {"text.sqlite", "search.sqlite", "MANIFEST.json"} or "MANIFEST.json" not in names:
                _refuse("BUILD_ACCEL_LAYOUT", f"unexpected files in the published {kind}", sid)
            for n in names:
                copy_file(gdir / n, out / dst / n)
            manifests[kind] = json.loads((gdir / "MANIFEST.json").read_text(encoding="utf-8"))
            db = out / dst / ("text.sqlite" if kind == "TEXT_STORE" else "search.sqlite")
            if digests.file_digest(db.read_bytes()) != manifests[kind]["file_sha256"]:
                _refuse("BUILD_ACCEL_DIGEST", f"{kind} file does not hash to its MANIFEST.json", sid)
        ts_digest = text_store_source_digest(site)
        if manifests["TEXT_STORE"]["source_digest"] != ts_digest:
            _refuse("BUILD_ACCEL_DIGEST", "the text store's source digest is not digests.text_store_source_digest of the generation", sid)
        graph_tables, ids = [], {}
        for table, raw in (("graph_nodes", "nodes.raw.jsonl"), ("graph_edges", "edges.raw.jsonl")):
            data = _canonical_rows(tmp / "graph" / raw, table, allowlist, sid)
            write_bytes(out / "accelerators" / "graph" / f"{table}.jsonl", data)
            ids[table] = [json.loads(x)["id"] for x in data.split(b"\n") if x]
            graph_tables.append({"table": table, "row_count": len(ids[table]), "rows_sha256": knowledge_rows.rows_sha256(data)})
        if digests.graph_digest(summary["graph_builder_version"], ids["graph_nodes"], ids["graph_edges"]) != summary["graph_digest"]:
            _refuse("BUILD_ACCEL_DIGEST", "GraphStore.Digest differs from digests.graph_digest over the shipped graph rows", sid)
    finally:
        rmtree(tmp)
    return {"rows": {"tables": tables}, "graph": {"tables": graph_tables, "digest": summary["graph_digest"],
                                                  "builder_version": summary["graph_builder_version"],
                                                  "nodes": summary["graph_nodes"], "edges": summary["graph_edges"]},
            "text_store": {**{k: manifests["TEXT_STORE"][k] for k in ("format", "generation", "source_digest", "documents", "pages", "passages", "file_sha256", "built_utc")},
                           "shipped": True, "accounting": "SHIPPED"},
            "lexical_index": {k: manifests["LEXICAL_INDEX"][k] for k in ("format", "generation", "source_digest", "documents", "passages", "terms", "file_sha256", "built_utc")},
            "vectors": {"status": "OMITTED_DEGRADED", "reason": "CP-1 is lexical-only: no vectors are built and nothing embeds (SG-4)"},
            "generation_id": summary["generation_id"], "documents": summary["documents"], "passages": summary["passages"]}


def s6_accelerate(ctx: BuildContext, work: Path) -> None:
    inp = Inputs(ctx)
    acc = build_accelerators(ctx, ctx.stage_dir("S5") / "site", work, "S6", inp.population(), inp.allowlist)
    write_bytes(work / "ACCELERATORS.json", json_pretty(acc))


# ===================================================================================== S7 assemble (B05-minimal)

_TOOL = lambda name: {"name": name, "version": VERSION, "commit": None, "config_sha256": None}  # noqa: E731


def _jsonl_count(root: Path, paths: list[str]) -> int:
    return sum(sum(1 for x in (root / p).read_bytes().split(b"\n") if x.strip()) for p in paths if p.endswith(".jsonl"))


def knowledge_release_manifest(ctx: BuildContext, inp: Inputs, rel: Path, acc: dict) -> dict:
    spec = ctx.spec
    E = lambda prefix: file_entries(rel, prefix)  # noqa: E731
    paths = lambda es: [e["path"] for e in es]    # noqa: E731
    originals, text, research = E("originals"), E("text"), E("research")
    records = [e for e in E("data") + E("corpus-v2") if not e["path"].startswith("corpus-v2/admissions")]
    admission = E("corpus-v2/admissions.jsonl") + E(ACCOUNTING_FILE) + E(CANDIDATE_SET_DIR) + E("registers/receipts")
    integrity = E("registers/integrity.jsonl")
    rows, graph = E("accelerators/rows"), E("accelerators/graph")
    index, tstore = E("accelerators/search-index"), E("accelerators/text-store")
    auth = lambda cid, kind, fmt, files, digest, count, verify: {  # noqa: E731
        "component_id": cid, "kind": kind, "format": fmt, "authority": "AUTHORITATIVE", "transport": "FULL", "files": files,
        "result_digest": digest, "result_count": count, "source_digest": None, "builder": None, "model_sha256": None,
        "disk_budget_bytes": None, "fallback": None, "verify": verify}
    base_verify = ["SHA256_EACH_FILE", "RESULT_DIGEST", "RESTRICTED_REGISTER"]
    records_digest = concat_digest(rel, paths(records))
    acc_comp = lambda cid, kind, fmt, files, digest, count, source, builder, verify, **kw: {  # noqa: E731
        "component_id": cid, "kind": kind, "format": fmt, "authority": "ACCELERATOR", "transport": "FULL", "files": files,
        "result_digest": digest, "result_count": count, "source_digest": source, "builder": _TOOL(builder), "model_sha256": None,
        "disk_budget_bytes": sum(f["bytes"] for f in files), "fallback": "REBUILD_LOCALLY_CHEAP", "verify": verify, **kw}
    rows_tables = [{**t, "file": f"accelerators/rows/{t['table']}.jsonl"} for t in acc["rows"]["tables"]]
    graph_tables = [{**t, "file": f"accelerators/graph/{t['table']}.jsonl"} for t in acc["graph"]["tables"]]
    gen_shas = sorted(g["generation_manifest_sha256"] for g in spec["inputs"]["producer_generations"])
    comps = [
        auth("originals", "ORIGINALS", "vault-sha256", originals, hashset_digest(e["sha256"] for e in originals), len(originals), base_verify),
        auth("text", "TEXT_DERIVATIVES", "page-marker-v1", text, hashset_digest(e["sha256"] for e in text), len(text), base_verify),
        auth("records", "RECORDS", "canonical-jsonl", records, records_digest, _jsonl_count(rel, paths(records)), base_verify + ["CONTRACT_VALIDATION"]),
        auth("research", "RESEARCH_AIDS", "jsonl", research, concat_digest(rel, paths(research)), _jsonl_count(rel, paths(research)), base_verify),
        auth("integrity", "INTEGRITY_REGISTER", "canonical-jsonl", integrity, concat_digest(rel, paths(integrity)), _jsonl_count(rel, paths(integrity)), base_verify),
        auth("admission", "ADMISSION_REGISTER", "canonical-jsonl", admission, concat_digest(rel, paths(admission)),
             _jsonl_count(rel, paths(admission)), base_verify + ["CONTRACT_VALIDATION"]),
        acc_comp("knowledge-rows", "KNOWLEDGE_ROWS", "mimamsa-knowledge-rows/1", rows, rows_component_digest(rows_tables),
                 sum(t["row_count"] for t in rows_tables),
                 sha256_bytes(canonical.canonical_bytes([gen_shas, inp.allowlist["knowledge_schema_version"]])), "knowledge-rows-reference",
                 ["SHA256_EACH_FILE", "ROW_COUNTS", "ROWS_ALLOWLIST_AND_TYPES", "ROWS_REDERIVE_COMPARE", "SOURCE_DIGEST_EQUALS_SITE"], tables=rows_tables),
        acc_comp("graph", "GRAPH", "c15-graph-rows-v1", graph, acc["graph"]["digest"], acc["graph"]["nodes"] + acc["graph"]["edges"],
                 sha256_bytes(f"{acc['graph']['builder_version']}|{records_digest}".encode()), "graph-builder",
                 ["SHA256_EACH_FILE", "GRAPH_DIGEST", "GRAPH_STRUCTURAL_RECHECK", "SAMPLED_REBUILD_PARITY", "SOURCE_DIGEST_EQUALS_SITE"], tables=graph_tables),
        acc_comp("lexical-index", "LEXICAL_INDEX", acc["lexical_index"]["format"], index, acc["lexical_index"]["file_sha256"],
                 acc["lexical_index"]["passages"], acc["lexical_index"]["source_digest"], "lexical-index-builder",
                 ["SHA256_EACH_FILE", "SQLITE_QUICK_CHECK", "SAMPLED_POSTINGS_REDERIVE", "SAMPLED_QUERY_PARITY", "SOURCE_DIGEST_EQUALS_SITE"]),
    ]
    if acc["text_store"]["shipped"]:   # source_digest: the bundle-independent 2.1 digest (B04 section 5)
        comps.append(acc_comp("text-store", "TEXT_STORE", acc["text_store"]["format"], tstore, acc["text_store"]["file_sha256"],
                              acc["text_store"]["documents"], acc["text_store"]["source_digest"], "text-store-builder",
                              ["SHA256_EACH_FILE", "SQLITE_QUICK_CHECK", "TEXT_STORE_BIND_EXACT", "PAGE_HASH_ON_READ", "SOURCE_DIGEST_EQUALS_SITE"],
                              binding="BIND_EXACT_TO_GENERATION_RECORDS"))
    shipped = {c["kind"] for c in comps}
    accounting = [{"kind": k, "status": "SHIPPED", "reason": "shipped in this release"} for k in c16rules.KNOWLEDGE_KINDS if k in shipped]
    if "TEXT_STORE" not in shipped:
        accounting.append({"kind": "TEXT_STORE", "status": "SITE_BUILDS_CHEAP", "reason": "text store not shipped in this build"})
    accounting.append({"kind": "VECTOR_PACK", "status": "OMITTED_DEGRADED",
                       "reason": "no vectors built (CP-1 lexical-only); the site never embeds passages (SG-4)"})
    gates = sorted(g["gate"] for g in inp.gate_status["gates"] if g["status"] == "OPEN" and "KNOWLEDGE" in g["applies_to"])
    return {
        "contract": spec["inputs"]["contracts"]["corpus"], "record_kind": "knowledge_release_manifest", "manifest_format": "MKR-1",
        "release_class": "KNOWLEDGE", "release_id": spec["release"]["release_id"], "release_sequence": spec["release"]["release_sequence"],
        "base": {"mode": "FULL", "base_release_id": None, "base_manifest_sha256": None},
        "corpus_generations": [{"corpus_generation_id": g["corpus_generation_id"], "manifest_sha256": g["generation_manifest_sha256"]}
                               for g in spec["inputs"]["producer_generations"]],
        "compatibility": {"knowledge_format": inp.defaults["knowledge_format"], "min_app_version": inp.defaults["min_app_version"],
                          "max_app_version": inp.defaults["max_app_version"],
                          "contracts": {"v1": spec["inputs"]["contracts"]["v1"], "corpus": spec["inputs"]["contracts"]["corpus"]},
                          "knowledge_schema_version": inp.allowlist["knowledge_schema_version"],
                          "graph_builder_version": acc["graph"]["builder_version"], "index_format": acc["lexical_index"]["format"],
                          "text_store_format": acc["text_store"]["format"], "vector_store_format": "MIMVEC01",
                          "required_models": [m for m in spec["inputs"]["models"] if m["role"] in ("EMBEDDER", "RERANKER")]},
        "components": comps,
        "capability": {"declared_service_level": "DEGRADED_LEXICAL_ONLY", "accounting": accounting, "semantic_search_promised": False,
                       "pending_future_gates": gates},
        "heavy_compute_on_site": {"ocr": "NONE", "embedding": "NONE", "graph_rebuild": "ONLY_IF_ACCELERATOR_REJECTED"},
        "notes": inp.defaults["notes"], "signing_purpose": "release"}


def assert_release_manifest(m: dict, sums: dict[str, str] | None, sid: str, ledger: int = 0) -> None:
    issues = c16rules.record_issues(m, auth_ledger_version=ledger)
    issues += knowledge_rows.manifest_table_owner_issues(m)   # I-2: graph tables only under GRAPH
    if sums is not None:
        issues += c16rules.component_inventory_issues(m, sums)
    if issues:
        _refuse(issues[0].code, "KNOWLEDGE_RELEASE.json fails the contract rules: " + issues[0].message, sid, _issue_list(issues))
    if m["capability"]["declared_service_level"] == "FULL":
        _refuse("KR_FULL_CAPABILITY_CLAIM", "the Stage 2 build never claims FULL service", sid)


def s7_assemble(ctx: BuildContext, work: Path) -> None:
    inp = Inputs(ctx)
    rel = work / "release"
    for base in (ctx.stage_dir("S4") / "tree", ctx.stage_dir("S6")):
        for p in files_under(base):
            r = p.relative_to(base).as_posix()
            if base.name == "S6" and not r.startswith("accelerators/"):
                continue
            link_or_copy(p, rel / r)
    m = knowledge_release_manifest(ctx, inp, rel, ctx.stage_json("S6", "ACCELERATORS.json"))
    assert_release_manifest(m, None, "S7")
    write_bytes(rel / "KNOWLEDGE_RELEASE.json", json.dumps(m, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8"))
    sums = sums_bytes(rel)
    write_bytes(rel / SUMS, sums)
    entries, bad = parse_sums(sums.decode("utf-8"))
    if bad:
        _refuse("SUMS_MALFORMED", "generated SHA256SUMS is malformed", "S7")
    assert_release_manifest(m, entries, "S7")


# ===================================================================================== S8 sign (development only)

def s8_sign(ctx: BuildContext, work: Path) -> None:
    inp = Inputs(ctx)
    sk, pub = load_dev_key(ctx.dev_key_path)
    if pub != inp.dev_pub():
        _refuse("BUILD_DEV_KEY_CHANGED", "development key differs from the S1 inventory", "S8")
    rel = ctx.stage_dir("S7") / "release"
    bundle = work / "bundle"
    for p in files_under(rel):
        link_or_copy(p, bundle / p.relative_to(rel))
    sums = (bundle / SUMS).read_bytes()
    write_bytes(bundle / SIG, sk.sign(sums))
    write_bytes(work / "dev-trust" / "trust_list.json", json_pretty(dev_trust_list(pub)))
    write_bytes(work / "SIGNING.json", json_pretty({
        "signing_mode": "DEVELOPMENT", "purpose": "release", "key_id": dev_key_id(pub), "holder": "DEVELOPMENT",
        "signed_file": SUMS, "signed_file_sha256": sha256_bytes(sums),
        "note": "development key (WD-11): production sites refuse it (SIGNATURE_DEV_KEY_IN_PRODUCTION); no trust-list change"}))


# ===================================================================================== S9 verify

def s9_verify(ctx: BuildContext, work: Path) -> None:
    from mimamsa_importer import configure_site, import_release
    inp = Inputs(ctx)
    bundle = ctx.stage_dir("S8") / "bundle"
    trust = parse_trust_list(json.loads((ctx.stage_dir("S8") / "dev-trust" / "trust_list.json").read_text(encoding="utf-8")))
    checks: dict[str, object] = {}
    rep = validate_bundle(bundle, trust_list=trust, mode="development", register=inp.register, current_release_sequence=0)
    errs = [i for i in rep.errors]
    if errs:
        _refuse(errs[0].code, "signed bundle fails v1 validation: " + errs[0].message, "S9", _issue_list(errs))
    checks["v1_bundle_development_mode"] = {"ok": True, "signature_verified": rep.signature_verified, "files": rep.checked_files, "records": rep.checked_records}
    prod = validate_bundle(bundle, trust_list=trust, mode="production", register=inp.register, current_release_sequence=0)
    prod_codes = sorted({i.code for i in prod.errors})
    if prod.ok:
        _refuse("BUILD_DEV_RELEASE_ACCEPTED_IN_PRODUCTION", "a development-signed release must be refused in production mode", "S9")
    checks["production_mode_refuses_dev_signature"] = prod_codes
    m = json.loads((bundle / "KNOWLEDGE_RELEASE.json").read_text(encoding="utf-8"))
    sums, _ = parse_sums((bundle / SUMS).read_text(encoding="utf-8"))
    assert_release_manifest(m, sums, "S9")
    checks["mkr1_schema_rules_inventory"] = "ok"
    # authoritative components: every file, every result digest (the assembler's definitions recomputed from the bundle)
    for c in m["components"]:
        for f in c["files"]:
            if sha256_file(bundle / f["path"]) != f["sha256"]:
                _refuse("KR_INVENTORY", "component file does not hash to the manifest", "S9")
    again = knowledge_release_manifest(ctx, inp, bundle, ctx.stage_json("S6", "ACCELERATORS.json"))
    if again["components"] != m["components"]:
        _refuse("KR_RESULT_DIGEST", "component digests recomputed from the signed bundle differ", "S9")
    checks["result_digests_recomputed"] = len(m["components"])
    # strict C16 validation of the shipped corpus-v2/, and the admission accounting recomputed from the bundle
    ex = {p.name: p.read_bytes() for p in (bundle / "corpus-v2").iterdir()}
    ex_err = [i for i in c16rules.exchange_issues(ex, mode="strict", register=inp.register) if i.severity == "error"]
    if ex_err:
        _refuse(ex_err[0].code, "shipped corpus-v2 fails strict validation", "S9", _issue_list(ex_err))
    pop = {}
    for name, data in ex.items():
        if name.endswith(".jsonl"):
            pop.setdefault(name.split(".", 1)[0], []).extend(parse_jsonl(data))
    docs = parse_jsonl((bundle / "data" / "documents.jsonl").read_bytes())
    shipped = {sha256_file(p) for p in (bundle / "originals").iterdir()}
    rdir = bundle / "registers" / "receipts"
    rr = receipt_resolution(pop, json.loads(ex["GENERATION.json"]), {p.name: p.read_bytes() for p in rdir.iterdir()} if rdir.is_dir() else {},
                            inp.register)
    acct = _accounting(ctx, inp, docs, pop, shipped, set(rr["unresolved_admissions"]), "S9")
    if acct != (bundle / ACCOUNTING_FILE).read_bytes():
        _refuse("BUILD_ACCOUNTING", "source accounting recomputed from the bundle differs from the shipped register", "S9")
    checks["source_accounting_recomputed"] = "equal (contract 2.1 register, accounting_issues clean)"
    # v7 candidate sets (2.1 CS1-CS5) with the reference check, against the signed ADMISSION_REGISTER inventory
    decl = json.loads(acct)
    adm_inv = {f["path"] for c in m["components"] if c["kind"] == "ADMISSION_REGISTER" for f in c["files"]}
    cs_files = {p.relative_to(bundle).as_posix(): p.read_bytes() for p in files_under(bundle / "registers" / "candidate_sets")} \
        if (bundle / "registers" / "candidate_sets").is_dir() else {}
    cs_union, cs_issues = accounting.candidate_set_issues(decl, cs_files, adm_inv)
    want_union = set().union(*inp.v7_sets().values()) if inp.v7_files else set()
    if cs_issues or cs_union != want_union:
        _refuse("BUILD_ACCOUNTING", "v7 candidate sets fail the 2.1 reference check (CS1-CS5)", "S9", _issue_list(cs_issues))
    checks["v7_candidate_sets"] = {"sources": sorted(inp.v7_files), "hashes": len(cs_union), "check": "accounting.candidate_set_issues: clean"}
    # knowledge rows: loader pre-COPY checks, row counts and the full re-derivation (ROWS_REDERIVE_COMPARE)
    for t in next(c for c in m["components"] if c["kind"] == "KNOWLEDGE_ROWS")["tables"]:
        data = (bundle / t["file"]).read_bytes()
        issues = knowledge_rows.row_file_issues(t["table"], data, inp.allowlist) + knowledge_rows.rederive_compare(t["table"], data, pop, inp.allowlist)
        if issues or sum(1 for x in data.split(b"\n") if x) != t["row_count"]:
            _refuse("KR_ROWS_REDERIVE_MISMATCH", f"{t['table']} rows fail verification", "S9", _issue_list(issues))
    checks["knowledge_rows"] = "row_file_issues, ROW_COUNTS and ROWS_REDERIVE_COMPARE pass"
    # a fresh scratch site imports the signed bundle; its own cheap rebuild of every accelerator must equal the shipped
    # bytes (full parity, stronger than the sampled checks; SOURCE_DIGEST_EQUALS_SITE included)
    scratch = ctx.build_root / ".tmp-S9-site"
    rmtree(scratch)
    try:
        configure_site(scratch / "site", exclusion_channel="none")
        res = import_release(bundle, scratch / "site", trust_list=trust, mode="development", register=inp.register)
        if not res.activated:
            _refuse("BUILD_VERIFY_IMPORT_REFUSED", "fresh scratch site refused the signed bundle: " + "; ".join(res.refused_reasons), "S9")
        site_c16 = res.c16 or {}
        if not site_c16.get("accounting_digests", {}).get("site_sha256"):
            _refuse("BUILD_VERIFY_IMPORT_REFUSED", "the site importer did not recompute the source accounting", "S9")
        ts_site_digest = text_store_source_digest(scratch / "site")
        acc = build_accelerators(ctx, scratch / "site", scratch / "rebuilt", "S9", pop, inp.allowlist)
        mismatched = []
        for p in files_under(scratch / "rebuilt" / "accelerators"):
            r = p.relative_to(scratch / "rebuilt").as_posix()
            if not (bundle / r).is_file() or sha256_file(p) != sha256_file(bundle / r):
                mismatched.append(r)
        if acc["graph"]["digest"] != next(c for c in m["components"] if c["kind"] == "GRAPH")["result_digest"]:
            mismatched.append("graph digest")
        shipped_ts = (bundle / "accelerators" / "text-store" / "MANIFEST.json").is_file()
        site_ts = {k: acc["text_store"][k] for k in ("documents", "pages", "passages", "file_sha256")}
    finally:
        rmtree(scratch)
    if mismatched:
        _refuse("BUILD_ACCEL_PARITY", "site-side rebuild differs from the shipped accelerators", "S9", [{"path": x} for x in mismatched])
    s6_ts = ctx.stage_json("S6", "ACCELERATORS.json")["text_store"]
    if site_ts["documents"] != s6_ts["documents"] or site_ts["passages"] != s6_ts["passages"]:
        _refuse("BUILD_TEXT_STORE_SITE_BUILD", "the site's text-store build does not cover the generation", "S9")
    ts_comp = next((c for c in m["components"] if c["kind"] == "TEXT_STORE"), None)
    if ts_comp is None or ts_comp["source_digest"] != ts_site_digest:
        _refuse("BUILD_TEXT_STORE_SOURCE_DIGEST", "the shipped text store's 2.1 source digest differs from the fresh site's", "S9")
    results = {"KNOWLEDGE_ROWS": "VERIFIED", "GRAPH": "VERIFIED", "LEXICAL_INDEX": "VERIFIED",
               "TEXT_STORE": "VERIFIED" if shipped_ts else "MISSING", "VECTOR_PACK": "MISSING"}
    outcome = components.activation_outcome(results, inp.contracts, mode="development")
    if outcome["result"] == "ACTIVE_FULL" or outcome["service_level"] == "FULL":
        _refuse("BUILD_CLAIMS_FULL", "CP-1 must never reach ACTIVE_FULL", "S9")
    checks["accelerator_rebuild_parity"] = "byte-identical on a fresh site: lexical index, text store, graph rows and digest, knowledge rows"
    checks["text_store"] = {"shipped": shipped_ts, "source_digest_equals_site": True, "site_build_documents": site_ts["documents"],
                            "site_build_passages": site_ts["passages"],
                            "note": "bundle-independent 2.1 source digest (digests.text_store_source_digest, B04 section 5)"}
    checks["site_importer"] = {"c16_active": site_c16.get("active"), "accounting_digests": site_c16.get("accounting_digests")}
    write_bytes(work / "VERIFY.json", json_pretty({
        "release_id": m["release_id"], "declared_service_level": m["capability"]["declared_service_level"],
        "expected_activation": outcome, "embedder_calls": 0, "checks": checks,
        "acceptance_level": "FIXTURE (SG-5): proves the wiring only; closes no FG gate on real data",
        "not_run_here": ["B03 .NET restricted-role row loader (CP-1 slice)", "B04 .NET kind-specific verifiers (sampled checks UNCALIBRATED)",
                         "B06 activation journal (CP-1 slice)"]}))


STAGES = {"S0": s0_spec, "S1": s1_fetch, "S2": s2_validate, "S3": s3_text, "S4": s4_bundle, "S5": s5_ref_import,
          "S6": s6_accelerate, "S7": s7_assemble, "S8": s8_sign, "S9": s9_verify}
FRESH = {"S1": s1_fresh}
