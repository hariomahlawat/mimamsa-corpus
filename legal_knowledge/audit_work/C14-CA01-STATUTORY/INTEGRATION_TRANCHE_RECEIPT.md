# C14 integrated candidate workflow and metadata adapter — development receipt

Date: 2026-11-26. No source acquisition, live inventory enumeration, corpus mutation, HF write, legal promotion, merge or rebase by this tranche.

## Review pins

Staging observed ee17b0660511b66fdd5307833e11d1268de35b56. PR #58 substantive head 2f6fe137cd46c64d2f01ae4408b5b4fcf79aeb9b; PR #59 substantive head 2297abda2a8b7d78a31bd897d156ce3ae1618b87. Subsequent receipt-only commit must not be mistaken for a different code review subject. Verify both live heads before review.

Previous Windows synthetic suite: owner screenshot 32/32, 0.721 s; exact checkout and runtime version not printed in screenshot. Screenshot digest independently rechecked against supplied image. Earlier audit CI results documented in WINDOWS_SYNTHETIC_ACCEPTANCE_RECEIPT.json. New CI runs pending; new six workflow and four SDK adapter regressions are committed but not yet observed passing.

## Candidate workflow

pipeline/candidate_workflow.py connects an exact manifest digest, strictly shaped document list, default classifier, candidate-only journal, explicit predecessor and negative release preflight. Caps: 15 documents, 100,000,000 declared bytes, 500 declared pages. Tests exercise persisted SQLite, duplicate aliases, rerun idempotence, explicit revision, restriction omission before opening fixture, declared-size mismatch, invalid manifest digest and duplicate IDs. No legacy writer, importer or application changes. Recovery state is a caller's scope claim, not proof of historical exclusion; bind to separately reviewed recovery plan before real inputs. Source sizes and page counts are preflight checks, not a hard parser resource limit. The workflow currently uses a caller-supplied journal and restriction predicate; enforce pinned register and verified input staging, protected output location, native path and process isolation before use. The old read-only recovery planning function has not been accepted for whole-corpus execution. Partial events can persist if a later item fails; a failed batch must not be reported as complete. Do not pass restricted material, active corpus or unapproved inputs.

## Metadata-only inventory

hf_inventory_provider.py adds a narrow adapter around the HF SDK dataset_info and list_repo_tree operations. Exact private dataset, full revision and endpoint checked; compares immediate roots against the seven known stores; uses pinned revision for every enumeration; only LFS SHA-256/size claims and permitted paths go to the existing collector. Unknown roots fail, missing hashes block complete coverage, no actual source byte claim. Four tests use inert SDK objects. No CLI activation, no token handling change. Verify real SDK 2.4.0 object shapes, pagination and tree semantics; bind restricted register and read-only credential, independently review permitted local-store coverage, use process deadline and safe output. No acquisition eligibility.

## Transport

acquisition_batch.py now invokes the earlier narrow robots parser, aggregate request/byte/time budget and safe attempt metadata. The unconditional execute interlock remains. DNS/connection failures do not yet produce a fully closed attempt record; deadline polling cannot interrupt blocked operations. Review bounded streaming, partial-file treatment, process-wide kill and descendant containment, native Windows ACL/reparse controls, trusted consent provisioning and safe receipts before lifting interlock. No live network test. The separate approval verifier is not activation wiring. No independently accepted acquisition.

## Next acceptance action

Run the updated 38-test PDF synthetic suite from an isolated reviewed checkout, verify the new audit CI logs, then give Codex the prior review packet, corrective tranche receipts and this integration receipt. Focus on exact reproducible findings and staged closure criteria, not a fresh broad audit. Do not merge, run active corpus, enable acquisition or make authority changes. After review, approve a bounded metadata-only local job separately from source acquisition. C14-01 through C14-15 remain open or contained, not independently closed.
