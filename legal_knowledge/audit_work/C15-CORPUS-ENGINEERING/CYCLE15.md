# Cycle 15 corpus engineering

The preservation checkpoint starts after PR #65 review commit 8937c853842dcb800f66d3c71f3ec3a9ce1ee12e. Acquisition and candidate generations have independent revisions. Nothing in this directory authorizes an application import or release.

## Acquisition

The formerly pending judicial commit was verified using its immutable revision. Per-batch receipts on PR #65 carry original and derivative hashes. The initial Guwahati reconciliation examined 617 eligible rows, representing 616 distinct originals. The pinned inventory already held 38, leaving 578. Additional hold clearances were screened separately. The collection receipt counts only original and derivative paths from verified batches. The inventory is an immutable HF tree projection. Legacy PDFs with no advertised SHA-256 remain outside the distinct SHA-256 total.

## Candidate preservation and reconstruction

The private dataset's cycle15-candidates branch stores immutable generations in legal_knowledge/candidates/cycle15. The candidate manifests and read-back receipts identify every uploaded byte sequence. The downloaded generation includes a physical page stream, record metadata, a reference search database, runnable reconstruction tools, the additive page-repair artifacts and the validation overlays.

Rebuild with `python -I portable_package.py rebuild PACKAGE_DIRECTORY NEW_DIRECTORY` in a Python environment with SQLite FTS5. The command hashes each input, reconstructs the index from the page stream, asserts unique page identities and rejects incorrect page hashes. It compares document, page, citation and search totals against the source manifest. No checkout, production index, network or credentials are required for the reconstruction itself.

## Review scope

The page repair reconciles 61 skipped inputs, including three local pairs recovered from the prior pilot environment and verified against recorded digests. It leaves preservation originals and legacy derivatives intact. The Act carrier contains 332 physical page slots outside the selected instrument scope. They contain no searchable text in the repaired map. Table, sparse-text and OCR risks remain explicit.

The validation overlays contain 100 contextual reviews across five categories and one separate extraction quarantine. Findings are evidence-bound candidates. QA replays the anchors and checks targeted search, source identities, and selected substantive issues. Decision hierarchy, subsequent treatment, controlling statutory versions, and legal authentication remain explicitly bounded by the individual findings. Broader automated legal enrichment remains outside this acceptance.

Chandigarh's official site leads to an HTTP POST search backend. It remains a discovery result pending a transport and artifact identity route. DESW's robots response remains 403. The historical Army Rules amendment has an official S.R.O. locator and awaits an eligible Gazette copy. Other acquisition holds and source gaps remain independent of candidate reconstruction.

## Latest preservation reconciliation

At preservation revision `f8a46dfaec55a13f2aaac2fde4139ca0acd5cff9`, all 618 judicial targets have a recorded disposition. The 596 verified original/derivative pairs comprise 589 on the main retry and seven on the bounded transport follow-up. The 22 holds comprise 19 marking reviews, two integrity holds and one sparse-page review. All eight original transport failures were reconsidered.

All 578 reconciled initial Guwahati originals were verified after upload. A further 58 orders cleared targeted review and passed pinned read-back. The inventory lists 685 preserved Guwahati originals including the earlier population. Outstanding AFT review cases lack sufficient full-document clearance and remain outside candidate intake.

The preservation tree has 2,387 distinct content-addressed originals with corresponding derivative paths. The union of these hashes with legacy SHA-256 metadata contains 4,803 distinct hashes. A further 1,631 legacy PDF paths have no trusted SHA-256 in this inventory and cannot contribute to a deduplicated count. No active application eligibility has been assigned.
