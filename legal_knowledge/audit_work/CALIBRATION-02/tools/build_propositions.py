"""CALIBRATION-02: deterministic segmentation of the 46 CALIBRATION-01 records into reviewable propositions.

Input (read-only): COORDINATION/CALIBRATION-01/calibration_package.csv (the authoritative sample, unchanged) and
curated_originals/knowledge_base/v0.9/records_658.jsonl (immutable). Output: CALIBRATION-02/propositions.csv.
Each record's body is split into sentences (stable IDs <record>#P<n>); the 'references' field is one extra
proposition <record>#REF. Original text is copied verbatim. Stdlib only; byte-identical on re-run."""
import csv, hashlib, json, re, sys
from pathlib import Path

AW = Path(__file__).resolve().parents[2]
ROOT = AW.parents[1]
KB = ROOT / "legal_knowledge/curated_originals/knowledge_base/v0.9/records_658.jsonl"
CAL = AW / "COORDINATION/CALIBRATION-01/calibration_package.csv"
OUT = AW / "CALIBRATION-02/propositions.csv"
KB_SHA = "9a8f0d193065762ffa987116dc761bcb734008d2a87a946f5591741f5befcfc1"
SPLIT = re.compile(r"(?<=[.;:!?])\s+(?=[A-Z(\[\"'])")


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main(out=OUT):
    if sha(KB) != KB_SHA:
        sys.exit("records_658 hash mismatch")
    kb = {json.loads(l)["id"]: json.loads(l) for l in KB.read_text(encoding="utf-8").splitlines() if l.strip()}
    cal = list(csv.DictReader(CAL.open(newline="", encoding="utf-8")))
    if len(cal) != 46:
        sys.exit("calibration sample must have 46 records")
    rows = []
    for c in cal:
        r = kb[c["record_id"]]
        rec_sha = hashlib.sha256(json.dumps(r, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        parts = [s.strip() for s in SPLIT.split(" ".join(r["body"].split())) if s.strip()]
        for n, s in enumerate(parts, 1):
            rows.append([c["rank"], c["record_id"], f"{c['record_id']}#P{n}", "body_sentence", s, r["module"], r["title"], r["kind"], r["status"], rec_sha])
        rows.append([c["rank"], c["record_id"], f"{c['record_id']}#REF", "references", r.get("references", ""), r["module"], r["title"], r["kind"], r["status"], rec_sha])
    with Path(out).open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["calibration_rank", "record_id", "proposition_id", "proposition_kind", "text_verbatim", "module", "title", "kind", "status_as_recorded", "record_canonical_sha256"])
        w.writerows(rows)
    print(f"records={len(cal)} propositions={len(rows)} kb_sha256={KB_SHA}")


if __name__ == "__main__":
    main(*(sys.argv[1:2]))
