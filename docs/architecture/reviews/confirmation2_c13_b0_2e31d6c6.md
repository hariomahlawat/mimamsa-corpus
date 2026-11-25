# Confirmation review 2: F02 and C01–C09 (branch `claude/c13-b-app` @ `2e31d6c6`)

- **Reviewer:** independent B0 reviewer. This review is read-only.
- **Scratch clone:** `reviews/b0/repo`, checked out at `2e31d6c6`.
- **Previous rounds:** `review_c13_b0_dc811848.md` and `confirmation_c13_b0_10ae5c04.md`.
- **Probe harness:** `negctl/negctl3.py`, results in `negctl/results3.txt`. It is rewritten for the current schema:
  - production mode, with an OWNER trust list;
  - `current_release_sequence=0` (now mandatory);
  - the current `reviewed_record` shape, with `reviewer.reviewer_id` and `reviewed_artefact {author_id, reviewed_commit}`.

  The author was right: my 10ae5c04 harness stopped at the release-sequence check, and its F02 positive case used the old review schema. I did not reuse it.

## Verdict

**F02 is closed. C01–C09 are all closed.** I found no new P1 or P2. One informational residual remains (R1).

**Tests:**

| Suite | Result |
| --- | --- |
| `app/contract` | 181 passed, 1 skipped. The skipped test is the parity check, which waits for the governance merge |
| `app/design` | 109 passed |

**Positive controls, all accepted:**
- B00: clean bundle;
- B02: an AI review raises `evidence_fidelity` to DOCUMENTARY_CHECKED;
- A05: `legal_applicability` raised with a full approval and appointment chain at ledger 1 with a trusted head;
- A10: a HUMAN review confirms identity with official-source evidence;
- I07: a candidate reviewed by an independent reviewer whose author matches.

The controls are therefore not rejecting everything.

## F02: the requested checks

| Requirement | Probes | Outcome |
| --- | --- | --- |
| An AI review cannot raise `legal_applicability` at v0 | A01, A02 (`reviewed_record` on the legal_applicability axis, AI and HUMAN); A03 (UNRESOLVED, PARTIAL_CHAIN, CONFLICTING, NOT_APPLICABLE with no review); A04 (EVIDENCED with a full approval and appointment chain at v0) | All rejected. The `reviewed_record` axis enum excludes `legal_applicability` (SCHEMA). `LEDGER_V0_NO_APPLICABILITY` and `LEGAL_AXIS_NEEDS_APPROVAL` fire. No technical review, human or AI, can set this axis; it needs an approval record under an appointment, and only when the ledger is above v0 |
| An AI review cannot raise `legal_approval` at v0 | A06 (T1 with full chain); A07 (`reviewed_record` on the legal_approval axis); A08 (APPROVAL_RECORDED_UNCONFIRMED) | All rejected (`LEDGER_V0_NO_APPROVAL`, SCHEMA) |
| An AI review cannot raise `source_authenticity` above the documentary level | A09 (AI review with valid official-source evidence); A14 (AI review with custodian-certificate evidence); A11 (HUMAN review with AUTH-LEDGER evidence at v0); A12 (no evidence); A13 (third-party carrier) | All rejected (`AI_REVIEW_CANNOT_CONFIRM_IDENTITY`, `AUTHENTICITY_EVIDENCE_INVALID`, `AUTHENTICITY_EVIDENCE_REQUIRED`). A15: PROVISIONAL is accepted without a review, which is consistent with it being documentary-level |
| Independence is checked structurally | I01: reviewer equals author. I02: same, differing only by case. I03: `reviewed_commit` is not a producing or release commit. I04: dangling subject. I05: legacy self-declared `independent_of_author`. I06: candidate where the declared author differs from the recorded `extractor.author_id` and the reviewer is that recorded author | All rejected (`REVIEW_NOT_INDEPENDENT`, `REVIEW_COMMIT_MISMATCH`, `DANGLING_REVIEW`, `REVIEW_AUTHOR_MISMATCH`, SCHEMA) |

**R1 (informational, not a finding):** for document and source-copy subjects there is no recorded author. Independence there reduces to two things:
- `reviewer_id` differs from the self-declared `author_id` (probe I08 is accepted when the two ids differ);
- the commit must match.

The owner signature on the bundle carries the remaining trust, as it does for `reviewer.kind`. Recording an author on documents (for example, a pipeline run id in provenance) would make the check symmetric with candidates.

## C01–C09

| ID | Status | Evidence |
| --- | --- | --- |
| C01 | Closed | Record-level: an unresolvable `review_record_id` is now an error (`REVIEW_UNRESOLVED_OUTSIDE_BUNDLE`) |
| C02 | Closed | `data/DOCUME~1.JSO` is rejected as `PATH_HAZARD`, with 0 records parsed |
| C03 | Closed | A release key past `valid_until` is not usable (`SIGNATURE_INVALID`); `today` comes from the site's trusted date |
| C04 | Closed | `RELEASE_SEQUENCE_REQUIRED` when the active sequence is missing; `DOWNGRADE_OR_REPLAY` for active 5 against bundle 1 |
| C05 | Closed | `SHA256SUMS` is read once, and the verified bytes are the bytes parsed (code inspection). Security §8.2 adds copying the bundle to a private ACL'd work folder |
| C06 | Closed (spec and code) | `ExclusionStore` keeps signed updates append-only, outside the database and backups. `load_latest` and `state_for_restore` refuse a missing store, or one older than the restored database (security §8.3) |
| C07 | Closed (spec) | Design 05 documents screen-reader behaviour: `role="application"` only on the results grid and the viewer, visible buttons and a command palette for every action, a "Screen-reader mode" setting, and NVDA/JAWS testing in P9 |
| C08 | Closed | The copied citation ends "(metadata not verified)" unless evidence fidelity has been checked |
| C09 | Closed | The ledger head is compared by exact full-hash equality. An 8-character prefix is rejected (`LEDGER_HEAD_UNVERIFIED`, SCHEMA) |

## Remaining for others

- **P6:** Authenticode verification, junction detection, BitLocker, and 8.3 names disabled on the data volume.
- **P9:** the reserved-key list, chip density, and NVDA/JAWS testing.
- **B1:** HTTP header tests and query-parser tests.
- **Owner:** the D-08 holdings exception (F21).
