# Readiness to scale beyond the calibration sample (612 remaining records)

**Verdict: the method can be scaled. The evidence base cannot yet support scaling without first fixing the items below.**

## What worked
- **Independent reviews found real, consequential errors.** Some were found by more than one reviewer:
  - COI-003: the admissibility of court-of-inquiry evidence is misstated.
  - CM-028: the record cites r.56 for the accused's illness; the relevant rules are r.82–84 and AA ss.145–146.
  - HCE-016: says s.80 applies "primarily", where it applies only to the persons it names.
  - CM-026: omits the s.65B / BSA s.63 certificate.
  - AFT-039: understates Parashotam Dass.
  - SC13 and J-03: the P S Gill holding is mislinked or incomplete.
  - The Isaac 2026 position is missing from all 658 records.
  - A new Gazette wording conflict in r.182 (SC4-01), reported by both A and C in separately committed reviews and confirmed by the coordinator and by the technical reviewer. Independence of reading is self-declared: worktrees shared a filesystem and git cannot prove it.
- **The protocol caught some of its own errors, but not all.** Before reconciliation, the coordinator caught mirror copies marked as primary (QC-02) and a severity rationale tied to record status (QC-03). The independent technical review then found more:
  - the validator accepted unheld or derived-text hashes as VERIFIED;
  - D had 15 VERIFIED rows citing derived text files;
  - reconciliation hid non-legal-classification dissent and corroborated severity splits;
  - "evidence-supported" proposals overstated secondary evidence.

  All were fixed; the validator and reconciler are now tested against each case. The reconciliation rule was revised after the reviews were seen, so both the pre-registered and the final rule outputs are disclosed (`reconciliation/rule_sensitivity.json`).
- **The process is reproducible.** Propositions, reconciliation, packages, the acquisition matrix and the coverage estimate all rebuild byte-identically. The validators are tested.

## Deficiencies to fix before scaling
1. **Primary sources (the binding constraint).**
   - No Gazette text of the Army Act 1950, the AFT Act 2007, the BNSS or the BSA is held. Statutory propositions on these therefore stop at "secondary only": 294 findings.
   - The Army Rules amendment chain is incomplete: OCR-only, hint and not-found instruments, with nothing searched after June 2022.
   - Eleven calibration records cannot progress at all.
   - Acquisition order: ACQ-C3-01 (Army Act as enacted) first; then the record copy of S.R.O. 484/1954 and the Army Rules hint instruments; then official judgments to replace mirrors (Kuldeep Yadav, Som Datt, Santosh Lohar, Harjeet, Pandappa, Pooja Pal). See `registers/acquisition_readiness/`.
2. **Legal decisions upstream of record-level review.** Thirteen adviser topics recur across records: s.133/BSA, the Entitlement Rules trigger date and Isaac, AFT s.15 for SCMs, and others. Each answer will change many records, so they should be answered before the 612-record pass. Otherwise the same question is reworked record by record.
3. **Scope boundaries between reviewers.** 151 propositions were non-legal or outside every reviewer's scope, and B marked 126 statutory rows "not yet reviewed". At scale, every legal proposition needs a declared owning dimension, so that no proposition is reviewed by nobody.
4. **Proposition splitting.** Sentence segmentation is deterministic but coarse: references are one block, and checklists are split mid-item. Before scaling, add typed segmentation that separates statutory citations, case citations and procedural steps.
5. **Severity calibration.** There is one P1 (COI-003#P6), and it came from Reviewer D after coordinator feedback that severity follows content, not record status (QC-03). The other three reviewers rated the same defect lower: A and C P2, B P3. Write anchor examples per severity, e.g. "implies admissibility of excluded evidence = P1", and give them to every reviewer before review starts.
6. **Rule-level indexing.** ANCHORED_FULL is 187 of 658. A verified rule index could make 155–188 of the 193 PROVISION_FILES_ABSENT records technically searchable (`registers/rule_index_spec/`). That would speed review, but searchability is not correctness.
7. **Cost.** Four full reviews of 46 records took about 1.1M reviewer tokens. At this depth, 612 records would need about 15M. Batches should be prioritised by the 349-record affected list, and the source and legal decisions above settled first.

## Recommended next stage (needs owner approval)
1. Approve the targeted acquisitions in priority order.
2. Put the 13 adviser topics and SC4-01 to a qualified legal adviser.
3. Pilot the improved segmentation and the severity anchors on the next 50 records from the affected list.
4. Only after that, scale up.
