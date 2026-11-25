import gzip,json,collections,re,hashlib,subprocess,sys
G=sys.argv[1]
E=[json.loads(l) for l in gzip.open(G+'/edges_candidate.jsonl.gz','rt')]+[json.loads(l) for l in open(G+'/edges_reviewed.jsonl')]
T={'FOLLOWS','APPLIES','DISTINGUISHES','CONSIDERS','EXPLAINS','DOUBTS','DISAPPROVES','OVERRULES'}
E=[e for e in E if e['edge_type'] in T]
cache={}
def text(doc):
    if doc not in cache:
        cache[doc]=subprocess.run(['git','-C','/home/user/c7','show',f'ad77758d:data/text/{doc}.txt'],capture_output=True,text=True).stdout
    return cache[doc]
def meta(doc):
    m=subprocess.run(['git','-C','/home/user/c7','show',f'ad77758d:data/meta/{doc}.json'],capture_output=True,text=True).stdout
    return json.loads(m) if m else {}
metas={}
res=collections.Counter(); bad=[]
nrm=lambda s: re.sub(r'\s+',' ',s).strip()
for e in E:
    ev=e['evidence']; d=ev['doc_id']; p=ev['passage']
    h=hashlib.sha256(p.encode()).hexdigest()==ev['passage_sha256'] or hashlib.sha256(nrm(p).encode()).hexdigest()==ev['passage_sha256']
    t=nrm(text(d)); ps=nrm(p)
    found=ps in t
    pg=False
    if found:
        i=t.find(ps)
        prev=[int(x) for x in re.findall(r'\[\[page (\d+)\]\]', t[:i])]
        cur=prev[-1] if prev else 1
        inside=[int(x) for x in re.findall(r'\[\[page (\d+)\]\]', ps)]
        pg= ev['page'] in [cur]+inside
    if d not in metas: metas[d]=meta(d)
    shaok = metas[d].get('sha256')==ev['source_copy_sha256']
    anc = bool(ev.get('anchor_text'))
    anc_in = anc and any(nrm(a) in t for a in ev['anchor_text'].split(' || '))
    res[(h,found,pg,shaok,anc,anc_in)]+=1
    if not (h and found and pg and shaok): bad.append((e['edge_id'],e['edge_type'],d,ev['page'],h,found,pg,shaok))
print(len(E)); 
for k,v in res.items(): print('hash,found,page,sha,anchor,anchor_in_text',k,v)
for b in bad[:15]: print(b)
