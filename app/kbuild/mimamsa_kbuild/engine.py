"""Stage engine: chained stage manifests, the contract resume rule, atomic stage publication and the build record.

Layout under <out-root>/<spec.output_dir>/ (= build/<build_id>/):
    S0/ ... S9/            one directory per stage, holding its outputs and STAGE.json (build_stage_manifest)
    <sid>.partial/         a stage being built; discarded on restart (a killed stage leaves only this)
    BUILD_RECORD.json      timings, budget as applied, stages run or reused (NOT part of the release; not deterministic)

Resume (B02 spec section 3): `build_spec.stages_to_run` decides once per invocation: the first stage without a valid
COMPLETE manifest, with a changed input digest or with outputs failing re-hashing (or, for S1, sources that no longer
hash to the inventory) re-runs together with every later stage; earlier stages are reused. Later stages are not
skipped even when a re-run stage reproduces its outputs, because stages also read earlier stages' outputs (the S1
cache), which the chained input digest does not cover; a finer rule needs per-input digests (spec section 3).
Output paths in manifests are relative to <out-root> and start with spec.output_dir, so two builds of one spec in two
different out-roots produce byte-identical manifests.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path

from mimamsa_contract.c16 import build_spec as bs
from mimamsa_contract.c16 import canonical

from . import VERSION
from .errors import BuildRefused
from .fsutil import files_under, json_pretty, rmtree, sha256_file, write_atomic
from .netguard import no_network
from .resources import Budget, check_disk

STAGE_FILE = "STAGE.json"
STAGE_IDS = [s for s, _ in bs.STAGES]


@dataclass
class BuildContext:
    spec: dict
    out_root: Path
    mirror: Path | None
    dev_key_path: Path | None
    accel_tool: Path | None
    budget: Budget
    fetch_plan: Path | None = None    # real corpus: the fetch plan the spec pins (tool mimamsa_kbuild.fetch_plan)
    hf_cache: Path | None = None      # real corpus: content-addressed HF fetch cache (outside the repository)
    base_bundle: Path | None = None   # DELTA: the signed FULL base release the spec names
    hf_transport: tuple | None = None  # tests only: (lister, opener) standing in for the HF API (no network)
    record: dict = field(default_factory=dict)
    _cache: dict = field(default_factory=dict)

    @property
    def build_root(self) -> Path:
        return self.out_root / self.spec["output_dir"]

    def stage_dir(self, sid: str) -> Path:
        return self.build_root / sid

    def rel(self, sid: str, rel_in_stage: str) -> str:
        return f"{self.spec['output_dir']}/{sid}/{rel_in_stage}"

    def tools(self, sid: str) -> list[dict]:
        base = [dict(t) for t in self.spec["inputs"]["tools"]]
        extra = {"S5": [{"name": "mimamsa_importer", "version": "v1", "commit": None, "config_sha256": None}],
                 "S6": [{"name": "KBuildAccel", "version": VERSION, "commit": None, "config_sha256": None},
                        {"name": "knowledge_rows.derive_rows", "version": "2.1", "commit": None, "config_sha256": None}],
                 "S9": [{"name": "mimamsa_importer", "version": "v1", "commit": None, "config_sha256": None}]}
        return base + extra.get(sid, [])

    def stage_json(self, sid: str, name: str) -> dict:
        key = (sid, name)
        if key not in self._cache:
            self._cache[key] = json.loads((self.stage_dir(sid) / name).read_text(encoding="utf-8"))
        return self._cache[key]

    def forget(self, sid: str) -> None:
        for k in [k for k in self._cache if k[0] == sid]:
            del self._cache[k]


def read_manifest(path: Path) -> dict | None:
    try:
        from mimamsa_contract.bundle import strict_loads
        m = strict_loads(path.read_text(encoding="utf-8"))
        return m if isinstance(m, dict) else None
    except (OSError, ValueError):
        return None


def load_manifests(ctx: BuildContext) -> dict[str, dict]:
    out = {}
    for sid in STAGE_IDS:
        m = read_manifest(ctx.stage_dir(sid) / STAGE_FILE)
        if m is not None:
            out[sid] = m
    return out


def outputs_verified(ctx: BuildContext, sid: str, manifest: dict | None, fresh_checks: dict) -> bool:
    """Every listed output exists with its sha256 and size, nothing unlisted sits in the stage directory, and the
    stage's own freshness check (S1: the pinned sources still hash to the inventory) passes."""
    if manifest is None:
        return False
    d = ctx.stage_dir(sid)
    prefix = f"{ctx.spec['output_dir']}/{sid}/"
    listed = set()
    for o in manifest.get("outputs", []):
        p = o.get("path", "")
        if not p.startswith(prefix):
            return False
        f = ctx.out_root / p
        listed.add(p)
        try:
            if not f.is_file() or f.stat().st_size != o["bytes"] or sha256_file(f) != o["sha256"]:
                return False
        except OSError:
            return False
    on_disk = {ctx.rel(sid, p.relative_to(d).as_posix()) for p in files_under(d)} - {ctx.rel(sid, STAGE_FILE)}
    if on_disk != listed:
        return False
    check = fresh_checks.get(sid)
    return check(ctx) if check else True


def plan(ctx: BuildContext, manifests: dict, fresh_checks: dict, forced: set[str]) -> list[str]:
    usable = {k: v for k, v in manifests.items() if k not in forced}
    verified = {}
    previous_ok = True
    for sid in STAGE_IDS:   # verify lazily, in order: the first failure decides
        if not previous_ok:
            break
        verified[sid] = sid in usable and outputs_verified(ctx, sid, usable.get(sid), fresh_checks)
        previous_ok = verified[sid]
    return bs.stages_to_run(ctx.spec, usable, verified)


def _publish_stage(ctx: BuildContext, sid: str, work: Path, previous: dict | None) -> dict:
    outputs = [{"path": ctx.rel(sid, p.relative_to(work).as_posix()), "sha256": sha256_file(p), "bytes": p.stat().st_size}
               for p in files_under(work) if p.relative_to(work).as_posix() != STAGE_FILE]
    m = bs.make_stage_manifest(ctx.spec, sid, previous, outputs, ctx.tools(sid))
    issues = bs.stage_manifest_issues(m, ctx.spec, previous)
    if issues:
        raise BuildRefused("BUILD_MANIFEST_INVALID", "; ".join(f"{i.code}: {i.message}" for i in issues), sid)
    write_atomic(work / STAGE_FILE, json_pretty(m))
    final = ctx.stage_dir(sid)
    if final.exists():
        old = ctx.build_root / f".{sid}.old"
        rmtree(old)
        os.replace(final, old)
        rmtree(old)
    os.replace(work, final)
    ctx.forget(sid)
    return m


def run(ctx: BuildContext, stages: dict, fresh_checks: dict, *, from_stage: str | None = None) -> dict:
    """Run the build to completion. Returns {"ran": [...], "reused": [...], "manifests": {...}}."""
    ctx.build_root.mkdir(parents=True, exist_ok=True)
    for p in ctx.build_root.iterdir():          # killed stages leave only .partial content: discard it
        if p.name.endswith(".partial") or p.name.startswith(".tmp-") or (p.name.startswith(".") and p.name.endswith(".old")):
            rmtree(p)
    manifests = load_manifests(ctx)
    forced = set(STAGE_IDS[STAGE_IDS.index(from_stage):]) if from_stage else set()
    ran: list[str] = []
    timings: dict[str, dict] = {}
    todo = plan(ctx, manifests, fresh_checks, forced)   # decided once: the first invalid stage and EVERY later stage
    for sid in todo:
        previous = manifests.get(STAGE_IDS[STAGE_IDS.index(sid) - 1]) if sid != "S0" else None
        work = ctx.build_root / f"{sid}.partial"
        rmtree(work)
        work.mkdir(parents=True)
        t0 = time.perf_counter()
        if sid == bs.NETWORK_STAGE:
            stages[sid](ctx, work)
        else:
            with no_network():
                stages[sid](ctx, work)
        manifests[sid] = _publish_stage(ctx, sid, work, previous)
        ran.append(sid)
        timings[sid] = {"seconds": round(time.perf_counter() - t0, 3), **check_disk(ctx.budget, ctx.build_root, sid)}
    reused = [s for s in STAGE_IDS if s not in ran]
    chain_ok = all(not bs.stage_manifest_issues(manifests[s], ctx.spec, manifests.get(STAGE_IDS[i - 1]) if i else None)
                   for i, s in enumerate(STAGE_IDS))
    ctx.record.update(stages_ran=ran, stages_reused=reused, stage_timings=timings, chain_valid=chain_ok,
                      final_stage_manifest_sha256=canonical.record_sha256(manifests["S9"]))
    return {"ran": ran, "reused": reused, "manifests": manifests}
