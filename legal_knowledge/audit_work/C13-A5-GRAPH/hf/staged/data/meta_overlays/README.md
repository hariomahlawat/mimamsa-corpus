# data/meta_overlays/

Additive, versioned metadata overlays for records in data/meta/. Made under the standing owner instruction
(docs/governance/CORPUS_REPOSITORY_GOVERNANCE.md in the GitHub repository). The base records in data/meta/ are
never rewritten in place; this follows the data/manifest_additions/ convention.

The current metadata view is: base data/meta record + every overlay file here, applied in file-name (date) order.
An overlay row names the record (doc_id), the source copy (source_copy_sha256), the field, the original value
and the overlay value, with its evidence and verification state.

- `<stem>_sc_case_numbers.jsonl`: Supreme Court `case_numbers` corrections. One JSON object per record.
  scope = METADATA_ONLY_NO_EVIDENCE_OR_AUTHENTICATION_STATUS_PROMOTED;
  verification = AI_DOCUMENTARY_RECONFIRMATION_NOT_LEGAL_VALIDATION.
- `<stem>_SHA256SUMS`: checksums of the files of that stem.

Overlays change no evidence class, authentication state or legal status. Records of each overlay (tool, HF commit,
verification) are in GitHub: legal_knowledge/audit_work/C13-A5-GRAPH/ for c13_2026-11-25.
