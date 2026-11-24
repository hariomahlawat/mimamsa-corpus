# Mimamsa — Corpus Crawler Brief for Claude Code

Source of truth: https://claude.ai/artifact/27tdbubCiwVqYx65pWPNvd (exported 2026-11-21)

## Goal and how to use this brief

Project name: Mimamsa (working title). Build a crawler and processing pipeline that collects public Indian military law documents into a clean, versioned repository with rich metadata, ready to copy into an offline search and RAG system.

Work phase by phase; review the output of each phase before starting the next.

Context:

- The final application runs fully offline. This pipeline runs on an internet-connected machine; only its output (the repository snapshot) moves to the offline environment.
- Documents are almost all in English. Many older ones are scanned PDFs and need OCR.
- The hardest problem downstream is validity over time: amended sections, superseded rules, overruled judgments, and the switch from IPC, CrPC and the Evidence Act to BNS, BNSS and the Bharatiya Sakshya Adhiniyam on 1 July 2024. Metadata must capture dates and relationships, not just text.
- A 50-question golden test set already exists. Every source it cites must end up in the repository.

## Scope and seed sources

Crawl official government and court sites only. Do not scrape commercial legal databases (Indian Kanoon, Casemine, SCC Online, Manupatra): their terms restrict it, and publisher headnotes are copyrighted. They may be used manually to discover case names, then fetch the judgment from the official source.

| Priority | Source | What to collect | Notes |
| --- | --- | --- | --- |
| 1 | [India Code](https://www.indiacode.nic.in) | Army Act 1950, Air Force Act 1950, Navy Act 1957, AFT Act 2007, Army and Air Force (Disposal of Private Property) Act 1950, Regulations for the Army 1987, BNS, BNSS, BSA 2023, IPC, CrPC, Evidence Act (historical) | Collect each Act's subordinate legislation and amendment notifications listed on its page |
| 1 | [Ministry of Defence](https://www.mod.gov.in) | Army Rules 1954, Act and Rule PDFs, manuals published there | Record any 'For Official Use Only' marking in metadata |
| 1 | [AFT Principal Bench](https://www.aftdelhi.nic.in) and regional benches | All disposed-case judgments and orders | Largest volume; organised by year and month |
| 2 | Supreme Court of India (sci.gov.in judgment portal) | Judgments mentioning Army Act, Air Force Act, Navy Act, AFT Act, court martial, disability pension, Entitlement Rules | Filter by keyword after download |
| 2 | High Courts (Delhi, Punjab and Haryana, Allahabad, J&K, others) | Writs against AFT orders; pre-2009 service and court-martial cases | Delhi HC first; it hears most AFT challenges |
| 3 | Gazette of India (egazette) | Notifications under the Army Act (e.g. active service declarations, s.12 notifications) | Needed for 'depends on notification' questions |
| 3 | [archive.org](https://archive.org) Digital Library of India | Indian Army Act 1911, Manual of Military Law editions, older military law books | Historical layer; tag as superseded |

Out of scope for this phase: internal policy letters, Army Orders, SOPs and anything not publicly published.

## Metadata schema

Every document gets one JSON metadata record. Use a JSON Schema file (`schema/document.schema.json`) and validate every record against it. Fields the pipeline cannot fill are `null`, never guessed.

**Common fields (all documents)**

| Field | Type | Example / rule |
| --- | --- | --- |
| doc_id | string | Stable, readable: `act-army-1950`, `sc-2013-dharamvir-singh-ca4949` |
| doc_type | enum | act, rules, regulations, manual, notification, judgment, order, book_historical |
| title | string | As printed on the document |
| number | string | Act number, notification number, case number |
| issuing_authority | string | Parliament, MoD, Supreme Court, AFT Principal Bench |
| issue_date | date | Date of enactment, notification or judgment |
| effective_date | date or null | Commencement date; often differs from issue date |
| status | enum | in_force, amended, partly_repealed, repealed, superseded, overruled, unknown |
| status_note | string | Why, with reference: 'omitted by Act 37 of 1992' |
| source_url | string | Exact URL downloaded |
| retrieved_at | datetime | When downloaded |
| sha256 | string | Hash of the raw file |
| access_marking | string or null | e.g. 'For Official Use Only' if printed |
| text_method | enum | pdf_text, ocr, html |
| ocr_confidence | number or null | Mean confidence where OCR was used |
| relations | list | See below |

**Extra fields for judgments and orders**

| Field | Type | Rule |
| --- | --- | --- |
| court, bench | string | e.g. Supreme Court; AFT Regional Bench Chandigarh |
| case_numbers | list | All numbers on the cover (OA, MA, CA, WP) |
| neutral_citation | string or null | e.g. 2025 INSC 549 |
| reported_citations | list | e.g. (2013) 7 SCC 316, if printed on the judgment itself |
| parties | object | petitioner, respondent |
| judges | list | Names as printed |
| outcome | enum or null | allowed, dismissed, partly_allowed, remanded, disposed |
| statutes_cited | list | Normalised: `{act: 'Army Act 1950', section: '69'}` |
| cases_cited | list | Raw citation strings, later resolved to doc_ids |
| topics | list | From a fixed list: court_martial, disability_pension, aft_jurisdiction, desertion, etc. |

**Relations** are typed edges between documents: `amends`, `amended_by`, `supersedes`, `superseded_by`, `repeals`, `overrules`, `overruled_by`, `follows`, `distinguishes`, `cites`, `implements` (rules implementing an Act). Each edge stores `target_doc_id` (or the raw reference text if unresolved), `type`, `effective_date`, `evidence` (the sentence it was taken from) and `confidence` (`extracted`, `llm_proposed`, `human_verified`). Anything other than `cites` needs human verification before the app relies on it.

Acts and rules are also split into **section-level records** (`act-army-1950#s69`) carrying their own amendment history, so a section omitted in 1992 is marked as such even though the Act is in force.

## Repository layout

Raw files are never modified. Every later stage writes to its own folder, so any stage can be re-run without re-downloading.

```
mimamsa-corpus/
  CLAUDE.md                 this brief
  schema/                   JSON Schemas (document, relation, section)
  config/sources.yaml       seed URLs, rate limits, allowed domains
  crawler/                  one module per source (indiacode, mod, aft, sci, hc, archive)
  pipeline/                 extract, ocr, classify, enrich, link, validate
  data/
    raw/<source>/<yyyy>/    original PDFs/HTML, named by sha256
    text/<doc_id>.txt       extracted text, page markers kept
    meta/<doc_id>.json      metadata record
    sections/<doc_id>/      section-level records for Acts and Rules
    relations.jsonl         all typed edges
    manifest.csv            one row per document: doc_id, type, status, source_url, sha256, retrieved_at
  state/crawl.sqlite        crawl queue, fetch status, retries, ETags
  reports/                  QA reports, coverage against the golden test set
  snapshots/                versioned, checksummed exports for offline transfer
  tests/
```

Use Python 3.11+, `httpx` for fetching, SQLite for crawl state, and `pdfplumber`/`pymupdf` for text. Keep dependencies pinned in `requirements.txt` so the same pipeline can be rebuilt later.

## Crawler requirements

The crawler must be polite, resumable and auditable. Government servers are slow and sometimes fragile; being blocked would stall the project.

- **Politeness:** obey robots.txt; at most 1 request every 2 seconds per domain (configurable); a descriptive User-Agent with a contact email; crawl heavy sources outside Indian working hours.
- **Allow-list only:** fetch only domains listed in `config/sources.yaml`. Never follow links off-domain.
- **Resumable:** every URL's state lives in `state/crawl.sqlite` (queued, fetched, failed, skipped). Killing and restarting the crawler loses nothing.
- **Retries:** exponential backoff on timeouts and 5xx; give up after 5 tries and log it.
- **No duplicates:** skip a file whose sha256 is already stored; record the extra URL as an alias.
- **Incremental:** use ETag/Last-Modified where offered, and date-based listing pages (e.g. AFT disposed cases by month) so later refreshes fetch only new items.
- **Audit trail:** log every request (time, URL, status, bytes). The manifest must let anyone trace a document back to its exact source URL and date.
- **Dry-run mode:** list what would be fetched, with counts per source, before downloading anything.
- **Per-source modules:** each site has its own listing logic. Start with one source, prove it end to end, then add the next.
- **No login, no CAPTCHA bypassing, no paywalls.** If a source needs any of these, stop and report.

## Processing pipeline

Each stage reads the previous stage's output and writes its own. Every stage is a separate command that can be re-run alone.

1. **Text extraction.** Use the PDF text layer when it exists and looks sane (enough characters per page, mostly dictionary words). Otherwise send the page to OCR. Keep page numbers as markers in the text so answers can cite pages.
2. **OCR.** Reuse the existing Prism OCR pipeline if available; otherwise Tesseract or PaddleOCR with English models. Store per-page confidence. Flag pages below a threshold for human review rather than silently keeping bad text.
3. **Relevance filtering.** AFT judgments and military statutes are relevant by definition. For SC and HC judgments, a keyword pass (Army Act, Air Force Act, Navy Act, AFT, court martial, court-martial, summary of evidence, disability pension, Entitlement Rules, invalided, release medical board) keeps candidates; borderline ones get a classifier or LLM check. Log rejects so the filter can be audited.
4. **Metadata extraction.** Parse cover pages with rules first (case numbers, dates, bench, parties, neutral citation); use an LLM only to fill gaps, and mark those fields as LLM-derived.
5. **Section splitting.** Split Acts and Rules into sections. Capture footnotes such as 'Omitted by Act 37 of 1992' or 'Subs. by Act 19 of 1955' as amendment history on that section.
6. **Citation extraction.** Extract statute references (normalise 'AA s.69', 'Section 69 of the Army Act' to one form) and case citations. Resolve case citations to doc_ids where the cited judgment is in the corpus.
7. **Relation building.** Create `cites` edges automatically. Propose `overrules`, `supersedes` and `amends` edges from explicit wording, with the evidence sentence, for human review.
8. **Validation.** Validate every metadata record against the schema; fail the run on invalid records.

## Quality checks and offline packaging

The repository is accepted when all of these hold:

- [ ] Every source cited in the 50-question golden test set is present, with correct metadata (`reports/golden_coverage.md`)
- [ ] 100% of metadata records validate against the schema
- [ ] A random sample of 50 documents is hand-checked: title, dates, case numbers and status correct in at least 95%
- [ ] OCR pages below the confidence threshold are listed for review, not silently included
- [ ] Known supersession cases are captured: field punishment (s.75-76 omitted 1992), s.127 omitted 1992, IPC to BNS from 1 July 2024, Dharamvir Singh (1982 Rules) vs the Sept 2026 SC ruling on 2008 Rules, the 2023 SC ruling on High Court writs against AFT orders
- [ ] Coverage report: document counts per source, per year and per type, with gaps called out

**Packaging.** Each snapshot is a dated folder in `snapshots/` containing `data/`, the manifest, the schema version and a `SHA256SUMS` file. The offline side verifies checksums before import. Refreshes produce a new snapshot plus a change list (added, updated, newly superseded), so the offline system can update without a full reload.

## Build order

Build in phases and stop for review after each. Start small: one source end to end beats six half-built crawlers.

1. **Foundation:** project skeleton, schema files, `sources.yaml`, crawl-state database, logging, dry-run mode.
2. **Statutes (India Code + MoD):** Army Act, Army Rules and the other Acts listed; text extraction; section splitting with amendment footnotes. Check against golden test questions Q01-Q50 that cite Act text.
3. **AFT judgments:** one bench, one year first; then all benches and years. Cover-page metadata extraction.
4. **Supreme Court and High Courts:** keyword-filtered collection; citation extraction.
5. **Relations and QA:** citation graph, proposed supersession edges, review queue, coverage and golden-set reports.
6. **Historical layer and gazette notifications.**
7. **Snapshot packaging and refresh mode.**

## Working rules

Ask before installing system packages, before any real download run, and whenever a source needs login or blocks us. Keep a short PROGRESS.md log of what was done and what is next.

Open questions to settle early: which machine runs the crawl and how much disk it has; whether the Prism OCR pipeline can be reused as a module; and who on the legal side reviews proposed supersession and overruling edges.

## Product direction and future design (recorded 2026-11-24)

Before planning future legal-knowledge, retrieval or application work, read:
- `docs/README.md`
- `docs/product/PRODUCT_VISION.md`
- `docs/product/COMMANDER_USE_CASES.md`
- `docs/architecture/LEGAL_KNOWLEDGE_ARCHITECTURE.md`
- `docs/architecture/SCENARIO_ADVISORY_ENGINE.md`
- `docs/architecture/CONTINUOUS_DOCUMENT_INGESTION.md`
- `docs/architecture/decisions/ADR-0001-SCENARIO_DRIVEN_EVIDENCE_GROUNDED_PRODUCT.md`
- `docs/architecture/decisions/ADR-0002-SHARED_ACCESS_AND_CONTINUOUS_INGESTION.md`

These record the owner's direction: the full legally accessible judgment corpus should remain searchable; Acts/Rules should link to judgments and propositions; and commanders should be able to ask ordinary-English, situation-based questions and receive evidenced, conditional guidance and checklists. The proposed technical designs are **not** implementation or legal-review approvals.

**Updated owner decisions (24 Nov 2026):** The initial app has **no RBAC, per-user document restrictions or feature tiers**. Every person allowed into the deployment can view all admitted documents and use every feature. All accepted content must therefore be eligible for the entire installation; source restrictions are assessed before shared ingestion, not by hiding results by user role. Users must be able to upload eligible policies, SOPs, circulars and reference documents at any time; the offline application automatically preserves, extracts/OCRs, analyses, indexes and proposes law/judgment/graph links. Such uploads are immediately distinguishable as unverified source material and cannot silently change authenticated law or mandatory guidance. Prioritise search, ingestion, graph and scenario capability, while retaining routine file safety, LAN access control, backup and prompt-injection isolation; more advanced hardening is a later phase.

The earlier crawler-only exclusion of internal policy documents remains the **scope of that acquisition phase**, not a restriction on the new in-app user-upload capability. No present authorisation is given to acquire restricted documents externally.

The existing `docs/legal-audit/EVIDENCE_STANDARD.md` and `docs/legal-audit/SOURCE_AUTHORITY_POLICY.md` remain controlling for authenticity, temporal applicability, source conflicts and review. Preserve the original corpus, access restrictions, offline deployment requirement, and AUTH-LEDGER approval boundaries. Do not turn scenario examples into asserted current law without independently verified evidence.
