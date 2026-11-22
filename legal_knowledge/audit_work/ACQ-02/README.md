# ACQ-02: acquisition supplement for the 16 archival PDFs found by the amendment search (proposal, not executed)

**Status: PROPOSAL. Nothing has been ingested into `data/` or added to `config/sources.yaml`.**
**Separate from PR #8.** The 14 URLs pinned in PR #8 (ACQ-01 B1/B2/B6) are unchanged. These 16 files are a new, separately identified proposal, and none is in the PR #8 list (`in_PR8_pinned_list = NO`).

## What was verified (2026-11-22, orchestrator, independent of the discovery agent)
| Check | Result | Where |
| --- | --- | --- |
| Integrity: size, MD5 and SHA-1 against fresh archive.org metadata (`/metadata/<identifier>`, fetched 2026-11-22) | 16/16 match | `supplement_inventory.csv`, `archive_org_metadata_snapshot_acq02.json` |
| SHA-256 recomputed and compared with the discovery agent's register | 16/16 agree | `supplement_inventory.csv` (`agent_sha256_agrees`) |
| Issue identity read from the page image (Gazette part, section, issue date, printed page, S.R.O. number and date, short title) | 17/17 instruments confirmed (16 files; S.R.O. 44 and 61 of 1991 share one issue) | `page_image_checks_acq02.csv` (PIC-13..PIC-28, own renders at 110 dpi); S.R.O. 332/1989 is PIC-12 |
| Operative wording of each instrument read from the image, not OCR | All operative pages image-checked. Continuation pages first read via the text layer (S.R.O. 205/1961 p.142-143, 5/1968 p.10, 278/1985 p.532) were image-checked on 2026-11-22: PIC-30..34 in `ARMY-RULES-CHAIN-01/page_image_checks_chain.csv`. S.R.O. 205/1961 ends on p.143 (p.144 is blank) | `page_image_checks_acq02.csv`, `ARMY-RULES-CHAIN-01/page_image_checks_chain.csv` |
| Access restrictions | No access marking printed on any checked page. No `access-restricted-item` flag in archive.org metadata. Gazette notifications are published law. | `supplement_inventory.csv` |
| Classification (SOURCE_AUTHORITY_POLICY v1) | `ENACTED_OR_NOTIFIED_PRIMARY`, carried as `THIRD_PARTY_ARCHIVAL_FACSIMILE`, fidelity `ARCHIVAL_FACSIMILE_OF_OFFICIAL`. The 2018 item is a digitally signed e-Gazette PDF. Declarations under r.188(e) are marked as such. | `supplement_inventory.csv` |
| Compilation comparison | India Code compilation r.193/r.194 image-checked (PIC-29) | `page_image_checks_acq02.csv` |

## Reproducibility
- The bytes checked here are in this session's scratchpad, which is **not** the evidence of record.
- After approval, the record copy must be re-fetched through the audited crawler from the pinned URLs in `proposed_documents_acq02.yaml`, which carries `expected_sha256`, `expected_md5` and `expected_bytes`.
- A fetch whose hash differs from the expected value fails, and is reported rather than accepted.
- Page-image checks are then re-run on the record copy, using the same pages and DPI. Render hashes depend on renderer version and DPI, so equality of **source** SHA-256 is the integrity test.

## Execution needed (each step needs owner approval)
1. A separate crawler-config PR adding the 16 URLs to `sources.archive.documents`, with tests that pin the exact list. This is like PR #8 but stacked after it, and it never edits the PR #8 list.
2. Dry run, then fetch with `--yes-download`, then the pipeline, then a checksum comparison against `expected_*`.
3. Page-image re-check on the record copy, an acquisition register, CI, and separate review proposals.
