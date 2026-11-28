"""C16 Stage 3 (S3-A) scale bench: build (kbuild S0-S9) and stage-only import of SYNTHETIC N-document sites, with peak
memory, duration and the CP-1 marker revalidation cost (re-hashing every file the bound marker binds).

Synthetic documents are cloned from a signed real-sample bundle exactly as app/b1/bench/build_scale_site.py does
(originals <= --max-bytes; each clone gets a unique trailer comment after %%EOF so every copy has its own sha256;
text and passages are the base document's). TEST DATA ONLY: written under --out (E:/Mimamsa-Data/c16s3a/bench),
never published, never uploaded, deleted afterwards with `clean`.

    python app/kbuild/bench/scale_bench.py run --sample-bundle <real S8/bundle> --n 4000 --out E:/Mimamsa-Data/c16s3a/bench
    python app/kbuild/bench/scale_bench.py import-only --bundle <S8/bundle> --trust <trust_list.json> --site <new dir>
    python app/kbuild/bench/scale_bench.py clean --out E:/Mimamsa-Data/c16s3a/bench --n 4000

Memory is the peak resident set of the WHOLE process tree (Python plus the .NET accelerator child), sampled every
0.2 s, and the Python process's own peak working set from the OS. The build runs under the spec's shared-host budget
(job object: half the CPUs at most, 4 GiB memory hard stop, below-normal priority).
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

KB = Path(__file__).resolve().parents[1]
REPO = KB.parents[1]
sys.path[:0] = [str(KB)]
import mimamsa_kbuild  # noqa: E402,F401  (paths)

BENCH_REPO, BENCH_REV = "local/bench-synthetic", "0" * 40


def jl(p: Path):
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


class TreeSampler:
    """Peak RSS of this process and its children, sampled in a thread."""

    def __init__(self, pid=None, period=0.2):
        import psutil
        self.p = psutil.Process(pid)
        self.period, self.peak, self._stop = period, 0, threading.Event()
        self.t = threading.Thread(target=self._run, daemon=True)

    def _run(self):
        import psutil
        while not self._stop.is_set():
            try:
                procs = [self.p] + self.p.children(recursive=True)
                self.peak = max(self.peak, sum(x.memory_info().rss for x in procs if x.is_running()))
            except psutil.Error:
                pass
            time.sleep(self.period)

    def __enter__(self):
        self.t.start()
        return self

    def __exit__(self, *_):
        self._stop.set()
        self.t.join()


def make_mirror(sample: Path, n: int, root: Path, max_bytes: int) -> dict:
    docs = {d["doc_id"]: d for d in jl(sample / "data" / "documents.jsonl")}
    derived = {d["doc_id"]: d for d in jl(sample / "data" / "derived_text.jsonl")}
    pool = sorted(k for k, d in docs.items() if d["source_copy"]["bytes"] <= max_bytes and k in derived)
    v1 = root / "local" / "bench-synthetic" / BENCH_REV / "v1"
    if v1.exists():
        shutil.rmtree(v1)
    (v1 / "originals").mkdir(parents=True)
    (v1 / "text").mkdir(parents=True)
    (v1 / "data").mkdir(parents=True)
    out_docs, out_der, total = [], [], 0
    for i in range(n):
        base = pool[i % len(pool)]
        did = f"bench{n}-{i:05d}"
        raw = (sample / "originals" / f"{docs[base]['source_copy']['sha256']}.pdf").read_bytes()
        data = raw + f"\n%mimamsa-bench {n} {i}\n".encode()
        h = hashlib.sha256(data).hexdigest()
        (v1 / "originals" / f"{h}.pdf").write_bytes(data)
        total += len(data)
        d = copy.deepcopy(docs[base])
        d.update(doc_id=did, title=f"{d.get('title') or base} [bench {i}]", parent_doc_id=None, alternate_copy_sha256=[])
        d["source_copy"].update(sha256=h, bytes=len(data), vault_path=f"vault/sha256/{h[:2]}/{h}")
        d["provenance"].update(source_system="bench-synthetic", source_record_id=f"{base}#{i}", aliases=[], git=None,
                               source_url=f"urn:mimamsa:bench:{n}:{i}", hf={"repo": BENCH_REPO, "revision": BENCH_REV, "path": f"v1/originals/{h}.pdf"})
        r = copy.deepcopy(derived[base])
        r.update(doc_id=did, source_copy_sha256=h, text_path=f"text/{did}.txt")
        (v1 / "text" / f"{did}.txt").write_bytes((sample / derived[base]["text_path"]).read_bytes())
        out_docs.append(d)
        out_der.append(r)
    w = lambda p, recs: p.write_bytes("".join(json.dumps(x, sort_keys=True, ensure_ascii=False) + "\n" for x in recs).encode())  # noqa: E731
    w(v1 / "data" / "documents.jsonl", out_docs)
    w(v1 / "data" / "derived_text.jsonl", out_der)
    w(v1 / "data" / "candidates.jsonl", [])
    (v1 / "research").mkdir()
    for p in sorted((sample / "research").glob("*.jsonl")):
        shutil.copyfile(p, v1 / "research" / p.name)
    return {"base_pool": len(pool), "originals_bytes": total, "documents": n}


def spec_for(n: int) -> dict:
    s = json.loads((KB / "specs" / "real-sample-290.spec.json").read_text(encoding="utf-8"))
    s["build_id"], s["output_dir"] = f"B-20261128-bench{n}", f"build/B-20261128-bench{n}"
    s["release"]["release_id"] = f"R16-bench{n}-20261128-{n:08x}"
    s["inputs"]["hf"] = [{"repo": BENCH_REPO, "revision": BENCH_REV, "purpose": "SYNTHETIC scale bench (test data only; never published)"}]
    s["inputs"]["tools"] = [t for t in s["inputs"]["tools"] if t["name"] == "mimamsa_kbuild"]
    s["resources"]["max_disk_bytes"] = 64 << 30
    return s


def rehash(gdir: Path) -> dict:
    """Re-hash every file the CP-1 bound marker binds (StagingMarker.BoundPaths): the full revalidation cost."""
    paths = ["generation.json"] + [p for p in ("KNOWLEDGE_RELEASE.json", "release/RELEASE.json", "corpus-v2/GENERATION.json") if (gdir / p).is_file()]
    paths += sorted(f"records/{p.name}" for p in (gdir / "records").glob("*.jsonl"))
    km = gdir / "KNOWLEDGE_RELEASE.json"
    if km.is_file():
        for c in json.loads(km.read_text(encoding="utf-8"))["components"]:
            if c["authority"] == "ACCELERATOR":
                paths += [f["path"] for f in c["files"]]
    paths = sorted(set(paths))
    total = sum((gdir / p).stat().st_size for p in paths)
    out = {"bound_files": len(paths), "bound_bytes": total}
    for label in ("first", "second"):
        t = time.perf_counter()
        for p in paths:
            h = hashlib.sha256()
            with open(gdir / p, "rb") as fh:
                for b in iter(lambda: fh.read(1 << 20), b""):
                    h.update(b)
        out[f"{label}_full_rehash_seconds"] = round(time.perf_counter() - t, 2)
    t = time.perf_counter()
    for p in paths:
        (gdir / p).stat()
    out["size_only_check_seconds"] = round(time.perf_counter() - t, 4)
    return out


def import_only(bundle: Path, trust: Path, site: Path, importer_root: Path | None = None) -> dict:
    """In a child process (its own memory), stage-only import; returns duration and peak memory."""
    code = r"""
import json, sys, time
sys.path[:0] = [sys.argv[5], sys.argv[1] + '/app/contract']
import psutil
from mimamsa_contract.restricted import load_register
from mimamsa_contract.trust import parse_trust_list
from mimamsa_importer import configure_site, import_release
configure_site(sys.argv[4], exclusion_channel='none')
t = time.perf_counter()
r = import_release(sys.argv[2], sys.argv[4], trust_list=parse_trust_list(json.loads(open(sys.argv[3], encoding='utf-8').read())),
                   mode='development', register=load_register(sys.argv[1] + '/config/restricted_material.json'), stage_only=True)
m = psutil.Process().memory_info()
print(json.dumps({'staged': r.staged, 'refused': r.refused_reasons[:3], 'verified': {k: len(v) for k, v in r.verified.items()},
                  'import_seconds': round(time.perf_counter() - t, 1), 'peak_working_set_bytes': m.peak_wset}))
"""
    root = importer_root or (REPO / "app" / "importer")
    t = time.perf_counter()
    p = subprocess.Popen([sys.executable, "-I", "-c", code, str(REPO), str(bundle), str(trust), str(site), str(root)],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                         creationflags=getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0))
    with TreeSampler(p.pid) as s:
        out, err = p.communicate()
    if p.returncode != 0:
        return {"error": err[-800:]}
    r = json.loads(out.strip().splitlines()[-1])
    r["sampled_peak_rss_bytes"] = s.peak
    r["wall_seconds"] = round(time.perf_counter() - t, 1)
    return r


def run(a) -> dict:
    from mimamsa_kbuild.cli import build_accel, default_accel_dll, run_build
    from mimamsa_kbuild.devkeys import ensure_dev_key
    base = a.out / str(a.n)
    base.mkdir(parents=True, exist_ok=True)
    t = time.perf_counter()
    mm = make_mirror(a.sample_bundle, a.n, base / "mirror", a.max_bytes)
    mm["mirror_seconds"] = round(time.perf_counter() - t, 1)
    accel = default_accel_dll(a.out / "tools")
    if not accel.is_file():
        build_accel(a.out / "tools")
    key = a.out / "dev.key"
    ensure_dev_key(key)
    spec = spec_for(a.n)
    t = time.perf_counter()
    with TreeSampler() as s:
        res = run_build(spec, base / "out", mirror=base / "mirror", dev_key=key, accel=accel)
    rec = json.loads(Path(res["record"]).read_text(encoding="utf-8"))
    build = {"seconds": round(time.perf_counter() - t, 1), "sampled_peak_tree_rss_bytes": s.peak,
             "python_peak_working_set_bytes": rec.get("resources_observed", {}).get("peak_working_set_bytes"),
             "stage_seconds": {k: v["seconds"] for k, v in rec["stage_timings"].items()},
             "build_tree_bytes": rec["stage_timings"]["S9"]["build_tree_bytes"], "budget": rec["budget"]["applied"].get("job")}
    root = base / "out" / spec["output_dir"]
    imp = import_only(root / "S8" / "bundle", root / "S8" / "dev-trust" / "trust_list.json", base / "site")
    gen = next((base / "site" / "generations").iterdir())
    marker = rehash(gen)
    old = None
    if a.compare_old:
        old = import_only(root / "S8" / "bundle", root / "S8" / "dev-trust" / "trust_list.json", base / "site-old", a.compare_old)
    out = {"label": "SYNTHETIC scale bench (clones of the real 290 sample; not real-corpus acceptance)", "n": a.n,
           "mirror": mm, "build": build, "stage_only_import": imp, "marker_revalidation": marker, "old_importer_import": old}
    (a.out / f"result-{a.n}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--sample-bundle", type=Path, required=True)
    r.add_argument("--n", type=int, required=True)
    r.add_argument("--out", type=Path, required=True)
    r.add_argument("--max-bytes", type=int, default=600_000)
    r.add_argument("--compare-old", type=Path, help="an importer package root of an earlier commit, for the before/after import")
    i = sub.add_parser("import-only")
    i.add_argument("--bundle", type=Path, required=True)
    i.add_argument("--trust", type=Path, required=True)
    i.add_argument("--site", type=Path, required=True)
    i.add_argument("--importer-root", type=Path)
    i.add_argument("--rehash", action="store_true")
    c = sub.add_parser("clean")
    c.add_argument("--out", type=Path, required=True)
    c.add_argument("--n", type=int, required=True)
    a = ap.parse_args()
    if a.cmd == "run":
        run(a)
    elif a.cmd == "import-only":
        res = import_only(a.bundle, a.trust, a.site, a.importer_root)
        if a.rehash and "error" not in res:
            res["marker_revalidation"] = rehash(next((a.site / "generations").iterdir()))
        print(json.dumps(res, indent=1))
    else:
        shutil.rmtree(a.out / str(a.n), ignore_errors=True)
        print("removed", a.out / str(a.n))
    return 0


if __name__ == "__main__":
    sys.exit(main())
