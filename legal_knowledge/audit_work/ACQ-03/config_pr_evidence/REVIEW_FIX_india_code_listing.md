# Regression evidence: India Code listing vs served bytes (PR #23 review finding)

## BEFORE the fix (tests written first, run against the unfixed config and verify_batch.py)
```
FAILED tests/test_verify_batch.py::test_watermarked_india_code_download_is_not_rejected
FAILED tests/test_verify_batch.py::test_served_sha256_pin_rejects_unexpected_change
FAILED tests/test_verify_batch.py::test_served_sha256_pin_passes_identical_bytes
FAILED tests/test_verify_batch.py::test_non_pdf_served_file_is_rejected - Ass...
FAILED tests/test_verify_batch.py::test_real_acq03_india_code_entries_use_listing_fields_not_strict_expectations
5 failed, 1 passed in 0.59s
--- faithful reproduction on a real ACQ-03 India Code entry:
E           AssertionError: ('acq03-033-b5', {'acq03-033-b5': ['acq03-033-b5', 'FAIL', 'md5 differs from pre-committed value; size differs from pre-committed value', '41ea3c0602698aebe3c1ad5addb50ba03ab801f2a66304c04440d31e691ced27']})
tests/test_verify_batch.py:109: AssertionError
```

## AFTER the fix
```
7 passed in 0.75s
188 passed, 1 skipped in 10.70s
```
