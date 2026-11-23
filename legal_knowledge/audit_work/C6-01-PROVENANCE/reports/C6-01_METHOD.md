# C6-01 method

Evidence was collected **only from committed registers**. Every item is cited as `file#row`, and nothing was reconstructed. The rules are coded in `tools/build_provenance.py` and summarised here.

## Evidence types
| Code | Evidence | Strength |
| --- | --- | --- |
| L1 | PILOT-01 code register: the official URL's recorded `official_sha256` equals the held sha256 | FULL |
| L2 | archive.org metadata: ACQ-02 supplement with size, MD5 and SHA-1 all OK; or the ACQ-01/ACQ-02 snapshot matched on MD5, SHA-1 and size | FULL |
| L2 | as above, matched on MD5 and size only (the ACQ-01 snapshot has no SHA-1) | MD5_SIZE |
| L3 | PILOT-01 `sources/*.json` retrieval record with URL and sha256 (including a sha256 stated inside a locator) | FULL |
| L4 | PILOT-01 source-discovery register download record (`downloaded_sha256`) | FULL |
| L5 | R23 amendment-search register: archive identifier with `md5_ok` | MD5 |
| L6 | WS-A identity register: computed MD5 equals the archived MD5, with an archive identifier | MD5 |
| I | page-image identity check with a 64-hex render hash, or an ARMY-RULES-CHAIN-01 row at `IMAGE_CHECKED` | — |
| T | page-1 text-layer identity. **Court PDFs only**, following the Cycle 4 PPS Bedi precedent; never accepted for a scanned publication | — |
| X | contradiction: the same official URL recorded with another sha256, or a WS-B identity row marked contradicted | — |

## Outcomes
| Outcome | When |
| --- | --- |
| `AUTHENTICATION_PENDING` | any X |
| `PROVENANCE_DOCUMENTED` | locator strength FULL or MD5_SIZE, **and** I (or T for a court copy), **and** no X |
| `PROVENANCE_PARTIALLY_DOCUMENTED` | a byte-identical locator without the required identity evidence, or identity evidence with only a locator lead |
| `IDENTITY_VERIFIED_PROVENANCE_UNDOCUMENTED` | identity evidence only |
| `NO_RECOVERABLE_PROVENANCE` | nothing |

MD5-only matches (L5 or L6 alone) never reach DOCUMENTED.

## Proposed classes
Each class is the same one Cycle 4 used for the same carrier type:

| Class | Applies to |
| --- | --- |
| `PRIMARY_GAZETTE_ARCHIVAL_FACSIMILE` | archive.org Gazettes |
| `PRIMARY_GAZETTE_GOVERNMENT_HOSTED_SCAN` | a Gazette scan hosted on India Code |
| `PRIMARY_OFFICIAL_COURT_COPY` | SC copies |
| `NON_PRIMARY_*` (outside the primary rule) | the Rajya Sabha record and the incomplete ER 2023 copy |

## Limits
- A matching hash proves byte identity, not legal authority.
- A filename or path identifier is treated as a lead only, never as a locator.
- No signature has been verified.
- Retrieval dates appear only where a retrieval record gives them. A register date is labelled as such.
