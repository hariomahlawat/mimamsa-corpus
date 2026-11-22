#!/usr/bin/env python3
"""Read-only baseline: inventory + 25-ID pilot selection manifest. Writes only to OUT."""
import csv, hashlib, json, re, sys, collections
from pathlib import Path

SRC = Path(sys.argv[1])   # checkout of legal-knowledge/claude-audit-agents-v1
OUT = Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
KB = SRC / "legal_knowledge/curated_originals/knowledge_base/v0.9/records_658.jsonl"
CASES = SRC / "legal_knowledge/curated_originals/case_law/v0.9/cases_53.jsonl"
SEED = "MIMAMSA-PILOT-01"

def sha(b): return hashlib.sha256(b).hexdigest()

def load(p):
    raw = p.read_bytes()
    lines = [l for l in raw.split(b"\n") if l.strip()]
    recs = []
    for n, l in enumerate(lines, 1):
        o = json.loads(l)
        recs.append({"line": n, "id": o["id"], "obj": o,
                     "line_sha256": sha(l),
                     "canonical_sha256": sha(json.dumps(o, sort_keys=True, ensure_ascii=False,
                                                        separators=(",", ":")).encode())})
    return raw, recs

kb_raw, kb = load(KB)
case_raw, cases = load(CASES)

def family(rid, module):
    if rid.startswith("KB-"): return "CORE_KB (earlier notes, all modules)"
    for p, f in [("HCE-", "HCE (M03)"), ("SC", "HCE (M03)"), ("J-", "HCE (M03)"),
                 ("COI-", "COI (M04)"), ("CM-", "CM (M05)"), ("ADM-", "ADM (M06_M07)"),
                 ("PEN-", "PEN (M08)"), ("CIV-", "CIV/V8"), ("V8-", "CIV/V8"),
                 ("AFT-", "AFT/V7"), ("V7-", "AFT/V7"), ("EV-", "EV/V9"), ("V9-", "EV/V9")]:
        if rid.startswith(p): return f
    return "UNMAPPED"

kbi = {r["id"]: r for r in kb}
inventory = {
    "generated_on": "2026-11-22",
    "nature": "READ-ONLY BASELINE. Research inventory; no legal verification implied.",
    "git": {"audit_branch": "legal-knowledge/claude-audit-agents-v1@74014b4",
            "staging_branch": "legal-knowledge/v2.5-staging@910a9e6", "main": "main@21de353"},
    "canonical_store": {
        "hf_dataset": "hariomahlawat/mimamsa-corpus (private)",
        "access": "READ via Hugging Face MCP connector (listing/cat). No HF token in container: direct byte download returned HTTP 401.",
        "hf_original_sizes_match_github": {"records_658.jsonl": 510586, "cases_53.jsonl": 179385},
        "hf_byte_hash_parity": "NOT VERIFIED (size match only)"},
    "knowledge_base": {
        "path": str(KB.relative_to(SRC)), "file_sha256": sha(kb_raw), "bytes": len(kb_raw),
        "records": len(kb), "unique_ids": len({r["id"] for r in kb}),
        "by_module": dict(collections.Counter(r["obj"]["module"] for r in kb)),
        "by_inferred_volume_family": dict(collections.Counter(family(r["id"], r["obj"]["module"]) for r in kb)),
        "by_kind": dict(collections.Counter(r["obj"]["kind"] for r in kb)),
        "by_status": dict(collections.Counter(r["obj"]["status"] for r in kb)),
        "operational_clearance_true": sum(1 for r in kb if r["obj"].get("operational_clearance")),
        "field_shapes": {", ".join(sorted(k)): v for k, v in collections.Counter(
            tuple(sorted(r["obj"])) for r in kb).items()},
        "records_with_url": sum(1 for r in kb if r["obj"].get("url")),
        "volume_mapping_caveat": "No explicit volume field exists. 'Volume family' is INFERRED from ID prefixes "
                                 "(V7=AFT, V8=CIV, V9=EV prefixes support it); owner must confirm the nine-volume mapping.",
        "record_hash_convention": "line_sha256 = SHA-256 of the exact JSONL line bytes (UTF-8, no trailing newline)."},
    "case_law": {
        "path": str(CASES.relative_to(SRC)), "file_sha256": sha(case_raw), "bytes": len(case_raw),
        "records": len(cases), "unique_ids": len({r["id"] for r in cases}),
        "courts": dict(collections.Counter(r["obj"]["court"] for r in cases)),
        "source_status": dict(collections.Counter(r["obj"]["source_status"] for r in cases)),
        "post_decision_treatment_status": dict(collections.Counter(
            r["obj"]["post_decision_treatment_status"] for r in cases)),
        "review_status": dict(collections.Counter(r["obj"]["review_status"] for r in cases)),
        "original_pdf_sha256_populated": sum(1 for r in cases if r["obj"].get("original_pdf_sha256"))},
    "corpus_reported_not_recounted": {
        "documents": 3481, "raw_files": 3197,
        "source": "PROGRESS.md 2026-11-22 and HF crosswalk/v2.7 summary (rev 3129636); NOT independently recounted (no byte access to data/manifest.csv)",
        "judgments": {"relevant": 2331, "borderline": 1035, "not_checked": 47, "removed": 121027},
        "aft_judgments": "NOT COLLECTED (blocked from container per PROGRESS.md)"},
}
(OUT / "inventory.json").write_text(json.dumps(inventory, indent=2, ensure_ascii=False))
with open(OUT / "kb_record_hashes.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["record_id", "line", "module", "kind", "status", "line_sha256", "canonical_sha256"])
    for r in kb: w.writerow([r["id"], r["line"], r["obj"]["module"], r["obj"]["kind"], r["obj"]["status"], r["line_sha256"], r["canonical_sha256"]])
with open(OUT / "case_record_hashes.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["case_id", "line", "title", "decision_date", "line_sha256", "canonical_sha256"])
    for r in cases: w.writerow([r["id"], r["line"], r["obj"]["title"], r["obj"]["decision_date"], r["line_sha256"], r["canonical_sha256"]])

# ---- Pilot: purposive strata (rationale per ID) + seeded controls
P = [
 ("STATUTORY", "HCE-010", ["statutory-auditor"], "States accused 'is not obliged' to make SoE statement: exact wording disputed (Rule 23(3) / S.R.O. 484 blocker EX36-001)."),
 ("STATUTORY", "CM-013", ["statutory-auditor"], "Brief-listed supersession: AA s.127 omitted 1992; verify amending Act, date and ss.125-126 text."),
 ("STATUTORY", "HCE-017", ["statutory-auditor", "procedure-auditor"], "Rank-specific limits on ss.80-82 punishments; P0 domain (punishments); check against s.81 text and Appendix III."),
 ("STATUTORY", "CIV-033", ["statutory-auditor"], "CrPC s.475 -> BNSS s.521 mapping; corpus correspondence table has no BNSS s.521 row (gap)."),
 ("STATUTORY", "CM-025", ["statutory-auditor"], "Claims 2025 AA s.133 still names Indian Evidence Act 1872; IEA->BSA transition (brief supersession case)."),
 ("STATUTORY", "EV-002", ["statutory-auditor"], "BSA s.170 repeal/savings for pending proceedings; temporal-validity test, Volume EV/V9."),
 ("PROCEDURE", "HCE-004", ["procedure-auditor"], "Rule 22(1) proviso after CoI conditional on Rule 180; 1993 amendment (S.R.O. 17(E)) chain unverified."),
 ("PROCEDURE", "COI-025", ["procedure-auditor"], "Rule 182 use of CoI evidence and exceptions; v2.8 'narrow text match' only."),
 ("PROCEDURE", "CM-011", ["procedure-auditor", "statutory-auditor"], "AA s.122 limitation computation and exceptions; P0 (court-martial)."),
 ("PROCEDURE", "ADM-009", ["procedure-auditor"], "Rule 17 notice / s.20 administrative action exceptions; Volume ADM."),
 ("PROCEDURE", "AFT-011", ["procedure-auditor", "statutory-auditor"], "AFT Act ss.21-22 deemed exhaustion/limitation; record itself flags a statutory-text issue."),
 ("JUDGMENT", "KB-026", ["judgment-auditor"], "Virendra Kumar 2020 paras 12-16; official SC PDF archived on HF (judgment_originals/sci/2020)."),
 ("JUDGMENT", "PEN-043", ["judgment-auditor"], "Dharamvir/Rajbir/N S Yadav presumption vs 2026 INSC 993 (Isaac); brief-listed supersession case."),
 ("JUDGMENT", "CIV-019", ["judgment-auditor", "statutory-auditor"], "Electronic evidence; Navjot s.65B line overruled in part (EX36-004); record cites only BSA."),
 ("JUDGMENT", "KB-028", ["judgment-auditor"], "Parashotam Dass 2023 paras 24-30: HC Art 226 review of AFT orders (brief-listed)."),
 ("JUDGMENT", "PEN-J-01", ["judgment-auditor"], "Dharamvir Singh 2013 digest: identity/citation and later treatment (Isaac 2026)."),
 ("COMMAND_AUTHORITY", "KB-003", ["procedure-auditor", "statutory-auditor"], "CO summary punishment powers ss.79-82 (P0: coercive powers)."),
 ("COMMAND_AUTHORITY", "CM-003", ["statutory-auditor"], "GCM/DCM convening authority ss.109-111, Rule 37 (P0: court-martial authority)."),
 ("COMMAND_AUTHORITY", "COI-008", ["procedure-auditor"], "CoI assembling authority Rule 177(3) and Rule 185 special procedure."),
 ("COMMAND_AUTHORITY", "CIV-008", ["statutory-auditor", "procedure-auditor"], "s.125 forum-choice authority vs unit CO; 1978 adjustment rules."),
 ("CROSS_VOLUME", "EV-016", ["cross-volume-auditor"], "SoE caution in V9 vs HCE-010/KB-006/V9-CL-04 (Rule 23(3) wording consistency)."),
 ("CROSS_VOLUME", "CIV-034", ["cross-volume-auditor"], "BSA s.1(2) applies to courts-martial vs CM-025 (AA s.133 names IEA) and CIV-019."),
 ("CROSS_VOLUME", "AFT-004", ["cross-volume-auditor", "judgment-auditor"], "AFT s.14 vs s.15 vs CM-036/KB-022 (s.3(o) exclusions); P S Gill 2019 caveat proposed in v2.8."),
]
RISK = re.compile(r"rule\s*(22|23|180|182)|section|s\s?\d|§|court-?martial|punish|arrest|custody|limitation|BNS|BSA|IPC|CrPC|"
                  r"pension|AFT|jurisdiction|AFSPA|warrant|supreme court|\sv\s|INSC|SCC|rule\s*\d|discharg|dismiss|terminat|disclos|sentence|charge|evidence|confess", re.I)
chosen = {p[1] for p in P}
pool = [r for r in kb if r["id"] not in chosen and r["obj"]["kind"] in ("TEMPLATE", "DRAFTING_AID", "CHECKLIST", "EARLIER_NOTE", "NOTE")
        and not RISK.search(r["obj"]["title"] + " " + r["obj"]["body"] + " " + str(r["obj"]["references"]))]
pool.sort(key=lambda r: sha((SEED + r["id"]).encode()))
controls = []
for r in pool:
    if len(controls) == 2: break
    if controls and family(r["id"], r["obj"]["module"]) == family(controls[0]["id"], controls[0]["obj"]["module"]): continue
    controls.append(r)
for r in controls:
    P.append(("CONTROL", r["id"], ["independent-reviewer"], f"Seeded control (seed {SEED}, lowest SHA-256(seed+id) among {len(pool)} records with no high-risk keyword)."))

assert len(P) == 25 and len({p[1] for p in P}) == 25 and all(p[1] in kbi for p in P)
NAMED = {  # 53-case rows whose party name appears verbatim in the KB record (asserted below)
 "KB-026": {"DCLR-SC-2020-002": "virendra kumar"},
 "KB-028": {"DCLR-SC-2023-009": "parashotam dass"},
 "PEN-043": {"DCLR-SC-2013-N08": "dharamvir", "DCLR-SC-2015-N09": "rajbir"},
 "PEN-J-01": {"DCLR-SC-2013-N08": "dharamvir"},
}
SUBJECT = {  # subject-matter leads (case NOT named in record) - for judgment-auditor to test as MISSING_AUTHORITY
 "CIV-019": ["DCLR-SC-2005-L01", "DCLR-SC-2014-N12"],
 "AFT-004": [], "COI-008": [],
}
def case_links(rid, o):
    t = (o["title"] + " " + o["body"] + " " + str(o["references"])).lower()
    out = []
    for cid, name in NAMED.get(rid, {}).items():
        assert name in t and cid in {c["id"] for c in cases}, (rid, cid)
        out.append({"case_id": cid, "basis": f"party name '{name}' appears in record text"})
    for cid in SUBJECT.get(rid, []):
        assert cid in {c["id"] for c in cases}
        out.append({"case_id": cid, "basis": "subject-matter lead only; case not cited by record"})
    return out
blind = {"KB-006", }  # placeholder; blind set chosen below
sel = []
for stratum, rid, agents, why in P:
    r = kbi[rid]
    sel.append({"record_id": rid, "stratum": stratum, "module": r["obj"]["module"],
                "inferred_volume_family": family(rid, r["obj"]["module"]), "kind": r["obj"]["kind"],
                "status": r["obj"]["status"], "title": r["obj"]["title"], "source_line": r["line"],
                "original_line_sha256": r["line_sha256"], "original_canonical_sha256": r["canonical_sha256"],
                "first_pass_agents": agents, "rationale": why,
                "linked_53_case_rows_UNVERIFIED": case_links(rid, r["obj"])})
BLIND = ["HCE-010", "HCE-017", "CM-011", "KB-003", "PEN-043", "AFT-004", "CIV-033", sel[-1]["record_id"]]
for s in sel: s["independent_review"] = "BLIND_BEFORE_FIRST_PASS" if s["record_id"] in BLIND else "AFTER_FIRST_PASS_P0_P1_ONLY"
manifest = {"batch_id": "PILOT-01", "status": "PROPOSED - AWAITING OWNER APPROVAL", "generated_on": "2026-11-22",
            "input_snapshot": {"kb_file_sha256": sha(kb_raw), "cases_file_sha256": sha(case_raw),
                               "git_ref": "origin/legal-knowledge/claude-audit-agents-v1@74014b4"},
            "selection_method": "Purposive stratified selection (23 IDs, rationale per ID) per PILOT_AND_ACCEPTANCE.md strata, "
                                "plus 2 seeded controls (deterministic, reproducible). Deviation: none in stratum counts.",
            "seed": SEED, "strata_counts": dict(collections.Counter(s["stratum"] for s in sel)),
            "family_coverage": dict(collections.Counter(s["inferred_volume_family"] for s in sel)),
            "records": sel}
(OUT / "pilot-selection.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
for s in sel:
    print(f'{s["stratum"]:18} {s["record_id"]:9} {s["module"]:8} {s["inferred_volume_family"]:28} {s["independent_review"][:5]} {s["original_line_sha256"][:12]} {[c["case_id"] for c in s["linked_53_case_rows_UNVERIFIED"]]} | {s["title"][:55]}')
print(inventory["knowledge_base"]["by_inferred_volume_family"])
