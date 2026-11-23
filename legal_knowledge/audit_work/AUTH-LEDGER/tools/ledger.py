"""AUTH-LEDGER: immutable, hash-chained authentication ledger (stdlib; offline; no network; no runtime AI).

Layout under a ledger root (default: the AUTH-LEDGER package):
  frozen_inputs.json          sha256 pins of every historical file read (tools/pins.py)
  ledger/manifest.jsonl       one JSON line per version; line N carries prev = sha256(line N-1 bytes); line 0 is GENESIS
  ledger/HEAD                 "<version> <sha256 of the last manifest line>"
  ledger/vNNNN.csv            immutable entry file of version NNNN (pinned by file_sha256 in its manifest line)
  decisions/*.md              committed owner decision records and reviewer reports (pinned in the manifest line that uses them)
  effective/vNNNN/            derived outputs (pinned by effective_sha256 in the manifest line)
Authority model: the ledger proves integrity (nothing silently edited, reordered or dropped) and completeness (every
approval has a hash-pinned decision record and reviewer record naming the exact entry and sha256). It does not
contain cryptographic signatures: authority comes from the reviewed merge of the PR that adds a version, and the
expected HEAD is also pinned in the test suite, so any ledger change is a visible two-place change."""
import json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import PKG, LedgerError, read_csv, sha256_file, sha256_text  # noqa: E402
import rules_v1  # noqa: E402
import strength  # noqa: E402

SCHEMA = json.loads((PKG / "schema/ledger_entry.schema.json").read_text(encoding="utf-8"))
COLS = SCHEMA["required"]
LINE_KEYS = ["version", "prev", "date", "rule_version", "frozen_inputs_sha256", "file", "file_sha256", "decisions", "reviews", "effective_sha256", "note"]
SUBTYPE = {"PRIMARY_GAZETTE_ARCHIVAL_FACSIMILE": "HELD_PRIMARY_GAZETTE_FACSIMILE",
           "PRIMARY_GAZETTE_GOVERNMENT_HOSTED_SCAN": "HELD_PRIMARY_GAZETTE_GOVERNMENT_SCAN",
           "PRIMARY_OFFICIAL_COURT_COPY": "HELD_PRIMARY_OFFICIAL_COURT_COPY"}


def canonical_line(d):
    if sorted(d) != sorted(LINE_KEYS):
        raise LedgerError(f"manifest line keys {sorted(d)} differ from the contract")
    return json.dumps({k: d[k] for k in LINE_KEYS}, sort_keys=False, separators=(",", ":"), ensure_ascii=True)


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
        if d["version"] != i:
            raise LedgerError(f"manifest line {i}: version {d['version']} out of order (lines deleted or reordered?)")
        if d["prev"] != prev:
            raise LedgerError(f"manifest line {i}: hash chain broken (prev {d['prev'][:12]} != {prev[:12]})")
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


def _parse_record(path):
    out = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        m = re.match(r"^([a-z_]+):\s*(.*)$", line)
        if m and m.group(1) not in out:
            out[m.group(1)] = m.group(2).strip()
    return out


def _check_record(root, line, kind, ref, sha_declared, entry):
    """Decision or review record: committed file, hash equal to the entry's declared hash AND to the manifest line's pin,
    naming this exact entry and sha256 for this exact version."""
    if not ref:
        raise LedgerError(f"{entry['entry_id']}: missing {kind} record reference")
    f = Path(root) / ref
    if not ref.startswith("decisions/") or not f.is_file():
        raise LedgerError(f"{entry['entry_id']}: {kind} record {ref!r} is not a committed file under decisions/")
    h = sha256_file(f)
    pins = line["decisions"] if kind == "decision" else line["reviews"]
    if h != sha_declared or pins.get(ref) != h:
        raise LedgerError(f"{entry['entry_id']}: {kind} record {ref} hash does not match the entry and the manifest pin")
    rec = _parse_record(f)
    items = [x.split("=", 1) for x in rec.get("entries", "").split(";") if "=" in x]
    keys = [k.strip() for k, _ in items]
    if len(keys) != len(set(keys)):
        raise LedgerError(f"{entry['entry_id']}: {kind} record lists an entry id more than once")
    pairs = {k.strip(): v.strip() for k, v in items}
    if pairs.get(entry["entry_id"]) != entry["sha256"]:
        raise LedgerError(f"{entry['entry_id']}: {kind} record does not name this entry with this sha256")
    if rec.get("ledger_version") != entry["entry_version"]:
        raise LedgerError(f"{entry['entry_id']}: {kind} record is for ledger version {rec.get('ledger_version')!r}")
    if kind == "decision" and rec.get("decision") != entry["owner_decision"]:
        raise LedgerError(f"{entry['entry_id']}: decision record says {rec.get('decision')!r}, entry says {entry['owner_decision']!r}")
    if kind == "review" and rec.get("verdict") not in ("ACCEPT", "ACCEPT_WITH_CONDITIONS"):
        raise LedgerError(f"{entry['entry_id']}: review verdict {rec.get('verdict')!r} does not support approval")
    for k in ("decided_by", "date") if kind == "decision" else ("reviewer", "date"):
        if not rec.get(k):
            raise LedgerError(f"{entry['entry_id']}: {kind} record lacks {k}")


def schema_check(e):
    errs = [f"missing column {k}" for k in COLS if k not in e]
    for k, spec in SCHEMA["properties"].items():
        v = e.get(k, "")
        if "enum" in spec and v not in spec["enum"]:
            errs.append(f"{k}={v!r} not allowed")
        if "pattern" in spec and not re.fullmatch(spec["pattern"], v):
            errs.append(f"{k}={v!r} does not match {spec['pattern']}")
    rule = SCHEMA["x-type-rules"].get(e.get("entry_type"), {})
    errs += [f"{k} must be set for {e.get('entry_type')}" for k in rule.get("nonempty", []) if not e.get(k)]
    errs += [f"{k} must be empty for {e.get('entry_type')}" for k in rule.get("empty", []) if e.get(k)]
    if errs:
        raise LedgerError(f"{e.get('entry_id', '?')}: schema: " + "; ".join(errs))


class Context:
    """Frozen facts the validator needs (all from pinned files)."""
    def __init__(self, held, baseline, copies, master):
        self.held, self.baseline, self.copies, self.master = held, baseline, copies, master


def _evidence_checks(e, ctx, cls):
    copy = ctx.copies.get(e["sha256"])
    if copy is None or copy["copy_id"] != e["copy_id"] or copy["source_id"] != e["source_id"]:
        raise LedgerError(f"{e['entry_id']}: copy {e['copy_id']} / source {e['source_id']} is not the Cycle 5 copy of this sha256")
    if not ctx.held.get(e["sha256"]):
        raise LedgerError(f"{e['entry_id']}: sha256 not in the held-source index")
    resolve_refs(e)
    kind, st, url = strength.first_class(e["first_class_record_ref"], e["sha256"])
    m = ctx.master[e["source_id"]]
    court = m["publication_type"] == "JUDICIAL"
    p1 = {r["sha256"]: r for r in read_csv(PKG / "evidence/copy_facts.csv")}.get(e["sha256"], {}).get("p1_text_excerpt", "")
    strength.identity_ok([y for y in e["identity_refs"].split("; ") if y], e["sha256"], court, m["title"], p1)
    if cls in rules_v1.PRIMARY_CLASSES:
        if court != (cls == "PRIMARY_OFFICIAL_COURT_COPY"):
            raise LedgerError(f"{e['entry_id']}: class {cls} does not fit publication type {m['publication_type']}")
        if court and copy["copy_carrier_provenance"].startswith("UNKNOWN"):
            raise LedgerError(f"{e['entry_id']}: primary court class on a copy whose carrier is UNKNOWN")
        if not court:
            issue = strength.fidelity_issue(e["sha256"])
            if issue:
                raise LedgerError(f"{e['entry_id']}: primary class fails copy fidelity: {issue}")
    bad = strength.contradiction(url, e["sha256"])
    if bad:
        raise LedgerError(f"{e['entry_id']}: locator {url} is also recorded with sha256 {bad[0][:12]} (contradiction)")
    return kind


def resolve_refs(e):
    """Every evidence reference is 'KIND:path#key' and must resolve to exactly one record."""
    for x in [y for y in e["evidence_refs"].split("; ") if y]:
        kind, sep, ref = x.partition(":")
        if not sep or not re.fullmatch(r"[A-Za-z0-9]+", kind):
            raise LedgerError(f"{e['entry_id']}: evidence reference {x!r} is not KIND:path#key")
        strength.resolve(ref)


def register_row(e, ctx, kind):
    return {"sha256": e["sha256"], "document_identity": e["document_identity"], "issuer_or_authority": ctx.master[e["source_id"]]["authority"],
            "held_paths": "; ".join(sorted(ctx.held[e["sha256"]])), "carrier": e["carrier"], "official_locator_recorded": e["official_locator_recorded"],
            "provenance_references": e["evidence_refs"], "provenance_evidence": f"AUTH-LEDGER {e['entry_id']} ({kind})",
            "authentication_state": e["proposed_authentication_state"], "effective_source_class": e["proposed_class"],
            "limitations": e["limitations"], "rationale": e["justification"]}


def apply_ledger(root, ctx, as_of=None):
    """Validate every version up to as_of and return (effective_register, transitions, withdrawn, lines)."""
    lines = read_manifest(root)
    as_of = len(lines) - 1 if as_of is None else as_of
    if not 0 <= as_of < len(lines):
        raise LedgerError(f"--as-of {as_of} outside 0..{len(lines) - 1}")
    frozen_sha = sha256_file(Path(root) / "frozen_inputs.json")
    eff = {s: dict(r) for s, r in ctx.baseline.items()}
    live = {"BASELINE:" + s: {"sha256": s, "entry_type": "BASELINE"} for s in ctx.baseline}  # target id -> entry
    by_sha = {s: "BASELINE:" + s for s in ctx.baseline}
    seen_ids, transitions, withdrawn = set(), [], []
    for line in lines[: as_of + 1]:
        if line["rule_version"] != 1:
            raise LedgerError(f"version {line['version']}: rule version {line['rule_version']} is not implemented (only rule 1)")
        if line["frozen_inputs_sha256"] != frozen_sha:
            raise LedgerError(f"version {line['version']}: frozen_inputs.json changed since this version was recorded")
        if line["version"] == 0:
            if line["file"] is not None or line["decisions"] or line["reviews"]:
                raise LedgerError("genesis line must carry no entries, decisions or reviews")
            continue
        f = Path(root) / (line["file"] or "")
        if not line["file"] or not f.is_file() or sha256_file(f) != line["file_sha256"]:
            raise LedgerError(f"version {line['version']}: entry file missing or modified after it was recorded")
        for k, h in list(line["decisions"].items()) + list(line["reviews"].items()):
            if not (Path(root) / k).is_file() or sha256_file(Path(root) / k) != h:
                raise LedgerError(f"version {line['version']}: pinned record {k} missing or modified")
        entries = read_csv(f)
        ids = [e.get("entry_id") for e in entries]
        dup = sorted({i for i in ids if ids.count(i) > 1} | {i for i in ids if i in seen_ids})
        if dup:
            raise LedgerError(f"version {line['version']}: duplicate entry id(s) {dup}")
        for e in entries:
            schema_check(e)
            if e["entry_version"] != f"{line['version']:04d}":
                raise LedgerError(f"{e['entry_id']}: entry_version {e['entry_version']} in version file {line['version']}")
            if e["entry_id"] in seen_ids:
                raise LedgerError(f"{e['entry_id']}: duplicate entry id")
            seen_ids.add(e["entry_id"])
            if e["owner_decision"] != "APPROVED":
                transitions.append({"version": line["version"], "entry_id": e["entry_id"], "entry_type": e["entry_type"], "sha256": e["sha256"],
                                    "effect": f"NONE (owner_decision {e['owner_decision']})", "before": "", "after": ""})
                continue
            _check_record(root, line, "decision", e["decision_record_ref"], e["decision_record_sha256"], e)
            _check_record(root, line, "review", e["reviewer_ref"], e["reviewer_record_sha256"], e)
            s = e["sha256"]
            before = f"{eff[s]['authentication_state']}/{eff[s]['effective_source_class']}" if s in eff else "NO_ROW"
            if e["entry_type"] == "ADD":
                if s in by_sha:
                    raise LedgerError(f"{e['entry_id']}: a live row already exists for this sha256 ({by_sha[s]}); use CORRECTION")
                kind = _evidence_checks(e, ctx, e["proposed_class"])
                if e["proposed_authentication_state"] != "PROVENANCE_DOCUMENTED" or e["proposed_class"] == "AUTHENTICATION_PENDING":
                    raise LedgerError(f"{e['entry_id']}: an ADD records documented provenance only")
                eff[s] = register_row(e, ctx, kind)
            else:
                tgt = live.get(e["target_entry_id"])
                if tgt is None or by_sha.get(s) != e["target_entry_id"]:
                    raise LedgerError(f"{e['entry_id']}: target {e['target_entry_id']} is not the live row for this sha256")
                if tgt.get("entry_type") == "WITHDRAW" and e["entry_type"] == "WITHDRAW":
                    raise LedgerError(f"{e['entry_id']}: a WITHDRAW of a WITHDRAW is invalid (use CORRECTION or a new ADD)")
                if e["entry_type"] == "CORRECTION":
                    if e["proposed_authentication_state"] == "PROVENANCE_DOCUMENTED":
                        if e["proposed_class"] == "AUTHENTICATION_PENDING":
                            raise LedgerError(f"{e['entry_id']}: documented state with a pending class")
                        eff[s] = register_row(e, ctx, _evidence_checks(e, ctx, e["proposed_class"]))
                    else:
                        if e["proposed_class"] != "AUTHENTICATION_PENDING":
                            raise LedgerError(f"{e['entry_id']}: a pending correction must carry class AUTHENTICATION_PENDING")
                        resolve_refs(e)
                        base = eff.get(s) or {"sha256": s, "held_paths": "; ".join(sorted(ctx.held.get(s, [])))}
                        eff[s] = dict(base, authentication_state="AUTHENTICATION_PENDING", effective_source_class="AUTHENTICATION_PENDING",
                                      rationale=f"corrected by {e['entry_id']}: {e['justification']}")
                    del live[e["target_entry_id"]]
                    live[e["entry_id"]] = e
                    by_sha[s] = e["entry_id"]
                else:  # WITHDRAW: the target's effect ends; the record stays; an optional resulting state keeps the adverse fact
                    del live[e["target_entry_id"]]
                    by_sha.pop(s, None)
                    if e["resulting_state"] == "AUTHENTICATION_PENDING":
                        eff[s] = dict(eff.get(s) or {"sha256": s, "held_paths": "; ".join(sorted(ctx.held.get(s, [])))},
                                      authentication_state="AUTHENTICATION_PENDING", effective_source_class="AUTHENTICATION_PENDING",
                                      rationale=f"withdrawn by {e['entry_id']} ({e['withdrawal_reason']})")
                        live[e["entry_id"]] = e  # the pending state is itself live: it can be CORRECTED, not withdrawn again
                        by_sha[s] = e["entry_id"]
                    else:
                        eff.pop(s, None)
                    withdrawn.append({"version": line["version"], "entry_id": e["entry_id"], "target_entry_id": e["target_entry_id"], "sha256": s,
                                      "withdrawal_reason": e["withdrawal_reason"], "resulting_state": e["resulting_state"] or "NO_ROW"})
            if e["entry_type"] == "ADD":
                live[e["entry_id"]] = e
                by_sha[s] = e["entry_id"]
            after = f"{eff[s]['authentication_state']}/{eff[s]['effective_source_class']}" if s in eff else "NO_ROW"
            transitions.append({"version": line["version"], "entry_id": e["entry_id"], "entry_type": e["entry_type"], "sha256": s,
                                "effect": "APPLIED", "before": before, "after": after})
    return eff, transitions, withdrawn, lines[: as_of + 1]
