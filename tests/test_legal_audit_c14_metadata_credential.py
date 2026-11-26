"""Synthetic checks for the C14 metadata credential's least-privilege gate."""

from pathlib import Path
import sys
import unittest


RUNNER = Path(__file__).resolve().parents[1] / "legal_knowledge/audit_work/C14-CA01-STATUTORY/runner"
REPO = "fictional-owner/inventory"


def response():
    return {
        "auth": {
            "type": "access_token",
            "accessToken": {
                "role": "fineGrained",
                "displayName": "discarded synthetic display name",
                "createdAt": "2026-11-25T00:00:00Z",
                "fineGrained": {
                    "global": [],
                    "canReadGatedRepos": False,
                    "scoped": [{
                        "entity": {"type": "dataset", "name": REPO, "_id": "a" * 24},
                        "permissions": ["repo.content.read"],
                    }],
                },
            },
        },
    }


class CredentialScopeTests(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, str(RUNNER))
        self.addCleanup(sys.path.remove, str(RUNNER))
        from hf_metadata_credential import CredentialScopeError, require_dataset_read_scope

        self.check = require_dataset_read_scope
        self.refusal = CredentialScopeError

    def test_accepts_single_exact_dataset_read_grant(self):
        data = response()
        self.assertIsNone(self.check(data, REPO))

    def test_rejects_unproved_or_broader_scope_with_redacted_error(self):
        for path, value in (
            (("auth", "type"), "oauth"),
            (("auth", "accessToken", "role"), "read"),
            (("auth", "accessToken", "role"), "write"),
            (("auth", "accessToken", "fineGrained", "global"), ["discussion.write"]),
            (("auth", "accessToken", "fineGrained", "canReadGatedRepos"), True),
            (("auth", "accessToken", "fineGrained", "canReadGatedRepos"), 0),
            (("auth", "accessToken", "fineGrained", "unknownScope"), []),
            (("auth", "accessToken", "additionalGrants"), []),
            (("auth", "resource"), {"sub": "synthetic-resource"}),
        ):
            with self.subTest(path=path, value=value):
                data = response()
                scope = data
                for key in path[:-1]:
                    scope = scope[key]
                scope[path[-1]] = value
                self.assert_redacted_refusal(data)

    def test_rejects_missing_or_malformed_scope_evidence(self):
        for key in ("global", "canReadGatedRepos", "scoped"):
            with self.subTest(key=key):
                data = response()
                del data["auth"]["accessToken"]["fineGrained"][key]
                self.assert_redacted_refusal(data)
        for data in (None, [], {}, {"auth": None}, {"auth": {"type": "access_token", "accessToken": []}}):
            with self.subTest(data=data):
                self.assert_redacted_refusal(data)

    def test_rejects_extra_or_other_repository_grants(self):
        initial = response()["auth"]["accessToken"]["fineGrained"]["scoped"][0]
        for entity, permissions in (
            ({"name": "fictional-owner/other"}, ["repo.content.read"]),
            ({"type": "model"}, ["repo.content.read"]),
            ({"name": "fictional-owner", "type": "user"}, ["repo.content.read"]),
            ({"name": "fictional-owner", "type": "org"}, ["repo.content.read"]),
            ({"_id": "bad-id"}, ["repo.content.read"]),
            ({}, ["repo.content.read", "repo.write"]),
            ({}, ["repo.write"]),
        ):
            with self.subTest(entity=entity, permissions=permissions):
                data = response()
                grant = data["auth"]["accessToken"]["fineGrained"]["scoped"][0]
                grant["entity"].update(entity)
                grant["permissions"] = permissions
                self.assert_redacted_refusal(data)

        data = response()
        data["auth"]["accessToken"]["fineGrained"]["scoped"].append(initial)
        self.assert_redacted_refusal(data)

    def assert_redacted_refusal(self, data):
        with self.assertRaises(self.refusal) as context:
            self.check(data, REPO)
        self.assertEqual(str(context.exception), "dataset-scoped read-only credential could not be verified")
        self.assertIsNone(context.exception.__cause__)


if __name__ == "__main__":
    unittest.main()
