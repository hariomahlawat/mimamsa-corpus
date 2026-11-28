"""C16 Stage 3 S3-B: B04 kind-specific verifier reference (contract 2.1 additive item 11).

Samples are deterministic and seeded by the release id; vector packs are checked by trailer, recomputed keys, the 2.1
source digest, the result digest and a spot re-embed; the graph structural recheck catches non-builder values, dangling
edges and unresolved evidence. Sample sizes and tolerances stay UNCALIBRATED in every contract: production never runs
an uncalibrated sampled check (OD-C16-UNCALIBRATED-PRODUCTION), development records the development default.
"""
from __future__ import annotations

import copy
import hashlib
import json
import struct
from pathlib import Path

import pytest

from mimamsa_contract.c16 import components, digests, verification as V

V21 = Path(__file__).resolve().parents[1] / "fixtures" / "c16" / "v2_1"
MODEL = "ca456c06b3a9505ddfd9131408916dd79290368331e7d76bb621f1cba6bc8665"


def _j(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def test_golden_vectors_are_the_reference_output():
    assert _j(V21 / "component_verification" / "golden.json") == json.loads(json.dumps(V.golden_vectors()))


def test_samples_are_deterministic_seeded_by_release_and_check():
    members = [f"d{i}" for i in range(500)]
    a = V.seeded_sample("R1", "SAMPLED_REBUILD_PARITY", members, 20)
    assert a == V.seeded_sample("R1", "SAMPLED_REBUILD_PARITY", list(reversed(members)), 20)   # order-independent
    assert a == sorted(a) and len(a) == 20
    assert a != V.seeded_sample("R2", "SAMPLED_REBUILD_PARITY", members, 20)
    assert a != V.seeded_sample("R1", "SAMPLED_POSTINGS_REDERIVE", members, 20)
    assert V.seeded_sample("R1", "X", members[:5], 50) == sorted(members[:5])      # size >= population: all
    with pytest.raises(ValueError):
        V.seeded_sample("R1", "X", members, 0)


def test_stratified_sample_reaches_every_stratum_and_rejects_overlap():
    strata = {"act": [f"a{i}" for i in range(3)], "judgment": [f"j{i}" for i in range(300)], "rules": ["r0"]}
    s = V.stratified_sample("R1", "VECTOR_SPOT_REEMBED", strata, 6)
    assert len(s) == 6 and {"r0"} <= set(s) and any(x.startswith("a") for x in s) and any(x.startswith("j") for x in s)
    with pytest.raises(ValueError):
        V.stratified_sample("R1", "X", {"a": ["x"], "b": ["x"]}, 2)


def test_every_contract_sampled_check_stays_uncalibrated_and_production_never_runs_it():
    for kind in ("GRAPH", "LEXICAL_INDEX", "VECTOR_PACK"):
        c = _j(V21 / "component_contracts" / f"{kind}.json")
        assert components.uncalibrated(c), kind
        for chk in c["checks"]:
            if chk["check_id"] in components.SAMPLED:
                with pytest.raises(PermissionError):
                    V.effective_sample(chk, "production")
                e = V.effective_sample(chk, "development")
                assert e["size_source"] == "UNCALIBRATED_DEVELOPMENT_DEFAULT"
                assert e["size"] == V.DEVELOPMENT_DEFAULTS[chk["check_id"]]["size"]
            else:
                assert V.effective_sample(chk, "production")["size"] == "ALL"


def test_a_calibrated_contract_value_wins_in_both_modes():
    chk = copy.deepcopy(next(x for x in _j(V21 / "component_contracts" / "GRAPH.json")["checks"] if x["check_id"] == "SAMPLED_REBUILD_PARITY"))
    chk["sample"]["size"] = {"value": 7, "calibration_ref": "study-x"}
    chk["sample"]["tolerance"] = "EXACT"
    for mode in ("production", "development"):
        assert V.effective_sample(chk, mode) == {"size": 7, "tolerance": "EXACT", "size_source": "CONTRACT_CALIBRATED"}


def test_detection_probability_is_hypergeometric():
    assert V.detection_probability(100, 0, 10) == 0.0
    assert V.detection_probability(100, 1, 100) == 1.0
    assert V.detection_probability(100, 1, 10) == pytest.approx(0.1)
    assert V.detection_probability(10_000, 100, 64) == pytest.approx(1 - (1 - 0.01) ** 64, abs=2e-3)


# ------------------------------------------------------------------ vector packs

def _vec(seed: str, dim=4):
    h = hashlib.sha256(seed.encode()).digest()
    xs = [(b - 127.5) for b in h[:dim]]
    n = sum(x * x for x in xs) ** 0.5
    return struct.pack(f"<{dim}f", *[x / n for x in xs])


def _pack(inputs, mutate=None):
    entries = [(V.vector_key(MODEL, 256, s), _vec(s)) for s in inputs]
    if mutate:
        entries = mutate(entries)
    return V.write_mimvec(4, entries), entries


INPUTS = [f"passage: text {i} " + "x" * (i * 97 % 1400) for i in range(60)]
PIDS = [(f"p{i}", s) for i, s in enumerate(INPUTS)]


def _check(data, entries, embed=lambda s: _vec(s), params=None, size=60, tol=1e-6, src=None):
    keys = [V.vector_key(MODEL, 256, s) for s in INPUTS]
    return V.check_vector_pack(data, params or V.vector_params(MODEL, 4, 256), PIDS, release_id="R1",
                               declared_result_digest=digests.vector_pack_digest(entries),
                               declared_source_digest=src or V.vector_pack_source_digest(MODEL, 256, keys),
                               model_sha256=MODEL, sample_size=size, tolerance=tol, embed=embed)


def test_a_clean_pack_verifies():
    data, entries = _pack(INPUTS)
    r = _check(data, entries)
    assert r["status"] == "VERIFIED", r


def test_trailer_and_shape_corruption_is_refused():
    data, entries = _pack(INPUTS)
    bad = bytearray(data)
    bad[40] ^= 1
    assert _check(bytes(bad), entries)["checks"]["VECTOR_TRAILER"] == "FAIL"
    assert _check(data[:-1], entries)["checks"]["VECTOR_TRAILER"] == "FAIL"


def test_a_swapped_vector_with_intact_keys_is_caught_by_the_spot_reembed_when_sampled():
    def swap(entries):
        e = list(entries)
        e[0], e[1] = (e[0][0], e[1][1]), (e[1][0], e[0][1])
        return e
    data, entries = _pack(INPUTS, swap)
    r = _check(data, entries)                          # result digest re-pinned to the bad entries: digest matches
    assert r["checks"]["VECTOR_KEYS_RECOMPUTED"] == "PASS" and r["checks"]["RESULT_DIGEST"] == "PASS"
    assert r["checks"]["VECTOR_SPOT_REEMBED"] == "FAIL" and r["status"] == "FAILED"


def test_foreign_and_missing_keys_are_refused():
    data, entries = _pack(INPUTS[:-1] + ["passage: not in this generation"])
    r = _check(data, entries)
    assert r["checks"]["VECTOR_KEYS_RECOMPUTED"] == "FAIL" and r["status"] == "FAILED"


def test_a_mismatched_model_is_refused():
    data, entries = _pack(INPUTS)
    r = _check(data, entries, params=V.vector_params("0" * 64, 4, 256))
    assert r["checks"]["VECTOR_KEYS_RECOMPUTED"] == "FAIL" and r["status"] == "FAILED"


def test_without_a_model_the_spot_check_does_not_run_and_the_pack_is_not_verified():
    data, entries = _pack(INPUTS)
    r = _check(data, entries, embed=None)
    assert r["checks"]["VECTOR_SPOT_REEMBED"] == "NOT_RUN" and r["status"] == "FAILED"


def test_source_digest_binds_the_generation_passages():
    data, entries = _pack(INPUTS)
    r = _check(data, entries, src="0" * 64)
    assert r["checks"]["SOURCE_DIGEST_EQUALS_SITE"] == "FAIL"


# ------------------------------------------------------------------ graph

def _graph():
    nodes = [{"id": "INST:aa", "kind": "instrument", "label": "AA", "doc_id": "act-a", "held": True, "page": None, "family": "aa", "code": "AA"},
             {"id": "PROV:AA:s.1", "kind": "provision", "label": "s.1", "doc_id": "act-a", "held": True, "page": 2, "family": "aa", "code": "AA"},
             {"id": "PROC:x", "kind": "procedural_requirement", "label": "x", "doc_id": None, "held": True, "page": None, "family": None, "code": None}]
    edges = [{"id": "E1", "type": "CONTAINS_PROVISION", "from_id": "INST:aa", "to_id": "PROV:AA:s.1", "origin": "TOC", "source_doc_id": "act-a",
              "page": 2, "temporal_from": None, "temporal_from_status": "NOT_APPLICABLE", "temporal_to": None, "temporal_to_status": "NOT_APPLICABLE",
              "verification": "EXTRACTED_STRUCTURE", "review_state": "UNREVIEWED", "uncertainty": "u", "has_legal_effect": False}]
    return nodes, edges


def test_graph_structural_recheck():
    docs = {"act-a": {1, 2, 3}}
    nodes, edges = _graph()
    assert V.graph_structural_issues(nodes, edges, docs) == []
    e = copy.deepcopy(edges)
    e[0]["verification"] = "LEGAL_REVIEWED"
    assert V.graph_structural_issues(nodes, e, docs) == ["GRAPH_NOT_BUILDER_VALUE: E1"]
    e = copy.deepcopy(edges)
    e[0]["to_id"] = "PROV:AA:s.9"
    assert V.graph_structural_issues(nodes, e, docs) == ["GRAPH_DANGLING_EDGE: E1"]
    e = copy.deepcopy(edges)
    e[0]["page"] = 99
    assert V.graph_structural_issues(nodes, e, docs) == ["GRAPH_EVIDENCE_PAGE_UNRESOLVED: E1"]
    assert V.graph_structural_issues(nodes, edges, {}) != []
    assert V.graph_digest_of_rows("c15-graph-1", nodes, edges) == digests.graph_digest("c15-graph-1", [n["id"] for n in nodes], ["E1"])
