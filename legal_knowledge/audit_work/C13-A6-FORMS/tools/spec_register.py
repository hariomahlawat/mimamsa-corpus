"""Register expansion data for C13 A6 (forms). Everything here is copied from a
cited page of a held, hash-verified copy, or is an explicit 'not held' /
'not determined' statement. Nothing is inferred from memory.
"""

# Pinned C12 inputs (read-only). The build refuses to run if they change.
C12_INPUTS = {
    "FORM_DISCOVERY_REGISTER.csv": "581a7c7f363ef9c9fcc34f13a59575c1332b36002086174871f5de2ab48cf2f5",
    "FORM_FIELDS.csv": "2ce17181d629528e63af37f2ea175e26f805adb6260406a34325104b046ac03d",
    "SOURCE_COVERAGE.csv": "fa50c5fc256c366cfa3b238be2527123d3cf5f3acacb5d756ed16dde1c39df28",
    "SUMMARY.json": "30d0f018a9cbfcfd2559ec28f83811708fe57ad724d088266279dc36a0911920",
}

# MML comparison copy (UNVERIFIED_MANUAL; used only to record differences).
MML2 = dict(root="scratch", path="mml_x/originals/MML 2.pdf",
            sha256="db2119182ed2e4ccca22dd225d955327f6398ee98303e1c94615ba85b4396f65")

# Rule text read from page images (verbatim as printed) that governs forms.
RULE_READINGS = [
    dict(id="RR-1993-P18-170A1", source="AR-AMD-1993", page=18, families=["FF-AR54-APPV-F1A", "FF-AR54-APPV-F1B"],
         text="170A. Death Warrant.—(1) The officer commanding the army, army corps or division or an officer commanding forces in the field shall nominate a provost marshal or other officer not below the rank of Lieutenant Colonel who shall be responsible for the due execution of the sentence of death passed under the Act, and shall issue to such officer the death warrant in the relevant form contained in Appendix V."),
    dict(id="RR-1993-P18-170A3", source="AR-AMD-1993", page=18, families=["FF-AR54-APPV-F1A", "FF-AR54-APPV-F1B"],
         text="(3) No sentence of death passed under the Act shall be carried into effect until the death warrant has been received by the provost marshal or other officer nominated under sub-rule (1)."),
    dict(id="RR-1993-P18-170A4", source="AR-AMD-1993", page=18, families=["FF-AR54-APPV-F1B"],
         text="(4) If the authority specified in sub-rule (1) is of the opinion that the sentence of death be carried out in a civil prison, he shall forward a warrant in one of the forms in Appendix V together with an order of the confirming authority certifying the confirmation of the sentence, to the civil prison for execution of the sentence."),
    dict(id="RR-1993-P18-170B1b", source="AR-AMD-1993", page=18, families=["FF-AR54-APPV-FI"],
         text="170B. Execution of sentence of death.—(1) On receipt of the death warrant, the provost marshal or other officer, nominated under sub-rule (1) of rule 170A shall :— ... (b) if the person sentenced has been committed to a civil prison under rule 169 obtain the custody of his person by issuing a warrant in one of the forms in Appendix V; and"),
    dict(id="RR-1993-P18-170B3", source="AR-AMD-1993", page=18, families=["FF-AR54-APPV-F1A", "FF-AR54-APPV-F1B"],
         text="(3) After the sentence of death has been carried into effect, the provost marshal or other officer nominated under sub-rule (1) of rule 170A or the Superintendent of the civil prison, as the case may be, shall complete or cause to be completed parts II and III of the death warrant, and shall without unnecessary delay return the completed death warrant to the officer who had issued the same\"."),
    dict(id="RR-1993-P18-179-5A", source="AR-AMD-1993", page=18, families=["FF-AR54-APPIII-P3C"],
         text="35. In rule 179 of the said rules, after sub rule (5), the following sub rule shall be inserted, namely :— \"(5A) Any witness may be summoned to attend by order under the hand of the officer assembling the Court. The summons shall be in the Form provided in Appendix III.\""),
    dict(id="RR-GAZ-P2-AR4", source="AR54-GAZ", page=2, families=["*ARMY_RULES_APPENDIX*"],
         text="4. Forms in Appendices.—(1) The forms set forth in the appendices to these rules, with such variations as the circumstances of each case may require, may be used for the respective purposes therein mentioned, and if used, shall be sufficient, but a deviation from such forms shall not, by reason only of such deviation, render invalid any charge, warrant, order, proceedings or any other document relevant to these rules. (2) Any omission of any such form shall not, by reason only of such omission, render any act or thing invalid. (3) The directions in the notes to, and the instructions in, the forms shall be duly complied with in all cases to which they relate, but any omission to comply with any such directions in the notes or instructions shall not, merely by reason of such omission, render any act or thing invalid."),
    dict(id="RR-NR65P2-DEF-PF", source="NR65-P2-C7", page=None, families=["*NAVY_REGS_P2_APPX1*"],
         text="(f) \"Prescribed form,\" means an appropriate form in Appendix I applicable to the relevant section or regulation. [text layer, regulation 2(f) area; page image not read]"),
]

# Navy Regulations Part II Appendix I (list read on page image p.105; p.106 text layer).
NAVY_P2_FORMS = [
    (1, "Punishment Warrant From", "Regulation 16", 107),
    (2, "Record of Offences Sheet", "Regulation 72", 111),
    (3, "Daily Record of Offences and Punishments", "Regulation 72 & 85", 112),
    (4, "Quarterly Punishment Return", "Regulation 73", 113),
    (5, "Committal Order for Detention", "Section 150 & Regulation 109", 115),
    (6, "Committal Order for Imprisonment", "--------do-------- (Section 150 & Regulation 109)", 117),
    (7, "Report of Arrest and Trial by Civil Power", "Regulation 119(6)", 119),
    (8, "Specimen Charge Sheet", "Regulation 155(15)", 121),
    (9, "Warrant ordering a Court Martial (To be used by Convening Authority holding a Commission from the Chief of the Naval Staff to order a Court Martial).", "Regulation159", 122),
    (10, "Warrant ordering a Court Martial (To be used when a court martial is ordered by the President or the Chief of the Naval Staff).", "Regulation 159", 123),
    (11, "Warrant by Convening Authority appointing Trial Judge Advocate", "Regulation 161", 124),
    (12, "Warrant Appointing Prosecutor", "Regulation 163", 125),
    (13, "Warrant Appointing Provost Marshal", "Regulation 164", 126),
    (14, "Warrant Appointing Officer of the Court", "Regulation 165", 127),
    (15, "Notice of Trial to the Accused", "Regulation 169", 129),
    (16, "Notice to the Prosecutor", "Regulation 170", 131),
    (17, "Form for intimating Defence Witnesses to the Trial Judge Advocate by the Accused.", "Regulation 178(2)", 132),
    (18, "Order of the Court and Report of Navigation Direction at Trial on Navigational Charge.", "Regulation 183", 133),
    (19, "Minutes of Proceedings", "Regulation 190", 137),
    (20, "Abstract of Certificates", "Regulation 192(3)", 144),
    (21, "Order for board of Inquiry", "Regulation 200", 145),
    (22, "From for forwarding Minutes of proceedings of Board of Inquiry Disciplinary Court etc.", "Regulation 208", 147),
    (23, "Form for Summoning witnesses required to give Evidence before a Board of Inquiry.", "Regulation 204 & 233 and Section 134(2)", 149),
    (24, "Summons for witness required to give evidence before officer preparing a Summary of evidence.", "Section 134(2) & Regulation 233", 150),
    (25, "Summons for witness required to give evidence before a Commanding Officer.", "Section 134(2) & Regulation 233", 151),
    (26, "Summons for witness required to give evidence before a court martial", "Regulation 233", 152),
    (27, "Summons for witness required to give evidence before a court martial (witnesses not subject to Naval Law)", "Regulation 233", 153),
    (28, "Warrant for Arrest", "Section 83", 154),
    (29, "Warrant of Interim commitment Until Execution of the Sentence of Death.", "Section 148", 156),
    (30, "Warrant for Execution of a sentence of Death", "Section 149", 157),
    (31, "Order for transfer of Prisoner or Person under Detention.", "Section 154", 158),
    (32, "Order for Retransfer of Prisoner or person under Detention.", "Section 155", 159),
    (33, "Warrant for Removal of Insane persons", "Section 156", 160),
    (34, "Form for Retransfer of the Prisoner to the Jail or Detention Quarters.", "Section 156", 161),
]

# Statutory requirement quotes for new families (verbatim, page image read).
NEW_STATUTORY = {
    "FF-NA57-S13-ALLEGIANCE": ("Navy Act 1957 s.13 [NA57-C7 p.15]", "s.13: 'Every officer and every sailor shall, as soon as may be, after appointment or enrolment make and subscribe before the commanding officer of the ship to which he belongs, or the prescribed officer an oath or affirmation in the following form'", "Officer or sailor after appointment or enrolment", "commanding officer of the ship to which he belongs, or the prescribed officer"),
    "FF-NA57-S104-1-MEMBER": ("Navy Act 1957 s.104(1) [NA57-C7 p.40]", "s.104(1): 'Before the court shall proceed to try the person charged, an oath or affirmation in the following form and manner shall be administered to the president and every member of the court-martial in the order of their seniority by the trial judge advocate'", "Naval court-martial, before trial", "trial judge advocate (administers)"),
    "FF-NA57-S104-2-TJA": ("Navy Act 1957 s.104(2) [NA57-C7 p.40]", "s.104(2): 'The trial judge advocate shall then be sworn or affirmed by the president in the following form'", "Naval court-martial, after members sworn", "president (administers)"),
}

# Instruments needed but not held (or held only in restricted form).
ACQUISITION_REQUESTS = [
    ("A6-ACQ-01", "ARMY", "Army Rules 1954 Appendix II (Forms of Charges) official Gazette text", "1954 Gazette arrangement p.58 lists Appendix II; text not printed in pp.59-86 of the held Gazette (page images read: p.72 passes from App I to App III Pt II)", "FF-AR54-APPII-P1;FF-AR54-APPII-P2;FF-AR54-APPII-P3;FF-AR54-APPII-P4", "NOT_HELD", "egazette.gov.in / archive.org Gazette of India 1954 (allow-listed)"),
    ("A6-ACQ-02", "ARMY", "Army Rules 1954 Appendix III Part I (Forms as to courts-martial) official Gazette text", "listed on 1954 Gazette p.58; not printed in held copy; only IAFD-905 para 9 (S.R.O. 17(E)/1993) held", "FF-AR54-APPIII-P1A;FF-AR54-APPIII-P1B;FF-AR54-APPIII-P1C-GCMDCM;FF-AR54-APPIII-P1D-CHAR;FF-AR54-APPIII-P1D-SCHED;FF-AR54-APPIII-SCM;FF-AR54-APPIII-SGCM;FF-AR54-APPIII-MOCERT;FF-AR54-APPIII-AR36", "NOT_HELD", "egazette.gov.in / archive.org"),
    ("A6-ACQ-03", "ARMY", "Army Rules amending S.R.O.s listed in the S.R.O. 17(E)/1993 Note (p.21), to be reconciled against held copies (held: Gazettes dated 1963-01-19, 1965-04-10 [S.R.O. 116], 1965-07-03, 1979-07-28, 1988-09-17; mapping to this list not established): E.7/1960, 205/1961, 1/1961, 34/1963, 126/1964, 215/1965, 5/1968, 188/1979, 246/1982, 44/1985, 55/1985, 68/1985, 278/1985, 169/1987, 302/1987, 216/1988, 332/1989, 44/1991, 61/1991, 235/1991", "amendment chain for forms cannot be closed without them; held 1963, 1965-07, 1979, 1988 copies only text-layer scanned (no form amendment found, not visually confirmed)", "ALL_AR54_APPENDIX_FAMILIES", "NOT_HELD_OR_NOT_RECONCILED", "egazette.gov.in"),
    ("A6-ACQ-04", "ARMY", "S.R.O. 348/1960 and S.R.O. 404/1960 (form changes per C12)", "C12 README: change forms; not held", "FF-AR54-APPI-F1;FF-AR54-APPI-F2", "NOT_HELD", "egazette.gov.in"),
    ("A6-ACQ-05", "ARMY", "Current Appendix I enrolment form IAFK-1162 official copy", "MML 2 names IAFK-1162; not held", "FF-AR54-APPI-F1;FF-AR54-APPI-F2", "NOT_HELD", "egazette.gov.in / MoD"),
    ("A6-ACQ-06", "ARMY", "Army and Air Force (Disposal of Private Property) Rules 1953 Schedules I-II official Gazette text", "India Code file d969593b ends at r.34 on p.6 (page image read); schedules not printed", "FF-DPPR53-S1-F1;FF-DPPR53-S1-F2;FF-DPPR53-S1-F3;FF-DPPR53-S2", "NOT_HELD", "egazette.gov.in / indiacode.nic.in"),
    ("A6-ACQ-07", "ARMY", "Indian Soldiers (Litigation) Rules 1938 official copy (Forms A-D)", "only unverified MML vol 3 held", "FF-ISLR38-FA;FF-ISLR38-FB;FF-ISLR38-FC;FF-ISLR38-FD", "NOT_HELD", "indiacode.nic.in / egazette.gov.in"),
    ("A6-ACQ-08", "ARMY", "Indian Tolls (Army and Air Force) Rules 1942 official copy (Form of Pass)", "only unverified MML vol 3 held", "FF-ITR42-PASS", "NOT_HELD", "indiacode.nic.in"),
    ("A6-ACQ-09", "ARMY", "Territorial Army Rules 1948 official copy (Forms I-II, Schedules II-B..II-I)", "only unverified MML vol 3 held", "FF-TAR48-S1-F1;FF-TAR48-S1-F2;FF-TAR48-S2B;FF-TAR48-S2C;FF-TAR48-S2D;FF-TAR48-S2E;FF-TAR48-S2F;FF-TAR48-S2G;FF-TAR48-S2H;FF-TAR48-S2I", "NOT_HELD", "indiacode.nic.in"),
    ("A6-ACQ-10", "ARMY", "Assam Rifles Act 1941 official copy with Schedule", "only unverified MML vol 3 held", "FF-ARA41-SCHED-STMT", "NOT_HELD", "indiacode.nic.in"),
    ("A6-ACQ-11", "TRI_SERVICE", "AFT (Procedure) Rules 2008 later amendments after 2011 (if any)", "supersession of AFT Forms I-III not determined; later amendments not searched", "FF-AFTPR08-F1;FF-AFTPR08-F2;FF-AFTPR08-F3", "NOT_SEARCHED", "indiacode.nic.in / egazette.gov.in"),
    ("A6-ACQ-12", "AIR_FORCE", "Air Force Rules 1969 official Gazette copy (enrolment, oath, court-martial and warrant forms referred to as 'prescribed form' in the Air Force Act 1950)", "Air Force Act 1950 India Code copy (ef50375e) prints no forms; it refers to prescribed forms (text-layer scan)", "(none registered: forms not held)", "NOT_HELD", "egazette.gov.in / indiacode.nic.in"),
    ("A6-ACQ-13", "AIR_FORCE", "Regulations for the Air Force: any form that exists only in that instrument", "the only held copy (RM-001, Reprinted Edition 2000) is access-restricted and was not opened or used; contents unknown", "(none registered)", "NEEDS_AUTHORISED_SOURCE", "owner decision required (RM-001); no external call made"),
    ("A6-ACQ-14", "NAVY", "Navy (Discipline and Miscellaneous Provisions) Regulations 1965 official Gazette copy (to authenticate the India Code retyped Regulations for the Navy Part II Appendix I forms)", "held copy 884a893c is a retyped India Code file with 1965 imprint; Gazette facsimile not held", "FF-NR65P2-F01..F34", "NOT_HELD", "egazette.gov.in"),
    ("A6-ACQ-15", "NAVY", "Amendments to Regulations for the Navy Part II after 1965 affecting Appendix I", "not searched; amendment state of the 34 forms unknown", "FF-NR65P2-F01..F34", "NOT_SEARCHED", "indiacode.nic.in / Naval HQ publications"),
    ("A6-ACQ-16", "ARMY", "Regulations for the Army 1987 / DSR forms and Army Orders and Instructions forms", "not held (C12)", "(none registered)", "NOT_HELD", "MoD publications (authorised channel only)"),
]

# Page images read for purposes other than field transcription (review 1b05490f F06).
OTHER_READINGS = [
    ("AR54-GAZ", 58, 150, "arrangement of Appendices; end of rules (K. C. JAIN, Dy. Secy.)"),
    ("AR-AMD-1965", 1, 150, "masthead No. 15, 10-04-1965"),
    ("AR-AMD-1965", 2, 150, "S.R.O. 116 opening (27-03-1965)"),
    ("AR-AMD-1965", 3, 150, "S.R.O. 116 r.2(b): Appendix I Form No. I amendments (VERSION_EVIDENCE)"),
    ("AR-AMD-1993", 18, 150, "rules 170A, 170B, 179(5A) (RULE_READINGS)"),
    ("DPPR53-C7", 6, 80, "confirms the copy ends at r.34; Schedules I-II not printed"),
    ("NR65-P2-C7", 1, 80, "contents page; no access marking seen"),
    ("NR65-P2-C7", 105, 100, "Appendix I list of prescribed forms, Forms 1-25 (Forms 25-34 on p.106 read from text layer only)"),
]
