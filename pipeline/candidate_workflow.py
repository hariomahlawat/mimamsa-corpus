"""Bounded candidate workflow for an explicitly enumerated, isolated input set.

No network, release writer, active corpus discovery or production CLI. Caller
must supply a reviewed input manifest and a dedicated candidate journal.
"""
from __future__ import annotations

import hashlib
import json
import re

from .assessment_register import canonical, check_assessment, valid_hash
from .shadow_assessment import assess
from .candidate_release_guard import preflight

MAX_DOCUMENTS = 15
MAX_DECLARED_BYTES = 100_000_000
MAX_PAGES = 500
ROOT_FIELDS = {'schema', 'purpose', 'documents'}
ROW_FIELDS = {'metadata', 'declared_bytes', 'previous_event_id', 'recovery_state'}
META_FIELDS = {'doc_id', 'sha256', 'raw_path', 'page_count', 'title'}
RECOVERY = {'NEW_CANDIDATE', 'HISTORICALLY_EXCLUDED_CANDIDATE'}


def run_candidates(root, manifest_bytes, *, expected_sha256, journal, restricted):
    """Run actual default classifier and persist candidate events.

    The manifest digest binds scope, not owner approval. Only synthetic or
    separately approved isolated inputs may be supplied. The restriction
    predicate must come from the pinned project register. No unrestricted
    fallback. A journal may persist completed events even if a later item
    fails; the caller must audit it, not treat partial work as a complete run.
    """
    if not isinstance(manifest_bytes, bytes) or not 0 < len(manifest_bytes) <= 262144:
        raise ValueError('bounded manifest bytes required')
    if hashlib.sha256(manifest_bytes).hexdigest() != expected_sha256:
        raise ValueError('manifest digest mismatch')

    def no_duplicates(pairs):
        d = {}
        for k, v in pairs:
            if k in d:
                raise ValueError('duplicate JSON key')
            d[k] = v
        return d

    manifest = json.loads(manifest_bytes, object_pairs_hook=no_duplicates)
    if (not isinstance(manifest, dict) or set(manifest) != ROOT_FIELDS
            or manifest['schema'] != 'c14-candidate-batch-v1'
            or manifest['purpose'] != 'ISOLATED_CANDIDATE_REVIEW'):
        raise ValueError('unexpected manifest')
    rows = manifest['documents']
    if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_DOCUMENTS:
        raise ValueError('document cap')
    total = 0
    pages = 0
    ids = set()
    permitted = []
    restricted_count = 0
    for row in rows:
        if not isinstance(row, dict) or set(row) != ROW_FIELDS:
            raise ValueError('unexpected document fields')
        m = row['metadata']
        if not isinstance(m, dict) or set(m) != META_FIELDS:
            raise ValueError('unexpected metadata fields')
        doc = m['doc_id']
        if (not isinstance(doc, str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,120}', doc)
                or doc in ids or not valid_hash(m['sha256'])
                or not isinstance(m['raw_path'], str)
                or not re.fullmatch(r'data/raw/[A-Za-z0-9_./-]+\.pdf',m['raw_path'])
                or any(s in ('','.','..') for s in m['raw_path'].split('/'))
                or not isinstance(m['title'],str) or len(m['title']) > 2000
                or type(m['page_count']) is not int or not 1 <= m['page_count'] <= MAX_PAGES):
            raise ValueError('invalid metadata or duplicate document identity')
        ids.add(doc)
        n = row['declared_bytes']
        prev = row['previous_event_id']
        if (type(n) is not int or not 0 < n <= 50_000_000
                or (prev is not None and not valid_hash(prev))
                or row['recovery_state'] not in RECOVERY):
            raise ValueError('invalid scope row')
        total += n
        pages += m['page_count']
        if total > MAX_DECLARED_BYTES or pages > MAX_PAGES:
            raise ValueError('aggregate declared scope cap')
        if restricted(doc_id=doc,sha256=m['sha256'],path=m['raw_path']):
            restricted_count += 1
            continue
        permitted.append(row)

    journal.audit()
    results = []
    for row in permitted:
        m = row['metadata']
        # The assessment rehashes the bytes it parses. Declared-size and page
        # budgets are preflight checks, not process-level resource isolation.
        from pathlib import Path
        base = Path(root).resolve()
        path = base / m['raw_path']
        if path.resolve() != path:
            raise ValueError('path containment failure')
        if path.stat().st_size != row['declared_bytes']:
            raise ValueError('declared size mismatch')
        a = check_assessment(assess(base,m))
        eid = journal.append(a,previous_event_id=row['previous_event_id'])
        results.append({'doc_id':m['doc_id'],'source_sha256':m['sha256'],
                        'assessment_id':a['assessment_id'],'event_id':eid,
                        'recovery_state':row['recovery_state'],
                        'relevance':a['relevance'],'research_eligible':False})
    guard = preflight([{'kind':'report','record':x} for x in results],workstream='C14')
    out = {'schema':'c14-candidate-run-v1','manifest_sha256':expected_sha256,
           'status':'CANDIDATE_ONLY_NOT_RELEASED','documents':results,
           'restricted_omitted_count':restricted_count,'journal':journal.audit(),
           'release_allowed':guard['release_allowed'],'research_eligible':False}
    out['receipt_sha256'] = hashlib.sha256(canonical(out)).hexdigest()
    return out
