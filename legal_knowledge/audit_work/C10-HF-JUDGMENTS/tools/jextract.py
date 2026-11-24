"""Deterministic per-judgment extraction for the C10 Hugging Face judicial corpus audit.

Every value produced here is an AUTOMATED CANDIDATE read from the PDF text layer. Nothing is legally verified, and a
field that cannot be found is NOT_FOUND (never inferred). Patterns are fixed in this file so a rerun gives identical
results for identical bytes.
"""
import hashlib, re
from collections import Counter

EXTRACTOR_VERSION = "c10-jextract/5"
MIN_CHARS_PAGE = 200          # a page with fewer text-layer characters is treated as image-only / unreadable

MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august",
                                      "september", "october", "november", "december"], 1)}
for k, v in list(MONTHS.items()):
    MONTHS[k[:3]] = v
MONTHS["sept"] = 9

# ---------------------------------------------------------------- statutes and instruments (name -> pattern)
STATUTES = [
    ("Army Act, 1950", r"\bArmy\s+Act\b"),
    ("Army Rules, 1954", r"\bArmy\s+Rules?\b"),
    ("Air Force Act, 1950", r"\bAir\s+Force\s+Act\b"),
    ("Air Force Rules, 1969", r"\bAir\s+Force\s+Rules?\b"),
    ("Navy Act, 1957", r"\bNavy\s+Act\b"),
    ("Armed Forces Tribunal Act, 2007", r"\bArmed\s+Forces\s+Tribunals?\s+Act\b|\bA\.?F\.?T\.?\s+Act\b"),
    ("AFT (Procedure) Rules, 2008", r"Armed\s+Forces\s+Tribunal\s+\(Procedure\)\s+Rules"),
    ("Regulations for the Army", r"Regulations\s+for\s+the\s+Army"),
    ("Pension Regulations for the Army", r"Pension\s+Regulations\s+for\s+the\s+Army|\bPension\s+Regulations\b"),
    ("Entitlement Rules", r"\bEntitlement\s+Rules\b"),
    ("Guide to Medical Officers", r"Guide\s+to\s+Medical\s+Officers"),
    ("Defence Service Regulations", r"Defence\s+Services?\s+Regulations"),
    ("Constitution of India", r"\bArticles?\s+(?:14|16|19|21|32|33|136|141|142|226|227|300-?A|309|310|311)\b|\bConstitution\s+of\s+India\b"),
    ("Code of Criminal Procedure, 1973", r"Code\s+of\s+Criminal\s+Procedure|\bCr\.?\s?P\.?\s?C\b"),
    ("Indian Penal Code, 1860", r"Indian\s+Penal\s+Code|\bI\.?P\.?C\.?\b"),
    ("Indian Evidence Act, 1872", r"(?:Indian\s+)?Evidence\s+Act"),
    ("Bharatiya Nyaya Sanhita, 2023", r"Bharatiya\s+Nyaya\s+Sanhita|\bBNS\b"),
    ("Bharatiya Nagarik Suraksha Sanhita, 2023", r"Bharatiya\s+Nagarik\s+Suraksha\s+Sanhita|\bBNSS\b"),
    ("Bharatiya Sakshya Adhiniyam, 2023", r"Bharatiya\s+Sakshya\s+Adhiniyam|\bBSA\b(?!\s*\d)"),
    ("Limitation Act, 1963", r"\bLimitation\s+Act\b"),
    ("CCS (Pension) Rules", r"C\.?C\.?S\.?\s*\(Pension\)\s*Rules"),
    ("CCS (CCA) Rules", r"C\.?C\.?S\.?\s*\(C\.?C\.?A\.?\)\s*Rules"),
    ("Border Security Force Act, 1968", r"Border\s+Security\s+Force\s+Act|\bB\.?S\.?F\.?\s+Act\b"),
    ("Central Reserve Police Force Act, 1949", r"Central\s+Reserve\s+Police\s+Force\s+Act|\bCRPF\s+Act\b"),
    ("Assam Rifles Act, 2006", r"Assam\s+Rifles\s+Act"),
    ("Indo-Tibetan Border Police Force Act, 1992", r"Indo-?\s?Tibetan\s+Border\s+Police"),
    ("Coast Guard Act, 1978", r"Coast\s+Guard\s+Act"),
    ("Territorial Army Act, 1948", r"Territorial\s+Army\s+Act"),
    ("Armed Forces (Special Powers) Act", r"Armed\s+Forces\s+\(Special\s+Powers\)\s+Act|\bAFSPA\b"),
    ("Official Secrets Act, 1923", r"Official\s+Secrets\s+Act"),
    ("Cantonments Act", r"\bCantonments?\s+Act\b"),
    ("Industrial Disputes Act, 1947", r"Industrial\s+Disputes\s+Act"),
    ("Right to Information Act, 2005", r"Right\s+to\s+Information\s+Act"),
]
STAT_RE = [(n, re.compile(p)) for n, p in STATUTES]
SEC_BEFORE = re.compile(r"(?:[Ss]ections?|[Ss]ec\.|[Ss]s?\.|[Rr]ules?|[Rr]egulations?|[Pp]aras?|[Aa]rticles?)\s*([0-9][0-9A-Za-z()\-,\s/&]{0,40}?)\s+(?:of\s+(?:the\s+)?)?$")

# ---------------------------------------------------------------- legal-issue taxonomy (automated topic tags)
TOPICS = [
    ("court_martial", r"court[\s-]+martial|\bG\.?C\.?M\b|\bS\.?G\.?C\.?M\b|\bD\.?C\.?M\b|summary\s+court"),
    ("summary_of_evidence", r"summary\s+of\s+evidence"),
    ("court_of_inquiry", r"court\s+of\s+inquiry|court\s+of\s+enquiry"),
    ("statutory_complaint", r"statutory\s+complaint|redress(?:al)?\s+of\s+grievances?"),
    ("aft_jurisdiction", r"Armed\s+Forces\s+Tribunal|\bA\.?F\.?T\b"),
    ("writ_against_aft_order", r"(?:order|judgment)\s+of\s+the\s+(?:learned\s+)?(?:Armed\s+Forces\s+)?Tribunal.{0,80}(?:Article\s+226|writ)"),
    ("disability_pension", r"disability\s+(?:pension|element)|war\s+injury\s+pension"),
    ("attributability_aggravation", r"attributab|aggravat"),
    ("medical_board", r"medical\s+board|invalid(?:ed|ment)|\bR\.?M\.?B\b|\bI\.?M\.?B\b"),
    ("service_pension", r"service\s+pension|qualifying\s+service|pensionary\s+benefits"),
    ("family_pension", r"family\s+pension"),
    ("orop_pay_fixation", r"one\s+rank\s+one\s+pension|\bOROP\b|pay\s+fixation|\bM\.?A\.?C\.?P\b|\bA\.?C\.?P\b"),
    ("dismissal_discharge_termination", r"dismiss(?:al|ed)\s+from\s+service|discharge(?:d)?\s+from\s+service|terminat(?:ion|ed)\s+of\s+service|removal\s+from\s+service"),
    ("reinstatement", r"reinstat"),
    ("desertion_absence", r"\bdesert(?:ion|er|ed)\b|absent\s+without\s+leave|\bA\.?W\.?L\b"),
    ("promotion_selection", r"promotion|selection\s+board|\bD\.?P\.?C\b"),
    ("seniority", r"\bseniority\b"),
    ("natural_justice", r"natural\s+justice|audi\s+alteram|show[\s-]+cause|bias"),
    ("delay_limitation", r"\bdelay\b|laches|limitation"),
    ("sentence_punishment", r"\bsentence\b|punishment"),
    ("compassionate_appointment", r"compassionate\s+appointment"),
    ("recovery_overpayment", r"\brecovery\b.{0,40}(?:excess|over)\s?payment|overpayment"),
    ("transfer_posting", r"\btransfer\s+order|\bposting\b"),
    ("constitutional_rights", r"Article\s+(?:14|16|21)\b|equality\s+before\s+the\s+law|arbitrar"),
    ("statutory_interpretation", r"statutory\s+interpretation|purposive\s+(?:interpretation|construction)|literal\s+(?:rule|interpretation)"),
]
TOP_RE = [(n, re.compile(p, re.I)) for n, p in TOPICS]

DIRECT = re.compile(r"\bArmy\s+Act\b|\bAir\s+Force\s+Act\b|\bNavy\s+Act\b|Armed\s+Forces\s+Tribunals?\s+Act|court[\s-]+martial|"
                    r"\bArmy\s+Rules?\b|\bAir\s+Force\s+Rules?\b|summary\s+of\s+evidence|statutory\s+complaint|Regulations\s+for\s+the\s+Army", re.I)
ADMIN = re.compile(r"disability\s+pension|Entitlement\s+Rules|Pension\s+Regulations|\binvalided\b|release\s+medical\s+board|"
                   r"ex[\s-]?servicem[ae]n|armed\s+forces|defence\s+personnel|Ministry\s+of\s+Defence|Army\s+Headquarters|"
                   r"Record\s+Office|Commanding\s+Officer|\bsepoy\b|\bnaik\b|\bhavildar\b|\bsubedar\b|\bjawan\b|\bAir\s+Force\b|\bIndian\s+Navy\b|"
                   r"Armed\s+Forces\s+Tribunal|Principal\s+Controller\s+of\s+Defence\s+Accounts|\bPCDA\b", re.I)
GENERAL = re.compile(r"natural\s+justice|audi\s+alteram|Article\s+(?:14|16|21|226|311)\b|arbitrar|legitimate\s+expectation|"
                     r"proportionality|Wednesbury|statutory\s+interpretation|doctrine\s+of\s+precedent|per\s+incuriam|res\s+judicata", re.I)

# ---------------------------------------------------------------- citations
CITES = [
    ("neutral_INSC", r"\b(?:19|20)\d{2}\s+INSC\s+\d{1,4}\b"),
    ("SCC", r"\(\s*(?:19|20)\d{2}\s*\)\s*\d{1,2}\s+SCC(?:\s*\(\w+\))?\s+\d{1,4}"),
    ("SCR", r"\[\s*(?:19|20)\d{2}\s*\]\s*\d{1,2}\s+S\.?\s?C\.?\s?R\.?\s+\d{1,4}"),
    ("AIR_SC", r"\bAIR\s+(?:19|20)\d{2}\s+SC\s+\d{1,4}"),
    ("AIR_other", r"\bAIR\s+(?:19|20)\d{2}\s+(?!SC\b)[A-Z][A-Za-z&]{1,8}\s+\d{1,4}"),
    ("SCALE", r"\(?(?:19|20)\d{2}\)?\s*\(?\d{1,2}\)?\s+SCALE\s+\d{1,4}"),
    ("JT", r"\bJT\s+(?:19|20)\d{2}\s*\(\d{1,2}\)\s*SC\s+\d{1,4}"),
    ("HC_neutral", r"\b(?:19|20)\d{2}\s*:\s*[A-Z]{2,6}(?:-[A-Z]{2,4})?\s*:\s*\d{1,6}(?:-DB)?\b"),
    ("SLR", r"\b(?:19|20)\d{2}\s*\(\d\)\s*SLR\s+\d{1,4}"),
]
CIT_RE = [(n, re.compile(p)) for n, p in CITES]

# ---------------------------------------------------------------- case numbers
CASE_RE = re.compile(
    r"(?P<type>W\.?\s?P\.?\s?\(\s?(?:C|Civil|Crl|S)\.?\s?\)|Writ\s+Petition(?:\s*\((?:Civil|Criminal|C)\))?|Civil\s+Appeal|Criminal\s+Appeal|"
    r"C\.?A\.?|S\.?L\.?P\.?\s?\((?:C|Civil|Crl)\.?\)|Special\s+Leave\s+Petition(?:\s*\((?:Civil|C|Criminal|Crl)\))?|L\.?P\.?A\.?|C\.?W\.?P\.?|"
    r"O\.?A\.?|T\.?A\.?|R\.?S\.?A\.?|CRM-M|C\.?R\.?P\.?|WRIA|WRIT\s*-?\s*A|Special\s+Appeal|SPLA|WPA|W\.?A\.?|Review\s+Petition|Transfer(?:red)?\s+Application|Original\s+Application)"
    r"\s*(?:Nos?\.?|Number)?\s*[:.\-–]?\s*(?P<num>\d{1,6}(?:\s*[-–]\s*\d{1,6}(?=\s*(?:of|/)))?)\s*(?:of|/|[-–])\s*(?P<year>(?:19|20)\d{2})(?!\d)", re.I)

# ---------------------------------------------------------------- dates
DATE_LABEL = re.compile(r"(?:Pronounced\s+on|Date\s+of\s+(?:Decision|Judgment|Order|Pronouncement)|Decided\s+on|Judgment\s+(?:delivered\s+)?on|"
                        r"Order\s+(?:pronounced\s+)?on|Dated?)\s*[:\-–]?\s*(?P<d>[0-9]{1,2}(?:st|nd|rd|th)?[\s./-]+(?:[0-9]{1,2}|[A-Za-z]{3,9})[\s.,/-]+(?:19|20)[0-9]{2})", re.I)
DATE_SC_TAIL = re.compile(r"New\s+Delhi\s*[;,.]?\s*(?P<d>(?:[A-Za-z]{3,9})\s+[0-9]{1,2}\s*,\s*(?:19|20)[0-9]{2}|[0-9]{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]{3,9}\s*,?\s*(?:19|20)[0-9]{2})", re.I)


# Decision-date evidence (strong): explicit decision labels, or the signature-block date in the last part of the text.
# Plain 'Dated' is excluded because it usually refers to an earlier order or notification.
DATE_STRONG = re.compile(r"(?:Pronounced\s+on|Date\s+of\s+(?:Decision|Judgment|Order|Pronouncement)|Decided\s+on|Judgment\s+delivered\s+on|"
                         r"Order\s+Date|Date\s+of\s+hearing\s+and\s+order)\s*[:\-–]*\s*(?P<d>[0-9]{1,2}(?:st|nd|rd|th)?[\s./-]+(?:[0-9]{1,2}|[A-Za-z]{3,9})[\s.,/-]+(?:19|20)[0-9]{2})", re.I)
DATE_TAIL_WORD = re.compile(r"\b(?P<d>(?:JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER|January|February|March|April|May|June|July|August|September|October|November|December)\s+[0-9]{1,2}\s*,\s*(?:19|20)[0-9]{2})")
DATE_TAIL_NUM = re.compile(r"(?<![\d/.-])(?P<d>[0-3]?[0-9][./-][01]?[0-9][./-](?:19|20)[0-9]{2})(?![\d/.-])")


def parse_date(s):
    s = s.strip().replace(",", " ")
    m = re.match(r"(\d{1,2})(?:st|nd|rd|th)?[\s./-]+(\d{1,2})[\s./-]+((?:19|20)\d{2})$", s)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    else:
        m = re.match(r"(\d{1,2})(?:st|nd|rd|th)?[\s./-]+([A-Za-z]{3,9})\.?[\s./-]+((?:19|20)\d{2})$", s)
        if m:
            d, mo, y = int(m.group(1)), MONTHS.get(m.group(2).lower()), int(m.group(3))
        else:
            m = re.match(r"([A-Za-z]{3,9})\.?\s+(\d{1,2})\s+((?:19|20)\d{2})$", s)
            if not m:
                return None
            mo, d, y = MONTHS.get(m.group(1).lower()), int(m.group(2)), int(m.group(3))
    if not mo or not (1 <= mo <= 12) or not (1 <= d <= 31):
        return None
    return f"{y:04d}-{mo:02d}-{d:02d}"


# ---------------------------------------------------------------- outcomes
OUTCOMES = [
    ("partly_allowed", r"(?:appeal|petition|application|O\.?A\.?|writ\s+petition)s?\s+(?:is|are|stands?)\s+(?:partly|partially)\s+allowed|allowed\s+in\s+part|partly\s+allowed"),
    ("remanded", r"remanded|remitted\s+(?:back\s+)?to\s+the|matter\s+is\s+sent\s+back"),
    ("allowed", r"(?:appeal|petition|application|O\.?A\.?|writ\s+petition|writ)s?\s+(?:is|are|stands?|is\s+accordingly|are\s+accordingly)\s+allowed|\ballowed\s+as\s+prayed|rule\s+(?:is\s+)?made\s+absolute"),
    ("dismissed", r"(?:appeal|petition|application|O\.?A\.?|writ\s+petition|writ)s?\s+(?:is|are|stands?|is\s+accordingly|are\s+accordingly|being\s+devoid\s+of\s+merit\s+is)\s+dismissed|\bdismissed\s+as\s+(?:withdrawn|infructuous|not\s+pressed)|devoid\s+of\s+merit|lacks?\s+merit"),
    ("disposed", r"(?:appeal|petition|application|O\.?A\.?|writ\s+petition)s?\s+(?:is|are|stands?)\s+(?:accordingly\s+)?disposed\s+of|disposed\s+of\s+in\s+(?:the\s+above|these)\s+terms"),
    ("set_aside_quashed", r"(?:impugned\s+)?(?:order|judgment|findings?|sentence)\s+(?:is|are|dated.{0,30}is)\s+(?:hereby\s+)?(?:set\s+aside|quashed)"),
    # generic phrasings observed in the corpus (batch 0 review): 'the same is, accordingly, dismissed', 'dismissed in limine', ...
    ("dismissed", r"\b(?:is|are|stands?)\s*,?\s*(?:hereby\s+|accordingly\s*,?\s+|therefore\s*,?\s+|thus\s+|hence\s+)?dismissed\b|dismissed\s+in\s+limine|(?:^|[.]\s)Dismissed\.|no\s+merit\s+and\s+is\s+dismissed"),
    ("allowed", r"\b(?:is|are|stands?)\s*,?\s*(?:hereby\s+|accordingly\s*,?\s+|therefore\s*,?\s+|thus\s+|hence\s+)?allowed\b(?!\s+to)|(?:^|[.]\s)Allowed\."),
    ("disposed", r"\b(?:is|are|stands?)\s*,?\s*(?:hereby\s+|accordingly\s*,?\s+)?disposed\s+of|[Dd]isposed\s+of\s+accordingly|consigned\s+to\s+(?:the\s+)?records|(?:^|[.]\s)Disposed\s+of\."),
    ("transferred", r"(?:case|petition|matter)\s+is\s+(?:hereby\s+)?transferred\s+to\s+the\s+(?:\w+\s+){0,4}(?:Armed\s+Forces\s+)?Tribunal"),
]
OUT_RE = [(n, re.compile(p, re.I)) for n, p in OUTCOMES]

PROP_MARK = re.compile(r"\b(?:we\s+(?:therefore\s+)?hold|it\s+is\s+(?:thus\s+)?held|it\s+is\s+(?:well\s+)?settled|the\s+law\s+is\s+(?:well\s+)?settled|"
                       r"we\s+are\s+(?:therefore\s+)?of\s+the\s+(?:considered\s+)?(?:view|opinion)|we\s+are\s+unable\s+to\s+accept|"
                       r"the\s+(?:legal\s+)?position\s+(?:of\s+law\s+)?is|in\s+our\s+(?:considered\s+)?(?:view|opinion))\b", re.I)
PARA_NUM = re.compile(r"(?:^|\n)\s*(\d{1,3})\.\s+[A-Z(]")
CORRECTED = re.compile(r"\b(?:corrected|corrigendum|errata|rectified|modified\s+judgment|revised\s+judgment|reportable\s+version)\b", re.I)


def _norm_case(t, n, y):
    t = re.sub(r"[^a-z]", "", t.lower())
    alias = {"wpc": "WPC", "writpetitioncivil": "WPC", "writpetitionc": "WPC", "writpetition": "WP", "wps": "WPS", "wpcrl": "WPCRL",
             "civilappeal": "CA", "ca": "CA", "criminalappeal": "CRLA", "slpc": "SLPC", "slpcivil": "SLPC", "specialleavepetitioncivil": "SLPC",
             "specialleavepetitionc": "SLPC", "slpcrl": "SLPCRL", "specialleavepetitioncriminal": "SLPCRL", "specialleavepetitioncrl": "SLPCRL",
             "specialleavepetition": "SLP", "lpa": "LPA", "cwp": "CWP", "oa": "OA", "originalapplication": "OA", "ta": "TA",
             "transferapplication": "TA", "transferredapplication": "TA", "rsa": "RSA", "crmm": "CRMM", "crp": "CRP", "wria": "WRIA", "writa": "WRITA",
             "specialappeal": "SPLA", "spla": "SPLA", "wpa": "WPA", "wa": "WA", "reviewpetition": "RP"}
    return f"{alias.get(t, t.upper())}-{re.sub(r'\s', '', n)}-{y}"


def norm_case_string(s):
    """Normalise a metadata case number like 'W.P.(C)/10368/2026' into TYPE-NUM-YEAR, or None."""
    m = re.match(r"\s*([A-Za-z.()\s-]+?)\s*[/\s.-]*\s*(?:No\.?\s*)?(\d{1,6})\s*(?:/|of)\s*((?:19|20)\d{2})", s or "")
    return _norm_case(m.group(1), m.group(2), m.group(3)) if m else None


def extract(pdf_bytes, fitz):
    """Return a dict of automated candidate fields for one judgment PDF."""
    r = {"extractor": EXTRACTOR_VERSION}
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as e:  # noqa: BLE001  (a corrupt file is a result, not a crash)
        return dict(r, pdf_status="UNREADABLE", pdf_error=str(e)[:200])
    r["pdf_status"] = "OPENED"
    r["encrypted"] = bool(doc.is_encrypted)
    r["pages"] = doc.page_count
    texts = []
    for i in range(doc.page_count):
        try:
            texts.append(doc[i].get_text())
        except Exception:  # noqa: BLE001
            texts.append("")
    chars = [len(t.strip()) for t in texts]
    r["text_chars_total"] = sum(chars)
    r["pages_low_text"] = [i + 1 for i, c in enumerate(chars) if c < MIN_CHARS_PAGE]
    r["text_extraction"] = ("NO_TEXT_LAYER" if r["text_chars_total"] < 100 else
                            "PARTIAL_TEXT_LAYER" if len(r["pages_low_text"]) > max(1, doc.page_count // 4) else "TEXT_LAYER_OK")
    full = "\n".join(texts)
    flat = re.sub(r"\s+", " ", full)
    r["text_sha256"] = hashlib.sha256(full.encode("utf-8", "replace")).hexdigest()
    # case numbers, citations, dates
    cases = []
    for m in CASE_RE.finditer(flat[:8000]):
        k = _norm_case(m.group("type"), m.group("num"), m.group("year"))
        if k not in cases:
            cases.append(k)
    r["case_numbers_text_p1_3"] = cases[:60]
    cits = {}
    for n, rx in CIT_RE:
        found = sorted(set(re.sub(r"\s+", " ", m.group(0)).strip() for m in rx.finditer(flat)))
        if found:
            cits[n] = found[:40]
    r["citations"] = cits
    dates = []
    for m in DATE_LABEL.finditer(flat[:8000]):
        d = parse_date(m.group("d"))
        if d and d not in dates:
            dates.append(d)
    tail = flat[-4000:]
    for m in DATE_SC_TAIL.finditer(tail):
        d = parse_date(m.group("d"))
        if d and d not in dates:
            dates.append(d)
    r["dates_text"] = dates[:6]
    strong = []
    for m in DATE_STRONG.finditer(flat):
        d = parse_date(m.group("d"))
        if d and d not in strong:
            strong.append(d)
    tail2 = flat[-700:]   # signature block region
    for rx in (DATE_SC_TAIL, DATE_TAIL_WORD, DATE_TAIL_NUM):
        for m in rx.finditer(tail2):
            if re.search(r"(?:dated|dt\.?|of|on|w\.e\.f\.?|since|from)\s*[:\-]?\s*$", tail2[max(0, m.start() - 16):m.start()], re.I):
                continue  # a referenced date (an earlier order, notification or event), not the signature date
            d = parse_date(m.group("d").replace(".", " ").replace("/", " ").replace("-", " ") if rx is DATE_TAIL_NUM else m.group("d"))
            if d and d not in strong:
                strong.append(d)
    r["decision_date_candidates"] = strong[:6]
    # statutes with section mentions
    st = {}
    for n, rx in STAT_RE:
        ms = list(rx.finditer(flat))
        if not ms:
            continue
        secs = Counter()
        for m in ms[:200]:
            pre = flat[max(0, m.start() - 60):m.start()]
            sm = SEC_BEFORE.search(pre)
            if sm:
                for tok in re.findall(r"\d{1,3}[A-Z]?", sm.group(1))[:6]:
                    secs[tok] += 1
        st[n] = {"mentions": len(ms), "provisions": [s for s, _ in secs.most_common(12)]}
    r["statutes"] = st
    r["topics"] = {n: len(rx.findall(flat)) for n, rx in TOP_RE if rx.search(flat)}
    r["relevance_scores"] = {"direct": len(DIRECT.findall(flat)), "admin": len(ADMIN.findall(flat)), "general": len(GENERAL.findall(flat))}
    # outcome: search the final quarter (by characters) for the last outcome phrase
    q = flat[int(len(flat) * 0.70):]
    hits = []
    for n, rx in OUT_RE:
        for m in rx.finditer(q):
            hits.append((m.start(), n, q[max(0, m.start() - 120):m.end() + 60]))
    hits.sort()
    if hits:
        last_kinds = {h[1] for h in hits[-3:]}
        r["outcome_candidate"] = hits[-1][1]
        r["outcome_conflict"] = sorted(last_kinds) if len(last_kinds - {"set_aside_quashed", "disposed", "transferred"}) > 1 else []
        r["outcome_evidence"] = hits[-1][2].strip()[:300]
        pos = int(len(flat) * 0.70) + hits[-1][0]
        acc, page = 0, None
        for i, t in enumerate(texts):
            acc += len(re.sub(r"\s+", " ", t)) + 1
            if acc >= pos:
                page = i + 1
                break
        r["outcome_page"] = page
    else:
        r["outcome_candidate"] = "NOT_FOUND"
        r["outcome_conflict"], r["outcome_evidence"], r["outcome_page"] = [], "", None
    # candidate propositions with page and nearest paragraph number
    props = []
    for i, t in enumerate(texts):
        if len(props) >= 6:
            break
        for m in PROP_MARK.finditer(t):
            s0 = max(t.rfind(".", 0, m.start()) + 1, 0)
            e0 = t.find(".", m.end())
            sent = re.sub(r"\s+", " ", t[s0:(e0 + 1 if e0 != -1 else m.end() + 300)]).strip()
            if len(sent) < 60:
                continue
            paras = [p.group(1) for p in PARA_NUM.finditer(t[:m.start()])]
            props.append({"page": i + 1, "para": paras[-1] if paras else None, "text": sent[:500],
                          "status": "AUTOMATED_CANDIDATE_NOT_VERIFIED"})
            if len(props) >= 6:
                break
    r["propositions"] = props
    r["corrected_marker"] = bool(CORRECTED.search(flat[:3000]))
    r["first_page_excerpt"] = re.sub(r"\s+", " ", texts[0] if texts else "")[:400]
    return r


def classify_relevance(scores, text_status, title=""):
    """Rule-based relevance class (automated)."""
    d, a, g = scores.get("direct", 0), scores.get("admin", 0), scores.get("general", 0)
    if text_status == "NO_TEXT_LAYER":
        return "RELEVANCE_UNCERTAIN_REVIEW", "no text layer (OCR needed)"
    if d >= 3:
        return "DIRECT_MILITARY_LAW", f"direct military-law terms x{d}"
    if d >= 1 or a >= 3:
        return "MILITARY_ADMIN_SERVICE_PENSION", f"direct x{d}, service/pension/administration terms x{a}"
    if g >= 2 and a >= 1:
        return "GENERAL_LAW_POTENTIALLY_APPLICABLE", f"general-law doctrine terms x{g} with a service/defence context x{a}"
    if a >= 1 or g >= 2:
        return "RELEVANCE_UNCERTAIN_REVIEW", f"weak signals: admin x{a}, general x{g}"
    return "NOT_RELEVANT_CURRENT_SCOPE", "no military, service or general-law doctrine signal in the text layer"
