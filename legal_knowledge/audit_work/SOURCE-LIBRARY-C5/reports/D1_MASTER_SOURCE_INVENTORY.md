# D1. Master source inventory

**Registers:**
- `registers/source_master_register.csv`: 112 publications or instruments, one row per legal instrument and copy class (for example, as-enacted Gazette vs government compilation).
- `registers/source_copy_register.csv` (new in schema c5-2): one row per held binary (67 copies). It carries copy-level carrier, acquisition provenance and authentication.

Both are built by `tools/build_registers.py` from `inputs/` and checked against the frozen held-file manifest, the discovery candidates and the Cycle 4 source-authentication register.

**Deduplication:** a source is one row however many copies are held. Copies of the same instrument are never merged into a single authenticated state. Each copy keeps its own state (see the authentication section below).

## Holding state by priority (from the register)
| Holding state | P0 | P1 | P2 |
| --- | --- | --- | --- |
| HELD_PRIMARY_GAZETTE_FACSIMILE | 4 | | |
| HELD_PRIMARY_GAZETTE_GOVERNMENT_SCAN | 1 | | |
| HELD_PRIMARY_OFFICIAL_COURT_COPY | | 7 | |
| HELD_AUTHENTICATION_PENDING (Isaac) | | 1 | |
| HELD_GOVERNMENT_COMPILATION | 5 | | |
| HELD_GOVERNMENT_COMPILATION_EXTRACT | 2 | | |
| HELD_OFFICIAL_PUBLICATION_PROVENANCE_UNDOCUMENTED | 23 | 1 | 2 |
| HELD_OFFICIAL_COURT_COPY_PROVENANCE_UNDOCUMENTED | | 8 | |
| HELD_UNVERIFIED_MANUAL (MML) | | | 8 |
| NOT_HELD_CANDIDATE_LOCATED | 7 | 10 | 16 |
| NOT_HELD_LEAD_ONLY (RA 1987) | 1 | | |
| NOT_HELD_NOT_FOUND_IN_SEARCHED_SOURCES | 3 | 5 | |
| NOT_HELD_NOT_CHECKED | | 7 | |
| NOT_HELD_RESTRICTED_SUSPECTED | 1 | | |

**Evidence stage** is derived from holding state and carrier. It is never set by hand.

| Stage | Count |
| --- | --- |
| DOCUMENT_ACQUIRED | 62 |
| OFFICIAL_CANDIDATE_LOCATED | 15 |
| ARCHIVAL_OR_THIRD_PARTY_CANDIDATE_LOCATED | 18 |
| LEAD_ONLY | 1 |
| NOT_FOUND_IN_SEARCHED_SOURCES | 8 |
| NOT_CHECKED | 7 |
| RESTRICTED_MARKING_SUSPECTED | 1 |

`DOCUMENT_AUTHENTICATED` is never reached, because no copy has custodian authentication. `AMENDMENT_CHAIN_COMPLETE` (policy value `CHECKED_FOR_RELEVANT_PERIOD`) is never reached either.

## Source authentication (derived from controlled metadata: `coverage_summary.json` → `authentication`)
The Cycle 4 source-authentication register has **13 rows**:

| Register class | Rows |
| --- | --- |
| PROVENANCE_DOCUMENTED primary: **5 Gazette** (4 archival facsimiles: S.R.O. 484/1954, 205/1961, 17(E)/1993, 8(E)/2003; 1 government-hosted scan: Act 37/1992) | 5 |
| PROVENANCE_DOCUMENTED primary: **7 official court copies** (PPS Bedi, Virendra Kumar, Parashotam Dass, Arjun Panditrao, Anvar, P S Gill, Jasbir Singh) | 7 |
| AUTHENTICATION_PENDING: **Isaac** (2026 INSC 993) | 1 |

That gives **12 documented-primary copies, in 12 sources, and 1 authentication-pending copy.**
- A register row is not by itself primary evidence. A copy counts only if its own row is PROVENANCE_DOCUMENTED with a PRIMARY_* class, under the Cycle 4 shared rule (`CALIBRATION-02/tools/evidence_classification.py`).
- The other 54 held copies have undocumented provenance under that rule: compilations, unregistered official copies and manuals.

**Act 37/1992** is one instrument with three copies, and only `f11d443e` has documented provenance:

| Copy | What it is | Eligible as primary |
| --- | --- | --- |
| `f11d443e` | Gazette scan with documented provenance | Yes |
| `a5943b72` | page-equivalent trailer-ID variant | No |
| `f1e69a74` | India Code text rendering | No |

## Headline gaps (evidence-bounded)
- **Gazette texts not held but located on archive.org** (md5 and size pinned): the Army Act 1950 as enacted, AFT Act 2007, BNSS, BSA and BNS.
- **Regulations for the Army 1987:** no complete official copy was located in the public sources successfully checked. The only held text is the India Code Chapter V extract. Historical CDA Guwahati and CDA Secunderabad file leads exist for Vols I and II (2014 secondary listing; Wayback snapshot metadata from 2021). The current official URLs return 404 or are unreachable. These are **leads only** (D2).
- **Territorial Army:**
  - The TA Rules 1948 and TA Regulations 1948 (Revised Edition 1976) are now **OFFICIAL_CANDIDATE_LOCATED** on India Code, based on search-index evidence from the official host.
  - Direct verification was **BLOCKED_ACCESS** (India Code robots.txt unreadable; fail-closed), and nothing was retrieved. They were previously NOT_FOUND.
  - The TA Act 1948 is located the same way.
- **Pension:**
  - Located on DESW but not held: PRA 2008 I/II, ER 2008 and the combined ER/GMO 2023 file.
  - The held 13 MB ER 2023 copy is INCOMPLETE: it contains the covering letter and ER-2023, but **GMO-2023 is absent**.
  - Not found in the sources checked: PRA 1961, ER 1982 and GMO 2002/2008.
- **CCCM Rules 1978 and S.O. 4010/1986:** not held. The held page is a Rajya Sabha record that the amendment was laid.
- **NOT_CHECKED this cycle:** AFT Procedure Rules, the ISO Act and Rules, Army Act s.4/s.9 notifications, and IPC/CrPC/IEA historical texts.
