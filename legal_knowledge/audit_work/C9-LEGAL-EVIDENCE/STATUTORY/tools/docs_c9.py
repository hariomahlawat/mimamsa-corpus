"""Markdown documents for C9-STAT (imported by build_stat_c9.py). Counts are computed; wording is fixed."""
import collections
import re

LIMIT = ("Every page reading cited is by an AI agent (Claude Opus 5.5 subagent), not human-confirmed. No legal status, applicability "
         "or commencement date is determined or inferred; compilation footnotes and 'w.e.f.' notes are recorded as compiler statements only.")


def _state(r):
    return re.split(r" \(|;", r["reconciliation_state"])[0]


def docs(ctx, metrics, acq_rows, ready, graph, irows):
    rd = ctx.rd
    out = {}
    st = collections.Counter(_state(r) for r in acq_rows)
    by_pr = collections.defaultdict(list)
    for r in acq_rows:
        if r["pending_branch"]:
            by_pr[r["pending_branch"]].append(r)
    commits = {r["pending_branch"]: r["branch_ref_commit"] for r in acq_rows if r["pending_branch"]}
    gst = collections.Counter(e["status"] for e in graph)
    inst = {r["instrument_id"]: r for r in irows}

    # ------------------------------------------------------------------ acquisition_reconciliation.md
    L = ["# Acquisition reconciliation (C9-STAT)", "", LIMIT, "",
         "Source: `acquisition_reconciliation.csv` (one row per required document). Pending branches were read from locally present "
         "remote-tracking refs in `/home/user/c7` with `git show <ref>:config/sources.yaml` only (no fetch). Refs may lag the remote.", "",
         "## Rows by reconciliation state", "", "| state | rows |", "| --- | --- |"]
    L += [f"| {k} | {v} |" for k, v in sorted(st.items())]
    L += ["", "## Pending acquisition stack (local refs)", "", "| PR | local ref commit | documents first introduced | research copy already held (md5-identical) | already in corpus raw store (same URL) |", "| --- | --- | --- | --- | --- |"]
    for pr in ["PR #8 (ACQ-01)", "PR #17 (ACQ-02)", "PR #23 (ACQ-03)", "PR #9 (DESW allow-list)", "staging (v2.5-staging)"]:
        rows = by_pr.get(pr, [])
        L.append(f"| {pr} | {commits.get(pr, '')} | {len(rows)} | {sum(r['held_state'] == 'HELD_RESEARCH_COPY_MD5_IDENTICAL' for r in rows)} | {sum(r['held_state'] == 'HELD_CORPUS_RAW_SAME_URL' for r in rows)} |")
    L += ["",
          "- **PR #8** (`claude/acq-01-config`): 12 archive.org + 2 India Code documents. The owner authorised batches B1, B2 and B6 on 2026-11-22 (PROGRESS.md on that branch); the PR itself, and a download run, are still unapproved. 9 of its archive.org pins are byte-identical (md5) to research copies already held; S.O. 488/1978, S.O. 4010/1986 and the Act 19/1955 Gazette are not held.",
          "- **PR #17** (`claude/acq-02-config`): all 16 pins are md5-identical to held research copies (they would create record copies with a retrieval log; they add no new text).",
          "- **PR #23** (`claude/acq-03-config`): local ref is 60715342; COORDINATION/PROGRESS_REGISTER.md recorded c0e2a425 at time of writing - the later docs commit is on the branch. Its 3 India Code B5 pins (ACQ03-033..035) use the same bitstream URLs that the approved 2026-11-21 India Code run already fetched into the corpus raw store (raw-data); they are redundant. The archive.org AFT rules copies ACQ03-030..032 are independent second copies; ACQ03-032 may supply the Practice Rules masthead.",
          "- **PR #9** (`claude/desw-allowlist` @97933ccf): lists ER 2023 (49.9 MB), the 13 MB ER 2023 copy and **GMO 2023** with byte sizes only (no hash). C8 said GMO 2023 is not in PR #9; on the local ref it is. DESW robots.txt returned 403, so it remains blocked (fail-closed).",
          "- **Army Act 1950 as enacted** (archive.org in.gazette.e.1950.306, md5 68bcdd4e...) and the Batch A Gazettes (AFT, BNS, BNSS, BSA, the three 2024 notifications, 10 post-2022 S.R.O.s) are pinned only as metadata (C5/C6-02). They are in no configuration PR.",
          "",
          "## Holdings C8 missed: corpus raw store", "",
          f"The corpus raw store `origin/raw-data` @{ctx.raw_commit[:8]} (India Code run approved 2026-11-21, PROGRESS.md) holds {len(ctx.raw)} statutory PDFs (`tools/inputs/rawdata_statutory_holdings.csv`). C8 counted only the scratchpad held binaries, so it missed these. Among them:",
          f"- AFT Act 2007 as published (Gazette Extraordinary No.66, 28-12-2007) - {rd('C9R-RD-AFT07-IMG')} (crawl category 'rule', title 'AFT-Act2007': mislabelled);",
          f"- AFT (Procedure) Rules 2008 {rd('C9R-RD-AFTPR08-IMG2')}, Amendment Rules 2011 {rd('C9R-RD-AFTPR11-IMG2')}, Practice Rules 2009 {rd('C9R-RD-AFTPRAC09-IMG')};",
          f"- AFT Act (Removal of Difficulties) Order 2008 {rd('C9R-RD-AFTRDO-IMG2')} and S.R.O. 9(E)/2009 (establishment, appointed day 10-08-2009) {rd('C9R-RD-AFTAPPT-IMG')} - in no C5/C8 register;",
          f"- Finance Act 2017 {rd('C9R-RD-FIN17-01')} and Tribunals Reforms Act 2021 {rd('C9R-RD-TRA21-IMG')};",
          f"- BNS India Code compilation {rd('C9R-RD-BNS-01')}; DPP Act 1950 compilation {rd('C9R-RD-DPP-02')}; IPC/IEA/CrPC renderings; Air Force and Navy Act compilations.",
          "- The 7 held India Code compilation copies classed PROVENANCE_UNDOCUMENTED (Army Act e47a4265, Army Rules 48f52219, AFT 665863d1 and Hindi 48f57c81, BNSS 572c7988, BSA 554b2b4a, TRA 2026 be619533) are byte-identical to raw-data files that do have retrieval records (source URL, timestamp, crawler run). That is a provenance lead for the owner (AP-C9-02). It is not an authentication.",
          "",
          "## Rows not linked to a P1-P5 instrument", "",
          "Regulations for the Army 1987/1962, RMSAF, Army Orders, Territorial Army instruments, historical RAI/RMS and RAF 1964 (C5-ACQ-12..19, 22..26). These are carried for completeness, with their C5 states.", "",
          "## Limitations", "",
          "- Only refs present locally were read. A PR head on the remote may differ. During this session the local staging ref advanced from ff425a9a to 21e73b83 (Merge PR #39, C8-SOURCES). Its official_copies entries are unchanged, and the acquisition refs (1b948727, b8ee3176, 60715342, 97933ccf) and raw-data (ad77758d) did not move.",
          "- md5 identity of a pin to a held research copy proves byte identity, not authenticity. India Code serves watermarked PDFs, so listing md5s are not comparable.",
          "- The raw-data copies have not been registered in C5 or AUTH-LEDGER. Their classification here is UNREGISTERED_CORPUS_RAW_COPY."]
    out["acquisition_reconciliation.md"] = "\n".join(L) + "\n"

    # ------------------------------------------------------------------ APPROVAL_PACKAGES.md
    pr8 = by_pr.get("PR #8 (ACQ-01)", [])
    A = ["# Approval packages (C9-STAT) - DRAFTS, NOTHING EXERCISED", "", LIMIT, "",
         "`acquisition_manifest_ready.csv` holds ONLY the documents already inside an approved scope: the 14 PR #8 documents of ACQ-01 batches B1, B2 and B6, which the owner authorised on 2026-11-22. Even these still need (1) owner approval/merge of PR #8 and (2) a logged download-run approval under the runbook. Every other acquisition needs one of the new permissions below.", "",
         "| package | scope | documents | authorisation sought | dependent KB records (gross) | notes |", "| --- | --- | --- | --- | --- | --- |"]

    def dep(iids):
        s = set()
        for i in iids:
            r = inst.get(i)
            if r:
                m = re.match(r"(\d+) KB records \(([^)]*)\)", r["linked_research_records"])
                if m:
                    s.update(x for x in m.group(2).split(";") if x and x != "...")
        return len(s)

    A += [
        f"| AP-C9-01 | execute PR #8 (ACQ-01 B1/B2/B6) | {len(pr8)} (ready manifest) | PR #8 approval + download-run approval (scope already authorised) | {dep(['I-CCCM-1978', 'I-CCCM-SO4010-1986', 'I-AA-ACT19-1955', 'I-AA-ACT13-1975'])} (excl. Army Rules chain) | yields the CCCM Rules 1978 and S.O. 4010/1986 (resolves the date dispute by page check), the Act 19/1955 Gazette with Schedule, and record copies of 9 held Army Rules instruments |",
        f"| AP-C9-02 | register corpus raw-store copies; provenance leads | {sum(1 for r in acq_rows if r['held_state'] == 'HELD_CORPUS_RAW')} raw-store documents + 7 held compilations | owner decision: C5 copy rows + AUTH-LEDGER rule-1 review (no download) | {dep(['I-AFT-2007', 'I-AFT-PR-2008', 'I-BNS-2023', 'I-AFT-TRA-2021', 'I-AFT-FIN-2017', 'I-DPP-1950'])} | highest value per effort: the AFT Act as published (89 records) and the AFT rules (43) are already held |",
        f"| AP-C9-03 | A-C5-1 Batch A archive.org Gazettes | Army Act 1950 as enacted, BNSS, BSA, BNS, 3 notifications of 2024, 10 post-2022 S.R.O.s (AFT optional) | A-C5-1 + a NEW crawler-config PR stacked on #8 (none exists) | {dep(['I-AA-1950', 'I-BNSS-2023', 'I-BSA-2023', 'I-BNS-2023'])} | Army Act enacted text: 185 records |",
        f"| AP-C9-04 | PR #17 and PR #23 | 16 + 39 | config approval + download run per source; ACQ03-016 keep/drop; drop ACQ03-033..035 (redundant) | see csv | PR #17 adds record copies only; PR #23 adds the Army Act commencement candidate, ALO 1956, Ord. 1975, Act 20/1983 and hints |",
        "| AP-C9-05 | discovery (no candidate in any register) | S.O. 14(E)/2008; TRA 2026 s.1(2) notification(s); Finance Act 2017 Part XIV notification; S.O. 3912(E)/2019; RAA 1957, 1960; 'S.R.O. 34 of 5-6-1963'; post-BNSS adjustment rules; IPC/CrPC/IEA as at repeal; AFA/NA Gazettes; ISO Act/Rules; Army Act notifications | discovery approval; Indian-network run for egazette (TLS failure from container) | n/a | no download in the discovery step |",
        f"| AP-C9-06 | DESW (A-C5-2) | PRA 2008 Pt I/II, ER 2008, ER/GMO 2023, circulars | A-C5-2 + allow-list extension beyond PR #9 + readable robots.txt (403 now) or owner-side manual retrieval with sha256 | {dep(['I-PRA-2008-PT1', 'I-PRA-2008-PT2', 'I-GMO-2023', 'I-ER-2023', 'I-ER-2008'])} | PR #9 has no integrity pin; add expected sizes and hashes |",
        "| AP-C9-07 | custodian (A-C5-3) + scope P-C6-04-SCOPE | RA 1987/1962, RMSAF, named AOs, E-7/1960, S.R.O. 258/2002 | approval of request text; access-marking handling | see csv | drafts in C8 CUSTODIAN_REQUEST_DRAFTS.md; no correspondence authorised |",
        "| AP-C9-08 | P-C7-02-META | DPP Amendment Act 2000 (the compilation names it Act 31 of 2000) | metadata-only archive.org route, then A-C5-1 | 0 | low consequence |",
        "", "## Gates common to every package", "",
        "- Dry run first. Record retrievals with sha256, md5, size and URL. Page-image check the operative provisions before any finding cites them.",
        "- Acquiring a document never changes a record's legal status. A delta review and legal review follow.",
        "- No HF upload and no push to raw-data without separate approval."]
    out["APPROVAL_PACKAGES.md"] = "\n".join(A) + "\n"

    # ------------------------------------------------------------------ AMENDMENT_GRAPH_FINDINGS.md
    new = [e for e in graph if e["origin"] == "C9-NEW"]
    G = ["# Amendment graph correction package (C9-STAT)", "", LIMIT, "",
         f"`amendment_graph.csv`: {len(graph)} edges ({len(graph) - len(new)} carried from the C8 amendment/commencement matrix and re-statused; {len(new)} new). Status rule: EVIDENCED = a held instrument states the commencement (or is the commencement instrument); UNRESOLVED_COMMENCEMENT = the instrument is held but its commencement is not evidenced by a held primary document; NOT_LOCATED = the amending or commencing instrument is not held (a candidate may be pinned); DISPUTED_PRESERVE_BOTH = the sources disagree, and every reading is kept in `preserved_readings`. Nothing is decided by majority vote. A historical interval is filled only for EVIDENCED edges.", "",
         "| status | edges |", "| --- | --- |"] + [f"| {k} | {v} |" for k, v in sorted(gst.items())] + ["",
         "## Corrections and additions to C8", "",
         f"1. **Army Act 1992 amendments (Act 37/1992).** Re-verified: the compilation prints '(w.e.f. 6-9-1992)' only at p.27 (ss.75-76; s.2), p.36 (s.127; s.11) and p.48 (Chapter XVI; s.19) {rd('C9R-AA-03')}. Every other Act 37/1992 footnote has no date {rd('C9R-AA-04')}. The Gazette scan has no commencement clause {rd('C9R-A37-03')}; it records assent on 06-09-1992 and publication in No.59 of 07-09-1992 {rd('C9R-A37-01')}. All 18 edges stay UNRESOLVED_COMMENCEMENT (AQ-05), with both readings kept.",
         f"2. **Act 13/1975.** No commencement clause {rd('C9R-A13-03')}. 25-01-1975 appears only in the s.4(2) 'as if' saving for actions under the Ordinance {rd('C9R-A13-02')}; the compilation prints 'w.e.f. 25-1-1975' {rd('C9R-AA-09')}. UNRESOLVED_COMMENCEMENT (OQ-A-04).",
         f"3. **AFT Act s.9A chain:** inserted by Finance Act 2017 s.181, with Part XIV in force on notified dates (s.156) {rd('C9R-RD-FIN17-02')}; amended by TRA 2021 s.26 {rd('C9R-RD-TRA21-02')}, deemed in force 04-04-2021 {rd('C9R-RD-TRA21-IMG')} (EVIDENCED); substituted by TRA 2026 Sch. II item 9, which commences by notification, with staged dates allowed {rd('C9R-TRA-02')} (not held). TRA 2021 is repealed by TRA 2026 s.24(1) {rd('C9R-TRA-03')}. C8's 'TRA 2021: provisions affected UNKNOWN' is superseded.",
         f"4. **New AFT instruments:** the Removal of Difficulties Order 2008 (S.R.O. 18(E), 21-07-2008, s.6(3)(a) 'and'->'or', on publication) is EVIDENCED. S.R.O. 9(E)/2009 establishes the Tribunal w.e.f. 10-08-2009, the appointed day under s.3(c); it is not the s.1(2) notification. S.O. 14(E)/2008 remains NOT_LOCATED.",
         "5. **AFT rules:** the Procedure Rules 2008 (S.R.O. 26(E), Gazette No.19 of 17-09-2008) and the Amendment Rules 2011 (S.R.O. 05(E), No.4 of 29-07-2011) both commence on publication and are EVIDENCED. The Practice Rules 2009 (S.R.O. 6(E) of 11-05-2009) are UNRESOLVED_COMMENCEMENT, because the held page carries no masthead.",
         f"6. **NEW discrepancy C9-AG-AR168:** S.R.O. 17(E)/1993 item 31 omits the field-punishment words from r.168(2) {rd('C9R-AR-02')}, yet the India Code Army Rules compilation still prints them {rd('C9R-AR-01')}. It is in no conflict register. Both readings are kept, and no conclusion is drawn on current text. This bears on the reliability of the compilation (48f52219) for other rules.",
         f"7. **S.O. 4010/1986:** DISPUTED_PRESERVE_BOTH. The Rajya Sabha page image reads 'dated the 6th December, 1986' {rd('C9R-RS-01')}. PILOT-01 and ACQ-01 give a notification dated 24-11-1986 with Gazette 06-12-1986. C5 review RV-01's '8 Dec' is contradicted by the C9 read.",
         f"8. **2024 commencement notifications** are distinct, each with its own exceptions: BNS S.O. 850(E) (except s.106(2)) {rd('C9R-RD-BNS-02')}; BNSS S.O. 848(E) (except the First Schedule entry for s.106(2)) {rd('C9R-BNSS-02')}; BSA S.O. 849(E) {rd('C9R-BSA-02')}. None is held, so all are NOT_LOCATED. Repeal provisions: BNSS s.531 {rd('C9R-BNSS-03')}, BSA s.170 {rd('C9R-BSA-03')}, BNS s.358 {rd('C9R-RD-BNS-03')} (corpus raw store copy). These are UNRESOLVED_COMMENCEMENT, with savings recorded.",
         "9. S.R.O. 34/1963 (C8-CR-02), S.R.O. 240/1955 (C8-CR-01) and the S.R.O. 17(E)/2019 Hindi/English footnote (C8-CR-14) are carried as DISPUTED_PRESERVE_BOTH edges. S.R.O. 17(E)/2019 also carries the CMS integrity caveat (C8-CR-03).", "",
         "## Open items", "", "- No Army Act amending instrument after 1992 has been located (not proof that none exists).", "- The Army Rules chain after 06-06-2022 and the gaps AR-001 and AR-030 remain NOT_LOCATED.",
         "- Reserved rule states (r.23(3) CONFLICTING, r.182 OPEN, r.193 OPEN, r.194 PROPOSAL) are carried unchanged."]
    out["AMENDMENT_GRAPH_FINDINGS.md"] = "\n".join(G) + "\n"

    # ------------------------------------------------------------------ UNRESOLVED_MATTERS.md
    U = ["# Specific unresolved matters (C9-STAT)", "", LIMIT, "",
         "## U-1 S.R.O. 34/1963 and the historical notes", "",
         "- **Held:** S.R.O. 34 dated 05-01-1963, a declaration under r.188(e) (No.3 of 19-01-1963, Pt II-S4, p.14; C8-PIC-02/03; copy 4acdb1a8, READY_FOR_OWNER_CONSIDERATION for copy provenance only).",
         "- **What the registers show:** Gazette-printed NOTEs to the 1982-1991 amendments list 'SRO 34 dated 5 Jun 63' among amendments of the Rules (S.R.O. 246/1982 p.413; 44/1985 p.60; 55/1985 p.97; 169/1987 p.197; 302/1987 p.367; 216/1988 p.617; 332/1989 p.736; 44/1991 p.214; 235/1991 p.614; Hindi 278/1985 p.531, 61/1991 p.217). S.R.O. 2(E)/2018 lists 'S.R.O. 34 dated 05th January, 1963' (C8-CR-02). Separately, S.R.O. 240/1955 is dated 25-06-1955 in the 1963 recital and 05-06-1955 in the 2018 Note (C8-CR-01).",
         "- **Missing:** the Part II-S4 issues of June-July 1963, to test whether a distinct S.R.O. 34 of 05-06-1963 exists. Not in any pin.",
         "- **Documentary requirement:** an image-checked copy of any 1963 instrument numbered S.R.O. 34 other than the 05-01-1963 declaration, or a full-issue check showing that none exists.",
         "- **Decision owner:** owner (discovery approval, AP-C9-05); then the legal adviser on any chain effect. Status: DISPUTED_PRESERVE_BOTH (C9-AG-AR-008).", "",
         "## U-2 Army Rule 23 and the '2022 amendment'", "",
         "- **What the registers show:** no register records any amendment to r.23. R23-VERIFY-01 / C5-CF-U-01 examined 31 instruments from 1960-2022 and found none that amends r.23. S.R.O. 6(E)/2022 amends r.16A(4) only (C8 D-AMC-AR-035). C8 review RC-01 (P1) removed an unsupported 'r.23 amended 2022' from EV-016, HCE-010 and SC03. The curated KB/case files contain no record linking r.23 to 2022 (C9 scan of records_658.jsonl and cases_53.jsonl).",
         "- **Held:** the 1954 Gazette (r.23(3) 'not obliged', p.300) and the compilation p.41; C-01 r.23(3) is CONFLICTING (two image checks).",
         "- **Missing:** E-7/1960 (AR-001), S.R.O. 258/2002 (AR-030), anything after 06-06-2022 (AR-036; 10 candidates in C5-ACQ-06), the unopened hints AR-012/013/015 and AR-037..046, and the text-layer-only AR-002..005 and AR-032.",
         "- **Documentary requirement:** the missing instruments, image-checked for any r.23 change.", "- **Decision owner:** legal adviser (C-01 is retained until legal review); owner for A-C5-1 and AP-C9-04.", "",
         "## U-3 Act 37/1992 and commencement of the affected Army Act provisions", "",
         f"- **Held:** the Gazette scan (f11d443e, DOCUMENTED_PRIMARY_COPY): assent 06-09-1992, No.59 of 07-09-1992 {rd('C9R-A37-01')}, no commencement clause {rd('C9R-A37-03')}.",
         f"- **Compilation, verified:** 'w.e.f. 6-9-1992' is printed ONLY at ss.75-76 (p.27), s.127 (p.36) and Ch XVI (p.48) {rd('C9R-AA-03')}. The other provisions (ss.77, 80, 81, 85, 90, 91, 122, 123, 135, 137, 139, 142, 151, 152, 169A, 174, 191) carry undated footnotes {rd('C9R-AA-04')}.",
         "- **Missing:** nothing documentary is known to exist. Whether an Act with no commencement clause takes effect on assent is a legal question (AQ-05). A 1992 corrigendum or notification has not been searched.",
         "- **Documentary requirement:** the adviser's answer to AQ-05; optionally a check of the 1992 Gazette for any notification under the Act.", "- **Decision owner:** legal adviser. Status: 18 edges UNRESOLVED_COMMENCEMENT.", "",
         "## U-4 S.O. 4010/1986 differing dates", "",
         f"- **Held:** the Rajya Sabha papers-laid page (fa51a4b1): 'Notification S.O. No. 4010, dated the 6th December, 1986' {rd('C9R-RS-01')}.",
         "- **Registers:** PILOT-01 T5-02 and ACQ-01 B2 record a notification dated 24-11-1986 published in the Gazette of 06-12-1986, pp.4881-82 (archive item read during discovery). The C5 master title says '6th December 1986'. C5 review RV-01 says '8 Dec 1986'; the C9 image read shows '6th'.",
         "- **Missing:** the notification itself (PR #8, md5 c5eaada9..., within ACQ-01 B2 authorised scope).", "- **Documentary requirement:** a page-image check of the record copy after the PR #8 run.",
         "- **Decision owner:** owner (AP-C9-01). Status: DISPUTED_PRESERVE_BOTH (C9-AG-CCCM-SO4010).", "",
         "## U-5 Rules and procedures dependent on later statutory changes", "",
         f"- Army Act provisions substituted by Act 37/1992 s.14 to refer to the CrPC (in place of the CrPC 1898) {rd('C9R-AA-14')}; Army Rules r.133(3) refers to CrPC 1973 s.340 {rd('C9R-AR-03')}. After BNSS s.531 {rd('C9R-BNSS-03')} and its saving s.531(2)(b) {rd('C9R-BNSS-04')}, how such references read is a legal question. The BNSS commencement notification is not held.",
         "- Army Act s.133 names the Indian Evidence Act 1872 against BSA s.170 (C-07 adviser question).",
         f"- The CCCM Rules 1978 were made under the CrPC; any post-BNSS rules are not located. BNSS s.531(2)(b) deems rules made under the CrPC to be made under BNSS {rd('C9R-BNSS-04')}.",
         f"- r.168(2) and the omission of field punishment by Act 37/1992: the compilation still prints field-punishment words {rd('C9R-AR-01')}, which the 1993 Gazette omits {rd('C9R-AR-02')} (C9-AG-AR168).",
         "- AFT s.9A and the conditions-of-service rules: the operative regime depends on the TRA 2026 commencement notification (not held). The AFT Procedure and Practice Rules are made under s.41 and are not shown to be amended by TRA 2026.",
         "- **Documentary requirement:** the BNS/BNSS/BSA notifications (C5-ACQ-05), the TRA 2026 notification(s), any post-BNSS adjustment rules, and the CCCM Rules 1978 (PR #8).", "- **Decision owner:** legal adviser (interpretation); owner (acquisition approvals).", "",
         "## U-6 Other carried discrepancies", "",
         "- Act 13/1975 'w.e.f. 25-1-1975' (OQ-A-04); S.R.O. 17(E)/2019 Hindi/English footnote (C8-CR-14) and CMS integrity failure (C8-CR-03); AFT Practice Rules publication date not on the held page."]
    out["UNRESOLVED_MATTERS.md"] = "\n".join(U) + "\n"

    # ------------------------------------------------------------------ STATUTORY_C9_FINDINGS.md
    def deps(i):
        return inst[i]["dependent_kb_record_count"] if i in inst else 0
    rank = [
        ("Army Act 1950 Gazette as enacted", "I-AA-1950", "PINNED metadata only; needs a new config PR", "A-C5-1 (AP-C9-03)"),
        ("Army Rules chain: post-2022 S.R.O.s, E-7/1960, S.R.O. 258/2002, hints", "I-AR-1954", "10 metadata pins (no PR); 2 need custodian/Indian network; hints in PR #23", "A-C5-1, PR #23, A-C5-3"),
        ("AFT Act 2007 as published", "I-AFT-2007", "ALREADY HELD (corpus raw) - registration only", "AP-C9-02 (no download)"),
        ("BSA 2023 Gazette", "I-BSA-2023", "PINNED metadata only", "A-C5-1"),
        ("BNSS 2023 Gazette", "I-BNSS-2023", "PINNED metadata only", "A-C5-1"),
        ("AFT Procedure/Practice Rules 2008/2009/2011", "I-AFT-PR-2008", "ALREADY HELD (corpus raw) - registration only; Practice Rules masthead via ACQ03-032", "AP-C9-02"),
        ("PRA 2008 Part I", "I-PRA-2008-PT1", "BLOCKED (robots 403)", "A-C5-2 (AP-C9-06)"),
        ("BNS 2023 Gazette (compilation already held)", "I-BNS-2023", "PINNED metadata; compilation held raw", "A-C5-1; AP-C9-02"),
        ("GMO 2023", "I-GMO-2023", "BLOCKED; listed in PR #9 without hash", "A-C5-2"),
        ("PRA 2008 Part II", "I-PRA-2008-PT2", "BLOCKED", "A-C5-2"),
        ("CCCM Rules 1978 + S.O. 4010/1986", "I-CCCM-1978", "AUTHORISED SCOPE (PR #8) - execution pending", "AP-C9-01"),
        ("BNS/BNSS/BSA commencement notifications", "I-BNSS-COMM-SO848E", "PINNED metadata only (upper bound 114 records)", "A-C5-1"),
        ("AFT commencement S.O. 14(E)/2008 (upper bound 89)", "I-AFT-SO14E-2008", "NO CANDIDATE", "discovery (AP-C9-05)"),
        ("Army Act commencement S.R.O. 120/1950 (upper bound 185)", "I-AA-SRO120-1950", "candidate in PR #23", "PR #23"),
    ]
    F = ["# STATUTORY_C9_FINDINGS (Cycle 9, statutory-source agent)", "", LIMIT, "",
         "Built on the reviewed C8-SOURCES baseline (snapshot 2d7c02cf) and the C8-EVIDENCE Gazette tranche. Regenerate everything with `python3 -I tools/build_stat_c9.py <repo> --evidence-repo <c8ev> [--check]`. The inputs are regenerated with `tools/extract_branch_pins.py` and `tools/collect_readings_c9.py`, both of which have `--check` modes.", "",
         "## 1. Baseline metrics (re-verified)", "",
         "All figures reproduce from the files: 658 KB records; 53 cases; 1,060 crosswalk rows = 983 citation items + 77 NO_CITATION; 42 exact / 652 partial / 289 missing; 618 records with no exact anchor (541 cite something, 77 cite nothing); 10 all-exact and 30 some-exact; cases 6/7/40. All 42 anchors rest on one copy (C5-SRC-P0-ARMY-RULES-1954~C1, sha256 c5ef95a9...). Details and method: `baseline_metrics.json` (all_match = " + str(metrics["all_match"]).lower() + ").", "",
         "## 2. Principal new findings", "",
         f"1. **The corpus raw store was outside C8's gap analysis.** `origin/raw-data` @{ctx.raw_commit[:8]} (approved India Code run, 2026-11-21) already holds the AFT Act 2007 as published, the AFT Procedure Rules 2008, the Amendment Rules 2011 and the Practice Rules 2009, the Finance Act 2017, TRA 2021, the BNS, DPP Act, Air Force Act and Navy Act compilations, and IPC/IEA/CrPC renderings. Ten C8 statements of 'not held' are corrected (see each instrument record). The acquisition need for the AFT Act (89 records) and the AFT rules (43 records) becomes a **registration** need.",
         "2. **Two AFT instruments are in no register:** the Removal of Difficulties Order 2008 (amends s.6(3)(a); EVIDENCED from 21-07-2008) and S.R.O. 9(E)/2009 (Tribunal established w.e.f. 10-08-2009, the appointed day). S.O. 14(E)/2008 (s.1(2)) is still not held.",
         "3. **TRA 2021:** deemed in force 04-04-2021; s.26 amends AFT s.9A. Both EVIDENCED from the corpus copy.",
         "4. **New text discrepancy:** in r.168(2), the compilation still prints field-punishment words that S.R.O. 17(E)/1993 item 31 omits. This is in no conflict register (C9-AG-AR168).",
         "5. **S.O. 4010/1986:** the Rajya Sabha page reads '6th December, 1986', not '8 Dec' (C5 RV-01). The PILOT-01 date 24-11-1986 is preserved as the other reading.",
         "6. **PR #9 does list GMO 2023** (C8 said it did not), with byte sizes only and no hash. PR #23's 3 India Code pins are redundant with the raw store. All 16 PR #17 pins and 9 PR #8 pins are md5-identical to research copies already held.",
         "7. **Provenance lead:** 7 held compilation copies classed PROVENANCE_UNDOCUMENTED match raw-data files that carry retrieval records (owner decision; not authentication).",
         "8. The 1992 'w.e.f. 6-9-1992' printing is confirmed only at ss.75-76, s.127 and Ch XVI. The 2024 commencement notifications are confirmed as three distinct S.O.s (850/848/849(E)), with different exceptions.", "",
         "## 3. Ranked documentary requirements (dependent KB records, gross and overlapping; from C8 gap rows)", "",
         "| rank | requirement | dependent KB records | state | authorisation |", "| --- | --- | --- | --- | --- |"]
    for n_, (name, iid, state, auth) in enumerate(rank, 1):
        F.append(f"| {n_} | {name} | {deps(iid)} | {state} | {auth} |")
    F += ["", "The counts overlap and cannot be added. Acquiring an enacted text does not by itself clear a record whose provision was later amended.", "",
          "## 4. Acquisition-ready (existing approval) vs new approval", "",
          f"- **Ready under existing scope:** {len(ready)} PR #8 documents (ACQ-01 B1/B2/B6, owner-authorised 2026-11-22), listed in `acquisition_manifest_ready.csv`. Gates: PR #8 approval/merge and a logged download run.",
          "- **New approval needed:** AP-C9-02 (registration, no download) to AP-C9-08. See `APPROVAL_PACKAGES.md`.", "",
          "## 5. Amendment graph", "", f"{len(graph)} edges: " + ", ".join(f"{k} {v}" for k, v in sorted(gst.items())) + ". See `AMENDMENT_GRAPH_FINDINGS.md`.", "",
          "## 6. Outputs", "",
          "`instrument_records.csv` + `instruments/*.md` (" + str(len(irows)) + " records); `acquisition_reconciliation.csv/.md`; `acquisition_manifest_ready.csv`; `APPROVAL_PACKAGES.md`; `amendment_graph.csv`; `AMENDMENT_GRAPH_FINDINGS.md`; `UNRESOLVED_MATTERS.md`; `baseline_metrics.json`; `readings_index.csv`; `OUTPUT_SHA256SUMS`; `tools/` (builder, input extractors, inputs). Page renders viewed during reading are not retained; each render sha256 in `readings_index.csv` is recomputed deterministically by `tools/collect_readings_c9.py`.", "",
          "## 7. Limitations", "",
          "- Readings are AI-agent readings and need human re-check from the recorded render hashes before any approval.",
          "- The raw-data blobs were read in memory from the local ref. They are unregistered, and their authenticity is not established.",
          "- The PR refs are local and may lag the remote. No network was used, nothing was downloaded, and no crawler, robots or config file was changed."]
    out["STATUTORY_C9_FINDINGS.md"] = "\n".join(F) + "\n"
    return out
