# D4. Amendment and supersession register

## Registers
- **`registers/amendment_register.csv` (87 rows):** instrument-level amendments.
  - 47 rows from ARMY-RULES-CHAIN-01 (Army Rules S.R.O.s).
  - 36 rows from the WS-A Army Act chain and its Cycle 3 addendum.
  - 4 C5 additions: RA 1987 slips (none located), PRA 2008 Reg 18 Pt II 2013, PRA family pension 2020, ER 2023 notifying letter. The letter is now held: it is p.1 of the 13 MB copy, read from the image as C5-PIC-01.
- **`registers/provision_amendment_chain.csv` (154 rows):** follows the brief's chain Publication → Provision → Instrument → Before text → After text → Effective date → Applicable period → Evidence.
  - 107 rows from the WS-A provision change log. Rows replaced by a Cycle 3 supersession are marked `superseded_by`.
  - 47 rows from the Army Rules provision chronology.
  - Before and after text are carried as recorded. Where the origin register did not transcribe it, the value is `NOT_CAPTURED`.
- **`registers/provision_register.csv` (212 rows):** one row per Army Rules heading located in the held India Code compilation. Each row gives the page and line (`sha256:<file> p.N line L`) and the WS-A completeness status. The register records **location**, not verified wording. Army Act sections are not yet indexed (see D8).

## Date discipline
Publication date, commencement as printed, effective date and retrospective deemed effect are kept in separate columns, exactly as in the origin registers. Every value missing from the origin is `NOT_DETERMINED` or `NOT_CAPTURED`; none is inferred. Commencement where an instrument is silent stays reserved (AQ-05), as does retrospective effect (AQ-06).

## Chain status by publication
| Publication | Chain status | Why |
| --- | --- | --- |
| Army Act 1950 | PARTIAL | The India Code amending-Acts list was blocked this cycle. Post-1992 amending Acts: NOT_FOUND (AA-13), which is not proof that none exist. The as-enacted Gazette is not held. |
| Army Rules 1954 | AMENDMENT_CHAIN_INCOMPLETE | 13 hint-only and 3 gap instruments (AR-001…). Nothing searched after 06-06-2022 until C5. There are now 10 unread candidates (C5C-004..013). |
| Regulations for the Army 1987 | AMENDMENT_CHAIN_INCOMPLETE | Neither the text nor any slip is held (D2). |
| PRA 2008 Parts I/II | AMENDMENT_CHAIN_INCOMPLETE | Two amending circulars located; the full circular archive was not paged. |
| ER 2008 / ER 2023 / GMO | AMENDMENT_CHAIN_INCOMPLETE | Instruments located but not held. The ER 2023 letter number and effective date come from secondary sources only. |
| AFT Act 2007, BNSS, BSA | PARTIAL | Compilations held; Gazette texts and later amendments not held. The Tribunals Reforms Act 2026 is held and amends AFT s.9A (C4). |

## Known supersession cases (CLAUDE.md acceptance list): documentary status only, no legal determination
| Case | Documentary evidence in the repository | State |
| --- | --- | --- |
| Field punishment, AA ss.75–76 omitted (1992) | Army (Amendment) Act 1992 (No. 37 of 1992), s.2 "omitted". Image-checked (PILOT-01 PIC-07; WS-A AA-08-s2), and re-confirmed on the image by independent review RV-26. | Instrument verified. **The Act has no commencement provision** (RV-26): assent 06-09-1992, Gazette 07-09-1992. The effective date stays NOT_STATED_PENDING_ADVICE (AQ-05). |
| AA s.127 omitted (1992) | Act 37 of 1992, s.11 "Section 127 of the principal Act shall be omitted." (WSA-PIC-27; AA-08-s11) | As above |
| IPC → BNS (and CrPC → BNSS, IEA → BSA) from 1 July 2024 | Gazette facsimiles of the three Acts and three commencement notifications **located, not held** (C5C-018..023) | Appointed date is NOT_DETERMINED from documents until the notifications are read (C5-ACQ-05). LAQ-13 is reserved. |
| Dharamvir Singh (ER 1982) vs Col N.C. Isaac 2026 INSC 993 (ER 2008) | Dharamvir held (official SC copy, provenance undocumented); Isaac held but AUTHENTICATION_PENDING. ER 1982 NOT_FOUND; ER 2008 located. The ER 2023 covering letter of 21-09-2023 (held, C5-PIC-01) prints "with effect from 21st September, 2023 and in supersession of all previous orders/rules on the subject". | LAQ-03 and LAQ-04 are reserved. Isaac's effect is not decided here. |
| 2023 SC ruling on High Court writs against AFT orders (Parashotam Dass) | Official SC copy held with documented provenance (C4 register) | Holding and treatment are tracked by WS-B, not changed here |

No `overrules`, `supersedes` or `amends` edge is proposed or verified in this package. Those edges stay with the WS-D relation graph and need legal review.
