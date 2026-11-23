# D1. Provenance recovery register (summary)

Register: `registers/provenance_recovery_register.csv`, 36 copies in 34 sources. Each row carries the source identity, issuing authority, carrier, retrieval URL, retrieval date (only where evidenced), retrieval method, checksums (sha256/md5/sha1/bytes), locator strength, pages, completeness, identity-verification references, related copies, current status, contradictions, proposed outcome and remaining gaps.

| Outcome | Court copies | Publication/record copies | Total |
| --- | --- | --- | --- |
| PROVENANCE_DOCUMENTED | 10 | 24 | 34 |
| PROVENANCE_PARTIALLY_DOCUMENTED | 0 | 2 | 2 |
| IDENTITY_VERIFIED_PROVENANCE_UNDOCUMENTED | 0 | 0 | 0 |
| NO_RECOVERABLE_PROVENANCE | 0 | 0 | 0 |
| AUTHENTICATION_PENDING | 0 | 0 | 0 |

Locator strength of the DOCUMENTED rows: FULL 28, MD5_SIZE 6. The six MD5_SIZE rows are the Army Rules Gazettes AR-010, AR-011, AR-016, AR-024, AR-034 and AR-035; the ACQ-01 snapshot records MD5 and size but no SHA-1. Retrieval dates: 8 rows carry a date from a retrieval record; the others have only a register date or none (`NOT_EVIDENCED`).

**The seven Supreme Court case records that were partial in Cycle 5** (Dharamvir Singh, Rajbir Singh, Girish Kumar (Feb 2026), Mullikote, Ranjit Thakur, S N Mukherjee, Navjot Sandhu): every one of their held copies has an L1 or L3 record (official URL with a sha256 equal to the held bytes) and a page-1 text identity match. No contradiction was found. N S Yadav (not one of the 53 cases) meets the same criteria. **Isaac is out of scope and unchanged (AUTHENTICATION_PENDING).**
