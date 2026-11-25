#!/usr/bin/env python3
"""C13-A5 deliverable 5: build the candidate legal knowledge graph and its IC-01 export.

Reads (all pinned, read-only): judgment metadata at ad77758d (git objects), C10 judgment reconciliation and amendment
graph, C11 citation graph and statute links (rev. 1.3), this workstream's treatment passages, identity overlay and
SC case-number overlay, C12 holdings (question_of_law and holding items only) and C12 forms registry.

Writes graph/:
  nodes.jsonl              one node per line (schema/graph_node.schema.json)
  edges_candidate.jsonl    every AUTOMATED_CANDIDATE_NOT_VERIFIED / PROPOSED_NOT_APPLIED edge (schema/graph_edge.schema.json)
  edges_reviewed.jsonl     edges whose exact row an independent AI documentary review confirmed (never legal validation;
                           never an OVERRULES / DISAPPROVES / DOUBTS / amendment edge, which always stay candidates)
  EDGE_TYPE_EVALUATION_C13.json   per-type measured (in-sample) precision where measured, else NOT_MEASURED
  GRAPH_SUMMARY_C13.json   counts by node type, edge type and state; input hashes; exclusions
  IC01_EXPORT_MANIFEST.json      IC-01 pinning: schema versions, file sha256, corpus and source revisions
Restricted material (config/restricted_material.json, RM-001) is excluded from every node, edge and export; the build
fails if any restricted sha256 or doc_id appears in the output.

  python -I -B graph_c13.py [--repo /home/user/c7] [--check]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common_c13 as C  # noqa: E402
import provenance_pin_c13  # noqa: E402

provenance_pin_c13.apply()   # deterministic register provenance (post-freeze fix, review A5-01b)

VERSION = "graph-c13/1.0.0"
SCHEMA_VERSION = "1.0.0"
OUT = C.PKG / "graph"
REL = C.AUDIT / "C11-JUDICIAL-QUALITY" / "relations" / "outputs"
REV = C.AUDIT / "C11-JUDICIAL-QUALITY" / "review"
C10J = C.AUDIT / "C10-RECONCILIATION" / "workstreams" / "judicial" / "JUDGMENT_RECONCILIATION.csv"
C10AG = C.AUDIT / "C10-RECONCILIATION" / "workstreams" / "statutory" / "amendment_graph_c10.csv"
HOLD = C.AUDIT / "C12-CONSOLIDATION" / "holdings" / "outputs" / "HOLDINGS_C12.jsonl"
FORMS = C.AUDIT / "C12-CONSOLIDATION" / "forms_registry" / "outputs" / "FORM_DISCOVERY_REGISTER.csv"
TREAT = C.PKG / "treatment" / "TREATMENT_PASSAGES_C13.csv.gz"
TREAT_SUM = C.PKG / "treatment" / "TREATMENT_SUMMARY_C13.json"
DEV_ROWS = C.PKG / "treatment" / "DEV_EVAL_ROWS_C13.csv"
IDENT = C.PKG / "identity" / "IDENTITY_RESOLUTION_OVERLAY_C13.csv"
SCNUM = C.PKG / "scnum" / "SC_CASE_NUMBER_OVERLAY_C13.jsonl"
HF_OVERLAY_COMMIT = C.PKG / "hf" / "HF_COMMIT.csv"
HF_CORPUS_REVISION = "3864faf3bb24edef4bfb18fa0916cc788eb68d79"   # corpus revision the inputs were built against

CAND = "AUTOMATED_CANDIDATE_NOT_VERIFIED"
REVIEWED = "REVIEWED_AI_DOCUMENTARY_NOT_LEGAL_VALIDATION"
ALWAYS_CANDIDATE = {"OVERRULES", "DISAPPROVES", "DOUBTS", "AMENDS_PROVISION_VERSION", "SUBSTITUTES_PROVISION_TEXT",
                    "INSERTS_PROVISION", "OMITS_PROVISION", "REPEALS_INSTRUMENT", "SAVES_OR_TRANSITIONS"}
NO_MARKER = {"CITES", "CITES_PROVISION", "DECIDES_PROCEEDING", "HAS_PROVISION"}
LEGAL_EFFECT = {"FOLLOWS", "APPLIES", "DISTINGUISHES", "EXPLAINS", "DOUBTS", "DISAPPROVES", "OVERRULES", "APPLIES_PROVISION",
                "AMENDS_PROVISION_VERSION", "SUBSTITUTES_PROVISION_TEXT", "INSERTS_PROVISION", "OMITS_PROVISION",
                "REPEALS_INSTRUMENT", "COMMENCES", "SAVES_OR_TRANSITIONS", "IMPLEMENTS", "PRESCRIBES_OR_EXEMPLIFIES_FORM",
                "REQUIREMENT_FROM_SOURCE"}
# Review f915ac11 (F01): independent AI sample put these types far below their in-sample figures. They stay in the
# native graph, flagged so consumers can filter them out, and are not exported under contract v1.
LOW_RELIABILITY_TYPES = {"DISTINGUISHES", "APPLIES", "EXPLAINS", "DOUBTS"}
REVIEW_VERDICTS = C.PKG / "reviews" / "treatment_sample_verdicts.csv"
TREATMENT_TYPES = {"FOLLOWS", "APPLIES", "DISTINGUISHES", "CONSIDERS", "EXPLAINS", "DOUBTS", "DISAPPROVES", "OVERRULES"}
DIRECTION = {
    "CITES": "citing judgment -> cited authority (citation only; no treatment inferred)",
    "CITES_PROVISION": "judgment -> provision or instrument mentioned (mention only; applicability not inferred)",
    "APPLIES_PROVISION": "judgment -> provision the court applies",
    "DECIDES_PROCEEDING": "judgment -> proceeding (case number) it decides or is listed under",
    "HAS_PROVISION": "instrument -> provision",
    "RAISES_QUESTION": "judgment -> question of law framed in it (candidate)",
    "STATES_PROPOSITION": "judgment -> proposition/holding candidate stated in it",
    "PRESCRIBES_OR_EXEMPLIFIES_FORM": "instrument -> form printed in it",
    "FORM_COMPETENT_AUTHORITY": "form -> competent authority or signatory as printed",
    "FORM_PROCEDURE": "form -> procedural dependency as printed",
    "REQUIREMENT_FROM_SOURCE": "requirement wording as printed -> form it governs",
}
for _t in TREATMENT_TYPES:
    DIRECTION[_t] = "later judgment (treating) -> earlier authority (treated)"
for _t in ("AMENDS_PROVISION_VERSION", "SUBSTITUTES_PROVISION_TEXT", "INSERTS_PROVISION", "OMITS_PROVISION", "REPEALS_INSTRUMENT",
           "COMMENCES", "SAVES_OR_TRANSITIONS", "IMPLEMENTS", "AMENDMENT_GRAPH_ENTRY_UNTYPED"):
    DIRECTION[_t] = "acting instrument -> affected instrument (provision in attributes)"
CLASS = {**{t: "JUDICIAL_TREATMENT" for t in TREATMENT_TYPES}, "CITES": "CITATION", "CITES_PROVISION": "STATUTORY_REFERENCE",
         "APPLIES_PROVISION": "STATUTORY_REFERENCE", "DECIDES_PROCEEDING": "STRUCTURAL", "HAS_PROVISION": "STRUCTURAL",
         "RAISES_QUESTION": "STRUCTURAL", "STATES_PROPOSITION": "STRUCTURAL", "PRESCRIBES_OR_EXEMPLIFIES_FORM": "FORMS",
         "FORM_COMPETENT_AUTHORITY": "FORMS", "FORM_PROCEDURE": "FORMS", "REQUIREMENT_FROM_SOURCE": "FORMS"}
CLASS_LETTER = {"CITATION": "C", "JUDICIAL_TREATMENT": "T", "STATUTORY_REFERENCE": "S", "AMENDMENT": "A", "STRUCTURAL": "X", "FORMS": "F"}


def h16(*parts):
    return hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()[:16]


def iv(x):
    try:
        return int(str(x).split(";")[0].split("-")[0])
    except (ValueError, TypeError):
        return None


def axes(extraction="extraction.AUTOMATED_CANDIDATE", prop="proposition.NOT_APPLICABLE", temporal="temporal.NOT_APPLICABLE"):
    return {"attribution_extraction": extraction, "legal_proposition": prop, "temporal_applicability": temporal,
            "authority_approval": "approval.NONE"}


def node_axes(byte="byte.BYTE_VERIFIED", identity="identity.PROVISIONAL", prop="proposition.NOT_APPLICABLE", temporal="temporal.NOT_APPLICABLE"):
    return {"byte_integrity": byte, "identity_fidelity": identity, "attribution_extraction": "extraction.AUTOMATED_CANDIDATE",
            "legal_proposition": prop, "temporal_applicability": temporal, "authority_approval": "approval.NONE"}


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")[:80]


class Builder:
    def __init__(self, repo):
        self.repo = repo
        self.r = C.Restricted()
        self.nodes = {}
        self.edges = []
        self.inputs = {}
        self.excluded = Counter()

    def inp(self, p):
        self.inputs[str(Path(p).relative_to(C.WT))] = C.sha256_file(p)
        return p

    # ------------------------------------------------------------------ nodes
    def add_node(self, nid, ntype, label, copies=(), anchor=None, attrs=None, restrictions=("CANDIDATE_DATA",), ax=None,
                 evaluation_ref=None):
        if nid in self.nodes:
            n = self.nodes[nid]
            n["source_copy_sha256"] = sorted(set(n["source_copy_sha256"]) | set(copies))
            for k, v in (attrs or {}).items():
                if isinstance(v, list) and isinstance(n["attributes"].get(k), list):
                    n["attributes"][k] = sorted(set(n["attributes"][k]) | set(v))
                else:
                    n["attributes"].setdefault(k, v)
            return n
        self.nodes[nid] = dict(node_id=nid, node_type=ntype, label=label or nid, source_copy_sha256=sorted(set(copies)),
                               anchor=anchor, extractor_version=VERSION, verification_axes=ax or node_axes(),
                               evaluation_ref=evaluation_ref, restrictions=list(restrictions), attributes=attrs or {})
        return self.nodes[nid]

    def add_edge(self, etype, source, target, target_raw, court, date, ev, method, extractor, state=CAND, reviews=(),
                 attrs=None, restrictions=None, temporal="temporal.NOT_APPLICABLE", key=None, eclass=None):
        eclass = eclass or CLASS.get(etype, "AMENDMENT")
        if etype in ALWAYS_CANDIDATE and state == REVIEWED:
            state = CAND
        rs = list(restrictions or ["CANDIDATE_DATA"])
        if etype not in NO_MARKER and "UNVERIFIED_MARKER_REQUIRED" not in rs:
            rs.append("UNVERIFIED_MARKER_REQUIRED")
        exported = (ev.get("passage") or None) and ev["passage"][:600]
        evidence = dict(source_copy_sha256=ev.get("sha"), doc_id=ev.get("doc_id"), page=ev.get("page"),
                        paragraph=ev.get("paragraph") or None, passage=exported,
                        passage_sha256=C.sha256_bytes(exported.encode()) if exported else None,
                        anchor_text=ev.get("anchor_text") or None,
                        char_start=ev.get("char_start"), char_end=ev.get("char_end"), pipeline_version=ev.get("pipeline_version"),
                        passage_full_sha256=ev.get("passage_full_sha256"), passage_truncated=ev.get("passage_truncated"))
        date = (date or None)
        if date and not re.match(r"^\d{4}(-\d{2}-\d{2})?$", date):
            date = None
        self.edges.append(dict(
            edge_id="G%s-%s" % (CLASS_LETTER[eclass], h16(etype, source, target, target_raw, key or "", ev.get("page"))),
            edge_type=etype, edge_class=eclass, source=source, target=target, target_raw=target_raw, direction=DIRECTION[etype],
            court=court or None, date=date, evidence=evidence, extraction_method=method, extractor_version=extractor,
            verification_state=state,
            verification_axes=axes("extraction.DOCUMENTARY_CHECKED" if state == REVIEWED else "extraction.AUTOMATED_CANDIDATE",
                                   "proposition.RESEARCH_CANDIDATE" if etype in LEGAL_EFFECT or etype == "STATES_PROPOSITION" else "proposition.NOT_APPLICABLE",
                                   temporal),
            legal_effect=etype in LEGAL_EFFECT, reviews=list(reviews), evaluation_ref=None, restrictions=rs, attributes=attrs or {}))

    # ------------------------------------------------------------------ judgments
    def load_judgments(self):
        tree = C.ls_tree(self.repo, C.TEXT_COMMIT, "data/meta")
        blobs = C.cat_blobs(self.repo, sorted(tree.values()))
        self.inputs["git:%s:data/meta (all records; judgments and orders used)" % C.TEXT_COMMIT] = hashlib.sha256(
            "".join(sorted(tree.values())).encode()).hexdigest()
        groups = {}
        for r in C.read_csv(self.inp(C10J)):
            groups[r["copy_sha256"]] = r["group_id"]
        self.jnode_of_sha, self.jnode_of_doc, self.meta = {}, {}, {}
        for path, oid in sorted(tree.items()):
            m = json.loads(blobs[oid])
            if m.get("doc_type") not in ("judgment", "order"):
                continue
            if self.r.hit(sha256=m.get("sha256"), doc_id=m.get("doc_id")):
                self.excluded["restricted_judgment_meta"] += 1
                continue
            sha = m["sha256"]
            g = groups.get(sha) or ("JG-" + sha[:12])
            nid = "JUD:" + g
            self.jnode_of_sha[sha] = nid
            self.jnode_of_doc[m["doc_id"]] = nid
            self.meta[m["doc_id"]] = m
            self.add_node(nid, "JUDGMENT", m.get("title"), copies=[sha],
                          anchor=dict(doc_id=m["doc_id"], page=1, paragraph=None, text=None),
                          attrs=dict(doc_ids=[m["doc_id"]], court=m.get("court") or m.get("issuing_authority"),
                                     decision_date=m.get("issue_date"), neutral_citation=m.get("neutral_citation"),
                                     case_numbers_meta=sorted(m.get("case_numbers") or []), rendition_group=g,
                                     identity_basis="C10 JUDGMENT_RECONCILIATION group (file hash != judgment)" if sha in groups else "single copy"),
                          ax=node_axes(identity="identity.PROVISIONAL"))
        # identity overlay: same bytes under several doc_ids already share a node (keyed by copy); record aliases
        for row in C.read_csv(self.inp(IDENT)):
            nid = self.jnode_of_sha.get(row["copy_sha256"])
            if nid:
                n = self.nodes[nid]["attributes"]
                n["doc_ids"] = sorted(set(n["doc_ids"]) | {row["doc_id"]})
                n["identity_overlay"] = row["resolution"]
                self.jnode_of_doc.setdefault(row["doc_id"], nid)

    def judgment_for(self, doc_id=None, sha=None, jid=None):
        if doc_id and doc_id in self.jnode_of_doc:
            return self.jnode_of_doc[doc_id]
        if sha and sha in self.jnode_of_sha:
            return self.jnode_of_sha[sha]
        if jid:
            for s, n in self.jnode_of_sha.items():
                if s.startswith(jid[2:]):
                    return n
        return None

    def proceedings(self):
        overlay = [json.loads(l) for l in open(self.inp(SCNUM), encoding="utf-8")]
        ov = {o["doc_id"]: o for o in overlay}
        common = defaultdict(list)
        for row in C.read_csv(IDENT):
            if row["resolution"] == "ONE_JUDGMENT_SEVERAL_PROCEEDINGS":
                common[row["copy_sha256"]].append(row["doc_id"])
        for doc_id, m in sorted(self.meta.items()):
            nid = self.jnode_of_doc[doc_id]
            court = m.get("court") or m.get("issuing_authority") or ""
            nums = [(n, "data/meta case_numbers") for n in (m.get("case_numbers") or [])]
            if doc_id in ov:
                nums += [(n, "SC case-number overlay C13-v1 (%s)" % ov[doc_id]["overlay_id"]) for n in ov[doc_id]["overlay_value"]]
                self.nodes[nid]["attributes"]["case_numbers_overlay_c13"] = ov[doc_id]["overlay_value"]
            for num, basis in nums:
                pid = "PROC:%s|%s" % (slug(court), num)
                self.add_node(pid, "PROCEEDING", "%s (%s)" % (num, court), copies=[m["sha256"]],
                              anchor=dict(doc_id=doc_id, page=None, paragraph=None, text=None),
                              attrs=dict(case_number=num, court=court, number_basis=[basis]), ax=node_axes(identity="identity.PROVISIONAL"))
                self.add_edge("DECIDES_PROCEEDING", nid, pid, None, court, m.get("issue_date"),
                              dict(sha=m["sha256"], doc_id=doc_id, page=None), "metadata (crawler record / reconfirmed overlay)",
                              VERSION, key=basis, attrs=dict(number_basis=basis,
                                                             connected_proceeding=len(m.get("case_numbers") or []) > 1 or m["sha256"] in common))

    # ------------------------------------------------------------------ citations and treatment
    def reviews(self):
        self.rev_edge, self.rev_sl = defaultdict(list), defaultdict(list)
        for f in ("fable_review_relations_c11_rows.csv", "fable_review_relations_c11_v11_rows.csv"):
            for r in C.read_csv(self.inp(REV / f)):
                ref = dict(review=f.replace("_rows.csv", ""), verdict=r["verdict"], category=r["category"])
                if r["row_id"].startswith("E-"):
                    self.rev_edge[r["row_id"]].append(ref)
                elif r["row_id"].startswith("SL-"):
                    self.rev_sl[r["row_id"]].append(ref)
        self.dev = {r["row_id"]: r for r in C.read_csv(self.inp(DEV_ROWS))}

    def citations(self):
        g = C.read_csv(self.inp(REL / "CASE_CITATION_GRAPH.csv"))
        self.cg = {r["edge_id"]: r for r in g}
        for r in g:
            src = self.judgment_for(doc_id=r["source_doc_id"])
            if src is None:
                self.excluded["cites_source_judgment_not_in_meta"] += 1
                continue
            tgt = None
            if r["target_state"] == "RESOLVED":
                for d in r["target_doc_ids"].split(";"):
                    tgt = tgt or self.judgment_for(doc_id=d.strip())
                if tgt is None:
                    for j in r["target_judgment_ids"].split(";"):
                        tgt = tgt or self.judgment_for(jid=j.strip())
            sha = self.nodes[src]["source_copy_sha256"][0] if len(self.nodes[src]["source_copy_sha256"]) == 1 else \
                self.meta[r["source_doc_id"]]["sha256"]
            revs = self.rev_edge.get(r["edge_id"], [])
            ok = tgt is not None and revs and all(x["verdict"] == "TARGET_CORRECT" for x in revs)
            self.add_edge("CITES", src, tgt, None if tgt else (r["cited_strings"] or r["citation_keys"]),
                          r["source_court"], r["source_date"],
                          dict(sha=sha, doc_id=r["source_doc_id"], page=iv(r["page"]), paragraph=r["paragraph"],
                               passage=r["excerpt"], anchor_text=r["cited_strings"]),
                          "rules: C11 citation detection and resolution (%s)" % (r["resolution_method"] or r["target_state"]),
                          "relations-c11/rev1.3", state=REVIEWED if ok else CAND, reviews=revs, key=r["edge_id"],
                          attrs=dict(c11_edge_id=r["edge_id"], target_state=r["target_state"], citation_keys=r["citation_keys"],
                                     resolution_method=r["resolution_method"], zone=r["zone"], occurrences=iv(r["occurrences"]),
                                     resolution_note=r["resolution_note"] or None))

    def treatment(self):
        tsum = json.loads(Path(self.inp(TREAT_SUM)).read_text(encoding="utf-8"))
        ev = tsum["dev_eval_in_sample"]
        rows = [r for r in C.read_csv(self.inp(TREAT)) if r["relation"] in TREATMENT_TYPES]
        # F08: one edge per (passage span, relation, target); lead rows without an anchor that share a span merge
        merged, seen = {}, {}
        for r in rows:
            e = self.cg.get(r["edge_id"]) or {}
            anchor = e.get("cited_strings") or ""
            if r["target_raw"] and not anchor:
                key = (r["source_doc_id"], r["char_page"], r["char_start"], r["char_end"], r["relation"])
                if key in seen:
                    keep = seen[key]
                    if len(r["target_raw"]) > len(keep["target_raw"]):
                        r["_merged"] = keep.get("_merged", []) + [keep["passage_id"]]
                        del merged[keep["passage_id"]]
                        merged[r["passage_id"]] = r
                        seen[key] = r
                    else:
                        keep.setdefault("_merged", []).append(r["passage_id"])
                    self.excluded["treatment_duplicate_lead_merged:" + r["relation"]] += 1
                    continue
                seen[key] = r
            merged[r["passage_id"]] = r
        rows = [r for r in rows if r["passage_id"] in merged]
        for r in rows:
            e = self.cg.get(r["edge_id"]) or {}
            src = self.judgment_for(doc_id=r["source_doc_id"])
            if src is None:
                self.excluded["treatment_source_not_in_meta"] += 1
                continue
            tgt = None
            if e.get("target_state") == "RESOLVED" and not r["target_raw"]:
                for d in e["target_doc_ids"].split(";"):
                    tgt = tgt or self.judgment_for(doc_id=d.strip())
            raw = None
            if not tgt:
                raw = r["target_raw"] or e.get("cited_strings") or e.get("citation_keys") or "unresolved"
                if r["target_raw"] and e.get("cited_strings"):
                    raw = "%s [anchor: %s]" % (r["target_raw"], e["cited_strings"].split(" || ")[0])
            revs, state = [], CAND
            for cid in r["merged_candidate_ids"].split(";"):
                d = self.dev.get(cid)
                if d and d["outcome"] != "EXCLUDED_ROW_NOT_IN_C11_REV13":
                    revs.append(dict(review=d["source"], verdict=d["reviewer_verdict"], truth_family=d["truth_family"],
                                     candidate_id=cid))
                    if d["outcome"] == "TP" and d["reviewer_verdict"] in ("SUPPORTED",):
                        state = REVIEWED
            attrs = dict(passage_id=r["passage_id"], c11_edge_id=r["edge_id"], voice=r["voice"], cue=r["cue"],
                         opinion=r["opinion"], overruling_language=r["overruling_language"] or None, reasons=r["reasons"] or None,
                         target_raw_context=r["target_raw_context"] or None, merged_passage_ids=sorted(r.get("_merged", [])) or None,
                         reliability="LOW_RELIABILITY_CANDIDATE" if r["relation"] in LOW_RELIABILITY_TYPES else "CANDIDATE",
                         binding="RAW_TARGET_ONLY_BINDING_NOT_ESTABLISHED" if raw and r["target_raw"] else ("UNRESOLVED_CITATION" if raw else "RESOLVED_TARGET"))
            rs = ["CANDIDATE_DATA"] + (["LOW_RELIABILITY_CANDIDATE"] if r["relation"] in LOW_RELIABILITY_TYPES else [])
            full = r["passage"]
            self.add_edge(r["relation"], src, tgt, raw, r["source_court"], r["source_date"],
                          dict(sha=self.meta[r["source_doc_id"]]["sha256"], doc_id=r["source_doc_id"], page=iv(r["page"]),
                               passage=full, anchor_text=e.get("cited_strings"),
                               char_start=iv(r["char_start"]), char_end=iv(r["char_end"]),
                               pipeline_version="data/text@%s" % C.TEXT_COMMIT,
                               passage_full_sha256=r["passage_sha256"], passage_truncated=r["passage_truncated"] == "YES"),
                          "rules: passage-level treatment classification (voice, binding, negation, opinion, competence)",
                          r["extractor"], state=state, reviews=revs, key=r["passage_id"], attrs=attrs, restrictions=rs)
        self.treat_eval = ev

    # ------------------------------------------------------------------ statutes
    def statutes(self):
        rows = C.read_csv(self.inp(REL / "STATUTE_JUDGMENT_LINKS.csv"))
        self.ins_map = {}
        for r in rows:
            if r["amendment_graph_instrument"]:
                self.ins_map[r["amendment_graph_instrument"]] = r["instrument_id"]
        for r in rows:
            src = self.judgment_for(doc_id=r["doc_id"])
            if src is None:
                self.excluded["statute_link_source_not_in_meta"] += 1
                continue
            ins = "INS:" + r["instrument_id"]
            self.add_node(ins, "INSTRUMENT", r["instrument"], attrs=dict(instrument_id=r["instrument_id"],
                          amendment_graph_instrument=r["amendment_graph_instrument"] or None,
                          copy_mapping="NOT_ESTABLISHED_IN_THIS_BUILD"), ax=node_axes(byte="byte.NOT_APPLICABLE", temporal="temporal.UNRESOLVED"))
            tgt = ins
            if r["provision_id"]:
                tgt = "PROV:" + r["provision_id"]
                self.add_node(tgt, "PROVISION", "%s %s" % (r["instrument"], r["printed_unit"] or r["provision_id"].split(":")[-1]),
                              attrs=dict(provision_id=r["provision_id"], instrument_id=r["instrument_id"],
                                         provision_version="NOT_ESTABLISHED (A4 ProvisionVersion interface: PV:<provision_id>@<valid_from>)"),
                              ax=node_axes(byte="byte.NOT_APPLICABLE", temporal="temporal.UNRESOLVED"))
                self.add_edge("HAS_PROVISION", ins, tgt, None, None, None, dict(), "derived from normalised provision id",
                              VERSION, key="has", eclass="STRUCTURAL")
            revs = self.rev_sl.get(r["link_id"], [])
            ok = revs and all(x["verdict"] == "SUPPORTED" for x in revs)
            self.add_edge("CITES_PROVISION", src, tgt, None, r["court"], r["judgment_date"],
                          dict(sha=self.meta[r["doc_id"]]["sha256"], doc_id=r["doc_id"], page=iv(r["page"]), paragraph=r["paragraph"],
                               passage=r["excerpt"], anchor_text=r["printed_unit"] or r["instrument"]),
                          "rules: C11 statute-link detection (label = bound cue)", "relations-c11/rev1.3",
                          state=REVIEWED if ok else CAND, reviews=revs, key=r["link_id"],
                          attrs=dict(c11_link_id=r["link_id"], link_label=r["relationship"], c11_status=r["status"],
                                     version_status=r["version_status"], code_transition_note=r["code_transition_note"] or None,
                                     applicability="NOT_INFERRED (mention is not application)"),
                          temporal="temporal.UNRESOLVED")

    def amendments(self):
        kinds = [("substitut", "SUBSTITUTES_PROVISION_TEXT"), ("insert", "INSERTS_PROVISION"), ("omit", "OMITS_PROVISION"),
                 ("repeal", "REPEALS_INSTRUMENT"), ("commencement", "COMMENCES"), ("implements", "IMPLEMENTS"),
                 ("saving", "SAVES_OR_TRANSITIONS"), ("amend", "AMENDS_PROVISION_VERSION")]
        tmap = {"EVIDENCED": "temporal.EVIDENCED", "UNRESOLVED_COMMENCEMENT": "temporal.UNRESOLVED", "NOT_LOCATED": "temporal.UNRESOLVED",
                "DISPUTED_PRESERVE_BOTH": "temporal.UNRESOLVED"}
        for r in C.read_csv(self.inp(C10AG)):
            k = r["edge_kind"].lower()
            if k.startswith("principal"):
                continue
            et = next((t for w, t in kinds if w in k and "not an amendment" not in k), "AMENDMENT_GRAPH_ENTRY_UNTYPED")
            if "declaration" in k and "not" in k:
                et = "AMENDMENT_GRAPH_ENTRY_UNTYPED"
            tid = r["target_instrument_id"]
            tgt = "INS:" + self.ins_map.get(tid, tid) if tid else None
            src = "INS:" + self.ins_map.get(r["amending_instrument_id"], r["amending_instrument_id"]) if r["amending_instrument_id"] else None
            for nid, lab in ((tgt, tid), (src, r["amending_instrument"])):
                if nid:
                    self.add_node(nid, "INSTRUMENT", lab, attrs=dict(c10_instrument_id=nid[4:]),
                                  ax=node_axes(byte="byte.NOT_APPLICABLE", temporal="temporal.UNRESOLVED"))
            if not src:
                self.excluded["amendment_entry_without_acting_instrument"] += 1
                continue
            self.add_edge(et, src, tgt, None if tgt else (r["provision"] or "target not recorded"), None,
                          r["commencement_date_evidenced"] or None,
                          dict(passage=r["evidence"] or r["status_detail"] or None),
                          "C10 amendment graph (manual documentary work), imported unchanged", "amendment-graph-c10",
                          state="PROPOSED_NOT_APPLIED" if r["c10_status"] != "EVIDENCED" else CAND, key=r["edge_id"], eclass="AMENDMENT",
                          temporal=tmap.get(r["c10_status"], "temporal.UNRESOLVED"),
                          attrs=dict(c10_edge_id=r["edge_id"], provision=r["provision"], edge_kind_raw=r["edge_kind"],
                                     c10_status=r["c10_status"], status_detail=r["status_detail"] or None,
                                     commencement_as_printed=r["commencement_as_printed"] or None, decision_owner=r["decision_owner"] or None))

    # ------------------------------------------------------------------ holdings (restricted research layer)
    def holdings(self):
        rs = ["NON_OPERATIONAL_RESEARCH_ONLY", "HIDDEN_FROM_USERS_THIS_CYCLE", "CANDIDATE_DATA"]
        with open(self.inp(HOLD), encoding="utf-8") as f:
            for line in f:
                h = json.loads(line)
                if h["item_type"] not in ("question_of_law", "holding"):
                    continue
                if self.r.hit(sha256=h["sha256"], doc_id=h["doc_id"]):
                    self.excluded["restricted_holding"] += 1
                    continue
                src = self.judgment_for(doc_id=h["doc_id"], sha=h["sha256"])
                if src is None:
                    self.excluded["holding_judgment_not_in_meta"] += 1
                    continue
                qual = h["item_type"] == "question_of_law"
                nid = ("QL:" if qual else "PROP:") + h["item_id"]
                self.add_node(nid, "QUESTION_OF_LAW" if qual else "PROPOSITION", h["excerpt"][:200], copies=[h["sha256"]],
                              anchor=dict(doc_id=h["doc_id"], page=h["page"], paragraph=None, text=h["excerpt"][:600]),
                              attrs=dict(item_id=h["item_id"], status=h["status"], verification=h["verification"], voice=h["voice"],
                                         opinion=h["opinion"], extractor=h["extractor"], legal_issue=h.get("legal_issue")),
                              restrictions=rs, ax=node_axes(prop="proposition.RESEARCH_CANDIDATE"),
                              evaluation_ref="legal_knowledge/audit_work/C12-CONSOLIDATION/holdings_eval/EVALUATION_HOLDINGS_C12.md")
                self.add_edge("RAISES_QUESTION" if qual else "STATES_PROPOSITION", src, nid, None, h["court"], None,
                              dict(sha=h["sha256"], doc_id=h["doc_id"], page=h["page"], passage=h["excerpt"]),
                              "C12 holdings extractor (restricted: C11 F06/F07)", h["extractor"], key=h["item_id"], restrictions=rs)

    # ------------------------------------------------------------------ forms (restricted research layer, WSG-R04)
    def forms(self):
        rs = ["NON_OPERATIONAL_RESEARCH_ONLY", "CANDIDATE_DATA"]
        placeholder = re.compile(r"^\(|^as\s+(?:stated|printed|recited)|^n/?a$", re.I)
        for r in C.read_csv(self.inp(FORMS)):
            sha = r["source_copy_sha256"] or None
            if self.r.hit(sha256=sha) or self.r.hit(text=r["source_file"]):
                self.excluded["restricted_form_occurrence"] += 1
                continue
            fid = "FORM:" + r["form_family_id"]
            page = iv(r["locator_start"])
            self.add_node(fid, "FORM", "%s %s: %s" % (r["instrument"], r["printed_form_number"], r["printed_title"][:120]),
                          copies=[sha] if sha else [], anchor=dict(doc_id=None, page=page, paragraph=None, text=r["anchor_text_as_printed"][:300] or None),
                          attrs=dict(form_family_id=r["form_family_id"], instrument=r["instrument"],
                                     form_authority_type_candidate=r["form_authority_type_candidate"],
                                     status_category=r["status_category"], verification_status=r["verification_status"],
                                     occurrences=[r["candidate_id"]]),
                          restrictions=rs, ax=node_axes(identity="identity.PROVISIONAL"),
                          evaluation_ref="legal_knowledge/audit_work/C12-CONSOLIDATION/forms_registry/README.md")
            ins = "INS:NAME:" + slug(r["instrument"])
            self.add_node(ins, "INSTRUMENT", r["instrument"], attrs=dict(name_only="instrument named in the forms registry; "
                                                                        "identity with C11 instrument ids not established"),
                          ax=node_axes(byte="byte.NOT_APPLICABLE", temporal="temporal.UNRESOLVED"))
            ev = dict(sha=sha, doc_id=None, page=page, passage=r["anchor_text_as_printed"] or None)
            self.add_edge("PRESCRIBES_OR_EXEMPLIFIES_FORM", ins, fid, None, None, None, ev, "C12 forms registry (as printed)",
                          "forms-registry-c12", key=r["candidate_id"], restrictions=rs,
                          attrs=dict(prescribing_provision=r["prescribing_provision"], occurrence_role=r["occurrence_role"]))
            for col, ntype, etype, prefix in (("competent_authority_as_printed", "COMPETENT_AUTHORITY", "FORM_COMPETENT_AUTHORITY", "AUTH"),
                                              ("signatory_as_printed", "COMPETENT_AUTHORITY", "FORM_COMPETENT_AUTHORITY", "AUTH"),
                                              ("procedural_dependencies", "PROCEDURE", "FORM_PROCEDURE", "PROCEDURE")):
                v = (r[col] or "").strip()
                if not v or placeholder.search(v):
                    continue
                nid = "%s:%s" % (prefix, h16(v))
                self.add_node(nid, ntype, v[:200], copies=[sha] if sha else [], attrs=dict(as_printed=v, field=col), restrictions=rs,
                              ax=node_axes(identity="identity.PROVISIONAL"))
                self.add_edge(etype, fid, nid, None, None, None, ev, "C12 forms registry column %s (as printed)" % col,
                              "forms-registry-c12", key=r["candidate_id"] + col, restrictions=rs, attrs=dict(field=col))
            req = (r["requirement_language_as_printed"] or "").strip()
            if req and not placeholder.search(req):
                nid = "REQ:" + h16(req)
                self.add_node(nid, "ADMINISTRATIVE_REQUIREMENT", req[:200], copies=[sha] if sha else [],
                              attrs=dict(as_printed=req, prescribing_provision=r["prescribing_provision"]), restrictions=rs,
                              ax=node_axes(identity="identity.PROVISIONAL"))
                self.add_edge("REQUIREMENT_FROM_SOURCE", nid, fid, None, None, None, ev, "C12 forms registry requirement wording (as printed)",
                              "forms-registry-c12", key=r["candidate_id"] + "req", restrictions=rs)

    # ------------------------------------------------------------------ evaluation refs and output
    def finish(self):
        dev = self.treat_eval
        per_type = {t: dict(displayable_measured_precision=None, development_in_sample=None, independent_ai_review_f915ac11=None)
                    for t in TREATMENT_TYPES | {"CITES", "CITES_PROVISION"}}
        fam = defaultdict(lambda: [0, 0])
        for d in self.dev.values():
            if d["outcome"] in ("TP", "FP"):
                fam[d["predicted"]][0 if d["outcome"] == "TP" else 1] += 1
        for t, (tp, fp) in fam.items():
            per_type[t]["development_in_sample"] = dict(
                tp=tp, fp=fp, displayable=False,
                note="DEVELOPMENT / IN-SAMPLE ONLY: the rules were written and tuned on these C11 reviewed rows. Not measured "
                     "performance; must not be displayed as precision.")
        rv = defaultdict(lambda: [0, 0])
        if REVIEW_VERDICTS.exists():
            self.inp(REVIEW_VERDICTS)
            for v in C.read_csv(REVIEW_VERDICTS):
                rv[v["edge_type"]][0 if v["fully_correct"] == "Y" else 1] += 1
        for t, (ok, bad) in rv.items():
            per_type.setdefault(t, {})["independent_ai_review_f915ac11"] = dict(
                fully_correct=ok, n=ok + bad, rate=round(ok / (ok + bad), 4),
                note="Independent AI review of extractor version treatment-c13/0.9.0-dev at f915ac11 (seeded stratified sample, "
                     "reviews/treatment_sample_verdicts.csv). Not human-checked; small n. The current rules were revised using "
                     "these findings, so these figures describe the earlier version and are no longer independent of the current one.")
        cr = sum(1 for v in self.rev_edge.values() for x in v if x["verdict"] == "TARGET_CORRECT")
        cw = sum(1 for v in self.rev_edge.values() for x in v if x["verdict"] == "WRONG_TARGET")
        per_type["CITES"]["c11_review_resolution_rows"] = dict(target_correct=cr, wrong_target=cw,
                                                             note="C11 review rounds 1-2 on C11 rev 1.0/1.1 resolved edges; AI review, not human-checked")
        for t in LOW_RELIABILITY_TYPES:
            per_type.setdefault(t, {})["reliability"] = "LOW_RELIABILITY_CANDIDATE (filterable; not exported under contract v1)"
        evaluation = dict(tool=VERSION, treatment_dev_eval_in_sample=dict(dev, displayable=False), per_edge_type=per_type,
                          displayable_policy="No figure in this file is displayable measured precision: none is human-checked "
                                             "and independent of the current extractor. Independent evaluation awaits A0 (H-REL-C13).",
                          rule="Absence of an edge never means absence of adverse authority.")
        ref = "legal_knowledge/audit_work/C13-A5-GRAPH/graph/EDGE_TYPE_EVALUATION_C13.json"
        for e in self.edges:
            if e["edge_type"] in per_type:
                e["evaluation_ref"] = ref + "#per_edge_type." + e["edge_type"]
        # restricted-material guard over the full serialised output
        nodes = [self.nodes[k] for k in sorted(self.nodes)]
        seen, edges = set(), []
        for e in sorted(self.edges, key=lambda x: x["edge_id"]):
            if e["edge_id"] in seen:
                self.excluded["repeat_of_same_edge_merged:" + e["edge_type"]] += 1
                continue
            seen.add(e["edge_id"])
            edges.append(e)
        cand = [e for e in edges if e["verification_state"] != REVIEWED]
        revd = [e for e in edges if e["verification_state"] == REVIEWED]
        nt, et, st = Counter(n["node_type"] for n in nodes), Counter(), Counter()
        for e in edges:
            et[e["edge_type"]] += 1
            st["%s|%s" % (e["edge_type"], e["verification_state"])] += 1
        files = {"nodes.jsonl.gz": C.to_jsonl(nodes), "edges_candidate.jsonl.gz": C.to_jsonl(cand), "edges_reviewed.jsonl": C.to_jsonl(revd),
                 "EDGE_TYPE_EVALUATION_C13.json": C.dumps(evaluation)}
        blob = "".join(files.values())
        hits = [s for s in self.r.shas if s in blob] + [i for i in self.r.ids if i in blob]
        assert not hits, "restricted material reached the graph output: %s" % hits[:3]
        assert not any(e["edge_type"] in ALWAYS_CANDIDATE and e["verification_state"] == REVIEWED for e in edges)
        summary = dict(tool=VERSION, schema_version=SCHEMA_VERSION, nodes=len(nodes), edges=len(edges),
                       nodes_by_type=dict(sorted(nt.items())), edges_by_type=dict(sorted(et.items())),
                       edges_by_type_and_state=dict(sorted(st.items())),
                       edges_candidate=len(cand), edges_reviewed=len(revd), excluded=dict(sorted(self.excluded.items())),
                       applies_provision_note="0 APPLIES_PROVISION edges: no extractor in this build distinguishes application from "
                                              "mention reliably (C11 withdrew PROVISION_APPLIED); statutory mentions are CITES_PROVISION only",
                       provision_version_note="0 PROVISION_VERSION nodes: no evidenced ProvisionVersion dataset exists yet "
                                              "(A4 branch has no commits); interface PV:<provision_id>@<valid_from>",
                       restricted_register=self.r.provenance, restricted_hits_in_output=0, inputs=dict(sorted(self.inputs.items())))
        files["GRAPH_SUMMARY_C13.json"] = C.dumps(summary)
        hf = C.read_csv(HF_OVERLAY_COMMIT)[0] if HF_OVERLAY_COMMIT.exists() else {}
        manifest = dict(contract="IC-01", contract_version=SCHEMA_VERSION, producer="C13-A5 graph workstream", tool=VERSION,
                        schemas={"node": "legal_knowledge/audit_work/C13-A5-GRAPH/schema/graph_node.schema.json",
                                 "edge": "legal_knowledge/audit_work/C13-A5-GRAPH/schema/graph_edge.schema.json"},
                        schema_sha256={k: C.sha256_file(C.PKG / "schema" / ("graph_%s.schema.json" % k)) for k in ("node", "edge")},
                        files={k: dict(sha256=C.sha256_bytes(v.encode()), bytes=len(v.encode()),
                                       records=v.count("\n") if ".jsonl" in k else None,
                                       sha256_note="sha256 of the uncompressed content" if k.endswith(".gz") else None)
                               for k, v in sorted(files.items())},
                        pins=dict(text_and_meta_git_commit=C.TEXT_COMMIT, hf_corpus_revision_inputs=HF_CORPUS_REVISION,
                                  hf_metadata_overlay_commit=hf.get("hf_commit"),
                                  artefact_git_commit="the GitHub commit that contains this manifest (Track B release pins it)"),
                        semantics=["Every edge is candidate data unless verification_state is REVIEWED_AI_DOCUMENTARY_NOT_LEGAL_VALIDATION, "
                                   "which is an AI documentary check, never legal validation.",
                                   "OVERRULES, DISAPPROVES, DOUBTS and amendment edges are always candidates.",
                                   "Edges carrying UNVERIFIED_MARKER_REQUIRED must render the 'proposed, not verified' marker.",
                                   "Nodes/edges with NON_OPERATIONAL_RESEARCH_ONLY must not drive advice, checklists, compliance or form validation; "
                                   "HIDDEN_FROM_USERS_THIS_CYCLE items are Admin-diagnostic only.",
                                   "Missing data is missing: the absence of an edge never establishes the absence of adverse authority."],
                        restricted_material_excluded=self.r.provenance)
        files["IC01_EXPORT_MANIFEST.json"] = C.dumps(manifest)
        return files, summary


def validate(files):
    try:
        import jsonschema
    except ImportError:
        print("jsonschema not available: schema validation skipped (tests validate)")
        return 0
    ns = json.loads((C.PKG / "schema" / "graph_node.schema.json").read_text())
    es = json.loads((C.PKG / "schema" / "graph_edge.schema.json").read_text())
    vn, ve = jsonschema.Draft202012Validator(ns), jsonschema.Draft202012Validator(es)
    bad = 0
    for line in files["nodes.jsonl.gz"].splitlines():
        for err in vn.iter_errors(json.loads(line)):
            bad += 1
            if bad < 5:
                print("node invalid:", err.message[:200])
    for f in ("edges_candidate.jsonl.gz", "edges_reviewed.jsonl"):
        for line in files[f].splitlines():
            for err in ve.iter_errors(json.loads(line)):
                bad += 1
                if bad < 10:
                    print("edge invalid:", err.message[:200], json.loads(line)["edge_id"])
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=C.DEFAULT_REPO)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--no-validate", action="store_true")
    a = ap.parse_args()
    b = Builder(a.repo)
    b.load_judgments()
    b.proceedings()
    b.reviews()
    b.citations()
    b.treatment()
    b.statutes()
    b.amendments()
    b.holdings()
    b.forms()
    files, summary = b.finish()
    if not a.no_validate:
        bad = validate(files)
        if bad:
            print("SCHEMA VALIDATION FAILED: %d errors" % bad)
            return 1
    rc = C.write_or_check(files, OUT, a.check)
    if not a.check:
        print(json.dumps({k: summary[k] for k in ("nodes", "edges", "nodes_by_type", "edges_by_type", "edges_reviewed", "excluded")}, indent=1))
    return rc


if __name__ == "__main__":
    sys.exit(main())
