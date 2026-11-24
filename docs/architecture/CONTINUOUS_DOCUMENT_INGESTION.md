# Continuous user document ingestion for Mimamsa

**Recorded:** 2026-11-24  
**Status:** Owner-confirmed capability and shared-access requirements; technical workflow is a proposal pending implementation review.  
**Relationship:** [ADR-0002](decisions/ADR-0002-SHARED_ACCESS_AND_CONTINUOUS_INGESTION.md), [Legal architecture](LEGAL_KNOWLEDGE_ARCHITECTURE.md).

## 1. Purpose and access boundary

Every person admitted to the offline Mimamsa application can search, open, upload, analyse and graph-link the same documents using the same features. **There are no role-based access controls, no per-user feature tiers and no user-private document libraries.**

Any app user may deliberately add policies, SOPs, service instructions, circulars, manuals and other useful reference files. After ingestion, accepted material is available to **all users** of that deployment. The upload screen must clearly state this before acceptance. Questions typed into the assistant are not automatically uploads.

**Deployment-wide eligibility:** admit a document to the common corpus only if it may lawfully be shared with every person who can access this installation. If an access marking, copyright restriction, court order or other obligation is incompatible with that common audience, do not add it to the shared source vault/search/index/embeddings/graph. Preserve provenance and access markings when an item is eligible; do not reinterpret markings as user-specific permissions. A different deployment with a different eligible audience would require its own controlled dataset.

## 2. Core user experience

1. Click **Add Document** from any research view.
2. Choose one or more eligible local files; the app confirms that the accepted material will be shared with all app users.
3. The app checks file size, format, basic safety and corpus eligibility; rejected files are not indexed.
4. Preserve exact file bytes and SHA-256; record submit time, filename, declared title/issuer (if known), extraction method and processing trace.
5. Extract searchable text with page/paragraph boundaries; use local OCR for scans. Record incomplete pages, poor OCR and parser failures without inventing contents.
6. Propose document type, issuer, date, issue/effective dates (distinguish them), status/version and legal subject tags. Unknown values remain unknown; reported dates are not treated as verified.
7. Detect quotations and references to Acts, Rules, judgments, policies and earlier SOPs. Construct **candidate** typed edges, cross-links and proposed supersession/contradiction relationships.
8. Publish accepted document bytes, text and search results to the shared library with **USER_UPLOADED_UNVERIFIED** and a visible processing/completeness state. Display candidate edges separately from verified relationships.
9. Offer an inspectable **Document Intelligence** page: original, extracted sections, candidate references, related judgments/provisions, possible clashes, version candidates and a review/feedback mechanism.
10. Allow additional documents over time without requiring a new whole-corpus rebuild, software redeployment or internet connection. Update local search indexes and graph candidates incrementally, with rollback/repair of failed jobs.

## 3. Data model (proposed)

- \`UserUpload\`: stable ID, source file hash, filename, local ingestion time, importer reference if available, declared description, sharing acknowledgment and source eligibility result.
- \`IngestionJob\`: queued/extracting/indexing/complete/failed state, version of parser and model, warnings and retry history.
- \`SourceCopy\`: immutable bytes, hash, media type, completeness and page count.
- \`SourceDocument\`: title, issuer, kind, version, issue/effective dates, access marking, provenance classification and identity candidates.
- \`ExtractedPassage\`: source copy, page/paragraph, span/hash, OCR quality and text.
- \`CandidateRelationship\`: typed reference (policy-to-Act/Rule/judgment/SOP), passage anchor, discovery method, candidate confidence and review status.
- \`PotentialConflict\`: asserted differences with an earlier law or document, passages on both sides, current status; not a legal ruling.
- \`ReviewRecord\`: corrections, reviewer evidence and valid approval artefacts if later available.

Avoid making the legal identity or status depend on a mutable filename. Keep original revisions and their hashes; a new upload of a changed SOP is a **new copy/version candidate**, never a silent overwrite.

## 4. Trust and legal authority

There are two deliberately separate outcomes of ingestion:

**Research availability:** Once the document passes eligibility, basic file checks and extraction, it becomes usable for source search, previews and **candidate graph navigation** by every app user. No requirement to await legal review of each uploaded SOP before it can be discovered.

**Legal authority:** Uploading a policy, even one carrying a signature or official-looking seal, does **not** authenticate its issuer, prove commencement/current applicability, replace statutory law, make graph edges legally conclusive, or authorise a mandatory checklist item. The system must label it as user-supplied and unverified until the necessary documentary/legal evaluation is complete.

A newly uploaded SOP may *claim* that an older SOP is superseded. The app should propose a \`POSSIBLY_SUPERSEDES_DOCUMENT\` edge with quotations and dates, but must not automatically deactivate the old document, alter the AUTH-LEDGER, or promote the claim into commander guidance.

Where a user asks about a policy with unclear authority, show the document and possible relevance, then state what remains unverified. Source conflicts must not be hidden or resolved by majority vote or retrieval score.

Approval/review status is an evidentiary property of a claim, **not** a feature permission or user role. Users retain equal access to inspect original material, candidate claims and reviews.

## 5. Supported media and offline operation

Initial formats proposed: PDF (including scans), DOCX, plain text and, where safe and needed, image files for OCR. Consider more formats after measuring demand; do not promise arbitrary-format understanding. Entire pipeline must run on the air-gapped LAN, with locally installed parsers, OCR and language models. No cloud OCR, API calls, analytics or external resolution at runtime.

A hosted URL pasted by the user cannot be fetched from the offline app; it can be recorded as provenance text or ingested later by a separately authorised online acquisition process and controlled transfer.

**Baseline security, not feature-heavy hardening:** enforce file limits, validate actual type rather than extension, reject or safely handle malformed files and decompression bombs, isolate parser/OCR execution with least privilege, prevent PDF scripts/macros or embedded instructions from executing, keep source text untrusted relative to model instructions, hash all originals, maintain local backups and basic audit logs. Apply ordinary deployment admission/network controls. Additional security architecture, role systems and heavy hardening are not prerequisites to proving product value.

## 6. Status and failure behaviour

Recommended distinct states:

- \`REJECTED_NOT_ELIGIBLE\`: unsuitable for shared deployment audience.
- \`REJECTED_FILE_SAFETY\`: format or safety checks failed.
- \`PRESERVED_PROCESSING\`: original held, parsing/indexing in progress.
- \`SEARCHABLE_UNVERIFIED\`: source searchable, derived legal claims not approved.
- \`PARTIAL_EXTRACTION\`: text incomplete; original still available and marked.
- \`FAILED_RECOVERABLE\`: retry possible without destroying the original.
- \`DOCUMENTARY_REVIEWED\` / \`LEGAL_REVIEWED\`: separate evidence statuses where supported.

These are **proposed ingestion states**, not an instruction to change existing AUTH-LEDGER rules. Track source identity, byte integrity, attribution, legal interpretation and temporal applicability independently.

## 7. Graph relationships and benefits

The app should automatically suggest connections such as:
- “This SOP mentions Army Rule 22 and Army Rule 23”: \`UPLOAD_REFERENCES_PROVISION\` candidate.
- “This policy quotes judgment X”: \`UPLOAD_REFERENCES_CASE\` candidate.
- “This instruction concerns summary of evidence”: \`RELATES_TO_SCENARIO\` candidate.
- “This document refers to an older order as superseded”: \`POSSIBLY_SUPERSEDES_DOCUMENT\` candidate.
- “This policy differs from published Rule text”: \`POSSIBLE_CONFLICT_WITH_PROVISION\` candidate with source passages.

Every non-trivial link carries a pinpoint, graph version and verification label. The user can move from the policy to the original Rule, related judgments, timeline and supporting documents in both directions. No unsourced mandatory procedure can be derived simply from a reference match.

## 8. Acceptance scenarios

- Upload a valid local SOP: source searchable to *every* app user; original opens; candidate links to cited Rules and judgments are visible and attributed.
- Upload a revised SOP: no overwrite; prior version retained; claimed supersession is candidate only until substantiated.
- Upload a scanned PDF: local OCR produces passages with page anchors; unreadable pages flagged.
- Upload a policy with false/injected instruction text: app treats it as document content, not a command to change security, reveal files or override legal rules.
- Upload an access-marked file incompatible with whole-deployment sharing: reject from shared corpus; no source snippets or derived index leakage.
- Ask a question without uploading: query does not appear in common search.
- Restart after interrupted extraction: job resumes or fails visibly; original and manifest remain consistent.
- Search entirely offline: no network access needed and no dependence on Hugging Face/GitHub.
- Upload text contradicting Army Rules: show conflict, do not silently replace current legal authority.

## 9. Delivery priority

Treat in-app uploads, automatic extraction, retrieval and provisional graph linking as **early essential capabilities**, developed alongside full-corpus search and the commander scenario experience. This is not postponed until after a comprehensive security hardening programme. Maintain basic cyber hygiene from day one; defer advanced hardening based on measured deployment risks and actual needs.
