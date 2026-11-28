"""S1 real fetch (B02 Stage 3): files of the private canonical HF dataset at PINNED revisions only.

Rules (CLAUDE.md HF standing instruction, plan WD-3, SG-6):
- Read-only. This module has no upload, commit, delete or branch call; it only lists a pinned tree and downloads files.
- A revision must be a full 40-hex commit id; a branch or tag name is refused (BUILD_INPUT_UNPINNED).
- Every file is verified before it enters the content-addressed cache: its size and its git object id (git blob sha1,
  or the LFS sha256) as the pinned commit's tree records them, and, where the caller knows one, the sha256 from a
  manifest (data/manifest.csv, a receipt held in git). A mismatch refuses the fetch (BUILD_INPUT_HASH).
- Restricted material is never downloaded: every path is checked against the restricted-material register (doc_id,
  path, and sha256 where known from the tree or a manifest) BEFORE the request; a hit is skipped and counted only (the
  register is the single source of truth; identities of restricted items are not repeated in any output).
- Bounded: at most `max_workers` concurrent transfers, a shared byte-rate cap and a free-disk floor on the cache volume.
- Credentials: the HTTP client is the owner-verified one (E:/Mimamsa-Data/scripts/hf_ipv4.py: httpx2, IPv4 source
  address, TLS verification on). Authorisation is added by huggingface_hub's own header builder (environment or the
  network secret); no token value is read, logged or written by this module.

Cache layout (under --hf-cache, e.g. E:/Mimamsa-Data/c16s3a/cache):
    cas/<sha256[:2]>/<sha256>                 verified file bytes, content-addressed
    trees/<owner>--<name>/<revision>.json     path -> {size, blob_id, lfs_sha256} as listed at the pinned revision
    index/<owner>--<name>/<revision>.json     path -> {sha256, bytes} for every verified download
A re-run with every requested path in the index and its CAS object present and re-hashing needs no network at all.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from .errors import BuildRefused
from .fsutil import write_atomic

HEX40 = re.compile(r"^[0-9a-f]{40}$")
CHUNK = 1 << 16


def _refuse(code, msg, details=None):
    raise BuildRefused(code, msg, "S1", details)


def require_pinned(revision: str) -> str:
    if not isinstance(revision, str) or not HEX40.match(revision):
        _refuse("BUILD_INPUT_UNPINNED", "HF revisions must be full 40-hex commit ids (a branch or tag name is not a pin)")
    return revision


def git_blob_sha1_init(size: int):
    h = hashlib.sha1()
    h.update(b"blob %d\0" % size)
    return h


@dataclass
class Transfer:
    """Bounded transfer settings (SG-6). max_bytes_per_second 0 = no rate cap."""
    max_workers: int = 2
    max_bytes_per_second: int = 8 << 20
    min_free_disk_bytes: int = 5 << 30
    timeout_seconds: int = 120
    retries: int = 4


class RateLimiter:
    """A shared byte-rate cap across worker threads (token bucket, one second of burst)."""

    def __init__(self, rate: int):
        self.rate = rate
        self._lock = threading.Lock()
        self._tokens = float(rate)
        self._t = time.monotonic()

    def take(self, n: int) -> None:
        if self.rate <= 0:
            return
        while True:
            with self._lock:
                now = time.monotonic()
                self._tokens = min(float(self.rate), self._tokens + (now - self._t) * self.rate)
                self._t = now
                if self._tokens >= n or self._tokens >= self.rate:
                    self._tokens -= n
                    return
                wait = (n - self._tokens) / self.rate
            time.sleep(min(wait, 1.0))


@dataclass
class FetchStats:
    requests: int = 0
    downloaded_files: int = 0
    downloaded_bytes: int = 0
    reused_files: int = 0
    reused_bytes: int = 0
    restricted_skipped: int = 0
    retries: int = 0
    seconds: float = 0.0
    log: list = field(default_factory=list)   # [{path, status, bytes}] (no time, no headers, no token)

    def as_dict(self) -> dict:
        d = {k: v for k, v in self.__dict__.items() if k != "log"}
        d["log_entries"] = len(self.log)
        return d


def _default_client(timeout: int):
    """The owner-verified HF client (hf_ipv4.py): httpx2, IPv4 source address, TLS verification on."""
    try:
        import httpx2 as hx
    except ImportError:   # pragma: no cover - the development venv has httpx2
        import httpx as hx
    return hx.Client(transport=hx.HTTPTransport(local_address="0.0.0.0", retries=2), follow_redirects=True, timeout=timeout)


def _install_hub_client(timeout: int) -> None:
    """huggingface_hub's own calls (tree listing) use the same client; process-local only."""
    try:
        from huggingface_hub import set_client_factory
        set_client_factory(lambda: _default_client(timeout))
    except ImportError:   # pragma: no cover - older hub versions use requests; nothing to install
        pass


class PinnedRepo:
    """One dataset repository at one pinned revision. Read-only."""

    def __init__(self, repo: str, revision: str, cache_root: Path, *, transfer: Transfer | None = None,
                 lister=None, opener=None, stats: FetchStats | None = None):
        self.repo = repo
        self.revision = require_pinned(revision)
        self.cache = Path(cache_root)
        self.transfer = transfer or Transfer()
        self.stats = stats or FetchStats()
        self._lister = lister            # tests inject a fake tree lister: paths -> {path: {size, blob_id, lfs_sha256}}
        self._opener = opener            # tests inject a fake byte source: path -> iterator of bytes
        self._rate = RateLimiter(self.transfer.max_bytes_per_second)
        self._lock = threading.Lock()
        self._local = threading.local()
        owner, name = repo.split("/", 1)
        self._key = f"{owner}--{name}"
        self.tree_file = self.cache / "trees" / self._key / f"{revision}.json"
        self.index_file = self.cache / "index" / self._key / f"{revision}.json"
        self._tree = self._load(self.tree_file)
        self._index = self._load(self.index_file)

    # ------------------------------------------------------------------ cache files
    @staticmethod
    def _load(p: Path) -> dict:
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def _save(self) -> None:
        with self._lock:
            write_atomic(self.tree_file, json.dumps(self._tree, sort_keys=True, indent=0).encode())
            write_atomic(self.index_file, json.dumps(self._index, sort_keys=True, indent=0).encode())

    def cas_path(self, sha: str) -> Path:
        return self.cache / "cas" / sha[:2] / sha

    def cached(self, path: str) -> dict | None:
        """{sha256, bytes} when the path was verified earlier and its CAS object still re-hashes."""
        e = self._index.get(path)
        if not e:
            return None
        p = self.cas_path(e["sha256"])
        try:
            if p.stat().st_size != e["bytes"]:
                return None
        except OSError:
            return None
        h = hashlib.sha256()
        with open(p, "rb") as fh:
            for b in iter(lambda: fh.read(1 << 20), b""):
                h.update(b)
        return e if h.hexdigest() == e["sha256"] else None

    # ------------------------------------------------------------------ tree (pinned listing)
    def tree(self, paths: list[str]) -> dict[str, dict]:
        """Size and object ids of `paths` at the pinned revision (cached; only missing entries are listed)."""
        missing = sorted({p for p in paths if p not in self._tree})
        if missing:
            got = self._list(missing)
            for p in missing:
                if p in got:
                    self._tree[p] = got[p]
            self._save()
        return {p: self._tree[p] for p in paths if p in self._tree}

    def list_prefix(self, prefix: str) -> list[str]:
        """Every file path under `prefix/` at the pinned revision (cached: the listing of a commit never changes)."""
        key = f"prefix:{prefix.rstrip('/')}/"
        if key not in self._tree:
            if self._lister is not None:
                found = self._lister([key])
            else:
                _install_hub_client(self.transfer.timeout_seconds)
                from huggingface_hub import HfApi
                found = {}
                try:
                    for e in HfApi().list_repo_tree(self.repo, path_in_repo=prefix.rstrip("/"), recursive=True,
                                                    repo_type="dataset", revision=self.revision):
                        if getattr(e, "blob_id", None) is not None and getattr(e, "size", None) is not None:
                            lfs = getattr(e, "lfs", None)
                            found[e.path] = {"size": int(e.size), "blob_id": e.blob_id, "lfs_sha256": lfs.sha256 if lfs else None}
                except Exception as exc:
                    if type(exc).__name__ in ("EntryNotFoundError", "RemoteEntryNotFoundError"):
                        found = {}
                    else:
                        _refuse("BUILD_FETCH_FAILED", f"listing failed at the pinned revision: {type(exc).__name__}")
                self.stats.requests += 1
            self._tree.update({p: v for p, v in found.items() if not p.startswith("prefix:")})
            self._tree[key] = {"files": sorted(p for p in found if not p.startswith("prefix:"))}
            self._save()
        return list(self._tree[key]["files"])

    def _list(self, paths: list[str]) -> dict[str, dict]:
        if self._lister is not None:
            return self._lister(paths)
        _install_hub_client(self.transfer.timeout_seconds)
        from huggingface_hub import HfApi
        api = HfApi()
        out = {}
        for i in range(0, len(paths), 200):
            chunk = paths[i:i + 200]
            for attempt in range(self.transfer.retries + 1):
                try:
                    infos = api.get_paths_info(self.repo, chunk, repo_type="dataset", revision=self.revision, expand=False)
                    self.stats.requests += 1
                    break
                except Exception as exc:   # network error: bounded retries with backoff, then refuse
                    if attempt == self.transfer.retries:
                        _refuse("BUILD_FETCH_FAILED", f"tree listing failed at the pinned revision: {type(exc).__name__}")
                    self.stats.retries += 1
                    time.sleep(min(30, 2 ** attempt))
            for info in infos:
                if getattr(info, "blob_id", None) is None:   # a folder
                    continue
                lfs = getattr(info, "lfs", None)
                out[info.path] = {"size": int(info.size), "blob_id": info.blob_id,
                                  "lfs_sha256": (lfs.sha256 if lfs is not None else None)}
        return out

    # ------------------------------------------------------------------ download
    def _open(self, path: str):
        if self._opener is not None:
            yield from self._opener(path)
            return
        from huggingface_hub import hf_hub_url
        from huggingface_hub.utils import build_hf_headers
        url = hf_hub_url(self.repo, path, repo_type="dataset", revision=self.revision)
        c = getattr(self._local, "client", None)
        if c is None:   # one keep-alive client per worker thread (TLS set-up per file dominated small transfers)
            c = self._local.client = _default_client(self.transfer.timeout_seconds)
        with c.stream("GET", url, headers=build_hf_headers()) as r:
            self.stats.requests += 1
            if r.status_code != 200:
                raise IOError(f"HTTP {r.status_code}")
            yield from r.iter_bytes(CHUNK)

    def _free_disk_ok(self) -> bool:
        try:
            return shutil.disk_usage(self.cache).free >= self.transfer.min_free_disk_bytes
        except OSError:
            return False

    def _download(self, path: str, entry: dict, expected_sha256: str | None) -> dict:
        tmpdir = self.cache / "tmp"
        tmpdir.mkdir(parents=True, exist_ok=True)
        tmp = tmpdir / (hashlib.sha256(f"{self.repo}@{self.revision}:{path}".encode()).hexdigest() + ".partial")
        last = None
        for attempt in range(self.transfer.retries + 1):
            if not self._free_disk_ok():
                _refuse("BUILD_DISK_FLOOR", "free disk on the cache volume is below the configured floor; fetch paused")
            sha, sha1, n = hashlib.sha256(), git_blob_sha1_init(entry["size"]), 0
            try:
                with open(tmp, "wb") as fh:
                    for chunk in self._open(path):
                        self._rate.take(len(chunk))
                        fh.write(chunk)
                        sha.update(chunk)
                        sha1.update(chunk)
                        n += len(chunk)
                    fh.flush()
                    os.fsync(fh.fileno())
                break
            except BuildRefused:
                raise
            except Exception as exc:   # timeouts, 5xx, resets: exponential backoff, give up after `retries`
                last = exc
                self.stats.retries += 1
                tmp.unlink(missing_ok=True)
                if attempt == self.transfer.retries:
                    self.stats.log.append({"path": path, "status": "FAILED", "bytes": 0})
                    _refuse("BUILD_FETCH_FAILED", f"download failed after {attempt + 1} attempts: {type(last).__name__}")
                time.sleep(min(60, 2 ** attempt))
        got = sha.hexdigest()
        ok = n == entry["size"] and (got == entry["lfs_sha256"] if entry.get("lfs_sha256") else sha1.hexdigest() == entry["blob_id"])
        if not ok or (expected_sha256 and got != expected_sha256):
            tmp.unlink(missing_ok=True)
            self.stats.log.append({"path": path, "status": "HASH_MISMATCH", "bytes": n})
            _refuse("BUILD_INPUT_HASH", "downloaded bytes do not match the pinned tree object or the manifest sha256",
                    [{"path": path}])
        dst = self.cas_path(got)
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            tmp.unlink(missing_ok=True)
        else:
            os.replace(tmp, dst)
        with self._lock:
            self._index[path] = {"sha256": got, "bytes": n}
            self.stats.downloaded_files += 1
            self.stats.downloaded_bytes += n
            self.stats.log.append({"path": path, "status": "OK", "bytes": n})
        return {"sha256": got, "bytes": n}

    def fetch(self, paths: list[str], *, expected_sha256: dict[str, str] | None = None, register=None,
              doc_ids: dict[str, str] | None = None) -> dict[str, dict]:
        """Fetch and verify `paths`. Returns {path: {sha256, bytes}} for every path fetched or reused; restricted paths
        are skipped (counted in stats.restricted_skipped) and absent from the result. A path absent from the pinned
        tree refuses (BUILD_INPUT_MISSING)."""
        expected_sha256 = expected_sha256 or {}
        doc_ids = doc_ids or {}
        t0 = time.perf_counter()
        out: dict[str, dict] = {}
        todo = []
        for p in sorted(set(paths)):
            if register is not None and register.is_restricted(sha256=expected_sha256.get(p), doc_id=doc_ids.get(p), path=p):
                self.stats.restricted_skipped += 1
                continue
            c = self.cached(p)
            if c is not None and (not expected_sha256.get(p) or c["sha256"] == expected_sha256[p]):
                out[p] = c
                self.stats.reused_files += 1
                self.stats.reused_bytes += c["bytes"]
                continue
            todo.append(p)
        if todo:
            tree = self.tree(todo)
            absent = [p for p in todo if p not in tree]
            if absent:
                _refuse("BUILD_INPUT_MISSING", f"{len(absent)} requested file(s) are not in the pinned revision", [{"path": p} for p in absent[:20]])
            final = []
            for p in todo:
                lfs = tree[p].get("lfs_sha256")
                if register is not None and lfs and register.is_restricted(sha256=lfs, doc_id=doc_ids.get(p), path=p):
                    self.stats.restricted_skipped += 1
                    continue
                if lfs and expected_sha256.get(p) and lfs != expected_sha256[p]:
                    _refuse("BUILD_INPUT_HASH", "the pinned tree's LFS sha256 differs from the manifest sha256", [{"path": p}])
                final.append(p)
            try:
                with ThreadPoolExecutor(max_workers=max(1, self.transfer.max_workers)) as ex:
                    results = list(ex.map(lambda p: (p, self._download(p, tree[p], expected_sha256.get(p))), final))
            finally:
                self._save()
            for p, r in results:
                if register is not None and register.is_restricted(sha256=r["sha256"]):
                    # defensive: a restricted hash that no listing or manifest revealed beforehand is purged at once
                    self.cas_path(r["sha256"]).unlink(missing_ok=True)
                    with self._lock:
                        self._index.pop(p, None)
                    self.stats.restricted_skipped += 1
                    continue
                out[p] = r
            self._save()
        self.stats.seconds += time.perf_counter() - t0
        return out

    def read(self, path: str) -> bytes:
        e = self._index[path]
        return self.cas_path(e["sha256"]).read_bytes()
