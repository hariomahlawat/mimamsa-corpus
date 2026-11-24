#!/usr/bin/env python3
"""Consolidate review findings across the Mimamsa audit record (Cycle 12).

What it does
------------
1. Inventories every row of every review findings CSV in scope:
   - tracked files matching ``findings*.csv`` under
     ``legal_knowledge/audit_work/{AUTH-LEDGER, C6-01-PROVENANCE, C8-SOURCES/review,
     C10-RECONCILIATION, C11-JUDICIAL-QUALITY, C12-CONSOLIDATION/reviews}``;
   - the two PR #46 blueprint findings CSVs, read from git at a pinned staging commit
     (they are not in this branch's tree).
   For each row it records the source file, the id (first column), the raw severity, the
   severity normalised to P1/P2/P3/INFO/OTHER and a one-line statement.
2. Joins the hand-maintained disposition table ``DISPOSITIONS.csv`` on (source_file, id).
3. Validates: every finding has exactly one disposition and vice versa; statuses are in the
   fixed vocabulary; every evidence file exists (worktree path, or ``staging:<path>`` at the
   pinned staging commit).
4. Writes ``FINDINGS_CONSOLIDATED.csv`` (or, with ``--check``, regenerates it in memory and
   byte-compares it with the committed file; exit 1 on any difference).

It makes no legal judgement and changes no other file. Output is deterministic for a given
tree and staging commit.

Usage (from anywhere inside the repository)::

    python -I -B consolidate_findings_c12.py            # write FINDINGS_CONSOLIDATED.csv
    python -I -B consolidate_findings_c12.py --check    # regenerate and byte-compare
    python -I -B consolidate_findings_c12.py --staging-ref <commit>

The staging commit must be present locally (``git fetch origin legal-knowledge/v2.5-staging``).
"""
import argparse
import collections
import csv
import io
import os
import re
import subprocess
import sys

STAGING_COMMIT_DEFAULT = "e0b3e7d2b8c3a1aa78f13ff99b67962534cf7e73"  # staging tip used for C12 consolidation
SCOPE_RE = re.compile(
    r"^legal_knowledge/audit_work/(AUTH-LEDGER|C6-01-PROVENANCE|C8-SOURCES/review|C10-RECONCILIATION|"
    r"C11-JUDICIAL-QUALITY|C12-CONSOLIDATION/reviews)/")
FINDINGS_RE = re.compile(r"findings.*\.csv$", re.IGNORECASE)
STAGING_FILES = (
    "docs/product/reviews/fable_review_pr46_c69eee41_findings.csv",
    "docs/product/reviews/fable_review_pr46_delta_findings.csv",
)
STATUSES = ("CLOSED_VERIFIED", "CLOSED_BY_AUTHOR_UNCONFIRMED", "DEFERRED_WITH_REASON",
            "OPEN_NO_RECORD", "SUPERSEDED", "NOT_A_DEFECT")
SEVERITIES = ("P1", "P2", "P3", "INFO", "OTHER")
STATEMENT_COLUMNS = ("title", "statement", "summary", "finding", "observation", "evidence_or_counterexample")
MAX_STATEMENT = 220
HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
DISPOSITIONS = os.path.join(PKG, "DISPOSITIONS.csv")
OUTPUT = os.path.join(PKG, "FINDINGS_CONSOLIDATED.csv")
DISP_HEADER = ["source_file", "id", "current_status", "status_evidence_file", "reason_or_note", "cycle13_action"]
OUT_HEADER = ["source_file", "id", "severity", "severity_raw", "statement", "current_status",
              "status_evidence_file", "reason_or_note", "cycle13_action"]


class ConsolidationError(Exception):
    pass


def git(root, *args):
    res = subprocess.run(["git", "-C", root] + list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if res.returncode != 0:
        raise ConsolidationError("git %s failed: %s" % (" ".join(args), res.stderr.decode("utf-8", "replace").strip()))
    return res.stdout


def repo_root():
    return git(HERE, "rev-parse", "--show-toplevel").decode("utf-8").strip()


def normalise_severity(raw):
    m = re.search(r"\b(P[123]|INFO)\b", raw or "", re.IGNORECASE)
    return m.group(1).upper() if m else "OTHER"


def one_line(text):
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) > MAX_STATEMENT:
        text = text[:MAX_STATEMENT - 3].rstrip() + "..."
    return text


def statement_of(row, header):
    for col in STATEMENT_COLUMNS:
        if col in header and (row.get(col) or "").strip():
            return one_line(row[col])
    if "status_or_file" in header:  # AUTH-LEDGER re-review 2e2df5ce: status (or file) plus evidence
        status = (row.get("status_or_file") or "").strip()
        ev = row.get("evidence") or ""
        if status and "/" not in status:
            return one_line("re-review status %s: %s" % (status, ev))
        return one_line(ev)
    return one_line(row.get("evidence") or "")


def parse_findings(source, text):
    reader = csv.reader(io.StringIO(text, newline=""))
    rows = list(reader)
    if not rows:
        raise ConsolidationError("%s: empty file" % source)
    header = [h.strip() for h in rows[0]]
    if "severity" not in header:
        raise ConsolidationError("%s: no severity column" % source)
    out = []
    for raw in rows[1:]:
        if not any(cell.strip() for cell in raw):
            continue
        if len(raw) != len(header):
            raise ConsolidationError("%s: row %r has %d cells, header has %d" % (source, raw[:1], len(raw), len(header)))
        rec = dict(zip(header, raw))
        fid = raw[0].strip()
        sev_raw = rec["severity"].strip()
        out.append({"source_file": source, "id": fid, "severity_raw": sev_raw,
                    "severity": normalise_severity(sev_raw), "statement": statement_of(rec, header)})
    return out


def inventory(root, staging_ref):
    tracked = git(root, "ls-files", "-z").decode("utf-8").split("\0")
    files = sorted(f for f in tracked if f and SCOPE_RE.match(f) and FINDINGS_RE.search(f))
    findings = []
    for f in files:
        with open(os.path.join(root, f), encoding="utf-8", newline="") as fh:
            findings.extend(parse_findings(f, fh.read()))
    for f in STAGING_FILES:
        text = git(root, "show", "%s:%s" % (staging_ref, f)).decode("utf-8")
        findings.extend(parse_findings("staging:" + f, text))
    seen = collections.Counter((r["source_file"], r["id"]) for r in findings)
    dup = [k for k, v in seen.items() if v > 1]
    if dup:
        raise ConsolidationError("duplicate (source_file, id): %r" % dup)
    return findings


def load_dispositions(root, staging_ref):
    with open(DISPOSITIONS, encoding="utf-8", newline="") as fh:
        rows = list(csv.reader(fh))
    if not rows or rows[0] != DISP_HEADER:
        raise ConsolidationError("DISPOSITIONS.csv header must be %r" % DISP_HEADER)
    table = {}
    errors = []
    staging_paths = None
    for n, raw in enumerate(rows[1:], start=2):
        if len(raw) != len(DISP_HEADER):
            errors.append("DISPOSITIONS.csv line %d: %d cells" % (n, len(raw)))
            continue
        rec = dict(zip(DISP_HEADER, raw))
        key = (rec["source_file"], rec["id"])
        if key in table:
            errors.append("DISPOSITIONS.csv line %d: duplicate %r" % (n, key))
        if rec["current_status"] not in STATUSES:
            errors.append("DISPOSITIONS.csv line %d: bad status %r" % (n, rec["current_status"]))
        ev = rec["status_evidence_file"]
        if ev.startswith("staging:"):
            if staging_paths is None:
                staging_paths = set(git(root, "ls-tree", "-r", "--name-only", "-z", staging_ref)
                                    .decode("utf-8").split("\0"))
            if ev[len("staging:"):] not in staging_paths:
                errors.append("DISPOSITIONS.csv line %d: evidence not at staging ref: %s" % (n, ev))
        elif not os.path.isfile(os.path.join(root, ev)):
            errors.append("DISPOSITIONS.csv line %d: evidence file missing: %s" % (n, ev))
        if not rec["reason_or_note"].strip() or not rec["cycle13_action"].strip():
            errors.append("DISPOSITIONS.csv line %d: empty reason_or_note or cycle13_action" % n)
        table[key] = rec
    if errors:
        raise ConsolidationError("\n".join(errors))
    return table


def build(root, staging_ref):
    findings = inventory(root, staging_ref)
    table = load_dispositions(root, staging_ref)
    keys = {(r["source_file"], r["id"]) for r in findings}
    missing = sorted(keys - set(table))
    orphan = sorted(set(table) - keys)
    if missing or orphan:
        raise ConsolidationError("findings without disposition: %r\ndispositions without finding: %r" % (missing, orphan))
    buf = io.StringIO(newline="")
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(OUT_HEADER)
    for r in findings:
        d = table[(r["source_file"], r["id"])]
        w.writerow([r["source_file"], r["id"], r["severity"], r["severity_raw"], r["statement"],
                    d["current_status"], d["status_evidence_file"], d["reason_or_note"], d["cycle13_action"]])
    return findings, table, buf.getvalue().encode("utf-8")


def summary(findings, table):
    counts = collections.Counter((r["severity"], table[(r["source_file"], r["id"])]["current_status"]) for r in findings)
    lines = ["rows: %d" % len(findings), "severity," + ",".join(STATUSES) + ",total"]
    for sev in SEVERITIES:
        vals = [counts.get((sev, st), 0) for st in STATUSES]
        if sum(vals):
            lines.append(sev + "," + ",".join(str(v) for v in vals) + ",%d" % sum(vals))
    lines.append("total," + ",".join(str(sum(counts.get((s, st), 0) for s in SEVERITIES)) for st in STATUSES)
                 + ",%d" % len(findings))
    open_p12 = [(r["source_file"], r["id"], table[(r["source_file"], r["id"])]["current_status"])
                for r in findings if r["severity"] in ("P1", "P2")
                and table[(r["source_file"], r["id"])]["current_status"] not in ("CLOSED_VERIFIED", "SUPERSEDED", "NOT_A_DEFECT")]
    lines.append("P1/P2 not CLOSED_VERIFIED/SUPERSEDED/NOT_A_DEFECT: %d" % len(open_p12))
    lines.extend("  %s %s %s" % t for t in open_p12)
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true", help="regenerate in memory and byte-compare with the committed output")
    ap.add_argument("--staging-ref", default=STAGING_COMMIT_DEFAULT, help="commit holding the PR #46 findings CSVs")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)
    try:
        root = repo_root()
        findings, table, data = build(root, args.staging_ref)
    except ConsolidationError as exc:
        print("CONSOLIDATION ERROR: %s" % exc, file=sys.stderr)
        return 2
    if args.check:
        try:
            with open(OUTPUT, "rb") as fh:
                current = fh.read()
        except OSError as exc:
            print("CHECK FAILED: cannot read %s: %s" % (OUTPUT, exc), file=sys.stderr)
            return 1
        if current != data:
            print("CHECK FAILED: FINDINGS_CONSOLIDATED.csv differs from regenerated output", file=sys.stderr)
            return 1
        print("CHECK OK: %d rows reproduce byte-identically" % len(findings))
    else:
        with open(OUTPUT, "wb") as fh:
            fh.write(data)
        print("wrote %s (%d rows)" % (os.path.relpath(OUTPUT, root), len(findings)))
    if not args.quiet:
        print(summary(findings, table))
    return 0


if __name__ == "__main__":
    sys.exit(main())
