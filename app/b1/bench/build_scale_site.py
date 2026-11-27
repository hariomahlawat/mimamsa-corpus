"""C14 S4: deterministic synthetic scale site (1,000 / 4,000 / 10,000 documents) through the real path.

Each synthetic document clones a document of the committed B1 sample bundle (only originals <= --max-bytes, so the
vault stays within the disk budget), gets the id `bench<N>-<i>`, and its original PDF gets a unique trailer comment
after %%EOF (`%mimamsa-bench <N> <i>`) so every copy has its own SHA-256 and the start-up re-hash scales like a real
library. Text and passages are the base document's. The bundle is written with a disposable development key, imported
with app/importer (restricted register applied) into <out>/site, timed, and then deleted.

Bench sites are TEST DATA ONLY: never published, never mixed with the real sample, never uploaded.

  python -I build_scale_site.py --sample-bundle <dir> --n 1000 --out E:\\Mimamsa-Data\\bench\\1000 [--max-bytes 600000]
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO / "app/contract"), str(REPO / "app/importer"), str(REPO / "scripts")]
from mimamsa_contract.devbundle import new_dev_keypair, write_bundle  # noqa: E402
from mimamsa_contract.restricted import load_register  # noqa: E402
from mimamsa_importer import configure_site, import_release  # noqa: E402


def jl(p: Path):
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


class LazyFiles:
    """extra_files for write_bundle: yields (path, (bytes, kind)) one at a time instead of holding GBs in memory."""

    def __init__(self, gen):
        self._gen = gen

    def items(self):
        return self._gen()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample-bundle", type=Path, required=True)
    ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--max-bytes", type=int, default=600_000)
    ap.add_argument("--keep-bundle", action="store_true")
    a = ap.parse_args()
    src = a.sample_bundle
    docs = {d["doc_id"]: d for d in jl(src / "data/documents.jsonl")}
    derived = {d["doc_id"]: d for d in jl(src / "data/derived_text.jsonl")}
    pool = sorted(k for k, d in docs.items() if d["source_copy"]["bytes"] <= a.max_bytes and k in derived)
    print(f"base pool: {len(pool)} of {len(docs)} sample documents (originals <= {a.max_bytes} bytes)")

    out_docs, out_der, plan = [], [], []
    for i in range(a.n):
        base = pool[i % len(pool)]
        did = f"bench{a.n}-{i:05d}"
        raw = (src / "originals" / f"{docs[base]['source_copy']['sha256']}.pdf").read_bytes()
        data = raw + f"\n%mimamsa-bench {a.n} {i}\n".encode()
        h = hashlib.sha256(data).hexdigest()
        d = copy.deepcopy(docs[base])
        d.update(doc_id=did, title=f"{d.get('title') or base} [bench {i}]", parent_doc_id=None, alternate_copy_sha256=[])
        d["source_copy"].update(sha256=h, bytes=len(data), vault_path=f"vault/sha256/{h[:2]}/{h}")
        d["provenance"].update(source_system="bench-synthetic", source_record_id=f"{base}#{i}", aliases=[], hf=None, git=None,
                               source_url=f"urn:mimamsa:bench:{a.n}:{i}")
        r = copy.deepcopy(derived[base])
        r.update(doc_id=did, source_copy_sha256=h, text_path=f"text/{did}.txt")
        out_docs.append(d)
        out_der.append(r)
        plan.append((did, base, h))

    def files():
        for did, base, h in plan:
            i = int(did.rsplit("-", 1)[1])
            raw = (src / "originals" / f"{docs[base]['source_copy']['sha256']}.pdf").read_bytes()
            yield f"originals/{h}.pdf", (raw + f"\n%mimamsa-bench {a.n} {i}\n".encode(), "original")
            yield f"text/{did}.txt", ((src / derived[base]["text_path"]).read_bytes(), "text")
        for p in sorted((src / "research").glob("abbreviations*.jsonl")):
            yield f"research/{p.name}", (p.read_bytes(), "report")

    manifest = json.loads((REPO / "app/contract/examples/release_manifest.example.json").read_text(encoding="utf-8"))
    stamp = datetime.now(timezone.utc)
    content = hashlib.sha256(json.dumps(plan).encode()).hexdigest()[:8]
    release_id = f"R14-bench{a.n}-{stamp:%Y%m%d}-{content}"
    manifest.update(release_id=release_id, created_at=stamp.strftime("%Y-%m-%dT%H:%M:%SZ"), release_sequence=1)
    reg_bytes = (REPO / "config/restricted_material.json").read_bytes()
    manifest["restricted_material"] = {"config_path": "config/restricted_material.json",
                                       "config_sha256": hashlib.sha256(reg_bytes).hexdigest(), "restriction_ids_applied": ["RM-001"]}
    # pinned.hf_* are schema placeholders: bench sites have no HF source.
    head = __import__("subprocess").run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    manifest["pinned"] = {"hf_repo": "local/bench-synthetic", "hf_revision": "0" * 40, "tools_commit": head[:12], "artefact_commits": {}, "model_bundles": []}
    key, pub = new_dev_keypair()
    bundle = a.out / "bundle" / release_id
    if bundle.exists():
        shutil.rmtree(bundle)
    t = time.perf_counter()
    write_bundle(bundle, manifest, documents=out_docs, derived=out_der, extra_files=LazyFiles(files), signing_key=key, public_key_raw=pub)
    t_bundle = time.perf_counter() - t
    del key
    site = a.out / "site"
    if not (site / "SITE_CONFIG.json").exists():
        configure_site(site, exclusion_channel="none")
    t = time.perf_counter()
    res = import_release(bundle, site, trusted_public_key=pub, mode="development", register=load_register(REPO / "config/restricted_material.json"))
    t_import = time.perf_counter() - t
    bundle_bytes = sum(p.stat().st_size for p in bundle.rglob("*") if p.is_file())
    if not a.keep_bundle:
        shutil.rmtree(a.out / "bundle")
    result = {"n": a.n, "release_id": release_id, "base_pool": len(pool), "activated": res.activated,
              "verified_documents": len(res.verified["documents"]), "verified_derived": len(res.verified["derived_text"]),
              "refused": res.refused_reasons[:5], "unresolved": len(res.unresolved), "bundle_write_s": round(t_bundle, 1),
              "import_s": round(t_import, 1), "bundle_gb": round(bundle_bytes / 2**30, 2),
              "site_gb": round(sum(p.stat().st_size for p in site.rglob("*") if p.is_file()) / 2**30, 2)}
    (a.out / "build_result.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    print(json.dumps(result))
    return 0 if res.activated else 1


if __name__ == "__main__":
    sys.exit(main())
