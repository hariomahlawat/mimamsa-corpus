#!/usr/bin/env python3
"""C13-A5 deliverable 3: non-destructive identity-resolution overlay for the C12 duplicate legal identities.

Scope: the 128 copies flagged DUPLICATE_IDENTITY in C12 `copy_verification_c12/COPY_VERIFICATION_MANIFEST.csv`
  * 42 files carrying several crawler doc_ids (SAME_SHA256_SEVERAL_CRAWLER_DOC_IDS);
  * 87 copies in 11 groups where one C10/C5 id carries several sha256 values (C10_ID_SEVERAL_SHA256);
  (one copy has both flags, so 42 + 87 = 129 memberships over 128 copies).
Every copy and every doc_id is kept. The overlay only states which logical identity (judgment, proceeding,
instrument, schedule, listing page) each (copy, doc_id) belongs to, with the evidence. Nothing is deleted,
merged, renamed or rewritten; no evidence or authentication state changes. Copies on the restricted-material
register (RM-001) are withheld from the overlay rows and counted only.

  python -I -B identity_c13.py [--repo /home/user/c7] [--check]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common_c13 as C  # noqa: E402

CV = C.AUDIT / "C12-CONSOLIDATION" / "copy_verification_c12" / "COPY_VERIFICATION_MANIFEST.csv"
OUT = C.PKG / "identity"
VERSION = "identity-c13/1.0.0"
STATUS = "PROPOSED_IDENTITY_OVERLAY_ALL_COPIES_KEPT"
VERIF = "AUTOMATED_CANDIDATE_NOT_VERIFIED"

HC_ID = re.compile(r"^hc-(?P<court>[a-z]+)-(?P<y>\d{4})-(?P<case>.+)-(?P<cnr>[a-z]{4}\d{6,}\d{4})-(?P<n>\d+)-(?P<date>\d{4}-\d{2}-\d{2})$")
SC_ID = re.compile(r"^sc-(?P<y>\d{4})-(?P<rest>.+)$")


def lj(sha):  # logical judgment id: content-independent of doc_id, stable over the lowest copy sha
    return "LJ-" + sha[:16]


def classify_multi_docid(ids, metas):
    """One file under several crawler doc_ids."""
    if all(i.startswith("sc-") for i in ids):
        rests = {SC_ID.match(i).group("rest") for i in ids}
        if len(rests) == 1:
            return ("ONE_JUDGMENT_DUPLICATE_DOC_ID_YEAR_PARTITION",
                    "doc_ids differ only in the crawler's year partition prefix; same INSC suffix and same bytes",
                    "JUDGMENT")
    hc = [HC_ID.match(i) for i in ids]
    if all(hc):
        dates = {m.group("date") for m in hc}
        cases = {m.group("case") for m in hc}
        courts = {m.group("court") for m in hc}
        if len(dates) == 1 and len(courts) == 1 and len(cases) == len(ids):
            return ("ONE_JUDGMENT_SEVERAL_PROCEEDINGS",
                    "same bytes, same court and decision date, %d distinct case numbers: one common judgment or order "
                    "disposing several proceedings" % len(cases), "JUDGMENT")
    titles = {(metas.get(i) or {}).get("title") for i in ids}
    return ("SAME_BYTES_DIFFERENT_DOC_TYPES_REVIEW",
            "same bytes listed under doc_ids of different kinds (%s); titles: %s" % (
                ", ".join(sorted({i.split('-')[0] for i in ids})), " | ".join(sorted(t for t in titles if t))[:200]),
            "INSTRUMENT_OR_NOTIFICATION")


def classify_group_member(group, row, doc_id, meta):
    cat = row["category"]
    title = row["title"]
    if group.startswith("SD-C5-"):
        return ("SAME_LOGICAL_DOCUMENT_SEVERAL_COPIES", "C5 source id with several registered copies (copy roles in C10 "
                "COPY_EQUIVALENCE_REGISTER); copies may differ in carrier or completeness", group[3:], "SOURCE_DOCUMENT")
    parent = group[3:]  # RD-<doc_id>
    if cat == "linked_records":
        return ("LISTING_PAGE_NOT_AN_INSTRUMENT", "India Code 'linked records' listing page grouped under the parent Act",
                "LISTING:" + row["copy_id"], "LISTING_PAGE")
    if doc_id == parent:
        return ("PRINCIPAL_COPY", "the parent instrument's own crawler record", "INS:" + parent, "INSTRUMENT")
    if doc_id.endswith("-hi") and doc_id[:-3] == parent:
        return ("LANGUAGE_RENDITION_OF_SAME_INSTRUMENT", "Hindi rendition (doc_id suffix -hi) of the parent instrument",
                "INS:" + parent, "INSTRUMENT")
    if "-alt-" in doc_id and doc_id.split("-alt-")[0] == parent:
        return ("ALTERNATE_COPY_OF_SAME_INSTRUMENT_VERSION_NOT_ESTABLISHED",
                "alternate India Code file with the same title; same instrument, version/date of the text not established",
                "INS:" + parent, "INSTRUMENT")
    if cat == "schedule" or "-sched-" in doc_id:
        return ("SCHEDULE_PART_OF_INSTRUMENT", "schedule file of the parent instrument (part, not a copy)",
                "INS:" + parent + "#" + doc_id.split("-sched-")[-1], "INSTRUMENT_PART")
    return ("DISTINCT_INSTRUMENT_GROUPED_UNDER_PARENT_ID",
            "a different instrument (%s) listed on the parent Act's page; separate logical identity, not a copy" % cat,
            "INS:" + doc_id, "INSTRUMENT")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=C.DEFAULT_REPO)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    restricted = C.Restricted()
    rows = [r for r in C.read_csv(CV) if r["identity_status"] == "DUPLICATE_IDENTITY"]
    assert len(rows) == 128, len(rows)
    all_ids = sorted({i for r in rows for i in r["crawler_doc_ids"].split(";") if i})
    blobs = C.cat_blobs(a.repo, ["%s:data/meta/%s.json" % (C.TEXT_COMMIT, i) for i in all_ids])
    metas = {i: (json.loads(blobs["%s:data/meta/%s.json" % (C.TEXT_COMMIT, i)]) if blobs["%s:data/meta/%s.json" % (C.TEXT_COMMIT, i)] else None)
             for i in all_ids}

    out, withheld, n_multi, groups = [], 0, 0, defaultdict(list)
    for r in rows:
        sha = r["computed_sha256"] or r["expected_sha256"]
        ids = [i for i in r["crawler_doc_ids"].split(";") if i]
        if restricted.hit(sha256=sha) or any(restricted.hit(doc_id=i) for i in ids):
            withheld += 1
            continue
        flags = r["identity_flags"]
        if "SAME_SHA256_SEVERAL_CRAWLER_DOC_IDS" in flags:
            n_multi += 1
            kind, why, lkind = classify_multi_docid(ids, metas)
            lid = lj(sha) if lkind == "JUDGMENT" else "INS-BYTES:" + sha[:16]
            for i in ids:
                m = metas.get(i) or {}
                out.append(dict(
                    membership="SAME_SHA256_SEVERAL_CRAWLER_DOC_IDS", copy_sha256=sha, hosted_path=r["hosted_path"],
                    source_id=r["source_id"][:200], doc_id=i, doc_id_has_meta_record="YES" if metas.get(i) else "NO",
                    meta_case_numbers=";".join(m.get("case_numbers") or []) if m else "",
                    meta_issue_date=m.get("issue_date") or "", resolution=kind, logical_identity_kind=lkind,
                    logical_identity_id=lid,
                    proceeding_id=("PR:" + i) if kind == "ONE_JUDGMENT_SEVERAL_PROCEEDINGS" else "",
                    evidence=why, copies_kept="ALL", status=STATUS, verification=VERIF, tool=VERSION))
        for f in flags.split(";"):
            if "C10_ID_SEVERAL_SHA256:" in f:
                for g in f.split(":", 1)[1].split(","):
                    groups[g.strip()].append(r)
                    doc_id = ids[0] if ids else ""
                    kind, why, lid, lkind = classify_group_member(g.strip(), r, doc_id, metas.get(doc_id))
                    out.append(dict(
                        membership="ONE_ID_SEVERAL_SHA256:" + g.strip(), copy_sha256=sha, hosted_path=r["hosted_path"],
                        source_id=r["source_id"][:200], doc_id=doc_id,
                        doc_id_has_meta_record="YES" if metas.get(doc_id) else ("NO" if doc_id else "NO_CRAWLER_DOC_ID"),
                        meta_case_numbers="", meta_issue_date=(metas.get(doc_id) or {}).get("issue_date") or "",
                        resolution=kind, logical_identity_kind=lkind, logical_identity_id=lid, proceeding_id="",
                        evidence=why + "; title: " + r["title"][:120], copies_kept="ALL", status=STATUS,
                        verification=VERIF, tool=VERSION))
    out.sort(key=lambda x: (x["membership"], x["logical_identity_id"], x["copy_sha256"], x["doc_id"]))
    # every non-withheld copy appears; nothing dropped
    assert len({x["copy_sha256"] for x in out}) == 128 - withheld

    tally, kinds = defaultdict(int), defaultdict(int)
    for x in out:
        tally[x["resolution"]] += 1
    logical = defaultdict(set)
    for x in out:
        logical[x["logical_identity_id"]].add(x["copy_sha256"])
    for x in {x["logical_identity_id"]: x["logical_identity_kind"] for x in out}.values():
        kinds[x] += 1
    summary = dict(tool=VERSION, copies_in_scope=128, copies_withheld_restricted=withheld,
                   copies_in_overlay=len({x["copy_sha256"] for x in out}), membership_rows=len(out),
                   files_with_several_doc_ids=n_multi + (0 if withheld == 0 else 0),
                   one_id_several_sha256_groups=len(groups),
                   group_sizes={g: len(v) for g, v in sorted(groups.items())},
                   resolution_rows=dict(sorted(tally.items())), logical_identities_by_kind=dict(sorted(kinds.items())),
                   logical_identities=len(logical),
                   proceedings_from_common_judgments=sum(1 for x in out if x["proceeding_id"]),
                   policy="non-destructive: every copy and doc_id kept; no deletion, merge or rename; overlay only",
                   input_sha256={str(CV.relative_to(C.WT)): C.sha256_file(CV)}, restricted_register=restricted.provenance)
    files = {"IDENTITY_RESOLUTION_OVERLAY_C13.csv": C.to_csv(out), "IDENTITY_SUMMARY_C13.json": C.dumps(summary)}
    rc = C.write_or_check(files, OUT, a.check)
    if not a.check:
        print(json.dumps(summary, indent=1)[:1500])
    return rc


if __name__ == "__main__":
    sys.exit(main())
