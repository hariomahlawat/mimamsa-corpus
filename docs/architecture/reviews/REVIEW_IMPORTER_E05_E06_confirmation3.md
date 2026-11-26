# Independent review of the C13-B0 importer: third confirmation (copy)

> **Copy note (C13-A9).** Section 6 of the reviewer's file `scratchpad/c13/reviews/b-app/REVIEW_IMPORTER_E05_E06.md`, copied without changes. The committed `REVIEW_IMPORTER_E05_E06.md` ends at section 5; this file adds the third confirmation that closes N1 and N4 and files N5.

## 6. Third confirmation (`6927277d..fbf4dce7`, N4)

- **Reviewed:** head `fbf4dce7`. The worktree is clean and the branch was not modified.
- **Probes:** `reviews/b-app/imp4/importer/tests/test_probe6.py`, run in a scratch copy and not committed.
- **Suites:** contract **225 passed, 1 skipped**; design **117 passed**; importer **61 passed**.

| Probe | Result |
| --- | --- |
| Original N4 sequence (signed site, and also a site installed "none" that later accepted a withdrawal): reconfigure to "none", delete the store, import a new release | Downgrade refused ("latched … never be downgraded"). Next import refused with an integrity error. `servable(None)` returns False; `cite` returns UNAVAILABLE |
| Delete the store, the generations and ACTIVE together | The latch file remains. Downgrade refused, re-import refused, `servable` False |
| Edit the active generation's `exclusion_channel` to "none", then delete the store | `servable` False (latch present) |
| Re-install over the top (delete SITE_CONFIG; `configure_site` "none" / "signed") | "none" refused; "signed" accepted; `servable(None)` False |
| Remove `EXCLUSION_LATCH` (as after a crash between the ACCEPTED replace and the latch write), then delete the store, on a "none"-installed site | **`servable(None)` returns True for the withdrawn document** (see N5) |
| Full wipe of exclusions, generations, ACTIVE, latch and config, followed by a fresh "none" install | Serves. This is a new install, and offline detection is impossible without an external witness; it is accepted as X4 (witness custody), not a defect here |

**Status:**
- **N4: CLOSED.**
- **N1: CLOSED.**

**New finding:**

| ID | Sev | Finding | Evidence | Required fix |
| --- | --- | --- | --- | --- |
| N5 | P3 | **The latch is written *after* ACCEPTED is replaced.** A crash in that window, combined with later loss of the store, leaves a "none"-installed site un-latched, so withdrawn items serve with `exclusions=None`. The latch is also placed at `store.dir.parent`, so a store deployed outside the site root (for example `D:\Mimamsa\exclusions\` with a different site root) latches the wrong folder. | `exclusions.py` `_accept` → `_write_latch`; probe `test_V4_latch_lost_with_crash` | Write and fsync the latch *before* the ACCEPTED replace, and pass the site root explicitly instead of deriving it. Add a crash test at that point. |

**Verdict: ACCEPT.** P1: 0. P2: 0 open. N1–N4 and E1–E10 are closed. Track N5 (P3) into B1/P8.
