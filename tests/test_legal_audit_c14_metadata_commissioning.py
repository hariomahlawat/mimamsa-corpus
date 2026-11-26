"""WP1 synthetic protocol and supervisor tests; no live metadata or credentials."""
import json
import hashlib
import sys
import tempfile
import unittest
from email.message import Message
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import urlsplit,parse_qs,quote,unquote
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'legal_knowledge/audit_work/C14-CA01-STATUTORY/runner'))
from hf_metadata_transport import MetadataAPI, ENDPOINT, REPO, STORES
from hf_metadata_job import DirectMetadataHTTPS, collect_receipt, supervise, bind_restriction, git_blob, save_candidate_receipt

REV='a'*40
BASE=f'{ENDPOINT}/api/datasets/{REPO}'
TREE=f'{BASE}/tree/{REV}/'
def encode(x):return json.dumps(x).encode()

class ProtocolTests(unittest.TestCase):
    def test_full_metadata_inventory_and_pagination(self):
        calls=[]
        def exchange(url,cap,remaining):
            calls.append(url)
            self.assertGreater(cap,0)
            self.assertGreater(remaining,0)
            u=urlsplit(url)
            if url==f'{BASE}/revision/{REV}':
                return encode(dict(id=REPO,sha=REV,private=True)),None
            store=unquote(u.path.split('/tree/'+REV+'/',1)[1])
            q=parse_qs(u.query)
            self.assertEqual(q['expand'],['false'])
            if store not in STORES:
                return encode([dict(path=s,type='directory') for s in STORES
                               if s.rsplit('/',1)[0]==store]),None
            suffix='page2.pdf' if 'cursor' in q else 'fixture.pdf'
            link=None
            if store==STORES[0] and 'cursor' not in q:
                link=f'<{TREE}{quote(store, safe="")}?cursor=next%2Btoken>; rel="next"'
            return encode([dict(path=store+'/'+suffix,type='file',size=10,
                               lfs=dict(oid='b'*64,size=10))]),link
        r=collect_receipt(REV,exchange,lambda **kw:False)
        self.assertTrue(r['coverage_of_supplied_scope'])
        self.assertEqual(len(r['claims']),8)
        self.assertEqual(r['metadata_requests'],12)
        self.assertFalse(r['acquisition_eligible'])
        self.assertEqual(r['source_downloads'],0)
        self.assertTrue(any('cursor=next%2Btoken' in u for u in calls))
        with tempfile.TemporaryDirectory() as tmp:
            # Windows hosted TEMP may be expressed using an 8.3 alias.
            # Supply the canonical fixture path; do not relax the writer's guard.
            job=Path(tmp).resolve(strict=True)
            summary=save_candidate_receipt(r,revision=REV,restricted=lambda **kw:False,job_dir=job)
            self.assertFalse(summary['acquisition_eligible'])
            self.assertEqual(summary['receipt_sha256'],hashlib.sha256((job/'metadata_inventory.json').read_bytes()).hexdigest())
            with self.assertRaises(ValueError):save_candidate_receipt(r,revision=REV,restricted=lambda **kw:False,job_dir=job)
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                save_candidate_receipt(r,revision=REV,restricted=lambda **kw:True,job_dir=Path(tmp).resolve(strict=True))
            self.assertEqual(list(Path(tmp).iterdir()),[])
            altered=dict(r,coverage_of_supplied_scope=False)
            with self.assertRaises(ValueError):
                save_candidate_receipt(altered,revision=REV,restricted=lambda **kw:False,job_dir=Path(tmp).resolve(strict=True))


    def tree(self,api):
        return list(api.list_repo_tree(REPO,path_in_repo=STORES[0],recursive=True,
                                       expand=False,revision=REV,repo_type='dataset'))

    def test_continuation_scope_denied_before_second_request(self):
        for dest in ('https://example.invalid/x',TREE+quote(STORES[1],safe=''),
                     TREE.replace(REV,'c'*40)+quote(STORES[0],safe=''),
                     TREE+quote(STORES[0],safe='')+'?recursive=false&cursor=x',
                     TREE+quote(STORES[0],safe='')+'?cursor=x&cursor=y'):
            with self.subTest(dest=dest):
                calls=[]
                def ex(url,cap,remaining):
                    calls.append(url)
                    return b'[]',f'<{dest}>; rel="next"'
                with self.assertRaises(ValueError):self.tree(MetadataAPI(REV,ex))
                self.assertEqual(len(calls),1)

    def test_empty_page_budget_and_loop(self):
        n=[0]
        def exchange(url,cap,remaining):
            n[0]+=1
            return b'[]',f'<{TREE}{quote(STORES[0],safe="")}?cursor={n[0]}>; rel="next"'
        with patch('hf_metadata_transport.MAX_PAGES',3):
            with self.assertRaises(ValueError):self.tree(MetadataAPI(REV,exchange))
        self.assertEqual(n[0],3)
        with self.assertRaises(ValueError):
            self.tree(MetadataAPI(REV,lambda *args:(b'[]',f'<{TREE}{quote(STORES[0],safe="")}?cursor=same>; rel="next"')))

    def test_deadline_and_body_size(self):
        clock=[0]
        def slow(*args):
            clock[0]=181
            return b'[]',None
        with self.assertRaises(TimeoutError):self.tree(MetadataAPI(REV,slow,clock=lambda:clock[0]))
        with patch('hf_metadata_transport.MAX_PAGE_BYTES',2):
            with self.assertRaises(ValueError):self.tree(MetadataAPI(REV,lambda *a:(b'[{}]',None)))

    def test_duplicate_json_key_denied(self):
        with self.assertRaises(ValueError):
            MetadataAPI(REV,lambda *a:(b'{"id":"x","id":"y"}',None)).dataset_info(REPO,revision=REV)

class TransportTests(unittest.TestCase):
    def make(self,status=200,body=b'[]',header=None):
        h=Message()
        h['Content-Type']='application/json'
        if header:h[header[0]]=header[1]
        class Response:
            headers=h
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,n):return body[:n]
        response=Response()
        response.status=status
        calls=[]
        class Conn:
            def request(self,method,path,headers):
                calls.append((method,path,headers))
            def getresponse(self):return response
            def close(self):pass
        def connect(host,port,**kw):
            self.assertEqual((host,port),('huggingface.co',443))
            self.assertTrue(kw['context'].check_hostname)
            return Conn()
        return DirectMetadataHTTPS(REV,'hf_synthetic',connect=connect),calls

    def test_direct_request_no_redirect(self):
        ex,calls=self.make(302)
        with self.assertRaises(ValueError):ex(f'{BASE}/revision/{REV}',100,1)
        self.assertEqual(len(calls),1)

    def test_direct_route_and_query_rejected(self):
        ex,calls=self.make()
        for url in ('https://example.invalid/x',f'{BASE}/resolve/{REV}/fixture.pdf',
                    TREE+quote(STORES[0],safe='')+'?recursive=false&expand=false',
                    f'{BASE}/revision/{REV}?expand=all'):
            with self.assertRaises(ValueError):ex(url,100,1)
        self.assertEqual(calls,[])

    def test_content_length_encoding_and_cap(self):
        for header,body in ((('Content-Length','9'),b'[]'),
                            (('Content-Encoding','gzip'),b'[]'),(None,b'x'*101)):
            ex,calls=self.make(body=body,header=header)
            with self.assertRaises(ValueError):ex(f'{BASE}/revision/{REV}',100,1)

class SupervisorTests(unittest.TestCase):
    def test_timeout_and_error_output(self):
        with self.assertRaisesRegex(TimeoutError,'metadata worker deadline exceeded'):
            supervise([sys.executable,'-c','import time; time.sleep(10)'],seconds=.05)
        with self.assertRaisesRegex(ValueError,'unexpected output'):
            supervise([sys.executable,'-c','import sys; sys.stderr.write("synthetic secret")'])
    def test_valid_candidate_receipt(self):
        r=supervise([sys.executable,'-c','print(\'{"acquisition_eligible":false}\')'])
        self.assertFalse(r['acquisition_eligible'])

    def test_restriction_snapshot_pin(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'config').mkdir()
            (root/'scripts').mkdir()
            config=root/'config/restricted_material.json'
            guard=root/'scripts/restricted_material.py'
            raw=b'fixture'
            src=b'def _load(): return CONFIG.read_text()\ndef is_restricted(**kw): return _load()=="fixture"\n'
            config.write_bytes(raw)
            guard.write_bytes(src)
            with patch('hf_metadata_job.REGISTER_BLOB',git_blob(raw)),patch('hf_metadata_job.GUARD_BLOB',git_blob(src)):
                f=bind_restriction(root)
                config.write_bytes(b'modified')
                self.assertTrue(f())
                with self.assertRaises(ValueError):bind_restriction(root)

if __name__=='__main__':unittest.main()
