"""Build a fail-closed Cycle 16 producer exchange against the pinned Contract 2.1 reference.

The adapter is deliberately independent of OCR execution.  It consumes immutable
inventory/taxonomy/access evidence and can be rerun without OCR or conversion.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
import c16_ocr

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


def join_access_decisions(inventory: list[dict], access_rows: list[dict]) -> list[dict]:
    by_id = {}
    for decision in access_rows:
        key = decision.get("inventory_id")
        if not key or key in by_id:
            raise ValueError(f"duplicate or missing access inventory id: {key}")
        by_id[key] = decision
    if set(by_id) != {row.get("inventory_id") for row in inventory}:
        raise ValueError("access register is not a one-to-one inventory join")
    joined = []
    for row in inventory:
        decision = by_id[row["inventory_id"]]
        if decision.get("source_sha256") != row.get("sha256"):
            raise ValueError(f"access source hash mismatch: {row['inventory_id']}")
        joined.append({**row, **decision})
    return joined


def partition_transferable(inventory: list[dict]) -> tuple[list[dict], list[dict]]:
    held_sha = {row["sha256"] for row in inventory
                if row.get("document_access_disposition") != "SCREENED_NO_MARKING_DETECTED"}
    quarantine = [row for row in inventory if row["sha256"] in held_sha]
    transferable = [row for row in inventory if row["sha256"] not in held_sha]
    for row in transferable:
        row.pop("derivative_withheld_reason", None)
    return transferable, quarantine


def _component(relative_path: str, label: str, basis: str) -> int:
    parts = relative_path.replace("\\", "/").split("/")
    if basis == "FILENAME_PATTERN":
        return -1
    for index, part in enumerate(parts[:-1]):
        if part == label:
            return index
    return max(0, len(parts) - 2)


def contract_provision_id(node_id: str) -> str:
    if not node_id.startswith("PROV:"):
        return node_id
    head, unit = node_id.rsplit(":", 1)
    prefix, number = unit.split(".", 1)
    return f"{head}:{prefix}.{number.split('(', 1)[0]}"


def project_relationships(subject_rows: list[dict], provision_rows: list[dict], inventory_by_id: dict[str, dict],
                          identities_by_sha: dict[str, dict], classification) -> list[dict]:
    """Project every v5 relationship; never infer legal effect from a folder."""
    out = []
    combined = {}
    for raw in subject_rows + provision_rows:
        key = (raw.get("inventory_id"), raw.get("target_node_id"), raw.get("relative_path"))
        combined[key] = raw
    for raw in combined.values():
            category = "associated_with_provision" if raw["target_node_id"].startswith("PROV:") else "classified_under_subject"
            inv = inventory_by_id.get(raw.get("inventory_id"))
            ident = identities_by_sha.get(raw.get("source_copy_sha256"))
            if inv is not None and ident is None and (inv.get("restricted") or inv.get("document_access_disposition") != "SCREENED_NO_MARKING_DETECTED"):
                continue
            if inv is None or ident is None:
                raise ValueError(f"relationship lacks verified identity binding: {raw.get('relationship_id') or raw.get('inventory_id')}")
            label = raw.get("source_label") or "unlabelled"
            if category == "classified_under_subject":
                target = {"resolved": True, "node_id": raw["target_node_id"]}
                expansion = None
                uncertainty = "Owner folder classification is a navigation aid, not an established legal finding."
                rule = "C16-FOLDER-SUBJECT"
            else:
                node_id = contract_provision_id(raw["target_node_id"])
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


def v5_subject_taxonomy(nodes: list[dict], subject_rows: list[dict]) -> list[dict]:
    paths = {}
    for row in subject_rows:
        if row["target_node_id"].startswith("SUBJ:"):
            paths.setdefault(row["target_node_id"], row["relative_path"].replace("\\", "/").rsplit("/", 1)[0])
    out = []
    for node in nodes:
        if not node["node_id"].startswith("SUBJ:"):
            continue
        out.append({"contract": "mimamsa-corpus-contract/2.0", "record_kind": "taxonomy_node",
                    "node_id": node["node_id"], "level": "SUBJECT", "label": node["label"],
                    "parent_ids": node.get("parent_ids") or [], "instrument_code": None, "provision": None,
                    "maps_to_subject": None, "aliases": [], "taxonomy_version": "c16-taxonomy-1.1",
                    "source": {"basis": "OWNER_FOLDER", "collection": "local:owner-corpus-c16",
                               "relative_path": paths.get(node["node_id"], node.get("original_label") or node["label"])},
                    "verification": "CURATED_NAVIGATION"})
    return out


def augment_taxonomy(taxonomy: list[dict], provision_rows: list[dict]) -> list[dict]:
    """Add only registry-valid statute/provision nodes referenced by preserved candidates."""
    nodes = {row["node_id"]: row for row in taxonomy}
    roots = {"AA-1950": ("Army Act", "SUBJ:local:army-act"),
             "AR-1954": ("Army Rules, 1954", "SUBJ:local:army-rules")}
    aliases: dict[str, set[str]] = {}
    for raw in provision_rows:
        node_id = contract_provision_id(raw["target_node_id"])
        if node_id.startswith(("PROV:AA-1950:", "PROV:AR-1954:")):
            aliases.setdefault(node_id, set()).add(raw.get("source_label") or node_id)
    for code, (label, parent) in roots.items():
        if any(node.startswith(f"PROV:{code}:") for node in aliases):
            if parent not in nodes:
                raise ValueError(f"missing owner-folder taxonomy parent for {code}: {parent}")
            nodes[f"INSTCODE:{code}"] = {
                "contract": "mimamsa-corpus-contract/2.0", "record_kind": "taxonomy_node",
                "node_id": f"INSTCODE:{code}", "level": "STATUTE", "label": label, "parent_ids": [parent],
                "instrument_code": code, "provision": None, "maps_to_subject": None, "aliases": [],
                "taxonomy_version": "c16-taxonomy-1.1", "source": {"basis": "GRAPH_INSTRUMENT"},
                "verification": "CANDIDATE",
            }
    for node_id, found_aliases in aliases.items():
        _, code, unit = node_id.split(":", 2)
        prefix, number = unit.split(".", 1)
        nodes[node_id] = {
            "contract": "mimamsa-corpus-contract/2.0", "record_kind": "taxonomy_node", "node_id": node_id,
            "level": "PROVISION", "label": f"{prefix}. {number}", "parent_ids": [f"INSTCODE:{code}"],
            "instrument_code": code, "provision": {"prefix": prefix, "number": number, "sub_provision": None},
            "maps_to_subject": None, "aliases": sorted(found_aliases), "taxonomy_version": "c16-taxonomy-1.1",
            "source": {"basis": "GRAPH_PROVISION"}, "verification": "CANDIDATE",
        }
    return list(nodes.values())


def prune_taxonomy(taxonomy: list[dict], relationships: list[dict]) -> list[dict]:
    nodes={row["node_id"]:row for row in taxonomy}
    keep={row["target"]["node_id"] for row in relationships if row.get("target",{}).get("resolved") and row["target"].get("node_id") in nodes}
    pending=list(keep)
    while pending:
        node=pending.pop()
        for parent in nodes[node].get("parent_ids") or []:
            if parent in nodes and parent not in keep:keep.add(parent);pending.append(parent)
    return [nodes[key] for key in sorted(keep)]


def load_state_tree(root: Path) -> list[dict]:
    state = root / "state"
    return [json.loads(path.read_text(encoding="utf-8")) for path in sorted(state.rglob("*.json"))]


def enrich_image_ocr(inventory: list[dict], primary: list[dict], secondary: list[dict], accepted_configs: set[str] | None = None) -> None:
    """Bind embedded-image status to verified v2 evidence, preferring a readable targeted retry."""
    grouped={}
    for row in primary+secondary:
        if accepted_configs is None or row.get("configuration_sha256") in accepted_configs:
            grouped.setdefault(row["image_sha256"],[]).append(row)
    for document in inventory:
        for image in document.get("embedded_images") or []:
            candidates=grouped.get(image["image_sha256"],[])
            if any(row.get("access_disposition")=="HELD_ACCESS_MARKING_REVIEW" for row in candidates):
                image["ocr_state"]="FAILED";image.pop("ocr_derivative_sha256",None);continue
            evidence = next((row for row in reversed(candidates) if row.get("state")=="COMPLETE" and row.get("evidence_verified") is True and not row.get("unreadable")),None)
            if evidence is None:
                image["ocr_state"] = "FAILED" if candidates else "QUEUED"
                image.pop("ocr_derivative_sha256", None)
            elif (not evidence.get("unreadable")
                  and evidence.get("access_disposition") == "SCREENED_NO_MARKING_DETECTED"
                  and (evidence.get("artifact_sha256") or {}).get("raw_text")):
                image["ocr_state"] = "DONE"
                image["ocr_derivative_sha256"] = evidence["artifact_sha256"]["raw_text"]
            else:
                image["ocr_state"] = "FAILED"
                image.pop("ocr_derivative_sha256", None)


def pdf_anchors(records: list[dict], root: Path, config: dict, identities_by_sha: dict[str, dict], canonical,
                derivative_root: Path | None = None) -> list[dict]:
    """Export clean verified pages, grouped into one deterministic OCR derivative per source PDF."""
    verified: dict[str, list[tuple[dict, bytes]]] = {}
    expected_config=config.get("configuration_sha256")
    seen=set()
    for record in records:
        key=(record.get("source_sha256"),record.get("physical_page"))
        if None not in key:
            if key in seen:raise ValueError(f"duplicate PDF page evidence: {key}")
            seen.add(key)
        if not (record.get("state") == "COMPLETE" and record.get("evidence_verified") is True
                and not record.get("unreadable")
                and record.get("access_disposition") == "SCREENED_NO_MARKING_DETECTED"
                and record.get("configuration_sha256")==expected_config):
            continue
        sha = record.get("source_sha256")
        if sha != record.get("verified_source_sha256") or sha not in identities_by_sha:
            continue
        if not c16_ocr.validate_record_artifacts(root,record):continue
        rel = (record.get("artifact_paths") or {}).get("raw_text")
        expected = (record.get("artifact_sha256") or {}).get("raw_text")
        if not rel or not expected:
            continue
        payload = (root / rel).read_bytes()
        if _sha(payload) == expected:
            verified.setdefault(sha, []).append((record, payload))
    out = []
    for sha, pages in verified.items():
        pages.sort(key=lambda item: item[0]["physical_page"])
        chunks, spans, offset = [], [], 0
        for record, payload in pages:
            header = f"[[page {record['physical_page']}]]\n".encode("utf-8")
            chunk = header + payload + b"\n"
            chunks.append(chunk)
            spans.append((record, payload, offset + len(header), offset + len(header) + len(payload.decode("utf-8"))))
            offset += len(chunk.decode("utf-8"))
        combined = b"".join(chunks)
        derivative_sha = _sha(combined)
        if derivative_root is not None:
            derivative_root.mkdir(parents=True, exist_ok=True)
            (derivative_root / f"{derivative_sha}.txt").write_bytes(combined)
        identity = identities_by_sha[sha]
        first = pages[0][0]
        ocr_config = {"engine": config["engine"], "engine_version": config["engine_version"],
                      "languages": config["languages"], "page_segmentation_mode": str(config["psm"][0]),
                      "preprocessing": config["preprocessing"], "dpi": config["render_dpi"],
                      "config_sha256": first["configuration_sha256"]}
        derivative_id = f"{identity['doc_id']}@c16-pdf-page-ocr/2.1.0"
        identity.setdefault("text_derivatives", []).append({
            "derivative_id": derivative_id, "pipeline_name": "c16-pdf-page-ocr", "pipeline_version": "2.1.0",
            "derivative_text_sha256": derivative_sha, "pagination_basis": "GENERATED_SEGMENT",
            "methods": ["OCR_PAGE_IMAGE"], "ocr_config": ocr_config, "text_reliability": "not_assessed",
            "quoting_permitted": False,
            "coverage": {"units_total": len(pages), "units_with_text": len(pages),
                         "images_total": 0, "images_text_extracted": 0}})
        for record, payload, start, end in spans:
            mean = record.get("mean_confidence")
            anchor = {
                "contract": "mimamsa-corpus-contract/2.0", "record_kind": "evidence_anchor", "anchor_id": "",
                "doc_id": identity["doc_id"], "original_sha256": sha, "representation_sha256": sha,
                "derivative_text_sha256": derivative_sha, "image_sha256": record["render_sha256"],
                "locator": {"kind": "SOURCE_PHYSICAL_PAGE", "physical_page": record["physical_page"],
                            "printed_page_label": None, "citable_as_source_page": True},
                "text_span": {"passage_id": None, "char_start": start, "char_end": end,
                              "text_sha256": _sha(payload)}, "bbox": None,
                "extraction": {"method": "OCR_PAGE_IMAGE", "pipeline_name": "c16-pdf-page-ocr",
                               "pipeline_version": "2.1.0", "ocr_config": ocr_config},
                "quality": {"text_reliability": "not_assessed", "ocr_mean_confidence": mean,
                            "low_confidence": bool(mean is None or mean < 60)},
                "verification": {"state": "AUTOMATED_CANDIDATE_NOT_VERIFIED", "review_ref": None},
                "quoting_permitted": False, "quote": None}
            anchor["anchor_id"] = canonical.anchor_id(anchor)
            out.append(anchor)
    return out


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def checked_revision(root: Path, expected: str) -> str:
    actual=subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],check=True,capture_output=True,text=True).stdout.strip()
    if actual!=expected:raise ValueError(f"revision mismatch at {root}: {actual} != {expected}")
    return actual


def consumer_dry_run(exchange: Path, rules, accounting, contract_accounting) -> dict:
    files={path.name:path.read_bytes() for path in exchange.iterdir() if path.is_file()}
    issues=[str(x) for x in rules.exchange_issues(files,mode="strict")]
    accounting_bytes=(exchange.parent/"registers"/"source_accounting.json").read_bytes()
    canonical=contract_accounting.register_bytes(accounting)
    if accounting_bytes!=canonical:issues.append("source accounting bytes are not normative canonical bytes")
    issues += [str(x) for x in contract_accounting.accounting_issues(accounting)]
    admissions=[json.loads(line) for line in files["admissions.jsonl"].decode("utf-8").splitlines() if line]
    if any(row.get("application_eligible") for row in admissions):issues.append("dry run refuses eligible admission")
    return {"mode":"CONSUMER_HELD_ONLY_DRY_RUN","files_read":len(files),"admissions":len(admissions),
            "eligible":sum(bool(row.get("application_eligible")) for row in admissions),"issues":issues,"accepted":not issues}


def build(args) -> dict:
    contract_python = Path(args.contract_root) / "app" / "contract"
    sys.path.insert(0, str(contract_python))
    from mimamsa_contract.c16 import accounting as contract_accounting, adapters, canonical, rules
    from mimamsa_contract.c16.schemas import schema_errors

    checked_revision(Path(args.contract_root),args.contract_commit)
    checked_revision(Path(args.producer_root),args.producer_commit)

    physical_inventory = load_jsonl(Path(args.inventory))
    if args.identity_assessment:
        assessed = {row["inventory_id"]: row for row in load_jsonl(Path(args.identity_assessment))}
        physical_inventory = [{**row, **assessed.get(row["inventory_id"], {})} for row in physical_inventory]
    if not args.access_register:
        raise ValueError("--access-register is required for a transferable package")
    joined = join_access_decisions(physical_inventory, load_jsonl(Path(args.access_register)))
    inventory, quarantine = partition_transferable(joined)
    source=Path(args.source)
    primary_valid=[];secondary_valid=[]
    if args.primary_image_register:
        jobs_by_hash,_=c16_ocr.image_jobs(physical_inventory,source);jobs=list(jobs_by_hash.values())
        primary_cfg=c16_ocr.load_verified_configuration(args.primary_image_root)
        primary_valid=c16_ocr.validate_evidence_population(args.primary_image_root,load_jsonl(Path(args.primary_image_register)),jobs,primary_cfg,"image_sha256",args.verification_workers)
        if args.secondary_image_register:
            secondary_cfg=c16_ocr.load_verified_configuration(args.secondary_image_root)
            secondary_jobs=c16_ocr.second_pass_candidates(jobs_by_hash,primary_valid)
            secondary_valid=c16_ocr.validate_evidence_population(args.secondary_image_root,load_jsonl(Path(args.secondary_image_register)),secondary_jobs,secondary_cfg,"image_sha256",args.verification_workers)
        enrich_image_ocr(inventory,primary_valid,secondary_valid,{primary_cfg["configuration_sha256"],*( [secondary_cfg["configuration_sha256"]] if args.secondary_image_register else [])})
    projected = adapters.from_pr76_inventory(
        inventory, collection="local:owner-corpus-c16", corpus_generation_id=args.generation_id)
    identities_by_sha = {row["source_copy"]["sha256"]: row for row in projected["identities"]}
    inventory_by_id = {row["inventory_id"]: row for row in joined}
    subject_rows = load_jsonl(Path(args.subject_relationships))
    provision_rows = load_jsonl(Path(args.provision_relationships))
    projected["relationships"] = project_relationships(
        subject_rows, provision_rows,
        inventory_by_id, identities_by_sha, adapters._classification)
    taxonomy_nodes = json.loads(Path(args.legal_taxonomy).read_text(encoding="utf-8"))["nodes"]
    projected["taxonomy"] = prune_taxonomy(
        augment_taxonomy(v5_subject_taxonomy(taxonomy_nodes, subject_rows), provision_rows),
        projected["relationships"])
    projected["anchors"] = []
    output = Path(args.output)
    if args.pdf_ocr_root:
        pdf_root = Path(args.pdf_ocr_root)
        config = c16_ocr.load_verified_configuration(pdf_root)
        jobs=c16_ocr.pdf_page_jobs(physical_inventory,source)
        pdf_records=c16_ocr.validate_evidence_population(pdf_root,load_jsonl(Path(args.pdf_register)),jobs,config,"page_key",args.verification_workers)
        pdf_records=[row for row in pdf_records if row.get("source_sha256") in identities_by_sha]
        projected["anchors"] += pdf_anchors(pdf_records, pdf_root, config, identities_by_sha, canonical,
                                            output / "derivatives")
    projected["reviewed_records"] = []

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
    registers = output / "registers"
    (registers / "receipts").mkdir(parents=True, exist_ok=True)
    decisions = {}
    for admission in projected["admissions"]:
        decisions[admission["decision"]] = decisions.get(admission["decision"], 0) + 1
    rejected = sum(count for decision, count in decisions.items() if decision.startswith(("REJECTED_", "EXCLUDED_")))
    quarantined = sum(count for decision, count in decisions.items() if decision.startswith("QUARANTINED_"))
    held = len(projected["admissions"]) - rejected - quarantined
    accounting = {
        "contract": CONTRACT, "record_kind": "source_admission_accounting",
        "release_id": f"R16-c16-v5-20261128-{args.producer_commit[:8]}", "scope": "DECLARED_BY_BUILD",
        "sources": [{"source": f"c16:{args.generation_id}", "path": "C16",
                     "provenance": {"generation_manifest_sha256": _sha(manifest_data),
                                    "hf_repo": args.hf_repo, "hf_revision": args.hf_revision,
                                    "candidate_set_sha256": None},
                     "input": len(projected["identities"]), "identities": len(projected["identities"]),
                     "effective_admissions": len(projected["admissions"]), "by_decision": decisions,
                     "held": held, "rejected": rejected, "quarantined": quarantined,
                     "eligible": 0, "served": 0, "not_served_reasons": decisions}]}
    accounting_data = contract_accounting.register_bytes(accounting)
    (registers / "source_accounting.json").write_bytes(accounting_data)
    candidates = b"".join((row["source_copy"]["sha256"] + "\n").encode("ascii") for row in sorted(projected["identities"], key=lambda r: r["source_copy"]["sha256"]))
    (registers / "exact_candidate_set.sha256").write_bytes(candidates)
    source_candidates = b"".join((sha + "\n").encode("ascii") for sha in sorted({row["sha256"] for row in physical_inventory}))
    receipt_register = {"contract": CONTRACT, "application_eligible_admissions": 0, "typed_gate_receipts": 0,
                        "reason": "All producer admissions are held or rejected; Contract 2.1 requires no gate receipt artefacts for ineligible admissions."}
    (registers / "TYPED_GATE_RECEIPT_REGISTER.json").write_text(json.dumps(receipt_register, indent=2), encoding="utf-8")
    input_files={"inventory":Path(args.inventory),"access_register":Path(args.access_register),
                 "primary_image_register":Path(args.primary_image_register),"secondary_image_register":Path(args.secondary_image_register),
                 "pdf_register":Path(args.pdf_register),"taxonomy":Path(args.legal_taxonomy)}
    safe_inputs={name:{"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"bytes":path.stat().st_size}
                 for name,path in input_files.items()}
    safe_manifest={"contract_commit":args.contract_commit,"producer_commit":args.producer_commit,"inputs":safe_inputs}
    (output/"SAFE_INPUT_MANIFEST.json").write_text(json.dumps(safe_manifest,sort_keys=True,indent=2),encoding="utf-8")
    quarantine_output=Path(args.quarantine_output)
    quarantine_output.mkdir(parents=True,exist_ok=True)
    quarantine_summary={"physical_sources":len(physical_inventory),"transferable_sources":len(inventory),
                        "quarantined_sources":len(quarantine),
                        "by_disposition":{d:sum(r.get("document_access_disposition")==d for r in quarantine)
                                          for d in sorted({r.get("document_access_disposition") for r in quarantine})}}
    (quarantine_output/"LOCAL_QUARANTINE_SUMMARY.json").write_text(json.dumps(quarantine_summary,indent=2),encoding="utf-8")
    dry_run=consumer_dry_run(exchange,rules,accounting,contract_accounting)
    (output/"CONSUMER_DRY_RUN.json").write_text(json.dumps(dry_run,indent=2),encoding="utf-8")
    inventory_files=[]
    for path in sorted(p for p in output.rglob("*") if p.is_file() and p.name not in ("TRANSFER_SHA256SUMS","PRODUCER_VALIDATION_REPORT.json")):
        inventory_files.append({"path":path.relative_to(output).as_posix(),"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"bytes":path.stat().st_size})
    sums="".join(f"{row['sha256']}  {row['path']}\n" for row in inventory_files).encode("utf-8")
    (output/"TRANSFER_SHA256SUMS").write_bytes(sums)
    report = {"contract_commit": args.contract_commit, "population_counts": {k: len(v) for k, v in populations.items()},
              "relationship_accounting": {"folder_and_provision_classifications": len(projected["relationships"]),
                                           "provision_candidates": len(provision_rows),
                                           "withheld_restricted_relationships": len(subject_rows) - len(projected["relationships"])},
              "candidate_set_sha256": _sha(candidates),
              "source_candidate_set_sha256": _sha(source_candidates),
              "physical_source_items": len(physical_inventory),
              "transferable_source_items":len(inventory),
              "local_quarantine_items":len(quarantine),
              "source_accounting_schema_errors": [str(issue) for issue in schema_errors(accounting)],
              "source_accounting_reconciliation_errors": [str(issue) for issue in contract_accounting.accounting_issues(accounting)],
              "consumer_dry_run":dry_run,"transfer_file_count":len(inventory_files),"transfer_inventory_sha256":_sha(sums),
              "validation_issues": [str(issue) for issue in issues],
              "strict_valid": not issues and not schema_errors(accounting) and not contract_accounting.accounting_issues(accounting) and dry_run["accepted"]}
    (output / "PRODUCER_VALIDATION_REPORT.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--contract-root", required=True); p.add_argument("--contract-commit", required=True)
    p.add_argument("--producer-root", required=True)
    p.add_argument("--inventory", required=True); p.add_argument("--source", required=True);p.add_argument("--subject-relationships", required=True)
    p.add_argument("--provision-relationships", required=True); p.add_argument("--output", required=True)
    p.add_argument("--quarantine-output", required=True)
    p.add_argument("--legal-taxonomy", required=True)
    p.add_argument("--generation-id", required=True); p.add_argument("--producer-commit", required=True)
    p.add_argument("--restricted-register-sha256", required=True)
    p.add_argument("--pdf-ocr-root");p.add_argument("--pdf-register")
    p.add_argument("--primary-image-register"); p.add_argument("--secondary-image-register")
    p.add_argument("--primary-image-root");p.add_argument("--secondary-image-root")
    p.add_argument("--identity-assessment"); p.add_argument("--access-register")
    p.add_argument("--hf-repo", default="hariomahlawat/mimamsa-corpus")
    p.add_argument("--hf-revision", required=True)
    p.add_argument("--verification-workers",type=int,default=12)
    return p.parse_args(argv)


def main(argv=None):
    report = build(parse_args(argv))
    print(json.dumps(report, indent=2))
    return 0 if report["strict_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
