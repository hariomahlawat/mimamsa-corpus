import json,csv,sys
R=sys.argv[1]
V={
'T01':('Y','Y','Y','Y','covered by Gawas Anil Madso (fn 2 = 2025 SCC OnLine Del 2018), resolved correctly'),
'T02':('Y','Y','Y','Y','same template as T01'),'T03':('Y','Y','Y','Y','same template'),'T04':('Y','Y','Y','Y','same template'),
'T05':('Y','Y','Y','Y','squarely covered by Gyanendra Dutt Misra CWP 7877/2009'),
'T06':('Y','Y','Y','Y','same template'),'T07':('Y','Y','Y','Y','covered by Tarsem Singh (2008) 8 SCC 648'),
'T08':('Y','Y','Y','Y','issue settled by SC in Ram Avtar; raw target'),
'T09':('Y','Y','N','Y','QUOTED: sentence is inside a reproduced passage of Gala International (opened with a curly quote before para 34); not the court\'s own voice'),
'T10':('Y','Y','Y','Y','no longer res integra: Jujhar Singh (2011) 7 SCC 735'),
'T11':('Y','Y','Y','Y','same template'),'T12':('Y','Y','Y','Y','same template'),
'T13':('Y','Y','Y','N','WRONG TARGET: covered-by authority is Gawas Anil Madso (fn 4); edge bound to fn 3 (2013) 7 SCC 316 Dharamvir Singh'),
'T14':('Y','Y','Y','Y','same template'),
'T15':('Y','Y','Y','Y','Ranjit Thakur described'),'T16':('Y','Y','Y','Y',''),'T17':('Y','Y','Y','Y',''),'T18':('Y','Y','Y','Y',''),
'T19':('Y','Y','Y','Y',''),'T20':('Y','Y','Y','Y',''),
'T21':('Y','Y','N','Y','PARTY CONTENTION: "Before the learned AFT, the petitioner primarily contended that ... Dharamvir Singh, wherein it was held"'),
'T22':('Y','Y','Y','Y',''),
'T23':('Y','Y','N','Y','QUOTED: "this Court considered" is the Supreme Court\'s voice inside a quotation reproduced by the HC'),
'T24':('Y','Y','N','Y','QUOTED: sentence ends a reproduced SC passage (closing quote then para 37)'),
'T25':('Y','Y','Y','Y',''),'T26':('Y','Y','Y','Y',''),
'T27':('N','-','Y','N','"Article 323A does not apply because the AFT is not an Administrative Tribunal": subject is Article 323A, not the cited authority (2025 SCC OnLine Del 6230)'),
'T28':('N','-','N','N','REPORTED TREATMENT: list of earlier decisions; "was distinguished" refers to Prakash Katiyar distinguishing Pradeep Kumar Rai, not this court'),
'T29':('Y','Y','Y','Y','Man Kanhaiya Kumar "has no application in the present case"'),
'T30':('N','-','N','N','tabular entry; "the amendment of 2018 is not applicable": subject is an amendment; raw target is a connected matter of the same common judgment'),
'T31':('Y','Y','Y','Y','borderline: court notes Independent Thought by its own terms would not apply to an adult woman; split-verdict opinion'),
'T32':('N','-','N','N','REPORTED TREATMENT, and target W.P.(C) 5145/2016 was in fact followed in the listed decisions'),
'T33':('Y','Y','Y','Y','Applying Dharamvir Singh'),
'T34':('Y','Y','N','N','QUOTED SC judgment (paras 22-23, "the appellant", "the Tribunal") reproduced in Gawas Anil Madso; two authorities in the sentence despite the stated one-authority rule'),
'T35':('Y','Y','N','Y','same quoted passage as T34 (other doc_id of the common judgment)'),
'T36':('Y','Y','Y','N','WRONG TARGET: applies L. Chandra Kumar (fn 11, (1997) 3 SCC 261); bound to fn 10 WP(C) 9139/2019'),
'T37':('N','-','Y','Y','"principles ... have been explained in Ranjit Thakur": the authority explains a principle; the citing court does not explain the authority (CONSIDERS/CITES)'),
'T38':('N','-','Y','Y','"concept of right to dignity has been explained in para 8 of Francis Coralie Mullin": same semantic issue'),
'T39':('N','-','Y','Y','"principle was clarified in R.K. Sharma": same semantic issue'),
'T40':('N','-','Y','N','"as clarified by the policy circular dated 11.3.2011": cue is about a policy circular, not D.S. Nakara'),
'T41':('N','-','N','Y','QUOTED: McDowell "per incuriam" is Nariman J in Shayara Bano, reproduced inside Sikri J\'s opinion (p.212); not this court\'s voice'),
'T42':('Y','Y','Y','Y','order of the court: M P Sharma stands overruled; raw target text truncated ("isposed of...") but anchor resolves to M P Sharma'),
'T43':('Y','Y','Y','Y','Sowmithri Vishnu overruled (anchor (1985) Supp SCC 137)'),
'T44':('Y','Y','Y','Y','M P Sharma overruled (plurality conclusions); duplicates T42 target'),
'T45':('Y','Y','Y','Y','"decisions of this Court saying to the contrary ... are accordingly overruled"; no anchor, unidentified target'),
'T46':('Y','Y','Y','Y','duplicate of T45 (same passage, different raw-target string)'),
'T47':('Y','Y','Y','Y','Sriharan: "we specifically overrule" Sangeet (2013) 2 SCC 452'),
'T48':('Y','Y','Y','Y','Bhanudas Krishna Gawde overruled'),
'T49':('Y','Y','Y','Y','V. Revathi overruled (anchor (1988) 2 SCC 72)'),
'T50':('Y','Y','Y','Y','Kharak Singh overruled to the extent stated'),
'T51':('Y','Y','Y','N','passage disapproves the SUBSEQUENT decisions following Kanhaiyalal; anchor binds to Kanhaiyalal itself (already captured by T54)'),
'T52':('Y','Y','Y','Y','"these two decisions do not lay down the correct law" (Subramanian, Kerala HC, and one other); raw target with context; no anchor'),
'T53':('Y','Y','Y','Y','Shri Kant Sharma does not lay down the correct law; resolved correctly'),
'T54':('Y','Y','Y','Y','Kanhaiyalal wrongly decided'),
}
rows=[]
for l in open(R+'/treatment_sample.jsonl'):
    e=json.loads(l); s=e['_sid']; t,d,v,g,n=V[s]
    full='Y' if (t,d,v,g)==('Y','Y','Y','Y') else 'N'
    rows.append([s,e['edge_id'],e['edge_type'],e['evidence']['doc_id'],e['evidence']['page'],e['attributes'].get('cue','').strip(),e.get('target') or '',(e.get('target_raw') or '')[:80],t,d,v,g,full,n])
with open(R+'/treatment_sample_verdicts.csv','w',newline='') as f:
    w=csv.writer(f); w.writerow(['sid','edge_id','edge_type','doc_id','page','cue','target','target_raw','type_ok','direction_ok','court_own_voice_ok','target_ok','fully_correct','note']); w.writerows(rows)
import collections
c=collections.defaultdict(lambda:[0,0,0])
for r in rows: c[r[2]][0]+=1; c[r[2]][1]+= r[8]=='Y'; c[r[2]][2]+= r[12]=='Y'
for k,v in c.items(): print(k,'n',v[0],'type_ok',v[1],'fully',v[2])
print('total', sum(v[2] for v in c.values()), '/', len(rows))
