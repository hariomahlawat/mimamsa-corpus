#!/usr/bin/env python3
"""Extract pinned acquisition documents from locally present remote-tracking refs (read-only).

Usage: extract_branch_pins.py <git_dir_with_refs> <snapshot_repo> <out_csv> [--check]

Runs only `git for-each-ref`, `git rev-parse` and `git show <ref>:config/sources.yaml` (no fetch, no network).
The staging configuration is read from the snapshot repo (<snapshot_repo>/config/sources.yaml).
"""
import csv, io, subprocess, sys
import yaml

REFS = [
    ("PR #8 (ACQ-01)", "origin/claude/acq-01-config"),
    ("PR #17 (ACQ-02)", "origin/claude/acq-02-config"),
    ("PR #23 (ACQ-03)", "origin/claude/acq-03-config"),
    ("PR #9 (DESW allow-list)", "origin/claude/desw-allowlist"),
    ("staging (v2.5-staging)", "origin/legal-knowledge/v2.5-staging"),
]
FIELDS = ["pr_label", "ref", "ref_commit", "source_key", "source_enabled", "allowed_hosts", "doc_id", "url",
          "title", "number", "issue_date", "expected_md5", "expected_bytes", "listing_md5", "listing_bytes",
          "md5_in_note", "bytes_in_note", "note"]


def git(gd, *a):
    return subprocess.run(["git", "-C", gd] + list(a), check=True, capture_output=True, text=True).stdout


def rows_from_yaml(text, label, ref, commit):
    import re
    y = yaml.safe_load(text)
    out = []
    for key, src in (y.get("sources") or {}).items():
        for d in (src or {}).get("documents") or []:
            note = str(d.get("note", ""))
            m = re.search(r"md5 ([0-9a-f]{32})", note)
            b = re.search(r"([\d,]+) bytes", note)
            out.append({
                "pr_label": label, "ref": ref, "ref_commit": commit, "source_key": key,
                "source_enabled": str(src.get("enabled")), "allowed_hosts": ";".join(src.get("allowed_hosts") or []),
                "doc_id": d.get("doc_id", ""), "url": d.get("url", ""), "title": d.get("title", ""),
                "number": str(d.get("number", "")), "issue_date": str(d.get("issue_date", "")),
                "expected_md5": d.get("expected_md5", "") or "", "expected_bytes": str(d.get("expected_bytes", "") or ""),
                "listing_md5": d.get("listing_md5", "") or "", "listing_bytes": str(d.get("listing_bytes", "") or ""),
                "md5_in_note": m.group(1) if m else "", "bytes_in_note": b.group(1).replace(",", "") if b else "", "note": note,
            })
    return out


def main():
    gd, snap, out = sys.argv[1], sys.argv[2], sys.argv[3]
    check = "--check" in sys.argv
    present = set(git(gd, "for-each-ref", "refs/remotes/origin", "--format=%(refname:short)").split())
    rows, missing = [], []
    for label, ref in REFS:
        if ref not in present:
            missing.append(ref)
            continue
        commit = git(gd, "rev-parse", ref).strip()
        rows += rows_from_yaml(git(gd, "show", f"{ref}:config/sources.yaml"), label, ref, commit)
    snapc = subprocess.run(["git", "-C", snap, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    rows += rows_from_yaml(open(f"{snap}/config/sources.yaml").read(), "snapshot c9src", "c9src:config/sources.yaml", snapc)
    buf = io.StringIO()
    w = csv.DictWriter(buf, FIELDS, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    for m in missing:
        w.writerow({"pr_label": "REF_ABSENT_LOCALLY", "ref": m})
    data = buf.getvalue()
    if check:
        ok = open(out).read() == data
        print("CHECK", "OK" if ok else "DIFF", out)
        sys.exit(0 if ok else 1)
    open(out, "w").write(data)
    print(len(rows), "rows;", "missing refs:", missing)


if __name__ == "__main__":
    main()
