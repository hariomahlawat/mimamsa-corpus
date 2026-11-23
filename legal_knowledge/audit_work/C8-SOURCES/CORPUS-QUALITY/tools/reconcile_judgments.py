#!/usr/bin/env python3
"""Deterministic, offline judgment-batch reconciliation (Mimamsa C8 / WS-E).

Classifies each item of an incoming judgment batch against the existing corpus.
It NEVER merges, NEVER overwrites, NEVER downloads and NEVER edits any input:
it only writes the CSV report named by --out (refused if --out is an input path).

Classes (first matching rule wins, evaluated in this order):
  EXACT_DUPLICATE        sha256 equals a copy already known to the corpus (or an
                         earlier row of the same batch).
  VERSION_RELATIONSHIP   same court + overlapping case number + same judgment date,
                         different sha256, AND the incoming item (or the matched corpus
                         copy) carries an explicit version marker (corrected,
                         corrigendum, uncorrected, revised, modified, amended,
                         reportable/non-reportable version, signed copy ...).
  SAME_JUDGMENT_NEW_COPY same court + overlapping case number + same judgment date,
                         different sha256, no version marker.
  POSSIBLE_MATCH_REVIEW  only a fuzzy signal: same case number with a different date
                         (possible later order in the same case), shared citation,
                         or party-name similarity >= threshold. Human review required.
  NEW                    no match in the SUPPLIED corpus snapshot. This is not a claim
                         that the judgment is absent from any other collection.

Input batch: .csv or .jsonl. Required fields per item:
  court, case_numbers, judgment_date (YYYY-MM-DD), parties, sha256 (64 hex),
  and at least one of source_url / provenance.
Optional: item_id, citations (or citation), version_label, copy_note, title.
case_numbers / citations may be a JSON list or a ';'-separated string.
parties may be a string ("A v B") or an object {"petitioner":..,"respondent":..}.

Validation fails closed: if ANY item is malformed the tool prints every problem to
stderr, writes no report, and exits with status 2.

Corpus (read-only):
  --repo <snapshot root>  uses
     legal_knowledge/curated_originals/case_law/v0.9/cases_53.jsonl
     legal_knowledge/audit_work/WS-B-JUDGMENTS/identity_resolution.csv
     legal_knowledge/audit_work/WS-B-JUDGMENTS/holdings_register.csv
     legal_knowledge/audit_work/WS-B-JUDGMENTS/holdings_register_cycle3.csv
     legal_knowledge/audit_work/SOURCE-LIBRARY-C5/registers/source_copy_register.csv
     legal_knowledge/audit_work/SOURCE-LIBRARY-C5/inputs/case_source_map.csv
  or explicit --cases / --identity / --holdings (repeatable) / --copies / --case-source-map.
  With --repo every listed file must exist (a missing corpus file would turn
  duplicates into false NEWs, so the tool fails closed).

Usage:
  python3 reconcile_judgments.py --incoming batch.jsonl --repo <root> --out report.csv
Exit status: 0 ok, 2 malformed input / missing corpus / unsafe output path.
"""
import argparse
import csv
import datetime
import io
import json
import os
import re
import sys

CLASSES = ("EXACT_DUPLICATE", "VERSION_RELATIONSHIP", "SAME_JUDGMENT_NEW_COPY",
           "POSSIBLE_MATCH_REVIEW", "NEW")
REQUIRED = ("court", "case_numbers", "judgment_date", "parties", "sha256")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
VERSION_RE = re.compile(r"\b(corrected|corrigendum|uncorrected|revised|modified|amended|"
                        r"rectified|errata|re-?issued|signed copy|non-?reportable|reportable version)\b", re.I)
PARTY_STOP = {"union", "of", "india", "and", "others", "ors", "anr", "another", "v", "vs", "versus",
              "the", "state", "ex", "retd", "lt", "col", "maj", "gen", "sgt", "hav", "sep", "nk", "cdr",
              "wg", "capt", "major", "general", "colonel", "havildar", "sepoy", "shri", "sh", "smt", "mr",
              "dr", "no", "ic", "secretary", "ministry", "defence", "chief", "army", "staff", "etc", "anr",
              "respondent", "respondents", "appellant", "appellants", "petitioner", "petitioners", "&"}
COURT_ALIASES = {
    "sc": "supreme court", "sci": "supreme court", "supreme court": "supreme court",
    "hon ble supreme court": "supreme court", "supreme court of india": "supreme court",
    "delhi hc": "delhi high court", "high court of delhi": "delhi high court",
    "aft": "armed forces tribunal", "aft pb": "armed forces tribunal principal bench",
    "armed forces tribunal principal bench new delhi": "armed forces tribunal principal bench",
}
CASE_TYPES = [
    (r"s\.?\s*l\.?\s*p\.?\s*\(\s*(?:crl|criminal)\.?\s*\)", "SLPCRL"),
    (r"s\.?\s*l\.?\s*p\.?\s*\(\s*c(?:ivil)?\.?\s*\)", "SLPC"),
    (r"special\s+leave\s+petition\s*\(\s*(?:crl|criminal)\.?\s*\)", "SLPCRL"),
    (r"special\s+leave\s+petition\s*\(\s*c(?:ivil)?\.?\s*\)", "SLPC"),
    (r"w\.?\s*p\.?\s*\(\s*(?:crl|criminal)\.?\s*\)", "WPCRL"),
    (r"w\.?\s*p\.?\s*\(\s*c(?:ivil)?\.?\s*\)", "WPC"),
    (r"writ\s+petitions?\s*\(\s*(?:crl|criminal)\.?\s*\)", "WPCRL"),
    (r"writ\s+petitions?\s*\(\s*c(?:ivil)?\.?\s*\)", "WPC"),
    (r"writ\s+petitions?|w\.?\s*p\.?", "WP"),
    (r"criminal\s+appeals?|crl\.?\s*a\.?|cr\.?\s*a\.?", "CRLA"),
    (r"civil\s+appeals?|c\.?\s*a\.?", "CA"),
    (r"review\s+petitions?|r\.?\s*p\.?", "RP"),
    (r"original\s+applications?|o\.?\s*a\.?", "OA"),
    (r"misc(?:ellaneous)?\.?\s+applications?|m\.?\s*a\.?", "MA"),
    (r"transfer(?:red)?\s+applications?|t\.?\s*a\.?", "TA"),
    (r"diary", "DIARY"),
]
NUM_TAIL = r"\s*(?:nos?\.?|numbers?)?\s*(\d+)(?:\s*[-–—]\s*(\d+))?\s*(?:of|/)\s*(\d{4})"


class InputError(Exception):
    pass


# ----------------------------------------------------------------- normalisation helpers
def norm_space(s):
    return re.sub(r"\s+", " ", str(s or "")).strip()


def norm_court(s):
    t = re.sub(r"[^a-z0-9 ]", " ", str(s or "").lower())
    t = norm_space(re.sub(r"\b(the|hon ble|honble)\b", " ", t))
    if t in COURT_ALIASES:
        return COURT_ALIASES[t]
    if "supreme court" in t:
        return "supreme court"
    m = re.search(r"high court of ([a-z ]+)", t)
    if m:
        return norm_space(m.group(1)) + " high court"
    return t


def as_list(v):
    if v is None:
        return []
    if isinstance(v, list):
        return [norm_space(x) for x in v if norm_space(x)]
    s = str(v).strip()
    if s.startswith("["):
        try:
            return as_list(json.loads(s))
        except ValueError:
            pass
    return [norm_space(x) for x in re.split(r";|\n", s) if norm_space(x)]


def parties_text(v):
    if isinstance(v, dict):
        return " v ".join(norm_space(v.get(k)) for k in ("petitioner", "appellant", "respondent") if v.get(k))
    s = str(v or "").strip()
    if s.startswith("{"):
        try:
            return parties_text(json.loads(s))
        except ValueError:
            pass
    return norm_space(s)


def party_tokens(s):
    toks = re.findall(r"[a-z]{3,}", str(s or "").lower())
    return frozenset(t for t in toks if t not in PARTY_STOP)


def case_keys(strings):
    """Return a set of (TYPE, number, year) keys. Ranges up to 60 numbers are expanded."""
    keys = set()
    for s in strings:
        low = str(s).lower()
        spans = []
        for pat, typ in CASE_TYPES:
            for m in re.finditer("(?<![a-z])(?:" + pat + ")" + NUM_TAIL, low):
                if any(m.start() < e and m.end() > b for b, e in spans):
                    continue
                spans.append((m.start(), m.end()))
                a, b, yr = int(m.group(1)), m.group(2), m.group(3)
                rng = range(a, int(b) + 1) if b and 0 <= int(b) - a <= 60 else [a]
                for n in rng:
                    keys.add((typ, n, yr))
        for m in re.finditer(r"\b(\d+)\s*(?:of|/)\s*(\d{4})\b", low):  # bare "1234/2019"
            if not any(m.start() < e and m.end() > b for b, e in spans):
                keys.add(("UNTYPED", int(m.group(1)), m.group(2)))
    return keys


def keys_overlap(a, b):
    if a & b:
        return sorted(a & b)
    # an UNTYPED key matches a typed key with same number/year
    out = []
    for t1, n1, y1 in a:
        for t2, n2, y2 in b:
            if n1 == n2 and y1 == y2 and "UNTYPED" in (t1, t2):
                out.append((t1 if t1 != "UNTYPED" else t2, n1, y1))
    return sorted(set(out))


def norm_citation(c):
    s = str(c or "").upper()
    s = s.replace("[", "(").replace("]", ")")
    s = re.sub(r"\s+", " ", s).strip(" .;")
    s = re.sub(r"\(\s*", "(", s)
    s = re.sub(r"\s*\)", ")", s)
    return s


def split_citations(v):
    out = set()
    for item in as_list(v):
        for part in re.split(r";", item):
            p = norm_citation(part)
            if re.search(r"\d", p) and len(p) >= 8:
                out.add(p)
    return out


def valid_date(s):
    try:
        datetime.date.fromisoformat(str(s))
        return re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(s)) is not None
    except ValueError:
        return False


# ----------------------------------------------------------------- input loading
def load_batch(path):
    if not os.path.isfile(path):
        raise InputError(f"incoming batch not found: {path}")
    ext = os.path.splitext(path)[1].lower()
    rows = []
    with open(path, encoding="utf-8", newline="") as f:
        if ext == ".jsonl":
            for i, line in enumerate(f, start=1):
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                except ValueError as e:
                    raise InputError(f"line {i}: invalid JSON ({e})")
                if not isinstance(obj, dict):
                    raise InputError(f"line {i}: item is not a JSON object")
                rows.append((i, obj))
        elif ext == ".csv":
            rd = csv.DictReader(f)
            if rd.fieldnames is None:
                raise InputError("CSV has no header")
            for i, obj in enumerate(rd, start=2):
                if None in obj:
                    raise InputError(f"line {i}: more fields than header columns")
                rows.append((i, obj))
        else:
            raise InputError("incoming batch must be .csv or .jsonl")
    if not rows:
        raise InputError("incoming batch is empty")
    return rows


def validate(rows):
    errors, items = [], []
    for line, obj in rows:
        e = []
        for k in REQUIRED:
            v = obj.get(k)
            if v is None or (isinstance(v, (str, list, dict)) and not (v if not isinstance(v, str) else v.strip())):
                e.append(f"missing required field '{k}'")
        sha = str(obj.get("sha256") or "").strip()
        if sha and not SHA_RE.match(sha):
            e.append("sha256 must be 64 lowercase hex characters")
        jd = str(obj.get("judgment_date") or "").strip()
        if jd and not valid_date(jd):
            e.append(f"judgment_date '{jd}' is not a valid YYYY-MM-DD date")
        prov = norm_space(obj.get("source_url")) or norm_space(obj.get("provenance"))
        if not prov:
            e.append("one of source_url / provenance is required")
        cns = as_list(obj.get("case_numbers"))
        if obj.get("case_numbers") and not cns:
            e.append("case_numbers is empty")
        if cns and not case_keys(cns):
            e.append("case_numbers contain no parseable '<number> of|/ <year>' pattern")
        pt = parties_text(obj.get("parties"))
        if obj.get("parties") and not pt:
            e.append("parties is empty")
        if e:
            errors.append(f"input line {line}: " + "; ".join(e))
            continue
        cits = split_citations(obj.get("citations") if obj.get("citations") not in (None, "") else obj.get("citation"))
        items.append(dict(
            line=line, item_id=norm_space(obj.get("item_id")) or f"line{line}", court_raw=norm_space(obj["court"]),
            court=norm_court(obj["court"]), case_numbers=cns, case_keys=case_keys(cns), date=jd,
            parties=pt, ptoks=party_tokens(pt), sha256=sha, citations=cits, provenance=prov,
            version_text=" ".join(norm_space(obj.get(k)) for k in ("version_label", "copy_note", "title", "notes"))))
    return errors, items


# ----------------------------------------------------------------- corpus loading
def rcsv(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def load_corpus(cases=None, identity=None, holdings=(), copies=None, case_source_map=None):
    """Build entities {key: {...}} and copies {sha256: [(key, label, version_text)]}."""
    ents, shas = {}, {}

    def ent(key):
        return ents.setdefault(key, dict(key=key, courts=set(), case_keys=set(), dates=set(), ptoks=set(),
                                         citations=set(), labels=set(), version_text=""))

    def add_sha(sha, key, label, vt=""):
        sha = (sha or "").strip().lower()
        if SHA_RE.match(sha):
            lst = shas.setdefault(sha, [])
            if (key, label) not in [(k, l) for k, l, _ in lst]:
                lst.append((key, label, vt))

    spec_to_case = {}
    if cases:
        with open(cases, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                c = json.loads(line)
                e = ent(c["id"])
                e["courts"].add(norm_court(c.get("court")))
                e["case_keys"] |= case_keys([c.get("case_number") or ""])
                if c.get("decision_date"):
                    e["dates"].add(c["decision_date"])
                e["ptoks"] |= party_tokens(c.get("title"))
                e["citations"] |= split_citations(c.get("reporter_citation"))
                e["labels"].add(f"cases_53:{c['id']}")
                add_sha(c.get("original_pdf_sha256"), c["id"], "cases_53.original_pdf_sha256")
    if identity:
        for r in rcsv(identity):
            key = r.get("case53_id") or ("WSB:" + r["spec_key"])
            spec_to_case[r["spec_key"]] = key
            e = ent(key)
            for f in ("curated_court",):
                if r.get(f):
                    e["courts"].add(norm_court(r[f]))
            e["case_keys"] |= case_keys(as_list(r.get("curated_case_number")) + as_list(r.get("intern_case_numbers")))
            for f in ("curated_decision_date", "intern_decision_date"):
                if valid_date(r.get(f) or ""):
                    e["dates"].add(r[f])
            e["ptoks"] |= party_tokens(r.get("curated_title")) | party_tokens(r.get("intern_parties"))
            e["citations"] |= split_citations(r.get("curated_reporter_citation")) | split_citations(
                r.get("intern_neutral_citation")) | split_citations(r.get("intern_reported_citations")) | split_citations(
                r.get("expected_neutral_citation_spec"))
            e["labels"].add(f"identity_resolution:{r['spec_key']}")
            for f in ("intern_sha256", "held_copy_sha256", "register_official_sha256"):
                for s in str(r.get(f) or "").split(";"):
                    add_sha(s, key, f"identity_resolution.{f}:{r['spec_key']}")
    for h in holdings or ():
        for r in rcsv(h):
            key = r.get("case53_id") or spec_to_case.get(r.get("spec_key")) or ("WSB:" + (r.get("spec_key") or "?"))
            e = ent(key)
            if valid_date(r.get("decision_date") or ""):
                e["dates"].add(r["decision_date"])
            e["case_keys"] |= case_keys([r.get("judgment") or ""])
            e["citations"] |= split_citations(re.findall(r"\d{4} INSC \d+", r.get("judgment") or ""))
            e["labels"].add(f"{os.path.basename(h)}:{r.get('row_id')}")
            add_sha(r.get("copy_sha256"), key, f"{os.path.basename(h)}:{r.get('row_id')}",
                    " ".join([r.get("uncertainty") or "", r.get("copy_role") or ""]))
    src_to_case = {}
    if case_source_map:
        for r in rcsv(case_source_map):
            src_to_case[r["source_id"]] = r["key"]
    if copies:
        for r in rcsv(copies):
            key = src_to_case.get(r["source_id"]) or ("C5:" + r["source_id"])
            e = ent(key)
            e["labels"].add(f"source_copy_register:{r['copy_id']}")
            add_sha(r.get("sha256"), key, f"source_copy_register:{r['copy_id']}", r.get("copy_role") or "")
    for e in ents.values():
        e["courts"].discard("")
    return ents, shas


# ----------------------------------------------------------------- classification
def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def classify(items, ents, shas, party_threshold=0.5):
    out, seen_batch = [], {}
    for it in items:
        row = dict(line=it["line"], item_id=it["item_id"], sha256=it["sha256"], court=it["court_raw"],
                   case_numbers="; ".join(it["case_numbers"]), judgment_date=it["date"], parties=it["parties"],
                   provenance=it["provenance"])
        # 1. exact duplicate (corpus, then earlier batch rows)
        if it["sha256"] in shas:
            hits = sorted(shas[it["sha256"]])
            row.update(classification="EXACT_DUPLICATE", matched_corpus_keys=";".join(sorted({k for k, _, _ in hits})),
                       matched_on="sha256",
                       reasons="sha256 equals known copy: " + ";".join(l for _, l, _ in hits))
            out.append(row)
            seen_batch.setdefault(it["sha256"], it["item_id"])
            continue
        if it["sha256"] in seen_batch:
            row.update(classification="EXACT_DUPLICATE", matched_corpus_keys="",
                       matched_on="sha256 (within batch)",
                       reasons=f"sha256 equals earlier incoming item {seen_batch[it['sha256']]}; not in corpus")
            out.append(row)
            continue
        seen_batch[it["sha256"]] = it["item_id"]
        # 2. same court + case number (+ date)
        strong, same_case_other_date, fuzzy = [], [], []
        for key in sorted(ents):
            e = ents[key]
            court_ok = (not e["courts"]) or (it["court"] in e["courts"])
            ov = keys_overlap(it["case_keys"], e["case_keys"])
            if ov and court_ok and e["courts"]:
                if it["date"] in e["dates"]:
                    strong.append((key, ov))
                    continue
                same_case_other_date.append((key, ov, sorted(e["dates"])))
                continue
            reasons = []
            if ov and not e["courts"]:
                reasons.append("case number overlap " + ",".join(f"{t} {n}/{y}" for t, n, y in ov)
                               + " but corpus entity has no court recorded")
            cit = it["citations"] & e["citations"]
            if cit:
                reasons.append("shared citation " + "; ".join(sorted(cit)))
            js = jaccard(it["ptoks"], e["ptoks"])
            if js >= party_threshold and (court_ok or not e["courts"]):
                yr_ok = any(abs(int(d[:4]) - int(it["date"][:4])) <= 1 for d in e["dates"]) if e["dates"] else True
                if yr_ok:
                    reasons.append(f"party-name similarity {js:.2f} ({' '.join(sorted(it['ptoks'] & e['ptoks']))})")
            if reasons:
                fuzzy.append((key, reasons))
        if strong:
            keys = [k for k, _ in strong]
            related = ("; related same-case entities with other dates (not merged): "
                       + ", ".join(f"{k} {d}" for k, _, d in same_case_other_date)) if same_case_other_date else ""
            corpus_vt = " ".join(vt for s, lst in shas.items() for k, _, vt in lst if k in keys)
            marker = VERSION_RE.search(it["version_text"]) or VERSION_RE.search(corpus_vt)
            ov_txt = "; ".join(f"{k}: " + ",".join(f"{t} {n}/{y}" for t, n, y in ov) for k, ov in strong)
            if marker:
                row.update(classification="VERSION_RELATIONSHIP", matched_corpus_keys=";".join(keys),
                           matched_on="court+case_number+judgment_date; version marker",
                           reasons=f"same court, case number ({ov_txt}) and date {it['date']}; different sha256; "
                                   f"version marker '{marker.group(0)}' -> record as a version of the same judgment, "
                                   f"do not replace the existing copy" + related)
            else:
                row.update(classification="SAME_JUDGMENT_NEW_COPY", matched_corpus_keys=";".join(keys),
                           matched_on="court+case_number+judgment_date",
                           reasons=f"same court, case number ({ov_txt}) and date {it['date']}; different sha256; "
                                   f"no version marker -> add as additional copy after byte/page comparison" + related)
            out.append(row)
            continue
        if same_case_other_date or fuzzy:
            keys = sorted({k for k, _, _ in same_case_other_date} | {k for k, _ in fuzzy})
            reasons = [f"{k}: same court and case number ({','.join(f'{t} {n}/{y}' for t, n, y in ov)}) "
                       f"but date {it['date']} not in {d or ['(no date recorded)']}: possible later/earlier order "
                       f"in the same case" for k, ov, d in same_case_other_date]
            reasons += [f"{k}: " + "; ".join(r) for k, r in fuzzy]
            row.update(classification="POSSIBLE_MATCH_REVIEW", matched_corpus_keys=";".join(keys),
                       matched_on="fuzzy (no court+case_number+date match)", reasons=" | ".join(reasons))
            out.append(row)
            continue
        row.update(classification="NEW", matched_corpus_keys="", matched_on="",
                   reasons="no sha256, case-number, citation or party match in the supplied corpus snapshot "
                           "(absence here does not prove absence from other collections)")
        out.append(row)
    return out


FIELDS = ["line", "item_id", "classification", "matched_corpus_keys", "matched_on", "reasons", "sha256", "court",
          "case_numbers", "judgment_date", "parties", "provenance"]


def write_report(rows, out):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k, "") for k in FIELDS})
    with open(out, "w", encoding="utf-8", newline="") as f:
        f.write(buf.getvalue())


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--incoming", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--repo")
    ap.add_argument("--cases")
    ap.add_argument("--identity")
    ap.add_argument("--holdings", action="append", default=[])
    ap.add_argument("--copies")
    ap.add_argument("--case-source-map")
    ap.add_argument("--party-threshold", type=float, default=0.5)
    a = ap.parse_args(argv)
    if a.repo:
        lk = os.path.join(a.repo, "legal_knowledge")
        a.cases = a.cases or os.path.join(lk, "curated_originals/case_law/v0.9/cases_53.jsonl")
        a.identity = a.identity or os.path.join(lk, "audit_work/WS-B-JUDGMENTS/identity_resolution.csv")
        a.holdings = a.holdings or [os.path.join(lk, "audit_work/WS-B-JUDGMENTS/holdings_register.csv"),
                                    os.path.join(lk, "audit_work/WS-B-JUDGMENTS/holdings_register_cycle3.csv")]
        a.copies = a.copies or os.path.join(lk, "audit_work/SOURCE-LIBRARY-C5/registers/source_copy_register.csv")
        a.case_source_map = a.case_source_map or os.path.join(lk, "audit_work/SOURCE-LIBRARY-C5/inputs/case_source_map.csv")
    inputs = [p for p in [a.incoming, a.cases, a.identity, a.copies, a.case_source_map] + list(a.holdings) if p]
    if not any([a.cases, a.identity, a.holdings, a.copies]):
        print("ERROR: no corpus supplied (use --repo or --cases/--identity/--holdings/--copies)", file=sys.stderr)
        return 2
    missing = [p for p in inputs if not os.path.isfile(p)]
    if missing:
        print("ERROR: missing input file(s): " + "; ".join(missing), file=sys.stderr)
        return 2
    if os.path.abspath(a.out) in {os.path.abspath(p) for p in inputs}:
        print("ERROR: --out must not be one of the input files", file=sys.stderr)
        return 2
    try:
        rows = load_batch(a.incoming)
    except InputError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    errors, items = validate(rows)
    if errors:
        for e in errors:
            print("ERROR: " + e, file=sys.stderr)
        print(f"ERROR: {len(errors)} malformed item(s); no report written (fail closed)", file=sys.stderr)
        return 2
    ents, shas = load_corpus(a.cases, a.identity, a.holdings, a.copies, a.case_source_map)
    out = classify(items, ents, shas, a.party_threshold)
    write_report(out, a.out)
    counts = {c: sum(1 for r in out if r["classification"] == c) for c in CLASSES}
    print(json.dumps({"items": len(out), "corpus_entities": len(ents), "corpus_copies": len(shas), **counts}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
