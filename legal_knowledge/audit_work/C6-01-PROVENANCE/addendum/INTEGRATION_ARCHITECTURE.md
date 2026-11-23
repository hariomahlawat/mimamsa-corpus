# Source-authentication integration architecture, revision 2 (DESIGN; not implemented)

**Status:** design for owner and reviewer decision. Nothing outside this package changes in PR #33.

**Revision 2** adopts the overlay design (option C′) recommended by the independent Fable 5.2 review of a165b0f3 (F-06 to F-09) and replaces revision 1. This document is the **single specification**. `AUTHENTICATION_ADDENDUM_PLAN.md` describes process only, and the draft entries follow `addendum_entry.schema.json`.

**Goal:** let individually approved evidence change an *effective* authentication view without editing any historical register or tool, without two hand-synchronised registers, and without coverage targets driving status.

## 1. Fixed points (never edited)
- **Cycle 4, frozen:** `CALIBRATION-02/registers/source_authentication_register.csv` (sha256 `cfe5f408…`), `held_sources_scratchpad.csv` and `tools/evidence_classification.py`.
- **Cycle 5 snapshot, frozen:** all `SOURCE-LIBRARY-C5/` inputs, tools and registers, which are the merged snapshot.
- **CI pins.** A test pins the sha256 of every file above. The overlay only reads them.

## 2. Overlay package
A new package, for example `legal_knowledge/audit_work/AUTH-LEDGER/`. Its only code dependency is reading the frozen files.

| Part | Content |
| --- | --- |
| `schema/addendum_entry.schema.json` | entry contract (the C6-01 draft schema is its seed) |
| `ledger/v0001.csv`, `v0002.csv`, … | **immutable** addendum versions; a merged version is never edited |
| `ledger/manifest.jsonl` | one line per version: version, file sha256, previous line's sha256 (**hash chain**), rule version, decision-record sha256s |
| `decisions/<id>.md` | committed owner decision records and reviewer reports; each hash-pinned in the manifest line that uses it |
| `tools/strength.py` | locator-strength and identity computation, moved here from C6-01, so the validator never imports C6-01 or C5 builders |
| `tools/reader.py` | applies v0 (the baseline) plus approved entries to produce the effective view |
| `effective/vNNNN/` | derived outputs per version: copy states, source states, crosswalk, coverage, `transitions.csv` (audit trail) and `newly_withdrawn.csv` (change list); each folder hash-pinned in the manifest |

`effective/v0000/` is the frozen state. The test is that the reader with zero entries reproduces the Cycle 5 copy and source states and crosswalk **byte-for-byte**.

## 3. Entries
- **Key:** the full sha256. Entry types:
  - `ADD`: a new copy row;
  - `CORRECTION`: names the entry or baseline row it supersedes, with evidence;
  - `WITHDRAW`: names its target and gives a **mandatory reason** (`CONTRADICTION`, `EVIDENCE_REVOKED`, `CLASSIFICATION_ERROR`, `OTHER`) and an optional `resulting_state`, for example `AUTHENTICATION_PENDING`, so a withdrawal for cause keeps the adverse fact rather than falling back to "no row".
- **Effect.** Only `owner_decision=APPROVED` takes effect. That requires a `decision_record_ref` to a committed decision file whose sha256 is in the manifest, and a `reviewer_ref` to a committed review.
- **ADD evidence.** An `ADD` must name a `first_class_record_ref`: a committed record whose **own** sha256 equals the key. A mention of the sha256 inside another copy's record is a lead only. This closes the sibling-evidence route behind F-01 (Rajbir C2).
- **Resolvable references.** `evidence_refs` and `identity_refs` must resolve to an existing file and row.
- **Strength.** `strength.py` computes it from the referenced records and refuses anything below FULL. A record that disclaims authenticity, or reports NOT_FOUND or CONFLICTING, is not a locator (F-02).
- **Classification changes go through the ledger.** A carrier, class or fidelity change is a `CORRECTION` with evidence. Hand edits to frozen inputs are impossible because they are hash-pinned (F-08).

## 4. Effective-state derivation
1. Copy authentication is the baseline row, or the latest approved entry chain for that sha256. Orphan rules:
   - a `CORRECTION` whose target is withdrawn is void;
   - a `WITHDRAW` of a `WITHDRAW` is invalid; re-adding needs a new `ADD`;
   - two live entries for one key is an error.
2. Copy status uses a rule **versioned with the ledger** (`rule_version` in the manifest). It is the Cycle 4 rule plus a controlled non-primary vocabulary:
   - `NON_PRIMARY_*` maps to `DOCUMENTED_NON_PRIMARY`, which is never EFFECTIVE_PRIMARY;
   - unknown classes are errors.

   The frozen Cycle 4 tool is not edited. The overlay carries its own versioned copy of the rule, and a test proves its primary-class behaviour equals the frozen tool's on every baseline row.
3. Source state is an **explicit transition table** from the frozen v0 state, using copy statuses:

   | v0 state | condition | resulting state |
   | --- | --- | --- |
   | `HELD_OFFICIAL_PUBLICATION_PROVENANCE_UNDOCUMENTED` | ≥1 effective primary copy of class X | `HELD_PRIMARY_<X subtype>` |
   | `HELD_OFFICIAL_COURT_COPY_PROVENANCE_UNDOCUMENTED` | ≥1 effective primary court copy | `HELD_PRIMARY_OFFICIAL_COURT_COPY` |
   | any HELD state | a pending copy and no primary copy | `HELD_AUTHENTICATION_PENDING` |
   | any | otherwise | unchanged |

   No column of the frozen Cycle 5 input is split or edited. The Cycle 5 consistency rule is applied by the overlay to its own outputs, so it stays **on**.
4. **Copy-level anchoring (F-09).** EXACT_ANCHOR needs a citation's checked copy to be the effective primary copy. Otherwise a recorded page-equivalence check between the checked copy and that copy is required. A source never lends EXACT_ANCHOR from one copy to another. A non-primary copy never anchors.

## 5. Reproducibility, withdrawal and change lists
- `reader.py --as-of N` reads manifest lines 1..N and the rule version pinned there. Outputs are compared with `effective/vN/` hashes.
- **Round trip.** Approve-then-withdraw (reason `OTHER`, no resulting state) reproduces the previous version's state columns byte-for-byte. The audit columns live in `transitions.csv`, not in the state files.
- **Composition (F-09).** The PR that adds a version shows the **joint** effect of exactly the entries it approves, computed by the reader. Per-entry simulations in the C6-01 draft are informational only, because they do not compose (the Rajbir example).
- `newly_withdrawn.csv` feeds offline snapshot refreshes ("added / updated / newly withdrawn").

## 6. Validator (hard errors, all offline)
- a frozen-file hash mismatch;
- a broken manifest chain, or a modified earlier version;
- a schema violation;
- an unresolvable reference;
- an ADD without a first-class record;
- strength below FULL;
- APPROVED without a decision file and reviewer reference;
- duplicate live entries;
- a URL recorded with a different sha256 anywhere in the committed registers (normalised URLs; F-17);
- a primary class on a copy that fails the copy-fidelity rule (signature range not covering the file, or an archive derivative);
- any field that would express legal status, in-force status or applicability (the schema has none).

## 7. Dependency order (acyclic)
frozen files, then ledger plus decisions, then `strength.py` and the copy rule, then copy states, then source transitions, then crosswalk and coverage, then the effective folder.

C6-01 depends on nothing in the overlay. The overlay depends on nothing in C6-01 at run time: the C6-01 draft is converted to `v0001.csv` once, by a reviewed PR.

## 8. Sequencing
1. **PR 1:** overlay skeleton, schema, versioned rule with non-primary vocabulary, validator, frozen-file pins and `--as-of 0` byte-identity, with **zero entries**.
2. **PR 2..n:** tranches of approved entries, each with its own review and joint-effect diff.
   - The Gazette tranche has no crosswalk effect, so it can go first.
   - The SC tranche carries the case anchors.

## 9. Alternatives
| Option | Pros | Cons | Verdict |
| --- | --- | --- | --- |
| A. Edit the Cycle 4 register in place | simplest | destroys the baseline; no withdrawal history | rejected |
| B. Addendum plus a hand relabel of Cycle 5 `holding_state` | small | two hand-synchronised registers | rejected |
| C. Addendum plus a derived holding state inside C4/C5 (revision 1) | single derivation | edits frozen tools and inputs; a moving historical record (F-06) | superseded |
| **C′. Overlay package (this revision)** | frozen history; derived state; hash-chained ledger; offline | new package; the rule copy must be kept equivalent (tested) | **recommended** |
| D. Event-sourced ledger for all registers | general | beyond current need | deferred |

## 10. What must not happen
- No migration merely to raise exact-anchor counts.
- No legal-status, currency or applicability change. Authentication says where a copy came from and that it is what it claims to be.
- An EXACT_ANCHOR says a documented copy is held. It says nothing about later treatment. For example, Navjot Sandhu's s.65B statement was later overruled (Anvar, PILOT-01 S-JUD-006); that is for the adviser.
