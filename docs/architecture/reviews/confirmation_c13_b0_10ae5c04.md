# Confirmation review: C13 B0 fixes (branch `claude/c13-b-app` @ `10ae5c04`)

- **Reviewer:** independent B0 reviewer. This review is read-only.
- **Scratch clone:** `reviews/b0/repo`, checked out at `10ae5c04`.
- **Previous review:** `review_c13_b0_dc811848.md`.
- **Probe harness:** `negctl/negctl2.py`, results in `negctl/results2.txt`. It runs in production mode with an OWNER trust list, except for the development-mode controls that are marked as such.
- **Findings CSV:** `confirmation_c13_b0_10ae5c04_findings.csv`.

## Verdict

**11 of 12 P2s confirmed closed. F02 is only partly closed and stays open at P2.** I found no new P1. I add 9 new P3s (C01–C09).

The P3s from the first review are accepted as dispositioned. I did not re-verify each one beyond the probes listed here. F21 is still an owner decision.

## Tests

| Suite | Result |
| --- | --- |
| `app/contract/tests` | 151 passed, 1 skipped. The skipped test is the parity check, which waits for the governance merge |
| `app/design/tests` | 109 passed |

The diff `dc811848..10ae5c04` touches only `app/`, `docs/` and `.github/workflows/app-ci.yml`. App CI still cannot trigger HF sync.

## Production-mode trust-list requirement

**It is correct.** The probe results:

| Probe | Outcome |
| --- | --- |
| N21: production with no trust list | `TRUST_LIST_REQUIRED`; no record parsed |
| N22: `dev-` key id | Refused |
| N23: DEVELOPMENT-holder trust list | Refused |
| N25: key trusted only for `register` signs a release | Refused |
| Revoked key | Refused |
| `allow_unsigned_dev` outside development mode | `MODE_INVALID` |
| Trust-list update signed by a non-trusted (site-Admin) key | Refused |
| Trust-list update with the same sequence (replay) | Refused |
| N20: clean bundle signed by an OWNER key | Accepted |
| N24: development mode with a bare dev key | Accepted |

My earlier harness's clean case fails only because it passed a bare key in production. That is the intended behaviour.

Residual issues:
- `valid_until` on trust-list keys is never enforced (C03).
- `current_release_sequence` is optional even in production, so the downgrade check is silently skipped when the importer omits it (C04).

## P2 confirmation

| ID | Status | Evidence |
| --- | --- | --- |
| F01 | **Closed** | `policy_v1` is rejected on all six non-authenticity axes (SCHEMA). A free-string `approval_ref` is rejected. An approval needs `approval_record` and `appointment_record` in the bundle, and fails with `LEDGER_HEAD_UNVERIFIED` when the ledger head is unpinned |
| F02 | **Partly closed; still P2** | Raised values without a review, IDENTITY_CONFIRMED with HASH_ONLY fidelity, and PUBLISHED with MISMATCH are all rejected; the positive case is accepted. But a bundle-resident `reviewed_record` with `reviewer.kind = AI_AGENT_INDEPENDENT` raises `legal_applicability` to **EVIDENCED at AUTH-LEDGER v0**, and it is accepted. The same reviewer kind also raises `source_authenticity` to IDENTITY_CONFIRMED, and that is accepted too. This contradicts the requested action (reject EVIDENCED while the ledger is at v0) and the plan's rule that nothing in Cycle 13 raises legal applicability without a recorded decision. Independence is only a self-declared `const true`. Separately, record-level validation (the CLI path) treats an unresolvable `review_record_id` as a warning only (C01) |
| F03 | **Closed** | Restricted references are rejected in an edge `node_id`, in `parent_doc_id`, in an upper-cased doc_id inside a title, in an upper-cased sha in free text, and in bundle edges. Variant spellings such as underscores are not matched, which is informational and not required |
| F04 | **Closed** | ADS, `CON.txt`, `con`, `COM1`, `aux/` directory, trailing dot, trailing space, `<`, `LPT¹`, case collisions and symlinks are all rejected, with 0 records parsed. New P3: 8.3 short-name aliases (`DOCUME~1.JSO`) are accepted (C02) |
| F05 | **Closed** | A bad signature or a checksum failure stops validation with 0 records parsed. The manifest `key_id` must name the verifying key. The trust-list change authority is owner-only, both in code and in security §8.1. C03, C04 and C05 are residual P3s |
| F06 | **Closed (spec and code)** | The signed `exclusion_update` channel has a replay check, a register-purpose key and a hash check. `items_to_suppress` exists. Security §8.2 step 9 and §8.4 cover re-application after activation, rollback and restore, and purging. Restricted Admin uploads are aborted before the vault write; nothing is quarantined. New P3: §8.3 does not say where the latest exclusion state is kept so that a restored, older database cannot roll it back (C06) |
| F07 | **Closed (spec)** | `policies/client_state_and_cache.json`: `no-store` on every sensitive class, `Clear-Site-Data` on logout, no localStorage, IndexedDB, service worker or Cache Storage, per-user state server-side, no offline view. B1 must add HTTP header tests |
| F08 | **Closed (spec)** | Authenticode is mandatory for the MSI, payloads, custom actions and the bundled trust list (security §8.1, assessment §12.1, ADR-0005). Verification falls to P6 |
| F09 | **Closed** | README §3.1 now describes the nine layers. There are new schemas for reviewed, appointment, approval and publication records. Refs resolve inside the bundle. A site publication channel (`SITE_ADMIN`, `RELEASE_ACTIVATION`) carried in a bundle is rejected |
| F10 | **Closed** | The new keymap avoids the documented Edge, Chrome and Windows reserved list (tested). New P3: the single-letter keys (B, E, N, K, C, T, M, X, O, P, G) collide with NVDA and JAWS browse-mode quick-navigation keys, and need a documented screen-reader behaviour (C07) |
| F11 | **Closed** | Effective-CSS-px breakpoints, a scaling table, touch layout chosen by pointer type, and a vertical-budget test |
| F12 | **Closed (spec plus reference formatter)** | The query syntax is specified, and the parser is deferred to B1. `citation.py` omits LLM-derived fields and guesses nothing. New P3: the copied legal citation is built from unverified (candidate) metadata and carries no candidate marker once it is on the clipboard (C08) |

## New P3s

| ID | Finding |
| --- | --- |
| C01 | Record-level CLI: a raised value with an unresolvable `review_record_id` is a warning only. Make it an error, or label the CLI as a schema-only check |
| C02 | 8.3 short-name aliases are accepted. Reject segments matching `~[0-9]`, or require 8.3 names to be disabled on the data volume (and check this in P6) |
| C03 | Trust-key `valid_until` is not enforced. Enforce it against the site's trusted time source, or remove the field |
| C04 | `current_release_sequence` is optional in production. Require it, or the explicit `rollback=True` path |
| C05 | `SHA256SUMS` is read twice: once as bytes for the signature check, then again for parsing. This is a time-of-check/time-of-use gap on writable media. Parse the bytes that were verified, and copy the bundle to a private ACL'd folder before validation |
| C06 | Where the latest accepted exclusion state lives is unspecified. Keep the signed updates in an append-only store outside the database backup, and have restore require it |
| C07 | Screen-reader interaction with the single-key shortcuts is undocumented. Document it, and test with NVDA and JAWS in P9 |
| C08 | A legal citation copied from candidate metadata has no candidate marker. Append "(metadata not verified)" unless evidence_fidelity is checked |
| C09 | The ledger-head comparison uses prefix matching in both directions. The schema blocks a 1-character head (probe rejected with SCHEMA), but an exact full-hash comparison would be safer |
