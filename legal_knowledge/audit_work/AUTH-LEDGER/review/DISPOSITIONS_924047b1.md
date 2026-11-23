# Dispositions: independent Fable 5.2 review of 924047b1 (AUTH-LEDGER-02)

- **Review:** `fable_review_924047b1.md` and `fable_review_924047b1_findings.csv`, copied verbatim.
- **Reviewer:** a separate read-only agent (claude-fable-5-2, as it reported).
- **Verdict:** ACCEPT WITH CONDITIONS. There was no P1. The 3 P2 findings must be fixed before merge; there were also 10 P3 and 2 INFO findings.
- **Implementer:** Claude Opus 5.5.
- **Re-review:** the corrections are in the commit after 924047b1 and are submitted for an independent re-review.

| ID | Sev | Disposition | Where |
| --- | --- | --- | --- |
| F-01 | P2 | **Fixed.** git runs with a sanitised environment: every inherited `GIT_*` variable is dropped; `GIT_NO_REPLACE_OBJECTS=1`, `GIT_GRAFT_FILE=/dev/null`, no system or global config, `core.useReplaceRefs=false`. Verification fails closed if `refs/replace/*` or `info/grafts` exists. One test per vector: replace graft, grafts file, and an inherited `GIT_DIR`, `GIT_WORK_TREE`, `GIT_OBJECT_DIRECTORY`, `GIT_GRAFT_FILE` or `GIT_REPLACE_REF_BASE`. All are killed by mutation | `tools/binding.py`; tests `ReviewFixes02.test_f01_*` |
| F-02 | P2 | **Fixed; the finding was correct.** The builder now also reads the cited L5 R23 records: status `LOCATED_IMAGE_CHECKED`, a render hash, and the copy's own sha256. The matrix reports their image quotations with the limitation that they are not an identity-reference kind under rule 1. All 20 rows have the identifier read from the image, and the split is now **18 ready / 2 born-digital held**. `TRANCHE1_FINDINGS.md` carries a correction note; the decision pack (B) and the readiness note are corrected | `tranches/tools/build_tranche1.py`, `tranches/T1-GAZETTE/*`, `RULE_DECISION_PACK.md`, `C7-PREP/WORKSTREAMS_READINESS.md` |
| F-03 | P2 | **Fixed, partly by correction and partly by tightening.** Tightened: archive.org locators may not carry a query; a trailing-slash directory path is rejected on every class. Corrected: `urlcheck.py`, D-12 and decision pack C now list what is still not canonicalised (`@` versus `%40`, query order, path aliases such as `/details/` versus `/download/`). Recommendation C is restated: adopt C2 with the archive.org item alias as its first entry; 10 items appear in both forms (`RULE_DECISION_PACK_data.json`) | `tools/urlcheck.py`, `tools/strength.py`, `DESIGN_NOTES.md`, `RULE_DECISION_PACK.md` |
| F-04 | P3 | **Fixed.** The whole ledger package tree must be identical at `reviewed_head` and at the merge. The remaining residual (code outside the package) is stated in `APPROVAL_CONTROLS.md` | `tools/binding.py`; `test_f04_*` |
| F-05 | P3 | **Fixed.** Bound transitions carry `binding_assurance` (git `VERIFIED_OFFLINE`; GitHub review `ASSERTED_NOT_VERIFIED_OFFLINE`). `APPROVAL_CONTROLS.md` says a local merge with invented review values passes the git checks, and that only O-2 makes a merge imply a review | `tools/ledger.py`; `test_f05_*` |
| F-06 | P3 | **Fixed.** A bare `gov.in` or `nic.in` host is rejected. Directory paths are rejected. Court locators must match the path shapes of all 17 committed api.sci.gov.in locators. An explicit host list for the government-hosted scan class is left to the owner: any `*.gov.in` or `*.nic.in` host remains acceptable, with a first-class record carrying the copy's own sha256 still required | `tools/strength.py` (`COURT_PATH`); `test_f06_*` |
| F-07 | P3 | **Fixed.** Decoded path and query must be strict UTF-8 with no Cc, Cf, Cs, Co, Cn, Zl or Zp character, no Zs other than space, and no NFKC change. Segments that are dots plus spaces are rejected. All failures give explicit reasons | `tools/urlcheck.py` (`_decoded_problem`); hostile list |
| F-08 | P3 | **Fixed.** A URL taken from free text must be the whole whitespace-delimited token, apart from trailing `,;|)`; otherwise it is refused | `tools/strength.py` (`_untruncated`); `test_f08_*` |
| F-09 | P3 | **Fixed as a lint.** Letter boundaries catch `Fable5`, `claude_code`, `GPT4` and `ai-assistant`. It is documented as over-inclusive and as a guard, not an identity control; O-4 together with O-1 is the identity route | `tools/ledger.py` (`AGENT`); `APPROVAL_CONTROLS.md` |
| F-10 | P3 | **Fixed.** `version` and `rule_version` must be exactly `int`, not bool or float. The line date must match `YYYY-MM-DD` and be a valid date; `20261123` is rejected | `tools/ledger.py`; `test_f10_*` |
| F-11 | P3 | **Fixed for the named survivors.** New tests cover: wrong scope; wrong declared record hash; `urlcheck.problem()` alone on bad hosts and on `%3F`, `%23`, `%2F`, `%25`; a genesis line with content. The BIND line carrying records was already tested. A mutation run on the 16 new controls of this round killed 14. The 2 survivors were closed: a redundant clause removed, and a date test added | tests `ReviewFixes02*` |
| F-12 | P3 | **Fixed.** The prepared rows use neutral S.R.O. 34 wording; the frozen C5 and C6-01 texts are unchanged. The identity, structural-only and identifier limitations are now in the `limitations` column. Text truncation in the matrix is removed. The born-digital text-layer search is limited to the page-1 excerpt held in the evidence; this is recorded, and no new extraction was made | `tranches/tools/build_tranche1.py` |
| F-13 | P3 | **Fixed.** A2 now counts 2 newly ineligible, and 4acdb1a8 is re-pointable to `ACQ02-03` (computed). The A3–B2 dependency (Navjot) is stated, and P-A becomes "A3 only with B2". The "newly eligible" columns are added to B and C. Anchor effects are reproduced by the reader in `simulated_joint_impact.json` and in the AUTH-LEDGER-01 tests | `tranches/tools/policy_impact.py`, `RULE_DECISION_PACK.md` |
| F-14 | INFO | **Recorded.** Withdrawals and corrections are staged until their BIND line. Snapshots must ship a git bundle with full history. Whether demotions should take effect at once is an owner decision (O-5 below) | `APPROVAL_CONTROLS.md` |
| F-15 | INFO | **Fixed.** The top-level label must be alphabetic, so `1.0x7f` is rejected. The git-version dependency of `GIT_NO_LAZY_FETCH` (2.44 and later) is noted; `protocol.allow=never` is the operative block | `tools/urlcheck.py`, `tools/binding.py`, `APPROVAL_CONTROLS.md` |

**New owner decision O-5.** Should a WITHDRAW, or a demoting CORRECTION, take effect immediately, before its BIND line, on the basis that withdrawing evidence is never less safe than keeping it? The current behaviour stages every version; that is conservative for promotion, but delays demotion.

**Unchanged by these corrections:**
- version zero (genesis line, HEAD, and the four Cycle 5 outputs byte-identical);
- the rule-1 outcome of every one of the 32 drafts;
- all protected paths.

No entry was approved.
