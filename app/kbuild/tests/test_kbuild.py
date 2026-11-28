"""B02 central build pipeline skeleton: stage chaining and resume, determinism, refusals, the degraded release under
the contract rules, network confinement and the shared-host budget."""
from __future__ import annotations

import copy
import hashlib
import json
import socket
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import KBUILD, SPEC, copy_build, load_spec

from mimamsa_contract.bundle import parse_sums, validate_bundle
from mimamsa_contract.c16 import accounting, digests, knowledge_rows
from mimamsa_contract.c16 import build_spec as bs
from mimamsa_contract.c16 import rules as c16rules
from mimamsa_contract.restricted import load_register
from mimamsa_contract.trust import parse_trust_list
from mimamsa_kbuild import REPO, engine, release, stages
from mimamsa_kbuild.cli import dry_run, run_build
from mimamsa_kbuild.errors import BuildRefused
from mimamsa_kbuild.fixture_mirror import GENERATION_SHA256, prepare, revision_root
from mimamsa_kbuild.netguard import NetworkForbidden, no_network

ALL = [f"S{i}" for i in range(10)]


def _tree(root: Path) -> dict[str, str]:
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file() and p.name != "BUILD_RECORD.json"}


def _build(spec, out, mirror, dev_key, accel, **kw):
    return run_build(spec, out, mirror=mirror, dev_key=dev_key, accel=accel, apply_budget=False, **kw)


# ------------------------------------------------------------------ spec (S0)

def test_cp1_spec_is_valid_and_supported():
    spec = load_spec()
    assert bs.spec_issues(spec) == []
    assert stages.spec_support_issues(spec) == []
    assert spec["resources"]["max_workers"] <= spec["resources"]["measured_logical_cpus"] // 2
    assert spec["resources"]["max_memory_bytes"] <= spec["resources"]["measured_memory_bytes"] // 2


@pytest.mark.parametrize("mutate,code", [
    (lambda s: s["stages"][3].update(network=True), "BUILD_NETWORK"),
    (lambda s: s["resources"].update(max_workers=7), "BUILD_RESOURCES"),
    (lambda s: s["resources"].update(cpu_priority="NORMAL"), "BUILD_RESOURCES"),
    (lambda s: s["resources"].update(max_memory_bytes=s["resources"]["measured_memory_bytes"]), "BUILD_RESOURCES"),
    (lambda s: s["stages"].reverse(), "BUILD_STAGE_ORDER"),
    (lambda s: s.pop("pinned_build_time"), "SCHEMA"),
])
def test_invalid_spec_refused_before_anything_is_written(tmp_path, mutate, code):
    spec = load_spec()
    mutate(spec)
    with pytest.raises(BuildRefused) as e:
        run_build(spec, tmp_path, apply_budget=False)
    assert e.value.code == code
    assert not any((tmp_path / spec.get("output_dir", "build")).glob("S*"))


def test_skeleton_refuses_what_it_does_not_build():
    """Stage 3 builds DELTA releases and several generations; PRODUCTION signing stays refused (Stage 4, OG-2)."""
    spec = load_spec()
    spec["release"].update(base_mode="DELTA", base_release_id="R15-cp1-fixture-20261126-00000001")
    spec["release"]["signing_mode"] = "PRODUCTION"
    codes = [i["code"] for i in stages.spec_support_issues(spec)]
    assert codes == ["BUILD_UNSUPPORTED"]
    spec["inputs"]["producer_generations"].append(dict(spec["inputs"]["producer_generations"][0]))
    assert "BUILD_GENERATIONS_INCOMPATIBLE" in {i["code"] for i in stages.spec_support_issues(spec)}


def test_dry_run_writes_nothing(tmp_path, mirror):
    out = dry_run(load_spec(), tmp_path / "out", mirror=mirror, dev_key=tmp_path / "absent.key")
    assert out["stages_to_run"] == ALL and out["spec_issues"] == []
    assert out["sources"][0]["by_area"]["v1/originals"] == 12
    assert out["producer_generations"][0]["files"] == 6
    assert not (tmp_path / "out").exists() and not (tmp_path / "absent.key").exists()


# ------------------------------------------------------------------ end to end on fixtures

def test_cp1_build_end_to_end(built):
    root, res = built["root"], built["res"]
    assert res["ran"] == ALL and res["reused"] == []
    spec = load_spec()
    prev = None
    for sid in ALL:   # every manifest chains, follows from the spec and its outputs, and only S1 may use the network
        m = json.loads((root / sid / "STAGE.json").read_text(encoding="utf-8"))
        assert bs.stage_manifest_issues(m, spec, prev) == [], sid
        assert m["network_used"] == (sid == "S1")
        prev = m
    inv = json.loads((root / "S1" / "INVENTORY.json").read_text(encoding="utf-8"))
    assert inv["mode"] == "OFFLINE_MIRROR" and inv["network_used"] is False
    verify = json.loads((root / "S9" / "VERIFY.json").read_text(encoding="utf-8"))
    assert verify["expected_activation"]["result"] == "ACTIVE_DEGRADED"
    assert verify["expected_activation"]["service_level"] == "DEGRADED_LEXICAL_ONLY"
    assert verify["expected_activation"]["site_embedding"] == "NEVER" and verify["embedder_calls"] == 0
    assert verify["checks"]["production_mode_refuses_dev_signature"] == ["SIGNATURE_DEV_KEY_IN_PRODUCTION"]
    rec = json.loads((root / "BUILD_RECORD.json").read_text(encoding="utf-8"))
    assert rec["outcome"] == "BUILT" and rec["chain_valid"] is True and rec["inputs"] == spec["inputs"]


def test_degraded_release_validates_under_the_contract_rules(built):
    bundle = built["root"] / "S8" / "bundle"
    m = json.loads((bundle / "KNOWLEDGE_RELEASE.json").read_text(encoding="utf-8"))
    sums, bad = parse_sums((bundle / "SHA256SUMS").read_text(encoding="utf-8"))
    assert bad == []
    assert c16rules.record_issues(m) == []                      # schema + rules._release_manifest
    assert c16rules.component_inventory_issues(m, sums) == []   # signed inventory against SHA256SUMS
    cap = m["capability"]
    assert cap["declared_service_level"] == "DEGRADED_LEXICAL_ONLY" and cap["semantic_search_promised"] is False
    status = {a["kind"]: a["status"] for a in cap["accounting"]}
    assert status["VECTOR_PACK"] == "OMITTED_DEGRADED" and status["TEXT_STORE"] == "SHIPPED"   # B04 2.1 source digest
    assert {c["kind"] for c in m["components"]} == {"ORIGINALS", "TEXT_DERIVATIVES", "RECORDS", "RESEARCH_AIDS", "INTEGRITY_REGISTER",
                                                    "ADMISSION_REGISTER", "KNOWLEDGE_ROWS", "GRAPH", "LEXICAL_INDEX", "TEXT_STORE"}
    # I-2: graph tables only under GRAPH; KNOWLEDGE_ROWS digest is the 2.1 table_rows_digest (final LF)
    assert knowledge_rows.manifest_table_owner_issues(m) == []
    comps = {c["kind"]: c for c in m["components"]}
    assert {t["table"] for t in comps["GRAPH"]["tables"]} == {"graph_nodes", "graph_edges"}
    rows = comps["KNOWLEDGE_ROWS"]["tables"]
    assert comps["KNOWLEDGE_ROWS"]["result_digest"] == digests.table_rows_digest([(t["table"], t["row_count"], t["rows_sha256"]) for t in rows])
    assert comps["TEXT_STORE"]["result_digest"] == digests.file_digest((bundle / "accelerators" / "text-store" / "text.sqlite").read_bytes())
    assert comps["LEXICAL_INDEX"]["result_digest"] == digests.file_digest((bundle / "accelerators" / "search-index" / "search.sqlite").read_bytes())
    assert comps["TEXT_STORE"]["source_digest"] == stages.text_store_source_digest(built["root"] / "S5" / "site")
    gates = json.loads((KBUILD / "config" / "GATE_STATUS.json").read_text(encoding="utf-8"))["gates"]
    assert cap["pending_future_gates"] == sorted(g["gate"] for g in gates if g["status"] == "OPEN" and "KNOWLEDGE" in g["applies_to"])
    assert all(p.relative_to(bundle).as_posix() in sums for p in bundle.rglob("*") if p.is_file() and p.name not in ("SHA256SUMS", "SHA256SUMS.sig"))
    trust = parse_trust_list(json.loads((built["root"] / "S8" / "dev-trust" / "trust_list.json").read_text(encoding="utf-8")))
    reg = load_register()
    assert validate_bundle(bundle, trust_list=trust, mode="development", register=reg, current_release_sequence=0).ok
    prod = validate_bundle(bundle, trust_list=trust, mode="production", register=reg, current_release_sequence=0)
    assert not prod.ok and "SIGNATURE_DEV_KEY_IN_PRODUCTION" in {i.code for i in prod.errors}
    # the ONE 2.1 accounting register (PR #82 clarification 1), declared by the build, in the ADMISSION_REGISTER
    raw = (bundle / "registers" / "source_accounting.json").read_bytes()
    acct = json.loads(raw)
    assert raw == accounting.register_bytes(acct) and accounting.accounting_issues(acct) == []
    assert acct["scope"] == "DECLARED_BY_BUILD" and acct["release_id"] == load_spec()["release"]["release_id"]
    g = load_spec()["inputs"]["producer_generations"][0]
    assert [s["source"] for s in acct["sources"]] == [f"c16:{g['corpus_generation_id']}", f"v1:hf:{g['hf_repo']}@{g['hf_revision']}"]
    assert acct["sources"][0]["provenance"]["generation_manifest_sha256"] == g["generation_manifest_sha256"]
    assert "registers/source_accounting.json" in {f["path"] for f in comps["ADMISSION_REGISTER"]["files"]}
    assert not (bundle / "registers" / "admission-accounting.json").exists()
    # B01 transport: every corpus-v2/ and registers/ file is a RELEASE.json file of kind 'other'
    listed = {f["path"]: f["kind"] for f in json.loads((bundle / "RELEASE.json").read_text(encoding="utf-8"))["files"]}
    for p in bundle.rglob("*"):
        r = p.relative_to(bundle).as_posix()
        if p.is_file() and r.startswith(("corpus-v2/", "registers/")):
            assert listed.get(r) == "other", r


def test_cp1_slice_exchange_is_reproducible_and_pinned(tmp_path):
    """The CP-1 slice exchange (real bytes from the B01 producer harness) is byte-reproducible on every platform and
    hashes to the cp1-slice spec pin; any drift in the harness is caught here, before S1 refuses a build."""
    spec = json.loads((KBUILD / "specs" / "cp1-slice.spec.json").read_text(encoding="utf-8"))
    g = spec["inputs"]["producer_generations"][0]
    root = prepare(tmp_path / "m", exchange="cp1")
    data = (root / g["path"]).read_bytes()
    assert hashlib.sha256(data).hexdigest() == g["generation_manifest_sha256"] == GENERATION_SHA256["cp1"]
    assert json.loads(data)["corpus_generation_id"] == g["corpus_generation_id"]


def test_v7_candidate_sets_are_declared_and_pass_the_reference_check():
    """2.1 CS1-CS5: a V7_REFERENCE source B02 declares carries candidate_set_sha256 of exactly the file it ships, with
    as many hashes as its input; never eligible or served. The reference check accepts it and refuses an orphan."""
    hs = [hashlib.sha256(x).hexdigest() for x in (b"v7-a", b"v7-b")]
    reg = release.source_accounting(release_id="R16-cp1-test-20261128-00000001", v1_docs=[], generations=[],
                                    shipped_original_shas=set(), v7_sets={"cycle15": hs})
    s = reg["sources"][0]
    assert (s["source"], s["path"], s["input"], s["held"], s["eligible"], s["served"]) == ("v7:cycle15", "V7_REFERENCE", 2, 2, 0, 0)
    path = accounting.candidate_set_path("v7:cycle15")
    files = {path: accounting.candidate_set_bytes(hs)}
    union, issues = accounting.candidate_set_issues(reg, files, set(files))
    assert issues == [] and union == set(hs)
    _, issues = accounting.candidate_set_issues(reg, {**files, "registers/candidate_sets/orphan.txt": b""}, set(files) | {"registers/candidate_sets/orphan.txt"})
    assert [i.code for i in issues] == ["C16_SOURCE_ACCOUNTING"]


def test_release_inventories_are_in_ordinal_path_order_on_mixed_case_paths(tmp_path):
    """Cross-platform hazard (B01 c006d300): Path objects compare case-insensitively on Windows and case-sensitively on
    Linux. SHA256SUMS, component file lists and concat digests must use the ordinal order of the '/'-separated path."""
    root = tmp_path / "rel"
    for rel in ("a/x.txt", "B/y.txt", "Z.txt", "b/z.txt", "accelerators/Rows/q.jsonl", "accelerators/rows/p.jsonl"):
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(rel.encode())
    want = sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())   # str order = code point order
    sums = release.sums_bytes(root).decode().splitlines()
    assert [line.split("  ", 1)[1] for line in sums] == want
    assert [e["path"] for e in release.file_entries(root, "accelerators")] == [w for w in want if w.startswith("accelerators/")]
    assert release.concat_digest(root, list(reversed(want))) == digests.concat_digest({w: (root / w).read_bytes() for w in want})


def test_component_digests_are_the_contract_2_1_definitions():
    """B02 computes every component digest with mimamsa_contract.c16.digests: checked against the 2.1 golden vectors."""
    g = json.loads((REPO / "app" / "contract" / "fixtures" / "c16" / "v2_1" / "digests" / "golden.json").read_text(encoding="utf-8"))
    kr = g["KNOWLEDGE_ROWS"]
    assert release.rows_component_digest(kr["tables"]) == kr["digest"] != kr["wrong_no_final_lf"]
    assert release.hashset_digest(g["HASHSET"]["hashes"]) == g["HASHSET"]["digest"]


@pytest.mark.parametrize("mutate,code", [
    (lambda m: m["capability"].update(declared_service_level="FULL", semantic_search_promised=True), "KR_FULL_CAPABILITY_CLAIM"),
    (lambda m: m["capability"]["accounting"].pop(), "KR_ACCOUNTING"),
    (lambda m: m["components"][0]["files"][0].update(path="sessions/x.pdf"), "KR_NAMESPACE"),
    (lambda m: [a.update(status="OMITTED_DEGRADED") for a in m["capability"]["accounting"] if a["kind"] == "ORIGINALS"], "KR_ACCOUNTING"),
])
def test_assembler_refuses_a_manifest_that_fails_the_rules(built, mutate, code):
    m = json.loads((built["root"] / "S8" / "bundle" / "KNOWLEDGE_RELEASE.json").read_text(encoding="utf-8"))
    mutate(m)
    with pytest.raises(BuildRefused) as e:
        stages.assert_release_manifest(m, None, "S7")
    assert e.value.code in (code, "SCHEMA")


def test_inventory_mismatch_is_refused(built):
    bundle = built["root"] / "S8" / "bundle"
    m = json.loads((bundle / "KNOWLEDGE_RELEASE.json").read_text(encoding="utf-8"))
    sums, _ = parse_sums((bundle / "SHA256SUMS").read_text(encoding="utf-8"))
    sums[m["components"][0]["files"][0]["path"]] = "0" * 64
    with pytest.raises(BuildRefused) as e:
        stages.assert_release_manifest(m, sums, "S7")
    assert e.value.code == "KR_INVENTORY"


# ------------------------------------------------------------------ determinism and resume

def test_two_builds_are_byte_identical(built, tmp_path, mirror, dev_key, accel_tool):
    _build(load_spec(), tmp_path, mirror, dev_key, accel_tool)
    a, b = _tree(built["out"] / "build"), _tree(tmp_path / "build")
    assert a == b
    assert any(k.endswith("S8/bundle/SHA256SUMS") for k in a) and any(k.endswith("S9/STAGE.json") for k in a)


def test_rerun_reuses_every_stage(built, tmp_path, mirror, dev_key, accel_tool):
    out = copy_build(built["out"], tmp_path / "out")
    res = _build(load_spec(), out, mirror, dev_key, accel_tool)
    assert res["ran"] == [] and res["reused"] == ALL


def test_tampered_stage_output_reruns_that_stage_and_later_only(built, tmp_path, mirror, dev_key, accel_tool):
    out = copy_build(built["out"], tmp_path / "out")
    f = out / load_spec()["output_dir"] / "S6" / "ACCELERATORS.json"
    f.write_bytes(f.read_bytes() + b" ")
    before = _tree(out / "build")
    res = _build(load_spec(), out, mirror, dev_key, accel_tool)
    assert res["ran"] == ALL[6:] and res["reused"] == ALL[:6]
    after = _tree(out / "build")
    assert after == _tree(built["out"] / "build")
    assert {k for k in before if before[k] != after.get(k)} == {k for k in before if "/S6/ACCELERATORS.json" in k}


def test_killed_stage_leaves_only_partial_and_resumes(built, tmp_path, mirror, dev_key, accel_tool, monkeypatch):
    out = copy_build(built["out"], tmp_path / "out")
    root = out / load_spec()["output_dir"]
    for sid in ALL[7:]:
        import shutil
        shutil.rmtree(root / sid)
    real = stages.STAGES["S7"]

    def crash(ctx, work):
        real(ctx, work)
        raise KeyboardInterrupt("simulated kill after S7 wrote its outputs, before its manifest")
    monkeypatch.setitem(stages.STAGES, "S7", crash)
    with pytest.raises(KeyboardInterrupt):
        _build(load_spec(), out, mirror, dev_key, accel_tool)
    assert (root / "S7.partial").is_dir() and not (root / "S7").exists()
    monkeypatch.setitem(stages.STAGES, "S7", real)
    res = _build(load_spec(), out, mirror, dev_key, accel_tool)
    assert res["ran"] == ALL[7:] and not (root / "S7.partial").exists()
    assert _tree(out / "build") == _tree(built["out"] / "build")


def test_changed_input_reruns_from_fetch(built, tmp_path, mirror, dev_key, accel_tool):
    import shutil
    m2 = tmp_path / "mirror"
    shutil.copytree(mirror, m2)
    research = revision_root(m2, "owner/fixture-corpus", load_spec()["inputs"]["hf"][0]["revision"]) / "v1" / "research" / "a4_provision_versions.jsonl"
    research.write_bytes(research.read_bytes().replace(b"Synthetic version record", b"Synthetic version record (changed)"))
    out = copy_build(built["out"], tmp_path / "out")
    res = _build(load_spec(), out, m2, dev_key, accel_tool)
    assert res["ran"] == ALL[1:] and res["reused"] == ["S0"]
    old, new = _tree(built["out"] / "build"), _tree(out / "build")
    key = next(k for k in new if k.endswith("S8/bundle/research/a4_provision_versions.jsonl"))
    assert old[key] != new[key]


def test_from_stage_forces_that_stage_and_later(built, tmp_path, mirror, dev_key, accel_tool):
    out = copy_build(built["out"], tmp_path / "out")
    res = _build(load_spec(), out, mirror, dev_key, accel_tool, from_stage="S8")
    assert res["ran"] == ["S8", "S9"]
    assert _tree(out / "build") == _tree(built["out"] / "build")


def test_changed_pin_reruns_everything(built, tmp_path, mirror, dev_key, accel_tool):
    spec = load_spec()
    spec["release"]["release_id"] = "R16-cp1-fixture-20261127-00000002"
    spec["release"]["release_sequence"] = 2
    out = copy_build(built["out"], tmp_path / "out")
    res = _build(spec, out, mirror, dev_key, accel_tool)
    assert res["ran"] == ALL


# ------------------------------------------------------------------ refusals (fail closed)

def _mirror_copy(mirror: Path, tmp: Path) -> tuple[Path, Path]:
    import shutil
    m2 = tmp / "mirror"
    shutil.copytree(mirror, m2)
    return m2, revision_root(m2, "owner/fixture-corpus", load_spec()["inputs"]["hf"][0]["revision"])


@pytest.mark.parametrize("damage,code", [
    (lambda r: (r / "exchanges" / "fixture" / "identities.jsonl").unlink(), "BUILD_INPUT_MISSING"),
    (lambda r: (r / "exchanges" / "fixture" / "taxonomy.jsonl").write_bytes(b"{}\n"), "BUILD_INPUT_HASH"),
    (lambda r: (r / "exchanges" / "fixture" / "GENERATION.json").write_bytes(b"{}"), "BUILD_PIN_MISMATCH"),
    (lambda r: __import__("shutil").rmtree(r), "BUILD_INPUT_MISSING"),
])
def test_missing_or_altered_input_is_refused_at_fetch(tmp_path, mirror, dev_key, accel_tool, damage, code):
    m2, rev = _mirror_copy(mirror, tmp_path)
    damage(rev)
    with pytest.raises(BuildRefused) as e:
        _build(load_spec(), tmp_path / "out", m2, dev_key, accel_tool)
    assert e.value.code == code and e.value.stage == "S1"
    root = tmp_path / "out" / load_spec()["output_dir"]
    assert (root / "S0" / "STAGE.json").is_file() and not (root / "S1").exists()
    rec = json.loads((root / "BUILD_RECORD.json").read_text(encoding="utf-8"))
    assert rec["outcome"] == "REFUSED" and rec["refusal"]["code"] == code


def test_missing_dev_key_and_register_pin_are_refused(tmp_path, mirror, accel_tool):
    with pytest.raises(BuildRefused) as e:
        _build(load_spec(), tmp_path / "a", mirror, tmp_path / "no.key", accel_tool)
    assert e.value.code == "BUILD_DEV_KEY_MISSING"
    spec = load_spec()
    spec["inputs"]["restricted_register_sha256"] = "0" * 64
    key = tmp_path / "k"
    key.write_text("11" * 32)
    with pytest.raises(BuildRefused) as e:
        _build(spec, tmp_path / "b", mirror, key, accel_tool)
    assert e.value.code == "BUILD_REGISTER_PIN"


def test_partial_exchange_is_refused_at_validate(tmp_path, mirror, dev_key, accel_tool):
    """An exchange whose GENERATION.json simply omits a population hashes to its own (new) pin and passes S1, but strict
    validation at S2 refuses it: a partial exchange is never importable."""
    m2, rev = _mirror_copy(mirror, tmp_path)
    ex = rev / "exchanges" / "fixture"
    gen = json.loads((ex / "GENERATION.json").read_text(encoding="utf-8"))
    gen["files"] = [f for f in gen["files"] if f["path"] != "taxonomy.jsonl"]
    (ex / "taxonomy.jsonl").unlink()
    data = json.dumps(gen, indent=1, sort_keys=True).encode()
    (ex / "GENERATION.json").write_bytes(data)
    spec = load_spec()
    spec["inputs"]["producer_generations"][0]["generation_manifest_sha256"] = hashlib.sha256(data).hexdigest()
    with pytest.raises(BuildRefused) as e:
        _build(spec, tmp_path / "out", m2, dev_key, accel_tool)
    assert e.value.stage == "S2" and e.value.code.startswith("C16_")


def test_sg1_relabelling_is_refused():
    pos = KBUILD.parents[1] / "app" / "contract" / "fixtures" / "c16" / "positive" / "exchange"
    idents = release.parse_jsonl((pos / "identities.jsonl").read_bytes())
    adms = release.parse_jsonl((pos / "admissions.jsonl").read_bytes())
    pins = {("owner/fixture-corpus", "0" * 40)}
    held = next(i for i in idents if i["doc_id"] == "local-d33bfb0313089bf8")
    eligible = next(i for i in idents if i["doc_id"] == "sc-2019-example-v-union-of-india-ca0001")

    def v1(doc_id, sha, hf=True):
        return {"doc_id": doc_id, "source_copy": {"sha256": sha}, "provenance": {
            "hf": {"repo": "owner/fixture-corpus", "revision": "0" * 40, "path": "x"} if hf else None, "acquisition_record_ref": None}}
    # a v1 record for the bytes of a HELD C16 copy (with or without its sidecar) is not established
    out = release.legacy_issues([v1("relabelled", held["source_copy"]["sha256"])], idents, adms, pins)
    assert [x["code"] for x in out] == ["C16_LEGACY_NOT_ESTABLISHED"]
    # the same bytes with an eligible effective admission are not refused by this rule
    assert release.legacy_issues([v1("other-id", eligible["source_copy"]["sha256"])], idents, adms, pins) == []
    # v7 candidate bytes and unpinned provenance are refused
    assert release.legacy_issues([v1("v7", "ab" * 32)], idents, adms, pins, v7_shas={"ab" * 32})[0]["code"] == "C16_LEGACY_NOT_ESTABLISHED"
    assert release.legacy_issues([v1("unpinned", "cd" * 32, hf=False)], idents, adms, pins)[0]["code"] == "C16_LEGACY_NOT_ESTABLISHED"


def test_contract_2_1_exchange_receipts_are_item_level(tmp_path, dev_key, accel_tool):
    """The 2.1 fixture exchange's G03 receipt binds a fixture register revision, so against the real register it does not
    resolve: the eligible copy is accounted not servable (item level) and the build still completes, degraded."""
    m = tmp_path / "mirror"
    prepare(m, exchange="v2_1")
    spec = load_spec()
    spec["inputs"]["producer_generations"][0]["generation_manifest_sha256"] = GENERATION_SHA256["v2_1"]
    spec["inputs"]["contracts"]["corpus"] = "mimamsa-corpus-contract/2.1"
    res = _build(spec, tmp_path / "out", m, dev_key, accel_tool)
    root = tmp_path / "out" / spec["output_dir"]
    val = json.loads((root / "S2" / "VALIDATION.json").read_text(encoding="utf-8"))
    assert "C16_RECEIPT_REGISTER" in sum(val["receipts"]["unresolved_admissions"].values(), [])
    acct = json.loads((root / "S8" / "bundle" / "registers" / "source_accounting.json").read_text(encoding="utf-8"))
    c16 = next(s for s in acct["sources"] if s["path"] == "C16")
    assert c16["not_served_reasons"].get("RECEIPTS_UNRESOLVED") == 1 and c16["served"] == 0 and c16["eligible"] == 0
    assert any(p.startswith("registers/receipts/") for p in parse_sums((root / "S8" / "bundle" / "SHA256SUMS").read_text())[0])
    assert res["ran"] == ALL


# ------------------------------------------------------------------ network and resources

def test_network_is_forbidden_outside_fetch(tmp_path, monkeypatch):
    with no_network():
        with pytest.raises(NetworkForbidden):
            socket.create_connection(("127.0.0.1", 9))
        with pytest.raises(NetworkForbidden):
            socket.getaddrinfo("localhost", 80)
    socket.getaddrinfo("localhost", 80)   # restored afterwards

    def s0_net(ctx, work):
        socket.create_connection(("127.0.0.1", 9))
    monkeypatch.setitem(stages.STAGES, "S0", s0_net)
    with pytest.raises(NetworkForbidden):
        run_build(load_spec(), tmp_path, apply_budget=False)
    assert not (tmp_path / load_spec()["output_dir"] / "S0").exists()


@pytest.mark.skipif(sys.platform != "win32", reason="the Windows job-object budget is read back from the OS")
def test_shared_host_budget_is_applied_and_read_back():
    p = subprocess.run([sys.executable, "-m", "mimamsa_kbuild", "budget", "--spec", str(SPEC)], cwd=KBUILD,
                       capture_output=True, text=True, timeout=120)
    assert p.returncode == 0, p.stderr
    b = json.loads(p.stdout)
    spec = load_spec()
    a = b["applied"]
    assert b["workers"] <= max(1, b["measured_now"]["logical_cpus"] // 2)
    assert b["memory_bytes"] <= b["measured_now"]["memory_bytes"] // 2
    assert a["process_priority_class"] == "BELOW_NORMAL" and a["process_io_priority"] == "LOW"
    assert a["job"]["assigned"] and a["job"]["job_memory_limit_bytes"] == min(spec["resources"]["max_memory_bytes"], b["measured_now"]["memory_bytes"] // 2)
    assert a["job"]["priority_class"] == "BELOW_NORMAL"
    assert 0 < a["job"]["cpu_rate_hard_cap_percent"] <= 50.0


def test_cli_build_runs_bounded_and_matches(built, tmp_path, mirror, dev_key, accel_tool):
    """The one command, in its own process, with the shared-host budget applied (job object, priorities): the result
    is byte-identical to the in-process build and the build record states the budget the OS reports."""
    out = tmp_path / "out"
    p = subprocess.run([sys.executable, "-m", "mimamsa_kbuild", "build", "--spec", str(SPEC), "--out-root", str(out),
                        "--source-mirror", str(mirror), "--dev-key", str(dev_key), "--accel-tool", str(accel_tool)],
                       cwd=KBUILD, capture_output=True, text=True, timeout=900)
    assert p.returncode == 0, p.stderr[-2000:]
    assert _tree(out / "build") == _tree(built["out"] / "build")
    rec = json.loads((out / load_spec()["output_dir"] / "BUILD_RECORD.json").read_text(encoding="utf-8"))
    applied = rec["budget"]["applied"]
    assert rec["outcome"] == "BUILT" and rec["budget"]["workers"] == 2
    if sys.platform == "win32":
        assert applied["job"]["assigned"] and applied["process_priority_class"] == "BELOW_NORMAL" and applied["process_io_priority"] == "LOW"


def test_effective_budget_never_exceeds_half_the_current_host():
    from mimamsa_kbuild.resources import HostMeasurement, effective_budget
    spec = copy.deepcopy(load_spec())
    b = effective_budget(spec, HostMeasurement(logical_cpus=2, memory_bytes=4 << 30))   # a smaller host than measured
    assert b.workers == 1 and b.memory_bytes == 2 << 30
    from mimamsa_kbuild.resources import stage_workers
    assert stage_workers(spec, "S6", b) == 1


def test_engine_rejects_unlisted_files_in_a_stage(built, tmp_path, mirror, dev_key, accel_tool):
    out = copy_build(built["out"], tmp_path / "out")
    (out / load_spec()["output_dir"] / "S4" / "tree" / "smuggled.txt").write_text("x")
    res = _build(load_spec(), out, mirror, dev_key, accel_tool)
    assert res["ran"] == ALL[4:]
    assert not (out / load_spec()["output_dir"] / "S4" / "tree" / "smuggled.txt").exists()
    assert engine.STAGE_IDS == ALL
