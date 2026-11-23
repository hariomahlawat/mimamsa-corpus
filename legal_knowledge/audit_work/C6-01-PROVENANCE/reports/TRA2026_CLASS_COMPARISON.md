# TRA 2026 copy versus the Cycle 4 Act 37/1992 precedent (class comparison; no decision)

**Purpose:** set out the evidence for the owner's decision on the class of the held TRA 2026 copy. The draft keeps `NON_PRIMARY_OFFICIAL_PUBLICATION_COPY`. Nothing here promotes it.

The structural facts below were read from the held files with PyMuPDF and a byte search, run locally on 2026-11-23. They are observations, not cryptographic verification.

| Dimension | Act 37/1992 (Cycle 4 row, `PRIMARY_GAZETTE_GOVERNMENT_HOSTED_SCAN`) | TRA 2026 (C6-01 `C6-01-AP-be619533`) |
| --- | --- | --- |
| Held bytes | sha256 `f11d443e…`, 165,367 bytes, 4 pages | sha256 `be619533…`, 637,026 bytes, 15 pages |
| Nature of the file | **Scanned Gazette facsimile**: one image per page with an added text layer (`SCANNED_IMAGE_WITH_TEXT_LAYER_ALL_PAGES`; 4 images) | **Born-digital publication**: text on every page (`TEXT_LAYER_NO_IMAGES_ALL_PAGES`; 7 small embedded images such as the emblem) |
| Host and re-hosting | India Code bitstream (re-hosted; the original printed Gazette is not on India Code) | India Code bitstream (re-hosted e-Gazette; the e-Gazette original is on egazette.gov.in) |
| Watermark | India Code watermarks served PDFs; Cycle 4 recorded "bytes are host-specific" | IndiaCode watermark on every page (C6-PIC-01/02) |
| Producer | iText# (r0.95) | iTextSharp 5.5.13.1 |
| Embedded signature | none (a scan carries none) | one `/ByteRange [0 577400 600412 8230]`, so the signed range ends at byte 608,642 of 637,026. The 28,384 bytes after it are not covered, so the signature cannot validate the held bytes. Not cryptographically checked. |
| Document identity | image-checked (WS-A WSA-PIC-25..28) | image-checked (C6-PIC-01/02, CONFIRMED; final review reproduced the renders) |
| Issuing authority on the face | Gazette of India, Ministry of Law (Legislative Department) | Gazette of India, Ministry of Law and Justice (Legislative Department); printer line and signatory on p.15 |
| Provenance | retrieval record with URL + sha256 (PILOT-01 S-STAT-008) | retrieval record with URL + sha256 (R23/PILOT-01 L3; retrieved 2026-11-22) |
| Completeness | complete issue pages for the Act | complete on its face (ends at signatory and printer line) |

## What distinguishes the two
- **The watermark does not.** Cycle 4 accepted a watermarked India Code copy as primary.
- **Scan versus born-digital.** For a scan, the page image *is* the evidence of the printed Gazette. A watermark adds a layer but leaves the image of the printed page intact. For a born-digital e-Gazette, the authoritative object is the signed PDF as issued; a re-hosted, re-written file is a derivative of it.
- **Signature integrity.** The e-Gazette is digitally signed. In the held copy the signature no longer covers the file, which shows the bytes were changed after signing (consistent with watermarking). The content can still be identical to the issued Gazette, but integrity cannot be shown from these bytes.
- **Identity, authority and provenance are the same kind of evidence in both:** an official host, a recorded sha256, and identity read on page images.

## Options for the owner
1. **Keep `NON_PRIMARY_OFFICIAL_PUBLICATION_COPY`** (current draft). It is safe: no coverage change, since TRA has no exact-anchor dependency today.
2. **Introduce a separate class**, for example `PRIMARY_GAZETTE_GOVERNMENT_HOSTED_DIGITAL_REHOST`, with a stated rule. Content identity must be shown against the signed e-Gazette original, either by an approved acquisition of the egazette.gov.in file with a valid signature, or by a text comparison against it. This needs the evidence first.
3. **Apply the Act 37 class.** Not recommended without option 2's evidence, because the Cycle 4 class was defined for scans.

**Evidence that would settle it:** the signed e-Gazette PDF for CG-DL-E-13082026-275447 from egazette.gov.in, acquired under an approved route with its signature validated, then compared with the held copy page by page. egazette.gov.in failed TLS verification in Cycle 5, and verification must not be disabled.

No legal status follows from either class. Commencement of TRA 2026 is by notification (s.1(2)) and must be evidenced separately.
