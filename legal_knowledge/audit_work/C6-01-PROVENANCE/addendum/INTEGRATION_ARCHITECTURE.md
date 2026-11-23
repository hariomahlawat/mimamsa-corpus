# Source-authentication integration architecture (DESIGN; not implemented)

**Status:** design for owner and reviewer decision. No code, register or schema outside this package changes in PR #33.

**Goal:** let approved C6-01 evidence change the *effective* authentication view, without rewriting historical registers, without two hand-synchronised registers, and without letting coverage targets drive status.

## 1. Current mechanism (as merged)
| Layer | File | How it is produced |
| --- | --- | --- |
| Held bytes | `CALIBRATION-02/registers/held_sources_scratchpad.csv` | Cycle 4, committed |
| Copy authentication | `CALIBRATION-02/registers/source_authentication_register.csv` (13 rows, sha256 `cfe5f408…`) | Cycle 4, hand-authored and reviewed |
| Shared rule | `CALIBRATION-02/tools/evidence_classification.py` `Evidence.source_status(sha)` | Returns EFFECTIVE_PRIMARY_VERIFIED, AUTHENTICATION_PENDING, PROVENANCE_UNKNOWN, NOT_PRIMARY_MIRROR_OR_SECONDARY or DERIVED |
| Source holding state | `SOURCE-LIBRARY-C5/inputs/target_publications.csv` `holding_state` | **hand-authored**; `build_registers.check_holding_vs_copies` fails if it disagrees with copy-level evidence |
| Crosswalk and coverage | `SOURCE-LIBRARY-C5/registers/corpus_crosswalk.csv`, `coverage_summary.json` | derived by `build_registers.py` |

**The problem.** Adding authentication rows makes the hand-authored `holding_state` wrong, and the consistency check (correctly) stops the build. Fixing that by hand creates two manually synchronised registers. That is the failure mode to avoid.

## 2. Proposed design: one evidence-driven derivation
```
baseline register (Cycle 4, immutable, hash-pinned)
  + approved addendum entries v1..vn (append-only; each with decision ref)
  - entries withdrawn by a later version
  = effective copy-authentication view          (derived, never edited)
      -> copy effective status (shared rule, by full sha256)
      -> source authentication component (derived from its copies)
      + hand-authored holding basis (held / not held, carrier, completeness)
      = effective holding_state                 (derived)
      -> crosswalk + coverage                    (derived)
```

### 2.1 Reading the Cycle 4 register
- Read it byte-for-byte and verify its sha256 against a pinned value in an `authentication_baseline.json` manifest. A mismatch is a hard error.
- The baseline is never edited. A later correction to a baseline row is an addendum entry of type `CORRECTION` that names the baseline row.

### 2.2 Applying approved addenda
- Addenda live in `CALIBRATION-02/registers/addenda/source_authentication_addendum_vN.csv`. Each file is immutable once merged, and its sha256 is listed in an `addenda_manifest.json` with version, date and decision reference.
- Entry types: `ADD` (new copy row), `CORRECTION` (supersedes a baseline or earlier addendum entry for the same sha256), `WITHDRAW` (removes an earlier entry's effect). Every entry carries `entry_id`, the full `sha256`, `owner_decision` (`APPROVED` only takes effect), `decision_record_ref`, `reviewer_ref` and `evidence_refs`.
- Order of application: baseline, then versions in manifest order, then entries in file order.

### 2.3 Resolving copy states
- Key: the **full sha256** of the held bytes. A source's documented copy never authenticates another copy of the same source; each copy needs its own entry (C6-01 Rajbir: three copies, three entries, one non-primary).
- The shared rule is unchanged for primary classes. **Non-primary classes** are added as a controlled vocabulary (`NON_PRIMARY_OFFICIAL_PUBLICATION_COPY`, `NON_PRIMARY_OFFICIAL_COURT_RENDITION`, `NON_PRIMARY_PARLIAMENTARY_RECORD`) that maps to a **new** status `DOCUMENTED_NON_PRIMARY`. It is never EFFECTIVE_PRIMARY, so it can never produce an EXACT_ANCHOR. Unknown classes stay a hard error. This replaces today's accidental mapping of NON_PRIMARY_* to "register row incomplete" (C6-01 final review R-03).

### 2.4 Deriving source holding states
- Split today's hand-authored `holding_state` into:
  - `holding_basis` (hand-authored, evidence-referenced): held or not, carrier, completeness, compilation versus publication. These are facts about the holding, not about authentication.
  - the authentication component, **derived** from the copies: `HELD_PRIMARY_<subtype>` if at least one copy is EFFECTIVE_PRIMARY (subtype from that copy's class), `HELD_AUTHENTICATION_PENDING` if a pending copy and no primary copy, otherwise the basis' `*_PROVENANCE_UNDOCUMENTED` state.
- `check_holding_vs_copies` stays **on**. It then checks the hand-authored basis against the derived component (for example that a source marked NOT_HELD has no copies), instead of checking a value a human must keep in sync.
- About 29 Cycle 5 sources would change derived state if the 33 PROPOSED entries were approved (21 Gazette + 8 SC sources; the 4 non-primary entries change none).

### 2.5 Historical snapshots
- The merged Cycle 5 registers are a snapshot of the effective view at `addenda_manifest` version 0 (baseline only). The builder gains `--as-of <manifest version>`. `--as-of 0` must reproduce the merged Cycle 5 registers byte-for-byte; this is a CI test.
- New effective registers are written to a versioned output folder (`SOURCE-LIBRARY-C5/registers/effective/vN/`) or replace the current outputs with the previous version retained under `snapshots/`. Either way the Cycle 5 integration state stays reproducible from git alone.

### 2.6 Duplicate and contradiction detection (hard errors)
- Two effective entries for one sha256; an `ADD` for a sha256 already in the baseline (must be `CORRECTION`); an entry whose `held_paths` differ from the held index; a locator URL recorded with a different sha256 anywhere in the committed registers (the C6-01 contradiction rule); an entry below FULL locator strength; a primary class on a copy whose carrier is UNKNOWN.

### 2.7 Withdrawal and supersession
- `WITHDRAW` removes the target entry's effect; the effective view then falls back to the previous applicable entry or to "no row". `CORRECTION` replaces the target's fields. Neither deletes a row. Tests: approve, then withdraw, must reproduce the pre-approval effective view byte-for-byte.

### 2.8 Coverage regeneration
- The crosswalk and coverage counts are always derived by the builder; no count is hand-entered. The PR that applies an addendum must show the crosswalk diff and it must equal the per-entry simulation recorded in the addendum draft (`crosswalk_effect_this_entry_alone`).

### 2.9 Invalid transitions (validator rules)
- `owner_decision` other than APPROVED has no effect; an APPROVED entry without `decision_record_ref` and `reviewer_ref` is an error; WITHHELD entries cannot become APPROVED in place (a new entry in a later version is required); class changes on an existing sha256 require a `CORRECTION` with evidence references; no entry may touch legal status, in-force status or reserved items (the schema has no such fields).

### 2.10 Audit trail
- Every effective copy row carries `effective_from_entry` (baseline row or addendum entry id). The manifest records each version's hash, decision reference and review reference. `git log` plus the manifest reconstruct every state.

## 3. Alternatives considered
| Option | Pros | Cons | Verdict |
| --- | --- | --- | --- |
| A. Edit the Cycle 4 register in place | simplest | destroys the auditable baseline; no withdrawal history | rejected |
| B. Addendum + hand-relabel Cycle 5 `holding_state` (the earlier draft plan) | small change | two hand-synchronised registers; the check only detects drift after the fact | superseded by this design |
| C. **Addendum + derived holding state (this design)** | single derivation; historical `--as-of`; check stays on | builder and schema change; needs a migration review | **recommended** |
| D. Event-sourced ledger for all registers | most general | large change, beyond database scope needs now | deferred |

## 4. Circularity and offline testing
- Dependency order is strictly: held index and baseline, then addenda, then copy status, then source state, then crosswalk. No step reads a later step's output.
- Everything reads committed files; no network, no held binaries. Tests: baseline hash pin; `--as-of 0` byte-identity; approve/withdraw round trip; duplicate/contradiction errors; non-primary never EXACT_ANCHOR; WITHHELD never applied; per-entry crosswalk diff equals the recorded simulation.

## 5. What must not happen
- No migration merely to raise exact-anchor counts. Each entry is decided on its evidence.
- No legal-status, currency or applicability change: authentication says where a copy came from and that it is what it claims to be, nothing more.
