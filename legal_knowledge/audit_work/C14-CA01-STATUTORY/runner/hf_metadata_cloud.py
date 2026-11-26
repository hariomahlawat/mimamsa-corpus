"""Owner-approved WP1 metadata execution on a dedicated Linux cloud host."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import stat
import os
from pathlib import Path
import re
import subprocess
import sys

from hf_metadata_approval import (
    GIT_PATH, MAX_APPROVAL_BYTES, PLAN_NAME, approval_payload, bounded, canonical,
    sha256, snapshot_runtime, strict_json, verify_approval,
)
from hf_metadata_job import (
    ROOT, DirectMetadataHTTPS, bind_restriction, collect_receipt, git_blob,
    supervise, validate_inventory, MAX_RECEIPT, MAX_WORKER_INPUT, _valid_token,
    REGISTER_BLOB, GUARD_BLOB, read_token,
)
from hf_inventory_metadata import REPO, HEX40, STORES
from hf_metadata_credential import CredentialScopeError

REVISION = "f4e6ba443ec9c0b89b2c5d21d0b5cda38f55d2dc"
APPROVAL = "METADATA_GET_ONLY"
TRUST = Path("/etc/mimamsa/wp1-owner.pem")
DEPLOYMENT = Path("/etc/mimamsa/wp1-deployment")
JOBS = Path("/var/lib/mimamsa-wp1/jobs")
RECEIPT = "metadata_inventory.json"
JOB_NAME = re.compile(r"wp1-[a-z0-9-]{1,48}\Z")
SELF = "legal_knowledge/audit_work/C14-CA01-STATUTORY/runner/hf_metadata_cloud.py"


def runtime(root, commit, *, verify_git):
    files = snapshot_runtime(root)
    own = root / SELF
    if own.resolve(strict=True) != own:
        raise ValueError("noncanonical runtime")
    files[SELF] = bounded(own, 1_000_000)
    if verify_git:
        def git(*args):
            return subprocess.check_output(["git", "-C", str(root), *args],
                                           stderr=subprocess.DEVNULL, timeout=10)
        if git("rev-parse", "HEAD").strip().decode("ascii") != commit:
            raise ValueError("checkout pin mismatch")
        observed = {}
        for row in git("--literal-pathspecs", "ls-tree", "-r", "-z", commit, "--", *files).split(b"\0"):
            if row:
                meta, name = row.split(b"\t", 1)
                mode, kind, digest = meta.decode("ascii").split()
                if (mode, kind) != ("100644", "blob"):
                    raise ValueError("nonordinary runtime file")
                observed[name.decode("utf-8")] = digest
        if observed != {name: git_blob(raw) for name, raw in files.items()}:
            raise ValueError("runtime byte mismatch")
    if (git_blob(files["config/restricted_material.json"]) != REGISTER_BLOB
            or git_blob(files["scripts/restricted_material.py"]) != GUARD_BLOB):
        raise ValueError("restriction input pin mismatch")
    return sha256(canonical({name: sha256(raw) for name, raw in files.items()}))


def _root_controlled(path, *, file=False):
    if path.resolve(strict=True) != path:
        raise ValueError("noncanonical deployment path")
    for part in (path, *path.parents):
        info = part.stat()
        expected = stat.S_ISREG if part == path and file else stat.S_ISDIR
        if info.st_uid != 0 or info.st_mode & 0o022 or not expected(info.st_mode):
            raise ValueError("deployment policy must be root-controlled")


def host_settings():
    # GitHub writers have no access to this host, account or provisioning.
    if sys.platform != "linux" or os.geteuid() == 0 or os.environ.get("GITHUB_ACTIONS"):
        raise ValueError("dedicated non-root Linux host required")
    _root_controlled(TRUST, file=True)
    _root_controlled(DEPLOYMENT, file=True)
    _root_controlled(JOBS.parent)
    if JOBS.resolve(strict=True) != JOBS:
        raise ValueError("noncanonical jobs root")
    public = bounded(TRUST, 4096)
    deployment = bounded(DEPLOYMENT, 128).strip()
    if not re.fullmatch(rb"[a-f0-9]{64}", deployment):
        raise ValueError("invalid deployment identity")
    return JOBS, public, sha256(deployment)


def scope(args, host):
    jobs, _, deployment = host
    if not HEX40.fullmatch(args.code_commit or "") or not JOB_NAME.fullmatch(args.job_name or ""):
        raise ValueError("exact code commit and fresh job name required")
    return {
        "revision": REVISION, "code_commit": args.code_commit,
        "runtime_sha256": runtime(ROOT, args.code_commit, verify_git=True),
        "plan_sha256": sha256(bounded(ROOT / GIT_PATH / PLAN_NAME, 1_000_000)),
        "register_blob": REGISTER_BLOB, "guard_blob": GUARD_BLOB,
        "jobs_root_sha256": sha256(str(jobs).encode()), "job_name": args.job_name,
        "deployment_sha256": deployment,
    }


@contextmanager
def claim(jobs, job_name):
    """Durably consume the signed job name before prompting for a token."""
    if not JOB_NAME.fullmatch(job_name):
        raise ValueError("invalid job name")
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_DIRECTORY
    root_fd = os.open(jobs, flags)
    try:
        info = os.fstat(root_fd)
        if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o700:
            raise ValueError("private jobs root required")
        os.mkdir(job_name, mode=0o700, dir_fd=root_fd)
        os.fsync(root_fd)
        job_fd = os.open(job_name, flags, dir_fd=root_fd)
        try:
            yield job_fd
        finally:
            os.close(job_fd)
    finally:
        os.close(root_fd)


def publish(job, raw):
    """Expose only a complete, flushed receipt and preserve any prior file."""
    pending = ".receipt.pending"
    fd = os.open(pending, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=job)
    try:
        with os.fdopen(fd, "wb") as stream:
            if stream.write(raw) != len(raw):
                raise OSError("short receipt write")
            stream.flush()
            os.fsync(stream.fileno())
        os.link(pending, RECEIPT, src_dir_fd=job, dst_dir_fd=job, follow_symlinks=False)
        os.fsync(job)
    finally:
        os.unlink(pending, dir_fd=job)


def worker():
    stage = "WORKER_INPUT_REJECTED"
    try:
        raw = sys.stdin.buffer.read(MAX_WORKER_INPUT + 1)
        if len(raw) > MAX_WORKER_INPUT:
            raise ValueError("oversize worker input")
        args = strict_json(raw)
        if set(args) != {"revision", "code_commit", "runtime_sha256", "token"}:
            raise ValueError("unexpected input")
        if (args["revision"] != REVISION or not HEX40.fullmatch(args["code_commit"])
                or not isinstance(args["token"], str) or not _valid_token(args["token"])):
            raise ValueError("invalid worker input")
        stage = "RUNTIME_OR_RESTRICTION_REJECTED"
        if runtime(ROOT, args["code_commit"], verify_git=False) != args["runtime_sha256"]:
            raise ValueError("runtime mismatch")
        restricted = bind_restriction(ROOT)
        stage = "TRANSPORT_SETUP_FAILED"
        exchange = DirectMetadataHTTPS(REVISION, args["token"])

        def tracked(url, cap, remaining):
            nonlocal stage
            stage = ("CREDENTIAL_REQUEST_FAILED" if url.endswith("/api/whoami-v2")
                     else "REVISION_REQUEST_FAILED" if "/revision/" in url
                     else "TREE_REQUEST_FAILED")
            result = exchange(url, cap, remaining)
            stage = ("CREDENTIAL_RESPONSE_REJECTED" if url.endswith("/api/whoami-v2")
                     else "REVISION_RESPONSE_REJECTED" if "/revision/" in url
                     else "TREE_RESPONSE_REJECTED")
            return result

        result = collect_receipt(REVISION, tracked, restricted, verify_credential=True)
        stage = "INVENTORY_VALIDATION_FAILED"
        sys.stdout.buffer.write(validate_inventory(result, revision=REVISION, restricted=restricted))
    except CredentialScopeError:
        print('{"acquisition_eligible":false,"failure":"CREDENTIAL_SCOPE_UNVERIFIED"}')
    except TimeoutError:
        print('{"acquisition_eligible":false,"failure":"METADATA_DEADLINE"}')
    except Exception:
        print(canonical({"acquisition_eligible": False, "failure": stage}).decode("utf-8"))
    return 0


FAILURES = {
    "WORKER_INPUT_REJECTED", "RUNTIME_OR_RESTRICTION_REJECTED", "TRANSPORT_SETUP_FAILED",
    "CREDENTIAL_REQUEST_FAILED", "REVISION_REQUEST_FAILED", "TREE_REQUEST_FAILED",
    "CREDENTIAL_RESPONSE_REJECTED", "REVISION_RESPONSE_REJECTED", "TREE_RESPONSE_REJECTED",
    "INVENTORY_VALIDATION_FAILED", "CREDENTIAL_SCOPE_UNVERIFIED", "METADATA_DEADLINE",
}


def run(approved, approval, job):
    fingerprint = approved["runtime_sha256"]
    restricted = bind_restriction(ROOT)
    result = None
    failure = None
    try:
        token = read_token()
        if not _valid_token(token):
            failure = "CREDENTIAL_MISSING_OR_INVALID"
        else:
            inputs = canonical({"revision": REVISION, "code_commit": approved["code_commit"],
                                "runtime_sha256": fingerprint, "token": token})
            boot = ("import runpy,sys; from pathlib import Path; "
                    "p=sys.argv.pop(1); sys.path.append(str(Path(p).parent)); runpy.run_path(p,run_name='__main__')")
            payload = supervise([sys.executable, "-I", "-B", "-c", boot, str(Path(__file__).resolve()), "--worker"],
                                worker_input=inputs, env={"LANG": "C.UTF-8"})
            if set(payload) == {"acquisition_eligible", "failure"} and payload["failure"] in FAILURES:
                failure = payload["failure"]
            else:
                validate_inventory(payload, revision=REVISION, restricted=restricted)
                result = payload
                if not result["coverage_of_supplied_scope"]:
                    failure = "INCOMPLETE_SCOPE"
    except TimeoutError:
        failure = "HARD_WORKER_DEADLINE"
    except (Exception, KeyboardInterrupt):
        failure = "LOCAL_OR_WORKER_FAILURE"
    receipt = {"schema": "c14-wp1-isolated-cloud-receipt-v1", **approved,
               "operation": APPROVAL, "repository": REPO, "roots": list(STORES),
               "approval_sha256": sha256(approval),
               "status": "METADATA_SCOPE_COMPLETE" if not failure else "METADATA_INCOMPLETE",
               "failure": failure, "inventory": result, "acquisition_eligible": False,
               "source_downloads": 0, "hf_writes": 0}
    raw = canonical(receipt) + b"\n"
    if len(raw) > MAX_RECEIPT:
        receipt.update(status="METADATA_INCOMPLETE", failure="RECEIPT_LIMIT", inventory=None)
        raw = canonical(receipt) + b"\n"
    publish(job, raw)
    print(canonical({"status": receipt["status"], "failure": receipt["failure"],
                     "revision": REVISION, "receipt_sha256": sha256(raw),
                     "acquisition_eligible": False,
                     "counts": result["counts"] if result is not None else None}).decode("utf-8"))
    return 0 if receipt["status"] == "METADATA_SCOPE_COMPLETE" else 1


def main(argv=None):
    import argparse

    argv = sys.argv[1:] if argv is None else argv
    if argv == ["--worker"]:
        return worker()
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare-approval", action="store_true")
    mode.add_argument("--execute", action="store_true")
    for flag in ("code-commit", "job-name", "approval", "signature"):
        parser.add_argument("--" + flag)
    args = parser.parse_args(argv)
    try:
        host = host_settings()
        approved = scope(args, host)
        now = datetime.now(timezone.utc)
        if args.prepare_approval:
            print(canonical(approval_payload(**approved, now=now)).decode())
            return 0
        from cryptography.hazmat.primitives.serialization import load_pem_public_key

        jobs, public, _ = host
        fingerprint = sha256(load_pem_public_key(public).public_bytes_raw())
        raw = bounded(args.approval, MAX_APPROVAL_BYTES)
        verify_approval(raw, bounded(args.signature, 64), public, fingerprint,
                        expected=approved, now=now)
        with claim(jobs, approved["job_name"]) as job:
            return run(approved, raw, job)
    except (Exception, KeyboardInterrupt):
        print("Cloud WP1 refused: deployment, one-use approval or receipt could not be verified.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
