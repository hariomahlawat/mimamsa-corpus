import gzip,json,random,sys
G=sys.argv[1]; out=sys.argv[2]
E=[json.loads(l) for l in gzip.open(G+'/edges_candidate.jsonl.gz','rt')]
plan={'FOLLOWS':14,'CONSIDERS':12,'DISTINGUISHES':6,'APPLIES':4,'EXPLAINS':4,'DOUBTS':1,'OVERRULES':9,'DISAPPROVES':4}
random.seed(13405)
S=[]
for t,n in plan.items():
    pool=sorted([e for e in E if e['edge_type']==t], key=lambda e:e['edge_id'])
    S+= pool if n>=len(pool) else random.sample(pool,n)
with open(out,'w') as f:
    for i,e in enumerate(S):
        e['_sid']=f"T{i+1:02d}"; f.write(json.dumps(e)+'\n')
print(len(S))
