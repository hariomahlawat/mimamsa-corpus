# Rule-version decision pack, Cycle 8 update (proposal; rule version 1 stays in force)

**Status.** Nothing here is implemented or adopted. Rule version 1 remains the only rule and stays reproducible. Any eligibility-changing rule needs owner approval, then a separately reviewed rule-version-2 PR with `--as-of` diffs. Agreement between agents is not a reason to adopt anything.

This pack updates `AUTH-LEDGER/RULE_DECISION_PACK.md` (Cycle 7) with evidence from Cycle 8. Counts refer to the 32 C6-01 drafts unless stated.

**Where the evidence is (Fable RC-06).** The Cycle 8 evidence lives in separate draft PRs, which are reviewed separately and not merged:
- `legal_knowledge/audit_work/C8-EVIDENCE/` is on branch `claude/c8-evidence-verification` (draft PR #36), pinned at commit `152045bd5ae851692ee349ff9e78b42ed477e05f`, which an independent re-review accepted. It holds the page checks, the born-digital signature results and the exact-anchor simulation.
- `AUTH-LEDGER/DEMOTION_SEMANTICS_O5.md` is on branch `claude/c8-security-closeout` (PR A), pinned at commit `81df0e6c1e6d4631b6f9511a41b1e233f9fbfe53`.

The facts this pack relies on are restated below with their source files, so the pack can be read on its own. A decision on any item that depends on them should wait until PR B, or PR A for O-5, has passed its review.

## A3: retrieval provenance and content identity treated separately
- **Current rule 1:** a retrieval record is first-class unless it is disclaimed, NOT_FOUND or CONFLICTING. SOURCE_LOCATED and SOURCE_VERIFIED count the same.
- **Proposed change:** add `retrieval_verification_state` to entries. A SOURCE_LOCATED record proves retrieval provenance only; content identity must come from an identity check.
- **Evidence:** 3 drafts rest on SOURCE_LOCATED records: Navjot `3b753548`, S.R.O. 34/1963 `4acdb1a8` (re-pointable to `ACQ02-03`), and the Rajbir rendition `6b495f14`. C8 confirmed the identity of Navjot and S.R.O. 34 on page images, as AI-agent readings.
- **Records affected:** 3. None becomes ineligible under A3. Under A2, which requires VERIFIED, 2 would.
- **False-positive risk:** low, because identity stays mandatory. **False-negative risk:** none added.
- **Reproducibility:** rule 2 with a new column. Version zero and rule-1 history are unchanged.
- **Tests:**
  - the column is present and copied from the record, not typed;
  - a LOCATED record needs the identity check and a limitation;
  - a VERIFIED record is unchanged.
- **Recommendation:** adopt A3 only together with B2. Navjot shows why: a LOCATED record plus a page-1 text match would otherwise create an exact anchor.

## B2: legacy image evidence accepted with limitations; stronger evidence for exact anchors
- **Current rule 1:** an older image-check row with a render hash, an ARMY-RULES-CHAIN-01 IMAGE_CHECKED row, or (court copies only) the page-1 text rule each counts as identity evidence.
- **Proposed change:** an entry whose approval creates an EXACT_ANCHOR needs a CONFIRMED identity check or a reviewer statement naming the identity elements.
- **New question raised by Cycle 8:** do AI-agent page readings count as CONFIRMED? C8 produced 39 Gazette and 28 Supreme Court checks with render hashes, but no person confirmed them.
  - **Recommendation:** no. Under B2, CONFIRMED should need either a human reader identified in the record, or a reviewer statement by the independent reviewer of the tranche PR that they re-read the hashed render.
  - AI-agent readings stay supporting evidence. They raise confidence, as here, where all 20 Gazette and 8 court identities are consistent, but they do not satisfy B2 alone.
- **Records affected:** the 7 court entries that would create anchors (Ranjit, S N Mukherjee, Navjot, Dharamvir, Rajbir C1, Girish, Mullikote) need a human-confirmed or reviewer-attested check. The 20 Gazette entries create no anchor, so B2 does not block them.
- **False-positive risk:** low. **False-negative risk:** a modest delay for the 7.
- **Reproducibility:** rule 2.
- **Tests:**
  - an anchor-creating entry without an accepted check is rejected;
  - a non-anchoring entry is accepted with a limitation;
  - an AI-agent check alone is rejected for anchors.
- **Recommendation:** adopt B2, with the AI-reader clarification.

## C2: conservative URL comparison and reviewed aliases
- **Current rule 1:** exact-string contradiction detection. Since AUTH-LEDGER-02 the strict parser rejects common second spellings.
- **Proposed change:** RFC-safe normalisation of the comparison set, plus a decision-referenced alias table. Matches are reported as candidates and never merged.
- **Evidence:** 10 archive.org items are recorded under both `/details/` and `/download/`.
  - C8 noted that `/jonew/judis/` and `/judgment/judis/` paths both serve court files. Whether they serve the same file is unverified (SC open question 6).
  - The existing contradiction (India Code TRA bitstream, two sha256 values) is unchanged.
- **Records affected:** none change outcome on current data.
- **False-positive risk:** low, since equivalence-preserving rules only. **False-negative risk:** reduced.
- **Reproducibility:** rule 2, with the alias table as a pinned input.
- **Tests:** each safe normalisation; each unsafe one is not applied; an alias needs a decision reference.
- **Recommendation:** adopt C2 with the archive.org item alias. The alias is **item identity plus hash agreement**, not URL equivalence, as the Fable review noted. Add a court-path alias only on evidence that both paths serve identical bytes.

## Copy-fidelity classification (POLICY_OPTIONS D): Cycle 8 refinement
- **Current rule 1:** a born-digital file whose signature byte range spans the file is primary, provisionally. Rule 1 never checks the signature value.
- **New evidence:**
  - S.R.O. 2(E)/2018: the CMS signature verifies against the embedded certificate. This is integrity only, with no trust chain.
  - S.R.O. 17(E)/2019: the CMS signature **fails**, although the digest matches. This was reproduced independently.
  - Rule 1 therefore treats a file whose signature fails as primary.
- **Proposed change:** split the class.
  - `BORN_DIGITAL_SIGNED_RANGE_SPANS_FILE_CMS_INTEGRITY_OK`: provisionally primary under P-D2.
  - `BORN_DIGITAL_SIGNATURE_FAILS`: **non-primary** until an independent official copy, obtained under an approved acquisition, resolves it.

  Certificate-chain or trust validation remains out of scope until offline trust evidence exists.
- **Records affected:** T1-20 (`138c1da0`) would become ineligible for a primary class. T1-19 (`7c12a7ec`) is unchanged.
- **False-positive risk:** removed for T1-20. **False-negative risk:** a genuine document with a defective signature waits for another copy.
- **Reproducibility:** rule 2. Signature checks need `openssl` or the Python `cryptography` package, both already present. Results must be pinned as evidence, not recomputed silently.
- **Tests:** an integrity-OK file is accepted; a failing signature is rejected; a scanned facsimile is unchanged. An **unsigned born-digital or text-layer file**, such as S.R.O. 6(E)/2022, needs its own class, not the scanned-facsimile route (Fable review, task 8).
- **Recommendation:** adopt the split (P-D2a). Until then, the preparer recommends that the owner not approve T1-20.

## JUDIS court-copy treatment (P-D3)
- **Current rule 1:** a JUDIS text rendition on a court host with a court carrier can be `PRIMARY_OFFICIAL_COURT_COPY`.
- **This already happened at baseline (Fable RC-03).** The Cycle 4 register, a frozen historical record, classes the PPS Bedi copy (`211dbaf4…`, DCLR-SC-1982-001) as a primary court copy, and it is one of the 6 exact anchors at version 0. Its file is the same kind as the three drafts: GNU Ghostscript 7.05, 38 pages, "http://JUDIS.NIC.IN … Page 1 of 38" header. The coordinator checked this against the held file.
- **Evidence (C8, PR B):**
  - Ranjit Thakur, S N Mukherjee and Navjot are Ghostscript 7.05 text renditions with a JUDIS header and watermark and no signature or date block.
  - The 1987 and 1990 files carry headnotes and consecutive law-report page numbers, which suggests keying from a law report; that is an inference.
  - The Ranjit headnote refers to a later review order dated 10.8.88, which is not held.
  - Dharamvir and Rajbir C1, also from `/jonew/judis/` paths, are court-layout PDFs.
- **Options, applied consistently to all four JUDIS renditions (PPS Bedi and the three drafts):**
  - (a) Court-system dissemination is official, so primary. Anchors go 6 → 13.
  - (b) Court-system rendition, so non-primary. The three drafts are not added and PPS Bedi's baseline row is demoted by a CORRECTION, so anchors go **6 → 9**. The demotion is itself a ledger transaction, needing records, review and binding, and its timing depends on O-5.
  - (c) Primary for identity, but anchors limited to the judgment text: excluding headnotes and editorial notes, and only where no later order is known. This needs rule-2 support for copy-level or page-range anchors.
- **Records affected:** 3 drafts and 1 baseline row; 4 anchors in total.
- **False-positive risk under (a):** headnote or editorial text, or a superseded paragraph, is treated as the judgment.
- **False-negative risk under (b):** older judgments with no court-layout copy cannot anchor at all, including one current baseline anchor.
- **Recommendation (revised after RC-03):**
  - The end state should be **(c)**: the identity of a JUDIS rendition is well evidenced, but its headnotes are not judgment text.
  - Until rule 2 supports (c), **do not add** the three JUDIS drafts.
  - Leave PPS Bedi's baseline row unchanged. Record its JUDIS character as a known limitation, and refer it to the owner as part of P-D3, rather than demoting it unilaterally.
  - Obtain court-layout copies or certified reprints under an approved acquisition where they exist.

## Owner and reviewer identity assurance (O-1, O-4)
- **Current rule:** names in decision and review records are text. An AI-agent owner name is rejected as a lint. A BIND line proves merge topology, not identity.
- **Proposed change:** an out-of-band owner key with a signature over each BIND statement (O-1), plus a committed identity list (O-4) that is authoritative only together with O-1.
- **Records affected:** none now.
- **Recommendation:** decide before the first BIND line. Without O-1, owner identity rests on GitHub account control, confirmed online.

## Withdrawal and demotion semantics (O-5)
See `AUTH-LEDGER/DEMOTION_SEMANTICS_O5.md` on the security branch.
- **Recommendation:** activation policy 2. Demotions for cause, with records, take effect immediately; promotions stay staged.
- **Status:** not implemented. It needs its own versioned PR and tests.

## Summary of owner decisions
| Decision | Recommendation |
| --- | --- |
| P-A | A3, only with B2 |
| P-B | B2; AI-agent page readings are supporting evidence, not CONFIRMED |
| P-C | C2, with the archive.org item alias |
| P-D1 | Confirm the fidelity table |
| P-D2 | T1-19: provisionally primary, integrity only |
| P-D2a | Split born-digital files whose signature fails into a non-primary class (T1-20) |
| P-D3 | End state option (c). Until then, do not add the three JUDIS drafts; keep PPS Bedi's baseline row, with its JUDIS limitation referred to the owner |
| O-1 / O-4 | Identity assurance, decided before the first BIND line |
| O-5 | Activation policy 2 |

Each adopted item is built as rule version 2, or activation policy 2, in its own reviewed PR.
