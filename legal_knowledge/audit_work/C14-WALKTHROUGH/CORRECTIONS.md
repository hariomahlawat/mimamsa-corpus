# Corrections after independent review (Codex, PR #64 at 8f369796)

The original evidence is preserved unchanged in `evidence/original/`:
- `search_raw.v1.json`
- `SEARCH_EVALUATION.v1.json`
- `walkthrough_observations.v1.json`

## C1: withdrawal citation probe sent `sha=undefined` (Codex P2, accepted)

**Defect.** In J13 the copy hash was parsed from a response body that `api()` had already cut to 160 characters. The hash was therefore `undefined`. The recorded `/api/cite` answer, `CITED_COPY_UNAVAILABLE`, came from a malformed request, not from withdrawal enforcement, so it did not validate that route.

**Fix.** `scripts/walkthrough.cjs`, J13:
- The hash is now read from the full `/api/documents/{id}` JSON (`copy.sha256`, first 12 characters).
- It is cross-checked against the permalink captured from the UI.
- The same `/api/cite` call is made before and after withdrawal.

**Re-run.** J13 only, on a fresh clone `mimamsa_b1_audit` (re-created from `mimamsa_b1`), at the same commit and release:

| Probe | Before withdrawal | After withdrawal |
| --- | --- | --- |
| Copy hash: metadata vs permalink | `35b9c948fe62` = `35b9c948fe62` | — |
| `/api/cite` with the real hash (positive control) | 200 `CITED_COPY_ELIGIBLE`, doc and page returned | 200 `CITED_COPY_UNAVAILABLE`, no doc, page or hash |
| `/api/documents/{id}`, `/v2/…/pdf-meta` | 200, 200 | 404, 404 |
| `/api/cite` with `sha=undefined` (negative control) | 200 `CITED_COPY_UNAVAILABLE` | — |

**Conclusion.** Withdrawal enforcement on `/api/cite` is now shown by a valid before/after pair. The negative control confirms that the original v1 observation was uninformative. No finding changes: F05 concerns the open viewer and the deep link, and both behave as originally recorded in the re-run.

## C2: server timing read from a non-existent field (Codex P2, accepted)

**Defect.** `scripts/search_eval.py` read `run.ms`. The API returns `run.elapsed_ms` (`Api.cs` `SearchDto`). All 43 v1 observations therefore had `server_ms: null`.

**Fix.** The script now reads `run.elapsed_ms`.

**Re-run.**
- All 43 queries were re-run on the commissioned instance (same commit, release and database).
- `evidence/search_raw.json` and `SEARCH_EVALUATION.json` were regenerated.
- **Top-five documents and totals are identical to v1 for all 43 queries** (0 differences), so every assessment and count stands: 24 pass, 8 partial, 10 fail, 1 not determinable.
- Server time now ranges from 0.5 ms to 173 ms. The highest value is the first query after the service restart.
