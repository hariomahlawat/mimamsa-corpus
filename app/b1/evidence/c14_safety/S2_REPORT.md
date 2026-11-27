# C14 S2: safety. Withdrawal invalidation, scope and reinstatement; account lockout, throttling, unlock and audit log

**Branch and base.** Branch `claude/c14-safety`, based on `legal-knowledge/v2.5-staging` at `ee17b066`.

**Scope.** Audit findings F05 and F15, plus the owner's withdrawal-scope and reinstatement policies. Nothing outside that scope was touched: search and ranking, Statutes, the results list, hybrid search and Hindi handling are unchanged.

## 1. What changed

### Withdrawal enforcement in the client (F05)

**Server.**
- Every `/api/*` response carries `X-Mimamsa-Policy-Epoch`, the serving-policy epoch at the moment the response is sent.
- New endpoint `GET /api/policy` returns the epoch. It checks the session without refreshing it, so an idle session still ends after 30 minutes.

**Client.**
- `api.js` notes the epoch on every API response, and `viewer.js` notes it on PDF metadata and range responses. A change raises `mimamsa:policy-changed`.
- `research.revalidateOpenDocuments()` re-checks each open tab:
  - an ordinary tab through the document route;
  - a tab pinned to an earlier copy through `/api/cite`.
- `research.invalidateDocument(docId)` handles a document that is no longer available. It:
  - destroys the viewer;
  - removes the header, text and evidence;
  - shows the generic notice "This document is not available in this installation." (`.docempty[data-invalidated]`).
- Triggers:
  - an epoch change seen on any response;
  - an epoch poll every 10 s, only while documents are open and the page is visible;
  - a 404 on PDF metadata or a range, now routed to `invalidateDocument` for background tabs too;
  - a network failure in the viewer, which prompts a re-check.
- Viewer edits are kept minimal:
  - two calls to `noteEpoch`;
  - the "unavailable" state reported when a page fetch fails after a 404.
- The withdrawal dialog wording now matches what actually happens. "Open viewers are cut off" is replaced by: transfers in progress are cut off, and pages already on screen are cleared at the reader's next action or within about 10 s.

**Correction to audit F05.** The audit said a deep link to a withdrawn document "silently opens the empty research home". That was an artefact of the audit probe. It captured only the first 300 characters of `main`, which ends before the document pane. The screenshot `J13b-deep-link-after-withdrawal.jpg` shows "Not available / This document is not available in this installation." Deep links were already correct; this branch adds a regression journey (C14-S2-02) and the acceptance check J13b-DL.

### Mid-transfer enforcement test

Protection was already in place through the R2-N01 writer-priority fence and the reset of active streams. It is now proven at two levels.

**C# test `AnInProgressRangeTransferIsCutOffByAWithdrawal`.**
- Runs a dedicated service: test mode, delivery slice 256 bytes, a 5 s `after-first-slice` pause, and its own database `<test db>_xfer`. A separate database is needed because the single-instance lock is per database.
- **Control:** the same range completes.
- **Test:** the first slice arrives; then the withdrawal returns `reset_streams >= 1`; the transfer ends short, with fewer than the requested bytes; a new range then returns 404.

**Playwright journey C14-S2-04.**
- A range request is admitted (credit reserved) and paused before handoff (`before-enter`). During the pause the document is withdrawn.
- **Result:** 404 and 0 bytes. The control without a withdrawal returns 206 with 100 bytes.

No change was made to transport, ledger or fence code.

### Withdrawal scope (owner policy)

**`WithdrawalScope.Compute`** is a pure function, unit-tested. It sorts what a withdrawal touches into three groups:

| Group | What it is | Treatment |
| --- | --- | --- |
| Own copies | Every copy of the named doc_id, current and earlier editions | Always included (F01 guarantee unchanged) |
| Verified duplicates | Other doc_ids with the same SHA-256 whose originals were re-hashed at load | Included only on explicit opt-in, one by one |
| Distinct editions | Same type, and the same normalised title or number, but different bytes | Listed for information; never included |

**API.**
- `GET /api/admin/withdraw-scope` lists the three groups.
- `POST /api/admin/withdraw` accepts `include_duplicates[]`. Anything that is not a verified duplicate is refused with 400, and nothing is withdrawn.
- Each withdrawal row records its scope: `document`, or `verified-duplicate-of:<id>`.

**Dialog.** It shows a checkbox per verified duplicate and a list of the distinct editions.

### Reinstatement (owner policy)

`POST /api/admin/reinstate` requires:
- an Admin;
- CSRF token and Origin check;
- a reason of 3–500 characters.

**Renewed eligibility verification.** `Eligibility.ReinstatementProblems` checks, at the moment of reinstatement:
- the document is in the ACTIVE generation;
- it is published for all users;
- no copy is on the restricted-material register;
- every copy re-hashes from the vault now, not from the load-time cache.

**On failure:** 409 with the list of problems, an audit event `reinstate_refused`, and the document stays withdrawn.

**Order of operations.** `ServingState.ReinstateAsync` commits the durable change first (`vault_copies` set eligible, epoch +1, a history row with the verification summary). Only then does it relax the in-memory fence. A failed commit therefore leaves the document withdrawn (fail closed).

**UI.** The history table is now "Withdrawals and reinstatements" (columns: action, scope, verification). A "Reinstate…" dialog appears on the latest row of each document that is currently withdrawn.

### Accounts (F15)

**Lockout fix** (`IdentityStore.LoginDetailedAsync`):
- An attempt while locked is refused before any password check. It is not counted and does not move `locked_until`.
- The lock is set once, at the 5th failure.
- After an expired lock, the count starts again.

**Lock duration.** 5 minutes, configurable only in test mode (`Mimamsa:Test:LockSeconds`).

**Throttling** (`LoginThrottle`): a sliding window of failed attempts, defaults:

| Limit | Value | Setting |
| --- | --- | --- |
| Per username | 10 per 5 min | `Mimamsa:Login:ThrottlePerUsername` |
| Per source address | 30 per 5 min | `Mimamsa:Login:ThrottlePerSource` |

- Both settings have a floor of 6 and a window of at least 10 s.
- A throttled attempt is refused before any password work: 429 with `Retry-After` and a generic text. It applies to unknown usernames in exactly the same way.

**Admin unlock.** `POST /api/admin/unlock` requires a reason, and the reason is recorded. `GET /api/admin/accounts` lists accounts. The Administration page has an Accounts table with "Unlock…".

**Audit log.**
- Events: `login`, `login_failed`, `lockout`, `login_refused_locked`, `login_throttled`, `unlock`, `withdraw`, `reinstate`, `reinstate_refused`.
- Read-only, paged view: `GET /api/admin/audit?before=&limit=` and the Audit log table, with Newest and Older controls.
- Content-free: no passwords, no search text. Unknown usernames are stored as `unknown`, so a password typed into the username field is never stored.

**Unchanged.** The 6-character password policy (PR #61). No password management or account recovery was added.

## 2. Tests

| Suite | Result | Notes |
| --- | --- | --- |
| C# (unit, site, HTTP, transfer) | **101/101** | 89 existing, unchanged, plus 12 new in `SafetyTests.cs` |
| Playwright SYN and sample | **35/35** across the final runs | 30 existing plus 5 new (C14-S2-01 to C14-S2-05). Full run: 34/35. The one failure was UX-06, at sign-in: HTTP 500 because the shared PostgreSQL was out of connection slots (`remaining connection slots are reserved`, 14 occurrences in pg.log, caused by parallel streams). Re-run SYN: 26/26. Sample 9/9 in the full run |
| Design tests | 117/117 | |
| `gen_tokens --check` | no drift | |
| Retrieval and transport oracles | not edited | |

**Existing test files changed (no behaviour reversed).**
- `HttpTests.cs` fixture: test-mode lock 3 s, a high per-source throttle (so the suite's own failed sign-ins never trip it), two reserved accounts; `WebDir()` made `internal` for reuse.
- `playwright.config.cjs`: overridable ports (`B1_SYN_PORT`, `B1_SAMPLE_PORT`) and, on the SYN server, the `locktest` account, a 4 s lock and a 5 s pause.
- `app-windows-poc.yml`: creates `mimamsa_b1_test_xfer`.

No existing assertion was changed. The existing dialog texts the journeys rely on are kept: "including earlier editions", "not legal approval", and the "Withdraw…" and "Withdraw" buttons.

## 3. Acceptance on the real sample (J13, J13b, J14 semantics)

`acceptance_s2.cjs` was run against a disposable sample instance in test mode (20 s lock). Results are in `s2_acceptance.json`, with screenshots `s2-*.jpg`.

13/13 checks pass:

| Check | Observed |
| --- | --- |
| J13-C+ (positive control) | `/api/cite` with the real hash before withdrawal: `CITED_COPY_ELIGIBLE` |
| J13-C- (negative control) | malformed hash: `CITED_COPY_UNAVAILABLE` even before withdrawal |
| J13-D | the dialog states what is covered; the "Open viewers are cut off" wording is gone |
| J13b-V | an open viewer is cleared with no reader action within **8.7 s** (10 s poll): page, header and evidence removed |
| J13-CITE | the same real hash after withdrawal: `CITED_COPY_UNAVAILABLE` |
| J13-API | document, text and pdf-meta: 404, 404, 404 |
| J13-S, J13b-DL | absent from search; the deep link shows the notice |
| J13b-ACT | after "go to page 3" the tab is cleared within **8.7 s**. This 5-page PDF was fully held by the viewer, so the action made no request and the poll cleared it. Actions that make a request clear at once (epoch header, or 404 on a range) |
| RI | reinstated: epoch 4, verification "active generation …, published, register clear, 1 copy re-hashed"; cite ELIGIBLE again |
| J14-EXP | 5 wrong → 401. Correct and wrong attempts at +3 s, +10 s and +17 s → 401. Correct at **+20.9 s → 200** (lock not extended) |
| J14-UNL | locked again, then Admin unlock with a reason → 200 → sign-in 200 |
| AUD | events: lockout, login, login_failed, login_refused_locked, reinstate, unlock, withdraw. No password text |

This instance ran with `Mimamsa:Login:ThrottlePerUsername=50`, so the per-username throttle (10 by default) would not mask the lock semantics during the 11 deliberate attempts. Throttling is tested separately in C#.

## 4. Security notes

- CSRF and Origin checks on every new POST. Admin role checked on the server for every admin route.
- `no-store` and content-free request logs are unchanged.
- The epoch header carries one integer and is sent only to the `/api` paths. Every `/api` route except login and health already requires a session.
- `/api/policy` does not refresh the session.
- Reinstatement cannot bypass the register or the vault re-hash.

## 5. Open issues

- **Environment (for the coordinator):** the shared private PostgreSQL has `max_connections = 50`. Several streams running e2e at once (pools up to 40 each) exhaust it, and requests then fail with HTTP 500. Lower the pool sizes in parallel runs, or raise `max_connections` (needs a PostgreSQL restart; not done here).

- Throttle windows are held in memory, per process. They reset on restart, which is acceptable for the single-instance B1. A multi-instance deployment would need them in PostgreSQL.
- Pages already rendered stay on screen for up to the 10 s poll interval when the reader does nothing. That is the documented bound; bytes already delivered cannot be recalled.
- The Withdrawals table shows the actor's user id, as before; the audit view resolves user ids to usernames.
- The audit view resolves user ids to usernames. Detail text is free text entered by Admins (reasons), and it is shown as plain text.
