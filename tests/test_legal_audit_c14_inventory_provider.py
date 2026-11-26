"""Metadata adapter tests: no HF network or file content access."""
from pathlib import Path
from types import SimpleNamespace as Obj
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'legal_knowledge/audit_work/C14-CA01-STATUTORY/runner'))
from hf_inventory_provider import inventory,ENDPOINT
from hf_inventory_metadata import REPO,STORES

REV='a'*40

class Api:
    endpoint=ENDPOINT
    def __init__(self):
        self.calls=[]
        self.extra=False
        self.sha=REV
    def dataset_info(self,repo,*,revision):
        self.calls.append(('info',repo,revision))
        return Obj(id=repo,sha=self.sha,private=True)
    def list_repo_tree(self,repo,*,path_in_repo,recursive,expand,revision,repo_type):
        self.calls.append(('tree',repo,path_in_repo,revision))
        assert repo==REPO and revision==REV and not expand and repo_type=='dataset'
        if not recursive:
            for store in STORES:
                if store.rsplit('/',1)[0]==path_in_repo:
                    yield Obj(path=store)
            if self.extra:yield Obj(path=path_in_repo+'/unexpected')
        else:
            yield Obj(path=path_in_repo+'/fixture.pdf',size=10,lfs=Obj(sha256='b'*64,size=10))

class ProviderTests(unittest.TestCase):
    def test_pinned_metadata_only(self):
        api=Api()
        result=inventory(api,REV,lambda **kw:False)
        self.assertTrue(result['coverage_of_supplied_scope'])
        self.assertEqual(len(result['claims']),7)
        self.assertFalse(result['acquisition_eligible'])
        self.assertEqual(len(api.calls),11)
        self.assertEqual(result['source_downloads'],0)
    def test_unknown_root_denied(self):
        api=Api();api.extra=True
        with self.assertRaises(ValueError):inventory(api,REV,lambda **kw:False)
    def test_wrong_revision_denied(self):
        api=Api();api.sha='c'*40
        with self.assertRaises(ValueError):inventory(api,REV,lambda **kw:False)
    def test_wrong_endpoint_denied(self):
        api=Api();api.endpoint='https://example.invalid'
        with self.assertRaises(ValueError):inventory(api,REV,lambda **kw:False)

if __name__=='__main__':unittest.main()
