"""Independent synthetic ingestion and producer checks for the pinned Cycle 13 inputs."""

import argparse
import io
import json
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import subprocess
import sys
import tarfile
from tempfile import TemporaryDirectory
from unittest.mock import patch

from jsonschema import Draft202012Validator


R1 = "9eeb04a457b532563d80610777d873ab24b52da5"
A4 = "c7a93ab6a38eee9d980f5729a09977356924fc8c"
A5 = "f915ac11494208a8ebad09f7910ea6cab6f21266"
A4_PATH = "legal_knowledge/audit_work/C13-A4-STATUTORY"
A5_PATH = "legal_knowledge/audit_work/C13-A5-GRAPH"
FIXTURES = json.loads(Path(__file__).with_name("data-fixtures.json").read_text())
NOW = "2090-01-01T00:00:00Z"
DOC_ID = "toy-blue-form-review"
SOURCE = FIXTURES["source_text"].encode()
ALT = FIXTURES["alternate_text"].encode()
REPLACEMENT = FIXTURES["replacement_text"].encode()


def require(condition, detail):
    if not condition:
        raise AssertionError(detail)


def digest(data):
    return sha256(data).hexdigest()


def kind(name):
    return {"contract_version": "1.0.0", "record_kind": name}


def document(data=SOURCE, doc_id=DOC_ID, publication="STAGED"):
    h = digest(data)
    values = {
        "source_integrity": "DECLARED_HASH_ONLY",
        "source_authenticity": "UNKNOWN",
        "evidence_fidelity": "AUTOMATED_CANDIDATE_NOT_VERIFIED",
        "legal_applicability": "NOT_ESTABLISHED",
        "legal_approval": "T0_RESEARCH_ONLY",
        "publication": publication,
        "dependency_freshness": "NOT_EVALUATED",
    }
    axes = {axis: {"value": value, "basis": "Synthetic fixture"} for axis, value in values.items()}
    axes["source_authenticity"]["policy_v1"] = {
        "document_authority": "UNKNOWN", "carrier_provenance": "USER_SUPPLIED",
        "copy_fidelity": "HASH_ONLY", "amendment_chain_status": "NOT_CHECKED",
    }
    return {
        **kind("document"), "doc_id": doc_id, "doc_type": "judgment", "title": "Fictional blue form",
        "number": None, "issuing_authority": None, "issue_date": None, "effective_date": None,
        "corpus_status": "unknown", "corpus_status_note": None, "text_method": "ocr",
        "source_copy": {"sha256": h, "bytes": len(data), "mime_type": "text/plain",
                        "vault_path": f"vault/sha256/{h[:2]}/{h}", "page_count": 1},
        "judicial": {"judgment_identity_id": "JUD:fictional-blue-form", "case_numbers": ["A", "B"]},
        "provenance": {"acquisition_channel": "RELEASE_IMPORT",
                       "source_url": "https://fictional.invalid/blue.txt", "retrieved_at": NOW,
                       "hf": {"repo": "fictional/toy", "revision": "a" * 40, "path": "toy/blue.txt"},
                       "git": {"commit": A5, "path": "toy/producer.py"}},
        "status_axes": axes,
        "restriction": {"access_marking": None, "marking_page": None, "eligibility": "ELIGIBLE_ALL_USERS",
                        "restriction_id": None, "decided_by": None, "basis": None},
        "field_origin": {"title": "rule"},
    }


def derived():
    return {
        **kind("derived_text"), "doc_id": DOC_ID, "source_copy_sha256": digest(SOURCE),
        "pipeline": {"name": "synthetic-extract", "version": "0.0.1"}, "text_path": "text/toy.txt",
        "text_sha256": digest(SOURCE), "page_marker": "[[page N]]", "quoting_permitted": False,
        "evidence_fidelity": "AUTOMATED_CANDIDATE_NOT_VERIFIED",
        "pages": [{"page": 1, "method": "ocr", "char_count": len(SOURCE), "low_confidence": True}],
        "passages": [{"passage_id": "p1-1", "page": 1, "char_start": 0,
                      "char_end": len(SOURCE), "text_sha256": digest(SOURCE)}],
    }


def candidate():
    return {
        **kind("candidate"), "candidate_id": "toy:edge:001", "candidate_type": "graph_edge",
        "source_doc_id": DOC_ID,
        "anchors": [{"source_copy_sha256": digest(SOURCE), "page": 1, "passage_id": "p1-1",
                     "char_start": 0, "char_end": len(SOURCE), "text_sha256": digest(SOURCE),
                     "pipeline_version": "0.0.1"}],
        "extractor": {"name": "synthetic-extract", "version": "0.0.1",
                      "artefact_commit": A5, "author_id": "toy-author"},
        "status": "AUTOMATED_CANDIDATE_NOT_VERIFIED", "capability_restriction": "NON_OPERATIONAL_RESEARCH_ONLY",
        "evaluation_ref": None,
        "payload": {"relation": "CITES_JUDGMENT", "source_node": "JUD:fictional-blue-form",
                    "target": {"resolved": False, "node_id": None, "raw_reference": FIXTURES["raw_reference"]},
                    "confidence": "extracted", "has_legal_effect": False, "evidence_text": FIXTURES["source_text"]},
    }


def review():
    return {
        **kind("reviewed_record"), "review_record_id": "RV-toy-blue",
        "subject": {"kind": "candidate", "id": candidate()["candidate_id"]}, "axis": "evidence_fidelity",
        "from_value": "AUTOMATED_CANDIDATE_NOT_VERIFIED", "to_value": "DOCUMENTARY_CHECKED",
        "reviewer": {"reviewer_id": "toy-reviewer", "name_or_role": "Fictional reviewer", "kind": "AI_AGENT"},
        "method": "Fictional documentary review", "decided_at": NOW,
        "record_location": {"path": "toy/review.json", "commit": "b" * 40},
        "reviewed_artefact": {"author_id": "toy-author", "reviewed_commit": A5},
    }


def publication(action, channel, actor="RELEASE_BUILDER"):
    return {
        **kind("publication_record"), "publication_record_id": f"PB-toy-{action.lower()}",
        "subject": {"doc_id": DOC_ID, "source_copy_sha256": digest(SOURCE)}, "action": action,
        "channel": channel, "actor_role": actor, "at": NOW, "reason": "Fictional publication event",
    }


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args])


def schema(repo, commit, path):
    return json.loads(git(repo, "show", f"{commit}:{path}"))


def extract_code(repo, commit, destination, *paths):
    with tarfile.open(fileobj=io.BytesIO(git(repo, "archive", commit, *paths)), mode="r:") as archive:
        for member in archive:
            if member.isfile():
                target = destination / member.name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.extractfile(member).read())


def r1_cases(repo, root):
    from mimamsa_contract.bundle import validate_bundle
    from mimamsa_contract.devbundle import new_dev_keypair, write_bundle
    from mimamsa_contract.restricted import register_from_bytes
    from mimamsa_contract.rules import record_issues

    reg = register_from_bytes(json.dumps({"items": [{
        "restriction_id": "RM-999", "source_sha256": digest(b"fictional restricted marker only"),
        "doc_id": "toy-excluded-id", "hosted_paths": ["toy/excluded.txt"],
    }]}).encode())
    manifest = schema(repo, R1, "app/contract/examples/release_manifest.example.json")
    manifest["restricted_material"].update(config_sha256=reg.config_sha256, restriction_ids_applied=["RM-999"])
    manifest["release_id"] = "R13-assurance-toy-20900101-00000000"
    manifest["pinned"]["artefact_commits"] = {"a4": A4, "a5": A5}
    key, pubkey = new_dev_keypair()

    def bundle(case, *, docs=None, copies=None, flip=False, **kwargs):
        path = root / case
        if docs is None:
            docs = [document()]
        if copies is None:
            copies = [SOURCE]
        files = {f"originals/{digest(data)}.txt": (data, "original") for data in copies}
        write_bundle(path, manifest, documents=docs, extra_files=files,
                     signing_key=key, public_key_raw=pubkey, **kwargs)
        if flip:
            (path / f"originals/{digest(SOURCE)}.txt").write_bytes(SOURCE + b".")
        return validate_bundle(path, mode="development", trusted_public_key=pubkey, register=reg)

    def report(case, result, expected_errors=(), expected_warnings=()):
        errors = {issue.code for issue in result.errors}
        warnings = {issue.code for issue in result.issues if issue.severity == "warning"}
        require(result.signature_verified, f"{case}: signature did not verify")
        require(errors == set(expected_errors), f"{case}: errors {errors}, expected {expected_errors}; {result.issues}")
        require(warnings == set(expected_warnings), f"{case}: warnings {warnings}, expected {expected_warnings}")
        print(f"{case} R1 {'rejected' if errors else 'accepted'}"
              f" errors={','.join(sorted(errors)) or 'none'} warnings={','.join(sorted(warnings)) or 'none'}")

    warning = ("OCR_CONFIDENCE_MISSING",)
    report("DA-01-control", bundle("da01-control"), expected_warnings=warning)
    wrong_path = document()
    wrong_path["source_copy"]["vault_path"] = f"vault/sha256/00/{digest(SOURCE)}"
    report("DA-01-vault-key", bundle("da01-vault", docs=[wrong_path]), ("VAULT_PATH_MISMATCH",), warning)
    report("DA-01-unbound-original", bundle("da01-unbound", copies=[ALT]), expected_warnings=warning)
    report("DA-01-missing-original", bundle("da01-missing", copies=[]), expected_warnings=warning)

    alias = document(doc_id="toy-blue-form-alias")
    alias["provenance"]["source_url"] = "https://fictional.invalid/mirror.txt"
    report("DA-02-repeat-bytes", bundle("da02-exact", docs=[document(), alias]), expected_warnings=warning)
    report("DA-02-repeat-id", bundle("da02-duplicate", docs=[document(), document()]), ("DUPLICATE_DOC_ID",), warning)
    first, alternate = document(), document(ALT, "toy-blue-form-alternate")
    first["alternate_copy_sha256"], alternate["alternate_copy_sha256"] = [digest(ALT)], [digest(SOURCE)]
    report("DA-02-alternate", bundle("da02-alternate", docs=[first, alternate], copies=[SOURCE, ALT]),
           expected_warnings=warning)
    result = bundle("da03", flip=True)
    report("DA-03-corrupt", result, ("CHECKSUM_MISMATCH",))
    require(result.checked_records == 0, "R1 parsed records after a failed checksum")
    truncated = document(publication="PUBLISHED")
    truncated["source_copy"]["completeness"] = "TRUNCATED_AT_SOURCE"
    truncated["status_axes"]["source_integrity"]["value"] = "TRUNCATED_AT_SOURCE"
    report("DA-03-truncated", bundle("da03-truncated", docs=[truncated]),
           expected_warnings=(*warning, "PUBLISHED_TRUNCATED"))

    text = derived()
    report("DA-04-ocr", bundle("da04-ocr", derived=[text]), expected_warnings=warning)
    forbidden = deepcopy(text)
    forbidden["quoting_permitted"] = True
    forbidden["passages"][0].update(page=2, char_start=2, char_end=1)
    report("DA-04-invalid-passage", bundle("da04-bad", derived=[forbidden]),
           ("OCR_QUOTING", "PASSAGE_PAGE_UNKNOWN", "ANCHOR_RANGE"), warning)
    far = deepcopy(text)
    far["passages"][0]["char_end"] = len(SOURCE) + 1
    report("DA-04-outside-page", bundle("da04-far", derived=[far]), expected_warnings=warning)

    missing = document()
    del missing["issuing_authority"]
    report("DA-05-missing-required-key", bundle("da05", docs=[missing]), ("SCHEMA",), warning)
    print("DA-05-explicit-null covered by DA-01-control")

    row, rv = candidate(), review()
    report("DA-06-candidate", bundle("da06-default", candidates=[row]), expected_warnings=warning)
    checked = dict(row, status="DOCUMENTARY_CHECKED", review_ref=rv["review_record_id"])
    report("DA-06-independent-review", bundle("da06-checked", candidates=[checked], reviews=[rv]),
           expected_warnings=warning)
    report("DA-06-missing-review", bundle("da06-unresolved", candidates=[checked]), ("REVIEW_UNRESOLVED",), warning)
    self_reviewed = deepcopy(rv)
    self_reviewed["reviewer"]["reviewer_id"] = row["extractor"]["author_id"]
    report("DA-06-self-review", bundle("da06-self", candidates=[checked], reviews=[self_reviewed]),
           ("REVIEW_NOT_INDEPENDENT",), warning)
    legal = document()
    legal["status_axes"]["legal_applicability"]["value"] = "EVIDENCED"
    report("DA-06-v0-legal-claim", bundle("da06-legal", docs=[legal]),
           ("LEDGER_V0_NO_APPLICABILITY", "LEGAL_AXIS_NEEDS_APPROVAL"), warning)

    restricted = deepcopy(row)
    restricted["payload"]["target"]["raw_reference"] = "Toy reference to TOY-EXCLUDED-ID"
    report("DA-07-nested-reference", bundle("da07", candidates=[restricted]), ("RESTRICTED_MATERIAL",), warning)
    marked = document(publication="PUBLISHED")
    marked["restriction"].update(access_marking="Fictional local-only marking", eligibility="NOT_ASSESSED")
    report("DA-08-ineligible-publication", bundle("da08-marked", docs=[marked]),
           ("PUBLISH_WITHOUT_ELIGIBILITY",), warning)
    upstream = publication("RELEASED_FOR_PUBLICATION", "UPSTREAM_RELEASE")
    report("DA-08-upstream", bundle("da08-upstream", docs=[document(publication="PUBLISHED")],
                                   publication_records=[upstream]), expected_warnings=warning)
    site = publication("PUBLISHED", "SITE_ADMIN", actor="ADMIN")
    report("DA-08-site-event", bundle("da08-site", publication_records=[site]),
           ("PUBLICATION_CHANNEL_SITE_ONLY",), warning)
    withdrawn = publication("WITHDRAWN", "UPSTREAM_WITHDRAWAL")
    report("DA-09-withdrawal-record", bundle("da09", docs=[], copies=[], publication_records=[withdrawn]))

    replacement = document(REPLACEMENT, "toy-green-form-revision")
    report("DA-10-replacement", bundle("da10", docs=[document(), replacement], copies=[SOURCE, REPLACEMENT],
                                       changes={"updated": [replacement["doc_id"]]}), expected_warnings=warning)
    untyped = dict(row, payload=dict(row["payload"], relation="DECIDES_PROCEEDING"))
    report("DA-34-unsupported-r1-edge", bundle("da34", candidates=[untyped]), ("SCHEMA", "EDGE_LEGAL_EFFECT_FLAG"), warning)
    source_wrong = deepcopy(row)
    source_wrong["anchors"][0].update(page=99, source_copy_sha256=digest(ALT))
    report("DA-35-dangling-copy", bundle("da35-dangling", candidates=[source_wrong]),
           ("DANGLING_ANCHOR",), warning)
    report("DA-35-cross-bound-anchor",
           bundle("da35-foreign", docs=[document(), alternate], copies=[SOURCE, ALT], candidates=[source_wrong]),
           expected_warnings=warning)

    for record_type in ("provision_version", "graph_node"):
        try:
            record_issues(record_type, {}, reg, "synthetic", 0)
        except KeyError as exc:
            require(exc.args == (record_type,), f"Unexpected R1 dispatch failure {exc}")
            print(f"R1 no native {record_type} record kind")
        else:
            raise AssertionError(f"R1 unexpectedly recognizes {record_type}")


def a4_cases():
    from validate_versions_c13 import resolve_at, validate

    for case, values in FIXTURES["a4_queries"].items():
        axes = {axis: {"status": "NOT_DETERMINED", "question_id": f"A4-LQ-{case}-{axis}"}
                for axis in ("conduct_date", "proceedings_date", "procedural_action_date",
                             "document_preparation_review_date")}
        exception = values.get("exception")
        exceptions = [{"instrument_id": "toy-instrument", "provision": "toy-exception", "effect": exception,
                       "anchor_state": "SYNTHETIC", "ref": "toy-page-1"}] if exception else []
        row = {
            "version_id": "AR1954/toy-blue/v01", "family": "AR1954", "principal_instrument": "Fictional instrument",
            "provision": "toy-blue", "provision_kind": "rule", "version_seq": 1, "version_kind": "as_notified",
            "change_summary": "Fictional rule",
            "created_by": {"instrument_id": "toy-instrument", "instrument": "Fictional instrument",
                           "instrument_date": "2090-04-01" if case == "DA-23" else "2090-01-01",
                           "publication_date": "2090-04-01" if case == "DA-23" else "2090-01-01",
                           "item_no": None, "register_refs": ["toy-record"]},
            "effective_from": {"date": values.get("effective_date"), "status": values["status"],
                               "reported_date": values.get("reported_date"), "basis": "Fictional date evidence"},
            "effective_to": {"date": None, "status": "OPEN_ON_LOCATED_INSTRUMENTS",
                             "next_version_id": None, "basis": "No later fictional source"},
            "retrospective_deemed_effect_from": values.get("retrospective_date"),
            "order_basis": "Fictional register order",
            "jurisdiction": {"status": "LIMITED_BY_RECORDED_INSTRUMENT" if exception
                             else "NOT_DETERMINED_FROM_HELD_TEXT", "note": exception or "Unknown"},
            "applicability_exceptions": exceptions, "savings_transitional": [], "temporal_axes": axes,
            "text_basis": "SELF_CONTAINED", "text_status": "TEXT_LAYER_ONLY",
            "text_evidence": [{"role": "principal_as_notified", "copy_id": DOC_ID, "sha256": digest(SOURCE),
                               "edition": "Fictional", "pdf_page": "1", "printed_page": None, "method": "TEXT_LAYER_ONLY",
                               "evidence_ids": ["toy-record"], "eligible_for_exact_anchor": False,
                               "anchoring_copy": "Fictional copy"}],
            "conflicts": values.get("conflicts", []), "open_items": ["Fictional legal question"],
            "currency": {"status": "NOT_ESTABLISHED", "chain_gaps": ["Fictional gap"]}, "priority_tags": [],
            "cited_by_items": 0, "legal_review_required": True, "determination_state": "AUTOMATED_CANDIDATE_NOT_VERIFIED",
            "sources": ["toy-record"],
        }
        errors = validate([row])
        require(not errors, f"{case}: {errors}")
        out = resolve_at([row], row["family"], row["provision"], values["query"])
        require(out["status"] == values["expected_resolution"], f"{case}: {out}")
        require(out["governing_axis"].startswith("NOT_DETERMINED"), f"{case}: governing axis selected")
        if case == "DA-21":
            require(not out["candidates"] and "compilation-reported" in out["possible_versions"][0]["reason"], out)
            wrong = deepcopy(row)
            wrong["effective_from"]["date"] = values["reported_date"]
            require(any("inferred date" in err for err in validate([wrong])), "A4 accepted inferred commencement")
        if case == "DA-22":
            require(not out["candidates"] and out["possible_versions"][0]["conflicts"] == values["conflicts"], out)
            wrong = dict(row, legal_review_required=False)
            require(any("conflict without legal_review_required" in err for err in validate([wrong])),
                    "A4 accepted disputed fixture with review flag removed")
        if case == "DA-23":
            require("retrospective deemed effect" in out["candidates"][0]["reason"], out)
            previous = resolve_at([row], row["family"], row["provision"], "2090-01-31")
            require(previous["status"] == "NOT_YET_IN_FORCE", previous)
        if case == "DA-24":
            require(row["applicability_exceptions"][0]["effect"] == exception, row)
            require("applicability_exceptions" not in out and "jurisdiction" not in out, out)
        print(f"{case} A4 schema and producer validator accepted, resolver={out['status']}, axis undetermined")


def a5_cases(repo, root):
    import graph_c13 as graph
    from mimamsa_contract.restricted import register_from_bytes
    from mimamsa_contract.rules import record_issues

    # The real loader requires a project-specific restricted marker. Supply only the synthetic register.
    register = (frozenset({digest(b"toy marker")}), frozenset({"toy-excluded-id"}), frozenset(), {})
    with patch.object(graph.C, "load_restricted", return_value=register):
        builder = graph.Builder(root)
    node_v = Draft202012Validator(schema(repo, A5, f"{A5_PATH}/schema/graph_node.schema.json"))
    edge_v = Draft202012Validator(schema(repo, A5, f"{A5_PATH}/schema/graph_edge.schema.json"))
    jud = "JUD:fictional-blue-form"
    ev = {"sha": digest(SOURCE), "doc_id": DOC_ID, "page": 1, "passage": FIXTURES["source_text"]}
    builder.add_node(jud, "JUDGMENT", "Fictional joint judgment", copies=[digest(SOURCE)])
    for ref in FIXTURES["proceedings"]:
        builder.add_node(ref, "PROCEEDING", ref, copies=[digest(SOURCE)])
        builder.add_edge("DECIDES_PROCEEDING", jud, ref, None, None, None, ev, "fixture extraction", graph.VERSION)
    require(len(builder.nodes) == 3 and len(builder.edges) == 2, "A5 conflated judgment and proceeding")
    require({edge["target"] for edge in builder.edges} == set(FIXTURES["proceedings"]), builder.edges)

    scope = FIXTURES["proposition_scope"]
    restrictions = ["NON_OPERATIONAL_RESEARCH_ONLY", "HIDDEN_FROM_USERS_THIS_CYCLE", "CANDIDATE_DATA"]
    prop = builder.add_node("PROP:fictional-blue-form", "PROPOSITION", "Fictional statement",
                            copies=[digest(SOURCE)], anchor={"doc_id": DOC_ID, "page": 1},
                            attrs=scope, restrictions=restrictions,
                            ax=graph.node_axes(prop="proposition.RESEARCH_CANDIDATE"))
    builder.add_edge("STATES_PROPOSITION", jud, prop["node_id"], None, None, None, ev, "fixture extraction",
                     graph.VERSION, restrictions=restrictions)
    require(prop["attributes"] == scope and "HIDDEN_FROM_USERS_THIS_CYCLE" in prop["restrictions"], prop)
    later = "JUD:fictional-later-order"
    builder.add_node(later, "JUDGMENT", "Fictional later order", copies=[digest(ALT)])
    later_ev = dict(ev, sha=digest(ALT), doc_id="toy-later-order", passage=FIXTURES["alternate_text"])
    builder.add_edge("FOLLOWS", later, prop["node_id"], None, None, None, later_ev, "fixture extraction",
                     graph.VERSION, restrictions=restrictions, attrs={"reported_voice": "submission"})
    treatment = builder.edges[-1]
    require(treatment["target"] == prop["node_id"] and treatment["legal_effect"]
            and treatment["verification_state"] == graph.CAND, treatment)
    require(node_v.is_valid(dict(prop, attributes={})), "A5 schema newly requires scoped attributes")

    builder.add_edge("CITES", jud, None, FIXTURES["raw_reference"], None, None, ev, "fixture extraction", graph.VERSION)
    cite = builder.edges[-1]
    require(cite["target"] is None and cite["target_raw"] == FIXTURES["raw_reference"], cite)
    require(edge_v.is_valid(dict(cite, target_raw=None)), "A5 schema newly requires a raw reference")
    require(cite["evidence"]["passage_sha256"] == digest(SOURCE) and cite["evidence"]["source_copy_sha256"] == digest(SOURCE)
            and cite["evidence"]["page"] == 1, cite)
    require(not edge_v.is_valid(dict(cite, evidence=dict(cite["evidence"], source_copy_sha256=None))),
            "A5 accepted missing citation copy hash")
    require(not edge_v.is_valid(dict(cite, edge_type="FABRICATED_RELATION")), "A5 accepted unsupported relation")
    for v, rows in ((node_v, list(builder.nodes.values())), (edge_v, builder.edges)):
        Draft202012Validator.check_schema(v.schema)
        for row in rows:
            v.validate(row)

    reg = register_from_bytes(json.dumps({"items": [{"restriction_id": "RM-999",
                                                     "source_sha256": digest(b"toy marker")}]}).encode())
    cite_r1 = candidate()
    cite_r1["payload"]["target"]["raw_reference"] = cite["target_raw"]
    require(not record_issues("candidate", cite_r1, reg, "synthetic", 0), "R1 rejected citation projection")
    empty = deepcopy(cite_r1)
    empty["payload"]["target"]["raw_reference"] = None
    require({issue.code for issue in record_issues("candidate", empty, reg, "synthetic", 0)} == {"EDGE_TARGET"},
            "R1 failed to require unresolved raw reference")
    holding = dict(cite_r1, candidate_type="holding", capability_restriction="HIDDEN_FROM_USERS",
                   payload={"item_type": "reasoning", "voice": scope["voice"], "opinion": scope["opinion"],
                            "provision_version_ref": scope["provision_version"]})
    require(not record_issues("candidate", holding, reg, "synthetic", 0), "R1 rejected narrow diagnostic holding")
    unhidden = dict(holding, capability_restriction="NON_OPERATIONAL_RESEARCH_ONLY")
    require({issue.code for issue in record_issues("candidate", unhidden, reg, "synthetic", 0)} == {"HOLDINGS_HIDDEN"},
            "R1 accepted a holding display restriction weaker than hidden")
    full_scope = deepcopy(holding)
    full_scope["payload"].update(proceeding_ref=scope["proceeding"], question_ref=scope["question"])
    require({issue.code for issue in record_issues("candidate", full_scope, reg, "synthetic", 0)} == {"SCHEMA"},
            "R1 newly accepts proceeding and question in the holding payload")
    print("DA-31 A5 builder/schema retained the joint judgment and its 2 distinct proceedings")
    print("DA-32 A5 builder retained proposition-target treatment as a candidate and scoped node restrictions;"
          " schema accepted empty attributes;"
          " R1 accepted hidden narrow projection, rejected unhidden and full-scope payloads")
    print("DA-33 A5 builder retained raw unresolved reference, A5 schema accepted both targets null;"
          " R1 rejected missing raw reference")
    print("DA-34 A5 schema rejected unknown edge, R1 rejected native structural relation")
    print("DA-35 A5 citation evidence retained copy/page/passage hash and rejects null copy hash")


def compare_observations(path):
    actual = json.loads(path.read_text())
    expected = FIXTURES["adapter_expected_evidence"]
    failures = []
    for case, fields in expected.items():
        observations = actual.get(case, {})
        for field, value in fields.items():
            observed = observations.get(field)
            if field not in observations or type(observed) is not type(value) or observed != value:
                failures.append(f"{case} {field}: expected {value!r}, observed {observed!r}"
                                f"{' (missing)' if field not in observations else ''}")
    if failures:
        raise SystemExit("\n".join(failures))
    print(f"Evidence fields match across {len(expected)} adapter cases. Runtime origin was not verified.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--repo", type=Path, help="Repository with the pinned R1, A4, and A5 Git objects")
    group.add_argument("--adapter-observations", type=Path, help="Compare observations collected independently from an adapter")
    args = parser.parse_args()
    if args.adapter_observations:
        compare_observations(args.adapter_observations)
        return
    for pin in (R1, A4, A5):
        git(args.repo, "cat-file", "-e", f"{pin}^{{commit}}")
    with TemporaryDirectory(prefix="c13-data-assurance-") as tmp:
        root = Path(tmp)
        extract_code(args.repo, R1, root, "app/contract/mimamsa_contract", "app/contract/schemas/v1")
        extract_code(args.repo, A4, root, f"{A4_PATH}/tools", f"{A4_PATH}/schema")
        extract_code(args.repo, A5, root, f"{A5_PATH}/tools")
        sys.path[:0] = [str(root / path) for path in ("app/contract", f"{A4_PATH}/tools", f"{A5_PATH}/tools")]
        r1_cases(args.repo, root / "bundles")
        a4_cases()
        a5_cases(args.repo, root)
    print("Pinned R1 and producer probes matched the recorded expectations, including open gaps.")


if __name__ == "__main__":
    main()
