"""C13-A3 contextual features and linear-model inference (standard library only).

Each sentence record from `c13_segment.segment` becomes a sparse binary feature set built from
  - its own words (unigrams and bigrams, lower-cased, numbers collapsed) and opening words,
  - the C12 propositional signals (conclusion marker, statement of law, normative predicate, ...),
  - structure: voice, opinion role, section heading, relative position in the opinion, distance from the end in
    court-voice sentences, analysis zone, paragraph position, length,
  - context: the voice and selected signals of the previous and next sentences.
The trained model is a JSON file of per-head logistic-regression weights (`model/c13_holdings_model.json`).
"""
import json
import math
import re

import c13_segment as sg

c12 = sg.c12

_TOK_RE = re.compile(r"[a-z][a-z'\-]+|\d+")
_FACTY_RE = re.compile(r"\b(?:was|were|had\s+been)\s+(?:enrolled|recruited|commissioned|posted|born|tried|arrested|charged|convicted|discharged|dismissed|invalided|"
                       r"released|promoted|transferred|issued|served|convened|filed|preferred|admitted|sanctioned|attested|granted|rejected)\b", re.I)
_ISSUE_HINT_RE = re.compile(r"\b(?:question|issue|point|controversy)s?\b.{0,80}\b(?:whether|arises?|for\s+(?:our\s+)?(?:consideration|determination|decision)|before\s+us)\b"
                            r"|^\W*(?:\(?[ivx]{1,4}[.)]|\(?[a-h][.)]|\d{1,2}[.)])?\s*Whether\b", re.I)
_RESULT_RE = re.compile(r"^\W*(?:\d+\s*[.)]?\s*)?(?:In\s+the\s+result|In\s+view\s+of\s+the\s+(?:above|foregoing)|For\s+the\s+(?:foregoing\s+|aforesaid\s+|above\s+)?reasons|Accordingly|Consequently|"
                        r"Therefore|Thus|Hence|We\s+(?:therefore\s+)?(?:hold|are\s+of\s+the|find|conclude)|In\s+our\s+(?:considered\s+)?(?:view|opinion))", re.I)


def _toks(s):
    out = []
    for t in _TOK_RE.findall(s.lower()):
        out.append("#" if t.isdigit() else t)
    return out


def _pos_bin(p):
    return "%d" % min(9, int(p * 10))


def _rend_bin(k):
    if k is None:
        return "na"
    for b in (1, 2, 3, 5, 10, 20, 50):
        if k <= b:
            return "le%d" % b
    return "gt50"


def _len_bin(n):
    for b in (40, 80, 150, 300, 600):
        if n <= b:
            return "le%d" % b
    return "gt600"


def short_signals(sent):
    sig = set(x.split("(")[0] for x in c12.legal_signals(sent))
    if c12._OPERATIVE_RE.search(sent):
        sig.add("OPERATIVE")
    if c12._DISPOSAL_RE.search(sent):
        sig.add("DISPOSAL")
    if c12._OBITER_RE.search(sent):
        sig.add("OBITER")
    if _FACTY_RE.search(sent):
        sig.add("FACTY")
    if c12._DATE_RE.search(sent):
        sig.add("DATE")
    if _ISSUE_HINT_RE.search(sent) or any(rx.search(sent) for rx in c12._Q_RES):
        sig.add("ISSUE_HINT")
    if re.search(r"\?\s*$", sent):
        sig.add("QMARK")
    if _RESULT_RE.search(sent):
        sig.add("RESULT_OPENER")
    if sg._REJECT_EXTRA_RE.search(sent):
        sig.add("REJECTS_SUBMISSION")
    if sg._CASE_REF_RE.search(sent):
        sig.add("CASE_REF")
    if re.search(r"\b(?:we|us|our)\b", sent, re.I):
        sig.add("WE")
    if re.search(r"\bI\b", sent):
        sig.add("I")
    if re.search(r"\bthis\s+Court\b", sent, re.I):
        sig.add("THIS_COURT")
    if re.search(r"\b(?:Tribunal|AFT|High\s+Court)\b", sent):
        sig.add("LOWER_NAMED")
    return sig


def features(seg, i, role_of):
    recs = seg["recs"]
    r = recs[i]
    sent = r["sent"]
    f = set()
    toks = _toks(sent)
    for t in toks:
        f.add("w:" + t)
    for a, b in zip(toks, toks[1:]):
        f.add("b:%s_%s" % (a, b))
    lead = [t for t in toks if t != "#"][:3]
    if lead:
        f.add("f1:" + lead[0])
        f.add("f3:" + "_".join(lead))
    sig = r.get("_sig")
    if sig is None:
        sig = r["_sig"] = short_signals(sent)
    for s in sig:
        f.add("sig:" + s)
    v = r["voice"]
    f.add("voice:" + v)
    role = role_of(r["oi"])
    f.add("role:" + role)
    f.add("sec:" + (r["section"] or "none"))
    f.add("pos:" + _pos_bin(r.get("pos_in_op", 0.0)))
    f.add("rend:" + _rend_bin(r.get("court_rank_from_end")))
    f.add("zone:" + ("analysis" if r.get("in_analysis_zone") else "pre"))
    f.add("len:" + _len_bin(len(sent)))
    if r.get("para_first"):
        f.add("para:first")
    if r.get("para_last"):
        f.add("para:last")
    if r.get("para_len", 1) == 1:
        f.add("para:single")
    for d, tag in ((-1, "prev"), (1, "next")):
        j = i + d
        if 0 <= j < len(recs) and recs[j]["oi"] == r["oi"]:
            o = recs[j]
            f.add("%svoice:%s" % (tag, o["voice"]))
            osig = o.get("_sig")
            if osig is None:
                osig = o["_sig"] = short_signals(o["sent"])
            for s in ("COURT_CONCLUSION_MARKER", "ISSUE_HINT", "INTRODUCES_QUOTATION_OR_LIST", "OPERATIVE", "CASE_REF", "FACTY"):
                if s in osig:
                    f.add("%ssig:%s" % (tag, s))
        else:
            f.add("%s:none" % tag)
    if v != "court":
        f.add("x:%s_%s" % (v, "WE" in sig))
    return f


class Model:
    """Logistic-regression heads stored as JSON: {"heads": {name: {"bias": b, "w": {feature: weight}}}, ...}."""

    def __init__(self, path):
        with open(path, encoding="utf-8") as fh:
            self.d = json.load(fh)
        self.heads = self.d["heads"]

    def prob(self, head, feats):
        h = self.heads[head]
        w = h["w"]
        z = h["bias"] + sum(w.get(x, 0.0) for x in feats)
        if z < -30:
            return 0.0
        return 1.0 / (1.0 + math.exp(-z))

    def top_features(self, head, feats, k=6):
        w = self.heads[head]["w"]
        sc = sorted(((w[x], x) for x in feats if x in w), reverse=True)
        return [x for _, x in sc[:k]]
