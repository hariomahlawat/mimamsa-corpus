# Cycle 15 independent review of the representative findings

The audited review file has SHA-256 `9d1bce075d15acbb2bfc0e5a94555a78aa563e7c58c9f2f99a15d83327a7ad3f`. The verifier independently reconciled the frozen package digests, 49 distinct review identities and source digests, provenance and application gates, and the full physical-page sequence and hashes of every selected document. It replayed all 152 anchors as exact Unicode substrings and found every anchor's tokenized phrase on its cited physical page through SQLite FTS. The 49 documents comprise 48 context-reviewed rows and one extraction quarantine.

## Findings by severity

| Severity | Status | Finding |
|---|---|---|
| High | Open release and expansion condition | The review covers 48 of the planned 100 context-reviewed documents. Disciplinary, service, pension and interpretation remain below quota. Original PDFs, subsequent case history and applicable statutory versions were outside this audit. The reviewed material remains application-ineligible and legal authority remains unreviewed. |
| Medium | Corrected and reverified | CWP-20575-2025 p.2 is now represented as an extraction observation under quarantine. The derivative interleaves two OCR columns and cannot independently certify the operative wording. |
| Medium | Corrected and reverified | Rojer Mathew’s Money Bill reference on p.156 now carries the Article 110 and Finance Act language in its own anchor. The p.158 disposition is limited to disposal of the batch. The p.156 ruling on excessive delegation and the order striking down the rules now have separate anchors. |
| Medium | Open evidence presentation limitation | Some multi-clause findings require the surrounding page or an adjacent page. The Rojer Mathew p.158 temporal anchor covers the pre-Finance Bill regime, with protection for existing additional salary and emoluments in the following sentences. A consumer presenting excerpts on their own should supply supporting spans for those additional clauses. |
| Low | Open source-quality limitation | All India Sainik Schools Employees (1988 INSC 310) records its disposition from the p.11 reporter result line and the benefit direction from p.10. P.10 includes the court's own disposal and costs lines in scrambled order. Preserve the reporter attribution and compare the original PDF before enriching those lines. |

## Semantic spot checks

- AFT-GUW-38 p.1 explicitly attributes the stay to counsel in agreement and records the date and appeal diary number. AFT-GUW-43 p.1 attributes the interim stay to the applicant’s counsel. The review does not independently certify current stay status. AFT-GUW-59 pp.1–2 confines its ratio candidate to the leave proceeding and accurately records refusal of leave.
- CWP-14095-2025 pp.2 and 6 preserves the chronological contradiction and the High Court’s case-specific refusal to interfere for lack of shown perversity. The disposition captures the lead writ’s dismissal and direction to copy the order to the connected file. The scan or docket would be needed to resolve any chronology or separately certify final status of the connected writ.
- AFT-GUW-54 pp.7 and 9 labels the historical instruments as version-unverified, preserves the evidentiary constraint, and records dismissal without costs. Delhi WP(C) 1049/2020 pp.16–17 preserves the 15-year restoration condition and distinguishes the January 2009 and December 2011 effect dates. Neither entry supplies an independently verified current statutory rule.
- Rojer Mathew pp.150–151 identifies Shrikant Sharma as the quoted two-judge decision. Rojer Mathew pp.156–158 supplies the majority's own rulings and directions. The 1996 National Ex-Servicemen decision p.5 differentiates dismissal of review petitions, the request to consider non-recovery sympathetically, and allowance of connected appeals.
- The AWES disposition p.72 distinguishes the allowed appeals from the case-specific continuation and non-discharge direction. Delhi WP(C) 3357/2007 pp.31–32 limits its permanent-commission and reinstatement summaries to the qualified groups and exclusions stated in the disposition.

Run `python /workspace/c15-qa/verify_reviews.py` against the local frozen package. The verifier tests exact-phrase retrieval constrained to each cited document and page. Corpus-wide ranking, adverse query sets, and active application behavior require separate evaluation.
