# Form Discovery and Coverage Register

**Recorded:** 2026-11-24  
**Status:** Discovery register specification and initial work queue. No inspection or completed inventory is claimed by this document.  
**Related:** [Document Studio](../architecture/DOCUMENT_STUDIO_AND_TEMPLATE_REGISTRY.md), [ADR-0003](../architecture/decisions/ADR-0003-DOCUMENT_STUDIO_AND_TEMPLATE_REGISTRY.md), [Evidence standard](../legal-audit/EVIDENCE_STANDARD.md), [Source authority policy](../legal-audit/SOURCE_AUTHORITY_POLICY.md).

## 1. Purpose

Establish an auditable inventory of every identified prescribed form, specimen, service/administrative template and related document requirement from actual admissible source editions. Coverage must be measured against inspected pages and known source scope, not against a model's list of expected form names. This is a data-development work package; no current form or template has been verified by writing this register.

## 2. Initial discovery queue

| Queue ID | Source family to examine | Coverage state | Required next evidence |
| --- | --- | --- | --- |
| FDQ-01 | Army Act, Army Rules and applicable appendices, amendments and corrigenda | NOT_ASSESSED_IN_THIS_REGISTER | Exact instrument/copy register, edition/operative version, page and appendix map |
| FDQ-02 | All eight user-provided MML DOC/PDF originals | NOT_ASSESSED_IN_THIS_REGISTER | Eight separate receipt/manifest identities, hashes, editions, access marks, visual page concordance; retain UNVERIFIED_MANUAL until evidence warrants promotion |
| FDQ-03 | Applicable Defence Service Regulations / Regulations for the Army and amendments | NOT_ASSESSED_IN_THIS_REGISTER | Identify exact instruments and editions, then page/paragraph/appendix coverage |
| FDQ-04 | Eligible authorised service orders, instructions, circulars and SOPs | NOT_ASSESSED_IN_THIS_REGISTER | Existing source-register entries or separately authorised Admin intake; verify issuer/date and whole-deployment eligibility |
| FDQ-05 | Relevant judgments and procedural-form defects | NOT_ASSESSED_IN_THIS_REGISTER | Source-anchored search and candidate treatment; distinguish holdings from pleadings and obiter |

Queue items are not source records, claims of availability or acquisition instructions. Reconcile with current source manifests before assigning actual source-copy IDs. All eight MML originals are mandatory first-pass practical references under the evidence standard, not automatically authenticated official manuals. No new acquisition, HF write or legal approval is authorised.

## 3. Required coverage records

One record per source copy/edition and examined segment; include:

- source logical ID, source-copy SHA-256, source authority and carrier provenance, access marking and version/edition evidence;
- actual PDF page count or documented stable rendering for DOC/DOCX (renderer/version and page mapping), printed page/section/appendix labels, expected inspection range, pages inspected visually and text-extracted, and page-image locators;
- pages missing, unreadable, inaccessible, unexamined or ambiguous; reason, remediation and review state;
- inspection method/date, reviewer evidence, discovered form IDs, duplicate/alternate edition candidates, potential conflict and legal-review references;
- coverage state: NOT_STARTED, PARTIAL, INSPECTED_WITH_GAPS, INSPECTED_NO_FORMS_FOUND, INSPECTED_FORMS_FOUND, or INACCESSIBLE, with explicit denominators and excluded ranges.

A scanned page/table must be inspected visually when extracting printed forms and material wording; OCR alone cannot establish fidelity. A negative discovery is a recorded result for the examined range, not a claim that no form exists anywhere. Every covered page must belong to the stated source-copy/render revision. Do not calculate aggregate coverage across unknown denominators or count copies as distinct forms.

## 4. Required discovery entries

For each candidate form record: stable candidate ID; exact source copy and page/appendix/paragraph; printed name/number, page image and boundaries; verbatim layout/fields/footnotes and source language indicating requirement or example; candidate form authority/type; scope/date basis and related provisions; companion records/checklist candidates; alternate copies/versions and conflict links; independent fidelity, applicability, legal approval, publication and dependency-freshness states. Link each to the relevant coverage record and eventual FormTemplate/TemplateVersion. Unknown values remain unknown. Preserve distinct versions and duplicate relationships, rather than silently consolidating them.

## 5. Deliverables and acceptance

The eventual data work should deliver a machine-readable coverage register, form candidate manifest, original page anchors, conflict/gap queue and independently checked sample. Reconcile each source's inspected, missing and remaining pages; count unique candidate forms separately from copies and versions; explain non-applicable sources. Report partial or zero findings honestly. For authoritative template activation apply the operational-use gate in Document Studio, section 3.2, including competent legal approval evidence. The coverage register does not confer authority.
