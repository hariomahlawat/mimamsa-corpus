"""Rule-version decision pack data (AUTH-LEDGER-02): what options A, B and C would change for the 32 C6-01 drafts.

Read-only analysis. It changes no rule: rule 1 stays the effective rule, and nothing here is a rule-2 implementation.
  python policy_impact.py           write AUTH-LEDGER/RULE_DECISION_PACK_data.json
  python policy_impact.py --check   fail if the committed file differs from a rebuild"""
import argparse, json, re, sys, urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / "RULE_DECISION_PACK_data.json"
PKG = HERE.parents[1]
sys.path.insert(0, str(PKG / "tools"))
from common import AW, LedgerError, read_csv  # noqa: E402
import strength  # noqa: E402

DRAFT = AW / "C6-01-PROVENANCE/addendum/authentication_addendum_v1_draft.csv"
INSTR = "ARMY-RULES-CHAIN-01/army_rules_instrument_register.csv"


def identity_basis(d):
    """Which kinds of identity reference would satisfy rule 1 for this draft, evaluated one reference at a time."""
    kinds = []
    refs = [x for x in d["identity_refs"].split("; ") if x]
    for ref in refs:
        kind, _, r = ref.partition(":")
        if kind == "T":
            continue
        path, rec = strength.resolve(r)
        try:
            strength.identity_ok([ref], d["sha256"], False, "", "")
        except LedgerError:
            continue
        if path == INSTR:
            kinds.append("REGISTER_ROW_IMAGE_CHECKED")
        elif path.startswith("C6-01-PROVENANCE/"):
            kinds.append("C6_CHECK_CONFIRMED")
        else:
            kinds.append("LEGACY_IMAGE_CHECK_NO_RESULT_FIELD")
    court_text = False
    for ref in refs:
        if ref.startswith("T:"):
            court_text = True
    return sorted(set(kinds)), court_text


def c2(url):
    p = urllib.parse.urlsplit(url)
    host = (p.hostname or "").lower()
    port = "" if p.port in (None, 443 if p.scheme.lower() == "https" else 80) else f":{p.port}"
    return urllib.parse.urlunsplit((p.scheme.lower(), host + port, p.path, p.query, ""))


def build():
    drafts = read_csv(DRAFT)
    out = {"label": "Analysis only. Rule 1 remains the effective rule; no option is adopted or implemented.", "drafts": len(drafts)}
    # A: verification state of the first-class retrieval record
    a_rows = []
    for d in drafts:
        kind, st, url = strength._first_class(d["first_class_record_ref"], d["sha256"])
        vs = ""
        if kind == "RET":
            _p, rec = strength.resolve(d["first_class_record_ref"])
            vs = rec.get("verification_state", "")
        a_rows.append({"sha256": d["sha256"][:8], "class": d["proposed_class"], "first_class_kind": kind, "verification_state": vs or "n/a (not a retrieval record)"})
    located = [r for r in a_rows if r["verification_state"] == "SOURCE_LOCATED"]
    alt = {}  # another FULL first-class record for the same sha256 among the draft's evidence references (Fable F-13)
    for d in drafts:
        for x in [y for y in d["evidence_refs"].split("; ") if y]:
            ref = x.split(":", 1)[1]
            if ref == d["first_class_record_ref"]:
                continue
            try:
                k2, st2, _u = strength._first_class(ref, d["sha256"])
            except LedgerError:
                continue
            if k2 == "RET":
                _p, r2 = strength.resolve(ref)
                if r2.get("verification_state") == "SOURCE_LOCATED":
                    continue
            alt.setdefault(d["sha256"][:8], []).append(f"{k2}:{ref}")
    repoint = sorted(f"{r['sha256']} -> {alt[r['sha256']][0]}" for r in located if r["sha256"] in alt)
    lost = [r for r in located if r["sha256"] not in alt]
    out["A"] = {"first_class_kinds": _count(a_rows, "first_class_kind"), "retrieval_verification_states": _count(a_rows, "verification_state"),
                "A1_keep_deny_list": {"newly_ineligible": 0, "newly_eligible": 0},
                "A2_require_SOURCE_VERIFIED": {"first_class_record_fails": len(located), "re_pointable_to_another_full_record": repoint,
                                               "newly_ineligible": len(lost), "which": sorted(f"{r['sha256']} {r['class']}" for r in lost), "newly_eligible": 0},
                "A3_split_provenance_and_content": {"newly_ineligible": 0, "newly_eligible": 0, "entries_needing_limitation_text": len(located)}}
    # B: identity basis
    b_rows = []
    for d in drafts:
        kinds, court_text = identity_basis(d)
        b_rows.append({"sha256": d["sha256"][:8], "class": d["proposed_class"], "kinds": kinds, "court_text": court_text,
                       "anchor_effect": "none" not in d["crosswalk_effect_this_entry_alone"]})
    legacy_only = [r for r in b_rows if r["kinds"] and set(r["kinds"]) <= {"LEGACY_IMAGE_CHECK_NO_RESULT_FIELD", "REGISTER_ROW_IMAGE_CHECKED"}]
    text_only = [r for r in b_rows if not r["kinds"] and r["court_text"]]
    out["B"] = {"identity_basis_by_draft": [{"sha256": r["sha256"], "class": r["class"], "image_kinds": r["kinds"], "court_text_rule": r["court_text"],
                                             "creates_exact_anchor_alone": r["anchor_effect"]} for r in b_rows],
                "legacy_or_register_only": len(legacy_only), "court_text_only": len(text_only),
                "B1_accept_as_now": {"newly_ineligible": 0, "newly_eligible": 0},
                "B2_fresh_check_only_where_anchor_created": {"needing_fresh_check_or_reviewer_statement":
                                                             sorted(r["sha256"] for r in legacy_only + text_only if r["anchor_effect"])},
                "B3_fresh_check_for_all_legacy": {"needing_fresh_check": sorted(r["sha256"] for r in legacy_only + text_only)}}
    # C: normalisation and contradictions
    pairs = sorted(strength.url_pairs())
    by_exact, by_c2 = {}, {}
    for u, s in pairs:
        by_exact.setdefault(u, set()).add(s)
        by_c2.setdefault(c2(u), set()).add(s)
    exact_contra = sorted(u for u, ss in by_exact.items() if len(ss) > 1)
    c2_contra = sorted(u for u, ss in by_c2.items() if len(ss) > 1)
    alias = {}
    for u, s in pairs:
        alias.setdefault(re.sub(r"/(jonew|judgment)/judis/", "/ALIAS/judis/", u), set()).add(s)
    alias_contra = sorted(u for u, ss in alias.items() if len(ss) > 1)
    variants = sorted({u for u, _ in pairs if c2(u) != u})
    items = {}  # archive.org items recorded under both /details/<item> and /download/<item>/<file> (Fable F-03)
    for u, s in pairs:
        m = re.match(r"https://archive\.org/(details|download)/([^/?#]+)", u)
        if m:
            items.setdefault(m.group(2), {}).setdefault(m.group(1), set()).add(s)
    both = sorted(i for i, v in items.items() if len(v) == 2)
    both_conflict = sorted(i for i in both if len(set().union(*items[i].values())) > 1)
    out["C"] = {"committed_url_sha_pairs": len(pairs), "distinct_urls": len(by_exact), "exact_string_contradictions": exact_contra,
                "urls_changed_by_C2_normalisation": variants, "C2_contradictions": c2_contra,
                "contradictions_if_jonew_judgment_alias_adopted": alias_contra,
                "archive_items_recorded_under_details_and_download": both,
                "archive_items_details_download_with_differing_sha256": both_conflict,
                "newly_eligible_under_any_C_option": 0,
                "first_class_locators_rejected_by_AUTH_LEDGER_02_strict_parser": sorted(u for u, _ in pairs if strength.urlcheck.problem(u))}
    return out


def _count(rows, k):
    c = {}
    for r in rows:
        c[r[k]] = c.get(r[k], 0) + 1
    return dict(sorted(c.items()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    text = json.dumps(build(), indent=1, sort_keys=True) + "\n"
    if a.check:
        if not OUT.is_file() or OUT.read_text(encoding="utf-8") != text:
            print("POLICY IMPACT CHECK FAILED", file=sys.stderr)
            return 1
        print("policy impact data reproduces")
        return 0
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
