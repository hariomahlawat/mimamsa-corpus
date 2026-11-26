"""Offline controls, synthetic metadata and clocks only."""
import sys
import unittest
from pathlib import Path

RUNNER = Path(__file__).resolve().parents[1] / 'legal_knowledge/audit_work/C14-CA01-STATUTORY/runner'
sys.path.insert(0,str(RUNNER))
from hf_inventory_metadata import collect, STORES
from transport_policy import Budget, robots_allows

REV='a'*40

def tree(store,rev):
    assert rev==REV
    yield store+'/fixture.pdf',100,'b'*64,100

def unrestricted(**kw): return False


class InventoryTests(unittest.TestCase):
    def test_complete_supplied_metadata_not_authority(self):
        result=collect(tree,REV,unrestricted)
        self.assertTrue(result['coverage_of_supplied_scope'])
        self.assertFalse(result['acquisition_eligible'])
        self.assertEqual(len(result['claims']),7)
        self.assertEqual(result['known_sha256'],['b'*64])
        self.assertFalse(result['scope_independently_attested'])

    def test_missing_hash_excluded_without_identity(self):
        def provider(store,rev):
            yield from tree(store,rev)
            yield store+'/unknown.pdf',100,None,None
        result=collect(provider,REV,unrestricted)
        self.assertFalse(result['coverage_of_supplied_scope'])
        self.assertEqual(result['unhashed_unclassified_pdf_count'],7)
        self.assertNotIn('unknown.pdf',str(result))

    def test_restricted_omitted(self):
        result=collect(tree,REV,lambda **kw:kw['path'].startswith(STORES[0]+'/'))
        self.assertEqual(result['restricted_excluded_count'],1)
        self.assertEqual(len(result['claims']),6)
        self.assertNotIn(STORES[0]+'/fixture.pdf',str(result))

    def test_failed_enumeration(self):
        def provider(store,rev):
            yield from tree(store,rev)
            raise OSError('synthetic')
        result=collect(provider,REV,unrestricted)
        self.assertFalse(result['coverage_of_supplied_scope'])
        self.assertEqual(result['enumeration_failures'][0]['error_type'],'OSError')

    def test_size_mismatch(self):
        result=collect(lambda s,r:iter([(s+'/fixture.pdf',100,'b'*64,99)]),REV,unrestricted)
        self.assertFalse(result['coverage_of_supplied_scope'])
        self.assertEqual(len(result['missing']),7)

    def test_moving_ref_denied(self):
        with self.assertRaises(ValueError): collect(tree,'main',unrestricted)


class PolicyTests(unittest.TestCase):
    def test_longest_literal_and_allow_tie(self):
        raw=b'User-agent: *\nDisallow: /x\nAllow: /x/public\n'
        self.assertTrue(robots_allows(raw,'https://example.invalid/x/public/a'))
        self.assertFalse(robots_allows(raw,'https://example.invalid/x/private'))
        self.assertTrue(robots_allows(b'User-agent: *\nDisallow: /x\nAllow: /x','https://example.invalid/x'))

    def test_unsupported_syntax_denies(self):
        for raw in (b'User-agent: *\nDisallow: /*.pdf$',b'<html>',b'User-agent: other\nAllow: /',
                    b'User-agent: *\nSitemap: https://example.invalid/sitemap.xml',b''):
            with self.subTest(raw=raw):
                self.assertFalse(robots_allows(raw,'https://example.invalid/a.pdf'))
        self.assertFalse(robots_allows(b'User-agent: *\nDisallow:', 'https://example.invalid/%61.pdf'))

    def test_deadline_and_aggregate_caps(self):
        now=[0.]
        b=Budget(max_seconds=10,max_bytes=5,max_attempts=2,clock=lambda:now[0])
        b.start_attempt()
        b.observe_bytes(3)
        b.start_attempt()
        with self.assertRaises(ValueError):b.start_attempt()
        with self.assertRaises(ValueError):b.observe_bytes(3)
        now[0]=10
        with self.assertRaises(TimeoutError):b.remaining()

if __name__=='__main__':unittest.main()
