"""Mimamsa C13 judicial outcome extractor V4: quoted versus operative language (V3 quote spans; V4 operative-resumption model added below).

All values are AUTOMATED CANDIDATES read from a PDF text layer; nothing is legally verified."""
import bisect
import re



# ------------------------------------------------------------------ quotes
_QUOTE_INTRO_RE = re.compile(
    r"\b(held|observed|opined|stated|noted|remarked|reads?|read|laid\s+down|provides?|extracted|reproduced|quoted|"
    r"said|ruled|directed|recorded|is\s+as\s+follows|as\s+under|as\s+follows|thus|in\s+the\s+following\s+words|"
    r"which\s+is\s+as\s+under)\b[^.:\n]{0,80}?:\s*[-–]?", re.I)
_OWN_ORDER_BEFORE_RE = re.compile(r"(we|court)\s+(hereby\s+)?(pass|issue|make|direct|order)|following\s+(order|directions?)"
                                  r"|we\s+order|in\s+the\s+result|accordingly", re.I)


_RESUME_RE = re.compile(
    r"\n[ \t]*\n[ \t]*(?:\d{1,3}\s*\.\s*)?(?=(?:For\s+the\s+(?:foregoing|aforesaid|above|reasons)|In\s+view\s+of|Accordingly|In\s+the\s+result|"
    r"Resultantly|Consequently|Hence|Thus,|Therefore,|In\s+the\s+(?:facts|light|instant|present)|We\s+(?:are|have|find|do|may|would|"
    r"therefore|accordingly|hold|see|also|now)|This\s+(?:petition|appeal|writ)|The\s+(?:petition|appeal|writ\s+petition)\s+is|"
    r"Applying|Having\s+regard|Coming\s+to|Reverting|Adverting|Admittedly|In\s+our\s+(?:view|opinion|considered)|Now,?|So\s+far)\b)")


def quote_spans(text, para_starts_fn=None):
    """Return sorted list of (start, end, kind, intro_start) quoted spans.
    kind: 'marked' (curly or straight quotation marks) or 'intro_block' (unmarked block after 'held as under:')."""
    spans = []
    i = 0
    n = len(text)
    while True:
        o = text.find("“", i)
        if o < 0:
            break
        c = text.find("”", o + 1)
        if c < 0 or c - o > 15000:
            i = o + 1
            continue
        spans.append((o, c + 1, "marked"))
        i = c + 1
    # straight quotes: decide opening/closing from the neighbouring characters, then pair open -> next close
    opened = None
    for m in re.finditer('"', text):
        p = m.start()
        prv = text[p - 1] if p > 0 else " "
        nxt = text[p + 1] if p + 1 < n else " "
        is_open = (prv.isspace() or prv in "([:-\u2014") and not nxt.isspace()
        is_close = (not prv.isspace()) and (nxt.isspace() or nxt in ".,;:)-\u2014")
        if is_open and not is_close:
            opened = p
        elif is_close and opened is not None:
            if p - opened <= 8000:
                spans.append((opened, p + 1, "marked"))
            opened = None
    # v3: some text layers carry the curly quotes as '<' (open) and '=' (close); pair them when that encoding is
    # evident (several '<Word' openings and 'word=' closings) and no curly quotes are present
    if "\u201c" not in text and len(re.findall(r"(?:^|\s)<\s?[A-Za-z0-9]", text)) >= 2 and \
            len(re.findall(r"[A-Za-z0-9.,;)]=(?=\s|$)", text)) >= 2:
        i = 0
        while True:
            mo = re.compile(r"(?:^|(?<=\s))<(?=\s?[A-Za-z0-9])").search(text, i)
            if not mo:
                break
            mc = re.compile(r"(?<=[A-Za-z0-9.,;)?!])=(?=\s|$)").search(text, mo.end())
            mo2 = re.compile(r"(?:^|(?<=\s))<(?=\s?[A-Za-z0-9])").search(text, mo.end(), mc.start() if mc else mo.end())
            if not mc or mc.start() - mo.start() > 4000 or mo2 or \
                    re.search(r"\n[ \t]*\d{1,3}[ \t]*\.[ \t]+[A-Z]", text[mo.end():mc.start()]):
                i = mo.end()
                continue
            spans.append((mo.start(), mc.end(), "marked"))
            i = mc.end()
    spans.sort()
    merged = []
    for s, e, kd in spans:
        if merged and s < merged[-1][1]:
            if e > merged[-1][1]:
                merged[-1] = (merged[-1][0], e, kd)
            continue
        merged.append((s, e, kd))
    out = [(s, e, kd, max(0, s - 300)) for s, e, kd in merged if e - s >= 60]
    # unmarked blocks introduced by 'held as under:' etc.
    for m in _QUOTE_INTRO_RE.finditer(text):
        after = text[m.end():m.end() + 60]
        if re.match(r"\s*[“\"'‘]", after):
            continue
        before = text[max(0, m.start() - 120):m.end()]
        if _OWN_ORDER_BEFORE_RE.search(before):
            continue
        bs = m.end()
        be = para_starts_fn(bs) if para_starts_fn else None
        if be is None:
            be = min(n, bs + 2500)
        be = min(be, bs + 6000)
        # v3: an unmarked block also ends where the court resumes in its own voice after a paragraph break
        mr = _RESUME_RE.search(text, bs + 20, be)
        if mr:
            be = mr.start()
        if be - bs >= 20:
            out.append((bs, be, "intro_block", max(0, m.start() - 300)))
    out.sort()
    return out


def in_spans(spans, starts, pos):
    i = bisect.bisect_right(starts, pos) - 1
    while i >= 0:
        s, e = spans[i][0], spans[i][1]
        if s <= pos < e:
            return spans[i]
        if i > 0 and spans[i - 1][1] > pos:
            i -= 1
            continue
        break
    return None
