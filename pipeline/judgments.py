"""Judgment metadata from the open-data indexes, and the relevance + citation stage.

build_docs()  one metadata record per downloaded judgment, from the index row the crawler kept.
              Only what the index states is filled; the rest is null / empty.
run()         suspended during C14 non-destructive adoption; no source or derivative writes.
"""
from __future__ import annotations

import csv
import json
import re
from collections import Counter

from .common import SCHEMA_VERSION, Paths, iso_date, slug, write_json
from .records import section_key

PORTAL = {"indian-supreme-court-judgments": "the Supreme Court's e-SCR portal",
          "indian-high-court-judgments": "the eCourts judgments portal"}

# ---- relevance: the keyword list is the brief's (pipeline stage 3)
KEYWORDS = {
    "army act": r"\barmy\s+act\b",
    "air force act": r"\bair\s+force\s+act\b",
    "navy act": r"\bnavy\s+act\b",
    "armed forces tribunal": r"\barmed\s+forces\s+tribunal\b|\bAFT\b",
    "court martial": r"\bcourt[\s-]+martial\b|\bcourts[\s-]+martial\b",
    "summary of evidence": r"\bsummary\s+of\s+evidence\b",
    "disability pension": r"\bdisability\s+pension\b",
    "entitlement rules": r"\bentitlement\s+rules\b",
    "invalided": r"\binvalided\b|\binvalidment\b|\binvalidation\b|\binvaliding\b",
    "release medical board": r"\brelease\s+medical\s+board\b",
}
_KW = {k: re.compile(v, re.I) for k, v in KEYWORDS.items()}
# the phrase in any case ("Armed Forces Tribunal" is the usual spelling); the abbreviation only in capitals
_KW["armed forces tribunal"] = re.compile(r"(?i:\barmed\s+forces\s+tribunal\b)|\bAFT\b")
TOPIC_OF = {"court martial": "court_martial", "summary of evidence": "summary_of_evidence",
            "disability pension": "disability_pension", "entitlement rules": "entitlement_rules",
            "invalided": "invalidment", "release medical board": "medical_board"}

# ---- statute references. Each Act: (normalised name, doc_id in this corpus, pattern for its name)
ACTS = [
    ("Army Act 1950", "act-army-1950", r"Army\s+Act(?:,?\s*1950)?"),
    ("Air Force Act 1950", "act-air-force-1950", r"Air\s+Force\s+Act(?:,?\s*1950)?"),
    ("Navy Act 1957", "act-navy-1957", r"Navy\s+Act(?:,?\s*1957)?"),
    ("Armed Forces Tribunal Act 2007", "act-armed-forces-tribunal-2007",
     r"Armed\s+Forces\s+Tribunal\s+Act(?:,?\s*2007)?|AFT\s+Act(?:,?\s*2007)?"),
    ("Indian Penal Code 1860", "act-ipc-1860", r"Indian\s+Penal\s+Code(?:,?\s*1860)?|I\.?P\.?C\.?"),
    ("Code of Criminal Procedure 1973", "act-crpc-1973",
     r"Code\s+of\s+Criminal\s+Procedure(?:,?\s*1973)?|Criminal\s+Procedure\s+Code(?:,?\s*1973)?|Cr\.?\s?P\.?C\.?"),
    ("Indian Evidence Act 1872", "act-evidence-1872", r"(?:Indian\s+)?Evidence\s+Act(?:,?\s*1872)?"),
    ("Bharatiya Nyaya Sanhita 2023", "act-bns-2023", r"Bharatiya\s+Nyaya\s+Sanhita(?:,?\s*2023)?|BNS"),
    ("Bharatiya Nagarik Suraksha Sanhita 2023", "act-bnss-2023", r"Bharatiya\s+Nagarik\s+Suraksha\s+Sanhita(?:,?\s*2023)?|BNSS"),
    ("Bharatiya Sakshya Adhiniyam 2023", "act-bsa-2023", r"Bharatiya\s+Sakshya\s+Adhiniyam(?:,?\s*2023)?|BSA"),
]
_SEC = r"(?:[Ss]ections?|[Ss]ec\.|[Ss]\.|u/s\.?|U/s\.?)\s*(\d{1,3}[A-Z]{0,2}(?:\s*\(\w{1,3}\))*)"
_REF = [(name, doc_id, re.compile(rf"{_SEC}\s*(?:,|and|&|/|read\s+with|r/w|to|\d|[A-Z]|\(|\)|\s)*?\s*of\s+(?:the\s+)?(?:said\s+)?({pat})\b"),
         re.compile(rf"\b({pat})\b")) for name, doc_id, pat in ACTS]


# --------------------------------------------------------------------- records
def _outcome(text: str | None) -> str | None:
    t = (text or "").lower()
    if not t:
        return None
    if "partly allowed" in t or "partially allowed" in t or "allowed in part" in t:
        return "partly_allowed"
    for word, out in (("dismiss", "dismissed"), ("allowed", "allowed"), ("remand", "remanded"), ("disposed", "disposed")):
        if word in t:
            return out
    return None


def _names(value: str | None) -> list[str]:
    v = (value or "").strip()
    if not v or v.lower() == "none" or re.search(r"\b(cases|bench|division|roster|pertaining|single)\b", v, re.I):
        return []
    return [n.strip() for n in re.split(r"\s*,\s*|\s+and\s+|\s*&\s*", v) if n.strip()]


def build_doc(row, meta: dict, base: dict) -> dict:
    """`row`: the crawl-state row; `meta`: its stored metadata; `base`: the common document fields."""
    ix, dataset, year = meta.get("index") or {}, meta["dataset"], meta.get("year")
    is_sc = dataset == "indian-supreme-court-judgments"
    stem = re.sub(r"\.pdf$", "", meta.get("filename") or "", flags=re.I)
    title = (ix.get("title") or meta.get("title") or stem).strip()
    prov = {"title": "crawler", "issue_date": "crawler", "judges": "crawler", "outcome": "rule"}
    if is_sc:
        doc_id = f"sc-{year}-{slug(ix.get('petitioner') or title, 30)}-{slug(ix.get('nc_display') or ix.get('path') or stem, 30)}"
        neutral = ix.get("case_id") if re.fullmatch(r"\d{4} INSC \d+", ix.get("case_id") or "") else None
        parties = {"petitioner": [ix["petitioner"]] if ix.get("petitioner") else [],
                   "respondent": [ix["respondent"]] if ix.get("respondent") else []}
        case_numbers, court = [], "Supreme Court of India"
        reported = [ix["citation"]] if (ix.get("citation") or "").strip() else []
        decided = iso_date(ix.get("decision_date"))
        record_id = ix.get("cnr") or ix.get("path") or stem
    else:
        m = re.match(r"^\s*([A-Za-z.() ]{1,25}/\d+/\d{4})\s+of\s+(.*)$", title, re.S)
        case_no = m.group(1).strip() if m else None
        doc_id = f"hc-{meta['court_key']}-{year}-{slug(case_no or '', 30)}-{slug(stem, 45)}".replace("--", "-")
        sides = re.split(r"\s+V[sS]\.?\s+", m.group(2) if m else title, maxsplit=1)
        parties = {"petitioner": [sides[0].strip()], "respondent": [sides[1].strip()]} if len(sides) == 2 else None
        case_numbers, court, neutral, reported = ([case_no] if case_no else []), meta.get("court_name") or ix.get("court"), None, []
        decided = iso_date((ix.get("decision_date") or "")[:10])
        record_id = ix.get("cnr") or stem
        prov.update({"parties": "rule", "case_numbers": "rule"})
    return {**base,
            "doc_id": doc_id[:120].rstrip("-"), "doc_type": "judgment", "title": title,
            "number": neutral or (case_numbers[0] if case_numbers else None),
            "issuing_authority": court, "issue_date": decided, "effective_date": None,
            "status": "unknown", "status_note": None, "status_as_of": (row["fetched_at"] or "")[:10] or None,
            "language": "en" if is_sc else None, "parent_doc_id": None, "original_filename": meta.get("filename"),
            "source_record": {"system": f"aws-open-data:{dataset}", "record_id": record_id,
                              "collection": meta.get("bench"), "act_id": None, "handle": None, "listing_raw_path": None},
            "curation_note": (f"From the AWS Open Data bucket '{dataset}' (CC-BY-4.0, maintained by P. Vanga / Dattam Labs), "
                              f"a copy of records from {PORTAL.get(dataset, 'an official court portal')}. "
                              "Pre-selected from the index by party names."),
            "court": court, "bench": None, "case_numbers": case_numbers, "neutral_citation": neutral,
            "reported_citations": reported, "parties": parties,
            "judges": _names(ix.get("judge")), "outcome": _outcome(ix.get("disposal_nature")),
            "statutes_cited": [], "cases_cited": [], "topics": [], "relevance": None,
            "field_provenance": prov}


# ------------------------------------------------------------------- relevance
OCR_TRUST = 70.0                 # mean OCR confidence below this: a "no keyword" result is not trusted

def keyword_counts(text: str) -> dict[str, int]:
    return {k: n for k, rx in _KW.items() if (n := len(rx.findall(text)))}


def classify(counts: dict[str, int]) -> str:
    total = sum(counts.values())
    if total == 0:
        return "rejected"
    return "relevant" if (len(counts) >= 2 or total >= 3) else "borderline"


def statute_refs(text: str, have_section) -> tuple[list[dict], list[tuple[str, str, str]]]:
    """(statutes_cited entries, [(target id, raw reference, evidence sentence)])."""
    flat = re.sub(r"\[\[page \d+\]\]", " ", text)
    flat = re.sub(r"\s+", " ", flat)
    cited: dict[tuple, dict] = {}
    edges: dict[str, tuple[str, str, str]] = {}
    for name, doc_id, with_section, bare in _REF:
        for m in with_section.finditer(flat):
            number = re.match(r"\d{1,3}[A-Z]{0,2}", m.group(1)).group(0)
            raw = re.sub(r"\s+", " ", m.group(0)).strip()
            cited.setdefault((name, number), {"act": name, "act_doc_id": doc_id, "section": number, "raw": raw[:200]})
            target = f"{doc_id}#{section_key(number)}"
            if have_section(doc_id, number) and target not in edges:
                a, b = max(0, m.start() - 150), min(len(flat), m.end() + 150)
                edges[target] = (target, raw[:200], flat[a:b].strip())
        if not any(k[0] == name for k in cited):
            m = bare.search(flat)
            if m and len(m.group(1)) > 4:                 # a bare abbreviation alone (IPC, BNS) is not recorded
                cited[(name, None)] = {"act": name, "act_doc_id": doc_id, "section": None, "raw": m.group(1)}
    return list(cited.values())[:300], list(edges.values())[:300]


def load_excluded(paths: Paths) -> dict[str, dict]:
    """sha256 -> log entry of every judgment removed as not about the armed forces."""
    p = paths.data / "excluded_judgments.jsonl"
    if not p.exists():
        return {}
    return {e["sha256"]: e for e in (json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip())}


def run(paths: Paths) -> dict:
    """Legacy mutation entry point is suspended during C14 adoption.

    Use shadow_assessment.assess on individually approved read-only inputs.
    Do not return a successful stage result while downstream consumers still
    expect mutable legacy metadata, relations and relevance.csv.
    """
    raise RuntimeError("C14 corpus mutation hold: legacy relevance is suspended")
