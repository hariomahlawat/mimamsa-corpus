# reads pipe-separated lines from stdin: item_id|cited_string|cited_case_name|target|relation|voice|excerpt|confidence|notes
import sys,json
W='/tmp/claude-0/-home-user-mimamsa-corpus/9dd71a54-b050-5d1e-a2e9-2ceef8ac3e20/scratchpad/c13/coding/H-REL-C13/coder_2/'
K=['item_id','cited_string','cited_case_name','target','relation_type','voice','excerpt','confidence','notes']
REL={'cites','follows','applies','distinguishes','overrules','doubts','not_followed','refers_to_larger_bench','other','unclear',''}
VO={'court_own','quoted_passage','party_submission','lower_forum','editorial','unclear',''}
out=[]
if True:
    for line in sys.stdin:
        line=line.rstrip('\n')
        if not line.strip(): continue
        p=line.split('|')
        assert len(p)==9,(len(p),line)
        d=dict(zip(K,[x.strip() for x in p]))
        if d['cited_string']=='NONE':
            d.update(relation_type='other',voice='unclear',confidence='high',target='',cited_case_name='')
        assert d['relation_type'] in REL and d['voice'] in VO and d['confidence'] in {'high','medium','low',''},line
        out.append(json.dumps(d)+'\n')

open(W+'tools/codes.jsonl','a').writelines(out)
print('added',len(out))
