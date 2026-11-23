# Proposals for owner decision: archive.org metadata access (C6-02) and a narrow scope extension (C6-04)

Neither proposal is implemented. Both need explicit owner approval, and neither changes CLAUDE.md, the crawler, the crawler config or the guarded runner in this PR.

## P-C6-02-META: pin the two DPP Amendment Act 2000 items from archive.org metadata
**Authorisation basis for these requests (Fable F-26):** the owner's Cycle 6 closeout instruction (Part VI item 12.1) asked for the missing integrity pins to be completed, with no downloads. The requests were metadata-only, made through the Cycle 5 guarded discovery runner (robots first; HEAD before any GET; no redirects followed; no document body). No GET other than robots.txt was made. No further request has been made since.

**Facts (2026-11-23, `discovery/c6_02_metadata_requests_v2.tsv`):**
- archive.org robots.txt was read (RULES_PARSED).
- `https://archive.org/metadata/<id>` answers HEAD with 405 (text/html), so the runner's HEAD-first rule refused the GET.
- `https://archive.org/download/<id>/<id>_files.xml` redirects (302) to a `dn*.archive.org` data node. That node has no robots.txt (404) and its HEAD gives no content type, so the GET was refused.
- No GET other than robots.txt was made.

**Proposed narrow rule** (a change to `SOURCE-LIBRARY-C5/tools/discovery_guard.py` in a separate reviewed PR):
- **Scope.** Allow a GET without a 200 HEAD **only** for URLs matching `^https://archive\.org/metadata/[A-Za-z0-9._-]+$`, after archive.org robots is RULES_PARSED and allows the path. Every GET-response gate stays: status 200; `application/json`; no attachment; identity encoding; 1 KiB prefix check; 2 MB cap.
- **No redirects.** Redirects are not followed for this route.
- **Use of the result.** The JSON is used only to read `files[]` `name`, `size`, `md5` and `sha1` for the named PDF. The pin is recorded with the request-log row as evidence.
- **Tests.** Mocked tests cover:
  - HEAD 405 then GET JSON is allowed;
  - a non-matching URL is refused;
  - a JSON body that is actually a PDF is refused by the prefix gate;
  - a redirect is not followed;
  - robots disallow wins.
- **Alternative rejected: acquire unpinned.** It is not acceptable; the brief requires proper verification.

**Approval needed:** owner decision C6-02-D1, then a reviewed guard PR, then a logged run.

## P-C6-04-SCOPE: narrowly scoped extension for named administrative publications
**Current scope (CLAUDE.md):** out of scope for this phase are "internal policy letters, Army Orders, SOPs and anything not publicly published".

**Proposed extension** (CLAUDE.md is edited only by the owner, or on the owner's explicit instruction):
- **Named publications only.** Allow *custodian-route requests* for exactly these:
  - Regulations for the Army 1987 (Vols I and II) with amendment and correction slips;
  - RA 1962;
  - RMSAF 2010 and 1983;
  - AO 45/2001;
  - AO 13/2006/PS;
  - the D&V Staff Officers' Handbook (May 2014).

  The Army Orders that ten records cite by category are added only after the owner names them.
- **Conditions:**
  1. Received through an authorised custodian, never a third-party upload.
  2. The printed access marking is recorded on receipt. Anything marked restricted (for example For Official Use Only) stays in a private store, is excluded from any public or HF export, and is ingested only with a further owner decision.
  3. Guidance (the handbook, policy letters) is tagged GUIDANCE and never substitutes for the Act, Rules or Regulations it cites.
  4. Each cited reference is checked against the governing instrument before any knowledge-base use.
- **Kept out of scope:** SOPs, internal policy letters not named here, and any bulk collection of Army Orders.
- **No correspondence** until the owner approves the request text (A-C5-3).
