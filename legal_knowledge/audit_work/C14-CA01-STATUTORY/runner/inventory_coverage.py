"""Check metadata-only deduplication inventory coverage; never download source bytes.

Input is a separately attested, revision-pinned enumeration of permitted PDF
paths plus SHA-256 claims. A claimed LFS digest is not an independent byte read.
Unknown or incomplete scope always blocks acquisition eligibility.
"""
from __future__ import annotations
import hashlib
import json
import re

HEX64 = re.compile(r'[0-9a-f]{64}\Z')
HEX40 = re.compile(r'[0-9a-f]{40}\Z')


def reconcile(expected, claims, *, revision, required_stores, enumerated_stores):
    if not isinstance(revision, str) or not HEX40.fullmatch(revision):
        raise ValueError('exact HF revision required')
    required = set(required_stores)
    if not required:
        raise ValueError('nonempty approved store scope required')
    enumerated = set(enumerated_stores)
    if enumerated - required:
        raise ValueError('unapproved store enumerated')
    def key(row):
        store, path = row['store'], row['path']
        if (store not in required or not isinstance(path, str) or not path.endswith('.pdf')
                or path.startswith('/') or '\\' in path
                or any(s in ('', '.', '..') for s in path.split('/'))):
            raise ValueError('invalid or unapproved inventory path')
        return store, path
    wanted = {}
    for row in expected:
        k = key(row)
        if k in wanted:
            raise ValueError('duplicate enumerated path')
        if type(row['bytes']) is not int or row['bytes'] <= 0:
            raise ValueError('invalid expected size')
        wanted[k] = row['bytes']
    seen = {}
    for row in claims:
        k = key(row)
        if k in seen or k not in wanted:
            raise ValueError('duplicate or unexpected claim')
        seen[k] = row
    missing, hashes, bad = [], [], []
    for k, size in sorted(wanted.items()):
        row = seen.get(k)
        if row is None:
            missing.append({'store': k[0], 'path': k[1]})
            continue
        digest = row.get('sha256')
        if (row.get('revision') != revision or row.get('bytes') != size or
                not isinstance(digest, str) or not HEX64.fullmatch(digest) or
                row.get('basis') not in ('HF_LFS_POINTER', 'REVISION_PINNED_BYTE_READ')):
            bad.append({'store': k[0], 'path': k[1]})
            continue
        hashes.append({'store': k[0], 'path': k[1], 'bytes': size,
                       'sha256': digest, 'basis': row['basis']})
    counts = {s: {'expected': sum(k[0] == s for k in wanted),
                  'valid_claims': sum(x['store'] == s for x in hashes)} for s in sorted(required)}
    complete = bool(wanted) and not missing and not bad and enumerated == required
    result = {'revision': revision, 'coverage_of_supplied_scope': complete,
              'scope_independently_attested': False, 'acquisition_eligible': False,
              'required_stores': sorted(required), 'unlisted_stores': sorted(required - enumerated),
              'counts': counts, 'missing': missing, 'invalid': bad, 'claims': hashes,
              'known_sha256': sorted(set(x['sha256'] for x in hashes)),
              'limits': 'Expected paths, store coverage and revision attribution require independent attestation; a miss is not proof of non-duplication.'}
    result['inventory_sha256'] = hashlib.sha256(json.dumps(result, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()
    return result
