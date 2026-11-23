# C6-01: Existing source provenance recovery (Cycle 6)

**What this package is:** proposals only. It contains no downloads, no edits to any earlier register, no legal-status change and no HF upload.

- **Baseline:** staging `04665eb17d2a1e4c8626d38346f17fa76b417548`, the merge of PR #32.
- **Branch:** `claude/c6-source-provenance`.
- **Scope:** the 34 Cycle 5 sources (36 held copies) whose holding state is `*_PROVENANCE_UNDOCUMENTED`:
  - 26 publication or record sources with 26 copies (one copy each);
  - 8 Supreme Court judgment sources with 10 copies (Rajbir has three);
  - total 34 sources and 36 copies (counted from `registers/provenance_recovery_register.csv`; a test checks the split).
- **Denominators kept separate:** 67 unique held binaries, 93 held paths, 54 undocumented copies in Cycle 5 (that larger set also includes compilations and manuals, which are out of scope here).

| Path | Content |
| --- | --- |
| `inputs/page_image_checks_c6.csv` | C6-01 page-image identity checks of held copies (render hash; renders in `reports/evidence/`). `CONFIRMED` counts as identity evidence; `PARTIAL` does not |
| `inputs/held_copy_facts.csv` | md5, sha1, bytes, pages and p.1 text excerpt for each in-scope copy (captured locally by `tools/compute_copy_facts.py` from the held binaries; sha256 re-verified) |
| `registers/provenance_recovery_register.csv` | **D1:** one row per investigated copy, with the evidence item references (file#row) |
| `registers/source_authentication_proposals.csv` | **D2:** proposed additions in the CALIBRATION-02 register columns (not incorporated) |
| `registers/unresolved_provenance_register.csv` | **D5** |
| `registers/c6_01_summary.json` | outcome counts and the **D4** coverage simulation |
| `reports/` | `C6-01_METHOD.md`, D1–D6 reports |
| `review/` | independent verification (D3); `legacy_proposal_id_map.csv` maps the sequential AP-nn IDs used by the first verification and the re-verification to the current sha256-based IDs |
| `tools/build_provenance.py` | deterministic builder (`--check`) |

Reproduce:
```bash
python legal_knowledge/audit_work/C6-01-PROVENANCE/tools/build_provenance.py --check
```
```bash
python -m unittest tests.test_legal_audit_c6_provenance
```
