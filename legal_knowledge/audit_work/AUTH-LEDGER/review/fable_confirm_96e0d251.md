# AUTH-LEDGER-01 focused confirmation of 96e0d251 (RESEARCH ONLY; not a sign-off)

**Verdict: ACCEPT.** N-01 (P2) is fixed without reopening F-09; N-02, N-04, N-05 and N-06 are fixed; N-03 is fixed for the cases I raised, with one latent P3 left (C-01). No P1 or P2 is open. This is a technical opinion on the validator and version zero only; it approves no ledger entry and does not stand in for the owner, the legal adviser or JAG.

Reviewer model: Fable 5.2 (`claude-fable-5-2`).

## Method
- Commit `96e0d251cdaa41f6c2a4bfee77a60a49a2b54336`, diff from `2e2df5ce` (9 files).
- In the repository, read-only: `auth_ledger.py verify` exit 0 (`HEAD 0 443c4bdf...`); 96 unit tests OK.
- Probes (`scripts2/c1.py`), the exec-order probe and an 86-mutant run (`scripts2/mut.py`) on a `git archive` export, removed afterwards. `git status --porcelain` empty before and after. No network.

## Status
| ID | Sev | Status | Evidence |
| --- | --- | --- | --- |
| N-01 | P2 | FIXED | R1 (ADD; WITHDRAW to pending; CORRECTION to documented) and R2 (ADD; WITHDRAW to unknown; new ADD) build at HEAD and as of version 2. F-09 stays closed: S1b (Isaac baseline withdrawn, claimed PROVENANCE_UNKNOWN, derived PENDING) is rejected as the latest event, also when a WITHHELD entry or an entry on another sha256 follows; WITHDRAW of a CORRECTION and foreign copy/source ids are rejected. Mutants "check every withdrawal" and "check none" are both killed. |
| N-02 | P3 | FIXED | Tampered builder re-pinned in frozen_inputs.json: verify and build exit 2 and the injected line did not run (no marker file). sys.path holds no frozen-tool directory after a full session. |
| N-03 | P3 | FIXED for the cases raised; residual C-01 | web.archive.org, http, archive.org/metadata and archive.org userinfo are refused. All 32 drafts pass the host rule. |
| N-04 | P3 | FIXED | 'A. Owner' versus 'A Owner', dates 9999-99-99 and 2026-02-30, and an indented capitalised duplicate 'Decision:' key are rejected. decisions/README.md states the limits. |
| N-05 | P3 | FIXED | Zero-entry file with a foreign header, kind L6 on a WSB row, the old C6-01 T reference and another copy's T reference are rejected. |
| N-06 | P3 | FIXED | WORKSTREAMS_READINESS.md now says "If the owner adopts policy B2 ...; rule 1 currently accepts them (B1)". |
| F-06 residual | P3 | FIXED | 84 of 86 mutants killed. Survivors: M11 (the ledger-side frozen_inputs check, now masked by the earlier reader-side check, whose own mutant is killed) and the T-reference resolve call (redundant with the exact-string check and the text-identity test). Both are redundant controls, not untested behaviour. |

## Version zero and the drafts
- Inert and byte-identical: the four registers equal Cycle 5 (cmp); ledger/, effective/, frozen_inputs.json, schema/ and evidence/ are unchanged since 2e2df5ce; frozen directories, C6-01 and C6-PREP are unchanged since 939a128a; ledger/ holds only HEAD and manifest.jsonl; decisions/ holds only README.md.
- All 32 drafts are accepted individually and jointly (case EXACT_ANCHOR 6 to 13 under synthetic approval). None is active.

## New findings
| ID | Sev | File and line | Evidence | Consequence | Recommended correction |
| --- | --- | --- | --- | --- | --- |
| C-01 | P3 | AUTH-LEDGER/tools/strength.py:31-43 | Userinfo is refused only for archive.org. `https://x.gov.in@evil.example/x` suits the government-hosted class and `https://api.sci.gov.in:pw@evil.example/x` suits PRIMARY_OFFICIAL_COURT_COPY, because the pattern stops at '@' or ':' without requiring '/', '?', '#' or end of string next. `https://archive.org/download/../web/x` also passes. The disposition says "Userinfo is refused". No such URL is in the pinned registers and URLs cannot come from an entry. | Latent; needs a future pinned record with such a locator. | Require the host to be followed by an optional numeric port and then '/', '?', '#' or end; reject '..' path segments. |
| C-02 | INFO | tests/test_legal_audit_auth_ledger.py (entry_from_draft) | The drafts pass only after their T references are rewritten from the C6-01 path to `T:AUTH-LEDGER/evidence/copy_facts.csv#<copy_id>`; the literal draft reference is rejected. | Expected: the specification has the draft converted once by a reviewed PR. The conversion PR must make this substitution. | None. |

## Not checked
Held binaries, signatures, source authenticity or currency, any legal proposition, Python versions other than 3.13.18, and the canonical Hugging Face snapshot (coverage against it unknown). Earlier-closed findings F-01 to F-05 and F-07 were not re-probed individually beyond the 96 tests, the mutation run and the draft acceptance check.
