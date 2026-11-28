"""Command line.

    python -m mimamsa_kbuild build --spec <spec.json> --out-root <dir> [--source-mirror <dir>] [--dev-key <file>]
                                   [--accel-tool <KBuildAccel.dll>] [--from <stage>] [--dry-run]
    python -m mimamsa_kbuild prepare-fixture-mirror --out <dir>      CP-1 fixture sources as an offline HF mirror
    python -m mimamsa_kbuild build-accel --artifacts <dir>           build the .NET S6 helper (local NuGet cache)
    python -m mimamsa_kbuild budget --spec <spec.json>               apply the resource budget and print what the OS reports
    python -m mimamsa_kbuild measure-host                            measured CPUs/memory for the spec's resources block

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
    return default_accel_dll(artifacts)


def make_context(spec: dict, out_root: Path, mirror, dev_key, accel, *, apply: bool = True, fetch_plan=None, hf_cache=None,
                 base_bundle=None, hf_transport=None):
    from .engine import BuildContext
    from .resources import apply_budget, effective_budget, measure_host
    budget = effective_budget(spec, measure_host(out_root))
    if apply:
        apply_budget(budget)
    res = lambda p: Path(p).resolve() if p else None  # noqa: E731
    return BuildContext(spec=spec, out_root=Path(out_root).resolve(), mirror=res(mirror), dev_key_path=res(dev_key),
                        accel_tool=res(accel), budget=budget, fetch_plan=res(fetch_plan), hf_cache=res(hf_cache),
                        base_bundle=res(base_bundle), hf_transport=hf_transport)


def run_build(spec: dict, out_root: Path, *, mirror=None, dev_key=None, accel=None, from_stage=None, apply_budget: bool = True,
              fetch_plan=None, hf_cache=None, base_bundle=None, hf_transport=None) -> dict:
    """Run (or resume) a build. Raises BuildRefused. Returns the engine result plus the build record path."""
    from mimamsa_contract.c16 import build_spec as bs

    from . import engine, stages
    ctx = make_context(spec, out_root, mirror, dev_key, accel, apply=apply_budget, fetch_plan=fetch_plan, hf_cache=hf_cache,
                       base_bundle=base_bundle, hf_transport=hf_transport)
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
        stats = ctx.record.pop("_fetch_stats", None)
        if stats is not None:
            ctx.record["fetch"] = stats.as_dict()
        ctx.record["resources_observed"] = _observed(ctx)
        ctx.build_root.mkdir(parents=True, exist_ok=True)
        write_atomic(ctx.build_root / "BUILD_RECORD.json", json_pretty(ctx.record))


def _observed(ctx) -> dict:
    """Resource use observed for this process (shared-host record, SG-6): peak working set and CPU seconds."""
    out = {}
    try:
        import psutil   # optional
        p = psutil.Process()
        mi = p.memory_info()
        out.update(peak_working_set_bytes=getattr(mi, "peak_wset", None) or mi.rss, cpu_seconds=round(sum(p.cpu_times()[:2]), 1))
    except Exception:
        try:
            import ctypes
            from ctypes import wintypes

            class PMC(ctypes.Structure):
                _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD), ("PeakWorkingSetSize", ctypes.c_size_t),
                            ("WorkingSetSize", ctypes.c_size_t), ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                            ("QuotaPagedPoolUsage", ctypes.c_size_t), ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                            ("QuotaNonPagedPoolUsage", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
            pmc = PMC()
            pmc.cb = ctypes.sizeof(PMC)
            h = ctypes.windll.kernel32.GetCurrentProcess()
            if ctypes.windll.psapi.GetProcessMemoryInfo(h, ctypes.byref(pmc), pmc.cb):
                out["peak_working_set_bytes"] = int(pmc.PeakWorkingSetSize)
        except Exception:
            pass
    try:
        import time as _t
        out.setdefault("cpu_seconds", round(_t.process_time(), 1))
    except Exception:
        pass
    try:
        from .fsutil import files_under
        out["build_root_bytes"] = sum(p.stat().st_size for p in files_under(ctx.build_root)) if ctx.build_root.exists() else 0
    except Exception:
        pass
    return out


def dry_run(spec: dict, out_root: Path, *, mirror=None, dev_key=None, accel=None, fetch_plan=None, hf_cache=None, base_bundle=None) -> dict:
    """What would be fetched (counts per source) and which stages would run. Writes nothing and, for a real-corpus
    build, uses no network (counts come from the pinned plan)."""
    from mimamsa_contract.c16 import build_spec as bs

    from . import engine, real_corpus, stages
    ctx = make_context(spec, out_root, mirror, dev_key, accel, apply=False, fetch_plan=fetch_plan, hf_cache=hf_cache, base_bundle=base_bundle)
    issues = [{"code": i.code, "message": i.message} for i in bs.spec_issues(spec)] + stages.spec_support_issues(spec)
    out = {"build_id": spec["build_id"], "spec_sha256": bs.spec_sha256(spec), "spec_issues": issues, "writes": "nothing (dry run)"}
    if issues:
        return out
    plan, _ = real_corpus.load_plan(ctx.fetch_plan, spec)
    if plan is not None:
        out["sources"] = real_corpus.plan_counts(plan)
        out["producer_generations"] = [{"corpus_generation_id": g["corpus_generation_id"], "hf_revision": g["hf_revision"]}
                                       for g in spec["inputs"]["producer_generations"]]
        out["network"] = "none in a dry run; S1 fetches only the pinned revisions above"
        manifests = engine.load_manifests(ctx) if ctx.build_root.exists() else {}
        out["stages_to_run"] = engine.plan(ctx, manifests, stages.FRESH, set())
        out["budget"] = ctx.budget.as_dict()
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


def stage_import(bundle: Path, trust: Path, site: Path) -> dict:
    """B01 stage_only import of a signed development bundle into an isolated site: the generation is written and
    verified but ACTIVE is not switched (activation is the journal's job, B06). Refuses an existing site directory."""
    from mimamsa_contract.restricted import load_register
    from mimamsa_contract.trust import parse_trust_list
    from mimamsa_importer import configure_site, import_release
    site = Path(site).resolve()
    if site.exists() and any(site.iterdir()):
        raise SystemExit("stage-import needs a new, empty, isolated site directory")
    t0 = time.perf_counter()
    configure_site(site, exclusion_channel="none")
    res = import_release(Path(bundle).resolve(), site, trust_list=parse_trust_list(json.loads(Path(trust).read_text(encoding="utf-8"))),
                         mode="development", register=load_register(), stage_only=True)
    c16 = res.c16 or {}
    gens = sorted(p.name for p in (site / "generations").iterdir()) if (site / "generations").is_dir() else []
    return {"stage_only": True, "staged": getattr(res, "staged", None), "activated": res.activated, "active_file_present": (site / "ACTIVE").exists(),
            "refused_reasons": res.refused_reasons, "release_id": res.release_id, "generations": gens,
            "verified": {k: len(v) for k, v in sorted(res.verified.items())},
            "unresolved_by_kind": {k: sum(1 for u in res.unresolved if u["kind"] == k) for k in sorted({u["kind"] for u in res.unresolved})},
            "c16_active": c16.get("active"), "c16_codes": c16.get("codes"), "accounting_digests": c16.get("accounting_digests"),
            "seconds": round(time.perf_counter() - t0, 1)}


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
    b.add_argument("--fetch-plan", type=Path, help="real corpus: the fetch plan the spec pins (tool mimamsa_kbuild.fetch_plan)")
    b.add_argument("--hf-cache", type=Path, help="real corpus: content-addressed HF fetch cache, e.g. E:/Mimamsa-Data/c16s3a/cache")
    b.add_argument("--base-bundle", type=Path, help="DELTA: the signed FULL base release (its S8/bundle)")
    m = sub.add_parser("prepare-fixture-mirror")
    m.add_argument("--out", type=Path, required=True)
    m.add_argument("--exchange", choices=["positive", "v2_1", "cp1"], default="positive",
                   help="producer exchange: the 2.0 positive fixture (cp1-fixture spec) or the CP-1 slice exchange (cp1-slice spec)")
    t = sub.add_parser("build-accel")
    t.add_argument("--artifacts", type=Path, required=True)
    g = sub.add_parser("budget")
    g.add_argument("--spec", type=Path, required=True)
    sub.add_parser("measure-host")
    si = sub.add_parser("stage-import", help="import a signed bundle into an ISOLATED site with B01 stage_only (ACTIVE untouched)")
    si.add_argument("--bundle", type=Path, required=True)
    si.add_argument("--trust", type=Path, required=True, help="the build's development trust list (S8/dev-trust/trust_list.json)")
    si.add_argument("--site", type=Path, required=True, help="a NEW, isolated site directory (never an operational site)")
    a = ap.parse_args(argv)
    if a.cmd == "stage-import":
        print(json.dumps(stage_import(a.bundle, a.trust, a.site), indent=1, sort_keys=True))
        return 0
    try:
        if a.cmd == "prepare-fixture-mirror":
            from .fixture_mirror import prepare
            print(prepare(a.out.resolve(), exchange=a.exchange))
            return 0
        if a.cmd == "build-accel":
            print(build_accel(a.artifacts.resolve()))
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
            print(json.dumps(dry_run(spec, out_root, mirror=a.source_mirror, dev_key=dev_key, accel=accel, fetch_plan=a.fetch_plan,
                                    hf_cache=a.hf_cache, base_bundle=a.base_bundle), indent=1, sort_keys=True))
            return 0
        from .devkeys import ensure_dev_key
        ensure_dev_key(dev_key)
        if accel is None:
            accel = default_accel_dll(out_root / "tools" / "dotnet")
            if not accel.is_file():
                build_accel(out_root / "tools" / "dotnet")
        res = run_build(spec, out_root, mirror=a.source_mirror, dev_key=dev_key, accel=accel, from_stage=a.from_stage,
                        fetch_plan=a.fetch_plan, hf_cache=a.hf_cache, base_bundle=a.base_bundle)
        print(json.dumps({"outcome": "BUILT", "ran": res["ran"], "reused": res["reused"], "record": res["record"],
                          "bundle": str(res["context"].stage_dir("S8") / "bundle")}, indent=1))
        return 0
    except BuildRefused as exc:
        print(json.dumps({"outcome": "REFUSED", **exc.as_dict()}, indent=1), file=sys.stderr)
        return 2
