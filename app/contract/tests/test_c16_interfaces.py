"""Tranche B Stage 1 interfaces (contract 2.1, additive): gate-receipt artefacts, build spec, knowledge rows,
activation journal scenarios and component verification. Fixtures: app/contract/fixtures/c16/v2_1."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from mimamsa_contract.c16 import build_spec, canonical, components, knowledge_rows, receipts, scenarios
from mimamsa_contract.c16.rules import exchange_issues
from mimamsa_contract.c16.schemas import schema_errors

CONTRACT = Path(__file__).resolve().parents[1]
FIX = CONTRACT / "fixtures" / "c16"
V21 = FIX / "v2_1"
REGISTER = json.loads((V21 / "exchange" / "GENERATION.json").read_text(encoding="utf-8"))["pinned_inputs"]["restricted_register_sha256"]


def _codes(issues):
    return {i.code for i in issues}


def _j(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def _jl(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x]


def _pop():
    return {k: _jl(V21 / "exchange" / f"{k}.jsonl") for k in ("identities", "anchors", "relationships", "taxonomy", "admissions", "reviewed_records")}


def _artefacts():
    d = V21 / "registers" / "receipts"
    return {f"registers/receipts/{p.name}": p.read_bytes() for p in sorted(d.iterdir())}


def _facts(drop=()):
    return {(f["source_copy_sha256"], f["receipt_kind"]): f["fact"] for f in _j(V21 / "site_facts.json") if f["receipt_kind"] not in drop}


def _resolve(admissions, artefacts, *, contract="mimamsa-corpus-contract/2.1", facts=None, inventory=None):
    pop = _pop()
    return receipts.resolve_receipts(admissions=admissions, identities=pop["identities"], anchors=pop["anchors"],
                                     relationships=pop["relationships"], artefacts=artefacts, exchange_contract=contract,
                                     manifest_register_sha256=REGISTER, site_register_sha256=REGISTER,
                                     site_facts=_facts() if facts is None else facts, inventory_paths=inventory)


def test_2_1_fixtures_are_byte_identical_to_builder_output():
    out = subprocess.run([sys.executable, "-I", str(FIX / "build_fixtures_2_1.py"), "--check"], capture_output=True, text=True)
    assert out.returncode == 0, out.stdout + out.stderr


# ---------------------------------------------------------------- receipts (I-1, FG-RECEIPTS interface)

def test_2_1_exchange_is_strictly_valid_and_receipts_resolve():
    files = {p.name: p.read_bytes() for p in (V21 / "exchange").iterdir()}
    assert exchange_issues(files, mode="strict") == []
    pop = _pop()
    issues, verification = _resolve(pop["admissions"], _artefacts())
    assert [str(i) for i in issues] == []
    (aid, gates), = verification.items()
    assert gates["G01_HASH_VERIFIED"] == "SITE_VERIFIED" and gates["G08_RELEVANCE_ASSESSED"] == "ASSERTED_BOUND"
    assert set(gates) == {g["gate_id"] for a in pop["admissions"] if a["admission_id"] == aid for g in a["gates"] if g["result"] == "PASS"}


def test_every_receipt_artefact_is_schema_valid_and_canonical():
    for path, data in _artefacts().items():
        a = json.loads(data)
        assert receipts.artefact_issues(a) == [] and receipts.artefact_path(a) == path


def _case(name):
    return _j(V21 / "negative_receipts" / f"{name}.json")


NEG = sorted(p.stem for p in (V21 / "negative_receipts").iterdir())


@pytest.mark.parametrize("name", NEG)
def test_negative_receipt_cases_fail_closed(name):
    c = _case(name)
    pop = _pop()
    adms = [c["admission"] if a["admission_id"] == c["admission"]["admission_id"] else a for a in pop["admissions"]]
    arts = {p: t.encode("utf-8") for p, t in c["artefacts"].items()}
    issues, verification = _resolve(adms, arts, contract=c["exchange_contract"], facts=_facts(c["drop_site_facts"]),
                                    inventory=set(c["inventory"]) if c["inventory"] is not None else None)
    assert c["expect_code"] in _codes(issues), [str(i) for i in issues]
    assert issues                                       # fail closed: the admission cannot be imported as eligible


def test_receipt_negative_coverage():
    codes = {_case(n)["expect_code"] for n in NEG}
    assert {"C16_RECEIPT_UNRESOLVED", "C16_RECEIPT_FIELD_MISMATCH", "C16_RECEIPT_REGISTER", "C16_RECEIPT_PAYLOAD", "C16_RECEIPT_PATH",
            "C16_RECEIPT_NOT_IN_INVENTORY", "C16_RECEIPTS_REQUIRE_2_1", "C16_RECEIPT_SITE_MISMATCH", "C16_RECEIPT_UNVERIFIABLE",
            "C16_RECEIPT_SUPERSEDED", "C16_RECEIPT_NOT_CANONICAL", "SCHEMA"} <= codes


def test_hash_existence_alone_never_passes():
    """An artefact that exists with the right name and hash but describes a FAIL, another copy or unverifiable facts
    does not verify the gate; and with no site facts at all, nothing site-recomputable is verified."""
    pop = _pop()
    issues, verification = _resolve(pop["admissions"], _artefacts(), facts={})
    assert "C16_RECEIPT_UNVERIFIABLE" in _codes(issues)
    assert all(v == "ASSERTED_BOUND" for gates in verification.values() for v in gates.values())


def test_ineligible_admissions_need_no_receipts_and_a_2_0_exchange_cannot_be_eligible():
    pop = _pop()
    ineligible = [a for a in pop["admissions"] if not a["application_eligible"]]
    assert _resolve(ineligible, {})[0] == []
    issues, _ = _resolve(pop["admissions"], _artefacts(), contract="mimamsa-corpus-contract/2.0")
    assert "C16_RECEIPTS_REQUIRE_2_1" in _codes(issues)


def test_recompute_site_facts_reference():
    pdf = b"%PDF-1.7 synthetic"
    der = b"[[page 1]]\nalpha\n[[page 2]]\nbeta\n"
    f = receipts.recompute_site_facts(original=pdf, derivative=der, register_matches=0)
    assert f["FORMAT_DETECTION"] == {"detected_format": "PDF", "magic_hex": "255044462d"}
    assert len(f["DERIVATIVE_VERIFICATION"]["unit_text_sha256"]) == 2 and f["REGISTER_CHECK"] == {"matches": 0}


# ---------------------------------------------------------------- B02 build spec

def test_build_spec_and_stage_chain():
    spec = _j(V21 / "build" / "spec.json")
    assert build_spec.spec_issues(spec) == []
    ms = {p.stem: _j(p) for p in (V21 / "build" / "stages").iterdir()}
    assert build_spec.stages_to_run(spec, ms, {s: True for s in ms}) == []
    assert build_spec.stages_to_run(spec, ms, dict({s: True for s in ms}, S6=False)) == ["S6", "S7", "S8", "S9"]
    changed = copy.deepcopy(spec)
    changed["inputs"]["restricted_register_sha256"] = "0" * 64
    assert build_spec.stages_to_run(changed, ms, {s: True for s in ms}) == [s for s, _ in build_spec.STAGES]
    no_s3 = {k: v for k, v in ms.items() if k != "S3"}
    assert build_spec.stages_to_run(spec, no_s3, {s: True for s in ms})[0] == "S3"


@pytest.mark.parametrize("mutate,code", [
    (lambda s: s["stages"][2].update(network=True), "BUILD_NETWORK"),
    (lambda s: s["stages"].reverse(), "BUILD_STAGE_ORDER"),
    (lambda s: s["resources"].update(max_workers=12), "BUILD_RESOURCES"),
    (lambda s: s["resources"].update(cpu_priority="NORMAL"), "BUILD_RESOURCES"),
    (lambda s: s["resources"].update(max_memory_bytes=15 * 2**30), "BUILD_RESOURCES"),
    (lambda s: s["release"].update(base_mode="DELTA"), "BUILD_RELEASE"),
    (lambda s: s.pop("pinned_build_time"), "SCHEMA"),
])
def test_build_spec_negatives(mutate, code):
    spec = _j(V21 / "build" / "spec.json")
    mutate(spec)
    assert code in _codes(build_spec.spec_issues(spec))


def test_stage_manifest_negatives():
    spec = _j(V21 / "build" / "spec.json")
    ms = {p.stem: _j(p) for p in (V21 / "build" / "stages").iterdir()}
    bad = copy.deepcopy(ms["S4"])
    bad["network_used"] = True
    assert "SCHEMA" in _codes(build_spec.stage_manifest_issues(bad, spec, ms["S3"]))
    bad = copy.deepcopy(ms["S4"])
    bad["outputs"][0]["sha256"] = "1" * 64
    assert "BUILD_MANIFEST_OUTPUT" in _codes(build_spec.stage_manifest_issues(bad, spec, ms["S3"]))
    assert "BUILD_MANIFEST_CHAIN" in _codes(build_spec.stage_manifest_issues(ms["S4"], spec, ms["S2"]))


# ---------------------------------------------------------------- B03 knowledge rows

def test_allowlist_and_rows_rederive():
    al = _j(V21 / "knowledge_rows" / "allowlist.json")
    assert knowledge_rows.allowlist_issues(al) == []
    pop = _pop()
    for p in (V21 / "knowledge_rows" / "rows").iterdir():
        data = p.read_bytes()
        assert knowledge_rows.row_file_issues(p.stem, data, al) == []
        assert knowledge_rows.rederive_compare(p.stem, data, pop, al) == []


def _rows(table):
    return (V21 / "knowledge_rows" / "rows" / f"{table}.jsonl").read_bytes()


@pytest.mark.parametrize("make,code", [
    (lambda d: ("app_users", d), "KR_ROWS_TABLE_NOT_ALLOWLISTED"),
    (lambda d: ("document_identities", d.replace(b'"doc_id"', b'"extra":"x","doc_id"', 1)), "KR_ROWS_TYPE"),
    (lambda d: ("document_identities", d.replace(b'"quoting_permitted":true', b'"quoting_permitted":"yes"', 1)), "KR_ROWS_TYPE"),
    (lambda d: ("document_identities", d + d.split(b"\n")[0] + b"\n"), "KR_ROWS_DUPLICATE_KEY"),
    (lambda d: ("document_identities", b"\n".join(reversed(d.rstrip(b"\n").split(b"\n"))) + b"\n"), "KR_ROWS_NOT_CANONICAL"),
    (lambda d: ("document_identities", b"[1,2]\n" + d), "KR_ROWS_MALFORMED"),
    (lambda d: ("document_identities", d.replace(b'"doc_id":"', b'"doc_id":"x\'; DROP TABLE site.app_users; --', 1)), "KR_ROWS_NOT_CANONICAL"),
])
def test_row_file_negatives(make, code):
    al = _j(V21 / "knowledge_rows" / "allowlist.json")
    table, data = make(_rows("document_identities"))
    assert code in _codes(knowledge_rows.row_file_issues(table, data, al))


def test_row_not_derivable_from_records_is_rejected():
    al = _j(V21 / "knowledge_rows" / "allowlist.json")
    rows = [json.loads(x) for x in _rows("corpus_admissions").splitlines()]
    rows[0]["application_eligible"] = not rows[0]["application_eligible"]
    data = knowledge_rows.row_file_bytes(rows, ["admission_id"])
    assert knowledge_rows.row_file_issues("corpus_admissions", data, al) == []           # well-formed ...
    assert "KR_ROWS_REDERIVE_MISMATCH" in _codes(knowledge_rows.rederive_compare("corpus_admissions", data, _pop(), al))  # ... but not true


def test_allowlist_cannot_widen_the_loader_or_move_graph_tables():
    al = _j(V21 / "knowledge_rows" / "allowlist.json")
    wider = copy.deepcopy(al)
    wider["loader"]["grants"].append("ALL ON SCHEMA site")
    assert schema_errors(wider)
    moved = copy.deepcopy(al)
    next(t for t in moved["tables"] if t["table"] == "graph_edges")["owner_component"] = "KNOWLEDGE_ROWS"
    assert "KR_ROWS_ALLOWLIST" in _codes(knowledge_rows.allowlist_issues(moved))


# ---------------------------------------------------------------- B06 activation scenarios

SCN = sorted(p.name[:-5] for p in (V21 / "activation_scenarios").iterdir() if not p.name.endswith(".expected.json"))


@pytest.mark.parametrize("sid", SCN)
def test_scenario_reproduces_expected_trace_and_invariants(sid):
    s = _j(V21 / "activation_scenarios" / f"{sid}.json")
    exp = _j(V21 / "activation_scenarios" / f"{sid}.expected.json")
    assert schema_errors(s) == [] and schema_errors(exp) == []
    out = scenarios.run_scenario(s)
    assert exp["scenario_sha256"] == canonical.record_sha256(s)
    assert out == exp
    assert scenarios.final_assertion_failures(s, out) == []


def test_scenario_corpus_covers_the_required_classes():
    covered = {c for sid in SCN for c in _j(V21 / "activation_scenarios" / f"{sid}.json")["covers"]}
    assert {"CRASH_BOUNDARY", "EXCLUSION_MID_SWITCH", "LOCK_CONTENTION", "STALE_PROCESS", "PARTICIPANT_LOSS", "TORN_JOURNAL",
            "JOURNAL_CORRUPTION", "RESPONSE_BOUNDARY_EXCLUSION", "EXCLUSION_READER_FAIL_CLOSED", "MODEL_SWITCH", "ROLLBACK",
            "RETENTION", "RESTORE", "DISK_PREFLIGHT"} <= covered
    crash = [sid for sid in SCN if "CRASH_BOUNDARY" in _j(V21 / "activation_scenarios" / f"{sid}.json")["covers"]]
    assert len(crash) >= 7


def test_journal_record_schema():
    rec = {"contract": "mimamsa-corpus-contract/2.1", "record_kind": "activation_journal_record", "seq": 1, "previous_record_sha256": None,
           "txn_id": "TX-00000001-0123456789ab", "step": "BEGIN", "target": "KNOWLEDGE", "from": "R1", "to": "R2", "action": "ACTIVATE",
           "writer": {"writer_id": "activator-1", "lock_epoch": 1}, "at": "2026-12-01T00:00:00Z"}
    assert schema_errors(rec) == []
    bad = dict(rec)
    del bad["to"]
    assert schema_errors(bad)
    opened = dict(rec, seq=2, previous_record_sha256="a" * 64, step="OPEN")
    for k in ("target", "from", "to", "action"):
        opened.pop(k)
    assert schema_errors(opened)                       # OPEN needs exclusion_seq
    assert schema_errors(dict(opened, exclusion_seq=3)) == []


# ---------------------------------------------------------------- B04 component verification and CP-1

def _contracts():
    return {p.stem: _j(p) for p in (V21 / "component_contracts").iterdir()}


def test_component_contracts_are_complete_and_uncalibrated():
    cs = _contracts()
    assert set(cs) == {"KNOWLEDGE_ROWS", "TEXT_STORE", "LEXICAL_INDEX", "VECTOR_PACK", "GRAPH"}
    for c in cs.values():
        assert components.contract_issues(c) == [] and c["site_embedding"] == "NEVER"
    assert all(components.uncalibrated(cs[k]) for k in ("LEXICAL_INDEX", "VECTOR_PACK", "GRAPH"))
    for c in cs.values():
        assert {x["check_id"] for x in c["checks"]} <= components.manifest_verify_ids()


def test_activation_outcome_rules():
    cs = _contracts()
    allv = {k: "VERIFIED" for k in cs}
    assert components.activation_outcome(allv, cs, mode="production")["result"] == "REFUSED"          # uncalibrated: fail closed
    assert components.activation_outcome(allv, cs, mode="development")["result"] == "ACTIVE_FULL"
    no_vec = dict(allv, VECTOR_PACK="MISSING")
    o = components.activation_outcome(no_vec, cs, mode="development")
    assert o["result"] == "ACTIVE_DEGRADED" and o["service_level"] == "DEGRADED_LEXICAL_ONLY" and o["site_embedding"] == "NEVER"
    assert components.activation_outcome(dict(allv, GRAPH="FAILED"), cs, mode="development")["result"] == "ACTIVE_AFTER_LOCAL_REBUILD"


@pytest.mark.parametrize("mutate", [
    lambda c: c.update(site_embedding="ALLOWED"),
    lambda c: c.update(on_failure="REBUILD_LOCALLY_CHEAP"),
    lambda c: c["checks"][3]["sample"].update(selection="FULL"),
])
def test_vector_contract_negatives(mutate):
    c = copy.deepcopy(_contracts()["VECTOR_PACK"])
    mutate(c)
    assert schema_errors(c) or components.contract_issues(c)


def test_cp1_slice_is_explicitly_degraded():
    from mimamsa_contract.c16.rules import record_issues
    man = _j(V21 / "cp1" / "KNOWLEDGE_RELEASE.json")
    rec = _j(V21 / "cp1" / "activation_record.json")
    assert record_issues(man) == [] and record_issues(rec) == []
    assert man["capability"]["declared_service_level"] == "DEGRADED_LEXICAL_ONLY"
    assert rec["result"] == "ACTIVE_DEGRADED" and rec["result"] != "ACTIVE_FULL"
    assert man["capability"]["pending_future_gates"]


# ---------------------------------------------------------------- I-5 legacy establishment and per-source accounting

def _v1_doc():
    d = json.loads((CONTRACT / "examples" / "document.example.json").read_text(encoding="utf-8"))
    d["status_axes"]["publication"]["value"] = "PUBLISHED"
    d["restriction"]["eligibility"] = "ELIGIBLE_ALL_USERS"
    d["provenance"]["hf"] = d["provenance"].get("hf") or {"repo": "owner/x", "revision": "a" * 40, "path": "data/raw/x.pdf"}
    return d


def test_legacy_v1_copy_established_only_independently():
    from mimamsa_contract.c16 import legacy
    d = _v1_doc()
    key = (d["doc_id"], d["source_copy"]["sha256"])
    ok = dict(c16_governed=set(), eligible_c16=set(), candidate_shas=set(), excluded=set())
    assert legacy.legacy_issues(d, **ok) == []
    for kw in (dict(ok, c16_governed={key}),                       # sidecar removed: still C16-governed
               dict(ok, candidate_shas={key[1]}),                  # v7 / unadmitted original relabelled as v1
               dict(ok, excluded={key[0]})):                       # withdrawal
        assert "C16_LEGACY_NOT_ESTABLISHED" in _codes(legacy.legacy_issues(d, **kw))
    gap = copy.deepcopy(d)
    gap["provenance"]["hf"] = None
    gap["provenance"]["acquisition_record_ref"] = None
    assert "C16_LEGACY_NOT_ESTABLISHED" in _codes(legacy.legacy_issues(gap, **ok))
    assert legacy.legacy_issues(d, **dict(ok, c16_governed={key}, eligible_c16={key})) == []   # governed and eligible: C16 path


def test_per_source_accounting_reconciles():
    from mimamsa_contract.c16 import legacy
    good = [{"source": "v1-canonical", "input": 10, "identities": 10, "held": 2, "rejected": 1, "quarantined": 0, "eligible": 7, "served": 7},
            {"source": "v7-candidates", "input": 5, "identities": 5, "held": 5, "rejected": 0, "quarantined": 0, "eligible": 0, "served": 0}]
    assert legacy.accounting_issues(good) == []
    bad = copy.deepcopy(good)
    bad[0]["held"] = 1
    bad[1]["served"] = 1
    assert len(legacy.accounting_issues(bad)) == 3


# ---------------------------------------------------------------- PR #82 clarifications (contract 2.1, additive)
# 1. one per-source admission accounting register

def test_accounting_register_positive_and_compare():
    from mimamsa_contract.c16 import accounting
    d, r = _j(V21 / "accounting" / "declared.json"), _j(V21 / "accounting" / "recomputed.json")
    assert accounting.FILE == "registers/source_accounting.json" and d["record_kind"] == "source_admission_accounting"
    assert accounting.accounting_issues(d) == [] and accounting.accounting_issues(r) == []
    assert accounting.compare_declared(d, r) == []
    assert (V21 / "accounting" / "declared.json").read_bytes() == accounting.register_bytes(d)   # canonical + LF


@pytest.mark.parametrize("name", sorted(p.stem for p in (V21 / "accounting" / "negative").glob("*.json")))
def test_accounting_negatives_fail_closed(name):
    from mimamsa_contract.c16 import accounting
    case = _j(V21 / "accounting" / "negative" / f"{name}.json")
    if case["check"] == "compare_declared":
        issues = accounting.compare_declared(case["declared"], case["register"])
    else:
        issues = accounting.accounting_issues(case["register"])
    assert case["expected_code"] in _codes(issues)


def test_cp1_admission_register_ships_the_accounting_register():
    from mimamsa_contract.c16 import accounting
    man = _j(V21 / "cp1" / "KNOWLEDGE_RELEASE.json")
    adm = next(c for c in man["components"] if c["kind"] == "ADMISSION_REGISTER")
    assert accounting.FILE in {f["path"] for f in adm["files"]}


# 2 and 5. exact component digests and the bundle-independent text-store source digest

def test_component_digest_golden_vectors():
    from mimamsa_contract.c16 import digests
    G = _j(V21 / "digests" / "golden.json")
    kr = G["KNOWLEDGE_ROWS"]
    tables = [(t["table"], t["row_count"], t["rows_sha256"]) for t in kr["tables"]]
    assert kr["preimage"].endswith("\n") and kr["preimage"].count("\n") == len(tables)
    assert digests.table_rows_digest(tables) == kr["digest"] == digests._h(kr["preimage"].encode())
    assert digests.table_rows_digest(list(reversed(tables))) == kr["digest"]          # tables sorted by name
    assert kr["wrong_no_final_lf"] != kr["digest"]                                     # the no-final-LF form is not it
    for t, n, s in tables:                                                             # bound to the real fixture row files
        data = (V21 / "knowledge_rows" / "rows" / f"{t}.jsonl").read_bytes()
        assert (n, s) == (data.count(b"\n"), knowledge_rows.rows_sha256(data))
    g = G["GRAPH"]
    assert digests.graph_digest(g["builder_version"], g["node_ids"], g["edge_ids"]) == g["digest"] == digests._h(g["preimage"].encode())
    for k in ("LEXICAL_INDEX", "TEXT_STORE"):
        assert digests.file_digest(bytes.fromhex(G[k]["file_hex"])) == G[k]["digest"]
    e = [(bytes.fromhex(x["key_hex"]), bytes.fromhex(x["vector_hex"])) for x in G["VECTOR_PACK"]["entries"]]
    assert digests.vector_pack_digest(e) == digests.vector_pack_digest(e[::-1]) == G["VECTOR_PACK"]["digest"]
    with pytest.raises(ValueError):
        digests.vector_pack_digest([(b"short", b"")])
    assert digests.hashset_digest(G["HASHSET"]["hashes"]) == G["HASHSET"]["digest"]
    assert digests.concat_digest({k: v.encode() for k, v in G["CONCAT"]["files"].items()}) == G["CONCAT"]["digest"]


def _ts_mutations():
    def gen(g, d, x):
        return g.replace("fixtures", "fixturez"), d, x

    def field(where, **kw):
        def m(g, d, x):
            where(d, x).update(kw)
            return g, d, x
        return m
    return [gen,
            field(lambda d, x: d[0], copy_sha256="0" * 64),
            field(lambda d, x: x[0], text_sha256="1" * 64),
            field(lambda d, x: x[0], source_copy_sha256="2" * 64),
            field(lambda d, x: x[0], quoting_permitted=False),
            field(lambda d, x: x[0]["pipeline"], version="1.3"),
            field(lambda d, x: x[0]["pages"][0], char_count=41),
            field(lambda d, x: x[1]["pages"][0], low_confidence=False),
            field(lambda d, x: x[0]["passages"][0], char_end=49),
            field(lambda d, x: x[0]["passages"][1], paragraph_label=None)]


def test_text_store_source_digest_is_bundle_independent_and_bound_to_derivatives():
    import inspect
    from mimamsa_contract.c16 import digests
    t = _j(V21 / "digests" / "golden.json")["TEXT_STORE_SOURCE"]
    gid, docs, der = t["generation_id"], t["documents"], t["derived"]
    base = digests.text_store_source_digest(gid, docs, der)
    assert base == t["digest"]
    assert digests.text_store_source_digest(gid, docs[::-1], der[::-1]) == base      # input order does not matter
    # no bundle checksum or generation.json bytes are inputs, so the central build can compute it before the bundle exists
    assert list(inspect.signature(digests.text_store_source_digest).parameters) == ["generation_id", "documents", "derived"]
    for mutate in _ts_mutations():
        g2, d2, x2 = mutate(gid, copy.deepcopy(docs), copy.deepcopy(der))
        assert digests.text_store_source_digest(g2, d2, x2) != base


# 3. loader grants: 2.1 is authoritative (no DDL for the loader) and the site DB is hardened

def test_loader_has_no_ddl_and_docs_state_2_1_is_authoritative():
    loader = _j(V21 / "knowledge_rows" / "allowlist.json")["loader"]
    assert loader["grants"] == ["USAGE ON SCHEMA kr_<n>_staging", "INSERT ON ALL TABLES IN SCHEMA kr_<n>_staging"]
    assert not any("CREATE" in g for g in loader["grants"])
    doc = (CONTRACT.parents[1] / "docs" / "architecture" / "c16" / "interfaces" / "B03_KNOWLEDGE_ROWS.md").read_text(encoding="utf-8")
    for needle in ("REVOKE TEMPORARY", "REVOKE CREATE ON SCHEMA public FROM PUBLIC", "2.1 is authoritative", "B07"):
        assert needle in doc


# 4. CP-1 follows I-2

def test_cp1_graph_tables_are_graph_component_tables():
    from mimamsa_contract.c16 import digests
    man = _j(V21 / "cp1" / "KNOWLEDGE_RELEASE.json")
    assert knowledge_rows.manifest_table_owner_issues(man) == []
    by_kind = {c["kind"]: c for c in man["components"]}
    assert {t["table"] for t in by_kind["GRAPH"]["tables"]} == {"graph_nodes", "graph_edges"}
    assert all(t["file"].startswith("accelerators/graph/") for t in by_kind["GRAPH"]["tables"])
    kr = by_kind["KNOWLEDGE_ROWS"]
    assert not {t["table"] for t in kr["tables"]} & {"graph_nodes", "graph_edges"}
    assert kr["result_digest"] == digests.table_rows_digest([(t["table"], t["row_count"], t["rows_sha256"]) for t in kr["tables"]])
    bad = copy.deepcopy(man)
    moved = next(c for c in bad["components"] if c["kind"] == "GRAPH")["tables"][0]
    next(c for c in bad["components"] if c["kind"] == "KNOWLEDGE_ROWS")["tables"].append(moved)
    assert "KR_ROWS_ALLOWLIST" in _codes(knowledge_rows.manifest_table_owner_issues(bad))


# ---------------------------------------------------------------- CP-1 gaps (contract 2.1, additive)
# gap 1: v7 candidate-set files

def _cs_positive():
    from mimamsa_contract.c16 import accounting
    d = _j(V21 / "accounting" / "declared.json")
    p = "registers/candidate_sets/candidates-2026.txt"
    return accounting, d, {p: (V21 / "accounting" / p).read_bytes()}, {accounting.FILE, p}


def test_candidate_set_positive_binds_to_declared_digest():
    from mimamsa_contract.c16 import digests
    accounting, d, files, inv = _cs_positive()
    shas, issues = accounting.candidate_set_issues(d, files, inv)
    assert issues == []
    v7 = next(s for s in d["sources"] if s["path"] == "V7_REFERENCE")
    data = next(iter(files.values()))
    assert len(shas) == v7["input"] and not data.endswith(b"\n") and b"\r" not in data
    assert v7["provenance"]["candidate_set_sha256"] == digests.hashset_digest(sorted(shas))
    assert accounting.candidate_set_path(v7["source"]) in files
    man = _j(V21 / "cp1" / "KNOWLEDGE_RELEASE.json")
    adm = next(c for c in man["components"] if c["kind"] == "ADMISSION_REGISTER")
    assert set(files) <= {f["path"] for f in adm["files"]}
    # the hashes feed the I-5 relabel check: a v1 record whose copy is a v7 candidate is not established
    from mimamsa_contract.c16 import legacy
    doc = {"doc_id": "doc-x", "source_copy": {"sha256": sorted(shas)[0]}}
    assert "C16_LEGACY_NOT_ESTABLISHED" in _codes(legacy.legacy_issues(doc, c16_governed=set(), eligible_c16=set(),
                                                                         candidate_shas=shas, excluded=set()))


def test_candidate_set_empty_source_is_the_empty_file():
    accounting, d, _, _ = _cs_positive()
    d = copy.deepcopy(d)
    v7 = next(s for s in d["sources"] if s["path"] == "V7_REFERENCE")
    import hashlib
    v7.update(input=0, identities=0, held=0, not_served_reasons={})
    v7["provenance"]["candidate_set_sha256"] = hashlib.sha256(b"").hexdigest()
    p = accounting.candidate_set_path(v7["source"])
    assert accounting.candidate_set_issues(d, {p: b""}, {accounting.FILE, p}) == (set(), [])


@pytest.mark.parametrize("name", sorted(p.stem for p in (V21 / "accounting" / "candidate_set_negative").glob("*.json")))
def test_candidate_set_negatives_fail_closed(name):
    from mimamsa_contract.c16 import accounting
    case = _j(V21 / "accounting" / "candidate_set_negative" / f"{name}.json")
    files = {k: bytes.fromhex(v) for k, v in case["files_hex"].items()}
    shas, issues = accounting.candidate_set_issues(case["declared"], files, set(case["admission_inventory"]))
    assert case["expected_code"] in _codes(issues) and shas == set()


# gap 2: lexical-only knowledge releases and model compatibility

LEX_SCENARIOS = ["SC26", "SC27", "SC28", "SC29", "SC30", "SC31"]


def test_lexical_only_scenarios_and_rules():
    seen = set()
    for p in sorted((V21 / "activation_scenarios").glob("SC*.json")):
        if p.name.endswith(".expected.json"):
            continue
        s = _j(p)
        sid = s["scenario_id"][:4]
        exp = _j(p.with_name(p.stem + ".expected.json"))
        has = all("semantic_search" in t for t in exp["trace"])
        assert has == ("lexical_only" in s["initial"]) == (sid in LEX_SCENARIOS)   # SC01-SC25 traces unchanged
        if sid in LEX_SCENARIOS:
            seen.add(sid)
            assert "LEXICAL_ONLY_ACTIVATION" in s["covers"]
            assert scenarios.final_assertion_failures(s, scenarios.run_scenario(s)) == []
    assert seen == set(LEX_SCENARIOS)


def test_model_gate_rules_directly():
    from mimamsa_contract.c16 import activation
    # K2: lexical-only target with no model, and with a verified model without vectors for it
    s = activation.Site(installed=["L1", "L2"], active="L1", models=None, lexical_only={"L1", "L2"})
    s.transition("KNOWLEDGE", "L2")
    assert s.pointers == {"KNOWLEDGE": "L2", "MODELS": None} and not s.semantic_search_enabled()
    # K1: a release with vectors still needs a verified model with verified vectors
    s = activation.Site(installed=["L1", "R2"], active="L1", models=None, lexical_only={"L1"})
    with pytest.raises(activation.Refused):
        s.transition("KNOWLEDGE", "R2")
    s = activation.Site(installed=["R1", "R2"], active="R1", staged_models={"M1": {"verified": True, "vectors_for": {"R1"}}})
    with pytest.raises(activation.Refused):
        s.transition("KNOWLEDGE", "R2")
    assert s.semantic_search_enabled()
    # K1 also requires the ACTIVE model to be verified, even when it has vectors for the target (SC31)
    s = activation.Site(installed=["R1", "R2"], active="R1", staged_models={"M1": {"verified": False, "vectors_for": {"R1", "R2"}}})
    with pytest.raises(activation.Refused):
        s.transition("KNOWLEDGE", "R2")
    assert not s.semantic_search_enabled()
    # M1 and M2: an unverified placeholder model is never activated; a verified one over lexical-only knowledge is
    s = activation.Site(installed=["L1"], active="L1", models=None, lexical_only={"L1"},
                        staged_models={"MX": {"verified": False, "vectors_for": set()}, "M2": {"verified": True, "vectors_for": set()}})
    with pytest.raises(activation.Refused):
        s.transition("MODELS", "MX")
    s.transition("MODELS", "M2")
    assert s.pointers["MODELS"] == "M2" and not s.semantic_search_enabled()
    # defaults reproduce the 2.0 behaviour (no lexical-only generations)
    s = activation.Site(installed=["R1", "R2"], active="R1")
    assert s.lexical_only == frozenset() and s.staged_models["M1"]["vectors_for"] == {"R1", "R2"}
