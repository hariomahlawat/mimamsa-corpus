# AUTH-LEDGER file-type hardening (Cycle 11; confirmation review of 2ba7b0a4, findings CA-01 to CA-04)

**Required before any first real BIND.** The ledger stays at version 0 (HEAD `0 443c4bdf…6b6b`) and no entry is added.

| Finding | Change |
| --- | --- |
| CA-01: a FIFO at `ledger/HEAD` or `ledger/manifest.jsonl` blocked `verify`; a directory at `ledger/HEAD` gave an uncaught `IsADirectoryError` (rc 1) | Every ledger, decision and review file is read through `ledger.read_regular_bytes`: `O_NOFOLLOW` (a symlink at the final path component is refused), `O_NONBLOCK` (a FIFO cannot block the open), then `fstat` on the open descriptor (anything but a regular file is refused). Every `OSError` becomes a `LedgerError`, and `OSError` is in the CLI's fail-closed handler. Covers the manifest, `HEAD`, entry files, pinned records, record parsing and `frozen_inputs.json`. |
| CA-02: the contents of `ledger/` and `decisions/` were not walked strictly | `unexpected_files` walks with `followlinks=False` and `lstat`. It reports a symlink (to a file or a directory, including a dangling one), a non-regular file, a directory that holds no accounted file, and any unaccounted file. |
| CA-03: parts of the AL-01 fix had no test | Tests now cover a symlinked `decisions/`, `decisions` as a plain file, and the symlinked-base guard inside `unexpected_effective`. |
| CA-04: an absent `decisions/` passes at version 0 without being documented | **Documented here, and pinned by a test.** An absent `decisions/` is allowed while no version carries records. From version 1 on, every pinned record must exist as a regular file, so a missing record still fails. |

**Tests:** class `C11LedgerFileTypes` (15 new tests, plus the 8 inherited from `C10EffectiveIntegrity`). Every mutation is made in a temporary `Synthetic` copy, and a 20-second alarm turns any hang into a failure. Against the unfixed code, 11 of the new tests fail, including both FIFO hangs. The other 4 pin behaviour that already existed but had no test.

**Residual risks (stated, not fixed):**
- Between the hash check of an entry file and its CSV parse (`read_csv`), a concurrent writer could swap the file. An attacker able to do that already has write access to the repository.
- Hard links remain accepted, as documented in C10.
