#!/usr/bin/env python3
"""C12 Workstream H: build the targeted-acquisition plan (no network).

Reads the C10/C11 input registers and the sources.yaml snapshot, decides every target's
candidate URL(s), checks each host against the allow-list, and writes acquisition/TARGETS.csv.
acquire.py then executes only the rows whose action is FETCH.

Usage: python -I build_targets.py
"""
from __future__ import annotations

import csv
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

import yaml

HERE = Path(__file__).resolve().parent
ACQ = HERE.parent
AUDIT = ACQ.parent.parent                      # .../audit_work
C11 = AUDIT / "C11-JUDICIAL-QUALITY"
C10 = AUDIT / "C10-RECONCILIATION"
C10HF = AUDIT / "C10-HF-JUDGMENTS"
C7_REPO = Path("/home/user/c7")
C7_COMMIT = "ad77758d"

# Hard rule for this workstream, regardless of sources.yaml.
NEVER_CONTACT = {"aftjabalpur.in", "www.aftjabalpur.in"}

HF_DATASET = "https://huggingface.co/datasets/hariomahlawat/mimamsa-corpus/resolve/main/"


def allow_list() -> tuple[set[str], set[str]]:
    cfg = yaml.safe_load((ACQ / "sources.yaml.snapshot").read_text())
    hosts: set[str] = set()
    for src in cfg["sources"].values():
        hosts.update(h.lower() for h in src.get("allowed_hosts", []))
    blocked = {h.lower() for h in cfg.get("blocked_hosts", [])}
    return hosts - NEVER_CONTACT - blocked, blocked | NEVER_CONTACT


ALLOWED, FORBIDDEN = allow_list()


def host_of(url: str) -> str:
    return (urlsplit(url).hostname or "").lower()


def allowed(url: str) -> bool:
    return host_of(url) in ALLOWED


def raw_manifest() -> dict[str, dict]:
    out = subprocess.run(["git", "-C", str(C7_REPO), "show", f"{C7_COMMIT}:data/raw_manifest.csv"],
                         capture_output=True, text=True, check=True).stdout
    return {r["sha256"]: r for r in csv.DictReader(out.splitlines())}


COLS = ["target_id", "workstream_target", "priority", "description", "action", "url", "fallback_url",
        "host", "allow_listed", "expected_sha256", "expected_md5", "expected_bytes", "existing_sha256",
        "existing_bytes", "existing_path", "original_filename", "selection_reason", "provenance"]


def row(**kw) -> dict:
    r = {c: "" for c in COLS}
    r.update({k: ("" if v is None else v) for k, v in kw.items()})
    if r["url"]:
        r["host"] = host_of(r["url"])
        r["allow_listed"] = "YES" if allowed(r["url"]) else "NO"
        if r["action"] == "FETCH" and r["allow_listed"] != "YES":
            r["action"] = "BLOCKED_HOST_NOT_ALLOW_LISTED"
    return r


# ---------------------------------------------------------------- target 1
def incomplete_targets(rm: dict[str, dict]) -> list[dict]:
    plan = list(csv.DictReader(open(C11 / "identity/outputs/INCOMPLETE_23_RECOVERY_PLAN.csv")))
    cont = {r["sha256"] for r in csv.DictReader(open(C10HF / "outputs/CONTINUATION_MANIFEST.csv"))}
    rows = []
    for p in plan:
        sha = p["sha256"]
        in_c10 = "yes" if sha in cont else "no"
        if p["recovery_action"].startswith("USE_EXISTING_COPY"):
            rows.append(row(target_id=f"T1-INC-{sha[:12]}", workstream_target="1", priority="-",
                            description=f"{p['court']} {p['case_numbers_meta']} {p['issue_date_meta']} (truncated copy)",
                            action="NOT_TARGETED_COMPLETE_CONTENT_COPY_IN_CORPUS",
                            existing_sha256=sha, existing_bytes=p["bytes"], existing_path=p["path"],
                            selection_reason="excluded from the 22: C11 plan says USE_EXISTING_COPY (complete content copy 9809fac1c6611f50 in corpus)",
                            provenance=f"INCOMPLETE_23_RECOVERY_PLAN.csv; C10 CONTINUATION_MANIFEST={in_c10}"))
            continue
        if p["recovery_action"] == "RETRIEVE_HELD_BYTES":
            url = HF_DATASET + p["path"]
            rows.append(row(target_id=f"T1-INC-{sha[:12]}", workstream_target="1", priority="1",
                            description=f"{p['court']} held copy {p['path'].rsplit('/', 1)[-1]} (bytes not in pinned commit)",
                            action="FETCH", url=url,
                            fallback_url="https://www.sci.gov.in/ (judgment search; CAPTCHA) or https://digiscr.sci.gov.in/",
                            expected_sha256=sha, expected_bytes=p["bytes"], existing_sha256=sha, existing_bytes=p["bytes"],
                            existing_path=p["path"], original_filename=p["path"].rsplit("/", 1)[-1],
                            selection_reason="C11 recovery_action RETRIEVE_HELD_BYTES; no source_url in raw_manifest (not a crawler record)",
                            provenance=f"INCOMPLETE_23_RECOVERY_PLAN.csv; C10 CONTINUATION_MANIFEST={in_c10}; held-copy path in project HF dataset"))
            continue
        m = rm.get(sha)
        if not m:
            rows.append(row(target_id=f"T1-INC-{sha[:12]}", workstream_target="1", priority="1",
                            description=f"{p['court']} {p['case_numbers_meta']}", action="NO_SOURCE_URL_RECORDED",
                            existing_sha256=sha, existing_bytes=p["bytes"], existing_path=p["path"],
                            provenance="INCOMPLETE_23_RECOVERY_PLAN.csv; not in raw_manifest@ad77758d"))
            continue
        rows.append(row(target_id=f"T1-INC-{sha[:12]}", workstream_target="1", priority="1",
                        description=f"{p['court']} {p['case_numbers_meta']} {p['issue_date_meta']} ({m['title'][:90]})",
                        action="FETCH", url=m["source_url"], existing_sha256=sha, existing_bytes=p["bytes"],
                        existing_path=p["path"], original_filename=m["original_filename"] or m["source_url"].rsplit("/", 1)[-1],
                        selection_reason=f"C11 recovery_action {p['recovery_action']}; re-fetch recorded source_url (same open-data mirror the crawler used)",
                        provenance=f"raw_manifest.csv@{C7_COMMIT} source_url, retrieved_at {m['retrieved_at']}; C10 CONTINUATION_MANIFEST={in_c10}"))
    return rows


# ---------------------------------------------------------------- targets 2, 3
def sc_orders() -> list[dict]:
    return [
        row(target_id="T2-GIRISH-KUMAR-2026-INSC-1113", workstream_target="2", priority="1",
            description="Union of India v Sgt Girish Kumar, SC clarification order 12-10-2026, 2026 INSC 1113 (official SC source only)",
            action="FETCH", url="https://www.sci.gov.in/judgements-case-no/",
            fallback_url="https://api.sci.gov.in/supremecourt/2018/<diary_no>/<diary_no>_2018_..._Order_12-Oct-2026.pdf (C.A. 6820-6824/2018; diary number not recorded)",
            selection_reason="official SC host required; sci.gov.in / api.sci.gov.in are not in any allowed_hosts entry (SC judgment search is also CAPTCHA-gated per sources.yaml note 2026-11-21)",
            provenance="task brief; C.A. Nos. 6820-6824 of 2018 per AUTH-LEDGER copy_facts (2026 INSC 149 parent judgment)"),
        row(target_id="T3-RAM-AVTAR-2014-CA418-2012", workstream_target="3", priority="1",
            description="Union of India v Ram Avtar, SC order 10-12-2014, C.A. 418/2012 and connected (official SC source only)",
            action="FETCH", url="https://www.sci.gov.in/case-status-case-no/",
            fallback_url="https://api.sci.gov.in/supremecourt/2012/<diary_no>/<diary_no>_2012_..._Order_10-Dec-2014.pdf (diary number not recorded)",
            selection_reason="official SC host required; sci.gov.in / api.sci.gov.in not allow-listed; no official URL ever recorded (CYCLE3 acquisition_schedule PQ-C3-37)",
            provenance="task brief; COORDINATION/CYCLE3-PLANNING/acquisition_schedule.csv PQ-C3-37"),
    ]


# ---------------------------------------------------------------- target 4
# The ten picked from primary_source_status_c10.csv LOCATED_NOT_ACQUIRED rows, by acquisition_priority_c10
# rank (AQ-AR-POST2022 r1, AQ-SANHITA-COMM r2, AQ-AA-GAZ r4) plus ST-AR-INTERIM-1950. Pins from
# SOURCE-LIBRARY-C5 registers (C5-ACQ-01/05/06/19, C5C-* candidates). Government host egazette.gov.in is
# tried first; the archive.org pin is the fallback (archive.org is allow-listed; md5 verified).
STAT = [
    # key,               source_key,             egazette path,                              archive id / file,                                                md5,                                bytes,   desc
    ("AA-ENACTED-1950", "ST-AA-ENACTED", "1950/E-2350-1950-0011-109089.pdf", "in.gazette.e.1950.306/E-2350-1950-0011-109089.pdf", "68bcdd4e8db91eb83d1e6b92a393b2db", 6491633, "Army Act 1950 as enacted, Gazette Extraordinary No.306 of 1950 (C5-ACQ-01)"),
    ("BSA-COMM-252352", "ST-SANHITA-COMM-2024", "2024/252352.pdf", "in.gazette.central.e.2024-02-24.252352/252352.pdf", "6288ffbc08004bbe858e6c4450524dc2", 922833, "BSA 2023 commencement notification, Gazette Extraordinary 24-02-2024 (C5C-022)"),
    ("BNS-COMM-252353", "ST-SANHITA-COMM-2024", "2024/252353.pdf", "in.gazette.central.e.2024-02-24.252353/252353.pdf", "393d0cd8277d823bfeb38113b0ae707d", 922134, "BNS 2023 commencement notification, Gazette Extraordinary 24-02-2024 (C5C-023)"),
    ("BNSS-COMM-252354", "ST-SANHITA-COMM-2024", "2024/252354.pdf", "in.gazette.central.e.2024-02-24.252354/252354.pdf", "af9e7e74b1f50f549ae6ab74e9747b58", 924297, "BNSS 2023 commencement notification, Gazette Extraordinary 24-02-2024 (C5C-021)"),
    ("AR-INTERIM-1950", "ST-AR-INTERIM-1950", "1950/E-2351-1950-0002-109235.pdf", "in.gazette.e.1950.8/E-2351-1950-0002-109235.pdf", "60ff798536c357ce3ef142d5fead48b6", 445365, "1950 rules under Army Act ss.21, 102(4), 191, Gazette Extraordinary No.8 of 1950 (C5-ACQ-19)"),
    ("AR-POST2022-236757", "ST-AR-AMD-POST2022", "2022/236757.pdf", "in.gazette.central.e.2022-06-23.236757/236757.pdf", "ee43c55c6320319bb80d8b578d7f675f", 150261, "DMA SRO 9(E) 23-06-2022, possible Army Rules amendment (subject unconfirmed) (C5C-004)"),
    ("AR-POST2022-241268", "ST-AR-AMD-POST2022", "2022/241268.pdf", "in.gazette.central.e.2022-12-21.241268/241268.pdf", "9466ea59e40ba9a003748bd54bd387c7", 76155, "DMA Part II s.4 Extraordinary 21-12-2022, possible Army Rules amendment (C5C-005)"),
    ("AR-POST2022-246457", "ST-AR-AMD-POST2022", "2023/246457.pdf", "in.gazette.central.e.2023-06-12.246457/246457.pdf", "b20748000f2d0a664ea776c9ae06f4b4", 775443, "DMA Part II s.4 Extraordinary 12-06-2023, possible Army Rules amendment (C5C-007)"),
    ("AR-POST2022-254308", "ST-AR-AMD-POST2022", "2024/254308.pdf", "in.gazette.central.e.2024-05-22.254308/254308.pdf", "99876ecc132a218702e10a74118d1067", 723410, "DMA SRO 15(E) 22-05-2024, possible Army Rules amendment (C5C-008)"),
    ("AR-POST2022-273809", "ST-AR-AMD-POST2022", "2026/273809.pdf", "in.gazette.central.e.2026-06-24.273809/273809.pdf", "5b6c2f639a1c12be508ceb546a9e8676", 361235, "DMA SRO 10(E) 24-06-2026, possible Army Rules amendment (C5C-013)"),
]

# LOCATED_NOT_ACQUIRED rows whose only located host is not allow-listed (recorded, not fetched).
STAT_BLOCKED = [
    ("PRA-2008", "ST-PRA-2008", "https://desw.gov.in/", "Pension Regulations for the Army 2008 Parts I and II (DESW)"),
    ("ER-2008", "ST-ER-2008", "https://desw.gov.in/", "Entitlement Rules for Casualty Pensionary Awards 2008 (DESW)"),
    ("GMO-2023", "ST-GMO-2023", "https://desw.gov.in/", "Guide to Medical Officers (Military Pensions) 2023 (DESW)"),
    ("PEN-CIRCULARS", "ST-PEN-CIRCULARS", "https://desw.gov.in/", "DESW circulars amending PRA 2008 / ER 2008"),
]


def statutory() -> list[dict]:
    status = {r["source_key"]: r for r in csv.DictReader(open(C10 / "workstreams/statutory/primary_source_status_c10.csv"))}
    rows = []
    for i, (key, sk, eg, ia, md5, nbytes, desc) in enumerate(STAT, 1):
        assert status[sk]["c10_status"] == "LOCATED_NOT_ACQUIRED", sk
        rows.append(row(target_id=f"T4-{key}", workstream_target="4", priority=str(i), description=desc,
                        action="FETCH", url=f"https://egazette.gov.in/WriteReadData/{eg}",
                        fallback_url=f"https://archive.org/download/{ia}", expected_md5=md5, expected_bytes=nbytes,
                        original_filename=ia.rsplit("/", 1)[-1],
                        selection_reason=f"{sk} LOCATED_NOT_ACQUIRED (C10); government Gazette host first, archive.org pin fallback",
                        provenance="C10 primary_source_status_c10.csv + acquisition_priority_c10.csv; pins SOURCE-LIBRARY-C5 registers"))
    for key, sk, url, desc in STAT_BLOCKED:
        assert status[sk]["c10_status"] == "LOCATED_NOT_ACQUIRED", sk
        rows.append(row(target_id=f"T4-{key}", workstream_target="4", priority="-", description=desc, action="FETCH",
                        url=url, selection_reason=f"{sk} LOCATED_NOT_ACQUIRED; only located host desw.gov.in (exact URLs in C5/C9 registers) is not allow-listed",
                        provenance=f"C10 primary_source_status_c10.csv basis: {status[sk]['basis'][:120]}"))
    # Remaining LOCATED_NOT_ACQUIRED rows: not attempted this cycle (no fetchable pinned URL, or beyond the 10).
    for sk, r in status.items():
        if r["c10_status"] == "LOCATED_NOT_ACQUIRED" and sk not in {s[1] for s in STAT} | {s[1] for s in STAT_BLOCKED}:
            rows.append(row(target_id=f"T4-{sk}", workstream_target="4", priority="-", description=r["source"][:140],
                            action="NOT_ATTEMPTED_NO_PINNED_URL_OR_OVER_CAP",
                            selection_reason="LOCATED_NOT_ACQUIRED but no exact pinned file URL on an allow-listed host, or outside the 10-item cap",
                            provenance=f"C10 basis: {r['basis'][:160]}"))
    return rows


# ---------------------------------------------------------------- target 5
RANKED_PARTY = re.compile(r"\b(SEP(OY)?|NAIK|NK|HAV(ILDAR)?|SUB(EDAR)?|NB SUB|RFN|SGT|CPL|LT\.?|CAPT\.?|MAJ\.?|COL\.?|COLONEL|BRIG\.?|BRIGADIER|"
                          r"GEN(ERAL)?\.?|WG\.? ?CDR|WING COMMANDER|SQN\.? ?LDR|GP\.? ?CAPT|AIR MARSHAL|COMMODORE|CDR\.?|LT\.? ?CDR|"
                          r"CHIEF OF (THE )?(ARMY|NAVAL|AIR) STAFF|ARMY HEADQUARTERS|DG PERSONNEL)\b")
NOT_SERVICE = re.compile(r"SCHOOL|WELFARE|HOUSING|ENGINEERING SERVICE|ENGINEER|ESTATE|CONTRACTOR|INSURANCE|GOLF|COLLEGE|INSTITUTE|"
                         r"SALVATION|CRPF|POLICE|SPORTS|SECURITY CHAMBERS|MAHARAJA|MILITARY FARM|CONSTRUCTION|NOIDA|DESIGN OFFICERS|"
                         r"STATE OF PUNJAB|REGISTRAR SUPREME COURT|INDUSTRIES|INDSUTRIES")
DB_CASE = re.compile(r"^(LPA|LPASW|LPAOW|SPL\.? ?APPEAL|SPECIAL APPEAL|SAW|SA)\b|^(CWP|RA-CW)/")


def party_class(r: dict) -> str | None:
    t = r["title"].upper()
    if "AFT" in r["signals"].split(";") or "ARMED FORCES TRIBUNAL" in t:
        return "AFT"
    if re.search(r"COURT[- ]?MARTIAL", t):
        return "COURT_MARTIAL"
    if NOT_SERVICE.search(t):
        return None
    sig = r["signals"].split(";")
    if ("rank_vs_union" in sig or "service_body" in sig) and RANKED_PARTY.search(t):
        return "ARMED_FORCES_SERVICE_PARTY"
    return None


def court_class(r: dict) -> str | None:
    if r["court"] == "Supreme Court of India":
        return "SUPREME_COURT"
    t = r["title"].upper()
    case_type = t.split(" OF ", 1)[0]
    if re.match(r"^(LPA|LPASW|LPAOW|SPL|SPECIAL APPEAL)", case_type):
        return "DIVISION_BENCH (intra-court appeal case type)"
    if party_class(r) == "AFT" and re.match(r"^(CWP|RA-CW|W\.P\.\(C\)|WP\(C\)|WRIA)", case_type):
        return "DIVISION_BENCH_PRESUMED (writ against an AFT order; heard by a Division Bench)"
    return None


def excluded_t1() -> list[dict]:
    allr = [r for r in csv.DictReader(open(C11 / "excluded/RE_ACQUISITION_MANIFEST.csv")) if r["tier"] == "T1"]
    elig = []
    for r in allr:
        pc, cc = party_class(r), court_class(r)
        if pc and cc:
            elig.append((r, pc, cc))
    # Quota: Supreme Court first (up to 13, by crawler score then rank), then Division Bench rows with an
    # AFT / court-martial party (by rank), then Division Bench armed-forces service party; cap 25.
    sc = sorted([e for e in elig if e[2] == "SUPREME_COURT"], key=lambda e: (-int(e[0]["score"]), int(e[0]["rank"])))
    db_aft = sorted([e for e in elig if e[2] != "SUPREME_COURT" and e[1] in ("AFT", "COURT_MARTIAL")], key=lambda e: int(e[0]["rank"]))
    db_svc = sorted([e for e in elig if e[2] != "SUPREME_COURT" and e[1] == "ARMED_FORCES_SERVICE_PARTY"], key=lambda e: int(e[0]["rank"]))
    pick = sc[:13]
    pick += db_aft[: 25 - len(pick)]
    pick += db_svc[: 25 - len(pick)]
    rows = []
    for i, (r, pc, cc) in enumerate(pick, 1):
        rows.append(row(target_id=f"T5-EXC-{r['rank'].zfill(4)}", workstream_target="5", priority=str(i),
                        description=f"{r['court']} {r['decided']} {r['title'][:120]}", action="FETCH", url=r["source_url"],
                        expected_sha256=r["sha256"], original_filename=r["source_url"].rsplit("/", 1)[-1],
                        selection_reason=f"T1 rank {r['rank']} score {r['score']}; party={pc}; court={cc}",
                        provenance=f"C11 RE_ACQUISITION_MANIFEST.csv doc_id {r['doc_id']} (crawler-logged sha256)"))
    with open(ACQ / "T1_PRIORITISATION.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["rank", "doc_id", "court", "title", "signals", "score", "party_class", "court_class", "selected"])
        chosen = {r["rank"] for r, _, _ in pick}
        for r, pc, cc in sorted(elig, key=lambda e: int(e[0]["rank"])):
            w.writerow([r["rank"], r["doc_id"], r["court"], r["title"], r["signals"], r["score"], pc, cc,
                        "YES" if r["rank"] in chosen else "NO"])
    print(f"T1 rows {len(allr)}, eligible {len(elig)} (SC {len(sc)}, DB-AFT/CM {len(db_aft)}, DB-service {len(db_svc)}), picked {len(pick)}")
    return rows


def main() -> int:
    rm = raw_manifest()
    rows = incomplete_targets(rm) + sc_orders() + statutory() + excluded_t1()
    for r in rows:
        for u in (r["url"],):
            if u and host_of(u) in FORBIDDEN:
                r["action"] = "FORBIDDEN_HOST"
    with open(ACQ / "TARGETS.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    from collections import Counter
    print(Counter((r["workstream_target"], r["action"]) for r in rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
