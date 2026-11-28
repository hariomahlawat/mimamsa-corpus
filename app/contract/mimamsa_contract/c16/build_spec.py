"""B02 central build spec (contract 2.1 interface): spec rules, stage-manifest chain and the resume decision."""
from __future__ import annotations

import hashlib

from ..issues import Issue
from . import canonical
from .schemas import schema_errors

STAGES = [("S0", "spec"), ("S1", "fetch"), ("S2", "validate"), ("S3", "text"), ("S4", "bundle"),
          ("S5", "ref-import"), ("S6", "accelerate"), ("S7", "assemble"), ("S8", "sign"), ("S9", "verify")]
NETWORK_STAGE = "S1"


def _e(code, msg, where=""):
    return Issue(code, msg, where)


def spec_sha256(spec: dict) -> str:
    return canonical.record_sha256(spec)


def spec_issues(spec) -> list[Issue]:
    issues = [_e("SCHEMA", m, "mkr_build_spec") for m in schema_errors(spec)]
    if issues:
        return issues
    got = [(s["stage_id"], s["name"]) for s in spec["stages"]]
    if got != STAGES:
        issues.append(_e("BUILD_STAGE_ORDER", "stages must be exactly S0..S9 in order with their names"))
    for s in spec["stages"]:
        if s["network"] and s["stage_id"] != NETWORK_STAGE:
            issues.append(_e("BUILD_NETWORK", "only the fetch stage (S1) may use the network", s["stage_id"]))
        if s["max_workers"] > spec["resources"]["max_workers"]:
            issues.append(_e("BUILD_RESOURCES", "a stage may not exceed the build-wide worker budget", s["stage_id"]))
    r = spec["resources"]
    if r["shared_host"]:
        if r["max_workers"] > max(1, r["measured_logical_cpus"] // 2):
            issues.append(_e("BUILD_RESOURCES", "on a shared host workers are bounded to half the measured logical CPUs"))
        if r["cpu_priority"] == "NORMAL" or r["io_priority"] == "NORMAL":
            issues.append(_e("BUILD_RESOURCES", "on a shared host CPU and I/O priority must be below normal"))
        if r["max_memory_bytes"] > r["measured_memory_bytes"] // 2:
            issues.append(_e("BUILD_RESOURCES", "on a shared host the build may use at most half the measured memory"))
    rel = spec["release"]
    if (rel["base_mode"] == "DELTA") != (rel["base_release_id"] is not None):
        issues.append(_e("BUILD_RELEASE", "a DELTA names its base release and a FULL build names none"))
    return issues


def input_digest(spec: dict, stage_id: str, previous_output_digest: str | None) -> str:
    return hashlib.sha256(canonical.canonical_bytes([spec_sha256(spec), stage_id, previous_output_digest])).hexdigest()


def output_digest(outputs: list[dict]) -> str:
    return hashlib.sha256(canonical.canonical_bytes(sorted(([o["path"], o["sha256"], o["bytes"]] for o in outputs)))).hexdigest()


def stage_manifest_issues(m, spec: dict, previous: dict | None) -> list[Issue]:
    issues = [_e("SCHEMA", x, "build_stage_manifest") for x in schema_errors(m)]
    if issues:
        return issues
    if m["spec_sha256"] != spec_sha256(spec) or m["build_id"] != spec["build_id"]:
        issues.append(_e("BUILD_MANIFEST_SPEC", "stage manifest belongs to another spec", m["stage_id"]))
    prev_sha = canonical.record_sha256(previous) if previous else None
    if m["previous_stage_manifest_sha256"] != prev_sha:
        issues.append(_e("BUILD_MANIFEST_CHAIN", "stage manifest does not chain to the previous stage", m["stage_id"]))
    if m["input_digest"] != input_digest(spec, m["stage_id"], previous["output_digest"] if previous else None):
        issues.append(_e("BUILD_MANIFEST_INPUT", "input digest does not follow from the spec and the previous stage", m["stage_id"]))
    if m["output_digest"] != output_digest(m["outputs"]):
        issues.append(_e("BUILD_MANIFEST_OUTPUT", "output digest does not follow from the outputs", m["stage_id"]))
    return issues


def stages_to_run(spec: dict, manifests: dict[str, dict], outputs_verified: dict[str, bool]) -> list[str]:
    """Resume rule: the first stage without a valid COMPLETE manifest, with a changed input digest, or whose outputs
    fail re-hashing, and every stage after it, rerun. Everything before it is reused."""
    previous = None
    for i, (sid, _) in enumerate(STAGES):
        m = manifests.get(sid)
        if m is None or stage_manifest_issues(m, spec, previous) or not outputs_verified.get(sid, False):
            return [s for s, _ in STAGES[i:]]
        previous = m
    return []


def make_stage_manifest(spec: dict, stage_id: str, previous: dict | None, outputs: list[dict], tools: list[dict]) -> dict:
    return {"contract": "mimamsa-corpus-contract/2.1", "record_kind": "build_stage_manifest", "build_id": spec["build_id"],
            "stage_id": stage_id, "spec_sha256": spec_sha256(spec),
            "previous_stage_manifest_sha256": canonical.record_sha256(previous) if previous else None,
            "input_digest": input_digest(spec, stage_id, previous["output_digest"] if previous else None),
            "outputs": outputs, "output_digest": output_digest(outputs), "tools": tools,
            "network_used": stage_id == NETWORK_STAGE, "status": "COMPLETE"}
