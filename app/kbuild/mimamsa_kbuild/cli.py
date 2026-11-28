"""Command line.

    python -m mimamsa_kbuild build --spec <spec.json> --out-root <dir> [--source-mirror <dir>] [--dev-key <file>]
                                   [--accel-tool <KBuildAccel.dll>] [--from <stage>] [--dry-run]
    python -m mimamsa_kbuild prepare-fixture-mirror --out <dir>      CP-1 fixture sources as an offline HF mirror
    python -m mimamsa_kbuild build-accel --artifacts <dir>           build the .NET S6 helper (local NuGet cache)
    python -m mimamsa_kbuild budget --spec <spec.json>               apply the resource budget and print what the OS reports
    python -m mimamsa_kbuild measure-host                            measured CPUs/memory for the spec's resources block
    python -m mimamsa_kbuild build-vectors --site <site> --model-dir <dir> --model-sha <sha> --out <dir> [--cache <file>]
                                   [--generation <id>] [--threads N] [--tool <KBuildVerify.dll>]
                                   central vector pack (C16 S3-B; the site never embeds the corpus)
    python -m mimamsa_kbuild build-model-release --pack <dir> --model-dir <dir> --release-id <id> --release-sequence <n>
                                   --out <dir> --dev-key <file> [--model-manifest <json>] [--model-id <label>]
                                   DEVELOPMENT intelligence release signed under purpose "model" (B10; production refuses it)

Outputs go under --out-root (never into the repository). Exit codes: 0 built, 2 refused, 1 usage or internal error.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from . import KBUILD_DIR, VERSION
from .errors import BuildRefused
from .fsutil import json_pretty, write_atomic


def _load_spec(path: Path) -> dict:
    from mimamsa_contract.bundle import strict_loads
    return strict_loads(Path(path).read_text(encoding="utf-8"))


def default_accel_dll(artifacts: Path) -> Path:
    return Path(artifacts) / "bin" / "KBuildAccel" / "release" / "KBuildAccel.dll"


def build_accel(artifacts: Path) -> Path:
    proj = KBUILD_DIR / "accel" / "KBuildAccel.csproj"
    p = subprocess.run(["dotnet", "build", str(proj), "-c", "Release", "--artifacts-path", str(artifacts), "-nologo", "-v", "q"],
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise BuildRefused("BUILD_TOOL_BUILD_FAILED", (p.stdout + p.stderr)[-800:])
    from .verify import build_verify_tool   # C16 S3-B: KBuildVerify (central B04 checks, central vector packs) beside it
    build_verify_tool(artifacts)
    return default_accel_dll(artifacts)


def make_context(spec: dict, out_root: Path, mirror, dev_key, accel, *, apply: bool = True):
    from .engine import BuildContext
    from .resources import apply_budget, effective_budget, measure_host
    budget = effective_budget(spec, measure_host(out_root))
    if apply:
        apply_budget(budget)
    return BuildContext(spec=spec, out_root=Path(out_root).resolve(), mirror=Path(mirror).resolve() if mirror else None,
                        dev_key_path=Path(dev_key).resolve() if dev_key else None, accel_tool=Path(accel).resolve() if accel else None,
                        budget=budget)


def run_build(spec: dict, out_root: Path, *, mirror=None, dev_key=None, accel=None, from_stage=None, apply_budget: bool = True) -> dict:
    """Run (or resume) a build. Raises BuildRefused. Returns the engine result plus the build record path."""
    from mimamsa_contract.c16 import build_spec as bs

    from . import engine, stages
    ctx = make_context(spec, out_root, mirror, dev_key, accel, apply=apply_budget)
    issues = bs.spec_issues(spec)   # fail before anything is written (S0 re-checks and records)
    if issues:
        raise BuildRefused(issues[0].code, issues[0].message, "S0", [{"code": i.code, "message": i.message} for i in issues])
    t0 = time.perf_counter()
    ctx.record.update(record_kind="kbuild_build_record", tool={"name": "mimamsa_kbuild", "version": VERSION},
                      spec_sha256=bs.spec_sha256(spec), build_id=spec["build_id"], release_id=spec["release"]["release_id"],
                      inputs=spec["inputs"], budget=ctx.budget.as_dict(), from_stage=from_stage)
    try:
        res = engine.run(ctx, stages.STAGES, stages.FRESH, from_stage=from_stage)
        ctx.record.update(outcome="BUILT", seconds=round(time.perf_counter() - t0, 3))
        return {**res, "record": str(ctx.build_root / "BUILD_RECORD.json"), "context": ctx}
    except BuildRefused as exc:
        ctx.record.update(outcome="REFUSED", refusal=exc.as_dict(), seconds=round(time.perf_counter() - t0, 3))
        raise
    finally:
        ctx.build_root.mkdir(parents=True, exist_ok=True)
        write_atomic(ctx.build_root / "BUILD_RECORD.json", json_pretty(ctx.record))


def dry_run(spec: dict, out_root: Path, *, mirror=None, dev_key=None, accel=None) -> dict:
    """What would be fetched (counts per source) and which stages would run. Writes nothing."""
    from mimamsa_contract.c16 import build_spec as bs

    from . import engine, stages
    ctx = make_context(spec, out_root, mirror, dev_key, accel, apply=False)
    issues = [{"code": i.code, "message": i.message} for i in bs.spec_issues(spec)] + stages.spec_support_issues(spec)
    out = {"build_id": spec["build_id"], "spec_sha256": bs.spec_sha256(spec), "spec_issues": issues, "writes": "nothing (dry run)"}
    if issues:
        return out
    try:
        inv, _ = stages.collect_inventory(ctx, dry_run=True)
        out["sources"] = [{"repo": h["repo"], "revision": h["revision"], "files": len(h["files"]), "bytes": sum(f["bytes"] for f in h["files"]),
                           "by_area": _areas(h["files"])} for h in inv["hf"]]
        out["producer_generations"] = [{"corpus_generation_id": g["corpus_generation_id"], "files": len(g["declared_files"]),
                                        "receipts": len(g["receipts"])} for g in inv["producer_generations"]]
        out["local_inputs"] = len(inv["local_inputs"])
    except BuildRefused as exc:
        out["sources_refused"] = exc.as_dict()
    manifests = engine.load_manifests(ctx) if ctx.build_root.exists() else {}
    out["stages_to_run"] = engine.plan(ctx, manifests, stages.FRESH, set()) if not out.get("sources_refused") else [s for s, _ in bs.STAGES]
    out["budget"] = ctx.budget.as_dict()
    return out


def _areas(files):
    areas: dict[str, int] = {}
    for f in files:
        parts = f["path"].split("/")
        key = "/".join(parts[:2]) if parts[0] in ("v1", "exchanges") else parts[0]
        areas[key] = areas.get(key, 0) + 1
    return dict(sorted(areas.items()))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="mimamsa_kbuild")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--spec", type=Path, required=True)
    b.add_argument("--out-root", type=Path, required=True)
    b.add_argument("--source-mirror", type=Path)
    b.add_argument("--dev-key", type=Path, help="development Ed25519 seed (hex); created if absent. Default <out-root>/dev-keys/release-dev.key")
    b.add_argument("--accel-tool", type=Path, help="KBuildAccel.dll; default <out-root>/tools/dotnet build (built on first use)")
    b.add_argument("--from", dest="from_stage", choices=[f"S{i}" for i in range(10)])
    b.add_argument("--dry-run", action="store_true")
    m = sub.add_parser("prepare-fixture-mirror")
    m.add_argument("--out", type=Path, required=True)
    m.add_argument("--exchange", choices=["positive", "v2_1", "cp1"], default="positive",
                   help="producer exchange: the 2.0 positive fixture (cp1-fixture spec) or the CP-1 slice exchange (cp1-slice spec)")
    t = sub.add_parser("build-accel")
    t.add_argument("--artifacts", type=Path, required=True)
    g = sub.add_parser("budget")
    g.add_argument("--spec", type=Path, required=True)
    sub.add_parser("measure-host")
    v = sub.add_parser("build-vectors")
    for n in ("--site", "--model-dir", "--out"):
        v.add_argument(n, type=Path, required=True)
    v.add_argument("--model-sha", required=True)
    v.add_argument("--cache", type=Path)
    v.add_argument("--generation")
    v.add_argument("--threads", type=int)
    v.add_argument("--tool", type=Path)
    r = sub.add_parser("build-model-release")
    for n in ("--pack", "--model-dir", "--out", "--dev-key"):
        r.add_argument(n, type=Path, required=True)
    r.add_argument("--model-manifest", type=Path, default=KBUILD_DIR.parent / "b1" / "hybrid" / "MODEL_MANIFEST.json")
    r.add_argument("--release-id", required=True)
    r.add_argument("--release-sequence", type=int, required=True)
    r.add_argument("--model-id", default="intfloat/multilingual-e5-small@614241f6")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "prepare-fixture-mirror":
            from .fixture_mirror import prepare
            print(prepare(a.out.resolve(), exchange=a.exchange))
            return 0
        if a.cmd == "build-accel":
            print(build_accel(a.artifacts.resolve()))
            return 0
        if a.cmd == "build-vectors":
            from .verify import build_vector_pack, build_verify_tool, default_verify_dll
            tool = a.tool or default_verify_dll(a.out.resolve().parent / "tools" / "dotnet")
            if not Path(tool).is_file():
                tool = build_verify_tool(a.out.resolve().parent / "tools" / "dotnet")
            print(json.dumps(build_vector_pack(Path(tool), a.site.resolve(), a.model_dir.resolve(), a.model_sha, a.out.resolve(),
                                               generation=a.generation, cache=a.cache, threads=a.threads), indent=1))
            return 0
        if a.cmd == "build-model-release":
            from .devkeys import ensure_dev_key
            from .verify import build_model_release
            ensure_dev_key(a.dev_key)
            print(json.dumps(build_model_release(release_id=a.release_id, release_sequence=a.release_sequence, model_dir=a.model_dir.resolve(),
                                                 model_manifest=a.model_manifest, pack_dir=a.pack.resolve(), out=a.out.resolve(),
                                                 dev_key=a.dev_key, model_id=a.model_id), indent=1))
            return 0
        if a.cmd == "measure-host":
            from .resources import measure_host
            h = measure_host()
            print(json.dumps({"measured_logical_cpus": h.logical_cpus, "measured_memory_bytes": h.memory_bytes,
                              "suggested_shared_host_max_workers": max(1, h.logical_cpus // 2),
                              "suggested_shared_host_max_memory_bytes": h.memory_bytes // 2}, indent=1))
            return 0
        if a.cmd == "budget":
            from .resources import apply_budget, effective_budget, measure_host
            bud = apply_budget(effective_budget(_load_spec(a.spec), measure_host()))
            print(json.dumps(bud.as_dict(), indent=1, sort_keys=True))
            return 0
        spec = _load_spec(a.spec)
        out_root = a.out_root.resolve()
        dev_key = a.dev_key or out_root / "dev-keys" / "release-dev.key"
        accel = a.accel_tool
        if a.dry_run:
            print(json.dumps(dry_run(spec, out_root, mirror=a.source_mirror, dev_key=dev_key, accel=accel), indent=1, sort_keys=True))
            return 0
        from .devkeys import ensure_dev_key
        ensure_dev_key(dev_key)
        if accel is None:
            accel = default_accel_dll(out_root / "tools" / "dotnet")
            if not accel.is_file():
                build_accel(out_root / "tools" / "dotnet")
        res = run_build(spec, out_root, mirror=a.source_mirror, dev_key=dev_key, accel=accel, from_stage=a.from_stage)
        print(json.dumps({"outcome": "BUILT", "ran": res["ran"], "reused": res["reused"], "record": res["record"],
                          "bundle": str(res["context"].stage_dir("S8") / "bundle")}, indent=1))
        return 0
    except BuildRefused as exc:
        print(json.dumps({"outcome": "REFUSED", **exc.as_dict()}, indent=1), file=sys.stderr)
        return 2
