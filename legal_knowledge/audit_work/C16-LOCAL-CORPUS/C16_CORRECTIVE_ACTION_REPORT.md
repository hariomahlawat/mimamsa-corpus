# Cycle 16 corrective action report

## Status

This commit corrects the unsafe identity and inventory assumptions identified in
the independent review of `cc917819`.  It does **not** claim Cycle 16 completion,
canonical absence, legal identity, OCR completion, conversion success, or
application eligibility.

The prior external output at
`E:\Mimamsa-Data\local-corpus-reconciliation` is retained as the superseded
generation.  Corrected outputs were written separately under `generation-v4`;
the intermediate `generation-v3` is also superseded because it materialised
native-text derivatives before image/page access-marking screening completed.
The original `E:\Judgements` collection remained read-only.

## Corrected methodology

- DOCX extraction now resolves body relationship references and inventories
  embedded image occurrences in reading order.
- Exact image SHA-256 values participate in an ordered document-content hash,
  so identical native headings with different screenshots cannot be promoted
  as content-identical documents.
- Image dimensions, detected format and a perceptual dHash nomination signal
  are recorded.  The perceptual hash is never used to establish identity.
- DOCX images are explicitly queued for OCR.  DOCX files are flow documents,
  not a fictitious physical page 1.
- Restriction matching scans all extracted native text rather than the first
  5,000 characters.
- Normalized-text equality is a review signal only.  It no longer creates a
  `VERIFIED_ALTERNATE_COPY` disposition.
- Provision lists in filenames are parsed as candidate associations.  Ranges
  remain unresolved and are not expanded automatically.
- Extraction methodology version 3 invalidates the previous checkpoint.
- Candidate bytes are withheld until image/page access-marking screening is
  complete.  The manifest contains a collection identifier, not an absolute
  source path.

## Full-population evidence

The version 3 run completed with exit code 0 and its independent package
validator reported `PASS` for all 1,965 inventory records.

| Measure | Result |
|---|---:|
| Original files | 1,965 |
| Original bytes | 1,889,520,054 |
| PDFs | 732 |
| DOCX files | 1,233 |
| Source SHA-256 mismatches against the superseded generation | 0 |
| DOCX files containing embedded images | 517 |
| Embedded image occurrences | 6,735 |
| Distinct exact image SHA-256 values | 3,784 |
| Repeated image occurrences | 2,951 |
| Documents requiring page or image OCR | 579 |
| Embedded image occurrences requiring OCR | 6,735 |
| Native-text restriction hits | 1 |
| Parsing errors | 0 |
| Copied candidate source files | 0 |

The mutually exclusive dispositions reconcile to 1,965:

| Disposition | Count |
|---|---:|
| `ACCESS_RESTRICTED` | 1 |
| `IDENTITY_UNRESOLVED` | 642 |
| `NEW_DOCUMENT` | 854 |
| `NON_RELEVANT` | 157 |
| `RELEVANCE_UNRESOLVED` | 311 |

The 157 files omitted from the earlier principal disposition narrative are now
explicitly represented as `NON_RELEVANT`.  This is still an automated candidate
classification, not a legal relevance finding.

## Regression evidence

The focused suite contains 18 tests and covers, among other controls:

- identical native headings with different embedded screenshots;
- relationship-resolved image order and occurrence identifiers;
- DOCX image OCR queueing without false physical-page claims;
- restriction markings beyond character 5,000;
- candidate-only normalized-text matches;
- provision lists versus unexpanded provision ranges;
- deterministic content-addressed primitives and safe archive paths.

Final focused verification: 18 tests passed.

The repository's bare `pytest` entry point remains unusable because an existing
audit test script calls `sys.exit(0)` during collection.  `pytest tests` is
separately blocked on Windows by the AUTH-LEDGER fail-closed
`O_NOFOLLOW/O_NONBLOCK` requirement.  With only that collection module ignored,
the current branch baseline produced 846 passed, 12 skipped, 65 failed and 8
errors (plus 49 passing subtests).  The failures are in pre-existing frozen
audit/checksum, unavailable-private-input, Windows path/encoding and ledger
portability checks; they are not changed or waived by this corrective patch.

## Remaining holds

- OCR has not yet been run on the 6,735 image occurrences.  Image-only access
  markings therefore remain unscreened and candidate bytes remain withheld.
- Hindi trained data is not installed; the local Tesseract installation exposes
  only `eng` and `osd`.
- LibreOffice was not available from the local command path.  No conversion or
  compression claim is made.
- PDF mixed-content completeness still requires page-image inspection and OCR.
- The inherited canonical index does not distinguish every original,
  derivative, LFS, audit and configuration hash and contains no complete remote
  normalized-text index.  No canonical-absence claim is made.
- The provisional contract at `4d476fabd08fe152dea4b10e989392e6e57718b4`
  was reviewed as a target, but this correction does not yet emit a validated
  `mimamsa-corpus-contract/2.0` exchange package.
- Completeness, legal-work identity, historical recovery and legal taxonomy
  validation remain review work.  No item is application eligible.

