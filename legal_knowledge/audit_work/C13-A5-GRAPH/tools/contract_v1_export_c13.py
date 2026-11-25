#!/usr/bin/env python3
"""C13-A5 review F04: export the candidate graph as Track B contract v1 `candidate` records (candidate_type graph_edge).

Contract: branch claude/c13-b-app, `app/contract/` (schemas/v1/candidate.schema.json, validator `mimamsa_contract`),
pinned to CONTRACT_COMMIT below. The native A5 graph (graph/) is unchanged; this adapter maps it onto v1:

| A5 edge type                    | v1 relation                      | exported | capability_restriction        |
| CITES                           | CITES_JUDGMENT                   | yes      | NONE_RECORDED                 |
| CITES_PROVISION (PROVISION_QUOTED label) | QUOTES_PROVISION        | yes      | NONE_RECORDED                 |
| CITES_PROVISION (other labels)  | CITES_PROVISION                  | yes      | NONE_RECORDED                 |
| FOLLOWS                         | FOLLOWS_PROPOSITION              | yes      | NON_OPERATIONAL_RESEARCH_ONLY |
| OVERRULES                       | OVERRULES_OR_LIMITS_PROPOSITION  | yes      | NON_OPERATIONAL_RESEARCH_ONLY |
| DISAPPROVES (declaratory)       | OVERRULES_OR_LIMITS_PROPOSITION  | yes (candidate_id prefix a5.disapproves.) | NON_OPERATIONAL_RESEARCH_ONLY |
| CONSIDERS                       | none in v1                       | no       | -                             |
| DISTINGUISHES, APPLIES, EXPLAINS, DOUBTS | LOW_RELIABILITY_CANDIDATE | no (filtered out) | -                   |
| amendment edges (C10 graph)     | no source-copy page anchor       | no       | -                             |
| forms, holdings, structural     | owned by other workstreams / no v1 record kind | no | -                       |

Every record: status AUTOMATED_CANDIDATE_NOT_VERIFIED, review_ref null (no RV- reviewed_record exists for these
edges), confidence 'extracted', evaluation_ref null (no human-checked, independent figure exists: the UI shows
'not evaluated'). Targets point at A5 node ids (JUD:...) or keep the raw reference. Passage ids are null (A5 has no
derived_text passage ids). Treatment edges carry a bound span (contract R2): pipeline_name 'corpus-data-text',
pipeline_version 'ad77758d', derivative_text_sha256 = sha256 of data/text/<doc_id>.txt, page-relative offsets counted
from the character after the '[[page N]]' marker. Citation and statute rows are page-only anchors with the excerpt
as quote.

  python -I -B contract_v1_export_c13.py [--check]     # writes contract_v1/
  validation: tests/test_legal_audit_c13_graph_contract_v1.py runs the B validator at CONTRACT_COMMIT on every record.
"""
from __future__ import annotations

import gzip
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common_c13 as C  # noqa: E402

CONTRACT_BRANCH = "claude/c13-b-app"
CONTRACT_COMMIT = "bb22ebd3"   # latest head (R2: optional span binding on page_anchor)
CONTRACT_VERSION = "1.0.0"
PIPELINE_NAME = "corpus-data-text"
OUT = C.PKG / "contract_v1"
G = C.PKG / "graph"
NO_LEGAL_EFFECT = {"CITES_PROVISION", "QUOTES_PROVISION", "CITES_JUDGMENT", "UPLOAD_REFERENCES_PROVISION", "UPLOAD_REFERENCES_CASE"}
MAP = {"CITES": "CITES_JUDGMENT", "FOLLOWS": "FOLLOWS_PROPOSITION", "OVERRULES": "OVERRULES_OR_LIMITS_PROPOSITION",
       "DISAPPROVES": "OVERRULES_OR_LIMITS_PROPOSITION", "CITES_PROVISION": "CITES_PROVISION"}
NOT_EXPORTED = {"CONSIDERS": "NO_V1_RELATION", "DISTINGUISHES": "LOW_RELIABILITY_CANDIDATE", "APPLIES": "LOW_RELIABILITY_CANDIDATE",
                "EXPLAINS": "LOW_RELIABILITY_CANDIDATE", "DOUBTS": "LOW_RELIABILITY_CANDIDATE"}
TOOLS = {"relations-c11/rev1.3": "legal_knowledge/audit_work/C11-JUDICIAL-QUALITY/relations/tools/relations_c11.py",
         "treatment": "legal_knowledge/audit_work/C13-A5-GRAPH/tools/treatment_c13.py"}
AUTHOR = {"relations-c11/rev1.3": "claude-agent-c11-relations", "treatment": "claude-agent-c13-a5"}


def anchor(ev, quote, text_sha):
    a = dict(source_copy_sha256=ev["source_copy_sha256"], page=ev["page"], passage_id=None, char_start=None, char_end=None,
             paragraph_label=None, text_sha256=None, pipeline_version=None, quote=quote, pipeline_name=None, derivative_text_sha256=None)
    if ev.get("char_start") is not None and ev.get("char_end") is not None and ev["doc_id"] in text_sha:
        a.update(char_start=ev["char_start"], char_end=ev["char_end"], pipeline_name=PIPELINE_NAME, pipeline_version=C.TEXT_COMMIT,
                 derivative_text_sha256=text_sha[ev["doc_id"]])
    return a


def last_commit(path):
    out = C.git(C.WT, "log", "-1", "--format=%H", "--", path).decode().strip()
    if not out:
        raise SystemExit("artefact %s is not committed; commit the tool before exporting" % path)
    return out[:12]


def jsonl(p):
    return [json.loads(l) for l in C.read_text_any(p).splitlines() if l.strip()]


def main():
    check = "--check" in sys.argv[1:]
    restricted = C.Restricted()
    edges = jsonl(G / "edges_candidate.jsonl.gz") + jsonl(G / "edges_reviewed.jsonl")
    tool_info = {}
    for k, path in TOOLS.items():
        tool_info[k] = dict(commit=last_commit(path), sha=C.sha256_file(C.WT / path), path=path)
    # span binding (contract R2): offsets are page-relative into data/text/<doc_id>.txt at ad77758d, counted from the
    # character after the '[[page N]]' marker; the derivative is that file, identified by the sha256 of its bytes.
    tdocs = sorted({e["evidence"]["doc_id"] for e in edges if e["evidence"].get("char_start") is not None and e["evidence"].get("doc_id")})
    tree = C.ls_tree(C.DEFAULT_REPO, C.TEXT_COMMIT, "data/text")
    blobs = C.cat_blobs(C.DEFAULT_REPO, [tree["data/text/%s.txt" % d] for d in tdocs])
    text_sha = {d: C.sha256_bytes(blobs[tree["data/text/%s.txt" % d]]) for d in tdocs}
    out, skipped = [], Counter()
    for e in sorted(edges, key=lambda x: x["edge_id"]):
        t = e["edge_type"]
        if t not in MAP:
            skipped[NOT_EXPORTED.get(t, "NOT_A_V1_GRAPH_EDGE:" + e["edge_class"])] += 1
            continue
        if "LOW_RELIABILITY_CANDIDATE" in e["restrictions"]:
            skipped["LOW_RELIABILITY_CANDIDATE"] += 1
            continue
        rel = MAP[t]
        if t == "CITES_PROVISION" and e["attributes"].get("link_label") == "PROVISION_QUOTED":
            rel = "QUOTES_PROVISION"
        ev = e["evidence"]
        if not ev.get("source_copy_sha256") or not isinstance(ev.get("page"), int) or ev["page"] < 1 or not ev.get("doc_id"):
            skipped["NO_PAGE_ANCHOR"] += 1
            continue
        kind = "treatment" if e["edge_class"] == "JUDICIAL_TREATMENT" else "relations-c11/rev1.3"
        ti = tool_info[kind]
        prefix = "a5.disapproves." if t == "DISAPPROVES" else "a5."
        quote = (ev.get("passage") or None) and ev["passage"][:2000]
        rec = dict(
            contract_version=CONTRACT_VERSION, record_kind="candidate", candidate_id=prefix + e["edge_id"],
            candidate_type="graph_edge", source_doc_id=ev["doc_id"],
            anchors=[anchor(ev, quote, text_sha)],
            extractor=dict(name="c13-a5-treatment" if kind == "treatment" else "c11-relations", version=e["extractor_version"][:64],
                           artefact_commit=ti["commit"], artefact_path=ti["path"], artefact_sha256=ti["sha"], author_id=AUTHOR[kind]),
            status="AUTOMATED_CANDIDATE_NOT_VERIFIED", review_ref=None,
            capability_restriction="NONE_RECORDED" if rel in NO_LEGAL_EFFECT else "NON_OPERATIONAL_RESEARCH_ONLY",
            deferred_findings=[], evaluation_ref=None,
            payload=dict(relation=rel, source_node=e["source"],
                         target=dict(resolved=e["target"] is not None, node_id=e["target"],
                                     raw_reference=None if e["target"] else (e["target_raw"] or "unresolved")[:1000]),
                         confidence="extracted", has_legal_effect=rel not in NO_LEGAL_EFFECT, effective_date=None,
                         evidence_text=quote))
        out.append(rec)
    text = C.to_jsonl(out)
    assert not restricted.hit(text=text), "restricted material in the contract export"
    counts = Counter(r["payload"]["relation"] for r in out)
    manifest = dict(contract="Track B data interchange contract v1", contract_branch=CONTRACT_BRANCH, contract_commit=CONTRACT_COMMIT,
                    contract_version=CONTRACT_VERSION, record_kind="candidate", candidate_type="graph_edge",
                    file="candidates_graph_edges.jsonl.gz", records=len(out),
                    sha256_uncompressed=C.sha256_bytes(text.encode()), relations=dict(sorted(counts.items())),
                    not_exported=dict(sorted(skipped.items())), extractor_artefacts=tool_info,
                    native_graph_manifest_sha256=C.sha256_file(G / "IC01_EXPORT_MANIFEST.json"),
                    restricted_register=restricted.provenance,
                    semantics=["All records are AUTOMATED_CANDIDATE_NOT_VERIFIED with evaluation_ref null ('not evaluated').",
                               "LOW_RELIABILITY_CANDIDATE types (DISTINGUISHES, APPLIES, EXPLAINS, DOUBTS) and CONSIDERS are not exported; "
                               "they remain in the native A5 graph with that marker.",
                               "DISAPPROVES (declaratory 'does not lay down the correct law') maps to OVERRULES_OR_LIMITS_PROPOSITION "
                               "with candidate_id prefix 'a5.disapproves.'; it is not an explicit overruling.",
                               "Absence of an edge never means absence of adverse authority."],
                    validation="python -m mimamsa_contract record candidate <decompressed file> --register config/restricted_material.json "
                               "(tests/test_legal_audit_c13_graph_contract_v1.py)")
    files = {"candidates_graph_edges.jsonl.gz": text, "CONTRACT_V1_EXPORT_MANIFEST.json": C.dumps(manifest)}
    rc = C.write_or_check(files, OUT, check)
    if not check:
        print(json.dumps(dict(records=len(out), relations=manifest["relations"], not_exported=manifest["not_exported"]), indent=1))
    return rc


if __name__ == "__main__":
    sys.exit(main())
