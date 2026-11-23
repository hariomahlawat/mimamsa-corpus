# AUTH-LEDGER design notes: discrepancies with the specification, and implementation decisions

The specification is `C6-01-PROVENANCE/addendum/INTEGRATION_ARCHITECTURE.md` revision 2, read in full from the merged staging commit `939a128a`. Each item below says where the implementation follows the specification, where it differs, and why.

## Decisions and discrepancies
| # | Topic | Specification | Implementation | Reason |
| --- | --- | --- | --- | --- |
| D-1 | Rule 1 crosswalk and master rows | "Rule version 1 is the Cycle 5 source-level anchoring rule exactly as frozen"; "the overlay only reads [frozen files]" | `reader.py` **executes the verified bytes** of the hash-pinned frozen `SOURCE-LIBRARY-C5/tools/build_registers.py` (and of the Cycle 4 module it imports), never via the import system, after `pins.verify()`, and calls its pure functions: `master_rows`, `check_holding_vs_copies`, `crosswalk` and the row builders for counts. It never calls the frozen `build()` or `copy_rows`, and never uses the frozen Cycle 4 module for status | Re-implementing the 120-line crosswalk risks silent divergence. Running the frozen, pinned code is the most exact form of "rule 1 exactly as frozen". The **copy-status rule is reimplemented** (`rules_v1.py`), as required, and proven equal to the frozen rule |
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
| D-12 | Locator validation (AUTH-LEDGER-02, Fable D-01) | First-class locators must be official, HTTPS, host suited to the class | `tools/urlcheck.py` parses with the standard RFC 3986 splitter. It cross-checks the authority with an independent grammar and **rejects** every ambiguous or second spelling (see its docstring); nothing is normalised. `strength.class_path_problem` adds per-class host and path rules: archive.org only as `/download/<item>/<file>` or `/details/<item>` | The AUTH-LEDGER-01 check caught only literal dot segments. Percent-encoded traversal, encoded separators, double encoding, malformed escapes, `;` parameters, explicit ports and case variants passed. All 74 committed locators and all 32 draft first-class locators still pass (tested). The change only rejects; it promotes nothing, and v0000 is unchanged |
| D-13 | Approval activation (AUTH-LEDGER-02) | Committed, hash-pinned decision records (D-7) | An approved version is staged until the next manifest line is a BIND line that `tools/binding.py` verifies offline against git history (`APPROVAL_CONTROLS.md`). A BIND line carries the extra key `binding`, so the genesis line's canonical form, and HEAD, are unchanged | Records alone cannot show that the reviewed bytes are the merged bytes, or that a version came through a reviewed merge |
| D-14 | Record content (AUTH-LEDGER-02) | Separate decision and review records | Records must state their scope and `legal_approval: NOT_GIVEN`. `decided_by` may not name an AI model or agent. Each pinned record must be cited, and may name only entries of its own version that cite it, once. The decision may not predate the review, and no record may postdate its manifest line | Closes orphan, duplicate and cross-version approvals and keeps the four roles apart |

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
  - The record is never deleted. `newly_withdrawn.json` lists it.
  - A WITHDRAW may target only an ADD or a BASELINE row. A CORRECTION is reverted by a new CORRECTION (Fable F-09).
- **Only APPROVED entries take effect.** WITHHELD and REJECTED entries need a decision record and are logged in `transitions.json` with no effect.
- **Class compatibility (`ledger.COMPAT`, Fable F-01/F-07):** each class has allowed publication types and copy-carrier prefixes. Primary classes also reject INCOMPLETE/EXTRACT completeness; the government-hosted scan class needs a scanned copy; and every first-class locator host must suit the class.
- **Records (Fable F-03/F-04):** decision `D-vNNNN*.md` and review `R-vNNNN*.md` are separate files by different persons. Each names `entry_id=sha256:entry_digest`, has no duplicate keys, has an id equal to its file name and a `YYYY-MM-DD` date. ACCEPT_WITH_CONDITIONS needs `conditions_status: DISCHARGED`.
- **Frozen code (Fable F-05):** it is executed from its verified bytes and never imported.

## Limitations
- No cryptographic signature verification of any document or decision; see D-7. Since AUTH-LEDGER-02, activation needs a git-verified BIND line (D-13); the approving GitHub review is recorded as an asserted fact, and an owner signature is open as owner decision O-1 (`APPROVAL_CONTROLS.md`).
- Copy fidelity relies on structural facts captured locally in C6-01. A signature byte range that spans the file is **not** proof of a valid signature.
- Copy-structure facts exist only for the 36 C6-01 copies. A primary non-judicial class for any other copy fails closed until facts are captured.
- Legacy image-check rows carry no result field and are accepted as identity evidence, as in Cycle 4. See `POLICY_OPTIONS.md` B.
- **Converting the C6-01 draft to a ledger version** (a future reviewed PR) must rewrite each text-identity reference from the C6-01 path to `T:AUTH-LEDGER/evidence/copy_facts.csv#<copy_id>`. It must also fill the decision-chain fields from committed D-/R- records. The literal draft rows are rejected by design (Fable confirmation C-02).
