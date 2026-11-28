# Cycle 16 generation-v5 corrective action and closure register

Independent review: PR #76, review `6094955629`. Contract target:
`mimamsa-corpus-contract/2.1` at `1e3060def474d8486d853b62bd5a25d9bc04372b`.

## Finding-wise closure register

| Finding | Corrective implementation | Adversarial regression evidence | Corrective commits | Status |
| --- | --- | --- | --- | --- |
| C16-PROD-01 | PDF bytes are read once, SHA-256 verified, and rendered from that verified in-memory snapshot. Each page record binds the source SHA-256 and size, physical page, render SHA-256 and dimensions, renderer/version, DPI, OCR configuration and content-addressed artifacts. | Changed source bytes are rejected; mutation after snapshot cannot affect the render; render/config changes alter the processing key. | `4f6a40cf` | Closed: 3,522/3,522 v2 pages complete, zero errors and zero pending. |
| C16-PROD-02 | Every OCR attempt is access-screened before selection. A marking in any attempt holds the result even if a different attempt supplies the selected transcription. | A low-scoring marked attempt plus a high-scoring clean attempt remains held. Cross-configuration positive markings survive a current clean record. | `4f6a40cf` | Closed in code and tests. |
| C16-PROD-03 | Configuration/input keyed state uses immutable attempt records, atomically replaced effective heads, fsynced content-addressed artifacts and recorded hashes. Reuse verifies configuration, source/render evidence and every artifact hash; errors remain retryable; summaries intersect the current job population and report pending/error counts. | ERROR-to-COMPLETE retry, tampered artifact, orphan artifact, stale-inventory record, partial-limit, render/config key, and configuration-isolation tests. | `4f6a40cf` | Closed in code and tests; external batch is restartable without repeating verified records. |
| C16-PROD-04 | Document access propagation groups all page/image attempts, preserves any positive marking, requires verified evidence from explicitly accepted configurations for clean screening, and withholds all derivatives on missing, unreadable, failed or marked evidence. | Wrong-configuration clean evidence is rejected; explicit CLI configuration sets reach the access decision; missing pages and unreadable images hold their containing documents and derivatives. | `4f6a40cf`, `82e00f88` | Closed: 1,965 documents accounted, 1,822 clean, 2 access holds, 141 unreadable/incomplete holds, 143 derivatives withheld. |

## Corrections implemented

- Full DOCX body, header, footer, footnote, endnote and comment image-relationship inspection, including VML, unresolved references and unreferenced media.
- Page-level PDF inspection that queues mixed native/image pages as well as image-dominant or sparse pages.
- Exact image-hash primary OCR reuse and configuration-bound immutable state.
- Targeted second-pass OCR only for the 1,021 empty primary results.
- Empty OCR and processing errors are fail-closed; image dimensions only nominate decorative review.
- Document-level access propagation holds every containing document and derivative when an image or required PDF page is missing, unreadable, failed or marked.
- Typed canonical identity separates original-source, derivative, LFS object, configuration and audit hashes. Untyped local audit hashes cannot establish document identity.
- Checkpoint reuse requires both an unchanged source SHA-256 and the exact processing-configuration SHA-256.
- Word conversion remains targeted, hash-verified and labelled as local reconstruction; originals are preserved.
- Accepted contract 2.0 remains recorded at `8052792186b822881508e0e4b95f586df6772a25`. The additive producer target is Contract 2.1 at `1e3060def474d8486d853b62bd5a25d9bc04372b`; OCR state remains independent of its receipt adapter.

## Verified external outcomes

- 1,965 files and 1,889,520,054 bytes preserved.
- 3,890/3,890 distinct embedded images completed primary OCR with zero errors.
- 1,021/1,021 unresolved primary images completed second-pass OCR with zero errors: 736 readable and 285 still held.
- 3,522/3,522 PDF pages completed under configuration `14323ea6661468f719fdba86b39387e087a39f5c9292a9368f0ffbb567034b55`: 3,519 clean, two unreadable held, one access-marking held, zero errors and zero pending.
- 507 taxonomy nodes, 5,294 classification relationships, 669 candidate provision associations and 235 unresolved labels/ranges are preserved.
- Revision-pinned canonical enumeration succeeded across 41,720 paths with typed original and LFS hashes kept distinct.

## Validation boundary

The focused suite contains 60 tests plus 5 parameterized subtests, including configuration-bound access, relationship-preservation, taxonomy, OCR-anchor and derivative-binding regressions. The final producer package contains 1,964 exportable identities/admissions, 3,519 verified PDF OCR anchors, 5,289 exportable relationships and 505 taxonomy nodes; five relationships belonging to the restricted document remain only in external hold evidence. Contract 2.1 strict validation, source-accounting schema validation and accounting reconciliation all report zero issues. No source content, OCR output, searchable PDF, full inventory or access register is committed to Git. No item is admitted, approved, legally validated or promoted by this work.
