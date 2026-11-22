# v3.3 — Four P0 case-source recovery: verified final outcome

As of 22 November 2026. This register is a **source-preservation and identity audit**, not certification of any judicial holding or JAG approval.

## Source recovery status

| Original research ID | Case | Acquisition status | Canonical private Hugging Face path | Source-authenticity caveat |
|---|---|---|---|---|
| DCLR-SC-1964-A11 | *Ram Sarup v Union of India*, 12 Dec 1963 | **Original Supreme Court JUDIS PDF archived, PDF identity and SHA verified** | `legal_knowledge/judgment_originals/sci/historical/v3.3/ram_sarup_1963.pdf` | Original case metadata says *Ram Swarup*; no silent original-record correction. 10 pages; SHA `88f84411abdb3028e974792fef51a224770c987a9aa5ff7bc5a58654304738fd` |
| DCLR-SC-2005-L01 | *State (NCT Delhi) v Navjot Sandhu*, 4 Aug 2005 | **Original Supreme Court JUDIS PDF archived, PDF identity and SHA verified** | `legal_knowledge/judgment_originals/sci/historical/v3.3/navjot_sandhu_2005.pdf` | 107 pages; SHA `3b75354869ffb928f73532f475f5f920e2f2a1f8817163caba2f7fb5e1eb215d`; electronic evidence proposition later overruled in part, not entire judgment |
| DCLR-SC-2016-L04 | *Ex Hav Mani Ram Bhaira v Union of India*, 11 Feb 2016 | **Third-party reproduction containing signed Supreme Court order archived, SHA and text identity checked** | `legal_knowledge/judgment_sources/third_party_court_document_copies/2016/mani_ram_bhaira_mirror_2016.pdf` | 15 pages including *Satwinder Singh* order and court proceedings; SHA `cce64004ab57b9747a85482bfddc7a4ebf0d35c5e56a6547b51065754d766787`. No court-hosted original PDF byte match. |
| DCLR-SC-2008-L05 | *Union of India v S.R. Dhingra*, 14 Dec 2007 | **Public judgment text/index available, source PDF not yet archived** | None | Indian Railways government-hosted compilation URL timed out twice in authenticated CI. This is a railway/civil-service pay/pension case, outside core Army law. No false source-archived claim. |

### Why earlier historical JUDIS downloads were incorrectly rejected

The two original court JUDIS HTTP 200 responses begin with four non-PDF wrapper bytes before `%PDF-`. Earlier code required the PDF marker at offset zero and rejected both despite valid PyMuPDF-readable PDFs. The updated strict workflow records the marker position, checks complete case-name/year text, opens the received bytes without rewriting them, uploads those exact bytes and SHA-256-readback verifies both originals.

- [Original court-PDF acquisition receipt](https://huggingface.co/datasets/hariomahlawat/mimamsa-corpus/blob/main/legal_knowledge/source_acquisition/v3.3/01_Historical_JUDIS_Source_Attempts.json)
- [Mani Ram third-party source PDF and provenance record](https://huggingface.co/datasets/hariomahlawat/mimamsa-corpus/tree/main/legal_knowledge/judgment_sources/third_party_court_document_copies/2016)
- [Official 2024 Supreme Court Navjot treatment source](https://huggingface.co/datasets/hariomahlawat/mimamsa-corpus/tree/main/legal_knowledge/judgment_originals/sci/2024)

## Statutory-source blockers

* **Army Rules original Gazette S.R.O. 484 dated 27 Nov 1954, Part II Section 4:** no original scan. Rule 23(3) disputed omission of the word “not” remains **CRITICAL OPEN**.
* **2022 S.R.O. 6(E) official eGazette PDF:** source download failed TLS certificate validation; no insecure bypass or official-file archive performed. This amendment concerns Rule 16A, not Rule 23.
* **Original S.R.O. 17(E) 6 Dec 1993 and intervening notifications:** not yet authenticated from Gazette originals.

## Safety and legal status

* The verified PDFs represent **source provenance**, not automatic validation of court holdings, continuing legal force, or compliance with all amendments.
* *Navjot Sandhu* Section 65B electronic-evidence proposition must be marked **adversely treated/overruled in part**, while its Section 27 discovery discussion is tracked separately and remains subject to case-specific review.
* *Mani Ram* disability-pension decision remains fact-specific and requires later-treatment and applicability review.
* The original 53 cases, 658 knowledge records, original MML Word/PDF sources and crawler corpus remain untouched. All JAG-approval flags stay false.
