# ADR-0004: Hugging Face as the central corpus repository; standing authorisation for routine corpus operations

- Status: **Accepted by the owner** (standing instruction, 2026-11-24)
- Details: `docs/governance/CORPUS_REPOSITORY_GOVERNANCE.md`

## Context
The corpus is about 2 GB, roughly 16k files, and growing. GitHub suits code and review records but not large binary corpora. Asking for per-operation approval for routine uploads and verification left source copies at risk: the 48 working-store copies stayed unpreserved for two cycles.

## Decision
1. The private HF dataset `hariomahlawat/mimamsa-corpus` is the central corpus repository.
2. GitHub holds code, schemas, tools, tests, documentation and review records.
3. Routine uploads, dataset updates, metadata corrections, preservation and integrity verification are authorised under established policies, with no repeated approval. Each must be versioned, non-destructive, SHA-256 verified by revision-pinned re-download, and recorded in GitHub.
4. Deleting source documents, publishing restricted material, changing repository visibility and legal authentication transactions still need separate owner approval.
5. Credentials stay injected into the environment and are never exposed.

## Consequences
- Agents may write to the HF dataset without asking. They must record every write and verify it.
- Merges to `main`, the GitHub Actions upload gate and session permission controls are unaffected.
- This is not legal validation of any corpus content.
