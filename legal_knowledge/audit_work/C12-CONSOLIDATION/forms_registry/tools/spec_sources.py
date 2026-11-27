"""Source-copy definitions for the C12 Workstream G forms registry.

Every source is identified by an exact byte hash. Paths are resolved against
named roots so the tool can be re-pointed without editing this file:

  scratch  -> the session scratchpad (working store; read-only use)
  c7git    -> git object store of /home/user/c7 at commit C7_COMMIT (blobs read
              with `git cat-file`; nothing is checked out or written)

Nothing here asserts authenticity, currency or legal approval. The
`evidence_class` / `edition_evidence` strings are copied (abridged) from the
C5 source registers or recorded from the copy itself, as stated.
"""

C7_COMMIT = "ad77758d"

# kind: pdf (page-addressed) | lines (derived line-numbered text of a DOC;
#       the original DOC hash is recorded separately, the derived text hash is
#       verified) | gittext (derived text file in c7 git; heading scan only)
SOURCES = {
    # ---------------------------------------------------------------- Army Rules
    "AR54-GAZ": dict(
        kind="pdf", root="scratch",
        path="downloads/discovery/ia_in.gazette.central.w.1954-11-27.103686.pdf",
        sha256="c5ef95a9d553685aa655f041b71d8360d6272e2775a19a3d6e7273c6cbd0aca6",
        c5_copy_id="C5-SRC-P0-ARMY-RULES-1954~C1", c5_source_id="C5-SRC-P0-ARMY-RULES-1954",
        title="Gazette of India No. 47, Pt II-Sec 4, 27 Nov 1954: S.R.O. 484 (Army Rules, 1954) with Appendices",
        edition_evidence="as notified 27-11-1954 (Gazette masthead, p.1); printed pp.291-378",
        evidence_class="HELD_PRIMARY_GAZETTE_FACSIMILE (C5); scanned image with OCR text layer",
        text_quality="OCR", match_mode="fuzzy", access_marking="NONE OBSERVED on page images of pp.2 (upper part), 59-61, 72; other pages not visually checked",
    ),
    "AR54-IC": dict(
        kind="pdf", root="scratch",
        path="downloads/independent-reviewer-A/army-rules.pdf",
        sha256="48f52219121bf74d070bc832e4573f2f512b239e0a0441ba96b1daca2983a727",
        c5_copy_id="C5-SRC-P0-ARMY-RULES-1954-INDIACODE~C1", c5_source_id="C5-SRC-P0-ARMY-RULES-1954-INDIACODE",
        title="Army Rules, 1954: India Code compilation (214 pp.) with notes",
        edition_evidence="India Code compilation; as-on date not printed (C5)",
        evidence_class="HELD_GOVERNMENT_COMPILATION (C5); native text layer",
        text_quality="TEXT", match_mode="exact", access_marking="NOT_CHECKED",
    ),
    "AR-AMD-1965": dict(
        kind="pdf", root="scratch",
        path="downloads/independent-reviewer-D/amend/in.gazette.central.w.1965-04-10.81813/81813.pdf",
        sha256="682afce5e2f1f3ce8381e74664fb2fb8d98a4571c9fb8a92160ff11193a8c046",
        c5_copy_id="C5-SRC-P0-AR-AMD-AR-010~C1", c5_source_id="C5-SRC-P0-AR-AMD-AR-010",
        title="Gazette Pt II-Sec 4 No.15, 10-04-1965: S.R.O. 116 (Army Rules amendment incl. App. I Form No. I)",
        edition_evidence="as published 10-04-1965", evidence_class="Gazette scan with OCR text layer (C5: IMAGE_CHECKED)",
        text_quality="OCR", match_mode="fuzzy", access_marking="NOT_CHECKED",
    ),
    "AR-AMD-1993": dict(
        kind="pdf", root="scratch",
        path="downloads/independent-reviewer-D/amend/in.gazette.central.e.1993-12-06.16490/16490.pdf",
        sha256="e9bf2114ab633716ea954db6e100be858e45949384f9fc0667364308bff46912",
        c5_copy_id="C5-SRC-P0-AR-AMD-AR-029~C1", c5_source_id="C5-SRC-P0-AR-AMD-AR-029",
        title="Gazette Extraordinary Pt II-Sec 4, 06-12-1993: S.R.O. 17(E) (Army Rules amendment incl. Appendices III-V)",
        edition_evidence="as published 06-12-1993", evidence_class="Gazette scan with OCR text layer (C5 LOCATED)",
        text_quality="OCR", match_mode="fuzzy", access_marking="NONE OBSERVED on p.19 image; other pages not visually checked",
    ),
    # ---------------------------------------------------------------- MML (owner-supplied; UNVERIFIED_MANUAL)
    "MML2": dict(
        kind="pdf", root="scratch", path="mml_x/originals/MML 2.pdf",
        sha256="db2119182ed2e4ccca22dd225d955327f6398ee98303e1c94615ba85b4396f65",
        c5_copy_id="C5-SRC-P2-MML-MML-2-PDF~C1", c5_source_id="C5-SRC-P2-MML-MML-2-PDF",
        title="Manual of Military Law (owner-supplied file 'MML 2.pdf'): Army Act 1950 + Army Rules 1954 with notes and appendices",
        edition_evidence="UNDATED PRINTING; imprint 'MGIPRRND-2188 Army/06-10,000' p.339; latest amendment notes 2003 (WS-C ES-02)",
        evidence_class="UNVERIFIED_MANUAL / USER_SUPPLIED / HASH_ONLY (WS-C ES-02); typeset PDF native text layer; printed page = PDF page",
        text_quality="TEXT", match_mode="exact",
        access_marking="NONE document-level on pp.1,339 images; 'CONFIDENTIAL' printed as a form label in App. III Pt IV (p.304)",
    ),
    "MML-AR-DOC1": dict(
        kind="lines", root="scratch", path="repro1/MML vol 2(AR).doc-1.lines.txt",
        sha256="e21396426157dbe6495176cf6410e7ee36b62038b016743f79df621966f88e76",
        original_path="mml_x/originals/MML vol 2(AR).doc-1.doc",
        original_sha256="8bb17d8255ea1be2b975a96b3c739d002264df3da8a56086d29d2a1961f3a162",
        c5_copy_id="C5-SRC-P2-MML-MML-VOL-2-AR--DOC-1~C1", c5_source_id="C5-SRC-P2-MML-MML-VOL-2-AR--DOC-1",
        title="Manual of Military Law (owner-supplied 'MML vol 2(AR).doc-1.doc'): Army Rules 1954 with appendices (DOC transcription)",
        edition_evidence="UNDATED; imprint 'GIPN-S1-609 DMR/ND/80-8-6-83-38500'; latest SRO 17(E) 06-12-1993 (WS-C ES-05)",
        evidence_class="UNVERIFIED_MANUAL (WS-C ES-05); line anchors from WS-C pinned derived text repro1 (input_manifest role mml_derived_text_USED); no stable page mapping",
        text_quality="TEXT", match_mode="exact", access_marking="'CONFIDENTIAL' as form label in Form of Delay Report only (WS-C)",
    ),
    "MML-AR-DOC": dict(
        kind="lines", root="scratch", path="repro1/MML vol 2(AR).doc.lines.txt",
        sha256="278cea66b17c0c4cbc80d3f9b71665f1e860461fb9ae663cf4b02cc7179c9d29",
        original_path="mml_x/originals/MML vol 2(AR).doc.doc",
        original_sha256="ed1d8a7fc1f4088f8d0fb7db6855c195b205b251874a70f611ced5c3fdb494a2",
        c5_copy_id="C5-SRC-P2-MML-MML-VOL-2-AR--DOC~C1", c5_source_id="C5-SRC-P2-MML-MML-VOL-2-AR--DOC",
        title="Manual of Military Law (owner-supplied 'MML vol 2(AR).doc.doc'): Army Rules 1954 with appendices (DOC transcription)",
        edition_evidence="UNDATED; sibling revision of ES-05; latest SRO 17(E) 06-12-1993 (WS-C ES-06)",
        evidence_class="UNVERIFIED_MANUAL (WS-C ES-06); line anchors from repro1 pinned derived text",
        text_quality="TEXT", match_mode="exact", access_marking="'CONFIDENTIAL' as form label in Form of Delay Report only (WS-C)",
    ),
    "MML3": dict(
        kind="pdf", root="scratch", path="mml_x/originals/MML vol 3.pdf.pdf",
        sha256="dfce01c1267dc321acead765aae79764a1a2b45838ac0ba183f1dfec729c68e3",
        c5_copy_id="C5-SRC-P2-MML-MML-VOL-3-PDF~C1", c5_source_id="C5-SRC-P2-MML-MML-VOL-3-PDF",
        title="Manual of Military Law (owner-supplied 'MML vol 3.pdf.pdf'): other Acts and instruments (Word 2010 export)",
        edition_evidence="UNDATED; '1040 DMR&F/80' signature marks; latest date 21-11-1990 (WS-C ES-08)",
        evidence_class="UNVERIFIED_MANUAL (WS-C ES-08); PDF export of DOC transcription, native text layer",
        text_quality="TEXT", match_mode="exact", access_marking="NONE OBSERVED (WS-C)",
    ),
    "MML3-DOC": dict(
        kind="lines", root="scratch", path="repro1/MML vol 3.doc.lines.txt",
        sha256="2153c4306b46d29807d1f61a5fbc4b9647cf84c6f8cc4fd64a468fda71e600be",
        original_path="mml_x/originals/MML vol 3.doc.doc",
        original_sha256="67d788b31e8e2b618bf98b18606b6263a8c497d1ce40c4f9d0a171c3ea1bcad8",
        c5_copy_id="C5-SRC-P2-MML-MML-VOL-3-DOC~C1", c5_source_id="C5-SRC-P2-MML-MML-VOL-3-DOC",
        title="Manual of Military Law (owner-supplied 'MML vol 3.doc.doc') (DOC transcription)",
        edition_evidence="UNDATED; '1040 DMR&F/80' marks (WS-C ES-07)",
        evidence_class="UNVERIFIED_MANUAL (WS-C ES-07); line anchors from repro1 pinned derived text",
        text_quality="TEXT", match_mode="exact", access_marking="NONE OBSERVED (WS-C)",
    ),
    "MML-AA-PDF": dict(
        kind="pdf", root="scratch", path="mml_x/originals/MML vol 2(AA).pdf",
        sha256="c8a791a1e3a4d8fee412cae1b0c2daa4517438bf926c9f9e27fffd81cada1ec9",
        c5_copy_id="C5-SRC-P2-MML-MML-VOL-2-AA--PDF~C1", c5_source_id="C5-SRC-P2-MML-MML-VOL-2-AA--PDF",
        title="Manual of Military Law (owner-supplied 'MML vol 2(AA).pdf'): Army Act 1950 with notes",
        edition_evidence="UNDATED; '609 DMR&F(ND)/80' marks; latest refs 1993 (WS-C ES-04)",
        evidence_class="UNVERIFIED_MANUAL (WS-C ES-04)", text_quality="TEXT", match_mode="exact",
        access_marking="NONE OBSERVED (WS-C)",
    ),
    "MML-AA-DOC": dict(
        kind="lines", root="scratch", path="repro1/MML vol 2(AA).doc.lines.txt",
        sha256="7168985023cdc6fa88ec32b2d40bf0c27bdc7cc7bba9888ddae4748723507e91",
        original_path="mml_x/originals/MML vol 2(AA).doc.doc",
        original_sha256="73fd304227ca680ebf3c8512dfd4aafa0eb2e16952558bb8b1c1edee637a455d",
        c5_copy_id="C5-SRC-P2-MML-MML-VOL-2-AA--DOC~C1", c5_source_id="C5-SRC-P2-MML-MML-VOL-2-AA--DOC",
        title="Manual of Military Law (owner-supplied 'MML vol 2(AA).doc.doc') (DOC transcription)",
        edition_evidence="UNDATED (WS-C ES-03)", evidence_class="UNVERIFIED_MANUAL (WS-C ES-03)",
        text_quality="TEXT", match_mode="exact", access_marking="NONE OBSERVED (WS-C)",
    ),
    "MML1-DOC": dict(
        kind="lines", root="scratch", path="repro1/MML 1.lines.txt",
        sha256="d56c98499f14dd5517519d0240089a5284c3b84ffd93e43de07f6d9a83d8a6ec",
        original_path="mml_x/originals/MML 1.doc",
        original_sha256="3a2e3a4f70669483678cdb96e1dd29d901c6c0ffc43a04a794a00d3ef0c3d1ed",
        c5_copy_id="C5-SRC-P2-MML-MML-1-DOC~C1", c5_source_id="C5-SRC-P2-MML-MML-1-DOC",
        title="Manual of Military Law (owner-supplied 'MML 1.doc'): Part I commentary",
        edition_evidence="UNDATED; content indicators pre-1992 (WS-C ES-01)", evidence_class="UNVERIFIED_MANUAL (WS-C ES-01)",
        text_quality="TEXT", match_mode="exact", access_marking="NONE OBSERVED (WS-C)",
    ),
    # ---------------------------------------------------------------- Other statutes / rules held
    "AA50-IC": dict(
        kind="pdf", root="scratch", path="downloads/independent-reviewer-A/army-act.pdf",
        sha256="e47a4265813e95b491a24926428ed306cfeaae9013e7edb928cefef6e69a7c08",
        c5_copy_id="C5-SRC-P0-ARMY-ACT-1950-INDIACODE~C1", c5_source_id="C5-SRC-P0-ARMY-ACT-1950-INDIACODE",
        title="The Army Act, 1950: India Code compilation (as on 21-07-2025 per C5)",
        edition_evidence="India Code compilation (C5)", evidence_class="HELD_GOVERNMENT_COMPILATION (C5)",
        text_quality="TEXT", match_mode="exact", access_marking="NOT_CHECKED",
    ),
    "RA87-CH5": dict(
        kind="pdf", root="scratch", path="downloads/discovery/indiacode_ra.pdf",
        sha256="4be12283236914c3ba54dbe09a048f234df2e2cd18ddefc482c41d6261afeeed",
        c5_copy_id="C5-SRC-P0-RA-1987-CH5-INDIACODE~C1", c5_source_id="C5-SRC-P0-RA-1987-CH5-INDIACODE",
        title="Regulations for the Army (Revised Edition) 1987, Chapter V (Reserve Forces) extract (India Code)",
        edition_evidence="Revised Edition 1987 (as printed on extract)", evidence_class="HELD_GOVERNMENT_COMPILATION_EXTRACT (C5)",
        text_quality="TEXT", match_mode="exact", access_marking="NOT_CHECKED",
    ),
    "AFT07-IC": dict(
        kind="pdf", root="scratch", path="downloads/independent-reviewer-A/aft.pdf",
        sha256="665863d1abb802f7488eb75f776946e30e72ccec16962da8e2b3ee8f2e023e3b",
        c5_copy_id="C5-SRC-P0-AFT-ACT-2007-INDIACODE~C1", c5_source_id="C5-SRC-P0-AFT-ACT-2007-INDIACODE",
        title="The Armed Forces Tribunal Act, 2007: India Code compilation (English)",
        edition_evidence="as on 01-09-2026 (C5)", evidence_class="HELD_GOVERNMENT_COMPILATION (C5)",
        text_quality="TEXT", match_mode="exact", access_marking="NOT_CHECKED",
    ),
    "AFTPR08-C7": dict(
        kind="pdf", root="c7git",
        path="data/raw/indiacode/0000/590cf7cd393564eacab37566d605357662429f900ea58a96f0ce0e5bb0e0e317.pdf",
        sha256="590cf7cd393564eacab37566d605357662429f900ea58a96f0ce0e5bb0e0e317",
        c5_copy_id="", c5_source_id="C5-SRC-P1-AFT-PROC-RULES (C5 records NOT_HELD_NOT_CHECKED; copy held in c7 git objects)",
        title="Armed Forces Tribunal (Procedure) Rules, 2008: India Code file 'AFT-Procedure-Rules-2008' (Gazette Extraordinary scan)",
        edition_evidence="Gazette of India Extraordinary Pt II-Sec 4 scan via India Code (c7 data/meta rules-aft-procedure-rules-2008)",
        evidence_class="Government site copy (India Code bitstream); scanned with OCR text layer; not in C5 copy register",
        text_quality="OCR", match_mode="fuzzy", access_marking="NONE OBSERVED on page images checked (pp.26, 27, 29 band, 37, 38, 42 upper part, 46, 47; 'IndiaCode' watermark only); other pages not visually checked",
    ),
    "AFTPRA11-C7": dict(
        kind="pdf", root="c7git",
        path="data/raw/indiacode/0000/fc27032fadfe44fdd20f899612d45b690f469bcdc96463ac8ea4ae9f82e29904.pdf",
        sha256="fc27032fadfe44fdd20f899612d45b690f469bcdc96463ac8ea4ae9f82e29904",
        c5_copy_id="", c5_source_id="(not in C5 registers; c7 data/meta rules-aft-amendment-procedure-rules-2011)",
        title="AFT (Procedure) Amendment Rules, 2011: S.R.O. 05(E) of 29-07-2011, Gazette of India Extraordinary Pt II-Sec 4 No. 4 (India Code file, 2 pp.: Hindi p.1, English p.2)",
        edition_evidence="as published 29-07-2011 (masthead p.1; page image checked)",
        evidence_class="Government site copy (India Code bitstream); bilingual scan with text layer; added C12 remediation (WSG-R06)",
        text_quality="OCR", match_mode="fuzzy", access_marking="NONE OBSERVED on pp.1-2 images",
    ),
    "AFTPRAC09-C7": dict(
        kind="pdf", root="c7git",
        path="data/raw/indiacode/0000/c57b113a310d5ec1a9c06e26a266ef7abf0e039f36cbd83977313bb0790a77ea.pdf",
        sha256="c57b113a310d5ec1a9c06e26a266ef7abf0e039f36cbd83977313bb0790a77ea",
        c5_copy_id="", c5_source_id="(not in C5 registers)",
        title="AFT Practice Rules, 2009: India Code file (12 pp.)",
        edition_evidence="India Code bitstream (c7 data/meta rules-aft-practice-rules-2009)",
        evidence_class="Government site copy; OCR text layer; not in C5 copy register",
        text_quality="OCR", match_mode="fuzzy", access_marking="NOT_CHECKED",
    ),
    "DPPR53-C7": dict(
        kind="pdf", root="c7git",
        path="data/raw/indiacode/0000/d969593bbb689144e39a406cab3d6fa806216438871ddf6321ba084e24c9b203.pdf",
        sha256="d969593bbb689144e39a406cab3d6fa806216438871ddf6321ba084e24c9b203",
        c5_copy_id="", c5_source_id="C5-SRC-P1-DPP-ACT-1950 (C5 NOT_HELD_CANDIDATE_LOCATED; rules copy held in c7 git)",
        title="Army and Air Force (Disposal of Private Property) Rules, 1953: India Code file (6 pp.)",
        edition_evidence="India Code bitstream (c7 data/meta)", evidence_class="Government site copy; native text layer",
        text_quality="TEXT", match_mode="exact", access_marking="NOT_CHECKED",
    ),
    "DPPA50-C7": dict(
        kind="pdf", root="c7git",
        path="data/raw/indiacode/1950/0884f3b50114c71f98f9aa0dfea43aaa0d1b0eee3da276591f6d6e2051ecdfca.pdf",
        sha256="0884f3b50114c71f98f9aa0dfea43aaa0d1b0eee3da276591f6d6e2051ecdfca",
        c5_copy_id="", c5_source_id="C5-SRC-P1-DPP-ACT-1950 (C5 NOT_HELD_CANDIDATE_LOCATED; Act copy held in c7 git)",
        title="Army and Air Force (Disposal of Private Property) Act, 1950: India Code file",
        edition_evidence="India Code bitstream (c7 data/meta)", evidence_class="Government site copy",
        text_quality="TEXT", match_mode="exact", access_marking="NOT_CHECKED",
    ),
    "RAF2000-C7": dict(
        kind="pdf", root="c7git",
        path="data/raw/indiacode/0000/4284820e5bc2fb7f52ae9fbe8a61650f1579e9b6389ba206a916a69fed016b14.pdf",
        sha256="4284820e5bc2fb7f52ae9fbe8a61650f1579e9b6389ba206a916a69fed016b14",
        c5_copy_id="", c5_source_id="C5-SRC-P2-RAF-1964 (C5: NOT_HELD_CANDIDATE_LOCATED; 'For Official Use Only' reported in search)",
        title="Regulations for the Air Force, reprinted edition 2000 (India Code file)",
        edition_evidence="reprinted edition 2000 (c7 data/meta title)", evidence_class="Government site copy; access marking to be checked",
        text_quality="TEXT", match_mode="exact", access_marking="C5 reports 'For Official Use Only' in search results; not checked here",
    ),
}

# Derived c7 texts examined by heading scan only (not itemised this cycle).
GITTEXT_SCANS = [
    ("data/text/regs-regulations-for-the-navy-part-i.txt", "Regulations for the Navy Part I (c7 derived text)"),
    ("data/text/regs-regulations-for-the-navy-part-ii.txt", "Regulations for the Navy Part II (c7 derived text)"),
    ("data/text/regs-regulations-for-the-navy-part-iii.txt", "Regulations for the Navy Part III (c7 derived text)"),
    ("data/text/regs-regulations-for-the-navy-part-iv.txt", "Regulations for the Navy Part IV (c7 derived text)"),
    ("data/text/regs-the-navy-pension-regulations-1964.txt", "Navy Pension Regulations 1964 (c7 derived text)"),
    ("data/text/act-bnss-2023-sched-the-second-schedule.txt", "BNSS 2023 Second Schedule (forms) (c7 derived text)"),
    ("data/text/act-crpc-1973-consolidated.txt", "CrPC 1973 consolidated incl. Second Schedule (c7 derived text; repealed w.e.f. 01-07-2024 subject to savings)"),
    ("data/text/act-air-force-1950.txt", "Air Force Act 1950 (c7 derived text)"),
    ("data/text/act-navy-1957.txt", "Navy Act 1957 (c7 derived text)"),
    ("data/text/rules-aft-procedure-investigation-rules-2008.txt", "AFT (Procedure for Investigation...) Rules 2008 (c7 derived text)"),
]
