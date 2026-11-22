"""Single-purpose private Hugging Face upload of immutable Army abbreviation glossary."""
import hashlib
import io
import json
import os
from pathlib import Path
from huggingface_hub import CommitOperationAdd, HfApi, hf_hub_download

REPO = "hariomahlawat/mimamsa-corpus"
DEST = "legal_knowledge/reference_data/abbreviations/v1.0"
JSON_FILE = "army_abbreviations_versioned_union_v1.0.json"
EXPECTED_SHA = "0a2286061f11dd2a5fb90d03dca940d3efb8fe0f75055b5d2d44ae1fe08a380f"
EXPECTED_SIZE = 1165414

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def main():
    parts = sorted(Path(".abbreviations_transfer").glob("part_*.txt"))
    if [p.name for p in parts] != [f"part_{i:03d}.txt" for i in range(6)]:
        raise RuntimeError("Expected exactly six ordered transfer parts")
    original = b"".join(p.read_bytes() for p in parts)
    if len(original) != EXPECTED_SIZE or sha(original) != EXPECTED_SHA:
        raise RuntimeError(f"Source integrity FAILED: bytes={len(original)} sha256={sha(original)}")
    glossary = json.loads(original)
    abbreviations = glossary["abbreviations"]
    assert len(abbreviations) == 2742
    assert sum(len(v["meanings"]) for v in abbreviations.values()) == 3071
    assert glossary["statistics"]["JSSD_2025_independently_checked_pairs"] == 135
    assert glossary["current_standard"] == "JSSD_2025"

    readme = """# Army and joint-services abbreviations: versioned reference lexicon v1.0

Private Mimamsa source lexicon for future offline question interpretation and historical-document lookup.

- 2,742 abbreviation codes and 3,071 code/meaning pairs.
- JSSD 2025 is only PARTIALLY incorporated: 135 independently checked pairs, not full Volume II coverage.
- Legacy Appendix C meanings are preserved for older documents, not asserted current.
- Expansion must use context: one code may have multiple meanings; preserve the user's original question.
- Reference glossary only, NOT binding legal authority or substitute for Acts, Rules, Gazettes or judgments.
- Scribd and third-party meanings are not line-by-line verified against official editions.
- Original JSON bytes are unchanged, with SHA-256 and validation metadata provided.
- Private dataset only; confirm rights/access markings before any public reuse.

Review state: structurally checked, not independently certified for lexical/legal correctness.
"""
    validation = {
        "codes_observed": 2742, "code_meaning_pairs_observed": 3071,
        "unique_code_meaning_pairs_observed": 3071,
        "codes_with_multiple_meanings": 258,
        "case_insensitive_key_collision_groups": 66,
        "jssd_sample_confirmed_codes": 133, "jssd_tagged_pairs": 135,
        "source_json_sha256": EXPECTED_SHA, "source_json_bytes": EXPECTED_SIZE,
        "review_level": "structural_consistency_only_not_independent_lexical_or_copyright_audit",
        "status": "REFERENCE_DATA_UNVALIDATED_FOR_AUTHORITATIVE_USE",
        "dataset_release": "v1.0", "historical_reference": "APPENDIX_C_LEGACY",
        "current_standard": "JSSD_2025"
    }
    payloads = {
        JSON_FILE: original,
        "README.md": readme.encode("utf-8"),
        "validation_summary.json": (json.dumps(validation, indent=2) + "\n").encode("utf-8")
    }
    payloads["SHA256SUMS"] = "".join(
        f"{sha(payloads[name])}  {name}\n" for name in ("README.md", JSON_FILE, "validation_summary.json")
    ).encode("utf-8")
    token = os.environ["HF_TOKEN"]
    api = HfApi(token=token)
    if not api.repo_info(repo_id=REPO, repo_type="dataset").private:
        raise RuntimeError("Refusing upload: target dataset must be private")
    ops = [CommitOperationAdd(path_in_repo=f"{DEST}/{name}", path_or_fileobj=io.BytesIO(data))
           for name, data in payloads.items()]
    commit = api.create_commit(
        repo_id=REPO, repo_type="dataset", operations=ops,
        commit_message="Archive versioned Army abbreviations reference lexicon v1.0 (original bytes)"
    )
    print(f"HF commit {commit.oid}: {len(ops)} glossary files")
    for name, data in payloads.items():
        path = hf_hub_download(repo_id=REPO, repo_type="dataset", filename=f"{DEST}/{name}",
                               revision=commit.oid, token=token, force_download=True)
        remote = Path(path).read_bytes()
        if remote != data or sha(remote) != sha(data):
            raise RuntimeError(f"Remote SHA-256 FAILED for {name}")
        print(f"REMOTE VERIFIED {name}: {len(remote)} bytes sha256={sha(remote)}")
    print(f"SUCCESS https://huggingface.co/datasets/{REPO}/tree/{commit.oid}/{DEST}")

if __name__ == "__main__":
    main()
