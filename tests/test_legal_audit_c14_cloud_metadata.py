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
    "WP1_CLOUD_ENABLED":"true","GITHUB_SHA":COMMIT,"GITHUB_RUN_ID":"123",
    "GITHUB_RUN_ATTEMPT":"1",
}
EVENT={"inputs":{"operation":cloud.APPROVAL,"revision":cloud.REVISION,"code_commit":COMMIT}}


class CloudTests(unittest.TestCase):
    def test_exact_dispatch_scope(self):
        result=cloud.scope(ENV,EVENT)
        self.assertEqual(result["roots"],list(cloud.STORES))
        self.assertEqual(result["revision"],cloud.REVISION)

    def test_reject_wrong_boundary(self):
        for name,value in (("GITHUB_EVENT_NAME","pull_request"),("GITHUB_REPOSITORY","other/repo"),
                           ("GITHUB_REF","refs/heads/main"),("RUNNER_OS","Windows"),
                           ("WP1_CLOUD_ENABLED","false"),("GITHUB_RUN_ATTEMPT","2"),
                           ("GITHUB_SHA","b"*40)):
            with self.subTest(name=name),self.assertRaises(ValueError):
                cloud.scope(dict(ENV,**{name:value}),EVENT)
        for name,value in (("revision","b"*40),("operation","UPLOAD"),("code_commit","b"*40)):
            with self.subTest(name=name),self.assertRaises(ValueError):
                cloud.scope(ENV,{"inputs":dict(EVENT["inputs"],**{name:value})})

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

if __name__=="__main__":unittest.main()
