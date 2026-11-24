# Dispositions: Fable 5.2 (claude-fable-5-2) confirmation review of PR #44 at bdc23f11

**Verdict: ACCEPT.** The C11-01 P2 is closed and no regression was found. The PR #44 head stays exactly as reviewed, so these dispositions are recorded here.

| ID | Sev | Disposition |
| --- | --- | --- |
| CB-01 | P3 | **Carried to a follow-up change (tests only).** The two version-1 tests use a FIFO, which `is_file()` rejects before the safe read is reached, so they do not pin that read. Still to add: a symlink at the version-1 entry file and at the D-/R- records, the symlinked-directory branch of the walk, the `O_NONBLOCK` half of the fail-closed check, and a special file at the schema. The reviewer found the behaviour correct on all of these by probe. |
| CB-02 | P3 | **Recorded here; the document is corrected in the follow-up.** `ledger.py` reads `frozen_inputs.json` through `sha256_regular`, not `sha256_file`; both are safe. The sentence about the "11 failing tests" belongs in the first test bullet. |
| CB-04 | INFO | **Intended behaviour change.** Pinned inputs, frozen code files and the schema must now be regular files; a symlink fails even when its hash matches. This is noted for owners who keep symlinked checkouts. |
| CB-05 | INFO | **Stated residual.** The schema read at import gives rc 1 with a traceback, not rc 2. It does not hang. |

**Integration:** a scratch merge with the #45 candidate passes `verify`. TXN-DEMO needs one regeneration on the same 22 keys, with behaviour unchanged (19 PASS).
