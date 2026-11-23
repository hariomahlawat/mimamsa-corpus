"""CALIBRATION-02 rule-sensitivity disclosure (stdlib, deterministic).

reconcile.py was revised after the reviews were seen (coordinator QC-07, then independent technical review). To make
that visible, this runs the frozen pre-registered rule (reconcile_preregistered_3af63ee3.py, verbatim from commit 3af63ee3)
on the same propositions and findings, in a temporary copy, and writes reconciliation/rule_sensitivity.json comparing its
headline figures with the final rule's scorecard.json. Neither result is a legal determination."""
import json, shutil, subprocess, sys, tempfile
from pathlib import Path

C2 = Path(__file__).resolve().parents[1]
KEYS = ["record_classification", "proposition_agreement", "disagreements", "correction_proposals_by_support", "findings_by_severity"]


def main():
    with tempfile.TemporaryDirectory() as t:
        base = Path(t) / "CALIBRATION-02"
        (base / "tools").mkdir(parents=True)
        shutil.copy(C2 / "tools/reconcile_preregistered_3af63ee3.py", base / "tools/reconcile.py")
        shutil.copy(C2 / "propositions.csv", base / "propositions.csv")
        shutil.copytree(C2 / "reviews", base / "reviews")
        subprocess.run([sys.executable, str(base / "tools/reconcile.py")], check=True, capture_output=True)
        pre = json.loads((base / "reconciliation/scorecard.json").read_text(encoding="utf-8"))
    fin = json.loads((C2 / "reconciliation/scorecard.json").read_text(encoding="utf-8"))
    out = {"pre_registered_rule": "tools/reconcile_preregistered_3af63ee3.py (commit 3af63ee3, before any review was seen)",
           "final_rule": "tools/reconcile.py",
           "pre_registered": {k: pre.get(k) for k in KEYS},
           "final": {k: fin.get(k) for k in KEYS + ["severity_splits_escalated"]},
           "changes_and_reasons": [
               "Disagreement made dimension-aware: a reviewer silent in another dimension is not a dissenter; but a reviewer that classes the proposition as not a legal proposition IS a dissenter (technical review P2).",
               "Severity splits escalated for corroborated defects too, including the only P1 (technical review P2).",
               "A VERIFIED row counts against a negative finding only if it verified the proposition as stated (severity NONE).",
               "CONTRADICTORY_EVIDENCE between sources is a source conflict (SOURCE_CONFLICT_OPEN), taking precedence over DISPUTED.",
               "EVIDENCE_SUPPORTED split into PRIMARY_EVIDENCE_SUPPORTED and SECONDARY_EVIDENCE_ONLY (technical review P2).",
               "NOT_YET_REVIEWED (out of a reviewer's scope) is not a source gap; FULLY_EVIDENCE_SUPPORTED additionally requires that no reviewer recorded INTERPRETATION_REQUIRES_LEGAL_ADVICE, UNSUPPORTED, CONTRADICTORY_EVIDENCE, SOURCE_NOT_HELD or HISTORICAL_VERSION_UNRESOLVED."],
           "note": "Readers should treat record-classification and agreement figures as rule-dependent; both rule outputs are disclosed."}
    (C2 / "reconciliation/rule_sensitivity.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"pre": out["pre_registered"]["record_classification"], "final": out["final"]["record_classification"]}))


if __name__ == "__main__":
    main()
