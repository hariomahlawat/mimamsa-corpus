"""Mimamsa C13 judicial outcome extractor V4: text layer: boilerplate masking, page index, sentence splitting (ported from V3 c12-extract-v3/1.0.0).

All values are AUTOMATED CANDIDATES read from a PDF text layer; nothing is legally verified."""
import bisect
import re

VERSION = "c13-extract-v4/1.0.0"
STATUS = "AUTOMATED_CANDIDATE_NOT_VERIFIED"
UNVERIFIED = "OUTCOME_UNVERIFIED"
OUTCOME_VOCAB = ["allowed", "partly_allowed", "dismissed", "dismissed_as_withdrawn", "dismissed_as_infructuous",
                 "disposed_of_with_directions", "remanded", "set_aside_and_remanded", "transferred", "not_final",
                 UNVERIFIED]   # internal (v2) clause classes
PRINTED_VOCAB = ["allowed", "partly_allowed", "dismissed", "dismissed_as_withdrawn", "dismissed_as_infructuous",
                 "dismissed_in_default", "disposed_of", "disposed_of_with_directions", "remanded", "set_aside_and_remanded",
                 "transferred", "not_final", UNVERIFIED]
SUBST_VOCAB = ["relief_granted", "relief_partly_granted", "relief_refused", "no_adjudication",
               "remanded_for_fresh_decision", "interim_only", UNVERIFIED]



PAGE_RE = re.compile(r"\[\[page (\d+)\]\]")

# ------------------------------------------------------------------ boilerplate masking
_MASK_LINE_RES = [re.compile(p, re.I) for p in [
    r"^\s*[A-H]\s*$",                                   # S.C.R. margin letters
    r"^\s*[-–]?\s*\d{1,4}\s*[-–]?\s*$",                 # bare page numbers
    r"^\s*\[\s*\d{1,3}\s*\]\s*$",                        # [2]
    r"^\s*-\s*\d{1,3}\s*-\s*$",
    r"^\s*SUPREME COURT REPORTS\s*$",
    r"^\s*\[\d{4}\]\s*(?:Supp\.?\s*)?\(?\d*\)?\s*S\.\s*C\.\s*R\.?\s*(?:\d+)?\s*$",
    r"^\s*\d+\s+\[\d{4}\].{0,20}S\.C\.R\.?\s*$",
    r"Digitally\s+Signed", r"^\s*By\s*:", r"Signing\s+Da", r"Signature\s+Not\s+Verified",
    r"^\s*\d{2}:\d{2}(:\d{2})?\s*$", r"^\s*\d{4}\.\d{2}\.\d{2}\s+\d{2}:\d{2}", r"I attest", r"authenticity of this",
    r"integrity of this", r"I am the author of this", r"^\s*document\s*$", r"Page\s+\d+\s+of\s+\d+",
    r"Neutral\s+Citation", r"VERDICTUM", r"Whether\s+(speaking|reasoned|reportable|approved|to be referred)",
    r"^\s*(Yes|No)\s*/\s*(Yes|No)\s*$", r"^\s*(Yes|No)\s*$", r"^\s*:\s*$", r"Uploaded\s+on", r"Downloaded\s+on",
    r"^\s*\$\s*~", r"^\s*[*+]\s*$", r"^\s*\.{0,3}\s*$",
    r"\[[A-Z][A-Z .,'()-]{2,60},\s*(?:C\.?\s*)?J\.?\s*\]\s*$",  # S.C.R. running head [NAME, J.]
    r"^\s*\(?\s*Assisted by\s*:",
]]


_SIGN_BLOCK_RE = re.compile(r"Signed\s*By|Signing\s+Da|Signature\s+Not\s+Verified|Digitally\s+Signed|^\s*Signed\s*$", re.I)
_SIGN_TAIL_RE = re.compile(r"^[ \t]*[A-Z][A-Z .:'-]{0,38}[ \t]*$|^[ \t]*[\d.:/ -]{4,25}[ \t]*$")


def mask_boilerplate(text):
    """Replace boilerplate lines with spaces (length preserved so offsets stay valid). v3: the short upper-case
    name/date lines that follow a digital-signature stamp ('Signed By:AMIT KUMAR' / 'SHARMA') are masked too."""
    out = []
    tail = 0
    for line in text.splitlines(True):
        body = line.rstrip("\n")
        if body and (any(r.search(body) for r in _MASK_LINE_RES) or _SIGN_BLOCK_RE.search(body)):
            out.append(" " * len(body) + line[len(body):])
            tail = 3 if _SIGN_BLOCK_RE.search(body) else tail
        elif body and tail and _SIGN_TAIL_RE.match(body):
            out.append(" " * len(body) + line[len(body):])
            tail -= 1
        else:
            out.append(line)
            if body.strip():
                tail = 0
    return "".join(out)


def mask_page_markers(text):
    return PAGE_RE.sub(lambda m: " " * len(m.group(0)), text)


def page_index(text):
    starts, nums = [], []
    for m in PAGE_RE.finditer(text):
        starts.append(m.start())
        nums.append(int(m.group(1)))
    return starts, nums


def page_at(pidx, pos):
    starts, nums = pidx
    if not starts:
        return 1
    i = bisect.bisect_right(starts, pos) - 1
    return nums[i] if i >= 0 else nums[0]


def squash(s, limit=None):
    s = " ".join(s.split())
    if limit and len(s) > limit:
        s = s[:limit - 3].rstrip() + "..."
    return s


# ------------------------------------------------------------------ sentences
_ABBR = set("""no nos v vs mr mrs ms dr hon ltd co st sr jr j jj art arts sec secs s ss r rr cl para paras crl cr w p c a m
misc appl viz i e g etc rs lt col gen maj capt brig sub hav nk sep smt sh shri govt pvt inc o u ex ors anr vol pp ibid
supra cf ch sl dt dated nb l k b d f h n t y x z civ spl crim wp cwp lpa slp ca ia cm ma oa ta sc scc scr air hc rtd retd
regt bn coy hq pb adv sr. addl asst dy jt ld sri km""".split())


def sentences(text, start, end):
    """Yield (s, e) sentence spans inside text[start:end]. Splits at . ? ! ; : followed by whitespace,
    except after common legal abbreviations and single letters; also at blank-line breaks."""
    spans = []
    s = start
    for m in re.finditer(r"[.?!;:][\u201d\u2019\"']?(?=\s)", text[start:end]):
        p = start + m.end()
        ch = m.group(0)[0]
        if ch == ".":
            j = start + m.start()
            k = j
            while k > start and (text[k - 1].isalnum() or text[k - 1] == "."):
                k -= 1
            tok = text[k:j].lower().strip(".")
            if tok in _ABBR or (len(tok) == 1 and tok.isalpha()) or re.fullmatch(r"(?:[a-z]\.){1,4}[a-z]", tok):
                continue   # v3: initials ('B.D. Khunte') do not end a sentence
            nxt = text[p:p + 30].lstrip()
            if nxt[:1].islower() or nxt[:1].isdigit() and tok in ("no", "nos"):
                continue
        if text[s:p].strip():
            spans.append((s, p))
        s = p
    if text[s:end].strip():
        spans.append((s, end))
    return spans



_DOC_HEADER_RE = re.compile(r"^[ \t]*\*?[ \t]*(?:IN[ \t]+THE[ \t]+(?:HIGH[ \t]+COURT|SUPREME[ \t]+COURT)|HIGH[ \t]+COURT[ \t]+OF[ \t]+[A-Z]|"
                            r"REPORTABLE|SUPREME[ \t]+COURT[ \t]+OF[ \t]+INDIA)", re.M)
_CAUSE_TITLE_RE = re.compile(r"\b(?:versus|Versus|VERSUS|Vs\.?|VS\.?|V/[Ss]|Petitioners?|PETITIONERS?|Appellants?|APPELLANTS?|"
                             r"Respondents?|RESPONDENTS?)\b")


_SCR_CASE_HEAD_RE = re.compile(r"\bv\.\s[\s\S]{0,250}?\(\s*(?:Civil|Criminal|Writ|Special|Transferred|Original|Review|Contempt)"
                               r"(?:[^()]|\([^()]*\)){0,120}?No(?:[^()]|\([^()]*\)){0,80}\)\s*"
                               r"(?:JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)\s+\d{1,2},?\s+"
                               r"(?:19|20)\d{2}", re.I)



def mask_running_headers(text, pidx):
    """Mask lines that open at least 3 pages (2 in files of up to 5 pages; and 30% of pages) with the same words:
    running headers such as (only where they open a page, so the same words elsewhere stay readable)
    'WP(C) No.3173/2023 along with connected matters' or 'CWP No. 13553 of 2009 -2-'. Offsets are preserved."""
    starts = pidx[0]
    if len(starts) < 3:
        return text
    count = {}
    for ps in starts:
        seen = set()
        for line in text[ps:ps + 400].splitlines()[1:6]:
            k = re.sub(r"\s+", " ", re.sub(r"\d{1,4}\s*$|^\s*-?\s*\d{1,4}\s*-?\s*", "", line)).strip()
            if len(k) >= 8 and k not in seen:
                seen.add(k)
                count[k] = count.get(k, 0) + 1
    need = 2 if len(starts) <= 5 else 3
    heads = set(k for k, c in count.items() if c >= need and c >= 0.3 * len(starts))
    if not heads:
        return text
    chars = list(text)
    for ps in starts[1:]:
        pos = ps
        for k_line, line in enumerate(text[ps:ps + 400].splitlines(True)[:6]):
            body = line.rstrip("\n")
            if k_line > 0:
                k = re.sub(r"\s+", " ", re.sub(r"\d{1,4}\s*$|^\s*-?\s*\d{1,4}\s*-?\s*", "", body)).strip()
                if k in heads:
                    for i in range(pos, pos + len(body)):
                        chars[i] = " "
            pos += len(line)
    return "".join(chars)


class Doc:
    def __init__(self, text, meta):
        self.text = text
        self.meta = meta
        self.pidx = page_index(text)
        self.mt = mask_page_markers(mask_running_headers(mask_boilerplate(text), self.pidx))
        self.qspans = []
        self.qstarts = []



def _alpha_ratio(s):
    words = s.split()
    if not words:
        return 0.0
    good = len(re.findall(r"[A-Za-z]{3,}", s))
    return good / len(words)
