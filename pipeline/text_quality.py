"""Text-layer quality detector (Cycle 13, workstream A1).

Decides, page by page, whether a PDF text layer can be trusted for relevance classification, and why
not when it cannot. It exists because the original pipeline accepted garbled text layers
(pipeline.extract.reads_as_english passes a garbled judgment whose e-signature block is English) and
the relevance stage then deleted those judgments as "no military keyword" (C12 finding).

Flags (each a short code, several can apply to one page):

  image_only        no usable text and an image covers most of the page (a scan)
  blank             no text and no image
  few_chars         fewer than MIN_CHARS non-space characters
  control_chars     C0/C1 control characters or U+FFFD in the text (glyph ids emitted without a
                    ToUnicode map: the P&H font defect)
  private_use       Private Use Area code points (broken CMap)
  cid_glyphs        "(cid:NN)" placeholders (broken CMap as rendered by some extractors)
  low_letter_share  letters are under LETTER_SHARE of the non-space characters
  implausible_chars Latin text whose vowel share or symbol share is far outside natural language
  low_dictionary    under DICT_RATIO of the Latin word tokens are common English words
  reversed_order    more word tokens read as English reversed than forwards (right-to-left extraction)
  vertical_order    most lines are one or two characters long (text extracted column-wise)
  missing_page      an empty page in a truncated file (no %%EOF): its bytes are missing (set by assess_pdf)

A page is `usable` when it has no flag. Devanagari text is judged on its script share instead of the
English dictionary (flag `non_latin_ok` is informational, not a defect).

Document-level checks: `truncated` (no %%EOF trailer near the end of the file) and `page_errors`
(a page that cannot be read). These come from the raw bytes, not the text layer.

Pure functions; no network, no writes. Thresholds are constants so a test can pin them.
"""
from __future__ import annotations

import re
import unicodedata

MIN_CHARS = 80
LETTER_SHARE = 0.5
DICT_RATIO = 0.15
CONTROL_SHARE = 0.01
IMAGE_COVER = 0.5
INK_SHARE = 0.001                # share of dark pixels on a low-resolution render: above this, the page is not blank (blank pages measure 0.0)

# Frequent English function words plus words that occur in nearly every Indian judgment. A page of real
# English prose has 35-60% of its word tokens in this list; garbled or mis-mapped text has almost none.
COMMON = set("""
a about above act after against all also an and any appeal appellant applicant application are as at
be been before being below between both but by can case cases civil code concerned could counsel court
date dated decided did do does done dismissed due during each either even facts filed for from further
given government had has have he hearing held her here high him his however i if in india into is it
its judgment justice law learned made may more must no not notice now of on one only or order orders
other our out paid para passed per petition petitioner petitioners present provided provisions reason
record relief respondent respondents rule rules said same section service shall she should since so
state such than that the their them then there these they this those through to under union upon us
was we were when where whether which while who whom will with within without would writ year years
army force officer pension tribunal armed forces ministry defence secretary
""".split())
VOWELS = set("aeiouAEIOU")
_WORD = re.compile(r"[A-Za-z]{2,}")
_CID = re.compile(r"\(cid:\d+\)")


def _is_control(ch: str) -> bool:
    if ch in "\n\r\t\f\v":
        return False
    cat = unicodedata.category(ch)
    return cat == "Cc" or ch == "�"


def _is_pua(ch: str) -> bool:
    o = ord(ch)
    return 0xE000 <= o <= 0xF8FF or 0xF0000 <= o <= 0xFFFFD or 0x100000 <= o <= 0x10FFFD


def _devanagari(ch: str) -> bool:
    return "ऀ" <= ch <= "ॿ"


def text_metrics(text: str) -> dict:
    """Counts used by the page verdict (also reported, so a decision can be audited)."""
    nonspace = [c for c in text if not c.isspace()]
    n = len(nonspace)
    letters = [c for c in nonspace if c.isalpha()]
    latin = [c for c in letters if c.isascii()]
    deva = sum(_devanagari(c) for c in letters)
    words = _WORD.findall(text)
    lw = [w.lower() for w in words]
    fwd = sum(w in COMMON for w in lw)
    rev = sum((w[::-1] in COMMON) and (w not in COMMON) and len(w) > 2 for w in lw)
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    short = sum(len(l) <= 2 for l in lines)
    symbols = sum(1 for c in nonspace if not c.isalnum() and c not in ".,;:()[]-'\"/&%!?*")
    return {
        "chars": n,
        "letters": len(letters),
        "letter_share": round(len(letters) / n, 3) if n else 0.0,
        "control": sum(_is_control(c) for c in text),
        "pua": sum(_is_pua(c) for c in text),
        "cid": len(_CID.findall(text)),
        "devanagari_share": round(deva / len(letters), 3) if letters else 0.0,
        "latin_letters": len(latin),
        "vowel_share": round(sum(c in VOWELS for c in latin) / len(latin), 3) if latin else 0.0,
        "symbol_share": round(symbols / n, 3) if n else 0.0,
        "words": len(words),
        "dict_ratio": round(fwd / len(words), 3) if words else 0.0,
        "reversed_hits": rev,
        "forward_hits": fwd,
        "lines": len(lines),
        "short_line_share": round(short / len(lines), 3) if lines else 0.0,
    }


def page_verdict(text: str, image_cover: float = 0.0, ink: float | None = None) -> dict:
    """Verdict for one page. `image_cover` = share of the page area covered by placed images (0..1);
    `ink` = share of dark pixels in a low-resolution render (None when not measured). A page with
    almost no text but visible ink is a scan even when its images are not reported as placed images
    (inline images, form XObjects, vector-drawn scans): v1 of this detector called such pages blank."""
    m = text_metrics(text)
    flags: list[str] = []
    n = m["chars"]
    if n < MIN_CHARS:
        if image_cover >= IMAGE_COVER or (ink is not None and ink >= INK_SHARE):
            flags.append("image_only")
        elif n == 0:
            flags.append("blank")
        else:
            flags.append("few_chars")
    if n:
        if m["control"] / max(n, 1) >= CONTROL_SHARE:
            flags.append("control_chars")
        if m["pua"] / max(n, 1) >= CONTROL_SHARE:
            flags.append("private_use")
        if m["cid"] >= 3:
            flags.append("cid_glyphs")
    if n >= MIN_CHARS:
        if m["letter_share"] < LETTER_SHARE:
            flags.append("low_letter_share")
        hindi = m["devanagari_share"] >= 0.5
        if hindi:
            flags.append("non_latin_ok")
        elif m["latin_letters"] >= 200:
            if not (0.22 <= m["vowel_share"] <= 0.55) or m["symbol_share"] > 0.25:
                flags.append("implausible_chars")
            if m["words"] >= 20:
                if m["reversed_hits"] > max(3, m["forward_hits"]):
                    flags.append("reversed_order")
                elif m["dict_ratio"] < DICT_RATIO:
                    flags.append("low_dictionary")
        if m["lines"] >= 20 and m["short_line_share"] > 0.5:
            flags.append("vertical_order")
    defects = [f for f in flags if f != "non_latin_ok"]
    return {"usable": not defects, "flags": flags, "metrics": m}


def image_cover_of(page) -> float:
    """Share of a PyMuPDF page's area covered by placed images (capped at 1)."""
    area = abs(page.rect) or 1.0
    covered = 0.0
    try:
        for info in page.get_image_info():
            x0, y0, x1, y1 = info["bbox"]
            covered += max(0.0, x1 - x0) * max(0.0, y1 - y0)
    except Exception:
        return 0.0
    return min(1.0, covered / area)


def ink_share(page, dpi: int = 30) -> float:
    """Share of dark (< 160 of 255) pixels in a grey render of a PyMuPDF page."""
    import pymupdf
    pix = page.get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY, alpha=False)
    data = pix.samples
    return sum(1 for b in data if b < 160) / max(1, len(data))


def has_eof(raw: bytes) -> bool:
    return b"%%EOF" in raw[-2048:]


def assess_pdf(path) -> dict:
    """Page verdicts plus document checks for one PDF. Never raises on a damaged file."""
    import pymupdf  # local import: the pure functions above need no PDF library

    from .extract import page_text

    raw = open(path, "rb").read()
    out = {"truncated": not has_eof(raw), "page_errors": [], "pages": [], "open_error": None}
    try:
        doc = pymupdf.open(stream=raw, filetype="pdf")
    except Exception as e:  # does not open at all
        out["open_error"] = f"{type(e).__name__}: {e}"[:200]
        return out
    with doc:
        try:
            n = doc.page_count
        except Exception as e:  # damaged page tree (typical of truncated downloads)
            out["open_error"] = f"page count unreadable: {type(e).__name__}: {e}"[:200]
            return out
        for i in range(n):
            try:
                page = doc[i]
                text, _ = page_text(page)
                cover = image_cover_of(page)
                few = len(re.sub(r"\s", "", text)) < MIN_CHARS
                v = page_verdict(text, cover, ink_share(page) if few and cover < IMAGE_COVER else None)
            except Exception as e:
                out["page_errors"].append(i + 1)
                v = {"usable": False, "flags": ["page_error"], "metrics": {}, "error": str(e)[:120]}
            v["page"] = i + 1
            out["pages"].append(v)
    if out["truncated"]:
        # In a file without its %%EOF trailer, an empty page is a page whose bytes are missing (MuPDF rebuilds a
        # page tree with phantom pages past the cut), not a blank page: it is a defect, never "no content".
        for v in out["pages"]:
            if v["flags"] == ["blank"]:
                v["flags"] = ["missing_page"]
                v["usable"] = False
    return out


def document_summary(assessment: dict) -> dict:
    """Roll page verdicts up to one document decision used by pipeline.relevance_states."""
    pages = assessment.get("pages", [])
    n = len(pages)
    bad = [p["page"] for p in pages if not p["usable"] and "blank" not in p["flags"]]
    blank = [p["page"] for p in pages if "blank" in p["flags"]]
    flags = sorted({f for p in pages for f in p["flags"] if f not in ("non_latin_ok",)})
    usable = [p["page"] for p in pages if p["usable"]]
    content = n - len(blank)
    share = len(usable) / content if content else 0.0
    if assessment.get("open_error") or n == 0:
        verdict = "EXTRACTION_FAILED"
    elif assessment.get("page_errors"):
        verdict = "EXTRACTION_FAILED"
    elif assessment.get("truncated"):
        verdict = "SOURCE_INCOMPLETE"          # a truncated file is never TEXT_OK, whatever its readable pages say
    elif not bad:
        verdict = "TEXT_OK"
    else:
        verdict = "OCR_REQUIRED"
    return {"verdict": verdict, "pages": n, "usable_pages": len(usable), "unusable_pages": bad,
            "blank_pages": blank, "usable_share": round(share, 3), "flags": flags,
            "truncated": bool(assessment.get("truncated"))}
