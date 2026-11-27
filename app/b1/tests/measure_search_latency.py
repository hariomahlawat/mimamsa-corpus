import json, os, time, urllib.request, urllib.parse, http.cookiejar, statistics, concurrent.futures as cf
base=os.environ["B1_URL"]
def client():
    op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    op.open(urllib.request.Request(base+"/api/login",data=json.dumps({"username":"reader","password":"reader-password-1"}).encode(),headers={"Content-Type":"application/json"}))
    return op
Q=["s.69 Army Act","2013 INSC 408","OA 411/2021","disability pension","court martial","summary of evidence","AFT jurisdiction","invalided out of service","exact:\"Entitlement Rules\"","desertion AND NOT pension","section:22 act:\"Army Rules\"","release medical board","\"court martial\" NEAR/10 delay","Civil Appeal No. 4949 of 2013","writ petition armed forces tribunal","field punishment","attributable to military service","sentence of dismissal","pension regulations 1961","Navy Act"]
op=client()
def one(q):
    t=time.perf_counter(); r=op.open(base+"/api/search?"+urllib.parse.urlencode({"q":q})).read(); return (time.perf_counter()-t)*1000
for q in Q: one(q)
seq=[one(q) for _ in range(5) for q in Q]
with cf.ThreadPoolExecutor(10) as ex: par=list(ex.map(one,[q for _ in range(10) for q in Q]))
def pct(a,p): a=sorted(a); return round(a[max(0,int(round(p/100*len(a)))-1)],1)
print(json.dumps({"queries":len(Q),"sequential":{"n":len(seq),"p50":pct(seq,50),"p95":pct(seq,95),"max":round(max(seq),1)},"concurrency10":{"n":len(par),"p50":pct(par,50),"p95":pct(par,95),"max":round(max(par),1)}}))
