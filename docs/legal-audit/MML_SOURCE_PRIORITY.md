# MML — mandatory first-pass foundational source workstream

**Database audit only.** The eight user-provided **Manual of Military Law (MML)** documents are among the *primary practical reference works* used by Indian Army unit commanders. They must be examined FIRST for their structure, citations, historical commentary, procedural explanations and links to the knowledge-base records. **They are not automatically primary binding legal authority**: authentication, edition, statutory date and later judicial treatment remain independent questions.

## Confirmed canonical source store (22 November 2026)

Private Hugging Face dataset: `hariomahlawat/mimamsa-corpus`, path `legal_knowledge/manual_sources/`.

Read the canonical `MML_Originals_Manifest.csv` and `UPLOAD_RECEIPT_2026-11-22.md`. The upload receipt records a successful authenticated GitHub Actions transfer, per-file hashes and byte-for-byte remote read-back verification. This confirms storage integrity, **not legal validity or authenticated edition**.

Exact eight original files in `legal_knowledge/manual_sources/originals/`:
1. `MML 1.doc`
2. `MML 2.pdf`
3. `MML vol 2(AA).doc.doc`
4. `MML vol 2(AA).pdf`
5. `MML vol 2(AR).doc-1.doc`
6. `MML vol 2(AR).doc.doc`
7. `MML vol 3.doc.doc`
8. `MML vol 3.pdf.pdf`

**Caution:** The historical GitHub `legal_knowledge/manual_sources/README.md` contains a pre-transfer upload status. The actual private HF listing and receipt (verified 22 November 2026) are later evidence that all eight originals are now present. Treat each original as a separate revision/source until content-based equivalence is shown. Do not assume a .doc/.pdf pairing or edition from names.

## First audit pass — before choosing the pilot

1. **Access and authority:** Verify private dataset permissions and any access/copyright/reproduction marking. Do not export restricted manuals or send them to an unapproved model/workspace. Escalate if use is not authorised.
2. **All-eight inventory:** Name, size, SHA-256 verified against manifest; document format, actual edition, printing/reprint date, part/volume, title page, publisher/compiling authority, visible amendments and supplements, status of scan/OCR/extraction. Unknowns must remain unknown.
3. **TOC and locator index:** Extract table of contents and section/chapter/paragraph identifiers; map printed page numbers to PDF pages and Word text offsets. Preserve figures, annexures, procedural flow and editorial footnotes. Flag inaccurate extraction/negations for scan checks.
4. **Version comparison:** Independently compare potentially overlapping Word and PDF passages. Record whether same content, different edition, incomplete extract or unrelated volume; produce page-anchored difference rows. No silent merging.
5. **Source chain:** Each relevant MML paragraph -> underlying statute, rule, Gazette or judgment -> effective-date and subsequent treatment -> existing KB record IDs, case IDs and known procedural topics. Mark `MANUAL_PASSAGE_LOCATED` independently from `PRIMARY_LAW_VERIFIED`.
6. **Risk register:** Note outdated commentary, superseded procedures, erroneous citations, missing exceptions, contradictory Word/PDF phrasing, content that cannot be authenticated and critical matters unit commanders act upon.
7. **Human-review route:** P0/P1 interpretation and discrepancies to legal advisor; formal JAG validation later. No automatic correction or commander-facing guidance.

## Pilot design

Choose exactly 25 different real v0.9 KB records, not fabricated IDs. Target at least **12 distinct records with demonstrable MML anchor(s)** across the 25, with coverage of core commander disciplinary/administrative subject matter. The 12 are a **minimum representation target**, not a reason to force spurious links. Where available, include cases in which the MML text conflicts with a current or historic authenticated rule. Inventory all eight manuals regardless of selection, but do not claim each was legally audited merely from inventory.

The manual auditor reports first; statutory/procedure/judgment agents assess applicable authority **independently**; cross-volume agent connects claims; red-team agent challenges the result. A manual passage supporting a proposition is NOT, alone, proof that the proposition is correct or currently operative.

## Required outputs

- `mml_originals_inventory` with eight distinct source rows and hashes.
- `mml_edition_and_format_concordance` with known/unknown/unmatched versions.
- `mml_locator_index` identifying chapter, paragraph, pages and original file.
- `mml_to_kb_and_authority_crosswalk` with source IDs, case/KB IDs and authority-status distinctions.
- `mml_discrepancy_register` including exact contradictory text and legal advisor queues.
- A read-only 25-record pilot proposal showing 12+ MML-linked IDs if supported; precise reason for shortfall otherwise.

**Known P0 research example:** The Rule 23(3) accused-statement caution: `MML 2.pdf` p.152 reportedly includes the word “not” while some government-hosted compilations omit it. The scanned original 1954 S.R.O. 484 Gazette remains unauthenticated in present research. No agent may resolve the discrepancy solely by preferring the MML or compilation.

**Stop after read-only inventory and pilot proposal until explicit owner authorisation. Do not implement the application.**
