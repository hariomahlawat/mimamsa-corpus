"""Shared helpers for the C13-A5 graph workstream (standard library only).

Inputs are read as git objects (no checkout) from the full-history object store passed with --repo
(default /home/user/c7) and from this worktree. Nothing here writes outside C13-A5-GRAPH/.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import subprocess
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent           # .../C13-A5-GRAPH
AUDIT = PKG.parent                                      # .../legal_knowledge/audit_work
WT = AUDIT.parent.parent                                # worktree root
TEXT_COMMIT = "ad77758d"                                # raw-data snapshot: data/raw, data/text, data/meta
DEFAULT_REPO = "/home/user/c7"

# Restricted-material register (single source of truth, C13-GOV RM-001). Read from the worktree when present,
# otherwise from the pinned governance branch commit as a git object.
RESTRICTED_CONFIG_PATH = "config/restricted_material.json"
RESTRICTED_CONFIG_COMMIT = "ea282cbd"                   # claude/c13-gov head that introduced RM-001
FOUO_SHA256 = "4284820e5bc2fb7f52ae9fbe8a61650f1579e9b6389ba206a916a69fed016b14"


def git(repo, *args) -> bytes:
    return subprocess.run(["git", "-C", str(repo)] + list(args), check=True, capture_output=True).stdout


def cat_blobs(repo, specs):
    """Read many objects ("<rev>:<path>" or blob sha) through one `git cat-file --batch`. Returns {spec: bytes|None}."""
    specs = list(specs)
    if not specs:
        return {}
    out = subprocess.run(["git", "-C", str(repo), "cat-file", "--batch"], input=("\n".join(specs) + "\n").encode(),
                         check=True, capture_output=True).stdout
    res, pos = {}, 0
    for s in specs:
        nl = out.index(b"\n", pos)
        header = out[pos:nl].decode()
        pos = nl + 1
        if header.endswith("missing"):
            res[s] = None
            continue
        size = int(header.split()[2])
        res[s] = out[pos:pos + size]
        pos += size + 1
    return res


def ls_tree(repo, commit, path):
    """{path: blob_sha} for every blob under path at commit."""
    out = {}
    for line in git(repo, "ls-tree", "-r", commit, path).decode("utf-8").splitlines():
        meta, p = line.split("\t", 1)
        out[p] = meta.split()[2]
    return out


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p) -> str:
    return sha256_bytes(Path(p).read_bytes())


def read_csv(p):
    with open(p, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def to_csv(rows, fields=None) -> str:
    buf = io.StringIO()
    if fields is None:
        fields = list(rows[0].keys()) if rows else []
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n", extrasaction="raise")
    w.writeheader()
    for r in rows:
        w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in fields})
    return buf.getvalue()


def to_jsonl(rows) -> str:
    return "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows)


def dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=True) + "\n"


def load_restricted():
    """Return (shas, doc_ids, paths, provenance) from the RM register."""
    local = WT / RESTRICTED_CONFIG_PATH
    if local.exists():
        raw, prov = local.read_bytes(), "worktree:" + RESTRICTED_CONFIG_PATH
    else:
        raw = git(WT, "show", "%s:%s" % (RESTRICTED_CONFIG_COMMIT, RESTRICTED_CONFIG_PATH))
        prov = "git:%s:%s" % (RESTRICTED_CONFIG_COMMIT, RESTRICTED_CONFIG_PATH)
    data = json.loads(raw)
    shas, ids, paths = set(), set(), set()
    for it in data["items"]:
        shas.add(it["source_sha256"].lower())
        shas.update(s.lower() for s in it.get("derived_sha256", []))
        ids.add(it["doc_id"])
        paths.update(it.get("hosted_paths", []))
    assert FOUO_SHA256 in shas, "restricted register no longer lists the FOUO RAF 2000 copy; stop and check"
    return frozenset(shas), frozenset(ids), frozenset(paths), dict(source=prov, sha256=sha256_bytes(raw))


class Restricted:
    def __init__(self):
        self.shas, self.ids, self.paths, self.provenance = load_restricted()

    def hit(self, sha256=None, doc_id=None, text=None) -> bool:
        if sha256 and str(sha256).lower() in self.shas:
            return True
        if doc_id and doc_id in self.ids:
            return True
        if text:
            t = str(text)
            if any(s in t for s in self.shas) or any(i in t for i in self.ids):
                return True
        return False


def write_or_check(files: dict, base: Path, check: bool) -> int:
    """files: {relative path: text}. In check mode compare byte-for-byte; else write."""
    bad = []
    for rel, text in sorted(files.items()):
        p = base / rel
        if check:
            if not p.exists() or p.read_text(encoding="utf-8") != text:
                bad.append(rel)
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8")
    if check:
        if bad:
            print("CHECK FAILED: %d file(s) differ: %s" % (len(bad), ", ".join(bad[:8])))
            return 1
        print("CHECK OK: %d outputs reproduce byte-identically" % len(files))
    return 0


def sums_text(files: dict) -> str:
    return "".join("%s  %s\n" % (sha256_bytes(t.encode("utf-8")), k) for k, t in sorted(files.items()))
