"""Writes the D1, D2, D4 and D5 summary reports from the committed C6-01 registers (deterministic)."""
import csv, json
from collections import Counter
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]


def read(n):
    with open(PKG / "registers" / n, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    s = json.loads((PKG / "registers/c6_01_summary.json").read_text())
    rec, props, unres = read("provenance_recovery_register.csv"), read("source_authentication_proposals.csv"), read("unresolved_provenance_register.csv")
    ci = s["coverage_impact"]
    o = s["outcomes_by_source_type"]
    doc = [r for r in rec if r["proposed_outcome"] == "PROVENANCE_DOCUMENTED"]
    L = ["# D1. Provenance recovery register (summary)", "",
         "**Register:** `registers/provenance_recovery_register.csv`, 36 copies in 34 sources.",
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
          "- Dharamvir Singh, Rajbir Singh, Girish Kumar (Feb 2026), Mullikote, Ranjit Thakur, S N Mukherjee and Navjot Sandhu.",
          "- Each has a FULL locator (an official URL with a sha256 equal to the held bytes) and a page-1 text identity match. No contradiction was found.",
          "- Where the evidence is a register corroboration only, the row carries the Cycle 4 caveat \"accepted because uncontradicted\".",
          "- Rajbir's third copy (a court-system text rendition with unknown carrier) is proposed as non-primary.",
          "- N S Yadav, which is not one of the 53 cases, meets the same criteria.",
          "", "**Isaac is out of scope and unchanged (AUTHENTICATION_PENDING).**"]
    (PKG / "reports/D1_PROVENANCE_RECOVERY_REGISTER.md").write_text("\n".join(L) + "\n")
    L = ["# D2. Source authentication proposals", "",
         f"**Register:** `registers/source_authentication_proposals.csv`, {len(props)} proposed **additions** in the CALIBRATION-02 register columns.",
         "- **The original register is not edited.**",
         "- Each row reads `C6-01 PROPOSAL - not incorporated`.",
         "- Before any addendum, each needs independent verification (D3) and owner approval.", "",
         "| Proposed class | Rows |", "| --- | --- |"] + [f"| {k} | {v} |" for k, v in s["proposals_by_class"].items()] + ["",
         "**Non-primary on purpose:**",
         "- the Rajya Sabha papers-laid page, which records the laying of a notification and is not the instrument;",
         "- the 13 MB ER 2023 copy, which is incomplete because GMO-2023 is absent;",
         "- Rajbir's court-system text rendition.", "",
         "**Exclusions:** no proposal for Isaac, and no promotion of anything AUTHENTICATION_PENDING.",
         "",
         "**Downgraded after independent verification:** Act 13/1975. Its download record gives an India Code identifier, not a retrieval URL, and has no date.",
         "",
         "**Limitations on every row:**",
         "- no signature verified;",
         "- the gaps from D1;",
         "- the Cycle 4 caveat \"accepted because uncontradicted\", where the evidence is a corroboration record only."]
    (PKG / "reports/D2_SOURCE_AUTHENTICATION_PROPOSALS.md").write_text("\n".join(L) + "\n")
    b, p, ab, ap = ci["baseline"], ci["proposed"], ci["authentication_baseline"], ci["authentication_proposed"]
    f = lambda d, k: " / ".join(str(d[k].get(x, 0)) for x in ("EXACT_ANCHOR", "PARTIAL_MATCH", "MISSING_EVIDENCE"))
    g = lambda d: " / ".join(str(d["kb_records_by_anchor_class"].get(x, 0)) for x in ("ALL_EXACT", "SOME_EXACT", "NO_EXACT_ANCHOR"))
    L = ["# D4. Coverage impact assessment", "",
         "**Method:**",
         "- The Cycle 5 builder is re-run with the D2 proposals added to the Cycle 4 register **in memory only**.",
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
    (PKG / "reports/D4_COVERAGE_IMPACT.md").write_text("\n".join(L) + "\n")
    L = ["# D5. Unresolved provenance register", "", f"**Register:** `registers/unresolved_provenance_register.csv`, {len(unres)} copies.", ""] + [
        f"- **{r['copy_id']}**: {r['proposed_outcome']}.\n  - Missing: {r['what_is_missing']}.\n  - Next step: {r['next_step']}." for r in unres] + ["",
        "The other 18 Cycle 5 undocumented copies (compilations and MML manuals: 54 − 36) are outside this scope. They are not investigated here and their status is unchanged."]
    (PKG / "reports/D5_UNRESOLVED_PROVENANCE.md").write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
