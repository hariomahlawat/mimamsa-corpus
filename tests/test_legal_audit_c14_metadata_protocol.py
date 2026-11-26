"""Offline HF 2.4 metadata wire-contract tests with inert exchanges."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parents[1]
                       / "legal_knowledge/audit_work/C14-CA01-STATUTORY/runner"))
import hf_metadata_transport as transport


REVISION = "a" * 40
ORIGIN = "https://huggingface.co"
BASE = f"{ORIGIN}/api/datasets/{transport.REPO}"
STORE = transport.STORES[0]
TREE = f"{BASE}/tree/{REVISION}/{quote(STORE, safe='')}"
INITIAL = TREE + "?recursive=true&expand=false"


class MetadataProtocolTests(unittest.TestCase):
    def tree(self, api):
        return list(api.list_repo_tree(
            transport.REPO, path_in_repo=STORE, recursive=True, expand=False,
            revision=REVISION, repo_type="dataset",
        ))

    def test_sdk_encoded_path_queries_and_lfs_projection(self):
        expected = [INITIAL, INITIAL + "&cursor=marker%2B%2F%3D"]
        bodies = [
            [{"type": "directory", "path": STORE + "/synthetic"}],
            [{"type": "file", "path": STORE + "/synthetic/item.pdf", "size": 10,
              "oid": "c" * 40, "lfs": {"size": 10, "oid": "b" * 64, "pointerSize": 118}}],
        ]
        requests = []

        def exchange(url, cap, remaining):
            index = len(requests)
            requests.append(url)
            self.assertEqual(url, expected[index])
            self.assertGreater(cap, 0)
            self.assertGreater(remaining, 0)
            next_link = (f'<{TREE}?expand=false&cursor=marker%2B%2F%3D&recursive=true>; rel="next"'
                         if index == 0 else None)
            return json.dumps(bodies[index]).encode(), next_link

        rows = self.tree(transport.MetadataAPI(REVISION, exchange))
        self.assertEqual(requests, expected)
        self.assertEqual(rows[0].path, STORE + "/synthetic")
        self.assertFalse(hasattr(rows[0], "size"))
        self.assertEqual((rows[1].path, rows[1].size, rows[1].lfs.sha256, rows[1].lfs.size),
                         (STORE + "/synthetic/item.pdf", 10, "b" * 64, 10))

    def test_pagination_allows_standard_next_and_previous_relations(self):
        calls = []
        next_url = INITIAL + "&cursor=second"

        def exchange(url, cap, remaining):
            calls.append(url)
            if len(calls) == 1:
                return b"[]", f'<{INITIAL}>; rel="first", <{next_url}>; rel="next"'
            return b"[]", f'<{INITIAL}>; rel="prev"'

        self.assertEqual(self.tree(transport.MetadataAPI(REVISION, exchange)), [])
        self.assertEqual(calls, [INITIAL, next_url])

    def test_failed_continuation_does_not_emit_a_second_request(self):
        for tail in (
            f'<{INITIAL}&cursor=one>, <{INITIAL}&cursor=two>; rel="next"',
            f'<{INITIAL}&cursor=one>; rel="next", <{INITIAL}&cursor=two>; rel="next"',
            f'<{INITIAL}&cursor=%ZZ>; rel="next"',
            f'<{TREE}?recursive=false&cursor=one>; rel="next"',
        ):
            with self.subTest(header=tail):
                calls = []

                def exchange(url, cap, remaining):
                    calls.append(url)
                    return b"[]", tail

                with self.assertRaises(ValueError):
                    self.tree(transport.MetadataAPI(REVISION, exchange))
                self.assertEqual(calls, [INITIAL])

    def test_repeated_cursor_stops_even_with_explicit_default_page_size(self):
        calls = []

        def exchange(url, cap, remaining):
            calls.append(url)
            limit = "" if len(calls) == 1 else "&limit=1000"
            return b"[]", f'<{INITIAL}{limit}&cursor=repeat>; rel="next"'

        with self.assertRaisesRegex(ValueError, "pagination loop"):
            self.tree(transport.MetadataAPI(REVISION, exchange))
        self.assertEqual(calls, [INITIAL, INITIAL + "&cursor=repeat"])

    def test_transport_request_target_contains_only_canonical_metadata_routes(self):
        for url in (INITIAL, INITIAL + "&cursor=token", BASE + "/revision/" + REVISION,
                    ORIGIN + "/api/whoami-v2"):
            with self.subTest(url=url):
                self.assertEqual(transport.metadata_request_target(url, REVISION),
                                 url.removeprefix(ORIGIN))
        for url in (TREE.replace("%2F", "/") + "?recursive=true&expand=false",
                    INITIAL + "&unexpected=true", ORIGIN + "/api/whoami-v2?expand=true",
                    BASE + "/revision/" + "main"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                transport.metadata_request_target(url, REVISION)

    def test_whoami_only_returns_permission_evidence(self):
        exchanges = []

        def exchange(url, cap, remaining):
            exchanges.append((url, cap))
            response = {
                "name": "synthetic-account",
                "email": "fixture@example.invalid",
                "auth": {"type": "access_token", "accessToken": {"role": "fineGrained", "displayName": "synthetic-token",
                                         "fineGrained": {"scoped": []}}},
            }
            return json.dumps(response).encode(), None

        info = transport.MetadataAPI(REVISION, exchange).credential_info()
        self.assertEqual(info, {"auth": {"type": "access_token", "accessToken": {
            "role": "fineGrained", "displayName": "synthetic-token", "fineGrained": {"scoped": []},
        }}})
        self.assertEqual([url for url, _ in exchanges], [ORIGIN + "/api/whoami-v2"])
        self.assertLess(exchanges[0][1], transport.MAX_PAGE_BYTES)

    def test_whoami_rejects_malformed_permission_evidence_and_pagination(self):
        for body, link in ((b'{"auth": null}', None),
                           (b'{"auth":{"accessToken":{"role":1}}}', None),
                           (b'{"auth":{"accessToken":{"role":"read"}}}', "unexpected"),
                           (b'{"auth":{"accessToken":{"role":"read","other":NaN}}}', None)):
            with self.subTest(body=body, link=link), self.assertRaises(ValueError):
                transport.MetadataAPI(REVISION, lambda *_: (body, link)).credential_info()

    def test_total_budget_applies_across_info_requests(self):
        body = json.dumps({"id": transport.REPO, "sha": REVISION, "private": True}).encode()
        caps = []

        def exchange(url, cap, remaining):
            caps.append(cap)
            return body, None

        with patch.object(transport, "MAX_TOTAL_BYTES", len(body) + 1):
            api = transport.MetadataAPI(REVISION, exchange)
            api.dataset_info(transport.REPO, revision=REVISION)
            with self.assertRaisesRegex(ValueError, "response exceeded budget"):
                api.dataset_info(transport.REPO, revision=REVISION)
        self.assertEqual(caps, [len(body) + 1, 1])

    def test_nonfinite_or_non_utf8_json_does_not_enter_inventory(self):
        for body in (b'{"sha": Infinity}', b'{"sha":"\xff"}',
                     '{"sha":"candidate"}'.encode("utf-16")):
            with self.subTest(body=body), self.assertRaises(ValueError):
                transport.MetadataAPI(REVISION, lambda *_: (body, None)).dataset_info(
                    transport.REPO, revision=REVISION)
