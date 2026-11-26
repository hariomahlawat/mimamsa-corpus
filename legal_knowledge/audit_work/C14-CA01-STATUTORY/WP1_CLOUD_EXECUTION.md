# Cloud WP1 execution proposal — 26 November 2026

Owner direction: cloud-first corpus processing; routine technical decisions delegated. This branch is stacked on the reviewed WP1 Windows draft, not staging. Existing reviewed code and local receipt are historical evidence. No Windows commands, signing key or Windows approval are required by the proposed cloud operation. The cloud authority is a dedicated protected GitHub environment, an immutable reviewed code commit and exact dispatch scope. Do not interpret local approval as cloud approval.

## Existing infrastructure and limits

GitHub repository is private; default branch is main. Existing sync workflow declares HF Trusted Publisher / OIDC but has write functions, so do not reuse it for WP1. The proposed dedicated workflow runs on GitHub-hosted Linux, 8-minute maximum, with contents: read and no OIDC permission. No separate billed HF job has been created. GitHub hosted allowance must be checked at account level before any live run. Connector can read checks/logs but does not provide workflow registration, environment provisioning, secret management or new dispatch. The new workflow is not registered on main; workflow_dispatch is not yet available merely by creating this draft branch. Do not merge or circumvent that boundary to make it available.

## Proposed one-time activation requirements

- Independent delta review of cloud adapter, workflow and tests at exact head. Synthetic CI first; never supply credentials to pull request jobs.
- Account owner establishes protected environment hf-corpus-metadata-read with approved deployment branch, required approval/review protection where supported, and dedicated fine-grained HF dataset read-only token in environment secret HF_WP1_READ_TOKEN. No token in chat, logs, repository, commands, or artifacts. The runner validates the actual grant before tree access. Existing upload credentials are unsuitable without scope proof.
- Establish GitHub-hosted allowance and explicitly confirm private artifact access/retention. Detailed restriction-filtered receipt is proposed for private Actions artifact, one day retention; only fixed status, counts and digests appear in logs. No HF writes or external transfer.
- Register the workflow through the normal reviewed repository change process. The live job remains unavailable until workflow registration and protected environment configuration are verified. Set the environment variable WP1_CLOUD_ENABLED=true only after acceptance. The flag alone is not proof of protection; environment policies must be verified by the owner.
- Manual dispatch selects corpus/cloud-wp1-20261126, operation METADATA_GET_ONLY, revision f4e6ba443ec9c0b89b2c5d21d0b5cda38f55d2dc, exact final reviewed branch commit. No automatic run on push, PR, scheduled trigger or retry. Any new revision requires updated reviewed scope. This is a dedicated read-only operation, not a source acquisition authorization.

## Reused reviewed controls

Pinned byte-exact runtime, restriction register and predicate; exact private dataset and seven roots; verified TLS and canonical metadata routes; request/response/time bounds; supervised worker; no raw exception or token logging; validated inventory digest; exclusive scratch receipt; incomplete/negative outcomes never eligible for acquisition. Cloud wrapper adds fixed stage codes for the prior generic worker failure. The hosted environment boundary is not proven by the synthetic tests.

No corpus source downloads, HF writes, acquisition, judicial recovery, releases, legal promotions, restricted source access, or ledger changes. Local preservation-store coverage is still unverified. No legal conclusions follow from inventory metadata.
