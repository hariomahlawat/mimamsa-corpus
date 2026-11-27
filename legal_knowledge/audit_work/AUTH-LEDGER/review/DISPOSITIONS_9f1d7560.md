# Dispositions: Fable 5.2 (claude-fable-5-2) review of PR #44 at 9f1d7560

**Verdict: ACCEPT WITH CONDITIONS** (one P2). The fixes are in the next commit, which has not itself been reviewed yet.

| ID | Sev | Disposition |
| --- | --- | --- |
| C11-01 | P2 | **FIXED.** The safe reader moved to `common.py`. `reader.py` and `pins.py` read `frozen_inputs.json` through it, and so does `ledger.py` via `sha256_file`. Tests cover a FIFO and a symlink at `frozen_inputs.json`. On a disposable copy, the CLI with a FIFO at `frozen_inputs.json` exits rc 2 at once. |
| C11-02 | P3 | **FIXED.** `common.sha256_file`, `read_csv` and `load_json` are safe, so all 76 pinned inputs, the strength evidence JSON, the frozen-code exec read, the frozen registers, the effective outputs and the schema read at import are covered. The import-time schema read is a stated residual (traceback, not a hang). |
| C11-03 | P3 | **FIXED (tests).** New tests pin: `O_NOFOLLOW` directly (a symlink to a regular file is refused); a FIFO at the version-1 entry file and at the decision record; and the CLI `OSError` handler (a mocked `OSError` gives rc 2). |
| C11-04 | P3 | **FIXED.** Documentation wording corrected. The warning baseline is restated as 222 at `2ba7b0a4` and 248 at the head. |
| C11-05 | P3 | **FIXED.** Without `O_NOFOLLOW` or `O_NONBLOCK` the reader raises `LedgerError`. A test covers this. |
| INFO | — | Noted. The gate-log header named the base commit, and the reviewer reproduced its numbers on the head. |

**Tests:** ledger suite 272 OK (venv pytest, and Python 3.11 unittest). `verify` on the committed package gives version 0 with HEAD unchanged.
