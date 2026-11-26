"""Metadata-only SDK adapter; deliberately not wired to an executable CLI.

No source downloads or writes. Use a read-only credential and approved
revision in a separately supervised local process after independent review.
"""
from __future__ import annotations
from hf_inventory_metadata import REPO, STORES, HEX40, MAX_ENTRIES, collect, path_in_store

ENDPOINT = 'https://huggingface.co'


def inventory(api, revision, restricted):
    if not isinstance(revision,str) or not HEX40.fullmatch(revision):
        raise ValueError('explicit full revision required')
    if getattr(api,'endpoint',None) != ENDPOINT:
        raise ValueError('unexpected SDK endpoint')
    def info():
        i=api.dataset_info(REPO,revision=revision)
        if i.sha!=revision or i.private is not True or i.id!=REPO:
            raise ValueError('dataset identity/revision mismatch')

    tree_entries_seen = 0

    def checked_entries(path, *, recursive):
        nonlocal tree_entries_seen
        for entry in api.list_repo_tree(REPO, path_in_repo=path, recursive=recursive,
                                        expand=False, revision=revision, repo_type='dataset'):
            tree_entries_seen += 1
            if tree_entries_seen > MAX_ENTRIES:
                raise ValueError('tree entry budget exceeded')
            if not path_in_store(getattr(entry, 'path', None), path):
                raise ValueError('tree entry outside expected scope')
            yield entry

    info()
    roots={'data/raw','legal_knowledge/preservation'}
    discovered=set()
    unexpected_count=0
    # Verify immediate root directories against scope; ignore no unknown root.
    for root in sorted(roots):
        for entry in checked_entries(root, recursive=False):
            path=entry.path
            if path not in STORES or hasattr(entry,'size'):
                unexpected_count+=1
                continue
            if path in discovered:
                raise ValueError('duplicate store root')
            discovered.add(path)
    if discovered!=set(STORES) or unexpected_count:
        raise ValueError('known storage scope differs from pinned tree')
    def tree(store,rev):
        if store not in STORES or rev!=revision:
            raise ValueError('unapproved metadata scope')
        for item in checked_entries(store, recursive=True):
            # The SDK's RepoFolder has no size.
            if not hasattr(item,'size'):
                continue
            lfs=getattr(item,'lfs',None)
            yield (item.path,item.size,getattr(lfs,'sha256',None),getattr(lfs,'size',None))
    result=collect(tree,revision,restricted)
    info()
    result.pop('inventory_sha256',None)
    result.update(provider='HF_SDK_METADATA_ONLY',source_downloads=0,hf_writes=0,
                  tree_entries_seen=tree_entries_seen,
                  root_scope_matches=True,scope_independently_attested=False,
                  acquisition_eligible=False)
    import json,hashlib
    result['inventory_sha256']=hashlib.sha256(json.dumps(result,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    return result
