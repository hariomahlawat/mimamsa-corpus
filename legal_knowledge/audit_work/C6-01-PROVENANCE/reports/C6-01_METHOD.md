# C6-01 method

Evidence was collected **only from committed registers**. Every item is cited as `file#row`, and nothing was reconstructed. The rules are coded in `tools/build_provenance.py` and summarised here.

## Evidence types
| Code | Evidence | Strength |
| --- | --- | --- |
| L1 | PILOT-01 code register: the official URL's recorded `official_sha256` equals the held sha256 | FULL |
| L2 | archive.org metadata: ACQ-02 supplement with size, MD5 and SHA-1 all OK; or the ACQ-01/ACQ-02 snapshot matched on MD5, SHA-1 and size | FULL |
| L2 | as above, matched on MD5 and size only (the ACQ-01 snapshot has no SHA-1) | MD5_SIZE (never sufficient for DOCUMENTED) |
| L3 | PILOT-01 `sources/*.json` retrieval record with URL and sha256 (including a sha256 stated inside a locator) | FULL |
| L4 | PILOT-01 source-discovery register download record (`downloaded_sha256`) with a URL | FULL |
| L4 | the same record with a repository identifier but no URL | IDENTIFIER_SHA (never sufficient for DOCUMENTED) |
| L5 | R23 amendment-search register: archive identifier with `md5_ok` | MD5 (never sufficient) |
| L6 | WS-A identity register: computed MD5 equals the archived MD5, with an archive identifier | MD5 (never sufficient) |
| I | page-image identity check with a 64-hex render hash, or an ARMY-RULES-CHAIN-01 row at `IMAGE_CHECKED`, or a C6-01 check (`inputs/page_image_checks_c6.csv`) with `identity_result=CONFIRMED` | — |
| Ip | a C6-01 page-image check with `identity_result=PARTIAL`: the page was read but a required identity element (for example the issuing authority or volume) is not printed on the copy. **Ip does not satisfy I** | — |
| T | page-1 text-layer identity. **Court PDFs only**, following the Cycle 4 PPS Bedi precedent; never accepted for a scanned publication | — |
| X | contradiction: the same official URL recorded with another sha256, or a WS-B identity row marked contradicted | — |

## Outcomes
| Outcome | When |
| --- | --- |
| `AUTHENTICATION_PENDING` | any X |
| `PROVENANCE_DOCUMENTED` | locator strength **FULL only**, **and** I (or T for a court copy), **and** no X. MD5_SIZE, IDENTIFIER_SHA and MD5 never qualify (Cycle 4 bar; verification F-02) |
| `PROVENANCE_PARTIALLY_DOCUMENTED` | a byte-identical locator without the required identity evidence, or identity evidence with only a locator lead |
| `IDENTITY_VERIFIED_PROVENANCE_UNDOCUMENTED` | identity evidence only |
| `NO_RECOVERABLE_PROVENANCE` | nothing |

Weaker locators (MD5_SIZE, IDENTIFIER_SHA, MD5) can reach at most PROVENANCE_PARTIALLY_DOCUMENTED. Tests enforce this on the committed register and on the builder's decision function.

## Proposed classes
Each class is the same one Cycle 4 used for the same carrier type:

| Class | Applies to |
| --- | --- |
| `PRIMARY_GAZETTE_ARCHIVAL_FACSIMILE` | archive.org Gazettes |
| `PRIMARY_GAZETTE_GOVERNMENT_HOSTED_SCAN` | a Gazette scan hosted on India Code (Cycle 4 class; assigned to no C6-01 proposal: the only in-scope India Code scan, Act 13/1975, is not DOCUMENTED) |
| `PRIMARY_OFFICIAL_COURT_COPY` | SC copies |
| `NON_PRIMARY_PARLIAMENTARY_RECORD` | the Rajya Sabha papers-laid record |
| `NON_PRIMARY_OFFICIAL_COURT_RENDITION` | a court-system rendition whose carrier is unknown (Rajbir bosir copy) |
| `NON_PRIMARY_OFFICIAL_PUBLICATION_COPY` | the incomplete ER 2023 copy; and, conservatively, the TRA 2026 copy: an e-Gazette text re-hosted by India Code with an IndiaCode watermark. No Cycle 4 class covers a watermarked born-digital re-host (the C4 `PRIMARY_GAZETTE_GOVERNMENT_HOSTED_SCAN` class was given to a scan), so the class is reserved for reviewer and owner decision |

## Limits
- A matching hash proves byte identity, not legal authority.
- A filename or path identifier is treated as a lead only, never as a locator.
- No signature has been verified (the TRA 2026 copy shows a digital-signature stamp; it was not cryptographically checked).
- Proposal IDs are display IDs (`C6-01-AP-<first 8 hex of sha256>`); the canonical identity is the full sha256. The builder stops on a duplicate.
- Retrieval dates appear only where a retrieval record gives them. A register date is labelled as such.
