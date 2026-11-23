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


def _git(cwd, *args, check=True):
    p = subprocess.run(["git", "-c", "protocol.allow=never", "-c", "core.useReplaceRefs=false", "-C", str(cwd), *args],
                       capture_output=True, env=_env())
    if check and p.returncode != 0:
        raise LedgerError(f"git {' '.join(args[:2])} failed: {p.stderr.decode(errors='replace').strip()[:200]}")
    return p


def _show(top, commit, path):
    p = _git(top, "cat-file", "blob", f"{commit}:{path}", check=False)
    return p.stdout if p.returncode == 0 else None


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


def verify(root, line, lines, canonical_line):
    """Verify the BIND line `line` against local git history. Returns a report dict; raises LedgerError on any failure."""
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
    parents = _git(top, "rev-list", "--parents", "-n", "1", mc).stdout.decode().split()[1:]
    if len(parents) != 2:
        raise LedgerError(f"version {line['version']}: merge_commit has {len(parents)} parent(s); an ordinary two-parent merge is required")
    if parents[1] != rh:
        raise LedgerError(f"version {line['version']}: merge_commit's second parent {parents[1][:12]} is not reviewed_head {rh[:12]}")
    if _git(top, "merge-base", "--is-ancestor", mc, "HEAD", check=False).returncode != 0:
        raise LedgerError(f"version {line['version']}: merge_commit is not in the history of the checked-out HEAD")
    mpath = rel("ledger/manifest.jsonl")
    want = [canonical_line(x) for x in lines[: n + 1]]
    at_head = _show(top, rh, mpath)
    if at_head is None or at_head.decode("utf-8").split("\n")[:-1] != want:
        raise LedgerError(f"version {line['version']}: the manifest at reviewed_head does not end exactly at version {n} with identical lines")
    at_base = _show(top, parents[0], mpath)
    base_lines = at_base.decode("utf-8").split("\n")[:-1] if at_base is not None else []
    if len(base_lines) != n or base_lines != want[:n]:
        raise LedgerError(f"version {line['version']}: the merge base does not stop at version {n - 1} (version {n} did not enter through this merge)")
    pinned = {bound["file"]: bound["file_sha256"], **bound["decisions"], **bound["reviews"]}
    # the whole ledger package (tools, records, ledger, evidence) must be unchanged between review and merge (Fable F-04)
    pkg = "" if prefix == "." else prefix
    tr = _git(top, "rev-parse", f"{rh}^{{tree}}" if not pkg else f"{rh}:{pkg}", check=False).stdout.decode().strip()
    tm = _git(top, "rev-parse", f"{mc}^{{tree}}" if not pkg else f"{mc}:{pkg}", check=False).stdout.decode().strip()
    if not tr or tr != tm:
        raise LedgerError(f"version {line['version']}: the ledger package tree differs between reviewed_head and merge_commit (changed after review)")
    for path in [mpath] + [rel(x) for x in sorted(pinned)]:
        a = _git(top, "rev-parse", f"{rh}:{path}", check=False).stdout.decode().strip()
        m = _git(top, "rev-parse", f"{mc}:{path}", check=False).stdout.decode().strip()
        if not a or a != m:
            raise LedgerError(f"version {line['version']}: {path} differs between reviewed_head and merge_commit (changed after review)")
    for path, h in pinned.items():
        blob = _show(top, rh, rel(path))
        if blob is None or hashlib.sha256(blob).hexdigest() != h:
            raise LedgerError(f"version {line['version']}: {path} at reviewed_head does not hash to its pin")
    return {"version": n, "bound_by": line["version"], "merge_commit": mc, "reviewed_head": rh, "git": "VERIFIED_OFFLINE",
            "github_review": f"ASSERTED_NOT_VERIFIED_OFFLINE (review {b['github_review_id']} by {b['github_review_login']} on PR #{b['pr_number']} of {b['repository']})"}

