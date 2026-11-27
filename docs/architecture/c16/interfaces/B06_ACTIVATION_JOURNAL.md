# B06 activation journal interface

**Schemas:** `ACTIVATION_JOURNAL_RECORD_SCHEMA.json`, `ACTIVATION_SCENARIO_SCHEMA.json`, `ACTIVATION_SCENARIO_OUTCOMES_SCHEMA.json`.

**Reference:**
- `activation.py`: the state machine from contract 2.0, unchanged;
- `scenarios.py`: the harness for the protocol parts below.

**Fixtures:** `v2_1/activation_scenarios/`.

## 1. Journal records

The journal is `journal\journal.jsonl`, append-only:
- **Format.** One canonical JSON record per line, LF-terminated, flushed (`FlushFileBuffers` or fsync) **before** the next effect.
- **Steps.** These match `activation.py`: BEGIN (target, from, to, action), DECIDED (**the single commit decision**), OPEN (with the exclusion sequence applied), and ABORTED. The effects in between (views and publication rows, pointer files, exclusion application, activation log) are idempotent and are reconstructed by recovery. They are not journal steps.
- **Chain.** Each record carries `previous_record_sha256`, the sha256 of the previous line's bytes.
- **Writer.** Each record carries `writer {writer_id, lock_epoch}`. A record with a lower epoch than one already seen is refused: a stale writer cannot append after a takeover.
- **Torn tail.** An unterminated or unparseable **last** line is absent; the next writer truncates it during recovery.
- **Corruption.** Any other damage (a broken chain or an unparseable line in the middle) is corruption: recovery fails closed and nothing is served.

## 2. Single writer

The **activation tool** is the only journal writer. Exclusion acceptance takes the same lock.

**The lock** is an exclusive journal file lock plus a PostgreSQL advisory lock, with a lock record `{writer_id, pid, epoch, heartbeat}`:
- **Contention.** A live holder blocks other writers (`LOCK_CONTENDED`).
- **Takeover.** A dead holder, or one whose heartbeat is older than `lock_stale_after_seconds` (configurable), is taken over with epoch + 1.
- **After takeover.** The new writer must `recover()` before any transition. The old writer's transitions are refused (`NOT_LOCK_HOLDER`).

## 3. Local authenticated control channel (activation tool ↔ web service)

The channel is a named pipe `\\.\pipe\mimamsa-activation` (a Unix socket on Linux CI).

**Access:**
- The ACL allows only the activation tool's service identity (connect) and the web service identity (serve).
- Each side verifies the peer's process identity, using the client process id and its token SID.
- Messages carry the current `lock_epoch`, and a lower epoch is rejected.
- Nothing on the channel is reachable from the network.

| Message | From → to | Meaning |
| --- | --- | --- |
| `ENTER_SWITCHING {txn_id, lock_epoch}` | tool → web | stop admitting new requests (503), drain admission |
| `ACK_SWITCHING {txn_id, admitted_stopped, pinned}` | web → tool | required **before BEGIN**; no ack means the transition is refused and nothing is journaled |
| `OPEN {txn_id, knowledge, models, exclusion_seq}` | tool → web | load the journal head, swap services, release the old generation once its last pin is released |
| `ACK_OPEN {txn_id}` | web → tool | serving the new head |
| `PING / PONG {lock_epoch}` | both | liveness |

**Participant loss.**
- Lost **before BEGIN:** the transition is refused.
- Lost **after DECIDED:** the decision stands and the tool rolls forward. The web service, on restart or reconnect, refuses to serve until the journal shows no in-flight transaction and its loaded generation equals the journal head.

## 4. Reader pins and the response boundary

- **Pins.** Every request pins `{knowledge generation, model generation, exclusion sequence}` (`Site.pin`). A pin is refused while a transition or recovery is in progress, while the exclusion reader is unhealthy, or while the participant is not on the journal head.
- **Response boundary.** Every response is filtered by the **current** exclusion state (`Site.respond`). An exclusion accepted after the pin is never bypassed.

## 5. Exclusion reader (I-6)

This is a read-only .NET reader of the Python ExclusionStore's latest effective state:
- **Signature.** Verified against the trust list (purpose `register`).
- **Monotone sequence.** The reader remembers the highest sequence seen.
- **Fail closed.** No pins, no responses and no transitions when the store is missing, the signature is invalid, or the sequence regressed (a store older than what has been seen or applied).
- **Never restored.** It is not restored from backup (arch §10).

## 6. Shared conformance scenarios

**The scenario file** (`ACTIVATION_SCENARIO_SCHEMA`) holds:
- the initial site state;
- a list of steps `{op, args, expect_error}`;
- hand-written `assert_final` invariants.

**The expected-outcomes file** (`ACTIVATION_SCENARIO_OUTCOMES_SCHEMA`) is bound to the scenario by its canonical sha256. It holds the **observable trace** after every step:
- pointers, views, state and serving;
- journal steps, publication rows and log length;
- the applied and store exclusion sequences;
- the installed set and pin count;
- the temp-empty flag, exclusion-reader health and lock epoch;
- the last response.

**Both** `scenarios.run_scenario` and the .NET implementation must reproduce the trace exactly. The test asserts the trace, the `assert_final` invariants and the expected errors.

| Scenario | Covers |
| --- | --- |
| SC01–SC07 | a crash after each of BEGIN … OPEN; no serving until recovery; recovery is idempotent |
| SC08 | an exclusion arriving mid-switch, applied before exposure |
| SC09 | lock contention |
| SC10 | a stale process that dies; takeover, mandatory recovery, the dead writer refused |
| SC11 | a stale heartbeat takeover |
| SC12, SC13 | participant loss before BEGIN and after DECIDED |
| SC14, SC15 | a torn DECIDED (abort) and a torn OPEN (roll forward again) |
| SC16 | corruption fails closed |
| SC17 | a pinned reader and a new exclusion at the response boundary |
| SC18–SC20 | the exclusion reader: missing, regressed and bad signature, all failing closed |
| SC21, SC22 | a model-switch crash; a model without vectors refused |
| SC23 | rollback with distinct retention and a protected recovery target |
| SC24 | restore follows the journal head |
| SC25 | measured disk preflight refusal |

**What the model does not prove.** It proves the protocol. Real fsync, PostgreSQL transactions, process kills and concurrent requests remain FG-JOURNAL-DURABILITY for the .NET implementation (B06), which runs these same files.
