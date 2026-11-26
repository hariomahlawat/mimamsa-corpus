"""WP1 owner-approved HF metadata inventory with an isolated worker."""
from __future__ import annotations
import base64
from datetime import datetime, timezone
import hashlib
import http.client
import json
import os
import ssl
import subprocess
import sys
import threading
import time
from pathlib import Path
from hf_inventory_metadata import REPO, STORES, HEX40, HEX64, path_in_store
from hf_inventory_provider import inventory, ENDPOINT
from hf_metadata_transport import MetadataAPI, MAX_SECONDS
from hf_metadata_approval import (
    GIT_PATH, MAX_APPROVAL_BYTES, PLAN_NAME, approval_payload, bounded,
    canonical, sha256, snapshot_runtime, strict_json, verify_approval,
)

REGISTER_BLOB = 'ca1096f11feb6f1cdffb69aca48ca016ac7d4a0b'
GUARD_BLOB = 'd2d11b77dc4fb7df0acbaa250004f44439f5a21e'
MAX_RECEIPT = 24_000_000
HARD_SECONDS = MAX_SECONDS + 15
MAX_WORKER_INPUT = 48_000
ROOT = Path(__file__).resolve().parents[4]


def git_blob(raw):
    return hashlib.sha1(b'blob '+str(len(raw)).encode('ascii')+b'\0'+raw,
                        usedforsecurity=False).hexdigest()


def bind_restriction(root):
    """Verify exact local register and existing predicate before any request."""
    from types import ModuleType,SimpleNamespace
    root=Path(root).resolve()
    config=root/'config/restricted_material.json'
    script=root/'scripts/restricted_material.py'
    snapshots=[]
    for path,digest in ((config,REGISTER_BLOB),(script,GUARD_BLOB)):
        if path.resolve()!=path:
            raise ValueError('restriction input path mismatch')
        raw=bounded(path, 1_000_000)
        if git_blob(raw)!=digest:
            raise ValueError('restriction input pin mismatch')
        snapshots.append(raw)
    # Use the exact verified guard source and freeze its config input in memory.
    module=ModuleType('c14_pinned_restriction')
    module.__file__=str(script)
    exec(compile(snapshots[1],str(script),'exec'),module.__dict__)
    module.CONFIG=SimpleNamespace(read_text=lambda **kw:snapshots[0].decode('utf-8'))
    module._load()
    return module.is_restricted


class DirectMetadataHTTPS:
    """GET exact fixed HTTPS origin only; no redirects, proxy or compression."""
    def __init__(self, revision, token, *, connect=http.client.HTTPSConnection):
        if not isinstance(revision,str) or not HEX40.fullmatch(revision):
            raise ValueError('immutable revision required')
        if not isinstance(token, str) or not _valid_token(token):
            raise ValueError('valid token required')
        self.revision=revision
        self.token=token
        self.connect=connect
        self.context=ssl.create_default_context()

    def __call__(self,url,cap,remaining):
        from hf_metadata_transport import metadata_request_target
        target = metadata_request_target(url, self.revision)
        if not 0 < cap <= 4_000_000 or remaining <= 0:
            raise ValueError("metadata request exceeds budget")
        deadline = time.monotonic() + remaining
        conn=self.connect('huggingface.co',443,timeout=min(15,remaining),context=self.context)
        try:
            conn.request('GET',target,
                         headers={'Authorization':'Bearer '+self.token,
                                  'Accept':'application/json','Accept-Encoding':'identity',
                                  'User-Agent':'Mimamsa-Metadata/1'})
            with conn.getresponse() as response:
                if response.status!=200 or response.headers.get_content_type()!='application/json':
                    raise ValueError('unexpected metadata response')
                encoding = response.headers.get_all('Content-Encoding', [])
                if len(encoding) > 1 or (encoding and encoding[0].strip().lower() != 'identity'):
                    raise ValueError('unexpected metadata encoding')
                transfer = response.headers.get_all('Transfer-Encoding', [])
                lengths=response.headers.get_all('Content-Length',[])
                if transfer and (lengths or len(transfer) != 1 or transfer[0].strip().lower() != 'chunked'):
                    raise ValueError('unexpected metadata framing')
                if len(lengths)>1 or (lengths and (not lengths[0].isascii() or not lengths[0].isdigit()
                                                   or int(lengths[0])>cap)):
                    raise ValueError('invalid metadata length')
                data = response.read(cap)
                if time.monotonic() >= deadline:
                    raise TimeoutError('metadata response exceeded deadline')
                if (len(data) > cap or (lengths and len(data) != int(lengths[0]))
                        or (len(data) == cap and not lengths and not response.isclosed())):
                    raise ValueError('metadata body outside budget')
                links=response.headers.get_all('Link',[])
                if len(links)>1:
                    raise ValueError('ambiguous pagination')
                return data, links[0] if links else None
        finally:
            conn.close()


def collect_receipt(revision, exchange, restricted, *, verify_credential=False):
    api = MetadataAPI(revision, exchange)
    if verify_credential:
        from hf_metadata_credential import require_dataset_read_scope
        require_dataset_read_scope(api.credential_info(), REPO)
    result=inventory(api,revision,restricted)
    result.pop('inventory_sha256',None)
    result.update(provider='BOUNDED_HF_METADATA_PROTOCOL',
                  register_git_blob=REGISTER_BLOB,guard_git_blob=GUARD_BLOB,
                  metadata_requests=api.requests,metadata_response_bytes=api.bytes,
                  acquisition_eligible=False,scope_independently_attested=False)
    result['inventory_sha256']=hashlib.sha256(json.dumps(result,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    return result


def supervise(command, *, seconds=HARD_SECONDS, worker_input=None, env=None):
    """Bound the only worker's runtime and pipe output, including failure paths."""
    if not 0 < seconds <= HARD_SECONDS:
        raise ValueError('invalid child deadline')
    if worker_input is not None and len(worker_input) > MAX_WORKER_INPUT:
        raise ValueError('invalid worker input size')
    deadline = time.monotonic() + seconds
    with subprocess.Popen(command, stdin=subprocess.PIPE if worker_input is not None else subprocess.DEVNULL,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env) as child:
        state = {}

        def exchange():
            try:
                if worker_input is not None:
                    with child.stdin:
                        child.stdin.write(worker_input)
                state["stdout"] = child.stdout.read(MAX_RECEIPT + 1)
            except OSError:
                state["io_failed"] = True

        def drain_error():
            state["has_stderr"] = bool(child.stderr.read(1))

        output = threading.Thread(target=exchange, daemon=True)
        error = threading.Thread(target=drain_error, daemon=True)
        output.start()
        error.start()
        try:
            output.join(max(0, deadline - time.monotonic()))
            if output.is_alive():
                raise TimeoutError('metadata worker deadline exceeded')
            raw = state.get("stdout")
            if state.get("io_failed") or raw is None or len(raw) > MAX_RECEIPT:
                raise ValueError('worker failed or produced unexpected output')
            child.wait(timeout=max(0, deadline - time.monotonic()))
            error.join(max(0, deadline - time.monotonic()))
            if child.returncode != 0 or error.is_alive() or state.get("has_stderr"):
                raise ValueError('worker failed or produced unexpected output')
        except subprocess.TimeoutExpired:
            raise TimeoutError('metadata worker deadline exceeded') from None
        finally:
            if child.poll() is None:
                child.kill()
                child.wait()
            output.join()
            error.join()
    try:
        result = strict_json(raw)
    except (ValueError, RecursionError):
        raise ValueError('worker failed or produced unexpected output') from None
    if not isinstance(result, dict) or result.get('acquisition_eligible') is not False:
        raise ValueError('unexpected worker receipt')
    return result


def validate_inventory(result, *, revision, restricted):
    """Return the validated canonical bytes without writing them."""
    if not isinstance(result,dict) or result.get('revision')!=revision or not HEX40.fullmatch(revision):
        raise ValueError('receipt revision mismatch')
    fields={'revision','coverage_of_supplied_scope','scope_independently_attested',
            'acquisition_eligible','required_stores','unlisted_stores','counts','missing',
            'invalid','claims','known_sha256','limits','inventory_sha256',
            'provider_entries_seen','restricted_excluded_count','unhashed_unclassified_pdf_count',
            'enumeration_failures','local_store_coverage','provider','source_downloads',
            'hf_writes','tree_entries_seen','root_scope_matches','register_git_blob','guard_git_blob',
            'metadata_requests','metadata_response_bytes'}
    if set(result)!=fields or any(result[k] is not False for k in ('scope_independently_attested','acquisition_eligible')):
        raise ValueError('receipt contract mismatch')
    if (result['register_git_blob']!=REGISTER_BLOB or result['guard_git_blob']!=GUARD_BLOB
            or result['provider']!='BOUNDED_HF_METADATA_PROTOCOL'
            or result['required_stores']!=sorted(STORES)
            or result['local_store_coverage']!='NOT_ATTESTED'
            or type(result['hf_writes']) is not int or result['hf_writes']!=0
            or type(result['source_downloads']) is not int or result['source_downloads']!=0):
        raise ValueError('receipt provenance mismatch')
    body=dict(result)
    digest=body.pop('inventory_sha256')
    if digest!=sha256(canonical(body)):
        raise ValueError('receipt digest mismatch')
    for kind in ('claims','missing','invalid'):
        for row in result[kind]:
            store,path=row['store'],row['path']
            if store not in STORES or not path_in_store(path,store) or restricted(path=path,sha256=row.get('sha256')):
                raise ValueError('receipt contains unapproved identity')
    for digest in result['known_sha256']:
        if not isinstance(digest,str) or not HEX64.fullmatch(digest) or restricted(sha256=digest):
            raise ValueError('unapproved digest in receipt')
    if result['known_sha256']!=sorted(set(row['sha256'] for row in result['claims'])):
        raise ValueError('receipt digest index mismatch')
    raw=json.dumps(result,sort_keys=True,ensure_ascii=False,allow_nan=False).encode('utf-8')+b'\n'
    if len(raw)>MAX_RECEIPT:
        raise ValueError('receipt exceeds output budget')
    return raw


def save_candidate_receipt(result, *, revision, restricted, job_dir):
    """Synthetic compatibility helper. Operational writes use the native sink."""
    raw = validate_inventory(result, revision=revision, restricted=restricted)
    job = Path(job_dir).absolute()
    if job.resolve() != job or not job.is_dir() or any(job.iterdir()):
        raise ValueError('fresh protected fixture directory required')
    with (job / 'metadata_inventory.json').open('xb') as out:
        out.write(raw)
    return {'receipt_sha256': sha256(raw), 'inventory_sha256': result['inventory_sha256'],
            'coverage_of_supplied_scope': result['coverage_of_supplied_scope'],
            'acquisition_eligible': False}


def _valid_token(value):
    import re
    return re.fullmatch(r'hf_[A-Za-z0-9_-]{1,255}', value) is not None


def _scope(root, revision, code_commit, jobs_root, job_name, *, verify_git):
    import re

    if not HEX40.fullmatch(revision or "") or not HEX40.fullmatch(code_commit or ""):
        raise ValueError("full immutable revisions required")
    if not isinstance(job_name, str) or not re.fullmatch(r"wp1-[A-Za-z0-9-]{1,48}", job_name):
        raise ValueError("invalid job name")
    output = Path(jobs_root).absolute()
    if output.resolve(strict=True) != output or not output.is_dir():
        raise ValueError("canonical jobs root required")
    files = snapshot_runtime(root)
    if verify_git:
        def git(*command):
            return subprocess.check_output(
                ["git", "-C", str(root), *command], stderr=subprocess.DEVNULL, timeout=10,
            )

        if git("rev-parse", "--verify", "HEAD").strip().decode("ascii") != code_commit:
            raise ValueError("checkout head mismatch")
        exact = {}
        for line in git("--literal-pathspecs", "ls-tree", "-r", "-z", code_commit, "--", *files).split(b"\0"):
            if line:
                meta, relative = line.split(b"\t", 1)
                mode, kind, blob = meta.decode("ascii").split()
                if mode != "100644" or kind != "blob":
                    raise ValueError("runtime requires ordinary tracked files")
                exact[relative.decode("utf-8")] = blob
        if exact != {name: git_blob(raw) for name, raw in files.items()}:
            raise ValueError("runtime files do not match the reviewed commit")
        for name in ("", "config", "scripts", GIT_PATH.rstrip("/"), GIT_PATH + "runner"):
            if (root / name / "__pycache__").exists():
                raise ValueError("fresh code checkout required")
    if (git_blob(files["config/restricted_material.json"]) != REGISTER_BLOB
            or git_blob(files["scripts/restricted_material.py"]) != GUARD_BLOB):
        raise ValueError("restriction input pin mismatch")
    return {
        "revision": revision, "code_commit": code_commit,
        "runtime_sha256": sha256(canonical({name: sha256(raw) for name, raw in files.items()})),
        "plan_sha256": sha256(files[GIT_PATH + PLAN_NAME]),
        "register_blob": REGISTER_BLOB, "guard_blob": GUARD_BLOB,
        "job_name": job_name, "jobs_root_sha256": sha256(str(output).encode("utf-8")),
    }


def approved_scope(args):
    scope = _scope(ROOT, args.revision, args.code_commit, args.jobs_root, args.job_name, verify_git=True)
    raw = bounded(args.approval, MAX_APPROVAL_BYTES)
    signature = bounded(args.signature, 64)
    public = bounded(args.owner_key, 4096)
    parameters = {
        "approval": base64.b64encode(raw).decode("ascii"),
        "signature": base64.b64encode(signature).decode("ascii"),
        "owner_key": base64.b64encode(public).decode("ascii"),
        "owner_key_sha256": args.owner_key_sha256,
        "code_commit": args.code_commit, "revision": args.revision,
        "jobs_root": str(Path(args.jobs_root).absolute()), "job_name": args.job_name,
    }
    verify_approval(raw, signature, public, args.owner_key_sha256, expected=scope,
                    now=datetime.now(timezone.utc))
    return scope, raw, parameters


def read_token():
    import getpass
    import warnings

    if not sys.stdin.isatty():
        raise ValueError("interactive console required")
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        token = getpass.getpass("HF dataset-scoped read token: ")
    if not _valid_token(token):
        raise ValueError("invalid token")
    return token


def _worker():
    """Recheck signed scope before the only two kinds of metadata requests."""
    from hf_metadata_credential import CredentialScopeError

    try:
        inputs = strict_json(sys.stdin.buffer.read(MAX_WORKER_INPUT + 1))
        if not isinstance(inputs, dict) or set(inputs) != {
            "approval", "signature", "owner_key", "owner_key_sha256", "code_commit",
            "revision", "jobs_root", "job_name", "token",
        }:
            raise ValueError("invalid worker input")
        scope = _scope(ROOT, inputs["revision"], inputs["code_commit"], inputs["jobs_root"],
                       inputs["job_name"], verify_git=False)
        verify_approval(*(base64.b64decode(inputs[k], validate=True)
                          for k in ("approval", "signature", "owner_key")),
                        inputs["owner_key_sha256"], expected=scope, now=datetime.now(timezone.utc))
        restricted = bind_restriction(ROOT)
        result = collect_receipt(scope["revision"], DirectMetadataHTTPS(scope["revision"], inputs["token"]),
                                 restricted, verify_credential=True)
        sys.stdout.buffer.write(validate_inventory(result, revision=scope["revision"], restricted=restricted))
    except CredentialScopeError:
        print('{"acquisition_eligible":false,"failure":"CREDENTIAL_SCOPE_UNVERIFIED"}')
    except TimeoutError:
        print('{"acquisition_eligible":false,"failure":"METADATA_DEADLINE"}')
    except Exception:
        print('{"acquisition_eligible":false,"failure":"WORKER_REJECTED_OR_UNAVAILABLE"}')
    return 0


def execute(args, scope, approval, parameters):
    from hf_metadata_windows import private_receipt_job

    restricted = bind_restriction(ROOT)
    boot = ("import runpy,sys; from pathlib import Path; "
            "p=sys.argv.pop(1); sys.path.append(str(Path(p).parent)); runpy.run_path(p,run_name='__main__')")
    command = [sys.executable, "-I", "-B", "-c", boot, str(Path(__file__).resolve()), "--worker"]
    env = {key: os.environ[key] for key in ("SYSTEMROOT",) if key in os.environ}
    with private_receipt_job(args.jobs_root, args.job_name) as job:
        result = None
        failure = None
        try:
            worker_input = canonical(dict(parameters, token=read_token()))
            payload = supervise(command, worker_input=worker_input, env=env)
            if set(payload) == {"acquisition_eligible", "failure"} and payload["failure"] in {
                "CREDENTIAL_SCOPE_UNVERIFIED", "METADATA_DEADLINE", "WORKER_REJECTED_OR_UNAVAILABLE",
            }:
                failure = payload["failure"]
            else:
                validate_inventory(payload, revision=scope["revision"], restricted=restricted)
                result = payload
                if not result["coverage_of_supplied_scope"]:
                    failure = "INCOMPLETE_SCOPE"
        except TimeoutError:
            failure = "HARD_WORKER_DEADLINE"
        except (ValueError, OSError, EOFError, KeyboardInterrupt):
            failure = "LOCAL_OR_WORKER_FAILURE"
        receipt = {
            "schema": "c14-wp1-metadata-operation-receipt-v1",
            "operation": "METADATA_GET_ONLY", "repository": REPO, "revision": scope["revision"],
            "code_commit": scope["code_commit"], "approval_sha256": sha256(approval),
            "runtime_sha256": scope["runtime_sha256"], "plan_sha256": scope["plan_sha256"],
            "register_git_blob": REGISTER_BLOB, "guard_git_blob": GUARD_BLOB,
            "status": "METADATA_SCOPE_COMPLETE" if not failure else "METADATA_INCOMPLETE",
            "failure": failure, "inventory": result, "acquisition_eligible": False,
            "hf_writes": 0, "source_downloads": 0,
        }
        raw = canonical(receipt) + b"\n"
        if len(raw) > MAX_RECEIPT:
            receipt.update(status="METADATA_INCOMPLETE", failure="RECEIPT_LIMIT", inventory=None)
            raw = canonical(receipt) + b"\n"
        job.write_receipt(raw)
        print(canonical({
            "status": receipt["status"], "failure": receipt["failure"], "revision": scope["revision"],
            "receipt_sha256": sha256(raw), "acquisition_eligible": False,
        }).decode("utf-8"))
        return 0 if receipt["status"] == "METADATA_SCOPE_COMPLETE" else 1


def main(argv=None):
    import argparse

    p = argparse.ArgumentParser(description=__doc__)
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--prepare-approval", action="store_true")
    mode.add_argument("--execute-metadata-only", action="store_true")
    mode.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    for flag in ("revision", "code-commit", "approval", "signature", "owner-key",
                 "owner-key-sha256", "jobs-root", "job-name"):
        p.add_argument("--" + flag)
    args = p.parse_args(argv)
    if args.worker:
        return _worker()
    if not args.prepare_approval and not args.execute_metadata_only:
        print("Offline scope preview: seven known HF roots. No network or output writes.")
        return 0
    try:
        if args.prepare_approval:
            scope = _scope(ROOT, args.revision, args.code_commit, args.jobs_root, args.job_name, verify_git=True)
            raw = canonical(approval_payload(**scope, now=datetime.now(timezone.utc))) + b"\n"
            with Path(args.approval).open("xb") as output:
                output.write(raw)
            print("Unsigned WP1 approval prepared for owner review.")
            return 0
        scope, approval, parameters = approved_scope(args)
        return execute(args, scope, approval, parameters)
    except (Exception, KeyboardInterrupt):
        # Paths, credential details, response bodies and child errors stay private.
        print("WP1 refused: approval, reviewed checkout, or private Windows job could not be verified.",
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
