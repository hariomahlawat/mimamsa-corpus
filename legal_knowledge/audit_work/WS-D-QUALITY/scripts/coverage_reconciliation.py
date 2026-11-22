#!/usr/bin/env python3
"""WS-D cycle 2, task 1: reconcile WS-C kb658 source-coverage states with WS-D coverage states.

Read-only, stdlib only, deterministic. WS-C's inventory is read from a LOCAL git ref (default
origin/claude/ws-c-mml) with `git show`; it is never modified. WS-D per-record states come from
scripts/coverage_scorecard.py (crawler corpus from a local ref, default origin/raw-data).

Both sides are mapped to a common coarse bucket (COMPLETE / PARTIAL / NONE / NO_CITATION); each
record whose buckets differ gets deterministic explanation tags (rules R1..R10 in RULES). A record
left with no tag is reported as UNEXPLAINED. Outputs coverage_reconciliation.csv and .md.
Coverage is about locating cited sources; it never says a record is legally correct.
"""
import argparse, collections, csv, hashlib, importlib.util, io, json, subprocess, sys
from pathlib import Path

WSD = Path(__file__).resolve().parents[1]
ROOT = WSD.parents[2]
WSC_PATH = "legal_knowledge/audit_work/WS-C-MML/kb658_source_coverage_inventory.csv"
C_BUCKET = {"FULL": "COMPLETE", "PARTIAL": "PARTIAL", "SOURCE_GAP": "NONE", "UNRESOLVED": "NONE", "NO_CITATION": "NO_CITATION"}
D_BUCKET = {"D_CODED_ALL_SEARCHABLE": "COMPLETE", "D_PLAIN_ALL_STATUTE_SEARCHABLE": "COMPLETE",
            "D_CODED_PARTLY_SEARCHABLE": "PARTIAL", "D_PLAIN_PARTLY_SEARCHABLE": "PARTIAL",
            "D_CODED_NONE_SEARCHABLE": "NONE", "D_PLAIN_STATUTE_NOT_SEARCHABLE": "NONE", "D_PLAIN_CASE_OR_LOCATOR_ONLY": "NONE",
            "D_PLAIN_NO_STATUTE_OR_CASE": "NO_CITATION", "NOT_CHECKED": "NOT_CHECKED"}
RULES = {
    "R1_CO_CITATION": "WS-C never rates a record FULL if a code is resolved only by co-citation; WS-D counts the co-citation target as searchable.",
    "R2_NO_PINPOINT": "WS-C FULL requires a pinpoint; WS-D searchability does not.",
    "R3_STRUCTURAL_FLAG": "WS-C downgrades FULL on provision-not-in-heading-index, Army Act/Rules cited without pinpoint, or non-official URL; WS-D has no such gate.",
    "R4_PLACEHOLDER": "WS-C counts [VERIFY]/'verify' placeholders as unresolved; WS-D ignores placeholders for searchability.",
    "R5_GAP_CODE": "Record has a firm code whose target is a declared GAP: WS-C counts it as a source gap; WS-D as not searchable.",
    "R6_PLAIN_CASE": "Plain-text case citation (incl. WS-C's short-title CASE_NAME_WITHOUT_CODE flag, parser fix ba3d370e): WS-C flags it unresolved and never rates the record FULL; WS-D excludes case names from statute searchability (case-or-locator-only = NONE).",
    "R7_PLAIN_INSTRUMENT_SET": "Plain statute set differs: WS-C treats AA/AR pinpoints and a fixed held list (incl. CrPC, Evidence Act, Air Force/Navy Act, Procedure Rules) as anchors without checking the corpus; WS-D maps only AA/AR/AFT Act/BNS/BNSS/BSA to crawler doc_ids.",
    "R8_NO_CITATION_DEFINITION": "NO_CITATION differs: WS-C requires a code, AA/AR pinpoint, held statute name or case pattern; WS-D counts any statute token (incl. 'AR trial rules') or locator continuation as a reference.",
    "R9_UNRESOLVED_CODE": "Record has a PROBABLE/CATEGORY_ONLY/UNRESOLVABLE code: WS-C counts it unresolved whatever its target; WS-D searchability looks only at whether the register target exists (identity class is scored separately in citation_resolution_score).",
    "R11_PLAIN_NAME_IN_CODED_RECORD": "Coded record that also names a statute in plain text outside WS-C's held list (e.g. 'Constitution'): WS-C counts it as a gap; WS-D scores coded records by their codes only.",
    "R10_TARGET_EXISTENCE": "WS-D checks the register target exists (DCLR id in cases_53; doc_id in crawler corpus); WS-C accepts any act-/rules-/DCLR- prefix not marked '(candidate)'.",
}


def git_show(ref, path):
    if ref == "auto":
        ref = "WORKTREE" if (ROOT / path).is_file() else "origin/claude/ws-c-mml"
    if ref == "WORKTREE":
        raw = (ROOT / path).read_bytes()
        return raw, "WORKTREE"
    out = subprocess.run(["git", "-C", str(ROOT), "show", f"{ref}:{path}"], check=True, capture_output=True).stdout
    commit = subprocess.run(["git", "-C", str(ROOT), "rev-parse", ref], check=True, capture_output=True, text=True).stdout.strip()
    return out, commit


def tags_for(c, d):
    t = []
    flags = c["broken_or_unresolved_flags"]
    if c["codes_co_citation_only"]:
        t.append("R1_CO_CITATION")
    if c["pinpoint_present"] == "NO" and c["coverage_state"] != "NO_CITATION":
        t.append("R2_NO_PINPOINT")
    if any(k in flags for k in ("PROVISION_NOT_IN_HEADING_INDEX", "ARMY_ACT_OR_RULES_CITED_WITHOUT_PINPOINT", "URL_NON_OFFICIAL_HOST")):
        t.append("R3_STRUCTURAL_FLAG")
    if "PLACEHOLDER" in flags:
        t.append("R4_PLACEHOLDER")
    if c["codes_resolved_gap"]:
        t.append("R5_GAP_CODE")
    if c["case_citation_pattern"] == "YES" or "CASE_NAME_WITHOUT_CODE" in flags or "CASE_REFERENCE" in d.get("segment_categories", []):
        t.append("R6_PLAIN_CASE")
    if d["family"] == "PLAINTEXT" and (c["other_statutes_plain"] or c["aa_sections"] or c["ar_rules"]):
        t.append("R7_PLAIN_INSTRUMENT_SET")
    if (c["coverage_state"] == "NO_CITATION") != (d["state"] == "D_PLAIN_NO_STATUTE_OR_CASE"):
        t.append("R8_NO_CITATION_DEFINITION")
    if c["codes_unresolved"] or any(s == "GAP_OR_NON_LEGAL" for s in d.get("code_states", {}).values()):
        t.append("R9_UNRESOLVED_CODE")
    held = {"bsa", "bnss", "bns", "crpc", "evidence act", "aft act", "aft (procedure) rules", "procedure rules", "air force act", "navy act"}
    if d["family"] == "CODED" and any(x.lower() not in held for x in filter(None, c["other_statutes_plain"].split(";"))):
        t.append("R11_PLAIN_NAME_IN_CODED_RECORD")
    if any(s in ("CASE_TARGET_MISSING", "DOC_TARGET_MISSING") for s in d.get("code_states", {}).values()):
        t.append("R10_TARGET_EXISTENCE")
    return t


def build(wsc_ref, corpus_ref):
    raw, commit = git_show(wsc_ref, WSC_PATH)
    if wsc_ref == "auto":
        wsc_ref = "WORKTREE" if commit == "WORKTREE" else "origin/claude/ws-c-mml"
    if commit == "WORKTREE":
        # identify which committed WS-C version the worktree file equals, if any (for the pin)
        for ref in ("origin/claude/ws-c-mml", "HEAD"):
            try:
                blob, c2 = git_show(ref, WSC_PATH)
                if blob == raw:
                    commit = c2; break
            except subprocess.CalledProcessError:
                continue
    wsc = {r["record_id"]: r for r in csv.DictReader(io.StringIO(raw.decode("utf-8"), newline=""))}
    spec = importlib.util.spec_from_file_location("cov", WSD / "scripts" / "coverage_scorecard.py")
    cov = importlib.util.module_from_spec(spec); spec.loader.exec_module(cov)
    sc = cov.build(corpus_ref)
    per = sc["_per_record"]
    assert set(per) == set(wsc) and len(per) == 658, "record sets differ"
    rows = []
    for rid in [r for r in wsc]:  # WS-C file order = KB line order
        c, d = wsc[rid], per[rid]
        cb, db = C_BUCKET[c["coverage_state"]], D_BUCKET[d["state"]]
        agree = cb == db
        tags = [] if agree else tags_for(c, d)
        rows.append({"record_id": rid, "module": c["module"], "wsc_state": c["coverage_state"], "wsd_state": d["state"],
                     "wsc_bucket": cb, "wsd_bucket": db, "agree": "YES" if agree else "NO",
                     "explanation_tags": ";".join(tags) if tags else ("" if agree else "UNEXPLAINED"),
                     "wsc_codes": c["codes"], "wsd_codes": ";".join(d["codes"]),
                     "codes_equal": "YES" if set(filter(None, c["codes"].split(";"))) == set(d["codes"]) else "NO",
                     "wsc_flags": c["broken_or_unresolved_flags"]})
    meta = {"wsc_ref": wsc_ref, "wsc_commit": commit, "wsc_csv_sha256": hashlib.sha256(raw).hexdigest(),
            "corpus_ref": sc["inputs"]["corpus_ref"], "corpus_commit": sc["inputs"]["corpus_commit"],
            "kb_sha256": sc["inputs"]["kb_sha256"]}
    return rows, meta


def render(rows, meta):
    cs = sorted(C_BUCKET); ds = sorted({r["wsd_state"] for r in rows})
    m = collections.Counter((r["wsc_state"], r["wsd_state"]) for r in rows)
    bm = collections.Counter((r["wsc_bucket"], r["wsd_bucket"]) for r in rows)
    bk = ["COMPLETE", "PARTIAL", "NONE", "NO_CITATION"]
    agree = sum(r["agree"] == "YES" for r in rows)
    tag = collections.Counter(t for r in rows for t in r["explanation_tags"].split(";") if t)
    unexplained = [r["record_id"] for r in rows if r["explanation_tags"] == "UNEXPLAINED"]
    code_diff = [r["record_id"] for r in rows if r["codes_equal"] == "NO"]
    L = ["# Coverage reconciliation: WS-C kb658 inventory vs WS-D scorecard", "",
         f"WS-C input: `{WSC_PATH}` at `{meta['wsc_ref']}` @ `{meta['wsc_commit'][:12]}` (sha256 `{meta['wsc_csv_sha256'][:12]}…`), read-only via `git show`. "
         f"WS-D: `scripts/coverage_scorecard.py`, crawler corpus `{meta['corpus_ref']}` @ `{(meta['corpus_commit'] or 'n/a')[:12]}`. KB sha `{meta['kb_sha256'][:12]}…`.", "",
         "**Coverage locates cited sources. It never says that a record is legally correct, current, or verified.**", "",
         "## 1. Definitions side by side", "",
         "| Aspect | WS-C (`build_kb658_inventory.py`) | WS-D (`coverage_scorecard.py`) |", "| --- | --- | --- |",
         "| Question answered | Is each citation anchored to an identified source held in the corpus, with a pinpoint and no broken flags? | Does every cited source exist as a document the database can search? |",
         "| Citation parser | own `kb_citations.py`: v3 codes + AA/AR pinpoints by context + other-statute names + case pattern (references + sources) | PILOT-01 `build_code_inventory.py` codes (v3 grammar); plain-text records via `plaintext_citation_index.csv` segments |",
         "| Code held | firm or co-citation class and target starts `act-`/`rules-`/`DCLR-`, not '(candidate)' | target is a DCLR id present in cases_53, or a doc_id present in crawler `data/meta` |",
         "| Co-citation codes | never FULL (PARTIAL at best) | target counted if searchable; inferred status scored separately (citation_resolution_score) |",
         "| Plain statutes | AA/AR pinpoints always anchors; fixed held list (BSA, BNSS, BNS, CrPC, Evidence Act, AFT Act, Procedure Rules, Air Force Act, Navy Act) | AA, AR, AFT Act, BNS, BNSS, BSA mapped to crawler doc_ids; Act sections checked against corpus section files |",
         "| Pinpoint | required for FULL | not required |",
         "| Placeholders, structural flags | downgrade FULL | ignored for searchability (reported in index) |",
         "| Plain case names | counted as citation; unresolved flag | not counted as statute; case-or-locator-only record = NONE |",
         "| States | FULL / PARTIAL / SOURCE_GAP / UNRESOLVED / NO_CITATION | coded: ALL / PARTLY / NONE searchable; plain: ALL / PARTLY / NOT searchable, CASE_OR_LOCATOR_ONLY, NO_STATUTE_OR_CASE |",
         "| Denominator | 658 records, one state each | 658 records, one state each (389 coded + 269 plain) |", "",
         "## 2. State totals", "", "| WS-C state | n | | WS-D state | n |", "| --- | --- | --- | --- | --- |"]
    cc = collections.Counter(r["wsc_state"] for r in rows); dc = collections.Counter(r["wsd_state"] for r in rows)
    for i in range(max(len(cs), len(ds))):
        a = cs[i] if i < len(cs) else ""; b = ds[i] if i < len(ds) else ""
        L.append(f"| {a} | {cc[a] if a else ''} | | {b} | {dc[b] if b else ''} |")
    L += ["", "Mapping to coarse buckets: WS-C FULL→COMPLETE, PARTIAL→PARTIAL, SOURCE_GAP/UNRESOLVED→NONE, NO_CITATION→NO_CITATION; "
          "WS-D *_ALL_*→COMPLETE, *_PARTLY_*→PARTIAL, *_NONE_*/STATUTE_NOT_SEARCHABLE/CASE_OR_LOCATOR_ONLY→NONE, NO_STATUTE_OR_CASE→NO_CITATION.", "",
          "## 3. Agreement matrix (coarse buckets; rows WS-C, columns WS-D)", "", "| WS-C \\ WS-D | " + " | ".join(bk) + " | total |", "| --- |" + " --- |" * (len(bk) + 1)]
    for a in bk:
        L.append(f"| {a} | " + " | ".join(str(bm[(a, b)]) for b in bk) + f" | {sum(bm[(a, b)] for b in bk)} |")
    L += ["", f"**Agreement: {agree}/658 ({round(100 * agree / 658, 1)}%).** Disagreements: {658 - agree}; with at least one explanation tag: {658 - agree - len(unexplained)}; unexplained: {len(unexplained)}" + (f" ({', '.join(unexplained)})" if unexplained else "") + ".", "",
          "## 4. Fine-grained matrix (WS-C state × WS-D state)", "", "| WS-C \\ WS-D | " + " | ".join(ds) + " |", "| --- |" + " --- |" * len(ds)]
    for a in cs:
        L.append(f"| {a} | " + " | ".join(str(m[(a, b)]) for b in ds) + " |")
    L += ["", "## 5. Explained differences (tag counts over disagreeing records; a record can carry several)", "", "| Rule | Records | Meaning |", "| --- | --- | --- |"]
    for k, v in RULES.items():
        L.append(f"| {k} | {tag[k]} | {v} |")
    L += ["", f"Code sets agree on {658 - len(code_diff)}/658 records" + (f"; differ on: {', '.join(code_diff)}" if code_diff else "") + ". (Both sides use the PILOT-01 v3 code grammar.)", "",
          "## 6. Proposed canonical definition set (PROPOSAL ONLY; needs coordinator/owner decision)", "",
          "Report **three separate, named measures** over the same 658 denominator instead of one blended state. Each must be computed by one shared, committed parser (proposal: WS-C `kb_citations.py` grammar extended with the WS-D plain-text segment index, so code sets and plain segments are identical on both sides):", "",
          "1. **CITATION_PRESENT** (yes/no + kind): the record cites at least one code, statute token, statute locator or case. Placeholders and editorial labels are not citations. This replaces both NO_CITATION definitions (closes R8).",
          "2. **SOURCE_IDENTIFIED** (ALL / PARTLY / NONE): each citation resolves to an identified instrument or judgment. Firm register classes only; co-citation is reported separately as INFERRED and never counted as identified (closes R1). Gap codes are NONE (R5); PROBABLE/CATEGORY_ONLY/UNRESOLVABLE are NONE (R9); plain case names are NONE until WS-B resolves them (R6).",
          "3. **SOURCE_SEARCHABLE** (ALL / PARTLY / NONE / NOT_CHECKED): every identified source exists in a searchable corpus, checked by existence (DCLR id in cases_53; doc_id in crawler `data/meta`; Act section file where a section is cited) (closes R10 and R7: one instrument map, held list = instruments actually present in the corpus).", "",
          "Pinpoint presence (R2), placeholders (R4) and structural flags (R3) become **quality flags reported alongside**, not gates inside the coverage state. Then 'FULL' would be the derived conjunction CITATION_PRESENT ∧ SOURCE_IDENTIFIED=ALL ∧ SOURCE_SEARCHABLE=ALL ∧ pinpoint ∧ no flags, published with its own name, e.g. `ANCHORED_FULL`. No measure implies text verification or legal correctness.", "",
          "Per-record detail: `coverage_reconciliation.csv` (one row per record: both states, buckets, agreement, explanation tags, code sets, WS-C flags).", ""]
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--wsc-ref", default="auto", help="auto (worktree file if present, else origin/claude/ws-c-mml), WORKTREE, or a git ref")
    ap.add_argument("--corpus-ref", default="origin/raw-data")
    a = ap.parse_args(argv)
    rows, meta = build(a.wsc_ref, a.corpus_ref)
    buf = io.StringIO(); w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n"); w.writeheader(); w.writerows(rows)
    (WSD / "coverage_reconciliation.csv").write_text(buf.getvalue(), encoding="utf-8")
    md = render(rows, meta)
    (WSD / "coverage_reconciliation.md").write_text(md, encoding="utf-8")
    # Input pins: the regeneration test rebuilds from exactly these inputs, wherever it runs.
    pins = {"note": "Inputs of coverage_reconciliation.csv/.md. The test regenerates from the WS-C inventory whose "
                    "SHA-256 is wsc_csv_sha256 (worktree file if it matches, else git object wsc_commit) and the "
                    "crawler corpus at corpus_commit. A different WS-C inventory means: rerun this script.",
            "wsc_path": WSC_PATH, "wsc_ref": meta["wsc_ref"], "wsc_commit": meta["wsc_commit"],
            "wsc_csv_sha256": meta["wsc_csv_sha256"], "corpus_ref": meta["corpus_ref"], "corpus_commit": meta["corpus_commit"],
            "kb_sha256": meta["kb_sha256"],
            "wsc_state_totals": dict(sorted(collections.Counter(r["wsc_state"] for r in rows).items())),
            "wsd_state_totals": dict(sorted(collections.Counter(r["wsd_state"] for r in rows).items())),
            "agreement": sum(r["agree"] == "YES" for r in rows),
            "explanation_tag_counts": dict(sorted(collections.Counter(t for r in rows for t in r["explanation_tags"].split(";") if t).items()))}
    (WSD / "coverage_reconciliation.meta.json").write_text(json.dumps(pins, indent=1) + "\n", encoding="utf-8")
    print(md.split("## 4.")[0][-900:])
    return 0


if __name__ == "__main__":
    sys.exit(main())
