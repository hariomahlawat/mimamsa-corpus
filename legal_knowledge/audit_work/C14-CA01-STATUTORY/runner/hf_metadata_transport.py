"""Bounded metadata protocol, without the SDK's implicit pagination.

No credentials, sockets, network client or activation in this module.
The exchange callback must be an independently commissioned HTTPS GET
transport with bounded reads, no redirects and no retry.
"""
from __future__ import annotations
import json
import re
import time
from types import SimpleNamespace
from urllib.parse import urlencode, urlsplit, parse_qsl

from hf_inventory_metadata import REPO, STORES, HEX40
from hf_inventory_provider import ENDPOINT

ROOTS = ('data/raw', 'legal_knowledge/preservation')
MAX_PAGES = 160
MAX_PAGE_BYTES = 4_000_000
MAX_TOTAL_BYTES = 48_000_000
MAX_SECONDS = 180
MAX_CURSOR = 8192


class MetadataAPI:
    endpoint = ENDPOINT

    def __init__(self, revision, exchange, *, clock=time.monotonic):
        if not isinstance(revision,str) or not HEX40.fullmatch(revision):
            raise ValueError('full immutable revision required')
        self.revision = revision
        self.exchange = exchange
        self.clock = clock
        self.deadline = clock() + MAX_SECONDS
        self.requests = 0
        self.bytes = 0

    def remaining(self):
        remaining = self.deadline - self.clock()
        if remaining <= 0:
            raise TimeoutError('metadata deadline exceeded')
        return remaining

    def _get(self, url):
        if self.requests >= MAX_PAGES:
            raise ValueError('metadata request budget exhausted')
        self.requests += 1
        cap = min(MAX_PAGE_BYTES, MAX_TOTAL_BYTES-self.bytes)
        if cap <= 0:
            raise ValueError('metadata byte budget exhausted')
        body, link = self.exchange(url, cap, self.remaining())
        if not isinstance(body,bytes) or len(body) > cap:
            raise ValueError('metadata response exceeded budget')
        self.bytes += len(body)
        self.remaining()
        if link is not None and (not isinstance(link,str) or len(link) > MAX_CURSOR+1024):
            raise ValueError('invalid pagination header')
        def unique(pairs):
            out = {}
            for k,v in pairs:
                if k in out:
                    raise ValueError('duplicate metadata key')
                out[k] = v
            return out
        return json.loads(body,object_pairs_hook=unique),link

    def dataset_info(self, repo, *, revision):
        if repo != REPO or revision != self.revision:
            raise ValueError('wrong repository or revision')
        data,link = self._get(f'{ENDPOINT}/api/datasets/{REPO}/revision/{revision}')
        if link is not None or not isinstance(data,dict):
            raise ValueError('unexpected identity response')
        return SimpleNamespace(id=data.get('id'),sha=data.get('sha'),private=data.get('private'))

    def _next(self, link, base, recursive):
        # Conservative grammar: accept a single explicit next link.
        # Other syntax is held rather than followed implicitly.
        if link is None:
            return None
        match = re.fullmatch(r'\s*<([^<>]+)>\s*;\s*rel="next"\s*',link)
        if not match:
            raise ValueError('unsupported pagination header')
        u = urlsplit(match[1])
        expected = urlsplit(base)
        if ((u.scheme,u.netloc,u.path) != (expected.scheme,expected.netloc,expected.path)
                or u.fragment or u.username or u.password):
            raise ValueError('pagination escaped exact metadata route')
        pairs = parse_qsl(u.query,keep_blank_values=True,strict_parsing=True,max_num_fields=4)
        q = dict(pairs)
        if len(q)!=len(pairs) or set(q)-{'cursor','recursive','expand','limit'}:
            raise ValueError('unsupported pagination query')
        cursor=q.get('cursor','')
        if not 0<len(cursor)<=MAX_CURSOR or not cursor.isascii() or any(ord(c)<33 for c in cursor):
            raise ValueError('invalid continuation cursor')
        if ('recursive' in q and q['recursive'] != str(recursive).lower()
                or 'expand' in q and q['expand'] != 'false'
                or 'limit' in q and q['limit'] != '1000'):
            raise ValueError('continuation changed tree scope')
        # Rebuild a canonical request instead of following the supplied URL.
        return base+'?'+urlencode({'recursive':str(recursive).lower(),
                                   'expand':'false','limit':'1000','cursor':cursor})

    def list_repo_tree(self, repo, *, path_in_repo, recursive, expand, revision, repo_type):
        if (repo!=REPO or revision!=self.revision or repo_type!='dataset'
                or expand is not False or type(recursive) is not bool
                or path_in_repo not in (STORES if recursive else ROOTS)):
            raise ValueError('tree request outside approved scope')
        base=f'{ENDPOINT}/api/datasets/{REPO}/tree/{revision}/{path_in_repo}'
        url=base+'?'+urlencode({'recursive':str(recursive).lower(),'expand':'false','limit':'1000'})
        seen=set()
        while url is not None:
            if url in seen:
                raise ValueError('pagination loop')
            seen.add(url)
            data,link=self._get(url)
            if not isinstance(data,list) or len(data)>1000:
                raise ValueError('invalid metadata page')
            # Validate continuation before passing entries to the collector.
            nxt=self._next(link,base,recursive)
            for row in data:
                if not isinstance(row,dict) or not isinstance(row.get('path'),str):
                    raise ValueError('invalid metadata row')
                kind=row.get('type')
                if kind=='directory':
                    yield SimpleNamespace(path=row['path'])
                elif kind=='file':
                    lfs=row.get('lfs')
                    if lfs is not None and not isinstance(lfs,dict):
                        raise ValueError('invalid LFS metadata')
                    yield SimpleNamespace(path=row['path'],size=row.get('size'),
                           lfs=SimpleNamespace(sha256=lfs.get('oid'),size=lfs.get('size')) if lfs else None)
                else:
                    raise ValueError('unknown metadata entry type')
            url=nxt
