#!/usr/bin/env python3
"""C11 workstream: proposals for the 368 Supreme Court judgment records whose
metadata case_numbers field is empty although the document prints one.

Deterministic, standard library only (no PyMuPDF needed). Reads source bytes and
text layers from git objects, never modifies any metadata, and writes a versioned
correction PROPOSAL into ../outputs.

Usage:
    python scnum_c11.py --repo /home/user/c7          # (re)generate outputs
    python scnum_c11.py --repo /home/user/c7 --check  # regenerate in memory and
                                                      # compare byte-for-byte
"""
from __future__ import annotations

import argparse
import bisect
import csv
import hashlib
import io
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

TOOL_VERSION = "scnum_c11/1.0"
SOURCE_COMMIT = "ad77758d"
CURATED_COMMIT = "21e73b83"
CURATED_PATH = "legal_knowledge/curated_originals/case_law/v0.9/cases_53.jsonl"
EXPECTED_RECORDS = 368
SAMPLE_SEED = "C11-SCNUM-REVIEW-SAMPLE-v1"
SAMPLE_SIZE = 20
LATE_ANCHOR_FRACTION = 0.6
EXCERPT_MAX = 200

HERE = Path(__file__).resolve().parent
SCNUM_DIR = HERE.parent
OUT_DIR = SCNUM_DIR / "outputs"
DEFAULT_AUDIT_WORK = SCNUM_DIR.parent.parent  # .../audit_work

CLASSES = [
    "CONFIRMED_FROM_SOURCE",
    "CONFIRMED_MULTIPLE_CONNECTED",
    "PARTIALLY_CONFIRMED",
    "AMBIGUOUS",
    "NOT_RECOVERABLE",
]

# --------------------------------------------------------------------------
# Text flattening with (page, line) back-mapping
# --------------------------------------------------------------------------
PAGE_RE = re.compile(r"^\[\[page (\d+)\]\]\s*$")
# running headers of the SCR renditions, removed before parsing (they interrupt
# lists that run across a page break): "[2024] 10 S.C.R.", "SUPREME COURT REPORTS
# [1957]", short "X v. Y" title lines without a 'No.', and a bare page number
# only when it directly follows such a header line.
HEADER_RES = [
    re.compile(r"^[\[(]?\d{4}[\])]?\s*(?:\d{1,2}\s*)?(?:(?:Suppl?|SUPP)\.?\s*(?:\(?\d\)?)?\s*)?S\.\s?C\.\s?R\.?\s*\d{0,4}$", re.I),
    re.compile(r"^(?:\d{1,4}\s+)?(?:\[?\d{4}\]?\s*)?SUPREME\s+COURT\s+REPORTS?\b.{0,25}$", re.I),
    re.compile(r"^(?!.*\bN[o0]s?\b)[^()\d]{2,70}\bv[s]?\.?\s[^\d]{2,60}(?:\d{1,4})?$"),
]


CTRL_RE = re.compile("[\x00-\x08\x0b-\x1f\x7f\u200b-\u200f\ufeff]")


def is_header(line: str) -> bool:
    return len(line) < 90 and any(rx.search(line) for rx in HEADER_RES)


class FlatText:
    """Whitespace-collapsed text of a whole document; every character offset
    can be mapped back to the PDF page marker and the line within that page."""

    def __init__(self, raw: str):
        parts = []
        self.starts: list[int] = []
        self.locs: list[tuple[int, int]] = []
        page, line_no, pos = 0, 0, 0
        after_header = False
        for line in raw.splitlines():
            m = PAGE_RE.match(line.strip())
            if m:
                page, line_no = int(m.group(1)), 0
                after_header = False
                continue
            line_no += 1
            s = " ".join(CTRL_RE.sub("", line).split())
            if not s:
                continue
            if is_header(s):
                after_header = True
                if parts and re.fullmatch(r"\d{1,4}", parts[-1]) and self.locs[-1][0] == page:
                    parts.pop()
                    self.locs.pop()
                    pos = self.starts.pop()
                continue
            if after_header and re.fullmatch(r"\d{1,4}", s):
                after_header = False
                continue
            after_header = False
            self.starts.append(pos)
            self.locs.append((page, line_no))
            parts.append(s)
            pos += len(s) + 1
        self.text = " ".join(parts)

    def loc(self, offset: int) -> tuple[int, int]:
        if not self.starts:
            return (0, 0)
        i = bisect.bisect_right(self.starts, offset) - 1
        return self.locs[max(i, 0)]


# --------------------------------------------------------------------------
# Case-reference grammar
# --------------------------------------------------------------------------
# "No." marker: No. / Nos. / No(s). / N0. (OCR) ; must be followed by a number.
NO_RE = re.compile(r"(?<![A-Za-z])[Nn][oO0](?:\(s\)|[sS5]|l(?=\.))?(?![A-Za-z])\s*[.,:)_]*")
# noise allowed between the marker / items: whitespace, stray OCR punctuation,
# and single margin letters A-H printed in the SCR gutter.
NOISE_RE = re.compile(r"(?:[\s\"'·.:;~`_\-]+|!(?=\s)|/(?=\s*of\b)|(?<![A-Za-z0-9])[A-Ha-h](?![A-Za-z0-9]))+")
OCR_DIGIT = {"l": "1", "I": "1", "i": "1", "|": "1", "!": "1", "J": "1", "]": "1",
             "O": "0", "o": "0", "L": "1"}
YEAR_CHARS = "0-9lIi|!J\\]OoL"
YEAR_RE = re.compile(r"([" + YEAR_CHARS + r"])(\s?[" + YEAR_CHARS + r"]){3}(?![0-9A-Za-z])")

ITEM_RE = re.compile(
    r"(?P<rslash>(?P<q1>\d{1,6})\s*[-\u2013]\s*(?P<q2>\d{1,6})\s*/\s*(?P<q3>\d{4}|\d{2})(?![0-9]))"
    r"|(?P<range>(?P<r1>\d{1,6})\s*[-–]\s*(?P<r2>\d{1,6})(?!\s*/)(?![0-9]))"
    r"|(?P<to>(?P<t1>\d{1,6})\s+to\s+(?P<t2>\d{1,6}))"
    r"|(?P<slash>(?P<s1>\d{1,6})\s*/\s*(?P<s2>\d{4}|\d{2})(?![0-9]))"
    r"|(?P<suf>(?P<f1>\d{1,6})(?:\s*-\s*)?(?P<f2>[A-Z])(?=\s*(?:of\b|,|&|and\b|\)|\.|$)))"
    r"|(?P<num>\d{1,6})(?![0-9])"
)
OF_RE = re.compile(r"of(?![A-Za-z])|(?:0f|9f|or)(?=\s*\d{4})", re.I)
OF_SKIP_RE = re.compile(r"(?:[\s).,·'\"~`]|(?<![A-Za-z0-9])(?![lIJ|]\s?\d)[A-Za-z](?![A-Za-z0-9]))+")
OCR_TAIL_RE = re.compile(r"\s?([lI|!])(?=\s*of|\s*[,&])")
OCR_HEAD_RE = re.compile(r"[lI|]\s?(\d{2,5})(?![0-9])")
SEP_RE = re.compile(r",|&|\band\b|\bAND\b|\bAnd\b")
ETC_RE = re.compile(r"etc\b\.?", re.I)

ARISING_RE = re.compile(
    r"\bfrom\s+the\b|\b(?:appeals?|petitions?)\s+(?:by\s+special\s+leave\s+)?from\b"
    r"|\barising\s+(?:out\s+of|from)\b|\bimpugned\b"
    r"|\bagainst\s+the\s+(?:final\s+)?(?:common\s+)?(?:judgments?|orders?|decrees?|awards?)\b"
    r"|\bon\s+appeal\s+from\b|\bfrom\s+(?:judgments?|orders?)\b",
    re.I)
DESC_RE = re.compile(r"\bunder\s+art(?:icle|\.|s\.)?\s*\d+|\bunder\s+section\b"
                     r"|\bfor\s+the\s+enforcement\b", re.I)
CONNECT_TAIL_RE = re.compile(r"(?:\b(?:WITH|With|ALONG\s*WITH|Along\s*with|alongwith|AND)|\.\W*with)[\W]*(?:\d{1,4}\W*)?$")
CONNECT_LOWER_RE = re.compile(r"\b(?:with|and)[\W]*(?:\d{1,4}\W*)?$")
SC_ONLY_CODES = re.compile(r"^(?:CA|CRLA|SLP(?:C|CRL)?|TP(?:C|CRL)?|TC(?:C|CRL)?|CONT(?:C|CRL)?|RP(?:C|CRL)?|CURP(?:C|CRL)?|CMP|CRLMP)(?:DIARY)?$")
GUTTER_RE = re.compile(r"(?<![A-Za-z0-9])[A-H](?![A-Za-z0-9])")
PARENT_TAIL_RE = re.compile(r"(?:^|[\s(])(?:in|In|IN)\s*$")
CITATION_TAIL_RE = re.compile(r"^\W{0,3}(?:decided\s+on|reported\s+in|dated)\b", re.I)

END_RE = re.compile(
    r"\bfor\s+the\s+(?:appellants?|petitioners?|respondents?|state|union|intervener|applicants?)\b"
    r"|Appearances\s+for\s+Part|Advs?\.\s+for\s+the|\bin[- ]person\b"
    r"|(?:judgment|order)\s+of\s+the\s+court\s+was\s+delivered|The\s+following\s+(?:judgment|order)",
    re.I)
BLOCK_MAX = 2500

MONTHS = ("JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|"
          "NOVEMBER|DECEMBER")
TITLE_DATE_RE = re.compile(r"\)\s*(?:" + MONTHS + r")\s+\d{1,2}\s*,\s*\d{4}")


def _ocr_word_ok(tok: str, target: str, max_dist: int) -> bool:
    a, b = tok.upper(), target
    if abs(len(a) - len(b)) > max_dist:
        return False
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1] <= max_dist


ANCHOR_TOKEN_RE = re.compile(r"\S{6,30}")
ANCHOR_PREV = ("APPELLATE", "ORIGINAL", "INHERENT", "ADVISORY")


def find_anchors(text: str) -> list[int]:
    """Offsets of 'XXX JURISDICTION' headings (OCR tolerant). Lower-case prose
    'jurisdiction' is never an anchor."""
    out = []
    for m in ANCHOR_TOKEN_RE.finditer(text):
        tok = m.group(0)
        start = m.start()
        colon_in_tok = False
        if ":" in tok or ";" in tok:
            cut = min(i for i in (tok.find(":"), tok.find(";")) if i >= 0)
            colon_in_tok = True
            tok = tok[:cut]
        core = tok.rstrip(",.")
        if len(core) > 15:  # glued e.g. 'CIVILAPPELLATE.JURISDICTION'
            start += len(core) - 12
            core = core[-12:]
        core2 = core.lstrip(".,'`")
        start += len(core) - len(core2)
        core = core2
        if not 9 <= len(core) <= 15:
            continue
        letters = [c for c in core if c.isalpha()]
        if not letters:
            continue
        upper_ratio = sum(c.isupper() for c in letters) / len(letters)
        if upper_ratio < 0.25:
            continue
        colon = colon_in_tok or bool(re.match(r"\s?[:;]", text[start + len(core):start + len(core) + 3]))
        before = text[max(0, start - 40):start].upper()
        words = re.findall(r"[A-Z0-9]{4,}", before)[-3:]
        prev_ok = any(_ocr_word_ok(w, p, 3) for w in words for p in ANCHOR_PREV)
        strict = _ocr_word_ok(core, "JURISDICTION", 4) and core[0] in "JjT."
        loose = prev_ok and colon and _ocr_word_ok(core, "JURISDICTION", 7) and \
            core.upper()[1:3] in ("UR", "JR", "VR", "UH") or (prev_ok and colon and core.upper()[0] in "J.T"
                                                              and _ocr_word_ok(core, "JURISDICTION", 6))
        if strict and upper_ratio >= 0.4 and ((colon and (prev_ok or upper_ratio >= 0.8)) or (prev_ok and upper_ratio >= 0.8)):
            out.append(start)
        elif loose:
            out.append(start)
    return out


# ---- label (case type) normalisation ------------------------------------
LABEL_STOP = {"with", "and", "in", "of", "from", "the", "to", "by", "under", "arising",
              "out", "jurisdiction", "dated", "order", "judgment", "on", "at", "for",
              "vide", "etc", "connected", "along", "alongwith", "s.c.r.", "scr", "reports",
              "court", "supreme", "respondent", "respondents", "appellant", "appellants",
              "petitioner", "petitioners"}
LABEL_LOWER_OK = {"appeal", "appeals", "petition", "petitions", "case", "cases", "application",
                  "applications", "leave", "writ", "misc.", "misc", "miscellaneous", "civil",
                  "criminal", "special", "transfer", "transferred", "review", "contempt",
                  "diary", "d.", "suo", "motu"}
LABEL_UPPER_OK = {"writ", "petition", "petitions", "civil", "appeal", "appeals", "criminal",
                  "special", "leave", "transfer", "transferred", "case", "cases", "review",
                  "contempt", "misc", "miscellaneous", "application", "applications", "diary",
                  "original", "suit", "reference", "curative", "election", "interlocutory",
                  "cwjc", "lpasw", "cmwp", "civtl", "crl", "suo", "motu"}
QUAL_RE = re.compile(r"[({]\s*([A-Za-z][A-Za-z!.]{0,8})\s*\.?\s*[)}]")
TOKEN_JUNK = "'\"`~·-_^"

SC_TYPES = [  # (fullmatch regex on squashed lower-case key, base code, takes qualifier)
    (r"(specialleavepetition|slp)s?", "SLP", True),
    (r"(civilmisc(ellaneous)?petition|cmp|civilmp)s?", "CMP", False),
    (r"(criminalmisc(ellaneous)?petition|crlmp|crlmiscpetition|crimp|crmp)s?", "CRLMP", False),
    (r"(transferredcase|transfercase|tc)s?", "TC", True),
    (r"(transferpetition|tp)s?", "TP", True),
    (r"(contemptpetition|contpet|conmtpet|cont|conmt|contempt|contemptpet)s?", "CONT", True),
    (r"(reviewpetition|rp)s?", "RP", True),
    (r"(curativepetition)s?", "CURP", True),
    (r"(interlocutoryapplication|ia)s?", "IA", False),
    (r"(misc(ellaneous)?application|ma)s?", "MA", False),
    (r"(misc(ellaneous)?petition|mp)s?", "MP", False),
    (r"(electionappeal)s?", "ELA", False),
    (r"(electionpetition)s?", "ELP", False),
    (r"(suomotuwrit(petition)?|smw|smwp)s?", "SMW", True),
    (r"(criminalwritpetition)s?", "WPCRL", False),
    (r"(writpetition|wp)s?", "WP", True),
    (r"(civilappeal|ca)s?", "CA", False),
    (r"(criminalappeal|crlappeal|crla|crlapp|crlappl)s?", "CRLA", False),
    (r"(originalsuit|suit)s?", "OS", False),
    (r"(specialreference|reference)s?", "REF", False),
    (r"(petition)s?", "PET", False),
    (r"(appeal)s?", "APPEAL", False),
]
SC_TYPES_C = [(re.compile(p), c, q) for p, c, q in SC_TYPES]
FUZZY_KEYS = [("specialleavepetition", "SLP", True), ("civilappeal", "CA", False),
              ("criminalappeal", "CRLA", False), ("writpetition", "WP", True),
              ("transferpetition", "TP", True), ("transferredcase", "TC", True),
              ("contemptpetition", "CONT", True), ("reviewpetition", "RP", True),
              ("miscellaneousapplication", "MA", False), ("interlocutoryapplication", "IA", False),
              ("civilmiscellaneouspetition", "CMP", False), ("civilmiscpetition", "CMP", False),
              ("criminalmiscpetition", "CRLMP", False)]


def _clean_tok(w: str) -> str:
    return w.strip(TOKEN_JUNK + ",;")


def extract_label(text: str, no_start: int, lo: int) -> tuple[str, int]:
    """Walk back from the 'No.' marker collecting label-like tokens; gutter
    letters (single A-H/a-h) and OCR junk tokens are skipped."""
    base = max(lo, no_start - 80)
    seg = text[base:no_start]
    toks = list(re.finditer(r"\S+", seg))
    picked = []
    for t in reversed(toks):
        raw = t.group(0)
        w = re.sub(r"[~'\"`\u00b7]", "", _clean_tok(raw))
        if not w:
            continue
        wl = w.lower()
        if re.fullmatch(r"[A-Z]{3,}\.?", w) and wl.rstrip(".") not in LABEL_UPPER_OK and len(w.rstrip(".")) >= 4:
            break
        if wl.rstrip(".") in ("india", "anr", "ors", "union", "state", "others"):
            break
        if raw.endswith((":", ";")) or wl.rstrip(".") in LABEL_STOP or wl in LABEL_STOP:
            break
        if re.search(r"\d", w) and not QUAL_RE.fullmatch(w):
            break
        if re.fullmatch(r"[A-Ha-h]", w):
            continue  # gutter letter
        if re.fullmatch(r"[a-z]\.?", w) and wl not in LABEL_LOWER_OK:
            continue  # OCR junk such as "''f.-"
        if not any(c.isalpha() for c in w) or (sum(c.isalpha() for c in w) == 1 and re.search(r"[^A-Za-z.()]", w)):
            continue
        if QUAL_RE.fullmatch(w) or re.fullmatch(r"[(]?[A-Za-z][A-Za-z.!]*[)]?\.?", w) \
                or re.fullmatch(r"(?:[A-Za-z]{1,5}\.){1,5}[A-Za-z]{0,5}\.?(?:[({][A-Za-z!.]+[)}])?", w) \
                or re.fullmatch(r"[A-Za-z][A-Za-z.]*[({][A-Za-z!.]+[)}]\.?", w):
            if w[0].islower() and wl not in LABEL_LOWER_OK and not QUAL_RE.fullmatch(w) \
                    and not re.fullmatch(r"(?:[a-z]{1,4}\.)+", w):
                break
            picked.append((t, w))
            if len(picked) >= 7:
                break
            continue
        break
    if not picked:
        return "", no_start
    picked.reverse()
    start = base + picked[0][0].start()
    return " ".join(w for _, w in picked), start


def _qualifier(label: str) -> str:
    for m in QUAL_RE.finditer(label):
        g = m.group(1).lower()
        if g.startswith("cr"):
            return "CRL"
        if g.startswith("c"):
            return "C"
        if g.startswith("pil"):
            return "PIL"
    if re.search(r"\bcivil\b", label, re.I) and not re.match(r"\s*civil\b", label, re.I):
        return "C"
    if re.search(r"\b(?:crl|criminal)\b", label, re.I) and not re.match(r"\s*(?:crl|criminal)\b", label, re.I):
        return "CRL"
    return ""


def squash(label: str) -> str:
    return re.sub(r"[^a-z]", "", QUAL_RE.sub("", label).lower())


def normalise_type(label: str) -> tuple[str, bool, str]:
    """Return (code, recognised_as_sc_type, flag). Diary numbers get a DIARY suffix."""
    if re.search(r"\bdiary\b|\bD\.(?=\s*$)|\bD\.(?=\s*\()", label, re.I):
        base = re.sub(r"\bdiary\b|\bD\.(?=\s*$)|\bD\.(?=\s*\()", " ", label, flags=re.I).strip()
        if not base:
            return "DIARY", False, "type_missing_diary_only"
        code, ok, fl = normalise_type(base)
        return code + "DIARY", ok, fl
    q = _qualifier(label)
    key = squash(label)
    if key.startswith("the"):
        key = key[3:]
    stripped = re.sub(r"(civil|criminal|crl)$", "", key) if not re.fullmatch(
        r"(civil|criminal|crl)", key) else key
    for k in (key, stripped):
        for rx, code, takes_q in SC_TYPES_C:
            if rx.fullmatch(k):
                return code + (q if takes_q else ""), True, ""
    for full, code, takes_q in FUZZY_KEYS:
        if len(key) >= 8 and _ocr_word_ok(key.upper(), full.upper(), 2):
            return code + (q if takes_q else ""), True, "ocr_type_fuzzy:" + label
    return generic_code(label), False, "type_unrecognised:" + label


def generic_code(label: str) -> str:
    lab = QUAL_RE.sub("", label)
    toks = re.findall(r"[A-Za-z]+", lab)
    if not toks:
        return "UNK"
    if "." in lab or all(len(t) <= 4 for t in toks):
        return "".join(toks).upper()
    return "".join(t[0] for t in toks if t[0].isupper() or len(toks) == 1).upper() or "UNK"


@dataclass
class Ref:
    start: int          # label start (or marker start)
    end: int
    label: str
    code: str
    sc_type: bool
    numbers: list        # list of (num_str, year or None)
    verbatim: str
    flags: list = field(default_factory=list)
    etc: bool = False

    def normalised(self) -> list[str]:
        out = []
        for n, y in self.numbers:
            out.append("%s-%s-%s" % (self.code, n, y if y else "YEAR?"))
        return out

    @property
    def clean(self) -> bool:
        return bool(self.numbers) and all(y for _, y in self.numbers) and not self.flags


def _fix_year(raw: str) -> tuple[str | None, bool]:
    s = raw.replace(" ", "")
    repaired = any(c in OCR_DIGIT for c in s)
    s2 = "".join(OCR_DIGIT.get(c, c) for c in s)
    if not re.fullmatch(r"\d{4}", s2):
        return None, repaired
    y = int(s2)
    if 1940 <= y <= 2026:
        return s2, repaired
    return None, repaired


def _expand(a: str, b: str) -> list[str] | None:
    if len(b) < len(a):
        b = a[:len(a) - len(b)] + b
    ia, ib = int(a), int(b)
    if ib <= ia or ib - ia > 200:
        return None
    return [str(i) for i in range(ia, ib + 1)]


def parse_numbers(text: str, pos: int, limit: int):
    """Parse the number list following a 'No.' marker.
    Returns (numbers, end, flags, etc)."""
    items: list[list] = []   # [num, year|None]
    flags: list[str] = []
    etc = False
    i = pos
    last_good = pos
    expecting_more = True
    while i < limit:
        m = NOISE_RE.match(text, i)
        if m and m.end() > i:
            i = m.end()
            continue
        of_here = bool(items) and OF_RE.match(text, i) is not None  # 'of' / OCR '9f', handled below
        mh = None if of_here or not expecting_more else OCR_HEAD_RE.match(text, i)
        if mh:
            items.append(["1" + mh.group(1), None])
            flags.append("ocr_number_repaired:" + mh.group(0).replace(" ", ""))
            i = mh.end()
            last_good = i
            expecting_more = False
            continue
        m = None if of_here else ITEM_RE.match(text, i)
        if m and not expecting_more and items and m.group("num") and text[last_good:i].strip() == "" \
                and items[-1][1] is None:
            # two numbers separated only by a space: split digit group or missing comma
            prev = items[-1][0]
            if prev.isdigit() and ((len(prev) <= 2 and len(m.group("num")) >= 2)
                                   or len(m.group("num")) == 1):
                items[-1][0] = prev + m.group("num")
                flags.append("ocr_number_space_joined:%s %s" % (prev, m.group("num")))
            else:
                items.append([m.group("num"), None])
                flags.append("missing_separator:%s %s" % (prev, m.group("num")))
            i = m.end()
            last_good = i
            continue
        mo = OCR_TAIL_RE.match(text, i)
        if mo and not expecting_more and items and items[-1][1] is None and items[-1][0].isdigit():
            items[-1][0] += "1"
            flags.append("ocr_number_repaired:%s%s" % (items[-1][0][:-1], mo.group(1)))
            i = mo.end()
            last_good = i
            continue
        if m and expecting_more:
            if m.group("rslash"):
                yy = m.group("q3")
                if len(yy) == 2:
                    yy = ("19" if int(yy) > 30 else "20") + yy
                y, _ = _fix_year(yy)
                exp = _expand(m.group("q1"), m.group("q2"))
                for it in items:
                    if it[1] is None:
                        it[1] = y or "BAD"
                if exp is None:
                    flags.append("range_unparsed:" + m.group(0))
                    exp = [m.group("q1")]
                items.extend([[n, y or "BAD"] for n in exp])
                if not y:
                    flags.append("bad_year:" + m.group(0))
            elif m.group("range"):
                exp = _expand(m.group("r1"), m.group("r2"))
                if exp is None:
                    flags.append("range_unparsed:" + m.group(0))
                    items.append([m.group("r1"), None])
                else:
                    items.extend([[n, None] for n in exp])
            elif m.group("to"):
                exp = _expand(m.group("t1"), m.group("t2"))
                if exp is None:
                    flags.append("range_unparsed:" + m.group(0))
                    items.append([m.group("t1"), None])
                else:
                    items.extend([[n, None] for n in exp])
            elif m.group("slash"):
                yy = m.group("s2")
                if len(yy) == 2:
                    yy = ("19" if int(yy) > 30 else "20") + yy
                y, _ = _fix_year(yy)
                for it in items:
                    if it[1] is None:
                        it[1] = y or "BAD"
                items.append([m.group("s1"), y or "BAD"])
                if not y:
                    flags.append("bad_year:" + m.group(0))
            elif m.group("suf"):
                items.append([m.group("f1") + m.group("f2"), None])
            else:
                items.append([m.group("num"), None])
            i = m.end()
            last_good = i
            expecting_more = False
            continue
        m = re.compile(r"to\b").match(text, i)
        if m and items and not expecting_more:
            # 'to' range whose end is garbled
            i = m.end()
            expecting_more = True
            flags.append("range_end_garbled")
            continue
        m = SEP_RE.match(text, i)
        if m and items:
            i = m.end()
            expecting_more = True
            continue
        m = OF_RE.match(text, i)
        if m and items:
            j = m.end()
            mm = OF_SKIP_RE.match(text, j)
            if mm:
                j = mm.end()
            ym = YEAR_RE.match(text, j)
            if ym:
                y, repaired = _fix_year(ym.group(0))
                for it in items:
                    if it[1] is None:
                        it[1] = y or "BAD"
                if not y:
                    flags.append("bad_year:" + ym.group(0))
                elif repaired:
                    flags.append("ocr_year_repaired:" + ym.group(0).replace(" ", ""))
                i = ym.end()
                last_good = i
                expecting_more = False
                continue
            flags.append("year_garbled:" + text[j:j + 6])
            last_good = j
            break
        m = ETC_RE.match(text, i)
        if m and items:
            etc = True
            i = m.end()
            last_good = i
            expecting_more = False
            continue
        break
    if len(items) == 2 and len(items[1][0]) <= len(items[0][0]) - 2 and items[1][0].isdigit():
        flags.append("possible_abbreviated_number:%s,%s" % (items[0][0], items[1][0]))
    nums = []
    for n, y in items:
        if y == "BAD":
            y = None
        nums.append((n, y))
    if any(y is None for _, y in nums) and not any(f.startswith(("bad_year", "year_garbled"))
                                                    for f in flags):
        flags.append("year_missing")
    return nums, last_good, flags, etc


def find_refs(text: str, lo: int, hi: int) -> list[Ref]:
    refs = []
    for m in NO_RE.finditer(text, lo, hi):
        # must be followed by a number (after noise)
        j = m.end()
        mm = NOISE_RE.match(text, j)
        if mm:
            j = mm.end()
        if j >= hi or not (text[j].isdigit() or OCR_HEAD_RE.match(text, j)):
            continue
        if refs and m.start() < refs[-1].end:
            continue
        label, lstart = extract_label(text, m.start(), lo)
        nums, end, flags, etc = parse_numbers(text, m.end(), min(hi, m.end() + 4000))
        if not nums:
            continue
        if label:
            code, sc, tflag = normalise_type(label)
        else:
            code, sc, tflag = "UNK", False, "type_unrecognised:<none>"
        if code == "DIARY" and refs:
            code, sc, tflag = refs[-1].code.replace("DIARY", "") + "DIARY", refs[-1].sc_type, \
                "type_inherited_from_previous_reference"
        r = Ref(start=lstart, end=end, label=label, code=code, sc_type=sc, numbers=nums,
                verbatim=text[lstart:end].strip(), flags=list(flags), etc=etc)
        if tflag:
            r.flags.append(tflag)
        refs.append(r)
    return refs


# --------------------------------------------------------------------------
# Block parser (state machine)
# --------------------------------------------------------------------------
@dataclass
class BlockResult:
    hosts: list = field(default_factory=list)       # Ref
    arising: list = field(default_factory=list)     # Ref
    parents: list = field(default_factory=list)     # Ref
    other: list = field(default_factory=list)       # Ref
    notes: list = field(default_factory=list)
    primary_found: bool = False                     # a host read before any WITH/heading switch


def parse_block(text: str, lo: int, hi: int, anchors_inside=()) -> BlockResult:
    res = BlockResult()
    refs = find_refs(text, lo, hi)
    events = []
    for m in ARISING_RE.finditer(text, lo, hi):
        events.append((m.start(), "ARISING"))
    for m in DESC_RE.finditer(text, lo, hi):
        events.append((m.start(), "DESC"))
    for a in anchors_inside:
        events.append((a, "ANCHOR"))
    events.sort()
    state = "HOST"
    cursor = lo
    ei = 0
    for r in refs:
        # apply events strictly before this ref
        while ei < len(events) and events[ei][0] < r.start:
            if events[ei][1] == "DESC" and not res.hosts:
                ei += 1  # e.g. 'JURISDICTION : UNDER ARTICLE 32 ... Writ Petition (Civil) No. 246'
                continue
            state = "HOST" if events[ei][1] == "ANCHOR" else events[ei][1]
            if events[ei][1] == "ANCHOR":
                cursor = events[ei][0]
            ei += 1
        gap = text[cursor:r.start]
        # events inside the reference itself (rare) are ignored
        gap_clean = NOISE_RE.sub(" ", gap).strip()
        if CITATION_TAIL_RE.match(text[r.end:r.end + 30]):
            r.flags.append("citation_context")
            res.other.append(r)
            cursor = r.end
            continue
        if PARENT_TAIL_RE.search(gap_clean) and state in ("HOST", "CONNECTED"):
            res.parents.append(r)
        elif state in ("HOST", "CONNECTED"):
            res.hosts.append(r)
            if state == "HOST" and not res.arising and not res.other:
                res.primary_found = True
        else:
            # re-enter host state when a connected-matter marker precedes the ref
            last_ev = max([e[0] for e in events if e[0] < r.start], default=lo)
            between = GUTTER_RE.sub(" ", text[max(cursor, last_ev):r.start])
            if CONNECT_TAIL_RE.search(between) or (
                    CONNECT_LOWER_RE.search(between) and SC_ONLY_CODES.match(r.code)):
                state = "CONNECTED"
                res.hosts.append(r)
            elif state == "ARISING":
                res.arising.append(r)
            else:
                res.other.append(r)
        cursor = r.end
    return res


def block_bounds(text: str, anchor: int) -> tuple[int, int]:
    m = END_RE.search(text, anchor, anchor + BLOCK_MAX)
    hi = m.start() if m else min(len(text), anchor + BLOCK_MAX)
    return anchor, hi


def anchor_skip(text: str, a: int) -> int:
    """Offset just after the 'JURISDICTION' token and optional colon."""
    m = re.compile(r"\S+").match(text, a)
    e = m.end() if m else a
    mm = re.compile(r"\s*[:;.,]").match(text, e)
    return mm.end() if mm else e


# --------------------------------------------------------------------------
# Curated cases
# --------------------------------------------------------------------------
CUR_NUM_RE = re.compile(r"(\d{1,6})(?:\s*[-–]\s*(\d{1,6}))?\s*(?:of\s*|/)\s*(\d{4})")
CUR_LIST_RE = re.compile(r"((?:\d{1,6}\s*(?:,|and|&)\s*)+)(\d{1,6})\s*(?:of\s*|/)\s*(\d{4})")


def curated_pairs(s: str) -> set:
    pairs = set()
    for m in CUR_LIST_RE.finditer(s):
        for n in re.findall(r"\d{1,6}", m.group(1)):
            pairs.add((n, m.group(3)))
    for m in CUR_NUM_RE.finditer(s):
        a, b, y = m.groups()
        if b:
            exp = _expand(a, b) or [a]
            for n in exp:
                pairs.add((n, y))
        else:
            pairs.add((a, y))
    return pairs


def title_words(t: str) -> set:
    stop = {"union", "india", "of", "and", "others", "ors", "the", "v", "vs", "versus",
            "another", "anr", "etc", "state", "lt", "col", "major", "ex", "and", "singh",
            "kumar", "lal", "ram", "devi", "prasad", "sharma", "chand", "general", "secretary",
            "ministry", "defence", "colonel", "captain", "naik", "sepoy", "havildar", "main",
            "judgment", "order", "review", "clarification", "and", "anor", "others", "the"}
    return {w for w in re.findall(r"[a-z]{3,}", t.lower()) if w not in stop}


# --------------------------------------------------------------------------
# Git access
# --------------------------------------------------------------------------
class GitBlobs:
    def __init__(self, repo: str):
        self.p = subprocess.Popen(["git", "-C", repo, "cat-file", "--batch"],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE)

    def get(self, spec: str) -> bytes | None:
        self.p.stdin.write((spec + "\n").encode())
        self.p.stdin.flush()
        header = self.p.stdout.readline().decode()
        if header.endswith("missing\n") or not header.strip():
            return None
        size = int(header.split()[2])
        data = self.p.stdout.read(size)
        self.p.stdout.read(1)
        return data

    def close(self):
        self.p.stdin.close()
        self.p.wait()


# --------------------------------------------------------------------------
# Per-record analysis
# --------------------------------------------------------------------------
def analyse_text(raw_text: str) -> dict:
    ft = FlatText(raw_text)
    text = ft.text
    out = {"ft": ft, "anchor": None, "block": None, "paren": None, "notes": []}
    if len(text) < 50:
        out["notes"].append("no_text_layer")
        return out
    anchors = find_anchors(text)
    if anchors:
        a = anchors[0]
        lo, hi = block_bounds(text, a)
        inside = [x for x in anchors[1:] if x < hi]
        res = parse_block(text, anchor_skip(text, a), hi, [anchor_skip(text, x) for x in inside])
        out["anchor"] = a
        out["anchor_fraction"] = a / max(len(text), 1)
        out["block"] = res
        out["block_bounds"] = (lo, hi)
        if len(anchors) > 1 + len(inside):
            out["notes"].append("further_jurisdiction_headings_after_block:%d" % (len(anchors) - 1 - len(inside)))
    # newer SCR layout: '(Civil Appeal No. 5605 of 2010)' right before 'JUNE 25, 2014'
    first_pages_end = len(text)
    for idx, (pg, _) in enumerate(ft.locs):
        if pg > 3:
            first_pages_end = ft.starts[idx]
            break
    for m in TITLE_DATE_RE.finditer(text, 0, first_pages_end):
        close = m.start()
        open_ = text.rfind("(", max(0, close - 400), close)
        while open_ > 0 and text.count(")", open_, close) > text.count("(", open_ + 1, close):
            open_ = text.rfind("(", max(0, close - 400), open_)
        if open_ < 0:
            continue
        res = parse_block(text, open_ + 1, close)
        if res.hosts or res.parents or res.arising:
            out["paren"] = res
            out["paren_bounds"] = (open_, close + 1)
            break
    return out


def decide(rec: dict, an: dict, curated: dict | None) -> dict:
    ft = an["ft"]
    text = ft.text
    blk, par = an["block"], an["paren"]
    notes = list(an["notes"])
    hosts, arising, parents, method = [], [], [], ""
    evidence_at = None
    cls = None
    if blk is not None and blk.hosts:
        hosts, arising, parents = blk.hosts, blk.arising, blk.parents
        method = "JURISDICTION_BLOCK"
        evidence_at = an["anchor"]
        if blk.other:
            notes.append("other_refs_in_block:" + "|".join(sorted({x for r in blk.other for x in r.normalised()})))
    elif par is not None and par.hosts:
        hosts, arising, parents = par.hosts, par.arising, par.parents
        method = "CAUSE_TITLE_PARENTHESIS"
        evidence_at = an["paren_bounds"][0]
    elif blk is not None:
        method = "JURISDICTION_BLOCK"
        evidence_at = an["anchor"]
        arising, parents = blk.arising, blk.parents
        if blk.parents:
            notes.append("only_parent_reference_found")
    host_norm = []
    for r in hosts:
        for n in r.normalised():
            if n not in host_norm:
                host_norm.append(n)
    arising_norm = []
    for r in arising:
        for n in r.normalised():
            if n not in arising_norm:
                arising_norm.append(n)
    parent_norm = sorted({n for r in parents for n in r.normalised()})
    # never let an impugned/arising number stand as a host number
    clash = [n for n in host_norm if n in arising_norm]
    competing = []
    if clash:
        # the same number read both as host and as impugned/arising: keep it out of
        # arising_from and send the record to review
        arising_norm = [n for n in arising_norm if n not in clash]
        competing.append("number_read_as_both_host_and_arising:" + "|".join(clash))

    # ---- cross-checks -----------------------------------------------------
    if method == "JURISDICTION_BLOCK" and hosts and par is not None and par.hosts:
        p_norm = {n for r in par.hosts + par.parents if r.clean for n in r.normalised()}
        b_norm = set(host_norm) | set(parent_norm)

        def _same(x, y):
            xa, ya = x.split("-"), y.split("-")
            return xa[1] == ya[1] and (xa[2] == ya[2] or "YEAR?" in (xa[2], ya[2]))
        if p_norm and not any(_same(x, y) for x in p_norm for y in b_norm):
            competing.append("cause_title_parenthesis_disagrees:" + "|".join(sorted(p_norm)))
        else:
            notes.append("cause_title_parenthesis_agrees")
    if method == "JURISDICTION_BLOCK" and an.get("anchor_fraction", 0) > LATE_ANCHOR_FRACTION and hosts:
        if not (par is not None and par.hosts):
            competing.append("jurisdiction_heading_late_in_file(%.2f):may_belong_to_next_case"
                             % an["anchor_fraction"])
    cur_status, cur_str = "NO_CURATED_RECORD", ""
    if curated is not None:
        cur_str = curated.get("case_number", "") or ""
        cp = curated_pairs(cur_str)
        hp = {(x.split("-")[1], x.split("-")[2]) for x in host_norm}
        if not cp:
            cur_status = "CURATED_RECORD_WITHOUT_NUMBER"
        elif not hp:
            cur_status = "CURATED_ONLY"
        elif cp == hp:
            cur_status = "MATCH"
        elif cp <= hp:
            cur_status = "MATCH_CURATED_SUBSET"
        elif cp & hp:
            cur_status = "PARTIAL_OVERLAP"
        else:
            cur_status = "MISMATCH"
            competing.append("curated_case_number_disagrees:" + cur_str)

    flags = sorted({f for r in hosts for f in r.flags})
    etc = any(r.etc for r in hosts)
    if not method:
        cls = "NOT_RECOVERABLE"
        notes.append("no_jurisdiction_heading_or_cause_title_number_found")
    elif not host_norm:
        if blk is not None and (blk.parents or blk.other or re.search(r"\d", text[an["anchor"]:an["block_bounds"][1]])):
            cls = "PARTIALLY_CONFIRMED"
            notes.append("heading_found_but_no_host_number_parsed")
        else:
            cls = "NOT_RECOVERABLE"
            notes.append("heading_found_without_number")
    elif competing:
        cls = "AMBIGUOUS"
    elif method == "JURISDICTION_BLOCK" and not blk.primary_found:
        cls = "PARTIALLY_CONFIRMED"
        notes.append("first_host_reference_not_parsed_only_parent_or_connected_matters_found")
    elif flags or etc or any(not r.clean for r in hosts) or any("YEAR?" in n for n in host_norm):
        cls = "PARTIALLY_CONFIRMED"
        if etc:
            notes.append("connected_matters_elided_by_etc")
    elif len(host_norm) > 1:
        cls = "CONFIRMED_MULTIPLE_CONNECTED"
    else:
        cls = "CONFIRMED_FROM_SOURCE"
    notes.extend(competing)

    page, line = (0, 0)
    excerpt = ""
    if hosts:
        page, line = ft.loc(hosts[0].start)
    elif evidence_at is not None:
        page, line = ft.loc(evidence_at)
    if evidence_at is not None:
        excerpt = text[evidence_at:evidence_at + EXCERPT_MAX]
        if len(excerpt) == EXCERPT_MAX:
            excerpt = excerpt[:EXCERPT_MAX]
    return {
        "host_case_numbers_normalised": ";".join(host_norm),
        "host_case_numbers_verbatim": " || ".join(r.verbatim for r in hosts),
        "page": str(page) if page else "",
        "line": str(line) if line else "",
        "evidence_excerpt": excerpt,
        "connected_count": str(max(len(host_norm) - 1, 0)) if host_norm else "0",
        "arising_from": ";".join(arising_norm),
        "arising_from_verbatim": " || ".join(r.verbatim for r in arising),
        "parent_case": ";".join(parent_norm),
        "curated_match": cur_status,
        "curated_case_number": cur_str,
        "classification": cls,
        "locator": method or "NONE",
        "flags": ";".join(flags),
        "notes": ";".join(notes),
    }


# --------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------
PROPOSAL_COLS = ["doc_id", "judgment_id", "sha256", "title", "host_case_numbers_normalised",
                 "host_case_numbers_verbatim", "page", "evidence_excerpt", "connected_count",
                 "arising_from", "curated_match", "classification", "method", "status",
                 # extra audit columns
                 "line", "locator", "arising_from_verbatim", "parent_case",
                 "curated_case_number", "flags", "notes", "source_path", "hash_verified",
                 "text_path"]


def csv_bytes(cols, rows) -> bytes:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, lineterminator="\n", extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue().encode("utf-8")


def load_inputs(audit_work: Path):
    c10 = audit_work / "C10-HF-JUDGMENTS" / "outputs"
    with open(c10 / "HF_JUDGMENT_METADATA_AUDIT.csv", newline="", encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh)
                if "Supreme" in r["court"] and not r["case_numbers_meta"].strip()]
    if len(rows) != EXPECTED_RECORDS:
        raise SystemExit("FAIL CLOSED: expected %d Supreme Court rows with empty case_numbers_meta, got %d"
                         % (EXPECTED_RECORDS, len(rows)))
    with open(c10 / "HF_JUDGMENT_COPY_REGISTER.csv", newline="", encoding="utf-8") as fh:
        reg = {r["sha256"]: r for r in csv.DictReader(fh)}
    return rows, reg


def build(repo: str, audit_work: Path) -> dict[str, bytes]:
    rows, reg = load_inputs(audit_work)
    git = GitBlobs(repo)
    cur_raw = git.get("%s:%s" % (CURATED_COMMIT, CURATED_PATH))
    if cur_raw is None:
        raise SystemExit("FAIL CLOSED: curated cases_53.jsonl not found at %s" % CURATED_COMMIT)
    curated = [json.loads(l) for l in cur_raw.decode("utf-8").splitlines() if l.strip()]
    curated = [c for c in curated if "Supreme" in c.get("court", "") and c.get("decision_date")]
    out_rows = []
    for rec in sorted(rows, key=lambda r: r["doc_id"]):
        sha = rec["sha256"]
        rr = reg.get(sha)
        if rr is None:
            raise SystemExit("FAIL CLOSED: sha %s not in copy register" % sha)
        blob = git.get("%s:%s" % (SOURCE_COMMIT, rr["path"]))
        if blob is None or hashlib.sha256(blob).hexdigest() != sha:
            raise SystemExit("FAIL CLOSED: source bytes for %s missing or hash mismatch" % rec["doc_id"])
        text_path = "data/text/%s.txt" % rec["doc_id"]
        tb = git.get("%s:%s" % (SOURCE_COMMIT, text_path))
        meta_b = git.get("%s:data/meta/%s.json" % (SOURCE_COMMIT, rec["doc_id"]))
        meta = json.loads(meta_b) if meta_b else {}
        if meta and meta.get("sha256") != sha:
            raise SystemExit("FAIL CLOSED: meta sha256 differs from audit for %s" % rec["doc_id"])
        issue = meta.get("issue_date") or rec.get("issue_date_meta", "")
        cmatch = None
        tw = title_words(rec["title"])
        for c in curated:
            if c["decision_date"] == issue and (tw & title_words(c["title"])):
                cmatch = c
                break
        if tb is None:
            an = {"ft": FlatText(""), "anchor": None, "block": None, "paren": None,
                  "notes": ["text_layer_file_missing"]}
        else:
            an = analyse_text(tb.decode("utf-8", errors="replace"))
        d = decide(rec, an, cmatch)
        d.update({
            "doc_id": rec["doc_id"], "judgment_id": rec["judgment_id"], "sha256": sha,
            "title": rec["title"], "method": "AUTOMATED_RULES", "status": "PROPOSAL_NOT_APPLIED",
            "source_path": rr["path"], "hash_verified": "SHA256_MATCH@" + SOURCE_COMMIT,
            "text_path": text_path + "@" + SOURCE_COMMIT if tb is not None else "",
        })
        out_rows.append(d)
    git.close()

    files: dict[str, bytes] = {}
    files["SC_CASE_NUMBER_PROPOSALS.csv"] = csv_bytes(PROPOSAL_COLS, out_rows)
    counts = {c: 0 for c in CLASSES}
    for r in out_rows:
        counts[r["classification"]] += 1
    acc = [{"classification": c, "count": str(counts[c])} for c in CLASSES]
    acc.append({"classification": "TOTAL", "count": str(sum(counts.values()))})
    if sum(counts.values()) != EXPECTED_RECORDS:
        raise SystemExit("FAIL CLOSED: accounting does not sum to %d" % EXPECTED_RECORDS)
    files["SC_CASE_NUMBER_ACCOUNTING.csv"] = csv_bytes(["classification", "count"], acc)

    review = []
    for r in out_rows:
        if r["classification"] in ("AMBIGUOUS", "PARTIALLY_CONFIRMED", "NOT_RECOVERABLE"):
            review.append(dict(r, review_reason="MANDATORY_" + r["classification"], sample_key=""))
    confirmed = [r for r in out_rows if r["classification"].startswith("CONFIRMED")]
    keyed = sorted(confirmed, key=lambda r: hashlib.sha256((SAMPLE_SEED + r["doc_id"]).encode()).hexdigest())
    for r in keyed[:SAMPLE_SIZE]:
        review.append(dict(r, review_reason="SAMPLE_CONFIRMED",
                           sample_key=hashlib.sha256((SAMPLE_SEED + r["doc_id"]).encode()).hexdigest()))
    rcols = ["doc_id", "sha256", "title", "classification", "review_reason", "sample_key",
             "host_case_numbers_normalised", "host_case_numbers_verbatim", "page", "line",
             "evidence_excerpt", "arising_from", "parent_case", "curated_match",
             "curated_case_number", "flags", "notes", "source_path", "text_path"]
    files["REVIEW_QUEUE.csv"] = csv_bytes(rcols, review)
    files["README.md"] = readme(counts, len(review)).encode("utf-8")
    sums = "".join("%s  %s\n" % (hashlib.sha256(files[k]).hexdigest(), k) for k in sorted(files))
    files["OUTPUT_SHA256SUMS"] = sums.encode("utf-8")
    return files


def readme(counts: dict, n_review: int) -> str:
    lines = [
        "# C11 - Supreme Court case-number recovery (proposal, not applied)",
        "",
        "Tool: `tools/scnum_c11.py` (%s). Deterministic; standard library only." % TOOL_VERSION,
        "Regenerate: `python tools/scnum_c11.py --repo /home/user/c7`; verify: add `--check`.",
        "",
        "## Scope",
        "",
        "The %d Supreme Court records in C10 `HF_JUDGMENT_METADATA_AUDIT.csv` whose `case_numbers_meta`"
        " is empty (the tool fails closed if the count differs). No metadata record is modified:"
        " every row is `status=PROPOSAL_NOT_APPLIED`, `method=AUTOMATED_RULES`." % EXPECTED_RECORDS,
        "",
        "## Inputs and integrity",
        "",
        "* Source PDF bytes: `git show %s:<path>` (path from C10 `HF_JUDGMENT_COPY_REGISTER.csv`);"
        " re-hashed, must equal the audited sha256, else the run aborts." % SOURCE_COMMIT,
        "* Text layer: `%s:data/text/<doc_id>.txt` (pipeline extraction of those bytes, `[[page N]]`"
        " markers = PDF page numbers). Metadata `%s:data/meta/<doc_id>.json` (sha256 cross-checked)."
        % (SOURCE_COMMIT, SOURCE_COMMIT),
        "* Curated cases: `%s:%s` (read-only), matched on identical decision date plus a shared"
        " significant title word." % (CURATED_COMMIT, CURATED_PATH),
        "* File names are never used.",
        "",
        "## Method",
        "",
        "1. Flatten the text layer (whitespace collapsed) keeping a map from every character to"
        " page and line.",
        "2. Locate the jurisdiction heading (`CIVIL APPELLATE JURISDICTION:`, `ORIGINAL JURISDICTION`,"
        " ...; OCR tolerant, edit distance <= 4, must be upper-case and followed by a colon or preceded"
        " by APPELLATE/ORIGINAL; lower-case prose 'jurisdiction' is never used). The first heading"
        " opens the block; the block ends at counsel appearances (`for the Appellant`, `Appearances"
        " for Parties`, `Judgment of the Court was delivered`, ...) or after 2,500 characters.",
        "3. Inside the block, find every `No./Nos./No(s).` marker followed by a number; read the case"
        " type backwards (label words / abbreviations, gutter letters A-H skipped) and the number list"
        " forwards (lists, `and`/`&`, ranges `4415-16`, `22 to 26`, `831/93`, `of 2004`, OCR"
        " `of2004`, gutter letters between tokens).",
        "4. A small state machine assigns each reference: HOST (start of block, after a further"
        " jurisdiction heading, or after `WITH` / `With` / `AND` / `alongwith` = connected matter);"
        " ARISING after `From the Judgment and Order`, `Appeal by special leave from`, `arising out"
        " of`, `impugned`, `against the order` (recorded in `arising_from`, never as host);"
        " PARENT when the reference is introduced by `in`/`In` (e.g. `Civil Misc. Petition No. X"
        " In Civil Appeal No. Y`, `Contempt Petition ... in W.P.(C) ...`); DESC after `Under Article"
        " 32`. References followed by `decided on` / `reported in` are treated as citations and"
        " dropped. A host number identical to an arising number is removed.",
        "5. Fallback for the newer SCR layout without a heading: the parenthesised cause-title"
        " number immediately before the decision date line (`(Civil Appeal No. 5605 of 2010) JUNE"
        " 25, 2014`) on pages 1-3. When both are present they are cross-checked.",
        "6. Case types normalised: CA, CRLA, WPC, WPCRL, WP (unqualified), SLPC, SLPCRL, TPC, TCC,"
        " CONTC, RPC, CURPC, MA, CMP, CRLMP, IA, ELA, ELP, OS, REF, PET (bare 'Petition' under"
        " Art. 32 in old SCR), APPEAL (bare). Form `TYPE-NUMBER-YEAR`; ranges are expanded;"
        " suffix letters kept (`CA-5085A-1991`).",
        "",
        "## Classification (exactly one per record)",
        "",
        "* CONFIRMED_FROM_SOURCE - one host number, recognised type, clean number and year.",
        "* CONFIRMED_MULTIPLE_CONNECTED - several clean host numbers (joint list, range or WITH matters).",
        "* PARTIALLY_CONFIRMED - host located but some part needs a human: year/number OCR-garbled"
        " or repaired (letter->digit), unrecognised type, `etc.` elision, or heading found but no"
        " number parsed.",
        "* AMBIGUOUS - competing candidates: cause-title number disagrees with the jurisdiction block,"
        " curated case number disagrees, or the only heading lies late in the file (may belong to"
        " the next reported case in an SCR page range).",
        "* NOT_RECOVERABLE - no text layer, or no heading/cause-title number printed.",
        "",
        "## Result",
        "",
        "| classification | count |",
        "| --- | --- |",
    ]
    for c in CLASSES:
        lines.append("| %s | %d |" % (c, counts[c]))
    lines.append("| TOTAL | %d |" % sum(counts.values()))
    lines += [
        "",
        "`REVIEW_QUEUE.csv` holds %d rows: every AMBIGUOUS, PARTIALLY_CONFIRMED and NOT_RECOVERABLE"
        " record plus %d CONFIRMED records chosen by lowest sha256(`%s` + doc_id)."
        % (n_review, SAMPLE_SIZE, SAMPLE_SEED),
        "",
        "## Output columns (beyond the required ones)",
        "",
        "`page` = PDF page marker of the first host reference in the text layer; `line` = line within"
        " that page of the text layer; `locator` = JURISDICTION_BLOCK or CAUSE_TITLE_PARENTHESIS;"
        " `parent_case` = matter in which an application/petition was filed; `flags` = parser"
        " warnings on host references; `notes` = cross-check results; `curated_match` = MATCH,"
        " MATCH_CURATED_SUBSET, PARTIAL_OVERLAP, MISMATCH, CURATED_RECORD_WITHOUT_NUMBER, CURATED_ONLY"
        " or NO_CURATED_RECORD.",
        "",
        "## Known failure patterns (all routed to the review queue)",
        "",
        "* OCR digit noise in number or year (`82 I of2001`, `of I999`, `of 200L`, `of 1~~`,"
        " `Petitions Nos. 22 to '.!G ... of Ul50`).",
        "* Lists interrupted by a page break/running header that the header filter does not"
        " recognise, or missing commas (`879 1209`), split digits (`254 7`, `3 798`).",
        "* Abbreviated second numbers (`Civil Appeal Nos. 2449 and 50 of 1992` = 2449-2450?).",
        "* `etc.` / `Etc. Etc.` elisions of connected matters.",
        "* Same number read both as host and in the arising/counsel section (S.P. Gupta).",
        "* Cause-title year differing from the jurisdiction heading (`D. No. 32135 of 2013` vs 2015).",
        "* Matters without a `No.` marker (`SLP (Civil) 27217 of 2010`) are recovered only via the"
        " cause-title fallback.",
        "",
        "## Limits",
        "",
        "* Works from the stored text layer, not a fresh PDF extraction; OCR noise in the SCR"
        " renditions (third-party mirror of e-SCR) can garble digits. Letter->digit year repairs"
        " are never auto-confirmed.",
        "* The SCR rendition is not the official SC cause title; numbers should be confirmed"
        " against the official judgment where one is available before being applied.",
        "* Connected matters printed only in the body (not in the jurisdiction block) are not captured;"
        " `etc.` elisions are flagged, not resolved.",
        "* `arising_from` type codes are best-effort abbreviations of the lower-court label.",
        "* Several doc_ids share one source file (same sha256); each is reported separately.",
        "* Curated comparison only covers the few cases_53 entries whose decision date and title match.",
        "* Proposal only: nothing is written to data/meta; legal/editorial review is required before use.",
        "",
    ]
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", required=True, help="git repo holding commits %s and %s"
                    % (SOURCE_COMMIT, CURATED_COMMIT))
    ap.add_argument("--audit-work", default=str(DEFAULT_AUDIT_WORK))
    ap.add_argument("--out", default=str(OUT_DIR))
    ap.add_argument("--check", action="store_true", help="regenerate and compare with existing outputs")
    a = ap.parse_args(argv)
    files = build(a.repo, Path(a.audit_work))
    out = Path(a.out)
    if a.check:
        bad = []
        for name, data in sorted(files.items()):
            p = out / name
            if not p.exists() or p.read_bytes() != data:
                bad.append(name)
        if bad:
            print("CHECK FAILED: differs: " + ", ".join(bad))
            return 1
        print("CHECK OK: %d files reproduced byte-for-byte" % len(files))
        return 0
    out.mkdir(parents=True, exist_ok=True)
    for name, data in sorted(files.items()):
        (out / name).write_bytes(data)
    acc = files["SC_CASE_NUMBER_ACCOUNTING.csv"].decode()
    print(acc)
    return 0


if __name__ == "__main__":
    sys.exit(main())
