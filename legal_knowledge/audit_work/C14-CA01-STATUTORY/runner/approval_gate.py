"""Offline verification of independently signed, narrowly scoped acquisition consent.

No private key, trust configuration, network client or automatic activation.
The operator must provision trusted owner/reviewer public keys outside the repo.
"""
from __future__ import annotations
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone

HEX64 = re.compile(r'[0-9a-f]{64}\Z')
HEX40 = re.compile(r'[0-9a-f]{40}\Z')
REPO = 'hariomahlawat/mimamsa-corpus'
OP = 'FETCH_PUBLIC_SOURCE_TO_LOCAL_QUARANTINE'


def verify(payload, signatures, public_keys, trust_fingerprints, *, code_commit,
           plan_sha256, inventory_sha256, target_ids, now):
    """Return the exact authorized IDs or raise. Trust pins are external inputs.

    The signed payload is raw UTF-8 JSON bytes; no normalization. The caller
    must establish code/plan/inventory provenance and independently protected
    trust configuration before using this function. No network is performed.
    """
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    roles = {'owner', 'independent_reviewer'}
    if any(set(m) != roles for m in (signatures, public_keys, trust_fingerprints)):
        raise ValueError('two independently trusted roles required')
    if public_keys['owner'] == public_keys['independent_reviewer']:
        raise ValueError('distinct keys required')
    if not isinstance(payload, bytes) or not 0 < len(payload) <= 16384:
        raise ValueError('bounded exact approval bytes required')
    for role in roles:
        key = public_keys[role]
        if not isinstance(key, bytes) or len(key) != 32:
            raise ValueError('raw Ed25519 public key required')
        if hashlib.sha256(key).hexdigest() != trust_fingerprints[role]:
            raise ValueError('untrusted public key')
        Ed25519PublicKey.from_public_bytes(key).verify(signatures[role], payload)

    def unique(pairs):
        d = {}
        for k, v in pairs:
            if k in d:
                raise ValueError('duplicate JSON key')
            d[k] = v
        return d

    d = json.loads(payload.decode('utf-8'), object_pairs_hook=unique)
    fields = {'version', 'repository', 'operation', 'code_commit', 'plan_sha256',
              'inventory_sha256', 'target_ids', 'issued_utc', 'expires_utc',
              'hf_writes', 'legal_promotions'}
    if set(d) != fields or type(d['version']) is not int or d['version'] != 1:
        raise ValueError('unexpected approval schema')
    if (d['repository'] != REPO or d['operation'] != OP or
            d['hf_writes'] is not False or d['legal_promotions'] is not False):
        raise ValueError('operation not permitted')
    if not HEX40.fullmatch(code_commit) or not HEX64.fullmatch(plan_sha256) or not HEX64.fullmatch(inventory_sha256):
        raise ValueError('invalid immutable pins')
    if (d['code_commit'], d['plan_sha256'], d['inventory_sha256']) != (code_commit, plan_sha256, inventory_sha256):
        raise ValueError('approval is for another code, scope or inventory')
    ids = d['target_ids']
    if (not isinstance(ids, list) or not ids or len(ids) > 6 or
            any(not isinstance(x, str) or not re.fullmatch(r'C14-D0[134567]', x) for x in ids) or
            len(set(ids)) != len(ids) or tuple(ids) != tuple(target_ids)):
        raise ValueError('target set mismatch')
    if now.tzinfo is None or now.utcoffset() != timedelta(0):
        raise ValueError('UTC clock required')
    def utc(s):
        if not isinstance(s, str) or not re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ', s):
            raise ValueError('canonical UTC timestamp required')
        return datetime.strptime(s, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
    issued, expires = utc(d['issued_utc']), utc(d['expires_utc'])
    if not issued <= now < expires or expires - issued > timedelta(hours=24):
        raise ValueError('approval expired, premature or exceeds duration')
    return tuple(ids)
