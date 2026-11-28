"""Write a kbuild fetch plan (mimamsa-kbuild-fetch-plan/1) for the real-corpus build. Deterministic; no network.

    python app/kbuild/specs/make_fetch_plan.py --name real-sample-290 --sample app/b1/sample/SAMPLE_MANIFEST.json \
        --out app/kbuild/specs/real-sample-290.fetch.json [--extra-doc-ids <file>]

The plan names exactly what S1 fetches: the canonical dataset's manifests (their sha256 pinned here), the selected
doc_ids (sorted), the research inputs, and the Cycle 15 v7 candidate package at its receipt revision with the sha256 of
every file taken from the receipt held in git. The plan's own sha256 is pinned in the build spec as the
`config_sha256` of the tool `mimamsa_kbuild.fetch_plan`, so the spec stays the one input of the build.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
HF_REPO = "hariomahlawat/mimamsa-corpus"
CANONICAL_REVISION = "3864faf3bb24edef4bfb18fa0916cc788eb68d79"
# data/manifest.csv and data/raw_manifest.csv at CANONICAL_REVISION (verified again at fetch against the pinned tree)
MANIFEST_SHA256 = {"data/manifest.csv": None, "data/raw_manifest.csv": None}
V7 = {
    "name": "cycle15-v7", "repo": HF_REPO, "revision": "217020dbd969e14c2373697f4094fa00557962a6",
    "branch_at_receipt": "cycle15-candidates", "namespace": "legal_knowledge/candidates/cycle15/v7",
    "receipt": {"git_ref": "origin/corpus/c14-collection-discovery-20261126", "git_commit": "ba1f4c16c3a2acae8d68b0ddc0859294e5091ec8",
                "path": "legal_knowledge/audit_work/C15-CORPUS-ENGINEERING/candidate-v7-hf-receipt.json",
                "sha256": "e9a18321bf8802572e047106ea90b17ceaed78398f6e7fc2254ea4cd34cf7c75"},
    "files": ["records.jsonl", "pages.jsonl.gz", "portable-manifest.json", "source-manifest.json"],
}
RESEARCH = [{"path": "legal_knowledge/reference_data/abbreviations/v1.0/army_abbreviations_versioned_union_v1.0.json", "as": "abbreviations"}]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--sample", type=Path, required=True, help="a committed sample manifest listing doc_ids (documents[].doc_id)")
    ap.add_argument("--extra-doc-ids", type=Path, help="optional file, one doc_id per line, added to the selection")
    ap.add_argument("--manifest-sha256", nargs=2, action="append", metavar=("PATH", "SHA256"), default=[])
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    ids = {d["doc_id"] for d in json.loads(a.sample.read_text(encoding="utf-8"))["documents"]}
    if a.extra_doc_ids:
        ids |= {x.strip() for x in a.extra_doc_ids.read_text(encoding="utf-8").splitlines() if x.strip()}
    receipt = json.loads(subprocess.run(["git", "-C", str(REPO), "show", f"{V7['receipt']['git_commit']}:{V7['receipt']['path']}"],
                                        capture_output=True, check=True).stdout)
    if receipt["revision"] != V7["revision"] or receipt["namespace"] != V7["namespace"] or receipt.get("application_eligible") is not False:
        raise SystemExit("the v7 receipt does not match the pinned revision/namespace, or claims application eligibility")
    v7 = dict(V7, expected_sha256={f: receipt["sha256"][f"{V7['namespace']}/{f}"] for f in V7["files"]})
    man = dict(MANIFEST_SHA256)
    man.update({p: s for p, s in a.manifest_sha256})
    plan = {
        "record_kind": "kbuild_fetch_plan", "format": "mimamsa-kbuild-fetch-plan/1", "name": a.name,
        "canonical": {"repo": HF_REPO, "revision": CANONICAL_REVISION, "layout": "HF_CANONICAL_V1",
                      "manifests": dict(sorted(man.items())), "doc_ids": sorted(ids), "research": RESEARCH,
                      "selection_basis": f"doc_ids of {a.sample.as_posix()}" + (f" plus {a.extra_doc_ids.as_posix()}" if a.extra_doc_ids else "")},
        "v7": [v7],
        "transfer": {"max_workers": 2, "max_bytes_per_second": 8388608, "min_free_disk_bytes": 10737418240, "retries": 4, "timeout_seconds": 120},
    }
    a.out.write_bytes((json.dumps(plan, indent=1, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8"))
    print(a.out, len(ids))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
