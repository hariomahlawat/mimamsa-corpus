# Mimamsa v3.3 — primary-source acquisition result and exceptions

**Run date:** 22 November 2026. Status: **RESEARCH_PROVENANCE_ONLY; NO JAG VALIDATION.**

## Successful archival

* **2024 Supreme Court original judgment:** *Ravishankar Tandon v State of Chhattisgarh*, 2024 INSC 299, 10 April 2024, 24 pages.
* **Published file:** `legal_knowledge/judgment_originals/sci/2024/ravishankar_tandon_2024.pdf`
* **Original court URL:** https://api.sci.gov.in/supremecourt/2023/27190/27190_2023_3_1502_52269_Judgement_10-Apr-2024.pdf
* **SHA-256:** `adae1b11687f9606ed2d09d3d901590edfcb4a88c747ccde3ccaec9e15315b5d`
* Validated: court-hosted PDF, judgment title, neutral citation, references to `Navjot Sandhu` and Section 27, and private Hugging Face byte-for-byte read-back SHA.
* **Legal status:** This 2024 opinion quotes and discusses the 2005 `Navjot Sandhu` Section 27 discovery-of-fact passage. That is legally distinct from the 2005 secondary electronic evidence Section 65B proposition adversely treated by Anvar P.V. (2014) and Chandrabhan Sudam Sanap (2025). Neither proposition has been certified for commander-facing advice.

## Source acquisitions unsuccessful (not uploaded)

### Official Gazette, S.R.O. 6(E), 6 June 2022

Attempted official URL: `https://egazette.gov.in/WriteReadData/2022/236353.pdf`.

The authenticated GitHub Actions runner **failed X.509 certificate verification** against `egazette.gov.in` (`CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate`). The process **did not disable TLS verification**, accept a mirror as authenticated original, or upload a purported official PDF.

This 2022 instrument concerns Rule 16A; the 1954 Gazette `S.R.O. 484` and its original Rule 23(3) wording are still unresolved. The archive of the 1954 instrument **does not exist** in the verified data.

### Supreme Court office-report citation for Ex Hav Mani Ram Bhaira

Targeted official URL: `https://api.sci.gov.in/officereport/2022/10779/10779_2022_2022-07-22_916.html`.

The official Supreme Court office-report web representation was available to public research and lists `Civil Appeal 4409 of 2011` as an **allowed** case decided 11 February 2016. However, the independent GitHub Actions download returned a response that did not pass the required minimum-size/HTML-identity test. **No original HTML snapshot and no signed 2016 case order were uploaded.** The URL and case-identification evidence remain recorded as a source lead, not an authenticated archived judgment.

## Crosswalk

The four formerly unmatched P0 originals remain without independently checked source PDF in the 3,197-document raw manifest, though external court/public catalogue metadata identifies them. Case-source identity is not the same as judicial-holding verification.

## Workflow and follow-up controls

- [Source and exception workflow](https://github.com/hariomahlawat/mimamsa-corpus/actions/runs/45003386322) exited overall successful because the *experimental two archive steps* had `continue-on-error: true`. Such a **workflow-level success is not proof of source archival**. Per-step logs and separately verified remote object existence govern archive status.
- The official court 2024 PDF and its metadata have been separately checked in the private dataset.
- A further archive attempt for blocked official portals must be explicitly initiated after the access/certificate or response-format issue is resolved.
- Original v0.9 case records, imported MML binaries, crawler data and JAG review flags remain unchanged.

**No original Gazette Rule 23(3) wording is legally authenticated. The missing sources and all complete legal-holding reviews remain OPEN.**
