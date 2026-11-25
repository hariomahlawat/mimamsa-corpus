"""Synthetic loopback HTTP PoC. Never point it at a real vault."""
import argparse
import hashlib
import hmac
import itertools
import json
import re
import secrets
import time
from contextlib import contextmanager
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import urlsplit

from delivery import Delivery

SLICE = 16 * 1024
MAX_RANGE = 128 * 1024
MAX_FULL_RESPONSE = 256 * 1024


def make_pdf():
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>', b'',
               b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    kids = []
    for page in range(1, 13):
        number = len(objects) + 1
        kids.append(f'{number} 0 R')
        objects.append(
            f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 400 200] /Resources '
            f'<< /Font << /F1 3 0 R >> >> /Contents {number+1} 0 R >>'.encode())
        visible = f'BT /F1 20 Tf 40 100 Td (Synthetic page {page}) Tj ET\n'.encode()
        padding = b'%' + (b'x' * 32768) + b'\n'
        stream = visible + padding
        objects.append(f'<< /Length {len(stream)} >>\nstream\n'.encode() + stream + b'endstream')
    objects[1] = f'<< /Type /Pages /Count 12 /Kids [{" ".join(kids)}] >>'.encode()
    pdf = bytearray(b'%PDF-1.4\n')
    offsets = []
    for index, data in enumerate(objects, 1):
        offsets.append(len(pdf))
        pdf.extend(f'{index} 0 obj\n'.encode() + data + b'\nendobj\n')
    xref = len(pdf)
    pdf.extend(f'xref\n0 {len(objects)+1}\n0000000000 65535 f \n'.encode())
    for offset in offsets:
        pdf.extend(f'{offset:010d} 00000 n \n'.encode())
    pdf.extend(f'trailer\n<< /Root 1 0 R /Size {len(objects)+1} >>\nstartxref\n{xref}\n%%EOF\n'.encode())
    return bytes(pdf)


def _range(value, length):
    match = re.fullmatch(r'bytes=([0-9]{1,10})-([0-9]{1,10})', value or '')
    if match:
        start, end = map(int, match.groups())
        if 0 <= start <= end < length and end - start + 1 <= MAX_RANGE:
            return start, end


class Handler(BaseHTTPRequestHandler):
    def log_message(self, _format, *args):
        pass

    def _generic(self, status):
        self.send_response(status)
        self.send_header('Content-Length', '0')
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()

    def do_GET(self):
        route = urlsplit(self.path)
        if self.server.assets and route.path in self.server.assets and not route.query:
            payload = self.server.assets[route.path]
            self.send_response(200)
            self.send_header('Content-Type', 'text/html' if route.path == '/' else 'text/javascript')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        if not hmac.compare_digest(self.headers.get('Authorization', '').encode(), self.server.auth):
            self._generic(404)
            return
        if route.path == '/metadata' and not route.query:
            self._protected(200, 'application/json', self.server.metadata, route.path)
        elif route.path == '/pdf' and route.query == f'copy={self.server.identity}':
            bounds = _range(self.headers.get('Range'), len(self.server.pdf))
            conditional = any(name in self.headers for name in ('If-Range', 'If-None-Match', 'If-Modified-Since',
                                                                'If-Match', 'If-Unmodified-Since'))
            if not bounds or conditional or len(self.headers.get_all('Range', [])) != 1:
                self._protected(416, 'text/plain', b'', route.path)
                return
            start, end = bounds
            self._protected(206, 'application/pdf', self.server.pdf[start:end+1], route.path,
                            f'bytes {start}-{end}/{len(self.server.pdf)}')
        else:
            self._generic(404)

    def _protected(self, status, mime, payload, route, content_range=None):
        header = (f'HTTP/1.1 {status} {HTTPStatus(status).phrase}\r\n'
                  f'Content-Type: {mime}\r\nContent-Length: {len(payload)}\r\n'
                  'Cache-Control: private, no-store\r\nConnection: close\r\n')
        if content_range:
            header += f'Content-Range: {content_range}\r\nAccept-Ranges: bytes\r\n'
        chunk_header = (header + '\r\n').encode()
        chunks = itertools.chain((chunk_header,), (payload[i:i+SLICE] for i in range(0, len(payload), SLICE)))
        connection = next(self.server.connection_ids)
        self.connection.setblocking(False)
        sent = body_sent = 0
        deadline = time.monotonic() + 2
        try:
            for index, chunk in enumerate(chunks):
                remaining = chunk
                while remaining and time.monotonic() < deadline:
                    result = self.server.delivery.handoff(connection, self.server.identity, remaining, self._take)
                    if result.outcome == 'would_block':
                        time.sleep(0.005)
                        continue
                    if result.outcome != 'accepted':
                        if result.outcome == 'denied' and not sent:
                            self.connection.settimeout(1)
                            self._generic(404)
                        return
                    sent += result.count
                    remaining = remaining[result.count:]
                    if index:
                        body_sent += result.count
                        self.server.observe(route, body_sent)
                if remaining:
                    return
        finally:
            self.close_connection = True

    def _take(self, data):
        try:
            return self.connection.send(data)
        except BlockingIOError:
            return 0


@contextmanager
def serve(pdf, token, *, observe=lambda *_: None, assets=None):
    if type(pdf) is not bytes or not token:
        raise ValueError('expected immutable synthetic PDF bytes and a nonempty fixture token')
    with ThreadingHTTPServer(('127.0.0.1', 0), Handler) as server:
        server.pdf = pdf
        server.identity = hashlib.sha256(pdf).hexdigest()
        server.auth = f'Bearer {token}'.encode()
        server.metadata = json.dumps({
            'copy': server.identity, 'length': len(pdf), 'maxRange': MAX_RANGE,
        }).encode()
        server.delivery = Delivery()
        server.connection_ids = itertools.count()
        server.observe = observe
        server.assets = assets
        worker = Thread(target=server.serve_forever, kwargs={'poll_interval': 0.05}, daemon=True)
        worker.start()
        try:
            yield server
        finally:
            server.shutdown()
            worker.join()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pdfjs', type=Path, required=True, help='local pdfjs-dist build directory')
    args = parser.parse_args()
    assets = {'/': Path(__file__).with_name('viewer.html').read_bytes()}
    for name in ('pdf.mjs', 'pdf.worker.mjs'):
        assets[f'/{name}'] = (args.pdfjs / name).read_bytes()
    token = secrets.token_urlsafe(24)
    with serve(make_pdf(), token, assets=assets) as server:
        print(f'http://127.0.0.1:{server.server_port}/#{token}', flush=True)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
