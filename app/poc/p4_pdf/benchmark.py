"""Measure bounded synthetic loopback traffic, using a fresh harness per run."""
import hashlib
import http.client
import json
import platform
import statistics
from concurrent.futures import ThreadPoolExecutor
from time import perf_counter

from harness import make_pdf, serve


def main():
    pdf = make_pdf()
    copy = hashlib.sha256(pdf).hexdigest()
    token = 'fixture-benchmark'
    with serve(pdf, token) as server:
        def request(_):
            started = perf_counter()
            client = http.client.HTTPConnection(*server.server_address, timeout=4)
            try:
                client.request('GET', f'/pdf?copy={copy}', headers={
                    'Authorization': f'Bearer {token}', 'Range': 'bytes=0-65535',
                })
                response = client.getresponse()
                if response.status != 206 or response.read() != pdf[:65536]:
                    raise RuntimeError('unexpected range result')
                return 1000 * (perf_counter() - started)
            finally:
                client.close()

        started = perf_counter()
        with ThreadPoolExecutor(max_workers=10) as pool:
            latencies = list(pool.map(request, range(80)))
        elapsed = perf_counter() - started
        print(json.dumps({
            'os': platform.platform(), 'python': platform.python_version(),
            'requests': len(latencies), 'concurrency': 10, 'pdf_bytes': len(pdf),
            'valid_body_bytes': len(latencies) * 65536,
            'retained_wire_credit': server.delivery.outstanding,
            'p50_ms': round(statistics.median(latencies), 3),
            'p95_ms': round(statistics.quantiles(latencies, n=20)[18], 3),
            'max_ms': round(max(latencies), 3),
            'requests_per_second': round(len(latencies) / elapsed, 2),
        }))


if __name__ == '__main__':
    main()
