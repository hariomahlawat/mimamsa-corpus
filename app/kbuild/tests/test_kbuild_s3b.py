"""C16 Stage 3 S3-B: the central side of B04. S9 runs the site's own .NET verifiers (KBuildVerify verify-accel) on the
signed bundle and records VERIFIED; a graph row or index posting rewritten consistently with its digest is refused
centrally (BUILD_B04_CENTRAL). Needs the .NET SDK (skipped otherwise, like the other build tests)."""
from __future__ import annotations

import json
import shutil
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest

from mimamsa_kbuild import verify
from mimamsa_kbuild.errors import BuildRefused


def _verify_json(built) -> dict:
    return json.loads((built["root"] / "S9" / "VERIFY.json").read_text(encoding="utf-8"))


def test_s9_records_the_central_b04_checks(built):
    b04 = _verify_json(built)["checks"]["b04_central"]
    assert b04["status"] == "VERIFIED"
    for kind, checks in (("GRAPH", ("GRAPH_DIGEST", "GRAPH_STRUCTURAL_RECHECK", "SAMPLED_REBUILD_PARITY")),
                         ("LEXICAL_INDEX", ("SQLITE_QUICK_CHECK", "SAMPLED_POSTINGS_REDERIVE", "SAMPLED_QUERY_PARITY", "SOURCE_DIGEST_EQUALS_SITE"))):
        assert b04[kind]["status"] == "VERIFIED"
        assert all(b04[kind]["checks"][c] == "PASS" for c in checks)
        assert "timings_ms" not in b04[kind]                      # deterministic stage output
        for s in b04[kind]["samples"].values():
            assert s["size_source"].startswith("CENTRAL_OVERRIDE")  # never a calibration


def _ctx(built, tmp_path):
    return SimpleNamespace(accel_tool=built["res"]["context"].accel_tool, build_root=tmp_path)


def test_the_untampered_bundle_verifies_on_the_reference_site(built, tmp_path):
    ev = verify.central_b04(_ctx(built, tmp_path), built["root"] / "S5" / "site", built["root"] / "S8" / "bundle", "S9")
    assert ev["status"] == "VERIFIED"


def test_a_graph_row_rewritten_after_the_build_is_refused_centrally(built, tmp_path):
    bundle = tmp_path / "bundle"
    shutil.copytree(built["root"] / "S8" / "bundle", bundle)
    edges = bundle / "accelerators" / "graph" / "graph_edges.jsonl"
    lines = edges.read_text(encoding="utf-8").splitlines()
    row = json.loads(lines[0])
    row["uncertainty"] = "rewritten after the build"            # ids unchanged: the GRAPH digest still matches
    lines[0] = json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    edges.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    site = built["root"] / "S5" / "site"
    with pytest.raises(BuildRefused) as e:
        verify.central_b04(_ctx(built, tmp_path), site, bundle, "S9")
    assert e.value.code == "BUILD_B04_CENTRAL"


def test_an_index_posting_rewritten_with_a_matching_manifest_is_refused_centrally(built, tmp_path):
    import hashlib
    bundle = tmp_path / "bundle"
    shutil.copytree(built["root"] / "S8" / "bundle", bundle)
    ix = bundle / "accelerators" / "search-index"
    with sqlite3.connect(ix / "search.sqlite") as c:   # drop the first posting of the most frequent term
        term, df, blob = c.execute("SELECT term, df, postings FROM terms ORDER BY df DESC LIMIT 1").fetchone()
        i = 0

        def get():
            nonlocal i
            v = sh = 0
            while True:
                x = blob[i]; i += 1; v |= (x & 0x7F) << sh
                if x < 0x80:
                    return v
                sh += 7
        first = get(); n = get()
        for _ in range(n):
            get()
        rest = bytearray(blob[i:])
        # rebase the next posting's passage delta onto 0
        j = 0; v = sh = 0
        while True:
            x = rest[j]; j += 1; v |= (x & 0x7F) << sh
            if x < 0x80:
                break
            sh += 7
        v += first
        enc = bytearray()
        while v >= 0x80:
            enc.append((v & 0x7F) | 0x80); v >>= 7
        enc.append(v)
        c.execute("UPDATE terms SET df = ?, postings = ? WHERE term = ?", (df - 1, bytes(enc + rest[j:]), term))
    m = json.loads((ix / "MANIFEST.json").read_text(encoding="utf-8"))
    data = (ix / "search.sqlite").read_bytes()
    m["file_sha256"], m["file_bytes"] = hashlib.sha256(data).hexdigest(), len(data)
    (ix / "MANIFEST.json").write_text(json.dumps(m), encoding="utf-8")
    with pytest.raises(BuildRefused) as e:
        verify.central_b04(_ctx(built, tmp_path), built["root"] / "S5" / "site", bundle, "S9")
    assert e.value.code == "BUILD_B04_CENTRAL"
