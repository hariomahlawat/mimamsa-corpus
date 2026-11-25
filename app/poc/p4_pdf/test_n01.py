import concurrent.futures
import hashlib
import http.client
import threading
import unittest

from delivery import Delivery
from harness import make_pdf, serve


class DeliveryTests(unittest.TestCase):
    def test_two_connections_contend_for_one_site_reservation(self):
        gate = Delivery(site_limit=64, connection_limit=64)
        ready = threading.Barrier(2)
        def submit(connection):
            ready.wait(timeout=2)
            return gate.handoff(connection, 'copy', b'x' * 64, len)
        with concurrent.futures.ThreadPoolExecutor() as pool:
            results = list(pool.map(submit, ('A', 'B')))
        self.assertEqual(sorted(result.outcome for result in results), ['accepted', 'would_block'])
        self.assertEqual(gate.outstanding, 64)

    def test_partial_and_uncertain_credit_survive_withdrawal(self):
        gate = Delivery(site_limit=64, connection_limit=64)
        first = gate.handoff('A', 'copy', b'x' * 64, lambda data: 16)
        self.assertEqual(first.count, 16)
        self.assertEqual(gate.outstanding, 16)
        second = gate.handoff('A', 'copy', b'y' * 48, lambda data: None)
        self.assertEqual(second.outcome, 'uncertain')
        self.assertEqual(gate.handoff('A', 'other', b'z', len).outcome, 'denied')
        gate.withdraw('copy')
        self.assertEqual(gate.outstanding, 64)
        gate.confirm_drain(first.attempt)
        self.assertEqual(gate.outstanding, 48)
        self.assertFalse(gate.confirm_drain(first.attempt))
        gate.confirm_drain(second.attempt)
        self.assertEqual(gate.outstanding, 0)

    def test_fence_denies_next_slice_but_preserves_unrelated_delivery(self):
        gate = Delivery()
        observed = []
        def transport(data):
            observed.append(data)
            return len(data)
        gate.handoff('A', 'copy', b'first', transport)
        gate.withdraw('copy')
        self.assertEqual(gate.handoff('A', 'copy', b'second', transport).outcome, 'denied')
        gate.handoff('B', 'other', b'unrelated', transport)
        self.assertEqual(observed, [b'first', b'unrelated'])


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.pdf = make_pdf()
        self.identity = hashlib.sha256(self.pdf).hexdigest()
        self.token = 'fixture-session'
        self.pause = None
        self.first_slice = threading.Event()
        self.resume = threading.Event()
        def observe(route, offset):
            if route == '/pdf' and offset and self.pause:
                self.first_slice.set()
                self.resume.wait(timeout=3)
        self.fixture = serve(self.pdf, self.token, observe=observe)
        self.server = self.fixture.__enter__()
        self.addCleanup(self.fixture.__exit__, None, None, None)

    def request(self, path, headers=None):
        with_connection = http.client.HTTPConnection(*self.server.server_address, timeout=4)
        self.addCleanup(with_connection.close)
        with_connection.request('GET', path, headers=headers or {})
        return with_connection.getresponse()

    def test_authenticated_metadata_and_exact_near_end_range(self):
        self.assertGreater(len(self.pdf), 256 * 1024)
        auth = {'Authorization': f'Bearer {self.token}'}
        response = self.request('/metadata', auth)
        self.assertEqual(response.status, 200)
        self.assertIn(self.identity.encode(), response.read())
        offset = len(self.pdf) - 512
        response = self.request(f'/pdf?copy={self.identity}', {**auth, 'Range': f'bytes={offset}-{len(self.pdf)-1}'})
        self.assertEqual(response.status, 206)
        self.assertEqual(response.getheader('Content-Range'), f'bytes {offset}-{len(self.pdf)-1}/{len(self.pdf)}')
        self.assertEqual(response.read(), self.pdf[offset:])

    def test_unauthorized_requests_do_not_disclose_protected_size(self):
        response = self.request(f'/pdf?copy={self.identity}', {'Range': 'bytes=0-5'})
        self.assertEqual(response.status, 404)
        self.assertIsNone(response.getheader('Content-Range'))
        response.read()

    def test_full_multi_oversize_and_stale_conditional_requests_fail(self):
        auth = {'Authorization': f'Bearer {self.token}'}
        for extra in ({}, {'Range': 'bytes=0-2,4-5'}, {'Range': 'bytes=0-131072'},
                      {'Range': 'bytes=0-5', 'If-Range': '"stale"'}):
            with self.subTest(extra=extra):
                response = self.request(f'/pdf?copy={self.identity}', {**auth, **extra})
                self.assertEqual(response.status, 416)
                self.assertIsNone(response.getheader('Content-Range'))
                response.read()

    def test_withdrawal_interrupts_an_active_response(self):
        self.pause = True
        response = self.request(f'/pdf?copy={self.identity}', {
            'Authorization': f'Bearer {self.token}', 'Range': 'bytes=0-65535'})
        try:
            self.assertTrue(self.first_slice.wait(timeout=3))
            self.server.delivery.withdraw(self.identity)
        finally:
            self.resume.set()
        with self.assertRaises(http.client.IncompleteRead) as error:
            response.read()
        self.assertGreater(len(error.exception.partial), 0)
        self.assertLess(len(error.exception.partial), 65536)
        denied = self.request('/metadata', {'Authorization': f'Bearer {self.token}'})
        self.assertEqual(denied.status, 404)
        denied.read()
        invalid_range = self.request(f'/pdf?copy={self.identity}', {
            'Authorization': f'Bearer {self.token}', 'Range': 'bytes=0-1,2-3'})
        self.assertEqual(invalid_range.status, 404)
        self.assertIsNone(invalid_range.getheader('Content-Range'))
        invalid_range.read()


if __name__ == '__main__':
    unittest.main()
