"""Offline acquisition limits and conservative robots subset.

Not RFC 9309 conformance: unsupported syntax denies rather than guesses.
The elapsed checks cannot interrupt blocking DNS/socket calls; a supervised
worker deadline and OS egress policy remain mandatory before activation.
"""
from __future__ import annotations
import time
from urllib.parse import urlsplit

MAX_ROBOTS = 262144
MAX_RULES = 4096


def robots_allows(raw, url):
    """Only a strict single wildcard group and literal ASCII paths supported."""
    if not isinstance(raw, bytes) or len(raw) > MAX_ROBOTS:
        return False
    try:
        text = raw.decode('ascii')
        parsed = urlsplit(url)
        target = parsed.path + ('?' + parsed.query if parsed.query else '')
        if parsed.scheme != 'https' or not target.startswith('/') or '%' in target:
            return False
        group = False
        rules = []
        for line in text.splitlines():
            line = line.split('#',1)[0].strip()
            if not line:
                continue
            if ':' not in line:
                return False
            name,value = (v.strip() for v in line.split(':',1))
            name = name.lower()
            if name == 'user-agent':
                if group or value != '*':
                    return False
                group = True
            elif name in ('allow','disallow'):
                if not group:
                    return False
                if not value and name == 'disallow':
                    continue
                if not value.startswith('/') or any(c in value for c in ('*','$','%','\\')) or any(ord(c)<33 or ord(c)>126 for c in value):
                    return False
                rules.append((value,name=='allow'))
                if len(rules)>MAX_RULES:
                    return False
            else:
                # Crawl-delay, sitemaps and all extensions are outside this
                # intentionally restrictive prototype. No fallback permission.
                return False
        if not group:
            return False
        matches=[(len(p),allow) for p,allow in rules if target.startswith(p)]
        if not matches:
            return True
        longest=max(n for n,_ in matches)
        return any(allow for n,allow in matches if n==longest)
    except (ValueError,UnicodeError):
        return False


class Budget:
    def __init__(self, *, max_seconds=600, max_bytes=150_000_000, max_attempts=12,
                 clock=time.monotonic):
        if not (0<max_seconds<=600 and 0<max_bytes<=300_000_000 and 0<max_attempts<=12):
            raise ValueError('invalid budget')
        self.clock=clock
        self.deadline=clock()+max_seconds
        self.max_bytes=max_bytes
        self.max_attempts=max_attempts
        self.bytes=0
        self.attempts=0

    def remaining(self):
        n=self.deadline-self.clock()
        if n<=0:
            raise TimeoutError('job deadline exceeded')
        return n

    def start_attempt(self):
        self.remaining()
        if self.attempts>=self.max_attempts:
            raise ValueError('attempt budget exhausted')
        self.attempts+=1

    def observe_bytes(self,n):
        if type(n) is not int or n<0:
            raise ValueError('invalid byte count')
        self.bytes+=n
        if self.bytes>self.max_bytes:
            raise ValueError('aggregate byte budget exceeded')
        self.remaining()
