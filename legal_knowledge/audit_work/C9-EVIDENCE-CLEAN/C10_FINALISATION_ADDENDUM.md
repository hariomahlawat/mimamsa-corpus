# Cycle 10 finalisation addendum: PR #36 against PR #40, and the privacy items under the owner's judicial publication policy

**Status:** analysis only. Neither PR is merged. Merging needs separate owner approval. This addendum supersedes the privacy framing of `TRANSFER_RECORD.md` sections 4 and 7 where they conflict; the record itself is not edited.

## 1. Owner policy (assignment of 24 November 2026)
The owner directed the following:
- Information in a lawfully published court judgment need not be masked merely because it is personal.
- Authentic judicial documents and accurate quotations are preserved.
- Git history is not rewritten solely because it reproduces published judgment text.
- Court-ordered restrictions remain binding.

No court-ordered restriction, sealing or confidentiality order has been identified for any of the eight Supreme Court judgments or the Mullikote and N S Yadav judgments.

## 2. PRIV-01 and PRIV-02 re-disposition
| Item | Cycle 9 position | Cycle 10 disposition under the policy |
| --- | --- | --- |
| PRIV-01: Mullikote officer service numbers (36 tokens in 12 C8 files; 36 in 11 earlier files) | owner decision: mask or accept | **Accept; no masking.** They are printed in a published Supreme Court judgment. The C9 SC-C9 package masked them in its own derived analysis files; that is harmless and does not alter any source. It need not be repeated, and the masking may be reversed in a later reviewed change if exact quotation is needed |
| PRIV-02: diagnosis term and N S Yadav service number in 4 and 3 earlier files, including the protected `records_658.jsonl` | owner decision: accept, mask derived files, or purge history | **Accept; no masking, no history rewrite.** Published judgment text, faithfully reproduced. The protected original stays untouched |
| B-03 page-text dumps in commit `5212a95b` (old branch) | removed from the tree; history retirement proposed | **Not a defect under the policy.** The dumps reproduced published judgment text. Retiring them, or asking GitHub to purge them, is **no longer needed on privacy grounds**. They remain unsuitable as evidence files because they are bulk page-text dumps with no evidentiary function; that is why they were replaced by hash-only render facts |
| Duplication in unrelated logs | — | Avoid copying personal details into test logs where they serve no evidentiary purpose (policy). The C9 and C10 tools print counts and hashes only |

## 3. PR #36 against PR #40
| Criterion | PR #36 (`claude/c8-evidence-verification` @ `152045bd`) | PR #40 (`claude/c9-evidence-clean` @ `9a6f9366`) |
| --- | --- | --- |
| Base | staging `1a21a2e8`, three merges behind | current staging `21e73b83` |
| Merge into current staging | clean (test merge) | clean (test merge) |
| `C8-EVIDENCE/` tree after merge | `d82436fe` | `d82436fe`: **identical** |
| Further content | none | `C9-EVIDENCE-CLEAN/`: transfer record, check tools, the **SC-C9 Supreme Court package** (human page-verification pack, JUDIS policy, anchor simulations), review records |
| Reviews | evidence tree accepted at `152045bd` | same tree, independently confirmed identical; transfer **ACCEPT WITH CONDITIONS** (applied in `37fe6a0f`, not re-reviewed); SC-C9 **ACCEPT**; LG-12 addendum not re-reviewed |
| History | keeps the review trail (`5212a95b` → `801d2c41` → `152045bd`), including the B-03 dumps (published judgment text) | one transfer commit; the review trail survives only as the review documents copied into the tree |
| Commits / files changed | 3 / 106 | 6 / 136 |

**Assessment.** Privacy is no longer a reason to prefer #40. The deciding points are:
- **Content:** #40 is a strict superset. It carries the same evidence tree plus the Cycle 9 Supreme Court package, which has no other carrier.
- **Base:** #40 is current.
- **History:** #36's only advantage is the full commit-level review trail. That trail is preserved in any case on its branch, and in the review documents both PRs carry.

**Recommendation:**
- Integrate **PR #40** after a focused re-review of its final head.
- Close **PR #36** unmerged as superseded, but **keep its branch**. Under the policy no history purge is needed, and the branch keeps the commit-level review trail for audit.
- Merging both is unnecessary. It would be harmless, because the evidence trees are identical.

## 4. Owner actions that are no longer required
`TRANSFER_RECORD.md` §7 items 3 to 5 (deleting the old branch for privacy, asking GitHub Support to purge `refs/pull/36/head` and `5212a95b`, and expiring local reflogs) are **withdrawn as privacy actions**. Closing #36 as superseded remains a housekeeping choice.
