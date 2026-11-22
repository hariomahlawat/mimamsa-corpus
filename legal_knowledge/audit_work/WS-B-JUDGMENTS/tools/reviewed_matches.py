"""Reviewed identity matches between WS-B specs and intern corpus doc_ids (origin/raw-data ad77758d).

method values:
  COVER_PAGE_READ          - WS-B read the intern text of the cover page: parties, case number (where printed)
                             and decision date agree with the spec. Identity of the MIRROR copy only.
  COVER_PAGE_READ_PARTIAL  - cover read, parties/date agree, but a field disagrees or is absent (see note).
  METADATA_LEAD            - intern metadata title/date agree but the text could not confirm (garbled/OCR).
Doc_ids listed together are same-bytes duplicates (year-folder copies) of one document.
"""
CR = 'COVER_PAGE_READ'
MATCHES = {
 'PPS_BEDI': dict(doc_ids=['sc-1982-lt-col-prithi-pal-singh-bedi-e-1982insc65','sc-1983-lt-col-prithi-pal-singh-bedi-e-1982insc65'], method=CR, note='SCR [1983] 1 SCR 393 copy; cover date August 25, 1982'),
 'KULDEEP': dict(doc_ids=['sc-2019-union-of-india-ors-2019insc1083'], method=CR, note='[2019] 15 SCR 662; CA 7603/2019'),
 'NITISHA': dict(doc_ids=['sc-2021-lt-col-nitisha-ors-2021insc210'], method=CR, note='[2021] 4 SCR 633; WP(C) 1109/2020'),
 'RANDHIR': dict(doc_ids=['sc-2019-randhir-singh-2019insc729'], method=CR, note='Crl.A 210/2017'),
 'GIRISH_MAIN': dict(doc_ids=['sc-2026-union-of-india-through-its-sec-2026insc149'], method=CR, note='[2026] 2 SCR 615 : 2026 INSC 149; CA 6820-6824/2018'),
 'PARASHOTAM': dict(doc_ids=['sc-2023-union-of-india-ors-2023insc265'], method=CR, note='[2023] 3 SCR 598; CA 447/2023'),
 'VISHAV': dict(doc_ids=['sc-2016-union-of-india-ors-2016insc495'], method=CR, note='[2016] 5 SCR 473; CA 8360/2010; OCR-like text prints VISHAY'),
 'BABITA': dict(doc_ids=['sc-2020-the-secretary-ministry-of-defe-2020insc198'], method=CR, note='CA 9367-9369/2011'),
 'VISWAN': dict(doc_ids=['sc-1983-r-viswan-others-1983insc60'], method=CR, note='Five-judge bench on cover'),
 'SN_MUKHERJEE': dict(doc_ids=['sc-1990-s-n-mukherjee-1990insc257'], method=CR, note='Five-judge bench on cover; text quality poor (OCR artefacts)'),
 'HUSSAIN': dict(doc_ids=['sc-1997-union-of-india-and-others-1997insc793'], method=CR, note='IC-14827 Major A. Hussain; Dec 8, 1997'),
 'JETHI': dict(doc_ids=['sc-2013-union-of-india-and-others-2013insc705'], method=CR, note='[2013] 16 SCR 495; CA 8914/2012 (cover OCR "891-t")'),
 'SHRI_KANT': dict(doc_ids=['sc-2015-union-of-india-ors-2015insc206'], method=CR, note='[2015] 4 SCR 676; CA 7400/2013'),
 'DHARAMVIR': dict(doc_ids=['sc-2013-dharamvir-singh-2013insc408'], method=CR, note='[2013] 8 SCR 1119; CA 4949/2013'),
 'RAJBIR': dict(doc_ids=['sc-2015-union-of-india-anr-2015insc114'], method=CR, note='[2015] 2 SCR 183; CA 2904/2011 (curated reporter_citation empty)'),
 'TARSEM': dict(doc_ids=['sc-2008-union-of-india-ors-2008insc930'], method=CR, note='[2008] 12 SCR 104; CA 5151-52/2008'),
 'ANNIE': dict(doc_ids=['sc-2020-union-of-india-ors-2020insc300'], method=CR, note='CA 2182-87/2020'),
 'CHARANJIT_GILL': dict(doc_ids=['sc-2000-union-of-india-and-anr-2000insc231'], method=CR, note='April 24, 2000; three-judge bench'),
 'HIMMAT': dict(doc_ids=['sc-1999-union-of-india-1999insc242'], method=CR, note='May 12, 1999'),
 'RATAN': dict(doc_ids=['sc-1991-ex-havildar-rat-an-singh-1991insc300'], method=CR, note='Nov 19, 1991'),
 'SP_RATHORE': dict(doc_ids=['sc-2019-g-h-union-of-india-ors-2019insc1359'], method=CR, note='[2019] 18 SCR 990; CA 10870/2018; Air Force officer'),
 'ACHUDAN': dict(doc_ids=['sc-1975-ous-kutilingal-achudan-nair-an-1975insc286','sc-1976-ous-kutilingal-achudan-nair-an-1975insc286'], method=CR, note='Nov 20, 1975'),
 'JUJHAR': dict(doc_ids=['sc-2011-union-of-india-ors-2011insc496'], method=CR, note='[2011] 8 SCR 258; CA 4281/2006'),
 'EEVFAM': dict(doc_ids=['sc-2016-extra-judicial-execution-victi-2016insc527'], method=CR, note='[2016] 4 SCR 909; WP(Crl) 129/2012'),
 'MANJEET': dict(doc_ids=['sc-2015-union-of-india-ors-2015insc402'], method=CR, note='[2015] 6 SCR 192; CA 4357-4358/2015; May 12, 2015 (curated date/case no. empty); sha matches v3.4 path'),
 'ANGAD': dict(doc_ids=['sc-2015-union-of-india-ors-2015insc150'], method=CR, note='[2015] 2 SCR 524; CA 11208/2011; Feb 24, 2015; Pension Regulations for Indian Air Force 1961 Reg 153 on cover'),
 'BUTTAR': dict(doc_ids=['sc-2011-k-j-s-buttar-2011insc249'], method=CR, note='[2011] 4 SCR 136; CA 5591/2006'),
 'BALJIT': dict(doc_ids=['sc-1996-union-of-india-and-anr-1996insc1198'], method='COVER_PAGE_READ_PARTIAL', note='Cover prints "SH. BALTIT SINGH", October 11, 1996; v3.2 corroborated CA 13272/1996 inside PDF; name spelling disagreement retained'),
 'BALACHANDRAN': dict(doc_ids=['sc-2005-controller-of-defence-accounts-2005insc515'], method=CR, note='October 21, 2005'),
 'SURINDER_RATHORE': dict(doc_ids=['sc-2008-union-of-india-ors-2008insc357'], method=CR, note='[2008] 4 SCR 909; CA 1960/2008; March 13, 2008'),
 'KESHAR': dict(doc_ids=['sc-2007-union-of-india-and-ors-2007insc446'], method=CR, note='April 20, 2007; Pension Regulations 1961 Reg 423/App II'),
 'NAGA': dict(doc_ids=['sc-1997-naga-people-s-movement-of-huma-1997insc763'], method=CR, note='Constitution Bench (5 judges) Nov 27, 1997'),
 'RANJIT': dict(doc_ids=['sc-1987-ranjit-thakur-1987insc285','sc-1988-ranjit-thakur-1987insc285'], method=CR, note='Oct 15, 1987'),
 'SHIVENDRA': dict(doc_ids=['sc-2003-union-of-india-and-ors-2003insc254'], method=CR, note='Navy Act 1957 court-martial; Apr 24, 2003'),
 'PS_GILL': dict(doc_ids=['sc-2019-union-of-india-ors-2019insc1290'], method=CR, note='Crl.A 404/2013; Nov 27, 2019'),
 'NS_YADAV': dict(doc_ids=['sc-2019-no-1466828m-ex-cfn-narsingh-ya-2019insc1121'], method=CR, note='[2019] 13 SCR 260; CA 7672/2019'),
 'SOM_DATT': dict(doc_ids=['sc-1968-som-datt-datta-1968insc246','sc-1969-som-datt-datta-1968insc246'], method=CR, note='Five-judge bench Sept 20, 1968'),
 'PANDAPPA': dict(doc_ids=['hc-delhi-2026-w-p-c-5992-2026-dlhc010190732026-1-2026-05-05'], method=CR, note='Delhi HC W.P.(C) 5992/2026'),
 'SANTOSH_LOHAR': dict(doc_ids=['hc-ph-2023-cwp-3118-2023-phhc010194042023-1-2023-10-03'], method='METADATA_LEAD', note='Intern title CWP/3118/2023 NK SANTOSH LOHAR; intern date 2023-10-03 vs KB 4 Oct 2023 (neutral 2023:PHHC:127834); intern text font-garbled, cannot confirm from text'),
 'HARJEET': dict(doc_ids=['sc-2001-union-of-india-and-ors-2001insc202'], method=CR, note='April 11, 2001; three-judge bench; KB ADM-JD-02'),
}
