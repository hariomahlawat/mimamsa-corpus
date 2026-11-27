"""Write a small manually assessed, derivative-bound legal research overlay."""
import json
import sqlite3
from pathlib import Path

root=Path('package-v2')
records={r['doc_id']:r for r in map(json.loads,(root/'records.jsonl').open())}
conn=sqlite3.connect((root/'search.sqlite').resolve().as_uri()+'?mode=ro&immutable=1',uri=True)
reviews={
' hc-allahabad-2018-wria-22663-2007-uphc011724832007-1-2018-07-16'.strip():{
 'bench':(1,"Hon'ble Manoj Misra,J.\nHon'ble Ved Prakash Vaish,J.","Manoj Misra and Ved Prakash Vaish"),
 'case_number':(1,'WRIT - A No. - 22663 of 2007','Writ A 22663 of 2007'),
 'decision_date':(3,'Order Date :- 16.7.2018','2018-07-16'),
 'order_type':(3,'The petition is dismissed.','Final disposition of the writ petition'),
 'material_facts':(1,'by treating\nhis date of birth as 13.1.1931','The department used the disputed birth date to retire the respondent in 1996.'),
 'legal_issues':(3,'without any enquiry as was contemplated by the rules','Whether the High Court should disturb the tribunal’s decision despite the lack of the contemplated enquiry.'),
 'arguments':(1,'the respondent was manipulated in the service records','The department alleged manipulation of the relevant service record.'),
 'reasoning':(3,'the view taken by the Tribunal does not call for any\ninterference','The Court declined to interfere, considering lack of enquiry and evidence and the surviving service record.'),
 'ratio_candidate':(3,'without any enquiry as was contemplated by the rules','On this record the High Court declined to disturb the tribunal’s decision. The passage is fact-specific and has no authority determination in this package.'),
 'other_observations':(3,'the Tribunal could have remanded the matter','The Court considered remand but said it would serve no purpose after the respondent’s death.'),
 'final_disposition':(3,'The petition is dismissed.','Writ petition dismissed.')},
'hc-allahabad-2018-wric-4147-2018-uphc010165912018-1-2018-02-05':{
 'bench':(1,"Hon'ble Tarun Agarwala,J.\nHon'ble Saumitra Dayal Singh,J.","Tarun Agarwala and Saumitra Dayal Singh"),
 'case_number':(1,'WRIT - C No. - 4147 of 2018','Writ C 4147 of 2018'),
 'decision_date':(1,'Order Date :- 5.2.2018','2018-02-05'),
 'order_type':(1,'The writ petition is dismissed.','Final procedural dismissal of this writ petition'),
 'material_facts':(1,'No.28569 of 2014, which was dismissed','A previous writ petition had been dismissed.'),
 'legal_issues':(1,'Second writ petition for the same cause of action','Maintainability of the second writ petition on the same cause of action.'),
 'ratio_candidate':(1,'Second writ petition for the same cause of action\nis not maintainable.','The stated maintainability ground for dismissing this second writ petition.'),
 'final_disposition':(1,'The writ petition is dismissed.','Writ petition dismissed.')}
}
with Path('manual-enrichment.jsonl').open('w') as out:
 for doc, fields in reviews.items():
    row=records[doc]
    pages=dict(conn.execute('SELECT physical_page,derivative FROM pages WHERE doc_id=?',(doc,)))
    findings={}
    for field,(page,excerpt,statement) in fields.items():
        start=pages[page].index(excerpt)
        findings[field]=dict(statement=statement,anchor=dict(physical_page=page,start=start,end=start+len(excerpt),text=excerpt))
    out.write(json.dumps(dict(schema='c14-manual-enrichment-v1',doc_id=doc,findings=findings,
         source_sha256=row['original_sha256'],derivative_sha256=row['derivative_sha256'],authority_status='unreviewed',
         verification_status='derivative-context-checked',application_eligible=False),ensure_ascii=False)+'\n')
print(len(reviews),'manually contextualized records')
