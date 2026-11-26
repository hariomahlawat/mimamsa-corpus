"""C14 six-source dry run and uncommissioned quarantine transport helpers."""
from __future__ import annotations
import argparse
import hashlib
import ipaddress
import http.client
from contextlib import contextmanager
import json
import socket
import ssl
import time
import urllib.request
from transport_policy import Budget, robots_allows
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

URLS = {
    'C14-D01': 'https://upload.wikimedia.org/wikipedia/commons/9/91/Acts_of_the_Parliament_of_India_1955.pdf',
    'C14-D03': 'https://www.indiacode.nic.in/repealedfileopen?rfilename=A1960-58.pdf',
    'C14-D04': 'https://egazette.gov.in/WriteReadData/2026/276593.pdf',
    'C14-D05': 'https://www.mha.gov.in/files/documents/250883_english01042024.pdf',
    'C14-D06': 'https://www.mha.gov.in/files/documents/250882_english_01042024_0.pdf',
    'C14-D07': 'https://www.mha.gov.in/files/documents/250884_2english_01042024.pdf',
}
UA = 'Mimamsa-Corpus/0.1'
CAP = 50_000_000


def validate(plan):
    rows = plan['targets']
    if (plan['schema_version'] != 1 or plan['max_targets'] != 6
            or len(rows) != 6 or {r['id'] for r in rows} != set(URLS)):
        raise ValueError('unexpected target inventory')
    for r in rows:
        if (r['url'] != URLS[r['id']] or type(r['enabled']) is not bool
                or r['maximum_bytes'] != CAP or r['expected_sha256'] is not None):
            raise ValueError('unexpected URL or scope')
        pin = (17513943, 'd6dba48f111834d37bd1d32b839c089aa76aa638') if r['id'] == 'C14-D01' else (None, None)
        if (r['expected_bytes'], r['expected_sha1']) != pin:
            raise ValueError('unexpected carrier pin')
    return rows


def public_address(address):
    ip = ipaddress.ip_address(address)
    if (not ip.is_global or ip.is_multicast or ip.is_reserved
            or (ip.version == 6 and (ip.scope_id is not None or ip.ipv4_mapped is not None))):
        raise ValueError('disallowed numeric peer')
    return ip


def check_dns(host):
    addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    if not addresses:
        raise ValueError('non-public or missing DNS answer')
    for address in addresses:
        checked_peer(address)
    return addresses


def checked_peer(address):
    family, kind, _, _, sockaddr = address
    ip = public_address(sockaddr[0])
    expected_family = socket.AF_INET if ip.version == 4 else socket.AF_INET6
    if (family != expected_family or kind != socket.SOCK_STREAM or sockaddr[1] != 443
            or (family == socket.AF_INET6 and sockaddr[3] != 0)):
        raise ValueError('disallowed numeric peer')
    return ip


class PinnedHTTPSConnection(http.client.HTTPSConnection):
    """Use only the checked numeric peer; preserve hostname verification/SNI."""
    def __init__(self, host, address, *, context, timeout=30):
        if not context.check_hostname or context.verify_mode != ssl.CERT_REQUIRED:
            raise ValueError('verifying TLS context required')
        super().__init__(host, port=443, context=context, timeout=timeout)
        self.address = address
        self.peer = None

    def connect(self):
        family, kind, proto, _, sockaddr = self.address
        expected = checked_peer(self.address)
        raw = socket.socket(family, kind, proto)
        try:
            raw.settimeout(self.timeout)
            raw.connect(sockaddr)  # numeric address from policy-checked resolution; no hostname lookup
            actual = raw.getpeername()
            if ipaddress.ip_address(actual[0]) != expected or actual[1] != 443:
                raise ValueError('connected peer mismatch')
            self.sock = self._context.wrap_socket(raw, server_hostname=self.host)
            self.peer = str(expected)
        except BaseException:
            raw.close()
            raise


def content_length(headers):
    values = headers.get_all('Content-Length', [])
    if not values:
        return None
    value = values[0]
    if len(values) != 1 or not 1 <= len(value) <= 9 or not value.isascii() or not value.isdigit():
        raise ValueError('invalid content length')
    return int(value)


class AttemptBody:
    """Expose a counted body and only small, typed metadata in the receipt."""
    def __init__(self, response, record, budget):
        self.response = response
        self.record = record
        self.budget = budget
        self.status = response.status
        self.headers = response.headers

    def read(self, size):
        self.budget.remaining()
        if self.response.isclosed():
            return b''
        available = self.budget.max_bytes - self.budget.bytes
        if size <= 0 or available <= 0:
            raise ValueError('aggregate byte budget exhausted')
        try:
            data = self.response.read(min(available, size))
        except http.client.IncompleteRead as exc:
            self.record['body_bytes'] += len(exc.partial)
            self.budget.observe_bytes(len(exc.partial))
            raise
        self.record['body_bytes'] += len(data)
        self.budget.observe_bytes(len(data))
        return data

    def isclosed(self):
        return self.response.isclosed()


class Transport:
    def __init__(self, budget=None):
        self.budget = budget or Budget()
        self.attempts = []
        if urllib.request.getproxies():
            raise ValueError('proxy configuration requires separate review')
        self.context = ssl.create_default_context()
        self.last = {}
        self.delay = {}

    @contextmanager
    def request(self, url):
        p = urlsplit(url)
        origins = {urlsplit(u).netloc for u in URLS.values()}
        if url not in URLS.values() and url not in {'https://' + h + '/robots.txt' for h in origins}:
            raise ValueError('unlisted URL')
        elapsed = time.monotonic() - self.last.get(p.hostname, -1000)
        wait = max(0, self.delay.get(p.hostname, 2) - elapsed)
        if wait >= self.budget.remaining():
            raise TimeoutError('pacing exceeds remaining deadline')
        time.sleep(wait)
        self.budget.start_attempt()
        self.last[p.hostname] = time.monotonic()
        # Resolution happens after pacing, and the selected sockaddr is used verbatim.
        record = {'url': url, 'started_utc': datetime.now(timezone.utc).isoformat(), 'status': None,
                  'body_bytes': 0, 'peer': None, 'content_type': None, 'declared_bytes': None}
        self.attempts.append(record)
        conn = None
        stage = 'DNS'
        try:
            address = check_dns(p.hostname)[0]
            stage = 'CONNECTION'
            conn = PinnedHTTPSConnection(p.hostname, address, context=self.context,
                                        timeout=min(30, self.budget.remaining()))
            path = p.path + ('?' + p.query if p.query else '')
            conn.request('GET', path, headers={'User-Agent': UA, 'Accept-Encoding': 'identity'})
            record['peer'] = conn.peer
            stage = 'HTTP'
            with conn.getresponse() as response:
                mime = response.headers.get_content_type()
                safe_mime = mime if mime in ('application/pdf', 'application/octet-stream', 'text/plain') else 'OTHER'
                record.update(status=response.status, content_type=safe_mime)
                record['declared_bytes'] = content_length(response.headers)
                self.budget.remaining()
                # No automatic redirect, authentication or retry.
                if response.status != 200:
                    raise ValueError('unexpected HTTP status; no redirect or challenge bypass')
                stage = 'BODY_OR_POLICY'
                yield AttemptBody(response, record, self.budget)
                if not response.isclosed():
                    raise ValueError('response body did not reach end of stream')
            record['outcome'] = 'COMPLETE'
        except TimeoutError:
            record['outcome'] = 'DEADLINE_OR_TIMEOUT'
            raise
        except BaseException:
            record['outcome'] = stage + '_FAILED'
            raise
        finally:
            record['ended_utc'] = datetime.now(timezone.utc).isoformat()
            if conn is not None:
                conn.close()

    def robots(self, url):
        host = urlsplit(url).hostname
        origin = 'https://' + host + '/robots.txt'
        with self.request(origin) as response:
            raw = response.read(262145)
            declared = content_length(response.headers)
            if (len(raw) > 262144 or not response.isclosed()
                    or (declared is not None and len(raw) != declared)
                    or response.headers.get('Content-Encoding', 'identity').lower() != 'identity'):
                raise ValueError('robots body outside limits')
            if not robots_allows(raw, url):
                raise ValueError('robots disallowed or unsupported syntax')
        self.delay[host] = 2



def receive(response, destination, row, known):
    if response.status != 200 or response.headers.get_content_type() not in ('application/pdf', 'application/octet-stream'):
        raise ValueError('unexpected HTTP status or content type')
    if response.headers.get('Content-Encoding', 'identity').lower() != 'identity':
        raise ValueError('unexpected content encoding')
    declared = content_length(response.headers)
    if declared is not None and not 0 < declared <= CAP:
        raise ValueError('invalid content length')
    sha = hashlib.sha256(); sha1 = hashlib.sha1(usedforsecurity=False); md5 = hashlib.md5(usedforsecurity=False)
    n = 0; start = b''; tail = b''
    with destination.open('xb') as fh:
        while chunk := response.read(65536):
            n += len(chunk)
            if n > CAP:
                raise ValueError('size cap exceeded; partial retained')
            start = (start + chunk)[:8]; tail = (tail + chunk)[-2048:]
            fh.write(chunk); sha.update(chunk); sha1.update(chunk); md5.update(chunk)
    result = {'sha256': sha.hexdigest(), 'sha1': sha1.hexdigest(), 'md5': md5.hexdigest(), 'bytes': n}
    pin_ok = (row['expected_bytes'] is None or n == row['expected_bytes']) and (row['expected_sha1'] is None or result['sha1'] == row['expected_sha1'])
    complete = start.startswith(b'%PDF-') and b'%%EOF' in tail and (declared is None or n == declared)
    result['status'] = ('HOLD_INTEGRITY' if not (pin_ok and complete) else 'DUPLICATE_BYTES_HOLD' if result['sha256'] in known else 'QUARANTINED_PENDING_REVIEW')
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--execute-approved', action='store_true')
    p.add_argument('--expected-commit')
    p.add_argument('--output', type=Path)
    p.add_argument('--known-sha256', type=Path, help='one SHA-256 per line from revision-pinned corpus inventory')
    args = p.parse_args()
    if args.execute_approved:
        p.error('C14 acquisition interlock: live transport disabled pending independent authorization and security acceptance')
    here = Path(__file__).resolve().parent
    plan = json.loads((here.parent / 'LOCAL_ACQUISITION_BATCH_01.json').read_text(encoding='utf-8'))
    rows = validate(plan)
    print('Targets:', len(rows), 'Enabled:', sum(r['enabled'] for r in rows))
    print('Dry run: no network or writes.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
