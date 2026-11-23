"""Writes the D1, D2, D4 and D5 summary reports from the committed C6-01 registers (deterministic)."""
import csv, json
from collections import Counter
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]


def read(n):
    with open(PKG / "registers" / n, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


OUT = {}


def main():
    s = json.loads((PKG / "registers/c6_01_summary.json").read_text())
    rec, props, unres = read("provenance_recovery_register.csv"), read("source_authentication_proposals.csv"), read("unresolved_provenance_register.csv")
    ci = s["coverage_impact"]
    o = s["outcomes_by_source_type"]
    doc = [r for r in rec if r["proposed_outcome"] == "PROVENANCE_DOCUMENTED"]
    L = ["# D1. Provenance recovery register (summary)", "",
         f"**Register:** `registers/provenance_recovery_register.csv`, {s['denominators']['scope_copies']} copies in {s['denominators']['scope_sources']} sources.",
         "",
         "Each row carries:",
         "- source identity, issuing authority and carrier;",
         "- retrieval URL, retrieval date (only where evidenced) and retrieval method;",
         "- checksums (sha256, md5, sha1, bytes) and locator strength;",
         "- pages, completeness and identity-verification references;",
         "- related copies, current status and contradictions;",
         "- proposed outcome and remaining gaps.", "",
         "| Outcome | Court copies | Publication/record copies | Total |", "| --- | --- | --- | --- |"]
    for k in ("PROVENANCE_DOCUMENTED", "PROVENANCE_PARTIALLY_DOCUMENTED", "IDENTITY_VERIFIED_PROVENANCE_UNDOCUMENTED", "NO_RECOVERABLE_PROVENANCE", "AUTHENTICATION_PENDING"):
        a, b = o.get(k + "|court", 0), o.get(k + "|publication", 0)
        L.append(f"| {k} | {a} | {b} | {a + b} |")
    L += ["", "**Locator strength of the DOCUMENTED rows:** " + ", ".join(f"{k} {v}" for k, v in sorted(Counter(r['locator_strength'] for r in doc).items())) + ".",
          "Only FULL can reach DOCUMENTED: a sha256 recorded with a URL, or archive size, md5 and sha1. This is the Cycle 4 bar.", "",
          f"**Retrieval dates:** {sum(1 for r in rec if r['retrieval_date'][:4].isdigit())} rows carry a date from a retrieval record. The rest have only a register date, or none (`NOT_EVIDENCED`).", "",
          "**The seven Supreme Court case records that were partial in Cycle 5:**",
          "- Dharamvir Singh, Rajbir Singh (copy C1 only), Girish Kumar (Feb 2026), Mullikote, Ranjit Thakur, S N Mukherjee and Navjot Sandhu.",
          "- Each anchor copy has a FULL locator (an official URL with a sha256 equal to the held bytes) and a page-1 text identity match on two title words plus the year or case number. No contradiction was found.",
          "- Where the evidence is a register corroboration only, the row carries the Cycle 4 caveat \"accepted because uncontradicted\" and keeps its \"as reported\" carrier qualifier.",
          "- Rajbir copy C2 is PARTIALLY_DOCUMENTED: its only locator is a mention inside C1's record (Fable F-01). Rajbir's third copy (a court-system rendition with unknown carrier) is non-primary.",
          "- N S Yadav, which is not one of the 53 cases, meets the same criteria.",
          "", "**Isaac is out of scope and unchanged (AUTHENTICATION_PENDING).**"]
    OUT["D1_PROVENANCE_RECOVERY_REGISTER.md"] = "\n".join(L) + "\n"
    L = ["# D2. Source authentication proposals", "",
         f"**Register:** `registers/source_authentication_proposals.csv`, {len(props)} proposed **additions** in the CALIBRATION-02 register columns.",
         "- **The original register is not edited.**",
         "- Each row reads `C6-01 PROPOSAL - not incorporated`.",
         "- Before any addendum, each needs independent verification (D3) and owner approval.",
         "- **Status:** " + ", ".join(f"{v} {k}" for k, v in s["proposals_by_status"].items()) + ".",
         "- **Not proposals:** the Rajya Sabha papers-laid record and Rajbir copy C2 fall to PROVENANCE_PARTIALLY_DOCUMENTED by rule (Fable F-01, F-02). The RS record is also WITHHELD by owner instruction and stays a discovery/evidence candidate; the S.O. 4010 date it transcribes ('6th December, 1986') is DISPUTED (C5 RV-01 reads 08-12-1986; C5 D7 disagreement OPEN); the notification's authoritative date and its date semantics are NOT_VERIFIED, and only the Gazette of S.O. 4010/1986 can settle the date.", "",
         "| Proposed class | Rows |", "| --- | --- |"] + [f"| {k} | {v} |" for k, v in s["proposals_by_class"].items()] + ["",
         "**Non-primary on purpose** (" + str(sum(1 for p in props if p["effective_source_class"].startswith("NON_PRIMARY"))) + "):"] + [
         f"- {p['document_identity'][:110]}: `{p['effective_source_class']}`" for p in props if p["effective_source_class"].startswith("NON_PRIMARY")] + ["",
         "The two Gazette-copy entries above (TRA 2026 and the 2022 archive.org derivative) follow one copy-fidelity rule for born-digital copies (Fable F-04); see `reports/TRA2026_CLASS_COMPARISON.md`. Class decisions are reserved for the owner.", "",
         "**Note on the Cycle 4 rule:** the shared Cycle 4 evidence rule does not recognise NON_PRIMARY_* classes, so non-primary entries have no coverage effect in the D4 simulation (final review R-03).", "",
         "**Exclusions:** no proposal for Isaac, and no promotion of anything AUTHENTICATION_PENDING.",
         "",
         "**Downgraded after independent verification:** Act 13/1975. Its download record gives an India Code identifier, not a retrieval URL, and has no date.",
         "",
         "**Limitations on every row:**",
         "- no signature verified;",
         "- the gaps from D1;",
         "- the Cycle 4 caveat \"accepted because uncontradicted\", where the evidence is a corroboration record only."]
    OUT["D2_SOURCE_AUTHENTICATION_PROPOSALS.md"] = "\n".join(L) + "\n"
    b, p, ab, ap = ci["baseline"], ci["proposed"], ci["authentication_baseline"], ci["authentication_proposed"]
    f = lambda d, k: " / ".join(str(d[k].get(x, 0)) for x in ("EXACT_ANCHOR", "PARTIAL_MATCH", "MISSING_EVIDENCE"))
    g = lambda d: " / ".join(str(d["kb_records_by_anchor_class"].get(x, 0)) for x in ("ALL_EXACT", "SOME_EXACT", "NO_EXACT_ANCHOR"))
    L = ["# D4. Coverage impact assessment", "",
         "**Method:**",
         "- The Cycle 5 builder is re-run with the D2 proposals added to the Cycle 4 register **in memory only**.",
         "- The simulation switches off the Cycle 5 holding-state consistency check (`check_holding_vs_copies`), because the frozen Cycle 5 master still labels those sources `*_PROVENANCE_UNDOCUMENTED`. Real incorporation would **not** relabel or edit Cycle 5: it would use the overlay design (`addendum/INTEGRATION_ARCHITECTURE.md`, revision 2), where source states are derived in a separate package with the consistency rule on (final review R-02; Fable F-05/F-06).",
         f"- {sum(1 for p in props if p['effective_source_class'].startswith('NON_PRIMARY'))} non-primary proposals are included in the simulation but have no effect: the Cycle 4 rule has no NON_PRIMARY_* class (R-03).",
         "- The classification rules are unchanged.",
         "- A test proves the committed Cycle 5 registers are unaffected.", "",
         "| Measure | Previous (Cycle 5, as merged) | Proposed (if D2 were incorporated) |", "| --- | --- | --- |",
         f"| Documented-primary copies | {ab['documented_primary_copies']} | {ap['documented_primary_copies']} |",
         f"| Sources with a documented-primary copy | {ab['sources_with_documented_primary_copy']} | {ap['sources_with_documented_primary_copy']} |",
         f"| Authentication-pending copies | {ab['authentication_pending_copies']} | {ap['authentication_pending_copies']} |",
         f"| KB citation items: exact / partial / missing | {f(b, 'crosswalk_kb_items_by_status')} | {f(p, 'crosswalk_kb_items_by_status')} |",
         f"| KB records: all / some / no exact | {g(b)} | {g(p)} |",
         f"| Cases (53): exact / partial / missing | {f(b, 'crosswalk_case_rows_by_status')} | {f(p, 'crosswalk_case_rows_by_status')} |", "",
         "**Why the KB figures do not move:**",
         "- KB citations resolve to the Army Act, Army Rules, AFT Act, BNSS and BSA. Their held copies are the 1954 Gazette (already primary) and government compilations, none of which are in scope.",
         "- The amendment Gazettes and judgments in scope carry no provision locators in the WS-D items.",
         "",
         "**The case gain** comes entirely from the seven SC case records in D1.",
         "",
         "Nothing is incorporated, and nothing changes legal status."]
    OUT["D4_COVERAGE_IMPACT.md"] = "\n".join(L) + "\n"
    L = ["# D5. Unresolved provenance register", "", f"**Register:** `registers/unresolved_provenance_register.csv`, {len(unres)} copies.", ""] + [
        f"- **{r['copy_id']}**: {r['proposed_outcome']}.\n  - Missing: {r['what_is_missing']}.\n  - Next step: {r['next_step']}." for r in unres] + ["",
        f"The other {s['denominators']['undocumented_copies_c5'] - s['denominators']['scope_copies']} Cycle 5 undocumented copies (compilations and MML manuals: {s['denominators']['undocumented_copies_c5']} − {s['denominators']['scope_copies']}) are outside this scope. They are not investigated here and their status is unchanged."]
    OUT["D5_UNRESOLVED_PROVENANCE.md"] = "\n".join(L) + "\n"


def run(argv=None):
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    OUT.clear()
    main()
    stale = [k for k, v in OUT.items() if (PKG / "reports" / k).read_text(encoding="utf-8") != v] if a.check else []
    if not a.check:
        for k, v in OUT.items():
            (PKG / "reports" / k).write_text(v, encoding="utf-8")
    print("STALE: " + ", ".join(stale) if stale else "ok")
    return 1 if stale else 0


if __name__ == "__main__":
    raise SystemExit(run())
