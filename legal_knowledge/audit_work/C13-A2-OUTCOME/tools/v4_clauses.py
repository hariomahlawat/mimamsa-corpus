"""Mimamsa C13 judicial outcome extractor V4: disposition clause parsing (verb form, tense, subject class) (ported from V3; V4 changes marked V4).

All values are AUTOMATED CANDIDATES read from a PDF text layer; nothing is legally verified."""
import bisect
import re

from v4_text import (  # noqa: F401
    sentences)
from v4_proceedings import (  # noqa: F401
    find_case_numbers)


# ------------------------------------------------------------------ disposition clause parsing
_AUX = {"is", "are", "stands", "stand", "stood", "already", "kindly", "be", "been", "being", "was", "were", "shall", "hereby", "accordingly", "also",
        "consequently", "therefore", "thus", "resultantly", "herewith", "thereby", "hence", "hereunder", "has", "have",
        "had", "will", "would", "should", "must", "may", "might", "can", "cannot", "could", "not", "to", "deserves",
        "deserve", "liable", "ought", "partly", "partially", "liberty", "also", "summarily", "finally", "consequentially",
        "as", "such", "herein", "in", "limine", "rightly", "wholly", "entirely", "fully"}
_PAST = {"was", "were", "been", "being", "had", "has", "have", "stood"}
_MODAL_WEAK = {"deserves", "deserve", "liable", "ought", "must", "should", "to"}
_MODAL_COND = {"would", "may", "might", "can", "cannot", "could", "not", "will"}

_PASSIVE_VERB_RE = re.compile(
    r"\b(partly\s+allowed|partially\s+allowed|allowed\s+in\s+part|allowed\s+partly|partly\s+accepted|"
    r"accepted\s+in\s+part|allowed|accepted|dismissed|rejected|disposed\s+of+|disposed\s+off|disposed|withdrawn|"
    r"remanded|remitted|transferred|set\s*-?\s*aside|quashed|closed|discharged|made\s+absolute|"
    r"consigned(?=\s+to\s+(?:the\s+)?records?)|transmitted(?=\s+to\s+the\s+(?:Armed|AFT|Tribunal)))\b", re.I)
_ACTIVE_RE = re.compile(
    r"\b(?:we|this\s+court|the\s+court)\b[\s,\-]*(?:(?:accordingly|therefore|hence|hereby|thus|consequently|would|"
    r",|also|partly|partially|,)\s*)*\b(allow|dismiss|dispose\s+of|dispose\s+off|remand|remit|accept|reject|"
    r"set\s+aside|quash|transfer)\b", re.I)
_COORD_ACTIVE_RE = re.compile(
    r"\band\s+(?:as\s+a\s+consequence\s+|consequently\s+|accordingly\s+|hence\s+|therefore\s+|thus\s+)?"
    r"(dismiss|allow|dispose\s+of|remand|remit)\s+(?=(?:the|this|these|both|all|it|present|instant)\b)", re.I)
_DEEM_RE = re.compile(r"\b(?:deems?|consider|considers|find|finds|think|thinks)\s+it\s+(?:fit|proper|appropriate|expedient|just)\s+"
                      r"(?:and\s+(?:proper|appropriate)\s+)?to\s+(transfer|remit|remand|allow|dismiss|dispose\s+of|quash|set\s+aside)\b", re.I)
_PARTY_STMT_RE = re.compile(r"\b(?:counsel|Counsel|Advocate|advocate|A\.?S\.?G\.?I?|C\.?G\.?S\.?C|petitioners?|appellants?|respondents?|"
                            r"applicants?)\b[^.;]{0,250}?\b(?:submits?|submitted|states?|stated|prays?|prayed|requests?|requested|"
                            r"contends?|contended|urges?|urged|seeks?|sought|agrees?|agreed|concedes?|conceded|fairly\s+states)\b")
_ADOPT_RE = re.compile(r"^\W*(?:\d+\s*\.\s*)?(?:ordered\s+accordingly|order\s+accordingly|prayer\s+(?:is\s+)?(?:accepted|allowed|granted)|"
                       r"request\s+(?:is\s+)?(?:accepted|acceded\s+to|allowed)|(?:dismissed|disposed\s+of|allowed)\s+as\s+prayed(?:\s+for)?)\b", re.I)
_INTRANS_RE = re.compile(r"\b(succeeds?|fails?)\b", re.I)

_CLAUSE_BOUND_RE = re.compile(r";|:|\b[Ww]hereas\b|\b[Ww]hile\b|,\s*and\b|\band\s+the\b|\band\s+that\b|"
                              r"\band\s+(?=(?:[A-Z][A-Za-z.()]*\s+){0,3}Nos?\b)|\band\s+(?=(?:these|this|all|both|such|its|his|her|their)\b)|"
                              r"\band\s+that\b|\b[Bb]ut\b|\b[Hh]owever\b|"
                              r"\bwith\s+the\s+result\s+that\b")
_COND_RE = re.compile(r"\b(if|in\s+case|failing\s+which|in\s+the\s+event|otherwise|unless|whether|lest|till|until|"
                      r"would\s+be|shall\s+be\s+deemed)\b", re.I)

# subject noun classes, scanned left to right; the first match decides
_NOUN_RES = [
    ("misc", re.compile(r"\b(applications?|appl\.?|i\.\s?a\.?(?=\s*(?:no|\d))|ia(?=\s*(?:no|\d))|c\.?\s?m\.?(?=\s*(?:appl|no|\d|\(|$))|"
                        r"crl\.?\s?m\.?\s?a\.?|m\.\s?a\.(?=\s*(?:no|\d))|ma(?=\s*(?:no\.?|\d))|miscellaneous|misc\.?|interlocutory|exemption|stay|"
                        r"condonation|delay|impleadment|caveat|interim|vacate|amendment|prayers?|requests?|costs?|"
                        r"objections?|contentions?|submissions?|pleas?|claims?|grounds?|issues?|questions?)\b", re.I)),
    ("lower_proc", re.compile(r"\b(o\.\s?a\.?|oa|original\s+applications?|t\.\s?a\.?|ta(?=\s*no)|complaints?|f\.?i\.?r\.?|"
                              r"suits?|court[\s-]+martial|g\.?c\.?m\.?|s\.?c\.?m\.?|d\.?c\.?m\.?|trial|inquiry|enquiry)\b", re.I)),
    ("lower_decision", re.compile(r"\b(impugned|orders?|judgments?|awards?|sentences?|convictions?|findings?|punishments?|"
                                  r"decisions?|proceedings|penalty|penalties|charge[-\s]?sheets?|notices?|communications?|"
                                  r"verdicts?|show\s+cause)\b", re.I)),
    ("main", re.compile(r"\b(appeals?|petitions?|writs?|w\.?\s?p\.?(?=\s*[\(\s\d]|\s*no)|c\.?w\.?p\.?|l\.?p\.?a\.?|s\.?l\.?p\.?|"
                        r"c\.?a\.?(?=\s*nos?\.?\s*\d)|crl\.?\s?a\.?|t\.?c\.?(?=\s*\()|transferred\s+cases?|revisions?|references?|"
                        r"cases?|matters?|contempt\s+(?:petitions?|cases?|appeals?)|reviews?|rule|lis|cwp|owp|lpa|slp|spla)\b", re.I)),
    ("pronoun", re.compile(r"^\s*(?:\(?[ivx]+\)|\(?[a-z]\)|\d+\.)?\s*(it|they|(?:the\s+)?same|both|all|all\s+of\s+them|these|"
                           r"this|which|(?:the\s+)?said)\s*$", re.I)),
]


_ALONG_WITH_RE = re.compile(r"[,\s]*\b(?:along\s*with|together\s+with|as\s+also|with)\s+(?:all\s+)?(?:the\s+)?(?:pending|connected|"
                            r"interim|miscellaneous|accompanying)?\s*(?:applications?|application\(s\)|C\.?M\.?s?|C\.?M\.?\s*APPL\S*|I\.?A\.?s?|"
                            r"misc\.?\s+applications?)\b[^,;]*,?", re.I)


def classify_subject(subj):
    s = _ALONG_WITH_RE.sub(" ", subj).strip()   # v3: 'The said writ petitions, along with all pending applications
    if "," in s:
        # v3: the comma-separated chunk nearest to the verb that names something decides
        # ('In view of our order ... No.242 of 2012, this appeal, filed by the appellant, also fails')
        for chunk in reversed(s.split(",")):
            r = _classify_subject(chunk)
            if r[0] not in ("unknown", "elided"):
                return r
    return _classify_subject(s)


def _classify_subject(subj):
    s = subj.strip()
    s2 = re.sub(r"^\s*(?:\(?[ivxlc]+\)|\(?[a-z]\)|[A-Z]\.|\d+\s*\.)\s*", "", s)
    if not re.search(r"[A-Za-z]{2,}", s2):
        return "elided", None
    best = None
    for cls, rx in _NOUN_RES:
        m = rx.search(s2)
        if m and (best is None or m.start() < best[1]):
            best = (cls, m.start())
    if best is None:
        return "unknown", None
    return best


_EXTENT_AFTER_RE = re.compile(r"\s*(?:\S+\s+){0,4}?(?:only\s+)?(?:to|in)\s+(?:the|that|this|such|a)?\s*(?:[a-z]+\s+){0,2}extent\b", re.I)
_EXTENT_BEFORE_RE = re.compile(r"\b(?:to|in)\s+(?:the|that|this|such)\s+(?:[a-z]+\s+){0,2}extent\b|\binsofar\s+as\b|\bin\s+so\s+far\s+as\b", re.I)


def verb_class(v, ctx_after):
    v = re.sub(r"\s+", " ", v.lower())
    after = ctx_after.lower()
    if v in ("withdrawn",) or re.match(r"\s*(?:as\s+)?(?:having\s+been\s+)?(?:withdrawn|not\s+pressed)", after) and \
            v in ("dismissed", "disposed of", "disposed", "closed", "dismiss", "dispose of"):
        return "dismissed_as_withdrawn"
    if v in ("allowed", "accepted") and re.match(r"\s*to\s+(be\s+)?withdraw", after):
        return "dismissed_as_withdrawn"
    if re.match(r"\s*(?:as\s+|being\s+)?(?:having\s+(?:been\s+)?(?:become|rendered)\s+|rendered\s+|become\s+)?infructuous", after) and \
            v in ("dismissed", "disposed of", "disposed", "closed", "dismiss", "dispose of"):
        return "dismissed_as_infructuous"
    if v in ("partly allowed", "partially allowed", "allowed in part", "allowed partly", "partly accepted",
             "accepted in part"):
        return "partly_allowed"
    if v in ("allowed", "accepted", "allow", "accept", "made absolute", "succeeds", "succeed"):
        if re.match(r"\s*(?:only\s+)?(?:partly|partially|in\s+part|to\s+(?:a\s+)?limited\s+extent)", after):
            return "partly_allowed"
        if _EXTENT_AFTER_RE.match(after):
            return "partly_allowed_extent"   # v3: 'allowed to the (above|aforesaid|limited) extent', 'to that extent'
        if re.match(r"\s*to\s+(?!the\s+extent|a\s+limited)", after):
            return None   # 'allowed to join/continue' etc.
        return "allowed"
    if v in ("dismissed", "rejected", "dismiss", "reject", "fails", "fail", "discharged"):
        if re.match(r"\s*(?:\w+\s+){0,2}?(?:except|save|but\s+only)\s+(?:to\s+the\s+extent|as\s+(?:indicated|mentioned|stated))", after):
            return "extent_qualified"
        return "dismissed"
    if v in ("disposed of", "disposed off", "disposed", "dispose of", "dispose off", "closed", "consigned"):
        if re.match(r"\s*(?:of\s+)?as\s+allowed\b", after):
            return "allowed"
        if re.match(r"\s*(?:of\s+)?as\s+dismissed\b", after):
            return "dismissed"
        return "disposed_of_with_directions"
    if v in ("remanded", "remitted", "remand", "remit"):
        return "remanded"
    if v in ("transferred", "transfer", "transmitted"):
        if re.match(r"\s*(?:back\s+)?to\b", after) or True:
            return "transferred"
    if v in ("set aside", "set-aside", "setaside", "set - aside", "quashed", "quash"):
        return "set_aside"
    return None


def _aux_chain(text, vstart, cstart):
    """Words immediately before the verb that belong to the auxiliary chain."""
    seg = text[cstart:vstart]
    words = re.findall(r"[A-Za-z]+|,", seg)
    chain = []
    for w in reversed(words):
        lw = w.lower()
        if lw == "," or lw in _AUX:
            chain.append(lw)
        else:
            break
    chain.reverse()
    k = len(seg)
    # position where the chain begins (to cut the subject)
    for w in reversed(words[len(words) - len(chain):] if chain else []):
        k = seg.rfind(w, 0, k)
    return [c for c in chain if c != ","], cstart + (k if chain else len(seg))


_ELLIPTICAL_SENT_RE = re.compile(r"^[\s\d.()ivx]*(?:accordingly,?\s+|consequently,?\s+|hence,?\s+)?(?:all\s+|both\s+)?(?:the\s+)?"
                                 r"(?:(?:writ|civil|criminal|special|letters\s+patent|transferred)\s+)?(?:leave\s+)?"
                                 r"(?:petitions?|appeals?|cases?|matters?)\s*$", re.I)


def parse_dispositions(text, s, e):
    """Disposition clauses in sentence text[s:e]. Returns list of dicts."""
    sent = text[s:e]
    out = []
    bounds = [0] + [m.end() for m in _CLAUSE_BOUND_RE.finditer(sent)]

    def clause_start(rel):
        i = bisect.bisect_right(bounds, rel) - 1
        return bounds[max(i, 0)]

    def clause_end(rel):
        i = bisect.bisect_right(bounds, rel)
        nb = [b for b in bounds if b > rel]
        return (nb[0] if nb else len(sent))

    found_spans = []
    # passive / standalone
    for m in _PASSIVE_VERB_RE.finditer(sent):
        v = m.group(1)
        if re.match(r"\s*(?:\([A-Za-z.]+\)\s*)?(?:cases?|petitions?|applications?)\b", sent[m.end():m.end() + 30], re.I):
            continue
        if v.lower() == "withdrawn" and re.search(r"(?:dismissed|disposed\s+of+|closed|rejected)\s+as\s+(?:having\s+been\s+)?$",
                                                  sent[max(0, m.start() - 40):m.start()], re.I):
            continue   # second half of 'dismissed as withdrawn' (already parsed with its verb)
        cs = clause_start(m.start())
        # v3: 'The present petition and all pending applications are disposed of' is one coordinated subject
        if cs > 0 and re.match(r"\s*(?:all\s+)?(?:the\s+)?(?:pending|connected|interim|miscellaneous|accompanying)\s+(?:civil\s+)?"
                               r"(?:misc\w*\s+)?applications?|\s*(?:all\s+)?(?:the\s+)?applications?\b", sent[cs:m.start()], re.I) and \
                re.search(r"\band\s*$", sent[:cs]):
            cs = clause_start(max(0, cs - 5))
        chain, subj_end = _aux_chain(sent, m.start(), cs)
        subj = sent[cs:subj_end - 0] if chain else sent[cs:m.start()]
        after = sent[m.end():m.end() + 60]
        cls = verb_class(v, after)
        if cls is None:
            continue
        stripped_sent = re.sub(r"^[\s\d.()ivx]*", "", sent).strip()
        standalone = stripped_sent.lower().startswith(re.sub(r"\s+", " ", v.lower())[:6]) and \
            not re.search(r"[A-Za-z]{2,}", re.sub(r"^[\s\d.()ivx]*", "", sent[:m.start()]))
        if not chain and not standalone and _ELLIPTICAL_SENT_RE.match(sent[:m.start()]) and len(sent.strip()) <= 90:
            chain = ["(elliptical)"]   # V4: 'All the petitions dismissed.' / 'Appeal dismissed.' (no auxiliary)
        if not chain and not standalone:
            # elliptical coordination 'X is quashed and OA No. 1/2020 dismissed' -> only with a case number
            if not find_case_numbers(subj):
                continue
            chain = ["(ellipsis)"]
        tense = "present"
        if chain[-2:] in (["will", "stand"], ["will", "be"]) and not ({"not", "would", "may", "can", "cannot"} & set(chain)):
            chain = ["shall"] + chain[-1:]   # v3: operative 'will stand dismissed' / 'will be disposed of'
        if any(c in _PAST for c in chain):
            tense = "past"
        elif any(c in _MODAL_COND for c in chain):
            tense = "conditional"
        elif any(c in _MODAL_WEAK for c in chain) and not ("shall" in chain):
            tense = "weak"
        elif chain and chain[0] == "be" and "shall" not in chain:
            tense = "weak"   # subjunctive 'that the petition be transferred'
        pre_sent = sent[:m.start()]
        if _PARTY_STMT_RE.search(pre_sent):
            tense = "party_statement"
        if cls == "allowed" and _EXTENT_BEFORE_RE.search(pre_sent[-160:]):
            cls = "partly_allowed_extent"   # 'To the aforesaid extent, the petition is allowed'
        if cls == "allowed" and re.search(r"\b(?:partly|partially)\s*$", pre_sent):
            cls = "partly_allowed"
        out.append({"verb": v, "cls": cls, "subject": subj, "tense": tense, "rel": m.start(),
                    "standalone": standalone, "form": "passive", "clause": sent[cs:clause_end(m.end())]})
        found_spans.append((m.start(), m.end()))
    for m in _ACTIVE_RE.finditer(sent):
        v = m.group(1)
        obj_end = clause_end(m.end())
        obj = sent[m.end():min(obj_end, m.end() + 160)]
        obj = re.split(r",|;|\band\s+(?=[a-z]+\s+(?:the|this|that|his|her|its|their)\b)", obj)[0]   # v3: object of THIS verb only
        cls = verb_class(v, obj)
        if v.lower() in ("allow", "accept") and re.match(r"\s*(?:the\s+)?(?:learned\s+)?(?:petitioners?|appellants?|applicants?|"
                                                       r"respondents?|him|her|them|counsel|parties)\b", obj, re.I):
            cls = "dismissed_as_withdrawn" if re.search(r"\bwithdraw", obj, re.I) else None
        if cls is None:
            continue
        pre = sent[clause_start(m.start()):m.start()]
        tense = "present"
        between = sent[m.start():m.start(1)].lower()
        if cls == "allowed" and re.search(r"partly|partially", between):
            cls = "partly_allowed"
        if cls == "allowed" and (_EXTENT_AFTER_RE.match(obj) or re.search(r"\bto\s+(?:the|that)\s+(?:[a-z]+\s+){0,2}extent\b|"
                                                                           r"\bin\s+part\b", obj, re.I)):
            cls = "partly_allowed_extent"
        if _PARTY_STMT_RE.search(sent[:m.start()]):
            tense = "party_statement"
        if re.search(r"\bwould\b", between) or _COND_RE.search(pre):
            tense = "conditional"
        out.append({"verb": v, "cls": cls, "subject": obj, "tense": tense, "rel": m.start(1), "standalone": False,
                    "form": "active", "clause": sent[clause_start(m.start()):obj_end]})
    for m in _COORD_ACTIVE_RE.finditer(sent):
        # v3: 'we uphold the judgment ... and as a consequence dismiss this petition'
        if any(abs(x["rel"] - m.start(1)) < 3 for x in out):
            continue
        we = list(re.finditer(r"\b(?:we|this\s+court)\b", sent[:m.start()], re.I))
        if we:
            between = sent[we[-1].end():m.start()]
        else:
            # the sentence may have been split after an abbreviation ('the GP. Secretary'): look back 300 chars,
            # ignoring periods after short capitalised tokens
            back = re.sub(r"\b([A-Z][A-Za-z]{0,3})\.", r"\1 ", text[max(0, s - 300):s] + sent[:m.start()])
            mw = list(re.finditer(r"\b(?:we|this\s+court)\b[^.;:?!]*$", back, re.I))
            if not mw:
                continue
            between = back[mw[-1].start() + 2:]
        if re.search(r"[;:]|\bthat\b|\bwhich\b|\bwho\b", between):
            continue
        v = m.group(1)
        obj_end = clause_end(m.end())
        obj = sent[m.end():min(obj_end, m.end() + 160)]
        obj = re.split(r",|;|\band\s+(?=[a-z]+\s+(?:the|this|that|his|her|its|their)\b)", obj)[0]
        cls = verb_class(v, obj)
        if cls is None:
            continue
        tense = "present"
        if re.search(r"\b(?:would|may|might|could|cannot|can|not|to|shall\s+not)\b", between, re.I) or \
                _COND_RE.search(sent[:m.start()]):
            tense = "conditional"
        if _PARTY_STMT_RE.search(sent[:m.start()]):
            tense = "party_statement"
        out.append({"verb": v, "cls": cls, "subject": obj, "tense": tense, "rel": m.start(1), "standalone": False,
                    "form": "coordinated_active", "clause": sent[m.start():obj_end]})
    for m in _DEEM_RE.finditer(sent):
        v = m.group(1)
        obj_end = clause_end(m.end())
        obj = sent[m.end():min(obj_end, m.end() + 160)]
        cls = verb_class(v, obj)
        if cls is None:
            continue
        out.append({"verb": v, "cls": cls, "subject": obj, "tense": "present", "rel": m.start(1), "standalone": False,
                    "form": "deem_proper", "clause": sent[clause_start(m.start()):obj_end]})
    for m in _INTRANS_RE.finditer(sent):
        cs = clause_start(m.start())
        subj = sent[cs:m.start()]
        c, _ = classify_subject(subj)
        if c not in ("main", "misc", "lower_proc", "pronoun"):
            continue
        pre_words = re.findall(r"[A-Za-z]+", subj.lower())[-3:]
        tense = "present"
        if any(w in ("would", "must", "may", "cannot", "will", "not", "to") for w in pre_words):
            tense = "conditional"
        cls = "allowed" if m.group(1).lower().startswith("succeed") else "dismissed"
        if cls == "allowed" and (re.search(r"\b(?:partly|partially)\s*$", subj, re.I) or
                                 re.match(r"\s*(?:only\s+)?(?:partly|partially|in\s+part)\b", sent[m.end():m.end() + 30], re.I)):
            cls = "partly_allowed"   # v3: 'the appeal partly succeeds'
        elif cls == "allowed" and _EXTENT_AFTER_RE.match(sent[m.end():m.end() + 60]):
            cls = "partly_allowed_extent"
        out.append({"verb": m.group(1), "cls": cls, "subject": subj, "tense": tense, "rel": m.start(),
                    "standalone": False, "form": "intransitive", "clause": sent[cs:clause_end(m.end())]})
    # v3: a closing quotation mark with no opening mark before it in the sentence quotes only what precedes it;
    # the court's own words after the closing mark are not quoted
    mq = re.search(r"^[^\u201c]*?\u201d", sent)
    close_rel = mq.end() if mq else -1
    ends_in_quote = bool(re.match(r"\s*[\u201d\"]", text[e:e + 3]))
    for d in out:
        d["pos"] = s + d["rel"]
        pre = re.sub(r"\bif\s+any\b|\bif\s+not\s+already\b", " ", text[s + clause_start(d["rel"]):d["pos"]], flags=re.I)
        d["conditional_context"] = bool(_COND_RE.search(pre))
        d["closes_quote"] = ends_in_quote or (close_rel >= 0 and d["rel"] < close_rel)
        d["sentence"] = (s, e)
    out.sort(key=lambda d: d["rel"])
    return out



_WITHDRAW_CTX_RE = re.compile(r"\b(?:seeks?|sought|prays?|prayed|requests?|requested|permission|leave)\s+(?:of\s+this\s+(?:Court|Bench)\s+)?"
                              r"(?:for\s+)?(?:permission\s+|leave\s+)?(?:to\s+)?withdraw|\bwithdraw(?:s|n)?\s+the\s+(?:present\s+|instant\s+)?"
                              r"(?:writ\s+)?(?:petition|appeal)\b|\bnot\s+press(?:ing)?\s+the\s+(?:petition|appeal)", re.I)



_REF_BEFORE_NUM_RE = re.compile(r"(?:\b(?:order|judgment|judgement|decision|view)\b[^,;]{0,60}\b(?:in|of)\s+(?:the\s+)?"
                                r"(?:[.]?[A-Z][A-Za-z.()]*\s*){0,4}(?:Nos?\.?\s*)?$)|\b(?:as\s+in|similar\s+to|like|following)\s+[^,;]{0,40}$", re.I)
