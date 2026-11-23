# WS-E tools (Cycle 8)

All tools are offline, Python 3 standard library only, and read-only. Each one takes the repository snapshot path as an argument and writes only the output file you name. `reconcile_judgments.py` refuses to write over an input or, without `--overwrite`, over any existing file.

| Tool | Purpose |
| --- | --- |
| `reconcile_judgments.py` | Classifies an incoming judgment batch against the existing corpus. |
| `test_reconcile_judgments.py` | Unit tests (unittest, synthetic fixtures, no network). |
| `xref_checks.py` | Deterministic cross-reference checks that emit candidate observations. Triage is done by hand in `../cross_reference_findings.csv`. |
| `select_sample.py` | Deterministic high-risk sample selection used for `../HIGH_RISK_REVIEW.md`. |

## reconcile_judgments.py

```
python3 reconcile_judgments.py --incoming batch.jsonl --repo <snapshot root> --out report.csv [--overwrite]
# or explicit corpus files:
python3 reconcile_judgments.py --incoming batch.csv --out report.csv \
    --cases cases_53.jsonl --identity identity_resolution.csv \
    --holdings holdings_register.csv --holdings holdings_register_cycle3.csv \
    --copies source_copy_register.csv --case-source-map case_source_map.csv
```

**Input.** The batch is `.csv` or `.jsonl`, UTF-8. Every item needs `court`, `case_numbers`, `judgment_date` (YYYY-MM-DD, not before 1800 and not after today), `parties`, `sha256` (64 lowercase hex characters) and at least one of `source_url` or `provenance`. These fields are optional: `item_id` (unique within the batch), `citations` (or `citation`), `version_label`, `copy_note`, `title`. Lists can be JSON arrays of strings or `;`-separated strings.

**Classes.** The first rule that matches wins:

1. `EXACT_DUPLICATE`: the sha256 is already known. Known hashes come from cases_53, the WS-B identity and holdings registers, and the C5 source_copy_register (mapped to cases through case_source_map). An item also gets this class if an earlier row in the same batch has the same sha256. If the item's court, case number or date contradicts what the corpus (or the earlier batch row) records for that hash, the row carries `flags=METADATA_CONFLICT_WITH_KNOWN_HASH`, the reasons say which fields disagree, and a warning goes to stderr. Review these rows: a wrongly pasted hash would otherwise hide a new judgment.
2. `VERSION_RELATIONSHIP`: same court, an overlapping typed case number (same type, number and year) and the same date, with a different sha256. The incoming item or the matched corpus copy also carries an explicit version marker, such as corrected, corrigendum, uncorrected, revised or modified.
3. `SAME_JUDGMENT_NEW_COPY`: same court, typed case number and date, with a different sha256 and no version marker.
4. `POSSIBLE_MATCH_REVIEW`: only fuzzy evidence. This covers the same case number with a different date (a possible later order in the same case), a number that matches only through an untyped `n/yyyy`, a shared citation, or party-name similarity of at least 0.5 (Jaccard similarity over distinctive tokens, with dates within one year). A person must review these items.
5. `NEW`: no match in the corpus snapshot supplied. This is not evidence that the judgment is missing from any external collection. The tool does not assume any collection is complete.

**Safety.** The tool never merges and never downloads anything. It writes only the report.

- It fails closed: if any item is malformed, it lists every problem on stderr, writes no report and exits with status 2. Malformed includes duplicate JSON keys, duplicate `item_id`, NUL or other control characters, non-string list members, implausible dates, duplicate CSV header columns, ragged CSV rows and non-UTF-8 input. An unreadable corpus file also exits 2.
- Output guard (exit 2, nothing written):
  - an `--out` that resolves to any input: same real path after symlinks, `os.path.samefile`, or same device and inode (hard link). This applies even with `--overwrite`;
  - an `--out` inside a `curated_originals` directory;
  - an existing `--out`, unless `--overwrite` is given;
  - an `--out` that is a directory, or whose parent directory is missing.
- The report is written atomically. It goes to a temporary file in the target directory, which is then hard-linked into place (fails if the path appeared meanwhile) or, with `--overwrite`, renamed over the old file. The guard is re-checked just before the switch.
- Report cells beginning with `=`, `+`, `-`, `@`, TAB or CR are prefixed with `'` so spreadsheets do not evaluate them.
- With `--repo`, every expected corpus file must exist. A missing corpus would silently turn duplicates into `NEW`.
- Output is byte-identical across runs for identical inputs.

**Matching details.**

- Case numbers are parsed into `(TYPE, number, year)` keys. TYPE is one of CA, CRLA, SLPC, SLPCRL, WPC, WPCRL, WP, RP, OA, MA, TA or DIARY, and bare `n/yyyy` numbers become UNTYPED keys.
- Ranges of up to 60 numbers are expanded, so `C.A. 6820–6824/2018` contains 6822.
- Courts are normalised. For example, "Supreme Court of India", "SC" and "Hon'ble Supreme Court" all become `supreme court`.
- A strong match also requires the corpus entity to have a recorded court. Other matches can only reach `POSSIBLE_MATCH_REVIEW`.

**Tests.** `python3 -m unittest test_reconcile_judgments -v` (47 tests; also run from the repository root as `python -m unittest tests.test_legal_audit_reconcile_judgments`). They cover each class, within-batch duplicates, version markers on either side, the same case number from a different court, CSV and JSONL input, determinism, unmodified inputs, malformed-input cases (fail closed), parsing of case-number types and ranges, and, after review RC-02/RC-10: `--out` as a symlink or hard link to an input, an existing non-input file (refused, then replaced with `--overwrite`), an input path with `--overwrite`, a `curated_originals` path, a directory or missing parent, a known hash with contradictory metadata, an untyped case number, formula-leading cells, duplicate keys and ids, NUL bytes, future and ancient dates, non-string list members, non-UTF-8 CSV and duplicate CSV headers.

**Known limits.**

- Version detection depends on explicit markers. Two unmarked copies of a corrected judgment are classed `SAME_JUDGMENT_NEW_COPY`, and the reason text asks for a byte and page comparison.
- Party similarity is token-based. Transliteration variants (for example Baljit/Baltit) can fall below the threshold, so items like that may come out as `NEW`.
- High Court and AFT bench names need explicit aliases in `COURT_ALIASES`.
- The metadata-conflict flag compares court, case number and date only. It cannot detect a wrong hash whose metadata happens to match.
- The guard refuses: any path resolving to an input (realpath, samefile or inode); paths inside `curated_originals`; any existing non-regular target (device, FIFO, socket, symlink), even with `--overwrite`; and, when `--repo` is given, any existing file inside the repository, even with `--overwrite`. New files inside the repository are allowed. **Without `--repo`, an existing file elsewhere is replaced if `--overwrite` is given**, so always pass `--repo` or write outside the repository. A narrow race remains between the final re-check and the rename, for an attacker who can write to the output directory at that moment.

## xref_checks.py / select_sample.py

```
python3 xref_checks.py <snapshot root> <held root> <out_csv>      # held root: directory the held-binary manifest paths are relative to
python3 select_sample.py <snapshot root> <out_csv> [per_domain=3]
```

The check IDs are documented in `../cross_reference_findings.md`.
