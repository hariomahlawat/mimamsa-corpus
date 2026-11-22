# Mimamsa legal case-law review v3.1 — first 11 critical-priority cases

**Evidence level: PROPOSED METADATA; no JAG approval, no judicial holding certification, no mutation of original v0.9 records.**

This register proposes identities and dates for all 11 P0 cases based on indexed judgments/court reproductions and NDLI metadata. Specific original source files and SHA matches must be established before accepting a correction to any curated case.

## Important risks detected
1. `DCLR-SC-1964-A11`: original title *Ram Swarup* vs a likely *Ram Sarup* judgment dated 12 Dec 1963 but reported in 1964 SCR. Avoid treating reporter year as decision year.
2. `DCLR-SC-2005-L01`: *Navjot Sandhu* (2005) secondary electronic evidence reasoning must not be published as current law after *Anvar P.V.* (2014) and *Arjun Panditrao* (2020), especially following Bharatiya Sakshya Adhiniyam 2023's later commencement. A post-2024 current-law review is separately required.
3. `DCLR-SC-2015-L03`: *Angad Singh Titaria* concerns an **Air Force** disability-pension claim. Classify as cross-service, not Army-specific.
4. `DCLR-SC-2008-L05`: *S.R. Dhingra* was explicitly flagged **out of core defence-law scope** in the original case data; its case ID year 2008 is a reporter year, while judgment is dated 14 Dec 2007.
5. Older medical-board/pension cases must be reviewed with subsequent SC holdings, statutory versions, and factual distinctions; do not flatten competing precedents.

## Source standard
Links in `01_P0_Proposed_Metadata.csv` are **discovery/source-reproduction candidates**, not authenticated downloaded original court PDFs. GitHub action `scripts/reconcile_p0_case_sources_v31.py` uses canonical Hugging Face raw manifests and original PDF checksums to independently test potential matches, and never promotes a holding.

## Gazette issue
Original scanned `S.R.O. 484` dated 27 November 1954 (Part II, Section 4) remains unavailable for original-text comparison of Rule 23(3). The Rule 23 accused-statement negation dispute remains **CRITICAL OPEN** in v3.0. See issue #2.

No changes to `legal_knowledge/curated_originals/` or `data/`.
