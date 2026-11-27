"""Inventory a private Hugging Face corpus at one immutable revision."""
import argparse
import collections
import json
import os
from pathlib import Path
import re

from huggingface_hub import HfApi

def collect(repo,revision):
    api=HfApi(token=os.environ['HF_TOKEN'])
    info=api.dataset_info(repo,revision=revision)
    if not info.private or not re.fullmatch(r'[0-9a-f]{40}',info.sha or ''):
        raise ValueError('Expected a private repository and an immutable pin')
    originals=set()
    text_sources=set()
    unbound=[]
    legacy_digests=set()
    roles=collections.Counter()
    for entry in api.list_repo_tree(repo,repo_type='dataset',revision=info.sha,recursive=True):
        if not hasattr(entry,'size'):
            continue
        path=Path(entry.path)
        parts=path.parts
        if 'preservation' not in parts:
            if path.suffix.lower()=='.pdf':
                value=getattr(entry.lfs,'sha256',None)
                if value and re.fullmatch(r'[0-9a-f]{64}',value):
                    legacy_digests.add(value)
                else:
                    unbound.append(1)
            continue
        group=parts[parts.index('preservation')+1]
        addr=path.parent.name.lower()
        if not re.fullmatch(r'[0-9a-f]{64}',addr):
            if path.suffix.lower()=='.pdf':unbound.append(1)
            continue
        if path.name=='original.pdf':
            lfs_sha=getattr(entry.lfs,'sha256',None)
            if lfs_sha and lfs_sha!=addr:
                raise ValueError('Original address and LFS digest disagree')
            originals.add(addr)
            roles[(group,'original_paths')]+=1
        if path.name=='text.txt':
            text_sources.add(addr)
            roles[(group,'derivative_paths')]+=1
    counts=collections.defaultdict(dict)
    for (group,kind),n in roles.items():
        counts[group][kind]=n
    return {'revision':info.sha,'private':True,'distinct_content_addressed_preservation_originals':len(originals),
            'originals_with_text_paths':len(originals & text_sources),'without_text_paths':len(originals-text_sources),
            'distinct_legacy_lfs_pdf_hashes':len(legacy_digests),
            'distinct_original_or_legacy_lfs_pdf_hashes':len(originals | legacy_digests),
            'other_pdf_paths_without_sha256':len(unbound),'preservation_paths_by_group':dict(counts),
            'byte_verification':'LFS metadata compared where available; full pin read-back is tracked in per-batch receipts',
            'active_application_promotion':False}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('repo')
    p.add_argument('output',type=Path)
    p.add_argument('--revision')
    a=p.parse_args()
    a.output.write_text(json.dumps(collect(a.repo,a.revision),indent=2)+'\n')
