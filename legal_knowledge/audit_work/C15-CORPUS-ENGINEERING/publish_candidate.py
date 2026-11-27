"""Publish a write-once, candidate-only package and verify it from the exact revision."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

from huggingface_hub import CommitOperationAdd, HfApi, hf_hub_download

BRANCH='cycle15-candidates'

def digest(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('package',type=Path)
    p.add_argument('generation')
    p.add_argument('base')
    p.add_argument('receipt',type=Path)
    a=p.parse_args()
    if not re.fullmatch(r'v[1-9][0-9]*',a.generation) or not re.fullmatch(r'[a-f0-9]{40}',a.base):
        raise ValueError('Expected a version and verified corpus commit')
    repo='hariomahlawat/mimamsa-corpus'
    token=os.environ['HF_TOKEN']
    api=HfApi(token=token)
    assert api.dataset_info(repo,revision=a.base).private
    api.create_branch(repo,branch=BRANCH,revision=a.base,repo_type='dataset',exist_ok=True)
    head=api.dataset_info(repo,revision=BRANCH).sha
    prefix=f'legal_knowledge/candidates/cycle15/{a.generation}'
    files={f'{prefix}/{file.name}':file for file in sorted(a.package.iterdir()) if file.is_file() and not file.is_symlink()}
    if len(files)<5 or not files:
        raise ValueError('Insufficient package artifacts')
    digests={k:digest(v) for k,v in files.items()}
    if a.receipt.exists():
        previous=json.loads(a.receipt.read_bytes())
        assert previous['sha256']==digests
        revision=previous['revision']
    else:
        if any(api.file_exists(repo,path,repo_type='dataset',revision=head) for path in files):
            raise ValueError('Generation already exists. Supply its receipt or choose a new version.')
        out=api.create_commit(repo,[CommitOperationAdd(path_in_repo=k,path_or_fileobj=v) for k,v in files.items()],
                              repo_type='dataset',revision=BRANCH,parent_commit=head,
                              commit_message=f'Preserve isolated Cycle 15 candidates {a.generation}')
        revision=out.oid
    receipt={'branch':BRANCH,'namespace':prefix,'revision':revision,'corpus_snapshot':a.base,
             'parent':head,'sha256':digests,'verified':False,'application_eligible':False}
    partial=a.receipt.with_suffix('.pending')
    partial.write_text(json.dumps(receipt,indent=2)+'\n')
    partial.replace(a.receipt)
    with tempfile.TemporaryDirectory() as tmp:
        working=Path(tmp)
        for remote,expected in digests.items():
            for delay in (0,2,6,14,30):
                if delay:time.sleep(delay)
                try:
                    file=Path(hf_hub_download(repo,remote,revision=revision,repo_type='dataset',token=token,
                                             force_download=True,cache_dir=working/'cache'))
                    if digest(file)!=expected:
                        raise ValueError('Downloaded artifact mismatch')
                    shutil.copyfile(file,working/Path(remote).name)
                    break
                except Exception as exc:
                    if delay==30:
                        raise RuntimeError(f'Pinned artifact read-back failed: {type(exc).__name__}') from None
        subprocess.run([sys.executable,'-I','portable_package.py','rebuild','.', 'reconstructed'],
                       cwd=working,env={'PATH':os.environ['PATH']},check=True)
        receipt['reconstruction']=json.loads((working/'reconstructed'/'receipt.json').read_bytes())
    receipt['verified']=True
    partial.write_text(json.dumps(receipt,indent=2)+'\n')
    partial.replace(a.receipt)
    print(revision,len(files))

if __name__=='__main__':
    main()
