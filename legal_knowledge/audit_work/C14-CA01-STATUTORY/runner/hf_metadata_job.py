"""Metadata-only commissioning candidate; live CLI remains held.

The child needs no source downloads, uploads, SDK pagination, browser, or
subprocesses. A trusted parent supplies approved scope and protects the job
directory. The native owner ACL, egress and credential gates remain external.
"""
from __future__ import annotations
import hashlib
import http.client
import json
import ssl
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit,parse_qsl
from hf_inventory_metadata import REPO, STORES, HEX40
from hf_inventory_provider import inventory, ENDPOINT
from hf_metadata_transport import MetadataAPI, MAX_SECONDS, MAX_CURSOR

REGISTER_BLOB = 'ca1096f11feb6f1cdffb69aca48ca016ac7d4a0b'
GUARD_BLOB = 'd2d11b77dc4fb7df0acbaa250004f44439f5a21e'
MAX_RECEIPT = 24_000_000
HARD_SECONDS = MAX_SECONDS + 15


def git_blob(raw):
    return hashlib.sha1(b'blob '+str(len(raw)).encode('ascii')+b'\0'+raw,
                        usedforsecurity=False).hexdigest()


def bind_restriction(root):
    """Verify exact local register and existing predicate before any request."""
    from types import ModuleType,SimpleNamespace
    root=Path(root).resolve()
    config=root/'config/restricted_material.json'
    script=root/'scripts/restricted_material.py'
    snapshots=[]
    for path,digest in ((config,REGISTER_BLOB),(script,GUARD_BLOB)):
        if path.resolve()!=path:
            raise ValueError('restriction input path mismatch')
        raw=path.read_bytes()
        if git_blob(raw)!=digest:
            raise ValueError('restriction input pin mismatch')
        snapshots.append(raw)
    # Use the exact verified guard source and freeze its config input in memory.
    module=ModuleType('c14_pinned_restriction')
    module.__file__=str(script)
    exec(compile(snapshots[1],str(script),'exec'),module.__dict__)
    module.CONFIG=SimpleNamespace(read_text=lambda **kw:snapshots[0].decode('utf-8'))
    module._load()
    return module.is_restricted


class DirectMetadataHTTPS:
    """GET exact fixed HTTPS origin only; no redirects, proxy or compression."""
    def __init__(self, revision, token, *, connect=http.client.HTTPSConnection):
        if not isinstance(revision,str) or not HEX40.fullmatch(revision):
            raise ValueError('immutable revision required')
        if not isinstance(token,str) or not token.startswith('hf_') or not token.isascii() or any(ord(c)<33 or ord(c)>126 for c in token):
            raise ValueError('valid token required')
        self.revision=revision
        self.token=token
        self.connect=connect
        self.context=ssl.create_default_context()

    def __call__(self,url,cap,remaining):
        u=urlsplit(url)
        dataset=f'/api/datasets/{REPO}'
        info=f'{dataset}/revision/{self.revision}'
        routes={f'{dataset}/tree/{self.revision}/{p}' for p in (*STORES,'data/raw','legal_knowledge/preservation')}
        if ((u.scheme,u.netloc)!=('https','huggingface.co') or u.fragment
                or (u.path!=info and u.path not in routes)
                or (u.path==info and u.query) or not 0<cap<=4_000_000 or remaining<=0):
            raise ValueError('metadata route or budget denied')
        if u.path in routes:
            pairs=parse_qsl(u.query,keep_blank_values=True,strict_parsing=True,max_num_fields=4)
            q=dict(pairs)
            scope=u.path.split('/tree/'+self.revision+'/',1)[1]
            recursive='true' if scope in STORES else 'false'
            if (len(q)!=len(pairs) or set(q)-{'recursive','expand','limit','cursor'}
                    or q.get('recursive')!=recursive or q.get('expand')!='false'
                    or q.get('limit')!='1000'):
                raise ValueError('metadata query outside scope')
            if 'cursor' in q and (not 0<len(q['cursor'])<=MAX_CURSOR
                    or not q['cursor'].isascii() or any(ord(c)<33 for c in q['cursor'])):
                raise ValueError('invalid metadata cursor')
        conn=self.connect('huggingface.co',443,timeout=min(15,remaining),context=self.context)
        try:
            conn.request('GET',u.path+('?' + u.query if u.query else ''),
                         headers={'Authorization':'Bearer '+self.token,
                                  'Accept':'application/json','Accept-Encoding':'identity',
                                  'User-Agent':'Mimamsa-Metadata/1'})
            with conn.getresponse() as response:
                if response.status!=200 or response.headers.get_content_type()!='application/json':
                    raise ValueError('unexpected metadata response')
                if response.headers.get('Content-Encoding','identity').lower()!='identity':
                    raise ValueError('unexpected metadata encoding')
                lengths=response.headers.get_all('Content-Length',[])
                if len(lengths)>1 or (lengths and (not lengths[0].isascii() or not lengths[0].isdigit()
                                                   or int(lengths[0])>cap)):
                    raise ValueError('invalid metadata length')
                data=response.read(cap+1)
                if len(data)>cap or (lengths and len(data)!=int(lengths[0])):
                    raise ValueError('metadata body outside budget')
                links=response.headers.get_all('Link',[])
                if len(links)>1:
                    raise ValueError('ambiguous pagination')
                return data, links[0] if links else None
        finally:
            conn.close()


def collect_receipt(revision,exchange,restricted):
    api=MetadataAPI(revision,exchange)
    result=inventory(api,revision,restricted)
    result.pop('inventory_sha256',None)
    result.update(provider='BOUNDED_HF_METADATA_PROTOCOL',
                  register_git_blob=REGISTER_BLOB,guard_git_blob=GUARD_BLOB,
                  metadata_requests=api.requests,metadata_response_bytes=api.bytes,
                  acquisition_eligible=False,scope_independently_attested=False)
    result['inventory_sha256']=hashlib.sha256(json.dumps(result,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    return result


def supervise(command, *, seconds=HARD_SECONDS):
    """Hard child wall-time cap. No child stdout/stderr is logged on failure.

    The reviewed worker must not spawn descendants. This does not establish
    arbitrary Windows Job Object/ACL containment.
    """
    if not 0<seconds<=HARD_SECONDS:
        raise ValueError('invalid child deadline')
    try:
        child=subprocess.run(command,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,timeout=seconds,check=False)
    except subprocess.TimeoutExpired:
        raise TimeoutError('metadata worker deadline exceeded') from None
    if child.returncode!=0 or len(child.stdout)>MAX_RECEIPT or child.stderr:
        raise ValueError('worker failed or produced unexpected output')
    result=json.loads(child.stdout)
    if not isinstance(result,dict) or result.get('acquisition_eligible') is not False:
        raise ValueError('unexpected worker receipt')
    return result

 
def candidate_worker(root,revision,token):
    """Reviewed worker body, not an authorised entry point.

    The parent must bind exact code/scope, owner approval, dataset-scoped
    read-only token and a private output destination before activating it.
    This callable is deliberately not exposed through a live CLI.
    """
    restricted=bind_restriction(root)
    return collect_receipt(revision,DirectMetadataHTTPS(revision,token),restricted)


def main():
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--execute-metadata-only',action='store_true')
    args=p.parse_args()
    if args.execute_metadata_only:
        p.error('C14 metadata commissioning hold: exact job approval, credential scope, native private output and transport acceptance required')
    print('Offline candidate: seven known HF roots; no network or output writes.')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
