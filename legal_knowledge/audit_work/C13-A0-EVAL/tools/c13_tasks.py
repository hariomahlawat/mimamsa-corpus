"""C13-A0 pluggable task definitions shared by the coding toolkit and the scoring harness.

A task fixes: the coder-visible pointer columns, the coding fields, the label vocabularies (exact labels; anything
else is an error, C12 tools F10), the label families, how a coded row is aligned to another coded row
(the unit key), and which fields carry the evidence anchor. Three tasks: outcome, holdings, relations.
"""
import re
import unicodedata

POINTER_COLS = ["item_id", "rep_sha256", "rep_raw_path", "rep_raw_store", "pages_to_code"]


def case_key(s):
    """Proceeding key, identical to C12 tools/holdout_v3_agreement_c12.py key(): number-year pairs, else the text."""
    m = re.findall(r"(\d{1,6})\s*(?:/|-|\s+of\s+|\s+OF\s+)\s*((?:19|20)\d\d)", s or "")
    return ";".join(sorted({f"{int(a)}-{b}" for a, b in m})) or (s or "").strip().upper()


STOP = set("""a an the and or but if then of to in on at by for with from into as is are was were be been being it its
this that these those which who not no so than can could may might must shall should will would such any all each
other also he she they we you i him her them us his their our your said per vs v viz ie eg etc thus hence however
whether about under over after before between through without within against out up more most one two three""".split())


def content_tokens(s):
    s = unicodedata.normalize("NFKC", s or "").lower()
    s = s.translate(str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-",
                                   "—": "-"}))
    toks = re.sub(r"[^0-9a-z]+", " ", s).split()
    return {t for t in toks if len(t) >= 2 and t not in STOP and not (t.isdigit() and len(t) <= 3)}


def norm_ws(s):
    s = unicodedata.normalize("NFKC", s or "")
    s = s.translate(str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-",
                                   "—": "-", "­": ""}))
    return re.sub(r"\s+", " ", s).strip().lower()


def citation_key(s):
    """Normalised citation key for relations: reporter citations '(2013) 7 SCC 316' -> 'SCC|2013|7|316';
    neutral '2025 INSC 549' -> 'INSC|2025|549'; otherwise case-number key or whitespace-normalised upper text."""
    t = (s or "").upper().replace("SCC ONLINE", "SCCOL").replace("SCC ON LINE", "SCCOL")
    m = re.search(r"[\(\[]?((?:19|20)\d\d)[\)\]]?\s+(\d{1,3})\s+(SCC|SCR|SLR)\s+(\d{1,5})", t)
    if m:
        return f"{m.group(3)}|{m.group(1)}|{m.group(2)}|{m.group(4)}"
    m = re.search(r"((?:19|20)\d\d)\s+(INSC|SCCOL\s+SC|SCCOL\s+DEL|SCALE)\s+(\d{1,6})", t)
    if m:
        return f"{m.group(2).replace(' ', '_')}|{m.group(1)}|{m.group(3)}"
    m = re.search(r"AIR\s+((?:19|20)\d\d)\s+(SC|[A-Z&]+)\s+(\d{1,5})", t)
    if m:
        return f"AIR|{m.group(1)}|{m.group(2)}|{m.group(3)}"
    k = case_key(s)
    return k if re.fullmatch(r"[\d;\-]+", k) else re.sub(r"\s+", " ", t).strip()


class Task:
    name = ""
    coding_fields = []
    vocab = {}          # field -> allowed labels (exact)
    families = {}       # field -> {label: family}
    required = []       # fields that must be non-empty in every coded row
    scored_fields = []
    unscorable = set()  # gold labels that make a unit not determinable (excluded from coverage denominator)

    def unit_key(self, row):
        raise NotImplementedError

    def is_null_row(self, row):
        """A row stating that the item has nothing to code (no holding / no citation on the page)."""
        return False

    def family(self, field, label):
        return self.families.get(field, {}).get(label, label)

    def validate_row(self, row):
        """Return list of errors for a coded row (blank / off-vocabulary labels are errors)."""
        errs = []
        for f in self.required:
            if not (row.get(f) or "").strip():
                errs.append(f"{f}: blank")
        for f, allowed in self.vocab.items():
            v = (row.get(f) or "").strip()
            if f in self.required or v:
                if v not in allowed:
                    errs.append(f"{f}: '{v}' not in vocabulary")
        return errs


class OutcomeTask(Task):
    name = "outcome"
    coding_fields = ["host_case_numbers", "proceeding", "printed_disposal", "substantive_result", "party_specific",
                     "final_or_interim", "page", "para", "excerpt", "confidence", "notes"]
    vocab = {
        "printed_disposal": {"allowed", "partly_allowed", "dismissed", "dismissed_as_withdrawn",
                             "dismissed_as_infructuous", "dismissed_in_default", "disposed_of",
                             "disposed_of_with_directions", "remanded", "set_aside_and_remanded", "transferred",
                             "not_final", "other", "unclear"},
        "substantive_result": {"relief_granted", "relief_partly_granted", "relief_refused", "no_adjudication",
                               "remanded_for_fresh_decision", "interim_only", "unclear"},
        "final_or_interim": {"final", "interim"},
        "confidence": {"high", "medium", "low"},
    }
    families = {
        "printed_disposal": {"allowed": "ALLOWED", "partly_allowed": "PARTLY", "dismissed": "DISMISSED",
                             "dismissed_as_withdrawn": "DISMISSED", "dismissed_as_infructuous": "DISMISSED",
                             "dismissed_in_default": "DISMISSED", "disposed_of": "DISPOSED",
                             "disposed_of_with_directions": "DISPOSED", "remanded": "REMANDED",
                             "set_aside_and_remanded": "REMANDED", "transferred": "TRANSFERRED"},
        "substantive_result": {"relief_granted": "GRANTED", "relief_partly_granted": "GRANTED_PARTLY",
                               "relief_refused": "REFUSED", "no_adjudication": "NO_ADJUDICATION",
                               "remanded_for_fresh_decision": "REMANDED", "interim_only": "INTERIM"},
    }
    required = ["proceeding", "printed_disposal", "substantive_result", "final_or_interim", "page", "confidence"]
    scored_fields = ["printed_disposal", "substantive_result"]
    unscorable = {"unclear", "other"}
    anchor_fields = ("page", "excerpt")

    def unit_key(self, row):
        return case_key(row.get("proceeding"))


class HoldingsTask(Task):
    name = "holdings"
    coding_fields = ["item_type", "opinion", "judge", "page", "para", "excerpt", "legal_issue", "certainty", "notes"]
    vocab = {
        "item_type": {"holding", "question_of_law"},
        "opinion": {"sole", "lead", "concurring", "separate", "dissent", "unclear"},
        "certainty": {"certain", "probable", "uncertain"},
    }
    families = {"item_type": {"holding": "HOLDING", "question_of_law": "QOL"},
                "opinion": {"sole": "MAJORITY", "lead": "MAJORITY", "concurring": "MAJORITY",
                            "separate": "OTHER_OPINION", "dissent": "OTHER_OPINION"}}
    required = ["item_type", "opinion", "page", "excerpt", "certainty"]
    scored_fields = ["item_type", "opinion"]
    anchor_fields = ("page", "excerpt")
    # span matcher (C12 primary matcher, pre-registered): >= 3 shared content tokens, overlap/min >= 0.60, page +/-1
    MATCH_OVERLAP, MATCH_PAGE_DIST, MATCH_MIN_SHARED = 0.60, 1, 3

    def unit_key(self, row):
        return None  # spans are matched, not keyed

    def is_null_row(self, row):
        return (row.get("notes") or "").strip() == "NO_HOLDING" and not any(
            (row.get(f) or "").strip() for f in self.coding_fields if f != "notes")

    def validate_row(self, row):
        return [] if self.is_null_row(row) else super().validate_row(row)

    def spans_match(self, a, b):
        try:
            pa, pb = int(a.get("page")), int(b.get("page"))
            if abs(pa - pb) > self.MATCH_PAGE_DIST:
                return False
        except (TypeError, ValueError):
            return False
        ta, tb = content_tokens(a.get("excerpt")), content_tokens(b.get("excerpt"))
        if not ta or not tb:
            return False
        inter = len(ta & tb)
        return inter >= self.MATCH_MIN_SHARED and inter / min(len(ta), len(tb)) >= self.MATCH_OVERLAP


class RelationsTask(Task):
    name = "relations"
    coding_fields = ["page", "cited_string", "cited_case_name", "target", "relation_type", "voice", "excerpt",
                     "confidence", "notes"]
    vocab = {
        "relation_type": {"cites", "follows", "applies", "distinguishes", "overrules", "doubts", "not_followed",
                          "refers_to_larger_bench", "other", "unclear"},
        "voice": {"court_own", "quoted_passage", "party_submission", "lower_forum", "editorial", "unclear"},
        "confidence": {"high", "medium", "low"},
    }
    families = {"relation_type": {"cites": "NEUTRAL", "follows": "POSITIVE", "applies": "POSITIVE",
                                  "distinguishes": "NEGATIVE_LIMITING", "not_followed": "NEGATIVE_LIMITING",
                                  "doubts": "NEGATIVE_LIMITING", "refers_to_larger_bench": "NEGATIVE_LIMITING",
                                  "overrules": "NEGATIVE_OVERRULING"}}
    required = ["page", "cited_string", "relation_type", "voice", "confidence"]
    scored_fields = ["relation_type", "target"]
    unscorable = {"unclear", "other"}
    anchor_fields = ("page", "excerpt")

    def unit_key(self, row):
        return f"p{(row.get('page') or '').strip()}|{citation_key(row.get('cited_string'))}"

    def is_null_row(self, row):
        return (row.get("cited_string") or "").strip().upper() == "NONE"


TASKS = {"outcome": OutcomeTask(), "holdings": HoldingsTask(), "relations": RelationsTask()}
HOLDOUT_TASK = {"H-OUT-C13": "outcome", "H-HOLD-C13": "holdings", "H-REL-C13": "relations"}
