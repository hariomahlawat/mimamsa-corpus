"""DELTA knowledge releases (B02 Stage 3; architecture section 9, "Delta transport"), kind-specific.

The build always assembles the FULL state first (S7 `full/`, with every component's full-state result digest), then
derives the delta against a verified FULL base release (spec `release.base_mode` DELTA, `base_release_id`; the base
bundle is passed with --base-bundle, hashed into the S1 inventory and its signature verified in S7):

| Kind | Delta transport here |
| --- | --- |
| ORIGINALS | DELTA: objects not in the base only (add-only; a base object absent from the new state refuses: removal is the exclusion channel's job or a FULL release) |
| TEXT_DERIVATIVES | DELTA: derivatives new or changed against the base only (a base derivative absent from the new state refuses) |
| RECORDS, RESEARCH_AIDS, INTEGRITY_REGISTER, ADMISSION_REGISTER | FULL replacement: full canonical JSONL (the architecture's first option; additions/tombstones are not used) |
| KNOWLEDGE_ROWS, GRAPH, LEXICAL_INDEX, TEXT_STORE | FULL replacement (accelerators are rebuilt from the full state; never patched) |
| any kind whose files and full-state result digest equal the base's | not shipped: UNCHANGED_FROM_BASE (the reason names the base and its digest) |
| VECTOR_PACK | as in the full state (lexical-only builds: OMITTED_DEGRADED) |

Every shipped component keeps the FULL-STATE result digest and count (architecture section 3: a delta changes what
travels, never what is verified). `base.base_manifest_sha256` is the sha256 of the base KNOWLEDGE_RELEASE.json bytes
(the bytes its SHA256SUMS and signature cover); FLAGGED: the contract does not yet fix this definition.

`apply` is the site-side application (S9 reconstructs base + delta and compares it with the full state byte for byte).
The site importer (B01) does not import deltas yet (Stage 4, B05/B06): S9 imports the reconstructed full state.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .errors import BuildRefused
from .fsutil import files_under, link_or_copy, rmtree, sha256_file

KR = "KNOWLEDGE_RELEASE.json"
MANIFEST_FILES = ("RELEASE.json", "CHANGES.json", KR, "SHA256SUMS", "SHA256SUMS.sig")
ADD_ONLY = ("ORIGINALS", "TEXT_DERIVATIVES")


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def base_issues(base_bundle, spec: dict) -> list[dict]:
    rel = spec["release"]
    if base_bundle is None or not (Path(base_bundle) / KR).is_file():
        return [{"code": "BUILD_DELTA_BASE_MISSING", "message": "a DELTA build needs --base-bundle (the signed FULL base release)"}]
    try:
        m = json.loads((Path(base_bundle) / KR).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return [{"code": "BUILD_DELTA_BASE_MISSING", "message": "base KNOWLEDGE_RELEASE.json unreadable"}]
    out = []
    if m.get("release_id") != rel["base_release_id"]:
        out.append({"code": "BUILD_DELTA_BASE_MISMATCH", "message": "the base bundle is not the release the spec names (base_release_id)"})
    if (m.get("base") or {}).get("mode") != "FULL":
        out.append({"code": "BUILD_DELTA_BASE_NOT_FULL", "message": "the base must be a FULL-transport release (delta chains need the site's state)"})
    if not isinstance(m.get("release_sequence"), int) or m["release_sequence"] >= rel["release_sequence"]:
        out.append({"code": "BUILD_DELTA_SEQUENCE", "message": "the delta's release_sequence must exceed the base's"})
    return out


def base_inventory(base_bundle, spec: dict) -> tuple[dict, dict[str, Path]]:
    issues = base_issues(base_bundle, spec)
    if issues:
        raise BuildRefused(issues[0]["code"], issues[0]["message"], "S1", issues)
    root = Path(base_bundle)
    files, blobs = [], {}
    for p in files_under(root):
        h = sha256_file(p)
        files.append({"path": p.relative_to(root).as_posix(), "sha256": h, "bytes": p.stat().st_size})
        blobs.setdefault(h, p)
    kr = next(f for f in files if f["path"] == KR)
    return {"release_id": spec["release"]["base_release_id"], "manifest_sha256": kr["sha256"], "files": files}, blobs


def materialise_base(base_inv: dict, blob_path, dst: Path) -> Path:
    """The base bundle tree, re-created from the S1 cache (hard links where possible)."""
    rmtree(dst)
    for f in base_inv["files"]:
        link_or_copy(blob_path(f["sha256"]), dst / f["path"])
    return dst


def make_delta(full_manifest: dict, base_manifest: dict, base_inv: dict) -> dict:
    """The DELTA manifest for `full_manifest` against the base (see the module table)."""
    base_by_kind = {c["kind"]: c for c in base_manifest["components"]}
    comps, status = [], {a["kind"]: dict(a) for a in full_manifest["capability"]["accounting"]}
    for c in full_manifest["components"]:
        b = base_by_kind.get(c["kind"])
        cfiles = {f["path"]: f["sha256"] for f in c["files"]}
        bfiles = {f["path"]: f["sha256"] for f in b["files"]} if b else {}
        if b and b["result_digest"] == c["result_digest"] and bfiles == cfiles and b["format"] == c["format"]:
            status[c["kind"]] = {"kind": c["kind"], "status": "UNCHANGED_FROM_BASE",
                                 "reason": f"unchanged from base {base_manifest['release_id']}; result_digest {c['result_digest']}"}
            continue
        if c["kind"] in ADD_ONLY:
            removed = sorted(p for p in bfiles if p not in cfiles)
            if removed:
                raise BuildRefused("BUILD_DELTA_REMOVAL", f"{c['kind']} is add-only in a delta: {len(removed)} base file(s) absent from the "
                                   "new state (withdrawal is the exclusion channel's job; otherwise build a FULL release)", "S7",
                                   [{"path": p} for p in removed[:20]])
            new = dict(c, transport="DELTA", files=[f for f in c["files"] if bfiles.get(f["path"]) != f["sha256"]])
        else:
            new = dict(c, transport="FULL")
        comps.append(new)
        status[c["kind"]] = {"kind": c["kind"], "status": "SHIPPED", "reason": "shipped in this release" if new["transport"] == "FULL"
                             else "shipped in this release (delta: new objects only; result digest is the full state)"}
    m = json.loads(json.dumps(full_manifest))
    m["base"] = {"mode": "DELTA", "base_release_id": base_manifest["release_id"], "base_manifest_sha256": base_inv["manifest_sha256"]}
    m["components"] = comps
    order = [a["kind"] for a in full_manifest["capability"]["accounting"]]
    m["capability"]["accounting"] = [status[k] for k in order]
    return m


def changes(full_docs: list[dict], base_docs: list[dict]) -> dict:
    b = {d["doc_id"]: json.dumps(d, sort_keys=True) for d in base_docs}
    f = {d["doc_id"]: json.dumps(d, sort_keys=True) for d in full_docs}
    return {"added": sorted(set(f) - set(b)), "updated": sorted(k for k in set(f) & set(b) if f[k] != b[k]),
            "newly_superseded": [], "withdrawn": [], "status_changed": [],
            "removed_from_records_not_withdrawn": sorted(set(b) - set(f))}


def write_delta_tree(full_dir: Path, delta_manifest: dict, release_json: dict, changes_json: dict, base_release_id: str, dst: Path) -> None:
    """The delta bundle tree (unsigned, no SHA256SUMS): the shipped component files, RELEASE.json (v1: delta true,
    previous_release_id = base, files = what ships), CHANGES.json and the delta KNOWLEDGE_RELEASE.json."""
    rmtree(dst)
    shipped = sorted({f["path"] for c in delta_manifest["components"] for f in c["files"]})
    for p in shipped:
        link_or_copy(full_dir / p, dst / p)
    ch = json.dumps(changes_json, indent=1).encode()
    (dst / "CHANGES.json").write_bytes(ch)
    rel = json.loads(json.dumps(release_json))
    keep = set(shipped)
    files = [dict(f) for f in rel["files"] if f["path"] in keep]
    files.append({"path": "CHANGES.json", "sha256": _sha(ch), "bytes": len(ch), "kind": "changes"})
    rel["files"] = sorted(files, key=lambda f: f["path"])
    rel["compatibility"] = dict(rel["compatibility"], delta=True, previous_release_id=base_release_id)
    (dst / "RELEASE.json").write_bytes(json.dumps(rel, indent=1, sort_keys=True).encode())
    (dst / KR).write_bytes(json.dumps(delta_manifest, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8"))


def apply(base_dir: Path, base_manifest: dict, delta_dir: Path, delta_manifest: dict, dst: Path) -> dict[str, str]:
    """Site-side application: base files, minus every FULL-replaced component's base files, plus every shipped file.
    Manifest files are not carried over. Returns {path: sha256} of the reconstructed state (written to `dst`)."""
    rmtree(dst)
    drop = set(MANIFEST_FILES)
    base_by_kind = {c["kind"]: c for c in base_manifest["components"]}
    for c in delta_manifest["components"]:
        if c["transport"] == "FULL" and c["kind"] in base_by_kind:
            drop |= {f["path"] for f in base_by_kind[c["kind"]]["files"]}
    for p in files_under(base_dir):
        r = p.relative_to(base_dir).as_posix()
        if r not in drop:
            link_or_copy(p, dst / r)
    for c in delta_manifest["components"]:
        for f in c["files"]:
            target = dst / f["path"]
            if target.exists():
                target.unlink()
            link_or_copy(delta_dir / f["path"], target)
    return {p.relative_to(dst).as_posix(): sha256_file(p) for p in files_under(dst)}
