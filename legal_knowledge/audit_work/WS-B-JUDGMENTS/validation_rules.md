# WS-B intake validation rules (judgments)

These are the rules WS-B applied to the intern's judgment intake (`origin/raw-data` at `ad77758d4569ba6aafa955cc7843d874489e10f7`). Run the same rules on every later delivery. To reproduce: `tools/build_registers.py` (for V1 to V9) and `tools/manual_registers.py` (for the hand-reviewed rows).

## V1. Read-only intake
- Extract with `git archive <commit> data/meta data/text data/excluded_judgments.jsonl | tar -x -C <scratch>`.
- Never check out the branch over a worktree. Never edit `data/**`.
- Record the commit SHA in `intake_stats.json`.

## V2. Document identity is the SHA-256 of the raw bytes
- One `intake_manifest.csv` row is one distinct `sha256`.
- Records that share bytes are collapsed into that row, with all their `doc_id`s listed. Two kinds occur:
  - **SC year-folder duplicates**: the same e-SCR record filed under both the decision year and the report year, with the same `record_id`.
  - **HC common judgments**: one PDF that decides many connected case numbers.
- A different SHA with the same neutral citation is flagged `SAME_NEUTRAL_CITATION_OTHER_BYTES`. It is not merged automatically.
- Different SHAs with the same eCourts `record_id` are separate orders in the same case, with different dates. They are kept apart.

## V3. Carrier is not authority (policy v1)
- Every intern judgment comes from the AWS Open Data buckets (CC-BY-4.0, maintained by a third party), not from a court host.
- Each row is classified as follows:
  - `document_authority = OFFICIAL_JUDICIAL_DECISION`
  - `carrier_provenance = THIRD_PARTY_ARCHIVAL_FACSIMILE`
  - `copy_fidelity = HASH_ONLY`
- The intern `sha256` proves the integrity of the mirror bytes only. It is never a court-copy SHA.
- SC mirror copies are SCR reports. Their first page(s) carry an **editorial headnote**, which is not evidence of a holding (rule V8).

## V4. Independent lexical re-check (lead only, never a relevance determination)
The re-check uses word-boundary, case-insensitive matching on whitespace-normalised text. It counts four kinds of term:

- **Strong**: Army/Air Force/Navy Act, Armed Forces Tribunal, AFT, AFT Act, court(s)-martial, summary of evidence, Entitlement Rules, release/invaliding medical board, Army Rules, Pension Regulations for the Army/Air Force/Navy, Regulations for the Army, AFSPA.
- **Weak**: invalided, disability pension.
- **Service context**: army, navy, air force, ranks and their abbreviations, ex-servicemen, armed forces and similar terms.
- **CAPF markers**: BSF, CRPF, ITBP, CISF, SSB, Assam Rifles, police.

Each document gets one class:

| Class | Rule |
| --- | --- |
| `MIL_CORE_LEXICAL` | at least 1 strong term, plus at least 1 service-context term or at least 3 strong terms |
| `MIL_PROBABLE_LEXICAL` | at least 1 weak term and at least 3 service-context terms |
| `CAPF_OR_OTHER_FORCE_LEAD` | at least 1 military term, but CAPF markers outnumber service-context terms |
| `WEAK_SIGNAL_REVIEW` | any other military term |
| `NO_MILITARY_SIGNAL` | no military term |
| `TEXT_UNAVAILABLE` | no text |

The class decides the intake decision:

- `INCLUDE`: the document is core or probable, or it is a reviewed identity match for a curated or cited case.
- `HOLD_FOR_REVIEW`: weak signal, CAPF, no text, or the intern says `relevant`/`not_checked` while WS-B finds no signal.
- `EXCLUDE_PROPOSED`: everything else. The intern's corpus is never changed by this decision.

## V5. Known intern-filter defects to test for
- `pipeline/judgments.py` counts the keyword "invalided" also on `\binvalidation\b`. Documents kept only through that word are flagged `INTERN_HIT_ONLY_VIA_INVALIDATION`. They are mostly civil and customs matters (for example, notices held invalid).
- A "no keyword" removal can drop precedents that the KB relies on (L. Chandra Kumar 1997; S.R. Dhingra 2007). Every delivery must be checked against an allow-list of cited precedents: the 53 curated cases plus the cases cited by the KB's 87-code register. Use `identity_resolution.csv` (column `intern_excluded_log_hits`).
- Relevance counts must be reported with their denominator and snapshot. Counts that differ from `PROGRESS.md` go to `open_questions.csv`.

## V6. Identity matching (curated case to intern document)
- A party-name regex is a **lead** only.
- A match is accepted (`COVER_PAGE_READ`) only after a person or agent has read the cover page of the intern text and confirmed the parties and decision date, plus the case number where it is printed.
- Fuzzy title or year similarity is never identity.
- An official court copy counts as `ISSUING_AUTHORITY` only when its SHA-256 equals the bytes actually held. The URL and SHA are recorded in `tools/held_copies.csv`.
- Disagreements (dates, spelling such as Baltit/Baljit, missing curated fields) are written into `discrepancies`. The curated row is never changed.

## V7. Pinpoints
- Pinpoints use the 1-based PDF page of the copy whose SHA is given, plus the paragraph number as printed.
- JUDIS copies without paragraph numbers are pinned by page and SCR page. Reporter paragraph numbers that the copy does not print are marked as not mappable.
- Legally significant wording (dispositions, negations, overruling sentences) is read from a page render, and the render's SHA-256 is recorded. Otherwise the column says `PDF_TEXT_LAYER`.
- PDFs that contain two versions (CORRECTED plus uncorrected: Virendra 2020, Mullikote 2026) must have the version stated.

## V8. Passage roles
Each passage gets exactly one role:

- HOLDING / RATIO
- OPERATIVE_DISPOSITION / OPERATIVE_DIRECTION
- COURT_OBSERVATION / OBITER
- PARTY_ARGUMENT (including arguments the court summarises)
- APPLICATION (facts)
- DISPOSITION_ON_MIRROR (a non-official copy)

Editorial headnotes and commercial-database summaries are never evidence.

## V9. States
- WS-B can reach at most technical review.
- `legal_advisor_state` and `jag_validation_state` are separate columns. They stay `NOT_STARTED` until an attributable approval artifact exists.
- Treatment rows are proposition-level. Absence of a treatment row is not proof that no treatment exists.

## V10. Statutes and dates (owner rule, 22 Nov 2026)
- Publication, commencement and effective dates are kept in separate columns.
- An effective date is never inferred from a Gazette publication date. Unresolved effective dates stay empty, with `NOT_STATED_PENDING_ADVICE`, `NOT_DETERMINED` or `UNKNOWN`.
- Army Rules versions follow the ARMY-RULES-CHAIN-01 seed on `claude/next-stage-proposal` (`11ce905e`): r.23(3) is C-01 CONFLICTING, r.193 is C-08 OPEN, r.194 is C-09 PROPOSAL. WS-B does not alter these.

## V11. No collection
- A judgment that is needed but absent becomes a row in `pending_source_queue.csv`.
- Allowed: reading bytes already held in the scratchpad, and read-only lookups.
- Not allowed: downloads into the corpus, CAPTCHA bypass, the AFT bare-IP route, and using a commercial database as evidence.
