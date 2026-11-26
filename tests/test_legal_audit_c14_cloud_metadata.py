"""Cloud authority, stage diagnostics and private output tests (no network)."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/
    "legal_knowledge/audit_work/C14-CA01-STATUTORY/runner"))
import hf_metadata_cloud as cloud

COMMIT="a"*40
APPROVED = {"revision": cloud.REVISION, "code_commit": COMMIT,
            "runtime_sha256": "d"*64, "job_name": "wp1-fixture"}


@unittest.skipUnless(sys.platform == "linux", "isolated Linux sink")
class CloudTests(unittest.TestCase):
    def test_prompt_failure_writes_incomplete_without_worker(self):
        with tempfile.TemporaryDirectory() as tmp:
            jobs = Path(tmp).resolve()
            with cloud.claim(jobs, APPROVED["job_name"]) as job, \
                 patch.object(cloud, "bind_restriction", return_value=lambda **kw: False), \
                 patch.object(cloud, "read_token", side_effect=EOFError), \
                 patch.object(cloud, "supervise") as sup, contextlib.redirect_stdout(io.StringIO()) as stdout:
                self.assertEqual(cloud.run(APPROVED, b"fixture approval", job), 1)
                sup.assert_not_called()
            out = jobs / APPROVED["job_name"] / cloud.RECEIPT
            receipt = json.loads(out.read_bytes())
            self.assertEqual(receipt["failure"], "LOCAL_OR_WORKER_FAILURE")
            self.assertIsNone(receipt["inventory"])
            self.assertFalse(receipt["acquisition_eligible"])
            self.assertEqual(receipt["source_downloads"], 0)
            self.assertEqual(receipt["hf_writes"], 0)
            self.assertEqual(out.stat().st_mode & 0o777, 0o600)
            self.assertEqual(json.loads(stdout.getvalue())["receipt_sha256"], cloud.sha256(out.read_bytes()))

    def test_stage_failure_is_sanitized(self):
        inputs={"revision":cloud.REVISION,"code_commit":COMMIT,"runtime_sha256":"d"*64,"token":"hf_synthetic"}
        stdin=type("Input",(),{"buffer":io.BytesIO(cloud.canonical(inputs))})()
        def transport(url,cap,remaining):
            raise OSError("synthetic secret detail")
        def collect(revision,exchange,restricted,verify_credential):
            exchange("https://huggingface.co/api/whoami-v2",100,1)
        with patch.object(sys,"stdin",stdin),patch.object(cloud,"runtime",return_value="d"*64),\
             patch.object(cloud,"bind_restriction",return_value=lambda **kw:False),\
             patch.object(cloud,"DirectMetadataHTTPS",return_value=transport),\
             patch.object(cloud,"collect_receipt",side_effect=collect),\
             contextlib.redirect_stdout(io.StringIO()) as stdout:
            self.assertEqual(cloud.worker(),0)
        self.assertEqual(json.loads(stdout.getvalue()),{"acquisition_eligible":False,"failure":"CREDENTIAL_REQUEST_FAILED"})
        self.assertNotIn("secret",stdout.getvalue())

    def test_complete_worker_and_parent_round_trip(self):
        from types import SimpleNamespace
        from urllib.parse import unquote,urlsplit
        calls=[]
        def exchange(url,cap,remaining):
            route=urlsplit(url).path
            calls.append(route)
            if route=="/api/whoami-v2":
                data={"auth":{"type":"access_token","accessToken":{"role":"fineGrained",
                    "fineGrained":{"global":[],"canReadGatedRepos":False,"scoped":[
                        {"entity":{"type":"dataset","name":cloud.REPO,"_id":"1"*24},
                         "permissions":["repo.content.read"]}]}}}}
            elif "/revision/" in route:
                data={"id":cloud.REPO,"sha":cloud.REVISION,"private":True}
            else:
                store=unquote(route.split("/tree/"+cloud.REVISION+"/",1)[1])
                if store in cloud.STORES:
                    data=[{"path":store+"/synthetic.pdf","type":"file","size":10,
                           "lfs":{"oid":"d"*64,"size":10}},
                          {"path":store+"/excluded.pdf","type":"file","size":10,
                           "lfs":{"oid":"e"*64,"size":10}}]
                else:
                    data=[{"path":name,"type":"directory"} for name in cloud.STORES
                          if name.rsplit("/",1)[0]==store]
            return cloud.canonical(data),None

        def restricted(**kwargs):
            return kwargs.get("sha256")=="e"*64 or "excluded.pdf" in (kwargs.get("path") or "")
        def synthetic_supervisor(command,*,worker_input,env):
            self.assertNotIn("hf_synthetic",str(command)+str(env))
            self.assertNotIn("hf_synthetic", env.values())
            buf=io.BytesIO()
            with patch.object(sys,"stdin",SimpleNamespace(buffer=io.BytesIO(worker_input))),\
                 patch.object(sys,"stdout",SimpleNamespace(buffer=buf)),\
                 patch.object(cloud,"DirectMetadataHTTPS",return_value=exchange):
                self.assertEqual(cloud.worker(),0)
            return json.loads(buf.getvalue())

        with tempfile.TemporaryDirectory() as tmp:
            jobs = Path(tmp).resolve()
            with cloud.claim(jobs, APPROVED["job_name"]) as job, \
                 patch.object(cloud, "runtime", return_value="d"*64), \
                 patch.object(cloud, "bind_restriction", return_value=restricted), \
                 patch.object(cloud, "read_token", return_value="hf_synthetic"), \
                 patch.object(cloud, "supervise", side_effect=synthetic_supervisor), \
                 contextlib.redirect_stdout(io.StringIO()) as stdout:
                self.assertEqual(cloud.run(APPROVED, b"fixture approval", job), 0)
            raw = (jobs / APPROVED["job_name"] / cloud.RECEIPT).read_bytes()
            receipt=json.loads(raw)
            report=json.loads(stdout.getvalue())
            self.assertEqual(calls[0],"/api/whoami-v2")
            self.assertEqual(receipt["inventory"]["metadata_requests"],len(calls))
            self.assertTrue(receipt["inventory"]["coverage_of_supplied_scope"])
            self.assertEqual(receipt["inventory"]["restricted_excluded_count"],7)
            self.assertEqual(report["receipt_sha256"],cloud.sha256(raw))
            self.assertFalse(receipt["acquisition_eligible"])
            self.assertNotIn(b"excluded.pdf",raw)
            self.assertNotIn(b"hf_synthetic",raw)
            self.assertNotIn("synthetic.pdf",stdout.getvalue())

if __name__=="__main__":unittest.main()

