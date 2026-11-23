"""Cycle 5 register builder (stdlib, deterministic, CI-runnable: reads only files in the repository).

Inputs (never modified):
- earlier registers: ARMY-RULES-CHAIN-01, WS-A-STATUTORY, SOURCE-CONFLICTS-01, CALIBRATION-02, WS-B-JUDGMENTS, WS-D-QUALITY
- this package: baseline/*.csv, discovery/*_candidates.csv, inputs/*.csv (hand-authored, evidence-referenced)

Outputs (registers/): source_master_register.csv (D1), acquisition_register.csv (D3), amendment_register.csv and
provision_amendment_chain.csv (D4), provision_register.csv, source_conflict_register.csv, corpus_crosswalk.csv and
coverage_summary.json (D6). `--check` rebuilds in memory and fails if any committed output differs.

Rules: values from earlier registers are carried verbatim with their origin file and row id; nothing is promoted.
A value the inputs do not give is written as NOT_CAPTURED / NOT_DETERMINED, never inferred."""
import argparse, csv, io, json, re, sys
from collections import Counter, defaultdict
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
AW = PKG.parent
REPO = AW.parents[1]
OUT = PKG / "registers"


def read(p):
    with open(p, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def csv_text(cols, rows):
    b = io.StringIO()
    w = csv.DictWriter(b, fieldnames=cols, lineterminator="\n", extrasaction="raise")
    w.writeheader()
    for r in rows:
        w.writerow({c: r.get(c, "") for c in cols})
    return b.getvalue()


# ---------------------------------------------------------------- schemas (column order is the contract)
COLS = {
    "source_master_register.csv": [
        "source_id", "priority", "title", "authority", "publication_type", "edition", "volume_or_part", "publication_date",
        "effective_date", "effective_date_status", "source_url", "provenance", "document_authority", "carrier_provenance", "authentication_status",
        "rights_status", "access_marking", "sha256", "held_paths", "pages", "text_layer_class", "completeness_status",
        "amendment_chain_status", "currency_status", "holding_state", "discovery_state", "discovery_candidate_ids",
        "acquisition_state", "existing_register_refs", "identity_notes", "evidence"],
    "acquisition_register.csv": [
        "rank", "acq_c5_id", "source_id", "title", "exact_location", "location_check", "justification", "dependencies",
        "access_restrictions", "integrity_pin", "required_approval", "approval_state", "existing_acq_refs", "batch"],
    "amendment_register.csv": [
        "amendment_id", "publication_source_id", "notification_number", "issuing_authority", "notification_date",
        "publication_date", "commencement_as_printed", "effective_date", "effective_date_status", "affected_provisions",
        "gazette_identity", "sha256", "evidence_level", "verification_status", "amendment_chain_status", "origin_register",
        "origin_id"],
    "provision_amendment_chain.csv": [
        "chain_row_id", "publication_source_id", "provision", "instrument_ref", "amendment_instrument", "change_type", "before_text_ref",
        "after_text_ref", "publication_date", "effective_date", "effective_date_status", "applicable_period", "evidence",
        "evidence_level", "superseded_by", "origin_register", "origin_id"],
    "provision_register.csv": [
        "provision_id", "source_id", "chapter", "section_or_rule", "paragraph", "subparagraph", "page",
        "exact_text_reference", "effective_from", "effective_to", "verification_status", "completeness_status",
        "origin_register"],
    "source_conflict_register.csv": [
        "conflict_id", "affected_source", "affected_provision", "source_a", "source_b", "nature_of_conflict", "evidence",
        "legal_adviser_required", "status", "reserved_status", "origin_register", "origin_id"],
    "corpus_crosswalk.csv": [
        "source_id", "provision_id", "knowledge_base_record_id", "case_id", "relationship_type", "evidence_status",
        "review_status", "basis"],
}

# Reserved states fixed by the owner (Cycle 4 closeout); carried, never changed here.
RESERVED = {"C-01": "CONFLICTING (r.23(3))", "C-08": "OPEN (r.193)", "C-09": "PROPOSAL (r.194)", "SC4-01": "OPEN (r.182)"}


def base_source(doc):
    return {"army-rules": "C5-SRC-P0-ARMY-RULES-1954", "army-act": "C5-SRC-P0-ARMY-ACT-1950"}[doc]


# ---------------------------------------------------------------- D4 amendment registers (derived)
def amendment_rows():
    rows = []
    for r in read(AW / "ARMY-RULES-CHAIN-01/army_rules_instrument_register.csv"):
        rows.append({
            "amendment_id": "C5-AMD-" + r["instr_id"], "publication_source_id": base_source("army-rules"),
            "notification_number": r["instrument"], "issuing_authority": "Central Government (Ministry of Defence) under AA s.191 (as printed in instruments; per instrument)",
            "notification_date": r["instrument_date"], "publication_date": r["publication_date"] or "NOT_CAPTURED",
            "commencement_as_printed": r["commencement_as_printed"], "effective_date": r["effective_date"],
            "effective_date_status": r["effective_date_status"], "affected_provisions": r["provisions_affected"],
            "gazette_identity": r["gazette_publication"], "sha256": r["sha256"], "evidence_level": r["evidence_level"],
            "verification_status": r["status"], "amendment_chain_status": "PARTIAL (Army Rules chain: AMENDMENT_CHAIN_INCOMPLETE)",
            "origin_register": "ARMY-RULES-CHAIN-01/army_rules_instrument_register.csv", "origin_id": r["instr_id"]})
    for fn in ("army_act_amendment_chain.csv", "army_act_amendment_chain_addendum_cycle3.csv"):
        for r in read(AW / "WS-A-STATUTORY" / fn):
            rows.append({
                "amendment_id": "C5-AMD-" + r["chain_id"], "publication_source_id": base_source("army-act"),
                "notification_number": f'{r["instrument"]} ({r["number_year"]})' if r["number_year"] else r["instrument"],
                "issuing_authority": "Parliament / Central Government (per instrument)", "notification_date": r["date_of_instrument"],
                "publication_date": r["publication_date"] or "NOT_CAPTURED", "commencement_as_printed": r["commencement_as_printed"],
                "effective_date": r["effective_date"], "effective_date_status": r["effective_date_status"],
                "affected_provisions": r["sections_affected"], "gazette_identity": r["gazette_identity"], "sha256": r["file_sha256"],
                "evidence_level": r["evidence_level"], "verification_status": r["copy_fidelity"],
                "amendment_chain_status": r["amendment_chain_status"], "origin_register": "WS-A-STATUTORY/" + fn, "origin_id": r["chain_id"]})
    extra = PKG / "inputs/amendment_register_additions.csv"
    if extra.exists():
        rows += read(extra)
    return rows


def chain_rows():
    sup = {}
    for r in read(AW / "WS-A-STATUTORY/provision_change_log_supersessions_cycle3.csv"):
        sup.setdefault(r["supersedes_change_id"], []).append(r["supersession_id"])
    rows = []
    for r in read(AW / "WS-A-STATUTORY/provision_change_log.csv"):
        pub = base_source("army-act") if r["instrument_ref"].startswith("AA") else base_source("army-rules")
        rows.append({
            "chain_row_id": "C5-PCH-" + r["change_id"], "publication_source_id": pub, "provision": r["provision"], "instrument_ref": r["instrument_ref"],
            "amendment_instrument": r["instrument"], "change_type": r["change_type"],
            "before_text_ref": r["text_before"] or "NOT_CAPTURED", "after_text_ref": r["text_after_or_summary"] or "NOT_CAPTURED",
            "publication_date": r["publication_date"] or "NOT_CAPTURED", "effective_date": r["effective_date"],
            "effective_date_status": r["effective_date_status"], "applicable_period": r["valid_span"] or "NOT_DETERMINED",
            "evidence": "; ".join(x for x in (f'sha256={r["file_sha256"]}' if r["file_sha256"] else "", r["page_anchor"], r["image_check_ids"]) if x) or "NOT_CAPTURED",
            "evidence_level": r["evidence_level"], "superseded_by": ";".join(sup.get(r["change_id"], [])),
            "origin_register": "WS-A-STATUTORY/provision_change_log.csv", "origin_id": r["change_id"]})
    for i, r in enumerate(read(AW / "ARMY-RULES-CHAIN-01/army_rules_provision_chronology.csv"), 1):
        rows.append({
            "chain_row_id": f"C5-PCH-ARC-{i:03d}", "publication_source_id": base_source("army-rules"), "provision": r["provision"], "instrument_ref": r["instrument_id"],
            "amendment_instrument": f'{r["instrument_id"]} {r["instrument"]}'.strip(), "change_type": r["event"],
            "before_text_ref": "NOT_CAPTURED (see text registers)", "after_text_ref": "NOT_CAPTURED (see text registers)",
            "publication_date": r["publication_date"] or "NOT_CAPTURED", "effective_date": r["effective_date"],
            "effective_date_status": r["effective_date_status"], "applicable_period": r["temporal_note"] or "NOT_DETERMINED",
            "evidence": r["evidence_level"], "evidence_level": r["evidence_level"], "superseded_by": "",
            "origin_register": "ARMY-RULES-CHAIN-01/army_rules_provision_chronology.csv", "origin_id": f"data row {i}"})
    return rows


# ---------------------------------------------------------------- provision register (derived)
def provision_rows(held_sha_by_name):
    comp = {}
    for r in read(AW / "WS-A-STATUTORY/statutory_version_completeness_cycle3.csv"):
        comp[r["provision"].strip()] = r
    rules_sha = held_sha_by_name["army-rules.pdf"]
    rows = []
    for r in read(AW / "CALIBRATION-02/registers/rule_index_spec/compilation_rule_presence.csv"):
        if r["doc_id"] != "rules-army-rules-1954":
            continue
        key = r["rule_key"]  # e.g. r23, r12A
        m = re.fullmatch(r"r(\d+)([A-Z]*)", key)
        label = f"r.{m.group(1)}{m.group(2)}" if m else key
        c = comp.get(label, {})
        rows.append({
            "provision_id": f"army-rules-1954#{key}", "source_id": "C5-SRC-P0-ARMY-RULES-1954-INDIACODE",
            "chapter": "NOT_CAPTURED", "section_or_rule": label, "paragraph": "", "subparagraph": "", "page": r["page"],
            "exact_text_reference": f"sha256:{rules_sha} compilation p.{r['page']} text line {r['text_line']} ({r['basis']})",
            "effective_from": "NOT_DETERMINED", "effective_to": "NOT_DETERMINED",
            "verification_status": "LOCATED_IN_GOVERNMENT_COMPILATION (heading match; wording not verified against Gazette)",
            "completeness_status": c.get("completeness_status", "NOT_ASSESSED_IN_WS-A"),
            "origin_register": "CALIBRATION-02/registers/rule_index_spec/compilation_rule_presence.csv; WS-A-STATUTORY/statutory_version_completeness_cycle3.csv"})
    return rows


# ---------------------------------------------------------------- source conflicts (derived + C5 additions)
def conflict_rows():
    rows = []
    sc = AW / "SOURCE-CONFLICTS-01"
    for fn in ("conflict_determinations.csv",):
        for r in read(sc / fn):
            cid = r["conflict_id"].split()[0]
            rows.append({"conflict_id": "C5-CF-" + cid, "affected_source": r["documents_compared"][:300], "affected_provision": r["provision"],
                         "source_a": r["authority_each"][:300], "source_b": r["provenance_each"][:300],
                         "nature_of_conflict": r["preferred_text_research_determination"][:400], "evidence": r["amendment_history"][:400],
                         "legal_adviser_required": r["legal_review_required"], "status": r["status"], "reserved_status": RESERVED.get(cid, ""),
                         "origin_register": "SOURCE-CONFLICTS-01/" + fn, "origin_id": r["conflict_id"]})
    for fn in ("conflict_determinations_update_2026-11-22b.csv", "conflict_determinations_update_2026-11-22c.csv",
               "conflict_determinations_update_2026-11-22e.csv"):
        for r in read(sc / fn):
            cid = r["conflict_id"].split()[0]
            rows.append({"conflict_id": f"C5-CF-{r['update_id']}", "affected_source": r.get("new_evidence", "")[:300], "affected_provision": r["conflict_id"],
                         "source_a": "", "source_b": "", "nature_of_conflict": r.get("change", "")[:400],
                         "evidence": r.get("revised_research_determination", "")[:400], "legal_adviser_required": r.get("legal_review_required", ""),
                         "status": r.get("status", ""), "reserved_status": RESERVED.get(cid, ""), "origin_register": "SOURCE-CONFLICTS-01/" + fn,
                         "origin_id": r["update_id"]})
    for r in read(sc / "conflict_split_2026-11-22d.csv"):
        rows.append({"conflict_id": "C5-CF-" + r["conflict_id"], "affected_source": f'split from {r["split_from"]}', "affected_provision": r["provision"],
                     "source_a": "", "source_b": "", "nature_of_conflict": r["question"][:400], "evidence": r["evidence_and_links"][:400],
                     "legal_adviser_required": r["legal_review_required"], "status": r["current_state"], "reserved_status": RESERVED.get(r["conflict_id"], ""),
                     "origin_register": "SOURCE-CONFLICTS-01/conflict_split_2026-11-22d.csv", "origin_id": r["conflict_id"]})
    for r in read(AW / "CALIBRATION-02/registers/source_conflicts_c4.csv"):
        rows.append({"conflict_id": "C5-CF-" + r["conflict_id"], "affected_source": "Army Rules 1954 r.182 (S.R.O. 17(E)/1993 item 36)", "affected_provision": r["provision"],
                     "source_a": f'{r["source_1"]} sha256={r["source_1_sha256"]} {r["source_1_locator"]}: {r["source_1_reading"]}'[:400],
                     "source_b": f'{r["source_2"]} sha256={r["source_2_sha256"]} {r["source_2_locator"]}: {r["source_2_reading"]}'[:400],
                     "nature_of_conflict": "printed wording differs between instrument and other texts", "evidence": r["independent_readings"][:400],
                     "legal_adviser_required": "YES", "status": r["state"], "reserved_status": RESERVED.get(r["conflict_id"], ""),
                     "origin_register": "CALIBRATION-02/registers/source_conflicts_c4.csv", "origin_id": r["conflict_id"]})
    for r in read(AW / "WS-B-JUDGMENTS/open_inconsistencies_cycle3.csv"):
        rows.append({"conflict_id": "C5-CF-WSB-" + r["item_id"], "affected_source": r["spec_key"], "affected_provision": "", "source_a": "", "source_b": "",
                     "nature_of_conflict": f'{r["kind"]}: {r["inconsistency"]}'[:400], "evidence": r["evidence"][:400],
                     "legal_adviser_required": r["legal_advisor_state"], "status": r["state"], "reserved_status": "WS-B inconsistency (OPEN; unchanged)",
                     "origin_register": "WS-B-JUDGMENTS/open_inconsistencies_cycle3.csv", "origin_id": r["item_id"]})
    for i, r in enumerate(read(AW / "ARMY-RULES-CHAIN-01/official_note_discrepancies.csv"), 1):
        rows.append({"conflict_id": f"C5-CF-OND-{i:02d}", "affected_source": r["note_in_instrument"], "affected_provision": "Army Rules amendment-history note",
                     "source_a": r["note_in_instrument"], "source_b": "located Gazette instruments (ARMY-RULES-CHAIN-01)",
                     "nature_of_conflict": f'official note lists through {r["listed_through"]}; {r["omits_or_errs"]}'[:400], "evidence": r["observed_on"],
                     "legal_adviser_required": "NO (documentary)", "status": "OPEN (recorded)", "reserved_status": "",
                     "origin_register": "ARMY-RULES-CHAIN-01/official_note_discrepancies.csv", "origin_id": f"data row {i}"})
    extra = PKG / "inputs/conflict_additions.csv"
    if extra.exists():
        rows += read(extra)
    return rows


# ---------------------------------------------------------------- D1 / D3 (inputs + derived columns)
def master_rows(held, cands, auth, targets=None):
    rows = []
    for t in (targets if targets is not None else read(PKG / "inputs/target_publications.csv")):
        shas = [s for s in t["held_sha256"].split(";") if s]
        paths, pages, tl = [], set(), set()
        for s in shas:
            if s not in held:
                raise SystemExit(f"{t['source_id']}: held_sha256 {s} not in baseline/held_binaries_manifest.csv")
            for h in held[s]:
                paths.append(h["held_path"]); pages.add(h["pages"]); tl.add(h["text_layer_class"])
        cids = [c for c in t["discovery_candidate_ids"].split(";") if c]
        for c in cids:
            if c not in cands:
                raise SystemExit(f"{t['source_id']}: discovery candidate {c} not found")
        states = sorted({cands[c]["discovery_state"] for c in cids})
        a = [auth[s] for s in shas if s in auth]
        r = dict(t)
        r.update({
            "sha256": ";".join(shas), "held_paths": ";".join(sorted(paths)), "pages": ";".join(sorted(p for p in pages if p)),
            "text_layer_class": ";".join(sorted(tl)),
            "holding_state": t["holding_state"],
            "discovery_state": ";".join(states) if states else t.get("discovery_state", "") or "NOT_CHECKED",
            "authentication_status": t["authentication_status"] + (f" | C4 register: {a[0]['authentication_state']}/{a[0]['effective_source_class']}" if a else ""),
        })
        if shas and t["holding_state"].startswith("NOT_HELD"):
            raise SystemExit(f"{t['source_id']}: holding_state NOT_HELD but sha256 given")
        if not shas and t["holding_state"].startswith("HELD"):
            raise SystemExit(f"{t['source_id']}: holding_state HELD without sha256")
        rows.append(r)
    return rows


def acquisition_rows(master, rows=None):
    ids = {m["source_id"] for m in master}
    rows = rows if rows is not None else read(PKG / "inputs/acquisition_batches.csv")
    for r in rows:
        if r["source_id"] not in ids:
            raise SystemExit(f"{r['acq_c5_id']}: unknown source_id {r['source_id']}")
        for d in [x for x in r["dependencies"].split(";") if x.startswith("C5-ACQ-")]:
            if d not in {q["acq_c5_id"] for q in rows}:
                raise SystemExit(f"{r['acq_c5_id']}: unknown dependency {d}")
        if r["approval_state"] != "NOT_APPROVED":
            raise SystemExit(f"{r['acq_c5_id']}: approval_state must be NOT_APPROVED in this package")
    return sorted(rows, key=lambda r: int(r["rank"]))


# ---------------------------------------------------------------- D6 crosswalk
def amended_rules():
    """Army Rules provisions with any recorded amendment event or reserved conflict (rule numbers only)."""
    out = {"r23", "r182", "r193", "r194"}  # reserved conflicts (C-01, SC4-01, C-08, C-09)
    texts = [r["provision"] for r in read(AW / "WS-A-STATUTORY/provision_change_log.csv") if not r["instrument_ref"].startswith("AA")]
    texts += [r["provision"] for r in read(AW / "ARMY-RULES-CHAIN-01/army_rules_provision_chronology.csv") if r["event"].lower() not in ("enacted", "enacts", "principal")]
    for t in texts:
        for n in re.findall(r"\br{1,2}\.?\s*(\d+[A-Z]?)", t):
            out.add("r" + n)
    return out


def crosswalk(master):
    m = {x["source_id"]: x for x in master}
    amended = amended_rules()
    mp = {r["key"]: r for r in read(PKG / "inputs/corpus_source_map.csv")}
    rows = []
    for r in read(AW / "WS-D-QUALITY/canonical_coverage.csv"):
        if not r["items"].strip():
            rows.append({"source_id": "NONE", "provision_id": "", "knowledge_base_record_id": r["record_id"], "case_id": "",
                         "relationship_type": "NO_CITATION", "evidence_status": "MISSING_EVIDENCE", "review_status": "NOT_REVIEWED (C5 crosswalk is technical)",
                         "basis": "record carries no source citation (WS-D canonical_coverage items empty)"})
            continue
        for it in [x for x in r["items"].split(" | ") if x]:
            mm = re.match(r"([a-z]+):(.*?)(?:=>([^\[#]+))?\[([a-z-]+)\](?:#(.*))?$", it)
            if not mm:
                rows.append({"source_id": "UNMAPPED", "provision_id": "", "knowledge_base_record_id": r["record_id"], "case_id": "",
                             "relationship_type": "CITES", "evidence_status": "MISSING_EVIDENCE", "review_status": "NOT_REVIEWED",
                             "basis": f"unparsed WS-D item: {it[:120]}"})
                continue
            kind, code, tgt, st, loc = mm.groups()
            key = (tgt or "").strip() or code.strip()
            e = mp.get(key) or mp.get(code.strip())
            sid = e["source_id"] if e else "UNMAPPED"
            src = m.get(sid)
            if sid == "UNMAPPED" or src is None:
                status, why = "MISSING_EVIDENCE", "citation not identified to a C5 source"
            elif not src["holding_state"].startswith("HELD"):
                status, why = "MISSING_EVIDENCE", f"source identified but not held ({src['holding_state']})"
            elif (st == "id" and loc and src["holding_state"].startswith("HELD_PRIMARY") and sid == "C5-SRC-P0-ARMY-RULES-1954"
                  and set(loc.split(",")) & amended):
                status, why = "PARTIAL_MATCH", "as-notified 1954 text held, but a cited rule has a recorded amendment or reserved conflict: current wording needs the chain"
            elif st == "id" and loc and src["holding_state"].startswith("HELD_PRIMARY"):
                status, why = "EXACT_ANCHOR", "identified, provision locator present, primary copy held (anchor to the held version; currency not implied)"
            else:
                status, why = "PARTIAL_MATCH", f"{'inferred identity' if st != 'id' else 'no provision locator' if not loc else 'held copy is ' + src['holding_state']}"
            rows.append({"source_id": sid, "provision_id": f"{key}#{loc}" if loc else "", "knowledge_base_record_id": r["record_id"], "case_id": "",
                         "relationship_type": "CITES", "evidence_status": status, "review_status": "NOT_REVIEWED (C5 crosswalk is technical)",
                         "basis": f"WS-D {kind}:{code}[{st}]; {why}"})
    cases = [json.loads(l) for l in open(REPO / "legal_knowledge/curated_originals/case_law/v0.9/cases_53.jsonl", encoding="utf-8")]
    cmap = {r["key"]: r for r in read(PKG / "inputs/case_source_map.csv")}
    for c in cases:
        e = cmap.get(c["id"])
        sid = e["source_id"] if e else "UNMAPPED"
        src = m.get(sid)
        if src is None:
            status, why = "MISSING_EVIDENCE", "no held official copy mapped"
        elif src["holding_state"].startswith("HELD_PRIMARY"):
            status, why = "EXACT_ANCHOR", "official judgment copy held (identity per mapping input)"
        else:
            status, why = "PARTIAL_MATCH", f"held copy is {src['holding_state']}"
        rows.append({"source_id": sid, "provision_id": "", "knowledge_base_record_id": "", "case_id": c["id"], "relationship_type": "IS_SOURCE_OF_CASE_RECORD",
                     "evidence_status": status, "review_status": "NOT_REVIEWED (C5 crosswalk is technical)",
                     "basis": f"case source_status={c['source_status']}; {why}"})
    return rows


def build():
    held = defaultdict(list)
    by_name = {}
    for h in read(PKG / "baseline/held_binaries_manifest.csv"):
        held[h["rehashed_sha256"]].append(h)
        by_name.setdefault(h["held_path"].rsplit("/", 1)[-1], h["rehashed_sha256"])
    cands = {}
    for p in sorted((PKG / "discovery").glob("*_candidates.csv")):
        for r in read(p):
            if r["candidate_id"] in cands:
                raise SystemExit(f"duplicate candidate id {r['candidate_id']}")
            cands[r["candidate_id"]] = r
    auth = {r["sha256"]: r for r in read(AW / "CALIBRATION-02/registers/source_authentication_register.csv")}
    master = master_rows(held, cands, auth)
    out = {
        "source_master_register.csv": master,
        "acquisition_register.csv": acquisition_rows(master),
        "amendment_register.csv": amendment_rows(),
        "provision_amendment_chain.csv": chain_rows(),
        "provision_register.csv": provision_rows(by_name),
        "source_conflict_register.csv": conflict_rows(),
        "corpus_crosswalk.csv": crosswalk(master),
    }
    texts = {k: csv_text(COLS[k], v) for k, v in out.items()}
    cw = out["corpus_crosswalk.csv"]
    kb = defaultdict(set)
    for r in cw:
        if r["knowledge_base_record_id"]:
            kb[r["knowledge_base_record_id"]].add(r["evidence_status"])
    def rec_class(s):
        return "ALL_EXACT" if s == {"EXACT_ANCHOR"} else "NO_EXACT_ANCHOR" if "EXACT_ANCHOR" not in s else "SOME_EXACT"
    summary = {
        "master_sources": len(master),
        "master_by_priority": dict(sorted(Counter(r["priority"] for r in master).items())),
        "master_by_holding_state": dict(sorted(Counter(r["holding_state"].split(" ")[0] for r in master).items())),
        "acquisition_items": len(out["acquisition_register.csv"]),
        "amendment_rows": len(out["amendment_register.csv"]), "provision_chain_rows": len(out["provision_amendment_chain.csv"]),
        "provision_register_rows": len(out["provision_register.csv"]), "conflict_rows": len(out["source_conflict_register.csv"]),
        "crosswalk_rows": len(cw),
        "crosswalk_kb_items_by_status": dict(sorted(Counter(r["evidence_status"] for r in cw if r["knowledge_base_record_id"]).items())),
        "crosswalk_case_rows_by_status": dict(sorted(Counter(r["evidence_status"] for r in cw if r["case_id"]).items())),
        "kb_records_in_crosswalk": len(kb),
        "kb_records_by_anchor_class": dict(sorted(Counter(rec_class(s) for s in kb.values()).items())),
        "kb_items_by_source": dict(sorted(Counter(r["source_id"] for r in cw if r["knowledge_base_record_id"]).items())),
    }
    texts["coverage_summary.json"] = json.dumps(summary, indent=1, sort_keys=True) + "\n"
    return texts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    texts = build()
    bad = []
    for k, t in texts.items():
        p = OUT / k
        if a.check:
            if not p.exists() or p.read_text(encoding="utf-8") != t:
                bad.append(k)
        else:
            p.write_text(t, encoding="utf-8")
    if bad:
        print("STALE OR DIFFERENT:", ", ".join(bad))
        return 1
    print(texts["coverage_summary.json"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
