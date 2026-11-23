# D1. Provenance recovery register (summary)

**Register:** `registers/provenance_recovery_register.csv`, 36 copies in 34 sources.

Each row carries:
- source identity, issuing authority and carrier;
- retrieval URL, retrieval date (only where evidenced) and retrieval method;
- checksums (sha256, md5, sha1, bytes) and locator strength;
- pages, completeness and identity-verification references;
- related copies, current status and contradictions;
- proposed outcome and remaining gaps.

| Outcome | Court copies | Publication/record copies | Total |
| --- | --- | --- | --- |
| PROVENANCE_DOCUMENTED | 10 | 23 | 33 |
| PROVENANCE_PARTIALLY_DOCUMENTED | 0 | 3 | 3 |
| IDENTITY_VERIFIED_PROVENANCE_UNDOCUMENTED | 0 | 0 | 0 |
| NO_RECOVERABLE_PROVENANCE | 0 | 0 | 0 |
| AUTHENTICATION_PENDING | 0 | 0 | 0 |

**Locator strength of the DOCUMENTED rows:** FULL 33.
Only FULL can reach DOCUMENTED: a sha256 recorded with a URL, or archive size, md5 and sha1. This is the Cycle 4 bar.

**Retrieval dates:** 15 rows carry a date from a retrieval record. The rest have only a register date, or none (`NOT_EVIDENCED`).

**The seven Supreme Court case records that were partial in Cycle 5:**
- Dharamvir Singh, Rajbir Singh, Girish Kumar (Feb 2026), Mullikote, Ranjit Thakur, S N Mukherjee and Navjot Sandhu.
- Each has a FULL locator (an official URL with a sha256 equal to the held bytes) and a page-1 text identity match. No contradiction was found.
- Where the evidence is a register corroboration only, the row carries the Cycle 4 caveat "accepted because uncontradicted".
- Rajbir's third copy (a court-system text rendition with unknown carrier) is proposed as non-primary.
- N S Yadav, which is not one of the 53 cases, meets the same criteria.

**Isaac is out of scope and unchanged (AUTHENTICATION_PENDING).**
