#!/usr/bin/env python3
"""C13-A5: publish the reconfirmed SC case-number metadata overlay to the HF corpus as NEW additive files.

Convention (as data/manifest_additions/): the base data/meta records are never rewritten; dated additive files
are applied in file-name order. New folder data/meta_overlays/ with its own README:
  data/meta_overlays/README.md
  data/meta_overlays/c13_2026-11-25_sc_case_numbers.jsonl      (= scnum/SC_CASE_NUMBER_OVERLAY_C13.jsonl, byte-identical)
  data/meta_overlays/c13_2026-11-25_SHA256SUMS

Governance (docs/governance/CORPUS_REPOSITORY_GOVERNANCE.md): new paths only; parent_commit pinned; every
target path must be absent at the parent; scripts/hf_protect.assert_additive; re-download at the new commit
into a fresh directory and compare SHA-256 with the git-held manifest; record the commit in hf/.

  python -I -B hf_overlay_c13.py --stage            # write hf/staged/ + hf/STAGED_MANIFEST.csv (offline)
  python -I -B hf_overlay_c13.py --upload           # one commit to HF (parent pinned), then verify
  python -I -B hf_overlay_c13.py --check            # offline: staged files reproduce and match the manifest
  python -I -B hf_overlay_c13.py --check --online   # also re-download at the recorded commit and compare
"""
from __future__ import annotations

import argparse
import csv
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common_c13 as C  # noqa: E402

REPO_ID = "hariomahlawat/mimamsa-corpus"
PARENT = "3864faf3bb24edef4bfb18fa0916cc788eb68d79"   # verified HF head at C13 start (brief baseline)
STEM = "c13_2026-11-25"
PREFIX = "data/meta_overlays/"
HF = C.PKG / "hf"
STAGED = HF / "staged"

README = """# data/meta_overlays/

Additive, versioned metadata overlays for records in data/meta/. Made under the standing owner instruction
(docs/governance/CORPUS_REPOSITORY_GOVERNANCE.md in the GitHub repository). The base records in data/meta/ are
never rewritten in place; this follows the data/manifest_additions/ convention.

The current metadata view is: base data/meta record + every overlay file here, applied in file-name (date) order.
An overlay row names the record (doc_id), the source copy (source_copy_sha256), the field, the original value
and the overlay value, with its evidence and verification state.

- `<stem>_sc_case_numbers.jsonl`: Supreme Court `case_numbers` corrections. One JSON object per record.
  scope = METADATA_ONLY_NO_EVIDENCE_OR_AUTHENTICATION_STATUS_PROMOTED;
  verification = AI_DOCUMENTARY_RECONFIRMATION_NOT_LEGAL_VALIDATION.
- `<stem>_SHA256SUMS`: checksums of the files of that stem.

Overlays change no evidence class, authentication state or legal status. Records of each overlay (tool, HF commit,
verification) are in GitHub: legal_knowledge/audit_work/C13-A5-GRAPH/ for c13_2026-11-25.
"""


def staged_files():
    overlay = (C.PKG / "scnum" / "SC_CASE_NUMBER_OVERLAY_C13.jsonl").read_text(encoding="utf-8")
    body = {PREFIX + "README.md": README, PREFIX + STEM + "_sc_case_numbers.jsonl": overlay}
    sums = "".join("%s  %s\n" % (C.sha256_bytes(t.encode()), Path(k).name) for k, t in sorted(body.items()))
    body[PREFIX + STEM + "_SHA256SUMS"] = sums
    return body


def manifest_text(files):
    rows = [dict(hf_path=k, sha256=C.sha256_bytes(t.encode()), bytes=len(t.encode())) for k, t in sorted(files.items())]
    return C.to_csv(rows)


def guard(files):
    r = C.Restricted()
    for k, t in files.items():
        assert not r.hit(text=t), "restricted material in %s" % k


def upload(files):
    from huggingface_hub import HfApi, CommitOperationAdd
    sys.path.insert(0, str(C.WT / "scripts"))
    import hf_protect
    api = HfApi()
    head = api.dataset_info(REPO_ID).sha
    assert head == PARENT, "HF head moved (%s); re-stage against the new head after review" % head
    existing = {e.path for e in api.list_repo_tree(REPO_ID, repo_type="dataset", path_in_repo="data", revision=PARENT)}
    assert PREFIX.rstrip("/") not in existing, "data/meta_overlays already exists at parent; refusing"
    local = [(STAGED / k, k) for k in files]
    hf_protect.assert_additive(api, REPO_ID, local, revision=PARENT)
    ops = [CommitOperationAdd(path_in_repo=k, path_or_fileobj=str(STAGED / k)) for k in sorted(files)]
    info = api.create_commit(REPO_ID, repo_type="dataset", operations=ops, parent_commit=PARENT,
                             commit_message="C13 metadata overlay: 99 reconfirmed Supreme Court case_numbers corrections "
                                            "(additive, data/meta unchanged)",
                             commit_description="New folder data/meta_overlays/ (README, overlay JSONL, SHA256SUMS). "
                                                "Metadata only; no evidence or authentication status promoted. "
                                                "Records: GitHub legal_knowledge/audit_work/C13-A5-GRAPH/.")
    commit = info.oid
    (HF / "HF_COMMIT.csv").write_text(C.to_csv([dict(hf_commit=commit, parent_commit=PARENT, files_added=len(files),
                                                     paths=";".join(sorted(files)))]), encoding="utf-8")
    return commit


def verify(files, commit):
    from huggingface_hub import HfApi, hf_hub_download
    api = HfApi()
    rows = []
    with tempfile.TemporaryDirectory(dir=str(C.WT.parent / "a5work") if (C.WT.parent / "a5work").is_dir() else None) as d:
        for k, t in sorted(files.items()):
            p = hf_hub_download(REPO_ID, k, repo_type="dataset", revision=commit, local_dir=d)
            got = C.sha256_file(p)
            exp = C.sha256_bytes(t.encode())
            rows.append(dict(hf_commit=commit, hf_path=k, expected_sha256=exp, downloaded_sha256=got,
                             bytes=Path(p).stat().st_size, result="MATCH" if got == exp else "MISMATCH"))
    # tree diff: only the staged paths were added relative to the parent
    new = {e.path for e in api.list_repo_tree(REPO_ID, repo_type="dataset", recursive=True, revision=commit,
                                              path_in_repo=PREFIX.rstrip("/"))}
    assert new == set(files), new
    return rows


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--stage", action="store_true")
    g.add_argument("--upload", action="store_true")
    g.add_argument("--check", action="store_true")
    ap.add_argument("--online", action="store_true")
    a = ap.parse_args()
    files = staged_files()
    guard(files)
    if a.stage:
        for k, t in files.items():
            (STAGED / k).parent.mkdir(parents=True, exist_ok=True)
            (STAGED / k).write_text(t, encoding="utf-8")
        (HF / "STAGED_MANIFEST.csv").write_text(manifest_text(files), encoding="utf-8")
        print("staged %d files" % len(files))
        return 0
    if a.upload:
        assert (HF / "STAGED_MANIFEST.csv").read_text(encoding="utf-8") == manifest_text(files), "stage first"
        commit = upload(files)
        rows = verify(files, commit)
        (HF / "VERIFICATION.csv").write_text(C.to_csv(rows), encoding="utf-8")
        print(commit, [r["result"] for r in rows])
        return 0 if all(r["result"] == "MATCH" for r in rows) else 1
    # check
    ok = (HF / "STAGED_MANIFEST.csv").read_text(encoding="utf-8") == manifest_text(files)
    ok &= all((STAGED / k).read_text(encoding="utf-8") == t for k, t in files.items())
    rec = list(csv.DictReader(open(HF / "VERIFICATION.csv", encoding="utf-8"))) if (HF / "VERIFICATION.csv").exists() else []
    ok &= all(r["result"] == "MATCH" and r["expected_sha256"] == C.sha256_bytes(files[r["hf_path"]].encode()) for r in rec)
    if a.online and rec:
        rows = verify(files, rec[0]["hf_commit"])
        ok &= all(r["result"] == "MATCH" for r in rows)
    print("CHECK OK: staged overlay, manifest and recorded verification agree" if ok else "CHECK FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
