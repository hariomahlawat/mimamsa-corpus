#!/usr/bin/env python3
"""WS-D cycle 2, task 2: PROPOSED v4 citation-code register (new file; PILOT-01 v3 is never edited).

Root cause of stale v3 usage columns (defect D-WSD-001): the v2 inventory grammar recognised bracket
codes only as `[CODE: locator]` and had no leading-digest form (`SC_VK paras 9-13`). The v3 grammar
added bare `[CODE]` and leading forms; codes first found that way got new rows (inventory_source
v3-new), but rows carried from v2 kept their v2 `n_records`/`records_using`. 14 record links on 8
codes were therefore omitted.

This script recounts `n_records` and `records_using` for EVERY code from the frozen KB with the
committed v3 grammar (PILOT-01/build_code_inventory.py) and leaves every other column byte-for-byte
as in v3 (identity, class, evidence, URLs, hashes). Two columns are appended: `change_vs_v3` and
`usage_recount_basis`. It also writes a deterministic cell-level diff against v3.
No resolution class changes: 72 confirmed / 3 co-citation / 12 unresolved stay exactly as in v3.
Outputs: WS-D-QUALITY/registers/source_code_resolution_v4_proposed.csv and source_code_resolution_v4_diff.csv
"""
import csv, hashlib, importlib.util, io, re, sys
from pathlib import Path

WSD = Path(__file__).resolve().parents[1]
ROOT = WSD.parents[2]
P1 = ROOT / "legal_knowledge/audit_work/PILOT-01"
V3 = P1 / "registers/source_code_resolution_v3.csv"
V3_SHA = "40b18c3dfff3ad81c099118a0ee058c28db5255a8c4ba47d4391bd1685e8d944"
OUT = WSD / "registers"
# forms() vocabulary -> v3 `forms_used` vocabulary
FORMS_V3 = {"structured": "structured", "bracket_bare": "bracket", "bracket_with_locator": "bracket",
            "v_series": "pipe/inline", "leading": "leading", "sources_field": "sources_field"}


def forms(code, rec):
    ref = str(rec["references"]); f = []
    if re.search(r"'source_id': '%s'" % re.escape(code), ref): f.append("structured")
    for m in re.finditer(r"\[%s(?=([\]:\s]))" % re.escape(code), ref):
        f.append("bracket_with_locator" if m.group(1) == ":" else "bracket_bare")
    if re.search(r"\b%s\b" % re.escape(code), ref) and re.fullmatch(r"V\d-S\d+", code): f.append("v_series")
    if re.match(r"\s*%s\s+(?:paras?|discussion|Judgment|judgment)" % re.escape(code), ref): f.append("leading")
    if code in (rec.get("sources") or []): f.append("sources_field")
    return f


def build():
    raw = V3.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == V3_SHA, "frozen v3 register changed"
    spec = importlib.util.spec_from_file_location("bci", P1 / "build_code_inventory.py")
    bci = importlib.util.module_from_spec(spec); spec.loader.exec_module(bci)
    inv, _, _ = bci.inventory()
    import json
    kb = {json.loads(l)["id"]: json.loads(l) for l in bci.KB.read_text(encoding="utf-8").splitlines() if l.strip()}
    rd = csv.DictReader(io.StringIO(raw.decode("utf-8"), newline=""))
    cols = rd.fieldnames; v3 = list(rd)
    out, diff = [], []
    for r in v3:
        c = r["code"]; recs = sorted(inv[c])
        new = dict(r)
        new["n_records"] = str(len(recs)); new["records_using"] = ";".join(recs)
        old = set(filter(None, r["records_using"].split(";")))
        added = [x for x in recs if x not in old]
        removed = sorted(old - set(recs))
        if added or removed or r["n_records"] != str(len(recs)):
            why = sorted({f for x in added for f in forms(c, kb[x])})
            new["change_vs_v3"] = (f"USAGE_RECOUNTED: +{len(added)} ({', '.join(added)})" + (f" -{len(removed)} ({', '.join(removed)})" if removed else "")
                                   + f"; missed by v2 grammar form(s): {'/'.join(why)}")
        else:
            new["change_vs_v3"] = "UNCHANGED"
        new["usage_recount_basis"] = "PILOT-01/build_code_inventory.py v3 grammar over records_658.jsonl (sha 9a8f0d19...)"
        for k in ("n_records", "records_using"):
            if new[k] != r[k]:
                diff.append({"code": c, "column": k, "v3_value": r[k], "v4_value": new[k]})
        out.append(new)
    return cols + ["change_vs_v3", "usage_recount_basis"], out, diff


def write(path, cols, rows):
    buf = io.StringIO(); w = csv.DictWriter(buf, fieldnames=cols, lineterminator="\n"); w.writeheader(); w.writerows(rows)
    path.write_text(buf.getvalue(), encoding="utf-8")


def main():
    cols, rows, diff = build()
    OUT.mkdir(exist_ok=True)
    write(OUT / "source_code_resolution_v4_proposed.csv", cols, rows)
    write(OUT / "source_code_resolution_v4_diff.csv", ["code", "column", "v3_value", "v4_value"], diff)
    changed = [r["code"] for r in rows if r["change_vs_v3"] != "UNCHANGED"]
    print(f"codes={len(rows)} changed={len(changed)} {changed} diff_cells={len(diff)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
