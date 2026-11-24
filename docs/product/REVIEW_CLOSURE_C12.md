# Review closure: C12 confirmation review of the product blueprint

**Recorded:** 2026-11-24  
**Review closed:** Fable confirmation review of PR #46 at `c69eee41` (ACCEPT WITH CONDITIONS; P1 0, P2 3, P3 7, INFO 3).  
**Status:** Documentation changes only. Nothing here creates a legal approval, appointment, approval artefact, verified source or legal conclusion. The Legal Reviewer path is a **proposal and a blocking open decision**; until it is confirmed, the operational-use gate fails closed.

| Finding | Sev | Change | File / section |
| --- | --- | --- | --- |
| F-01 | P2 | Defined a proposed legal-approval path: a recorded **Legal Reviewer designation** that is not a third access role and is backed by an `Appointment` from the competent authority. Admin capacity never records approval. Added approval tiers T0 to T2 that separate the designated legal adviser from formal JAG validation, a tier-requirement table with fail-closed defaults, three artefact channels (signed release import, local Legal Reviewer decision, Admin transcription that stays unconfirmed until confirmed; recording is not approving), revision-pinned approvals, and fail-closed conditions. Marked the review workspace as deferred and operated by the Legal Reviewer. Listed blocking open decisions. Stated that no approval exists today. | Document Studio 3.2, **3.3 (new)**, 8.1, 11 (approval-path test); Vision 2 (persona rows), PR-19, PR-28, 6 (Legal review workspace); ADR-0002 "Not decided"; ADR-0003 decision 11 and "Blocking open decisions"; Architecture 4 (`Appointment`), 8; Ingestion 2 steps 10 and 11, 3 (`ReviewRecord`); Scenario engine 2 step 6; Use cases 4; README; CLAUDE.md (review corrections paragraph) |
| F-12 | INFO | Criteria for "credible" and "material" triggers, automatic blocking rule, precautionary hold, and the Legal Reviewer as sole decider for dismissal and re-enabling. | Document Studio 3.3 ("Who judges credible material"), 8.1; Ingestion 2 step 11; Scenario engine 8 |
| F-02 | P2 | Added release/local reconciliation: atomic signed import verification, SHA-256 identity and aliasing, collision handling (no auto-merge), precedence, a route from local amending Acts and judgments to **candidate** `ProvisionVersion`/`Judgment` nodes (verified only on documentary checks plus Legal Reviewer verification, on site or by signed release), deterministic edge re-derivation, revision-pinned approvals and bindings, and change lists as impact triggers for 8.1. | Architecture **9.1 (new)**, 9; Ingestion 2 steps 10 and 12 (new), 7 (two tests); Document Studio 8.1; ADR-0002 |
| F-03 | P2 | Added edge types `REPEALS_INSTRUMENT`/`REPEALS_PROVISION`, `OMITS_PROVISION`, `SUBSTITUTES_PROVISION_TEXT`/`INSERTS_PROVISION`, `RE_ENACTED_AS`, `COMMENCES`, `SAVES_OR_TRANSITIONS`, `IMPLEMENTS` and `SUPERSEDES_INSTRUMENT`. Stated that the table is non-exhaustive. Mapped the corpus relation types (`amends` … `implements`), corpus confidence values and corpus status enum onto the graph. Added named temporal acceptance cases TA-01 to TA-05 (ss.75–76; s.127; IPC/CrPC/Evidence Act to BNS/BNSS/BSA from 1 July 2024; Dharamvir on the 1982 Rules versus later authority on the 2008 Rules; Parashotam 2023) as representational tests, with facts to be taken from verified sources. | Architecture 5, **7.1 (new)**; Document Studio 4.1; Scenario engine 8 |
| F-04 | P3 | Replaced stale user-upload wording with Admin-upload or working-document wording. Settled on one display label, `ADMIN_PUBLISHED_UNVERIFIED`, backed by policy v1 fields. Limited "edit" to metadata and template definitions. | CLAUDE.md (line formerly 184); Vision PR-12; Architecture 5 (`UPLOAD_REFERENCES_PROVISION`); Ingestion 4; Document Studio 2 table; Use cases 4; README reading list |
| F-05 | P3 | PR-10 now refers to controlling event date(s) per constraint. Section 9.2 stores controlling dates and the date basis per constraint. | Vision PR-10; Document Studio 9.2 |
| F-06 | P3 | Added Publication and Dependency-freshness dimensions, a single vocabulary reconciliation table mapping Architecture 6, Studio 3 and Ingestion 4 to policy v1 fields, a rule that recurring statuses are qualified by axis, and v1 fields with initial values on `SourceDocument`. | Architecture 6; Ingestion 3, 4 |
| F-07 | P3 | Audit log holds metadata only. Working-session data is excluded from backups by default, or kept under the same ownership, retention and deletion rules. | Document Studio 2; Architecture 11; Ingestion 6 |
| F-08 | P3 | Section 9.2 now says replay is refused for withdrawn or ineligible revisions, with the identifiers listed and no withdrawn text shown. Added a test. | Document Studio 9.2, 11 |
| F-09 | P3 | Scope statement: tri-service statutes, the AFT Act and IPC/CrPC/Evidence Act with BNS/BNSS/BSA are the target; the pilot is Army-first; narrowing needs an ADR. | Vision 1; README; Form register 2; Document Studio 3; ADR-0003 outstanding decisions |
| F-10 | P3 | Moved the UC-24 to UC-28 subsection above the section 4 heading and fixed the trailing bullet punctuation. | Use cases 3 and 4 |
| F-11 | INFO | Marked the C10 figures and the outcome-error statement as reported in C10 records that are not on this branch's base. | Architecture 2; Vision 5 |
| F-13 | INFO | Not addressable in these docs: the cold-review record should be committed by the coordinator alongside the review records. | None |

## Delta confirmation (Fable 5.2, `claude-fable-5-2`) of c69eee41..ebeab659: **ACCEPT**
No open P1 or P2. F-01, F-02 and F-03 are closed; F-04 to F-12 hold. The record is in `reviews/fable_review_pr46_delta.md`.

**Deferred P3s** (wording only; no behaviour depends on them):

| ID | Disposition |
| --- | --- |
| D-01 | Follow-up. In TA-04 and TA-05, use the brief's wording, or cite the corpus source as an unreviewed candidate. |
| D-02 | Follow-up. Make the signed decision mandatory for T2 in channel 2. |
| D-03 | Follow-up. Map the older approval-value vocabularies (Studio 3, Architecture 6) onto T0–T2. |
| D-04 | Follow-up, under blocking decision 3. The proposed T1 default must exclude the P0-critical subjects: punishment, custody and court-martial. |
| D-05 | Follow-up. Define visibility while a withdrawn source is "flagged until decided". |

**Still open:**
- **F-13.** The original cold-review record is still not in the branch; its author should add it.
- **Owner decision.** Whether to confirm the Legal Reviewer designation (ADR-0003, blocking open decision 1).
