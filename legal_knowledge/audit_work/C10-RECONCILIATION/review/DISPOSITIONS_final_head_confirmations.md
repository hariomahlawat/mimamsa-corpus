# Dispositions: confirmation reviews of the final heads (PRs #40, #41, #42, and the #43 reconciliation core)

Reviewer: Fable 5.2 (claude-fable-5-2). The reports are in `final_head_confirmations/`. The cd4f50ac confirmation of the #43 judgment audit and workstreams is `../review/fable_review_cd4f50ac.md`: ACCEPT, no findings.

| PR | Reviewed head | Verdict |
| --- | --- | --- |
| #42 AUTH-LEDGER | `2ba7b0a4` | **ACCEPT** (4 P3, 6 INFO) |
| #41 C9-LEGAL-EVIDENCE | `a61c0e57` | **ACCEPT** (2 P3, 5 INFO) |
| #40 C9-EVIDENCE-CLEAN | `e4d59196` | **ACCEPT** (1 P3, 4 INFO) |
| #43 reconciliation core | `7ccb9c2e` (re-checked at `cd4f50ac`) | ACCEPT WITH CONDITIONS (2 P2, 4 P3, 7 INFO) |

**Why #40, #41 and #42 have no new commits.** Their heads stay exactly as reviewed. Their P3s are recorded here and are not fixed on those branches, so that no unreviewed commit follows acceptance. Each P3 is carried into a follow-up change, which needs its own review and owner approval.

## #43 core: fixed in the commit after cd4f50ac
| ID | Sev | Disposition |
| --- | --- | --- |
| RR-01 | P2 | **FIXED.** In `build_reconciliation.py` the `parent_doc_id` fallback no longer applies to judgment rows: their parent is the court bucket, not a document identity. The five court buckets are gone. `SAME_DOC_ID_DIFFERENT_BYTES_REQUIRES_IDENTITY_REVIEW` = 8 statute groups. A test asserts that no group is a court bucket. Downstream: the statutory pin of `COPY_EQUIVALENCE_REGISTER.csv` is updated, and the quality snapshot copy of `RECONCILIATION_MANIFEST.json` is refreshed (all four snapshot inputs `LIVE_MATCHES_SNAPSHOT`). Statutory, quality and judicial `--check` OK. This supersedes the "13 groups" in `DISPOSITIONS_160adfd1.md` (RC-11). |
| RR-02 | P2 | **FIXED (wording).** `CAPTURE.md` now says which CSVs carry the `hf_snapshot` column (inventory and repository reconciliation). The other outputs take the same unpinned snapshot through `RECONCILIATION_MANIFEST.json`. |
| RR-05 | P3 | **FIXED.** The `check_dataset_integrity.py` docstring now states the `raw_manifest.csv` size difference. |
| RR-03 | P3 | **DEFERRED.** The basis wording for the 12 `hf_legal_knowledge` groups and the working store. No count depends on it. |
| RR-04 | P3 | **ESCALATED (legal side).** The authority-matrix ranking of open-data bulk copies above SCR renditions for the Supreme Court needs the legal adviser's confirmation. The ranking is not used to change any status. |
| RR-06 | P3 | **PARTLY ADDRESSED.** RR-01 now has a test. Dedicated tests for RC-01, RC-02, RC-04 and the RC-10 guard are deferred to a follow-up. |
| RR-13 | INFO | **NOTED.** The service-number-shaped tokens are inside published case titles. Under the judicial publication policy they are not masked, and the count is unchanged. |

## P3s on #40, #41 and #42: recorded, carried to a follow-up change
| ID | PR | Disposition |
| --- | --- | --- |
| CA-01 | #42 | Carry forward. A FIFO at `ledger/HEAD` or `ledger/manifest.jsonl` can block `verify`, and a directory at `ledger/HEAD` gives rc 1. Both are pre-existing. Fix: an `lstat` regular-file check before opening, and `OSError` in the fail-closed handler. |
| CA-02 | #42 | Carry forward. Strict walk of the `ledger/` and `decisions/` contents (symlinks, FIFOs, stray directories). |
| CA-03 | #42 | Carry forward. Tests for a symlinked `decisions/`, the non-directory branch and the `unexpected_effective` base guard. |
| CA-04 | #42 | Carry forward. Document that an absent `decisions/` passes at version 0. |
| CL-01 | #41 | Carry forward. The "not verbatim readings" label also covers `C9-AG-RES-SC4-01`, which does hold quoted readings. |
| CL-02 | #41 | Carry forward. The truncation marker is to be extended to `provision`, `amending_instrument`, `edge_kind` and `status_detail`. |
| CC-01 | #40 | Carry forward. The `build_c9_pack.py` usage text still names `c9out_SC`; documentation only. |

The ledger stays at version 0 (HEAD `0 443c4bdf…6b6b`). No real entries exist.
