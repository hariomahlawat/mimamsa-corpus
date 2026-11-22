#!/usr/bin/env python3
"""WS-D cycle 3, task 2: proposed identity map for non-firm citation codes and short case-name references.

Repository evidence only (read-only, stdlib, deterministic): the frozen KB, the PILOT-01 v3 register,
WS-B identity_resolution.csv, WS-C case_name_lexicon.csv and kb658_source_coverage_inventory.csv
(CASE_NAME_WITHOUT_CODE flags), cases_53, and crawler meta read from a local git ref with `git show`.

Confidence vocabulary: confirmed / inferred / unresolved.
  confirmed  - the record itself carries the identity (record-explicit) AND repository evidence binds it to
               one identified official document (e.g. the record's own URL filename equals the
               original_filename of the official corpus copy).
  inferred   - a specific identity is supported but not bound (co-citation, filename pattern, short-name match).
  unresolved - no specific identity in repository evidence.
This is a PROPOSAL. It changes no register and no KPI: the published figure stays 72/87 confirmed. A name or
URL match proves nothing about the legal content of the record. Outputs identity_map_proposed.csv/.json/.md.
Usage: python3 build_identity_map.py [--corpus-ref REF] [--check]
"""
import argparse, collections, csv, hashlib, importlib.util, io, json, re, subprocess, sys
from pathlib import Path

WSD = Path(__file__).resolve().parents[1]
ROOT = WSD.parents[2]
AW = ROOT / "legal_knowledge/audit_work"
KB = ROOT / "legal_knowledge/curated_originals/knowledge_base/v0.9/records_658.jsonl"
CASES = ROOT / "legal_knowledge/curated_originals/case_law/v0.9/cases_53.jsonl"
INPUTS = {"register": AW / "PILOT-01/registers/source_code_resolution_v3.csv",
          "wsb_identity": AW / "WS-B-JUDGMENTS/identity_resolution.csv",
          "wsc_lexicon": AW / "WS-C-MML/case_name_lexicon.csv",
          "wsc_inventory": AW / "WS-C-MML/kb658_source_coverage_inventory.csv"}
NON_FIRM = ("RESOLVED_CO_CITATION", "PROBABLE", "CATEGORY_ONLY", "UNRESOLVABLE")
OFFICIAL = re.compile(r"^https://([a-z0-9-]+\.)*(indiacode\.nic\.in|indiacode\.gov\.in|sci\.gov\.in|gov\.in|nic\.in)/", re.I)
OUT_CSV, OUT_JSON, OUT_MD = (WSD / "identity_map_proposed.csv", WSD / "identity_map_proposed.json", WSD / "identity_map_proposed.md")
OUT_JSON_PATH = OUT_JSON
LABEL = "identity map"
COLS = ["item_type", "item", "records", "current_state", "proposed_identity", "proposed_target", "confidence",
        "evidence_kind", "evidence", "what_would_confirm"]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def rows(p):
    return list(csv.DictReader(io.StringIO(p.read_text(encoding="utf-8"), newline="")))


def meta(ref, doc):
    try:
        return json.loads(subprocess.run(["git", "-C", str(ROOT), "show", f"{ref}:data/meta/{doc}.json"],
                                         check=True, capture_output=True).stdout)
    except (subprocess.CalledProcessError, ValueError):
        return None


def url_file(u):
    m = re.search(r"filename=([^&]+)", u) or re.search(r"/([^/?#]+\.pdf)(?:$|[?#])", u)
    return m.group(1) if m else ""


def build(corpus_ref):
    spec = importlib.util.spec_from_file_location("bci", AW / "PILOT-01/build_code_inventory.py")
    bci = importlib.util.module_from_spec(spec); spec.loader.exec_module(bci)
    inv, _, _ = bci.inventory()
    kb = {json.loads(l)["id"]: json.loads(l) for l in KB.read_text(encoding="utf-8").splitlines() if l.strip()}
    cases = {json.loads(l)["id"]: json.loads(l) for l in CASES.read_text(encoding="utf-8").splitlines() if l.strip()}
    reg = {r["code"]: r for r in rows(INPUTS["register"])}
    wsb = {r["spec_key"]: r for r in rows(INPUTS["wsb_identity"])}
    lex = rows(INPUTS["wsc_lexicon"])
    rec_codes = collections.defaultdict(set)
    for c, rs in inv.items():
        for r in rs:
            rec_codes[r].add(c)
    out = []
    for c in sorted(x for x in inv if reg[x]["resolution_class"] in NON_FIRM):
        r = reg[c]; recs = sorted(inv[c])
        target = re.sub(r"\s*\(candidate\)", "", r["corpus_target_or_gap"]).strip()
        doc = target if re.match(r"^(act|rules)-[a-z0-9-]+$", target) else ""
        m = meta(corpus_ref, doc) if doc else None
        single = [x for x in recs if rec_codes[x] == {c}]
        single_urls = sorted({kb[x].get("url") or "" for x in single})
        ev, kind, conf, what = [], "", "unresolved", ""
        if r["resolution_class"] == "CATEGORY_ONLY":
            kind, what = "CATEGORY_NOT_INSTRUMENT", "a specific order number/date in the record"
            ev.append("register: category only, no specific instrument named in any using record")
        elif r["resolution_class"] == "UNRESOLVABLE":
            kind, what = "NO_EVIDENCE", "record text naming the document"
            ev.append("register: no identity evidence in using records")
        elif single and len(single_urls) == 1 and single_urls[0] and OFFICIAL.match(single_urls[0]):
            u = single_urls[0]; fn = url_file(u)
            ev.append(f"{len(single)} record(s) cite only {c} and all carry url {u}")
            if m and fn and m.get("original_filename") == fn:
                conf, kind = "confirmed", "RECORD_URL_FILENAME_EQUALS_OFFICIAL_CORPUS_ORIGINAL_FILENAME"
                ev.append(f"crawler meta {doc} original_filename = {fn} (sha256 {m.get('sha256', '')[:12]}...)")
            else:
                conf, kind = "inferred", "RECORD_URL_OFFICIAL_HOST_FILENAME_NOT_BOUND"
                ev.append(f"url filename {fn!r} not recorded in crawler meta for {doc or 'the candidate'}"
                          + (f" (corpus doc {doc}: {m.get('title')}, number {m.get('number')})" if m else ""))
                what = "official listing or corpus metadata binding the URL filename to the instrument"
        elif doc and m:
            conf, kind = "inferred", "CANDIDATE_CORPUS_DOCUMENT_EXISTS"
            ev.append(f"register candidate {doc} exists in crawler corpus ({m.get('title')}); using records do not name it unambiguously")
            what = "record text naming the instrument (title/year) or a single-code record URL bound to it"
        else:
            kind, what = "NO_SPECIFIC_DOCUMENT", "record text identifying the document; or acquisition of the source"
            ev.append(f"register: {r['resolved_identity'] or 'no identity'}; target {r['corpus_target_or_gap'] or 'none'}")
        if r["resolution_class"] == "RESOLVED_CO_CITATION" and conf == "unresolved":
            conf = "inferred"; kind = kind or "CO_CITATION"
        if r["resolution_class"] == "RESOLVED_CO_CITATION" and not single:
            ev.append("no record cites this code alone; record URLs are shared with other codes")
            conf, kind = "inferred", "CO_CITATION_ONLY"
            what = what or "a record citing only this code with an identifying URL or title"
        out.append({"item_type": "CODE", "item": c, "records": ";".join(recs), "current_state": r["resolution_class"],
                    "proposed_identity": r["resolved_identity"], "proposed_target": target, "confidence": conf,
                    "evidence_kind": kind, "evidence": " | ".join(ev), "what_would_confirm": what})
    # short case names without a code (WS-C flag)
    by_key = collections.defaultdict(set)
    for x in lex:
        by_key[x["key"]].add((x["case53_id"], x["spec_key"]))
    for r in rows(INPUTS["wsc_inventory"]):
        for f in r["broken_or_unresolved_flags"].split(" | "):
            if not f.startswith("CASE_NAME_WITHOUT_CODE:"):
                continue
            for pair in f.split(":", 1)[1].split("/"):
                name, _, tgt = pair.partition("->")
                cands = by_key.get(name, set())
                ev = [f"WS-C flag {name!r}->{tgt}", f"lexicon candidates: {sorted(cands) or 'none'}"]
                spec_keys = {s for _, s in cands}
                ids_state = [wsb[s]["identity_state"] for s in spec_keys if s in wsb]
                if ids_state:
                    ev.append(f"WS-B identity_state: {'; '.join(sorted(set(ids_state)))}")
                c53 = next((c for c, _ in cands if c), "")
                year = re.search(r"\b(19|20)\d\d\b", str(kb[r["record_id"]]["references"]) + " " + kb[r["record_id"]]["title"])
                if c53 and year:
                    dy = cases[c53]["decision_date"][:4]
                    ev.append(f"record year {year.group(0)} vs case decision {dy}: {'consistent' if year.group(0) == dy else 'DIFFERENT'}")
                if len(spec_keys) == 1 and (c53 or any(st.startswith(("IDENTITY_CORROBORATED", "CITATION_METADATA_CORROBORATED")) for st in ids_state)):
                    conf, kind = "inferred", "SHORT_NAME_UNIQUE_LEXICON_MATCH"
                elif len(spec_keys) > 1:
                    conf, kind = "unresolved", "SHORT_NAME_AMBIGUOUS"
                else:
                    conf, kind = "unresolved", "SHORT_NAME_TARGET_UNIDENTIFIED"
                out.append({"item_type": "CASE_NAME_REF", "item": f"{r['record_id']}:{name}", "records": r["record_id"],
                            "current_state": "CASE_NAME_WITHOUT_CODE", "proposed_identity": tgt,
                            "proposed_target": c53 or next(iter(spec_keys), ""), "confidence": conf, "evidence_kind": kind,
                            "evidence": " | ".join(ev),
                            "what_would_confirm": "a code or full citation in the record bound to an official copy (WS-B)"})
    out.sort(key=lambda x: (x["item_type"], x["item"]))
    inputs = {k: {"path": str(p.relative_to(ROOT)), "sha256": sha(p)} for k, p in INPUTS.items()}
    inputs["kb"] = {"path": str(KB.relative_to(ROOT)), "sha256": sha(KB)}
    try:
        cc = subprocess.run(["git", "-C", str(ROOT), "rev-parse", corpus_ref], check=True, capture_output=True, text=True).stdout.strip()
    except subprocess.CalledProcessError:
        cc = None
    inputs["corpus"] = {"ref": corpus_ref, "commit": cc}
    return out, inputs


def render(out, inputs):
    codes = [r for r in out if r["item_type"] == "CODE"]; names = [r for r in out if r["item_type"] == "CASE_NAME_REF"]
    cc = collections.Counter((r["current_state"], r["confidence"]) for r in codes)
    nc = collections.Counter(r["confidence"] for r in names)
    up = [r["item"] for r in codes if r["confidence"] == "confirmed"]
    L = ["# Proposed identity map (non-firm codes and short case names)", "",
         "Generated by `scripts/build_identity_map.py` from repository evidence only. **PROPOSAL**: no register, KPI or record is changed. Identity resolution is not legal verification.", "",
         "Inputs (SHA-256): " + "; ".join(f"`{k}` {v['sha256'][:12]}…" for k, v in inputs.items() if "sha256" in v)
         + f"; crawler corpus `{inputs['corpus']['ref']}` @ `{(inputs['corpus']['commit'] or 'n/a')[:12]}`.", "",
         "## Codes (denominator = 15 non-firm codes of 87)", "", "| Current class | Proposed confidence | n |", "| --- | --- | --- |"]
    L += [f"| {a} | {b} | {n} |" for (a, b), n in sorted(cc.items())]
    L += ["", f"Proposed `confirmed`: {', '.join(up) or 'none'}. If accepted by the coordinator, firm codes would be {72 + len(up)}/87; **the published figure remains 72/87** until a reviewed register version adopts it.", "",
          "| Code | Current | Proposed | Target | Evidence | What would confirm |", "| --- | --- | --- | --- | --- | --- |"]
    L += [f"| {r['item']} | {r['current_state']} | **{r['confidence']}** ({r['evidence_kind']}) | {r['proposed_target']} | {r['evidence']} | {r['what_would_confirm']} |" for r in codes]
    L += ["", f"## Short case names without a code (denominator = {len(names)} name references in {len({r['records'] for r in names})} records)", "",
          "| Confidence | n |", "| --- | --- |"] + [f"| {k} | {v} |" for k, v in sorted(nc.items())]
    L += ["", "A unique short-name match is at most `inferred`: the record does not cite the judgment, and identity of the *case* (WS-B) is not identity of the *reference*.", "",
          "| Reference | Proposed target | Confidence | Evidence |", "| --- | --- | --- | --- |"]
    L += [f"| {r['item']} | {r['proposed_target']} | {r['confidence']} ({r['evidence_kind']}) | {r['evidence']} |" for r in names]
    return "\n".join(L) + "\n"


def outputs(corpus_ref):
    out, inputs = build(corpus_ref)
    buf = io.StringIO(); w = csv.DictWriter(buf, fieldnames=COLS, lineterminator="\n"); w.writeheader(); w.writerows(out)
    js = json.dumps({"artifact": "WS-D proposed identity map", "proposal_only": True, "published_kpi_unchanged": "72/87",
                     "inputs": inputs, "items": out}, indent=1, ensure_ascii=False) + "\n"
    return {OUT_CSV: buf.getvalue(), OUT_JSON: js, OUT_MD: render(out, inputs)}


def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument("--corpus-ref", default="origin/raw-data"); ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    if a.check and subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--verify", "-q", a.corpus_ref],
                                  capture_output=True).returncode != 0:
        # CI checkouts lack the crawler-corpus ref: verify the pinned input hashes only and say so.
        pinned = json.loads(OUT_JSON_PATH.read_text(encoding="utf-8"))["inputs"]
        bad = [k for k, v in pinned.items() if "sha256" in v and hashlib.sha256((ROOT / v["path"]).read_bytes()).hexdigest() != v["sha256"]]
        print("%s: corpus ref %s unavailable - regeneration NOT_CHECKED; pinned inputs %s"
              % (LABEL, a.corpus_ref, "MATCH" if not bad else f"CHANGED {bad} (regenerate)"))
        return 1 if bad else 0
    files = outputs(a.corpus_ref)
    if a.check:
        bad = [str(p.name) for p, t in files.items() if not p.is_file() or p.read_text(encoding="utf-8") != t]
        print("identity map: " + ("MATCH" if not bad else f"DIFFERS {bad}"))
        return 1 if bad else 0
    for p, t in files.items():
        p.write_text(t, encoding="utf-8")
    print(files[OUT_MD].split("## Short")[0][-1200:])
    return 0


if __name__ == "__main__":
    sys.exit(main())
