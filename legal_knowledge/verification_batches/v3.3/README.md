# Mimamsa legal-law source verification v3.3

Date: 22 November 2026. All rows are **RESEARCH ONLY**, not JAG approved.

## Source acquisition
The four case IDs remaining unmatched by exact or relaxed title/year PDF matching have actionable identifiers from the Supreme Court, its later office reports, or the Ministry of Education's National Digital Library of India. A later official judgment or case-management entry is documentary support for the prior decision's identity, **not** the original judgment.

**DCLR-SC-1964-A11** *Ram Swarup* vs verified bibliographic title *Ram Sarup*, judgment 12 Dec 1963, reported [1964] 5 SCR 931. Note that source catalog reports the decision in its 1964 browse collection; the actual judgment year is 1963.

**DCLR-SC-2005-L01** *Navjot Sandhu* merits both positive and negative legal-treatment relationships: 2024 *Ravishankar Tandon* discusses the **Section 27** discovery passage, while 2025 *Chandrabhan Sudam Sanap* describes overruling of the **Section 65B** secondary electronic-evidence passage. They are distinct legal questions. No wholesale case overruling is asserted.

**DCLR-SC-2016-L04** *Ex Hav Mani Ram Bhaira*, Civil Appeal 4409/2011, 11 Feb 2016, has an official court office-report citation dated 22 July 2022; this does not replace the signed decision.

**DCLR-SC-2008-L05** *S.R. Dhingra* is relevant only as general administrative-service comparison (railway/civilian pension); it is not an Army Act precedent.

## Original Gazette
S.R.O. 484, 27 November 1954, Gazette of India Part II Section 4 pp. 291–378: the original printed Gazette scan remains **NOT ACQUIRED**. Government-hosted annotated copies contain the contested Rule 23(3) omission of “not”; original Gazette evidence must be obtained before certification.

2022 S.R.O. 6(E), Gazette ID 236353, is available at the official candidate URL `https://egazette.gov.in/WriteReadData/2022/236353.pdf`, but official PDF download and hash matching in the private dataset have not yet been completed. It concerns Rule 16A, not directly Rule 23.

Scripts `archive_sc_treatment_v33.py` and `archive_gazette_v33.py` use an official-domain PDF, case/instrument identity checks and Hugging Face SHA-256 read-back. They do not update `data/` or `legal_knowledge/curated_originals/`.

All source originals immutable; no publication of commander-facing legal advice or JAG certification from these records.
