#!/usr/bin/env python3
"""Mimamsa Cycle 11: judicial relationships and statute links.

Deterministic builder. Reads only pinned, read-only inputs:
  * text layer + metadata at raw-data commit ad77758d of --repo (git objects, no checkout);
  * amendment graph at cfc52d57 (C9 STATUTORY) and the C10 statutory graph statuses;
  * curated cases at 21e73b83 (cases_53.jsonl);
  * C10 outputs (HF judgment audit, C10 judicial reconciliation).
Writes outputs/ next to this tools/ folder. Never writes anywhere else.

    python3.11 -I tools/relations_c11.py --repo /home/user/c7          # build
    python3.11 -I tools/relations_c11.py --repo /home/user/c7 --check  # rebuild in memory, compare bytes

Standard library only (no PyMuPDF, no jsonschema). Every relation stronger than CITES is a *proposal*;
nothing is ever marked LEGALLY_VALIDATED.
"""
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
from collections import Counter, defaultdict

TOOL_VERSION = "relations_c11 1.0.0"
TEXT_COMMIT = "ad77758d"
AG_COMMIT = "cfc52d57"
CURATED_COMMIT = "21e73b83"
AG_PATH = "legal_knowledge/audit_work/C9-LEGAL-EVIDENCE/STATUTORY/amendment_graph.csv"
CURATED_PATH = "legal_knowledge/curated_originals/case_law/v0.9/cases_53.jsonl"

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.dirname(HERE)                     # .../C11-JUDICIAL-QUALITY/relations
PKG = os.path.dirname(WS)                      # .../C11-JUDICIAL-QUALITY
AUDIT = os.path.dirname(PKG)                   # .../audit_work
OUT = os.path.join(WS, "outputs")
C10HF = os.path.join(AUDIT, "C10-HF-JUDGMENTS", "outputs")
C10J = os.path.join(AUDIT, "C10-RECONCILIATION", "workstreams", "judicial")
C10S = os.path.join(AUDIT, "C10-RECONCILIATION", "workstreams", "statutory")

STATUS_AUTO = "AUTOMATED_DETECTED"
STATUS_DOC = "DOCUMENTARY_CHECK_REQUIRED"
STATUS_ADV = "LEGAL_INTERPRETATION_ADVISER_REVIEW"
# "LEGALLY_VALIDATED" exists in the vocabulary but is never assigned by this tool.
STATUS_LEVELS = [STATUS_AUTO, STATUS_DOC, STATUS_ADV, "LEGALLY_VALIDATED"]
STRONG_RELATIONS = ("OVERRULES", "REVERSES", "QUESTIONS")
BNS_SWITCH = "2024-07-01"
# Instruments for which the amendment graph is shown to hold the complete amendment history. None is, on the C9/C10
# evidence (each graph carries NOT_LOCATED / unknown-scope rows, and IPC/CrPC/IEA carry only repeal rows), so no
# provision version can be established from the graph. Kept as an explicit, empty, auditable set.
COMPLETE_HISTORY_INSTRUMENTS = frozenset()


# ----------------------------------------------------------------------------- input reading
def git(repo, *args):
    return subprocess.run(["git", "-C", repo] + list(args), check=True, capture_output=True).stdout


def ls_tree(repo, commit, path):
    out = {}
    for line in git(repo, "ls-tree", "-r", commit, path).decode("utf-8").splitlines():
        meta, p = line.split("\t", 1)
        out[p] = meta.split()[2]
    return out


def cat_blobs(repo, shas):
    """Read many blobs through one `git cat-file --batch` call. Returns {sha: bytes}."""
    shas = sorted(set(shas))
    if not shas:
        return {}
    data = subprocess.run(["git", "-C", repo, "cat-file", "--batch"], input=("\n".join(shas) + "\n").encode(),
                          check=True, capture_output=True).stdout
    out, pos = {}, 0
    for _ in shas:
        nl = data.index(b"\n", pos)
        head = data[pos:nl].decode().split()
        size = int(head[2])
        out[head[0]] = data[nl + 1: nl + 1 + size]
        pos = nl + 1 + size + 1
    return out


def read_csv_file(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ws(s):
    return re.sub(r"\s+", " ", s or "").strip()


def clip(s, n=250):
    s = ws(s)
    return s if len(s) <= n else s[: n - 1] + "…"


# ----------------------------------------------------------------------------- text structure
PAGE_RE = re.compile(r"\[\[page (\d+)\]\]")


class Doc:
    """Text with page offsets, paragraph markers, editorial (reporter) zone and sentence boundaries."""

    def __init__(self, doc_id, text, court):
        self.doc_id = doc_id
        self.text = text
        self.court = court
        self.page_offs, self.page_nos = [], []
        for m in PAGE_RE.finditer(text):
            self.page_offs.append(m.start())
            self.page_nos.append(int(m.group(1)))
        self.editorial_end = self._editorial_end()
        self.para_offs, self.para_nos = self._paragraphs()

    def page_at(self, off):
        i = bisect.bisect_right(self.page_offs, off) - 1
        return self.page_nos[i] if i >= 0 else 1

    def page_text(self, page):
        if page not in self.page_nos:
            return ""
        i = self.page_nos.index(page)
        end = self.page_offs[i + 1] if i + 1 < len(self.page_offs) else len(self.text)
        return self.text[self.page_offs[i]:end]

    # SCR / JUDIS renditions carry reporter matter (headnote, "Case Law Cited/Reference", appearances)
    # before the judgment proper. Treatment words there ("relied on", "held inapplicable") are the
    # reporter's, never the court's.
    BODY_DELIVERED = re.compile(r"(?:Judgment|JUDGMENT|Order|ORDER|judgment|order)s?\s+of\s+the\s+Court\s+(?:was|were)\.?\s+delivered\s+by")
    HEADNOTE = re.compile(r"Headnotes?\b|HEADNOTE|Case Law Cited|Case Law Reference|Issue for Consideration")
    BODY_HEAD = re.compile(r"(?mi)^[ \t]*(?:J\s?U\s?D\s?G\s?M\s?E\s?N\s?T|O\s?R\s?D\s?E\s?R)[ \t]*:?[ \t]*$")

    def _editorial_end(self):
        if not self.court.startswith("Supreme Court"):
            return 0
        t = self.text
        half = min(len(t), max(len(t) // 2, 8000))
        m = self.BODY_DELIVERED.search(t, 0, half)
        if m:
            return m.end()
        h = self.HEADNOTE.search(t, 0, max(4000, len(t) // 6))
        if h:
            b = self.BODY_HEAD.search(t, h.end(), half)
            if b:
                return b.end()
        return 0

    PARA = re.compile(r"(?m)^[ \t]*(\d{1,3})[ \t]*[.)](?:[ \t]+|[ \t]*\n[ \t]*)(?=[A-Z“\"'(\[])")

    def _paragraphs(self):
        offs, nos, last = [], [], 0
        for m in self.PARA.finditer(self.text, self.editorial_end):
            n = int(m.group(1))
            if last < n <= last + 5:
                offs.append(m.start())
                nos.append(n)
                last = n
        return offs, nos

    def para_at(self, off):
        if off < self.editorial_end:
            return ""
        i = bisect.bisect_right(self.para_offs, off) - 1
        return str(self.para_nos[i]) if i >= 0 else ""

    def para_span(self, off):
        if off < self.editorial_end:
            return max(0, off - 1500), self.editorial_end
        i = bisect.bisect_right(self.para_offs, off) - 1
        start = self.para_offs[i] if i >= 0 else max(self.editorial_end, off - 1500)
        end = self.para_offs[i + 1] if i + 1 < len(self.para_offs) else min(len(self.text), off + 2500)
        start = max(start, off - 4000)
        end = min(end, off + 4000)
        return start, end


ABBREV = set("v vs ors anr no nos s ss sec art arts r rr para paras p pp mr ms mrs dr sh smt shri lt col gen maj capt "
             "j jj cj ltd co i e g etc viz cl sub vol supp hon ble u o ld ex retd sep hav nk sgt sqn ldr cdr wg "
             "govt dept st reg regs ch app ref sl cr crl c w a d m n k b h l t f".split())


def sentence_bounds(text, start, end, lo, hi):
    """Sentence containing [start, end) within [lo, hi). Simple boundary finder aware of legal abbreviations."""
    def is_boundary(i):
        # text[i] is '.', '?' or ';' followed by whitespace + uppercase/quote/digit-para
        if text[i] in "?":
            return True
        j = i - 1
        while j >= lo and text[j].isalpha():
            j -= 1
        word = text[j + 1:i].lower()
        if word in ABBREV or (len(word) == 1):
            return False
        if i > 0 and text[i - 1].isdigit():
            # "para 32." is a boundary only if a capital follows after newline
            pass
        return True

    s = lo
    i = start - 1
    while i > lo:
        c = text[i]
        if c in ".?" and i + 2 < len(text) and text[i + 1].isspace():
            k = i + 1
            while k < len(text) and text[k].isspace():
                k += 1
            if k < len(text) and (text[k].isupper() or text[k] in "“\"(") and is_boundary(i):
                s = i + 1
                break
        if start - i > 600:
            s = i
            break
        i -= 1
    e = hi
    i = end
    while i < hi:
        c = text[i]
        if c in ".?" and i + 2 < len(text) and text[i + 1].isspace():
            k = i + 1
            while k < len(text) and text[k].isspace():
                k += 1
            if k < len(text) and (text[k].isupper() or text[k] in "“\"(") and is_boundary(i):
                e = i + 1
                break
        if i - end > 600:
            e = i
            break
        i += 1
    return s, e


# ----------------------------------------------------------------------------- citation patterns
YEAR = r"(1[89]\d\d|20[0-3]\d)"
VOL = r"(\d{1,2})"
PAGE = r"(\d{1,5})"
SUPP = r"Supp\.?\s*\(?\s*(\d?)\s*\)?"
DOT_SCR = r"S\.?\s?C\.?\s?R\.?"

CIT_PATTERNS = [
    # (kind, regex, key-builder)
    ("INSC", re.compile(YEAR + r"\s*INSC\s*" + PAGE + r"\b"), lambda m: ("INSC", m.group(1), "", m.group(2))),
    ("SCC_ONLINE", re.compile(YEAR + r"\s*SCC\s*On\s?[Ll]ine\s*([A-Z][A-Za-z&]{0,8}(?:\s?&\s?[A-Z])?)\s*" + PAGE),
     lambda m: ("SCCOL", m.group(1), norm_court_code(m.group(2)), m.group(3))),
    ("SCC", re.compile(r"\(\s*" + YEAR + r"\s*\)\s*" + SUPP + r"\s*SCC\s*(?:\(\s*L\s*&\s*S\s*\)\s*)?" + PAGE),
     lambda m: ("SCC", m.group(1), "S" + (m.group(2) or "1"), m.group(3))),
    ("SCC", re.compile(r"\(\s*" + YEAR + r"\s*\)\s*" + VOL + r"\s*SCC\s*(?:\(\s*L\s*&\s*S\s*\)\s*)?" + PAGE),
     lambda m: ("SCC", m.group(1), m.group(2), m.group(3))),
    ("SCC", re.compile(r"(?<![\d(])" + YEAR + r"\s*\(\s*" + VOL + r"\s*\)\s*SCC\s*(?:\(\s*L\s*&\s*S\s*\)\s*)?" + PAGE),
     lambda m: ("SCC", m.group(1), m.group(2), m.group(3))),
    ("SCC", re.compile(r"(?<![\d(\[])" + YEAR + r"\s+(?:Vol\.?\s*)?" + VOL + r"\s+SCC\s*(?:\(\s*L\s*&\s*S\s*\)\s*)?" + PAGE),
     lambda m: ("SCC", m.group(1), m.group(2), m.group(3))),
    ("SCC", re.compile(r"(?<![\d(])" + YEAR + r"\s*" + SUPP + r"\s*SCC\s*" + PAGE),
     lambda m: ("SCC", m.group(1), "S" + (m.group(2) or "1"), m.group(3))),
    ("SCR", re.compile(r"[\[(\{]\s*" + YEAR + r"\s*[\])J]\s*" + SUPP + r"\s*" + DOT_SCR + r"\s*" + PAGE),
     lambda m: ("SCR", m.group(1), "S" + (m.group(2) or "1"), m.group(3))),
    ("SCR", re.compile(r"[\[(\{]\s*" + YEAR + r"\s*[\])J]\s*" + VOL + r"\s*" + DOT_SCR + r"\s*" + PAGE),
     lambda m: ("SCR", m.group(1), m.group(2), m.group(3))),
    ("SCR", re.compile(r"[\[(\{]\s*" + YEAR + r"\s*[\])J]\s*" + DOT_SCR + r"\s*" + PAGE),
     lambda m: ("SCR", m.group(1), "0", m.group(2))),
    ("SCR", re.compile(r"(?<![\d(\[])" + YEAR + r"\s*\(\s*" + VOL + r"\s*\)\s*" + DOT_SCR + r"\s*" + PAGE),
     lambda m: ("SCR", m.group(1), m.group(2), m.group(3))),
    ("SCR", re.compile(r"(?<![\d(\[])" + YEAR + r"\s*" + DOT_SCR + r"\s*\(\s*" + VOL + r"\s*\)\s*" + PAGE),
     lambda m: ("SCR", m.group(1), m.group(2), m.group(3))),
    ("SCR", re.compile(r"(?<![\d(\[])" + YEAR + r"\s*" + SUPP + r"\s*\(?\s*" + DOT_SCR + r"\s*\)?\s*" + PAGE),
     lambda m: ("SCR", m.group(1), "S" + (m.group(2) or "1"), m.group(3))),
    ("SCR", re.compile(r"(?<![\d(\[])" + YEAR + r"\s+" + VOL + r"\s+SCR\s+" + PAGE),
     lambda m: ("SCR", m.group(1), m.group(2), m.group(3))),
    ("SCR", re.compile(r"(?<![\d(\[])" + YEAR + r"\s*SCR\s*" + PAGE + r"\b"),
     lambda m: ("SCR", m.group(1), "0", m.group(2))),
    ("AIR", re.compile(r"\bAIR\s*" + YEAR + r"\s*(S\.?\s?C\.?|Supreme Court|SUPREME COURT|[A-Z][A-Za-z&]{1,10}(?:\s?&\s?[A-Z])?)\s*" + PAGE),
     lambda m: ("AIR", m.group(1), norm_court_code(m.group(2)), m.group(3))),
    ("JT", re.compile(r"\bJT\s*\(?\s*" + YEAR + r"\s*\)?\s*\(?\s*" + VOL + r"\s*\)?\s*(?:S\.?\s?C\.?)?\s*" + PAGE),
     lambda m: ("JT", m.group(1), m.group(2), m.group(3))),
    ("SLT", re.compile(r"\(?\s*" + YEAR + r"\s*\)?\s*\(?\s*" + VOL + r"\s*\)?\s*SLT\s*" + PAGE),
     lambda m: ("SLT", m.group(1), m.group(2), m.group(3))),
    ("SCALE", re.compile(r"\(?\s*" + YEAR + r"\s*\)?\s*\(?\s*" + VOL + r"\s*\)?\s*SCALE\s*" + PAGE),
     lambda m: ("SCALE", m.group(1), m.group(2), m.group(3))),
    ("SLR", re.compile(r"\(?\s*" + YEAR + r"\s*\)?\s*\(?\s*" + VOL + r"\s*\)?\s*SLR\s*" + PAGE),
     lambda m: ("SLR", m.group(1), m.group(2), m.group(3))),
    ("HC_NEUTRAL", re.compile(r"\b" + YEAR + r"\s*:\s*([A-Z]{2,6}(?:-[A-Z]{2,4})?)\s*:\s*(\d{1,6})(?:\s*-\s*(DB|FB))?"),
     lambda m: ("HCNC", m.group(1), m.group(2), m.group(3))),
]

CASE_TYPES = [
    ("CA", r"Civil\s+Appeal"),
    ("CRLA", r"Criminal\s+Appeal|Crl\.?\s*Appeal|Crl\.?\s*A\."),
    ("SLPC", r"Special\s+Leave\s+Petition\s*\(\s*C(?:ivil)?\s*\)|SLP\s*\(\s*C(?:ivil)?\s*\)"),
    ("WPC", r"W\.?\s?P\.?\s?\(\s*C(?:ivil)?\s*\)|Writ\s+Petition\s*\(\s*(?:C|Civil)\s*\)"),
    ("CWP", r"C\.?\s?W\.?\s?P\.?"),
    ("SWP", r"S\.?\s?W\.?\s?P\.?"),
    ("OWP", r"O\.?\s?W\.?\s?P\.?"),
    ("WRIA", r"WRIA|Writ\s*-\s*A|Writ\s+A"),
    ("LPA", r"L\.?\s?P\.?\s?A\.?"),
]
CASE_RE = re.compile(r"(?P<type>" + "|".join("(?P<%s>%s)" % (c, p) for c, p in CASE_TYPES) + r")\s*"
                     r"(?:Diary\s*)?No(?:s)?\s*\.?\s*(?:\(\s*s\s*\)\s*)?\.?\s*:?\s*(?P<num>\d{1,6})(?:\s*[-–]\s*\d{1,6})?"
                     r"\s*(?:of|/)\s*(?P<year>(?:19|20)\d\d)")
CASE_RE_NONO = re.compile(r"(?P<type>" + "|".join("(?P<%s>%s)" % (c, p) for c, p in CASE_TYPES[3:]) + r")\s*"
                          r"(?P<num>\d{1,6})\s*/\s*(?P<year>(?:19|20)\d\d)")


def norm_court_code(s):
    s = re.sub(r"[\s.]", "", s or "").upper()
    return {"SC": "SC", "SUPREMECOURT": "SC", "DEL": "DEL", "DELHI": "DEL", "P&H": "P&H", "PH": "P&H",
            "PUNJ": "P&H", "ALL": "ALL", "J&K": "J&K", "JK": "J&K", "JKL": "J&K"}.get(s, s)


COURT_CODE = {"Supreme Court of India": "SC", "High Court of Delhi": "DEL", "High Court of Punjab and Haryana": "P&H",
              "Allahabad High Court": "ALL", "High Court of Jammu and Kashmir": "J&K"}
HC_NC_CODE = {"DHC": "High Court of Delhi", "PHHC": "High Court of Punjab and Haryana",
              "AHC": "Allahabad High Court", "AHC-LKO": "Allahabad High Court", "JKLHC": "High Court of Jammu and Kashmir",
              "JKLHC-JMU": "High Court of Jammu and Kashmir", "JKLHC-SXR": "High Court of Jammu and Kashmir"}
SC_REPORTERS = {"SCC", "SCR", "INSC", "JT", "SLT", "SCALE"}


def key_str(k):
    return "|".join(x for x in k if x is not None)


def norm_scr_meta(s):
    """Normalise a reporter citation string from metadata/curated records to a key, or None."""
    for kind, rx, kb in CIT_PATTERNS:
        if kind in ("HC_NEUTRAL",):
            continue
        m = rx.search(s)
        if m:
            return key_str(kb(m))
    return None


CIT_ANCHOR = re.compile(r"SCC|S\.?\s?C\.?\s?R|AIR|JT|SLT|SCALE|SLR|INSC|\d{4}\s*:\s*[A-Z]")


def find_citations(text, lo=0, hi=None):
    """All reporter/neutral citations, longest-first non-overlapping. Returns sorted list of dicts.
    Patterns run only in short windows around anchor tokens (speed); results equal a full scan for these patterns."""
    hi = len(text) if hi is None else hi
    wins = []
    for a in CIT_ANCHOR.finditer(text, lo, hi):
        w0, w1 = max(lo, a.start() - 40), min(hi, a.end() + 40)
        if wins and w0 <= wins[-1][1]:
            wins[-1][1] = max(wins[-1][1], w1)
        else:
            wins.append([w0, w1])
    found = set()
    for w0, w1 in wins:
        for kind, rx, kb in CIT_PATTERNS:
            for m in rx.finditer(text, w0, w1):
                found.add((m.start(), -(m.end() - m.start()), m.end(), kind, key_str(kb(m)), m.group(0)))
    found = sorted(found)
    out, last_end = [], -1
    for s, _neg, e, kind, key, raw in found:
        if s < last_end:
            continue
        out.append({"start": s, "end": e, "kind": kind, "key": key, "raw": ws(raw)})
        last_end = e
    return out


CASE_ANCHOR = re.compile(r"Appeal|W\.?\s?P|C\.?\s?W\.?\s?P|S\.?\s?W\.?\s?P|O\.?\s?W\.?\s?P|WRIA|Writ|L\.?\s?P\.?\s?A|SLP|"
                         r"Special\s+Leave|Crl")


def find_case_numbers(text, lo=0):
    out, seen = [], set()
    wins = []
    for a in CASE_ANCHOR.finditer(text, lo):
        w0, w1 = max(lo, a.start() - 30), min(len(text), a.end() + 60)
        if wins and w0 <= wins[-1][1]:
            wins[-1][1] = max(wins[-1][1], w1)
        else:
            wins.append([w0, w1])
    ms = []
    for w0, w1 in wins:
        for rx in (CASE_RE, CASE_RE_NONO):
            ms.extend(rx.finditer(text, w0, w1))
    ms.sort(key=lambda m: (m.start(), -m.end()))
    for m in ms:
        if m.start() in seen:
            continue
        seen.add(m.start())
        gd = m.groupdict()
        ctype = next(c for c, _ in CASE_TYPES if gd.get(c))
        out.append({"start": m.start(), "end": m.end(), "kind": "CASE_NUMBER",
                    "key": "CASE|%s|%s|%s" % (ctype, int(m.group("num")), m.group("year")), "raw": ws(m.group(0))})
    return sorted(out, key=lambda d: d["start"])


def cluster(cits, text):
    """Group parallel citations ('[2008] 12 SCR 104 : (2008) 8 SCC 648') into one cited authority."""
    clusters = []
    for c in cits:
        if clusters:
            prev = clusters[-1][-1]
            between = text[prev["end"]:c["start"]]
            if len(between) <= 6 and re.fullmatch(r"[\s:=,]*", between) and (":" in between or "=" in between
                                                                             or "," in between or between.strip() == ""):
                clusters[-1].append(c)
                continue
        clusters.append([c])
    return clusters


# ----------------------------------------------------------------------------- party matching
PARTY_STOP = set("""union india of the and ors others other anr another state government govt chief army staff secretary
ministry defence through its ltd mr mrs smt shri sri ex retd no col lt major maj gen general sep sepoy hav havildar nk naik
sgt capt cdr wing commander air commodore brig brigadier sub subedar officer officers commanding etc vs versus pradesh
punjab haryana delhi uttar jammu kashmir corporation limited company bank board authority director controller accounts
pension pcda principal deputy addl additional district collector commissioner municipal singh kumar kaur ram lal chand
devi prasad das dass nath rao mohd mohammad ali khan respondent respondents petitioner petitioners appellant appellants
anr. union's indian navy force forces navy narayan ex-servicemen servicemen late widow smt. kumari risaldar lance
naib sepoy/ sowar gunner signalman craftsman rifleman hony honorary flt sqn ldr cpl lac jwo mwo cpo po wo ac sgt.
commandant commander-in-chief inspector senior junior welfare association society trust india's admn administration
vice deputy chairman member president sons son father mother wife daughter mahto sharma verma gupta yadav
public interest litigation centre common cause welfare supreme court high record advocates advocate association bench
tribunal armed judgment apex case cases legal matter matters writ petition appeal civil criminal rules section military
service services medical disability through behalf people peoples""".split())
# "sharma", "yadav" etc. are kept out of the distinctive set because they are too common to identify a case alone.


def party_tokens(meta):
    names = []
    p = meta.get("parties") or {}
    for side in ("petitioner", "respondent"):
        v = p.get(side) or []
        names.extend(v if isinstance(v, list) else [v])
    names.append(meta.get("title") or "")
    toks = set()
    for n in names:
        for t in re.findall(r"[A-Za-z]{4,}", n or ""):
            t = t.lower()
            if t not in PARTY_STOP:
                toks.add(t)
    return toks


GOV_PARTY = re.compile(r"union\s+of\s+india|\bstate\s+of\b|government|chief\s+of|ministry|secretary|controller|"
                       r"commanding|officer\s+in|director|commissioner|corporation|\bbank\b|authority|board", re.I)
RANK_WORDS = set("""ex retd no lt col colonel major maj gen general sep sepoy hav havildar nk naik sgt capt captain cdr wing commander
air commodore brig brigadier sub subedar etc ors anr others another and the of smt mr mrs dr risaldar lance naib sowar gunner
signalman craftsman rifleman hony honorary flt sqn ldr cpl lac jwo mwo cpo po wo ac late widow lieutenant admiral vice rear
marshal havaldar naik sigman cfn rect recruit gnr sgt l nb hony sub maj""".split())


def name_bigrams(meta):
    """Distinctive two-word name phrases of the private party (e.g. 'tarsem singh', 'kant sharma')."""
    p = meta.get("parties") or {}
    names = []
    for side in ("petitioner", "respondent"):
        v = p.get(side) or []
        names.extend(v if isinstance(v, list) else [v])
    out = set()
    for n in names:
        if not n or GOV_PARTY.search(n):
            continue
        words = [w.lower() for w in re.findall(r"[A-Za-z]+", n)]
        words = [w for w in words if w not in RANK_WORDS]
        for a, b in zip(words, words[1:]):
            if any(len(w) >= 4 and w not in PARTY_STOP for w in (a, b)):
                out.add((a, b))
    return out


def window_bigrams(window):
    words = [w.lower() for w in re.findall(r"[A-Za-z]+", window)]
    return set(zip(words, words[1:]))


def party_match(tokens, window):
    if not tokens:
        return False, []
    wt = set(t.lower() for t in re.findall(r"[A-Za-z]{4,}", window))
    present = sorted(tokens & wt)
    need = min(2, len(tokens))
    return len(present) >= need, present


# ----------------------------------------------------------------------------- treatment cues
CUES = [
    ("OVERRULES", r"\bover-?\s?rul(?:ed|e|ing)\b"),
    ("OVERRULES", r"does\s+not\s+lay\s+down\s+(?:the\s+|a\s+)?(?:correct|good)\s+(?:law|position)"),
    ("OVERRULES", r"(?:is|was)\s+not\s+(?:a\s+)?good\s+law"),
    ("OVERRULES", r"no\s+longer\s+(?:holds?\s+)?(?:a\s+)?good\s+law"),
    ("OVERRULES", r"not\s+correctly\s+decided"),
    ("REVERSES", r"\brevers(?:ed|ing|al)\b"),
    ("QUESTIONS", r"per\s+incuriam"),
    ("QUESTIONS", r"\bdoubted\b"),
    ("QUESTIONS", r"requires?\s+re-?\s?consideration"),
    ("QUESTIONS", r"referred\s+to\s+a\s+larger\s+[Bb]ench"),
    ("QUESTIONS", r"doubt\s+(?:the|its)\s+correctness\s+of\s+(?:the\s+)?(?:said\s+|that\s+|this\s+|above\s+)?(?:decision|judgment|view|ratio|law\s+laid)"),
    ("DISTINGUISHES", r"\bdistinguish(?:able|ed|ing)\b"),
    ("DISTINGUISHES", r"(?:is|are|would\s+be|was)\s+of\s+no\s+(?:assistance|help)"),
    ("DISTINGUISHES", r"(?:has|have|had)\s+no\s+application"),
    ("DISTINGUISHES", r"not\s+applicable\s+to\s+the\s+(?:facts|present|instant|case)"),
    ("DISTINGUISHES", r"held\s+inapplicable"),
    ("DISTINGUISHES", r"\b(?:is|was)\s+(?:wholly\s+|clearly\s+|totally\s+|grossly\s+|thus\s+)?(?:misconceived|misplaced)\b"),
    ("DISTINGUISHES", r"(?:does|do|would)\s+not\s+(?:apply|come\s+to\s+the\s+(?:aid|rescue))"),
    ("FOLLOWS", r"\bfollowed\b(?!\s+by)"),
    ("FOLLOWS", r"\bwe\s+(?:respectfully\s+)?follow\b"),
    ("FOLLOWS", r"\bfollowing\s+the\s+(?:ratio|decision|judgment|law\s+laid)"),
    ("FOLLOWS", r"\b(?:are|is|am)\s+bound\s+by\b"),
    ("APPLIES", r"applying\s+the\s+(?:ratio|principles?|law|dictum|test|decision|judgment)"),
    ("APPLIES", r"squarely\s+(?:applicable|appl(?:y|ies)|covered|covers)"),
    ("APPLIES", r"(?:is|are|stands?)\s+(?:fully\s+|squarely\s+|clearly\s+)?covered\s+by"),
    ("APPLIES", r"(?:fully|squarely|clearly|aptly)\s+applicable"),
    ("APPLIES", r"in\s+(?:the\s+)?light\s+of\s+the\s+(?:ratio|law\s+laid\s+down)"),
    ("APPLIES", r"in\s+view\s+(?:of\s+)?the\s+(?:law\s+laid\s+down|ratio)"),
    ("APPLIES", r"\bhas\s+been\s+settled\b"),
    ("APPLIES", r"\bon\s+all\s+fours\b"),
    ("EXPLAINS", r"\b(?:is|are|stands?)\s+explained\b"),
    ("EXPLAINS", r"\bwe\s+(?:would\s+|may\s+|must\s+)?explain\b"),
    ("CLARIFIES", r"\b(?:is|are|stands?)\s+(?:hereby\s+)?clarified\b"),
    ("CLARIFIES", r"\bwe\s+(?:would\s+|may\s+|must\s+)?clarify\b"),
    ("LEAVES_OPEN", r"\b(?:left|kept)\s+open\b"),
    ("LEAVES_OPEN", r"leave\s+(?:the|this|that)?\s*(?:question|issue|it)\s+open"),
    ("LEAVES_OPEN", r"express\s+no\s+(?:opinion|view)"),
    ("LEAVES_OPEN", r"need\s+not\s+(?:decide|go\s+into|examine)"),
]
ANY_CUE = re.compile("|".join("(?:%s)" % p for _, p in CUES), re.I)
CUE_WORDS = ("overrul", "over-rul", "over rul", "correct law", "correct position", "good law", "correctly decided", "revers",
             "incuriam", "doubt", "consideration", "larger bench", "distinguish", "no assistance", "no help", "application",
             "applicable", "not apply", "do not", "does not", "would not", "misconceived", "misplaced", "in view the", "follow", "bound by", "applying", "squarely",
             "covered", "light of", "view of the", "settled", "all fours", "explained", "clarif", "open", "express no",
             "need not", "of no")


def cue_prefilter(seg):
    low = seg.lower()
    return any(w in low for w in CUE_WORDS)
CUES = [(r, re.compile(p, re.I)) for r, p in CUES]
INHERENT_NEG = re.compile(r"does\s+not\s+lay|not\s+good|no\s+longer|not\s+correctly|no\s+application|not\s+applicable|"
                          r"no\s+(?:assistance|help)|does\s+not|do\s+not|would\s+not|need\s+not|express\s+no", re.I)
NEG_BEFORE = re.compile(r"\b(?:not|never|no\s+longer|cannot|can\s*not|could\s+not|neither|nor|hardly|without)\b[^.;]{0,25}$", re.I)
SUBMISSION = re.compile(r"learned\s+(?:senior\s+)?counsel|\bLd\.?\s+counsel|counsel\s+for\s+the|\bsubmit(?:ted|s|ting)\b|"
                        r"\bsubmission|\bcontend(?:ed|s|ing)?\b|\bcontention|\bargu(?:ed|es|ment)|\burg(?:ed|es)\b|"
                        r"placed\s+reliance|relied\s+(?:up)?on\s+by|\bAdvocate\b|\bA\.?S\.?G\.?\b|Solicitor\s+General|"
                        r"\bpleaded\b|\bit\s+is\s+the\s+case\s+of\s+the\s+(?:petitioner|respondent|appellant)|"
                        r"\b(?:he|she|they)\s+(?:also\s+|further\s+)?(?:stated|states|pointed\s+out|drew|relied|referred)", re.I)
COURT_VOICE = re.compile(r"\b(?:we\s+(?:are|find|hold|have|do|see|would)|in\s+our\s+(?:considered\s+)?(?:view|opinion)|"
                         r"this\s+court\s+(?:is|finds|holds|has)|i\s+(?:am|find|hold)|we\s+agree|we\s+disagree)\b", re.I)
FORUM_VERBS = (r"[^.;]{0,60}?\b(?:held|observed|relied|followed|distinguished|applied|took\s+the\s+view|found|noted|"
               r"placed\s+reliance|has\s+failed|failed|allowed|granted|rejected|dismissed|erred|appreciate|considered|concluded|"
               r"came\s+to|directed|passed|recorded|declined|refused)")
LOWER_FORUM = re.compile(r"\b(?:the\s+)?(?:learned\s+)?(?:Tribunal|AFT|Single\s+Judge|Writ\s+Court|court\s+below|"
                         r"Armed\s+Forces\s+Tribunal|trial\s+court|Division\s+Bench)\b" + FORUM_VERBS, re.I)
HIGH_COURT_ACT = re.compile(r"\bthe\s+High\s+Court\b" + FORUM_VERBS, re.I)
HIGH_COURT_WORD = re.compile(r"\bthe\s+High\s+Court\b", re.I)
OTHER_COURT_REPORT = re.compile(r"(?:(?:Supreme|Apex)\s+Court|this\s+Court|Their\s+Lordships|the\s+Court|the\s+Bench|Constitution\s+Bench)"
                                r"[^.;]{0,80}?\b(?:noted|held|observed|found|opined|said|ruled|took\s+the\s+view|"
                                r"considered|was\s+dealing|dealt)\b", re.I)
QUOTE_LEADIN = re.compile(r"(?:as\s+under|as\s+follows|in\s+the\s+following\s+(?:terms|words)|observed|held|reads?|stated|"
                          r"opined|ruled|in\s+(?:these|those)\s+words|para(?:graph)?s?\s*\d+[^:\n]{0,40})\s*"
                          r"(?:\([^)\n]{0,60}\))?\s*:\s*[-–—]?", re.I)
QUOTE_CLOSE = re.compile(r"\(\s*emphasis|\bemphasis\s+(?:supplied|added|ours|mine)|”|\.\.\.\s*\"", re.I)


PARTICIPLE = re.compile(r"(?:over-?\s?ruled|reversed|doubted|distinguished|followed|explained|clarified|left\s+open|kept\s+open)$", re.I)
PASSIVE_BEFORE = re.compile(r"\b(?:is|was|were|are|been|be|being|stands?|stood|hereby|get|got)\s+(?:[A-Za-z]+\s+){0,2}$", re.I)
AGENT_AFTER = re.compile(r"^\s*,?\s*(?:in|by)\s+(?:the\s+)?(?:(?:case|judgment|decision|ratio)s?\s+(?:of|in)\s+)?"
                         r"(?:[A-Z(\[]|this\s+Court|the\s+(?:Supreme|Apex|Hon|Constitution|larger|three|five|seven))")
IN_BY_BETWEEN = re.compile(r"^[\s,]*(?:in|by)\b", re.I)


STRONG_PAST = re.compile(r"(?:over-?\s?ruled|reversed|doubted)$", re.I)
PRESENT_VOICE_BEFORE = re.compile(r"(?:\b(?:is|are|hereby|stands?|be|being)\s+(?:[A-Za-z]+\s+)?|\bwe\s+(?:[A-Za-z]+\s+){0,2})$", re.I)


def treatment_direction(t, cue, cpos, cend, o):
    """Who does what to whom. Returns (ok, attribution_if_not_ok, reason).
    ok=True means the wording plausibly has the citing court acting on the cited authority (object = target)."""
    is_part = bool(PARTICIPLE.search(cue))
    dist = cpos - o["end"] if cpos >= o["end"] else o["start"] - cend
    if dist > 250:
        return False, "CUE_TOO_FAR", "cue word is %d characters from the cited authority" % dist
    if is_part and not PRESENT_VOICE_BEFORE.search(t[max(0, cpos - 40):cpos]):
        if STRONG_PAST.search(cue):
            return False, "REPORTED_TREATMENT_OF_TARGET", "past-tense '%s' without present/first-person voice: reads as history of the authority, not the citing court's act" % ws(cue).lower()
        return False, "DIRECTION_UNCLEAR", "past participle '%s' without present/first-person voice: who treated whom is not shown" % ws(cue).lower()
    if cpos >= o["end"]:
        between = t[o["end"]:cpos]
        _s0, s1 = sentence_bounds(t, o["start"], o["end"], max(0, o["start"] - 600), min(len(t), o["end"] + 800))
        if cpos >= s1 and not re.search(r"\b(?:said|that|this|these|those|above|aforesaid|supra|such)\s+(?:\w+\s+){0,2}"
                                        r"(?:judgment|decision|case|ruling|precedent|authority|view)s?\b|\(supra\)",
                                        t[s1:cpos], re.I):
            return False, "NEXT_SENTENCE_NO_BACK_REFERENCE", "cue is in the following sentence without a back-reference to the cited authority"
        if dist > 150:
            return False, "CUE_TOO_FAR", "cue word is %d characters after the cited authority" % dist
        if re.search(r"\b(?:wherein|in\s+which|it\s+was\s+held|held\s+that|observed\s+that|ruled\s+that|it\s+has\s+been\s+held)\b", between, re.I):
            return False, "TARGET_CONTENT", "cue sits inside the description of what the cited decision held"
    if cpos >= o["end"]:  # cue after the anchor
        after = t[cend:cend + 80]
        if AGENT_AFTER.match(after) and (is_part or re.search(r"incuriam|doubt", cue, re.I)):
            return False, "REPORTED_TREATMENT_OF_TARGET", "wording reports treatment of the cited authority by another decision ('%s ...')" % ws(after)[:40]
        if is_part and not PASSIVE_BEFORE.search(t[max(0, cpos - 40):cpos]):
            return False, "TARGET_IS_AGENT", "active verb after the cited authority: the cited decision is the likely subject (it did the %s)" % ws(cue).lower()
        return True, "", ""
    between = t[cend:o["start"]]
    if is_part and IN_BY_BETWEEN.match(between):
        return False, "TARGET_IS_AGENT", "'%s in/by <authority>': the cited decision did the %s, not the citing court" % (ws(cue).lower(), ws(cue).lower())
    return True, "", ""


def in_quotation(text, pos, lo):
    """True when `pos` most likely falls inside a quoted passage of another judgment/document."""
    look = text[max(lo, pos - 2500):pos]
    lo_q = look.rfind("“")
    lc_q = look.rfind("”")
    if lo_q > lc_q:
        return True, "unclosed opening quotation mark before the wording"
    if look[-1500:].count('"') % 2 == 1:
        return True, "odd number of straight quotation marks before the wording"
    tail = look[-1800:]
    lead = None
    for m in QUOTE_LEADIN.finditer(tail):
        lead = m
    if lead is not None:
        after = tail[lead.end():]
        if not QUOTE_CLOSE.search(after):
            return True, "wording follows a quotation lead-in ('%s') with no closing marker" % ws(lead.group(0))[-40:]
    return False, ""


# ----------------------------------------------------------------------------- statutes
PROV_ITEM = r"\d{1,3}[A-Z]{0,2}(?:\s*\(\s*[0-9a-zA-Z]{1,5}\s*\))*"
PROV_LIST = PROV_ITEM + r"(?:\s*(?:,|and|&|/|to|-|–|or)\s*" + PROV_ITEM + r")*"
PROV_HEAD = r"(?P<head>Sections?|Secs?\.|Ss\.|S\.|u/s\.?|Sub-section\s*\(\w+\)\s*of\s*Section|Rules?|Rr?\.|Regulations?|Regs?\.|Paras?|Paragraphs?|Articles?|Arts?\.)"
PRE_PROV = re.compile(PROV_HEAD + r"\s*(?P<list>" + PROV_LIST + r")\s*,?\s*(?:of|under|in)?\s*(?:the\s+)?(?:said\s+)?$", re.I)
POST_PROV = re.compile(r"^\s*,?\s*\(?\s*" + PROV_HEAD + r"\s*(?P<list>" + PROV_LIST + r")", re.I)

STATUTES = [
    # id, label, regex, amendment-graph instrument, default provision kind
    ("IAA-1911", "Indian Army Act, 1911", r"Indian\s+Army\s+Act(?:,?\s*1911)?", None, "s"),
    ("AFT-PR-2008", "Armed Forces Tribunal (Procedure) Rules, 2008",
     r"(?:Armed\s+Forces\s+Tribunals?|AFT)\s*\(\s*Procedure\s*\)\s*Rules(?:,?\s*2008)?", "I-AFT-PR-2008", "r"),
    ("AFT-2007", "Armed Forces Tribunal Act, 2007", r"Armed\s+Forces\s+Tribunals?\s+Act(?:,?\s*2007)?|\bA\.?F\.?T\.?\s+Act\b",
     "I-AFT-2007", "s"),
    ("AA-1950", "Army Act, 1950", r"(?<!Indian\s)(?<!Territorial\s)\bArmy\s+Act(?:,?\s*(?:of\s+)?1950)?", "I-AA-1950", "s"),
    ("AR-1954", "Army Rules, 1954", r"(?<!Territorial\s)\bArmy\s+Rules?(?:,?\s*1954)?", "I-AR-1954", "r"),
    ("PRA", "Pension Regulations for the Army",
     r"Pension\s+Regulations?\s+for\s+the\s+Army(?:\s*,?\s*(?:Part\s*[I1]+\s*,?\s*)?\(?\s*(?P<yr>1961|2008)\s*\)?)?", None, "reg"),
    ("RA-1987", "Regulations for the Army, 1987", r"(?<!Pension\s)Regulations?\s+for\s+the\s+Army(?:\s*,?\s*1987)?", None, "para"),
    ("ENT", "Entitlement Rules for Casualty Pensionary Awards",
     r"Entitlement\s+Rules(?:\s+for\s+Casualty\s+Pensionary\s+Awards?)?(?:[^.\n;]{0,60}?\b(?P<yr>1982|2008)\b)?", None, "r"),
    ("NA-1957", "Navy Act, 1957", r"\bNavy\s+Act(?:,?\s*1957)?", None, "s"),
    ("AFA-1950", "Air Force Act, 1950", r"\bAir\s+Force\s+Act(?:,?\s*1950)?", "I-AFA-1950", "s"),
    ("COI", "Constitution of India", r"\bConstitution\s+of\s+India\b|\bthe\s+Constitution\b(?!\s*\(\s*[\w\s-]{0,30}Amendment)"
     r"(?!\s+of\s+(?:the\s+)?(?:a\s+)?(?:Medical|Board|Court|Bench|Committee|Tribunal|Review|Release|Invaliding|Re-?survey|Selection))",
     None, "art"),
    ("CRPC-1973", "Code of Criminal Procedure, 1973", r"Code\s+of\s+Criminal\s+Procedure(?:,?\s*1973)?|\bCr\.?\s?P\.?\s?C\b\.?",
     "I-CRPC-1973", "s"),
    ("BNSS-2023", "Bharatiya Nagarik Suraksha Sanhita, 2023", r"Bharatiya\s+Nagarik\s+Suraksha\s+Sanhita(?:,?\s*2023)?|\bBNSS\b",
     "I-BNSS-2023", "s"),
    ("IPC-1860", "Indian Penal Code, 1860", r"Indian\s+Penal\s+Code(?:,?\s*1860)?|\bI\.\s?P\.\s?C\b\.?|\bIPC\b", "I-IPC-1860", "s"),
    ("BNS-2023", "Bharatiya Nyaya Sanhita, 2023", r"Bharatiya\s+Nyaya\s+Sanhita(?:,?\s*2023)?|\bBNS\b", "I-BNS-2023", "s"),
    ("IEA-1872", "Indian Evidence Act, 1872", r"(?:Indian\s+)?Evidence\s+Act(?:,?\s*1872)?", "I-IEA-1872", "s"),
    ("BSA-2023", "Bharatiya Sakshya Adhiniyam, 2023", r"Bharatiya\s+Sakshya\s+Adhiniyam(?:,?\s*2023)?", "I-BSA-2023", "s"),
]
STATUTES_RX = [(sid, lab, re.compile(rx), ag, kind) for sid, lab, rx, ag, kind in STATUTES]
# Structural-unit names used interchangeably in citations of the same instrument ("Para 173" / "Regulation 173").
KIND_NORMALISE = {("PRA", "para"): "reg", ("RA-1987", "reg"): "para"}
LISTED_ARTICLES = {"14", "16", "21", "32", "33", "136", "226", "227", "309", "311"}
BARE_ARTICLE = re.compile(r"\bArt(?:icle)?s?\.?\s*(?P<list>" + PROV_LIST + r")")
C10_STATUTE_NAMES = {"Army Act, 1950": "AA-1950", "Armed Forces Tribunal Act, 2007": "AFT-2007", "Army Rules, 1954": "AR-1954",
                     "Entitlement Rules": "ENT", "Pension Regulations for the Army": "PRA", "Regulations for the Army": "RA-1987",
                     "Air Force Act, 1950": "AFA-1950", "Indian Penal Code, 1860": "IPC-1860",
                     "Code of Criminal Procedure, 1973": "CRPC-1973", "Navy Act, 1957": "NA-1957",
                     "Indian Evidence Act, 1872": "IEA-1872", "AFT (Procedure) Rules, 2008": "AFT-PR-2008",
                     "Constitution of India": "COI", "Bharatiya Nagarik Suraksha Sanhita, 2023": "BNSS-2023",
                     "Bharatiya Nyaya Sanhita, 2023": "BNS-2023"}

HEAD_KIND = [(re.compile(r"^(?:sub-section|sections?|secs?\.|ss\.|s\.|u/s)", re.I), "s"), (re.compile(r"^(?:rules?|rr?\.)", re.I), "r"),
             (re.compile(r"^(?:regulations?|regs?\.)", re.I), "reg"), (re.compile(r"^(?:paras?|paragraphs?)", re.I), "para"),
             (re.compile(r"^(?:articles?|arts?\.)", re.I), "art")]

REL_CUES = [
    ("PROVISION_CHALLENGED", re.compile(r"\bvires\b|constitutional\s+validity|\bunconstitutional\b|validity\s+of\s+(?:the\s+)?"
                                        r"(?:said\s+)?(?:section|rule|regulation|provision|article)|\bstruck\s+down\b|strike\s+down", re.I)),
    ("PROVISION_HELD_INAPPLICABLE", re.compile(r"(?:not|never)\s+(?:be\s+)?(?:applicable|attracted)|has\s+no\s+application|"
                                               r"(?:does|would|will|did|shall)\s+not\s+apply|\binapplicable\b", re.I)),
    ("HISTORICAL_VERSION_RELEVANT", re.compile(r"as\s+it\s+(?:then\s+)?stood|\bunamended\b|pre-?\s?amend|(?:prior\s+to|before)\s+"
                                               r"(?:its\s+|the\s+)?amendment|since\s+(?:repealed|omitted)|(?:omitted|substituted|"
                                               r"inserted)\s+by|\berstwhile\b|\brepealed\b|\bas\s+amended\b|\bthen\s+in\s+force\b", re.I)),
    ("PROVISION_INTERPRETED", re.compile(r"\binterpret|\bconstru(?:e|ed|ing|ction)\b|meaning\s+of|\bpurport\b|plain\s+"
                                         r"(?:reading|language)|the\s+expression|true\s+import", re.I)),
    ("PROVISION_APPLIED", re.compile(r"in\s+exercise\s+of\s+(?:the\s+)?(?:its\s+)?powers?|\binvok(?:ed|ing)\b|(?:was|were|been|is|are)\s+"
                                     r"(?:charged|tried|convicted|sentenced|dismissed|discharged|invalided|released|"
                                     r"punished)\s+under|punishable\s+under|\bis\s+attracted\b|(?:is|are|was|were)\s+applicable", re.I)),
    ("PROVISION_QUOTED", re.compile(r"reads?\s+as\s+(?:under|follows)|which\s+reads|(?:is|are)\s+(?:reproduced|extracted|quoted)|"
                                    r"provides?\s+as\s+(?:under|follows)|(?:extracted|reproduced|quoted)\s+(?:below|hereunder|"
                                    r"as\s+under)|is\s+as\s+under", re.I)),
]
REL_PRIORITY = [r for r, _ in REL_CUES]
REL_STATUS = {"PROVISION_CHALLENGED": STATUS_DOC, "PROVISION_HELD_INAPPLICABLE": STATUS_DOC,
              "HISTORICAL_VERSION_RELEVANT": STATUS_DOC, "PROVISION_INTERPRETED": STATUS_DOC,
              "PROVISION_APPLIED": STATUS_DOC, "PROVISION_QUOTED": STATUS_AUTO, "RELATIONSHIP_UNRESOLVED": STATUS_AUTO,
              "STATUTE_MENTIONED": STATUS_AUTO}


def expand_list(lst):
    items = re.findall(r"\d{1,3}[A-Z]{0,2}(?:\s*\(\s*[0-9a-zA-Z]{1,5}\s*\))*|to|-|–", lst)
    out, prev, rng = [], None, False
    for it in items:
        if it in ("to", "-", "–"):
            rng = True
            continue
        base = re.match(r"\d{1,3}[A-Z]{0,2}", it).group(0)
        sub = re.sub(r"\s+", "", it[len(base):])
        if rng and prev is not None and prev.isdigit() and base.isdigit() and 0 < int(base) - int(prev) <= 15:
            for n in range(int(prev) + 1, int(base)):
                out.append((str(n), ""))
        out.append((base, sub))
        prev = base
        rng = False
    return out


def head_kind(head, default):
    for rx, k in HEAD_KIND:
        if rx.match(head.strip()):
            return k
    return default


# ----------------------------------------------------------------------------- amendment graph
def parse_graph_provisions(prov):
    """Extract provision numbers (kind, number) from an amendment-graph 'provision' cell."""
    p = prov or ""
    low = p.lower().strip()
    if low in ("", "unknown", "none") or low.startswith("unknown") or "unknown" in low[:20]:
        return "UNKNOWN", []
    if low.startswith("all") or low.startswith("whole"):
        return "WHOLE", []
    found = []
    for m in re.finditer(r"\b(ss?|rr?)\.\s*(\d{1,3}[A-Z]{0,2})((?:\s*(?:\([^)]*\))*\s*,\s*\d{1,3}[A-Z]{0,2})*)", p):
        kind = "s" if m.group(1).startswith("s") else "r"
        nums = [m.group(2)] + re.findall(r",\s*(\d{1,3}[A-Z]{0,2})", m.group(3) or "")
        for n in nums:
            found.append((kind, n))
    if not found:
        return "NON_NUMERIC", []
    return "SPECIFIC", sorted(set(found))


# ----------------------------------------------------------------------------- builder
class Builder:
    def __init__(self, repo):
        self.repo = repo
        self.inputs = {}

    # ---------------- load
    def load(self):
        repo = self.repo
        meta_t = ls_tree(repo, TEXT_COMMIT, "data/meta")
        text_t = ls_tree(repo, TEXT_COMMIT, "data/text")
        blobs = cat_blobs(repo, list(meta_t.values()))
        metas = {}
        for p, sha in meta_t.items():
            d = json.loads(blobs[sha].decode("utf-8"))
            if d.get("doc_type") in ("judgment", "order"):
                metas[d["doc_id"]] = d
        self.inputs["git:%s:data/meta (judgment/order records)" % TEXT_COMMIT] = hashlib.sha256(
            "".join(sorted(meta_t[p] for p in meta_t)).encode()).hexdigest()
        # canonical record per sha (22 SC copies carry two crawler records)
        by_sha = defaultdict(list)
        for did, d in metas.items():
            by_sha[d["sha256"]].append(did)
        self.judg = {}
        for sha, dids in by_sha.items():
            def rank(did):
                d = metas[did]
                yr = (d.get("issue_date") or "")[:4]
                return (0 if yr and did.split("-")[1] == yr else 1, did)
            dids = sorted(dids, key=rank)
            jid = "J-" + sha[:16]
            self.judg[jid] = {"jid": jid, "doc_id": dids[0], "alias_doc_ids": dids[1:], "meta": metas[dids[0]], "sha": sha}
        tshas = {}
        for jid, j in self.judg.items():
            p = "data/text/%s.txt" % j["doc_id"]
            if p not in text_t:
                for a in j["alias_doc_ids"]:
                    if "data/text/%s.txt" % a in text_t:
                        p = "data/text/%s.txt" % a
                        break
            if p in text_t:
                tshas[jid] = text_t[p]
                j["text_path"] = p
        tblobs = cat_blobs(repo, list(tshas.values()))
        self.inputs["git:%s:data/text (judgment texts)" % TEXT_COMMIT] = hashlib.sha256(
            "".join(sorted(tshas.values())).encode()).hexdigest()
        self.docs = {}
        for jid, sha in tshas.items():
            m = self.judg[jid]["meta"]
            self.docs[jid] = Doc(self.judg[jid]["doc_id"], tblobs[sha].decode("utf-8", "replace"), m.get("court") or "")
        self.no_text = sorted(j for j in self.judg if j not in self.docs)
        # groups (C10 reconciliation): different renditions of the same judgment
        recon_path = os.path.join(C10J, "JUDGMENT_RECONCILIATION.csv")
        self.inputs[os.path.relpath(recon_path, AUDIT)] = sha256_file(recon_path)
        self.group_of = {}
        self.group_members = defaultdict(set)
        self.recon = {}
        for r in read_csv_file(recon_path):
            jid = "J-" + r["copy_sha256"][:16]
            self.recon.setdefault(r["group_id"], []).append({k: r[k] for k in ("group_class", "copy_sha256", "rendition_type",
                                                                                 "official_court_copy_in_group", "presence",
                                                                                 "working_store_paths", "hf_paths", "crawler_doc_ids")})
            if jid in self.judg:
                self.group_of[jid] = r["group_id"]
        for jid in self.judg:
            g = self.group_of.setdefault(jid, "JG-" + self.judg[jid]["sha"][:12])
            self.group_members[g].add(jid)
        # curated cases + C10 held status
        cur = [json.loads(l) for l in git(repo, "show", "%s:%s" % (CURATED_COMMIT, CURATED_PATH)).decode("utf-8").splitlines() if l.strip()]
        self.inputs["git:%s:%s" % (CURATED_COMMIT, CURATED_PATH)] = hashlib.sha256(
            git(repo, "show", "%s:%s" % (CURATED_COMMIT, CURATED_PATH))).hexdigest()
        ccs_path = os.path.join(C10J, "CURATED_CASE_COPY_STATUS.csv")
        self.inputs[os.path.relpath(ccs_path, AUDIT)] = sha256_file(ccs_path)
        ccs = {r["case_id"]: r for r in read_csv_file(ccs_path)}
        sha_to_jid = {j["sha"]: jid for jid, j in self.judg.items()}
        self.curated = []
        for c in cur:
            st = ccs.get(c["id"], {})
            held_jids = []
            for p in (st.get("github_raw_data_paths") or "").split(";"):
                m = re.search(r"([0-9a-f]{64})", p)
                if m and m.group(1) in sha_to_jid:
                    held_jids.append(sha_to_jid[m.group(1)])
            self.curated.append({"id": c["id"], "title": c.get("title"), "date": c.get("decision_date"), "c10": st,
                                 "case_number": c.get("case_number"), "reporter": c.get("reporter_citation") or "",
                                 "held_status": st.get("held_status_c10", ""), "held_jids": held_jids})
        # C10 HF relationships (for cross-check) and legal issues
        rel_path = os.path.join(C10HF, "HF_JUDGMENT_RELATIONSHIPS.csv")
        li_path = os.path.join(C10HF, "HF_JUDGMENT_LEGAL_ISSUES.jsonl")
        for p in (rel_path, li_path):
            self.inputs[os.path.relpath(p, AUDIT)] = sha256_file(p)
        self.c10_rel = set()
        for r in read_csv_file(rel_path):
            self.c10_rel.add((r["source_judgment_id"], r["target"]))
        self.c10_li = {}
        with open(li_path, encoding="utf-8") as f:
            for line in f:
                d = json.loads(line)
                self.c10_li[d["judgment_id"]] = d.get("statutes") or {}
        # amendment graph
        ag_bytes = git(repo, "show", "%s:%s" % (AG_COMMIT, AG_PATH))
        self.inputs["git:%s:%s" % (AG_COMMIT, AG_PATH)] = hashlib.sha256(ag_bytes).hexdigest()
        ag9 = list(csv.DictReader(io.StringIO(ag_bytes.decode("utf-8"))))
        ag10_path = os.path.join(C10S, "amendment_graph_c10.csv")
        self.inputs[os.path.relpath(ag10_path, AUDIT)] = sha256_file(ag10_path)
        ag10 = {r["edge_id"]: r for r in read_csv_file(ag10_path)}
        self.graph = defaultdict(list)
        for r in ag9:
            inst = r["target_instrument_id"]
            if not inst:
                continue
            r10 = ag10.get(r["edge_id"], {})
            scope, provs = parse_graph_provisions(r["provision"])
            self.graph[inst].append({"edge_id": r["edge_id"], "provision": r["provision"], "scope": scope, "provs": provs,
                                     "status": r10.get("c10_status") or r["status"],
                                     "commencement": r10.get("commencement_date_evidenced") or r["commencement_date_evidenced"],
                                     "kind": r["edge_kind"]})
        for p in ("JUDICIAL_TREATMENT_C10.csv", "TREATMENT_CITATION_HITS.csv"):
            self.inputs[os.path.relpath(os.path.join(C10J, p), AUDIT)] = sha256_file(os.path.join(C10J, p))
        self.c10_treat = read_csv_file(os.path.join(C10J, "JUDICIAL_TREATMENT_C10.csv"))
        self.c10_hits = read_csv_file(os.path.join(C10J, "TREATMENT_CITATION_HITS.csv"))

    # ---------------- target index
    def build_index(self):
        self.idx = defaultdict(set)          # citation key -> groups (metadata-derived)
        self.idx_method = {}
        self.curated_idx = defaultdict(set)  # key -> groups via curated crosswalk
        self.curated_not_held = {}           # key -> curated id (case known, copy not in corpus)
        self.case_idx = defaultdict(set)     # CASE|type|num|year -> jids
        self.g_meta = {}
        self.party = {}
        for jid, j in self.judg.items():
            m = j["meta"]
            g = self.group_of[jid]
            self.party[jid] = party_tokens(m)
            nc = m.get("neutral_citation") or ""
            mm = re.search(YEAR + r"\s*INSC\s*(\d+)", nc)
            if mm:
                self.idx["INSC|%s||%s" % (mm.group(1), mm.group(2))].add(g)
            for rc in m.get("reported_citations") or []:
                k = norm_scr_meta(rc)
                if k:
                    self.idx[k].add(g)
            for cn in m.get("case_numbers") or []:
                mm = re.match(r"(.+?)/(\d+)/(\d{4})$", cn)
                if mm:
                    t = mm.group(1).upper().replace(".", "").replace(" ", "")
                    ct = {"WP(C)": "WPC", "CWP": "CWP", "SWP": "SWP", "OWP": "OWP", "WRIA": "WRIA", "LPA": "LPA"}.get(t)
                    if ct:
                        self.case_idx["CASE|%s|%s|%s" % (ct, int(mm.group(2)), mm.group(3))].add(jid)
            doc = self.docs.get(jid)
            if doc is not None:
                head = doc.text[:6000]
                if (m.get("court") or "").startswith("Supreme"):
                    for c in find_case_numbers(head):
                        self.case_idx[c["key"]].add(jid)
                else:
                    ncs = set(c["key"] for c in find_citations(doc.text[:700]) if c["kind"] == "HC_NEUTRAL")
                    if len(ncs) == 1:
                        k = ncs.pop()
                        parts = k.split("|")
                        if HC_NC_CODE.get(parts[2]) == m.get("court"):
                            self.idx[k].add(g)
                            self.idx_method[(k, g)] = "SELF_PRINTED_HC_NEUTRAL_CITATION"
        for c in self.curated:
            groups = set(self.group_of[j] for j in c["held_jids"])
            for part in re.split(r";", c["reporter"]):
                k = norm_scr_meta(part)
                if not k:
                    continue
                if groups and c["held_status"] == "HELD":
                    self.curated_idx[k] |= groups
                elif not groups:
                    self.curated_not_held[k] = "%s (%s; C10 held status: %s)" % (c["id"], c["title"], c["held_status"] or "?")

    def g_label(self, g):
        jids = sorted(self.group_members[g])
        j = self.judg[jids[0]]
        m = j["meta"]
        return {"jids": jids, "doc_ids": [self.judg[x]["doc_id"] for x in jids], "title": ws(m.get("title")),
                "date": min((self.judg[x]["meta"].get("issue_date") or "9999") for x in jids), "court": m.get("court") or "",
                "nc": m.get("neutral_citation") or ""}

    # ---------------- resolve
    def resolve_cluster(self, clus, src_jid, window, learned):
        src_g = self.group_of[src_jid]
        methods, groups = [], set()
        notes = []
        for c in clus:
            k = c["key"]
            if k in self.idx:
                gs = self.idx[k]
                groups |= gs
                for g in gs:
                    methods.append(self.idx_method.get((k, g), "NEUTRAL_CITATION_METADATA" if k.startswith("INSC")
                                                       else "REPORTER_CITATION_METADATA"))
            elif k in self.curated_idx:
                groups |= self.curated_idx[k]
                methods.append("CURATED_CROSSWALK_C10_HELD")
            elif learned is not None and k in learned:
                groups |= learned[k]
                methods.append("PARALLEL_CITATION_LEARNED")
            if k in self.curated_not_held:
                notes.append("curated case not in corpus: " + self.curated_not_held[k])
        if src_g in groups:
            return {"self": True}
        if len(groups) == 1:
            return {"state": "RESOLVED", "group": next(iter(groups)), "methods": sorted(set(methods)), "cands": [], "notes": notes}
        if len(groups) > 1:
            return {"state": "UNRESOLVED_CONFLICT", "group": "", "methods": sorted(set(methods)), "cands": sorted(groups), "notes": notes}
        # fallback: case number + party, or party + year + court
        first = clus[0]
        if first["kind"] == "CASE_NUMBER":
            jids = self.case_idx.get(first["key"], set())
            jids = set(j for j in jids if self.group_of[j] != src_g)
            if not jids:
                return {"state": "UNRESOLVED", "group": "", "methods": [], "cands": [], "notes": notes}
            ok = []
            wb = window_bigrams(window)
            for j in sorted(jids):
                if self.jid_bigrams(j) & wb:
                    ok.append(j)
            src_date = self.judg[src_jid]["meta"].get("issue_date") or ""
            if ok and all((self.judg[j]["meta"].get("issue_date") or "") == src_date for j in ok):
                return {"same_day": True}
            ok = [j for j in ok if (self.judg[j]["meta"].get("issue_date") or "") != src_date]
            gs = sorted(set(self.group_of[j] for j in ok))
            if len(gs) == 1:
                return {"state": "RESOLVED", "group": gs[0], "methods": ["CASE_NUMBER_PLUS_PARTY"], "cands": [], "notes": notes}
            cands = sorted(set(self.group_of[j] for j in (ok or jids)))
            return {"state": "UNRESOLVED_AMBIGUOUS" if len(cands) > 1 or ok else "UNRESOLVED_CASE_NUMBER_ONLY",
                    "group": "", "methods": [], "cands": cands, "notes": notes}
        parts = first["key"].split("|")
        kind = parts[0]
        try:
            year = int(parts[1])
        except ValueError:
            return {"state": "UNRESOLVED", "group": "", "methods": [], "cands": [], "notes": notes}
        if kind in ("SCC", "SCR", "JT", "SLT", "SCALE") or (kind == "AIR" and parts[2] == "SC") or (kind == "SCCOL" and parts[2] == "SC"):
            court = "Supreme Court of India"
        elif kind in ("AIR", "SCCOL"):
            court = {"DEL": "High Court of Delhi", "P&H": "High Court of Punjab and Haryana", "ALL": "Allahabad High Court",
                     "J&K": "High Court of Jammu and Kashmir"}.get(parts[2])
        else:
            court = None
        if not court:
            return {"state": "UNRESOLVED", "group": "", "methods": [], "cands": [], "notes": notes}
        years = {year} if kind in ("SCCOL",) else {year, year - 1}
        ok = []
        wb = window_bigrams(window)
        for g in self.groups_by_court_year(court, years):
            if g == src_g:
                continue
            if any(self.jid_bigrams(j) & wb for j in self.group_members[g]):
                ok.append(g)
        ok = sorted(set(ok))
        if len(ok) == 1:
            known = self.known_keys(ok[0])
            same_series = [k for k in known if k.split("|")[0] == kind]
            if same_series and first["key"] not in known:
                return {"state": "UNRESOLVED_CITATION_MISMATCH", "group": "", "methods": [], "cands": ok,
                        "notes": notes + ["party/year match, but the target's known %s citation is %s, not %s" % (
                            kind, ";".join(sorted(same_series)), first["key"])]}
            return {"state": "RESOLVED", "group": ok[0], "methods": ["PARTY_YEAR_COURT"], "cands": [], "notes": notes}
        if len(ok) > 1:
            return {"state": "UNRESOLVED_AMBIGUOUS", "group": "", "methods": [], "cands": ok, "notes": notes}
        return {"state": "UNRESOLVED", "group": "", "methods": [], "cands": [], "notes": notes}

    def known_keys(self, g):
        if not hasattr(self, "_known"):
            self._known = defaultdict(set)
            for src in (self.idx, self.curated_idx, getattr(self, "learned", {}) or {}):
                for k, gs in src.items():
                    for x in gs:
                        self._known[x].add(k)
        return self._known.get(g, set())

    def jid_bigrams(self, jid):
        if not hasattr(self, "_jb"):
            self._jb = {}
        if jid not in self._jb:
            self._jb[jid] = frozenset(name_bigrams(self.judg[jid]["meta"]))
        return self._jb[jid]

    def groups_by_court_year(self, court, years):
        if not hasattr(self, "_gcy"):
            self._gcy = defaultdict(set)
            for jid, j in self.judg.items():
                d = j["meta"].get("issue_date") or ""
                if d[:4].isdigit():
                    self._gcy[(j["meta"].get("court"), int(d[:4]))].add(self.group_of[jid])
        out = set()
        for y in years:
            out |= self._gcy.get((court, y), set())
        return sorted(out)

    # ---------------- citations pass
    def own_case_keys(self, jid):
        keys = set()
        for cn in self.judg[jid]["meta"].get("case_numbers") or []:
            mm = re.match(r"(.+?)/(\d+)/(\d{4})$", cn)
            if mm:
                t = mm.group(1).upper().replace(".", "").replace(" ", "")
                ct = {"WP(C)": "WPC", "CWP": "CWP", "SWP": "SWP", "OWP": "OWP", "WRIA": "WRIA", "LPA": "LPA"}.get(t)
                if ct:
                    keys.add("CASE|%s|%s|%s" % (ct, int(mm.group(2)), mm.group(3)))
        doc = self.docs.get(jid)
        if doc is not None:
            first = doc.page_text(doc.page_nos[0]) if doc.page_nos else doc.text[:4000]
            for c in find_case_numbers(first[:6000]):
                keys.add(c["key"])
        return keys

    def scan_citations(self):
        self.occ = []   # occurrences
        self.same_case_refs = 0
        self.same_day_refs = 0
        per_doc = {}
        for jid in sorted(self.docs):
            doc = self.docs[jid]
            cits = find_citations(doc.text) + find_case_numbers(doc.text)
            cits.sort(key=lambda c: c["start"])
            # drop case-number hits overlapping reporter hits
            clean, last = [], -1
            for c in cits:
                if c["start"] < last:
                    continue
                clean.append(c)
                last = c["end"]
            per_doc[jid] = cluster(clean, doc.text)
        self.per_doc = per_doc
        # pass 1: learn parallel citations from metadata-resolved clusters
        learned_raw = defaultdict(set)
        for jid, clusters in per_doc.items():
            for clus in clusters:
                strong = set()
                for c in clus:
                    if c["key"] in self.idx:
                        strong |= self.idx[c["key"]]
                if len(strong) == 1:
                    for c in clus:
                        if c["key"] not in self.idx and c["key"] not in self.curated_idx and c["kind"] != "CASE_NUMBER":
                            learned_raw[c["key"]] |= strong
        self.learned = {k: v for k, v in learned_raw.items() if len(v) == 1}
        self.learned_conflicts = sorted(k for k, v in learned_raw.items() if len(v) > 1)
        # pass 2: resolve
        self.self_cites = 0
        for jid, clusters in per_doc.items():
            doc = self.docs[jid]
            t = doc.text
            prev_end = 0
            own = self.own_case_keys(jid)
            for ci, clus in enumerate(clusters):
                s, e = clus[0]["start"], clus[-1]["end"]
                if clus[0]["kind"] == "CASE_NUMBER" and clus[0]["key"] in own:
                    self.same_case_refs += 1
                    prev_end = e
                    continue
                wlo = max(prev_end, s - 180)
                window = t[wlo:s]
                if ";" in window:
                    window = window[window.rfind(";") + 1:]
                if clus[0]["kind"] == "CASE_NUMBER":
                    window = t[max(prev_end, s - 220):min(len(t), e + 160)]
                prev_end = e
                res = self.resolve_cluster(clus, jid, window, self.learned)
                if res.get("self"):
                    self.self_cites += 1
                    continue
                if res.get("same_day"):
                    self.same_day_refs += 1
                    continue
                if res["state"] == "RESOLVED":
                    lab = self.g_label(res["group"])
                    srcd = self.judg[jid]["meta"].get("issue_date") or ""
                    if lab["date"] and srcd and lab["date"] > srcd:
                        res = {"state": "UNRESOLVED_TEMPORAL_CONFLICT", "group": "", "methods": res["methods"],
                               "cands": [res["group"]], "notes": res["notes"] + ["candidate decided after the citing judgment"]}
                    elif clus[0]["kind"] == "CASE_NUMBER" and lab["date"] and srcd and lab["date"] == srcd:
                        pass
                self.occ.append({"jid": jid, "ci": ci, "start": s, "end": e, "clus": clus, "res": res,
                                 "page": doc.page_at(s), "para": doc.para_at(s),
                                 "zone": "REPORTER_EDITORIAL" if s < doc.editorial_end else "BODY"})

    # ---------------- treatment
    def classify_treatment(self):
        self.cands = []
        occ_by_doc = defaultdict(list)
        for o in self.occ:
            occ_by_doc[o["jid"]].append(o)
        for jid in sorted(occ_by_doc):
            doc = self.docs[jid]
            t = doc.text
            src_court = self.judg[jid]["meta"].get("court") or ""
            olist = sorted(occ_by_doc[jid], key=lambda o: o["start"])
            cit_starts = [o["start"] for o in olist]
            olist = olist + self.name_refs(jid, doc, olist)
            olist.sort(key=lambda o: o["start"])
            starts = cit_starts
            for oi, o in enumerate(olist):
                if not cue_prefilter(t[max(0, o["start"] - 450):o["end"] + 700]):
                    continue
                plo, phi = doc.para_span(o["start"])
                s0, s1 = sentence_bounds(t, o["start"], o["end"], plo, phi)
                # next sentence too
                n0, n1 = sentence_bounds(t, min(s1 + 1, phi - 1), min(s1 + 2, phi), plo, phi) if s1 + 2 < phi else (s1, s1)
                win_lo, win_hi = s0, max(s1, n1)
                win_hi = min(win_hi, o["end"] + 700)
                win_lo = max(win_lo, o["start"] - 450)
                seg = t[win_lo:win_hi]
                if not ANY_CUE.search(seg):
                    continue
                for rel, rx in CUES:
                    for m in rx.finditer(seg):
                        cpos = win_lo + m.start()
                        cend = win_lo + m.end()
                        # another citation between this one and the cue?
                        lo_, hi_ = (o["end"], cpos) if cpos >= o["end"] else (cend, o["start"])
                        i0, i1 = bisect.bisect_left(starts, lo_), bisect.bisect_left(starts, hi_)
                        between_other = any(p != o["start"] for p in starts[i0:i1])
                        cand = self._candidate(jid, doc, o, rel, m.group(0), cpos, cend, win_lo, win_hi, between_other,
                                               src_court, plo)
                        self.cands.append(cand)

    def group_bigrams(self, g):
        if not hasattr(self, "_gb"):
            self._gb = {}
        if g not in self._gb:
            bg = set()
            for j in self.group_members[g]:
                bg |= name_bigrams(self.judg[j]["meta"])
            self._gb[g] = re.compile("|".join(r"\b%s[\s.]+%s\b" % (re.escape(a), re.escape(b)) for a, b in sorted(bg)), re.I) if bg else None
        return self._gb[g]

    def name_refs(self, jid, doc, olist):
        """Later references to a cited judgment by party name ('Tarsem Singh (supra)'), within a judgment that
        cites it by a citation string. They anchor treatment wording that sits paragraphs away from the citation."""
        out = []
        by_g = defaultdict(list)
        for o in olist:
            if o["res"]["state"] == "RESOLVED":
                by_g[o["res"]["group"]].append(o)
        t = doc.text
        for g in sorted(by_g):
            rx = self.group_bigrams(g)
            if rx is None:
                continue
            taken = [o["start"] for o in by_g[g]]
            n = 0
            for m in rx.finditer(t, doc.editorial_end):
                if any(abs(m.start() - p) < 250 for p in taken):
                    continue
                taken.append(m.start())
                o0 = by_g[g][0]
                out.append({"jid": jid, "ci": -1, "start": m.start(), "end": m.end(),
                            "clus": [{"start": m.start(), "end": m.end(), "kind": "NAME_REFERENCE", "key": o0["clus"][0]["key"],
                                      "raw": ws(m.group(0))}], "res": o0["res"], "page": doc.page_at(m.start()),
                            "para": doc.para_at(m.start()), "zone": "BODY", "anchor": "NAME_REFERENCE"})
                n += 1
                if n >= 40:
                    break
        return out

    def _candidate(self, jid, doc, o, rel, cue, cpos, cend, win_lo, win_hi, between_other, src_court, plo):
        t = doc.text
        reasons = []
        attribution = "COURT_LIKELY"
        negated = False
        pre = t[max(win_lo, cpos - 60):cpos]
        if not INHERENT_NEG.match(cue) and NEG_BEFORE.search(pre):
            negated = True
        if rel == "OVERRULES" and re.search(r"\bnot\s+(?:been\s+)?over-?\s?ruled|never\s+over-?\s?ruled", t[max(win_lo, cpos - 40):cend], re.I):
            negated = True
        s0, s1 = sentence_bounds(t, cpos, cend, max(plo, win_lo - 400), min(len(t), win_hi + 400))
        sent = t[s0:s1]
        res = o["res"]
        tgt_court = self.g_label(res["group"])["court"] if res["state"] == "RESOLVED" else ""
        if o["zone"] == "REPORTER_EDITORIAL":
            attribution = "REPORTER_EDITORIAL"
            reasons.append("wording is in the reporter's headnote/case-reference matter, not the judgment")
        else:
            inq, why = in_quotation(t, cpos, max(doc.editorial_end, cpos - 2500))
            if inq:
                attribution = "QUOTED_PASSAGE"
                reasons.append("quoted passage: " + why)
            elif SUBMISSION.search(sent):
                attribution = "PARTY_SUBMISSION_OR_MIXED"
                reasons.append("sentence carries submission wording (counsel/submitted/contended/relied upon by)")
                if COURT_VOICE.search(sent):
                    reasons.append("court-voice marker also present: mixed sentence, attribution unclear")
            elif OTHER_COURT_REPORT.search(t[s0:cpos]):
                attribution = "REPORTED_TREATMENT_OF_TARGET"
                reasons.append("sentence reports what another court/bench held or noted, not the citing court's own treatment")
            elif LOWER_FORUM.search(sent) or (src_court.startswith("Supreme") and HIGH_COURT_ACT.search(sent)):
                attribution = "LOWER_FORUM_REPORTED"
                reasons.append("sentence reports what a lower forum (Tribunal/Single Judge/High Court) did")
        if attribution == "COURT_LIKELY":
            ok, att2, why = treatment_direction(t, cue, cpos, cend, o)
            if not ok:
                attribution = att2
                reasons.append(why)
        if negated:
            reasons.append("negation before the cue word")
        if between_other:
            reasons.append("another citation lies between this citation and the cue: cue may refer to that authority")
        proposed = ""
        status = STATUS_AUTO
        if attribution == "COURT_LIKELY" and not negated and not between_other:
            if rel == "OVERRULES":
                hier_ok = (src_court.startswith("Supreme") and (not tgt_court or tgt_court.startswith("Supreme"))) or \
                          (src_court and src_court == tgt_court)
                if not hier_ok:
                    reasons.append("citing court (%s) cannot overrule the cited court (%s): wording reports another court's "
                                   "treatment of the target" % (src_court, tgt_court or "unresolved"))
                    attribution = "REPORTED_TREATMENT_OF_TARGET"
                else:
                    proposed = rel
            elif rel == "REVERSES":
                hier_ok = src_court.startswith("Supreme") and tgt_court and not tgt_court.startswith("Supreme")
                if not hier_ok:
                    reasons.append("reversal needs an appellate relationship (higher court, same case); not shown")
                    attribution = "REPORTED_TREATMENT_OF_TARGET"
                else:
                    proposed = rel
            elif rel == "QUESTIONS" and not src_court.startswith("Supreme") and tgt_court.startswith("Supreme"):
                reasons.append("a High Court questioning a Supreme Court decision is unusual: likely reports another court")
                attribution = "REPORTED_TREATMENT_OF_TARGET"
            else:
                proposed = rel
        if proposed:
            status = STATUS_ADV if proposed in STRONG_RELATIONS else STATUS_DOC
            if proposed in STRONG_RELATIONS:
                reasons.append("overruling/reversal/questioning proposals always go to legal adviser review")
        elif rel in STRONG_RELATIONS and attribution in ("REPORTED_TREATMENT_OF_TARGET", "TARGET_IS_AGENT") and not negated:
            status = STATUS_ADV
            reasons.append("possible report of a later court's treatment of the cited authority: adviser to check")
        exc_lo = max(0, min(o["start"], cpos) - 60)
        exc_hi = max(o["end"], cend) + 60
        excerpt = t[exc_lo:exc_hi]
        if len(ws(excerpt)) > 250:
            mid = (cpos + cend) // 2
            excerpt = t[max(0, mid - 125):mid + 125]
        return {"jid": jid, "occ": o, "cue_relation": rel, "cue": ws(cue), "cue_page": doc.page_at(cpos),
                "cue_para": doc.para_at(cpos), "attribution": attribution, "negated": negated,
                "between_other": between_other, "proposed": proposed, "status": status, "reasons": reasons,
                "excerpt": clip(excerpt), "cpos": cpos}

    # ---------------- statute links
    def scan_statutes(self):
        self.links = []
        for jid in sorted(self.docs):
            doc = self.docs[jid]
            t = doc.text
            date = self.judg[jid]["meta"].get("issue_date") or ""
            agg = {}
            for sid, lab, rx, ag, dkind in STATUTES_RX:
                for m in rx.finditer(t, doc.editorial_end):
                    if sid == "AA-1950" and re.match(r"\s*(?:and|&)\s*Air\s+Force", t[m.end():m.end() + 20]):
                        continue  # "Army and Air Force (Disposal ...)" style titles are not the Army Act
                    inst = sid
                    if sid in ("PRA", "ENT"):
                        yr = m.groupdict().get("yr")
                        inst = "%s-%s" % (sid, yr) if yr else "%s-UNSPECIFIED" % sid
                    pre = t[max(0, m.start() - 140):m.start()]
                    post = t[m.end():m.end() + 60]
                    provs = []
                    pm = PRE_PROV.search(pre)
                    if pm:
                        k = head_kind(pm.group("head"), dkind)
                        provs = [(k, b, sub) for b, sub in expand_list(pm.group("list"))]
                    else:
                        qm = POST_PROV.search(post)
                        if qm:
                            k = head_kind(qm.group("head"), dkind)
                            provs = [(k, b, sub) for b, sub in expand_list(qm.group("list"))]
                        elif sid == "AR-1954":
                            q2 = re.match(r"\s*(" + PROV_LIST + r")", post)
                            if q2 and m.group(0).rstrip().endswith("Rule"):
                                provs = [("r", b, sub) for b, sub in expand_list(q2.group(1))]
                    provs = [(KIND_NORMALISE.get((sid, k), k), b, sub) for k, b, sub in provs]
                    if sid == "COI":
                        provs = [x for x in provs if x[0] == "art"]
                    self._add_link(agg, jid, doc, inst, lab, ag, None, m.start(), m.end())
                    for k, b, sub in provs:
                        self._add_link(agg, jid, doc, inst, lab, ag, (k, b, sub), m.start(), m.end())
            # bare listed Articles (Constitution) not already captured
            for m in BARE_ARTICLE.finditer(t, doc.editorial_end):
                tail = t[m.end():m.end() + 60]
                if re.match(r"\s*(?:of|under)\s+(?:the\s+)?(?!Constitution)[A-Z]", tail):
                    continue
                for b, sub in expand_list(m.group("list")):
                    if b in LISTED_ARTICLES:
                        self._add_link(agg, jid, doc, "COI", "Constitution of India", None, ("art", b, sub), m.start(), m.end(),
                                       bare=True)
            for key in sorted(agg):
                self.links.append(self._finish_link(jid, date, agg[key]))

    def _add_link(self, agg, jid, doc, inst, lab, ag, prov, s, e, bare=False):
        t = doc.text
        if prov:
            k, b, sub = prov
            pid = "%s:%s.%s" % (inst, k, b)
        else:
            pid = ""
        key = (inst, pid)
        a = agg.get(key)
        if a is None:
            a = agg[key] = {"inst": inst, "label": lab, "ag": ag, "pid": pid, "subs": set(), "mentions": 0, "pages": set(),
                            "cues": Counter(), "best": None, "first": None, "bare_only": True, "excluded_cues": Counter()}
        a["mentions"] += 1
        a["pages"].add(doc.page_at(s))
        if not bare:
            a["bare_only"] = False
        if prov and prov[2]:
            a["subs"].add(prov[2])
        plo, phi = doc.para_span(s)
        s0, s1 = sentence_bounds(t, s, e, max(0, s - 500), min(len(t), e + 500))
        sent = t[s0:s1]
        ex = t[max(s0, s - 110):min(s1, e + 130)]
        if a["first"] is None:
            a["first"] = (doc.page_at(s), doc.para_at(s), clip(ex))
        if not prov:
            hm = REL_CUES[2][1].search(sent)
            if hm:
                a["cues"]["HISTORICAL_VERSION_RELEVANT"] += 1
                if a["best"] is None:
                    a["best"] = ("HISTORICAL_VERSION_RELEVANT", doc.page_at(s), doc.para_at(s), clip(ex), ws(hm.group(0)))
            return
        inq, _ = in_quotation(t, s, max(doc.editorial_end, s - 2500))
        sub = bool(SUBMISSION.search(sent))
        near = t[max(s0, s - 120):min(s1, e + 150)]
        for rel, rx in REL_CUES:
            mm = rx.search(near)
            if not mm:
                continue
            if rel == "PROVISION_QUOTED":
                # the cue must follow the mention ("Section 69 ... reads as under")
                if not rx.search(t[e:min(len(t), e + 200)]):
                    continue
            elif rel not in ("PROVISION_CHALLENGED",) and (inq or sub):
                a["excluded_cues"][rel + (":QUOTED" if inq else ":SUBMISSION")] += 1
                continue
            a["cues"][rel] += 1
            cur = a["best"]
            if cur is None or REL_PRIORITY.index(rel) < REL_PRIORITY.index(cur[0]):
                a["best"] = (rel, doc.page_at(s), doc.para_at(s), clip(ex), ws(mm.group(0)))

    def _finish_link(self, jid, date, a):
        inst, pid = a["inst"], a["pid"]
        if pid:
            rel = a["best"][0] if a["best"] else "RELATIONSHIP_UNRESOLVED"
        else:
            rel = "STATUTE_MENTIONED"
        if a["best"]:
            page, para, excerpt, cue = a["best"][1], a["best"][2], a["best"][3], a["best"][4]
        else:
            page, para, excerpt = a["first"]
            cue = ""
        # amendment graph
        ag = a["ag"]
        edges, whole, unknown, nonnum = [], [], [], []
        if ag and ag in self.graph:
            kind_num = None
            if pid:
                k, num = pid.split(":")[1].split(".", 1)
                kind_num = (k, num)
            for ed in self.graph[ag]:
                if ed["scope"] == "UNKNOWN":
                    unknown.append(ed)
                elif ed["scope"] == "WHOLE":
                    whole.append(ed)
                elif ed["scope"] == "NON_NUMERIC":
                    nonnum.append(ed)
                elif kind_num and kind_num in ed["provs"]:
                    edges.append(ed)
        if not ag:
            vstat, vbasis = "VERSION_NOT_ESTABLISHED", "no amendment-graph instrument for this statute"
        elif ag not in self.graph:
            vstat, vbasis = "VERSION_NOT_ESTABLISHED", "instrument %s has no rows in the amendment graph" % ag
        elif not pid:
            vstat, vbasis = "VERSION_NOT_ESTABLISHED", "statute-level mention: no provision version applies"
        elif not date:
            vstat, vbasis = "VERSION_NOT_ESTABLISHED", "judgment date unknown"
        elif ag not in COMPLETE_HISTORY_INSTRUMENTS:
            vstat = "VERSION_NOT_ESTABLISHED"
            vbasis = ("amendment graph does not record a complete amendment history for %s (absence of an edge is not "
                      "evidence that the provision was unamended)" % ag)
            if edges:
                vbasis += "; matched edge(s): " + ",".join("%s[%s]" % (ed["edge_id"], ed["status"]) for ed in edges)
        else:
            rel_edges = edges + whole
            unevid = [ed for ed in rel_edges if ed["status"] != "EVIDENCED" or not ed["commencement"]]
            if unknown or nonnum:
                vstat = "VERSION_NOT_ESTABLISHED"
                vbasis = ("%d amendment-graph edge(s) on %s have unknown or non-numeric provision scope (%s), so no "
                          "provision can be shown unaffected" % (len(unknown) + len(nonnum), ag,
                                                                 ",".join(sorted(ed["edge_id"] for ed in (unknown + nonnum))[:6])))
            elif unevid:
                vstat = "VERSION_NOT_ESTABLISHED"
                vbasis = "commencement not evidenced for %s" % ",".join(sorted(ed["edge_id"] for ed in unevid)[:6])
            else:
                before = [ed["edge_id"] for ed in rel_edges if ed["commencement"][:10] <= date]
                vstat = "VERSION_AT_JUDGMENT_DATE_INDICATED_NOT_VERIFIED"
                vbasis = ("all matched edges have evidenced commencement; in force at judgment date: %s. The relevant "
                          "version may depend on the date of the facts, not the judgment" % (",".join(before) or "principal text"))
        trans = ""
        if inst in ("IPC-1860", "CRPC-1973", "IEA-1872", "BNS-2023", "BNSS-2023", "BSA-2023"):
            if date and date >= BNS_SWITCH:
                trans = ("judgment dated on/after 2024-07-01 (BNS/BNSS/BSA switch noted; commencement notification "
                         "C9-AG-%s-COMM NOT_LOCATED in the amendment graph): which code governs depends on the date of the "
                         "offence/proceeding and is NOT assumed" % ("BNS" if inst in ("IPC-1860", "BNS-2023") else
                                                                    "BNSS" if inst in ("CRPC-1973", "BNSS-2023") else "BSA"))
            elif date:
                trans = "judgment pre-dates 2024-07-01 (switch noted, not assumed)"
                if inst in ("BNS-2023", "BNSS-2023", "BSA-2023"):
                    trans += "; ANOMALY: new-code mention in a pre-switch judgment (check text/OCR or date)"
        # C10 cross-check
        c10 = self.c10_li.get(jid)
        if c10 is None:
            c10x = "NOT_IN_C10_LEGAL_ISSUES"
        else:
            names = [n for n, v in C10_STATUTE_NAMES.items() if v == inst.split("-UNSPECIFIED")[0].replace("-1961", "").replace("-2008", "").replace("-1982", "") or v == inst]
            hit = [n for n in names if n in c10]
            if not names:
                c10x = "STATUTE_NOT_IN_C10_VOCABULARY"
            elif not hit:
                c10x = "C10_DID_NOT_DETECT_STATUTE"
            elif pid:
                num = pid.split(".", 1)[1]
                c10x = "C10_PROVISION_AGREES" if any(num == str(p) for n in hit for p in (c10[n].get("provisions") or [])) \
                    else "C10_STATUTE_ONLY"
            else:
                c10x = "C10_STATUTE_AGREES"
        st = REL_STATUS[rel]
        notes = []
        if a["bare_only"] and inst == "COI":
            notes.append("bare 'Article N' mention attributed to the Constitution")
        if a["excluded_cues"]:
            notes.append("cues ignored (quoted/submission context): " + ";".join("%s x%d" % (k, v) for k, v in sorted(a["excluded_cues"].items())))
        if inst.endswith("-UNSPECIFIED"):
            notes.append("instrument year/version not printed with the mention")
        return {"jid": jid, "inst": inst, "label": a["label"], "pid": pid, "subs": ";".join(sorted(a["subs"])),
                "rel": rel, "status": st, "cues": ";".join("%s x%d" % (k, v) for k, v in sorted(a["cues"].items())),
                "cue": cue, "mentions": a["mentions"], "pages": ";".join(str(p) for p in sorted(a["pages"])),
                "page": page, "para": para, "excerpt": excerpt, "ag": ag or "",
                "edges": ";".join(sorted(ed["edge_id"] for ed in edges)), "whole": ";".join(sorted(ed["edge_id"] for ed in whole)),
                "unknown_n": len(unknown) + len(nonnum), "vstat": vstat, "vbasis": vbasis, "trans": trans, "c10x": c10x,
                "notes": " | ".join(notes)}

    # ---------------- outputs
    def edges_table(self):
        agg = {}
        cand_by_occ = defaultdict(list)
        for i, c in enumerate(self.cands):
            cand_by_occ[id(c["occ"])].append(c)
        for o in sorted(self.occ, key=lambda o: (o["jid"], o["start"])):
            res = o["res"]
            tkey = res["group"] if res["state"] == "RESOLVED" else "RAW:" + o["clus"][0]["key"]
            k = (o["jid"], tkey)
            a = agg.get(k)
            if a is None:
                a = agg[k] = {"jid": o["jid"], "tkey": tkey, "res": res, "occs": [], "raws": [], "keys": set()}
            a["occs"].append(o)
            for c in o["clus"]:
                if c["raw"] not in a["raws"]:
                    a["raws"].append(c["raw"])
                a["keys"].add(c["key"])
        rows = []
        for k in sorted(agg):
            a = agg[k]
            occs = a["occs"]
            body = [o for o in occs if o["zone"] == "BODY"]
            first = body[0] if body else occs[0]
            doc = self.docs[a["jid"]]
            t = doc.text
            exc = t[max(0, first["start"] - 120):first["end"] + 120]
            res = a["res"]
            j = self.judg[a["jid"]]
            props = []
            for o in occs:
                for c in self._cands_for(o):
                    if c["proposed"]:
                        props.append(c["proposed"])
            if res["state"] == "RESOLVED":
                lab = self.g_label(res["group"])
                strong_meta = all(m in ("NEUTRAL_CITATION_METADATA", "REPORTER_CITATION_METADATA", "SELF_PRINTED_HC_NEUTRAL_CITATION")
                                  for m in res["methods"])
                status = STATUS_AUTO if strong_meta else STATUS_DOC
                c10m = "C10_CITES_AGREES" if any((a["jid"], x) in self.c10_rel for x in lab["jids"]) else "NOT_IN_C10_170"
            else:
                lab = {"jids": [], "doc_ids": [], "title": "", "date": "", "court": "", "nc": ""}
                status = STATUS_AUTO
                c10m = ""
            eid = "E-" + hashlib.sha256(("%s|%s" % (a["jid"], a["tkey"])).encode()).hexdigest()[:12]
            cands = [self.g_label(g) for g in res.get("cands", [])]
            rows.append({
                "edge_id": eid, "source_judgment_id": a["jid"], "source_doc_id": j["doc_id"],
                "source_court": j["meta"].get("court") or "", "source_date": j["meta"].get("issue_date") or "",
                "relation": "CITES", "status": status, "target_state": res["state"],
                "target_group_id": res["group"] if res["state"] == "RESOLVED" else "",
                "target_judgment_ids": ";".join(lab["jids"]), "target_doc_ids": ";".join(lab["doc_ids"]),
                "target_title": lab["title"], "target_date": lab["date"], "target_court": lab["court"],
                "cited_strings": " || ".join(a["raws"][:4]), "citation_keys": ";".join(sorted(a["keys"])),
                "resolution_method": ";".join(res.get("methods", [])),
                "candidates": " || ".join("%s %s (%s, %s)" % (g["jids"][0], g["title"][:60], g["date"], g["court"]) for g in cands[:5]),
                "resolution_note": "; ".join(res.get("notes", [])[:2]),
                "occurrences": len(occs), "body_occurrences": len(body),
                "pages": ";".join(str(p) for p in sorted(set(o["page"] for o in occs))),
                "page": first["page"], "paragraph": first["para"], "zone": first["zone"], "excerpt": clip(exc),
                "proposed_treatments": ";".join(sorted(set(props))), "c10_crosscheck": c10m,
            })
        self.edge_rows = rows
        return rows

    def _cands_for(self, o):
        if not hasattr(self, "_cmap"):
            self._cmap = defaultdict(list)
            for c in self.cands:
                self._cmap[id(c["occ"])].append(c)
        return self._cmap.get(id(o), [])

    def cand_table(self):
        rows = []
        edge_id_of = {}
        for r in self.edge_rows:
            edge_id_of[(r["source_judgment_id"], r["target_group_id"] or "RAW:" + r["citation_keys"].split(";")[0])] = r["edge_id"]
        seen = set()
        for c in sorted(self.cands, key=lambda c: (c["jid"], c["cpos"], c["occ"]["start"], c["cue_relation"])):
            o = c["occ"]
            res = o["res"]
            tkey = res["group"] if res["state"] == "RESOLVED" else "RAW:" + o["clus"][0]["key"]
            # dedupe: same citing occurrence + same cue position
            dk = (c["jid"], o["start"], c["cpos"], c["cue_relation"])
            if dk in seen:
                continue
            seen.add(dk)
            j = self.judg[c["jid"]]
            lab = self.g_label(res["group"]) if res["state"] == "RESOLVED" else None
            cid = "TC-" + hashlib.sha256(("%s|%d|%d|%s" % dk).encode()).hexdigest()[:12]
            eid = "E-" + hashlib.sha256(("%s|%s" % (c["jid"], tkey)).encode()).hexdigest()[:12]
            rows.append({
                "candidate_id": cid, "edge_id": eid, "source_judgment_id": c["jid"], "source_doc_id": j["doc_id"],
                "source_court": j["meta"].get("court") or "", "source_date": j["meta"].get("issue_date") or "",
                "target_state": res["state"], "target_group_id": res["group"] if lab else "",
                "target_doc_ids": ";".join(lab["doc_ids"]) if lab else "", "target_title": lab["title"] if lab else "",
                "anchor": o.get("anchor", "CITATION_STRING"),
                "cited_string": o["clus"][0]["raw"], "citation_page": o["page"], "citation_paragraph": o["para"],
                "cue_relation": c["cue_relation"], "cue_text": c["cue"], "cue_page": c["cue_page"], "cue_paragraph": c["cue_para"],
                "attribution": c["attribution"], "negated": "YES" if c["negated"] else "NO",
                "other_citation_between": "YES" if c["between_other"] else "NO",
                "proposed_relation": c["proposed"], "status": c["status"], "reasons": "; ".join(c["reasons"]),
                "excerpt": c["excerpt"],
            })
        self.cand_rows = rows
        return rows

    def link_table(self):
        rows = []
        for l in self.links:
            j = self.judg[l["jid"]]
            lid = "SL-" + hashlib.sha256(("%s|%s|%s" % (l["jid"], l["inst"], l["pid"])).encode()).hexdigest()[:12]
            rows.append({
                "link_id": lid, "judgment_id": l["jid"], "doc_id": j["doc_id"], "court": j["meta"].get("court") or "",
                "judgment_date": j["meta"].get("issue_date") or "", "instrument_id": l["inst"], "instrument": l["label"],
                "provision_id": l["pid"], "sub_provisions": l["subs"], "relationship": l["rel"], "status": l["status"],
                "cue_text": l["cue"], "cues_all": l["cues"], "mentions": l["mentions"], "pages": l["pages"],
                "page": l["page"], "paragraph": l["para"], "excerpt": l["excerpt"],
                "amendment_graph_instrument": l["ag"], "amendment_graph_edges": l["edges"],
                "amendment_graph_whole_instrument_edges": l["whole"], "amendment_graph_unknown_scope_edges": l["unknown_n"],
                "version_status": l["vstat"], "version_basis": l["vbasis"], "code_transition_note": l["trans"],
                "c10_crosscheck": l["c10x"], "notes": l["notes"],
            })
        self.link_rows = rows
        return rows

    # ---------------- run
    def run(self):
        self.load()
        self.build_index()
        self.scan_citations()
        self.classify_treatment()
        self.scan_statutes()
        files = {}
        files["CASE_CITATION_GRAPH.csv"] = to_csv(self.edges_table())
        files["TREATMENT_CANDIDATES.csv"] = to_csv(self.cand_table())
        files["STATUTE_JUDGMENT_LINKS.csv"] = to_csv(self.link_table())
        import dossier_c11
        files["PRIORITY_TREATMENT_DOSSIER.md"] = dossier_c11.build(self).encode("utf-8")
        files["GRAPH_SUMMARY.json"] = (json.dumps(self.summary(), indent=1, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
        return files

    def summary(self):
        e = self.edge_rows
        c = self.cand_rows
        l = self.link_rows
        resolved = [r for r in e if r["target_state"] == "RESOLVED"]
        body_edges = [r for r in e if r["body_occurrences"]]
        indeg = Counter()
        for r in resolved:
            indeg[r["target_group_id"]] += 1
        top = []
        for g, n in indeg.most_common(25):
            lab = self.g_label(g)
            top.append({"group": g, "in_degree_citing_judgments": n, "title": lab["title"], "date": lab["date"],
                        "doc_ids": lab["doc_ids"]})
        kinds = Counter()
        for o in self.occ:
            for cc in o["clus"]:
                kinds[cc["kind"]] += 1
        return {
            "tool": TOOL_VERSION, "pinned_inputs": {"text_layer_commit": TEXT_COMMIT, "amendment_graph_commit": AG_COMMIT,
                                                    "curated_commit": CURATED_COMMIT},
            "input_sha256": dict(sorted(self.inputs.items())),
            "judgments": {"metadata_records_judgment_order": sum(1 + len(j["alias_doc_ids"]) for j in self.judg.values()),
                          "distinct_copies_by_sha": len(self.judg), "with_text": len(self.docs), "without_text": self.no_text},
            "citations": {
                "citation_strings_detected_by_kind": dict(sorted(kinds.items())),
                "cited_authority_occurrences_excluding_self": len(self.occ), "self_citations_dropped": self.self_cites,
                "same_case_number_references_dropped": self.same_case_refs,
                "same_day_connected_matter_references_dropped": self.same_day_refs,
                "edges_total": len(e), "edges_with_body_occurrence": len(body_edges),
                "edges_by_target_state": dict(sorted(Counter(r["target_state"] for r in e).items())),
                "edges_by_relation": dict(sorted(Counter(r["relation"] for r in e).items())),
                "edges_by_status": dict(sorted(Counter(r["status"] for r in e).items())),
                "resolved_edges_by_method": dict(sorted(Counter(r["resolution_method"] for r in resolved).items())),
                "resolution_rate_edges": round(len(resolved) / len(e), 4) if e else 0,
                "resolution_rate_note": ("share of distinct (citing judgment, cited authority) edges whose target is a held "
                                         "corpus judgment; most cited authorities are simply not in the 4,259-judgment corpus, "
                                         "so a low rate is expected and is not an error rate"),
                "resolution_rate_sc_reporter_edges": self._sc_rate(),
                "distinct_resolved_targets": len(indeg),
                "learned_parallel_aliases": len(self.learned), "learned_alias_conflicts_discarded": len(self.learned_conflicts),
                "c10_170_cites_reproduced": self._c10_repro(),
                "top_in_degree": top,
            },
            "treatment": {
                "cue_hits": len(c),
                "by_cue_relation": dict(sorted(Counter(r["cue_relation"] for r in c).items())),
                "by_attribution": dict(sorted(Counter(r["attribution"] for r in c).items())),
                "proposed_by_relation": dict(sorted(Counter(r["proposed_relation"] for r in c if r["proposed_relation"]).items())),
                "by_status": dict(sorted(Counter(r["status"] for r in c).items())),
                "legally_validated": 0,
            },
            "statute_links": {
                "links_total": len(l), "judgments_with_links": len(set(r["judgment_id"] for r in l)),
                "by_instrument": dict(sorted(Counter(r["instrument_id"] for r in l).items())),
                "by_relationship": dict(sorted(Counter(r["relationship"] for r in l).items())),
                "by_status": dict(sorted(Counter(r["status"] for r in l).items())),
                "by_version_status": dict(sorted(Counter(r["version_status"] for r in l).items())),
                "with_amendment_graph_edge_match": sum(1 for r in l if r["amendment_graph_edges"]),
                "c10_crosscheck": dict(sorted(Counter(r["c10_crosscheck"] for r in l).items())),
            },
            "status_vocabulary": STATUS_LEVELS, "legally_validated_assigned": 0,
        }

    def _sc_rate(self):
        n = r = 0
        for e in self.edge_rows:
            ks = e["citation_keys"].split(";")
            if any(k.split("|")[0] in ("SCC", "SCR", "INSC") for k in ks):
                n += 1
                r += e["target_state"] == "RESOLVED"
        return {"edges": n, "resolved": r, "rate": round(r / n, 4) if n else 0}

    def _c10_repro(self):
        mine = set()
        for e in self.edge_rows:
            if e["target_state"] == "RESOLVED":
                for t in e["target_judgment_ids"].split(";"):
                    mine.add((e["source_judgment_id"], t))
        c10 = set(x for x in self.c10_rel if x[1].startswith("J-"))
        # C10 targets are single copies; count a C10 edge reproduced when any copy of its target group is linked
        ok = 0
        missing = []
        for s, t in sorted(c10):
            g = self.group_of.get(t)
            if g and any((s, x) in mine for x in self.group_members[g]):
                ok += 1
            else:
                missing.append("%s->%s" % (s, t))
        return {"c10_edges": len(c10), "reproduced": ok, "not_reproduced_examples": missing[:15]}


def to_csv(rows):
    buf = io.StringIO()
    if rows:
        w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()), lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return buf.getvalue().encode("utf-8")


def write_outputs(files):
    os.makedirs(OUT, exist_ok=True)
    for name, data in files.items():
        with open(os.path.join(OUT, name), "wb") as f:
            f.write(data)


def sums(files, extra):
    allf = dict(files)
    allf.update(extra)
    lines = ["%s  %s" % (hashlib.sha256(allf[n]).hexdigest(), n) for n in sorted(allf)]
    return ("\n".join(lines) + "\n").encode()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--repo", required=True, help="git clone holding commits %s, %s, %s" % (TEXT_COMMIT, AG_COMMIT, CURATED_COMMIT))
    ap.add_argument("--check", action="store_true", help="rebuild in memory and compare with outputs/ byte for byte")
    a = ap.parse_args()
    sys.path.insert(0, HERE)
    b = Builder(a.repo)
    files = b.run()
    readme_path = os.path.join(OUT, "README.md")
    extra = {}
    if os.path.exists(readme_path):
        with open(readme_path, "rb") as f:
            extra["README.md"] = f.read()
    files["OUTPUT_SHA256SUMS"] = sums(files, extra)
    if a.check:
        bad = []
        for n, data in sorted(files.items()):
            p = os.path.join(OUT, n)
            if not os.path.exists(p):
                bad.append(n + " (missing)")
                continue
            with open(p, "rb") as f:
                if f.read() != data:
                    bad.append(n)
        if bad:
            print("CHECK FAILED: " + ", ".join(bad))
            sys.exit(1)
        print("CHECK OK: %d outputs reproduce byte-identically" % len(files))
        return
    write_outputs(files)
    s = json.loads(files["GRAPH_SUMMARY.json"])
    print(json.dumps({"edges": s["citations"]["edges_total"], "resolution_rate": s["citations"]["resolution_rate_edges"],
                      "treatment_cue_hits": s["treatment"]["cue_hits"], "proposed": s["treatment"]["proposed_by_relation"],
                      "statute_links": s["statute_links"]["links_total"]}, indent=1))


if __name__ == "__main__":
    main()
