"""AUTH-LEDGER: append-only, hash-chained authentication ledger (stdlib; offline; no network; no runtime AI).

Layout under a ledger root (default: the AUTH-LEDGER package):
  frozen_inputs.json          sha256 pins of every historical file read (tools/pins.py)
  ledger/manifest.jsonl       one canonical JSON line per version; line N carries prev = sha256(line N-1); line 0 is GENESIS
  ledger/HEAD                 "<version> <sha256 of the last manifest line>"
  ledger/vNNNN.csv            immutable entry file of version NNNN (pinned by file_sha256 in its manifest line)
  decisions/D-vNNNN*.md       owner decision records; decisions/R-vNNNN*.md reviewer records (pinned in the manifest line)
  effective/vNNNN/            derived outputs (pinned by effective_sha256 in the manifest line)

What the mechanism does and does not establish (Fable review F-14): the chain is UNKEYED. It detects an edit, deletion,
reordering or replacement that is not followed by a consistent re-derivation of every later line and of HEAD. It cannot
stop a repository writer from re-deriving the whole chain. Detection of that rests on two further controls: the expected
HEAD is pinned in the test suite as well as in ledger/HEAD (a two-place change visible in review), and every version is
added by a reviewed PR. There are no cryptographic signatures; authority is the reviewed merge, and since AUTH-LEDGER-02 an
approved version is effective only after a BIND line whose git facts tools/binding.py verifies offline (APPROVAL_CONTROLS.md)."""
import json, posixpath, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import LOGICAL_PKG, PKG, LedgerError, read_csv, sha256_file, sha256_text  # noqa: E402
import rules_v1  # noqa: E402
import strength  # noqa: E402
import binding  # noqa: E402

SCHEMA = json.loads((PKG / "schema/ledger_entry.schema.json").read_text(encoding="utf-8"))
COLS = SCHEMA["required"]
LINE_KEYS = ["version", "prev", "date", "rule_version", "frozen_inputs_sha256", "file", "file_sha256", "decisions", "reviews", "effective_sha256", "note"]
SUBTYPE = {"PRIMARY_GAZETTE_ARCHIVAL_FACSIMILE": "HELD_PRIMARY_GAZETTE_FACSIMILE",
           "PRIMARY_GAZETTE_GOVERNMENT_HOSTED_SCAN": "HELD_PRIMARY_GAZETTE_GOVERNMENT_SCAN",
           "PRIMARY_OFFICIAL_COURT_COPY": "HELD_PRIMARY_OFFICIAL_COURT_COPY"}
# Class compatibility (Fable review F-01, F-07): publication types, copy-carrier prefixes, and extra requirements.
COMPAT = {
    "PRIMARY_GAZETTE_ARCHIVAL_FACSIMILE": {"pub": {"GAZETTE_NOTIFICATION", "SUBORDINATE_LEGISLATION", "STATUTE"}, "carrier": ("THIRD_PARTY_ARCHIVAL_FACSIMILE",)},
    "PRIMARY_GAZETTE_GOVERNMENT_HOSTED_SCAN": {"pub": {"GAZETTE_NOTIFICATION", "SUBORDINATE_LEGISLATION", "STATUTE"}, "carrier": ("GOVERNMENT_HOSTED",), "scan": True},
    "PRIMARY_OFFICIAL_COURT_COPY": {"pub": {"JUDICIAL"}, "carrier": ("ISSUING_AUTHORITY", "OFFICIAL_COURT_HOST")},
    "NON_PRIMARY_OFFICIAL_COURT_RENDITION": {"pub": {"JUDICIAL"}, "carrier": None},
    "NON_PRIMARY_PARLIAMENTARY_RECORD": {"pub": {"PARLIAMENTARY_RECORD"}, "carrier": None},
    "NON_PRIMARY_OFFICIAL_PUBLICATION_COPY": {"pub_not": {"JUDICIAL", "PARLIAMENTARY_RECORD"}, "carrier": None},
}
EVIDENCE_KINDS = {"L1", "L2", "L3", "L4", "L5", "L6", "WSB"}
KIND_FILES = {  # each evidence kind label is tied to its file family (re-review N-05)
    "L1": lambda p: p == "PILOT-01/registers/source_code_resolution_v3.csv",
    "L2": lambda p: p in ("ACQ-02/supplement_inventory.csv",) + strength.SNAPSHOTS,
    "L3": lambda p: strength._json_source(p),
    "L4": lambda p: p == "PILOT-01/registers/source_discovery_2026-11-22.csv",
    "L5": lambda p: p == "R23-VERIFY-01/registers/amendment_search_2026-11-22.csv",
    "L6": lambda p: p == "WS-A-STATUTORY/identity_transcription_register.csv",
    "WSB": lambda p: p == "WS-B-JUDGMENTS/tools/held_copies.csv",
}
DIGEST_EXCLUDE = {"decision_record_ref", "decision_record_sha256", "reviewer_ref", "reviewer_record_sha256"}
DATE = re.compile(r"\d{4}-\d{2}-\d{2}$")
# Letter boundaries, not word boundaries, so 'Fable5', 'claude_code' and 'GPT4' are caught (Fable F-09). This is
# deliberately over-inclusive: a person whose name contains one of these words (e.g. 'Claude') must be identified in
# decided_by by another form of their name. The list is a guard against agent self-approval, not an identity control.
AGENT = re.compile(r"(?i)(?<![a-z])(claude|fable|opus|sonnet|haiku|anthropic|gpt|chatgpt|openai|gemini|copilot|llm|ai|agent|assistant|bot|model)(?![a-z])")


def canonical_line(d):
    """Entry and genesis lines carry LINE_KEYS; a BIND line (AUTH-LEDGER-02) carries LINE_KEYS + ['binding']. Genesis is
    unchanged, so the committed chain and HEAD are unchanged."""
    keys = LINE_KEYS + ["binding"] if "binding" in d else LINE_KEYS
    if sorted(d) != sorted(keys):
        raise LedgerError(f"manifest line keys {sorted(d)} differ from the contract")
    return json.dumps({k: d[k] for k in keys}, sort_keys=False, separators=(",", ":"), ensure_ascii=True)


def entry_digest(e):
    """sha256 of the canonical entry content (every column except the four that reference the records themselves).
    Decision and review records must name this digest, so a pinned record covers exactly what was decided (F-03)."""
    return sha256_text(json.dumps({k: e[k] for k in COLS if k not in DIGEST_EXCLUDE}, sort_keys=True, ensure_ascii=True))


def read_manifest(root):
    """Verify the hash chain and HEAD; return the list of manifest dicts (index = version)."""
    p = Path(root) / "ledger/manifest.jsonl"
    raw = p.read_text(encoding="utf-8").split("\n")
    if raw[-1] != "":
        raise LedgerError("manifest.jsonl must end with a newline")
    lines, prev = [], "GENESIS"
    for i, s in enumerate(raw[:-1]):
        try:
            d = json.loads(s)
        except json.JSONDecodeError as e:
            raise LedgerError(f"manifest line {i}: not JSON ({e})")
        if canonical_line(d) != s:
            raise LedgerError(f"manifest line {i}: not in canonical form (edited by hand?)")
        for k in ("version", "rule_version"):  # bool is an int subclass and 1.0 == 1: both refused (Fable F-10)
            if type(d[k]) is not int:
                raise LedgerError(f"manifest line {i}: {k} must be an integer, not {d[k]!r}")
        try:
            import datetime
            if not (isinstance(d["date"], str) and DATE.match(d["date"])):
                raise ValueError
            datetime.date.fromisoformat(d["date"])
        except ValueError:
            raise LedgerError(f"manifest line {i}: date {d['date']!r} is not a valid YYYY-MM-DD date")
        if d["version"] != i:
            raise LedgerError(f"manifest line {i}: version {d['version']} out of order (lines deleted or reordered?)")
        if d["prev"] != prev:
            raise LedgerError(f"manifest line {i}: hash chain broken (prev {str(d['prev'])[:12]} != {prev[:12]})")
        if "binding" in d:
            if i == 0 or d["file"] is not None or d["file_sha256"] is not None or d["decisions"] or d["reviews"]:
                raise LedgerError(f"manifest line {i}: a BIND line carries no entry file and no records")
        elif i > 0 and d["file"] != f"ledger/v{i:04d}.csv":
            raise LedgerError(f"manifest line {i}: entry file must be ledger/v{i:04d}.csv, not {d['file']!r}")
        prev = sha256_text(s)
        lines.append(d)
    if not lines:
        raise LedgerError("manifest has no genesis line")
    head = (Path(root) / "ledger/HEAD").read_text(encoding="utf-8").strip()
    if head != f"{len(lines) - 1} {prev}":
        raise LedgerError(f"ledger/HEAD {head!r} does not match the manifest chain ({len(lines) - 1} {prev})")
    return lines


def head_value(root):
    return (Path(root) / "ledger/HEAD").read_text(encoding="utf-8").strip()


def unexpected_files(root, lines):
    """Files in ledger/ or decisions/ that no manifest line accounts for (F-12)."""
    root = Path(root)
    known = {"ledger/manifest.jsonl", "ledger/HEAD", "decisions/README.md"}
    for d in lines:
        if d["file"]:
            known.add(d["file"])
        known |= set(d["decisions"]) | set(d["reviews"])
    found = {str(p.relative_to(root)) for sub in ("ledger", "decisions") if (root / sub).is_dir() for p in (root / sub).rglob("*") if p.is_file()}
    return sorted(found - known)


def _parse_record(path):
    """key: value lines; duplicate keys are an error (an ambiguous record is never read in the approving sense)."""
    out = {}
    for n, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        m = re.match(r"^\s*([A-Za-z_]+)\s*:\s*(.*)$", line)  # keys are case- and indentation-insensitive (re-review N-04)
        if not m:
            continue
        k = m.group(1).lower()
        if k in out:
            raise LedgerError(f"{path.name}: key {k!r} appears more than once (line {n})")
        out[k] = m.group(2).strip()
    return out


def _person(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def _safe_ref(ref, prefix):
    if not ref or posixpath.normpath(ref) != ref or not ref.startswith(prefix) or ".." in ref.split("/"):
        raise LedgerError(f"record reference {ref!r} must be a normalised path under {prefix}")
    return ref


def _check_record(root, line, kind, ref, sha_declared, entry):
    """Decision (D-) or review (R-) record: committed file under decisions/, hash equal to the entry's declared hash AND to
    the manifest pin, naming this exact entry id, sha256 and content digest, for this exact version."""
    if not ref:
        raise LedgerError(f"{entry['entry_id']}: missing {kind} record reference")
    _safe_ref(ref, "decisions/")
    stem = Path(ref).name
    want = "D-" if kind == "decision" else "R-"
    if not (stem.startswith(want + f"v{int(entry['entry_version']):04d}") and stem.endswith(".md")):
        raise LedgerError(f"{entry['entry_id']}: {kind} record must be decisions/{want}v{entry['entry_version']}*.md")
    f = Path(root) / ref
    if not f.is_file():
        raise LedgerError(f"{entry['entry_id']}: {kind} record {ref} is not a committed file")
    h = sha256_file(f)
    pins = line["decisions"] if kind == "decision" else line["reviews"]
    if h != sha_declared or pins.get(ref) != h:
        raise LedgerError(f"{entry['entry_id']}: {kind} record {ref} hash does not match the entry and the manifest pin")
    rec = _parse_record(f)
    idkey = "decision_id" if kind == "decision" else "review_id"
    if rec.get(idkey) != stem[:-3]:
        raise LedgerError(f"{entry['entry_id']}: {kind} record {idkey} must equal its file name")
    items = [x.split("=", 1) for x in rec.get("entries", "").split(";") if "=" in x]
    keys = [k.strip() for k, _ in items]
    if len(keys) != len(set(keys)):
        raise LedgerError(f"{entry['entry_id']}: {kind} record lists an entry id more than once")
    pairs = {k.strip(): v.strip() for k, v in items}
    if pairs.get(entry["entry_id"]) != f"{entry['sha256']}:{entry_digest(entry)}":
        raise LedgerError(f"{entry['entry_id']}: {kind} record does not name this entry with this sha256 and content digest")
    if rec.get("ledger_version") != entry["entry_version"]:
        raise LedgerError(f"{entry['entry_id']}: {kind} record is for ledger version {rec.get('ledger_version')!r}")
    import datetime
    try:
        if not DATE.match(rec.get("date", "")):
            raise ValueError
        datetime.date.fromisoformat(rec["date"])
    except (ValueError, KeyError):
        raise LedgerError(f"{entry['entry_id']}: {kind} record date must be a valid YYYY-MM-DD date")
    if rec["date"] > line["date"]:
        raise LedgerError(f"{entry['entry_id']}: {kind} record is dated after its manifest line ({rec['date']} > {line['date']})")
    want_scope = "AUTHENTICATION_PROVENANCE_ONLY" if kind == "decision" else "TECHNICAL_AND_EVIDENCE_REVIEW"
    if rec.get("scope") != want_scope or rec.get("legal_approval") != "NOT_GIVEN":
        raise LedgerError(f"{entry['entry_id']}: {kind} record must state scope: {want_scope} and legal_approval: NOT_GIVEN "
                          f"(technical review, evidence authentication, owner approval and legal approval stay distinct)")
    if kind == "decision":
        if rec.get("decision") != entry["owner_decision"]:
            raise LedgerError(f"{entry['entry_id']}: decision record says {rec.get('decision')!r}, entry says {entry['owner_decision']!r}")
        if not re.search(r"[A-Za-z]{2}", rec.get("decided_by", "")):
            raise LedgerError(f"{entry['entry_id']}: decision record lacks decided_by")
        if AGENT.search(rec["decided_by"]):
            raise LedgerError(f"{entry['entry_id']}: decided_by names an AI model or agent; an agent's statement is never owner approval")
        return rec
    verdict = rec.get("verdict")
    if verdict not in ("ACCEPT", "ACCEPT_WITH_CONDITIONS"):
        raise LedgerError(f"{entry['entry_id']}: review verdict {verdict!r} does not support approval")
    if verdict == "ACCEPT_WITH_CONDITIONS" and rec.get("conditions_status") != "DISCHARGED":
        raise LedgerError(f"{entry['entry_id']}: ACCEPT_WITH_CONDITIONS requires conditions_status: DISCHARGED")
    if not re.search(r"[A-Za-z]{2}", rec.get("reviewer", "")):
        raise LedgerError(f"{entry['entry_id']}: review record lacks reviewer")
    return rec


def schema_check(e, header):
    if header != COLS:
        raise LedgerError(f"version file header must equal the schema columns exactly (got {header})")
    errs = [f"missing value for {k}" for k in COLS if e.get(k) is None]
    for k, spec in SCHEMA["properties"].items():
        v = e.get(k) or ""
        if "enum" in spec and v not in spec["enum"]:
            errs.append(f"{k}={v!r} not allowed")
        if "pattern" in spec and not re.fullmatch(spec["pattern"], v):
            errs.append(f"{k}={v!r} does not match {spec['pattern']}")
    rule = SCHEMA["x-type-rules"].get(e.get("entry_type"), {})
    errs += [f"{k} must be set for {e.get('entry_type')}" for k in rule.get("nonempty", []) if not e.get(k)]
    errs += [f"{k} must be empty for {e.get('entry_type')}" for k in rule.get("empty", []) if e.get(k)]
    if e.get("entry_id", "")[4:8] != e.get("entry_version"):
        errs.append("entry_id version part differs from entry_version")
    if errs:
        raise LedgerError(f"{e.get('entry_id', '?')}: schema: " + "; ".join(errs))


class Context:
    """Frozen facts the validator needs (all from pinned files)."""
    def __init__(self, held, baseline, copies, master):
        self.held, self.baseline, self.copies, self.master = held, baseline, copies, master


def _association(e, ctx):
    copy = ctx.copies.get(e["sha256"])
    if copy is None or copy["copy_id"] != e["copy_id"] or copy["source_id"] != e["source_id"]:
        raise LedgerError(f"{e['entry_id']}: copy {e['copy_id']} / source {e['source_id']} is not the Cycle 5 copy of this sha256")
    if not ctx.held.get(e["sha256"]):
        raise LedgerError(f"{e['entry_id']}: sha256 not in the held-source index")
    return copy


def resolve_refs(e, ctx):
    """Every evidence reference is 'KIND:path#key' with KIND in a fixed vocabulary, resolves to exactly one record, and
    concerns THIS sha256: its own sha256 field equals the key, or (archive snapshots) its md5 and size equal the copy's."""
    facts = {r["sha256"]: r for r in read_csv(PKG / "evidence/copy_facts.csv")}.get(e["sha256"])
    refs = [y for y in e["evidence_refs"].split("; ") if y]
    for x in refs:
        kind, sep, ref = x.partition(":")
        if not sep or kind not in EVIDENCE_KINDS:
            raise LedgerError(f"{e['entry_id']}: evidence reference {x!r} is not KIND:path#key with KIND in {sorted(EVIDENCE_KINDS)}")
        path, rec = strength.resolve(ref)
        if not KIND_FILES[kind](path):
            raise LedgerError(f"{e['entry_id']}: evidence kind {kind} does not belong to file {path}")
        own = ""
        for col in ("sha256", "official_sha256", "downloaded_sha256", "file_sha256", "document_sha256"):
            if isinstance(rec, dict) and (rec.get(col) or "").strip():
                own = rec[col].strip()[:64]
                break
        if path in strength.SNAPSHOTS:
            if not facts or rec.get("md5") != facts["md5"] or str(rec.get("size")) != facts["bytes"]:
                raise LedgerError(f"{e['entry_id']}: snapshot reference {ref} does not match this copy's md5 and size")
        elif own != e["sha256"]:
            raise LedgerError(f"{e['entry_id']}: evidence reference {ref} does not concern this sha256")
    return refs


def _evidence_checks(e, ctx, cls):
    copy = _association(e, ctx)
    refs = resolve_refs(e, ctx)
    if not any(x.split(":", 1)[1] == e["first_class_record_ref"] for x in refs):
        raise LedgerError(f"{e['entry_id']}: the first-class record must also be listed among evidence_refs")
    kind, st, url = strength.first_class(e["first_class_record_ref"], e["sha256"], cls)
    if e["official_locator_recorded"] != url:
        raise LedgerError(f"{e['entry_id']}: official_locator_recorded must equal the first-class record's URL ({url})")
    m = ctx.master[e["source_id"]]
    pub = m["publication_type"]
    court = pub == "JUDICIAL"
    c = COMPAT.get(cls)
    if c is None:
        raise LedgerError(f"{e['entry_id']}: class {cls} has no compatibility rule")
    if ("pub" in c and pub not in c["pub"]) or ("pub_not" in c and pub in c["pub_not"]):
        raise LedgerError(f"{e['entry_id']}: class {cls} does not fit publication type {pub}")
    carrier = copy["copy_carrier_provenance"]
    if c["carrier"] is not None and not carrier.startswith(c["carrier"]):
        raise LedgerError(f"{e['entry_id']}: class {cls} does not fit copy carrier {carrier.split(' ')[0]}")
    if e["carrier"] != carrier:
        raise LedgerError(f"{e['entry_id']}: carrier must equal the Cycle 5 copy carrier")
    if cls in rules_v1.PRIMARY_CLASSES:
        comp = m["completeness_status"].upper()
        if "INCOMPLETE" in comp or "EXTRACT" in comp:
            raise LedgerError(f"{e['entry_id']}: primary class on an incomplete or extract copy ({m['completeness_status'][:60]})")
        if c.get("scan") and not copy["text_layer_class"].startswith("SCANNED"):
            raise LedgerError(f"{e['entry_id']}: class {cls} needs a scanned copy (text layer class {copy['text_layer_class']})")
        if not court:
            issue = strength.fidelity_issue(e["sha256"])
            if issue:
                raise LedgerError(f"{e['entry_id']}: primary class fails copy fidelity: {issue}")
    p1 = {r["sha256"]: r for r in read_csv(PKG / "evidence/copy_facts.csv")}.get(e["sha256"], {}).get("p1_text_excerpt", "")
    ids = [y for y in e["identity_refs"].split("; ") if y]
    for y in ids:
        if y.startswith("T:"):
            if y != f"T:AUTH-LEDGER/evidence/copy_facts.csv#{e['copy_id']}":
                raise LedgerError(f"{e['entry_id']}: text-identity reference must name this copy's row in the pinned evidence/copy_facts.csv")
            strength.resolve(y[2:])
    strength.identity_ok(ids, e["sha256"], court, m["title"], p1)
    bad = strength.contradiction(url, e["sha256"])
    if bad:
        raise LedgerError(f"{e['entry_id']}: locator {url} is also recorded with sha256 {bad[0][:12]} (contradiction)")
    return kind


def register_row(e, ctx, kind):
    return {"sha256": e["sha256"], "document_identity": e["document_identity"], "issuer_or_authority": ctx.master[e["source_id"]]["authority"],
            "held_paths": "; ".join(sorted(ctx.held[e["sha256"]])), "carrier": e["carrier"], "official_locator_recorded": e["official_locator_recorded"],
            "provenance_references": e["evidence_refs"], "provenance_evidence": f"AUTH-LEDGER {e['entry_id']} ({kind})",
            "authentication_state": e["proposed_authentication_state"], "effective_source_class": e["proposed_class"],
            "limitations": e["limitations"], "rationale": e["justification"], "origin": f"AUTH-LEDGER {e['entry_id']}"}


def _record_set_checks(root, line, entries):
    """Every pinned record is used by an entry of this version, and every entry a record names exists in this version and
    cites that record: no orphan, extra, duplicated or cross-version approvals (AUTH-LEDGER-02)."""
    by_id = {e["entry_id"]: e for e in entries}
    for kind, pins, col in (("decision", line["decisions"], "decision_record_ref"), ("review", line["reviews"], "reviewer_ref")):
        named = {}
        for ref in pins:
            if not any(e[col] == ref for e in entries):
                raise LedgerError(f"version {line['version']}: pinned {kind} record {ref} is cited by no entry")
            rec = _parse_record(Path(root) / ref)
            for x in rec.get("entries", "").split(";"):
                eid = x.split("=", 1)[0].strip()
                if not eid:
                    continue
                if eid not in by_id or by_id[eid][col] != ref:
                    raise LedgerError(f"version {line['version']}: {kind} record {ref} names {eid}, which is not an entry of this version citing it")
                if eid in named:
                    raise LedgerError(f"version {line['version']}: {eid} is named by two {kind} records ({named[eid]}, {ref})")
                named[eid] = ref


def _apply_version(root, ctx, line, st):
    """Validate one entry version and apply it to the state st (eff, live, by_sha, seen_ids, transitions, withdrawn)."""
    eff, live, by_sha, seen_ids, transitions, withdrawn = (st[k] for k in ("eff", "live", "by_sha", "seen_ids", "transitions", "withdrawn"))
    for k in list(line["decisions"]) + list(line["reviews"]):
        _safe_ref(k, "decisions/")
    if set(line["decisions"]) & set(line["reviews"]):
        raise LedgerError(f"version {line['version']}: a file cannot be both a decision record and a review record")
    f = Path(root) / line["file"]
    if not f.is_file() or sha256_file(f) != line["file_sha256"]:
        raise LedgerError(f"version {line['version']}: entry file missing or modified after it was recorded")
    for k, h in list(line["decisions"].items()) + list(line["reviews"].items()):
        if not (Path(root) / k).is_file() or sha256_file(Path(root) / k) != h:
            raise LedgerError(f"version {line['version']}: pinned record {k} missing or modified")
    with open(f, newline="", encoding="utf-8") as fh:
        header = fh.readline().rstrip("\r\n").split(",")
    if header != COLS:
        raise LedgerError(f"version {line['version']}: version file header must equal the schema columns exactly (got {header})")
    entries = read_csv(f)
    ids = [e.get("entry_id") for e in entries]
    dup = sorted({i for i in ids if ids.count(i) > 1} | {i for i in ids if i in seen_ids})
    if dup:
        raise LedgerError(f"version {line['version']}: duplicate entry id(s) {dup}")
    _record_set_checks(root, line, entries)
    for e in entries:
        schema_check(e, header)
        if e["entry_version"] != f"{line['version']:04d}":
            raise LedgerError(f"{e['entry_id']}: entry_version {e['entry_version']} in version file {line['version']}")
        seen_ids.add(e["entry_id"])
        _association(e, ctx)  # every entry type names the real copy and source of its sha256 (F-09)
        dec = _check_record(root, line, "decision", e["decision_record_ref"], e["decision_record_sha256"], e)
        if e["owner_decision"] != "APPROVED":
            transitions.append({"version": line["version"], "entry_id": e["entry_id"], "entry_type": e["entry_type"], "sha256": e["sha256"],
                                "effect": f"NONE (owner_decision {e['owner_decision']})", "before": "", "after": ""})
            continue
        rev = _check_record(root, line, "review", e["reviewer_ref"], e["reviewer_record_sha256"], e)
        if e["decision_record_ref"] == e["reviewer_ref"] or _person(dec["decided_by"]) == _person(rev["reviewer"]):
            raise LedgerError(f"{e['entry_id']}: decision and review must be separate records by different persons (F-04)")
        if dec["date"] < rev["date"]:
            raise LedgerError(f"{e['entry_id']}: the owner decision ({dec['date']}) predates the independent review ({rev['date']})")
        s = e["sha256"]
        before = f"{eff[s]['authentication_state']}/{eff[s]['effective_source_class']}" if s in eff else "NO_ROW"
        if e["entry_type"] == "ADD":
            if s in by_sha:
                raise LedgerError(f"{e['entry_id']}: a live row already exists for this sha256 ({by_sha[s]}); use CORRECTION")
            if e["proposed_authentication_state"] != "PROVENANCE_DOCUMENTED" or e["proposed_class"] == "AUTHENTICATION_PENDING":
                raise LedgerError(f"{e['entry_id']}: an ADD records documented provenance only")
            eff[s] = register_row(e, ctx, _evidence_checks(e, ctx, e["proposed_class"]))
            live[e["entry_id"]] = e
            by_sha[s] = e["entry_id"]
        else:
            tgt = live.get(e["target_entry_id"])
            if tgt is None or by_sha.get(s) != e["target_entry_id"]:
                raise LedgerError(f"{e['entry_id']}: target {e['target_entry_id']} is not the live row for this sha256")
            if e["entry_type"] == "WITHDRAW" and tgt.get("entry_type") in ("WITHDRAW", "CORRECTION"):
                raise LedgerError(f"{e['entry_id']}: a WITHDRAW may target only an ADD or a BASELINE row; revert a "
                                  f"{tgt.get('entry_type')} with a new CORRECTION (F-09)")
            if e["entry_type"] == "CORRECTION":
                if e["proposed_authentication_state"] == "PROVENANCE_DOCUMENTED":
                    if e["proposed_class"] == "AUTHENTICATION_PENDING":
                        raise LedgerError(f"{e['entry_id']}: documented state with a pending class")
                    eff[s] = register_row(e, ctx, _evidence_checks(e, ctx, e["proposed_class"]))
                else:
                    if e["proposed_class"] != "AUTHENTICATION_PENDING":
                        raise LedgerError(f"{e['entry_id']}: a pending correction must carry class AUTHENTICATION_PENDING")
                    resolve_refs(e, ctx)
                    base = eff.get(s) or {"sha256": s, "held_paths": "; ".join(sorted(ctx.held.get(s, [])))}
                    eff[s] = dict(base, authentication_state="AUTHENTICATION_PENDING", effective_source_class="AUTHENTICATION_PENDING",
                                  rationale=f"corrected by {e['entry_id']}: {e['justification']}", origin=f"AUTH-LEDGER {e['entry_id']}")
                del live[e["target_entry_id"]]
                live[e["entry_id"]] = e
                by_sha[s] = e["entry_id"]
            else:  # WITHDRAW of an ADD or a BASELINE row: its effect ends; the record stays
                del live[e["target_entry_id"]]
                by_sha.pop(s, None)
                if e["resulting_state"] == "AUTHENTICATION_PENDING":
                    eff[s] = dict(eff.get(s) or {"sha256": s, "held_paths": "; ".join(sorted(ctx.held.get(s, [])))},
                                  authentication_state="AUTHENTICATION_PENDING", effective_source_class="AUTHENTICATION_PENDING",
                                  rationale=f"withdrawn by {e['entry_id']} ({e['withdrawal_reason']})", origin=f"AUTH-LEDGER {e['entry_id']}")
                    live[e["entry_id"]] = e  # the pending state is live: it can be CORRECTED, not withdrawn again
                    by_sha[s] = e["entry_id"]
                else:
                    eff.pop(s, None)
                withdrawn.append({"version": line["version"], "entry_id": e["entry_id"], "target_entry_id": e["target_entry_id"], "sha256": s,
                                  "withdrawal_reason": e["withdrawal_reason"], "resulting_state": e["resulting_state"] or "NO_ROW"})
        after = f"{eff[s]['authentication_state']}/{eff[s]['effective_source_class']}" if s in eff else "NO_ROW"
        transitions.append({"version": line["version"], "entry_id": e["entry_id"], "entry_type": e["entry_type"], "sha256": s,
                            "effect": "APPLIED", "before": before, "after": after})


COMMITTED_PACKAGE = LOGICAL_PKG  # the authoritative ledger package (logical path); tests may point it at a temporary layout


def is_committed_package(root):
    import os
    return Path(os.path.abspath(root)) == Path(COMMITTED_PACKAGE) or Path(root).resolve() == Path(COMMITTED_PACKAGE).resolve()


def check_committed_layout(root):
    """Run the package-layout check (no symlink, a real committed directory) before ANY file of the committed ledger is
    read; a no-op for synthetic roots. Called first by reader.effective_state, auth_ledger.verify and apply_ledger."""
    if is_committed_package(root):
        binding.check_package_layout(COMMITTED_PACKAGE)
        return True
    return False


def apply_ledger(root, ctx, as_of=None, require_binding=True):
    """Validate every version up to as_of and return (effective_register, transitions, withdrawn, lines).

    With require_binding (the default, and the only mode the CLI uses) an entry version is fully validated but STAGED:
    its effect appears in transitions as PENDING_REPOSITORY_BINDING and the effective register is unchanged until the next
    manifest line is a BIND line that binding.verify() accepts against local git history. Only the last line may be an
    unbound entry version. require_binding=False is the AUTH-LEDGER-01 semantics, kept for synthetic evidence-rule tests."""
    import copy as _copy
    committed = check_committed_layout(root)  # a symlinked package is never read as the authoritative ledger (C8, C-02)
    lines = read_manifest(root)
    as_of = len(lines) - 1 if as_of is None else as_of
    if not 0 <= as_of < len(lines):
        raise LedgerError(f"--as-of {as_of} outside 0..{len(lines) - 1}")
    frozen_sha = sha256_file(Path(root) / "frozen_inputs.json")
    st = {"eff": {s: dict(r, origin="CALIBRATION-02 baseline") for s, r in ctx.baseline.items()},
          "live": {"BASELINE:" + s: {"sha256": s, "entry_type": "BASELINE"} for s in ctx.baseline},
          "by_sha": {s: "BASELINE:" + s for s in ctx.baseline}, "seen_ids": set(), "transitions": [], "withdrawn": []}
    pending = None
    for line in lines[: as_of + 1]:
        if line["rule_version"] != 1:
            raise LedgerError(f"version {line['version']}: rule version {line['rule_version']} is not implemented (only rule 1)")
        if line["frozen_inputs_sha256"] != frozen_sha:
            raise LedgerError(f"version {line['version']}: frozen_inputs.json changed since this version was recorded")
        if line["version"] == 0:
            if line["file"] is not None or line["decisions"] or line["reviews"] or "binding" in line:
                raise LedgerError("genesis line must carry no entries, decisions, reviews or binding")
            continue
        if "binding" in line:
            if not require_binding:
                raise LedgerError(f"version {line['version']}: BIND lines are evaluated only with require_binding")
            if pending is None or pending[0] != line["version"] - 1:
                raise LedgerError(f"version {line['version']}: BIND line binds nothing pending")
            # the repository that contains the logical package path (Fable R-02, C-01, C-02); None only for synthetic roots
            pinned_top = Path(COMMITTED_PACKAGE).parents[2] if committed else None
            report = binding.verify(root, line, lines, canonical_line, expected_top=pinned_top)
            st = pending[1]
            for t in st["transitions"]:
                if t["version"] == pending[0]:
                    t["bound_by"] = report["bound_by"]
                    t["binding_assurance"] = f"git topology {report['git']}; GitHub review {report['github_review']}"
            pending = None
            continue
        if pending is not None:
            raise LedgerError(f"version {line['version']}: entry version appended before version {pending[0]} was bound")
        if require_binding:
            staged = _copy.deepcopy(st)
            _apply_version(root, ctx, line, staged)
            pending = (line["version"], staged)
        else:
            _apply_version(root, ctx, line, st)
    if pending is not None:  # the last version awaits its BIND line: report, do not apply
        log = [dict(t, effect="PENDING_REPOSITORY_BINDING") if t["effect"] == "APPLIED" else dict(t)
               for t in pending[1]["transitions"] if t["version"] == pending[0]]
        return st["eff"], st["transitions"] + log, st["withdrawn"], lines[: as_of + 1]
    return st["eff"], st["transitions"], st["withdrawn"], lines[: as_of + 1]
