"""Gazette tranche 1 (AUTH-LEDGER-02 preparation): the 20 primary Gazette candidates of the C6-01 draft addendum.

Writes PREPARATION material only. Nothing here is a ledger version, a decision record or a review record, and nothing is
approved or activated. The committed ledger (ledger/manifest.jsonl, HEAD) is never touched.

For each candidate the builder:
  - converts the C6-01 draft row into a ledger-format entry (text-identity reference rewritten to the overlay's pinned
    evidence/copy_facts.csv, as DESIGN_NOTES requires) and leaves owner_decision EMPTY, so the row cannot pass the schema
    if copied into a ledger file unchanged;
  - runs the ACTUAL rule-1 checks end to end on that single entry in a temporary directory with synthetic records
    (schema, association, evidence references, first-class record, strict locator, class compatibility, completeness,
    copy fidelity, identity, contradiction, copy-status rule, frozen Cycle 5 consistency) and records PASS or the reason;
  - collects the documentary facts for the 14 verification items from pinned registers;
then runs all 20 jointly in a temporary directory to simulate the coverage impact.

  python build_tranche1.py           write the outputs next to this tool's parent directory
  python build_tranche1.py --check   rebuild in memory and fail if any committed output differs"""
import argparse, csv, io, json, re, shutil, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "T1-GAZETTE"
PKG = HERE.parents[1]
sys.path.insert(0, str(PKG / "tools"))
from common import AW, LedgerError, read_csv, sha256_file, sha256_text, csv_text  # noqa: E402
import ledger as L  # noqa: E402
import reader  # noqa: E402
import strength  # noqa: E402

CLS = "PRIMARY_GAZETTE_ARCHIVAL_FACSIMILE"
SIM_DATE = "2026-11-23"
DRAFT = AW / "C6-01-PROVENANCE/addendum/authentication_addendum_v1_draft.csv"
INSTR = "ARMY-RULES-CHAIN-01/army_rules_instrument_register.csv"  # a register row, not a page-image observation


def load():
    drafts = [r for r in read_csv(DRAFT) if r["proposed_class"] == CLS]
    rec = {r["sha256"]: r for r in read_csv(AW / "C6-01-PROVENANCE/registers/provenance_recovery_register.csv")}
    st = {r["sha256"]: r for r in read_csv(PKG / "evidence/copy_structure.csv")}
    fa = {r["sha256"]: r for r in read_csv(PKG / "evidence/copy_facts.csv")}
    cp = {r["sha256"]: r for r in read_csv(AW / "SOURCE-LIBRARY-C5/registers/source_copy_register.csv")}
    ms = {r["source_id"]: r for r in read_csv(AW / "SOURCE-LIBRARY-C5/registers/source_master_register.csv")}
    return drafts, rec, st, fa, cp, ms


SRO34_C6 = "(1963-01-05 (notes misdate as 05-06-1963))"
SRO34_NEUTRAL = ("(1963-01-05; the government notes list an 'S.R.O. 34 dated 5-6-1963', and whether that is this instrument is "
                 "UNVERIFIED)")


def neutral_identity(identity):
    """The C6-01 draft wording 'notes misdate' asserts what is unverified (Fable F-12); the prepared rows use neutral wording."""
    return identity.replace(SRO34_C6, SRO34_NEUTRAL)


def to_entry(d, n, cp, version=1):
    e = {k: "" for k in L.COLS}
    e.update({"entry_id": f"AL-v{version:04d}-{n:03d}", "entry_version": f"{version:04d}", "entry_type": "ADD", "sha256": d["sha256"],
              "source_id": d["source_id"], "copy_id": d["copy_id"], "document_identity": neutral_identity(d["document_identity"]),
              "evidence_refs": d["evidence_refs"], "first_class_record_ref": d["first_class_record_ref"],
              "identity_refs": d["identity_refs"].replace("T:C6-01-PROVENANCE/inputs/held_copy_facts.csv#", "T:AUTH-LEDGER/evidence/copy_facts.csv#"),
              "proposed_authentication_state": "PROVENANCE_DOCUMENTED", "proposed_class": d["proposed_class"],
              "carrier": cp[d["sha256"]]["copy_carrier_provenance"],
              "official_locator_recorded": strength._first_class(d["first_class_record_ref"], d["sha256"])[2],
              "limitations": d["limitations"], "justification": d["justification"], "rule_version": "1", "owner_decision": ""})
    return e


class Sim:
    """Temporary ledger root with synthetic SIMULATION records; deleted afterwards. Never written to the repository."""
    def __init__(self):
        self.dir = Path(tempfile.mkdtemp(prefix="tranche1_sim_"))
        shutil.copy(PKG / "frozen_inputs.json", self.dir / "frozen_inputs.json")
        (self.dir / "ledger").mkdir()
        (self.dir / "decisions").mkdir()
        shutil.copy(PKG / "ledger/manifest.jsonl", self.dir / "ledger/manifest.jsonl")
        shutil.copy(PKG / "ledger/HEAD", self.dir / "ledger/HEAD")

    def run(self, entries):
        es = [dict(e, owner_decision="APPROVED") for e in entries]
        pairs = ";".join(f"{e['entry_id']}={e['sha256']}:{L.entry_digest(e)}" for e in es)
        recs = {}
        for name, body in (("D-v0001.md", f"decision_id: D-v0001\ndecision: APPROVED\nledger_version: 0001\nentries: {pairs}\ndecided_by: simulation owner\n"
                                          f"date: {SIM_DATE}\nscope: AUTHENTICATION_PROVENANCE_ONLY\nlegal_approval: NOT_GIVEN\n"),
                           ("R-v0001.md", f"review_id: R-v0001\nverdict: ACCEPT\nledger_version: 0001\nentries: {pairs}\nreviewer: simulation reviewer\n"
                                          f"date: {SIM_DATE}\nscope: TECHNICAL_AND_EVIDENCE_REVIEW\nlegal_approval: NOT_GIVEN\n")):
            (self.dir / "decisions" / name).write_text(body, encoding="utf-8")
            recs[name] = sha256_file(self.dir / "decisions" / name)
        for e in es:
            e["decision_record_ref"], e["decision_record_sha256"] = "decisions/D-v0001.md", recs["D-v0001.md"]
            e["reviewer_ref"], e["reviewer_record_sha256"] = "decisions/R-v0001.md", recs["R-v0001.md"]
        (self.dir / "ledger/v0001.csv").write_text(csv_text(L.COLS, es), encoding="utf-8")
        prev = sha256_text((self.dir / "ledger/manifest.jsonl").read_text(encoding="utf-8").split("\n")[-2])
        line = {"version": 1, "prev": prev, "date": SIM_DATE, "rule_version": 1, "frozen_inputs_sha256": sha256_file(self.dir / "frozen_inputs.json"),
                "file": "ledger/v0001.csv", "file_sha256": sha256_file(self.dir / "ledger/v0001.csv"),
                "decisions": {"decisions/D-v0001.md": recs["D-v0001.md"]}, "reviews": {"decisions/R-v0001.md": recs["R-v0001.md"]},
                "effective_sha256": "", "note": "SIMULATION"}
        s = L.canonical_line(line)
        with open(self.dir / "ledger/manifest.jsonl", "a", encoding="utf-8") as fh:
            fh.write(s + "\n")
        (self.dir / "ledger/HEAD").write_text(f"1 {sha256_text(s)}\n", encoding="utf-8")
        texts, _ = reader.effective_state(self.dir, 1, require_binding=False)  # simulation of the post-binding effect
        return texts

    def close(self):
        shutil.rmtree(self.dir, ignore_errors=True)


def rule1(entry):
    sim = Sim()
    try:
        sim.run([entry])
        return "PASS", ""
    except (LedgerError, KeyError, ValueError) as ex:
        return "FAIL", str(ex)[:300]
    finally:
        sim.close()


def identity_summary(refs):
    out = []
    for ref in [x for x in refs.split("; ") if x]:
        kind, _, r = ref.partition(":")
        if kind == "T":
            out.append(f"{ref} (page-1 text excerpt; not identity evidence for a Gazette under rule 1)")
            continue
        path, rec = strength.resolve(r)
        if path == INSTR:
            out.append(f"{rec.get('instr_id')}: evidence_level {rec.get('evidence_level')}; {rec.get('instrument', '')}; {rec.get('gazette_publication', '')}")
        elif path.startswith("WS-A-STATUTORY/"):
            out.append(f"{rec.get('check_id')}: pdf p.{rec.get('pdf_page')} printed p.{rec.get('printed_page')}; render {rec.get('render_png_sha256', '')}; "
                       f"transcription: {rec.get('independent_transcription', '')}")
        else:
            seen = rec.get("observed_on_image") or rec.get("reading") or rec.get("what_was_read") or ""
            out.append(f"{rec.get('check_id')}: {rec.get('page', '')}; render {rec.get('render_png_sha256', '')}; observed: {seen}"
                       + (f"; identity_result {rec['identity_result']}" if rec.get("identity_result") else ""))
    return " | ".join(out)


def l5_observations(evidence_refs, sha):
    """R23 amendment-search records cited as L5 evidence that quote the page image (status LOCATED_IMAGE_CHECKED, a
    64-hex render hash, and this sha256). Their identity_evidence field quotes the masthead and the S.R.O. line
    (Fable review F-02: the first build scanned identity_refs only and missed these)."""
    out = []
    for ref in [x for x in evidence_refs.split("; ") if x.startswith("L5:")]:
        _p, rec = strength.resolve(ref[3:])
        if (rec.get("status") == "LOCATED_IMAGE_CHECKED" and (rec.get("sha256") or "").strip() == sha
                and re.fullmatch(r"[0-9a-f]{64}", (rec.get("render_sha256") or "").strip())):
            out.append((ref, rec))
    return out


def identity_text(refs):
    """Text that a person read from the page image (image-check observations and independent transcriptions) only.
    Register rows (ARMY-RULES-CHAIN-01) restate the expected identity and are excluded, so the check is not circular."""
    parts = []
    for ref in [x for x in refs.split("; ") if x and not x.startswith("T:")]:
        path, rec = strength.resolve(ref.partition(":")[2])
        if path == INSTR:
            continue
        parts.append(" ".join(str(rec.get(k, "")) for k in ("observed_on_image", "reading", "what_was_read", "independent_transcription")))
    return " ".join(parts)


def sro_numbers(identity):
    return list(dict.fromkeys(re.findall(r"S\.R\.O\.\s*(\d+(?:\s*\(E\))?)", identity)))


def fidelity_class(stc, text_class, pages):
    """POLICY_OPTIONS D classes, from structural facts only (never a statement about legal validity or a valid signature)."""
    if stc["producer"].startswith("Internet Archive"):
        return "ARCHIVE_DERIVATIVE"
    if stc["signature_byte_ranges"].strip():
        return "BORN_DIGITAL_SIGNED_RANGE_SPANS_FILE" if stc["signed_range_covers_file"] == "YES" else "BORN_DIGITAL_REWRITTEN"
    if text_class.startswith("SCANNED") or (stc["embedded_images"].isdigit() and pages.isdigit() and int(stc["embedded_images"]) >= int(pages)):
        return "SCANNED_FACSIMILE"
    return "UNCLASSIFIED"


def build():
    drafts, rec, st, fa, cp, ms = load()
    if len(drafts) != 20:
        raise SystemExit(f"expected 20 primary Gazette candidates, found {len(drafts)}")
    drafts.sort(key=lambda d: d["source_id"])
    entries = [to_entry(d, i + 1, cp) for i, d in enumerate(drafts)]
    reg, matrix, contra, pending = [], [], [], []
    for i, (d, e) in enumerate(zip(drafts, entries), 1):
        s = d["sha256"]
        R, T, F, C, M = rec[s], st[s], fa[s], cp[s], ms[d["source_id"]]
        tid = f"T1-{i:02d}"
        kind, strg, url = strength._first_class(d["first_class_record_ref"], s)
        verdict, why = rule1(e)
        fc = fidelity_class(T, C["text_layer_class"], F["pages"])
        l5 = l5_observations(e["evidence_refs"], s)
        idtxt = identity_text(e["identity_refs"]) + " " + " ".join(r.get("identity_evidence", "") for _x, r in l5)
        sros = sro_numbers(d["document_identity"])
        pat = lambda n: r"S\.?\s*R\.?\s*O\.?\s*" + re.escape(n.split("(")[0].strip()) + r"\b"
        sro_img = [n for n in sros if re.search(pat(n), idtxt)]
        sro_p1 = [n for n in sros if re.search(pat(n), F["p1_text_excerpt"])]
        exact = strength.contradiction(url, s)
        id_read = bool(sros) and set(sro_img) == set(sros)
        sub = "1B-FIDELITY" if fc.startswith("BORN_DIGITAL") else ("1A-READY" if id_read else "1A-CONFIRM-ID")
        special = ""
        if "S.R.O. 34 (1963" in d["document_identity"]:
            special = ("S.R.O. 34/1963: the held file is the 05-01-1963 r.188(e) declaration (image-checked). The government notes' "
                       "'S.R.O. 34 dated 5-6-1963' is NOT shown to be this instrument; identity of the listed instrument stays UNVERIFIED; "
                       "no amendment-chain inference may rest on this copy")
        elif sub == "1B-FIDELITY":
            special = ("born-digital Gazette (GPL Ghostscript 8.15) with an embedded signature byte range that spans the file: STRUCTURAL ONLY; "
                       "the signature has NOT been cryptographically validated and no signer certificate has been checked")
        if not id_read:
            special = ((special + "; ") if special else "") + (
                "the recorded image-check observation confirms the page content but does not transcribe the S.R.O. number and date line; "
                "the number comes from the ARMY-RULES-CHAIN-01 register row (IMAGE_CHECKED)")
        if verdict != "PASS":
            rcm = "HOLD (fails rule 1)"
        elif sub == "1B-FIDELITY":
            rcm = ("ELIGIBLE UNDER RULE 1; RECOMMEND HOLDING until the owner confirms fidelity class 2 (POLICY_OPTIONS D)"
                   + ("" if id_read else " and a CONFIRMED image check transcribing the S.R.O. number and date line exists"))
        elif not id_read:
            rcm = ("ELIGIBLE UNDER RULE 1; RECOMMEND a CONFIRMED image check transcribing the S.R.O. number and date line before the owner decision"
                   + ("; then copy provenance only, with the S.R.O. 34 limitation recorded verbatim" if "S.R.O. 34/1963" in special else ""))
        elif "S.R.O. 34/1963" in special:
            rcm = ("ELIGIBLE UNDER RULE 1 FOR COPY PROVENANCE ONLY; READY for an owner decision with the S.R.O. 34 identity limitation "
                   "recorded verbatim (no amendment-chain inference)")
        else:
            rcm = "ELIGIBLE UNDER RULE 1; READY for an owner decision with the stated limitations"
        reg.append({"tranche_id": tid, "sub_tranche": sub, "sha256": s, "source_id": d["source_id"], "copy_id": d["copy_id"],
                    "document_identity": neutral_identity(d["document_identity"]), "issuing_authority": M["authority"], "publication_type": M["publication_type"],
                    "notification_identifiers": "; ".join(f"S.R.O. {n}" for n in sros),
                    "identifier_read_on_image": "YES" if id_read else "NOT_RECORDED", "carrier": C["copy_carrier_provenance"].split(" ")[0],
                    "fidelity_class": fc, "first_class_locator": url, "proposed_class": CLS, "rule1_result": verdict, "recommendation": rcm})
        matrix.append({
            "tranche_id": tid, "sha256": s,
            "v01_exact_source": f"{d['source_id']} / {d['copy_id']}: {neutral_identity(M['title'])}",
            "v02_held_file_sha256": f"{s} (held: {R['held_paths']})",
            "v03_issuing_authority": M["authority"],
            "v04_title_and_identifier": (f"{neutral_identity(d['document_identity'])}; S.R.O. number(s) {sros}: read in image-check, transcription or L5 image-quote text {sro_img or 'NOT FOUND'}; "
                                         f"in page-1 text layer {sro_p1 or 'NOT FOUND'} (text-layer absence is not adverse for a scanned page)"),
            "v05_carrier_classification": f"{C['copy_carrier_provenance']}; class {CLS}; publication type {M['publication_type']}",
            "v06_provenance_evidence": (f"first-class {kind}/{strg}: {d['first_class_record_ref']} -> {url}; checksums: {R['checksum_evidence']}; "
                                        f"retrieval date: {R['retrieval_date']}"),
            "v07_identity_page_evidence": identity_summary(e["identity_refs"]) + "".join(
                f" | {x}: {r.get('status')}; render {r.get('render_sha256', '')}; quoted: {r.get('identity_evidence', '')} "
                "(L5 R23 amendment-search record: an image quotation by the R23 examiner; not an identity-reference kind under rule 1)" for x, r in l5),
            "v08_completeness": f"{M['completeness_status']}; pages {F['pages']}; master pages {M['pages']}",
            "v09_derivative_or_rehosting": (f"re-hosted by archive.org (third-party archival facsimile of a Government of India Gazette); producer "
                                            f"'{T['producer']}'; {'not' if fc != 'ARCHIVE_DERIVATIVE' else 'IS'} an Internet Archive derivative producer"),
            "v10_signed_or_scanned": f"{C['text_layer_class']}; embedded images {T['embedded_images']}; text chars {T['text_chars']}; EOF markers {T['eof_markers']}",
            "v11_signature_coverage": (f"signature byte range {T['signature_byte_ranges']} covers file: {T['signed_range_covers_file']}; NOT CRYPTOGRAPHICALLY VERIFIED"
                                       if T["signature_byte_ranges"].strip() else "no embedded signature (scanned facsimile)"),
            "v12_contradictions": f"exact-string locator contradictions: {exact or 'none'}; recovery register: {R['contradictions']}",
            "v13_remaining_to_verify": (R["remaining_gaps"] if R["remaining_gaps"] != "none recorded" else "none recorded in C6-01")
                                       + ("; " + special if special else ""),
            "v14_rule1_permits_class": verdict + (f": {why}" if why else ""),
        })
        contra.append({"tranche_id": tid, "sha256": s, "locator": url, "exact_string_contradictions": "; ".join(exact) or "NONE",
                       "recovery_register_contradictions": R["contradictions"],
                       "identity_discrepancy": special if special.startswith("S.R.O. 34") else "NONE_RECORDED",
                       "status": "DOCUMENTED_UNCERTAINTY" if special.startswith("S.R.O. 34") else "NO_CONTRADICTION_FOUND_IN_SEARCHED_REGISTERS"})
        extra = []
        if "S.R.O. 34/1963" in special:
            extra.append("IDENTITY: the notes' 'S.R.O. 34 dated 5-6-1963' is not shown to be this 05-01-1963 instrument (UNVERIFIED); "
                         "copy provenance only; no amendment-chain inference")
        if sub == "1B-FIDELITY":
            extra.append("FIDELITY: born-digital; embedded signature byte range spans the file - STRUCTURAL ONLY, signature NOT "
                         "cryptographically validated; held pending the owner's fidelity-class decision")
        if not id_read:
            extra.append("IDENTIFIER: S.R.O. number and date line not found in a committed image observation; confirm before approval")
        e = dict(e, limitations="; ".join([e["limitations"]] + extra))
        pending.append(dict(e, tranche_status="PENDING_NOT_IN_LEDGER", tranche_note=(
            "PREPARED ONLY. owner_decision is deliberately EMPTY (fails the ledger schema). Converting this row needs committed D-/R- records, "
            "its own PR and review, and a BIND line after the merge.")))
    # joint simulation
    base, _ = reader.effective_state(PKG, 0)
    sim = Sim()
    try:
        joint = sim.run(entries)
    finally:
        sim.close()
    sim1a = Sim()
    try:
        joint1a = sim1a.run([e for e, r in zip(entries, reg) if r["sub_tranche"] == "1A-READY"])
    finally:
        sim1a.close()
    return reg, matrix, contra, pending, impact(base, joint, joint1a, entries)


def _rows(t):
    return list(csv.DictReader(io.StringIO(t)))


def impact(base, joint, joint1a, entries):
    def diff(after):
        b = {r["sha256"]: r for r in _rows(base["source_copy_register.csv"])}
        a = {r["sha256"]: r for r in _rows(after["source_copy_register.csv"])}
        copies = sorted((s[:8], b[s]["copy_effective_status"], a[s]["copy_effective_status"]) for s in b if b[s]["copy_effective_status"] != a[s]["copy_effective_status"])
        bs = {r["source_id"]: r for r in _rows(base["source_states.csv"])}
        as_ = {r["source_id"]: r for r in _rows(after["source_states.csv"])}
        sources = sorted((k, bs[k]["effective_holding_state"], as_[k]["effective_holding_state"]) for k in bs if bs[k]["effective_holding_state"] != as_[k]["effective_holding_state"])
        bc = {(r["case_id"], r.get("proposition_id", "")): r["evidence_status"] for r in _rows(base["corpus_crosswalk.csv"])}
        ac = {(r["case_id"], r.get("proposition_id", "")): r["evidence_status"] for r in _rows(after["corpus_crosswalk.csv"])}
        cw = sorted({k: (bc[k], ac.get(k)) for k in bc if bc[k] != ac.get(k)}.items())
        bj, aj = json.loads(base["coverage_summary.json"]), json.loads(after["coverage_summary.json"])
        summ = {k: {"before": bj.get(k), "after": aj.get(k)} for k in sorted(set(bj) | set(aj)) if bj.get(k) != aj.get(k)}
        return {"copy_status_changes": len(copies), "copy_status_transitions": sorted({f"{x[1]} -> {x[2]}" for x in copies}),
                "source_holding_changes": [{"source_id": k, "before": x, "after": y} for k, x, y in sources],
                "crosswalk_row_changes": len(cw), "coverage_summary_changes": summ}
    return {"label": "SIMULATION ONLY: synthetic approval records in a temporary directory, deleted after the run. Not a ledger version, "
                     "not an approval, not evidence of owner or legal approval. The committed ledger stays at version 0.",
            "entries_simulated": len(entries), "joint_all_20": diff(joint), "sub_tranche_1A_READY_only": diff(joint1a)}


def outputs():
    reg, matrix, contra, pending, imp = build()
    return {
        "tranche1_source_register.csv": csv_text(list(reg[0]), reg),
        "evidence_verification_matrix.csv": csv_text(list(matrix[0]), matrix),
        "contradiction_register.csv": csv_text(list(contra[0]), contra),
        "proposed_entries_PENDING.csv": csv_text(L.COLS + ["tranche_status", "tranche_note"], pending),
        "simulated_joint_impact.json": json.dumps(imp, indent=1, sort_keys=True) + "\n",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    texts = outputs()
    if a.check:
        bad = [k for k, v in texts.items() if not (OUT / k).is_file() or (OUT / k).read_text(encoding="utf-8") != v]
        if bad:
            print(f"TRANCHE 1 CHECK FAILED: {bad}", file=sys.stderr)
            return 1
        print(f"tranche 1 outputs reproduce ({len(texts)} files)")
        return 0
    OUT.mkdir(parents=True, exist_ok=True)
    for k, v in texts.items():
        (OUT / k).write_text(v, encoding="utf-8")
    print(f"wrote {len(texts)} files to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
