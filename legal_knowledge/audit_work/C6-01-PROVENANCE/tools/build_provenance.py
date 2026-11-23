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
     ARMY-RULES-CHAIN-01 instrument row for this sha256 with evidence_level IMAGE_CHECKED, or a C6-01 check
     (inputs/page_image_checks_c6.csv) whose identity_result is CONFIRMED. A C6 check marked PARTIAL (page read,
     but a required identity element is not on the copy) is recorded as Ip and does NOT satisfy I.
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
# documentary findings carried on the row (not corrections of the C5 register, which is not edited here; see C6-PREP C5-CO-03)
DOCUMENTARY_FINDINGS = {
    "C5-SRC-P0-AA-AMD-ACT13-1975": ["documentary finding (WSA-PIC-29; C6-01 verification F-04; C5-CO-03): the Gazette masthead reads Hindi "
                                    "issue No.16 but English issue No.15 on the image (the English number is recorded as uncertain in WSA-PIC-29); the C5 master title gives No.16 only. Cite the issue as "
                                    "'No.16 (Hindi masthead) / No.15 (English masthead)' until resolved against another copy of the same issue; "
                                    "Part II s.1, 29-03-1975, Act No.13 of 1975 and p.81 are confirmed; a handwritten '17'-like mark and a faint circular "
                                    "stamp appear right of the masthead on p.1 (Fable F-18; coordinator re-read 2026-11-23), unexplained; India Code serves "
                                    "download-specific bytes, so a re-acquisition would be a NEW copy with a new sha256 and could document these held bytes only "
                                    "through a defined equivalence test (cf. C5 RV-13: Act 37 copies differ only in a trailer ID)"],
}
# Disputed facts inside a transcribed identity (not resolved here; see SOURCE-LIBRARY-C5 D7 "Disagreements").
SO4010_DISPUTE = ("date of MHA Notification S.O. No. 4010 as transcribed from the RS page ('6th December, 1986', C5-PIC-02 4x zoom; "
                  "PILOT-01 S-REVA-021) is DISPUTED: the Cycle 5 independent reviewer read '08-12-1986' (SOURCE-LIBRARY-C5 review RV-01); "
                  "the disagreement is OPEN (SOURCE-LIBRARY-C5/reports/D7_INDEPENDENT_REVIEW_REPORT.md, Disagreements); the notification "
                  "itself is not held and its authoritative date is NOT_VERIFIED; the Gazette of S.O. 4010/1986 is the evidence required to settle it; date semantics are also UNVERIFIED (whether 'dated' is the "
                  "signing date or the Gazette issue date; 6 December 1986 fell on a Saturday, the weekly Gazette day: reviewer inference, Fable F-20); "
                  "the sitting date 03-03-1987 rests on the archive file name, not on the printed page (Fable F-02)")
IDENTITY_ANNOTATIONS = {
    "C5-SRC-P0-AR-AMD-AR-008": " [the held file is the 05-01-1963 r.188(e) declaration; whether the 'S.R.O. 34 dated 5-6-1963' listed in the 1988, "
                               "1993 and 2003 Government notes is a misdate of this instrument or a different, unlocated instrument is UNVERIFIED "
                               "(R23 S-REVD-002 'IDENTITY MISMATCH WITH TARGET'; amendment search: 'absence not proven')]",
    "C5-SRC-P2-RS-PAPERS-LAID-1987": " [S.O. 4010 date as transcribed from the RS page; DISPUTED (C5 RV-01 reads 08-12-1986; C5 D7 disagreement OPEN); "
                                     "authoritative notification date NOT_VERIFIED]",
}
DOCUMENTARY_FINDINGS_EXTRA = {
    "C5-SRC-P0-AR-AMD-AR-008": ["documentary finding (Fable F-03): the notes' 'S.R.O. 34 dated 5-6-1963' is not shown to be this 05-01-1963 "
                                "instrument; identity of the listed amending instrument UNVERIFIED; no amendment-chain inference may rest on this copy"],
    "C5-SRC-P2-DHC-RULES-CH6": ["currency markers (Fable F-19): p.5 cites Army Act ss.125, 126 and 127, but s.127 was omitted by Act 37/1992 "
                                "(SOURCE-LIBRARY-C5 RV-26), and the chapter reproduces the 1952 Rules (PILOT-01 T5-03); currency UNKNOWN, treat as historical text"],
"C5-SRC-P2-RS-PAPERS-LAID-1987": ["documentary finding: " + SO4010_DISPUTE]}
# Proposals withheld by owner instruction: kept on record (append-only) but never simulated or approvable as they stand.
WITHHELD = {
    "C5-SRC-P2-RS-PAPERS-LAID-1987": "WITHHELD (owner instruction, PR #33 finalisation 2026-11-23): retained as a discovery/evidence candidate, "
                                     "not approved as authenticated parliamentary evidence; the retrieval record marks authenticity UNCONFIRMED and "
                                     "the URL is an archive.org item page, not a verified file URL; its procedural value as a record of laying "
                                     "is distinct from the legal authority of the notification it mentions",
}
# copy-level findings (keyed by copy_id, never by source: one copy's facts do not attach to its siblings)
COPY_FINDINGS = {
    "C5-SRC-J-SC-2015-RAJBIR~C2": ["copy finding (Fable F-01): its only locator is a parenthesis inside copy C1's retrieval record S-BLIND-013 "
                                   "(retrieved_on/by belong to C1); it is not a duplicate of C1 (163,859 bytes / 21 pp. vs 230,938 / 20 pp.); pp.20-21 are "
                                   "a Record of Proceedings ending '(Signed reportable judgment is placed on the file)'; describe it as 'judgment text + ROP of "
                                   "13-02-2015'; page equivalence to the JUDIS copy NOT established (C5 copy register); its embedded signature range does not "
                                   "cover the file (inputs/copy_structure_c6.csv); needs its own retrieval record and a page comparison"],
}
NEXT_STEP_OVERRIDES = {
    "C5-SRC-J-SC-2015-RAJBIR~C2": "its own retrieval record (URL, date, sha256 of these bytes) and a page-level comparison with the JUDIS copy; until then not an anchor copy",
    "C5-SRC-P2-RS-PAPERS-LAID-1987~C1": "an RS Debates record with affirmative authenticity and the printed sitting date; separately, the Gazette of S.O. 4010/1986 to settle the date dispute; WITHHELD meanwhile",
}
WATERMARKED_GAZETTE_REHOSTS = {"C5-SRC-P0-TRA-2026"}  # C6-PIC-01/02: IndiaCode watermark over an e-Gazette page
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
        with open(fn, encoding="utf-8") as fh:
            recs = json.load(fh)
        for o in recs:
            s = o.get("sha256") or ""
            loc = o.get("locator") or ""
            for s2 in sorted(set(HEX.findall(loc)) - {s}):  # another copy's sha256 recorded inside a retrieval record's locator
                before = [u for u in re.finditer(r"https?://[^ ;),]+", loc) if u.end() <= loc.index(s2)]
                if before:
                    ev[s2].append(("L3lead", f"{Path(fn).parent.parent.name}/sources/{Path(fn).name}#{o.get('source_id', '')} (locator)",
                                   f"{before[-1].group(0)} | retrieved_on={o.get('retrieved_on')} | retrieved_by={o.get('retrieved_by')} | sha256 stated in locator"))
            if HEX.fullmatch(s) and re.search(r"https?://", loc):
                # a record that itself disclaims authenticity, or reports NOT_FOUND / CONFLICTING, is a lead, not a locator (Fable F-02)
                disclaimed = str(o.get("authenticity", "")).upper() == "UNCONFIRMED" or o.get("verification_state") in ("NOT_FOUND", "CONFLICTING")
                ev[s].append(("L3x" if disclaimed else "L3", f"{Path(fn).parent.parent.name}/sources/{Path(fn).name}#{o.get('source_id', '')}",
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
    for r in read(PKG / "inputs/page_image_checks_c6.csv"):  # C6-01 checks on held copies (no download); PARTIAL never counts as I
        s = r["document_sha256"].strip()
        if HEX.fullmatch(s) and HEX.fullmatch(r["render_png_sha256"].strip()) and r["identity_result"] in ("CONFIRMED", "PARTIAL"):
            ev[s].append(("I" if r["identity_result"] == "CONFIRMED" else "Ip", f"C6-01-PROVENANCE/inputs/page_image_checks_c6.csv#{r['check_id']}",
                          f"{r['identity_result']}: {r['register_mismatch']}"[:200]))
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
    struct = {r["sha256"]: r for r in read(PKG / "inputs/copy_structure_c6.csv")}
    held_index = defaultdict(list)
    for r in read(AW / "CALIBRATION-02/registers/held_sources_scratchpad.csv"):
        held_index[r["sha256"]].append(r["scratchpad_relative_path"])
    snaps = {}
    for rel in ("ACQ-01/archive_org_metadata_snapshot.json", "ACQ-02/archive_org_metadata_snapshot_acq02.json"):
        with open(AW / rel, encoding="utf-8") as fh:
            snapdata = json.load(fh)
        for ident, d in snapdata.items():
            for f in d.get("pdf_files", []) + d.get("files", []):
                snaps[(f.get("md5"), f.get("sha1") or "", str(f.get("size")))] = (f"{rel}#{ident}/{f.get('name')}", f"https://archive.org/download/{ident}/{f.get('name')}"
                                                                                  + (" [archive file source=derivative]" if f.get("source") == "derivative" else ""))
    ev = collect()
    url_by_sha = defaultdict(set)
    for s, items in ev.items():
        for k, _ref, det in items:
            if k in ("L1", "L3", "L3x", "WSB", "L4") and "(locator)" not in _ref:
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
        nums = re.findall(r"\d{3,5}", re.sub(r"\(.*?\)", " ", m["title"]))  # year or case number outside parentheses (Fable F-10)
        t_ok = bool(court and keys and all(k.lower() in p1 for k in keys[:2]) and any(n in p1 for n in nums))
        if t_ok:
            items.append(("T", "C6-01-PROVENANCE/inputs/held_copy_facts.csv#" + c["copy_id"], f"p.1 text contains {keys[:2]} and {[n for n in nums if n in p1]}"))
        L = sorted(k for k in {k for k, _, _ in items} if k in ("L1", "L2", "L3", "L4", "L5", "L6"))
        # locator strength: FULL = sha256 recorded with a URL locator (L1/L3/L4-with-URL) or archive size+md5+sha1 (L2);
        # MD5_SIZE = archive md5 and size only; IDENTIFIER_SHA = sha256 with a repository identifier but no URL (L4);
        # MD5 = md5 only (L5/L6). PROVENANCE_DOCUMENTED needs FULL only (Cycle 4 bar; verification F-02).
        # MD5_SIZE, IDENTIFIER_SHA and MD5 never qualify.
        full = (any(k in ("L1", "L3") for k, _, _ in items) or any(k == "L4" and d.startswith("http") for k, _, d in items)
                or any(k == "L2" and ("size/md5/sha1 OK" in d or ("sha1" in d and "no sha1" not in d)) for k, _, d in items))
        strength = ("FULL" if full
                    else "MD5_SIZE" if any(k == "L2" for k, _, _ in items)
                    else "IDENTIFIER_SHA" if any(k == "L4" for k, _, _ in items) else "MD5" if L else "NONE")
        I = "I" in kinds
        X = contradictions(s, url_by_sha)
        lead = bool(re.search(r"in\.gazette\.[a-z.]+\d", c["held_paths"])) or bool({"I?", "L3lead", "L3x"} & kinds)
        outcome = classify(strength, bool(I or t_ok), bool(X), bool(L), lead)
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
            if "Ip" in kinds:
                gaps.append("identity page image-checked but only PARTIAL: " + "; ".join(sorted({d.split(': ', 1)[1] for k, _, d in items if k == "Ip"})))
            else:
                gaps.append("identity not verified on a page image" + ("" if court else " (scanned/official publication: text layer not accepted)"))
        if not dates:
            gaps.append("no retrieval date in a retrieval record" + (" (only a register date)" if regdates else ""))
        gaps += DOCUMENTARY_FINDINGS.get(c["source_id"], []) + DOCUMENTARY_FINDINGS_EXTRA.get(c["source_id"], []) + COPY_FINDINGS.get(c["copy_id"], [])
        if c["source_id"] in WITHHELD:
            gaps.append(WITHHELD[c["source_id"]])
        siblings = [x["copy_id"] for x in read(AW / "SOURCE-LIBRARY-C5/registers/source_copy_register.csv") if x["source_id"] == c["source_id"] and x["copy_id"] != c["copy_id"]]
        cls = proposed_class(m, outcome, c, struct.get(s), items)
        row = {
            "copy_id": c["copy_id"], "source_id": c["source_id"], "sha256": s, "held_paths": c["held_paths"],
            "source_identity": m["title"] + IDENTITY_ANNOTATIONS.get(c["source_id"], ""), "issuing_authority": m["authority"], "carrier": c["copy_carrier_provenance"],
            "retrieval_url": " ; ".join(urls[:3]) or "; ".join(d.split(" | ")[0] for k, _, d in items if k == "L4") or "NOT_EVIDENCED", "retrieval_date": "; ".join(dates) or ("; ".join(regdates) if regdates else "NOT_EVIDENCED"),
            "retrieval_method": "; ".join(sorted({{"L1": "official URL corroborated by recorded sha256", "L2": "archive.org file matched to item metadata (size/md5/sha1)",
                                                   "L3": "agent retrieval record (source JSON)", "L4": "discovery register download record",
                                                   "L5": "R23 amendment-search record (archive identifier, md5 ok)",
                                                   "L6": "WS-A identity record: md5 equal to archive.org metadata"}[k] for k in L})) or "NOT_EVIDENCED",
            "checksum_evidence": f"sha256 {s}; md5 {f['md5']}; sha1 {f['sha1']}; bytes {f['bytes']}" + ("; byte match: " + ",".join(L) if L else ""),
            "locator_strength": strength,
            "pages": f["pages"], "completeness": m["completeness_status"],
            "identity_verification": "; ".join(f"{k}:{ref}" for k, ref, _ in items if k in ("I", "Ip", "T")) or "NONE",
            "related_copies": ";".join(siblings), "current_authentication_status": f"{m['holding_state']} / C4 register: {c['c4_register_state']}",
            "evidence_items": " | ".join(f"{k}:{ref}" for k, ref, _ in sorted(items)), "contradictions": " | ".join(X) or "NONE_FOUND_IN_SEARCHED_REGISTERS",
            "proposed_outcome": outcome, "proposed_effective_source_class": cls, "remaining_gaps": "; ".join(gaps) or "none recorded",
        }
        rec.append(row)
        if outcome == "PROVENANCE_DOCUMENTED":
            props.append({
                "sha256": s, "document_identity": m["title"] + IDENTITY_ANNOTATIONS.get(c["source_id"], ""), "issuer_or_authority": m["authority"],
                "proposal_status": WITHHELD.get(c["source_id"], "PROPOSED (pending review and owner approval)"),
                "held_paths": "; ".join(sorted(held_index[s])), "carrier": c["copy_carrier_provenance"] if not any(k == "L3" for k, _, _ in items) else c["copy_carrier_provenance"].split(" (as reported")[0],
                "official_locator_recorded": file_url(urls, items) if urls else "; ".join(d.split(" | ")[0] for k, _, d in items if k == "L4"), "provenance_references": "; ".join(ref for k, ref, _ in sorted(items) if k in ("L1", "L2", "L3", "L4", "L5", "L6", "I", "T", "WSB")),
                "provenance_evidence": "; ".join(sorted({{"L1": "official URL with recorded sha256 equal to held bytes",
                                                          "L2": ("size, MD5 and SHA-1 equal to archive.org metadata" if any(k == "L2" and ("size/md5/sha1 OK" in d or ("sha1" in d and "no sha1" not in d)) for k, _, d in items) else "MD5 and size equal to archive.org metadata"),
                                                          "L3": "retrieval record with URL and sha256", "L4": "discovery download record with URL and sha256",
                                                          "L5": "archive identifier with md5 match", "L6": "archive identifier with md5 equal to archived md5 (WS-A)"}[k] for k in L})) + ("; identity image-checked" if I else "; identity read from p.1 text (court PDF)"),
                "authentication_state": "PROVENANCE_DOCUMENTED", "effective_source_class": cls,
                "limitations": "; ".join(x for x in ["C6-01 PROPOSAL - not incorporated; no signature verified"] + gaps + extra_limits(items, cls, c, struct.get(s)) if x),
                "rationale": "Meets the same evidence criteria as the Cycle 4 register rows of its class; requires independent verification (D3) and owner approval before incorporation",
            })
        else:
            unresolved.append({"copy_id": c["copy_id"], "source_id": c["source_id"], "sha256": s, "proposed_outcome": outcome,
                               "what_is_missing": row["remaining_gaps"], "evidence_found": row["evidence_items"] or "none",
                               "next_step": NEXT_STEP_OVERRIDES.get(c["copy_id"], next_step(outcome, m, gaps))})
    return rec, props, unresolved, copies


def classify(strength, identity_ok, contradicted, has_locator, lead):
    """Outcome decision. PROVENANCE_DOCUMENTED requires FULL strength AND identity evidence AND no contradiction
    (Cycle 4 bar; verification F-02). MD5_SIZE, IDENTIFIER_SHA and MD5 never qualify."""
    if contradicted:
        return "AUTHENTICATION_PENDING"
    if strength == "FULL" and identity_ok:
        return "PROVENANCE_DOCUMENTED"
    if has_locator or (identity_ok and lead):
        return "PROVENANCE_PARTIALLY_DOCUMENTED"
    if identity_ok:
        return "IDENTITY_VERIFIED_PROVENANCE_UNDOCUMENTED"
    return "NO_RECOVERABLE_PROVENANCE"


def extra_limits(items, cls, c, st=None):
    out = []
    kinds = {k for k, _, _ in items}
    if "L1" in kinds and not ({"L3", "L4"} & kinds):
        out.append("provenance rests on a register corroboration record (official URL + sha256) without a separate retrieval record; accepted because uncontradicted (Cycle 4 PPS Bedi precedent)")
    if any(k == "L2" and "derivative" in d for k, _, d in items) and cls.startswith("PRIMARY"):
        out.append("the matched archive.org file is a derivative, not the uploaded original")
    urls = " ".join(d for k, _, d in items if k in ("L1", "L3", "WSB"))
    if "/jonew/judis/" in urls or "/judgment/judis/" in urls:
        out.append("JUDIS rendition: re-typed text with CITATION/CITATOR INFO/HEADNOTE material that is not part of the judgment; pinpoints must exclude it (Fable F-16)")
    if "/judgment/judis/" in urls:
        out.append("locator path /judgment/judis/ differs from the /jonew/judis/ form of the other JUDIS rows; locator consistency NOT_CHECKED in V7-S10 (Fable F-17)")
    if "corrected" in c.get("copy_id", "").lower() or "MULLIKOTE" in c["source_id"]:
        out.append("the copy is a CORRECTED judgment at a URL that can be re-served; evidence is a corroboration record with no retrieval date, so the version-to-date link is not evidenced (Fable F-15)")
    if cls == "NON_PRIMARY_PARLIAMENTARY_RECORD":
        out.append("non-primary: records the laying of a notification, not the instrument; the retrieval record states the RS Debates archive copy's "
                   "authenticity as UNCONFIRMED and its URL is an archive.org item page, not the file (owner decision, final review R-08)")
    if cls == "NON_PRIMARY_OFFICIAL_PUBLICATION_COPY" and fidelity_issue(st, items):
        out.append("non-primary (uniform copy-fidelity rule, Fable F-04): " + fidelity_issue(st, items)
                   + ". Document authority (Gazette of India), carrier and copy fidelity are reported separately: identity and provenance are documented, "
                   "fidelity to the issued publication is not. Copies of the same series whose signature range covers the whole file stay primary. "
                   "Class decision reserved for the owner; see reports/TRA2026_CLASS_COMPARISON.md")
    elif cls == "NON_PRIMARY_OFFICIAL_PUBLICATION_COPY":
        if c["source_id"] in WATERMARKED_GAZETTE_REHOSTS:
            out.append("non-primary (conservative): born-digital e-Gazette text re-hosted by India Code with an IndiaCode watermark; the embedded "
                       "signature's byte range ends before the end of the held file, so it cannot cover these bytes (structural observation, "
                       "not a cryptographic check). Cycle 4 gave PRIMARY_GAZETTE_GOVERNMENT_HOSTED_SCAN to the watermarked India Code scan of "
                       "Act 37/1992, so the watermark alone is not the distinction; class decision reserved for the owner (final review R-04)")
        else:
            out.append("non-primary: incomplete or extract copy (see completeness)")
    if cls == "NON_PRIMARY_OFFICIAL_COURT_RENDITION":
        out.append("non-primary: court-system rendition with unknown carrier status, not the judgment copy as issued")
    return out


def file_url(urls, items):
    """Prefer a direct file URL (archive.org /download/ or a .pdf) over an item page (Fable F-13)."""
    cands = list(urls) + [re.search(r"https?://[^ |]+", d).group(0) for k, _, d in sorted(items)
                          if k in ("L2", "L3", "L5", "L6") and re.search(r"https?://[^ |]+", d)]
    direct = [u for u in cands if "/download/" in u or u.lower().endswith(".pdf") or "/bitstreams/" in u]
    return (direct or cands)[0]


def fidelity_issue(st, items):
    """Copy-fidelity rule for born-digital copies (Fable F-04/F-12), applied uniformly: a copy whose embedded signature's byte
    range does not cover the held file, or an archive.org derivative (re-rendered by the archive, not the uploaded file),
    is not shown to be the publication as issued. Structural observation only (inputs/copy_structure_c6.csv)."""
    if st and st["signed_range_covers_file"] == "NO":
        return ("embedded signature byte range " + st["signature_byte_ranges"] + " does not cover the " + st["bytes"] + "-byte held file ("
                + st["eof_markers"] + " %%EOF marker(s); " + ("not an incremental update, so no signed revision can be extracted" if st["eof_markers"] == "1"
                                                            else "the signed revision may be extractable offline") + ")")
    if any(k == "L2" and "derivative" in d for k, _, d in items):
        return "the matched archive.org file is a derivative re-rendered by the archive (producer " + (st or {}).get("producer", "?") + "), not the uploaded original"
    return ""


def proposed_class(m, outcome, copy=None, st=None, items=()):
    if outcome != "PROVENANCE_DOCUMENTED":
        return ""
    if m["publication_type"] != "JUDICIAL" and fidelity_issue(st, items):
        return "NON_PRIMARY_OFFICIAL_PUBLICATION_COPY"  # copy fidelity not established (uniform born-digital rule)
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
        if any("only PARTIAL" in g for g in gaps):
            steps.append("identity elements absent from the held copy (issuing authority, volume, edition/date) must come from another record: the "
                         "printed rules volume, or a court-registry confirmation of the file; the image check cannot supply them")
        if any(("identifier" in g) or ("md5" in g) or ("no locator" in g) for g in gaps):
            steps.append("a retrieval record with URL and sha256 for THESE bytes; an approved re-acquisition creates a new copy (new sha256) and "
                         "documents the held bytes only through a defined equivalence test")
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
    orig_descriptor = EC.Evidence.__dict__["from_dir"]  # restore the original classmethod descriptor (Fable F-25)
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
        EC.Evidence.from_dir = orig_descriptor
        B.check_holding_vs_copies = orig_check
    keys = ("crosswalk_kb_items_by_status", "crosswalk_case_rows_by_status", "kb_records_by_anchor_class")
    return {"rule": "Cycle 5 crosswalk rules unchanged; proposals simulated as register rows", "baseline": {k: base[k] for k in keys},
            "proposed": {k: sim[k] for k in keys}, "authentication_baseline": base["authentication"], "authentication_proposed": sim["authentication"]}


def proposal_id(sha256):
    """Short display ID. The canonical identity of a proposal is its full sha256 (column `sha256`); the ID depends only on
    that copy's bytes, so adding or removing another proposal never renumbers it. Legacy sequential IDs used by the first
    verification and the re-verification are mapped in review/legacy_proposal_id_map.csv."""
    return f"C6-01-AP-{sha256[:8]}"


def outputs():
    rec, props, unresolved, copies = build()
    rec_cols = list(rec[0])
    ids = [proposal_id(p["sha256"]) for p in props]
    if len(set(ids)) != len(ids) or len({p["sha256"] for p in props}) != len(props):
        raise SystemExit("duplicate proposal_id or sha256 in proposals: give ONLY the colliding proposals a longer prefix (other IDs must not change)")
    texts = {
        "provenance_recovery_register.csv": csv_text(rec_cols, rec),
        "source_authentication_proposals.csv": csv_text(["proposal_id", "proposal_status"] + AUTH_COLS, [dict(p, proposal_id=proposal_id(p["sha256"])) for p in props]),
        "unresolved_provenance_register.csv": csv_text(["copy_id", "source_id", "sha256", "proposed_outcome", "what_is_missing", "evidence_found", "next_step"], unresolved),
    }
    with open(AW / "SOURCE-LIBRARY-C5/registers/coverage_summary.json", encoding="utf-8") as fh:
        c5auth = json.load(fh)["authentication"]  # denominators derived, not hard-coded (Fable F-23)
    impact = coverage_impact([p for p in props if p["proposal_status"].startswith("PROPOSED")])  # withheld entries are never simulated
    summary = {
        "denominators": {"held_unique_binaries_c5": c5auth["copies_total"], "held_binary_paths_c5": len(read(AW / "SOURCE-LIBRARY-C5/baseline/held_binaries_manifest.csv")),
                         "undocumented_copies_c5": c5auth["copies_by_evidence_class"]["PROVENANCE_UNDOCUMENTED_COPY"],
                         "scope_sources": len({c["source_id"] for c in copies}), "scope_copies": len(copies)},
        "outcomes_by_copy": dict(sorted(Counter(r["proposed_outcome"] for r in rec).items())),
        "outcomes_by_source_type": dict(sorted(Counter(f'{r["proposed_outcome"]}|{"court" if "-J-" in r["source_id"] else "publication"}' for r in rec).items())),
        "proposals": len(props), "proposals_by_status": dict(sorted(Counter(p["proposal_status"].split(" ")[0] for p in props).items())),
        "proposals_by_class": dict(sorted(Counter(p["effective_source_class"] for p in props).items())),
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
