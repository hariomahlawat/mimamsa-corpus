"""C13 A6 forms build: official-copy transcriptions, R04 comparison, expanded
register, versioned field file, acquisition requests and summary.

  python -I build_a6.py           # write outputs/
  python -I build_a6.py --check   # exit 0 only if outputs reproduce byte-for-byte

Inputs: the hash-verified official copies (a6_common.SOURCES), the MML 2 copy
(comparison only), and the pinned C12 forms_registry outputs (read-only).
Every row carries verification_status DISCOVERED_FROM_SOURCE_NOT_LEGALLY_APPROVED
and legal_approval_state NOT_APPROVED. Nothing here is a legal determination.
"""
import argparse
import csv
import difflib
import hashlib
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import a6_common as C  # noqa: E402
import spec_register as SR  # noqa: E402
import spec_transcriptions as ST  # noqa: E402
import spec_oracle as SO  # noqa: E402

TOOL = "c13-a6-forms/1.1.0"
OUT = os.path.join(C.A6_DIR, "outputs")
VS = "DISCOVERED_FROM_SOURCE_NOT_LEGALLY_APPROVED"
ILL = "[illegible]"
INC = "[INCIPIT_ONLY"
OFFICIAL_SOURCES = {"AR54-GAZ", "AR-AMD-1993", "AR-AMD-1965", "AFTPR08-C7", "NA57-C7", "NR65-P4-C7", "NR65-P2-C7", "AR54-IC", "DPPR53-C7"}


def norm(s):
    s = s.split(INC)[0].replace(ILL, " ")
    s = s.replace("|", " ").replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = re.sub(r"[^0-9a-z]+", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def sha_file(p):
    with open(p, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def load_c12():
    d = os.path.join(C.C12_FR, "outputs")
    for fn, h in SR.C12_INPUTS.items():
        got = sha_file(os.path.join(d, fn))
        if got != h:
            raise SystemExit(f"C12 input changed: {fn} {got}")
    with open(os.path.join(d, "FORM_DISCOVERY_REGISTER.csv"), encoding="utf-8") as fh:
        reg = list(csv.DictReader(fh))
    with open(os.path.join(d, "FORM_FIELDS.csv"), encoding="utf-8") as fh:
        fields = list(csv.DictReader(fh))
    return reg, fields


def mml_pages_text(lo, hi):
    import pymupdf
    p = os.path.join(C.SCRATCH, SR.MML2["path"])
    with open(p, "rb") as fh:
        b = fh.read()
    if C.sha256(b) != SR.MML2["sha256"]:
        raise SystemExit("MML2 sha mismatch")
    doc = pymupdf.open(stream=b, filetype="pdf")
    t = "\n".join(doc[i - 1].get_text() for i in range(lo, min(hi, doc.page_count) + 1))
    return re.sub(r"-\s*\n\s*", "", t)


def transcription_rows():
    """Flatten spec_transcriptions into (family, source, page, bbox, dpi, region, seq, label, kind)."""
    rows, pages = [], []
    fam_seq = {}
    for e in ST.T:
        segs = [(e["source"], e["page"], e["bbox"], e["fields"])] + [tuple(c) for c in e["continues"]]
        for si, (src, pg, bbox, flds) in enumerate(segs):
            if C.is_restricted(sha256=C.SOURCES[src]["sha256"], path=C.SOURCES[src]["path"]):
                raise SystemExit("restricted source in transcription")
            pages.append(dict(family=e["family"], source=src, page=pg, bbox=bbox, dpi=e["dpi"],
                              region=e["region"], n=len(flds), illegible=e["illegible"] if si == 0 else [],
                              notes=e["notes"] if si == 0 else ""))
            for (label, kind) in flds:
                fam_seq[(e["family"], src)] = fam_seq.get((e["family"], src), 0) + 1
                rows.append(dict(family=e["family"], source=src, page=pg, seq=fam_seq[(e["family"], src)],
                                 label=label, kind=kind, dpi=e["dpi"], bbox=bbox))
    return rows, pages


def legibility(label):
    if ILL in label:
        return "CONTAINS_ILLEGIBLE_SPAN"
    if INC in label:
        return "INCIPIT_ONLY"
    return "LEGIBLE"


def fmt_bbox(b):
    return ",".join(f"{v:.2f}" for v in b)


def csv_text(header, rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=header, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k, "") for k in header})
    return buf.getvalue()


def build():
    reg, c12_fields = load_c12()
    primary = {r["form_family_id"]: r for r in reg if r["occurrence_role"] == "PRIMARY"}
    occ_by_fam = {}
    for r in reg:
        occ_by_fam.setdefault(r["form_family_id"], []).append(r)
    trows, tpages = transcription_rows()
    out = {}

    # ---------------------------------------------------------------- page image log
    pl = []
    for i, p in enumerate(tpages, 1):
        s = C.SOURCES[p["source"]]
        pl.append(dict(reading_id=f"A6-PIR-{i:03d}", form_family_id=p["family"], source_key=p["source"],
                       copy_sha256=s["sha256"], hf_preserved_path=s["hf_path"], pdf_page=p["page"],
                       region=p["region"], region_bbox_fractions=fmt_bbox(p["bbox"]), renderer=ST.RENDERER,
                       dpi=p["dpi"], colorspace="GRAY", fields_transcribed=p["n"],
                       illegible_notes=" | ".join(p["illegible"]), transcriber_notes=p["notes"],
                       reading_method="AI visual reading of rendered page image (not legal validation)",
                       reproduce_with=f"python -I tools/render_pages.py {p['source']} {p['page']} --dpi {p['dpi']}",
                       review_state="PENDING_INDEPENDENT_REVIEW"))
    for r in pl:
        r["reading_kind"] = "FIELD_TRANSCRIPTION"
    for j, (src, pg, dpi, purpose) in enumerate(SR.OTHER_READINGS, len(pl) + 1):
        s_ = C.SOURCES[src]
        pl.append(dict(reading_id=f"A6-PIR-{j:03d}", form_family_id="", source_key=src, copy_sha256=s_["sha256"],
                       hf_preserved_path=s_["hf_path"], pdf_page=pg, region=purpose, region_bbox_fractions="0.00,0.00,1.00,1.00",
                       renderer=ST.RENDERER, dpi=dpi, colorspace="GRAY", fields_transcribed=0, illegible_notes="",
                       transcriber_notes="", reading_method="AI visual reading of rendered page image (not legal validation)",
                       reproduce_with=f"python -I tools/render_pages.py {src} {pg} --dpi {dpi}",
                       review_state="PENDING_INDEPENDENT_REVIEW", reading_kind="RULE_OR_COVERAGE_READING"))
    out["PAGE_IMAGE_LOG.csv"] = csv_text(list(pl[0].keys()), pl)

    # ---------------------------------------------------------------- official transcriptions
    ot = []
    for r in trows:
        s = C.SOURCES[r["source"]]
        ot.append(dict(field_id=f"{r['family']}#O{r['seq']:03d}" + ("" if r["source"] == _first_source(r["family"]) else f"~{r['source']}"),
                       form_family_id=r["family"], source_key=r["source"], copy_sha256=s["sha256"],
                       pdf_page=r["page"], region_bbox_fractions=fmt_bbox(r["bbox"]), renderer=ST.RENDERER, dpi=r["dpi"],
                       seq=r["seq"], field_label_as_printed=r["label"], field_kind=r["kind"],
                       legibility=legibility(r["label"]),
                       mandatory_indication_as_printed="NONE_PRINTED_FOR_FIELD",
                       transcription_basis="PAGE_IMAGE_READING_C13", verification_status=VS,
                       review_state="PENDING_INDEPENDENT_REVIEW"))
    out["OFFICIAL_TRANSCRIPTIONS.csv"] = csv_text(list(ot[0].keys()), ot)

    # ---------------------------------------------------------------- R04 comparison
    fam_official = {}
    for r in trows:
        fam_official.setdefault(r["family"], []).append(r)
    r04_fams = sorted(f for f, p in primary.items() if p["field_set_version"].startswith("MML_VERSION_UNVERIFIED"))
    stat_fams = sorted(f for f, p in primary.items() if p["form_authority_type_candidate"] == "STATUTORY_PRESCRIBED")
    scope = sorted(set(r04_fams) | set(stat_fams))
    comp, famstat = [], []
    conf_map = {}  # C12 field_id -> index (within fam_official[fam]) of the official row that contains it
    tot = dict(confirmed=0, mml_only=0, official_only=0, official_variant=0, illegible=0)
    for fam in scope:
        p = primary[fam]
        mml_fields = [f for f in c12_fields if f["form_family_id"] == fam]
        off = fam_official.get(fam, [])
        if not off:
            famstat.append(dict(form_family_id=fam, in_r04_22=fam in r04_fams, statutory_candidate=fam in stat_fams,
                                official_status="OFFICIAL_COPY_NOT_HELD", official_pages="",
                                mml_fields=len(mml_fields), official_fields=0, mml_fields_confirmed=0,
                                mml_fields_not_in_official=0, official_fields_not_in_mml=0, official_fields_variant=0,
                                official_fields_illegible=0, note="no official copy of the form text is held; NOT filled from MML (see ACQUISITION_REQUESTS_A6.csv)"))
            continue
        otext = " " + " ".join(norm(r["label"]) for r in off) + " "
        partial = fam == "FF-AR54-APPIII-P1D-CHAR"
        # MML side
        mml_text = ""
        if p["source_key"] == "MML2":
            mml_text = " " + norm(mml_pages_text(int(p["locator_start"]), int(p["locator_end"]))) + " "
        elif p["source_key"] in ("AR54-IC",):
            mml_alt = [o for o in occ_by_fam[fam] if o["source_key"] == "MML2"]
            if mml_alt:
                mml_text = " " + norm(mml_pages_text(int(mml_alt[0]["locator_start"]), int(mml_alt[0]["locator_end"]))) + " "
        n_conf = n_mo = 0
        for f in mml_fields:
            lab = norm(f["field_label_as_printed"])
            hit = bool(lab) and (" " + lab + " ") in otext
            if hit:
                conf_map[f["field_id"]] = span_of(lab, off)
                n_conf += 1
                st = "OFFICIAL_CONFIRMED"
            else:
                n_mo += 1
                st = "MML_LABEL_NOT_IN_OFFICIAL_TRANSCRIPTION" + (" (official copy is amending text only)" if partial else "")
            comp.append(dict(form_family_id=fam, side="C12_FIELD_ROW", field_ref=f["field_id"],
                             label=f["field_label_as_printed"], c12_primary_source=p["source_key"],
                             result=st, detail="normalised whole-phrase containment in the official transcription of this family"))
        n_oo = n_var = n_ill = 0
        for r in off:
            if legibility(r["label"]) == "CONTAINS_ILLEGIBLE_SPAN":
                n_ill += 1
            lab = norm(r["label"])
            if not mml_text:
                res, det = "NO_MML_COMPARISON_TEXT", "C12 primary is not MML 2 and no MML 2 occurrence is registered"
            elif not lab:
                res, det = "EMPTY_AFTER_NORMALISATION", ""
            elif (" " + lab + " ") in mml_text:
                res, det = "IN_MML_EXACT", ""
            else:
                ratio, missing = best_window(lab, mml_text)
                if ratio >= 0.85:
                    res, det = "IN_MML_WITH_VARIANT", f"best-window ratio {ratio:.2f}; official tokens not matched in MML window: {' '.join(missing)[:200]}"
                    n_var += 1
                else:
                    res, det = "NOT_FOUND_IN_MML", f"best-window ratio {ratio:.2f}"
                    n_oo += 1
            comp.append(dict(form_family_id=fam, side="OFFICIAL_TRANSCRIPTION_ROW",
                             field_ref=f"{fam}@{r['source']}p{r['page']}#{r['seq']}", label=r["label"],
                             c12_primary_source=p["source_key"], result=res, detail=det))
        tot["confirmed"] += n_conf
        tot["mml_only"] += n_mo
        tot["official_only"] += n_oo
        tot["official_variant"] += n_var
        tot["illegible"] += n_ill
        pages = sorted({(r["source"], r["page"]) for r in off})
        famstat.append(dict(form_family_id=fam, in_r04_22=fam in r04_fams, statutory_candidate=fam in stat_fams,
                            official_status="OFFICIAL_AMENDING_TEXT_ONLY" if partial else "OFFICIAL_TRANSCRIBED_FROM_PAGE_IMAGE",
                            official_pages=";".join(f"{s} p.{pg}" for s, pg in pages),
                            mml_fields=len(mml_fields), official_fields=len(off), mml_fields_confirmed=n_conf,
                            mml_fields_not_in_official=n_mo, official_fields_not_in_mml=n_oo,
                            official_fields_variant=n_var, official_fields_illegible=n_ill,
                            note=_fam_note(fam)))
    for f in famstat:
        f["r04_disposition"] = r04_disposition(f)
    out["R04_COMPARISON.csv"] = csv_text(["form_family_id", "side", "field_ref", "label", "c12_primary_source", "result", "detail"], comp)
    out["R04_FAMILY_STATUS.csv"] = csv_text(list(famstat[0].keys()), famstat)

    # ---------------------------------------------------------------- versioned field file (new; C12 file untouched)
    # Supersession is explicit (review 1b05490f F01): an official row supersedes only
    # the C12 rows it contains. For a family whose official copy is complete, the
    # remaining C12 rows are superseded by the full official transcription (each such
    # row is a recorded R04 difference). For a family whose official copy is partial
    # (amending text only), the remaining C12 rows are CARRIED as MML_ONLY_UNVERIFIED.
    status_of = {f["form_family_id"]: f["official_status"] for f in famstat}
    ff, disp = [], []
    for fam in sorted(set(primary) | set(fam_official)):
        c12rows = [x for x in c12_fields if x["form_family_id"] == fam]
        offs = fam_official.get(fam, [])
        partial = status_of.get(fam) == "OFFICIAL_AMENDING_TEXT_ONLY"
        vid = {}
        for i, r in enumerate(offs):
            vid[i] = f"{fam}#V2-{i + 1:03d}"
            covered = [x["field_id"] for x in c12rows if conf_map.get(x["field_id"]) and conf_map[x["field_id"]][0] <= i <= conf_map[x["field_id"]][1]]
            ff.append(dict(field_id=vid[i], form_family_id=fam, field_label_as_printed=r["label"], field_kind=r["kind"],
                           source_key=r["source"], copy_sha256=C.SOURCES[r["source"]]["sha256"], pdf_page=r["page"],
                           field_set_version=f"OFFICIAL_PAGE_IMAGE_TRANSCRIPTION_C13 ({r['source']})" + (" [amending text only]" if partial else ""),
                           legibility=legibility(r["label"]), mandatory_indication_as_printed="NONE_PRINTED_FOR_FIELD",
                           supersedes_c12_field_ids=";".join(covered) if fam in primary else "(new family in C13)",
                           verification_status=VS,
                           reviewer_confirmation="SET_ACCEPTED_WITH_FINDINGS_BY_INDEPENDENT_REVIEW_1b05490f (census+seeded sample, 693/955 rows checked, 99.42% text-only row accuracy, 95% CI 98.53-99.78; this row not necessarily individually checked)"))
        for x in c12rows:
            if x["field_id"] in conf_map and offs:
                disp.append(dict(c12_field_id=x["field_id"], form_family_id=fam, disposition="SUPERSEDED_BY_OFFICIAL_ROW",
                                 official_field_ids=";".join(vid[k] for k in range(conf_map[x["field_id"]][0], conf_map[x["field_id"]][1] + 1)), basis="C12 label contained in the official row (normalised)"))
            elif offs and not partial:
                disp.append(dict(c12_field_id=x["field_id"], form_family_id=fam, disposition="SUPERSEDED_BY_FULL_OFFICIAL_TRANSCRIPTION",
                                 official_field_ids=f"{vid[0]}..{vid[len(offs) - 1]}",
                                 basis="official copy of the whole form transcribed; label not found in it (recorded R04 difference in R04_COMPARISON.csv)"))
            else:
                why = ("official copy covers para 9 only (S.R.O. 17(E)/1993 item 39(a)); rest of form held only in MML"
                       if partial else "no official copy held")
                label = ("CARRIED_FROM_C12: MML_ONLY_UNVERIFIED (" + why + ")") if (partial or primary[fam]["source_basis"] == "MML_ONLY") \
                    else "CARRIED_FROM_C12: " + x["field_set_version"]
                ff.append(dict(field_id=x["field_id"], form_family_id=fam, field_label_as_printed=x["field_label_as_printed"],
                               field_kind=x["field_kind"], source_key=primary[fam]["source_key"],
                               copy_sha256=primary[fam]["source_copy_sha256"], pdf_page="", field_set_version=label,
                               legibility="NOT_ASSESSED_C13", mandatory_indication_as_printed="NONE_PRINTED_FOR_FIELD",
                               supersedes_c12_field_ids="", verification_status=VS,
                               reviewer_confirmation="NOT_APPLICABLE (" + why + ")"))
                disp.append(dict(c12_field_id=x["field_id"], form_family_id=fam, disposition="CARRIED_IN_V2",
                                 official_field_ids="", basis=label))
    out["FORM_FIELDS_C13_v2.csv"] = csv_text(list(ff[0].keys()), ff)
    out["C12_FIELD_DISPOSITION.csv"] = csv_text(["c12_field_id", "form_family_id", "disposition", "official_field_ids", "basis"], disp)

    # ---------------------------------------------------------------- expanded register
    regrows = build_register(primary, occ_by_fam, fam_official, famstat)
    out["FORM_REGISTER_C13.csv"] = csv_text(list(regrows[0].keys()), regrows)

    # ---------------------------------------------------------------- acquisition requests
    acq = [dict(request_id=a[0], service=a[1], instrument_needed=a[2], why=a[3], affected_families=a[4],
                status=a[5], candidate_lawful_channel=a[6], action_taken="NONE (no download made in A6)")
           for a in SR.ACQUISITION_REQUESTS]
    out["ACQUISITION_REQUESTS_A6.csv"] = csv_text(list(acq[0].keys()), acq)

    # ---------------------------------------------------------------- oracle
    oracle_lines, oracle_stats = SO.build_oracle(trows)
    out["ORACLE_CASES.jsonl"] = "".join(json.dumps(x, ensure_ascii=False, sort_keys=True) + "\n" for x in oracle_lines)

    # ---------------------------------------------------------------- summary
    r04 = [f for f in famstat if f["in_r04_22"]]
    st = [f for f in famstat if f["statutory_candidate"]]
    summ = dict(
        tool=TOOL, python=sys.version.split()[0],
        status="RESEARCH_ONLY; every row DISCOVERED_FROM_SOURCE_NOT_LEGALLY_APPROVED; legal_approval_state NOT_APPROVED",
        c12_inputs=SR.C12_INPUTS,
        official_copies={k: v["sha256"] for k, v in C.SOURCES.items()},
        restricted_material_excluded=["RM-001 (config/restricted_material.json on claude/c13-gov; guard in tools/a6_common.py)"],
        transcription_conventions=ST.CONVENTIONS,
        degraded_glyph_normalisations=[dict(source=a, page=b, family=c, note=d) for a, b, c, d in ST.DEGRADED_GLYPH_NORMALISATIONS],
        independent_review=dict(ref="reviews/review_c13_a6_1b05490f.md", verdict="ACCEPT_WITH_FINDINGS",
                                row_accuracy_text_only="99.42% (95% CI 98.53-99.78) over 693/955 rows",
                                findings_addressed="F01 (P2), F02, F03, F04, F05 (documented), F06, F08, F09 (noted)"),
        c12_field_dispositions={k: sum(1 for d in disp if d["disposition"] == k) for k in sorted({d["disposition"] for d in disp})},
        page_image_readings=len(pl), page_image_readings_for_transcription=len(tpages),
        distinct_pages_read=len({(p["source_key"], p["pdf_page"]) for p in pl}),
        distinct_pages_transcribed=len({(p["source"], p["page"]) for p in tpages}),
        official_transcription_rows=len(ot),
        official_rows_with_illegible_span=sum(1 for r in ot if r["legibility"] == "CONTAINS_ILLEGIBLE_SPAN"),
        official_rows_incipit_only=sum(1 for r in ot if r["legibility"] == "INCIPIT_ONLY"),
        illegible_notes=sum(len(e["illegible"]) for e in ST.T),
        r04=dict(
            families=len(r04),
            official_transcribed_full=sum(1 for f in r04 if f["official_status"] == "OFFICIAL_TRANSCRIBED_FROM_PAGE_IMAGE"),
            official_amending_text_only=sum(1 for f in r04 if f["official_status"] == "OFFICIAL_AMENDING_TEXT_ONLY"),
            official_not_held=sum(1 for f in r04 if f["official_status"] == "OFFICIAL_COPY_NOT_HELD"),
            c12_mml_field_rows=sum(f["mml_fields"] for f in r04),
            mml_field_rows_confirmed_in_official=sum(f["mml_fields_confirmed"] for f in r04),
            mml_field_rows_not_in_official=sum(f["mml_fields_not_in_official"] for f in r04),
            official_rows=sum(f["official_fields"] for f in r04),
            official_rows_not_in_mml=sum(f["official_fields_not_in_mml"] for f in r04),
            official_rows_variant_vs_mml=sum(f["official_fields_variant"] for f in r04),
            official_rows_with_illegible_span=sum(f["official_fields_illegible"] for f in r04)),
        statutory=dict(
            families=len(st),
            official_transcribed=sum(1 for f in st if f["official_status"] != "OFFICIAL_COPY_NOT_HELD"),
            official_not_held=sum(1 for f in st if f["official_status"] == "OFFICIAL_COPY_NOT_HELD"),
            mml_or_c12_field_rows_confirmed=sum(f["mml_fields_confirmed"] for f in st),
            c12_field_rows_not_in_official=sum(f["mml_fields_not_in_official"] for f in st),
            official_rows=sum(f["official_fields"] for f in st),
            official_rows_not_in_mml=sum(f["official_fields_not_in_mml"] for f in st),
            official_rows_variant_vs_mml=sum(f["official_fields_variant"] for f in st),
            official_rows_with_illegible_span=sum(f["official_fields_illegible"] for f in st)),
        register=dict(
            families_total=len(regrows),
            by_service={s: sum(1 for r in regrows if r["service"] == s) for s in sorted({r["service"] for r in regrows})},
            new_in_c13=sum(1 for r in regrows if r["new_in_c13"] == "YES"),
            statutory_prescribed_candidates=sum(1 for r in regrows if r["form_authority_type_candidate"] == "STATUTORY_PRESCRIBED"),
            fidelity=_count(regrows, "source_fidelity_c13"),
            legal_approval=_count(regrows, "legal_approval_state")),
        acquisition_requests=len(acq),
        oracle=oracle_stats,
        version_evidence=ST.VERSION_EVIDENCE,
        method_limits=[
            "Transcriptions are AI visual readings of page images; an independent reviewer must confirm them before any status promotion.",
            "Long printed condition paragraphs of Appendix I forms are recorded as incipits (INCIPIT_ONLY) with every blank itemised; full wording remains on the page image.",
            "R04 comparison uses normalised whole-phrase containment and a best-window token ratio; it locates differences, it does not judge their legal effect.",
            "bbox values are approximate fractions read by eye.",
            "Navy Regulations Part II Appendix I forms are registered from the list page only; their fields were not transcribed this cycle.",
        ],
    )
    out["SUMMARY.json"] = json.dumps(summ, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    return out


def span_of(lab, off):
    """Smallest consecutive run (i, j) of official rows whose joined text contains lab."""
    best = None
    for i in range(len(off)):
        acc = ""
        for j in range(i, len(off)):
            acc = (acc + " " + norm(off[j]["label"])).strip()
            if (" " + lab + " ") in (" " + acc + " "):
                if best is None or (j - i) < (best[1] - best[0]):
                    best = (i, j)
                break
    return best


def r04_disposition(f):
    st = f["official_status"]
    if f["in_r04_22"] and st == "OFFICIAL_TRANSCRIBED_FROM_PAGE_IMAGE":
        return "R04_CLOSURE_RECOMMENDED_CLOSED_VERIFIED (independent review 1b05490f; transcription fidelity only; capability restriction unchanged)"
    if f["in_r04_22"] and st == "OFFICIAL_AMENDING_TEXT_ONLY":
        return ("R04_STILL_DEFERRED: only para 9 is held in an official copy (S.R.O. 17(E)/1993 item 39(a), AR-AMD-1993 p.19); "
                "Appendix III Part I base text of IAFD-905 not held (1954 Gazette p.72 passes from Appendix I to Appendix III Part II); "
                "other field rows remain MML_ONLY_UNVERIFIED (A6-ACQ-02)")
    if not f["in_r04_22"] and st == "OFFICIAL_COPY_NOT_HELD":
        return "OUTSIDE_R04: no official copy held; field list MML_ONLY_UNVERIFIED (see ACQUISITION_REQUESTS_A6.csv)"
    return "OUTSIDE_R04: statutory candidate transcribed from official page image (not one of the 22)"


def _count(rows, k):
    d = {}
    for r in rows:
        d[r[k]] = d.get(r[k], 0) + 1
    return dict(sorted(d.items()))


_FIRST = {}


def _first_source(fam):
    if not _FIRST:
        for e in ST.T:
            _FIRST.setdefault(e["family"], e["source"])
    return _FIRST[fam]


def _fam_note(fam):
    notes = [e["notes"] for e in ST.T if e["family"] == fam and e["notes"]]
    return " || ".join(notes)[:600]


def best_window(lab, text):
    toks = lab.split()
    ttoks = text.split()
    n = len(toks)
    if n == 0 or not ttoks:
        return 0.0, toks
    first = set(toks[:3])
    best, bestw = 0.0, []
    cand = [i for i, t in enumerate(ttoks) if t in first] or range(0, len(ttoks), max(1, n // 2))
    for i in cand:
        for j in (max(0, i - 2), i):
            w = ttoks[j:j + n + 2]
            r = difflib.SequenceMatcher(None, toks, w, autojunk=False).ratio()
            if r > best:
                best, bestw = r, w
    sm = difflib.SequenceMatcher(None, toks, bestw, autojunk=False)
    missing = [t for tag, a, b, _, _ in sm.get_opcodes() if tag in ("replace", "delete") for t in toks[a:b]]
    return best, missing


def service_of(fam):
    if fam.startswith(("FF-NA57", "FF-NR65")):
        return "NAVY"
    if fam.startswith(("FF-AFTPR08", "FF-DPPR53", "FF-ITR42")):
        return "TRI_SERVICE_OR_ARMY_AIR_FORCE"
    return "ARMY"


def build_register(primary, occ_by_fam, fam_official, famstat):
    fs = {f["form_family_id"]: f for f in famstat}
    rows = []
    sigs = {}
    for fam, offs in fam_official.items():
        sigs[fam] = "; ".join(dict.fromkeys(r["label"] for r in offs if r["kind"] == "signature"))
    for fam in sorted(primary):
        p = primary[fam]
        off = fam_official.get(fam)
        r04d = fs.get(fam, {}).get("r04_disposition", "")
        stt = fs.get(fam, {}).get("official_status") or ("OFFICIAL_TRANSCRIBED_FROM_PAGE_IMAGE" if off else "NOT_IN_R04_OR_STATUTORY_SCOPE")
        pages = sorted({(r["source"], r["page"]) for r in off}) if off else []
        if off and stt == "OFFICIAL_TRANSCRIBED_FROM_PAGE_IMAGE":
            fid = "TRANSCRIBED_FROM_OFFICIAL_PAGE_IMAGE_PENDING_INDEPENDENT_REVIEW"
        elif off:
            fid = "OFFICIAL_AMENDING_TEXT_TRANSCRIBED; REST_MML_ONLY_UNVERIFIED"
        elif p["source_basis"] == "MML_ONLY":
            fid = "MML_ONLY_UNVERIFIED (official copy not held)"
        else:
            fid = "C12_" + p["fidelity_state"]
        vh = p["version_amendment_history"]
        for ve in ST.VERSION_EVIDENCE:
            if fam in ve["families"]:
                vh += f" || C13 page-image evidence ({ve['source']} pp.{ve['pages']}): {ve['effect_on_fields']}"
        rr = [x["id"] for x in SR.RULE_READINGS if fam in x["families"] or
              (x["families"] == ["*ARMY_RULES_APPENDIX*"] and fam.startswith("FF-AR54-APP"))]
        rows.append(dict(
            form_id=fam, new_in_c13="NO", service=service_of(fam), instrument=p["instrument"],
            appendix_part_or_schedule=p["appendix_part_or_schedule"], printed_form_number=p["printed_form_number"],
            printed_title=p["printed_title"],
            prescribing_authority=C.SOURCES[pages[0][0]]["authority"] if pages else p["source_evidence_class"][:120],
            primary_source_c13=";".join(sorted({s for s, _ in pages})) if pages else p["source_key"],
            source_copy_sha256=";".join(sorted({C.SOURCES[s]["sha256"] for s, _ in pages})) if pages else p["source_copy_sha256"],
            source_edition=" ; ".join(sorted({C.SOURCES[s]["edition"] for s, _ in pages})) if pages else p["edition_or_version_evidence"],
            exact_pages=";".join(f"{s} p.{pg}" for s, pg in pages) if pages else f"{p['source_key']} {p['locator_type']} {p['locator_start']}-{p['locator_end']} (C12)",
            provision=p["prescribing_provision"], requirement_language_as_printed=p["requirement_language_as_printed"],
            form_authority_type_candidate=p["form_authority_type_candidate"], mandatory_or_specimen_status=p["status_category"],
            statutory_confirmation_status=("CONFIRMED_FROM_OFFICIAL_COPY_PAGE_IMAGE (form text); rule quote per C12" if (off and stt == "OFFICIAL_TRANSCRIBED_FROM_PAGE_IMAGE" and p["form_authority_type_candidate"] == "STATUTORY_PRESCRIBED") else p["statutory_confirmation_status"]),
            applicability_conditions_as_printed=p["applicability_conditions_as_printed"], applicability_state="NOT_ESTABLISHED",
            required_fields=(f"{len(off)} official rows (para 9 only) + C12 rows carried as MML_ONLY_UNVERIFIED in FORM_FIELDS_C13_v2.csv; official coverage of the form is partial; no field-level mandatoriness printed" if (off and stt == "OFFICIAL_AMENDING_TEXT_ONLY") else
                             f"{len(off)} printed elements in FORM_FIELDS_C13_v2.csv (official); no field-level mandatoriness printed" if off else "see FORM_FIELDS_C13_v2.csv (carried from C12); no field-level mandatoriness printed"),
            field_set_version_c13=(f"OFFICIAL_PAGE_IMAGE_TRANSCRIPTION_C13" + (" (amending text only)" if stt == "OFFICIAL_AMENDING_TEXT_ONLY" else "")) if off else "CARRIED_FROM_C12: " + p["field_set_version"],
            competent_authority_as_printed=p["competent_authority_as_printed"],
            signatory_requirements_as_printed=sigs.get(fam) or p["signatory_as_printed"],
            supporting_documents_as_printed=p["companion_documents_as_printed"],
            procedural_dependencies=p["procedural_dependencies"] + (" || rule readings: " + ",".join(rr) if rr else ""),
            version_history=vh, supersession=p["supersession_status"],
            source_fidelity_c13=fid, r04_status=stt + (" | " + r04d if r04d else ""),
            cross_cutting_caveat_as_printed=p["cross_cutting_caveat_as_printed"],
            mml_alternates=";".join(sorted({o["source_key"] for o in occ_by_fam[fam] if o["source_key"].startswith("MML")})),
            legal_approval_state="NOT_APPROVED", publication_state="NOT_STAGED", freshness_state="NOT_ASSESSED",
            outstanding_uncertainties=p["outstanding_uncertainties"][:500], verification_status=VS))
    # new families
    for fam, (prov, quote, appl, comp) in SR.NEW_STATUTORY.items():
        off = fam_official[fam]
        rows.append(_new_row(fam, "NAVY", "Navy Act 1957", "", "(statutory form in section text)", off[0]["label"][:80],
                             off, prov, quote, "STATUTORY_PRESCRIBED", "MANDATORY_WITH_ALTERNATIVE_PERMITTED (oath / affirmation)",
                             appl, comp, sigs.get(fam, "")))
    off = fam_official["FF-NR65P4-S2-OATH"]
    rows.append(_new_row("FF-NR65P4-S2-OATH", "NAVY", "Regulations for the Navy Part IV (INAS Regulations 1973)", "Schedule II",
                         "SCHEDULE II", "FORM OF OATH/AFFIRMATION", off, "Regulation 15 (as printed on the Schedule)",
                         "requirement language of Regulation 15 not extracted (text layer fragmentary; page image of reg.15 not read)",
                         "OTHER_OR_UNDETERMINED", "REQUIREMENT_LANGUAGE_NOT_EXTRACTED", "INAS personnel on attestation (not established)",
                         "Commanding Officer (as printed below signature)", sigs.get("FF-NR65P4-S2-OATH", "")))
    rows.append(_new_row("FF-NR65P4-S1-INXS1", "NAVY", "Regulations for the Navy Part IV (INAS Regulations 1973)", "Schedule I",
                         "Form INXS I", "INDIAN NAVAL AUXILIARY SERVICE ENROLMENT FORM (Application for enrolment) (See Regulation 4)", None,
                         "Regulation 4 (as printed on the form); reg.53 refers to 'the enrolment form' (text layer)",
                         "reg.53(1) [text layer p.25]: 'Application for enrolment shall be made in the enrolment form to the nearest recruiting organization, or Commanding Officer of any establishment or Officer-in-Charge of Coast Batteries.'",
                         "OTHER_OR_UNDETERMINED", "REQUIREMENT_LANGUAGE_NOT_EXTRACTED", "not established", "not extracted", "",
                         pages="NR65-P4-C7 pp.78-80 (text layer; page image not read)", fid="DISCOVERED_TEXT_LAYER_ONLY_FIELDS_NOT_TRANSCRIBED"))
    for (n, title, prov, pg) in SR.NAVY_P2_FORMS:
        rows.append(_new_row(f"FF-NR65P2-F{n:02d}", "NAVY", "Regulations for the Navy Part II (Statutory)", "Appendix I",
                             f"FORM No. {n}", title, None, prov + " (as listed in Appendix I)",
                             "Appendix I list: p.105 page image read (Forms 1-25); p.106 text layer only (Forms 25-34); reg. definition (f): '\"Prescribed form,\" means an appropriate form in Appendix I applicable to the relevant section or regulation.' (text layer). Per-form requirement wording not quoted.",
                             "OTHER_OR_UNDETERMINED", "REQUIREMENT_LANGUAGE_NOT_EXTRACTED", "not established", "not extracted", "",
                             pages=f"NR65-P2-C7 p.{pg} (form heading, text layer); list p.105 (image, Forms 1-25) / p.106 (text layer, Forms 25-34)",
                             fid="DISCOVERED_FROM_LIST_PAGE_IMAGE; FIELDS_NOT_TRANSCRIBED_THIS_CYCLE"))
    return rows


def _new_row(fam, service, instrument, part, number, title, off, prov, quote, ftype, status, appl, comp, sig, pages=None, fid=None):
    src = "NA57-C7" if fam.startswith("FF-NA57") else ("NR65-P4-C7" if "NR65P4" in fam else "NR65-P2-C7")
    s = C.SOURCES[src]
    if off:
        pages = ";".join(f"{x} p.{pg}" for x, pg in sorted({(r['source'], r['page']) for r in off}))
        fid = "TRANSCRIBED_FROM_OFFICIAL_PAGE_IMAGE_PENDING_INDEPENDENT_REVIEW"
    return dict(
        form_id=fam, new_in_c13="YES", service=service, instrument=instrument, appendix_part_or_schedule=part,
        printed_form_number=number, printed_title=title, prescribing_authority=s["authority"], primary_source_c13=src,
        source_copy_sha256=s["sha256"], source_edition=s["edition"], exact_pages=pages, provision=prov,
        requirement_language_as_printed=quote, form_authority_type_candidate=ftype, mandatory_or_specimen_status=status,
        statutory_confirmation_status=("CONFIRMED_FROM_OFFICIAL_COPY_PAGE_IMAGE (government compilation)" if ftype == "STATUTORY_PRESCRIBED" else "NOT_APPLICABLE"),
        applicability_conditions_as_printed=appl, applicability_state="NOT_ESTABLISHED",
        required_fields=(f"{len(off)} printed elements in FORM_FIELDS_C13_v2.csv; no field-level mandatoriness printed" if off else "NOT_TRANSCRIBED_THIS_CYCLE"),
        field_set_version_c13=("OFFICIAL_PAGE_IMAGE_TRANSCRIPTION_C13" if off else "NONE"),
        competent_authority_as_printed=comp, signatory_requirements_as_printed=sig or "not extracted",
        supporting_documents_as_printed="not extracted", procedural_dependencies="not examined",
        version_history=s["edition"] + "; later amendments not searched", supersession="NOT_DETERMINED",
        source_fidelity_c13=fid, r04_status="NOT_IN_R04_SCOPE (new family)", cross_cutting_caveat_as_printed="",
        mml_alternates="", legal_approval_state="NOT_APPROVED", publication_state="NOT_STAGED", freshness_state="NOT_ASSESSED",
        outstanding_uncertainties="India Code copy; authentication against the Gazette not done; amendment state not determined",
        verification_status=VS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    out = build()
    if a.check:
        bad = []
        for fn, txt in out.items():
            p = os.path.join(OUT, fn)
            if not os.path.isfile(p) or open(p, encoding="utf-8").read() != txt:
                bad.append(fn)
        if bad:
            print("CHECK FAILED:", ", ".join(bad))
            sys.exit(1)
        print(f"CHECK OK: {len(out)} files reproduce byte-for-byte")
        return
    os.makedirs(OUT, exist_ok=True)
    for fn, txt in out.items():
        with open(os.path.join(OUT, fn), "w", encoding="utf-8", newline="") as fh:
            fh.write(txt)
    print("wrote", len(out), "files to", OUT)


if __name__ == "__main__":
    main()
