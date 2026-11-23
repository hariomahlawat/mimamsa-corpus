#!/usr/bin/env python3
"""Deterministic, offline judgment-batch reconciliation (Mimamsa C8 / WS-E).

Classifies each item of an incoming judgment batch against the existing corpus.
It NEVER merges, NEVER downloads and NEVER edits any input. It only writes the CSV
report named by --out, and it refuses (exit 2) an --out that:
  - resolves to any input file (same real path after symlinks, os.path.samefile, or
    the same device+inode, i.e. a hard link), even with --overwrite;
  - lies inside a 'curated_originals' directory;
  - already exists, unless --overwrite is given;
  - is a directory, or whose parent directory does not exist.
The report is written atomically: a temporary file is created in the target
directory and then linked (no-clobber) or, with --overwrite, renamed into place.

Classes (first matching rule wins, evaluated in this order):
  EXACT_DUPLICATE        sha256 equals a copy already known to the corpus (or an
                         earlier row of the same batch). If the item's court, case
                         number or date contradicts what the corpus records for that
                         hash, the row is flagged METADATA_CONFLICT_WITH_KNOWN_HASH
                         (flags column + stderr warning) and must be reviewed: a
                         wrongly pasted hash would otherwise hide a new judgment.
  VERSION_RELATIONSHIP   same court + overlapping TYPED case number (same case type,
                         number and year) + same judgment date,
                         different sha256, AND the incoming item (or the matched corpus
                         copy) carries an explicit version marker (corrected,
                         corrigendum, uncorrected, revised, modified, amended,
                         reportable/non-reportable version, signed copy ...).
  SAME_JUDGMENT_NEW_COPY same court + overlapping TYPED case number + same judgment date,
                         different sha256, no version marker.
  POSSIBLE_MATCH_REVIEW  only a fuzzy signal: same case number with a different date
                         (possible later order in the same case), an UNTYPED case
                         number (bare 'n/yyyy') matching a corpus number, shared
                         citation, or party-name similarity >= threshold. Human review
                         required.
  NEW                    no match in the SUPPLIED corpus snapshot. This is not a claim
                         that the judgment is absent from any other collection.

Input batch: .csv or .jsonl. Required fields per item:
  court, case_numbers, judgment_date (YYYY-MM-DD), parties, sha256 (64 hex),
  and at least one of source_url / provenance.
Optional: item_id, citations (or citation), version_label, copy_note, title.
case_numbers / citations may be a JSON list or a ';'-separated string.
parties may be a string ("A v B") or an object {"petitioner":..,"respondent":..}.

Validation fails closed: if ANY item is malformed the tool prints every problem to
stderr, writes no report, and exits with status 2. Malformed includes: missing or
empty required fields, bad sha256, invalid or implausible dates (before 1800 or
after today), duplicate JSON keys, duplicate item_id, NUL or other control
characters, non-string list members, duplicate CSV header columns, ragged CSV rows,
and a batch that is not valid UTF-8.

Report cells that begin with '=', '+', '-', '@', TAB or CR are prefixed with a single
quote so that a spreadsheet does not evaluate them as formulas.

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
  python3 reconcile_judgments.py --incoming batch.jsonl --repo <root> --out report.csv [--overwrite]
Exit status: 0 ok, 2 malformed input / unreadable or missing corpus / unsafe output path.
"""
import argparse
import csv
import datetime
import io
import json
import os
import re
import sys
import tempfile

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
CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
FORMULA_LEAD = ("=", "+", "-", "@", "\t", "\r")
MIN_YEAR = 1800
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


def plausible_date(s, today=None):
    """Return an error string for an implausible judgment date, or ''."""
    d = datetime.date.fromisoformat(str(s))
    today = today or datetime.date.today()
    if d.year < MIN_YEAR:
        return f"judgment_date '{s}' is before {MIN_YEAR} (implausible)"
    if d > today:
        return f"judgment_date '{s}' is in the future (after {today.isoformat()})"
    return ""


def _no_dup_keys(pairs):
    obj = {}
    for k, v in pairs:
        if k in obj:
            raise InputError(f"duplicate JSON key '{k}'")
        obj[k] = v
    return obj


# ----------------------------------------------------------------- input loading
def load_batch(path):
    if not os.path.isfile(path):
        raise InputError(f"incoming batch not found: {path}")
    ext = os.path.splitext(path)[1].lower()
    rows = []
    try:
        with open(path, encoding="utf-8", newline="") as f:
            if ext == ".jsonl":
                for i, line in enumerate(f, start=1):
                    if not line.strip():
                        continue
                    try:
                        obj = json.loads(line, object_pairs_hook=_no_dup_keys)
                    except InputError as e:
                        raise InputError(f"line {i}: {e}")
                    except ValueError as e:
                        raise InputError(f"line {i}: invalid JSON ({e})")
                    if not isinstance(obj, dict):
                        raise InputError(f"line {i}: item is not a JSON object")
                    rows.append((i, obj))
            elif ext == ".csv":
                rd = csv.DictReader(f)
                if rd.fieldnames is None:
                    raise InputError("CSV has no header")
                dup = sorted({h for h in rd.fieldnames if rd.fieldnames.count(h) > 1})
                if dup:
                    raise InputError("CSV header has duplicate column(s): " + ", ".join(dup))
                for i, obj in enumerate(rd, start=2):
                    if None in obj:
                        raise InputError(f"line {i}: more fields than header columns")
                    rows.append((i, obj))
            else:
                raise InputError("incoming batch must be .csv or .jsonl")
    except UnicodeDecodeError as e:
        raise InputError(f"incoming batch is not valid UTF-8 ({e})")
    except csv.Error as e:
        raise InputError(f"CSV parse error ({e})")
    if not rows:
        raise InputError("incoming batch is empty")
    return rows


def _walk_strings(v):
    if isinstance(v, str):
        yield v
    elif isinstance(v, dict):
        for k, x in v.items():
            yield str(k)
            yield from _walk_strings(x)
    elif isinstance(v, list):
        for x in v:
            yield from _walk_strings(x)


def validate(rows, today=None):
    errors, items = [], []
    seen_ids = {}
    for line, obj in rows:
        e = []
        if any(CONTROL_RE.search(x) for k, v in obj.items() for x in _walk_strings({k: v})):
            e.append("NUL or other control character in a field (not allowed)")
        for k in ("case_numbers", "citations"):
            v = obj.get(k)
            if isinstance(v, list) and any(not isinstance(x, str) for x in v):
                e.append(f"'{k}' list members must be strings")
        iid = norm_space(obj.get("item_id"))
        if iid:
            if iid in seen_ids:
                e.append(f"duplicate item_id '{iid}' (first at input line {seen_ids[iid]})")
            else:
                seen_ids[iid] = line
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
        elif jd:
            pe = plausible_date(jd, today)
            if pe:
                e.append(pe)
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


def metadata_conflicts(it, courts, ckeys, dates):
    """Fields on which an item contradicts what is recorded for a known hash."""
    bad = []
    if courts and it["court"] not in courts:
        bad.append("court " + repr(it["court_raw"]) + " vs " + "/".join(sorted(courts)))
    if ckeys and it["case_keys"] and not keys_overlap(it["case_keys"], ckeys):
        bad.append("case number " + "; ".join(it["case_numbers"]) + " vs "
                   + ",".join(f"{t} {n}/{y}" for t, n, y in sorted(ckeys)[:6]))
    if dates and it["date"] not in dates:
        bad.append(f"date {it['date']} vs " + ",".join(sorted(dates)))
    return bad


def typed_overlap(a, b):
    """Overlap on identical (TYPE, number, year) keys where TYPE is not UNTYPED."""
    return sorted(k for k in (a & b) if k[0] != "UNTYPED")


def classify(items, ents, shas, party_threshold=0.5, warn=None):
    out, seen_batch = [], {}
    for it in items:
        row = dict(line=it["line"], item_id=it["item_id"], sha256=it["sha256"], court=it["court_raw"],
                   case_numbers="; ".join(it["case_numbers"]), judgment_date=it["date"], parties=it["parties"],
                   provenance=it["provenance"], flags="")
        # 1. exact duplicate (corpus, then earlier batch rows)
        if it["sha256"] in shas:
            hits = sorted(shas[it["sha256"]])
            keys = sorted({k for k, _, _ in hits})
            courts, ckeys, dates = set(), set(), set()
            for k in keys:
                e = ents.get(k) or {}
                courts |= e.get("courts", set())
                ckeys |= e.get("case_keys", set())
                dates |= e.get("dates", set())
            bad = metadata_conflicts(it, courts, ckeys, dates)
            reasons = "sha256 equals known copy: " + ";".join(l for _, l, _ in hits)
            if bad:
                row["flags"] = "METADATA_CONFLICT_WITH_KNOWN_HASH"
                reasons += (" | WARNING: incoming metadata contradicts the known copy (" + "; ".join(bad)
                            + "); check the hash before treating this item as a duplicate")
                if warn:
                    warn(f"WARNING: item {it['item_id']}: sha256 is known but metadata conflicts: " + "; ".join(bad))
            row.update(classification="EXACT_DUPLICATE", matched_corpus_keys=";".join(keys),
                       matched_on="sha256", reasons=reasons)
            out.append(row)
            seen_batch.setdefault(it["sha256"], it)
            continue
        if it["sha256"] in seen_batch:
            first = seen_batch[it["sha256"]]
            bad = metadata_conflicts(it, {first["court"]}, first["case_keys"], {first["date"]})
            reasons = f"sha256 equals earlier incoming item {first['item_id']}; not in corpus"
            if bad:
                row["flags"] = "METADATA_CONFLICT_WITH_KNOWN_HASH"
                reasons += " | WARNING: metadata differs from the earlier item (" + "; ".join(bad) + ")"
                if warn:
                    warn(f"WARNING: item {it['item_id']}: same sha256 as {first['item_id']} but metadata conflicts: "
                         + "; ".join(bad))
            row.update(classification="EXACT_DUPLICATE", matched_corpus_keys="",
                       matched_on="sha256 (within batch)", reasons=reasons)
            out.append(row)
            continue
        seen_batch[it["sha256"]] = it
        # 2. same court + case number (+ date)
        strong, same_case_other_date, fuzzy = [], [], []
        for key in sorted(ents):
            e = ents[key]
            court_ok = (not e["courts"]) or (it["court"] in e["courts"])
            ov = typed_overlap(it["case_keys"], e["case_keys"])
            ov_any = keys_overlap(it["case_keys"], e["case_keys"])
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
            elif ov_any and not ov and court_ok:
                reasons.append("case number " + ",".join(f"{n}/{y}" for _, n, y in ov_any)
                               + " matches only through an UNTYPED number (case type not stated on both sides)")
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
          "case_numbers", "judgment_date", "parties", "provenance", "flags"]


class OutputError(Exception):
    pass


def safe_cell(v):
    s = "" if v is None else str(v)
    return "'" + s if s.startswith(FORMULA_LEAD) else s


def _same_file(a, b):
    try:
        if os.path.realpath(a) == os.path.realpath(b):
            return True
        if os.path.exists(a) and os.path.exists(b):
            if os.path.samefile(a, b):
                return True
            sa, sb = os.stat(a), os.stat(b)
            return (sa.st_dev, sa.st_ino) == (sb.st_dev, sb.st_ino)
    except OSError:
        return False
    return False


def check_out_path(out, inputs, overwrite=False):
    """Raise OutputError if writing the report to `out` could touch an input or an original."""
    for p in inputs:
        if _same_file(out, p):
            raise OutputError(f"--out resolves to input file {p} (refused, even with --overwrite)")
    real = os.path.realpath(out)
    parts = re.split(r"[\\/]+", os.path.abspath(out)) + re.split(r"[\\/]+", real)
    if "curated_originals" in parts:
        raise OutputError("--out lies inside a curated_originals directory (originals are never written)")
    if os.path.isdir(out):
        raise OutputError(f"--out is a directory: {out}")
    parent = os.path.dirname(os.path.abspath(out))
    if not os.path.isdir(parent):
        raise OutputError(f"--out parent directory does not exist: {parent}")
    if os.path.lexists(out) and not overwrite:
        raise OutputError(f"--out already exists: {out} (pass --overwrite to replace a non-input file)")


def write_report(rows, out, inputs=(), overwrite=False):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow({k: safe_cell(r.get(k, "")) for k in FIELDS})
    data = buf.getvalue().encode("utf-8")
    parent = os.path.dirname(os.path.abspath(out))
    fd, tmp = tempfile.mkstemp(prefix=".reconcile-", suffix=".tmp", dir=parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        check_out_path(out, inputs, overwrite)  # re-check immediately before the switch
        if overwrite:
            os.replace(tmp, out)
        else:
            try:
                os.link(tmp, out)  # atomic and never clobbers: fails if out appeared meanwhile
            except FileExistsError:
                raise OutputError(f"--out already exists: {out}")
            except OSError:
                if os.path.lexists(out):
                    raise OutputError(f"--out already exists: {out}")
                os.replace(tmp, out)
    finally:
        if os.path.lexists(tmp):
            os.unlink(tmp)


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
    ap.add_argument("--overwrite", action="store_true",
                    help="replace an existing --out file (never an input file)")
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
    try:
        check_out_path(a.out, inputs, a.overwrite)
    except OutputError as e:
        print(f"ERROR: {e}", file=sys.stderr)
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
    try:
        ents, shas = load_corpus(a.cases, a.identity, a.holdings, a.copies, a.case_source_map)
    except (UnicodeDecodeError, ValueError, KeyError, csv.Error, OSError) as e:
        print(f"ERROR: corpus file unreadable or malformed ({type(e).__name__}: {e}); no report written",
              file=sys.stderr)
        return 2
    out = classify(items, ents, shas, a.party_threshold, warn=lambda m: print(m, file=sys.stderr))
    try:
        write_report(out, a.out, inputs, a.overwrite)
    except (OutputError, OSError) as e:
        print(f"ERROR: {e}; no report written", file=sys.stderr)
        return 2
    counts = {c: sum(1 for r in out if r["classification"] == c) for c in CLASSES}
    print(json.dumps({"items": len(out), "corpus_entities": len(ents), "corpus_copies": len(shas), **counts}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
