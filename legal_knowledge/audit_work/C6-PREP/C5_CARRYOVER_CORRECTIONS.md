# Cycle 5 carry-over correction record

These are non-blocking P3 items found after PR #32 was reviewed. The Cycle 5 package is integrated and is **not edited in this branch**. Each item will be corrected in a future reviewed maintenance change to `SOURCE-LIBRARY-C5`.

| ID | Source | Item | Correct statement |
| --- | --- | --- | --- |
| C5-CO-01 | final confirmation of a37f1c23 | `reports/D7_INDEPENDENT_REVIEW_REPORT.md` says each accepted runner limitation "discards data or keeps a non-document listing" | Not every case is covered. A binary document placed behind a text lead-in longer than 1 KiB is **kept**, as `DISCOVERY_SAFETY_POLICY.md` "Stated limits" correctly says. |
| C5-CO-02 | final confirmation of a37f1c23 | `tools/run_guarded_discovery.py` docstring, line 15: "at most 1 KiB was received" | The 1 KiB figure applies at the application layer; TLS and socket buffers may hold more. |
| C5-CO-03 | C6-01 verification (P3) | C5 master title for `C5-SRC-P0-AA-AMD-ACT13-1975` gives "No.16" | The page image shows Hindi issue No.16 and English issue No.15 (the English number is recorded as uncertain in WSA-PIC-29). |
| C5-CO-04 | C6-01 final review R-12 (P3) | C5 master row `C5-SRC-P1-ER-2023-HELD-13MB` cites PILOT-01 discovery T3-02 (the 49.9 MB file, HEAD only, never downloaded) | The held 13,011,188-byte copy matches T3-01 (sha256, size and URL). |
