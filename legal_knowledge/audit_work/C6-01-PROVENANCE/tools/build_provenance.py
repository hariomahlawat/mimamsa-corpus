"""C6-01 provenance recovery builder (stdlib, deterministic, CI-safe: reads only committed files).

Scope: the 34 sources (36 held copies) whose Cycle 5 holding_state is HELD_OFFICIAL_PUBLICATION_PROVENANCE_UNDOCUMENTED
or HELD_OFFICIAL_COURT_COPY_PROVENANCE_UNDOCUMENTED. The wider set of 54 undocumented copies (which adds
compilations and manuals) is not in scope; denominators are kept separate in the summary.

Evidence is collected per copy from committed registers only; nothing is reconstructed. Each evidence item records
its file and row key. Classification rules (also in reports/C6-01_METHOD.md):
  L  locator with byte identity, any of
     L1 PILOT-01 code register: official_corroboration_url whose official_sha256 equals the copy's sha256
     L2 archive.org metadata byte match: ACQ-02 supplement row with archive size/md5/sha1 all OK for this sha256, or
        an ACQ-01/ACQ-02 metadata snapshot file whose md5 and sha1 and size equal the copy's (held_copy_facts.csv)
     L3 a PILOT-01 sources/*.json record whose sha256 equals the copy's, with a URL locator
     L4 PILOT-01 source_discovery register row whose downloaded_sha256 equals the copy's, with a URL
     (strength FULL = sha256 recorded with a URL (L1/L3/L4-with-URL) or archive size+md5+sha1 (L2); MD5_SIZE,
      IDENTIFIER_SHA and MD5 are weaker and never reach PROVENANCE_DOCUMENTED - Cycle 4 evidence bar)
     L5 R23 amendment_search register row with this sha256, an archive identifier and md5_ok=YES
     L6 WS-A identity_transcription row for this sha256 whose computed md5 equals the archived md5, with an
        archive identifier in the recorded path
  I  identity verified on a page image: a page-image check record (with a 64-hex render hash) for this sha256 in
     ACQ-02 / WS-A / ARMY-RULES-CHAIN-01 / R23 / CALIBRATION-02 / SOURCE-LIBRARY-C5 registers, or an
     ARMY-RULES-CHAIN-01 instrument row for this sha256 with evidence_level IMAGE_CHECKED
  T  identity read from the page-1 text layer (C6 held_copy_facts.csv) and matching the source title keys
     (accepted as identity evidence only for born-digital court PDFs, as in the Cycle 4 PPS Bedi precedent)
  X  contradiction: any committed record pairing this copy's official URL with a different sha256, or a WS-B
     identity row for the case marked as contradicted/disputed
Outcome:
  AUTHENTICATION_PENDING                     X present
  PROVENANCE_DOCUMENTED                      FULL-strength L and (I, or T for a court copy) and no X
  PROVENANCE_PARTIALLY_DOCUMENTED            L without the required identity evidence, or identity evidence plus a
                                             locator lead without byte identity
  IDENTITY_VERIFIED_PROVENANCE_UNDOCUMENTED  I or T but no L and no lead
  NO_RECOVERABLE_PROVENANCE                  none of the above
Proposals (D2) are written only for PROVENANCE_DOCUMENTED, in the CALIBRATION-02 source-authentication register
columns, as ADDITIONS for review. The original register is never edited. `--check` verifies committed outputs."""
import argparse, csv, glob, io, json, re, sys
from collections import Counter, defaultdict
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
AW = PKG.parent
REPO = AW.parents[1]
HEX = re.compile(r"(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])")
SCOPE = ("HELD_OFFICIAL_PUBLICATION_PROVENANCE_UNDOCUMENTED", "HELD_OFFICIAL_COURT_COPY_PROVENANCE_UNDOCUMENTED")
AUTH_COLS = ["sha256", "document_identity", "issuer_or_authority", "held_paths", "carrier", "official_locator_recorded",
             "provenance_references", "provenance_evidence", "authentication_state", "effective_source_class",
             "limitations", "rationale"]


def read(p):
    with open(p, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def csv_text(cols, rows):
    b = io.StringIO()
    w = csv.DictWriter(b, fieldnames=cols, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow({c: r.get(c, "") for c in cols})
    return b.getvalue()


# ------------------------------------------------------------------ evidence collectors (committed files only)
def collect():
    ev = defaultdict(list)  # sha256 -> [(kind, ref, detail)]
    for r in read(AW / "PILOT-01/registers/source_code_resolution_v3.csv"):
        s = (r.get("official_sha256") or "").strip()
        if HEX.fullmatch(s) and r.get("official_corroboration_url"):
            ev[s].append(("L1", f"PILOT-01/registers/source_code_resolution_v3.csv#{r['code']}", r["official_corroboration_url"]))
    for r in read(AW / "ACQ-02/supplement_inventory.csv"):
        s = r["sha256"].strip()
        ok = lambda v: (v or "").strip().lower() in ("yes", "true")  # the register records True/False (verification F: route was dead)
        if HEX.fullmatch(s) and ok(r["archive_size_ok"]) and ok(r["archive_md5_ok"]) and ok(r["archive_sha1_ok"]):
            ev[s].append(("L2", f"ACQ-02/supplement_inventory.csv#{r['supp_id']}", f"{r['url']} (archive size/md5/sha1 OK)"))
        if HEX.fullmatch(s) and r.get("page_image_check_id"):
            ev[s].append(("I?", f"ACQ-02/supplement_inventory.csv#{r['supp_id']}", r["page_image_check_id"]))
    for fn in sorted(glob.glob(str(AW / "PILOT-01/sources/*.json")) + glob.glob(str(AW / "R23-VERIFY-01/sources/*.json"))):  # explicit evidence folders (re-verification N-3)
        for o in json.load(open(fn, encoding="utf-8")):
            s = o.get("sha256") or ""
            loc = o.get("locator") or ""
            for s2 in sorted(set(HEX.findall(loc)) - {s}):  # another copy's sha256 recorded inside a retrieval record's locator
                before = [u for u in re.finditer(r"https?://[^ ;),]+", loc) if u.end() <= loc.index(s2)]
                if before:
                    ev[s2].append(("L3", f"{Path(fn).parent.parent.name}/sources/{Path(fn).name}#{o.get('source_id', '')} (locator)",
                                   f"{before[-1].group(0)} | retrieved_on={o.get('retrieved_on')} | retrieved_by={o.get('retrieved_by')} | sha256 stated in locator"))
            if HEX.fullmatch(s) and re.search(r"https?://", loc):
                ev[s].append(("L3", f"{Path(fn).parent.parent.name}/sources/{Path(fn).name}#{o.get('source_id', '')}",
                              f"{re.search(r'https?://[^ ;)]+', loc).group(0)} | retrieved_on={o.get('retrieved_on')} | retrieved_by={o.get('retrieved_by')}"))
    for r in read(AW / "PILOT-01/registers/source_discovery_2026-11-22.csv"):
        s = r["downloaded_sha256"].strip()
        m = re.search(r"https?://[^ ;,)]+", r["candidate_url_or_identifier"])
        ident = m.group(0) if m else r["candidate_url_or_identifier"].strip()[:160]
        if HEX.fullmatch(s) and ident:
            ev[s].append(("L4", f"PILOT-01/registers/source_discovery_2026-11-22.csv#{r['target_id']}", f"{ident} | register dated 2026-11-22"))
    for r in read(AW / "R23-VERIFY-01/registers/amendment_search_2026-11-22.csv"):
        s = r["sha256"].strip()
        if HEX.fullmatch(s) and r["archive_identifier"] and r["md5_ok"].upper().startswith("YES"):
            ev[s].append(("L5", f"R23-VERIFY-01/registers/amendment_search_2026-11-22.csv#{r['target']}",
                          f"https://archive.org/details/{r['archive_identifier']} | md5_ok | register dated 2026-11-22"))
    for r in read(AW / "WS-A-STATUTORY/identity_transcription_register.csv"):
        s = (r.get("file_sha256") or "").strip()[:64]
        md, am = (r.get("file_md5_computed") or "").strip(), (r.get("archived_md5") or "").strip()
        ident = re.search(r"in\.gazette\.[a-z0-9.\-]+", r.get("scratch_path") or "")
        if HEX.fullmatch(s) and md and md == am and ident:
            ev[s].append(("L6", f"WS-A-STATUTORY/identity_transcription_register.csv#{r['check_id']}", f"https://archive.org/details/{ident.group(0)} | md5 {md} equal to archived md5"))
    # page-image identity checks (render hash required)
    for rel, shacol in (("ACQ-02/page_image_checks_acq02.csv", "document_sha256"), ("WS-A-STATUTORY/identity_transcription_register.csv", "file_sha256"),
                        ("ARMY-RULES-CHAIN-01/page_image_checks_chain.csv", "document_sha256"), ("R23-VERIFY-01/registers/page_image_checks.csv", "document_sha256"),
                        ("CALIBRATION-02/reviews/A/page_image_checks_A.csv", "document_sha256"), ("CALIBRATION-02/reviews/C/page_image_checks_C.csv", "document_sha256"),
                        ("SOURCE-LIBRARY-C5/inputs/page_image_checks_c5.csv", "document_sha256")):
        p = AW / rel
        if not p.exists():
            continue
        for r in read(p):
            s = (r.get(shacol) or "").strip()[:64]
            if HEX.fullmatch(s) and HEX.fullmatch((r.get("render_png_sha256") or "").strip()[:64]):
                ev[s].append(("I", f"{rel}#{r['check_id']}", (r.get("observed_on_image") or r.get("reading") or r.get("independent_transcription") or "")[:160]))
    for r in read(AW / "ARMY-RULES-CHAIN-01/army_rules_instrument_register.csv"):
        m = HEX.search(r["sha256"])
        if m and r["evidence_level"].startswith("IMAGE_CHECKED"):
            ev[m.group(0)].append(("I", f"ARMY-RULES-CHAIN-01/army_rules_instrument_register.csv#{r['instr_id']}", f"{r['instrument']} {r['gazette_publication']} ({r['evidence_locator']})"))
    # WS-B held copies: official URL per sha (corroborating L1/L3, also used for contradiction checks)
    for r in read(AW / "WS-B-JUDGMENTS/tools/held_copies.csv"):
        if HEX.fullmatch(r["sha256"]):
            ev[r["sha256"]].append(("WSB", f"WS-B-JUDGMENTS/tools/held_copies.csv#{r['spec_key']}", f"{r['official_url']} | {r['basis']}"))
    return ev


def contradictions(sha, url_by_sha):
    """Another committed record pairing one of this copy's official URLs with a different sha256."""
    out = []
    urls = url_by_sha.get(sha, set())
    for s2, us in url_by_sha.items():
        if s2 != sha and urls & us:
            out.append(f"URL {sorted(urls & us)[0]} also recorded with sha256 {s2[:12]}")
    for r in read(AW / "WS-B-JUDGMENTS/identity_resolution.csv"):
        if sha in (r.get("held_copy_sha256") or "") and re.search(r"CONTRADICT|DISPUTED", r.get("identity_state", "") + r.get("discrepancies", ""), re.I):
            out.append(f"WS-B identity_resolution {r['spec_key']}: {r['identity_state']}")
    return out


def title_keys(title):
    """Distinctive tokens from the source title used to check page-1 text (case-insensitive)."""
    t = re.sub(r"\(.*?\)", " ", title)
    toks = [w for w in re.findall(r"[A-Za-z]{4,}", t) if w.lower() not in {"union", "india", "versus", "with", "court", "supreme", "gazette",
                                                                               "extraordinary", "army", "rules", "amendment", "part", "section"}]
    return toks[:4]


def build():
    master = {r["source_id"]: r for r in read(AW / "SOURCE-LIBRARY-C5/registers/source_master_register.csv")}
    copies = [c for c in read(AW / "SOURCE-LIBRARY-C5/registers/source_copy_register.csv") if master[c["source_id"]]["holding_state"] in SCOPE]
    facts = {r["sha256"]: r for r in read(PKG / "inputs/held_copy_facts.csv")}
    held_index = defaultdict(list)
    for r in read(AW / "CALIBRATION-02/registers/held_sources_scratchpad.csv"):
        held_index[r["sha256"]].append(r["scratchpad_relative_path"])
    snaps = {}
    for rel in ("ACQ-01/archive_org_metadata_snapshot.json", "ACQ-02/archive_org_metadata_snapshot_acq02.json"):
        for ident, d in json.load(open(AW / rel, encoding="utf-8")).items():
            for f in d.get("pdf_files", []) + d.get("files", []):
                snaps[(f.get("md5"), f.get("sha1") or "", str(f.get("size")))] = (f"{rel}#{ident}/{f.get('name')}", f"https://archive.org/download/{ident}/{f.get('name')}"
                                                                                  + (" [archive file source=derivative]" if f.get("source") == "derivative" else ""))
    ev = collect()
    url_by_sha = defaultdict(set)
    for s, items in ev.items():
        for k, _ref, det in items:
            if k in ("L1", "L3", "WSB", "L4") and "(locator)" not in _ref:
                m = re.match(r"https?://\S+", det)
                if m:
                    url_by_sha[s].add(m.group(0).rstrip("|").strip())
    rec, props, unresolved = [], [], []
    for c in copies:
        s, m = c["sha256"], master[c["source_id"]]
        items = list(ev.get(s, []))
        f = facts[s]
        snap = snaps.get((f["md5"], f["sha1"], f["bytes"]))
        if snap:
            items.append(("L2", snap[0], f"{snap[1]} | md5 {f['md5']} sha1 {f['sha1']} size {f['bytes']} equal to archive.org metadata"))
        else:
            snap = snaps.get((f["md5"], "", f["bytes"]))
            if snap:
                items.append(("L2", snap[0], f"{snap[1]} | md5 {f['md5']} and size {f['bytes']} equal to archive.org metadata (no sha1 in snapshot)"))
        kinds = {k for k, _, _ in items}
        court = m["publication_type"] == "JUDICIAL"
        keys = title_keys(m["title"])
        p1 = f["p1_text_excerpt"].lower()
        t_ok = court and keys and all(k.lower() in p1 for k in keys[:2])
        if t_ok:
            items.append(("T", "C6-01-PROVENANCE/inputs/held_copy_facts.csv#" + c["copy_id"], f"p.1 text contains {keys[:2]}"))
        L = sorted(k for k in {k for k, _, _ in items} if k in ("L1", "L2", "L3", "L4", "L5", "L6"))
        # locator strength: FULL = sha256 recorded with the locator (L1/L3/L4) or archive size+md5+sha1 (L2 full);
        # MD5_SIZE = archive md5 and size only; MD5 = md5 only (L5/L6). PROVENANCE_DOCUMENTED needs FULL or MD5_SIZE.
        full = (any(k in ("L1", "L3") for k, _, _ in items) or any(k == "L4" and d.startswith("http") for k, _, d in items)
                or any(k == "L2" and ("size/md5/sha1 OK" in d or ("sha1" in d and "no sha1" not in d)) for k, _, d in items))
        strength = ("FULL" if full
                    else "MD5_SIZE" if any(k == "L2" for k, _, _ in items)
                    else "IDENTIFIER_SHA" if any(k == "L4" for k, _, _ in items) else "MD5" if L else "NONE")
        I = "I" in kinds
        X = contradictions(s, url_by_sha)
        lead = bool(re.search(r"in\.gazette\.[a-z.]+\d", c["held_paths"])) or "I?" in kinds
        if X:
            outcome = "AUTHENTICATION_PENDING"
        elif strength == "FULL" and (I or t_ok):  # same evidence bar as the Cycle 4 register (verification F-02)
            outcome = "PROVENANCE_DOCUMENTED"
        elif L or ((I or t_ok) and lead):
            outcome = "PROVENANCE_PARTIALLY_DOCUMENTED"
        elif I or t_ok:
            outcome = "IDENTITY_VERIFIED_PROVENANCE_UNDOCUMENTED"
        else:
            outcome = "NO_RECOVERABLE_PROVENANCE"
        urls = sorted(url_by_sha.get(s, set())) or sorted({re.search(r"https?://[^ |]+", d).group(0) for k, _, d in items
                                                           if k in ("L2", "L3", "L5", "L6") and re.search(r"https?://[^ |]+", d)})
        dates = sorted({re.search(r"retrieved_on=(\S+)", d).group(1) for k, _, d in items if k == "L3" and "retrieved_on=" in d})
        regdates = sorted({"register dated 2026-11-22" for k, _, d in items if k in ("L4", "L5")})
        gaps = []
        if not L:
            gaps.append("no locator with byte identity")
        elif strength == "MD5":
            gaps.append("locator matched by md5 only (no size or sha1 record)")
        elif strength == "MD5_SIZE":
            gaps.append("archive match on md5 and size only (no sha1 or sha256 retrieval record)")
        elif strength == "IDENTIFIER_SHA":
            gaps.append("download record gives a repository identifier, not a retrieval URL")
        if not (I or t_ok):
            gaps.append("identity not verified on a page image" + ("" if court else " (scanned/official publication: text layer not accepted)"))
        if not dates:
            gaps.append("no retrieval date in a retrieval record" + (" (only a register date)" if regdates else ""))
        siblings = [x["copy_id"] for x in read(AW / "SOURCE-LIBRARY-C5/registers/source_copy_register.csv") if x["source_id"] == c["source_id"] and x["copy_id"] != c["copy_id"]]
        cls = proposed_class(m, outcome, c)
        row = {
            "copy_id": c["copy_id"], "source_id": c["source_id"], "sha256": s, "held_paths": c["held_paths"],
            "source_identity": m["title"], "issuing_authority": m["authority"], "carrier": c["copy_carrier_provenance"],
            "retrieval_url": " ; ".join(urls[:3]) or "; ".join(d.split(" | ")[0] for k, _, d in items if k == "L4") or "NOT_EVIDENCED", "retrieval_date": "; ".join(dates) or ("; ".join(regdates) if regdates else "NOT_EVIDENCED"),
            "retrieval_method": "; ".join(sorted({{"L1": "official URL corroborated by recorded sha256", "L2": "archive.org file matched to item metadata (size/md5/sha1)",
                                                   "L3": "agent retrieval record (source JSON)", "L4": "discovery register download record",
                                                   "L5": "R23 amendment-search record (archive identifier, md5 ok)",
                                                   "L6": "WS-A identity record: md5 equal to archive.org metadata"}[k] for k in L})) or "NOT_EVIDENCED",
            "checksum_evidence": f"sha256 {s}; md5 {f['md5']}; sha1 {f['sha1']}; bytes {f['bytes']}" + ("; byte match: " + ",".join(L) if L else ""),
            "locator_strength": strength,
            "pages": f["pages"], "completeness": m["completeness_status"],
            "identity_verification": "; ".join(f"{k}:{ref}" for k, ref, _ in items if k in ("I", "T")) or "NONE",
            "related_copies": ";".join(siblings), "current_authentication_status": f"{m['holding_state']} / C4 register: {c['c4_register_state']}",
            "evidence_items": " | ".join(f"{k}:{ref}" for k, ref, _ in sorted(items)), "contradictions": " | ".join(X) or "NONE_FOUND_IN_SEARCHED_REGISTERS",
            "proposed_outcome": outcome, "proposed_effective_source_class": cls, "remaining_gaps": "; ".join(gaps) or "none recorded",
        }
        rec.append(row)
        if outcome == "PROVENANCE_DOCUMENTED":
            props.append({
                "sha256": s, "document_identity": m["title"], "issuer_or_authority": m["authority"],
                "held_paths": "; ".join(sorted(held_index[s])), "carrier": c["copy_carrier_provenance"].split(" (as reported")[0],
                "official_locator_recorded": urls[0] if urls else "; ".join(d.split(" | ")[0] for k, _, d in items if k == "L4"), "provenance_references": "; ".join(ref for k, ref, _ in sorted(items) if k in ("L1", "L2", "L3", "L4", "L5", "L6", "I", "T", "WSB")),
                "provenance_evidence": "; ".join(sorted({{"L1": "official URL with recorded sha256 equal to held bytes",
                                                          "L2": ("size, MD5 and SHA-1 equal to archive.org metadata" if any(k == "L2" and ("size/md5/sha1 OK" in d or ("sha1" in d and "no sha1" not in d)) for k, _, d in items) else "MD5 and size equal to archive.org metadata"),
                                                          "L3": "retrieval record with URL and sha256", "L4": "discovery download record with URL and sha256",
                                                          "L5": "archive identifier with md5 match", "L6": "archive identifier with md5 equal to archived md5 (WS-A)"}[k] for k in L})) + ("; identity image-checked" if I else "; identity read from p.1 text (court PDF)"),
                "authentication_state": "PROVENANCE_DOCUMENTED", "effective_source_class": cls,
                "limitations": "; ".join(x for x in ["C6-01 PROPOSAL - not incorporated; no signature verified"] + gaps + extra_limits(items, cls, c) if x),
                "rationale": "Meets the same evidence criteria as the Cycle 4 register rows of its class; requires independent verification (D3) and owner approval before incorporation",
            })
        else:
            unresolved.append({"copy_id": c["copy_id"], "source_id": c["source_id"], "sha256": s, "proposed_outcome": outcome,
                               "what_is_missing": row["remaining_gaps"], "evidence_found": row["evidence_items"] or "none",
                               "next_step": next_step(outcome, m, gaps)})
    return rec, props, unresolved, copies


def extra_limits(items, cls, c):
    out = []
    kinds = {k for k, _, _ in items}
    if "L1" in kinds and not ({"L3", "L4"} & kinds):
        out.append("provenance rests on a register corroboration record (official URL + sha256) without a separate retrieval record; accepted because uncontradicted (Cycle 4 PPS Bedi precedent)")
    if any(k == "L3" and "(locator)" in ref for k, ref, _ in items) and not any(k == "L3" and "(locator)" not in ref for k, ref, _ in items):
        out.append("URL and sha256 are stated inside another copy's retrieval record only")
    if any(k == "L2" and "derivative" in d for k, _, d in items):
        out.append("the matched archive.org file is a derivative, not the uploaded original")
    if cls == "NON_PRIMARY_PARLIAMENTARY_RECORD":
        out.append("non-primary: records the laying of a notification, not the instrument; RS Debates authenticity of the archive copy not confirmed")
    if cls == "NON_PRIMARY_OFFICIAL_PUBLICATION_COPY":
        out.append("non-primary: incomplete or extract copy (see completeness)")
    if cls == "NON_PRIMARY_OFFICIAL_COURT_RENDITION":
        out.append("non-primary: court-system rendition with unknown carrier status, not the judgment copy as issued")
    return out


def proposed_class(m, outcome, copy=None):
    if outcome != "PROVENANCE_DOCUMENTED":
        return ""
    if m["publication_type"] == "JUDICIAL":
        if copy and copy["copy_carrier_provenance"].startswith("UNKNOWN"):
            return "NON_PRIMARY_OFFICIAL_COURT_RENDITION"  # e.g. a court-system text rendition (verification P3)
        return "PRIMARY_OFFICIAL_COURT_COPY"
    if m["publication_type"] == "PARLIAMENTARY_RECORD":
        return "NON_PRIMARY_PARLIAMENTARY_RECORD"
    if m["publication_type"] == "GAZETTE_NOTIFICATION" and m["carrier_provenance"].startswith("THIRD_PARTY_ARCHIVAL_FACSIMILE"):
        return "PRIMARY_GAZETTE_ARCHIVAL_FACSIMILE"
    return "NON_PRIMARY_OFFICIAL_PUBLICATION_COPY"  # conservative: extracts, incomplete or unclassified official copies


def next_step(outcome, m, gaps=()):
    if outcome == "PROVENANCE_PARTIALLY_DOCUMENTED":
        steps = []
        if any("identity not verified" in g for g in gaps):
            steps.append("page-image identity check of the identity page with a render hash (file is held; no download needed)")
        if any(("identifier" in g) or ("md5" in g) or ("no locator" in g) for g in gaps):
            steps.append("a retrieval record with URL and sha256, i.e. an approved re-acquisition from the official host")
        return "; ".join(steps) or "see remaining gaps"
    if outcome == "IDENTITY_VERIFIED_PROVENANCE_UNDOCUMENTED":
        return "locate a retrieval or corroboration record; otherwise an approved re-acquisition from the official host with sha256 recorded"
    if outcome == "AUTHENTICATION_PENDING":
        return "resolve the contradiction (independent evidence); no promotion"
    return "approved re-acquisition from the official host (C6-02/C6-03) or custodian confirmation"


def coverage_impact(props):
    """Re-run the Cycle 5 builder with the proposals added to the Cycle 4 register (simulation only)."""
    sys.path.insert(0, str(AW / "SOURCE-LIBRARY-C5/tools"))
    import build_registers as B
    EC = B.EC
    orig_from_dir, orig_check = EC.Evidence.from_dir, B.check_holding_vs_copies
    base = json.loads(B.build()["coverage_summary.json"])

    def from_dir(c2, root=None):
        e = orig_from_dir(c2, root)
        for p in props:
            e.register.setdefault(p["sha256"], p)
        return e
    EC.Evidence.from_dir = classmethod(lambda cls, c2, root=None: from_dir(c2, root))
    B.check_holding_vs_copies = lambda m, c: None  # simulation: source-level labels are not re-derived here
    try:
        sim = json.loads(B.build()["coverage_summary.json"])
    finally:
        EC.Evidence.from_dir, B.check_holding_vs_copies = orig_from_dir, orig_check
    keys = ("crosswalk_kb_items_by_status", "crosswalk_case_rows_by_status", "kb_records_by_anchor_class")
    return {"rule": "Cycle 5 crosswalk rules unchanged; proposals simulated as register rows", "baseline": {k: base[k] for k in keys},
            "proposed": {k: sim[k] for k in keys}, "authentication_baseline": base["authentication"], "authentication_proposed": sim["authentication"]}


def outputs():
    rec, props, unresolved, copies = build()
    rec_cols = list(rec[0])
    texts = {
        "provenance_recovery_register.csv": csv_text(rec_cols, rec),
        "source_authentication_proposals.csv": csv_text(["proposal_id"] + AUTH_COLS, [dict(p, proposal_id=f"C6-01-AP-{p['sha256'][:8]}") for p in props]),
        "unresolved_provenance_register.csv": csv_text(["copy_id", "source_id", "sha256", "proposed_outcome", "what_is_missing", "evidence_found", "next_step"], unresolved),
    }
    impact = coverage_impact(props)
    summary = {
        "denominators": {"held_unique_binaries_c5": 67, "held_binary_paths_c5": 93, "undocumented_copies_c5": 54,
                         "scope_sources": len({c["source_id"] for c in copies}), "scope_copies": len(copies)},
        "outcomes_by_copy": dict(sorted(Counter(r["proposed_outcome"] for r in rec).items())),
        "outcomes_by_source_type": dict(sorted(Counter(f'{r["proposed_outcome"]}|{"court" if "-J-" in r["source_id"] else "publication"}' for r in rec).items())),
        "proposals": len(props), "proposals_by_class": dict(sorted(Counter(p["effective_source_class"] for p in props).items())),
        "coverage_impact": impact,
    }
    texts["c6_01_summary.json"] = json.dumps(summary, indent=1, sort_keys=True) + "\n"
    return texts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    texts = outputs()
    bad = []
    for k, t in texts.items():
        p = PKG / "registers" / k
        if a.check:
            if not p.exists() or p.read_text(encoding="utf-8") != t:
                bad.append(k)
        else:
            p.write_text(t, encoding="utf-8")
    if bad:
        print("STALE:", bad)
        return 1
    print(texts["c6_01_summary.json"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
