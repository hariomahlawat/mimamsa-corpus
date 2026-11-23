# Fable 5.2 re-review of corrections at 4bf0a96a (condensed record)

Reviewer: Claude Fable 5.2 (`claude-fable-5-2`, self-reported), the same agent and model as the a165b0f3 review, so this re-review is not independent of it. Read-only tools; no network; no hashing, git or code execution. Condensed by the coordinator (Claude Opus 5.5); findings, severities and verdict are kept.

**Verdict: ACCEPT WITH CONDITIONS.** No P1. One new P2 (N-01) and P3 items. Conditions: fix N-01 before any draft row becomes a ledger version or is approved; correct N-02 to N-05 and N-07 before or at incorporation; a git-capable independent check of diff scope and hashes (F-26).

**Answers:** (a) no DOCUMENTED row rests on a sibling-copy or disclaimed record (rows 19-33 cite records keyed by their own sha256; Navjot S-REVB-012 and the bosir rendition S-JUD-005 rest on SOURCE_LOCATED records that are not disclaimed; rows 2-18 not re-opened at this commit). (b) The fidelity rule is applied in code to every non-judicial copy; the 2022 change is supported (ACQ-01 `source: derivative`; producer "Internet Archive PDF 1.4.16 ..."; no /ByteRange); TRA supported (one %%EOF); byte-range arithmetic for 2018, 2019, Girish and Mullikote sums to file size; derivative input exists for only 7 of 21 archive rows (N-04). (c) Report counts match the summary (32/4; 20/8/3/1; 12->40; 12->40; 13/0/40). (d) Architecture mostly consistent; gaps N-01, N-05, N-06.

**F-01..F-26:** FIXED: F-01, F-03 (add C5 carry-over), F-04, F-05, F-06 (design), F-11, F-12, F-13, F-14, F-15, F-18, F-19, F-20, F-21, F-23, F-24, F-25. PARTLY: F-02 (deny-list, not affirmative state; external image rows), F-07 (schema lacks CORRECTION/WITHDRAW), F-08 (draft enforcement weaker than stated, N-01), F-09 (N-06), F-10 (number often only a year; test checks source-id format), F-16 (too broad, N-03), F-17 (normalisation only in design), F-22 (no rebuild test), F-26 (authorisation basis not verifiable; checks not independent).

**New findings:**
- N-01 (P2) `first_class_record_ref` takes the first sorted L1-L4 item; rows 14 (`682afce5`, ACQ-01 snapshot, md5+size only) and 11 (`b76bf4aa`, ACQ-02 snapshot, no sha256) name records without a sha256 although records with one exist; `validate()` never checks the record's own sha256; `resolves()` is substring-based ("S.R.O. 1" matches "S.R.O. 126"). Correction: priority L3, L1/L4, ACQ-02 supplement; parse and require own sha256; exact row key; negative tests.
- N-02 (P3) Rajbir C2 byte range ends 4 bytes short of the file; probable 4-byte host prefix (S-JUD-003 quirk); text misattributed to Fable F-01.
- N-03 (P3) JUDIS headnote limitation applied by URL pattern to rows where it was not checked (Dharamvir, Rajbir C1, Navjot).
- N-04 (P3) Derivative trigger relies on a field present only in the ACQ-01 snapshot; also applied to scans; soften "structurally intact".
- N-05 (P3) Schema cannot express CORRECTION/WITHDRAW (no target, reason, resulting_state; FULL/DOCUMENTED required for all types).
- N-06 (P3) Architecture: copy-level anchoring vs v0 byte-identity; transition table for HELD_PRIMARY losing its primary copy; validator inputs live in C6-01; frozen C5 vs carry-over edits and P-C6-02-META.
- N-07 (P3) Stale METHOD limits and class table; tautological T test; no decoy or UNCONFIRMED tests.
- N-08 (P3) `fable_review_a165b0f3.md` is a condensation labelled verbatim (faithful in substance).
- N-09 (INFO) Dharamvir producer mis-decoded.
