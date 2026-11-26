# Cycle 14 corpus operating direction: cloud first

26 November 2026

Owner direction: corpus should be cloud first. This records the operating direction, not an Authority Ledger decision, permission for a live network acquisition, a release decision, or a change to any existing interlock.

## Existing evidence and transition boundary

- PR #58: f1bbd15dc9a57531b0b061578fdceba94ff35753. PR #59: 8ed353a882feaac54d4b3d4d1613501a3851977f. Staging observed at ee17b0660511b66fdd5307833e11d1268de35b56.
- Owner's local WP1 attempt at dataset revision f4e6ba443ec9c0b89b2c5d21d0b5cda38f55d2dc produced METADATA_INCOMPLETE / WORKER_REJECTED_OR_UNAVAILABLE / exit 1. Local preparation and signed approval succeeded. Actual metadata coverage was not established. Preserve the receipt; no local retry requested. Do not reinterpret the signed local approval as cloud approval.
- Keep both reviewed branches and their acceptance evidence intact. Windows native controls remain applicable to a Windows runner, but do not prescribe them as prerequisites for cloud jobs. Carry forward the bounded request logic, pinned restriction predicate, source hash and receipt invariants, non-destructive journal, release denial and legal validation requirements.
- No changes to application engineering, restricted register, Authority Ledger or HF data in this transition record.

## Default operating model

ChatGPT owns source discovery, corpus reconciliation, controlled acquisition/processing design, tests, evidence management and coordination. Prefer connected read-only metadata tools and existing private GitHub-hosted CI for finite, reproducible CPU jobs. HF remains the private corpus data store. Codex performs targeted independent technical assurance, and Claude owns app-side integration. Owner workstation is reserved for final offline deployment and exceptional explicitly agreed activities.

Avoid a new persistent server, paid Space, GPU or separately billed compute until the owner has approved the cost and need. No new owner commands as the default workflow. Owner decisions should be scope, cost, access and legal approval rather than routine shell execution.

## First cloud job: metadata-only WP1

Use a dedicated cloud-scoped operation, not the Windows launcher and not the existing HF write/sync workflow. The reviewed direct metadata protocol can be reused after a narrowly scoped cloud adaptation.

Existing staging workflow .github/workflows/sync-legal-knowledge-hf.yml already describes GitHub OIDC / HF Trusted Publisher for corpus uploads. That is a possible integration pattern, not proof of a read-only credential or a configured protected environment for WP1. Never reuse the upload credential for this read-only operation without independently establishing least privilege. No live dispatch is authorized here.

1. Confirm whether the connected HF interface can supply revision-qualified, bounded metadata coverage and verifiable completion. Current available filesystem interface does not document an immutable revision parameter or complete pagination attestation. A limited listing is not a complete inventory.
2. If necessary, propose a separate manual cloud runner with immutable reviewed code and dataset revision, a protected owner approval boundary, dedicated verified dataset-read credential, isolated scratch, bounded request count/bytes/time, no blob routes, no upload, no retries beyond the approved policy, and a restricted-predicate binding. Prefer existing infrastructure; verify permissions, dispatch capability and available runner allowance first.
3. In synthetic tests ensure incomplete scope, missing LFS hashes, unexpected paths, credential failures and network failures remain incomplete. Keep private detailed inventory out of public logs and unapproved artifacts; return counts, revision and digests. Determine an approved private persistence mechanism before execution.
4. Obtain explicit operation-specific owner approval, then run and record actual HF metadata coverage. Local-store coverage remains separately unverified, and LFS metadata is not a fresh byte hash. Do not claim full deduplication or acquisition eligibility on metadata alone.

## Next corpus deliveries

- Reconcile known source gaps using existing public official source discovery and immutable metadata evidence.
- Commission a small bounded statutory acquisition batch after separate source/transport/approval gates, only with non-destructive quarantine and no publication.
- Commission a small representative judicial recovery/OCR pilot before the held 534-item recovery; preserve original bytes, aliases and exclusions. Measure fidelity, page anchors and uncertainty. Keep outputs candidate-only.
- Coordinate importer/retrieval safeguards with Claude separately before any legal evidence promotion. No promotion without applicable human legal validation and established authority procedures.

## Non-goals and holds

No bulk corpus download, recovery, HF write, legal promotion, restricted source access, separate billed compute, staging merge or modification of Claude's worktree is authorized by this record. No use of RM-001. Do not re-open the entire Cycle 14 review merely because the runtime changes; review the new execution boundary and relevant regressions only. This is a documentation-only transition branch and does not activate a workflow.
