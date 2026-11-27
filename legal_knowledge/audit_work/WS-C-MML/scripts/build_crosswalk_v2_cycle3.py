#!/usr/bin/env python3
"""Versioned crosswalk (cycle 3): mml_provision_crosswalk_v2_cycle3.csv. Copies mml_provision_crosswalk.csv (unchanged)
and sets a per-row verification state from page-image locator checks:
  * renders made in cycle 3 (JSON from the private scratchpad, arg 1: xw_id -> render page + PNG sha), each viewed;
  * cycle-2 MML 2 heading checks (crosswalk_locator_verification.csv, WSC-PIC-54..108);
  * index corrections found on the image (arg 2: JSON).
Rows not checked stay REQUIRES_VERIFICATION (text-layer locator). The original crosswalk is not overwritten.
Stdlib. Usage: python3 build_crosswalk_v2_cycle3.py <c3_render.json> <c3_corrections.json>"""
import csv, json, sys
from pathlib import Path

W = Path(__file__).resolve().parent.parent
REN = {o["xw_id"]: o for o in json.load(open(sys.argv[1])) if "render_sha" in o}
COR = json.load(open(sys.argv[2]))
lv = {r["provision"]: r for r in csv.DictReader(open(W / "crosswalk_locator_verification.csv", encoding="utf-8"))}
SRC = {"MML 2.pdf": "ORIGINAL_PDF_PAGE", "MML vol 2(AA).pdf": "ORIGINAL_PDF_PAGE"}
rows = list(csv.DictReader(open(W / "mml_provision_crosswalk.csv", encoding="utf-8")))
out = []
for r in rows:
    r = dict(r); r.pop("verification_state", None)
    x = r["xw_id"]
    r.update(verification_state="REQUIRES_VERIFICATION (text-layer locator)", evidence_level="TEXT_LAYER_LOCATOR",
             render_source="", render_page="", render_dpi="", render_png_sha256="", corrected_locator="", check_note="")
    if x in COR:
        c = COR[x]
        r.update(verification_state="LOCATOR_CORRECTED_IMAGE_CHECKED", evidence_level="IMAGE_CHECKED",
                 render_source=c["render_source"], render_page=str(c["page"]), render_dpi="110", render_png_sha256=c["sha"],
                 corrected_locator=c["corrected_locator"], check_note=c["note"])
    elif x in REN:
        o = REN[x]
        r.update(verification_state="LOCATOR_IMAGE_CHECKED", evidence_level="IMAGE_CHECKED",
                 render_source=SRC.get(r["mml_file"], "LIBREOFFICE_RENDER_OF_NATIVE_DOC_TEXT"),
                 render_page=str(o["render_page"]), render_dpi="110", render_png_sha256=o["render_sha"],
                 check_note="cycle 3: heading/paragraph start viewed on render; wording not relied on")
    elif r["mml_file"] == "MML 2.pdf" and r["provision"] in lv:
        L = lv[r["provision"]]; sha = L["heading_render"].split("sha ")[-1]
        r.update(verification_state="LOCATOR_IMAGE_CHECKED", evidence_level="IMAGE_CHECKED",
                 render_source="ORIGINAL_PDF_PAGE", render_page=L["index_locator"].replace("PDF p.", ""), render_dpi="150",
                 render_png_sha256=sha, check_note=f"cycle 2 {L['lv_id']}")
    out.append(r)
with open(W / "mml_provision_crosswalk_v2_cycle3.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
from collections import Counter
print(Counter(r["verification_state"] for r in out), Counter((r["mml_file"], r["verification_state"][:8]) for r in out if r["verification_state"].startswith("LOC")))
