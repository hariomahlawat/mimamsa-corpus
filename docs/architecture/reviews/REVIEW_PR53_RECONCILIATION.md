# Independent review: PR #53 reconciliation (C13 B0, branch `claude/c13-b-app`)

- **Reviewed:** `9eeb04a4..31a21df4` (one commit, `31a21df4`), worktree `scratchpad/c13/b-app`. The branch was not modified.
- **Compared against:** PR #53 head `6a0ae735e4ea0b5e616a25db3019bd212d6604b1`. All 11 documents under `docs/architecture/intelligence/` were read in full.
- **Reviewer:** independent of the author. Date 2026-11-25.

## 1. What was re-run (measured)

| Check | Command | Result |
| --- | --- | --- |
| Contract tests | `cd app/contract && venv/python -m pytest -q -p no:cacheprovider tests`, as in app-ci.yml | **202 passed, 1 skipped**. Matches the claim. The skip is `test_restricted_material.py:159` (`scripts/restricted_material.py` not on the branch); it existed before this change. |
| Design tests | `cd app/design && venv/python -m pytest -q -p no:cacheprovider tests` | **111 passed**. Matches the claim. |
| CLI example validation | app-ci.yml step, with `--register` set to the `claude/c13-gov` register | All 4 examples are VALID. Without a register the CLI fails closed with `RESTRICTED_CONFIG_MISSING`, which is correct. |
| New-test count | diff inspection | 21 new contract tests (15 + 6) and 2 new design tests. Matches the claim. |
| A5 crosswalk facts (§4) | read at `f915ac11` | `edges_reviewed.jsonl` has 173 rows. Review keys are `{candidate_id, category, review, truth_family, verdict}`; 0 rows carry reviewer and commit binding. `edge_type` has 28 values and `restrictions` is an array of 4 enum values. Confirmed. |
| Crash-recovery probes (my own; run in a scratch copy of `app/contract`, not committed) | `reviews/b-app/probe/test_probe.py` | (a) After a crash once the pair is written but before ACCEPTED, `append` of the same update fails with `ExclusionError: already stored`. (b) A leftover `staging/<seq>` directory makes `append` raise a raw `FileExistsError`. (c) `doc_id: ""` and `source_copy_sha256: ""` are both rejected. |

**Confirmed sound:**
- **Null-only fix.** The schema `anyOf` branches now require a `string` type, and the base property `$ref` patterns still apply. The Python check repeats the rule as defence in depth.
- **RM-001.** `restricted.py` is untouched and the restricted-material tests pass against the governance register. The reserved-kind early return emits an error, so it cannot let a record slip past the restricted check.
- **No agentic activation.** Reserved namespaces and record kinds only reject; no agent, model, broker or engine code was added.
- **No scope expansion.** No new capability IDs, gates or enums used by producers.
- **Nothing presented as measured that was not.** All PR #53 numeric limits are labelled proposed, and R2-N01 is consistently routed to the PoC agent.

## 2. Findings

| ID | Sev | Finding | Evidence | Required fix |
| --- | --- | --- | --- | --- |
| **F01** | P2 | **Several COMPATIBLE_ALREADY rows are really partial or deferred**, so the 24/11/12/5 split overstates readiness. These rows say "comes later" or "comes in B2" in their own reason column:<br>• R21 (re-admission records come in B2);<br>• R22: the dependency index covers only source→candidates/edges/templates. It does not cover caches, saved results, exports or the query/count/coverage dependencies that Serving §7 requires;<br>• R34: only `model_id/sha256/licence` are pinned. There is no signed manifest, trust purpose, staged loader or monotone revocation state (RT §7);<br>• R42: there is no append-only impact record or scope-overlap check (ENG §9);<br>• R45: there is no coverage record or independent contrary-search budget (RG §7);<br>• R35, R37 and R46 (mixed-load admission, model caches, alias/OCR-variant identifiers) are only in part present. | `INTELLIGENCE_ARCHITECTURE_RECONCILIATION_C13.md:52,53,65,66,68,74,76,77`; `SECURITY_AND_DEPLOYMENT_ARCHITECTURE.md:196-198`; `release_manifest.schema.json:70-85` | Reclassify these rows as DEFER, or add a fifth class "PARTIAL (hook present, remainder deferred)", and recompute §1. In each row, name the milestone that owns the remainder. |
| **F02** | P2 | **R21 hides a behavioural conflict and an unrecorded redevelopment risk.** Two problems:<br>1. `items_to_suppress` uses only the *latest* signed withdrawal list. A row dropped from a later complete list stops being suppressed at the next re-application (activation, rollback or restore). That is re-admission by omission, which Serving §7 forbids.<br>2. Local Admin withdrawals are a DB corpus mutation, and the DB can be rolled back. They are not in the monotone store outside rollback that Serving §4 (last sentence) and §7 require. T-VIS-03's "restore a backup taken before the change → item absent" therefore holds only for the signed channel.<br>Neither problem is in §3 (X1–X6). | `exclusions.py:58-59,63-74`; `SECURITY_AND_DEPLOYMENT_ARCHITECTURE.md:146,223,267`; reconciliation `:52` | Record this as conflict **X7**: denial history and local-withdrawal durability. State the redevelopment risk, because B2 publication/withdrawal storage would have to move out of the rollbackable DB. Assign an owner decision. Narrow T-VIS-03 and the contract README claim to the signed channel until it is resolved. |
| **F03** | P2 | **R18 "reference protocol implemented" overclaims.** It does not implement these Serving §4/§8 cases:<br>• "New verified pair durable, not yet accepted → revalidate and complete acceptance or discard". Retrying the same update raises `already stored`, so that signed withdrawal can never be accepted (probe a).<br>• "Staged incomplete pair → quarantine". The leftover staging directory raises an untyped `FileExistsError` (probe b).<br>• §8 P3 "lost ack → idempotent retry returns the original outcome". The retry fails with "sequence must increase".<br>Also, the acceptance-time CAS (read, then `os.replace`) is not atomic. That is acceptable only under the stated single-writer assumption, which nothing enforces. The ACCEPTED record has no signature reference and no epoch (§4 lists both). The CAS test exercises only the early `expected_sequence` pre-check. | `exclusions.py:111-138` (`:123` already-stored, `:125` `mkdir(exist_ok=False)`, `:135-137` CAS); `tests/test_trust_and_exclusions.py` (`test_compare_and_set_rejects_stale_writer`) | Either:<br>(a) add `complete_pending(seq)` and quarantine of staging residue; make a retry with an identical digest return the accepted state; wrap `OSError` in `ExclusionError`; add a single-writer lock (for example an exclusive lock file); and add tests for each restart row; or<br>(b) reclassify R18 as PARTIAL and list these cases as P8/B2 work. |
| **F04** | P2 | **PR #53 requirements missing from the 52-row table**, which is presented as complete:<br>• RT §2: authenticated local service-to-service calls ("loopback is not authentication"); the inference worker has no DB, vault or network access;<br>• RT §4 and TC §5: content-free logs; session deletion removes derivatives, vectors, caches and exports;<br>• RT §5: kill switch for generative features;<br>• RG §2 and RT §7: index generation records the embedding model and dimension; no mixed vector spaces; model and index switch atomically;<br>• RG §3: exact identifier matches cannot be displaced by reranking; rank-based fusion;<br>• AG §7: server-owned workspace state; typed progress events with a monotone sequence; reconnect via a fresh snapshot;<br>• Serving §8 P3: operation ID and idempotent acknowledgement;<br>• Serving §4: local Admin withdrawal history (see F02);<br>• EV §3/§6/§8: mapping of INT-01..INT-20 into B1/B2/P8 acceptance (only REV and CLAIM are mapped, R29 and R38). | PR #53 `LOCAL_AI_SECURITY_AND_RUNTIME.md` §2, §4, §5, §7; `RETRIEVAL_AND_GRAPHRAG.md` §2–3; `AGENTIC_AI_ARCHITECTURE.md` §7; `SERVING_AND_REVOCATION_CONTRACT.md` §4, §8; `EVALUATION_AND_ROADMAP.md` §3, §6, §8; reconciliation `:30-83` | Add rows R53 onward with a classification. Most are DEFER or COMPATIBLE with a named owner. RT §2 and RG §3 bear on B1 worker and search design now, so record them as B1 design inputs. Update the totals. |
| **F05** | P3 | **§4 states stale producer heads.** It says the A4/A5 branch heads "are identical to the commits PR #53 pinned". At the B0 commit (14:53) the heads were already A4 `c7a93ab6` (14:47) and A5 `e92557de` (14:47). The A4 change is to tests and README only, and the A5 change adds reviews, so producer schemas and data are unchanged. However, the A5 independent review at `e92557de` (F01–F04 P2) was not considered. | reconciliation `:101`; `git log 01132c34..c7a93ab6`, `git log f915ac11..e92557de` | Correct the heads. Note that the schemas and data are unchanged, and check whether the A5 review findings affect the crosswalk rows. |
| **F06** | P3 | `resolve_span` ignores character offsets when `passage_id` is null: it returns the first passage on the page whatever the offsets are, and does no bounds check (Crosswalk §1 "validate bounds/hash"). | `evidence.py:40-50`, esp. `:48` | Match only a passage whose `[char_start, char_end)` contains the anchor range, otherwise return `None`. Add a test. |
| **F07** | P3 | **ADR §4a over-labels the adapter boundaries.**<br>• AD-5 ("assertion only") and AD-10 ("none (outside the core)") have no core-facing interface, so calling them adapter boundaries runs against owner directive 5.<br>• AD-9 names Tesseract, ONNX Runtime and llama.cpp as the Windows adapter, although no runtime has been selected (Tesseract is not even available on the host).<br>No code abstraction was added, so this is wording only. | `ADR-0005-APPLICATION-STACK.md:105,109,110` | Relabel AD-5 and AD-10 as deployment controls, not interfaces. Word AD-9 as "candidates, selected by PoC". |
| **F08** | P3 | **Internal inconsistencies.**<br>• ADR maps PUBLISHED_RESEARCH to "layer 7"; the security doc maps it to "layers 1–8, published view".<br>• Security §7.4 is placed before §7.3.<br>• The policy note "originals stream after hash check" contradicts `disableStream: true` and the bounded-range transport. | `ADR-0005…:121` vs `SECURITY…:60`; `SECURITY…:132,141`; `client_state_and_cache.json:9` | Align the layer mapping, reorder the sections, and update the note. |
| **F09** | P3 | **R2 cannot be detected by machine.** The schemas changed (new anchor fields, stricter withdrawal rows) but `CONTRACT_VERSION` stays `1.0.0`, with no revision marker. PR #53 is asked to re-pin, yet producers and consumers cannot tell R1 from R2. | `mimamsa_contract/__init__.py:8`; `app/contract/README.md` R2 line | Add `CONTRACT_REVISION = "R2"`, or a schema `$comment`/`$id` suffix, and a test. Alternatively, state explicitly that revision is pinned by commit only. |
| **F10** | P3 | **Class counts are confusing.** §1 shows 5 conflicts but describes six risks, with X5 counted under DEFER. | reconciliation `:21,85` | Show "5 classified + 1 DEFER-with-risk (X5) = 6 risks" in the §1 table itself; add X7 per F02. |

## 3. Questions answered

- **Is each classification honest?** Mostly, but not fully: see F01, F02 and F03. The INCORPORATE rows R06, R09, R12, R15, R16 and R17 are genuinely done at the level claimed (contract, policy or document) and are tested where testable. R14, R23, R24 and R30 are documentation-only incorporations and are correctly labelled as such.
- **Were deferrals or conflicts used to hide redevelopment risk?** One material case: F02 (denial history and local-withdrawal durability) sits under COMPATIBLE. Otherwise X1–X6 are candid; X1 and X3 in particular are recorded with the correct owner and gate.
- **Are the contract changes correct, minimal and tested?** The null-only fix is correct and tested. The span binding and reserved namespaces are minimal and additive. The ExclusionStore rewrite is larger than the rest and has the gaps in F03. `common.schema.json` and `client_state_and_cache.json` were reformatted wholesale, which inflates the diff without semantic change (no finding, but avoid this in future).
- **Do the ADR-0005 edits over-abstract or expand scope?** No code abstraction was added. There is some over-labelling in §4a (F07). K10 is a reasonable criterion, consistent with PR #53 T0/T1, and does not pre-decide the framework.
- **Any agentic AI activation?** None.
- **Does RM-001 still hold?** Yes.
- **Is anything unsupported claimed as measured?** No. Test counts reproduce exactly. The §4 branch-head statement is a stale fact, not a measurement (F05).

## 4. Verdict

**ACCEPT WITH CONDITIONS.** P1: 0. P2: 4 (F01–F04). P3: 6 (F05–F10).

Conditions before PR #53 re-pins to this revision:
1. Fix F01: reclassify and recount.
2. Fix F02: record X7 and narrow the T-VIS-03 claim.
3. Fix F03: implement the restart and lost-ack cases with tests, or reclassify R18 as PARTIAL.
4. Fix F04: add the missing rows.

The P3 findings can be fixed in the same pass or tracked.

---

## 5. Confirmation review of the fixes (`31a21df4..bb22ebd3`)

- **Reviewed:** head `bb22ebd3`, a single commit. The worktree is clean and the branch was not modified.
- **Method:** I re-ran all tests and my original probes. I also wrote new adversarial probes, run in a scratch copy at `reviews/b-app/cc2/tests/test_probe2.py`, not committed.

### 5.1 Re-run (measured)

| Check | Result |
| --- | --- |
| Contract tests (app-ci.yml command) | **214 passed, 1 skipped.** This matches the author. The skip is the same pre-existing one. |
| Design tests | **111 passed.** |
| Original probe (a): pair stored, no ACCEPTED, re-append | Now accepted (epoch 2); `pending()` is empty. **Fixed.** |
| Original probe (b): staging residue | Residue moved to `quarantine/00000003-<ns>`, then the update is accepted. **Fixed.** |
| Replay of an old signed list (seq 2 after seq 3) | Rejected with "sequence must increase". The seq-2 withdrawal stays suppressed. **Holds.** |
| Omission from a later list | Item still WITHDRAWN. **Holds.** |
| RM-001 dropped from a later register (replaced by a dummy item) | RM-001 doc_id and sha remain tombstoned and suppressed. **Holds.** It is labelled `WITHDRAWN`, not `RESTRICTED` (see C2). |
| Readmission without `authority_ref` | Rejected by the schema (author test; confirmed). |
| Concurrent writer / stale LOCK | A second writer gets a typed `ExclusionError`. A stale LOCK fails closed, with no recovery tool (C5). |

### 5.2 Original findings

| ID | Status | Basis |
| --- | --- | --- |
| F01 | **CLOSED** | PARTIAL class added. R21, R22, R34, R35, R37, R42, R45 and R46 reclassified, each naming its owning milestone. Counts add up: 16 + 11 + 13 + 15 + 6 = 61. |
| F02 | **CLOSED** | The signed channel now uses monotone tombstones (`effective_state`, used by `state_for_restore`) with explicit signed `readmissions`. The local Admin channel is recorded honestly as X7 / R60 (CONFLICT), with a proposed B2 fix and an owner decision. T-VIS-03, the security architecture §8.4 and the README are narrowed to the signed channel. |
| F03 | **CLOSED** | Probes (a) and (b) pass. Also added: lost-ack idempotency, refusal of different bytes, LOCK, typed I/O errors, and an ACCEPTED record carrying signature digest, epoch and history. Residual narrow gaps are C1, C3 and C4 (P3). |
| F04 | **CLOSED** | R53–R61 added and classified honestly. R53 and R57 are flagged as B1 design inputs. R57 is a spec-only incorporation, labelled as such. R61 defers the INT mapping with a named owner. |
| F05 | **CLOSED** | Heads corrected (A4 `c7a93ab6`, A5 `e92557de`). A5 review F04 considered; 2 crosswalk rows added. |
| F06 | **CLOSED** | `resolve_span` now checks offsets against passage bounds; test added. |
| F07 | **CLOSED** | AD-5 and AD-10 are now DC-1 and DC-2, deployment controls with no core interface. AD-9 is worded as PoC candidates. |
| F08 | **CLOSED** | Layer mapping aligned; §7.4 placed after §7.3; policy note corrected. |
| F09 | **CLOSED** | `CONTRACT_REVISION = "R2"` added, with a test. |
| F10 | **CLOSED** | §1 shows the 6 classified conflicts and 7 risks separately. |

### 5.3 New findings from the confirmation (all P3; none blocks)

| ID | Sev | Finding | Evidence | Required fix |
| --- | --- | --- | --- | --- |
| C1 | P3 | **A crash between the two pair moves wedges that sequence.** If `.json` is in `pairs/` and `.sig` is still in `staging/`, `append` raises "different bytes already stored" and `complete_pending` raises "incomplete". This fails closed and a later sequence can still be accepted, but that signed update can never be accepted without manual repair. | `exclusions.py`, `append` (pair-exists branch) and `complete_pending`; probe `test_crash_between_two_moves` | When `pairs/` holds a lone `.json` identical to the incoming bytes, quarantine it and restage. Add a test. |
| C2 | P3 | **A restriction that persists only as a tombstone is labelled `WITHDRAWN`, not `RESTRICTED`.** This happens when a register entry (for example RM-001) is dropped from the latest register. The security architecture §8.4 treats `EXCLUDED_RESTRICTED` differently: no copy, and bytes purged. `readmissions` can also lift a register entry with any 3-character `authority_ref`, with nothing to distinguish it from correcting a withdrawal. Both rows are owner-signed, so this is not a weakening relative to R1, but it is coarse. | `exclusions.py` `effective_state` and `items_to_suppress`; probe `test_rm001_omitted_from_later_register` | Keep separate tombstone sets for restricted and withdrawn identities, so suppression reports `RESTRICTED`. For lifting a restriction, require `restriction_id` plus a non-blank owner decision reference, for example a pattern with no whitespace-only values. |
| C3 | P3 | **`readmissions` accepts a whitespace-only `reason` and `authority_ref`**, and an `operation_id` already used for an accepted update can be reused for different bytes. Serving §8 P3 says "different bytes under same ID reject". R59's claim covers only same bytes under a different ID. | `exclusion_update.schema.json` `readmissions` (`minLength: 3` only); `exclusions.py` `append`; probe `test_readmit_whitespace_authority_and_opid_reuse` | Add a `pattern` requiring non-whitespace content. Reject an `operation_id` already present in the accepted history with a different digest (store the op id per history entry). |
| C4 | P3 | **ACCEPTED `history` is not integrity-checked.** Deleting a history entry silently drops its tombstones: the probe shows the item un-suppressed. Writing to the store already permits other tampering (custody is X4), but a cheap consistency check would turn silent loss into a halt. | `exclusions.py` `effective_state`; probe `test_history_tamper` | Halt if the history sequence is not strictly increasing, if its last entry differs from (`sequence`, `digest`), or if any accepted-range pair file on disk is missing from the history. Record a chained digest. |
| C5 | P3 | **Operational gaps.**<br>• A stale LOCK after a crash blocks all acceptance, and there is no documented recovery.<br>• `append` now returns an ack, and `accept_exclusion_update` returns a state without tombstones. The "on acceptance" re-application path in the security architecture §8.4 must call `effective_state`, but nothing says so. | `exclusions.py` `_lock`, `append`; `SECURITY…` §8.4 re-application rule | Document LOCK recovery: an Admin action with an audit record. State in §8.4 and the README that re-application always uses `effective_state`. |

### 5.4 Abstraction, scope and agentic AI

- **Abstraction and scope.** The only new contract surface is the optional, owner-signed `readmissions` array and `CONTRACT_REVISION`. Both are justified by F02/F09 and are additive. No new capability IDs, gates, services or interfaces were added; F07 *reduced* the interface list.
- **Agentic AI.** None activated.
- **RM-001.** Still excluded. The tombstones strengthen it against omission from a later register.

### 5.5 Final verdict

**ACCEPT.** P1: 0. P2: 0 open. The 10 original findings are closed. The 5 new P3 findings (C1–C5) should be tracked into B1/B2 and P8. None blocks PR #53 re-pinning to `bb22ebd3` / contract R2.
