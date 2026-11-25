# 01. Personas and workflows

Personas are design tools, not access tiers. There are exactly two roles, **Admin** and **User**; three of the four personas below are Users. The **Legal Reviewer** is a designation on an existing account and is inactive in Cycle 13; no persona can record a legal approval.

## 1. Personas

### P-CDR Unit commander (User)

- **Context:** time-poor, not a lawyer; asks about situations, not sections (UC-01..UC-20). Uses a shared office desktop at 1366×768 or 1920×1080, sometimes a tablet.
- **Needs in Cycle 13:** find the relevant Act/Rule text and a few relevant judgments quickly; see clearly what is verified and what is not; know when to escalate to a legal adviser.
- **Risk to design against:** reading candidate data as settled law. Countermeasures: candidate chips, banner, no summaries, no generated conclusions.
- **View:** commander presentation (CAP-CA-04): fewer facets, larger excerpts, provenance always visible. The assistant itself is gated off.

### P-LEG Legal practitioner / JAG officer (User)

- **Context:** reads full judgments, compares versions, needs pinpoint citations, adverse authority and amendment history (PR-02, PR-07, PR-10).
- **Needs:** precise search (identifiers, phrases), open-at-page, copy citation with page and copy hash, statute explorer with amendment footnotes, cited/citing lists, notes. Works for hours; 1920×1080 or 2560×1440, often two monitors.
- **Risk:** over-trusting extracted outcomes or edges. Countermeasure: measured precision shown beside every candidate; "not evaluated" when unmeasured.

### P-RES Research officer / content reviewer (User or Admin)

- **Context:** builds research sets, checks extraction quality, proposes corrections through ordinary channels (PR-14).
- **Needs:** provenance and evidence panels, alternate copies, OCR quality flags, saved searches, export of citations.

### P-ADM Admin (Admin)

- **Context:** maintains the library (PR-16, PR-17): uploads, reviews staging, publishes, withdraws, imports signed release bundles, manages accounts, watches backups.
- **Needs:** a clear staging queue, side-by-side original vs extracted text, OCR confidence per page, eligibility decision with recorded basis, restricted-material rejections by id, release verification report, audit log.
- **Risk:** mistaking publication for legal approval. Countermeasure: publish dialog states "Publication makes the document visible to all users. It is not legal approval."

## 2. Key workflows (Cycle 13 scope)

| ID | Persona | Workflow | Steps | Capabilities |
| --- | --- | --- | --- | --- |
| W-01 | CDR, LEG | Find by situation words | Type plain words in search → hybrid results with excerpts → filter by document type → open Act section or judgment at page | CAP-US-01, -03, -04, -05, -06 |
| W-02 | LEG | Find by identifier | Type "s.69 Army Act" or "OA 123/2019" → parsed chips show interpretation → exact matches first | CAP-US-02 |
| W-03 | LEG | Read and cite a passage | Open judgment → jump between hits (F3 / Shift+F3) → select passage → Copy citation (doc id, copy sha256 prefix, page, para if printed, release id) | CAP-US-06, CAP-RW-04 |
| W-04 | LEG, RES | Check what is known about a judgment | Metadata header with per-field origin chips → evidence panel (seven axes) → provenance panel → proceedings and copies | CAP-JI-01, -02, -06, CAP-RW-05 |
| W-05 | LEG | Look at candidate outcome | Outcome chip "candidate · P 91.3% · cov 64.8% (V3, not human-checked)" → popover with report link and restriction | CAP-JI-03 |
| W-06 | LEG | Explore a section | Statute workspace → TOC → section → amendment strip (candidates; "temporal chain not established") → related judgments | CAP-SE-01, -02, -04, -05 |
| W-07 | LEG, RES | Explore connections | From a judgment, open graph → expand neighbours → filter edge types → click edge → evidence passage | CAP-KG-01..05 |
| W-08 | RES | Keep research | Pin passages, add private notes, save a search, build a research set | CAP-RW-03, -07 |
| W-09 | ADM | Add a source | Upload → automatic checks → staging review (original, text, OCR flags, metadata candidates, suggested links, eligibility) → publish or reject | CAP-KA-01, CAP-KG-06 |
| W-10 | ADM | Withdraw a source | Find → Withdraw (reason required) → confirmation shows it disappears from search for everyone | CAP-KA-01, CAP-US-07 |
| W-11 | ADM | Import a release | Choose bundle folder → verification report (signature, checksums, compatibility, restricted register, records) → import to new generation → smoke queries → switch; rollback available | CAP-KA-02, -03 |
| W-12 | Any | Work on a private file (B3) | Document Studio → new session → upload → view/OCR/annotate → export; session expires | CAP-DS-01, -05 |
| W-13 | Any | Meet a closed gate | Opens Commander assistant or a legal-rule feature → gate notice explains what must happen (appointment, approvals) and links to research search | CAP-CA-01, CAP-DS-03 |

## 3. Workflow acceptance (usability walkthrough)

Ten scripted tasks run by a reviewer who did not design the screens: W-01, W-02, W-03, W-04, W-05, W-06, W-07, W-09, W-10, W-13. Record completion, time, errors and whether the reviewer correctly stated the evidence state of what they found. A task "passes" only if the reviewer also identifies candidate data as candidate.
