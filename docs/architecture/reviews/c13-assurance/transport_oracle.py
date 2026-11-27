"""Check normalized R2-N01 evidence and run a pinned synthetic HTTP control."""

import argparse
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass
from hashlib import sha256
from http.client import HTTPConnection, IncompleteRead
import json
from pathlib import Path
import platform
import re
from secrets import token_urlsafe
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Event
from time import perf_counter


REFERENCE = 'fbeda3745b21047278b3477a7db3d701d69994bf'
PDF_DIGEST = '975782a1688d037b4916bfe7dbd9c711b286873dc0e38f124daababe658380e6'
FIXTURES = Path(__file__).with_name('transport-fixtures.json')
MAX_SLICE = 64 * 1024
MAX_RANGE = 128 * 1024
SOURCES = {
    'reserve': 'ledger',
    'enter': 'policy_probe',
    'settle': 'ledger',
    'accept': 'terminal',
    'occupancy': 'drain_probe',
    'prove_release': 'drain_probe',
    'admit': 'policy_probe',
    'fence': 'witness',
    'recover': 'witness',
    'restart': 'fault_driver',
    'ack': 'client',
    'cancel': 'client',
    'receive': 'client',
    'http': 'client',
}


class Rejected(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise Rejected(message)


def integer(value, low=0):
    return type(value) is int and value >= low


@dataclass
class Attempt:
    connection: str
    stream: str
    copy: str
    offset: int
    size: int
    epoch: int
    boot: int
    charge: int
    entered: bool = False
    accepted: int = 0
    received: int = 0
    state: str = 'reserved'


def check_trace(trace, http_cases):
    site_limit, connection_limit = (trace['limits'][key] for key in ('site', 'connection'))
    require(integer(connection_limit, 1) and integer(site_limit, connection_limit),
            'invalid credit limits')
    current = (trace['initial_witness']['epoch'], trace['initial_witness']['digest'])
    require(integer(current[0]) and isinstance(current[1], str) and current[1],
            'missing trusted initial witness')

    mounted = True
    boot = 0
    pending = {}
    committed = {}
    revoked = set()
    cancelled = set()
    blocked = set()
    attempts = {}
    streams = {}
    next_offset = {}
    charges = Counter()
    site_charge = peak = 0
    counts = Counter()
    finished_http = set()
    withdrawal_times = []
    last_sequence = 0

    for event in trace['events']:
        sequence, kind = event['seq'], event['kind']
        require(integer(sequence, last_sequence + 1), 'events must have strictly increasing sequence')
        last_sequence = sequence
        require(kind in SOURCES and event.get('source') == SOURCES[kind],
                f'{sequence}: wrong independent source for {kind}')
        counts[kind] += 1

        if kind == 'reserve':
            identifier = event['attempt']
            connection, stream, copy, offset, size, epoch = (
                event[key] for key in ('connection', 'stream', 'copy', 'offset', 'size', 'epoch')
            )
            require(mounted and not pending and epoch == current[0],
                    'reservation without fresh policy authority')
            require(copy not in revoked and stream not in cancelled, 'withdrawn or cancelled stream')
            require(stream not in blocked, 'unresolved attempt on stream')
            require(identifier not in attempts, 'duplicate reservation ID')
            require(integer(offset) and integer(size, 1) and size <= MAX_SLICE,
                    'invalid offset or slice bound')
            require(streams.setdefault(stream, (connection, copy)) == (connection, copy),
                    'stream identity changed')
            require(next_offset.setdefault(stream, offset) == offset, 'suffix offset mismatch')
            require(charges[connection] + size <= connection_limit, 'connection credit cap exceeded')
            require(site_charge + size <= site_limit, 'site credit cap exceeded')
            attempts[identifier] = Attempt(connection, stream, copy, offset, size, epoch, boot, size)
            blocked.add(stream)
            charges[connection] += size
            site_charge += size
            peak = max(peak, site_charge)
        elif kind in {'enter', 'accept', 'settle', 'prove_release', 'receive'}:
            require(event['attempt'] in attempts, 'event without reservation')
            attempt = attempts[event['attempt']]
            if kind == 'enter':
                require(mounted and not pending and attempt.epoch == current[0] and attempt.boot == boot,
                        'handoff guard without fresh policy authority')
                require(attempt.copy not in revoked and attempt.stream not in cancelled,
                        'handoff guard on withdrawn or cancelled stream')
                require(attempt.state == 'reserved' and not attempt.entered,
                        'duplicate or inactive reservation at handoff guard')
                attempt.entered = True
            elif kind == 'accept':
                size = event['size']
                require(mounted and attempt.epoch == current[0] and attempt.boot == boot,
                        'terminal handoff after fence or restart')
                require(attempt.copy not in revoked and attempt.stream not in cancelled,
                        'terminal handoff to withdrawn or cancelled stream')
                require(attempt.state == 'reserved' and attempt.entered and not attempt.accepted,
                        'duplicate, unguarded or settled terminal acceptance')
                require(event['offset'] == attempt.offset and integer(size, 1) and size <= attempt.size,
                        'terminal acceptance must be the exact reserved prefix')
                attempt.accepted = size
                next_offset[attempt.stream] += size
            elif kind == 'receive':
                size = event['size']
                require(integer(size, 1) and attempt.received + size <= attempt.accepted,
                        'client receipt exceeds observed acceptance')
                attempt.received += size
            elif kind == 'settle':
                require(attempt.state == 'reserved', 'duplicate or invalid settlement')
                outcome = event['outcome']
                require(outcome in {'accepted', 'zero', 'uncertain'}, 'unknown settlement outcome')
                if outcome == 'uncertain':
                    attempt.state = 'uncertain'
                    continue
                keep = event.get('size') if outcome == 'accepted' else 0
                require(integer(keep, int(outcome == 'accepted')) and keep == attempt.accepted,
                        'settlement differs from terminal acceptance')
                unused = attempt.charge - keep
                charges[attempt.connection] -= unused
                site_charge -= unused
                attempt.charge = keep
                attempt.state = outcome
                blocked.discard(attempt.stream)
            else:
                require(attempt.state in {'accepted', 'uncertain'} and attempt.charge,
                        'duplicate or invalid credit release')
                require(event['proof'] in {'drain', 'termination', 'reconciliation'},
                        'credit release lacks independent proof')
                if attempt.state == 'uncertain':
                    require(attempt.stream in cancelled, 'uncertain route was not cancelled')
                charges[attempt.connection] -= attempt.charge
                site_charge -= attempt.charge
                attempt.charge = 0
                attempt.state = 'released'
        elif kind == 'occupancy':
            measurements = event['connections']
            require(all(integer(size) and size <= charges[connection]
                        for connection, size in measurements.items()),
                    'uncovered connection occupancy')
            require(integer(event['site']) and event['site'] == sum(measurements.values())
                    and event['site'] <= site_charge, 'uncovered site occupancy')
            require(set(measurements) >= {key for key, size in charges.items() if size},
                    'occupancy evidence omits a charged connection')
        elif kind == 'admit':
            operation = event['operation']
            require(mounted and operation not in pending and operation not in committed,
                    'duplicate policy admission or missing authority')
            require(integer(event['monotonic_ms']), 'invalid admission time')
            pending[operation] = (event['copy'], event['monotonic_ms'])
        elif kind == 'fence':
            operation = event['operation']
            require(mounted and operation in pending and pending[operation][0] == event['copy'],
                    'durable fence without matching admission')
            require(event['epoch'] == current[0] + 1 and isinstance(event['digest'], str)
                    and event['digest'] and event['digest'] != current[1],
                    'invalid durable witness transition')
            current = (event['epoch'], event['digest'])
            copy, admitted_at = pending.pop(operation)
            revoked.add(copy)
            committed[operation] = (current, admitted_at)
        elif kind == 'ack':
            require(event['operation'] in committed,
                    'acknowledgment before matching durable fence')
            witness, admitted_at = committed[event['operation']]
            require((event['epoch'], event['digest']) == witness,
                    'acknowledgment before matching durable fence')
            require(integer(event['monotonic_ms'], admitted_at), 'invalid acknowledgment time')
            withdrawal_times.append(event['monotonic_ms'] - admitted_at)
        elif kind == 'cancel':
            require(event['stream'] in streams, 'cancel evidence for unknown stream')
            cancelled.add(event['stream'])
        elif kind == 'restart':
            mounted = False
            boot += 1
            for attempt in attempts.values():
                if attempt.state == 'reserved':
                    attempt.state = 'uncertain'
        elif kind == 'recover':
            require(not mounted and (event['epoch'], event['digest']) == current,
                    'recovery lacks exact current witness')
            mounted = True
        elif kind == 'http':
            case = event['case']
            expected = http_cases.get(case)
            require(expected is not None and case not in finished_http,
                    'missing or duplicate HTTP case definition')
            require(all(key in event and event[key] == value for key, value in expected.items()),
                    f'HTTP evidence disagrees with case {case}')
            require(event['status'] != 304, 'HTTP conditional cache reuse')
            if event['status'] in {200, 206}:
                require(mounted and event['authenticated'] is True and event['copy'] not in revoked,
                        'HTTP delivery without current authority')
            if event['status'] == 206:
                requested = re.fullmatch(r'bytes=(\d+)-(\d+)', event.get('range', ''))
                returned = re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)', event.get('content_range') or '')
                require(requested and returned and requested.groups() == returned.groups()[:2],
                        'HTTP range boundaries do not agree')
                start, end, total = map(int, returned.groups())
                require(start <= end < total and event['length'] == end - start + 1 <= MAX_RANGE,
                        'HTTP range length or bound mismatch')
            require(event.get('phase', 'current') != 'withdrawn' or event['copy'] in revoked,
                    'HTTP withdrawn control preceded durable fence')
            finished_http.add(case)

    require(counts, 'empty evidence trace')
    return {'events': last_sequence, 'peak_reserved_wire_bytes': peak,
            'remaining_wire_charge': site_charge, 'counts': dict(counts),
            'http_cases': sorted(finished_http), 'authority_mounted': mounted,
            'withdrawal_ack_latency_ms': withdrawal_times}


def run_self_test(fixtures):
    base = fixtures['vector']
    http_cases = fixtures['http_cases']
    result = check_trace(base, http_cases)
    require(result['peak_reserved_wire_bytes'] == 65536 and result['remaining_wire_charge'] == 65536
            and set(result['http_cases']) == set(http_cases), 'positive vector result mismatch')
    for case in fixtures['reject_vectors']:
        events = list(base['events'])
        for edit in sorted(case.get('edits', [case]), key=lambda item: item['index'], reverse=True):
            index = edit['index']
            if 'insert' in edit:
                events.insert(index, edit['insert'])
            elif 'replace' in edit:
                events[index] = edit['replace']
            else:
                del events[index]
        events = [dict(event, seq=seq) for seq, event in enumerate(events, 1)]
        try:
            check_trace(base | {'events': events, **case.get('overrides', {})}, http_cases)
        except Rejected as error:
            require(case['error'] in str(error), f"{case['name']}: wrong rejection: {error}")
        else:
            raise Rejected(f"{case['name']}: expected rejection")
    return {'positive_vectors': 1, 'rejected_vectors': len(fixtures['reject_vectors'])}


@contextmanager
def pinned_harness(repository):
    """Import only the fixed reference blobs, regardless of working-tree changes."""
    with TemporaryDirectory(prefix='c13-transport-') as staging:
        for name in ('delivery.py', 'harness.py'):
            blob = subprocess.check_output(
                ['git', '-C', str(repository), 'show', f'{REFERENCE}:app/poc/p4_pdf/{name}'],
            )
            (Path(staging) / name).write_bytes(blob)
        sys.path.insert(0, staging)
        try:
            import harness
            yield harness
        finally:
            sys.path.pop(0)
            sys.modules.pop('harness', None)
            sys.modules.pop('delivery', None)


def run_reference(repository):
    with pinned_harness(repository) as harness:
        pdf = harness.make_pdf()
        digest = sha256(pdf).hexdigest()
        require(len(pdf) == 396871 and digest == PDF_DIGEST, 'synthetic known PDF bytes changed')
        token = token_urlsafe(24)
        path = f'/pdf?copy={digest}'
        auth = {'Authorization': f'Bearer {token}'}
        paused = Event()
        resume = Event()

        def pause_after_first(route, received_offset):
            if route == '/pdf' and received_offset:
                paused.set()
                resume.wait(timeout=4)

        def request(server, target, headers):
            client = HTTPConnection(*server.server_address, timeout=4)
            try:
                client.putrequest('GET', target)
                for name, value in headers.items() if isinstance(headers, dict) else headers:
                    client.putheader(name, value)
                client.endheaders()
                response = client.getresponse()
                return response.status, dict(response.getheaders()), response.read()
            finally:
                client.close()

        with harness.serve(pdf, token) as server:
            status, headers, raw = request(server, '/metadata', auth)
            require(status == 200 and 'no-store' in headers['Cache-Control']
                    and json.loads(raw) == {'copy': digest, 'length': len(pdf), 'maxRange': 131072},
                    'unexpected bootstrap metadata')
            ranges = [(0, 131071), (len(pdf) - 257, len(pdf) - 1)]
            for start, end in ranges:
                status, headers, body = request(server, path, auth | {'Range': f'bytes={start}-{end}'})
                require(status == 206 and headers['Content-Range'] == f'bytes {start}-{end}/{len(pdf)}'
                        and int(headers['Content-Length']) == end - start + 1 and body == pdf[start:end + 1]
                        and 'no-store' in headers['Cache-Control'] and 'Content-Encoding' not in headers,
                        'incorrect bounded response')
            controls = [
                ('anonymous-metadata', '/metadata', {}, 404),
                ('anonymous-pdf', path, {'Range': 'bytes=0-0'}, 404),
                ('stale-copy', f'/pdf?copy={digest[::-1]}', auth | {'Range': 'bytes=0-0'}, 404),
                ('unbounded', path, auth, 416),
                ('malformed', path, auth | {'Range': 'invalid'}, 416),
                ('oversize', path, auth | {'Range': 'bytes=0-131072'}, 416),
                ('multi-range', path, auth | {'Range': 'bytes=0-1,3-4'}, 416),
                ('duplicate-header', path, [*auth.items(), ('Range', 'bytes=0-0'), ('Range', 'bytes=0-0')], 416),
            ]
            for conditional in ('If-Range', 'If-None-Match', 'If-Match',
                                'If-Modified-Since', 'If-Unmodified-Since'):
                controls.append((conditional, path, auth | {'Range': 'bytes=0-0', conditional: '*'}, 416))
            for name, target, outgoing, expected in controls:
                status, headers, body = request(server, target, outgoing)
                require(status == expected and not body and 'Content-Range' not in headers
                        and 'ETag' not in headers and 'Last-Modified' not in headers
                        and headers['Content-Length'] == '0', f'public denial control failed: {name}')

        with harness.serve(pdf, token, observe=pause_after_first) as server:
            client = HTTPConnection(*server.server_address, timeout=4)
            try:
                client.request('GET', path, headers=auth | {'Range': 'bytes=0-65535'})
                response = client.getresponse()
                require(response.status == 206 and paused.wait(timeout=3),
                        'deterministic active transfer pause missing')
                before = response.read(4096)
                require(before == pdf[:4096], 'pre-withdrawal client bytes differ from fixture')
                started = perf_counter()
                try:
                    server.delivery.withdraw(digest)
                finally:
                    resume.set()
                withdrawal_ms = (perf_counter() - started) * 1000
                try:
                    response.read()
                except IncompleteRead as error:
                    received = before + error.partial
                    require(received == pdf[:len(received)] and 4096 <= len(received) <= 16384,
                            'received bytes exceeded the single pre-withdrawal body slice')
                else:
                    raise Rejected('active body did not end early at withdrawal')
            finally:
                resume.set()
                client.close()
            for target, outgoing in [
                ('/metadata', auth),
                (path, auth | {'Range': 'bytes=0-0'}),
                (path, auth | {'Range': f'bytes={len(pdf)}-{len(pdf)}'}),
            ]:
                status, headers, body = request(server, target, outgoing)
                require(status == 404 and not body and 'Content-Range' not in headers,
                        'withdrawn request did not receive uniform denial')

    return {'reference_commit': REFERENCE, 'environment': platform.platform(),
            'python': platform.python_version(), 'pdf_bytes': len(pdf),
            'eligible_ranges': ranges, 'pre_withdrawal_denial_controls': len(controls),
            'active_response_received_bytes': len(received), 'fresh_withdrawn_denials': 3,
            'in_memory_withdrawal_ms': round(withdrawal_ms, 3)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--self-test', action='store_true', help='run positive and negative trace vectors')
    modes.add_argument('--trace', type=Path, help='check an independently collected normalized JSON trace')
    modes.add_argument('--reference', type=Path, help='Git checkout with the pinned synthetic reference commit')
    parser.add_argument('--http-cases', type=Path, help='separate HTTP oracle pinned before capturing a trace')
    args = parser.parse_args()
    if args.http_cases and not args.trace:
        parser.error('--http-cases requires --trace')
    fixtures = json.loads(FIXTURES.read_text(encoding='utf-8'))
    try:
        if args.self_test:
            result = run_self_test(fixtures)
        elif args.reference:
            result = run_reference(args.reference)
        else:
            trace = json.loads(args.trace.read_text(encoding='utf-8'))
            http_cases = fixtures['http_cases']
            if args.http_cases:
                http_cases = json.loads(args.http_cases.read_text(encoding='utf-8'))
            result = check_trace(trace, http_cases)
    except (Rejected, KeyError, TypeError, OSError, subprocess.CalledProcessError) as error:
        print(f'REJECTED: {error}', file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
