#!/usr/bin/env python3
"""Score ordered synthetic passage IDs. See retrieval-ux.md for the input contract."""

import argparse
import json
import math
import statistics
import sys
from pathlib import Path


def load(path):
    with path.open(encoding="utf-8") as source:
        return json.load(source)


def catalogue(fixture):
    members = {}
    for document in fixture["documents"]:
        for page in document["pages"]:
            key = page["id"]
            if key in members:
                raise ValueError(f"duplicate passage in fixture: {key}")
            members[key] = document["publication"]
    cases = {case["id"]: case for case in fixture["queries"]}
    if len(cases) != len(fixture["queries"]):
        raise ValueError("duplicate case in fixture")
    for case in cases.values():
        grades = case["relevance"]
        if any(grade not in (1, 2, 3) for grade in grades.values()):
            raise ValueError(f"{case['id']}: grades must be 1, 2 or 3")
        mandatory = case.get("must_at", {}).values()
        target_ids = set(grades) | set(case.get("top1", []))
        for window in mandatory:
            target_ids.update(window)
        if any(members.get(key) != "published" for key in target_ids):
            raise ValueError(f"{case['id']}: unknown or hidden positive passage")
        forbidden = set(case.get("forbidden", []))
        if forbidden - members.keys() or target_ids & forbidden:
            raise ValueError(f"{case['id']}: inconsistent prohibited passage")
        if (case.get("empty") or case.get("exclusive_state")) and target_ids:
            raise ValueError(f"{case['id']}: empty/error case has positives")
    return members, cases


def dcg(grades):
    return sum((2**grade - 1) / math.log2(rank + 1)
               for rank, grade in enumerate(grades, start=1))


def metrics(ranking, relevance, identifier):
    if not relevance:
        return {}
    grades = [relevance.get(key, 0) for key in ranking]
    values = {
        "recall@10": sum(grade > 0 for grade in grades[:10]) / len(relevance),
        "recall@20": sum(grade > 0 for grade in grades[:20]) / len(relevance),
        "precision@5": sum(grade > 0 for grade in grades[:5]) / 5,
        "MRR@20": next((1 / rank for rank, grade in enumerate(grades[:20], 1) if grade), 0.0),
        "nDCG@10": dcg(grades[:10]) / dcg(sorted(relevance.values(), reverse=True)[:10]),
    }
    if identifier:
        values["exact_precision@5"] = sum(grade >= 2 for grade in grades[:5]) / 5
        values["exact_MRR@20"] = next(
            (1 / rank for rank, grade in enumerate(grades[:20], 1) if grade >= 2), 0.0
        )
    return values


def score(fixture, observations):
    members, cases = catalogue(fixture)
    if not isinstance(observations, dict):
        raise ValueError("observations must map case IDs to result objects")
    if observations.keys() != cases.keys():
        raise ValueError(f"case coverage mismatch, missing={sorted(cases.keys() - observations.keys())}, "
                         f"unknown={sorted(observations.keys() - cases.keys())}")
    outcomes = {}
    for case_id, case in cases.items():
        observation = observations[case_id]
        if not isinstance(observation, dict) or not isinstance(observation.get("ranking"), list):
            raise ValueError(f"{case_id}: expected result object with a ranking list")
        ranking = observation["ranking"]
        if len(ranking) > 20 or any(not isinstance(key, str) for key in ranking):
            raise ValueError(f"{case_id}: expected up to 20 passage ID strings")
        state = observation.get("state")
        if state not in ("results", "empty", "parser_error"):
            raise ValueError(f"{case_id}: unknown or missing observation state")
        errors = []
        expected_state = case.get("exclusive_state") or ("empty" if case.get("empty") else "results")
        if state != expected_state or bool(ranking) != (state == "results"):
            errors.append(f"expected consistent {expected_state} state")
        if observation.get("mode") != case["mode"]:
            errors.append(f"expected mode {case['mode']}")
        if len(set(ranking)) != len(ranking):
            errors.append("duplicate ranked passage")
        unexpected = set(ranking) & set(case.get("forbidden", []))
        if unexpected:
            errors.append(f"prohibited passages: {sorted(unexpected)}")
        hidden = {key for key in ranking if members.get(key) != "published"}
        if hidden:
            errors.append(f"unknown or unpublished passages: {sorted(hidden)}")
        if "top1" in case and (not ranking or ranking[0] not in case["top1"]):
            errors.append("first passage did not match an allowed exact or preferred hit")
        for depth, required in case.get("must_at", {}).items():
            missing = set(required) - set(ranking[:int(depth)])
            if missing:
                errors.append(f"missing at rank {depth}: {sorted(missing)}")
        outcomes[case_id] = {
            "errors": errors,
            "metrics": metrics(list(dict.fromkeys(ranking)), case["relevance"],
                               case["mode"] == "identifier"),
        }
    all_metrics = [outcome["metrics"] for outcome in outcomes.values()]
    metric_names = sorted({key for row in all_metrics for key in row})
    aggregate = {
        name: {"macro": statistics.mean(row[name] for row in all_metrics if name in row),
               "n": sum(name in row for row in all_metrics)} for name in metric_names
    }
    return {"cases": outcomes, "aggregate": aggregate,
            "passed": sum(not row["errors"] for row in outcomes.values()), "total": len(outcomes)}


def self_test(fixture):
    observations = {}
    for case in fixture["queries"]:
        ranking = sorted(case["relevance"], key=lambda key: -case["relevance"][key])
        observations[case["id"]] = {
            "mode": case["mode"],
            "state": case.get("exclusive_state") or ("results" if ranking else "empty"),
            "ranking": ranking,
        }
    result = score(fixture, observations)
    assert result["passed"] == result["total"] == 14, result
    assert result["aggregate"]["recall@20"] == {"macro": 1, "n": 12}, result
    assert result["aggregate"]["nDCG@10"] == {"macro": 1, "n": 12}, result
    mutations = {
        "RET-01": {"ranking": ["A-117"]},
        "RET-03": {"ranking": ["J2-QUOTE"]},
        "RET-05": {"ranking": ["M-SYN", "M-SYN", "M-NEAR"]},
        "RET-07": {"ranking": ["J2-MAJ"], "mode": "lexical"},
        "RET-09": {"ranking": ["L-EN"]},
        "RET-10": {"ranking": ["J1-DISS", "J1-SUB"]},
        "RET-11": {"ranking": ["V-WITHDRAWN"], "state": "results"},
        "RET-13": {"state": "empty"},
    }
    for case_id, change in mutations.items():
        observations[case_id].update(change)
    observed = score(fixture, observations)
    assert {case_id for case_id, row in observed["cases"].items() if row["errors"]} == mutations.keys()
    print(f"ORACLE SELF-TEST ONLY: {result['passed']}/{result['total']} ideal cases and "
          f"{len(mutations)}/{len(mutations)} negative mutations behaved as expected")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path,
                        default=Path(__file__).with_name("retrieval-dev-fixture.json"))
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument("--observations", type=Path)
    args = parser.parse_args()
    try:
        fixture = load(args.fixture)
        if args.self_test:
            self_test(fixture)
            return 0
        result = score(fixture, load(args.observations))
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"Invalid scorer input: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] == result["total"] else 1


if __name__ == "__main__":
    sys.exit(main())
