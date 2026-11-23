"""C6-01 versioned authentication addendum: DRAFT plan (deterministic; nothing is incorporated).

Reads the committed C6-01 proposals and recovery register, the Cycle 4 register (CALIBRATION-02) and the Cycle 5
registers, and writes addendum/authentication_addendum_v1_draft.csv: one row per proposal with the existing source
and copy, the original authentication status, the exact evidence, the proposed status and class, the justification,
the limitations, the effect on the Cycle 5 crosswalk of that entry alone, and a reviewer/owner decision field that
is always PENDING here. The Cycle 4 register is never edited; incorporation is a separate, owner-approved change.
`--check` verifies the committed output."""
import argparse, csv, io, json, sys
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
AW = PKG.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_provenance as P  # noqa: E402

COLS = ["addendum_entry_id", "proposal_id", "sha256", "source_id", "copy_id", "document_identity", "original_c5_holding_state",
        "original_c4_register_state", "provenance_evidence_refs", "locator_strength", "identity_evidence_refs",
        "proposed_authentication_state", "proposed_effective_source_class", "primary_or_non_primary", "justification",
        "limitations", "crosswalk_effect_this_entry_alone", "reviewer_decision", "owner_decision", "decision_record_ref"]


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

    def from_dir(c2, root=None):
        e = orig_from_dir(c2, root)
        e.register.setdefault(prop["sha256"], prop)
        return e
    EC.Evidence.from_dir = classmethod(lambda cls, c2, root=None: from_dir(c2, root))
    B.check_holding_vs_copies = lambda m, c: None
    try:
        sim = {key(r): r["evidence_status"] for r in csv.DictReader(io.StringIO(B.build()["corpus_crosswalk.csv"]))}
    finally:
        EC.Evidence.from_dir, B.check_holding_vs_copies = orig_from_dir, orig_check
    ch = sorted(f"{k[3] or k[2]}: {base.get(k, 'ABSENT')} -> {v}" for k, v in sim.items() if base.get(k) != v)
    return "; ".join(ch) or "none (no crosswalk row changes)"


def build():
    props = read(PKG / "registers/source_authentication_proposals.csv")
    rec = {r["sha256"]: r for r in read(PKG / "registers/provenance_recovery_register.csv")}
    c4 = {r["sha256"] for r in read(AW / "CALIBRATION-02/registers/source_authentication_register.csv")}
    rows = []
    for i, p in enumerate(sorted(props, key=lambda p: (rec[p["sha256"]]["source_id"], p["sha256"])), 1):
        r = rec[p["sha256"]]
        assert p["sha256"] not in c4, "an addendum entry must not duplicate a Cycle 4 register row"
        cls = p["effective_source_class"]
        rows.append({
            "addendum_entry_id": f"C6-ADD-v1-{p['sha256'][:8]}", "proposal_id": p["proposal_id"], "sha256": p["sha256"],
            "source_id": r["source_id"], "copy_id": r["copy_id"], "document_identity": p["document_identity"],
            "original_c5_holding_state": r["current_authentication_status"].split(" / ")[0],
            "original_c4_register_state": "NO_ROW (copy absent from the Cycle 4 register)",
            "provenance_evidence_refs": "; ".join(x for x in r["evidence_items"].split(" | ") if x.split(":")[0] in ("L1", "L2", "L3", "L4", "L5", "L6", "WSB")),
            "locator_strength": r["locator_strength"],
            "identity_evidence_refs": r["identity_verification"],
            "proposed_authentication_state": p["authentication_state"], "proposed_effective_source_class": cls,
            "primary_or_non_primary": "NON_PRIMARY" if cls.startswith("NON_PRIMARY") else "PRIMARY",
            "justification": "FULL-strength locator (" + p["provenance_evidence"] + "); no contradiction in the searched registers; "
                             + ("non-primary class proposed by C6-01; the Cycle 4 register has no NON_PRIMARY_* class (see limitations)"
                                + ("; class reserved for owner decision (final review R-04)" if r["source_id"] in P.WATERMARKED_GAZETTE_REHOSTS else "")
                                if cls.startswith("NON_PRIMARY") else "class follows the Cycle 4 class for the same carrier type"),
            "limitations": p["limitations"],
            "crosswalk_effect_this_entry_alone": crosswalk_effect(p),
            "reviewer_decision": "PENDING (C6-01 final review covers the proposal; an addendum-specific review is required before incorporation)",
            "owner_decision": "PENDING (not approved)", "decision_record_ref": "",
        })
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
