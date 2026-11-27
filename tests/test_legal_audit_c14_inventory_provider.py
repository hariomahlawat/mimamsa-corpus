"""Metadata adapter tests: no HF network or file content access."""
from pathlib import Path
from types import SimpleNamespace as Obj
from urllib.parse import unquote
from unittest.mock import patch
from importlib.util import find_spec
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

    def test_pdf_suffix_case_preserves_exact_provider_path(self):
        class UppercaseFiles(Api):
            def list_repo_tree(self, *args, **kwargs):
                for item in super().list_repo_tree(*args, **kwargs):
                    if hasattr(item, 'size'):
                        item.path = item.path.removesuffix('.pdf') + '.PDF'
                    yield item

        result = inventory(UppercaseFiles(), REV, lambda **kw: False)
        self.assertTrue(result['coverage_of_supplied_scope'])
        self.assertEqual(len(result['claims']), len(STORES))
        self.assertTrue(all(row['path'].endswith('/fixture.PDF') for row in result['claims']))

    def test_folder_rows_count_toward_the_inventory_budget(self):
        class FolderTree(Api):
            folders_seen = 0

            def list_repo_tree(self, *args, **kwargs):
                if kwargs['recursive']:
                    for number in range(20):
                        self.folders_seen += 1
                        yield Obj(path=f"{kwargs['path_in_repo']}/folder{number}")
                yield from super().list_repo_tree(*args, **kwargs)

        api = FolderTree()
        with patch('hf_inventory_provider.MAX_ENTRIES', 10):
            result = inventory(api, REV, lambda **kw: False)
        self.assertFalse(result['coverage_of_supplied_scope'])
        self.assertLess(api.folders_seen, 20)
        self.assertEqual(result['enumeration_failures'][0]['error_type'], 'ValueError')

    def test_recursive_folder_must_be_inside_its_scope(self):
        class MisroutedTree(Api):
            def list_repo_tree(self, *args, **kwargs):
                if kwargs['recursive']:
                    yield Obj(path='outside-fixture-store/folder')
                yield from super().list_repo_tree(*args, **kwargs)

        result = inventory(MisroutedTree(), REV, lambda **kw: False)
        self.assertFalse(result['coverage_of_supplied_scope'])
        self.assertEqual(result['enumeration_failures'][0]['error_type'], 'ValueError')
        self.assertNotIn('outside-fixture-store', str(result))

    @unittest.skipUnless(find_spec('huggingface_hub'), 'optional pinned HF SDK')
    def test_sdk_parses_two_pages_of_tree_metadata(self):
        from huggingface_hub import HfApi
        from httpx2 import Request, Response

        dataset_url = f'{ENDPOINT}/api/datasets/{REPO}'
        info_url = f'{dataset_url}/revision/{REV}'
        tree_url = f'{dataset_url}/tree/{REV}/'
        first_store = STORES[0]
        metadata_requests = []

        def respond(method, url, **kwargs):
            metadata_requests.append(url)
            self.assertEqual(method, 'GET')
            self.assertNotIn('authorization', kwargs['headers'])
            if url == info_url:
                data = {'id': REPO, 'sha': REV, 'private': True}
                return Response(200, json=data, request=Request(method, url))

            self.assertTrue(url.startswith(tree_url), url)
            path, _, cursor = unquote(url.removeprefix(tree_url)).partition('?')
            folders = [
                {'path': store, 'oid': '0' * 40, 'type': 'directory'}
                for store in STORES if store.rsplit('/', 1)[0] == path
            ]
            headers = {}
            if folders:
                data = folders
            else:
                self.assertIn(path, STORES)
                suffix = 'second.pdf' if cursor else 'fixture.pdf'
                data = [{
                    'path': f'{path}/{suffix}', 'oid': '0' * 40, 'type': 'file',
                    'size': 10, 'lfs': {'oid': 'b' * 64, 'size': 10, 'pointerSize': 130},
                }]
                if path == first_store and not cursor:
                    headers['Link'] = f'<{url}?cursor=page2>; rel="next"'
            return Response(200, json=data, headers=headers, request=Request(method, url))

        api = HfApi(endpoint=ENDPOINT, token=False)
        session = Obj(get=lambda url, **kwargs: respond('GET', url, **kwargs))
        with patch('huggingface_hub.hf_api.get_session', return_value=session), \
             patch('huggingface_hub.utils._pagination.http_backoff', side_effect=respond):
            result = inventory(api, REV, lambda **kw: False)
        self.assertTrue(result['coverage_of_supplied_scope'])
        self.assertEqual(len(result['claims']), len(STORES) + 1)
        self.assertEqual(result['known_sha256'], ['b' * 64])
        self.assertEqual(len(metadata_requests), 12)

if __name__=='__main__':unittest.main()
