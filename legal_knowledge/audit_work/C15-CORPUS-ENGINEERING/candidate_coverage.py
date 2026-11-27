"""Count evidence-backed coverage, independently of application indices."""
import argparse
from collections import Counter
import json
from pathlib import Path

def rows(path):
    if path.is_file():
        with path.open() as f:
            yield from (json.loads(line) for line in f)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('records',type=Path)
    p.add_argument('output',type=Path)
    p.add_argument('overlays',type=Path,nargs='*')
    o=p.parse_args()
    docs=list(rows(o.records))
    sha={x['original_sha256'] for x in docs}
    courts=Counter()
    for x in docs:
        doc=x['doc_id']
        cohort=x['court_metadata']
        if not cohort:
            if doc.startswith('AFT-GUW-'):cohort='AFT Guwahati'
            elif doc.startswith('SC-'):cohort='Supreme Court of India'
            elif doc.startswith('CA01-'):cohort='Statutory source'
            else:cohort='unresolved'
        courts[cohort]+=1
    categories=Counter()
    reviewed=set()
    for file in o.overlays:
        for rec in rows(file):
            if rec.get('review_state')!='context-reviewed-selected-findings' or rec['doc_id'] in reviewed:
                continue
            reviewed.add(rec['doc_id'])
            categories[rec['primary_category']]+=1
    report={'candidates':len(docs),'distinct_originals_in_candidates':len(sha),
            'courts_or_catalog_cohorts':dict(courts),'subject_counts_context_reviewed_only':dict(categories),
            'context_reviewed':len(reviewed),'active_application_eligible':sum(bool(x['application_eligible']) for x in docs),
            'authority_policy':'Authority is separately unreviewed; coverage is not a release or authentication opinion.'}
    o.output.write_text(json.dumps(report,indent=2)+'\n')
