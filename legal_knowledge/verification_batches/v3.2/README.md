# Mimamsa v3.2 — five unresolved P0 case sources and proposition-level precedent treatment

Date: 2026-11-22. **RESEARCH_ONLY / JAG_APPROVAL_PENDING.**

Source of the starting point: previously verified [v3.1 strict P0 corpus crosswalk](https://huggingface.co/datasets/hariomahlawat/mimamsa-corpus/tree/main/legal_knowledge/crosswalk/v3.1). Four records had no strict party/year PDF match; *Baljit Singh* had matching raw-file SHA but failed case-name extraction. The separate forensic script `scripts/forensic_p0_source_v32.py` re-probes the original archived PDF for document-level identifiers and searches the entire raw manifest with controlled name/year variants. It never updates an original record or promotes a judicial holding.

## Important authority leads
- *Ram Sarup v Union of India* is a 12 December **1963** decision reported in [1964] 5 SCR 931, not necessarily a case decided in 1964. 1963 INSC 254 is an available court-catalog identifier, from the NDLI Supreme Court-sourced index.
- *State (NCT of Delhi) v Navjot Sandhu*, 4 August 2005, 2005 INSC 333, is a general criminal/electronic evidence decision. Its proposition on secondary electronic proof is restricted by *Anvar P.V.* and *Arjun Panditrao*, with the Supreme Court's 28 January 2025 judgment directly recording the limited overruling and procedural concerns.
- *Ex Hav Mani Ram Bhaira* is a Supreme Court order dated 11 Feb 2016, Civil Appeal 4409/2011. A later official SC office report references it; the original certified signed PDF is not yet downloaded.
- *Union of India v S.R. Dhingra* is **civil/railway public-service pension**, not a military law decision; isolate outside the core operational precedents.
- *Union of India v Baljit Singh*, 11 Oct 1996, civil appeal 13272/1996, 1996 INSC 1198, [1996] Supp 7 SCR 626, has a potential historical OCR spelling "Baltit"; don't falsely reject an archived PDF until document number and date have been inspected.

## Gazette / statutory blocker
The earliest scanned original `S.R.O. 484` dated 27 Nov 1954 has not been obtained, so neither version of the disputed Rule23(3) accused-statement wording can be declared authenticated Gazette text on this evidence alone. [Central Secretariat Library](https://csl.nic.in/page/innerpage/gazette-of-india.php) confirms historical digitization, not a direct located item. Continue escalation in GitHub issue #2.

No JAG approval; no original-source overwrites; no claim that a name/year lead is the entire judicial holding; no cross-era application of repealed/overruled legislation.
