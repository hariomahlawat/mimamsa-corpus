"""C14 six-source acquisition prototype. No network by default; no HF writes."""
from __future__ import annotations
import argparse
import hashlib
import ipaddress
import json
import socket
import ssl
import subprocess
import time
import urllib.request
import urllib.robotparser
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


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def check_dns(host):
    addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise ValueError('non-public or missing DNS answer')


class Transport:
    def __init__(self):
        if urllib.request.getproxies():
            raise ValueError('proxy configuration requires separate review')
        self.opener = urllib.request.build_opener(NoRedirect(), urllib.request.HTTPSHandler(context=ssl.create_default_context()))
        self.last = {}
        self.delay = {}

    def request(self, url):
        p = urlsplit(url)
        origins = {urlsplit(u).netloc for u in URLS.values()}
        if url not in URLS.values() and url not in {'https://' + h + '/robots.txt' for h in origins}:
            raise ValueError('unlisted URL')
        check_dns(p.hostname)
        elapsed = time.monotonic() - self.last.get(p.hostname, -1000)
        time.sleep(max(0, self.delay.get(p.hostname, 2) - elapsed))
        self.last[p.hostname] = time.monotonic()
        return self.opener.open(urllib.request.Request(url, headers={'User-Agent': UA, 'Accept-Encoding': 'identity'}), timeout=30)

    def robots(self, url):
        host = urlsplit(url).hostname
        origin = 'https://' + host + '/robots.txt'
        with self.request(origin) as response:
            if response.status != 200:
                raise ValueError('robots unavailable')
            raw = response.read(262145)
        if len(raw) > 262144:
            raise ValueError('robots oversized')
        body = raw.decode('utf-8', errors='strict')
        if '<html' in body.lower() or '<!doctype' in body.lower():
            raise ValueError('robots not plain text')
        rp = urllib.robotparser.RobotFileParser()
        rp.parse(body.splitlines())
        if not rp.can_fetch(UA, url):
            raise ValueError('robots disallowed')
        rate = rp.request_rate(UA)
        self.delay[host] = max(2, rp.crawl_delay(UA) or 0, rate.seconds / rate.requests if rate and rate.requests else 0)
        if self.delay[host] > 60:
            raise ValueError('robots delay exceeds job limit')


def receive(response, destination, row, known):
    if response.status != 200 or response.headers.get_content_type() not in ('application/pdf', 'application/octet-stream'):
        raise ValueError('unexpected HTTP status or content type')
    if response.headers.get('Content-Encoding', 'identity').lower() != 'identity':
        raise ValueError('unexpected content encoding')
    declared = response.headers.get('Content-Length')
    if declared is not None and not 0 < int(declared) <= CAP:
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
    complete = start.startswith(b'%PDF-') and b'%%EOF' in tail and (declared is None or n == int(declared))
    result['status'] = ('HOLD_INTEGRITY' if not (pin_ok and complete) else 'DUPLICATE_BYTES_HOLD' if result['sha256'] in known else 'QUARANTINED_PENDING_REVIEW')
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--execute-approved', action='store_true')
    p.add_argument('--expected-commit')
    p.add_argument('--output', type=Path)
    p.add_argument('--known-sha256', type=Path, help='one SHA-256 per line from revision-pinned corpus inventory')
    args = p.parse_args()
    here = Path(__file__).resolve().parent
    plan = json.loads((here.parent / 'LOCAL_ACQUISITION_BATCH_01.json').read_text(encoding='utf-8'))
    rows = validate(plan)
    print('Targets:', len(rows), 'Enabled:', sum(r['enabled'] for r in rows))
    if not args.execute_approved:
        print('Dry run: no network or writes.'); return 0
    if plan['scope_approval'] != 'APPROVED' or not all(r['enabled'] for r in rows):
        p.error('scope disabled; independent review and approved plan required')
    if not all((args.expected_commit, args.output, args.known_sha256)):
        p.error('commit, output and known SHA inventory required')
    repo = Path(subprocess.check_output(['git', '-C', str(here), 'rev-parse', '--show-toplevel'], text=True).strip()).resolve()
    head = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
    dirty = subprocess.check_output(['git', '-C', str(repo), 'status', '--porcelain'], text=True).strip()
    if head != args.expected_commit or dirty:
        p.error('clean reviewed commit required')
    output = args.output.resolve()
    if output.parent != (repo.parent / 'jobs').resolve() or output.exists():
        p.error('fresh sibling jobs directory required')
    known_raw = args.known_sha256.read_bytes()
    known = set(known_raw.decode('ascii').splitlines())
    if not known or any(len(s) != 64 or any(c not in '0123456789abcdef' for c in s) for s in known):
        p.error('invalid known-hash inventory')
    transport = Transport()
    output.mkdir(parents=True, exist_ok=False)
    report = {'status': 'INCOMPLETE', 'commit': head, 'known_hash_inventory_sha256': hashlib.sha256(known_raw).hexdigest(), 'records': [], 'hf_writes': 0, 'legal_promotions': 0}
    def save():
        tmp = output / 'report.tmp'; tmp.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8'); tmp.replace(output / 'report.json')
    save()
    for row in rows:
        rec = {'id': row['id'], 'url': row['url'], 'eligible_for_exact_anchor': False}
        try:
            transport.robots(row['url'])
            with transport.request(row['url']) as response:
                rec.update(receive(response, output / (row['id'] + '.pdf'), row, known))
            if rec.get('sha256'): known.add(rec['sha256'])
        except Exception as exc:
            rec.update(status='REVIEW_REQUIRED', error_type=type(exc).__name__)
        report['records'].append(rec); save()
    report['status'] = 'QUARANTINE_REVIEW_REQUIRED'; save()
    return 1  # no automatic acceptance, even on a clean fetch


if __name__ == '__main__':
    raise SystemExit(main())
