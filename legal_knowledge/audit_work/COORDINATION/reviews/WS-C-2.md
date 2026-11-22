# Coordinator review: WS-C cycle 2 (99db4830, 98e8c380; head after base merge 7eca19d7)
- **Scope / gates:** only `WS-C-MML/`; tests, strict validation, check_registers, CSVs and records_658 sha all pass. No complete MML text: the longest non-edition CSV field is 877 chars, a descriptive note.
- **Independent check (FID-01, Army Act s.41(2) negation):** own renders, 130 dpi.
  - MML 2.pdf p.33 (file sha db211918…, render 0a14f0bf7edcb930e75ec6fa1ae0e2cf9ad3f1627c1a0a6934760e6e806a6d27): "if he commits such offence when not on active service ... five years".
  - MML vol 2(AA).pdf p.41 (file sha c8a791a1…, render 598741a98ea46acf9fbc6115254f3ba97d976d82077ad6c6a5c61a31b9c4e6b7): "if he commits such offence when on active service ... five years" ("not" missing).

  **Confirmed.** This is a transcription defect in the vol 2(AA) copy, not a statement of law.
- **Other items:** FID-02/03 (s.85 proviso, s.129 "person" vs "officer"; the s.129 Act text goes to WS-A, OQ-C-09); 1993 changes not applied in the vol 2(AR) DOCs; 47 locators and 8 time clauses image-checked; 20-step procedure crosswalk with distinct dates; cross-check of WS-A's itemisation (22 agree; XC-03 r.15 source unresolved).
- **Disposition:** accepted as a review proposal (PR #20 updated). Editions remain UNVERIFIED; no substantive 658 audit.
