# AUTH-LEDGER design notes: discrepancies with the specification, and implementation decisions

The specification is `C6-01-PROVENANCE/addendum/INTEGRATION_ARCHITECTURE.md` revision 2, read in full from the merged staging commit `939a128a`. Each item below says where the implementation follows the specification, where it differs, and why.

## Decisions and discrepancies
| # | Topic | Specification | Implementation | Reason |
| --- | --- | --- | --- | --- |
| D-1 | Rule 1 crosswalk and master rows | "Rule version 1 is the Cycle 5 source-level anchoring rule exactly as frozen"; "the overlay only reads [frozen files]" | `reader.py` imports the **hash-pinned frozen** `SOURCE-LIBRARY-C5/tools/build_registers.py` **after** `pins.verify()` and calls its pure functions: `master_rows`, `check_holding_vs_copies`, `crosswalk` and the row builders for counts. It never calls the frozen `build()` or `copy_rows`, and never uses the frozen Cycle 4 module for status | Re-implementing the 120-line crosswalk risks silent divergence. Running the frozen, pinned code is the most exact form of "rule 1 exactly as frozen". The **copy-status rule is reimplemented** (`rules_v1.py`), as required, and proven equal to the frozen rule |
| D-2 | Coverage summary | v0000 byte identity for copy states, source states and crosswalk | Also byte identity for `coverage_summary.json` and `source_master_register.csv`. `reader.summary()` mirrors the frozen summary structure | Stronger check; the brief requires coverage equality too |
| D-3 | Source-state representation | Derived source states | `source_states.csv` (new) plus the frozen-format `source_master_register.csv`. The master is rebuilt by the frozen `master_rows` from the input rows with the **derived** holding state substituted. Nothing is edited on disk | No second hand-kept register; the frozen consistency check runs on the derived output |
| D-4 | Losing the only primary copy | Basis "from the copies' resulting states" | A source that is `HELD_PRIMARY_*` or `HELD_AUTHENTICATION_PENDING` at version 0, with no primary or pending copy left, falls to `HELD_OFFICIAL_COURT_COPY_PROVENANCE_UNDOCUMENTED` if its publication type is JUDICIAL, otherwise to `HELD_OFFICIAL_PUBLICATION_PROVENANCE_UNDOCUMENTED`. This happens **only** if an applied WITHDRAW or CORRECTION touched that source; otherwise it is a hard error | Resolves the Fable INFO note on the frozen basis; fails closed |
| D-5 | Multiple primary classes in one source | Not specified | If the frozen holding state already names one of the classes, it is kept. If there is one class, it is used. Mixed classes with no frozen match are a hard error | Unrecognised combinations fail closed |
| D-6 | Contradiction detection | "Normalised URLs (F-17)" | **Rule 1: exact string** (`strength.contradiction`); URL variants are not merged (tested). Normalisation is an open policy question (`POLICY_OPTIONS.md` C) | Avoids silently changing behaviour before an owner decision |
| D-7 | Decision authority | Committed, hash-pinned decision records | `ledger._check_record` requires a decision record **and** a reviewer record under `decisions/`, each hash-equal to the entry's declared hash **and** to the manifest line's pin. Each must name the exact `entry_id=sha256` pair and the ledger version, with decision APPROVED, verdict ACCEPT or ACCEPT_WITH_CONDITIONS, `decided_by`/`reviewer` and a date. A file that merely contains "APPROVED" is rejected (tested) | **No cryptographic signatures exist.** Authority is the reviewed merge of the PR that adds a version, and the expected HEAD is pinned in the test suite as well as in `ledger/HEAD` (two-place change) |
| D-8 | Rule version 2 | Copy-level anchoring is a future rule version | Not implemented. A manifest line with `rule_version` 2 is a hard error (tested) | It must be a separately reviewed transition |
| D-9 | Evidence inputs | Copy facts and structure copied into the overlay | Copied with provenance and pinned. Other evidence registers (PILOT-01, R23, ACQ, WS-A, WS-B, image-check registers) are read in place and pinned | No duplication of large registers; the pins make them frozen for the overlay |
| D-10 | Exact references | Resolve by exact key | Each evidence file has a **designated key column**, or `source_id` for retrieval JSON, or `identifier/filename` for archive snapshots. A reference must resolve to exactly one record. Any other file type is rejected | Closes the C6-01 looseness (any-column match) |
| D-11 | `effective/vNNNN` for v0000 | Derived outputs committed and pinned | Committed: about 380 KB, mostly byte copies of Cycle 5 registers | Auditable without running code; `verify` rebuilds and compares |

## Entry semantics implemented
- **ADD**
  - The sha256 has no live row. The copy and source are the Cycle 5 copy of that sha256, and the bytes are in the held index.
  - Every evidence reference resolves.
  - A FULL first-class record carries this sha256 and does not disclaim authenticity.
  - Identity evidence holds for this sha256.
  - The class is in the controlled vocabulary.
  - A primary court class needs a JUDICIAL source and a carrier that is not UNKNOWN. A primary non-judicial class needs copy fidelity: the signature range is not short and the file is not an archive derivative.
  - No exact-string URL contradiction.
- **CORRECTION**
  - It targets the live row for that sha256 (an entry id, or `BASELINE:<sha256>`).
  - A documented correction is re-verified like an ADD. A pending correction uses class AUTHENTICATION_PENDING and needs resolvable evidence references.
- **WITHDRAW**
  - It targets the live row and must give a reason.
  - With `resulting_state` AUTHENTICATION_PENDING, a pending row remains: it is live and can be corrected, but not withdrawn again. Otherwise the row ends and the copy falls back to the rule's no-row status.
  - The record is never deleted. `newly_withdrawn.csv` lists it.
- **Only APPROVED entries take effect.** WITHHELD and REJECTED entries are recorded in `transitions.csv` with no effect.

## Limitations
- No cryptographic signature verification of any document or decision; see D-7.
- Copy fidelity relies on structural facts captured locally in C6-01. A signature byte range that spans the file is **not** proof of a valid signature.
- Copy-structure facts exist only for the 36 C6-01 copies. A primary non-judicial class for any other copy fails closed until facts are captured.
- Legacy image-check rows carry no result field and are accepted as identity evidence, as in Cycle 4. See `POLICY_OPTIONS.md` B.
