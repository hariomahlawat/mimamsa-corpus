"""Cloud authority, stage diagnostics and private output tests (no network)."""
import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/
    "legal_knowledge/audit_work/C14-CA01-STATUTORY/runner"))
import hf_metadata_cloud as cloud

COMMIT="a"*40
ENV={
    "GITHUB_ACTIONS":"true","GITHUB_EVENT_NAME":"workflow_dispatch",
    "GITHUB_REPOSITORY":cloud.REPO,"GITHUB_REF":cloud.REF,"RUNNER_OS":"Linux",
    "WP1_CLOUD_APPROVED_COMMIT":COMMIT,"GITHUB_SHA":COMMIT,"GITHUB_RUN_ID":"123",
    "GITHUB_WORKFLOW_SHA":COMMIT,"GITHUB_WORKFLOW_REF":cloud.WORKFLOW_REF,
    "GITHUB_ACTOR":cloud.OWNER,"GITHUB_TRIGGERING_ACTOR":cloud.OWNER,
    "GITHUB_RUN_ATTEMPT":"1",
}
EVENT={"repository":{"private":True,"full_name":cloud.REPO},"inputs":{"operation":cloud.APPROVAL,"revision":cloud.REVISION,"code_commit":COMMIT}}


class CloudTests(unittest.TestCase):
    def test_exact_dispatch_scope(self):
        result=cloud.scope(ENV,EVENT)
        self.assertEqual(result["roots"],list(cloud.STORES))
        self.assertEqual(result["revision"],cloud.REVISION)

    def test_reject_wrong_boundary(self):
        for name,value in (("GITHUB_EVENT_NAME","pull_request"),("GITHUB_REPOSITORY","other/repo"),
                           ("GITHUB_REF","refs/heads/main"),("RUNNER_OS","Windows"),
                           ("WP1_CLOUD_APPROVED_COMMIT","b"*40),("GITHUB_RUN_ATTEMPT","2"),
                           ("GITHUB_WORKFLOW_SHA","b"*40),("GITHUB_WORKFLOW_REF","unexpected"),
                           ("GITHUB_ACTOR","other"),("GITHUB_TRIGGERING_ACTOR","other"),
                           ("GITHUB_SHA","b"*40)):
            with self.subTest(name=name),self.assertRaises(ValueError):
                cloud.scope(dict(ENV,**{name:value}),EVENT)
        for name,value in (("revision","b"*40),("operation","UPLOAD"),("code_commit","b"*40)):
            with self.subTest(name=name),self.assertRaises(ValueError):
                cloud.scope(ENV,dict(EVENT,inputs=dict(EVENT["inputs"],**{name:value})))

    def test_public_repository_refused(self):
        with self.assertRaises(ValueError):
            cloud.scope(ENV,dict(EVENT,repository={"private":False,"full_name":cloud.REPO}))

    def test_missing_token_writes_incomplete_without_worker(self):
        if os.name!="posix":
            self.skipTest("Linux cloud sink")
        with tempfile.TemporaryDirectory() as tmp:
            temp=Path(tmp).resolve()
            event=temp/"event.json"
            event.write_text(json.dumps(EVENT),encoding="utf-8")
            env=dict(ENV,GITHUB_EVENT_PATH=str(event),RUNNER_TEMP=str(temp))
            with patch.dict(os.environ,env,clear=True),patch.object(cloud,"runtime",return_value="d"*64),\
                 patch.object(cloud,"bind_restriction",return_value=lambda **kw:False),\
                 patch.object(cloud,"supervise") as sup,contextlib.redirect_stdout(io.StringIO()) as stdout:
                self.assertEqual(cloud.run(),1)
                sup.assert_not_called()
            out=temp/"wp1-cloud"/"metadata_inventory.json"
            receipt=json.loads(out.read_bytes())
            self.assertEqual(receipt["failure"],"CREDENTIAL_MISSING_OR_INVALID")
            self.assertIsNone(receipt["inventory"])
            self.assertFalse(receipt["acquisition_eligible"])
            self.assertEqual(receipt["source_downloads"],0)
            self.assertEqual(receipt["hf_writes"],0)
            self.assertEqual(out.stat().st_mode & 0o777,0o600)
            self.assertEqual(json.loads(stdout.getvalue())["receipt_sha256"],cloud.sha256(out.read_bytes()))

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
            self.assertNotIn("HF_WP1_READ_TOKEN",os.environ)
            buf=io.BytesIO()
            with patch.object(sys,"stdin",SimpleNamespace(buffer=io.BytesIO(worker_input))),\
                 patch.object(sys,"stdout",SimpleNamespace(buffer=buf)),\
                 patch.object(cloud,"DirectMetadataHTTPS",return_value=exchange):
                self.assertEqual(cloud.worker(),0)
            return json.loads(buf.getvalue())

        if os.name!="posix":
            self.skipTest("Linux cloud sink")
        with tempfile.TemporaryDirectory() as tmp:
            temp=Path(tmp).resolve()
            event=temp/"event.json"
            event.write_text(json.dumps(EVENT),encoding="utf-8")
            env=dict(ENV,GITHUB_EVENT_PATH=str(event),RUNNER_TEMP=str(temp),
                     HF_WP1_READ_TOKEN="hf_synthetic")
            with patch.dict(os.environ,env,clear=True),patch.object(cloud,"runtime",return_value="d"*64),\
                 patch.object(cloud,"bind_restriction",return_value=restricted),\
                 patch.object(cloud,"supervise",side_effect=synthetic_supervisor),\
                 contextlib.redirect_stdout(io.StringIO()) as stdout:
                self.assertEqual(cloud.run(),0)
            raw=(temp/"wp1-cloud"/"metadata_inventory.json").read_bytes()
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

