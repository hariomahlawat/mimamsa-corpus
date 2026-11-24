# Amendment graph correction package (C9-STAT)

Every page reading cited is by an AI agent (Claude Opus 5.5 subagent), not human-confirmed. No legal status, applicability or commencement date is determined or inferred; compilation footnotes and 'w.e.f.' notes are recorded as compiler statements only.

`amendment_graph.csv`: 116 edges (105 carried from the C8 amendment/commencement matrix and re-statused; 11 new). Status rule: EVIDENCED = a held instrument states the commencement (or is the commencement instrument); UNRESOLVED_COMMENCEMENT = the instrument is held but its commencement is not evidenced by a held primary document; NOT_LOCATED = the amending or commencing instrument is not held (a candidate may be pinned); DISPUTED_PRESERVE_BOTH = the sources disagree, and every reading is kept in `preserved_readings`. Nothing is decided by majority vote. A historical interval is filled only for EVIDENCED edges.

| status | edges |
| --- | --- |
| DISPUTED_PRESERVE_BOTH | 15 |
| EVIDENCED | 17 |
| NOT_LOCATED | 43 |
| UNRESOLVED_COMMENCEMENT | 41 |

## Corrections and additions to C8

1. **Army Act 1992 amendments (Act 37/1992).** Re-verified: the compilation prints '(w.e.f. 6-9-1992)' only at p.27 (ss.75-76; s.2), p.36 (s.127; s.11) and p.48 (Chapter XVI; s.19) C9R-AA-03 [held sha256 e47a4265813e95b4 p.27;36;48]. Every other Act 37/1992 footnote has no date C9R-AA-04 [held sha256 e47a4265813e95b4 p.27;28;29;30;35;37;38;39;40;42;44;45;48]. The Gazette scan has no commencement clause C9R-A37-03 [held sha256 f11d443ebfdada41; absent on all pages]; it records assent on 06-09-1992 and publication in No.59 of 07-09-1992 C9R-A37-01 [held sha256 f11d443ebfdada41 p.1]. All 18 edges stay UNRESOLVED_COMMENCEMENT (AQ-05), with both readings kept.
2. **Act 13/1975.** No commencement clause C9R-A13-03 [held sha256 8358d2b3882b2a74; absent on all pages]. 25-01-1975 appears only in the s.4(2) 'as if' saving for actions under the Ordinance C9R-A13-02 [held sha256 8358d2b3882b2a74 p.2]; the compilation prints 'w.e.f. 25-1-1975' C9R-AA-09 [held sha256 e47a4265813e95b4 p.11;12;26]. UNRESOLVED_COMMENCEMENT (OQ-A-04).
3. **AFT Act s.9A chain:** inserted by Finance Act 2017 s.181, with Part XIV in force on notified dates (s.156) C9R-RD-FIN17-02 [corpus raw store sha256 7a5551bab08518a7 p.53]; amended by TRA 2021 s.26 C9R-RD-TRA21-02 [corpus raw store sha256 0c2f4e9e023d5d7b p.13], deemed in force 04-04-2021 C9R-RD-TRA21-IMG [corpus raw store sha256 0c2f4e9e023d5d7b p.1; render sha256 3abbdbe6b554b239] (EVIDENCED); substituted by TRA 2026 Sch. II item 9, which commences by notification, with staged dates allowed C9R-TRA-02 [held sha256 be619533e45739bf p.1] (not held). TRA 2021 is repealed by TRA 2026 s.24(1) C9R-TRA-03 [held sha256 be619533e45739bf p.9]. C8's 'TRA 2021: provisions affected UNKNOWN' is superseded.
4. **New AFT instruments:** the Removal of Difficulties Order 2008 (S.R.O. 18(E), 21-07-2008, s.6(3)(a) 'and'->'or', on publication) is EVIDENCED. S.R.O. 9(E)/2009 establishes the Tribunal w.e.f. 10-08-2009, the appointed day under s.3(c); it is not the s.1(2) notification. S.O. 14(E)/2008 remains NOT_LOCATED.
5. **AFT rules:** the Procedure Rules 2008 (S.R.O. 26(E), Gazette No.19 of 17-09-2008) and the Amendment Rules 2011 (S.R.O. 05(E), No.4 of 29-07-2011) both commence on publication and are EVIDENCED. The Practice Rules 2009 (S.R.O. 6(E) of 11-05-2009) are UNRESOLVED_COMMENCEMENT, because the held page carries no masthead.
6. **NEW discrepancy C9-AG-AR168:** S.R.O. 17(E)/1993 item 31 omits the field-punishment words from r.168(2) C9R-AR-02 [held sha256 e9bf2114ab633716 p.17], yet the India Code Army Rules compilation still prints them C9R-AR-01 [held sha256 48f52219121bf74d p.189]. It is in no conflict register. Both readings are kept, and no conclusion is drawn on current text. This bears on the reliability of the compilation (48f52219) for other rules.
7. **S.O. 4010/1986:** DISPUTED_PRESERVE_BOTH. The Rajya Sabha page image reads 'dated the 6th December, 1986' C9R-RS-01 [held sha256 fa51a4b132c409ed p.1; render sha256 88cf5a512f6d8446]. PILOT-01 and ACQ-01 give a notification dated 24-11-1986 with Gazette 06-12-1986. C5 review RV-01's '8 Dec' is contradicted by the C9 read.
8. **2024 commencement notifications** are distinct, each with its own exceptions: BNS S.O. 850(E) (except s.106(2)) C9R-RD-BNS-02 [corpus raw store sha256 d4449e9995b21fd5 p.16]; BNSS S.O. 848(E) (except the First Schedule entry for s.106(2)) C9R-BNSS-02 [held sha256 572c79880b9f8eff p.18]; BSA S.O. 849(E) C9R-BSA-02 [held sha256 554b2b4ae3d9f09b p.10]. None is held, so all are NOT_LOCATED. Repeal provisions: BNSS s.531 C9R-BNSS-03 [held sha256 572c79880b9f8eff p.174], BSA s.170 C9R-BSA-03 [held sha256 554b2b4ae3d9f09b p.51], BNS s.358 C9R-RD-BNS-03 [corpus raw store sha256 d4449e9995b21fd5 p.110] (corpus raw store copy). These are UNRESOLVED_COMMENCEMENT, with savings recorded.
9. S.R.O. 34/1963 (C8-CR-02), S.R.O. 240/1955 (C8-CR-01) and the S.R.O. 17(E)/2019 Hindi/English footnote (C8-CR-14) are carried as DISPUTED_PRESERVE_BOTH edges. S.R.O. 17(E)/2019 also carries the CMS integrity caveat (C8-CR-03).

## Open items

- No Army Act amending instrument after 1992 has been located (not proof that none exists).
- The Army Rules chain after 06-06-2022 and the gaps AR-001 and AR-030 remain NOT_LOCATED.
- Reserved rule states (r.23(3) CONFLICTING, r.182 OPEN, r.193 OPEN, r.194 PROPOSAL) are carried unchanged.
