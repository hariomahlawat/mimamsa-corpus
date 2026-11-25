"""Explicit relevance pipeline states (Cycle 13, workstream A1). Supersedes the deletion rule.

The original stage (pipeline.judgments.run) has two outcomes for a judgment with no military keyword:
it is "rejected" and its metadata, text and raw file are DELETED. A garbled or image-only text layer
therefore looks exactly like an unrelated civil case, and relevant writs were deleted (C12 finding:
all 12 Punjab and Haryana writs against AFT orders acquired in C12 had been deleted this way).

This module replaces that single test with explicit states:

  RELEVANT                  keyword pass relevant, or borderline confirmed by the second check
  IRRELEVANT                usable text, no keyword, and the second check finds no armed-forces context
  INSUFFICIENT_TEXT         text was read (layer or OCR) but too little usable text to judge
  OCR_REQUIRED              the text layer is unusable (garbled, broken CMap, image-only) and no OCR yet
  EXTRACTION_FAILED         the file could not be opened or a page could not be read
  CLASSIFICATION_UNCERTAIN  weak or conflicting signals (borderline keywords, or one context family)
  SOURCE_INCOMPLETE         the file is truncated (no %%EOF) and the readable part has no keyword
  MANUAL_REVIEW_REQUIRED    no keyword, but strong armed-forces context: a possible false negative

The rule this module enforces: a judgment is never IRRELEVANT because its text could not be
extracted. IRRELEVANT needs a usable text layer (or usable OCR text) over at least
MIN_USABLE_SHARE of its content pages and at least MIN_WORDS words.

Only IRRELEVANT may lead to removal from the corpus, and even then the new module removes nothing
itself: callers record the state. Uncertain and review states are never ingested automatically.

The second check is a fixed, auditable lexicon of armed-forces context families (ranks, service
headquarters, service pension and medical-board vocabulary, AFT proceedings). It returns the families
and the matched strings, so every decision can be traced. It is a rule, not a model.
"""
from __future__ import annotations

import re

from .judgments import classify, keyword_counts

STATES = ("RELEVANT", "IRRELEVANT", "INSUFFICIENT_TEXT", "OCR_REQUIRED", "EXTRACTION_FAILED",
          "CLASSIFICATION_UNCERTAIN", "SOURCE_INCOMPLETE", "MANUAL_REVIEW_REQUIRED")
MIN_USABLE_SHARE = 0.8
MIN_WORDS = 150
STRONG_FAMILIES = 2

# family -> pattern. Families, not single words, are counted, so one repeated word cannot decide.
CONTEXT = {
    "aft_proceeding": r"\bArmed\s+Forces\s+Tribunal\b|\bAFT\b|\bO\.?\s?A\.?\s+No\.?\s*\d+\s+of\s+\d{4}\b.{0,80}\bTribunal\b",
    "court_martial": r"\bcourts?[\s-]+martial\b|\bsummary\s+of\s+evidence\b|\bG\.?C\.?M\b|\bS\.?G\.?C\.?M\b",
    "service_statute": r"\b(?:Army|Air\s+Force|Navy)\s+(?:Act|Rules|Regulations)\b|\bRegulations\s+for\s+the\s+(?:Army|Air\s+Force|Navy)\b",
    "other_rank": r"\b(?:Sepoy|Sep\.|Havildar|Hav\.|Naik|Lance\s+Naik|L/Nk|Subedar|Sub\.\s+Maj|Naib\s+Subedar|Nb\.?\s?Sub|Risaldar|Jemadar|Rifleman|Gunner|Sapper|Signalman|Craftsman|Sowar|Jawan|Airman|Sergeant|Corporal|Petty\s+Officer|Sailor|Seaman)\b",
    "officer_rank": r"\b(?:Lt\.?\s?Col\.?|Lieutenant\s+Colonel|Colonel|Brigadier|Major\s+General|Lieutenant\s+General|Lt\.?\s?Gen\.?|Maj\.?\s?Gen\.?|Capt\.?|Captain|Wing\s+Commander|Wg\.?\s?Cdr\.?|Squadron\s+Leader|Sqn\.?\s?Ldr\.?|Flight\s+Lieutenant|Flt\.?\s?Lt\.?|Group\s+Captain|Gp\.?\s?Capt\.?|Air\s+Commodore|Air\s+Marshal|Lieutenant\s+Commander|Lt\.?\s?Cdr\.?|Commander|Vice\s+Admiral|Rear\s+Admiral)\b",
    "service_hq": r"\bIndian\s+(?:Army|Air\s+Force|Navy)\b|\bArmy\s+Headquarters\b|\bArmy\s+HQ\b|\bIntegrated\s+Headquarters\b|\bChief\s+of\s+(?:the\s+)?(?:Army|Air|Naval)\s+Staff\b|\bRecords?\s+Office\b|\bRegiment(?:al)?\b|\bBattalion\b|\bCommand(?:ing)?\s+Officer\b|\bUnit\b.{0,40}\bArmy\b",
    "service_pension": r"\bdisability\s+pension\b|\bservice\s+pension\b|\bEntitlement\s+Rules\b|\binvalid(?:ed|ment|ing)\b|\b(?:Release|Invaliding|Re-?survey)\s+Medical\s+Board\b|\bP\.?C\.?D\.?A\.?\b|\bPension\s+Regulations\s+for\s+the\b|\battributable\s+to\s+(?:or\s+aggravated\s+by\s+)?military\s+service\b",
    "ex_servicemen": r"\bex[\s-]+servicem[ae]n\b|\bEx[\s-]+(?:Sep|Hav|Nk|Sub|Capt|Maj|Col)\b",
    "defence_ministry": r"\bMinistry\s+of\s+Defence\b|\bDefence\s+Services\b|\bDepartment\s+of\s+Ex[\s-]+Servicemen\s+Welfare\b",
}
_CTX = {k: re.compile(v, re.I) for k, v in CONTEXT.items()}
# "AFT" counts only in capitals (as in pipeline.judgments); the rest of the family is case-insensitive
_CTX["aft_proceeding"] = re.compile(r"(?i:\bArmed\s+Forces\s+Tribunal\b)|\bAFT\b|(?i:\bO\.?\s?A\.?\s+No\.?\s*\d+\s+of\s+\d{4}\b.{0,80}\bTribunal\b)")
# families that on their own are too generic to signal armed-forces service law
WEAK = {"officer_rank", "defence_ministry", "service_hq"}


def second_check(text: str) -> dict:
    """Armed-forces context families found in `text`, with up to three matched strings each."""
    found = {}
    for fam, rx in _CTX.items():
        hits = [re.sub(r"\s+", " ", m.group(0))[:60] for m in rx.finditer(text)]
        if hits:
            found[fam] = {"count": len(hits), "examples": sorted(set(hits))[:3]}
    strong = [f for f in found if f not in WEAK]
    return {"families": sorted(found), "strong_families": sorted(strong), "detail": found,
            "score": len(strong) + 0.5 * (len(found) - len(strong))}


def decide(*, text: str | None, quality: dict | None, extraction_error: str | None = None,
           truncated: bool = False, ocr_done: bool = False) -> dict:
    """One state for one judgment.

    text        the best text available (OCR text when OCR ran, else the text layer), page markers allowed
    quality     pipeline.text_quality.document_summary() of THAT text (layer or OCR)
    """
    out = {"state": None, "keyword_status": None, "keywords": {}, "second_check": None, "reasons": []}
    if extraction_error:
        out.update(state="EXTRACTION_FAILED", reasons=[f"extraction failed: {extraction_error[:120]}"])
        return out
    text = text or ""
    q = quality or {}
    counts = keyword_counts(text) if text else {}
    kw = classify(counts) if text else "not_checked"
    sc = second_check(text) if text else {"families": [], "strong_families": [], "detail": {}, "score": 0}
    out.update(keyword_status=kw, keywords=counts, second_check=sc)
    words = len(re.findall(r"[A-Za-z\u0900-\u097f]{2,}", text))
    usable_share = q.get("usable_share", 0.0)
    text_ok = q.get("verdict") == "TEXT_OK" or (usable_share >= MIN_USABLE_SHARE)

    if kw == "relevant":                       # positive evidence is trusted even from imperfect text
        out.update(state="RELEVANT", reasons=["keyword pass relevant"])
        return out
    if kw == "borderline":
        if len(sc["strong_families"]) >= STRONG_FAMILIES:
            out.update(state="RELEVANT", reasons=["keyword borderline; second check strong"])
        else:
            out.update(state="CLASSIFICATION_UNCERTAIN", reasons=["keyword borderline; second check weak"])
        return out
    # no keyword at all (or no text): only now does text quality decide
    if truncated:
        out.update(state="SOURCE_INCOMPLETE", reasons=["file truncated (no %%EOF) and no keyword in the readable part"])
        return out
    if not text_ok:
        if not ocr_done:
            out.update(state="OCR_REQUIRED",
                       reasons=[f"text layer unusable on pages {q.get('unusable_pages', [])[:10]} "
                                f"(flags {q.get('flags', [])})"])
        else:
            out.update(state="INSUFFICIENT_TEXT",
                       reasons=[f"OCR text usable share {usable_share} < {MIN_USABLE_SHARE}"])
        return out
    if words < MIN_WORDS:
        out.update(state="INSUFFICIENT_TEXT", reasons=[f"only {words} words of usable text"])
        return out
    if len(sc["strong_families"]) >= STRONG_FAMILIES:
        out.update(state="MANUAL_REVIEW_REQUIRED",
                   reasons=[f"no keyword but armed-forces context {sc['strong_families']}: possible false negative"])
    elif sc["families"]:
        out.update(state="CLASSIFICATION_UNCERTAIN", reasons=[f"no keyword; weak context {sc['families']}"])
    else:
        out.update(state="IRRELEVANT", reasons=["usable text, no keyword, no armed-forces context"])
    return out


def legacy_relevance(decision: dict, note_prefix: str = "") -> dict:
    """The schema's `relevance` object for a decision. Only RELEVANT maps to a positive status;
    every non-final state is `not_checked` with the state in the note, never `rejected`."""
    kw = decision.get("keyword_status")
    counts = decision.get("keywords") or {}
    if decision["state"] == "RELEVANT":
        status = "relevant" if kw == "relevant" else "borderline"
    elif decision["state"] == "IRRELEVANT":
        status = "rejected"
    else:
        status = "not_checked"
    note = f"{note_prefix}C13 state {decision['state']}: {'; '.join(decision['reasons'])}"
    return {"status": status, "hits": sum(counts.values()), "keywords": counts, "note": note[:600]}


def may_remove(decision: dict) -> bool:
    """Only an IRRELEVANT decision may ever lead to removal; every other state keeps the file."""
    return decision.get("state") == "IRRELEVANT"
