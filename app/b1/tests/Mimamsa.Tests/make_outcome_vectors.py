"""Write outcome_vectors.json: cases for the contract 2.1 activation-outcome rule (PR #82 1e3060de, C16-I21-01/02/03)
with the decision of the Python reference (mimamsa_contract.c16.components.activation_outcome). The .NET mirror
(Mimamsa.Core.Activation.ActivationOutcome) must reproduce every decision (C16DigestTests / C16Cp1OutcomeTests).
    python -I app/b1/tests/Mimamsa.Tests/make_outcome_vectors.py [--check]
"""
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / "app" / "contract"))
from mimamsa_contract.c16 import components  # noqa: E402

CONTRACTS = {k: json.loads((REPO / "app" / "contract" / "fixtures" / "c16" / "v2_1" / "component_contracts" / f"{k}.json").read_text(encoding="utf-8"))
             for k in components.ACCELERATOR_KINDS}


def calibrated(c):
    c = copy.deepcopy(c)
    for x in c["checks"]:
        if x["sample"]["size"] == "UNCALIBRATED":
            x["sample"]["size"] = {"value": 64, "calibration_ref": "CAL-FIXTURE-1"}
        if x["sample"]["tolerance"] == "UNCALIBRATED":
            x["sample"]["tolerance"] = {"value": 0.001, "calibration_ref": "CAL-FIXTURE-1"}
    return c


CAL = {k: calibrated(c) for k, c in CONTRACTS.items()}
LEX_ONLY = {"KNOWLEDGE_ROWS": "VERIFIED", "GRAPH": "VERIFIED", "LEXICAL_INDEX": "VERIFIED", "TEXT_STORE": "VERIFIED", "VECTOR_PACK": "MISSING"}
FULL = {**LEX_ONLY, "VECTOR_PACK": "VERIFIED"}


def rebuild(kind, **over):
    r = {"status": "VERIFIED", "builder": {"name": "site-builder", "version": "1", "commit": "abc1234"}, "source_digest": "a" * 64,
         "result_digest": "b" * 64, "checks": {c: "PASS" for c in components.REQUIRED_CHECKS[kind]}}
    r.update(over)
    return r


def without(c, check):
    c = copy.deepcopy(c)
    c["checks"] = [x for x in c["checks"] if x["check_id"] != check]
    return c


CASES = [
    ("lexical_only_development", LEX_ONLY, CONTRACTS, "development", None),
    ("lexical_only_production_uncalibrated", LEX_ONLY, CONTRACTS, "production", None),
    ("lexical_only_production_calibrated", LEX_ONLY, CAL, "production", None),
    ("full_production_calibrated", FULL, CAL, "production", None),
    ("full_production_uncalibrated", FULL, CONTRACTS, "production", None),
    ("full_development_uncalibrated", FULL, CONTRACTS, "development", None),
    ("text_store_failed_rebuilt_full", {**FULL, "TEXT_STORE": "FAILED"}, CAL, "production", {"TEXT_STORE": rebuild("TEXT_STORE")}),
    ("text_store_missing_rebuilt_lexical", {**LEX_ONLY, "TEXT_STORE": "MISSING"}, CONTRACTS, "development", {"TEXT_STORE": rebuild("TEXT_STORE")}),
    ("text_store_failed_no_rebuild", {**LEX_ONLY, "TEXT_STORE": "FAILED"}, CONTRACTS, "development", None),
    ("lexical_missing_no_rebuild", {**LEX_ONLY, "LEXICAL_INDEX": "MISSING"}, CONTRACTS, "development", None),
    ("lexical_omitted_counts_missing", {k: v for k, v in LEX_ONLY.items() if k != "LEXICAL_INDEX"}, CONTRACTS, "development", None),
    ("rebuild_with_failed_check", {**LEX_ONLY, "TEXT_STORE": "FAILED"}, CONTRACTS, "development",
     {"TEXT_STORE": rebuild("TEXT_STORE", checks={"SQLITE_QUICK_CHECK": "PASS", "TEXT_STORE_BIND_EXACT": "FAIL", "PAGE_HASH_ON_READ": "PASS"})}),
    ("rebuild_not_verified", {**LEX_ONLY, "GRAPH": "FAILED"}, CONTRACTS, "development", {"GRAPH": rebuild("GRAPH", status="FAILED")}),
    ("rebuild_without_provenance", {**LEX_ONLY, "GRAPH": "FAILED"}, CONTRACTS, "development", {"GRAPH": rebuild("GRAPH", builder={"name": "x", "version": "", "commit": "c"})}),
    ("rebuild_bad_digest", {**LEX_ONLY, "GRAPH": "FAILED"}, CONTRACTS, "development", {"GRAPH": rebuild("GRAPH", result_digest="XYZ")}),
    ("rebuild_for_vectors", LEX_ONLY, CONTRACTS, "development", {"VECTOR_PACK": {"status": "VERIFIED"}}),
    ("unknown_state", {**LEX_ONLY, "GRAPH": "OK"}, CONTRACTS, "development", None),
    ("unknown_kind", {**LEX_ONLY, "MODEL_FILE": "VERIFIED"}, CONTRACTS, "development", None),
    ("unknown_mode", LEX_ONLY, CONTRACTS, "staging", None),
    ("missing_contract", LEX_ONLY, {k: v for k, v in CONTRACTS.items() if k != "GRAPH"}, "development", None),
    ("contract_of_another_kind", LEX_ONLY, {**CONTRACTS, "GRAPH": CONTRACTS["LEXICAL_INDEX"]}, "development", None),
    ("contract_missing_required_check", LEX_ONLY, {**CONTRACTS, "TEXT_STORE": without(CONTRACTS["TEXT_STORE"], "PAGE_HASH_ON_READ")}, "development", None),
    ("vectors_failed_lexical", {**FULL, "VECTOR_PACK": "FAILED"}, CAL, "production", None),
    ("lexical_rebuilt_full_calibrated", {**FULL, "LEXICAL_INDEX": "FAILED"}, CAL, "production", {"LEXICAL_INDEX": rebuild("LEXICAL_INDEX")}),
]


def build():
    out = []
    for name, results, contracts, mode, rebuilds in CASES:
        out.append({"name": name, "results": results, "contracts": contracts, "mode": mode, "rebuilds": rebuilds,
                    "expected": components.activation_outcome(results, contracts, mode=mode, rebuilds=rebuilds)})
    return json.dumps(out, indent=1, sort_keys=True) + "\n"


if __name__ == "__main__":
    target = HERE / "outcome_vectors.json"
    text = build()
    if "--check" in sys.argv:
        same = target.read_text(encoding="utf-8") == text
        print("outcome vectors match the reference" if same else "outcome vectors DIFFER from the reference")
        sys.exit(0 if same else 1)
    target.write_text(text, encoding="utf-8", newline="\n")
    print(f"{len(CASES)} cases written")
