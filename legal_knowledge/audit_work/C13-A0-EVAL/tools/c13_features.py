#!/usr/bin/env python3
"""C13-A0 stage 1: deterministic text features for every judicial record (no model, no extractor output).

Inputs (read-only):
  * corpus commit ad77758d: data/manifest.csv (type == judgment), data/meta/<doc_id>.json, data/text/<doc_id>.txt;
  * the 22 C12 judicial additions (18 ingested + 4 held-original derived records), read from a local copy of the
    pinned HF commits and verified against judicial_recovery_c12/STAGED_MANIFEST.csv sha256 before use.
Output: outputs/frame/TEXT_FEATURES.csv (one row per record). The features are signals for stratification and text
quality; they are not legal findings. The rules are fixed here and pre-registered in PROTOCOL_C13.md.

  python -I -B c13_features.py [--check]
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from c13_common import (C12, OUT, CorpusBlobs, additions_cache_dir, read_csv, render_csv, sha256_bytes,  # noqa: E402
                        split_pages, write_or_check, argv_check)

USABLE_PAGE_MIN_LETTERS = 200      # a page has usable text if it has >= 200 letters ...
USABLE_PAGE_MIN_SHARE = 0.50       # ... and letters are >= 50% of its non-space characters (C12 letter-share test)
OPERATIVE_TAIL_SHARE = 0.35        # party-specific cues are looked for in the last 35% of the text (min 6,000 chars)

PARTY_RE = re.compile(
    r"(?:\b(?:qua|in respect of|so far as|insofar as|in so far as|as regards|in relation to|in the case of)\s+"
    r"(?:the\s+)?(?:petitioner|respondent|appellant|applicant)s?\s*(?:no\.?|nos\.?)\s*\d)"
    r"|(?:\b(?:petitioner|respondent|appellant|applicant)s?\s*(?:no\.?|nos\.?)\s*\d+(?:\s*(?:,|and|&|to)\s*\d+)*"
    r"[^.]{0,80}?\b(?:is|are|stands?|shall be|be)\s+(?:allowed|dismissed|disposed|entitled|granted|rejected|set aside))"
    r"|(?:\bappeals?\s+(?:filed\s+)?(?:by|of)\s+(?:the\s+)?(?:appellant|respondent|petitioner)s?\s*(?:no\.?|nos\.?)\s*\d)"
    r"|(?:\b(?:allowed|dismissed)\s+(?:only\s+)?(?:qua|against|in favour of)\s+(?:the\s+)?"
    r"(?:petitioner|respondent|appellant)s?\s*(?:no\.?|nos\.?)\s*\d)",
    re.I)
MULTI_OPINION_RE = re.compile(
    r"\(\s*dissenting\s*\)|\bdissenting (?:opinion|judgment|note)\b|\bconcurring (?:opinion|judgment)\b"
    r"|\bI have had the (?:advantage|benefit|privilege) of (?:reading|going through|perusing)\b"
    r"|\b(?:separate|supplementing) (?:opinion|judgment)\b|\bI (?:respectfully )?(?:agree|concur) with\b"
    r"|\bI regret (?:my inability|that I am unable) to agree\b", re.I)
CONNECTED_RE = re.compile(
    r"\bwith\s+(?:c\.?a\.?|civil appeal|w\.?p\.?|writ petition|cwp|slp|lpa|crl\.?)\b"
    r"|\b(?:and|&)\s+(?:other\s+)?connected (?:matters|cases|petitions|appeals)\b"
    r"|\b(?:batch of|bunch of|group of) (?:writ petitions|petitions|appeals|cases)\b"
    r"|\bcommon (?:judgment|order)\b", re.I)


def page_stats(text):
    pages = split_pages(text)
    n_usable = 0
    letters_total = nonspace_total = 0
    for _, t in sorted(pages.items()):
        letters = sum(ch.isalpha() for ch in t)
        nonspace = sum(not ch.isspace() for ch in t)
        letters_total += letters
        nonspace_total += nonspace
        if letters >= USABLE_PAGE_MIN_LETTERS and nonspace and letters / nonspace >= USABLE_PAGE_MIN_SHARE:
            n_usable += 1
    share = letters_total / nonspace_total if nonspace_total else 0.0
    return len(pages), n_usable, letters_total, round(share, 4)


def signals(text):
    tail_len = max(int(len(text) * OPERATIVE_TAIL_SHARE), 6000)
    tail = text[-tail_len:]
    head = text[:4000]
    return (len(PARTY_RE.findall(tail)), len(MULTI_OPINION_RE.findall(text)), len(CONNECTED_RE.findall(head)))


def feature_row(doc_id, population, meta_bytes, text_bytes, text_source):
    row = dict(doc_id=doc_id, population=population, meta_sha256=sha256_bytes(meta_bytes) if meta_bytes else "",
               text_source=text_source, text_present=bool(text_bytes), text_sha256="", text_pages=0,
               pages_usable=0, letters=0, letter_share=0.0, party_specific_cues=0, multi_opinion_cues=0,
               connected_matter_cues=0)
    if text_bytes:
        text = text_bytes.decode("utf-8", errors="replace")
        n, u, letters, share = page_stats(text)
        p, m, c = signals(text)
        row.update(text_sha256=sha256_bytes(text_bytes), text_pages=n, pages_usable=u, letters=letters,
                   letter_share=share, party_specific_cues=p, multi_opinion_cues=m, connected_matter_cues=c)
    return row


def additions():
    """Yield (doc_id, population, meta_bytes, text_bytes, text_source) for the 22 C12 additions, sha-verified."""
    staged = {r["hf_path"].rsplit("/", 1)[-1]: r for r in read_csv(C12 / "judicial_recovery_c12" / "STAGED_MANIFEST.csv")
              if r["kind"] in ("meta", "text")}
    cache = additions_cache_dir()
    log = read_csv(C12 / "judicial_recovery_c12" / "INGESTION_LOG.csv")
    for r in log:
        if r["action"] not in ("INGESTED", "DERIVED_TEXT_AND_META_TO_VERSIONED_PATH"):
            continue
        pop = "C12_INGESTED" if r["action"] == "INGESTED" else "C12_HELD_ORIGINAL_DERIVED"
        out = []
        for kind, ext in (("meta", ".json"), ("text", ".txt")):
            name = r["doc_id"] + ext
            if name not in staged:
                out.append(None)
                continue
            b = (cache / kind / name).read_bytes()
            if sha256_bytes(b) != staged[name]["sha256"]:
                raise SystemExit(f"C12 addition {name}: sha256 differs from STAGED_MANIFEST.csv")
            out.append(b)
        src = ("hf:" + staged[r["doc_id"] + ".txt"]["hf_path"]) if out[1] else "none (no text written: text layer unusable)"
        yield r["doc_id"], pop, out[0], out[1], src


def build():
    blobs = CorpusBlobs()
    try:
        man = blobs.get("data/manifest.csv").decode("utf-8")
        import csv, io
        docs = sorted(r["doc_id"] for r in csv.DictReader(io.StringIO(man)) if r["type"] == "judgment")
        rows = []
        for d in docs:
            mb = blobs.get(f"data/meta/{d}.json")
            meta = json.loads(mb)
            tp = meta.get("text_path")
            tb = blobs.get(tp) if tp else None
            rows.append(feature_row(d, "BASE_AD77758D", mb, tb, f"git:{tp}" if tb else "none"))
    finally:
        blobs.close()
    rows += [feature_row(*a) for a in additions()]
    rows.sort(key=lambda r: r["doc_id"])
    return {"frame/TEXT_FEATURES.csv": render_csv(rows)}


def main():
    return write_or_check(build(), OUT, argv_check(), "c13_features")


if __name__ == "__main__":
    sys.exit(main())
