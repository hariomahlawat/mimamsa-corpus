"""Mimamsa C13 judicial outcome extractor V4: proceeding map: case numbers, host proceedings, batch sections (ported from V3; V4 fixes below).

All values are AUTOMATED CANDIDATES read from a PDF text layer; nothing is legally verified."""
import bisect
import re

from v4_text import (  # noqa: F401
    squash,
    _CAUSE_TITLE_RE,
    _SCR_CASE_HEAD_RE)
from v4_quotes import (  # noqa: F401
    in_spans)


# ------------------------------------------------------------------ paragraph numbers
_PARA_CAND_RE = re.compile(r"(?m)^[ \t]*(\d{1,3})[ \t]*\.(?=\s)")


def host_paragraphs(text, start, end, quote_list, qstarts):
    """Longest +1/+2 chain of line-initial paragraph numbers (outside marked quotes). Returns [(pos, n)]."""
    cands = []
    for m in _PARA_CAND_RE.finditer(text, start, end):
        q = in_spans(quote_list, qstarts, m.start()) if quote_list else None
        if q and q[2] == "marked":
            continue
        cands.append((m.start(), int(m.group(1))))
    if not cands:
        return []
    L = len(cands)
    dp = [1] * L
    prev = [-1] * L
    for i in range(L):
        ni = cands[i][1]
        best, bj = 0, -1
        for j in range(i - 1, max(-1, i - 80), -1):
            d = ni - cands[j][1]
            if d in (1, 2, 3) and dp[j] - (0.25 * (d - 1)) > best:
                best, bj = dp[j] - (0.25 * (d - 1)), j
        if bj >= 0:
            dp[i] = best + 1
            prev[i] = bj
        elif ni > 3:
            dp[i] = 0.5
    i = max(range(L), key=lambda k: (dp[k], k))
    chain = []
    while i >= 0:
        chain.append(cands[i])
        i = prev[i]
    chain.reverse()
    if len(chain) < 2 and chain and chain[0][1] != 1:
        return []
    return chain


def para_at(chain, pos):
    if not chain:
        return None
    lo = bisect.bisect_right([c[0] for c in chain], pos) - 1
    return chain[lo][1] if lo >= 0 else None


# ------------------------------------------------------------------ case numbers
_NUMGROUP = r"((?:\d{1,6}(?:\s*[-–]\s*\d{1,6})?\s*(?:,|and|&)\s*)*\d{1,6}(?:\s*[-–]\s*\d{1,6})?)"
_CASENO_RE = re.compile(_NUMGROUP + r"\s*(?:of|/|-)\s*((?:19|20)\d{2})\b", re.I)
_TYPE_BEFORE_RE = re.compile(r"([A-Za-z][A-Za-z.()&\s\-]{0,45}?)\s*(?:Nos?\s*\.?|Numbers?|D\.?\s*No\.?)?\s*[:.\-\u2013]?\s*$")


def _expand(group):
    nums = set()
    for part in re.split(r"\s*(?:,|and|&)\s*", group):
        part = part.strip()
        if not part:
            continue
        m = re.match(r"(\d+)\s*[-–]\s*(\d+)$", part)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            if 0 <= b - a <= 60:
                nums.update(range(a, b + 1))
            else:
                nums.update([a, b])
        elif part.isdigit():
            nums.add(int(part))
    return nums


def ptype(t):
    t = (t or "").lower()
    t = re.sub(r"[^a-z]", "", t)
    if not t:
        return ""
    for key, pat in [("ia", r"(^|[^a-z])?(ia|interlocutoryapplication)$"), ]:
        pass
    table = [
        ("misc", r"(cmappl|cmapp|crlmappl|crlma|^cm$|cmno|cmp|^ia$|interlocutory|application|appl|^ma$|miscellaneous|misc|exemption|stay|caveat)"),
        ("lower", r"(^oa$|originalapplication|^ta$|transferapplication|complaint|fir|suit$|^cs$|courtmartial|^gcm$|^scm$|^dcm$)"),
        ("tc", r"(transferredcase|^tc|transfercase)"),
        ("slp", r"(slp|specialleave)"),
        ("lpa", r"(lpa|letterspatent)"),
        ("crla", r"(criminalappeal|crla|crlapp|^cra$)"),
        ("ca", r"(civilappeal|^ca$|^cas$)"),
        ("wp", r"(writpetition|^wp|cwp|owp|^swp|writa|writc|^writ|wpc|wpcrl|wps|wpcrl|^wri[ac]$|crwp|crlwp|wpil)"),
        ("spla", r"(specialappeal|spla)"),
        ("rp", r"(review|^rp$|^rplpa$)"),
        ("cont", r"(contempt|cocp|conc|coc)"),
        ("rev", r"(revision|crr|crrev)"),
        ("appeal", r"(appeal|^rsa$|^fao$|^capl$|^laapp$|^macapp$|^crr$|^cr$)"),
        ("petition", r"(petition)"),
    ]
    for key, pat in table:
        if re.search(pat, t):
            return key
    return "other"


def find_case_numbers(s):
    """Return list of dicts {type, ptype, nums, year, label, pos}."""
    out = []
    for m in _CASENO_RE.finditer(s):
        pre = s[max(0, m.start() - 50):m.start()]
        tm = _TYPE_BEFORE_RE.search(pre)
        typ = tm.group(1).strip() if tm else ""
        typ = re.sub(r"^.*\b(?:in|of|and|with|the|from|by|vide|under|to)\s+", "", typ, flags=re.I).strip()
        km = list(_TYPE_KEY_RE.finditer(typ))
        if km:
            typ = typ[km[-1].start():].strip()
        elif typ.split():
            typ = typ.split()[-1]
        label = squash((typ + " " + s[m.start():m.end()]) if typ else s[m.start():m.end()])
        out.append({"type": typ, "ptype": ptype(typ), "nums": _expand(m.group(1)), "year": int(m.group(2)),
                    "label": label, "pos": m.start()})
    for m in re.finditer(r"\b([A-Z][A-Za-z.()]{1,20})[-/ ](\d{1,6})[-/]((?:19|20)\d{2})\b", s):
        if any(o["pos"] <= m.start() < o["pos"] + 30 for o in out):
            continue
        if re.sub(r"[^a-z]", "", m.group(1).lower()) in ("no", "nos", "number", "dated", "dt") or \
                any(o["year"] == int(m.group(3)) and int(m.group(2)) in o["nums"] and abs(o["pos"] - m.start()) < 30 for o in out):
            continue
        out.append({"type": m.group(1), "ptype": ptype(m.group(1)), "nums": {int(m.group(2))},
                    "year": int(m.group(3)), "label": m.group(0), "pos": m.start()})
    out.sort(key=lambda o: o["pos"])
    return out


def meta_case_numbers(s):
    out = []
    for part in (s or "").split(";"):
        part = part.strip()
        m = re.match(r"(.+?)/(\d+)/((?:19|20)\d{2})$", part)
        if m:
            out.append({"type": m.group(1), "ptype": ptype(m.group(1)), "nums": {int(m.group(2))},
                        "year": int(m.group(3)), "label": part, "pos": -1})
    return out



# ------------------------------------------------------------------ host proceedings (v3)
_CANON = [
    (r"^(?:civilappeals?|cas?|civilappealnos?|civilappealno)$", "CA"),
    (r"^(?:criminalappeals?|crlas?|crlapp|cras?|criminalappealnos?)$", "CRLA"),
    (r"^(?:criminalappeal|crla|crlapp)\((s|db|sj)\)$", "CRLA(%s)"),
    (r"^(?:writpetition|writpetitions|wp|wps)\((c|civil)\)$", "WP(C)"),
    (r"^(?:writpetition|writpetitions|wp|wps)\((crl|criminal)\)$", "WP(CRL)"),
    (r"^(?:writpetition|writpetitions|wp|wps)$", "WP"),
    (r"^wpc$", "WP(C)"),
    (r"^(?:specialleavepetitions?|slps?)\((c|civil)\)$", "SLP(C)"),
    (r"^(?:specialleavepetitions?|slps?)\((crl|criminal)\)$", "SLP(CRL)"),
    (r"^(?:specialleavepetitions?|slps?)$", "SLP"),
    (r"^(?:transferredcases?|tcs?)\((c|civil)\)$", "TC(C)"),
    (r"^(?:transferredcases?|tcs?)$", "TC"),
    (r"^(?:specialappeals?|splas?)$", "SPLA"),
    (r"^(?:specialappeal)\((d|defective)\)$", "SPLA(D)"),
    (r"^(?:regularsecondappeals?|rsas?)$", "RSA"),
    (r"^(?:sa)$", "SA"),
    (r"^(?:lettersppatentappeals?|letterspatentappeals?|lpas?)$", "LPA"),
    (r"^(?:reviewpetitions?|rps?|reviewapplications?)$", "RP"),
    (r"^(?:civilwritpetitions?|cwps?|cwpnos?)$", "CWP"),
    (r"^(?:criminalwritpetitions?|crwps?|crlwps?)$", "CRWP"),
    (r"^(?:servicewritpetitions?|swps?)$", "SWP"),
    (r"^(?:otherwritpetitions?|owps?)$", "OWP"),
    (r"^(?:writa|writ\-?a|wria)$", "WRIT-A"),
    (r"^(?:writc|writ\-?c|wric)$", "WRIT-C"),
    (r"^(?:mattersunderarticle(?:227)?)$", "MATTERS-U/A-227"),
    (r"^(?:contemptpetitions?|contemptpetition\(c\)|cocp|conc|coc|contemptcases?)$", "CONT"),
]


_TYPE_KEY_RE = re.compile(
    r"(?<![A-Za-z])(civil\s+appeal|criminal\s+appeal|crl\.?\s*a(?:ppeal)?\.?(?:\s*\((?:s|db|sj)\))?|writ\s+petitions?(?:\s*\((?:civil|c|criminal|crl)\))?|"
    r"special\s+leave\s+petitions?(?:\s*\((?:civil|c|criminal|crl)\))?|s\.?\s*l\.?\s*p\.?(?:\s*\((?:civil|c|criminal|crl)\))?|"
    r"transferred\s+cases?(?:\s*\((?:civil|c)\))?|t\.?\s*c\.?\s*\((?:civil|c)\)|special\s+appeal(?:\s*\((?:d|defective)\))?|"
    r"regular\s+second\s+appeal|letters?\s+patent\s+appeal|l\.?\s*p\.?\s*a\.?|review\s+(?:petition|application)|r\.?\s*p\.?|"
    r"civil\s+writ\s+petition|c\.?\s*w\.?\s*p\.?|cr\.?\s*w\.?\s*p\.?|criminal\s+writ\s+petition|s\.?\s*w\.?\s*p\.?|o\.?\s*w\.?\s*p\.?|"
    r"writ\s*-\s*[ac]\b|writ\s+[ac]\b|matters\s+under\s+article\s+227|contempt\s+(?:petition|case)s?(?:\s*\((?:civil|c)\))?|"
    r"w\.?\s*p\.?\s*\((?:c|civil|crl|criminal|s)\)|w\.\s*p\.|wp|c\.\s*a\.|r\.\s*s\.\s*a\.|rsa)(?![A-Za-z])", re.I)


def canon_type(raw):
    """Normalised proceeding type for a printed case-type string ('Civil Appeal' -> CA, 'W.P.(C)' -> WP(C)).
    The right-most recognised type phrase in the string wins (cause-title noise before it is ignored)."""
    raw = raw or ""
    ms = list(_TYPE_KEY_RE.finditer(raw))
    cand = [raw]
    if ms:
        cand = [ms[-1].group(0)] + cand
    for c0 in cand:
        t = c0.lower()
        t = re.sub(r"\b(?:nos?|numbers?|in|the|of|and|with|d)\b\.?", " ", t) if c0 is raw else t
        t = re.sub(r"[^a-z()]", "", t)
        t = t.replace("()", "")
        for pat, out in _CANON:
            m = re.match(pat, t)
            if m:
                return out % m.group(1).upper() if "%s" in out else out
    t2 = re.sub(r"[^A-Za-z()\-]", "", raw.split()[-1] if raw.split() else "").upper()
    return t2[:20] or "CASE"


def norm_label(c, n=None):
    """'TYPE NUM/YEAR' for one number of a case-number dict."""
    n = min(c["nums"]) if n is None else n
    return "%s %d/%d" % (canon_type(c.get("type", "")), n, c["year"])


_NOT_HOST_BEFORE_RE = re.compile(
    r"(?:arising\s+(?:out\s+)?(?:of|from)|@|\bagainst\b|impugned|passed\s+in|(?:order|judgment)\s+dated|decided\s+on|dated\s+\d|"
    r"\bin\s+(?:the\s+)?(?:O\.?\s?A|T\.?\s?A|R\.?\s?A|M\.?\s?A|Original\s+Application|Transferred\s+Application|"
    r"Writ\s+Petition|W\.?\s?P|C\.?\s?W\.?\s?P|Civil\s+Writ|LPA|S\.?\s?W\.?\s?P|O\.?\s?W\.?\s?P|Crl|Criminal|Civil|case\s+of)|"
    r"High\s+Court\s+(?:of\s+[A-Za-z&\s]{3,40}\s+)?in|Tribunal\s+(?:[A-Za-z,\s]{0,40}\s+)?in|\bin\s+(?:CWP|SWP|OWP|WP|LPA)\b|"
    r"\bwith\s+reference\s+to|\bcited\b|\breported\s+in|(?:passed|rendered|delivered)\s+by\b|"
    r"(?-i:\bin)\s+(?:the\s+)?(?:Writ|Special\s+Appeal|Spl|First\s+Appeal|Second\s+Appeal|Review|Contempt|Transfer|Misc|"
    r"Matters|Application|Petition|Case|SLP|S\.?\s?L\.?\s?P|C\.?\s?A\b|Civil\s+Appeal|Criminal\s+Appeal))(?:(?!\bWITH\b|\bWith\b|\n[ \t]*with[ \t]*\n|\n[ \t]*\n)[^;]){0,70}$", re.I)
_FROM_MARK_RE = re.compile(r"\bFrom\s+the\b|\bArising\s+(?:out\s+)?(?:of|from)\b|\bAgainst\s+the\b|\b(?:Judgment|Order)\s+(?:and|&)\s+"
                           r"(?:Order|Judgment)\b|\bdated\b", re.I)
_WITH_MARK_RE = re.compile(r"\bWITH\b|\bWith\b|\n[ \t]*with[ \t]*\n|\n[ \t]*and\s+(?=Civil|Criminal|C\.A|Writ|SLP|Special|Transferred)|\bAND\b|\bAlong\s+with\b|\(\s*(?=(?:Civil|Criminal|Writ|Special|Transferred))")


def _after_from_marker(zt, pos):
    """True when the number follows a 'From the judgment ...'/'arising out of' marker with no 'WITH' in between
    (S.C.R. jurisdiction lines: 'Civil Appeal No. 1 of 1997. From the ... High Court in C.W.P. No. 2 of 1993. WITH ...')."""
    pre = zt[max(0, pos - 400):pos]
    fm = list(_FROM_MARK_RE.finditer(pre))
    if not fm:
        return False
    wm = [m for m in _WITH_MARK_RE.finditer(pre) if m.start() > fm[-1].start()]
    return not wm


_PARA1_RE = re.compile(r"(?m)^[ \t]*1[ \t]*\.[ \t]*(?:\n[ \t]*)?[A-Z][a-z]+\s")


def _host_numbers(mt, js, case_numbers_meta, scr, page2=None):
    """Host proceedings: crawler metadata case numbers plus main-proceeding numbers printed in the cause title.
    Numbers introduced as the source of the appeal ('arising out of', 'against', 'impugned', 'in O.A.') are not
    hosts; a bare number list after a typed number inherits its type ('WP(C) Nos. 233, ... of 2024 and 540 of 2025')."""
    hosts = meta_case_numbers(case_numbers_meta)
    for h in hosts:
        h["src"] = "meta"
    if scr:
        zone_end = 2500
        mh = _SCR_CASE_HEAD_RE.search(mt, 0, 9000)
        mj = re.search(r"(?:CIVIL|CRIMINAL|ORIGINAL)\s+[A-Z ]{0,16}JURISDICTION", mt[:min(len(mt), 80000)])
        extra = []
        if mh:
            extra.append((mh.start(), min(len(mt), mh.end() + 50)))
        if mj:
            je = min(len(mt), mj.start() + 700)
            mstop = re.search(r"for\s+the\s+(?:Appellant|Petitioner|Respondent)|The\s+Judgment\s+of\s+the\s+Court|delivered\s+by|"
                              r"(?m:^[ \t]*1\s*\.\s)", mt[mj.start():je])
            extra.append((mj.start(), mj.start() + mstop.start() if mstop else je))
        zones = [(0, zone_end)] + extra
    else:
        zone_end = js if 150 <= js <= 6000 else max(min(js, 6000), 1500)
        if 6000 < js <= 60000 and len(_CAUSE_TITLE_RE.findall(mt, 0, js)) >= 4 and \
                sum(1 for c in find_case_numbers(mt[:js]) if c["ptype"] not in ("misc", "lower", "", "other")) >= 4:
            zone_end = js   # long cause title of a batch (every connected matter listed before the judgment starts)
            mp = _PARA1_RE.search(mt, 200, js)
            if mp:
                zone_end = max(1500, mp.start())   # ... but never past the first paragraph of the judgment
        elif js < 150 and page2 is not None and 200 < page2 < zone_end:
            zone_end = page2
        zones = [(0, zone_end)]
    prev = None
    for z0, z1 in zones:
        zt = mt[z0:z1]
        for c in find_case_numbers(zt):
            pre = zt[max(0, c["pos"] - 90):c["pos"]]
            pt = c["ptype"]
            if pt in ("", "other") and prev is not None and re.match(r"^[\s,&]*(?:and|&|,)?[\s,&]*$", zt[prev[1]:c["pos"]] or " ") \
                    and c["pos"] - prev[1] <= 12:
                c["type"], c["ptype"] = prev[0]["type"], prev[0]["ptype"]
                pt = c["ptype"]
            prev = (c, c["pos"] + _case_span_len(zt, c["pos"]))
            if pt in ("misc", "lower", "", "other"):
                continue
            if _NOT_HOST_BEFORE_RE.search(pre) or _after_from_marker(zt, c["pos"]):
                continue
            c["src"] = "cause_title"
            hosts.append(c)
    # one host per (number, year)
    out, seen = [], set()
    for h in hosts:
        for n in sorted(h["nums"]):
            k = (n, h["year"])
            if k in seen:
                continue
            seen.add(k)
            hh = dict(h)
            hh["nums"] = {n}
            hh["label_norm"] = norm_label(h, n)
            out.append(hh)
    return out


def _match_host(c, hosts):
    for h in hosts:
        if h["year"] == c["year"] and (h["nums"] & c["nums"]):
            return h
    return None


def _case_span_len(s, pos):
    m = _CASENO_RE.match(s, pos)
    return (m.end() - pos) if m else 0


_PAREN_LONG_RE = re.compile(r"\([^()]{13,}\)")
_PARTY_RE = re.compile(r"(?:filed|preferred|instituted|moved)\s+(?:on\s+behalf\s+of|by)\s+(?:the\s+)?(.{3,60}?)(?=\s+(?:are|is|stand|stands|be|"
                       r"have|has|respectively|shall)\b|,|$)|\bof\s+the\s+(appellants?|respondents?|petitioners?|accused|Union\s+of\s+India|"
                       r"State|officer|applicant)s?\b", re.I)


def _heading_scope(mt, seg_start, pos):
    """Most recent short case-number heading line before pos (Delhi-style 'CM APPL. 123/2023 (exemption)')."""
    window = mt[max(seg_start, pos - 4000):pos]
    last = None
    for m in re.finditer(r"(?m)^[ \t]*([A-Z][A-Za-z.()\s&]{1,30}?\s*(?:Nos?\.?\s*)?\d{1,6}\s*(?:/|of)\s*(?:19|20)\d{2}[^\n]{0,60})$", window):
        line = m.group(1)
        if len(line) <= 110:
            last = line
    if not last:
        return None
    cs = find_case_numbers(last)
    return cs[0] if cs else None


_BLOCK_HEAD_RE = re.compile(r"(?m)^[ \t]*((?:[A-Z][A-Za-z.()&\s]{1,40}?)\s*(?:Nos?\.?\s*)?\d{1,6}(?:\s*[-/]\s*\d{1,6})?\s*(?:/|of|-)\s*(?:19|20)\d{2}[^\n]{0,50})[ \t]*\n(?=\s*1\s*\.\s)")


def block_headings(mt, s0, s1):
    """Case-number heading lines immediately followed by paragraph '1.' (a common order with separately
    numbered blocks per proceeding). Returns [(pos, case_number_dict)]."""
    out = []
    for m in _BLOCK_HEAD_RE.finditer(mt, s0, s1):
        cs = find_case_numbers(m.group(1))
        if cs and len(m.group(1)) <= 110:
            out.append((m.start(), cs[0]))
    return out



_SECTION_HEAD_RE = re.compile(
    r"(?m)^[ \t]*(?:\(?\d{1,3}[ \t]*[.)][ \t]*)?((?:[A-Z][A-Za-z.()&/ \t-]{0,40}?)[ \t]*(?:Nos?\.?[ \t]*)?\d{1,6}[ \t]*(?:/|[Oo][Ff]|-)[ \t]*(?:19|20)\d{2})"
    r"[ \t]*(?:\([^)\n]{0,40}\))?[ \t]*(?:(?:&|and|with)\b[^\n]{0,90})?[ \t]*[:.\-]?[ \t]*$")


def find_sections(d, js, s1, hosts):
    """Per-proceeding sections of a batch judgment: heading lines that consist of a HOST case number (optionally
    numbered '25.'), after the judgment start. Returns [(start, end, host, unsafe_reason)] or [].
    A jump in the printed serial numbers ('25.' then '27.') marks the section before the jump unsafe, because a
    heading may have been missed and its disposition would be attributed to the wrong proceeding."""
    mt = d.mt
    if len(hosts) < 2:
        return []
    found = {}
    for m in _SECTION_HEAD_RE.finditer(mt, js, s1):
        cs = find_case_numbers(m.group(1))
        if not cs or cs[0]["ptype"] in ("misc", "lower", "", "other"):
            continue
        h = _match_host(cs[0], hosts)
        if h is None or h["label_norm"] in found:
            continue
        ms = re.match(r"[ \t]*\(?(\d{1,3})[ \t]*[.)]", mt[m.start():m.end()])
        found[h["label_norm"]] = (m.start(), h, int(ms.group(1)) if ms else None)
    heads = sorted(found.values(), key=lambda x: x[0])
    missing = [h for h in hosts if h["label_norm"] not in found]
    if heads and len(missing) == 1 and len(re.sub(r"\s", "", mt[js:heads[0][0]])) >= 800:
        # lead case discussed first without a heading, connected case(s) under their own headings
        heads = [(js, missing[0], None)] + heads
    if len(heads) < 2:
        return []
    serials = [x[2] for x in heads]
    use_serial = sum(1 for x in serials if x is not None) >= 0.8 * len(serials)
    secs = []
    for i, (a, h, sn) in enumerate(heads):
        e = heads[i + 1][0] if i + 1 < len(heads) else s1
        unsafe = ""
        if use_serial and i + 1 < len(heads):
            nx = heads[i + 1][2]
            if sn is None or nx is None or nx != sn + 1:
                unsafe = "SECTION_SERIAL_GAP_POSSIBLE_UNDETECTED_PROCEEDING"
        secs.append((a, e, h, unsafe))
    big = [x for x in secs if len(re.sub(r"\s", "", mt[x[0]:x[1]])) >= 800]
    if not big or len(big) < 0.5 * len(secs):
        return []
    return secs



def _subject_ptypes(subj):
    s = subj.lower()
    out = set()
    if re.search(r"\bappeals?\b|\bc\.?a\.?\b|\bcrl\.?\s?a", s):
        out.add("appeal")
    if re.search(r"\bpetitions?\b|\bwrits?\b|\bw\.?p\b|\bcwp|\bswp|\bowp|\bslp", s):
        out.add("petition")
    if re.search(r"\btransferred\s+cases?\b|\bt\.?c\.?\b", s):
        out.add("tc")
    if re.search(r"\breview\b", s):
        out.add("rp")
    return out



_PT_FAMILY = {"ca": "appeal", "crla": "appeal", "lpa": "appeal", "spla": "appeal", "appeal": "appeal", "wp": "petition",
              "slp": "petition", "petition": "petition", "cont": "petition", "rev": "petition", "tc": "tc", "rp": "rp"}


def _host_family(h):
    return _PT_FAMILY.get(h.get("ptype", ""), "other")
