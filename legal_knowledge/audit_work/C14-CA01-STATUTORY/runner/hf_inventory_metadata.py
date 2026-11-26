"""Read-only HF metadata inventory prototype.

No blob download, no write to HF, no credential logging. The CLI is disabled
for live enumeration pending an independently reviewed metadata-only scope.
The pure collector is testable with inert provider callbacks.
"""
from __future__ import annotations
import re
from inventory_coverage import reconcile

REPO = 'hariomahlawat/mimamsa-corpus'
STORES = ('data/raw/hc', 'data/raw/indiacode', 'data/raw/official_copies',
          'data/raw/sci', 'legal_knowledge/preservation/c12_acquired_not_ingested',
          'legal_knowledge/preservation/c13_a7_acquired',
          'legal_knowledge/preservation/c5_working_store')
HEX64 = re.compile(r'[0-9a-f]{64}\Z')
HEX40 = re.compile(r'[0-9a-f]{40}\Z')
MAX_ENTRIES = 30_000


def collect(tree, revision, restricted):
    """tree(store, revision) yields (path, size, lfs_sha256, lfs_size).

    Only metadata from the pinned tree is processed. Provider errors, unknown
    file hashes and incomplete enumerations prevent coverage. The restriction
    predicate must be the pinned project register; restricted identities are
    not serialized into the report.
    """
    if not isinstance(revision, str) or not HEX40.fullmatch(revision):
        raise ValueError('exact revision required')
    expected, claims, enumerated, failures = [], [], [], []
    excluded_count = 0
    unhashed_excluded_count = 0
    total = 0
    for store in STORES:
        try:
            for path, size, digest, lfs_size in tree(store, revision):
                total += 1
                if total > MAX_ENTRIES:
                    raise ValueError('entry budget exceeded')
                if (not isinstance(path, str) or not path.startswith(store+'/')
                        or '\\' in path or any(p in ('', '.', '..') for p in path.split('/'))):
                    raise ValueError('path outside approved root')
                if not path.lower().endswith('.pdf'):
                    continue
                # The existing reconcile contract accepts lowercase .pdf only.
                if restricted(path=path, sha256=digest if isinstance(digest,str) else None):
                    excluded_count += 1
                    continue
                if not isinstance(digest, str) or not HEX64.fullmatch(digest):
                    # Without a digest we cannot exclude restricted content by
                    # hash; do not emit its path in a transferable receipt.
                    unhashed_excluded_count += 1
                    continue
                if not path.endswith('.pdf') or type(size) is not int or size <= 0:
                    raise ValueError('unsupported metadata entry')
                expected.append(dict(store=store,path=path,bytes=size))
                if type(lfs_size) is int and lfs_size == size:
                    claims.append(dict(store=store,path=path,bytes=size,revision=revision,
                                       sha256=digest,basis='HF_LFS_POINTER'))
            enumerated.append(store)
        except Exception as exc:
            failures.append({'store':store,'error_type':type(exc).__name__})
            # Fail closed, stop the traversal on provider error.
            break
    result = reconcile(expected,claims,revision=revision,required_stores=STORES,
                       enumerated_stores=enumerated)
    result.pop('inventory_sha256',None)
    result.update(provider_entries_seen=total,restricted_excluded_count=excluded_count,
                  unhashed_unclassified_pdf_count=unhashed_excluded_count,
                  enumeration_failures=failures,
                  local_store_coverage='NOT_ATTESTED',
                  scope_independently_attested=False, acquisition_eligible=False)
    if failures or unhashed_excluded_count:
        result['coverage_of_supplied_scope'] = False
    import hashlib,json
    result['inventory_sha256']=hashlib.sha256(json.dumps(result,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    return result


def main():
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--execute-metadata-only',action='store_true')
    args=p.parse_args()
    if args.execute_metadata_only:
        p.error('C14 metadata enumeration interlock: pinned scope and provider review required')
    print('Dry run: seven known store roots; no network, no file writes.')
    for root in STORES:
        print(root)


if __name__=='__main__':
    main()
