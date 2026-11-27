# Cycle 16 generation-v5 quantitative report

Evidence date: 2026-11-28. This is a processing report, not an admission or legal-validation certificate.

## Preserved population

| Measure | Result |
|---|---:|
| Source files | 1,965 |
| Source bytes | 1,889,520,054 |
| PDF files | 732 |
| Word documents | 1,233 |
| Word documents containing images | 566 |
| Embedded-image occurrences | 9,505 |
| Distinct embedded-image SHA-256 values | 3,890 |
| Reused image occurrences | 5,615 |
| PDF pages inspected | 10,812 |
| PDF pages requiring OCR | 3,522 |
| Mixed native/image pages | 2,803 |
| Image-dominant pages | 697 |
| Documents requiring image or page OCR | 867 |
| DOCX unresolved image relationships | 0 |
| DOCX unreferenced media | 0 |
| Source parsing errors | 0 |

## Embedded-image OCR

Primary OCR processed all 3,890 distinct image hashes with zero processing errors. It reused results across 9,505 occurrences and produced 1,021 empty/unreadable results.

The targeted second pass processed exactly those 1,021 hashes using PSM 6 and 11, 2x upscaling and thresholding:

| Result | Count |
|---|---:|
| Second-pass readable | 736 |
| Still unreadable and held | 285 |
| Access-marking holds added by second pass | 0 |
| Processing errors | 0 |
| Small-image decorative nominations | 796 |

Decorative nomination is non-dispositive. Every empty result remains held.

## Canonical and taxonomy reconciliation

The successful revision-pinned metadata retry examined 41,720 Hugging Face paths. Typed identity classes contain 6,562 original-source hashes and 3,241 LFS object hashes. The 31,593 untyped local manifest/audit hashes are measured but excluded from canonical identity decisions.

Taxonomy output preserves 507 nodes, all 5,294 folder-classification relationships, 669 candidate provision associations and 235 unresolved ranges or labels. Candidate associations are not legal findings.

## Conversion evidence

The 50-document Word pilot converted 50/50 documents with macros forced off and link updates disabled. Originals totalled 6,657,559 bytes; reconstructed PDFs totalled 16,254,553 bytes, a 2.441518 size ratio. All 50 PDFs contain extractable text. Eleven image-bearing documents produced 33 rendered review pages; one page per document was visually inspected with no obvious clipping, blank-image loss or page-geometry failure. The check is scoped and does not claim pixel identity for unreviewed pages. This disproves blanket conversion as a storage strategy. Conversion remains targeted to application compatibility, searchable representation and image-evidence viewing.

## Verification

- Local focused suite: 40 tests plus 5 parameterized subtests passing at the latest documented checkpoint.
- Accepted contract 2.0 at `8052792186b822881508e0e4b95f586df6772a25`: 160 tests passing.
- Generated corpus content remains outside Git.
- Original documents remain read-only and preserved.

PDF page OCR and final document-level access propagation are restartable external batches. Their final counts must be taken from the configuration-bound registers; incomplete or missing page results remain held.
