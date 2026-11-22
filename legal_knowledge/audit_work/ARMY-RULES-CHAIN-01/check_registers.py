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
pics = {r["check_id"] for r in rows("ACQ-02/page_image_checks_acq02.csv")} | {r["check_id"] for r in rows("R23-VERIFY-01/registers/page_image_checks.csv")} | {r["check_id"] for r in rows("PILOT-01/registers/page_image_checks.csv")} | {r["check_id"] for r in rows("ARMY-RULES-CHAIN-01/page_image_checks_chain.csv")}
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
    for pid in re.findall(r"(?<![A-Za-z-])PIC-\d+", r["evidence_locator"]):
        if pid not in pics: err.append(f"{r['instr_id']} cites unknown {pid}")
    s = r["sha256"][:64]
    if r["evidence_level"].startswith("IMAGE_CHECKED") and not re.fullmatch(r"[0-9a-f]{64}", s): err.append(f"{r['instr_id']} image-checked without full sha256")
    if "ACQ02" in r["evidence_locator"] and s not in invsha: err.append(f"{r['instr_id']} sha256 not in ACQ-02 inventory")
    if r["evidence_level"].startswith(("TEXT_LAYER", "HINT", "NOT_")) and r["status"] == "LOCATED": err.append(f"{r['instr_id']} OCR/hint row marked LOCATED")
# dates: publication, commencement and effective date are distinct; effective date only when stated in the instrument
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
for name, data, key in (("register", reg, "instr_id"), ("chronology", chron, "provision")):
    for r in data:
        eff, st = r.get("effective_date", ""), r.get("effective_date_status", "")
        if not st: err.append(f"{name} {r[key]}: missing effective_date_status")
        if eff and not st.startswith("STATED_IN_INSTRUMENT"): err.append(f"{name} {r[key]}: effective_date set without a stated commencement")
        if st.startswith("STATED_IN_INSTRUMENT") and not DATE.fullmatch(eff): err.append(f"{name} {r[key]}: stated commencement but no effective_date")
        if eff and DATE.fullmatch(eff) is None: err.append(f"{name} {r[key]}: bad effective_date")
        # a retrospective deemed effect stated in the instrument is kept apart from commencement (effective_date)
        dm = r.get("retrospective_deemed_effect_from", "")
        if dm:
            if DATE.fullmatch(dm) is None: err.append(f"{name} {r[key]}: bad retrospective_deemed_effect_from")
            elif not st.startswith("STATED_IN_INSTRUMENT") or not DATE.fullmatch(eff): err.append(f"{name} {r[key]}: deemed effect without a stated commencement")
            elif dm >= eff: err.append(f"{name} {r[key]}: deemed effect not earlier than commencement")
for r in reg:
    if r["evidence_level"] == "IMAGE_CHECKED" and not r.get("continuation_pages_status", "").startswith("ALL_IMAGE_CHECKED"):
        err.append(f"{r['instr_id']}: IMAGE_CHECKED but continuation pages not all image-checked")
    if r["evidence_level"].startswith("TEXT_LAYER") and "REQUIRES_VERIFICATION" not in r.get("continuation_pages_status", ""):
        err.append(f"{r['instr_id']}: text-layer row not marked REQUIRES_VERIFICATION")
ver = rows("ARMY-RULES-CHAIN-01/statutory_version_register_seed.csv")
for r in ver:
    if r["effective_date"] and not r["effective_date_status"].startswith("STATED_IN_INSTRUMENT"): err.append(f"version {r['provision']} {r['version']}: effective_date without stated commencement")
    if r["provision"].startswith("r.193") and r["conflict_id"] != "C-08": err.append("r.193 rows must carry C-08")
    if r["provision"].startswith("r.194") and r["conflict_id"] != "C-09": err.append("r.194 rows must carry C-09")
    if r["provision"] == "r.193" and r["determination_state"].split()[0] != "OPEN": err.append("r.193 must stay OPEN")
    # OQ-D-021: guard every version row of the three disputed provisions, not only the latest
    if r["provision"] in ("r.23(3)", "r.193", "r.194") and r["determination_state"].split()[0] not in ("OPEN", "PROPOSAL", "CONFLICTING"):
        err.append(f"{r['provision']} {r['version']}: state must be OPEN, PROPOSAL or CONFLICTING")
for r in ver:
    if r["provision"].startswith("r.23(3)") and r["determination_state"] != "CONFLICTING": err.append("r.23(3) must stay CONFLICTING")
    if r["provision"] == "r.194" and r["version"] == "v1989" and not r["determination_state"].startswith("PROPOSAL"): err.append("r.194 must stay PROPOSAL")
    if "APPROVED" in r["determination_state"].upper(): err.append(f"{r['provision']} claims approval")
print(f"instruments={len(reg)} chronology={len(chron)} acq02={len(inv)} versions={len(ver)} pics_known={len(pics)} errors={len(err)}")
for e in err: print("ERROR", e)
sys.exit(1 if err else 0)
