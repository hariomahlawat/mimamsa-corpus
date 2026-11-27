"""Repository binding of approvals (AUTH-LEDGER-02): an approved ledger version becomes EFFECTIVE only when a later
manifest line (a BIND line) ties it to the ordinary merge commit of the pull request that carried it, and that tie is
verified OFFLINE against local git history.

Why: decision (D-) and review (R-) records are text. A repository writer can author both, with any names. Their pins and
entry digests stop alteration and reuse, but cannot show that the reviewed content is the content that was merged, or that
the version entered through a reviewed PR at all. The BIND line closes that gap with facts that git can check without a
network:

  1. the bound version is the line immediately before the BIND line, and its canonical text hashes to bound_line_sha256;
  2. merge_commit exists locally, has exactly two parents, its second parent is reviewed_head, and it is an ancestor of
     (or equal to) the checked-out HEAD;
  3. at reviewed_head the manifest has exactly the bound version as its last line, byte-identical to the current lines;
     at the merge's first parent (the base) the manifest stops before the bound version: the version entered by this merge;
  4. every file the bound line pins (entry file, decision and review records) and the manifest itself have the same blob at
     reviewed_head and at merge_commit (nothing changed between review and merge), and the blobs hash to the pins;
  5. the clone is not shallow (a shallow clone cannot show parents; verification fails closed).

What it does NOT establish, and how that is reported:
  - who approved on GitHub. github_review_id / github_review_login / github_review_commit are recorded as ASSERTED facts:
    git history does not contain PR reviews. They can be checked online (GET /repos/{repository}/pulls/{pr}/reviews) by
    an auditor; this module never contacts the network and never reports them as verified. The commit must equal
    reviewed_head (a review of an earlier commit does not cover later pushes).
  - identity of the persons named in D-/R- records. Commit author and committer text is never treated as identity.
  - legal or JAG approval. A BIND line is repository provenance for an evidence-authentication decision only.
A cryptographic owner signature (for example an SSH or OpenPGP signature over the BIND statement, checked against an
out-of-band trusted key) would add identity assurance; it is an owner decision and is not implemented here (no signing
tool or enrolled key exists in this environment, and no signature is ever described as verified without verification)."""
import json, os, re, subprocess
from pathlib import Path

from common import LedgerError, sha256_text
import hashlib

BIND_KEYS = ["binds_version", "bound_line_sha256", "repository", "pr_number", "reviewed_head", "merge_commit",
             "github_review_id", "github_review_login", "github_review_commit"]
SHA1 = re.compile(r"[0-9a-f]{40}")


def _env():
    """Sanitised environment (Fable F-01): no inherited GIT_* variable (GIT_DIR, GIT_OBJECT_DIRECTORY, GIT_GRAFT_FILE,
    GIT_REPLACE_REF_BASE ...), no system or global config, replace objects and grafts disabled, no prompts. Network
    transports are refused by protocol.allow=never on every call; GIT_NO_LAZY_FETCH additionally blocks partial-clone
    lazy fetches on git >= 2.44 (older git ignores it; protocol.allow=never still applies)."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(GIT_NO_REPLACE_OBJECTS="1", GIT_GRAFT_FILE=os.devnull, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
               GIT_NO_LAZY_FETCH="1", GIT_TERMINAL_PROMPT="0", GIT_OPTIONAL_LOCKS="0")
    return env


def _git(cwd, *args, check=True, input=None):
    try:
        p = subprocess.run(["git", "-c", "protocol.allow=never", "-c", "core.useReplaceRefs=false", "-c", "core.commitGraph=false",
                            "-C", str(cwd), *args],
                           capture_output=True, env=_env(), input=input)
    except FileNotFoundError:  # no git on PATH: fail closed with a ledger error, not a traceback (re-review R-04)
        raise LedgerError("git is not installed or not on PATH; the repository checks cannot run")
    if check and p.returncode != 0:
        raise LedgerError(f"git {' '.join(args[:2])} failed: {p.stderr.decode(errors='replace').strip()[:200]}")
    return p


def _show(top, commit, path):
    p = _git(top, "cat-file", "blob", f"{commit}:{path}", check=False)
    return p.stdout if p.returncode == 0 else None


PACKAGE_PARTS = ("legal_knowledge", "audit_work", "AUTH-LEDGER")


def check_package_layout(package):
    """Fail closed unless the committed ledger package is a real directory inside its repository (C8, Fable C-02).

    `package` is the logical (unresolved) package path. Every component from the repository top down to the package
    (legal_knowledge/audit_work/AUTH-LEDGER) must exist and must not be a symlink, including a broken one. Where git is
    available, the checked-out commit must also record each of those components as a tree (mode 040000), never as a
    committed symlink (120000). Returns the logical repository top."""
    package = Path(os.path.abspath(package))
    if tuple(package.parts[-3:]) != PACKAGE_PARTS:
        raise LedgerError(f"ledger package {package} is not at legal_knowledge/audit_work/AUTH-LEDGER")
    top = package.parents[2]
    cur = top
    for part in PACKAGE_PARTS:
        cur = cur / part
        if cur.is_symlink():
            raise LedgerError(f"ledger package path component {cur} is a symlink; a symlinked package could redirect verification")
        if not cur.is_dir():
            raise LedgerError(f"ledger package path component {cur} is not a directory")
    p = _git(top, "rev-parse", "--show-toplevel", check=False)
    if p.returncode != 0:
        if (top / ".git").exists():  # a repository git refuses (e.g. "dubious ownership"): fail closed (re-review R-04)
            raise LedgerError(f"git cannot read the repository at {top}: {p.stderr.decode(errors='replace').strip()[:160]}")
        return top  # no git repository at all (an exported snapshot): the filesystem checks above apply; BIND lines cannot verify
    if Path(p.stdout.decode().strip()).resolve() != top.resolve():
        raise LedgerError(f"the git repository top {p.stdout.decode().strip()} is not the package's own repository top {top}")
    if _git(top, "rev-parse", "--verify", "-q", "HEAD", check=False).returncode != 0:
        raise LedgerError("the repository has no HEAD commit; the committed package layout cannot be confirmed")
    for i in range(1, len(PACKAGE_PARTS) + 1):
        rel = "/".join(PACKAGE_PARTS[:i])
        out = _git(top, "ls-tree", "HEAD", "--", rel, check=False).stdout.decode().split()
        if not out:
            raise LedgerError(f"{rel} is not recorded in HEAD; the committed package layout cannot be confirmed")
        if out[0] != "040000":
            raise LedgerError(f"{rel} is committed with mode {out[0]} (not a directory tree); a committed symlink or gitlink could redirect verification")
    return top


def _ancestry_ok(top, ancestor):
    """Re-hash every commit on the ancestry path from `ancestor` to HEAD (re-review R-02): `merge-base --is-ancestor`
    reads those commits unhashed, so a forged interior commit could otherwise fake the ancestry. One batched read."""
    ids = _git(top, "rev-list", "--ancestry-path", f"{ancestor}..HEAD").stdout.decode().split() + [ancestor]
    out = _git(top, "cat-file", "--batch", input=("\n".join(ids) + "\n").encode()).stdout
    i = 0
    for oid in ids:
        nl = out.index(b"\n", i)
        hdr = out[i:nl].split()
        if len(hdr) != 3 or hdr[0].decode() != oid or hdr[1] != b"commit":
            return False
        size = int(hdr[2])
        body = out[nl + 1:nl + 1 + size]
        if hashlib.sha1(b"commit %d\0" % size + body).hexdigest() != oid:
            return False
        i = nl + 1 + size + 1
    return True


def _object_ok(top, sha, kind):
    """Re-hash a commit object from its stored bytes (C8, Fable C-04): a forged loose or packed object stored under a
    genuine id is rejected here, not only incidentally by merge-base."""
    body = _git(top, "cat-file", kind, sha, check=False)
    if body.returncode != 0:
        return False
    return hashlib.sha1(f"{kind} {len(body.stdout)}\0".encode() + body.stdout).hexdigest() == sha


def _read_verified(top, commit, path, version):
    """Walk commit -> root tree -> each path component, re-hashing every object from its stored bytes. Returns
    (object_id, content) of the final tree or blob, or None if the path does not exist. Any object whose bytes do not
    hash to its id raises (forged or corrupt). The commit object itself is re-hashed too."""
    if not _object_ok(top, commit, "commit"):
        raise LedgerError(f"version {version}: commit object {commit[:12]} does not hash to its id (forged or corrupt object)")
    body = _git(top, "cat-file", "commit", commit).stdout
    oid = body.split(b"\n", 1)[0].split(b" ")[1].decode()
    kind = "tree"
    for part in [x for x in path.split("/") if x]:
        content = _verified_content(top, oid, "tree", version)
        nxt, i = None, 0
        while i < len(content):
            sp, nul = content.index(b" ", i), content.index(b"\0", i)
            mode, name, ent = content[i:sp].decode(), content[sp + 1:nul].decode("utf-8", "surrogateescape"), content[nul + 1:nul + 21].hex()
            i = nul + 21
            if name == part:
                nxt = (ent, "tree" if mode == "40000" else ("blob" if mode in ("100644", "100755") else "other"))
                break
        if nxt is None:
            return None
        oid, kind = nxt
        if kind == "other":
            raise LedgerError(f"version {version}: {path} passes through a symlink, gitlink or other non-file entry")
    return oid, _verified_content(top, oid, kind, version)


def _verified_content(top, oid, kind, version):
    body = _git(top, "cat-file", kind, oid, check=False)
    if body.returncode != 0 or hashlib.sha1(f"{kind} {len(body.stdout)}\0".encode() + body.stdout).hexdigest() != oid:
        raise LedgerError(f"version {version}: {kind} object {oid[:12]} does not hash to its id (forged or corrupt object)")
    return body.stdout


def check_shape(b):
    if not isinstance(b, dict) or list(b) != BIND_KEYS:
        raise LedgerError(f"binding keys must be exactly {BIND_KEYS}")
    if not isinstance(b["binds_version"], int) or isinstance(b["binds_version"], bool) or b["binds_version"] < 1:
        raise LedgerError("binding: binds_version must be a positive integer")
    if not isinstance(b["pr_number"], int) or isinstance(b["pr_number"], bool) or b["pr_number"] < 1:
        raise LedgerError("binding: pr_number must be a positive integer")
    if not isinstance(b["github_review_id"], int) or isinstance(b["github_review_id"], bool) or b["github_review_id"] < 1:
        raise LedgerError("binding: github_review_id must be a positive integer")
    if not (isinstance(b["repository"], str) and re.fullmatch(r"[A-Za-z0-9-]{1,39}/[A-Za-z0-9._-]{1,100}", b["repository"])):
        raise LedgerError("binding: repository must be owner/name")
    if not (isinstance(b["github_review_login"], str) and re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})", b["github_review_login"])):
        raise LedgerError("binding: github_review_login is not a GitHub login")
    for k in ("bound_line_sha256",):
        if not (isinstance(b[k], str) and re.fullmatch(r"[0-9a-f]{64}", b[k])):
            raise LedgerError(f"binding: {k} must be a sha256")
    for k in ("reviewed_head", "merge_commit", "github_review_commit"):
        if not (isinstance(b[k], str) and SHA1.fullmatch(b[k])):
            raise LedgerError(f"binding: {k} must be a full 40-hex commit id")
    if b["github_review_commit"] != b["reviewed_head"]:
        raise LedgerError("binding: the approving review must be of reviewed_head itself (a review of an earlier commit does not cover later pushes)")
    if b["merge_commit"] == b["reviewed_head"]:
        raise LedgerError("binding: merge_commit equals reviewed_head (a fast-forward is not a reviewed merge)")


def verify(root, line, lines, canonical_line, expected_top=None):
    """Verify the BIND line `line` against local git history. Returns a report dict; raises LedgerError on any failure.
    expected_top pins the repository top (Fable R-02): for the committed ledger it is the repository that contains the
    package, so a `.git` directory or `gitdir:` file planted inside the ledger root cannot divert verification to
    another history."""
    b = line["binding"]
    check_shape(b)
    n = b["binds_version"]
    if n != line["version"] - 1:
        raise LedgerError(f"version {line['version']}: a BIND line must immediately follow the version it binds (binds {n})")
    bound = lines[n]
    if bound.get("binding") is not None or not bound["file"]:
        raise LedgerError(f"version {line['version']}: version {n} is not an entry version")
    if sha256_text(canonical_line(bound)) != b["bound_line_sha256"]:
        raise LedgerError(f"version {line['version']}: bound_line_sha256 does not match manifest line {n}")
    root = Path(root).resolve()
    p = _git(root, "rev-parse", "--show-toplevel", check=False)
    if p.returncode != 0:
        raise LedgerError(f"version {line['version']}: no git history at the ledger root; a binding can be verified only in a git clone or bundle")
    top = Path(p.stdout.decode().strip()).resolve()
    if expected_top is not None and top != Path(expected_top).resolve():
        raise LedgerError(f"version {line['version']}: git repository top {top} is not the expected repository {Path(expected_top).resolve()} "
                          "(a nested .git would divert verification)")
    if _git(top, "rev-parse", "--is-shallow-repository").stdout.decode().strip() == "true":
        raise LedgerError(f"version {line['version']}: shallow clone; binding verification needs full history (fetch-depth: 0)")
    # history-rewriting mechanisms make topology claims unverifiable: fail closed if any is present (Fable F-01)
    if _git(top, "for-each-ref", "refs/replace/").stdout.strip():
        raise LedgerError(f"version {line['version']}: refs/replace exists; replaced objects make the history unverifiable")
    common = Path(_git(top, "rev-parse", "--git-common-dir").stdout.decode().strip())  # not --git-path: GIT_GRAFT_FILE is /dev/null here
    if ((common if common.is_absolute() else top / common) / "info/grafts").exists():
        raise LedgerError(f"version {line['version']}: info/grafts exists; grafted parents make the history unverifiable")
    prefix = root.relative_to(top).as_posix()
    rel = (lambda x: x) if prefix == "." else (lambda x: f"{prefix}/{x}")
    mc, rh = b["merge_commit"], b["reviewed_head"]
    for c in (mc, rh):
        if _git(top, "cat-file", "-t", c, check=False).stdout.decode().strip() != "commit":
            raise LedgerError(f"version {line['version']}: commit {c[:12]} is not in the local history")
    for c in (mc, rh):
        if not _object_ok(top, c, "commit"):
            raise LedgerError(f"version {line['version']}: commit object {c[:12]} does not hash to its id (forged or corrupt object)")
    parents = _git(top, "rev-list", "--parents", "-n", "1", mc).stdout.decode().split()[1:]
    if len(parents) != 2:
        raise LedgerError(f"version {line['version']}: merge_commit has {len(parents)} parent(s); an ordinary two-parent merge is required")
    if not all(_object_ok(top, x, "commit") for x in parents):
        raise LedgerError(f"version {line['version']}: a parent commit object of merge_commit does not hash to its id")
    if parents[1] != rh:
        raise LedgerError(f"version {line['version']}: merge_commit's second parent {parents[1][:12]} is not reviewed_head {rh[:12]}")
    if _git(top, "merge-base", "--is-ancestor", mc, "HEAD", check=False).returncode != 0 or not _ancestry_ok(top, mc):
        raise LedgerError(f"version {line['version']}: merge_commit is not in the history of the checked-out HEAD")
    mpath = rel("ledger/manifest.jsonl")
    want = [canonical_line(x) for x in lines[: n + 1]]
    # every tree and blob the verdict depends on is read through re-hashed objects (C8, Fable review of be861ec0 F-02:
    # a forged tree stored under a genuine id must not be able to supply the manifest or the pinned files)
    vr = lambda commit, path: _read_verified(top, commit, path, line["version"])
    at_head = vr(rh, mpath)
    if at_head is None or at_head[1].decode("utf-8").split("\n")[:-1] != want:
        raise LedgerError(f"version {line['version']}: the manifest at reviewed_head does not end exactly at version {n} with identical lines")
    at_base = vr(parents[0], mpath)
    base_lines = at_base[1].decode("utf-8").split("\n")[:-1] if at_base is not None else []
    if len(base_lines) != n or base_lines != want[:n]:
        raise LedgerError(f"version {line['version']}: the merge base does not stop at version {n - 1} (version {n} did not enter through this merge)")
    pinned = {bound["file"]: bound["file_sha256"], **bound["decisions"], **bound["reviews"]}
    # the whole ledger package (tools, records, ledger, evidence) must be unchanged between review and merge (Fable F-04)
    pkg = "" if prefix == "." else prefix
    tr, tm = vr(rh, pkg), vr(mc, pkg)
    if tr is None or tm is None or tr[0] != tm[0]:
        raise LedgerError(f"version {line['version']}: the ledger package tree differs between reviewed_head and merge_commit (changed after review)")
    for path in [mpath] + [rel(x) for x in sorted(pinned)]:
        a, m = vr(rh, path), vr(mc, path)
        if a is None or m is None or a[0] != m[0]:
            raise LedgerError(f"version {line['version']}: {path} differs between reviewed_head and merge_commit (changed after review)")
    for path, h in pinned.items():
        got = vr(rh, rel(path))
        if got is None or hashlib.sha256(got[1]).hexdigest() != h:
            raise LedgerError(f"version {line['version']}: {path} at reviewed_head does not hash to its pin")
    return {"version": n, "bound_by": line["version"], "merge_commit": mc, "reviewed_head": rh, "git": "VERIFIED_OFFLINE",
            "github_review": f"ASSERTED_NOT_VERIFIED_OFFLINE (review {b['github_review_id']} by {b['github_review_login']} on PR #{b['pr_number']} of {b['repository']})"}

