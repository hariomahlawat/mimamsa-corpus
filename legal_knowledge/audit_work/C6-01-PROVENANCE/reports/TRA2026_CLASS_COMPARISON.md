# Born-digital Gazette copies: one copy-fidelity rule (TRA 2026 and comparators; owner decision)

**Purpose:** give the owner a complete comparison for classifying born-digital Gazette copies. The Fable 5.2 review (F-04) found that the first version left out the closest comparators.

**Rule applied uniformly in the builder** (`fidelity_issue()` in `tools/build_provenance.py`):
- A born-digital copy is classed primary only if nothing shows the held bytes were changed after issue.
- A copy is not primary if its embedded signature's byte range does not cover the held file, or if it is an archive.org derivative re-rendered by the archive.
- Structural facts come from `inputs/copy_structure_c6.csv`, produced locally by `tools/compute_copy_facts.py`. **No signature was cryptographically validated for any copy.**

Following SOURCE_AUTHORITY_POLICY v1, the table reports document authority, carrier and copy fidelity separately.

| Copy | Document authority | Carrier | File nature | Signature structure (`/ByteRange`; %%EOF markers) | Copy fidelity | Proposed class |
| --- | --- | --- | --- | --- | --- | --- |
| Act 37/1992 (Cycle 4 precedent, `f11d443e`) | Gazette of India Extraordinary, Ministry of Law | India Code bitstream (re-hosted; IndiaCode watermark) | **scan**: 4 page images plus a text layer | none (a scan carries none) | image of the printed page; watermark recorded by Cycle 4 | `PRIMARY_GAZETTE_GOVERNMENT_HOSTED_SCAN` (Cycle 4) |
| S.R.O. 2(E)/2018 (`7c12a7ec`, AR-033) | Gazette of India Extraordinary, MoD | archive.org item (third party) | born-digital e-Gazette (Ghostscript 8.15) | `[0 260473 1699735 7652]` **covers all 1,707,387 bytes**; 2 markers | signed bytes structurally intact | `PRIMARY_GAZETTE_ARCHIVAL_FACSIMILE` |
| S.R.O. 17(E)/2019 (`138c1da0`, AR-034) | as above | archive.org item | born-digital e-Gazette (Ghostscript 8.15) | `[0 324995 332029 7495]` **covers all 339,524 bytes**; 2 markers | signed bytes structurally intact | `PRIMARY_GAZETTE_ARCHIVAL_FACSIMILE` |
| S.R.O. 6(E)/2022 (`2bdab5b7`, AR-035) | as above | archive.org **derivative** file (`source: derivative` in the ACQ-01 snapshot; producer "Internet Archive PDF … mupdf"; 4 page images) | re-rendered by the archive from an upload | **no signature** | not the uploaded file; fidelity to the issued e-Gazette not shown | **`NON_PRIMARY_OFFICIAL_PUBLICATION_COPY`** (changed in this revision; previously primary) |
| TRA 2026 (`be619533`) | Gazette of India Extraordinary, Ministry of Law and Justice | India Code bitstream (re-hosted; IndiaCode watermark) | born-digital e-Gazette re-written by iTextSharp 5.5.13.1 | `[0 577400 600412 8230]`, ending at byte 608,642 of **637,026**; **1 marker** | bytes changed after signing; signed revision not extractable (see below) | `NON_PRIMARY_OFFICIAL_PUBLICATION_COPY` |

## What the comparison shows
- **The watermark is not the distinction.** Cycle 4 accepted a watermarked India Code scan.
- **The host is not the distinction either.** Third-party archive.org copies whose signed bytes are intact (2018, 2019) stay primary. A Government-hosted copy whose bytes were re-written (TRA) and an archive-rendered derivative (2022) do not.
- **Why a scan is treated differently.** For a scan, the page image *is* the evidence of the printed Gazette. For a born-digital e-Gazette, the issued object is the signed PDF. A copy re-written after signing, or re-rendered, is a derivative whose fidelity has to be shown.
- **Identity, authority and provenance** are documented for all five copies by the same kinds of evidence.

## Offline revision check (Fable F-12)
Some signed PDFs carry later changes as an *incremental update* appended after the signed bytes; the signed revision can then be cut out and validated offline. The held TRA file has a **single** %%EOF marker, so it was rewritten, not incrementally updated. Bytes 0–608,642 are not a self-contained PDF revision, and no signed revision can be extracted from these bytes. This is a structural finding, not a cryptographic validation.

## Options for the owner
1. **Keep the uniform rule (recommended).** TRA 2026 and the 2022 derivative stay non-primary. Neither has an exact-anchor dependency today, so coverage is unaffected.
2. **Add a class** such as `PRIMARY_GAZETTE_DIGITAL_REHOST`, used only where content identity against the signed original is shown: either an approved acquisition of the egazette.gov.in original with a validated signature (egazette.gov.in failed TLS verification in Cycle 5, and verification must not be disabled), or a full text comparison against such an original.
3. **Apply a primary class to re-written copies on host trust alone.** Not recommended: it ranks by host, which SOURCE_AUTHORITY_POLICY v1 warns against.

No legal status follows from any class. TRA 2026 s.1(2) provides commencement by notification, which must be evidenced separately.
