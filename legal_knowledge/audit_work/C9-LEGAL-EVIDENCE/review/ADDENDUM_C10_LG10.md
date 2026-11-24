# Addendum (Cycle 10): LG-10 closed

`DISPOSITIONS_c9_legal.md` recorded LG-10 (P3, documentary) as open. It is fixed in this commit. The earlier disposition record is not edited.

- **C9R-AA-09:** the needle now allows the wording between "s. 3" and the date. The Army Act compilation (`e47a4265…`) prints "w.e.f. 25-1-1975" on p.12, after `for "all words"`. The reading now lists **pp.11, 12 and 26**. It is an AI agent text-layer reading, not human-confirmed; p.12 was also checked in the text layer by the coordinator.
- **C9-AG-AFT-02:** the `provision` cell no longer inherits "UNKNOWN" from the C8 row. It names **s.9A** (words substituted by TRA 2021 s.26). Its status was already EVIDENCED, and the status and dates are unchanged.
- **Regeneration:** `collect_readings_c9.py` and `build_stat_c9.py`. Both `--check` runs pass, and `OUTPUT_SHA256SUMS` is updated.
