#!/usr/bin/env python3
"""Build the C8 Workstream B (Gazette tranche 1) evidence outputs. Offline.

Usage:
  python -I build_c8b.py --base <repo snapshot root> --out <c8out/B>

Inputs (read-only): tranche1 files, C6-01 recovery register, ARMY-RULES-CHAIN-01
register, ACQ-01/ACQ-02 archive metadata snapshots; plus C8 work files in --out:
render_log.csv, crop_log.csv, tools/readings_notes.txt (AI-agent page readings),
bd_work/T1-19.json, bd_work/T1-20.json, bd_work/*_rsa_diag.json.
Outputs (in --out): page_image_checks_c8.csv, gazette_evidence_register.csv,
evidence/T1-NN.md, contradiction_register_c8.csv, eligibility_recommendations.csv,
born_digital_structure.csv.
Nothing in --base is written.
"""
import argparse, csv, json, os, re

READER = "AI agent (Claude Opus 5.5 subagent), not human-confirmed"
CHECKED_ON = "2026-11-23"
AW = "legal_knowledge/audit_work"

# Per-check metadata decided on the page images (what was read, result, discrepancies).
# key: (tranche, pdf_page)
CHECKS = {
 ('T1-01', 1): ("masthead (issue no., date, Part/Section) + S.R.O. heading, date line, short title, signature block", "CONFIRMED", "none: S.R.O. 1, 22-12-1961, No.1, 06-01-1962, Pt II-S4, p.1 all legible and consistent with the register"),
 ('T1-02', 1): ("masthead (issue no., date, Part/Section) of the issue carrying S.R.O. 34", "CONFIRMED", "none: No.3, 19-01-1963, PART II-Section 4 consistent with the register"),
 ('T1-02', 2): ("S.R.O. heading, date line, nature (declaration), signature block; running header", "CONFIRMED", "none against the register identity (S.R.O. 34, 05-01-1963, p.14, r.188(e) declaration). The page gives no basis to equate this instrument with the 'S.R.O. 34 dated 5-6-1963' of the Government notes (see C8-CR-02, UNRESOLVED). Running header ends '[PART II-' (section on the masthead page)"),
 ('T1-03', 1): ("masthead (issue no., date, Part/Section)", "CONFIRMED", "none; register gives no issue number - image shows No. 13 (addition, not a conflict)"),
 ('T1-03', 12): ("S.R.O. heading, date line, short title, signature block; running header", "CONFIRMED", "none: S.R.O. 126, 12-03-1964, p.282 consistent"),
 ('T1-04', 1): ("masthead (issue no., date, Part/Section)", "CONFIRMED", "none: No.15, 10-04-1965, PART II-Section 4 consistent"),
 ('T1-04', 2): ("S.R.O. heading, date line, short title; running header", "CONFIRMED", "none: S.R.O. 116, 27-03-1965, p.96 consistent; short title printed '(1st Amendment)' (already recorded in PIC-37). Signature on p.97 not re-rendered in C8"),
 ('T1-05', 1): ("masthead (issue no., date, Part/Section)", "CONFIRMED", "none: No.27, 03-07-1965, PART II-Section 4 consistent"),
 ('T1-05', 2): ("S.R.O. heading, date line, short title, signature block; running header", "CONFIRMED", "none: S.R.O. 215, 17-06-1965, p.172 consistent"),
 ('T1-06', 1): ("masthead (issue no., date, Part/Section) + S.R.O. heading, date line, short title", "CONFIRMED", "none: S.R.O. 5, 23-12-1968, No.2, 11-01-1969, p.9 consistent; short title printed with a blank ordinal '(——— Amendment)'"),
 ('T1-07', 1): ("masthead (issue no., date, Part/Section)", "CONFIRMED", "none: No.30, 28-07-1979, PART II-Section 4 consistent"),
 ('T1-07', 6): ("S.R.O. heading, date line, short title, commencement; running header", "CONFIRMED", "none: S.R.O. 188, 04-06-1979, p.258 consistent"),
 ('T1-08', 1): ("masthead (issue no., date, Part/Section)", "CONFIRMED", "none; register gives no issue number - image shows No. 45"),
 ('T1-08', 11): ("S.R.O. heading, date line, short title, file no., NOTE of previous S.R.O.s; running header", "CONFIRMED", "none against the register (S.R.O. 246, 12-10-1982, p.413). Context for C8-CR-02: the printed NOTE lists 'SRO 34 dated 5 Jun 63'. No signatory name printed under the English text (file no. only)"),
 ('T1-09', 1): ("masthead (issue no., date, Part/Section)", "CONFIRMED", "none; register gives no issue number - image shows No. 6"),
 ('T1-09', 2): ("S.R.O. heading, date line, short title, signature block, NOTE; running header", "CONFIRMED", "none: S.R.O. 44, 24-01-1985, p.60 consistent. NOTE lists 'SRO 34 dated 5 jun 1963' (context for C8-CR-02)"),
 ('T1-10', 1): ("masthead (issue no., date, Part/Section)", "CONFIRMED", "none; register gives no issue number - image shows No. 9"),
 ('T1-10', 11): ("S.R.O. heading, date line, short title, signature block, NOTE; running header", "CONFIRMED", "none: S.R.O. 55, 22-02-1985, p.97 consistent. NOTE lists 'SRO 34 dated 5th June, 1963'"),
 ('T1-11', 1): ("masthead (issue no., date, Part/Section)", "CONFIRMED", "none; register gives no issue number - image shows No. 14; Part/Section printed 'PART II-Section IV' (Roman numeral)"),
 ('T1-11', 2): ("CORRIGENDUM heading, date line, S.R.O. number, corrigendum target, signature block; running header", "CONFIRMED", "none: S.R.O. 68, 01-04-1985, corrigendum to S.R.O. 55 (Gazette Pt II s.4, 09-03-1985, p.97, col.1 line 20 'or'->'of'), p.142 consistent. Observation C8-CR-08: file no. printed '4(2)/884/D (AG)' vs '4(2)|84|D(AG)' on S.R.O. 55"),
 ('T1-12', 1): ("masthead (issue no., date, Part/Section)", "CONFIRMED", "none; register gives no issue number - image shows No. 50"),
 ('T1-12', 31): ("S.R.O. heading, date line, short title, commencement; running header", "CONFIRMED", "none: S.R.O. 278, 29-11-1985, p.531 consistent. Signature on p.532 not re-rendered in C8 (recorded in PIC-34)"),
 ('T1-13', 1): ("masthead (issue no., date, Part/Section)", "CONFIRMED", "none; register gives no issue number - image shows No. 21"),
 ('T1-13', 5): ("S.R.O. heading, date line, short title, NOTE; running header", "CONFIRMED", "none: S.R.O. 169, 15-05-1987, p.197 consistent. Observation C8-CR-09: no file number or signatory is printed for the English S.R.O. 169 text on this page"),
 ('T1-14', 1): ("masthead (issue no., date, Part/Section)", "CONFIRMED", "none; register gives no issue number - image shows No. 38. Observation C8-CR-10: section sub-heading printed 'Orders and Notifications issued by the Ministry of Defence'"),
 ('T1-14', 21): ("S.R.O. heading, date line, short title, signature block, NOTE; running header", "PARTIAL", "S.R.O. 302, '18th September, 1987', short title and signatory legible and consistent; running header (Hindi only) legible for 'अक्तूबर 10' but the last digit of the Saka year is degraded and no Gregorian year is legible on this page - issue year taken from the masthead check C8-PIC for p.1 (No.38, 10-10-1987). Print quality poor (broken glyphs)"),
 ('T1-15', 1): ("masthead (issue no., date, Part/Section)", "CONFIRMED", "none: No.36, 17-09-1988, PART II-Section 4 consistent"),
 ('T1-15', 9): ("S.R.O. heading, date line, short title, commencement, signature block; running header", "CONFIRMED", "none: S.R.O. 216, 30-08-1988, p.617 consistent"),
 ('T1-16', 1): ("masthead (issue no., date, Part/Section)", "CONFIRMED", "none; register gives no issue number - image shows No. 46"),
 ('T1-16', 12): ("S.R.O. heading, date line, short title, signature block, NOTE, printer line; running header", "CONFIRMED", "none: S.R.O. 332, 26-09-1989, p.736, 02-12-1989 consistent"),
 ('T1-17', 1): ("masthead (issue no., date, Part/Section)", "CONFIRMED", "none; register gives no issue number - image shows No. 8"),
 ('T1-17', 2): ("S.R.O. 44 heading, date line, short title, commencement, signature block; running header", "PARTIAL", "S.R.O. 44, '1st February, 1991', short title and signatory legible and consistent; the day digits of the English running header ('FEBRUARY 2?, 1991/PHALGUNA 4, 1912') are illegible - issue date taken from the p.213 masthead check (No.8, 23-02-1991). Observation C8-CR-11: short title printed 'Army (Second Amendment) Rules, 1990'"),
 ('T1-17', 5): ("S.R.O. 61 heading, date line, short title, commencement, signature block; running header", "CONFIRMED", "none: S.R.O. 61, 07-02-1991, p.217, 23-02-1991 consistent. Observations C8-CR-11/12: short title printed '...Rules, 1990'; enacting formula printed 'Army Act 1960 (46 of 1950)'"),
 ('T1-18', 1): ("masthead (issue no., date, Part/Section) + Hindi version heading", "CONFIRMED", "none; register gives no issue number - image shows No. 41"),
 ('T1-18', 2): ("S.R.O. heading, date line, short title, signature block, NOTE; running header", "PARTIAL", "S.R.O. 235, '1st October, 1991' (glyphs of '1st' broken but legible; Hindi '1 अक्तूबर, 1991' on p.613 agrees), short title and signatory legible and consistent; month/day of the English running header ('N?VEMBER 9, 1991/KARTIKA 18, 1913') faint and broken - issue date taken from the p.613 masthead check (No.41, 09-11-1991)"),
 ('T1-19', 1): ("masthead (Extraordinary, issue no., date, Part/Section) + Hindi version", "CONFIRMED", "none: Extraordinary, PART II-Section 4, No. 02, 20-02-2018 consistent (register gives no issue no.; image shows No. 02)"),
 ('T1-19', 2): ("S.R.O. heading, date line, nature (declaration), signature block, Note, visible digital-signature appearance; running header", "CONFIRMED", "none against the register (S.R.O. 2(E), 20-02-2018, p.2, r.188(e) declaration). NEW C8-CR-01: Note dates 'S.R.O. 240 dated 05th June, 1955' whereas held S.R.O. 34/1963 recites 'SRO 240, dated the 25th June, 1955'. The visible 'Digitally signed by RAKESH SUKUL' appearance is an image/text element, not a validation"),
 ('T1-20', 1): ("masthead (Extraordinary, issue no., date, Part/Section)", "CONFIRMED", "none: Extraordinary, PART II-Section 4, No. 13, 28-12-2019 consistent"),
 ('T1-20', 2): ("S.R.O. heading, date line, short title, commencement, signature block, Foot Note; running header", "CONFIRMED", "none: S.R.O. 17(E), 28-12-2019, p.2 consistent"),
}

# Facts as printed, from the C8 page readings (AI agent, not human-confirmed).
FACTS = {
 'T1-01': dict(issue="No. 1, Saturday 06-01-1962 (weekly)", part="Part II-Section 4", sro="S.R.O. 1", dateline="New Delhi, the 22nd December 1961", nature="amendment: Army (Second Amendment) Rules, 1961 (r.187(1))", sign="[No. 95678|PSI.] S. DEVANATH, Dy. Secy.", pages="printed p.1 (PDF p.1)"),
 'T1-02': dict(issue="No. 3, Saturday 19-01-1963 (weekly)", part="Part II-Section 4", sro="S.R.O. 34", dateline="New Delhi, the 5th January 1963", nature="declaration under r.188(e) Army Rules 1954 (in supersession of notifications 609/1950, SRO 8/1951, 210/1951, 240/1955, 399/1955, 176/1956); no short title; not an amendment", sign="[No. 25003|PSI.] S. DEVANATH, Dy. Secy.", pages="printed p.14 (PDF p.2)"),
 'T1-03': dict(issue="No. 13, Saturday 28-03-1964 (weekly)", part="Part II-Section 4", sro="S.R.O. 126", dateline="New Delhi, the 12th March 1964", nature="amendment: Army (Amendment) Rules, 1964 (r.13(2A) ins.)", sign="[File No. 8(1)|61|D(AG.II).] S. DEVANATH, Dy. Secy.", pages="printed p.282 (PDF p.12)"),
 'T1-04': dict(issue="No. 15, Saturday 10-04-1965 (weekly)", part="Part II-Section 4", sro="S.R.O. 116", dateline="New Delhi, the 27th March 1965", nature="amendment: Army (1st Amendment) Rules, 1965 (Table below r.13; App. I)", sign="not re-read in C8 (on p.97; WSA-PIC-38: S. DEVANATH, Dy. Secy.)", pages="printed pp.96-97 (PDF pp.2-3)"),
 'T1-05': dict(issue="No. 27, Saturday 03-07-1965 (weekly)", part="Part II-Section 4", sro="S.R.O. 215", dateline="New Delhi, the 17th June 1965", nature="amendment: Army (2nd Amendment) Rules, 1965 (proviso to r.192)", sign="[Case No. 43448|PS1.] S. DEVANATH, Dy. Secy.", pages="printed p.172 (PDF p.2)"),
 'T1-06': dict(issue="No. 2, Saturday 11-01-1969 (weekly)", part="Part II-Section 4", sro="S.R.O. 5", dateline="New Delhi, the 23rd December 1968", nature="amendment: Army (——— Amendment) Rules, 1968 (r.13-A ins.)", sign="not re-read in C8 (on p.10; PIC-33: S. Devanath)", pages="printed pp.9-10 (PDF pp.1-2)"),
 'T1-07': dict(issue="No. 30, Saturday 28-07-1979 (weekly)", part="Part II-Section 4", sro="S.R.O. 188", dateline="New Delhi, the 4th June, 1979", nature="amendment: Army (Amendment) Rules 1979; in force on publication", sign="not re-read in C8 (instrument continues to p.261)", pages="printed pp.258-261 (PDF pp.6-9)"),
 'T1-08': dict(issue="No. 45, Saturday 13-11-1982 (weekly)", part="Part II-Section 4", sro="S.R.O. 246", dateline="New Delhi, the 12th October, 1982", nature="amendment: Army (Amendment) Rules, 1982 (r.59A ins.)", sign="[File No 95678/AG/DV-1|934-S|D (AG)]; no signatory name printed under the English text", pages="printed p.413 (PDF p.11)"),
 'T1-09': dict(issue="No. 6, Saturday 16-02-1985 (weekly)", part="Part II-Section 4", sro="S.R.O. 44 (1985)", dateline="New Delhi, the 24th January, 1985", nature="amendment: Army (Amendment) Rules, 1985 (r.184 subs.)", sign="[File No. B|80290|JAG/449(AG)] PAVAN RAINA, Director (Works)", pages="printed p.60 (PDF p.2)"),
 'T1-10': dict(issue="No. 9, Saturday 09-03-1985 (weekly)", part="Part II-Section 4", sro="S.R.O. 55", dateline="New Delhi, the 22nd February, 1985", nature="amendment: Army (Amendment) Rules, 1985 (r.80-A ins.; r.164 amended)", sign="[File No. 4(2)|84|D(AG)] V. M. LABROO, Dy. Secy. (AG)", pages="printed p.97 (PDF p.11)"),
 'T1-11': dict(issue="No. 14, Saturday 20-04-1985 (weekly)", part="Part II-Section IV (masthead) / PART II-SEC. 4 (running header)", sro="S.R.O. 68", dateline="New Delhi, the 1st April, 1985", nature="CORRIGENDUM to S.R.O. 55 (Army (Amendment) Rules, 1985; Gazette Pt II s.4, 09-03-1985, p.97, col.1, line 20: after 'trial' for 'or' read 'of')", sign="[File No. 4(2)/884/D (AG)] V. M. LABROO, Dy. Secy. (AG)", pages="printed p.142 (PDF p.2)"),
 'T1-12': dict(issue="No. 50, Saturday 28-12-1985 (weekly)", part="Part II-Section 4", sro="S.R.O. 278", dateline="New Delhi, the 29th November, 1985", nature="amendment: Army (Third Amendment) Rules, 1985; in force on publication (r.16-A(5))", sign="not re-read in C8 (on p.532; PIC-34: M.S. Sokhanda)", pages="printed pp.531-532 (PDF pp.31-32)"),
 'T1-13': dict(issue="No. 21, Saturday 30-05-1987 (weekly)", part="Part II-Section 4", sro="S.R.O. 169", dateline="New Delhi, the 15th May, 1987", nature="amendment: Army (Amendment) Rules, 1987 (r.147 subs.)", sign="no file number or signatory printed for the English text on p.197 (as read)", pages="printed p.197 (PDF p.5)"),
 'T1-14': dict(issue="No. 38, Saturday 10-10-1987 (weekly)", part="Part II-Section 4", sro="S.R.O. 302", dateline="New Delhi, the 18th September, 1987", nature="amendment: Army (Amendment) Rules, 1987 (r.193 subs.)", sign="M. S. SOKHANDA, Dy. Secy. (A.G.) (no file no. printed in the English block)", pages="printed p.367 (PDF p.21)"),
 'T1-15': dict(issue="No. 36, Saturday 17-09-1988 (weekly)", part="Part II-Section 4", sro="S.R.O. 216", dateline="New Delhi, the 30th August, 1988", nature="amendment: Army (Amendment) Rules, 1988; in force on publication; items deemed from 04-06-1979", sign="[File No. PC A/39123/AG/PS 2(a)/5792/D(AG)] M. S. SOKHANDA, Dy. Secy. (AG)", pages="printed p.617 (PDF p.9)"),
 'T1-16': dict(issue="No. 46, Saturday 02-12-1989 (weekly)", part="Part II-Section 4", sro="S.R.O. 332", dateline="New Delhi, the 26th September, 1989", nature="amendment: Army (Amendment) Rules, 1989 (r.194 subs.)", sign="[F. No. PCA/39123/AG/PS2(A)/5792|D(AG)] BHAG MALL, Dy. Secy. (AG)", pages="printed p.736 (PDF p.12)"),
 'T1-17': dict(issue="No. 8, Saturday 23-02-1991 (weekly)", part="Part II-Section 4", sro="S.R.O. 44 (1991); S.R.O. 61 (1991)", dateline="New Delhi, the 1st February, 1991 (S.R.O. 44); New Delhi, the 7th February, 1991 (S.R.O. 61)", nature="amendments: 'Army (Second Amendment) Rules, 1990' (S.R.O. 44; r.16A(5)(g)); 'Army (Amendment) Rules, 1990' (S.R.O. 61; r.15-A(3),(4)); both in force on publication", sign="S.R.O. 44: [File No. PC: B/32232/RVC/AG|PS2(a)|172|D(AG)] BHAG MALL, Dy. Secy.; S.R.O. 61: [File No. B/32284/AG/PS2(a)|7763|D(AG)] BHAG MALL, Dy. Secy. (AG)", pages="printed p.214 (PDF p.2) and p.217 (PDF p.5)"),
 'T1-18': dict(issue="No. 41, Saturday 09-11-1991 (weekly)", part="Part II-Section 4", sro="S.R.O. 235", dateline="New Delhi, the 1st October, 1991", nature="amendment: Army (Amendment) Rules, 1991; in force on publication (r.13A)", sign="[Case No. 00470|DP-SCN|MS8C|5652|D(AG)] A. P. JOSHI, Dy Secy.(AG)", pages="printed p.614 (PDF p.2)"),
 'T1-19': dict(issue="Extraordinary No. 02, Tuesday 20-02-2018", part="Part II-Section 4", sro="S.R.O. 2(E)", dateline="New Delhi, the 20th February, 2018", nature="declaration under r.188(e) Army Rules 1954; Note amends S.R.O.s 609/1950 ... 34/1963 'from the date of this notification'; not an amendment of the Rules", sign="[F. No. 23(20)/2009/D(GS-III-B)] RAJEEV SINGH THAKUR, Jt. Secy.; visible appearance 'Digitally signed by RAKESH SUKUL Date: 2018.02.20 19:22:55 +05'30''", pages="printed p.2 (PDF p.2; Hindi version p.1)"),
 'T1-20': dict(issue="Extraordinary No. 13, Saturday 28-12-2019", part="Part II-Section 4", sro="S.R.O. 17(E)", dateline="New Delhi, the 28th December, 2019", nature="amendment: Army (Amendment) Rules, 2019; in force on publication (r.15B ins.; r.16A)", sign="[F. No. F.14(3)/98/D(AG)] M. SUBBARAYAN, Jt. Secy.", pages="printed p.2 (PDF p.2; Hindi version p.1-2)"),
}


AUTH = {
 'T1-14': "Ministry of Defence (section heading 'Orders and Notifications issued by the Ministry of Defence'; operative words 'the Central Government')",
 'T1-19': "'MINISTRY OF DEFENCE' 'NOTIFICATION' (Extraordinary; operative words 'the Central Government'); signed RAJEEV SINGH THAKUR, Jt. Secy.",
 'T1-20': "'MINISTRY OF DEFENCE (Department of Defence)' 'NOTIFICATION' (Extraordinary; operative words 'the Central Government'); signed M. SUBBARAYAN, Jt. Secy.",
}


def rd(p):
    return list(csv.DictReader(open(p, newline='', encoding='utf-8')))


def wr(p, rows, fields):
    with open(p, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, '') for k in fields})


def parse_notes(path):
    notes = {}
    for ln in open(path, encoding='utf-8'):
        m = re.match(r'(T1-\d\d) p(\d+) \(printed ([^)]*)\): (.*)', ln.rstrip('\n'))
        if not m:
            continue
        t, p, pp, txt = m.group(1), int(m.group(2)), m.group(3), m.group(4)
        # split transcription from agent commentary
        cut = len(txt)
        for tok in [' CONFIRMED', ' NEW CONTEXT', ' NEW DOCUMENT', ' Observation', ' Crop ', ' Crops ', ' Image quality', ' Print degraded', ' No signatory', ' No CG-DL', ' No digital', ' No file number', ' No reference', ' No short title']:
            i = txt.find(tok)
            if i != -1 and i < cut:
                cut = i
        comm = re.sub(r'CONFIRMED(\s*\([^)]*\))?\.?', '', txt[cut:]).strip()
        comm = re.sub(r'\s+', ' ', comm)
        notes[(t, p)] = (pp.split(';')[0].strip(), txt[:cut].strip(), comm)
    return notes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    B = os.path.join(a.base, AW)
    T = os.path.join(B, 'AUTH-LEDGER/tranches/T1-GAZETTE')
    O = a.out
    src = rd(os.path.join(T, 'tranche1_source_register.csv'))
    mat = {r['tranche_id']: r for r in rd(os.path.join(T, 'evidence_verification_matrix.csv'))}
    con = rd(os.path.join(T, 'contradiction_register.csv'))
    rec = {r['copy_id']: r for r in rd(os.path.join(B, 'C6-01-PROVENANCE/registers/provenance_recovery_register.csv'))}
    arc = {r['instr_id']: r for r in rd(os.path.join(B, 'ARMY-RULES-CHAIN-01/army_rules_instrument_register.csv'))}
    snap1 = json.load(open(os.path.join(B, 'ACQ-01/archive_org_metadata_snapshot.json')))
    snap2 = json.load(open(os.path.join(B, 'ACQ-02/archive_org_metadata_snapshot_acq02.json')))
    rlog = rd(os.path.join(O, 'render_log.csv'))
    clog = rd(os.path.join(O, 'crop_log.csv'))
    notes = parse_notes(os.path.join(O, 'tools/readings_notes.txt'))
    bd = {t: json.load(open(os.path.join(O, f'bd_work/{t}.json'))) for t in ('T1-19', 'T1-20')}
    rsa = {t: json.load(open(os.path.join(O, f'bd_work/{t}_rsa_diag.json'))) for t in ('T1-19', 'T1-20')}

    # ---- page image checks
    order = sorted(rlog, key=lambda r: (r['tranche_id'], int(r['pdf_page'])))
    srcmap = {r['tranche_id']: r for r in src}
    checks = []
    cid = {}
    for i, r in enumerate(order, 1):
        t, p = r['tranche_id'], int(r['pdf_page'])
        what, res, disc = CHECKS[(t, p)]
        pp, reading, comm = notes[(t, p)]
        crops = [c for c in clog if c['source_png'] == r['png']]
        cs = '; '.join(f"crop {c['crop_png']} sha256 {c['crop_sha256']} (box px {c['box_px']}, Lanczos x{c['scale']}, from this render)" for c in crops)
        if r['hash_check'] != 'MATCH':
            raise SystemExit('hash mismatch ' + t)
        k = f"C8-PIC-{i:02d}"
        cid[(t, p)] = k
        checks.append(dict(check_id=k, tranche_id=t, source_id=srcmap[t]['source_id'], document_sha256=r['sha256'],
                           pdf_page=p, printed_page=pp, what_was_read=what, reading=reading, identity_result=res,
                           discrepancies=disc + (('; reader note: ' + comm) if comm else ''),
                           render_png_sha256=r['png_sha256'],
                           render_settings=f"{r['render_settings']}; output {r['width']}x{r['height']} px 8-bit gray; file renders/{r['png']} (not committed)" + (('; ' + cs) if cs else ''),
                           reader=READER, checked_on=CHECKED_ON))
    # cross-reference placeholders in discrepancy texts
    for c in checks:
        if c['tranche_id'] in ('T1-14', 'T1-17', 'T1-18') and c['identity_result'] == 'PARTIAL':
            c['discrepancies'] = c['discrepancies'].replace('masthead check C8-PIC for p.1', 'masthead check ' + cid[(c['tranche_id'], 1)]).replace('p.213 masthead check', cid[(c['tranche_id'], 1)] + ' (masthead, printed p.213)').replace('p.613 masthead check', cid[(c['tranche_id'], 1)] + ' (masthead, printed p.613)')
    pic_fields = ['check_id', 'tranche_id', 'source_id', 'document_sha256', 'pdf_page', 'printed_page', 'what_was_read', 'reading',
                  'identity_result', 'discrepancies', 'render_png_sha256', 'render_settings', 'reader', 'checked_on']
    wr(os.path.join(O, 'page_image_checks_c8.csv'), checks, pic_fields)

    # candidate-level identity result
    cand_id = {}
    for t in srcmap:
        rs = [c['identity_result'] for c in checks if c['tranche_id'] == t]
        # PARTIAL only on a running header whose element is covered by a CONFIRMED masthead check of the same file
        cand_id[t] = 'CONFIRMED' if all(x in ('CONFIRMED', 'PARTIAL') for x in rs) and any(x == 'CONFIRMED' for x in rs) else 'UNCERTAIN'
        if 'UNCERTAIN' in rs:
            cand_id[t] = 'UNCERTAIN'

    # ---- contradiction register (carry forward + new)
    crs = []
    for r in con:
        crs.append(dict(entry_id=f"T1-CR-{r['tranche_id'][3:]}", origin='CARRIED_FORWARD (T1-GAZETTE/contradiction_register.csv#' + r['tranche_id'] + ')',
                        tranche_id=r['tranche_id'], sha256=r['sha256'], kind='register_check',
                        description=f"exact-string: {r['exact_string_contradictions']}; recovery register: {r['recovery_register_contradictions']}; identity: {r['identity_discrepancy']}",
                        evidence_refs=f"{AW}/AUTH-LEDGER/tranches/T1-GAZETTE/contradiction_register.csv#{r['tranche_id']}",
                        affects='identity' if r['identity_discrepancy'] != 'NONE_RECORDED' else 'none recorded',
                        status=r['status'], c8_update='unchanged; C8 page inspection (see page_image_checks_c8.csv) found no conflict with the register identity' if r['tranche_id'] != 'T1-02' else 'status kept; relationship restated as UNRESOLVED in C8-CR-02'))
    s02 = srcmap['T1-02']['sha256']; s19 = srcmap['T1-19']['sha256']; s20 = srcmap['T1-20']['sha256']; s08 = srcmap['T1-08']['sha256']
    new = [
     dict(entry_id='C8-CR-01', tranche_id='T1-19; T1-02', sha256=f"{s19}; {s02}", kind='document_to_document date discrepancy (NEW, C8 page inspection)',
          description="S.R.O. 2(E)/2018 Note (English and Hindi) lists 'S.R.O. 240 dated 05th June, 1955' ('का.नि.आ. 240 दिनांक 05 जून, 1955'); held S.R.O. 34/1963 recites 'SRO 240, dated the 25th June, 1955'. Which date is correct is not established by the held documents; S.R.O. 240/1955 itself is not held.",
          evidence_refs=f"{cid[('T1-19',2)]} ({s19} PDF p.2), {cid[('T1-19',1)]} ({s19} PDF p.1), {cid[('T1-02',2)]} ({s02} PDF p.2)",
          affects='none of the 20 identities (S.R.O. 240/1955 is not a tranche candidate); relevant to any future r.188(e) declaration chain', status='UNRESOLVED', c8_update='new'),
     dict(entry_id='C8-CR-02', tranche_id='T1-02', sha256=s02, kind='identity relationship (restated with new documentary context)',
          description="The held instrument is S.R.O. 34 dated 'New Delhi, the 5th January 1963', a declaration under r.188(e), printed in No.3 of 19-01-1963, Pt II-S4, p.14. Gazette-printed NOTEs of previous S.R.O.s appended to later Army Rules amendments list 'SRO 34 dated 5 Jun 63' (S.R.O. 246/1982 p.413), 'SRO 34 dated 5 jun 1963' (S.R.O. 44/1985 p.60), 'SRO 34 dated 5th June, 1963' (S.R.O. 55/1985 p.97; S.R.O. 302/1987 p.367; S.R.O. 216/1988 p.617; S.R.O. 332/1989 p.736; S.R.O. 44/1991 p.214; S.R.O. 235/1991 p.614), 'SRO 34 dated 5 Jun 1963' (S.R.O. 169/1987 p.197) and Hindi equivalents ('5 जून, 1963'); these NOTEs give no Gazette issue or page for it and present it among amendments of the Rules. S.R.O. 2(E)/2018 (a later r.188(e) declaration) lists 'S.R.O. 34 dated 05th January, 1963' among the r.188(e) S.R.O.s it amends. Whether the NOTEs' 'SRO 34 dated 5 Jun 63' denotes this 05-01-1963 declaration (misdated) or a different, unlocated instrument is NOT proved by any held document. No amendment-chain inference is made.",
          evidence_refs=f"{cid[('T1-02',2)]}, {cid[('T1-02',1)]}, {cid[('T1-08',11)]}, {cid[('T1-09',2)]}, {cid[('T1-10',11)]}, {cid[('T1-13',5)]}, {cid[('T1-14',21)]}, {cid[('T1-15',9)]}, {cid[('T1-16',12)]}, {cid[('T1-17',2)]}, {cid[('T1-17',5)]}, {cid[('T1-18',2)]}, {cid[('T1-19',2)]}; {AW}/R23-VERIFY-01/registers/amendment_search_2026-11-22.csv#S.R.O. 34 (agent discovery register, not approved: its 'apparent misdating' note is a proposal, not proof); {AW}/ARMY-RULES-CHAIN-01/army_rules_instrument_register.csv#AR-008 ('notes misdate' wording is unverified)",
          affects='amendment chronology only (not the copy identity of T1-02)', status='UNRESOLVED', c8_update='new context: the 5-6-1963 listing also appears in Gazette-printed NOTEs 1982-1991, not only in the 1988/1993/2003 Government notes'),
     dict(entry_id='C8-CR-03', tranche_id='T1-20', sha256=s20, kind='born-digital signature integrity (NEW, C8 structural parse)',
          description=f"Embedded CMS (adbe.pkcs7.detached) signature: messageDigest attribute equals SHA-256 of the signed byte ranges ({rsa['T1-20']['sha256_signed_content']}), but the RSA signature value does not verify with the only embedded certificate (CN=MANOJ KUMAR VERMA; serial matches the SignerInfo sid): the RSA public operation does not yield a PKCS#1 v1.5 block (openssl cms -verify -noverify: 'CMS Verification failure ... RSA_padding_check_PKCS1_type_1:invalid padding'). Cause UNCERTAIN (signing-software defect at origin, wrong certificate embedded, or alteration of the signature value); the held bytes cannot distinguish these.",
          evidence_refs="born_digital_structure.csv#T1-20; bd_work/T1-20.json; bd_work/T1-20_rsa_diag.json; tools/born_digital.py; tools/rsa_diag.py",
          affects='copy fidelity / documentary authenticity evidence for T1-20 (not identity: page text CONFIRMED)', status='OPEN', c8_update='new'),
     dict(entry_id='C8-CR-04', tranche_id='T1-19', sha256=s19, kind='born-digital signature integrity (C8 structural parse; no conflict)',
          description=f"Embedded CMS signature verifies at the integrity level only: messageDigest equals SHA-256 of the signed ranges and the RSA signature over signedAttrs verifies with the embedded signer certificate CN=RAKESH SUKUL (openssl cms -verify -noverify: 'CMS Verification successful'; independent raw-RSA check agrees). Certificate chain, trust anchor, validity at signing time against a trusted clock and revocation were NOT validated.",
          evidence_refs="born_digital_structure.csv#T1-19; bd_work/T1-19.json; bd_work/T1-19_rsa_diag.json",
          affects='copy fidelity evidence (supporting, limited)', status='NO_CONTRADICTION (recorded for completeness)', c8_update='new'),
     dict(entry_id='C8-CR-05', tranche_id='T1-08', sha256=s08, kind='observation (not an identity discrepancy)', description="English S.R.O. 246/1982 on p.413 carries a file number but no printed signatory name.", evidence_refs=cid[('T1-08',11)], affects='none', status='OBSERVATION', c8_update='new'),
     dict(entry_id='C8-CR-06', tranche_id='T1-02', sha256=s02, kind='observation (not an identity discrepancy)', description="Running header of p.14 ends '[PART II-' (section not printed on that page); Part II-Section 4 is read on the masthead p.13.", evidence_refs=f"{cid[('T1-02',2)]}, {cid[('T1-02',1)]}", affects='none', status='OBSERVATION', c8_update='new'),
    ]
    obs = [
     ('C8-CR-08', 'T1-11', "Corrigendum S.R.O. 68/1985 prints file no. '4(2)/884/D (AG)'; the corrected S.R.O. 55/1985 (T1-10 p.97) prints '[File No. 4(2)|84|D(AG)]'. Possibly a misprint; not established.", f"{cid[('T1-11',2)]}, {cid[('T1-10',11)]}"),
     ('C8-CR-09', 'T1-13', "English S.R.O. 169/1987 on p.197 has no printed file number or signatory between the rule text and the Note.", cid[('T1-13',5)]),
     ('C8-CR-10', 'T1-14', "Masthead sub-heading of No.38 of 10-10-1987 reads 'Orders and Notifications issued by the Ministry of Defence' (other issues: 'Statutory Rules and Orders ...'). Part II-Section 4 unchanged.", cid[('T1-14',1)]),
     ('C8-CR-11', 'T1-17', "Short titles printed 'Army (Second Amendment) Rules, 1990' (S.R.O. 44, dated 1st February, 1991) and 'Army (Amendment) Rules, 1990' (S.R.O. 61, dated 7th February, 1991): year in the short title precedes the notification year. As printed; already quoted in the R23 register.", f"{cid[('T1-17',2)]}, {cid[('T1-17',5)]}"),
     ('C8-CR-12', 'T1-17', "S.R.O. 61/1991 enacting formula prints 'section 191 of the Army Act 1960 (46 of 1950)' (Act year misprinted; Act number correct).", cid[('T1-17',5)]),
     ('C8-CR-13', 'T1-18', "S.R.O. 235/1991 prints 'or the Military Secretory' (sic). Hindi note list on p.614 prints '22 फरवरी, 1965' for S.R.O. 55 (1985) and '30 अगस्त, 1986' for S.R.O. 216 (1988) - misprints in the Hindi list only.", cid[('T1-18',2)]),
    ]
    for eid, t, d, ev in obs:
        new.append(dict(entry_id=eid, tranche_id=t, sha256=srcmap[t]['sha256'], kind='observation (not an identity discrepancy)', description=d, evidence_refs=ev, affects='none for identity; text-fidelity note', status='OBSERVATION', c8_update='new'))
    for n in new:
        n['origin'] = 'C8 Workstream B (AI agent, not human-confirmed)'
    cr_fields = ['entry_id', 'origin', 'tranche_id', 'sha256', 'kind', 'description', 'evidence_refs', 'affects', 'status', 'c8_update']
    wr(os.path.join(O, 'contradiction_register_c8.csv'), crs + new, cr_fields)

    # ---- born-digital structure csv
    bds = []
    for t in ('T1-19', 'T1-20'):
        j = bd[t]; s = j['signature_dictionaries'][0]; c = j['cms_checks'][0]; rr = rsa[t]
        signer = [x for x in rr['per_certificate'] if x['pkcs1_type1_wellformed']]
        bds.append(dict(tranche_id=t, source_id=srcmap[t]['source_id'], sha256_expected=srcmap[t]['sha256'], sha256_rehashed=j['sha256'], hash_check=j['hash_check'], bytes=j['bytes'],
            pdf_header=j['pdf_header'], linearized='yes (/Linearized /L equals file length)', eof_markers=j['eof_count'], eof_offsets=' '.join(map(str, j['eof_offsets'])),
            startxref_values=' '.join(map(str, j['startxref_values'])), incremental_update_sections='none detected: two %%EOF = linearized first-page section + main section; one /Prev; /L equals file length',
            bytes_after_last_eof=f"{j['bytes_after_last_eof_marker']} (hex {j['trailing_bytes_after_last_eof_hex']}, CR LF)",
            signature_dictionaries=j['signature_dictionary_count'], sig_dict_object=s['dict_object'], byte_range=' '.join(map(str, s['byte_range'])), signed_bytes=s['signed_bytes'],
            contents_hole=f"{s['hole'][0]}-{s['hole'][1]} (matches /Contents hex string: {s['hole_matches_contents_string']})",
            signed_ranges_cover_whole_file_except_contents=s['covers_whole_file_except_contents_hole'], bytes_after_last_signed_range=s['bytes_after_last_signed_range'],
            Filter=s['Filter'], SubFilter=s['SubFilter'], Name_as_printed=s['Name'], Reason=s['Reason'] or 'absent', Location=s['Location'] or 'absent', M_as_printed=s['M'], ContactInfo=s['ContactInfo'] or 'absent',
            producer=j['metadata']['producer'], creator=j['metadata']['creator'], creationDate=j['metadata']['creationDate'], modDate=j['metadata']['modDate'],
            xmp_producer=j['xmp_Producer'], xmp_creatortool=j['xmp_CreatorTool'], ia_rerender_markers=';'.join(j['ia_or_rerender_markers_in_bytes']) or 'none found',
            cms_type=f"detached ({c['cms_eContentType']}; eContent absent {c['cms_eContent_absent(detached)']}); digest {';'.join(c['cms_digestAlgorithms'])}; sig {';'.join(c['cms_signatureAlgorithms'])}",
            cms_der_sha256=c['der_sha256'], signed_content_sha256=c['signed_content_sha256'],
            messageDigest_equals_signed_content='yes' if c['openssl_cms_verify_noverify_rc'] == 0 or rr['sha256_signed_content'].startswith(c['cms_messageDigest_raw'].split(' - ')[1].replace(' ', '').replace('-', '')[:16]) else 'see notes',
            rsa_signature_over_signedAttrs=('VERIFIES with embedded cert ' + signer[0]['cert_subject_CN'].split(',')[0]) if signer else 'DOES NOT VERIFY with any embedded certificate (invalid PKCS#1 v1.5 padding)',
            openssl_cms_verify_noverify=c['openssl_cms_verify_stderr'].splitlines()[0],
            embedded_certificates=c['embedded_certs'].replace('\n\n', ' || ').replace('\n', ' / '),
            cryptographic_validation_performed='PARTIAL INTEGRITY ONLY: messageDigest and RSA signature value checked against the embedded certificate with installed openssl/cryptography; NO certificate-chain, trust-anchor, validity-at-signing or revocation validation; no timestamp token checked',
            derivative_generation_evidence=('none: producer GPL Ghostscript 8.15 / creator PScript5.dll; no Internet Archive markers; ' + ('ACQ-01 snapshot files[].source = original' if t == 'T1-20' else 'ACQ-02 snapshot records name/size/md5/sha1/mtime 1534716964 but no source field (original/derivative not recorded)')),
            evidence_refs=f"tools/born_digital.py; tools/rsa_diag.py; bd_work/{t}.json; bd_work/{t}_rsa_diag.json; {AW}/AUTH-LEDGER/evidence/copy_structure.csv#{srcmap[t]['copy_id']}"))
    wr(os.path.join(O, 'born_digital_structure.csv'), bds, list(bds[0].keys()))

    # ---- evidence register + md + eligibility
    ev_rows, el_rows = [], []
    for r in src:
        t = r['tranche_id']; m = mat[t]; f = FACTS[t]
        rc = rec.get(r['copy_id'], {})
        ars = re.findall(r'AR-\d{3}', r['source_id'])
        arrow = ' | '.join(f"{x}: {arc[x]['instrument']} dated {arc[x]['instrument_date']}; {arc[x]['gazette_publication']}; nature {arc[x]['nature']}" for x in ars if x in arc)
        if 'misdate' in arrow:
            arrow += " [caution: the register's 'notes misdate' wording is an unverified assertion; C8 records the relationship as UNRESOLVED (C8-CR-02)]"
        item = re.search(r'in\.gazette\.central\.[we]\.\d{4}-\d\d-\d\d\.\d+', r['first_class_locator']).group(0)
        sn = snap1.get(item) or snap2.get(item)
        snaptxt = 'not in ACQ-01/ACQ-02 snapshots'
        if sn:
            snapfile = 'ACQ-01/archive_org_metadata_snapshot.json' if item in snap1 else 'ACQ-02/archive_org_metadata_snapshot_acq02.json'
            files = sn.get('files') or sn.get('pdf_files') or []
            fi = files[0] if files else {}
            snaptxt = f"{snapfile}#{item}: file {fi.get('name')} size {fi.get('size')} md5 {fi.get('md5')}" + (f" source={fi['source']}" if 'source' in fi else ' (no original/derivative field)') + (f" mtime={fi['mtime']}" if 'mtime' in fi else '') + (f"; retrieved {sn['retrieved']}" if 'retrieved' in sn else '')
        mychecks = [c for c in checks if c['tranche_id'] == t]
        renders = '; '.join(f"{c['check_id']} PDF p.{c['pdf_page']} (printed {c['printed_page']}) png sha256 {c['render_png_sha256']} [{c['identity_result']}]" for c in mychecks)
        crlist = [n['entry_id'] for n in crs + new if t in n['tranche_id'].split('; ')]
        scanned = 'born-digital (text layer, no images)' if 'BORN_DIGITAL' in r['fidelity_class'] else 'scanned facsimile (page images' + (' with OCR text layer)' if 'TEXT' in m['v10_signed_or_scanned'] else ')')
        if t == 'T1-02':
            rec_ = 'READY_FOR_OWNER_CONSIDERATION'
            why = "rule 1 PASS; held-instrument identity CONFIRMED on fresh page images (S.R.O. 34, 05-01-1963, No.3 19-01-1963, Pt II-S4, p.14, r.188(e) declaration). For COPY PROVENANCE ONLY: the relationship to the notes' 'SRO 34 dated 5 Jun 63' stays UNRESOLVED (C8-CR-02) and no amendment-chain inference may rest on this copy"
        elif t == 'T1-19':
            rec_ = 'HOLD_FIDELITY_DECISION'
            why = "rule 1 PASS; identity CONFIRMED; hold for owner decision P-D2 (born-digital, no trust-chain validation). Structural: one signature, ByteRange spans the file except /Contents, no incremental update; CMS integrity check (messageDigest + RSA with embedded cert) passes; chain/revocation not validated"
        elif t == 'T1-20':
            rec_ = 'NEEDS_FURTHER_EVIDENCE'
            why = "rule 1 PASS; identity CONFIRMED; but the embedded CMS signature value does NOT verify with the embedded signer certificate (C8-CR-03) although the ByteRange spans the file and messageDigest matches. P-D2's premise (spanning range, unvalidated) does not cover a signature that fails integrity; obtain an independent copy (egazette.gov.in original) or an explanation before any fidelity decision; then still subject to P-D2"
        else:
            rec_ = 'READY_FOR_OWNER_CONSIDERATION'
            why = "rule 1 PASS; masthead and S.R.O. line freshly read on page images and CONFIRMED against the register" + ('' if r['identifier_source'] != 'L5_DISCOVERY_REGISTER_ONLY' else ' (closes the F-T1-1 advisory: the number is no longer quoted only in the R23 discovery register)')
        lim = ['C8 page readings are AI-agent readings, not human-confirmed; a human should re-check from the render hashes before approval']
        if 'register dated' in m['v06_provenance_evidence']:
            lim.append('no retrieval date in a retrieval record (register date 2026-11-22 only)')
        if any(c['identity_result'] == 'PARTIAL' for c in mychecks):
            lim.append('running header partly illegible on the S.R.O. page; issue date taken from the masthead page of the same file')
        if t == 'T1-17':
            lim.append('one copy carries two instruments (S.R.O. 44/1991 and 61/1991); entry covers the copy')
        outstanding = []
        if t in ('T1-19', 'T1-20'):
            outstanding.append('owner decision P-D2')
        if t == 'T1-20':
            outstanding.append('resolve C8-CR-03 (signature value fails integrity) with an independent copy or issuer evidence')
        if t == 'T1-02':
            outstanding.append('C8-CR-02 stays UNRESOLVED; no chain inference')
        outstanding.append('human re-check of C8 readings; committed D-/R- records, independent review, BIND line (APPROVAL_CONTROLS.md)')
        verification = f"identity {cand_id[t]} on fresh C8 page images (AI-agent reading)"
        ev = dict(tranche_id=t, source_id=r['source_id'], copy_id=r['copy_id'], sub_tranche=r['sub_tranche'],
                  gazette_issue=f"{f['issue']}; {f['part']}", printed_pages=f['pages'], notification_number=f['sro'], notification_date_line=f['dateline'],
                  issuing_authority_as_printed=AUTH.get(t, "Ministry of Defence (section heading 'Statutory Rules and Orders issued by the Ministry of Defence' / 'MINISTRY OF DEFENCE'; operative words 'the Central Government')"),
                  issuing_authority_register=r['issuing_authority'], title_or_nature_as_printed=f['nature'], signature_block_as_printed=f['sign'],
                  held_sha256=r['sha256'], sha256_rehash='MATCH (re-hashed 2026-11-23; render_log.csv)', held_path=next(x['held_path'] for x in rlog if x['tranche_id'] == t),
                  provenance_first_class=m['v06_provenance_evidence'].split(';')[0], provenance_what_it_proves='that the held bytes equal the file published at the archive.org locator (size/md5/sha1 match to item metadata); it does not prove the Government of India originated those bytes (documentary authenticity) or that the scan is complete beyond the page count',
                  retrieval_evidence=f"{rc.get('retrieval_url','')} ; date {rc.get('retrieval_date','')} ; method {rc.get('retrieval_method','')}", retrieval_limitations=('no retrieval date in a retrieval record (register date only)' if 'register dated' in m['v06_provenance_evidence'] else 'retrieval date from agent retrieval record (R23 independent-reviewer-D source JSON)') + f"; archive snapshot: {snaptxt}",
                  original_carrier='Government of India Gazette (printed weekly issue)' if 'BORN' not in r['fidelity_class'] else 'Government of India e-Gazette (digitally signed PDF, Extraordinary)',
                  current_host='archive.org (third-party archival host; item ' + item + ')', scanned_or_born_digital=scanned, fidelity_class=r['fidelity_class'],
                  page_count_and_completeness=f"{m['v08_completeness']}", identity_page_refs_prior=' | '.join(x.split(';')[0] for x in m['v07_identity_page_evidence'].split(' | ')),
                  c8_checks_and_render_hashes=renders, c8_identity_result=cand_id[t], contradictions=';'.join(crlist),
                  rule1_result=r['rule1_result'], rule1_source='tranche1_source_register.csv#rule1_result (not recomputed)', c8_recommendation=rec_,
                  outstanding_requirements='; '.join(outstanding), limitations='; '.join(lim),
                  evidence_refs=f"{AW}/AUTH-LEDGER/tranches/T1-GAZETTE/tranche1_source_register.csv#{t}; evidence_verification_matrix.csv#{t}; {AW}/C6-01-PROVENANCE/registers/provenance_recovery_register.csv#{r['copy_id']}; {AW}/ARMY-RULES-CHAIN-01/army_rules_instrument_register.csv#{'+'.join(ars)}; page_image_checks_c8.csv#{','.join(c['check_id'] for c in mychecks)}")
        ev_rows.append(ev)
        el_rows.append(dict(tranche_id=t, source_id=r['source_id'], sha256=r['sha256'], rule1_status=r['rule1_result'], prior_recommendation=r['recommendation'],
                            documentary_verification_after_c8=verification + ('; born-digital CMS integrity passes (no chain validation)' if t == 'T1-19' else '; born-digital CMS signature FAILS integrity with embedded cert' if t == 'T1-20' else ''),
                            recommendation=rec_, reasons=why, limitations='; '.join(lim), evidence_refs=ev['evidence_refs']))
        # markdown
        md = [f"# {t}: evidence record (C8 Workstream B)", "",
              "> Prepared evidence only. No approval, activation or legal-status change. Page readings are by an " + READER + ".", "",
              "| Item | Evidence |", "| --- | --- |"]
        for k in ['source_id', 'copy_id', 'gazette_issue', 'printed_pages', 'notification_number', 'notification_date_line', 'issuing_authority_as_printed',
                  'title_or_nature_as_printed', 'signature_block_as_printed', 'held_sha256', 'sha256_rehash', 'held_path', 'provenance_first_class', 'provenance_what_it_proves',
                  'retrieval_evidence', 'retrieval_limitations', 'original_carrier', 'current_host', 'scanned_or_born_digital', 'page_count_and_completeness',
                  'identity_page_refs_prior', 'c8_identity_result', 'contradictions', 'rule1_result', 'c8_recommendation', 'outstanding_requirements', 'limitations']:
            md.append(f"| {k} | {str(ev[k]).replace('|', '/')} |")
        md += ["", "## Arm y-rules chain register row (context, not re-verified)".replace('Arm y', 'Army'), "", arrow or 'n/a', "", "## C8 page-image checks", ""]
        for c in mychecks:
            md += [f"### {c['check_id']}: PDF p.{c['pdf_page']} (printed {c['printed_page']}) - {c['identity_result']}", "",
                   f"- What was read: {c['what_was_read']}", f"- Reading (verbatim, as transcribed): {c['reading']}", f"- Discrepancies / notes: {c['discrepancies']}",
                   f"- Render: sha256 `{c['render_png_sha256']}`; {c['render_settings']}", f"- Reader: {c['reader']}; checked on {c['checked_on']}", ""]
        if t in ('T1-19', 'T1-20'):
            b = next(x for x in bds if x['tranche_id'] == t)
            md += ["## Born-digital structure (see BORN_DIGITAL_FINDINGS.md)", ""] + [f"- {k}: {v}" for k, v in b.items() if k not in ('tranche_id', 'source_id', 'embedded_certificates')] + [""]
        md += ["## Recommendation", "", f"**{rec_}**: {why}", "", "## Evidence references", "", ev['evidence_refs'], ""]
        os.makedirs(os.path.join(O, 'evidence'), exist_ok=True)
        open(os.path.join(O, 'evidence', f'{t}.md'), 'w', encoding='utf-8').write('\n'.join(md))
    wr(os.path.join(O, 'gazette_evidence_register.csv'), ev_rows, list(ev_rows[0].keys()))
    wr(os.path.join(O, 'eligibility_recommendations.csv'), el_rows, list(el_rows[0].keys()))
    from collections import Counter
    print('checks', len(checks), Counter(c['identity_result'] for c in checks))
    print('candidates', Counter(cand_id.values()))
    print('recs', Counter(r['recommendation'] for r in el_rows))


if __name__ == '__main__':
    main()
