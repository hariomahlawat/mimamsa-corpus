import hashlib
import json
import unittest
from datetime import datetime, timezone
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from approval_gate import verify, REPO, OP


class ApprovalTests(unittest.TestCase):
    def setUp(self):
        self.keys = {r: Ed25519PrivateKey.generate() for r in ('owner', 'independent_reviewer')}
        self.pub = {r: k.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw) for r, k in self.keys.items()}
        self.trust = {r: hashlib.sha256(k).hexdigest() for r, k in self.pub.items()}
        self.d = dict(version=1, repository=REPO, operation=OP, code_commit='a'*40,
                      plan_sha256='b'*64, inventory_sha256='c'*64, target_ids=['C14-D01'],
                      issued_utc='2026-11-26T01:00:00Z', expires_utc='2026-11-26T02:00:00Z',
                      hf_writes=False, legal_promotions=False)
        self.args = dict(code_commit='a'*40, plan_sha256='b'*64, inventory_sha256='c'*64,
                         target_ids=['C14-D01'], now=datetime(2026,11,26,1,30,tzinfo=timezone.utc))

    def signed(self):
        body = json.dumps(self.d).encode()
        return body, {r: k.sign(body) for r,k in self.keys.items()}

    def check(self):
        body,sigs=self.signed()
        return verify(body,sigs,self.pub,self.trust,**self.args)

    def test_valid(self):
        self.assertEqual(self.check(), ('C14-D01',))

    def test_missing_role(self):
        body,sigs=self.signed(); del sigs['owner']
        with self.assertRaises(ValueError): verify(body,sigs,self.pub,self.trust,**self.args)

    def test_tampered_bytes(self):
        body,sigs=self.signed()
        with self.assertRaises(Exception): verify(body+b' ',sigs,self.pub,self.trust,**self.args)

    def test_wrong_plan(self):
        self.args['plan_sha256']='d'*64
        with self.assertRaises(ValueError): self.check()

    def test_wrong_inventory(self):
        self.args['inventory_sha256']='d'*64
        with self.assertRaises(ValueError): self.check()

    def test_wrong_code(self):
        self.args['code_commit']='d'*40
        with self.assertRaises(ValueError): self.check()

    def test_wrong_target(self):
        self.args['target_ids']=['C14-D03']
        with self.assertRaises(ValueError): self.check()

    def test_expired(self):
        self.args['now']=datetime(2026,11,26,2,0,tzinfo=timezone.utc)
        with self.assertRaises(ValueError): self.check()

    def test_untrusted_key(self):
        self.trust['owner']='0'*64
        with self.assertRaises(ValueError): self.check()

    def test_write_permission_denied(self):
        self.d['hf_writes']=True
        with self.assertRaises(ValueError): self.check()

    def test_same_key_denied(self):
        self.pub['independent_reviewer']=self.pub['owner']
        with self.assertRaises(ValueError): self.check()

    def test_duplicate_json_denied(self):
        body=json.dumps(self.d).encode().replace(b'{', b'{"version": 1, ',1)
        sigs={r:k.sign(body) for r,k in self.keys.items()}
        with self.assertRaises(ValueError): verify(body,sigs,self.pub,self.trust,**self.args)

if __name__ == '__main__': unittest.main()
