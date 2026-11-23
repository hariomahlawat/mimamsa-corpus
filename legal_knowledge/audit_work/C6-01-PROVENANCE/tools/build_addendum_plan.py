"""C6-01 versioned authentication addendum: DRAFT plan (deterministic; nothing is incorporated).

Reads the committed C6-01 proposals and recovery register, the Cycle 4 register (CALIBRATION-02) and the Cycle 5
registers, and writes addendum/authentication_addendum_v1_draft.csv: one row per proposal with the existing source
and copy, the original authentication status, the exact evidence, the proposed status and class, the justification,
the limitations, the effect on the Cycle 5 crosswalk of that entry alone, and a reviewer/owner decision field that
is always PENDING here. The Cycle 4 register is never edited; incorporation is a separate, owner-approved change.
`--check` verifies the committed output."""
import argparse, csv, io, json, re, sys
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
AW = PKG.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_provenance as P  # noqa: E402

SCHEMA = json.loads((PKG / "addendum/addendum_entry.schema.json").read_text(encoding="utf-8"))
COLS = SCHEMA["required"]


def read(p):
    with open(p, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def crosswalk_effect(prop):
    """Cases/KB items whose crosswalk evidence_status changes when ONLY this proposal is simulated."""
    sys.path.insert(0, str(AW / "SOURCE-LIBRARY-C5/tools"))
    import build_registers as B
    EC = B.EC
    key = lambda r: (r["source_id"], r["provision_id"], r["knowledge_base_record_id"], r["case_id"], r["relationship_type"])
    base = {key(r): r["evidence_status"] for r in csv.DictReader(io.StringIO(B.build()["corpus_crosswalk.csv"]))}
    orig_from_dir, orig_check = EC.Evidence.from_dir, B.check_holding_vs_copies
    orig_descriptor = EC.Evidence.__dict__["from_dir"]

    def from_dir(c2, root=None):
        e = orig_from_dir(c2, root)
        e.register.setdefault(prop["sha256"], prop)
        return e
    EC.Evidence.from_dir = classmethod(lambda cls, c2, root=None: from_dir(c2, root))
    B.check_holding_vs_copies = lambda m, c: None
    try:
        sim = {key(r): r["evidence_status"] for r in csv.DictReader(io.StringIO(B.build()["corpus_crosswalk.csv"]))}
    finally:
        EC.Evidence.from_dir = orig_descriptor
        B.check_holding_vs_copies = orig_check
    ch = sorted(f"{k[3] or k[2]}: {base.get(k, 'ABSENT')} -> {v}" for k, v in sim.items() if base.get(k) != v)
    return "; ".join(ch) or "none (no crosswalk row changes)"


def resolves(ref):
    """'<audit_work-relative path>#<row key>' must name an existing committed file containing that key (Fable F-08)."""
    path, _, key = ref.partition("#")
    key = key.replace(" (locator)", "").split("/")[0].strip()
    f = AW / path
    return f.is_file() and (not key or key in f.read_text(encoding="utf-8", errors="replace"))


def validate(rows):
    errs = []
    req = SCHEMA["required"]
    for r in rows:
        for k in req:
            if r.get(k) is None:
                errs.append(f"{r.get('entry_id')}: missing {k}")
        for k, spec in SCHEMA["properties"].items():
            v = r.get(k, "")
            if "enum" in spec and v not in spec["enum"]:
                errs.append(f"{r['entry_id']}: {k}={v!r} not in schema enum")
            if "pattern" in spec and not re.fullmatch(spec["pattern"], v):
                errs.append(f"{r['entry_id']}: {k} does not match {spec['pattern']}")
        refs = [x.split(":", 1)[1] for x in (r["evidence_refs"] + "; " + r["identity_refs"]).split("; ") if ":" in x]
        for ref in refs + [r["first_class_record_ref"]]:
            if not resolves(ref):
                errs.append(f"{r['entry_id']}: unresolvable ref {ref}")
        if r["owner_decision"] == "APPROVED" and not (r["entry_status"] == "APPROVED" and r["decision_record_ref"] and r["reviewer_ref"]):
            errs.append(f"{r['entry_id']}: APPROVED without decision record and reviewer ref")
    if len({r["sha256"] for r in rows}) != len(rows):
        errs.append("duplicate sha256 in addendum")
    return errs


def build():
    props = read(PKG / "registers/source_authentication_proposals.csv")
    rec = {r["sha256"]: r for r in read(PKG / "registers/provenance_recovery_register.csv")}
    c4 = {r["sha256"] for r in read(AW / "CALIBRATION-02/registers/source_authentication_register.csv")}
    rows = []
    for p in sorted(props, key=lambda p: (rec[p["sha256"]]["source_id"], p["sha256"])):
        r = rec[p["sha256"]]
        if p["sha256"] in c4:
            raise SystemExit("an ADD entry must not duplicate a Cycle 4 register row (use CORRECTION)")
        cls = p["effective_source_class"]
        withheld = p["proposal_status"].startswith("WITHHELD")
        items = [x for x in r["evidence_items"].split(" | ") if x]
        # first-class record: a locator record whose own sha256 is this copy's (L1/L3/L4/L2 rows are keyed by this sha; '(locator)' mentions are not)
        first = [x.split(":", 1)[1] for x in items if x.split(":")[0] in ("L3", "L1", "L4", "L2") and "(locator)" not in x]
        rows.append({
            "entry_id": f"C6-ADD-v1-{p['sha256'][:8]}", "entry_version": "v1", "entry_type": "ADD", "sha256": p["sha256"],
            "proposal_id": p["proposal_id"], "source_id": r["source_id"], "copy_id": r["copy_id"], "document_identity": p["document_identity"],
            "prior_effective_state": "C4: NO_ROW; C5 holding_state: " + r["current_authentication_status"].split(" / ")[0],
            "evidence_refs": "; ".join(x for x in items if x.split(":")[0] in ("L1", "L2", "L3", "L4", "L5", "L6", "WSB")),
            "first_class_record_ref": first[0] if first else "",
            "locator_strength": r["locator_strength"], "identity_refs": r["identity_verification"],
            "proposed_authentication_state": p["authentication_state"], "proposed_class": cls,
            "primary_or_non_primary": "NON_PRIMARY" if cls.startswith("NON_PRIMARY") else "PRIMARY",
            "justification": "FULL-strength locator (" + p["provenance_evidence"] + "); no contradiction in the searched registers; "
                             + ("non-primary class proposed by C6-01 (no Cycle 4 NON_PRIMARY_* class exists; see limitations); class reserved for owner decision"
                                if cls.startswith("NON_PRIMARY") else "class follows the Cycle 4 class for the same carrier type"),
            "limitations": p["limitations"],
            "crosswalk_effect_this_entry_alone": "not simulated (WITHHELD)" if withheld else crosswalk_effect(p),
            "entry_status": "WITHHELD" if withheld else "DRAFT", "reviewer_decision": "PENDING", "reviewer_ref": "",
            "owner_decision": "WITHHELD" if withheld else "PENDING", "decision_record_ref": "",
        })
    errs = validate(rows)
    if errs:
        raise SystemExit("addendum draft invalid:\n" + "\n".join(errs))
    return rows


def text():
    b = io.StringIO()
    w = csv.DictWriter(b, fieldnames=COLS, lineterminator="\n")
    w.writeheader()
    w.writerows(build())
    return b.getvalue()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    out = PKG / "addendum/authentication_addendum_v1_draft.csv"
    t = text()
    if a.check:
        ok = out.exists() and out.read_text(encoding="utf-8") == t
        print("OK" if ok else "STALE: addendum/authentication_addendum_v1_draft.csv")
        return 0 if ok else 1
    out.parent.mkdir(exist_ok=True)
    out.write_text(t, encoding="utf-8")
    print(f"entries={t.count(chr(10)) - 1}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
