"""Regression check for statutory_version_completeness_cycle3.csv (stdlib only).

For every Army Act section and Army Rule row in the completeness table:
  C1  every amending instrument registered against that provision in
      army_act_amendment_chain.csv (AA), provision_change_log.csv (AR) or
      ARMY-RULES-CHAIN-01/army_rules_instrument_register.csv (AR) appears in
      located_amending_instruments;
  C2  no row says amendments_image_checked = ALL, or a status that rests on all
      located amendments being image-checked (ESTABLISHED*, or for AA
      PARTIALLY_ESTABLISHED), while any registered amendment is unexamined or
      text-only.
Exit 1 on any failure; prints one line per failure.
Usage: python3 check_completeness_cycle3.py [--table PATH] [--selftest]
"""
import csv, re, sys, pathlib
HERE = pathlib.Path(__file__).resolve().parent.parent          # WS-A-STATUTORY
AW = HERE.parent                                               # audit_work
def rows(p): return list(csv.DictReader(open(p, newline="", encoding="utf-8")))

def secs(text):
    """Section/rule numbers following 's.'/'ss.'/'r.'/'rr.' (ranges a-b expanded)."""
    out = set()
    for m in re.finditer(r"\b(?:ss?|rr?)\.\s*((?:\d+[A-Z]?(?:\([^)]*\))*\s*(?:[,/&]|and|-|to)?\s*)+)", text):
        chunk = re.sub(r"\([^)]*\)", "", m.group(1))
        for a, b in re.findall(r"(\d+)\s*-\s*(\d+)", chunk):
            if int(b) > int(a) and int(b) - int(a) < 40: out.update(str(i) for i in range(int(a), int(b) + 1))
        out.update(re.findall(r"\d+[A-Z]?", chunk))
    return out

def aa_key(row):
    """Canonical key for an Army Act amending instrument, as used in the completeness table."""
    ny = row["number_year"]; inst = row["instrument"]
    if "Adaptation" in inst or "A.L.O" in ny: return "A.L.O."
    if ny.startswith("S.O."): return ny.split(" ")[0] + " " + ny.split(" ")[1]
    if ny.startswith("Reg."): return "Reg."
    m = re.match(r"(?:Ord\.\s*)?(\d+) of (\d{4})", ny)
    if m: return ("Ord. " if ny.startswith("Ord") else "Act ") + f"{m.group(1)}/{m.group(2)}"
    return ny

def registered_aa():
    reg = {}
    src = rows(HERE / "army_act_amendment_chain.csv")
    add = HERE / "army_act_amendment_chain_addendum_cycle3.csv"
    if add.exists(): src += rows(add)
    for r in src:
        inst = r["instrument"]
        if r["chain_id"] in ("AA-00", "AA-13") or "Bill" in inst or r["number_year"].startswith("Bill"): continue
        if r["sections_affected"].lower().startswith("none"): continue
        img = r["evidence_level"].startswith("IMAGE_CHECKED")
        # drop references to sections of the AMENDING Act itself, e.g. "(s.3 and Second Schedule)", "s.3 of Act 19/1955"
        txt = re.sub(r"s\.\s*\d+\s+(?:of Act[^;)]*|and (?:the )?(?:Second )?Sch[^;)]*)", "", r["sections_affected"])
        for s in secs(txt):
            k = aa_key(r)
            reg.setdefault(s, {})
            reg[s][k] = reg[s].get(k, False) or img
    return reg

def registered_ar():
    reg = {}
    for r in rows(HERE / "provision_change_log.csv"):
        iid = r["instrument_ref"]
        if not iid.startswith("AR-") or iid == "AR-000": continue
        img = r["copy_fidelity"].startswith("PAGE_IMAGE_CHECKED")
        for s in secs(r["provision"]):
            reg.setdefault(s, {}); reg[s][iid] = reg[s].get(iid, False) or img
    for r in rows(AW / "ARMY-RULES-CHAIN-01" / "army_rules_instrument_register.csv"):
        iid = r["instr_id"]
        if iid == "AR-000" or not r["provisions_affected"] or "declaration" in r["nature"].lower(): continue
        if not r["evidence_level"].startswith(("IMAGE_CHECKED", "TEXT_LAYER")): continue
        img = r["evidence_level"].startswith("IMAGE_CHECKED")
        for s in secs(r["provisions_affected"]):
            reg.setdefault(s, {}); reg[s].setdefault(iid, img)
    return reg

def present(token, text):
    """Token-boundary match: 'AR-01' does not match inside 'AR-010'; 'S.O. 39' not inside 'S.O. 3912(E)'."""
    return re.search(r"(?<![A-Za-z0-9])" + re.escape(token) + r"(?![A-Za-z0-9])", text) is not None

def check(table, aa=None, ar=None):
    """aa/ar: optional injected registries {provision_number: {instrument_key: image_checked_bool}} (for fixtures)."""
    fails = []
    aa = registered_aa() if aa is None else aa
    ar = registered_ar() if ar is None else ar
    for r in rows(table):
        kind, prov = r["provision"].split(" ", 1)
        n = prov.split(".", 1)[1]
        reg = (aa if kind == "AA" else ar).get(n, {})
        loc = r["located_amending_instruments"]
        unexamined = [k for k, img in reg.items() if not img]
        for k in reg:
            if not present(k, loc): fails.append(f"C1 {r['provision']}: registered amendment '{k}' missing from located_amending_instruments")
        if unexamined:
            st = r["completeness_status"]
            if r["amendments_image_checked"].startswith("ALL"):
                fails.append(f"C2 {r['provision']}: amendments_image_checked=ALL but unexamined/text-only: {', '.join(sorted(unexamined))}")
            if st.startswith("ESTABLISHED") or (kind == "AA" and st.startswith("PARTIALLY_ESTABLISHED")):
                fails.append(f"C2 {r['provision']}: status '{st.split(' ')[0]}' rests on image-checked amendments but unexamined/text-only: {', '.join(sorted(unexamined))}")
    return fails

def selftest():
    import tempfile, os
    base = rows(HERE / "statutory_version_completeness_cycle3.csv"); cols = list(base[0].keys())
    def run(rs, aa=None, ar=None):
        fd, p = tempfile.mkstemp(suffix=".csv"); os.close(fd)
        with open(p, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rs)
        out = check(p, aa, ar); os.unlink(p); return out
    def fx(prov, loc, img, st):
        r = {c: "" for c in cols}
        r.update(provision=prov, located_amending_instruments=loc, amendments_image_checked=img, completeness_status=st); return r
    results = []
    def case(name, got_fail_prefixes, expect):
        ok = (expect == "PASS" and not got_fail_prefixes) or (expect != "PASS" and any(f.startswith(expect) for f in got_fail_prefixes))
        results.append((name, expect, ok)); return ok
    aa = registered_aa()
    none_sec = next(r for r in base if r["provision"].startswith("AA") and r["provision"].split(".", 1)[1] not in aa)
    img_only = next(r for r in base if r["provision"].startswith("AA") and aa.get(r["provision"].split(".", 1)[1]) and all(aa[r["provision"].split(".", 1)[1]].values()))
    # live-data boundary cases
    case(f"live: no registered amendment ({none_sec['provision']})", run([none_sec]), "PASS")
    case(f"live: only image-checked amendments, ALL ({img_only['provision']})", run([img_only]), "PASS")
    bad = dict(img_only); bad["located_amending_instruments"] = "none"
    case("live: registered instrument removed", run([bad]), "C1")
    # explicit fixtures (independent of live data)
    E = {}
    case("fixture: unexamined registration forced ALL -> C2", run([fx("AA s.999", "Act 1/2000 (fixture)", "ALL", "NOT_ESTABLISHED")], {"999": {"Act 1/2000": False}}, E), "C2")
    case("fixture: unexamined registration with PARTIALLY_ESTABLISHED (AA) -> C2", run([fx("AA s.999", "Act 1/2000", "NOT ALL", "PARTIALLY_ESTABLISHED (x)")], {"999": {"Act 1/2000": False}}, E), "C2")
    case("fixture: unexamined registration, NOT ALL, NOT_ESTABLISHED -> PASS", run([fx("AA s.999", "Act 1/2000", "NOT ALL", "NOT_ESTABLISHED")], {"999": {"Act 1/2000": False}}, E), "PASS")
    case("fixture: prefix ID 'AR-01' must NOT match 'AR-010' -> C1", run([fx("AR r.999", "AR-010 S.R.O. X", "ALL", "PARTIALLY_ESTABLISHED")], E, {"999": {"AR-01": True}}), "C1")
    case("fixture: exact ID 'AR-010' present -> PASS", run([fx("AR r.999", "AR-010 S.R.O. X", "ALL", "PARTIALLY_ESTABLISHED")], E, {"999": {"AR-010": True}}), "PASS")
    case("fixture: prefix key 'S.O. 39' must NOT match 'S.O. 3912(E)' -> C1", run([fx("AA s.999", "S.O. 3912(E) 2019", "NOT ALL", "NOT_ESTABLISHED")], {"999": {"S.O. 39": False}}, E), "C1")
    ok = all(r[2] for r in results)
    for name, exp, good in results: print(f"  selftest {'ok  ' if good else 'FAIL'} expect={exp:4} {name}")
    print("selftest", "PASS" if ok else "FAIL", f"({sum(r[2] for r in results)}/{len(results)} cases)")
    return ok

if __name__ == "__main__":
    t = HERE / "statutory_version_completeness_cycle3.csv"
    if "--table" in sys.argv: t = pathlib.Path(sys.argv[sys.argv.index("--table") + 1])
    f = check(t)
    for x in f: print("FAIL", x)
    print(f"rows_checked={len(rows(t))} failures={len(f)}")
    st = selftest() if "--selftest" in sys.argv else True
    sys.exit(1 if f or not st else 0)
