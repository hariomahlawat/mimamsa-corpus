# Delta confirmation review: PR #46 blueprint fixes, c69eee41..ebeab659

- **Reviewer:** Fable 5.2 (`claude-fable-5-2`), independent confirmation review. Technical and documentary review only; **not legal validation**.
- **Reviewed:** `origin/claude/c12-blueprint-fixes` at `ebeab6590c23b95d85409d09c2008a2fdb12f553` (one commit on top of `c69eee41`). Delta only: 11 blueprint files changed, plus `REVIEW_CLOSURE_C12.md` and the copied review record. Documentation only. Read-only; nothing committed, pushed or posted.
- **Date:** 2026-11-24

## Verdict: ACCEPT

No open P1 or P2. F-01, F-02 and F-03 are closed. F-04 to F-10 hold. Four new P3 items and one INFO item are wording-level and do not block.

Counts for the delta: P1 0, P2 0, P3 4, INFO 1.

## 1. P2 closures

| Finding | Status | Closing text |
| --- | --- | --- |
| F-01 approval write path | CLOSED | Studio 3.3: "A *Legal Reviewer designation* is a recorded authorisation attached to a named, authenticated account. It permits exactly one additional class of action, recording legal review decisions within its stated scope. It must be backed by an `Appointment` record". "Admin capacity never confers it." Tiers: `T0_RESEARCH_ONLY`, `T1_LEGAL_ADVISER_REVIEWED`, `T2_FORMAL_JAG_VALIDATED`, with "An output class missing from the table is treated as requiring T2." Channels: signed release import, local Legal Reviewer decision, Admin transcription where "Recording is not approving. The record stays `APPROVAL_RECORDED_UNCONFIRMED`, and the gate does not count it". Decider: "**Only a Legal Reviewer** may dismiss a trigger as not credible or not material, lift a hold, or re-enable a blocked scope". |
| F-02 update channels | CLOSED | Architecture 9.1: "Verify the bundle manifest signature and every checksum offline before changing anything. Any failure rejects the whole bundle." "If a bundle contains bytes already uploaded locally, keep one `SourceCopy`, record both provenances". "Never auto-merge them." Item 5: uploaded legislation and judgments create candidate nodes that "never change the operative timeline used for definitive outputs until documentary and fidelity verification is recorded and, for edges with legal effect, a Legal Reviewer verifies them". Item 8: "Every bundle carries a change list ... Each entry ... is an impact trigger for Document Studio 8.1". |
| F-03 graph vocabulary | CLOSED | Architecture 5 adds `REPEALS_INSTRUMENT` / `REPEALS_PROVISION`, `OMITS_PROVISION`, `SUBSTITUTES_PROVISION_TEXT` / `INSERTS_PROVISION`, `RE_ENACTED_AS`, `COMMENCES`, `SAVES_OR_TRANSITIONS`, `IMPLEMENTS`, `SUPERSEDES_INSTRUMENT`; "The table is **not exhaustive**."; a mapping table for all corpus relation types; and "A corpus `human_verified` mark does not by itself amount to a Legal Reviewer approval." Architecture 7.1 adds TA-01 to TA-05. |

## 2. Requested checks

- **F-01 internally consistent:** yes. The designation is described the same way in Studio 3.3, Vision 2, PR-19 and 6, ADR-0002, ADR-0003, Architecture 4 and 8, Ingestion 2 and 3, Scenario engine 3, README and CLAUDE.md. It adds no research access, the two-role statements stand, and ADR-0002's matrix is unchanged. It is listed as blocking open decision 1 in ADR-0003, with the appointing authority, tier table, channels and edge reviewer as decisions 2 to 5.
- **No approval is claimed:** confirmed. Studio 3.3: "**No approval, appointment or approval artefact exists today**, and none is created by this document." ADR-0003, README and the closure table repeat it. The persona row reads "proposed; not yet appointed".
- **Fail-closed:** confirmed. Studio 3.3 lists six refusal conditions, and Studio 11 adds a test for each of the main ones (no appointment, unconfirmed transcription, Admin account, revision N versus N+1, T1 against a T2 class, revocation).
- **TA-01 to TA-05 are tests, not legal conclusions:** confirmed, with one exception (D-01). Section 7.1 says "These are representational tests, not legal conclusions" and "unverified until then"; TA-01 and TA-02 say "recorded as omitted"; TA-04 says "Do not treat the earlier judgment as wholly overruled unless a scoped ... edge is verified"; `RE_ENACTED_AS` says "Correspondence is not textual or legal equivalence".
- **P3 fixes F-04 to F-10:** all hold.
  - F-04: no stale "user-upload", "user-supplied policy", `USER_SUPPLIED_UNVERIFIED` or "local user documents" remains in the 12 files. `carrier_provenance=USER_SUPPLIED` is the policy's own value and is explained.
  - F-05: PR-10 and Studio 9.2 now use controlling event date(s) per constraint.
  - F-06: Architecture 6 has the two added dimensions, the reconciliation table and v1 fields on `SourceDocument`. One residual (D-03).
  - F-07: metadata-only audit log and backup exclusion stated in Studio 2, Architecture 11 and Ingestion 6.
  - F-08: Studio 9.2 refuses replay of withdrawn revisions; test added.
  - F-09: scope statement in Vision 1, README, Register 2, Studio 3 and ADR-0003.
  - F-10: the UC-24 to UC-28 subsection now sits under section 3; section 4 heading precedes its list.
- **INFO items:** F-11 and F-12 addressed. F-13 is still open: the cold-review record is not in the branch.
- **New contradictions across the 12 files:** none that affect behaviour. ADR-0001 is unchanged and remains consistent. The copied review record and CSV under `docs/product/reviews/` are byte-identical to the originals.

## 3. New findings

| ID | Sev | Statement | Location | Requested action |
| --- | --- | --- | --- | --- |
| D-01 | P3 | Section 7.1 says the case descriptions "come from the root `CLAUDE.md` brief". TA-05 names "Parashotam (Supreme Court, 2023)", and TA-04 adds "entitlement"; the brief names neither. A source of that name exists in the corpus (`C5-SRC-J-SC-2023-PARASHOTAM`) but its crosswalk rows are `PARTIAL_MATCH`, `NOT_REVIEWED`. The case identity is therefore an unverified assertion presented as coming from the brief. | Architecture 7.1, TA-04 and TA-05; closure table F-03 row | Use the brief's wording ("the 2023 SC ruling on High Court writs against AFT orders"), or cite the corpus source ID as an unreviewed candidate. |
| D-02 | P3 | For a local decision at T2, the tier table requires the formal approval artefact, but channel 2 says the decision is recorded "optionally with a scanned signed decision attached by hash". | Studio 3.3, tier table versus channel 2 | State that the attached artefact is mandatory for T2 on channel 2. |
| D-03 | P3 | The Studio 3 axis table still lists Legal approval values `RESEARCH_ONLY; LEGAL_REVIEWED; LEGAL_VALIDATED`, and Architecture 6 lists `NONE / REVIEWED / FORMALLY_AUTHORISED`. The new tiers T0 to T2 are not mapped to either set. | Studio 3 (line 50) and 3.3; Architecture 6 | Add a one-line mapping, or replace the older values with the tier names. |
| D-04 | P3 | The proposed default lets "definitive advisory routes" open at T1. EVIDENCE_STANDARD classes coercive and disciplinary powers, custody, punishments and court-martial as P0 critical. The default does not separate those subjects. It is labelled a proposal and is blocking decision 3, so nothing opens today. | Studio 3.3, tier defaults | Default P0-critical subject matter to T2, or note the point for the competent authority in ADR-0003 decision 3. |
| D-05 | INFO | When a bundle withdraws a source that was also published locally, "the Admin is prompted and the item is flagged until decided". Whether the item stays visible to ordinary users meanwhile is not stated. | Architecture 9.1 item 4 | Say which state applies while flagged. |

## 4. Limits of this review

Delta only; unchanged text was not re-reviewed. No code exists to test. Legal correctness of the tier defaults, credibility criteria and temporal cases was not assessed.
