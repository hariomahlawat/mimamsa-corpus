"""C6-02..C6-05 preparation registers (no network, no downloads). Run locally: the overlap check reads the crawler
PR heads with `git show <sha>:config/sources.yaml` (the PRs themselves are not modified). Outputs are committed;
`--check` re-derives ALL outputs and compares whole files, so it needs the crawler PR commits as local git objects; without
them the overlap column reads UNKNOWN and the check reports STALE (it does not degrade to a partial check; Fable F-22).

C6-02 registers/c6_02_batch_a_files.csv   one row per archive.org file in Batch A, with pins and PR overlap
C6-03 registers/c6_03_desw_package.csv    DESW items, PR #9 allow-list overlap, the held incomplete ER-2023 copy
C6-04 registers/c6_04_custodian_request_inventory.csv  publication request inventory (no correspondence)
C6-05 registers/c6_05_adviser_pack_status.json  counts of the unresolved items, carried unchanged"""
import argparse, csv, io, json, re, subprocess, sys
from collections import Counter
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
AW = PKG.parent
REPO = AW.parents[1]
C5 = AW / "SOURCE-LIBRARY-C5"
PRS = {"PR#8": "1b948727eeb359da45886c208e6433c394d251ba", "PR#17": "b8ee3176cfbb587b0df10f8344f0665503a0de80",
       "PR#23": "60715342b3f002dc4c08778c3eef672abcd1226f", "PR#9": "97933ccf4e7deb27715c18ea767eeec01cdcd802"}


def read(p):
    with open(p, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def csv_text(rows):
    b = io.StringIO()
    w = csv.DictWriter(b, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return b.getvalue()


def pr_configs():
    out = {}
    for k, s in PRS.items():
        p = subprocess.run(["git", "-C", str(REPO), "show", f"{s}:config/sources.yaml"], capture_output=True, text=True)
        out[k] = p.stdout if p.returncode == 0 else None
    return out


def overlap(cfgs, *needles):
    hits = [k for k, c in cfgs.items() if c is not None and any(n and n in c for n in needles)]
    missing = [k for k, c in cfgs.items() if c is None]
    return ";".join(hits) or ("NOT_CONFIGURED_IN_PR_STACK" if not missing else "UNKNOWN (PR commit not available: " + ",".join(missing) + ")")


def batch_a(cfgs):
    cands = {r["candidate_id"]: r for f in ("C_candidates.csv",) for r in read(C5 / "discovery" / f)}
    acq = {r["acq_c5_id"]: r for r in read(C5 / "registers/acquisition_register.csv")}
    plan = [("C5-ACQ-01", ["C5C-001"]), ("C5-ACQ-02", ["C5C-016"]), ("C5-ACQ-03", ["C5C-018"]), ("C5-ACQ-04", ["C5C-019"]),
            ("C5-ACQ-05", ["C5C-021", "C5C-022", "C5C-023"]), ("C5-ACQ-06", [f"C5C-{i:03d}" for i in range(4, 14)]),
            ("C5-ACQ-20", ["C5C-020"]), ("C5-ACQ-21", ["C5C-026", "C5C-027"])]
    rows = []
    for acq_id, cids in plan:
        for cid in cids:
            c = cands[cid]
            blob = " ".join(c.values())
            ident = re.search(r"in\.gazette\.[a-z0-9.\-]+", blob)
            fname = re.search(r"file ([\w\-.]+\.pdf)", blob)
            md5 = re.search(r"md5[^0-9a-f]{0,12}([0-9a-f]{32})", blob)
            ident_s = ident.group(0).rstrip(".") if ident else ""
            url = f"https://archive.org/download/{ident_s}/{fname.group(1)}" if ident and fname else ""
            rows.append({"acq_c5_id": acq_id, "candidate_id": cid, "publication": c["publication"], "archive_identifier": ident_s,
                         "file_name": fname.group(1) if fname else "NOT_RECORDED", "download_url": url or "NOT_PINNED",
                         "expected_md5": md5.group(1) if md5 else "NOT_PINNED", "expected_bytes": c["content_length"] or "NOT_PINNED",
                         "pin_status": ("PINNED (md5 and bytes from archive.org metadata recorded in Cycle 5 discovery)" if md5 and c["content_length"]
                                        else "NOT_PINNED: C6 guarded metadata attempt 2026-11-23 refused fail-closed (metadata API HEAD 405; "
                                             "_files.xml HEAD gave no content type); see discovery/c6_02_metadata_requests_v2.tsv; owner decision C6-02-D1"),
                         "identity_evidence": c["identity_evidence"][:240], "identity_status": "METADATA_ONLY (content not examined)",
                         "pr_stack_overlap": overlap(cfgs, ident_s + "/" if ident_s else "", fname.group(1) if fname else ""),
                         "rights": "Government of India Gazette; archive.org carrier recorded as THIRD_PARTY_ARCHIVAL_FACSIMILE; private store until owner decides",
                         "prerequisites": "owner approval A-C5-1; separate crawler-config PR stacked on #8 (#8 adds *.archive.org; staging lists archive.org only) and not altering #7/#8/#17/#23; archive.org robots RULES_PARSED at run time; HTTPS; redirects only to *.archive.org data nodes, each with its own robots decision (data nodes answered robots 404 on 2026-11-23)",
                         "validation_after_download": "sha256; md5+bytes equal pin; PDF signature; page count; masthead page-image check (issue, date, Part/Section); then a reviewed source-authentication addendum",
                         "approval_state": acq[acq_id]["approval_state"]})
    return rows


def desw(cfgs):
    acq = {r["acq_c5_id"]: r for r in read(C5 / "registers/acquisition_register.csv")}
    rows = []
    for acq_id in ("C5-ACQ-07", "C5-ACQ-08", "C5-ACQ-09", "C5-ACQ-10", "C5-ACQ-11"):
        a = acq[acq_id]
        locs = [u.strip() for u in re.split(r" ; |; ", a["exact_location"]) if u.strip()]
        if a["exact_location"].startswith("URLs in"):
            bc = {r["candidate_id"]: r for r in read(C5 / "discovery/B_candidates.csv")}
            locs = [bc[c]["url_or_identifier"] for c in re.findall(r"C5B-\d{3}", a["exact_location"])]
        for url in locs:
            rows.append({"acq_c5_id": acq_id, "item": a["title"], "url_or_location": url, "size_pin": a["integrity_pin"],
                         "pr9_allow_list": "LISTED_IN_PR9 (draft, not authorised)" if cfgs.get("PR#9") and url.split("/")[-1] in cfgs["PR#9"]
                         else ("NOT_IN_PR9: allow-list extension needed" if cfgs.get("PR#9") is not None else "UNKNOWN"),
                         "prerequisites": "owner approval A-C5-2; DESW allow-list extension in a separate config PR; desw.gov.in robots policy must be established at run time (it returned 403 in Cycle 5: fail-closed applies)",
                         "validation_after_download": "sha256; bytes equal HEAD size; PDF signature; title page identity on image; letter number/date from image",
                         "approval_state": a["approval_state"]})
    rows.append({"acq_c5_id": "HELD (not an acquisition)", "item": "Held ER-2023 copy 29f6fa2c... (13,011,188 bytes): covering letter + ER-2023 Appendix-I + annexures; GMO-2023 ABSENT",
                 "url_or_location": "desw.gov.in (held since Cycle 3; C5-SRC-P1-ER-2023-HELD-13MB)", "size_pin": "sha256 29f6fa2cfcd961aadce490679a686b5a3b7b2e683a0eaceb42bc2cd2ebb70dad",
                 "pr9_allow_list": "n/a", "prerequisites": "keep separately identified; compare with C5-ACQ-09 after download (C5-CF-C5-03)",
                 "validation_after_download": "page-by-page comparison with the complete file", "approval_state": "n/a"})
    return rows


def custodian():
    rows = [
        ("RA-1987-V1", "Regulations for the Army, Revised Edition 1987, Volume I", "C5-SRC-P0-RA-1987", "two-volume structure per a 2014 secondary listing only (C5D-004/006)"),
        ("RA-1987-V2", "Regulations for the Army, Revised Edition 1987, Volume II", "C5-SRC-P0-RA-1987", "C5D-005"),
        ("RA-1987-SLIPS", "All amendment lists / correction slips to RA 1987, with the amendment-incorporation record", "C5-SRC-P0-RA-1987", "none located (C5A-005)"),
        ("RA-1962", "Regulations for the Army, 1962, with amendment slips", "C5-SRC-P0-RA-1962", "cited in a 1987 Gazette (C5A-008)"),
        ("RMSAF-2010", "Regulations for the Medical Services of the Armed Forces, 2010 (revised), with amendments", "C5-SRC-P1-RMSAF-2010", "Scribd copy only (not acceptable)"),
        ("RMSAF-1983", "Regulations for the Medical Services of the Armed Forces, 1983 edition", "C5-SRC-P1-RMSAF-2010", "C5A-018"),
        ("AO-45-2001", "Army Order 45/2001 (as discussed in Pooja Pal (2026); cited by KB ADM-014)", "C5-SRC-P0-ARMY-ORDERS-INSTRUCTIONS", "only specific AO number found in the 658 records"),
        ("DV-SOH-2014", "Staff Officers' Handbook: Processing of Statutory/Non-Statutory Complaints on D&V Matters (apparently Addl DG Discipline & Vigilance, AG's Branch, IHQ of MoD (Army), May 2014)", "NONE (C6-04 discovery lead; no C5 source row)", "third-party Scribd upload only (document 733107547), not examined; see inputs/c6_04_discovery_candidates.csv"),
        ("AO-13-2006-PS", "Army Order 13/2006/PS (reported as cited in the D&V handbook; extraction candidate, unverified)", "C5-SRC-P0-ARMY-ORDERS-INSTRUCTIONS", "reported reference only (C6-04 discovery lead DV-SOH-2014)"),
        ("AO-CATEGORY", "Army Orders / Instructions cited by category in COI-002, COI-007, COI-018, COI-029, COI-033, COI-046, CM-040, HCE-030, HCE-031, HCE-033", "C5-SRC-P0-ARMY-ORDERS-INSTRUCTIONS", "owner to identify the specific orders before any request"),
    ]
    out = []
    for rid, pub, sid, ev in rows:
        out.append({"request_id": rid, "publication": pub, "c5_source_id": sid, "evidence_of_existence": ev,
                    "items_requested": "printed title page (publisher, printer, job number); access marking; complete text; amendment/correction-slip record",
                    "access_marking": "UNKNOWN (record the printed marking on receipt; sibling RAF reprint reported FOUO)",
                    "custody_requirements": "authorised custodian copy only; private store; restricted material stays out of public stores; no third-party copies",
                    "archived_copy_lead": "C5-ACQ-26 (archived CDA copies; owner decision before examination)" if rid.startswith("RA-1987") else "",
                    "correspondence": "NONE SENT (not authorised)", "status": "PREPARED"})
    return out


def adviser():
    idx = read(C5 / "registers/legal_adviser_evidence_index.csv")
    ws_b = read(AW / "WS-B-JUDGMENTS/open_inconsistencies_cycle3.csv")
    conf = {r["conflict_id"]: r for r in read(C5 / "registers/source_conflict_register.csv")}
    return {"c4_adviser_topics": sum(1 for r in idx if r["item_type"] == "ADVISER_TOPIC"),
            "c4_calibration_escalations": sum(1 for r in idx if r["item_type"].startswith("C4_ESCALATION_")),
            "reserved_items": sum(1 for r in idx if r["item_type"] == "RESERVED_ITEM"),
            "ws_b_inconsistencies_open": sum(1 for r in ws_b if r["state"].upper().startswith("OPEN")),
            "reserved_states": {k: conf[k]["reserved_status"] for k in ("C5-CF-C-01", "C5-CF-SC4-01", "C5-CF-C-08", "C5-CF-C-09")},
            "determinations_made": sum(1 for r in idx if not r["determination"].startswith("NONE")),
            "c6_01_documentary_inputs_for_adviser": ["ER 2023 covering letter 'with effect from 21st September, 2023 ... in supersession of all previous orders/rules' (held, C5-PIC-01): LAQ-03/LAQ-04",
                                                     "Act 37/1992 has no commencement provision (independent review RV-26): AQ-05",
                                                     "7 SC judgments proposed PROVENANCE_DOCUMENTED (C6-01 D2) change evidence availability, not holdings or treatment"]}


def outputs():
    cfgs = pr_configs()
    return {"c6_02_batch_a_files.csv": csv_text(batch_a(cfgs)), "c6_03_desw_package.csv": csv_text(desw(cfgs)),
            "c6_04_custodian_request_inventory.csv": csv_text(custodian()),
            "c6_05_adviser_pack_status.json": json.dumps(adviser(), indent=1, sort_keys=True) + "\n"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    texts = outputs()
    bad = [k for k, t in texts.items() if a.check and (PKG / "registers" / k).read_text(encoding="utf-8") != t]
    if not a.check:
        for k, t in texts.items():
            (PKG / "registers" / k).write_text(t, encoding="utf-8")
    print("STALE: " + ", ".join(bad) if bad else "ok")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
