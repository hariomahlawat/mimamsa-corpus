# C13-A7 review dispositions (coordinator, Cycle 13)

Source review: `reviews/review_c13_a7_84e10767.md` (independent; ACCEPT WITH CONDITIONS). This record changes **no crawler configuration**. Everything under `proposed/` stays a proposal and is not applied.

| ID | Sev | Disposition |
|---|---|---|
| F01 | P1 | **CLOSED in staging.** PR #51 (merged at 9ed152af) removed aftjabalpur.in from allowed_hosts, added it to blocked_hosts, and added the code-level `NEVER_CONTACT` backstop. |
| F02 | P2 | **CLOSED** by the same PR #51 (`crawler/config.py` NEVER_CONTACT plus test). |
| F03 | P2 | **ACCEPTED: patch 0003 is not integrated.** It bundles TLS trust (`ca_extra_pem`), redirect_scopes, From-header behaviour, require_https and fetch integrity. It needs its own review and owner approval before adoption. F07 must be fixed first. |
| F04 | P2 | **ACCEPTED RETROACTIVELY as a recorded process deviation.** The egazette pinned-intermediate configuration was used before acceptance, for 47 requests and 17 preserved files. Verification was not weakened: the chain validates to ISRG Root X1, partial-chain trust was cleared, and CERT_REQUIRED was set. The files stay preserved, with identity verified by hash. No re-fetch is required. The configuration itself stays unadopted (F03). |
| F05 | P3 | Recorded. One diagnostic egazette request was made with partial-chain trust on (robots.txt only). It must not recur; diagnostics must never weaken verification. |
| F06 | P2 | **OPEN.** 20 observed-redirect archive.org hosts have no probe evidence. redirect_scopes is not adopted until they are probed (F03). |
| F07 | P3 | OPEN. This is a precondition for adopting 0003: reject percent-encoded dot segments, and normalise paths before prefix matching. |
| F08 | P3 | Recorded. DESW "exact URLs" is enforced by the source type, not the allow-list. Any allow-list change for DESW needs path pinning. |
| F09 | P3 | Accepted as benign. The two pin mismatches are derivative "Text PDF" files; the originals are identified. |
| F10 | P3 | Recorded. The reviewer's all-page marking scan of the 63 files found no access marking. |
| F11 | P3 | Recorded. HF 9e3cf986 also made an automatic, additive `.gitattributes` change (+44 LFS lines). |
| F12 | P3 | Deferred to A9. The 11 legacy `scripts/*.py` should be retired or routed through the allow-list. None of them targets aftjabalpur.in. |
| F13 | P3 | Recorded. The frozen C12 snapshot is unchanged. Tools that read it subtract NEVER_CONTACT. |
| F14 | P3 | Deferred to A9: add a push trigger for crawler-security-ci and pin pytest. |
| F16 | P3 | Deferred: log a `from_header_sent` flag per request. |

## Disposition of the earlier acquisition PRs (A7 PR review)

These are recommendations only. No PR was closed or merged by this record. Each needs owner action or a separate approved scope.

- **PR #7:** superseded by PR #51 in staging.
- **PR #8:** revise. The archive.org wildcard should become item-scoped entries.
- **PR #9:** revise. DESW needs path-pinned exact URLs.
- **PR #17:** close as superseded. Its 16 items are byte-identical to the corpus.
- **PR #23:** revise.

Download runs for these configurations still need owner approval.
