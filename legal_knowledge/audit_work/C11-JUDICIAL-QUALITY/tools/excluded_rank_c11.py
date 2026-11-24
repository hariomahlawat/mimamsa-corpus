#!/usr/bin/env python3
"""C11: rank the excluded-judgment log for owner consideration of re-acquisition (no acquisition is made).

Facts from the log itself: the crawler read each excluded judgment's text and excluded it because none of ten phrases
appeared (army act, air force act, navy act, armed forces tribunal, court martial, summary of evidence, disability
pension, entitlement rules, invalided, release medical board). Service matters that never use those phrases (posting,
promotion, ACR, recruitment, defence civilian employment, defence land) can therefore be missed; titles are the only
remaining evidence. Every entry carries sha256 and source_url, so a re-acquired copy is verifiable byte-for-byte.

Tiers (title rules, fixed; a tier is a lead, never a relevance finding):
  T1 military forum or military service party (AFT, court martial, ex-servicemen, Army/Navy/Air Force/military bodies
     or Chief of Army/Naval/Air Staff, rank-titled officer against Union/MoD)
  T2 Ministry of Defence / defence department party without land terms (service of defence civilians, contracts)
  T3 defence land: Defence Estates, cantonment, military land, MES/works
  T4 central armed police forces (BSF, CRPF, ITBP, CISF, SSB, Assam Rifles, NSG): outside current scope, kept separate
  T5 other flagged titles (weak signal)
  NOT_FLAGGED  not in the C10 re-screen candidates (not listed in the manifest; counted only)
  python -I -B excluded_rank_c11.py --repo <full clone> [--check]
"""
import argparse, csv, gzip, hashlib, io, json, re, subprocess, sys
from collections import Counter
from pathlib import Path
HERE = Path(__file__).resolve().parent
PKG = HERE.parent
OUT = PKG / "excluded"
J10 = PKG.parent / "C10-HF-JUDGMENTS" / "outputs" / "HF_JUDGMENT_EXCLUDED_DISPOSITIONS.csv.gz"
RAW = "ad77758d"
U = r"(?:union\s+of\s+india|u\.?\s?o\.?\s?i\b|ministry\s+of\s+defen[cs]e|ministery\s+of\s+defen[cs]e|m\.?o\.?d\b|govt?\.?\s+of\s+india)"
R = [
    ("T1", 60, "AFT", re.compile(r"armed\s+forces\s+tribunal|\ba\.?\s?f\.?\s?t\b", re.I)),
    ("T1", 60, "court_martial", re.compile(r"court[\s-]*martial", re.I)),
    ("T1", 50, "ex_servicemen", re.compile(r"ex[\s.-]*servicem[ae]n|sainik", re.I)),
    ("T1", 45, "service_body", re.compile(r"chief\s+of\s+(?:the\s+)?(?:army|naval|air)\s+staff|army\s+(?:head\s*quarters|hq)|integrated\s+h(?:ead)?q|"
                                         r"\b(?:indian\s+)?army\b|\bair\s*force\b|\bindian\s+navy\b|\bnaval\b|\bmilitary\b|\bsoldier|\bjawan|record\s+office|"
                                         r"\b(?:regiment|battalion|corps)\b|\bwing\s+commander|squadron\s+leader|flight\s+lieutenant|brigadier|colonel|commodore", re.I)),
    ("T1", 35, "rank_vs_union", re.compile(r"^(?:.*?\bof\s+)?(?:ex[\s.-]*)?(?:sep|hav|nk|l/nk|sub|nb\s*sub|capt|maj|col|lt|brig|gen|sgt|cpl|jwo|mwo|cdr|cmde|wg\s*cdr|sqn\s*ldr|flt\s*lt|gp\s*capt)(?:\.\s*|\s)(?!\s*(?:inspector|manager|divisional|division|registrar|secy|secretary|post\s+office|zone|governor|insurance)).*\bvs?\b.*" + U, re.I)),
    ("T3", 30, "defence_land", re.compile(r"defen[cs]e\s+estates?|cantonment|cantt\b|military\s+(?:farm|land|engineer)|\bm\.?e\.?s\.?\b|garrison\s+engineer|\bdgde\b", re.I)),
    ("T2", 25, "defence_ministry", re.compile(r"minist?e?r?y?\.?\s*of\s+defen[cs]e|minst\.?\s*of\s+defen[cs]e|defen[cs]e\s+(?:secretary|ministry|accounts|production|research|r\s*&\s*d|personnel)|\bm\.?o\.?d\b|\bdrdo\b|ordnance|\bc\.?d\.?a\b|controller\s+of\s+defen[cs]e", re.I)),
    ("T4", 10, "capf", re.compile(r"\bb\.?s\.?f\b|border\s+security\s+force|\bc\.?r\.?p\.?f\b|central\s+reserve\s+police|\bi\.?t\.?b\.?p\b|indo[\s-]+tibet|\bc\.?i\.?s\.?f\b|"
                                    r"\bs\.?s\.?b\b|sashastra\s+seema|assam\s+rifles|\bn\.?s\.?g\b|coast\s+guard", re.I)),
]
TIER_ORDER = {"T1": 1, "T2": 2, "T3": 3, "T4": 4, "T5": 5}


def classify(title):
    hits = [(t, w, n) for t, w, n, rx in R if rx.search(title or "")]
    if not hits:
        return "T5", 1, ""
    # a CAPF title is T4 unless it also names a military body or forum
    tiers = {t for t, _, _ in hits}
    tier = min(tiers, key=lambda t: TIER_ORDER[t])
    if "T4" in tiers and tier != "T4" and not any(n in ("AFT", "court_martial", "ex_servicemen") for _, _, n in hits):
        names = {n for _, _, n in hits}
        if names <= {"capf", "rank_vs_union", "defence_ministry"}:
            tier = "T4"
    score = sum(w for _, w, _ in hits)
    return tier, score, ";".join(n for _, _, n in hits)


def build(repo):
    log = {json.loads(l)["doc_id"]: json.loads(l) for l in subprocess.run(["git", "-C", repo, "show", f"{RAW}:data/excluded_judgments.jsonl"],
                                                                     capture_output=True, check=True).stdout.decode().splitlines() if l.strip()}
    disp = list(csv.DictReader(io.StringIO(gzip.decompress(J10.read_bytes()).decode("utf-8"))))
    assert len(disp) == len(log) == 120185, (len(disp), len(log))
    rows, tally = [], Counter()
    for d in disp:
        if d["disposition"] != "EXCLUDED_FILE_NOT_RETAINED_RESCREEN_CANDIDATE":
            tally["NOT_FLAGGED"] += 1
            continue
        e = log[d["doc_id"]]
        tier, score, why = classify(e["title"])
        tally[tier] += 1
        rows.append(dict(doc_id=e["doc_id"], court=e["court"], decided=e["decided"], title=e["title"], tier=tier, score=score, signals=why,
                         sha256=e["sha256"], source_url=e["source_url"], crawler_reason=e["reason"],
                         acquisition="NOT_ACQUIRED_REQUIRES_OWNER_APPROVAL", verification_on_acquisition="SHA256_MUST_EQUAL_LOGGED_VALUE"))
    rows.sort(key=lambda r: (TIER_ORDER[r["tier"]], -r["score"], r["decided"] or "", r["doc_id"]))
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    fields = ["rank"] + [k for k in rows[0] if k != "rank"]
    s = io.StringIO(); w = csv.DictWriter(s, fieldnames=fields, lineterminator="\n"); w.writeheader(); w.writerows(rows)
    by_court = Counter((r["tier"], r["court"]) for r in rows)
    summ = dict(excluded_total=len(disp), flagged=len(rows), tiers=dict(sorted(tally.items())),
                tier_by_court={f"{t}|{c}": n for (t, c), n in sorted(by_court.items())},
                note="Ranking by fixed title rules; nothing acquired. Crawler excluded each on its own text scan for ten phrases.")
    return {"RE_ACQUISITION_MANIFEST.csv": s.getvalue(), "EXCLUDED_RANK_SUMMARY.json": json.dumps(summ, indent=1, sort_keys=True) + "\n"}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--repo", required=True); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    out = build(a.repo)
    if a.check:
        bad = [k for k, v in out.items() if not (OUT / k).is_file() or (OUT / k).read_text(encoding="utf-8") != v]
        print("CHECK FAILED: " + ", ".join(bad) if bad else f"excluded ranking reproduces ({len(out)} files)"); return 1 if bad else 0
    OUT.mkdir(exist_ok=True)
    for k, v in out.items():
        (OUT / k).write_text(v, encoding="utf-8")
    print(out["EXCLUDED_RANK_SUMMARY.json"][:600]); return 0


if __name__ == "__main__":
    sys.exit(main())
