# Source hierarchy for resolving conflicting sources (owner rule, 2026-11-22)

**Binding on all audit agents. Supplements `EVIDENCE_STANDARD.md`.** This rule decides how to weigh documents. It does not let an agent approve a legal proposition; legal review remains required.

## 1. Determine, for every document in a conflict
1. **Authority:** who issued it and under what power. For example: Parliament (Act); Central Government under AA s.191 (Rules, S.R.O.); a court (judgment); MoD or Army HQ (manual); a private author (commentary).
2. **Provenance:** where this copy came from and its chain of custody. For example: certified custodian copy; archival reproduction of the printed Gazette (host, uploader, checksum); official consolidated compilation (India Code); government-issued manual edition; user-supplied file; third-party database.
3. **Applicable date:** the date of the text the document represents (notification, commencement, edition or consolidation date). Distinguish the date of the instrument from the date of the copy.
4. **Amendment history:** the amending instruments and corrigenda affecting the provision between that date and the date in question, and whether the document reflects them.

## 2. Order of precedence
1. **The authenticated original legal instrument:** the Act or Rules as notified in the official Gazette, with its amending instruments and corrigenda. A custodian-certified copy is best.
2. **An archival reproduction of the official Gazette** (e.g. a scan of the printed Gazette on archive.org) is evaluated **as a copy of that primary document**. It is never third-party commentary merely because of where it is hosted. Its weight depends on its custody checks:
   - identity (masthead, issue, date, Part/Section, S.R.O. number, printed page, read from the image)
   - integrity (checksum against the host's published value; recorded SHA-256)
   - completeness (page range present)

   With these checks passed and the pinpoint image-checked, it may support SOURCE_VERIFIED for "the Gazette prints X". It ranks below a certified copy only where the two differ. Schema class: `ARCHIVAL_COPY_OF_OFFICIAL` (validator-enforced: primary `source_type`, `custody_checks`, `sha256`).
3. **Binding judicial decisions** on the meaning or validity of the provision. These bind on interpretation; they are not substitutes for the instrument's text.
4. **Official later transcriptions and consolidations** (India Code, ministry compilations). These are useful but are copies made later. Where they differ from the notified instrument plus its amendments, the instrument prevails, and the compilation discrepancy is recorded.
5. **Government-issued manuals** (e.g. Manual of Military Law editions issued by the Government or Army HQ). They carry greater evidentiary weight than third-party commentary, but **never override Acts, Rules, amendments or binding judicial decisions**. Their reproduced legal text is evidence of what the instrument said at the edition date; their notes are commentary. Schema: `source_type: MANUAL`, authenticity `GOVERNMENT_ISSUED_MANUAL` once the issuing authority and edition are established; until then `USER_SUPPLIED_REFERENCE`.
6. **Third-party commentary and databases** (Indian Kanoon, SCC Online, LiveLaw, textbooks). Used for discovery only.

## 3. Applying the rule
- A later document outranks an earlier one only where it is itself an amending instrument, or where it reflects a located amending instrument. A later *transcription* does not outrank the original *instrument*.
- If the amendment history is incomplete, the preferred text is stated **as at the latest date covered**, and the gap is recorded.
- The determination is a **research determination of evidentiary weight**. The legal status of a disputed provision stays `CONFLICTING` until legal review. No record wording is changed by an agent.
- Record each determination in a conflict-determination register, with all four elements for every document.
