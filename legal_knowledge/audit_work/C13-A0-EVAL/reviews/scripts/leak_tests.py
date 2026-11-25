import sys, csv, io, os, collections
T = sys.argv[1]; sys.path.insert(0, T); import c13_coding as K
pkt = sys.argv[2]; out = sys.argv[3]
rows = list(csv.DictReader(open(pkt))); cols = list(rows[0].keys())
def w(name, rs, cs):
    p = os.path.join(out, name)
    with open(p, "w", newline="") as f:
        d = csv.DictWriter(f, fieldnames=cs, lineterminator="\n"); d.writeheader(); [d.writerow(r) for r in rs]
    return p
def res(fn):
    try: r = fn(); return f"PASS({r if not isinstance(r, tuple) else len(r[1])} errs)"
    except K.LeakError as e: return f"LEAK_DETECTED: {str(e)[:110]}"
    except Exception as e: return f"ERROR {type(e).__name__}: {e}"
txt = lambda rs, cs: (lambda s: (csv.DictWriter(s, fieldnames=cs, lineterminator="\n").writeheader(), [csv.DictWriter(s, fieldnames=cs, lineterminator="\n").writerow(r) for r in rs], s.getvalue())[-1])(io.StringIO())
print("B0 clean blank:", res(lambda: K.check_blank_sheet_text(open(pkt).read(), "outcome")))
print("B1 blank with model label prefilled:", res(lambda: K.check_blank_sheet_text(txt([dict(rows[0], printed_disposal="dismissed")] + rows[1:], cols), "outcome")))
print("B2 blank with model label in notes:", res(lambda: K.check_blank_sheet_text(txt([dict(rows[0], notes="V4 says dismissed")] + rows[1:], cols), "outcome")))
print("B3 blank with extra column model_output:", res(lambda: K.check_blank_sheet_text(txt([dict(r, model_output="dismissed") for r in rows], cols + ["model_output"]), "outcome")))
print("B4 blank with extra column 'hint':", res(lambda: K.check_blank_sheet_text(txt([dict(r, hint="dismissed") for r in rows], cols + ["hint"]), "outcome")))
fill = dict(coder_id="C1", proceeding="WP 1/2020", printed_disposal="dismissed", substantive_result="relief_refused", final_or_interim="final", page="2", confidence="high")
done = [dict(r, **fill) for r in rows]; cc = ["coder_id"] + cols
p = w("ok.csv", done, cc)
print("C0 clean completed:", res(lambda: K.check_completed_sheet(p, "outcome", "C1", pkt, ["C2"])))
p = w("c1.csv", [dict(done[0], notes="per C2: dismissed")] + done[1:], cc)
print("C1 other coder named in notes:", res(lambda: K.check_completed_sheet(p, "outcome", "C1", pkt, ["C2"])))
p = w("c2.csv", [dict(done[0], notes="AUTOMATED_CANDIDATE_NOT_VERIFIED extractor V4 output: dismissed")] + done[1:], cc)
print("C2 model output pasted in notes:", res(lambda: K.check_completed_sheet(p, "outcome", "C1", pkt, ["C2"])))
p = w("c3.csv", [dict(done[0], proceeding="OUTCOME_UNVERIFIED")] + done[1:], cc)
print("C3 model token in proceeding:", res(lambda: K.check_completed_sheet(p, "outcome", "C1", pkt, ["C2"])))
p = w("c4.csv", [dict(r, model_pred="dismissed") for r in done], cc + ["model_pred"])
print("C4 extra model_pred column:", res(lambda: K.check_completed_sheet(p, "outcome", "C1", pkt, ["C2"])))
p = w("c5.csv", done, cc)
print("C5 other coder's labels copied verbatim, unnamed (expected undetectable):", res(lambda: K.check_completed_sheet(p, "outcome", "C1", pkt, ["C2"])))
p = w("c6.csv", done, cc)
print("C6 no --other-coder given:", res(lambda: K.check_completed_sheet(p, "outcome", "C1", pkt, [])))
# adjudication
a = [dict(item_id=r["item_id"], coder_id="CODER-ONE", proceeding="WP 1/2020", printed_disposal="dismissed", substantive_result="relief_refused", final_or_interim="final", page="2", confidence="high", excerpt="x", notes="") for r in rows[:200]]
b = [dict(x, coder_id="CODER-TWO", printed_disposal=("allowed" if i % 2 else x["printed_disposal"])) for i, x in enumerate(a)]
items, summ = K.agreement("outcome", a, b)
sheet, key = K.adjudication_sheet("outcome", a, b, items)
kr = list(csv.DictReader(io.StringIO(key)))
print("A1 adjsheet names coders?:", "CODER-ONE" in sheet or "CODER-TWO" in sheet, "| X=A share:", round(sum(r["X"] == "A" for r in kr) / len(kr), 2), "n", len(kr))
print("A2 check_adjudication_sheet_text clean:", res(lambda: K.check_adjudication_sheet_text(sheet, {"CODER-ONE", "CODER-TWO"})))
bad = sheet.replace("relief_refused", "relief_refused CODER-ONE", 1)
print("A3 coder name injected:", res(lambda: K.check_adjudication_sheet_text(bad, {"CODER-ONE", "CODER-TWO"})))
# can X/Y be recomputed from public seed?
import hashlib
rec = all((int(hashlib.sha256(f"mimamsa-c13-adjudication|xy|{r['item_id']}".encode()).hexdigest()[0], 16) < 8) == (r["X"] == "A") for r in kr)
print("A4 X/Y key recomputable from public seed in code:", rec)
print("AGREE summary:", {k: summ[k] for k in ("items", "items_agree", "strict_item_agreement", "strict_unit_agreement")}, summ["fields"]["printed_disposal"])
