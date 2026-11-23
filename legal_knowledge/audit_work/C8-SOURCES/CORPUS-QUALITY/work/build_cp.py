import csv,json
B='<scratchpad>/c8base/legal_knowledge/curated_originals/'
KB={json.loads(l)['id']:json.loads(l) for l in open(B+'knowledge_base/v0.9/records_658.jsonl')}
CS={json.loads(l)['id']:json.loads(l) for l in open(B+'case_law/v0.9/cases_53.jsonl')}
F=["proposal_id","finding_ref","record_id","field","current_text_quoted","proposed_change","evidence","priority","proposal_type","status"]
rows=[]
GIR="held sha256 4f7ea3a451c6f9a11d7e4dd96822e68cd9cd7a01d8dc74cf46ad34e79029b86c PDF pp.15-16 para 22 (Union of India v Sgt Girish Kumar, 2026 INSC 149; official SC copy; text layer); WS-B WSB-T-005"
def p(pid,fr,rid,field,cur,chg,ev,pri,typ):
    if rid in KB: assert cur in (KB[rid].get(field) or ''), (pid,cur)
    elif rid in CS: assert cur in str(CS[rid].get(field)), (pid,cur)
    rows.append(dict(zip(F,[pid,fr,rid,field,cur,chg,ev,pri,typ,"PROPOSAL_NOT_APPLIED"])))
p("E8-CP-01","E8-XR-01","AFT-013","body","Tarsem Singh distinguishes a continuing wrong from stale claims and cautions against prejudice to settled third-party rights. Arrears may be limited despite a current grievance;",
  "Supplement (append, do not replace): 'Later treatment: in Union of India v Sgt Girish Kumar (2026 INSC 149, 12-02-2026, para 22) the Supreme Court held Tarsem Singh of no application to ex-servicemen already in receipt of disability pension who seek broad-banding re-computation, and held the AFT Act s.22(1)(c) bar inapplicable to those claims; read with the 12-10-2026 clarification (2026 INSC 1113, official copy not held). Scope of the distinction is for legal review.'",GIR,"P2","SUPPLEMENTATION")
p("E8-CP-02","E8-XR-01","V7-SC-02","body","compare Tarsem Singh, old PPO, refusals and statutory limitation.",
  "Supplement: 'If the claim is a broad-banding re-computation of an existing disability pension, also read Girish Kumar (2026 INSC 149) para 22, which held Tarsem Singh inapplicable to such claims, and the October 2026 clarification.'",GIR,"P2","SUPPLEMENTATION")
p("E8-CP-03","E8-XR-01","DCLR-SC-2008-N10","post_decision_treatment_status","NOT_EXHAUSTIVELY_CHECKED",
  "Overlay (no edit of curated field): add treatment edge 'DISTINGUISHED by DCLR-SC-2026-007 (2026 INSC 149) para 22, scope: broad-banding re-computation claims' with confidence=extracted, human_verified=false; extend WS-B WSB-T-005 affected_kb_ids with AFT-013;V7-SC-02.",GIR+"; WS-B case_relations.csv edge DCLR-SC-2026-007 -> DCLR-SC-2008-N10 DISTINGUISHED","P2","RELATION_SUPPLEMENTATION")
p("E8-CP-04","E8-XR-02","PEN-044","body","Ram Avtar addressed eligible personnel leaving after completion of tenure with disability attributable/aggravated by service.",
  "After an official copy of Union of India v Wg Cdr S P Rathore (CA 10870/2018, 11-12-2019) is held: assess adding 'S P Rathore (2019) paras 8-9 explained that Ram Avtar did not decide entitlement under para 8.2 and that there is no rounding-off below 20%'; apply the same assessment to PEN-023 and PEN-WF-08. Until then: no text change; add WSB-T-024 affected_kb_ids PEN-023;PEN-044;PEN-WF-08.","WS-B WSB-T-024 (INTERN_MIRROR_SCR sha256 2f89730f3d0ae1c81a1a423f259136c4423dc8cd43d7bc75a2a2a3121eec6e38 pp.4-5 paras 8-9); official copy NOT held","P3","SUPPLEMENTATION (conditional)")
for k in ["DCLR-SC-1996-L07","DCLR-SC-2005-L08","DCLR-SC-2008-L09","DCLR-SC-2007-L10"]:
    p(f"E8-CP-05-{k[-3:]}","E8-XR-03",k,"accessible_source_url","https://api.sci.gov.in/jonew/bosir/orderpdf/1525127.pdf",
      "Overlay: re-label as citing_document_url (lead: Union of India v Ravinder Kumar order, DCLR-SC-2012-A05) and mark accessible_source_url UNRESOLVED until the judgment's own official copy is located; do not present 1525127.pdf as this judgment.","cases_53.jsonl DCLR-SC-2012-A05.primary_source_url is the same URL; WS-B identity_resolution.csv gives a distinct identity for this record (intern mirror)","P3","PROVENANCE_CORRECTION")
for row,ins in [("C5-PCH-PCL-BL-01","AR-016"),("C5-PCH-PCL-BL-16","AR-016"),("C5-PCH-PCL-BL-14","AR-034"),("C5-PCH-PCL-BL-21","AR-034"),("C5-PCH-PCL-BL-22","AR-035"),("C5-PCH-PCL-BL-36","AR-031")]:
    rows.append(dict(zip(F,[f"E8-CP-06-{row[-5:]}","E8-XR-04",f"SOURCE-LIBRARY-C5/registers/provision_amendment_chain.csv#{row}","effective_date_status","NOT_DETERMINED (commencement clause not yet read)",
      f"Overlay correction record: align with amendment_register origin {ins} 'STATED_IN_INSTRUMENT (in force on publication)' after confirming the page-image reading cited by the amendment register; no change to the frozen C5 file.",f"amendment_register.csv row with origin_id={ins}","P3","REGISTER_CONSISTENCY","PROPOSAL_NOT_APPLIED"])))
rows.append(dict(zip(F,["E8-CP-07","E8-XR-05","SOURCE-LIBRARY-C5/registers/source_conflict_register.csv#C5-CF-C-04","status","OPEN (observation only)","Overlay: status 'SPLIT into C5-CF-C-08 (r.193) and C5-CF-C-09 (r.194) on 2026-11-22d'; exclude from open-conflict counts.","SOURCE-CONFLICTS-01/conflict_split_2026-11-22d.csv","P3","REGISTER_CONSISTENCY","PROPOSAL_NOT_APPLIED"])))
p("E8-CP-08","E8-XR-08","ADM-022","body","For non-officers §26(2) explicitly directs complaint to next superior when the complained-of officer would otherwise be recipient.",
  "Replace with: 'For non-officers, §26(2) permits the aggrieved person to complain to the next superior officer where the officer complained against is the officer to whom the complaint would otherwise be preferred.'","held sha256 e47a4265813e95b491a24926428ed306cfeaae9013e7edb928cefef6e69a7c08 PDF p.16, Army Act s.26(2) ('may complain to such officer's next superior officer'); government compilation","P3","WORDING_CORRECTION")
for rid,refs in [("CM-011","F-PROC-006; F-PROC-007"),("CM-025","F-STAT-013")]:
    p(f"E8-CP-09-{rid}","E8-XR-09",rid,"status","SOURCE_REVIEWED_JAG_APPROVAL_PENDING",
      f"Overlay flag OPEN_P1_FINDINGS={refs} displayed with the status; original status unchanged until the P1 proposals are dispositioned.","PILOT-01/registers/corrections_register.csv (status PROPOSAL_NOT_APPLIED)","P3","CLASSIFICATION_FLAG")
for k,nc in [("DCLR-SC-2026-007","2026 INSC 149"),("DCLR-SC-2023-009","2023 INSC 265"),("DCLR-SC-1982-001","1982 INSC 65"),("DCLR-SC-2013-N08","2013 INSC 408"),("DCLR-SC-1987-R01","1987 INSC 285")]:
    cur=CS[k]['reporter_citation']
    rows.append(dict(zip(F,[f"E8-CP-10-{k[-4:]}","E8-XR-06",k,"reporter_citation / neutral_citation",f"'{cur}'",f"Supplement neutral_citation '{nc}' after reading it from the first page of the held official copy (value currently from WS-B identity spec/intern columns).","WS-B identity_resolution.csv (expected_neutral_citation_spec / intern_neutral_citation; held_copy_sha256 present)","P3","METADATA_SUPPLEMENTATION","PROPOSAL_NOT_APPLIED"])))
rows.append(dict(zip(F,["E8-CP-11","E8-XR-07","WS-B-JUDGMENTS/holdings_register_cycle3.csv#WSB-H3-001..008,016,019; subsequent_treatment_cycle3.csv#WSB-T3-004","affected_kb_ids","'V8-S15' / 'PEN-*' / 'AFT-*'","Expand to explicit KB record ids (use WS-D source_code_resolution for V8-S15 users) or move to a separate scope column.","xref_checks.py X14b output","P3","REGISTER_CONSISTENCY","PROPOSAL_NOT_APPLIED"])))
with open('<c8out>/E/correction_proposals.csv','w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=F); w.writeheader(); w.writerows(rows)
print(len(rows))
