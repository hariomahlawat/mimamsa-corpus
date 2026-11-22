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

def check(table):
    fails = []; aa, ar = registered_aa(), registered_ar()
    for r in rows(table):
        kind, prov = r["provision"].split(" ", 1)
        n = prov.split(".", 1)[1]
        reg = (aa if kind == "AA" else ar).get(n, {})
        loc = r["located_amending_instruments"]
        unexamined = [k for k, img in reg.items() if not img]
        for k in reg:
            token = k if kind == "AR" else k.replace("Act ", "Act ")
            if token not in loc: fails.append(f"C1 {r['provision']}: registered amendment '{k}' missing from located_amending_instruments")
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
    def run(rs):
        fd, p = tempfile.mkstemp(suffix=".csv"); os.close(fd)
        with open(p, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rs)
        out = check(p); os.unlink(p); return out
    aa = registered_aa()
    none_sec = next(r for r in base if r["provision"].startswith("AA") and r["provision"].split(".", 1)[1] not in aa)
    img_only = next(r for r in base if r["provision"].startswith("AA") and aa.get(r["provision"].split(".", 1)[1]) and all(aa[r["provision"].split(".", 1)[1]].values()))
    ok = True
    # boundary 1: section with no registered amendment -> no failure
    ok &= run([none_sec]) == []
    # boundary 2: section with only image-checked amendments, ALL -> no failure
    ok &= run([img_only]) == []
    # negative 1: drop the registered instrument from a row -> C1 failure
    bad = dict(img_only); bad["located_amending_instruments"] = "none"
    ok &= any(f.startswith("C1") for f in run([bad]))
    # negative 2: s.137 with an unexamined amendment marked ALL -> C2 failure
    s137 = dict(next(r for r in base if r["provision"] == "AA s.137")); s137["amendments_image_checked"] = "ALL"
    ok &= any(f.startswith("C2") for f in run([s137])) if any(not v for v in aa.get("137", {}).values()) else True
    print("selftest", "PASS" if ok else "FAIL", f"(no-amendment case: {none_sec['provision']}; image-only case: {img_only['provision']})")
    return ok

if __name__ == "__main__":
    t = HERE / "statutory_version_completeness_cycle3.csv"
    if "--table" in sys.argv: t = pathlib.Path(sys.argv[sys.argv.index("--table") + 1])
    f = check(t)
    for x in f: print("FAIL", x)
    print(f"rows_checked={len(rows(t))} failures={len(f)}")
    st = selftest() if "--selftest" in sys.argv else True
    sys.exit(1 if f or not st else 0)
