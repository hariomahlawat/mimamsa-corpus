# Regression evidence: fetch-time integrity enforcement (PR #17 review finding)

## BEFORE the fix (tests written first)
```
>       assert stats["downloaded"] == 0 and stats["failed"] == 1, stats
E       AssertionError: {'downloaded': 1, 'duplicate': 0, 'not_modified': 0, 'retry_later': 0, ...}
tests/test_fetch_integrity.py:39: AssertionError
>       assert stats["downloaded"] == 0 and stats["failed"] == 1, stats
E       AssertionError: {'downloaded': 1, 'duplicate': 0, 'not_modified': 0, 'retry_later': 0, ...}
tests/test_fetch_integrity.py:46: AssertionError
>       assert stats["downloaded"] == 0 and stats["failed"] == 1, stats
E       AssertionError: {'downloaded': 1, 'duplicate': 0, 'not_modified': 0, 'retry_later': 0, ...}
tests/test_fetch_integrity.py:53: AssertionError
>       assert stats["downloaded"] == 0 and stats["failed"] == 1, stats
E       AssertionError: {'downloaded': 1, 'duplicate': 0, 'not_modified': 0, 'retry_later': 0, ...}
tests/test_fetch_integrity.py:72: AssertionError
```

## AFTER the fix
```
6 passed in 0.37s
175 passed, 1 skipped in 7.52s
Real config: archive (ACQ-01) 12/12 and archive_acq02 16/16 queued entries carry pinned values enforced at fetch time; India Code entries are recorded only (download-specific bytes).
```
