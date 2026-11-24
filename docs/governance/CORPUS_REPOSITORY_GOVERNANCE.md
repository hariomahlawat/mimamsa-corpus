# Corpus repository governance: Hugging Face and GitHub (standing owner instruction, 2026-11-24)

This document records a **standing project instruction from the owner**. It applies for the whole development lifecycle until the owner withdraws or amends it in writing, in an ADR or a reviewed amendment to this file.

## 1. Roles of the two repositories

| Repository | Holds | Visibility |
| --- | --- | --- |
| **Hugging Face dataset `hariomahlawat/mimamsa-corpus`**: the **central corpus repository** | Source documents (raw PDFs/HTML, preservation copies), extracted text, metadata records, sections, manifests, relations, corpus snapshots | Private; must stay private |
| **GitHub `hariomahlawat/mimamsa-corpus`** | Application code, schemas, tools, tests, documentation, review records and audit work (registers, proposals, evaluations, hash ledgers) | Private |

GitHub records must still be enough to trace and re-verify every corpus object on Hugging Face: path, revision, SHA-256 and provenance.

## 2. Standing authorisation (no repeated approval needed)

Within the established project policies, the following are authorised as **routine operations**:
- uploads to the HF dataset;
- dataset updates;
- metadata corrections;
- source preservation;
- integrity verification, including revision-pinned downloads and hash checks.

The controlling policies are:
- `CLAUDE.md` crawler and pipeline rules;
- `docs/legal-audit/EVIDENCE_STANDARD.md`;
- `docs/legal-audit/SOURCE_AUTHORITY_POLICY.md`;
- `docs/HF_SYNC_SAFEGUARD.md`;
- AUTH-LEDGER rules.

Agents do not ask for approval again for these operations.

Every routine HF write must:
1. **Use versioned, non-destructive updates.** Add new paths or new revisions. Never rewrite history or force-push. Never delete or overwrite an original source document. Corrections go in new files or overlays that reference the original.
2. **Keep provenance complete.** Each source document carries its source URL or origin, retrieval time, SHA-256 and acquisition record. Each commit message says what changed and why.
3. **Verify with SHA-256.** Hash before upload. After upload, re-download at the **pinned commit revision** into a fresh directory and compare against a manifest held independently in git. Record the HF commit id and the result in GitHub.
4. **Be reproducible.** Each derived dataset file is produced by a tool committed to GitHub that has a `--check` mode.
5. **Keep the dataset private.** Do not upload material outside the project's access rules.

## 3. Operations that still need separate, explicit owner approval

- **Deletion** of any source document, on HF or GitHub, including temporary working copies, unless the owner has already approved release after verification.
- **Publication of restricted material.** This includes anything marked For Official Use Only, Restricted, Confidential or Secret, or otherwise access-limited. It applies to any destination, including making such material visible to a wider audience.
- **Changes to repository visibility** on HF or GitHub.
- **Legal authentication transactions**, including any real AUTH-LEDGER BIND or approval.

Also unchanged, and still requiring their own approvals or rules:
- merges into `main`;
- the GitHub Actions corpus-upload gate (`I-APPROVE-CORPUS-UPLOAD`, `docs/HF_SYNC_SAFEGUARD.md`);
- external source acquisition beyond the allow-list rules;
- the never-contact list;
- any action the session's own permission controls block. Those are never circumvented.

## 4. Credentials

- HF credentials are **injected securely into the environment**, preferably as a network secret limited to `huggingface.co`, so the value never enters the session.
- Never print, log, echo, commit or paste token values, and never ask for them in chat.
- Use the narrowest scope that works: a fine-grained token with read and write on this dataset only.

## 5. Records

Each HF write is recorded in the relevant GitHub audit folder with:
- the HF commit id;
- the parent revision;
- the paths added;
- the SHA-256 manifest;
- the verification result.

The first operation under this instruction is the Cycle 12 preservation of the 48 working-store copies: HF commit `5524c3d99b6a069249012fecea75093b875a22c7`, byte-verified (`legal_knowledge/audit_work/C12-CONSOLIDATION/preservation/PRESERVATION_STATUS_C12.md`).
