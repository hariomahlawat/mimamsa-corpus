# Independent review: release importer (ASR-E05), citation navigation (ASR-E06), C1–C5 P3 fixes

- **Reviewed:** `bb22ebd3..a56e1e5f` on `claude/c13-b-app`. The two commits are `5f4b8071` (C1–C5) and `a56e1e5f` (E05/E06). The worktree is clean and the branch was not modified.
- **Oracle:** PR #54 `pr54` = `703d98cb`, which equals `refs/pull/54/head` on origin. `data_oracle.py` and `data-fixtures.json` were extracted unmodified (sha256 `6a32a60b…` and `f5bb693e…`) and run with `python -I -B`.
- **My probes:** run in scratch copies, not committed:
  - `reviews/b-app/imp/importer/tests/test_probe3.py` (importer);
  - `reviews/b-app/imp/contract/tests/test_probe2.py` (store, re-run).

## 1. Re-run (measured)

| Check | Result |
| --- | --- |
| Contract suite | **225 passed, 1 skipped** (the pre-existing governance skip) |
| Design suite | **116 passed** |
| Importer suite (`app/importer`, as in the app-ci.yml `importer` job) | **24 passed** |
| `data_oracle.py --repo /home/user/mimamsa-corpus` | exit 0, "Pinned R1 and producer probes matched the recorded expectations, including open gaps" |
| `da_cases.py --observations obs.json`, then `data_oracle.py --adapter-observations obs.json` | exit 1 with 63 lines, all `observed None (missing)`. No contradicted value. DA-01 and DA-35 have no lines; DA-03 lacks `allowed_truncation_warning_visible`; DA-04 lacks `ocr_warning_visible` and `page_image_match`. **This matches RESULTS_DA §2.** |
| C1–C5 re-probe on the new head | **All CLOSED.**<br>• C1: a lone payload after a crash between moves is quarantined and the pair restaged, then accepted.<br>• C2: a restriction kept as a tombstone now reports `RESTRICTED`, and a readmission without `restriction_id` does not lift RM-001.<br>• C3: a reused operation ID with different bytes is refused, and authority/reason patterns reject blanks.<br>• C4: deleting a history entry now halts ("pair within accepted range missing from the history").<br>• C5: LOCK recovery and use of `effective_state` are documented. |

**Confirmed sound in the importer:**
- SHA-256 is recomputed from the bundled bytes. Size, vault key and PDF page count (pypdfium2) are checked on the real bytes.
- A missing or mismatched original refuses the generation before any vault or generation write, and the previous ACTIVE and vault are unchanged (tests plus my reading of `importer.py:150-178`).
- A derivative declared against another document's copy, a text-hash mismatch, a char_count mismatch, an out-of-page passage end and a passage-hash mismatch are each quarantined.
- A passage on a page the derivative does not declare is refused at contract level (`PASSAGE_PAGE_UNKNOWN`; probe P1).
- A cross-bound sibling-copy anchor at page 99 is quarantined.
- **RM-001** is refused by contract validation before any write. This covers the doc_id (test with the real register); any record mentioning the sha or doc_id (`deep_match` substring scan); and bundled files whose digest is in `source_sha256` or `derived_sha256` (`bundle.py:260`).

## 2. Findings

| ID | Sev | Finding | Evidence | Required fix |
| --- | --- | --- | --- | --- |
| **E1** | P2 | **A bound span with character offsets but no `passage_id` is never range-checked.** An anchor with offsets 10000–20000 on a 53-character page activates and the candidate is servable. Offsets are checked only when a passage is found, and `char_end`-only spans are also unchecked. This is the DA-04/DA-35 range criterion. | `importer.py:236-247`; probe `test_P2_bound_span_offsets_no_passage_id`: `True cand servable True` | When there is no `passage_id`, check `0 <= char_start <= char_end <= len(page_text)` against the verified derivative page. Handle a single missing bound. Quarantine on failure and add tests. |
| **E2** | P2 | **The anchor `text_sha256` is neither compared with the passage hash nor recomputed**, yet it is copied into `candidate_evidence`. Observation `passage_hash_retained=True` merely checks that the declared value was copied. An anchor with `text_sha256 = "e"*64` is servable, and the bogus hash is stored as evidence. PR #54 DA-35 requires the "range, passage hash … concordant". | `importer.py:252-255`; `da_cases.py:158`; probe `test_P3_anchor_text_hash_not_verified` | Recompute the hash of the anchored range from the verified page text, or compare it with the verified passage hash; quarantine on mismatch. Until then, record DA-35 as Passed for 4 fields and Not implemented for passage-hash verification. |
| **E3** | P2 | **Page count is measured according to the *declared* MIME type.** A one-page PDF declared `text/plain`, with four `\f` bytes appended, is accepted with `page_count` 5 and activates. Anchors to pages 2–5 would then count as physical pages. Verification depends on declared metadata for the page dimension. | `importer.py:56-69,164`; probe `test_P6_mime_declared_text_plain_for_pdf`: `activated True` | Sniff the content type: `%PDF-` magic for PDF, strict UTF-8 decode and no PDF magic for `text/plain`. Refuse when the declared and detected types differ. Add a test. |
| **E4** | P2 | **Generation integrity.**<br>(a) The importer does not take the active generation's `release_sequence` as `current_release_sequence`; it relies on the caller. With `None` (allowed outside production) or a stale value, an older validly signed release re-activates: seq 1 after seq 2 activated (probe P4). Production refuses `None` (`bundle.py:157`) but still trusts the caller's number.<br>(b) Re-importing the same `release_id` rewrites the *active* generation's `generation.json` in place with a non-atomic `write_text` (probe P5). A crash there corrupts the serving generation.<br>(c) `generation.json` and `ACTIVE` are not fsynced, nor is the directory. "Switch atomically" holds for rename only. | `importer.py:117-122,274-282`; probes `test_P4_old_release_replay` (`replay older seq1 activated: True`) and `test_P5_…` (`rewritten: True`) | Read `ACTIVE`'s `release_sequence` and pass it, with the rollback path explicit. Refuse an existing generation directory. Build the generation in a temporary directory, then fsync and rename. Fsync ACTIVE. Add crash and replay tests. |
| **E5** | P2 | **`servable()` ignores the exclusion channel.** An item withdrawn by an accepted signed update, or tombstoned, is still reported servable if it is in the generation's list. The README says re-application is "not covered yet", but `servable()` is documented as the gate ("True only for items verified…"). | `importer.py:111-114`; `app/importer/README.md` "Not covered yet" | Make `servable()` apply `ExclusionStore.effective_state` (or take the state as an argument), or rename it `verified_in_generation` and document that it is not a serving decision. Add a test with a withdrawn document. |
| **E6** | P2 | **RESULTS_DA counts a non-observation as Passed.** DA-04 `ocr_quote_enabled=false` is computed from the *input fixture* (`far["quoting_permitted"]`), not from any importer or UI behaviour. Under PR #54 README §4, "Passed" needs an executed observation; static inspection must be kept separate. E1 and E2 also bear on the DA-04 and DA-35 statuses. | `da_cases.py:147`; `RESULTS_DA.md` DA-04 and DA-35 rows | Record `ocr_quote_enabled` as Not implemented (no quotation surface). Restate DA-04 and DA-35 after E1/E2, and recount. |
| **E7** | P2 | **The E06 notices disclose restricted and withdrawn status to Users.** "Not available in this library" (restricted), "does not hold" (not held) and "withdrawn … on {date}" are three distinguishable responses. This contradicts the non-disclosure row added this cycle: "hidden, not-found, restricted, withdrawn and staged items return one indistinguishable response". | `citation_resolution.json` states; `06_RESPONSIVE_AND_STATES.md` (citation bullets); `SECURITY_AND_DEPLOYMENT_ARCHITECTURE.md:143` | Use one notice for callers not authorised to see the item. If disclosing withdrawal is intended (for example, a public withdrawal record), record that as an explicit exception in §7.3 and merge restricted with not-held. Add a test asserting identical text for these states. |
| **E8** | P2 | **E06 conflicts with the E05 serving model.** UX-12 requires a cited copy to be honoured across N→N+1 when it has been replaced by a repaginated copy. However, `servable()` consults only the ACTIVE generation, and the importer keeps no eligibility for held-but-replaced copies. A copy cited in N and replaced in N+1 is therefore either reported NOT_HELD (wrong: it is held) or served while not servable. The policy has no state for "held, eligible, not in the active generation". | `importer.py:111-114`; `citation_resolution.json` (states); `CAPABILITY_TRACEABILITY_MATRIX.csv` CAP-RW-04 acceptance (UX-12) | Define the eligibility of superseded-but-held copies across generations (retained in the generation or in a held-copies index), add the policy state, and add a test of the N→N+1 replacement case. |
| **E9** | P3 | **The citation policy has no states for:**<br>• a cited page beyond the cited copy's page count;<br>• a `sha12` prefix matching more than one held copy;<br>• a permalink whose `doc_id` and `sha12` disagree.<br>Nothing prevents an implementer from clamping, opening page 1, or guessing. | `citation_resolution.json`; `02_INFORMATION_ARCHITECTURE.md` `/cite/` route | Add `CITED_PAGE_NOT_IN_COPY`, `AMBIGUOUS_REFERENCE` and `REFERENCE_MISMATCH` states, each with a notice and no content, and require a full-hash match. Add tests. |
| **E10** | P3 | **Unbound spans are described as "kept page-only"**, but their unverified `passage_id` and offsets stay in the servable candidate record (probe P8: bogus `p9-9` and 5000–6000 servable). | `importer.py:236` (`bound` branch only); probe `test_P8_…` | Strip the unverified span fields from what is served, or flag them; test it. |

**E06 document consistency:** `02_INFORMATION_ARCHITECTURE.md` and `06_RESPONSIVE_AND_STATES.md` now agree: exact cited copy and page, current edition only as a separate action, no automatic substitution. No remaining "resolves to the current copy" wording was found under `app/` or `docs/architecture/`. Within the defined states I found no path that substitutes the current copy. The open gaps are the undefined states (E8, E9).

## 3. Verdict

**ACCEPT WITH CONDITIONS.** P1: 0. P2: 8 (E1–E8). P3: 2 (E9–E10). C1–C5 are all closed.

The importer verifies real bytes for the original's identity and refuses before any write. However:
- span and hash verification of anchors is incomplete (E1, E2);
- the page count can be steered by the declared MIME type (E3);
- generation replay and in-place rewrite are possible (E4);
- `servable()` is not yet a serving decision (E5).

RESULTS_DA must be recounted (E6). The E06 policy needs the non-disclosure and cross-generation fixes (E7, E8) before B1 builds against it.
