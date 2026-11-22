"""Deterministic cross-reference check for ARMY-RULES-CHAIN-01 and ACQ-02 (stdlib only). Exit 1 on any error."""
import csv, re, sys, pathlib
B = pathlib.Path(__file__).resolve().parent.parent
def rows(p): return list(csv.DictReader(open(B / p, newline="", encoding="utf-8")))
err = []
reg = rows("ARMY-RULES-CHAIN-01/army_rules_instrument_register.csv")
ids = {r["instr_id"] for r in reg}
if len(ids) != len(reg): err.append("duplicate instr_id")
chron = rows("ARMY-RULES-CHAIN-01/army_rules_provision_chronology.csv")
for r in chron:
    if r["instrument_id"] and r["instrument_id"] not in ids: err.append(f"chronology -> unknown {r['instrument_id']}")
pics = {r["check_id"] for r in rows("ACQ-02/page_image_checks_acq02.csv")} | {r["check_id"] for r in rows("R23-VERIFY-01/registers/page_image_checks.csv")} | {r["check_id"] for r in rows("PILOT-01/registers/page_image_checks.csv")}
inv = rows("ACQ-02/supplement_inventory.csv")
for r in inv:
    for k in ("sha256", "md5"):
        n = 64 if k == "sha256" else 32
        if not re.fullmatch(f"[0-9a-f]{{{n}}}", r[k]): err.append(f"{r['supp_id']} bad {k}")
    if r["archive_md5_ok"] != "True" or r["archive_size_ok"] != "True": err.append(f"{r['supp_id']} archive check not True")
    if r["page_image_check_id"].split()[0] not in pics: err.append(f"{r['supp_id']} PIC missing")
    if not r["in_PR8_pinned_list"].startswith("NO"): err.append(f"{r['supp_id']} must be outside PR #8 list")
invsha = {r["sha256"] for r in inv}
for r in reg:
    for pid in re.findall(r"PIC-\d+", r["evidence_locator"]):
        if pid not in pics: err.append(f"{r['instr_id']} cites unknown {pid}")
    s = r["sha256"][:64]
    if r["evidence_level"].startswith("IMAGE_CHECKED") and not re.fullmatch(r"[0-9a-f]{64}", s): err.append(f"{r['instr_id']} image-checked without full sha256")
    if "ACQ02" in r["evidence_locator"] and s not in invsha: err.append(f"{r['instr_id']} sha256 not in ACQ-02 inventory")
    if r["evidence_level"].startswith(("TEXT_LAYER", "HINT", "NOT_")) and r["status"] == "LOCATED": err.append(f"{r['instr_id']} OCR/hint row marked LOCATED")
ver = rows("ARMY-RULES-CHAIN-01/statutory_version_register_seed.csv")
for r in ver:
    if r["provision"].startswith("r.23(3)") and r["determination_state"] != "CONFLICTING": err.append("r.23(3) must stay CONFLICTING")
    if r["provision"] == "r.194" and r["version"] == "v1989" and not r["determination_state"].startswith("PROPOSAL"): err.append("r.194 must stay PROPOSAL")
    if r["provision"] == "r.193" and r["version"] == "v1987" and not r["determination_state"].startswith("OPEN"): err.append("r.193 must stay OPEN")
    if "APPROVED" in r["determination_state"].upper(): err.append(f"{r['provision']} claims approval")
print(f"instruments={len(reg)} chronology={len(chron)} acq02={len(inv)} versions={len(ver)} pics_known={len(pics)} errors={len(err)}")
for e in err: print("ERROR", e)
sys.exit(1 if err else 0)
