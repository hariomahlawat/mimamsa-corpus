# WS-E tools (Cycle 8)

All tools are offline, Python 3 standard library only, and read-only. Each one takes the repository snapshot path as an argument and writes only the output file you name.

| Tool | Purpose |
| --- | --- |
| `reconcile_judgments.py` | Classifies an incoming judgment batch against the existing corpus. |
| `test_reconcile_judgments.py` | Unit tests (unittest, synthetic fixtures, no network). |
| `xref_checks.py` | Deterministic cross-reference checks that emit candidate observations. Triage is done by hand in `../cross_reference_findings.csv`. |
| `select_sample.py` | Deterministic high-risk sample selection used for `../HIGH_RISK_REVIEW.md`. |

## reconcile_judgments.py

```
python3 reconcile_judgments.py --incoming batch.jsonl --repo <snapshot root> --out report.csv
# or explicit corpus files:
python3 reconcile_judgments.py --incoming batch.csv --out report.csv \
    --cases cases_53.jsonl --identity identity_resolution.csv \
    --holdings holdings_register.csv --holdings holdings_register_cycle3.csv \
    --copies source_copy_register.csv --case-source-map case_source_map.csv
```

**Input.** The batch is `.csv` or `.jsonl`. Every item needs `court`, `case_numbers`, `judgment_date` (YYYY-MM-DD), `parties`, `sha256` (64 lowercase hex characters) and at least one of `source_url` or `provenance`. These fields are optional: `item_id`, `citations` (or `citation`), `version_label`, `copy_note`, `title`. Lists can be JSON arrays or `;`-separated strings.

**Classes.** The first rule that matches wins:

1. `EXACT_DUPLICATE`: the sha256 is already known. Known hashes come from cases_53, the WS-B identity and holdings registers, and the C5 source_copy_register (mapped to cases through case_source_map). An item also gets this class if an earlier row in the same batch has the same sha256.
2. `VERSION_RELATIONSHIP`: same court, an overlapping case number and the same date, with a different sha256. The incoming item or the matched corpus copy also carries an explicit version marker, such as corrected, corrigendum, uncorrected, revised or modified.
3. `SAME_JUDGMENT_NEW_COPY`: same court, case number and date, with a different sha256 and no version marker.
4. `POSSIBLE_MATCH_REVIEW`: only fuzzy evidence. This covers the same case number with a different date (a possible later order in the same case), a shared citation, or party-name similarity of at least 0.5 (Jaccard similarity over distinctive tokens, with dates within one year). A person must review these items.
5. `NEW`: no match in the corpus snapshot supplied. This is not evidence that the judgment is missing from any external collection. The tool does not assume any collection is complete.

**Safety.** The tool never merges, never overwrites and never downloads anything.

- It fails closed: if any item is malformed, it lists every problem on stderr, writes no report and exits with status 2.
- It refuses an `--out` path that is one of its inputs.
- With `--repo`, every expected corpus file must exist. A missing corpus would silently turn duplicates into `NEW`.
- Output is byte-identical across runs for identical inputs.

**Matching details.**

- Case numbers are parsed into `(TYPE, number, year)` keys. TYPE is one of CA, CRLA, SLPC, SLPCRL, WPC, WPCRL, WP, RP, OA, MA, TA or DIARY, and bare `n/yyyy` numbers become UNTYPED keys.
- Ranges of up to 60 numbers are expanded, so `C.A. 6820–6824/2018` contains 6822.
- Courts are normalised. For example, "Supreme Court of India", "SC" and "Hon'ble Supreme Court" all become `supreme court`.
- A strong match also requires the corpus entity to have a recorded court. Other matches can only reach `POSSIBLE_MATCH_REVIEW`.

**Tests.** `python3 -m unittest test_reconcile_judgments -v` (25 tests). They cover each class, within-batch duplicates, version markers on either side, the same case number from a different court, CSV and JSONL input, determinism, unmodified inputs, seven malformed-input cases (fail closed), and parsing of case-number types and ranges.

**Known limits.**

- Version detection depends on explicit markers. Two unmarked copies of a corrected judgment are classed `SAME_JUDGMENT_NEW_COPY`, and the reason text asks for a byte and page comparison.
- Party similarity is token-based. Transliteration variants (for example Baljit/Baltit) can fall below the threshold, so items like that may come out as `NEW`.
- High Court and AFT bench names need explicit aliases in `COURT_ALIASES`.

## xref_checks.py / select_sample.py

```
python3 xref_checks.py <snapshot root> <held root (scratchpad)> <out_csv>
python3 select_sample.py <snapshot root> <out_csv> [per_domain=3]
```

The check IDs are documented in `../cross_reference_findings.md`.
