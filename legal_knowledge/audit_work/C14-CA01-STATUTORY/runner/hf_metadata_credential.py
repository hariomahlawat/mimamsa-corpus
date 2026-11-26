"""Validate least-privilege evidence from Hugging Face's whoami-v2 response.

The provider's public OpenAPI defines the grant structure. This job requires
explicit disabled gated access and an empty global grant list, since the
schema permits omission without defining its meaning. The owner must confirm
the issued token's settings for the exact dataset and use the same credential
for the provider check and enumeration. A repository-content read grant can
access blobs. Transport policy enforces the metadata-only boundary.
"""

from __future__ import annotations

import re


class CredentialScopeError(ValueError):
    def __init__(self):
        super().__init__("dataset-scoped read-only credential could not be verified")


def _known_fields(value, allowed):
    if not isinstance(value, dict) or value.keys() - allowed:
        raise CredentialScopeError()
    return value


def require_dataset_read_scope(whoami: object, repo_id: str) -> None:
    """Accept a single explicit repository-content read grant for the dataset."""
    if not isinstance(whoami, dict) or not isinstance(repo_id, str) or not repo_id:
        raise CredentialScopeError()

    auth = _known_fields(whoami.get("auth"), {"type", "accessToken", "expiresAt"})
    token = _known_fields(auth.get("accessToken"), {"displayName", "role", "fineGrained", "createdAt"})
    if auth.get("type") != "access_token" or token.get("role") != "fineGrained":
        raise CredentialScopeError()

    policy = _known_fields(token.get("fineGrained"), {"scoped", "global", "canReadGatedRepos"})
    if policy.get("global") != [] or policy.get("canReadGatedRepos") is not False:
        raise CredentialScopeError()
    grants = policy.get("scoped")
    if not isinstance(grants, list) or len(grants) != 1:
        raise CredentialScopeError()

    grant = _known_fields(grants[0], {"entity", "permissions"})
    entity = _known_fields(grant.get("entity"), {"_id", "type", "name"})
    resource_id = entity.get("_id")
    if (
        entity.get("type") != "dataset"
        or entity.get("name") != repo_id
        or not isinstance(resource_id, str)
        or re.fullmatch(r"[0-9a-f]{24}", resource_id) is None
        or grant.get("permissions") != ["repo.content.read"]
    ):
        raise CredentialScopeError()
