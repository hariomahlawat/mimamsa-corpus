#!/usr/bin/env python3
"""C9-STAT: re-hash every held binary and take text-layer / page-image readings used by the C9 packages.

Usage (run with the PyMuPDF venv, isolated mode):
  venv/bin/python -I collect_readings_c9.py <scratchpad_root> <repo> <inputs_dir> [--rawdata-git <git_dir>] [--check]

With --rawdata-git, blobs of the corpus raw store are read IN MEMORY from the locally present ref
origin/raw-data (git ls-tree / git show only; no fetch, no checkout, nothing written to disk) and
<inputs_dir>/rawdata_statutory_holdings.csv lists every non-judgment raw file of that ref.

Reads only local files. Writes (or, with --check, compares):
  <inputs_dir>/held_hashes_c9.csv   - every row of SOURCE-LIBRARY-C5/baseline/held_binaries_manifest.csv re-hashed
  <inputs_dir>/c9_page_readings.csv - needle readings (text layer) and page-image readings (render sha256)
Reader of every reading: AI agent (Claude Opus 5.5 subagent), not human-confirmed.
"""
import csv, hashlib, io, os, re, sys, warnings
warnings.filterwarnings("ignore")
import pymupdf as fitz

READER = "AI agent (Claude Opus 5.5 subagent), not human-confirmed"
AA = "downloads/independent-reviewer-A/army-act.pdf"
A37 = "downloads/statutory-auditor/1992-37.pdf"
A13 = "downloads/discovery/indiacode_1975-13.pdf"
A19 = "downloads/discovery/indiacode_A1955-19.pdf"
AFT = "downloads/independent-reviewer-A/aft.pdf"
TRA = "downloads/independent-reviewer-A/tra2026.pdf"
BNSS = "downloads/independent-reviewer-A/bnss.pdf"
BSA = "downloads/independent-reviewer-A/bsa2.pdf"
RS = "downloads/independent-reviewer-A/rs_313431.pdf"
ARC = "downloads/independent-reviewer-A/army-rules.pdf"
AR93 = "downloads/independent-reviewer-D/amend/in.gazette.central.e.1993-12-06.16490/16490.pdf"

# (reading_id, held_path, mode, regex, what the reading is used for)
# mode "all": record every page where the regex matches; "absent": record that it matches nowhere.
NEEDLES = [
    ("C9R-AA-01", AA, "all", r"As on the 21st July, 2025", "Army Act compilation as-on date"),
    ("C9R-AA-02", AA, "all", r"22nd July, 1950, vide notification No\. S\.R\.[O0] 120", "s.1(2) commencement footnote (compilation only)"),
    ("C9R-AA-03", AA, "all", r"w\.e\.f\. 6-9-1992", "pages printing 'w.e.f. 6-9-1992' (expect ss.75-76, s.127, Ch XVI only)"),
    ("C9R-AA-04", AA, "all", r"Act 37 of 1992, s\.\s*\d+", "footnotes attributing changes to Act 37/1992 (no date printed)"),
    ("C9R-AA-05", AA, "all", r"Army \(Amendment\)\s+Act, 1992 \(37 of 1992\), s\.\s*\d+", "omission entries citing Act 37/1992"),
    ("C9R-AA-06", AA, "all", r"Delegated Legislation Provisions \(Amendment\) Act, 1983 \(20 of 1983\)", "title of Act 20/1983 as printed in the compilation list"),
    ("C9R-AA-07", AA, "all", r"Act 20 of 1983, s\. 2 and the Schedule \(w\.e\.f\. 15-3-1984\)", "s.193A footnote (compilation)"),
    ("C9R-AA-08", AA, "all", r"S\.O\. 3912 \(E\), dated 30th October, 2019", "S.O. 3912(E)/2019 footnote (compilation)"),
    ("C9R-AA-09", AA, "all", r"Act 13 of 1975, s\.\s*3[^()]{0,40}\(w\.e\.f\.\s*25-1-\s*1975\)", "Act 13/1975 footnotes with w.e.f. 25-1-1975 (compilation)"),
    ("C9R-AA-10", AA, "all", r"Act 19 of 1955", "Act 19/1955 footnotes (compilation)"),
    ("C9R-AA-11", AA, "all", r"Adaptation of [Ll]aws \(No\. 3\) [Oo]rder, 1956", "ALO (No.3) 1956 footnotes (compilation)"),
    ("C9R-AA-12", AA, "all", r"Repealing and Amending Act, 1957 \(36 of 1957\)", "RAA 1957 footnote (compilation)"),
    ("C9R-AA-13", AA, "all", r"ACT NO\. 46 OF 1950\s*1? \[20th May, 1950\.\]", "Army Act assent date as printed in the compilation"),
    ("C9R-AA-14", AA, "all", r"Subs\. by Act 37 of 1992, s\. ?14, for .Code of Criminal Procedure, 1898", "references to the CrPC 1898 substituted by Act 37/1992 s.14 (dependency on later criminal-procedure statutes)"),
    ("C9R-AR-01", ARC, "all", r"or until the completion of the field punishment, unless such field punishment is remitted by a competent authority", "India Code Army Rules compilation r.168(2) still prints the field-punishment words"),
    ("C9R-AR-02", AR93, "all", r"31\. in sub-rule \(2\) of rule 168 of the said rules, the words, .or with field punishment", "S.R.O. 17(E)/1993 item 31 omits the field-punishment words from r.168(2)"),
    ("C9R-AR-03", ARC, "all", r"in accordance with section 340 of the Code of Criminal Procedure, 1973\s?\(Act 2 of 1974\)", "r.133(3) (compilation) refers to CrPC 1973 s.340 (dependency on BNSS)"),
    ("C9R-AR-04", ARC, "all", r"168\. Sentence of Cashiering or Dismissal", "r.168 heading in the compilation"),
    ("C9R-A37-01", A37, "all", r"received the assent of the President on\s+the 6th September, 1992", "Act 37/1992 assent date as printed in the Gazette scan"),
    ("C9R-A37-02", A37, "all", r"No\. 59\]", "Gazette Extraordinary issue number"),
    ("C9R-A37-03", A37, "absent", r"(?i)come into force", "no commencement clause anywhere in the 4-page text layer"),
    ("C9R-A37-04", A37, "all", r"Chapter XVI", "s.19 omission of Chapter XVI"),
    ("C9R-A13-01", A13, "all", r"received the assent of the President\s+on the 29th March, 1975", "Act 13/1975 assent"),
    ("C9R-A13-02", A13, "all", r"as if this Act had come into force on the 25th day\s+of January, 1975", "s.4(2) saving ('as if') clause"),
    ("C9R-A13-03", A13, "absent", r"(?i)shall come into force", "no commencement clause"),
    ("C9R-A19-01", A19, "all", r"\[3rd May, 1955\.\]", "Act 19/1955 assent (India Code text rendering)"),
    ("C9R-A19-02", A19, "all", r"7th May, 1955, vide notification No\. S\.R\.O\. 2\(E\), dated the 7th May, 1955", "commencement footnote (rendering only)"),
    ("C9R-A19-03", A19, "all", r"Rep\. by the Repealing and Amending Act, 58 of 1960", "s.2 and Schedule repealed by Act 58/1960 (Schedule text absent)"),
    ("C9R-AFT-01", AFT, "all", r"As on the 1st September, 2026", "AFT compilation as-on date"),
    ("C9R-AFT-02", AFT, "all", r"The Tribunals Reforms Act, 2021 \(33 of 2021\)", "TRA 2021 listed as amending Act"),
    ("C9R-AFT-03", AFT, "all", r"(?<!\(33 of )2021", "every page mentioning 2021 (to test for TRA 2021 footnote attributions)"),
    ("C9R-AFT-04", AFT, "all", r"15th June, 2008, vide Notifn\. No\. S\.O\. 14\(E\), dated 13th June, 2008", "s.1(2) commencement footnote"),
    ("C9R-AFT-05", AFT, "all", r"Ins\. by Act 7 of 2017, s\. 181 \(w\.e\.f\. 26-5-2017\)", "s.9A insertion footnote"),
    ("C9R-AFT-06", AFT, "all", r"Subs by Act 17 of 2026, s\. 18 and Sch\. II for section 9A \(w\.e\.f\. 25-08-2026\)", "s.9A substitution footnote"),
    ("C9R-AFT-07", AFT, "all", r"ACT NO\. 55 OF 2007", "Act number"),
    ("C9R-TRA-01", TRA, "all", r"No\. 17 of 2026", "TRA 2026 number"),
    ("C9R-TRA-02", TRA, "all", r"different dates may be appointed\s+for different provisions", "s.1(2) staged commencement power"),
    ("C9R-TRA-03", TRA, "all", r"24\. \(1\) The Tribunals Reforms Act, 2021 is hereby repealed", "s.24(1) repeal of TRA 2021"),
    ("C9R-TRA-04", TRA, "all", r"For section 9A of the Armed Forces Tribunal Act, 2007", "Sch. II item substituting AFT s.9A"),
    ("C9R-TRA-05", TRA, "all", r"CG-DL-E-13082026-275447", "Gazette Extraordinary identifier"),
    ("C9R-BNSS-01", BNSS, "all", r"As on the 6th October, 2025", "BNSS compilation as-on date"),
    ("C9R-BNSS-02", BNSS, "all", r"S\.O\.\s*848\(E\), dated, 23rd day of February, 2024", "commencement footnote S.O. 848(E) (except First Schedule entry for s.106(2))"),
    ("C9R-BNSS-03", BNSS, "all", r"531\. Repeal and savings\.—\(1\) The Code of Criminal Procedure, 1973 \(2 of 1974\) is hereby repealed", "s.531(1)"),
    ("C9R-BNSS-04", BNSS, "all", r"as if this Sanhita had not come into force", "s.531(2)(a) saving"),
    ("C9R-BSA-01", BSA, "all", r"As on the 6th October, 2025", "BSA compilation as-on date"),
    ("C9R-BSA-02", BSA, "all", r"S\.O\.\s*849\(E\), dated, 23rd February, 2024", "commencement footnote S.O. 849(E)"),
    ("C9R-BSA-03", BSA, "all", r"170\. Repeal and savings\.—\(1\) The Indian Evidence Act, 1872 \(1 of 1872\) is hereby repealed", "s.170(1)"),
    ("C9R-BSA-04", BSA, "all", r"as if this\s+Adhiniyam had not come into force", "s.170(2) saving"),
]

RAW = "raw:"  # prefix: corpus raw store blob addressed by sha256 (origin/raw-data)
NEEDLES += [
    ("C9R-RD-AFTPR08-01", RAW + "590cf7cd393564eacab37566d605357662429f900ea58a96f0ce0e5bb0e0e317", "all", r"These Rules may be called the Armed Forces Tribunal \(Procedure\) Rules,\s*2008", "AFT Procedure Rules 2008 short title (English text)"),
    ("C9R-RD-FIN17-01", RAW + "7a5551bab08518a7f52eb60c6cb08dc775726a8b2f5b89369413af771d173766", "all", r"181\. In the Armed Force Tribunal Act, 2007, after section 9, the following section shall be inserted", "Finance Act 2017 s.181 inserting AFT s.9A"),
    ("C9R-RD-FIN17-02", RAW + "7a5551bab08518a7f52eb60c6cb08dc775726a8b2f5b89369413af771d173766", "all", r"156\. The provisions of this Part shall come into force on such date as the Central Government may, by\s+notification in the Official Gazette, appoint, and different dates may be appointed", "Finance Act 2017 s.156: Part XIV commencement by notification, staged dates allowed"),
    ("C9R-RD-FIN17-03", RAW + "7a5551bab08518a7f52eb60c6cb08dc775726a8b2f5b89369413af771d173766", "all", r"NO\. 7 OF 2017\s+\[31st March, 2017\.\]", "Finance Act 2017 number and assent date"),
    ("C9R-RD-TRA21-01", RAW + "0c2f4e9e023d5d7b72d60797e1df67a7b2d2e340da8fe493a4328940638f0451", "all", r"It shall be deemed to have come into force on the 4th April, 2021", "TRA 2021 s.1(2) deemed commencement"),
    ("C9R-RD-TRA21-02", RAW + "0c2f4e9e023d5d7b72d60797e1df67a7b2d2e340da8fe493a4328940638f0451", "all", r"26\. In section 9A of the Armed Force Tribunal Act, 2007", "TRA 2021 s.26 amending AFT s.9A"),
    ("C9R-RD-BNS-01", RAW + "d4449e9995b21fd52627811d08f9d21feda6a3678b7e5355b651242d152167f5", "all", r"As on the 6th October, 2025", "BNS India Code compilation as-on date"),
    ("C9R-RD-BNS-02", RAW + "d4449e9995b21fd52627811d08f9d21feda6a3678b7e5355b651242d152167f5", "all", r"except the provision of sub-section \(2\) of section 106, vide notification No\. S\.O\. 850\(E\), dated, 23rd February, 2024", "BNS commencement footnote S.O. 850(E) (except s.106(2))"),
    ("C9R-RD-BNS-03", RAW + "d4449e9995b21fd52627811d08f9d21feda6a3678b7e5355b651242d152167f5", "all", r"358\. Repeal and savings\.\u2014\(1\) The Indian Penal Code \(45 of 1860\) is hereby repealed", "BNS s.358(1)"),
    ("C9R-RD-BNS-04", RAW + "d4449e9995b21fd52627811d08f9d21feda6a3678b7e5355b651242d152167f5", "all", r"anything done or any action taken under the said Code shall be deemed to have been done or taken under the corresponding provisions of this Sanhita", "BNS s.358(3) saving"),
    ("C9R-RD-DPP-01", RAW + "0884f3b50114c71f98f9aa0dfea43aaa0d1b0eee3da276591f6d6e2051ecdfca", "all", r"ACT NO\. 40 OF 1950\] \(As on the 21st July, 2025\)", "DPP Act 1950 compilation (Act 40 of 1950) as-on date"),
    ("C9R-RD-DPP-02", RAW + "0884f3b50114c71f98f9aa0dfea43aaa0d1b0eee3da276591f6d6e2051ecdfca", "all", r"The Army and Air Force \(Disposal of Private Property\) Amendment Act, 2000 \(31 of 2000\)", "DPP Amendment Act 2000 = Act 31 of 2000 per compilation list"),
    ("C9R-RD-DPP-03", RAW + "0884f3b50114c71f98f9aa0dfea43aaa0d1b0eee3da276591f6d6e2051ecdfca", "all", r"22nd July, 1950, vide notification No\. S\.R\.O\. 123", "DPP Act commencement footnote (compilation only)"),
    ("C9R-RD-IPC-01", RAW + "fa8878e0208e0942e51bcf7e437efa7b6d25baecb04f4cd83da30df44c977f85", "all", r"THE INDIAN PENAL CODE", "IPC rendering present (India Code Repeal Acts collection)"),
    ("C9R-RD-IEA-01", RAW + "06729a1f84e186ae953798766696a736c344dcbd94da2b0cc2a474e7859378ce", "all", r"it shall come into force on the first day of September, 1872", "IEA rendering present; s.1 commencement 01-09-1872 as printed"),
    ("C9R-RD-AFA-01", RAW + "ef50375ea0550ddc1e6414c45bd9403d3842aa395a297e71e2e627403632ebd0", "all", r"ACT NO\. 45 OF 1950\] \(As on the 21st July, 2025\)", "Air Force Act compilation as-on date"),
    ("C9R-RD-NA-01", RAW + "db6d2b3ef1e60d95f4d8127730430a01a3aab39637d88a39901aa20142399083", "all", r"\(ACT NO\. 62 OF 1957\) \[As on the 1st June, 2026\]", "Navy Act compilation as-on date"),
]

# Page-image readings: (reading_id, source, page, dpi, clip fractions (x0,y0,x1,y1) or None, transcription by the reader)
IMAGE_READINGS = [
    ("C9R-RS-01", RS, 1, 200, None,
     "Rajya Sabha [Debates], 'Papers Laid on the Table', printed cols 207-208; heading 'Criminal Courts and Court Martial "
     "(Adjustment of jurisdiction) Amendment Rules, 1986'; text: 'SHRI P. CHIDAMBARAM ... lay on the Table a copy (in English "
     "and Hindi) of the Ministry of Home Affairs Notification S.O. No. 4010, dated the 6th December, 1986, publishing the "
     "Criminal Courts and Court-Martial (Adjustment of Jurisdiction) Amendment Rules, 1986. [Placed in Library. See No. LT-3868/87]'. "
     "The day reads '6th' (not '8th'). Debate date is not printed on this page."),
    ("C9R-RD-AFT07-IMG", RAW + "338d43addeaa14b7112298f3d460fd18bf8edd7b340b48fce0a546076cf273ef", 1, 110, None,
     "Gazette of India Extraordinary Part II-Section 1, No. 66, New Delhi, Friday, December 28, 2007/Pausa 7, 1929; Ministry of Law and "
     "Justice (Legislative Department); assent of the President on the 25th December, 2007; 'THE ARMED FORCES TRIBUNAL ACT, 2007 No. 55 OF "
     "2007 [25th December, 2007.]'; s.1(2) 'It shall come into force on such date as the Central Government may, by notification, appoint.' "
     "India Code watermark. (raw-data category 'rule', title 'AFT-Act2007': mislabelled in the crawl manifest; content is the Act as published.)"),
    ("C9R-RD-AFTAPPT-IMG", RAW + "8d774f1fcc3358e892a288346d2cad361694abec3f4191d35b34156c29425136", 1, 110, None,
     "Gazette of India Extraordinary Part II-Section 4, No. 8, Friday, August 7, 2009; Ministry of Defence Notification, New Delhi, the 7th "
     "August, 2009: 'S.R.O. 9(E).-In exercise of the powers conferred by Section 4 of the Armed Forces Tribunal Act, 2007 (55 of 2007), the "
     "Central Government hereby establishes the Armed Forces Tribunal with effect from the 10th August, 2009, which shall be the appointed day "
     "within the meaning of clause (c) of Section 3 of the Act.' [F. No. 7(6)/2009/D (AFT Cell)] ANAND MISRA, Jt. Secy. This is NOT the s.1(2) "
     "commencement notification S.O. 14(E)/2008."),
    ("C9R-RD-AFTRDO-IMG1", RAW + "1c6db257efe5ac077d13847177a5c3706375ef92242f1d45d8f2bbabe683e849", 1, 110, (0, 0.25, 1, 0.45),
     "Masthead: Extraordinary, Part II-Section 4, No. 13, New Delhi, Monday, July 21, 2008/Asadha 30, 1930; Ministry of Defence Order, New Delhi, "
     "the 21st July, 2008."),
    ("C9R-RD-AFTRDO-IMG2", RAW + "1c6db257efe5ac077d13847177a5c3706375ef92242f1d45d8f2bbabe683e849", 1, 110, (0, 0.45, 1, 1),
     "'S.R.O. 18(E).-In exercise of the powers conferred by sub-section (1) of Section 40 of the Armed Forces Tribunal Act, 2007 (55 of 2007) ... "
     "1. (1) This Order may be called the Armed Forces Tribunal Act (Removal of Difficulties) Order, 2008. (2) It shall come into force on the date "
     "of its publication in the Official Gazette. 2. In the Armed Forces Tribunal Act, 2007 (55 of 2007), in Section 6, in sub-section (3), in clause "
     "(a), for the word \"and\" occurring at the end, the word \"or\" shall be substituted.' [F No. 7(3)/2008-D (AFT Cell)] AJAY TIRKEY, Jt. Secy."),
    ("C9R-RD-AFTPR08-IMG1", RAW + "590cf7cd393564eacab37566d605357662429f900ea58a96f0ce0e5bb0e0e317", 1, 110, (0, 0.3, 1, 0.42),
     "Masthead: Extraordinary, Part II-Section 4; Hindi date line 'No. 19] ... [Wednesday], September 17, 2008/Bhadra 26, 1930' (English line "
     "below the crop is in the text layer: 'No. 19] NEW DELHI, WEDNESDAY, SEPTEMBER 17, 2008')."),
    ("C9R-RD-AFTPR08-IMG2", RAW + "590cf7cd393564eacab37566d605357662429f900ea58a96f0ce0e5bb0e0e317", 23, 110, (0, 0.2, 1, 0.75),
     "Ministry of Defence Notification, New Delhi, the 17th September, 2008: 'S.R.O. 26(E).-In exercise of the powers conferred by clauses (f), "
     "(g) and (k) of sub-section (2) of Section 41 of the Armed Forces Tribunal Act, 2007 ... 1. Short title and commencement.-(1) These Rules may "
     "be called the Armed Forces Tribunal (Procedure) Rules, 2008. (2) They shall come into force from the date of publication in the Official "
     "Gazette.' Whether p.23 belongs to the same issue as the p.1 masthead is inferred from the single India Code bundle only."),
    ("C9R-RD-AFTPR11-IMG1", RAW + "fc27032fadfe44fdd20f899612d45b690f469bcdc96463ac8ea4ae9f82e29904", 1, 110, (0, 0.28, 1, 0.4),
     "Masthead: Part II-Section 4, No. 4, New Delhi, Friday, July 29, 2011/Sravana 7, 1933."),
    ("C9R-RD-AFTPR11-IMG2", RAW + "fc27032fadfe44fdd20f899612d45b690f469bcdc96463ac8ea4ae9f82e29904", 2, 110, (0, 0, 1, 0.45),
     "p.2 'THE GAZETTE OF INDIA: EXTRAORDINARY [PART II-SEC. 4]'; Ministry of Defence Notification, New Delhi, the 29th July, 2011: 'S.R.O. 05(E).-"
     "... clauses (f), (g) and (k) of sub-section (2) of Section 41 ... rules to amend the Armed Forces Tribunal (Procedure) Rules, 2008 ... (1) "
     "These rules may be called the Armed Forces Tribunal (Procedure) Amendment Rules, 2011. (2) They shall come into force on the date of their "
     "publication in the Official Gazette.' Rule 2: r.7 renumbered as sub-rule (1) and sub-rule (2) (fee payable only for OA, RA, CA, MA, AT) inserted; "
     "rule 3: r.12A inserted."),
    ("C9R-RD-AFTPRAC09-IMG", RAW + "c57b113a310d5ec1a9c06e26a266ef7abf0e039f36cbd83977313bb0790a77ea", 1, 150, None,
     "Running header '[भाग II-खण्ड 4] भारत का राजपत्र : असाधारण' page 99; Ministry of Defence Notification, New Delhi, the 11th May, 2009: "
     "'S.R.O. 6(E).-In exercise of the powers conferred by clauses (f), (g) and (k) of sub-section (2) of section 41 of the Armed Forces Tribunal "
     "Act, 2007 ... 1. Short title and commencement - (1) These rules may be called the Armed Forces Tribunal (Practice) Rules, 2009. (2) They "
     "shall come into force from the date of publication in the official gazette.' No masthead (issue number or publication date) on this page."),
    ("C9R-RD-TRA21-IMG", RAW + "0c2f4e9e023d5d7b72d60797e1df67a7b2d2e340da8fe493a4328940638f0451", 1, 110, None,
     "Gazette of India Extraordinary Part II-Section 1, No. 45, New Delhi, Friday, August 13, 2021/Sravana 22, 1943 (Saka); CG-DL-E-13082021-228989; "
     "assent 13th August, 2021; 'THE TRIBUNALS REFORMS ACT, 2021 No. 33 OF 2021 [13th August, 2021.]'; s.1(2) 'It shall be deemed to have come "
     "into force on the 4th April, 2021.'"),
]


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def md5(p):
    return hashlib.md5(open(p, "rb").read()).hexdigest()


def norm(s):
    return re.sub(r"\s+", " ", s).strip()


import subprocess


class Raw:
    def __init__(self, gitdir, ref="origin/raw-data"):
        self.gitdir, self.ref = gitdir, ref
        self.commit = subprocess.run(["git", "-C", gitdir, "rev-parse", ref], check=True, capture_output=True, text=True).stdout.strip()
        names = subprocess.run(["git", "-C", gitdir, "ls-tree", "-r", "--name-only", ref], check=True, capture_output=True, text=True).stdout.split()
        self.by_sha = {os.path.basename(n).split(".")[0]: n for n in names if n.startswith("data/raw/")}

    def blob(self, sha256):
        path = self.by_sha[sha256]
        data = subprocess.run(["git", "-C", self.gitdir, "show", f"{self.ref}:{path}"], check=True, capture_output=True).stdout
        if hashlib.sha256(data).hexdigest() != sha256:
            raise SystemExit(f"raw blob hash mismatch {sha256}")
        return path, data

    def text(self, path):
        return subprocess.run(["git", "-C", self.gitdir, "show", f"{self.ref}:{path}"], check=True, capture_output=True, text=True).stdout


def open_src(root, raw, src):
    if src.startswith(RAW):
        if raw is None:
            return None, None, None
        path, data = raw.blob(src[len(RAW):])
        return fitz.open(stream=data, filetype="pdf"), f"raw-data@{raw.commit[:8]}:{path}", src[len(RAW):]
    p = os.path.join(root, src)
    return fitz.open(p), src, sha(p)


def main():
    root, repo, outdir = sys.argv[1], sys.argv[2], sys.argv[3]
    check = "--check" in sys.argv
    raw = Raw(sys.argv[sys.argv.index("--rawdata-git") + 1]) if "--rawdata-git" in sys.argv else None
    man = list(csv.DictReader(open(os.path.join(repo, "legal_knowledge/audit_work/SOURCE-LIBRARY-C5/baseline/held_binaries_manifest.csv"))))
    hb = io.StringIO()
    w = csv.writer(hb, lineterminator="\n")
    w.writerow(["held_path", "manifest_sha256", "rehash_sha256", "md5", "bytes", "pages", "hash_check"])
    for r in sorted(man, key=lambda r: r["held_path"]):
        p = os.path.join(root, r["held_path"])
        if not os.path.exists(p):
            w.writerow([r["held_path"], r["rehashed_sha256"], "", "", "", "", "FILE_ABSENT"])
            continue
        s = sha(p)
        try:
            pages = fitz.open(p).page_count if p.lower().endswith(".pdf") else ""
        except Exception:
            pages = "UNREADABLE"
        w.writerow([r["held_path"], r["rehashed_sha256"], s, md5(p), os.path.getsize(p), pages,
                    "MATCH" if s == r["rehashed_sha256"] else "MISMATCH"])
    rb = io.StringIO()
    w2 = csv.writer(rb, lineterminator="\n")
    w2.writerow(["reading_id", "held_path", "sha256", "method", "pattern", "result", "pages", "excerpt", "render_sha256", "purpose", "reader"])
    for rid, src_, mode, pat, purpose in NEEDLES:
        doc, path, shaval = open_src(root, raw, src_)
        if doc is None:
            w2.writerow([rid, src_, "", "", pat, "NOT_RUN_NO_RAWDATA", "", "", "", purpose, READER])
            continue
        pages, excerpt = [], ""
        for i, pg in enumerate(doc):
            t = norm(pg.get_text())  # whitespace-normalised page text
            m = re.search(pat, t)
            if m:
                pages.append(str(i + 1))
                if not excerpt:
                    excerpt = norm(t[max(0, m.start() - 40): m.end() + 160])
        if mode == "absent":
            result = "ABSENT_ALL_PAGES" if not pages else "PRESENT"
        else:
            result = "FOUND" if pages else "NOT_FOUND"
        w2.writerow([rid, path, shaval, f"PyMuPDF {fitz.VersionBind} text layer; regex; mode={mode}; pages={doc.page_count}", pat,
                     result, ";".join(pages), excerpt[:400], "", purpose, READER])
    for rid, src_, page, dpi, clip, tr in IMAGE_READINGS:
        doc, path, shaval = open_src(root, raw, src_)
        if doc is None:
            w2.writerow([rid, src_, "", "", "", "NOT_RUN_NO_RAWDATA", str(page), tr, "", "page-image reading", READER])
            continue
        pg = doc[page - 1]
        kw = dict(dpi=dpi, colorspace=fitz.csGRAY, alpha=False)
        if clip:
            r = pg.rect
            kw["clip"] = fitz.Rect(r.x0 + clip[0] * r.width, r.y0 + clip[1] * r.height, r.x0 + clip[2] * r.width, r.y0 + clip[3] * r.height)
        pix = pg.get_pixmap(**kw)
        rh = hashlib.sha256(pix.tobytes("png")).hexdigest()
        w2.writerow([rid, path, shaval, f"page image: PyMuPDF {fitz.VersionBind} get_pixmap(dpi={dpi}, csGRAY, clip={clip}), viewed and transcribed",
                     "", "IMAGE_READ", str(page), tr, rh, "page-image reading", READER])
    outs = {"held_hashes_c9.csv": hb.getvalue(), "c9_page_readings.csv": rb.getvalue()}
    if raw is not None:
        man = {r["doc_id"]: r for r in csv.DictReader(io.StringIO(raw.text("data/manifest.csv")))}
        rawm = list(csv.DictReader(io.StringIO(raw.text("data/raw_manifest.csv"))))
        ob = io.StringIO()
        w3 = csv.writer(ob, lineterminator="\n")
        w3.writerow(["rawdata_commit", "sha256", "raw_path", "bytes", "content_type", "retrieved_at", "source_url", "doc_id", "parent_doc_id",
                     "category", "title", "original_filename", "manifest_doc_status"])
        for r in sorted(rawm, key=lambda r: (r["parent_doc_id"], r["category"], r["sha256"])):
            if not (r["raw_path"].startswith("data/raw/indiacode/") or r["raw_path"].startswith("data/raw/official_copies/")):
                continue
            if r["content_type"] != "application/pdf":
                continue
            st = man.get(r["doc_id"], {}).get("status", "") if r["doc_id"] else ""
            w3.writerow([raw.commit, r["sha256"], r["raw_path"], r["bytes"], r["content_type"], r["retrieved_at"], r["source_url"],
                         r["doc_id"], r["parent_doc_id"], r["category"], r["title"], r["original_filename"], st])
        outs["rawdata_statutory_holdings.csv"] = ob.getvalue()
    bad = 0
    for name, data in outs.items():
        fp = os.path.join(outdir, name)
        if check:
            ok = os.path.exists(fp) and open(fp).read() == data
            print("CHECK", "OK" if ok else "DIFF", name)
            bad += 0 if ok else 1
        else:
            open(fp, "w").write(data)
            print("wrote", fp)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
