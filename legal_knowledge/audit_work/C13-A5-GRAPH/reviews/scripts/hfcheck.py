import sys, hashlib, os, json
from huggingface_hub import HfApi, hf_hub_download
api=HfApi(); repo='hariomahlawat/mimamsa-corpus'; NEW='844383f55d3b8e61068c3c786a69e8160061cc32'; PAR='3864faf3bb24edef4bfb18fa0916cc788eb68d79'
out=sys.argv[1]
info=api.dataset_info(repo, revision=NEW); print('resolved', info.sha)
commits=api.list_repo_commits(repo, repo_type='dataset')
ids=[c.commit_id for c in commits]
print('head', ids[0][:8], 'NEW idx', ids.index(NEW) if NEW in ids else None, 'PAR idx', ids.index(PAR) if PAR in ids else None)
fa={x for x in api.list_repo_files(repo, repo_type='dataset', revision=PAR)}
fb={x for x in api.list_repo_files(repo, repo_type='dataset', revision=NEW)}
print('parent files',len(fa),'new files',len(fb),'removed',len(fa-fb),'added',sorted(fb-fa))
def tree(rev, path):
    return {e.path:(getattr(e,'blob_id',None) or getattr(e,'oid',None), getattr(e,'lfs',None) and e.lfs.sha256) for e in api.list_repo_tree(repo, path_in_repo=path, repo_type='dataset', revision=rev, recursive=True) if hasattr(e,'size')}
ta=tree(PAR,'data/meta'); tb=tree(NEW,'data/meta')
print('data/meta entries', len(ta), len(tb), 'identical', ta==tb)
# also full-tree blob compare for common files
TA=tree(PAR,''); TB=tree(NEW,'')
chg=[p for p in TA if p in TB and TA[p]!=TB[p]]
print('common files changed', len(chg), chg[:5])
for p in sorted(fb-fa):
    lp=hf_hub_download(repo, p, repo_type='dataset', revision=NEW, local_dir=out)
    print(p, hashlib.sha256(open(lp,'rb').read()).hexdigest())
