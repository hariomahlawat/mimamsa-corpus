"""C16 Stage 3 S3-B: the central side of B04 (kind-specific checks) and B10 (model releases, DEVELOPMENT ONLY).

* `central_b04` runs the site's own .NET verifiers (KBuildVerify verify-accel: GRAPH digest, structural recheck and
  sampled rebuild parity; LEXICAL_INDEX manifest, quick_check, source digest, sampled postings re-derivation and sampled
  query parity) against the signed bundle on the S9 scratch site. Centrally the samples run at the FULL population (the
  build can afford it); this is recorded as such and is not a calibration. The contracts stay UNCALIBRATED.
* `build_vector_pack` embeds the corpus CENTRALLY with the kbuild budget (KBuildVerify vectors: batches, at most half
  the logical CPUs, below-normal priority, a content-keyed cache). The site never embeds the corpus.
* `build_model_release` assembles a DEVELOPMENT intelligence release (arch §2 row 3, §8.3, decision D3): the pinned
  embedder files, a FULL vector pack for a reference site's generation, an MKR-1 manifest with release_class
  INTELLIGENCE and signing_purpose `model`, SHA256SUMS signed with a DEVELOPMENT key under the `model` purpose, and a
  development model trust list. No operational trust list carries the `model` purpose (the v1 trust-list schema does not
  allow it; FG-MODEL-TRUST-PURPOSE stays OPEN), so production sites refuse these releases.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from mimamsa_contract.c16 import rules as c16rules
from mimamsa_contract.devbundle import trust_list_for

from . import KBUILD_DIR, VERSION
from .devkeys import dev_key_id, load_dev_key
from .errors import BuildRefused
from .fsutil import copy_file, files_under, json_pretty, rmtree, sha256_bytes, sha256_file, write_bytes
from .release import SIG, SUMS, sums_bytes

_BELOW_NORMAL = 0x4000


def default_verify_dll(artifacts: Path) -> Path:
    return Path(artifacts) / "bin" / "KBuildVerify" / "release" / "KBuildVerify.dll"


def build_verify_tool(artifacts: Path) -> Path:
    proj = KBUILD_DIR / "verify" / "KBuildVerify.csproj"
    p = subprocess.run(["dotnet", "build", str(proj), "-c", "Release", "--artifacts-path", str(artifacts), "-nologo", "-v", "q", "-m:2"],
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise BuildRefused("BUILD_TOOL_BUILD_FAILED", (p.stdout + p.stderr)[-800:])
    return default_verify_dll(artifacts)


def verify_tool_for(accel_tool: Path | None) -> Path | None:
    """KBuildVerify built next to KBuildAccel (same --artifacts-path), or MIMAMSA_KBUILD_VERIFY."""
    env = os.environ.get("MIMAMSA_KBUILD_VERIFY")
    if env and Path(env).is_file():
        return Path(env)
    if accel_tool is None:
        return None
    p = Path(accel_tool).parents[3] / "bin" / "KBuildVerify" / "release" / "KBuildVerify.dll" if len(Path(accel_tool).parents) > 3 else None
    return p if p is not None and p.is_file() else None


def _run(tool: Path, args: list[str], threads: int | None = None, timeout: int = 7200) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    if threads:
        env["DOTNET_PROCESSOR_COUNT"] = str(threads)
        env["OMP_NUM_THREADS"] = str(threads)
    flags = _BELOW_NORMAL if os.name == "nt" else 0
    return subprocess.run(["dotnet", str(tool), *args], env=env, creationflags=flags, capture_output=True, text=True, timeout=timeout)


def central_b04(ctx, site: Path, bundle: Path, sid: str) -> dict:
    """B04 GRAPH and LEXICAL_INDEX checks of the signed bundle on the scratch site (S9). Refuses the build on a failure."""
    tool = verify_tool_for(ctx.accel_tool)
    if tool is None:
        return {"status": "NOT_RUN", "why": "KBuildVerify not built next to KBuildAccel (python -m mimamsa_kbuild build-accel builds both)"}
    out = ctx.build_root / f".tmp-{sid}-b04.json"
    p = _run(tool, ["verify-accel", "--site", str(site), "--bundle", str(bundle), "--out", str(out)])
    if p.returncode not in (0, 2) or not out.is_file():
        raise BuildRefused("BUILD_TOOL_FAILED", f"KBuildVerify verify-accel exited {p.returncode}: {(p.stderr or '')[-400:]}", sid)
    ev = json.loads(out.read_text(encoding="utf-8"))
    out.unlink()
    if p.returncode == 2 or ev.get("status") != "VERIFIED":
        bad = [f"{k}: {i}" for k in ("GRAPH", "LEXICAL_INDEX") for i in (ev.get(k) or {}).get("issues", [])][:5]
        raise BuildRefused("BUILD_B04_CENTRAL", "the B04 kind-specific checks fail on the signed bundle: " + "; ".join(bad), sid)
    for k in ("GRAPH", "LEXICAL_INDEX"):
        for s in (ev.get(k) or {}).get("samples", {}).values():
            s["size_source"] = "CENTRAL_FULL_POPULATION (not a calibration; contracts stay UNCALIBRATED)"
    return ev


def build_vector_pack(tool: Path, site: Path, model_dir: Path, model_sha256: str, out: Path, *, generation: str | None = None,
                      cache: Path | None = None, threads: int | None = None, max_tokens: int = 256) -> dict:
    threads = max(1, min(threads or (os.cpu_count() or 2) // 2, max(1, (os.cpu_count() or 2) // 2)))
    args = ["vectors", "--site", str(site), "--model-dir", str(model_dir), "--model-sha", model_sha256, "--out", str(out),
            "--threads", str(threads), "--max-tokens", str(max_tokens)]
    if generation:
        args += ["--generation", generation]
    if cache:
        args += ["--cache", str(cache)]
    p = _run(tool, args, threads=threads, timeout=6 * 3600)
    if p.returncode != 0:
        raise BuildRefused("BUILD_VECTORS_FAILED", f"KBuildVerify vectors exited {p.returncode}: {(p.stderr or '')[-400:]}")
    return json.loads((out / "summary.json").read_text(encoding="utf-8"))


MODEL_FILES = ("onnx/model.onnx", "onnx/sentencepiece.bpe.model", "onnx/tokenizer.json", "onnx/config.json",
               "onnx/special_tokens_map.json", "onnx/tokenizer_config.json")


def _entry(rel: Path, root: Path) -> dict:
    p = root / rel
    return {"path": rel.as_posix(), "sha256": sha256_file(p), "bytes": p.stat().st_size}


def build_model_release(*, release_id: str, release_sequence: int, model_dir: Path, model_manifest: Path, pack_dir: Path,
                        out: Path, dev_key: Path, model_id: str, builder_commit: str | None = None) -> dict:
    """DEVELOPMENT intelligence release: pinned embedder files (each must hash to the committed MODEL_MANIFEST.json) and
    the central vector pack in `pack_dir` (KBuildVerify vectors output). Signed under purpose `model` with a DEVELOPMENT
    key; writes <out>/bundle, <out>/dev-model-trust/trust_list.json and <out>/SIGNING.json."""
    pins = json.loads(Path(model_manifest).read_text(encoding="utf-8"))["files"]
    summary = json.loads((pack_dir / "summary.json").read_text(encoding="utf-8"))
    msha = summary["model_sha256"]
    if pins["onnx/model.onnx"]["sha256"] != msha:
        raise BuildRefused("BUILD_MODEL_PIN", "the vector pack was not built with the pinned model")
    bundle = out / "bundle"
    rmtree(bundle)
    for f in MODEL_FILES:
        src = Path(model_dir) / f
        if sha256_file(src) != pins[f]["sha256"]:
            raise BuildRefused("BUILD_MODEL_PIN", f"{f} does not hash to the committed model manifest")
        copy_file(src, bundle / "models" / "embedder" / f)
    for n in (f"{msha}.mimvec", f"{msha}.params.json"):
        copy_file(pack_dir / n, bundle / "accelerators" / "vectors" / n)
    model_files = [_entry(Path("models/embedder") / f, bundle) for f in MODEL_FILES]
    vec_files = [_entry(Path("accelerators/vectors") / n, bundle) for n in (f"{msha}.mimvec", f"{msha}.params.json")]
    integrity = "".join(json.dumps({"path": e["path"], "sha256": e["sha256"], "bytes": e["bytes"]}, sort_keys=True) + "\n"
                        for e in model_files).encode()
    write_bytes(bundle / "registers" / "integrity-models.jsonl", integrity)
    integ = [_entry(Path("registers/integrity-models.jsonl"), bundle)]
    model_digest = sha256_bytes("\n".join(sorted(e["sha256"] for e in model_files)).encode("ascii"))
    tool = {"name": "KBuildVerify", "version": VERSION, "commit": builder_commit, "config_sha256": vec_files[1]["sha256"]}
    manifest = {
        "contract": "mimamsa-corpus-contract/2.0", "record_kind": "knowledge_release_manifest", "manifest_format": "MKR-1",
        "release_class": "INTELLIGENCE", "release_id": release_id, "release_sequence": release_sequence,
        "base": {"mode": "FULL", "base_release_id": None, "base_manifest_sha256": None},
        "corpus_generations": [{"corpus_generation_id": summary["generation_id"], "manifest_sha256": summary["source_digest"]}],
        "compatibility": {"knowledge_format": "1.0", "min_app_version": "0.16.0", "max_app_version": None,
                          "contracts": {"v1": "1.0.0", "corpus": "mimamsa-corpus-contract/2.0"}, "knowledge_schema_version": 1,
                          "graph_builder_version": "c15-graph-1", "index_format": "mimamsa-index-sqlite-1",
                          "text_store_format": "mimamsa-text-store/1", "vector_store_format": "MIMVEC01",
                          "required_models": [{"model_id": model_id, "role": "EMBEDDER", "sha256": msha}]},
        "components": [
            {"component_id": "model-embedder", "kind": "MODEL_FILE", "format": "onnx", "authority": "AUTHORITATIVE", "transport": "FULL",
             "files": model_files, "result_digest": model_digest, "result_count": 1, "source_digest": None, "builder": None,
             "model_sha256": msha, "disk_budget_bytes": None, "fallback": None, "verify": ["SHA256_EACH_FILE", "RESULT_DIGEST", "ONNX_LOAD_SELFTEST"]},
            {"component_id": "vectors-embedder", "kind": "VECTOR_PACK", "format": "MIMVEC01", "authority": "ACCELERATOR", "transport": "FULL",
             "files": vec_files, "result_digest": summary["result_digest"], "result_count": summary["entries"],
             "source_digest": summary["source_digest"], "builder": tool, "model_sha256": msha,
             "disk_budget_bytes": sum(e["bytes"] for e in vec_files), "fallback": "REFUSE_RELEASE",
             "verify": ["SHA256_EACH_FILE", "VECTOR_TRAILER", "VECTOR_KEYS_RECOMPUTED", "VECTOR_SPOT_REEMBED", "SOURCE_DIGEST_EQUALS_SITE"]},
            {"component_id": "integrity", "kind": "INTEGRITY_REGISTER", "format": "canonical-jsonl", "authority": "AUTHORITATIVE",
             "transport": "FULL", "files": integ, "result_digest": sha256_bytes(integrity), "result_count": len(model_files),
             "source_digest": None, "builder": None, "model_sha256": None, "disk_budget_bytes": None, "fallback": None,
             "verify": ["SHA256_EACH_FILE", "RESULT_DIGEST", "RESTRICTED_REGISTER"]},
        ],
        "capability": {"declared_service_level": "FULL", "semantic_search_promised": True,
                       "accounting": [{"kind": "MODEL_FILE", "status": "SHIPPED", "reason": "pinned embedder"},
                                      {"kind": "VECTOR_PACK", "status": "SHIPPED", "reason": "full vectors built centrally (the site never embeds the corpus)"},
                                      {"kind": "RULE_PACK", "status": "NOT_APPLICABLE", "reason": "no rule pack exists; refused at AUTH-LEDGER v0"},
                                      {"kind": "INTEGRITY_REGISTER", "status": "SHIPPED", "reason": "model hashes"}],
                       "pending_future_gates": ["FG-CALIBRATED-SAMPLES", "FG-DISK-PREFLIGHT", "FG-JOURNAL-DURABILITY", "FG-MODEL-TRUST-PURPOSE",
                                                "FG-REAL-RESTORE-TEST", "FG-RECEIPTS", "FG-ROW-LOADER", "FG-SITE-IMPORTER"]},
        "heavy_compute_on_site": {"ocr": "NONE", "embedding": "NONE", "graph_rebuild": "NONE"},
        "notes": "DEVELOPMENT intelligence release (C16 S3-B B10): development key, purpose model; production refuses it",
        "signing_purpose": "model"}
    issues = c16rules.record_issues(manifest)
    write_bytes(bundle / "KNOWLEDGE_RELEASE.json", json_pretty(manifest))
    sums = sums_bytes(bundle)
    write_bytes(bundle / SUMS, sums)
    sk, pub = load_dev_key(dev_key)
    write_bytes(bundle / SIG, sk.sign(sums))
    write_bytes(out / "dev-model-trust" / "trust_list.json", json_pretty(trust_list_for([(pub, "DEVELOPMENT", ["model"])])))
    signing = {"signing_mode": "DEVELOPMENT", "purpose": "model", "key_id": dev_key_id(pub), "holder": "DEVELOPMENT",
               "signed_file": SUMS, "signed_file_sha256": sha256_bytes(sums),
               "contract_issues": [f"{i.code}: {i.message}" for i in issues],
               "note": ("development key under the separate `model` purpose (D3). The development trust list naming it is NOT a "
                        "v1-schema trust list (the v1 schema has no `model` purpose): it can never be installed as an operational "
                        "trust list. FG-MODEL-TRUST-PURPOSE stays OPEN; production sites refuse intelligence releases.")}
    write_bytes(out / "SIGNING.json", json_pretty(signing))
    return {"bundle": str(bundle), "files": len(files_under(bundle)), **signing}
