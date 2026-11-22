# Amendment search, 2026-11-22: review proposal, not approved

`amendment_search_2026-11-22.csv` was produced by a read-only discovery agent working in the scratchpad (not on any branch) and integrated by the orchestrator. Nothing was ingested into `data/`.

| Status | Count | Instruments |
| --- | --- | --- |
| LOCATED_IMAGE_CHECKED | 17 | S.R.O. 205/1961, 1/1961, 34/1963, 126/1964, 5/1968, 246/1982, 44/1985, 55/1985, 68/1985 (corrigendum to 55/1985), 278/1985, 169/1987, 302/1987, 332/1989, 44/1991, 61/1991, 235/1991, 2(E)/2018 |
| LOCATED_TEXT_ONLY | 5 | Extra instruments: S.R.O. 331, 348, 351 and 404 of 1960; S.R.O. 22 of 2010 |
| NOT_FOUND | 3 | E-7 of 17-06-1960; S.R.O. 258 of 27-11-2002; anything after 06-06-2022 |

- **Does any instrument amend Rule 23? None of the 22 located.** Combined with R23-VERIFY-01's earlier 9, that is 31 instruments examined, none amending r.23.
- **Corrections to the official amendment notes:**
  - "S.R.O. 34 dated 5-6-1963" is S.R.O. 34 of 05-01-1963, a declaration under r.188(e) (printed p.14). S.R.O. 2(E)/2018 itself cites "05th January, 1963".
  - S.R.O. 2(E)/2018 is also an r.188(e) declaration, not an amendment of the Rules.
- **Orchestrator spot-checks:**
  - All 22 SHA-256 values recomputed from the downloaded files; 0 mismatches.
  - S.R.O. 332/1989 (r.194) re-checked on the page image (`page_image_checks.csv`, PIC-12).
- **Carrier classification (SOURCE_AUTHORITY_POLICY v1):**
  - archive.org scans: `ENACTED_OR_NOTIFIED_PRIMARY` / `THIRD_PARTY_ARCHIVAL_FACSIMILE`.
  - The 2018 item is a digitally signed e-Gazette PDF carried by archive.org.
- **Limitation:** for a few multi-page instruments, later pages were read from the text layer only (noted per row). Absence of an instrument is not proof that none exists; egazette.gov.in is unreachable from this container.
