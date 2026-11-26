"""Cloud WP1 entry point. No source download, HF write, or legal promotion.

The protected GitHub environment is the cloud authority boundary. This
module does not accept the Windows approval as cloud approval. The live
workflow remains a proposal until the environment and credential are
provisioned by the account owner.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys

from hf_metadata_approval import bounded, canonical, sha256, snapshot_runtime, strict_json
from hf_metadata_job import (
    ROOT, DirectMetadataHTTPS, bind_restriction, collect_receipt, git_blob,
    supervise, validate_inventory, MAX_RECEIPT, MAX_WORKER_INPUT, _valid_token,
)
from hf_inventory_metadata import REPO, HEX40, STORES
from hf_metadata_credential import CredentialScopeError

REVISION = "f4e6ba443ec9c0b89b2c5d21d0b5cda38f55d2dc"
REF = "refs/heads/corpus/cloud-wp1-20261126"
APPROVAL = "METADATA_GET_ONLY"
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
    return sha256(canonical({name: sha256(raw) for name, raw in files.items()}))


def scope(env, event):
    commit = env.get("GITHUB_SHA", "")
    if (
        env.get("GITHUB_ACTIONS") != "true"
        or env.get("GITHUB_EVENT_NAME") != "workflow_dispatch"
        or env.get("GITHUB_REPOSITORY") != REPO
        or env.get("GITHUB_REF") != REF
        or env.get("RUNNER_OS") != "Linux"
        or env.get("WP1_CLOUD_ENABLED") != "true"
        or not HEX40.fullmatch(commit)
        or not re.fullmatch(r"[0-9]+", env.get("GITHUB_RUN_ID", ""))
        or not re.fullmatch(r"[0-9]+", env.get("GITHUB_RUN_ATTEMPT", ""))
        or env.get("GITHUB_RUN_ATTEMPT") != "1"
        or not isinstance(event, dict)
    ):
        raise ValueError("cloud execution boundary not established")
    expected = {"operation": APPROVAL, "revision": REVISION, "code_commit": commit}
    if event.get("inputs") != expected:
        raise ValueError("dispatch scope mismatch")
    return {
        "repository": REPO, "revision": REVISION, "code_commit": commit,
        "operation": APPROVAL, "roots": list(STORES),
        "run_id": env["GITHUB_RUN_ID"], "run_attempt": env["GITHUB_RUN_ATTEMPT"],
    }


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


def run():
    event = strict_json(bounded(Path(os.environ["GITHUB_EVENT_PATH"]), 128_000))
    approved = scope(os.environ, event)
    fingerprint = runtime(ROOT, approved["code_commit"], verify_git=True)
    restricted = bind_restriction(ROOT)
    token = os.environ.pop("HF_WP1_READ_TOKEN", "")
    temp = Path(os.environ["RUNNER_TEMP"])
    if not temp.is_absolute() or temp.resolve(strict=True) != temp or not temp.is_dir():
        raise ValueError("invalid scratch directory")
    out = temp / "wp1-cloud"
    out.mkdir(mode=0o700)
    result = None
    failure = None
    try:
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
    except Exception:
        failure = "LOCAL_OR_WORKER_FAILURE"
    receipt = {"schema": "c14-wp1-cloud-receipt-v1", **approved,
               "runtime_sha256": fingerprint,
               "status": "METADATA_SCOPE_COMPLETE" if not failure else "METADATA_INCOMPLETE",
               "failure": failure, "inventory": result, "acquisition_eligible": False,
               "source_downloads": 0, "hf_writes": 0}
    raw = canonical(receipt) + b"\n"
    if len(raw) > MAX_RECEIPT:
        receipt.update(status="METADATA_INCOMPLETE", failure="RECEIPT_LIMIT", inventory=None)
        raw = canonical(receipt) + b"\n"
    fd = os.open(out / "metadata_inventory.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    print(canonical({"status": receipt["status"], "failure": receipt["failure"],
                     "revision": REVISION, "receipt_sha256": sha256(raw),
                     "acquisition_eligible": False,
                     "counts": result["counts"] if result is not None else None}).decode("utf-8"))
    return 0 if receipt["status"] == "METADATA_SCOPE_COMPLETE" else 1


def main():
    if sys.argv[1:] == ["--worker"]:
        return worker()
    if sys.argv[1:] != ["--execute"]:
        print("Cloud WP1: no execution without exact protected workflow dispatch.")
        return 2
    try:
        return run()
    except Exception:
        print("Cloud WP1 refused: execution boundary or immutable inputs not verified.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
