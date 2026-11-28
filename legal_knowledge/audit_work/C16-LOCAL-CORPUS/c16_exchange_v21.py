"""Build a fail-closed Cycle 16 producer exchange against the pinned Contract 2.1 reference.

The adapter is deliberately independent of OCR execution.  It consumes immutable
inventory/taxonomy/access evidence and can be rerun without OCR or conversion.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

CONTRACT = "mimamsa-corpus-contract/2.1"
RECORD_FILES = {
    "identities.jsonl": "document_identity",
    "anchors.jsonl": "evidence_anchor",
    "relationships.jsonl": "corpus_relationship",
    "taxonomy.jsonl": "taxonomy_node",
    "admissions.jsonl": "corpus_admission",
    "reviewed_records.jsonl": "reviewed_record",
}


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def jsonl_bytes(rows: list[dict]) -> bytes:
    return b"".join((json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8") for row in rows)


def _component(relative_path: str, label: str, basis: str) -> int:
    parts = relative_path.replace("\\", "/").split("/")
    if basis == "FILENAME_PATTERN":
        return -1
    for index, part in enumerate(parts[:-1]):
        if part == label:
            return index
    return max(0, len(parts) - 2)


def project_relationships(subject_rows: list[dict], provision_rows: list[dict], inventory_by_id: dict[str, dict],
                          identities_by_sha: dict[str, dict], classification) -> list[dict]:
    """Project every v5 relationship; never infer legal effect from a folder."""
    out = []
    for category, rows in (("classified_under_subject", subject_rows), ("associated_with_provision", provision_rows)):
        for raw in rows:
            inv = inventory_by_id.get(raw.get("inventory_id"))
            ident = identities_by_sha.get(raw.get("source_copy_sha256"))
            if inv is None or ident is None:
                raise ValueError(f"relationship lacks verified identity binding: {raw.get('relationship_id') or raw.get('inventory_id')}")
            label = raw.get("source_label") or "unlabelled"
            if category == "classified_under_subject":
                target = {"resolved": True, "node_id": raw["target_node_id"]}
                expansion = None
                uncertainty = "Owner folder classification is a navigation aid, not an established legal finding."
                rule = "C16-FOLDER-SUBJECT"
            else:
                node_id = raw["target_node_id"]
                target = ({"resolved": True, "node_id": node_id} if node_id.startswith(("PROV:AA-1950:", "PROV:AR-1954:"))
                          else {"resolved": False, "node_id": None, "raw_reference": label,
                                "unresolved": {"unresolved": "AMBIGUOUS_REFERENCE",
                                               "note": "instrument code is not in the Contract 2.1 registry"}})
                exp = raw.get("abbreviation_expansion") or {}
                expansion = ({"abbreviation": exp.get("abbreviation"), "expansion": exp.get("reading"),
                              "lexicon_ref": "C16-ABBREVIATION-LEXICON/2.0",
                              "alternatives": exp.get("alternatives") or []} if exp else None)
                uncertainty = "Provision association is an automated filename or folder candidate, not a legal finding."
                rule = "C16-PROVISION-NAVIGATION"
            out.append(classification(
                category, doc_id=ident["doc_id"], sha=raw["source_copy_sha256"],
                subject_node=ident["work_identity"]["graph_node_ref"], target=target,
                basis=raw.get("basis") or "FOLDER_PATH", collection="local:owner-corpus-c16",
                rel_path=raw["relative_path"], inventory_id=raw.get("inventory_id"),
                component=_component(raw["relative_path"], label, raw.get("basis") or "FOLDER_PATH"),
                matched=label, expansion=expansion, verification=raw.get("verification") or "CANDIDATE",
                uncertainty=uncertainty, rule=rule,
            ))
    return sorted(out, key=lambda row: row["relationship_id"])


def augment_taxonomy(taxonomy: list[dict], provision_rows: list[dict]) -> list[dict]:
    """Add only registry-valid statute/provision nodes referenced by preserved candidates."""
    nodes = {row["node_id"]: row for row in taxonomy}
    roots = {"AA-1950": ("Army Act", "SUBJ:local:army-act"),
             "AR-1954": ("Army Rules, 1954", "SUBJ:local:army-rules")}
    aliases: dict[str, set[str]] = {}
    for raw in provision_rows:
        node_id = raw["target_node_id"]
        if node_id.startswith(("PROV:AA-1950:", "PROV:AR-1954:")):
            aliases.setdefault(node_id, set()).add(raw.get("source_label") or node_id)
    for code, (label, parent) in roots.items():
        if any(node.startswith(f"PROV:{code}:") for node in aliases):
            if parent not in nodes:
                raise ValueError(f"missing owner-folder taxonomy parent for {code}: {parent}")
            nodes[f"INST:{code}"] = {
                "contract": "mimamsa-corpus-contract/2.0", "record_kind": "taxonomy_node",
                "node_id": f"INST:{code}", "level": "STATUTE", "label": label, "parent_ids": [parent],
                "instrument_code": code, "provision": None, "maps_to_subject": None, "aliases": [],
                "taxonomy_version": "c16-taxonomy-1.1", "source": {"basis": "GRAPH_INSTRUMENT"},
                "verification": "CANDIDATE",
            }
    for node_id, found_aliases in aliases.items():
        _, code, unit = node_id.split(":", 2)
        prefix, number = unit.split(".", 1)
        nodes[node_id] = {
            "contract": "mimamsa-corpus-contract/2.0", "record_kind": "taxonomy_node", "node_id": node_id,
            "level": "PROVISION", "label": f"{prefix}. {number}", "parent_ids": [f"INST:{code}"],
            "instrument_code": code, "provision": {"prefix": prefix, "number": number, "sub_provision": None},
            "maps_to_subject": None, "aliases": sorted(found_aliases), "taxonomy_version": "c16-taxonomy-1.1",
            "source": {"basis": "GRAPH_PROVISION"}, "verification": "CANDIDATE",
        }
    return list(nodes.values())


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build(args) -> dict:
    contract_python = Path(args.contract_root) / "app" / "contract"
    sys.path.insert(0, str(contract_python))
    from mimamsa_contract.c16 import adapters, canonical, rules

    inventory = load_jsonl(Path(args.inventory))
    projected = adapters.from_pr76_inventory(
        inventory, collection="local:owner-corpus-c16", corpus_generation_id=args.generation_id)
    identities_by_sha = {row["source_copy"]["sha256"]: row for row in projected["identities"]}
    inventory_by_id = {row["inventory_id"]: row for row in inventory}
    subject_rows = load_jsonl(Path(args.subject_relationships))
    provision_rows = load_jsonl(Path(args.provision_relationships))
    projected["relationships"] = project_relationships(
        subject_rows, provision_rows,
        inventory_by_id, identities_by_sha, adapters._classification)
    projected["taxonomy"] = augment_taxonomy(projected["taxonomy"], provision_rows)
    projected["anchors"] = []
    projected["reviewed_records"] = []

    output = Path(args.output)
    exchange = output / "exchange"
    exchange.mkdir(parents=True, exist_ok=True)
    populations = {
        "identities.jsonl": projected["identities"], "anchors.jsonl": projected["anchors"],
        "relationships.jsonl": projected["relationships"], "taxonomy.jsonl": projected["taxonomy"],
        "admissions.jsonl": projected["admissions"], "reviewed_records.jsonl": projected["reviewed_records"],
    }
    files = {}
    manifest_files = []
    for name, rows in populations.items():
        data = canonical.dumps_jsonl(rows)
        (exchange / name).write_bytes(data)
        files[name] = data
        manifest_files.append({"path": name, "record_kind": RECORD_FILES[name], "records": len(rows), "sha256": _sha(data)})
    manifest = {
        "contract": CONTRACT, "record_kind": "corpus_generation_manifest",
        "corpus_generation_id": args.generation_id, "built_at": None,
        "files": sorted(manifest_files, key=lambda row: row["path"]),
        "pinned_inputs": {
            "git": [{"commit": args.contract_commit, "purpose": "contract, schemas and validation"}],
            "hf": [], "restricted_register_sha256": args.restricted_register_sha256,
            "tools": [{"name": "c16-exchange-producer", "version": "2.1.0", "commit": args.producer_commit,
                       "config_sha256": None}],
        },
        "registries": {"instrument_codes": sorted(adapters.ABBREVIATIONS[k]["code"] for k in adapters.ABBREVIATIONS if adapters.ABBREVIATIONS[k]["code"]),
                       "external_judgments": []},
    }
    manifest_data = (json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    (exchange / "GENERATION.json").write_bytes(manifest_data)
    files["GENERATION.json"] = manifest_data
    issues = rules.exchange_issues(files, mode="strict")
    report = {"contract_commit": args.contract_commit, "population_counts": {k: len(v) for k, v in populations.items()},
              "validation_issues": [str(issue) for issue in issues], "strict_valid": not issues}
    (output / "PRODUCER_VALIDATION_REPORT.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--contract-root", required=True); p.add_argument("--contract-commit", required=True)
    p.add_argument("--inventory", required=True); p.add_argument("--subject-relationships", required=True)
    p.add_argument("--provision-relationships", required=True); p.add_argument("--output", required=True)
    p.add_argument("--generation-id", required=True); p.add_argument("--producer-commit", required=True)
    p.add_argument("--restricted-register-sha256", required=True)
    return p.parse_args(argv)


def main(argv=None):
    report = build(parse_args(argv))
    print(json.dumps(report, indent=2))
    return 0 if report["strict_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
