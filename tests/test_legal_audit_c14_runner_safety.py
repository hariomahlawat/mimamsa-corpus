"""Checks for held operation and safe evidence using inert fixtures only."""
import contextlib
import importlib.util
import io
import json
import socket
import ssl
import sys
import tempfile
import unittest
from email.message import Message
from pathlib import Path
from unittest.mock import Mock, patch

PACKAGE = Path(__file__).resolve().parents[1] / 'legal_knowledge/audit_work/C14-CA01-STATUTORY'
sys.path.insert(0, str(PACKAGE / 'runner'))
import acquisition_batch
import corpus_runner
from test_corpus_runner import API, ROW, downloader

spec = importlib.util.spec_from_file_location('c14_historical_verifier', PACKAGE / 'verify_preserved_copies.py')
historical_verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(historical_verifier)


class RunnerSafetyTests(unittest.TestCase):
    def test_acquisition_interlock_precedes_input_loading(self):
        with patch.object(sys, 'argv', ['acquisition_batch.py', '--execute-approved']):
            with patch.object(Path, 'read_text') as read:
                read.side_effect = AssertionError('operational interlock must precede file access')
                with contextlib.redirect_stderr(io.StringIO()) as stderr, self.assertRaises(SystemExit) as refusal:
                    acquisition_batch.main()
        self.assertEqual(refusal.exception.code, 2)
        self.assertIn('acquisition interlock', stderr.getvalue())

    def test_preservation_interlock_precedes_input_loading(self):
        with patch.object(sys, 'argv', ['corpus_runner.py', '--execute-read-only']):
            with patch.object(corpus_runner, 'load_inventory') as load:
                load.side_effect = AssertionError('operational interlock must precede file access')
                with contextlib.redirect_stderr(io.StringIO()) as stderr, self.assertRaises(SystemExit) as refusal:
                    corpus_runner.main()
        self.assertEqual(refusal.exception.code, 2)
        self.assertIn('preservation interlock', stderr.getvalue())

    def test_historical_verifier_is_offline_only(self):
        with patch.object(sys, 'argv', ['verify_preserved_copies.py', 'synthetic.json', '--execute-read-only']):
            with patch.object(Path, 'read_text') as read:
                read.side_effect = AssertionError('historical interlock must precede file access')
                with contextlib.redirect_stderr(io.StringIO()) as stderr, self.assertRaises(SystemExit) as refusal:
                    historical_verifier.main()
        self.assertEqual(refusal.exception.code, 2)
        self.assertIn('historical verifier is offline only', stderr.getvalue())

    def test_preservation_report_records_the_revision_of_bytes_checked(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            job = Path(tmp) / 'job'
            self.assertEqual(corpus_runner.execute([ROW], 'synthetic', job, API(), downloader()), 0)
            report = json.loads((job / 'verification.json').read_bytes())
        self.assertEqual(report['observed_head_evidence'], 'PATH_PRESENCE_ONLY')
        self.assertFalse(report['observed_head_bytes_verified'])
        self.assertFalse(report['full_backup_verified'])
        self.assertEqual(report['records'][0]['byte_check_revision'], corpus_runner.PRESERVATION)


class InertTransportTests(unittest.TestCase):
    def transport(self):
        with patch.object(acquisition_batch.urllib.request, 'getproxies', return_value={}):
            return acquisition_batch.Transport()

    def test_resolver_error_closes_attempt_without_error_text(self):
        transport = self.transport()
        url = 'https://example.invalid/synthetic.pdf'
        with patch.object(acquisition_batch, 'URLS', {'fixture': url}):
            with patch.object(acquisition_batch, 'check_dns', side_effect=OSError('synthetic detail')):
                with self.assertRaises(OSError), transport.request(url):
                    self.fail('resolver failed before opening an inert response')
        attempt, = transport.attempts
        self.assertIsNotNone(attempt['ended_utc'])
        self.assertEqual(attempt['outcome'], 'DNS_FAILED')
        self.assertEqual(attempt['body_bytes'], 0)
        self.assertNotIn('synthetic detail', json.dumps(attempt))

    def test_checked_peer_retains_typed_address_and_tls_hostname(self):
        hostname = 'example.invalid'
        sockaddr = ('2001:4860:4860::8888', 443, 0, 0)
        answer = (socket.AF_INET6, socket.SOCK_STREAM, socket.IPPROTO_TCP, '', sockaddr)
        context = Mock(check_hostname=True, verify_mode=ssl.CERT_REQUIRED)
        raw_socket = Mock()
        raw_socket.getpeername.return_value = sockaddr
        connection = acquisition_batch.PinnedHTTPSConnection(hostname, answer, context=context)
        with patch.object(acquisition_batch.socket, 'socket', return_value=raw_socket) as make_socket:
            connection.connect()
        make_socket.assert_called_once_with(socket.AF_INET6, socket.SOCK_STREAM, socket.IPPROTO_TCP)
        raw_socket.connect.assert_called_once_with(sockaddr)
        context.wrap_socket.assert_called_once_with(raw_socket, server_hostname=hostname)
        self.assertEqual(connection.peer, sockaddr[0])

    def test_response_receipt_counts_only_body_and_selected_headers(self):
        transport = self.transport()
        url = 'https://example.invalid/synthetic.pdf'
        response = Mock(status=200, headers=Message())
        response.headers['Content-Type'] = 'application/pdf; name=ignored.pdf'
        response.headers['Content-Length'] = '4'
        response.headers['Set-Cookie'] = 'fixture-header-must-not-be-recorded'
        response.read.return_value = b'data'
        response.isclosed.side_effect = [False, True]
        connection = Mock(peer='2001:4860:4860::8888')
        connection.getresponse.return_value = contextlib.nullcontext(response)
        with (patch.object(acquisition_batch, 'URLS', {'fixture': url}),
              patch.object(acquisition_batch, 'check_dns', return_value=[None]),
              patch.object(acquisition_batch, 'PinnedHTTPSConnection', return_value=connection),
              transport.request(url) as body):
            self.assertEqual(body.read(4), b'data')
        attempt, = transport.attempts
        self.assertEqual(attempt['body_bytes'], 4)
        self.assertEqual(attempt['declared_bytes'], 4)
        self.assertEqual(attempt['content_type'], 'application/pdf')
        self.assertEqual(attempt['outcome'], 'COMPLETE')
        self.assertEqual(transport.budget.bytes, 4)
        self.assertNotIn('fixture-header-must-not-be-recorded', json.dumps(attempt))
