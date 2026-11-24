# Dispositions: Fable 5.2 (claude-fable-5-2) reviews of the relations workstream

| Round | Reviewed | Verdict | Findings and outcome |
| --- | --- | --- | --- |
| 1 | 9529f7fe (rev. 1.0) | Not acceptable | **REL-01 (P1):** 9 of 10 OVERRULES/QUESTIONS proposals were not the court's own words. **REL-02 (P1):** 17 Narsingh Yadav APPLIES proposals were negated. P2s: REL-03 to REL-11. Fixed in rev. 1.1 (b262175f). |
| 2 | b262175f (rev. 1.1), on fresh rows | Accept with 2 open P2 | **Measured precision:** APPLIES/FOLLOWS 29/30, DISTINGUISHES 6/6, resolved edges 30/30. **Still open:** REL-05 (own-voice overruling missed) and REL-10 (statute labels). Fixed in rev. 1.2 (c0c7362f) and 48da982c, which removed the approval-state literal flagged by APR-1. |
| 3 | c0c7362f / 48da982c (rev. 1.2) | Not yet | REL-10 closed. **REL-05 still open:** declaratory forms were missed (9 authorities, incl. Ajmer Singh 1987). Fixed in rev. 1.3 (cc798a33). |
| 4 | cc798a33 (rev. 1.3) | **ACCEPT, no open P1/P2** | All 9 named misses queued. Adviser queue: 30 rows, fit for an adviser. No regression. |

Round-4 P3 findings, carried to the follow-up change (the adviser can see each by reading the row):

| ID | Disposition |
| --- | --- |
| V13-01 | **Follow-up.** Two OVERRULES proposals are false: C.S. Gill p.19 is a description of court-martial procedure, and Shatrughan Chauhan p.54 sits inside a quotation from Triveniben. Both are to be withdrawn. Two SCAORA separate-opinion rows (a rhetorical question, and a negated statement) are to be dropped. **Until then, the adviser should disregard these four rows; they are listed here.** |
| V13-02 | **Follow-up.** Puttaswamy (2018) p.1065 (2 rows) is Chandrachud J.'s dissent, not Bhushan J.'s opinion: prefer the bracketed footer to the running header. The Mafatlal pp.105/133 author is not Ahmadi CJ. Neither error changes a proposal. |
| V13-03 | **Follow-up.** The TC-09b5d373b025 candidate for Mohd. Saeed Siddiqui is wrong; (2004) 2 SCC 130 is Teri Oat Estates. Match candidates on the party name in the sentence. |
| V13-04 | **Follow-up.** Carry the preceding sentences into `lead_target_raw` for "these two decisions" (Ajmer Singh: Kerala HC Subramanian; Calcutta HC Anand Singh Bisht). |
