"""Mimamsa C13 judicial outcome extractor V4: relief analysis of the operative part (new in V4).

Three readings that V3 did by phrase alone are made here from the operative directions as a whole, in the court's own
voice (outside quotations and party statements):

  extent_resolution   C11 F05. An allowance qualified by an extent phrase is partly_allowed only when the operative
                      part limits the relief. A *referential* phrase ('allowed to the extent and in terms herein
                      above', 'to the aforesaid extent') points back to the directions; if those directions quash
                      every impugned decision and nothing is refused, the allowance is complete. Otherwise abstain.
  transfer_direction  The court sends the proceeding itself to another forum (record or paper book transmitted to the
                      Armed Forces Tribunal, 'this petition is transferred', a transfer prayer 'ordered accordingly').
  referenced_remand   'allowed in the above terms' where the terms are a fresh decision by the authority.

All values are AUTOMATED CANDIDATES read from a PDF text layer; nothing is legally verified."""
import re

from v4_quotes import in_spans
from v4_clauses import _PARTY_STMT_RE

# referential extent: the phrase points back to directions given earlier
_REFERENTIAL_EXTENT_RE = re.compile(
    r"\bto\s+the\s+(?:aforesaid|above|said|abovementioned|above[-\s]mentioned|afore[-\s]?stated|extent\s+(?:and\s+in\s+(?:the\s+)?terms\s+)?"
    r"(?:herein\s*(?:above|before|after)|indicated|stated|mentioned|noted|directed|ordered|set\s+out)|indicated|stated|"
    r"mentioned)\s*(?:above|hereinabove|herein\s+above|earlier)?\s*(?:extent)?\b|\bto\s+that\s+extent\b|\bto\s+this\s+extent\b|"
    r"\bto\s+the\s+extent\s+(?:as\s+)?(?:indicated|stated|mentioned|directed|noted)\b", re.I)
_LIMITED_EXTENT_RE = re.compile(r"\b(?:limited\s+extent|limited\s+to|confined\s+to|only\s+to\s+the\s+extent|"
                                r"partly|partially|in\s+part)\b", re.I)
# the operative part refuses or cuts down part of what was sought
_LIMITATION_RE = re.compile(
    r"\b(?:rest\s+of\s+the|remaining|other|further)\s+(?:claims?|prayers?|reliefs?|grounds?|contentions?)\b[^.;]{0,120}?"
    r"\b(?:rejected|declined|refused|dismissed|not\s+(?:granted|allowed|pressed|entertained))|"
    r"\b(?:claim|prayer|relief|request)s?\s+(?:for|of|to)\b[^.;]{0,120}?\b(?:is|are|stands?|be)\s+(?:hereby\s+)?"
    r"(?:rejected|declined|refused|dismissed|not\s+(?:granted|allowed))|"
    r"\b(?:relief|prayer|claim)s?\s+(?:of|for)\b[^.;]{0,80}?\b(?:cannot|can\s*not|could\s+not|shall\s+not)\s+be\s+granted|"
    r"\bwe\s+(?:\w+,?\s+){0,2}decline\b|\bnot\s+entitled\s+to\b|\bno\s+(?:arrears|interest|back\s*wages|costs?\s+(?:is|are)\s+claimed)\b|"
    r"\b(?:is|are|stands?|be)\s+(?:hereby\s+)?(?:modified|reduced|substituted)\b|\bwith\s+(?:the\s+)?(?:aforesaid|above|following)\s+modifications?\b|"
    r"\bsave\s+and\s+except\b|\bexcept\s+(?:for|that|to\s+the\s+extent)\b|\bpartly\b|\bpartially\b|\bin\s+part\b|"
    r"\bconfined\s+to\b|\blimited\s+to\s+the\b|\brestricted\s+to\b|\bonly\s+(?:to\s+the\s+extent|for\s+the\s+period|from\s+the\s+date)\b",
    re.I)
_IMPUGNED_RE = re.compile(r"\bimpugned\b|\b(?:order|notice|judgment|judgement|award|decision|communication|letter)s?\s+dated\b|"
                          r"\b(?:reassessment|assessment|termination|dismissal|discharge|punishment)\s+order\b", re.I)
_QUASH_RE = re.compile(r"\b(?:is|are|stands?|be|being)\s+(?:hereby\s+|accordingly\s+|also\s+)*(?:quashed|set\s*-?\s*aside)\b|"
                       r"\bwe\s+(?:hereby\s+|accordingly\s+)*(?:quash|set\s+aside)\b", re.I)


_SENT_BREAK_RE = re.compile(r"[.;:?!][\u201d\u2019\"']?\s+(?=[\"\u201c(]?[A-Z0-9(])")


def sentence_start(mt, a, pos):
    """Start of the sentence holding pos (not earlier than a). Dots inside dates and numbers ('31.03.2021',
    'No.123') do not end a sentence."""
    last = a
    for m in _SENT_BREAK_RE.finditer(mt, max(a, pos - 1500), pos):
        last = m.end()
    return last


def court_voice(d, a, b, rx):
    """Matches of rx in mt[a:b] outside quotations and outside sentences that report a party's statement."""
    out = []
    for m in rx.finditer(d.mt, a, b):
        if in_spans(d.qspans, d.qstarts, m.start()):
            continue
        ls = sentence_start(d.mt, a, m.start())
        if _PARTY_STMT_RE.search(d.mt[ls:m.start()]):
            continue
        out.append(m)
    return out


def extent_kind(sentence):
    """'limited' (the wording itself cuts down the relief), 'referential' (points back to the directions), or ''."""
    if _LIMITED_EXTENT_RE.search(sentence):
        return "limited"
    if _REFERENTIAL_EXTENT_RE.search(sentence) or re.search(r"\bextent\b", sentence, re.I):
        return "referential"
    return ""


def extent_resolution(d, ev, zone):
    """Resolve an extent-qualified allowance (C11 F05). Returns (printed, substantive, note_or_reason).
    printed is 'partly_allowed', 'allowed' or None (abstain)."""
    sent = d.mt[ev["sentence"][0]:ev["sentence"][1]]
    kind = extent_kind(sent)
    zs, ze = zone if zone else (ev["sentence"][0], ev["sentence"][1])
    # the directions an extent phrase refers to are the operative paragraphs before the disposing sentence
    a = max(0, min(zs, ev["sentence"][0] - 2500))
    if kind == "limited":
        return "partly_allowed", "relief_partly_granted", "note:EXTENT_LIMITING_WORDS_READ_AS_PARTLY_ALLOWED"
    lim = [m for m in court_voice(d, a, ze, _LIMITATION_RE) if not (ev["sentence"][0] <= m.start() < ev["sentence"][1])]
    if lim:
        return "partly_allowed", "relief_partly_granted", "note:EXTENT_PHRASE_WITH_LIMITATION_IN_OPERATIVE_PART:" + \
            " ".join(lim[0].group(0).split())[:60]
    quash = [m for m in court_voice(d, a, ze, _QUASH_RE)
             if _IMPUGNED_RE.search(d.mt[sentence_start(d.mt, a, m.start()):m.end()])]
    if quash:
        return "allowed", "relief_granted", "note:EXTENT_PHRASE_REFERS_TO_DIRECTIONS_QUASHING_IMPUGNED_DECISIONS_NONE_REFUSED"
    return None, None, "EXTENT_QUALIFIED_ALLOWANCE_NO_LIMITATION_OR_QUASHING_FOUND"


# ------------------------------------------------------------------ transfer to another forum
_TRANSFER_DIR_RE = re.compile(
    r"\b(?:transmit|transfer|send|forward)\s+(?:the\s+)?(?:entire\s+)?(?:record|records|paper\s*-?\s*book|file|case|matter|petition|"
    r"writ\s+petition)\b[^.;]{0,140}?\bto\s+the\s+(?:learned\s+)?(?:Armed\s+Forces?\s+Tribunal|A\.?\s?F\.?\s?T\.?|Tribunal)|"
    r"\b(?:record|records|paper\s*-?\s*book|file|case|matter|petition|writ\s+petition|it)\b[^.;]{0,140}?\b(?:is|are|be|shall\s+(?:be|stand)|"
    r"stands?|is\s+hereby|are\s+hereby)\s+(?:hereby\s+|accordingly\s+|also\s+)*(?:transmitted|transferred|sent|forwarded|remitted)\b"
    r"[^.;]{0,80}?\bto\s+the\s+(?:learned\s+)?(?:Armed\s+Forces?\s+Tribunal|A\.?\s?F\.?\s?T\.?|Tribunal)|"
    r"\b(?:Registry|Registrar|office)\b[^.;]{0,60}?\bdirected\s+to\s+(?:send|transmit|forward|transfer)\b[^.;]{0,120}?"
    r"\b(?:Armed\s+Forces?\s+Tribunal|A\.?\s?F\.?\s?T\.?|Tribunal)|"
    r"\b(?:not\s+adjudicated|not\s+decided)\b[^.;]{0,80}?\bbut\s+(?:is\s+)?(?:transmitted|transferred|sent)\s+to\s+the\s+"
    r"(?:Armed\s+Forces?\s+Tribunal|A\.?\s?F\.?\s?T\.?|Tribunal)", re.I)
_TRANSFER_PRAYER_RE = re.compile(r"\bprayer\s+is\s+for\s+(?:the\s+)?transfer\b[^.]{0,160}\.\s*(?:It\s+is\s+)?(?:Ordered|Order)\s*,?\s+accordingly",
                                 re.I)
_NOT_THIS_CASE_RE = re.compile(r"\bif\s|\bin\s+case\b|\bshould\b|\bmay\s+(?:be\s+)?(?:transfer|send)|\bfiled\s+before\b|"
                               r"\bliberty\b|\bopen\s+to\b|\bcopy\s+of\b|\bcopies\b|\bcertified\b", re.I)


def transfer_direction(d, zone):
    """The court's own direction sending this proceeding to the Tribunal (or None). Returns the match."""
    if not zone:
        return None
    zs, ze = zone
    for m in court_voice(d, zs, ze, _TRANSFER_PRAYER_RE) + court_voice(d, zs, ze, _TRANSFER_DIR_RE):
        ls = sentence_start(d.mt, zs, m.start())
        if _NOT_THIS_CASE_RE.search(d.mt[ls:m.end()]):
            continue
        return m
    return None


# ------------------------------------------------------------------ allowance whose terms are a fresh decision
_REF_TERMS_RE = re.compile(r"\bin\s+(?:the\s+)?(?:above|aforesaid|following|said|afore-?stated|terms\s+(?:indicated|stated)\s+above)\s+terms\b|"
                           r"\bin\s+terms\s+of\s+the\s+(?:above|aforesaid)\s+directions?\b", re.I)
_FRESH_RE = re.compile(r"\bbe\s+re-?examined\b|\b(?:a\s+)?fresh\s+(?:speaking\s+|reasoned\s+)?(?:order|decision|consideration)\s+"
                       r"(?:be|shall\s+be|is\s+to\s+be)\s+(?:passed|taken|made)\b|\bre-?consider(?:ation)?\b[^.;]{0,60}\b(?:afresh|in\s+accordance|"
                       r"in\s+terms|as\s+per)\b|\bdirected\s+re-?consideration\b|\bconsider\s+(?:the\s+)?(?:case|claim|representation|matter)\s+"
                       r"(?:of\s+the\s+(?:petitioner|appellant)\s+)?afresh\b", re.I)


def referenced_remand(d, ev, zone):
    """'The petition is allowed in the aforesaid terms' where the terms send the matter back for a fresh decision."""
    sent = d.mt[ev["sentence"][0]:ev["sentence"][1]]
    if not _REF_TERMS_RE.search(sent):
        return None
    a = max(0, ev["sentence"][0] - 3000)
    if zone:
        a = max(a, zone[0] - 2500)
    ms = court_voice(d, a, ev["sentence"][0], _FRESH_RE)
    return ms[-1] if ms else None


# ------------------------------------------------------------------ operative directions and confidence (V4)
_DIRECTION_KINDS = [
    ("set_aside", _QUASH_RE),
    ("remand", re.compile(r"\b(?:remand\w*|remit(?:s|ted)?|sent\s+back|restored?\s+to\s+(?:the\s+)?file)\b|\bafresh\b|\bde\s+novo\b|"
                          r"\bfresh\s+(?:decision|consideration|order)\b", re.I)),
    ("transfer", _TRANSFER_DIR_RE),
    ("direction", re.compile(r"\b(?:is|are|stand|be)\s+(?:hereby\s+)?directed\b|\bwe\s+(?:hereby\s+)?direct\b|\bit\s+is\s+(?:hereby\s+)?directed\b",
                             re.I)),
    ("relief", re.compile(r"\b(?:shall|is|are)\s+(?:be\s+)?(?:hereby\s+)?(?:entitled|reinstated|granted|released|paid)\b", re.I)),
    ("modification", re.compile(r"\b(?:is|are|stands?|be)\s+(?:hereby\s+)?modified\b", re.I)),
    ("withdrawal", re.compile(r"\bwithdrawn\b|\bwithdrawal\b|\bnot\s+pressed\b|\bliberty\s+to\s+withdraw", re.I)),
    ("liberty", re.compile(r"\bliberty\b|\bopen\s+to\s+the\s+(?:petitioner|appellant|respondent)s?\b", re.I)),
    ("listing_or_adjournment", re.compile(r"\b(?:be\s+(?:re-?)?listed|list\s+(?:on|the\s+matter)|stands?\s+adjourned|next\s+date\s+of\s+hearing)\b",
                                          re.I)),
    ("interim_relief", re.compile(r"\binterim\s+(?:order|relief|protection|stay)\b|\bstay\s+(?:is\s+)?granted\b|\bin\s+the\s+meanwhile\b", re.I)),
    ("costs", re.compile(r"\bcosts?\s+(?:of|quantified|assessed)\b|\bwith\s+costs\b|\bexemplary\s+costs\b", re.I)),
]


def direction_kinds(d, zone):
    """Kinds of operative directions given in the court's own voice in the operative part (multiple directions are
    common: set aside + remand + time limit + liberty). Returns a ';'-joined sorted list."""
    if not zone:
        return ""
    zs, ze = zone
    return ";".join(sorted(k for k, rx in _DIRECTION_KINDS if court_voice(d, zs, ze, rx)))


_INFERENTIAL_NOTES = ("EXTENT_", "ALLOWED_IN_TERMS", "TRANSFER_DIRECTION", "withdrawal_sought", "party_prayer_adopted",
                      "modal_only", "inferred_from")


def confidence_tier(method, notes, flags, alpha):
    """Rule-based evidence tier for an answered row: 'high' (a disposing sentence found under an operative cue or order
    heading, or the whole of a short order, mapped without inference, clean text), 'low' (no cue, text noise, or the
    label inferred from directions rather than printed words), else 'medium'. In-sample precision per tier is reported
    in dev_eval; the tier is information for users, not a guarantee."""
    m = method or ""
    if "final_sentences_no_cue" in m or alpha < 0.6 or any(x in (notes or "") or x in m for x in _INFERENTIAL_NOTES):
        return "low"
    if ("operative_cue" in m or "order_heading" in m or "short_order_whole_body" in m) and "batch_section" not in m and \
            not any(f.startswith(("HOSTS_", "SEGMENTS_", "DISSENTING")) for f in flags):
        return "high"
    return "medium"
