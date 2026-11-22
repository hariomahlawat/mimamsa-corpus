"""WS-B cycle 3: name scan of the intern corpus for later judgments citing P0 / calibration cases (discovery leads only).
Usage: python3 cycle3_citescan.py <out.json> <snapshot_dir>"""
import json,glob,re,os,collections,sys
S=sys.argv[2].rstrip('/')+'/data'  # snapshot dir (git archive of origin/raw-data)
pats={
 'MANJEET':(r'Manjeet Singh','2015-05-12'),'ANGAD':(r'Angad Singh Titaria','2015-02-24'),'BALJIT':(r'Bal[jt]it Singh\W{0,40}\(1996|Union of India (?:and|&) (?:Anr\.?|Another)\.? v\.? (?:Sh\.? )?Bal[jt]it Singh','1996-10-11'),
 'BALACHANDRAN':(r'Balachandran Nair','2005-10-21'),'SURINDER_RATHORE':(r'Surinder Singh Rathore','2008-03-13'),'KESHAR':(r'Keshar Singh','2007-04-20'),
 'NAGA':(r"Naga People'?s? Movement",'1997-11-27'),'NAVJOT':(r'Navjot Sandhu','2005-08-04'),'MANI_RAM':(r'Mani Ram Bh?aira','2016-02-11'),
 'RAM_SARUP':(r'Ram Sarup v\.?\s*(?:The )?Union','1963-12-12'),
 'KULDEEP':(r'Kuldeep Yadav','2019-09-25'),'PPS_BEDI':(r'Prith[iv]i? Pal Singh','1982-08-25'),'PS_GILL':(r'P\.\s?S\.\s?Gill','2019-11-27'),
 'VIRENDRA':(r'Virendra Kumar','2020-01-07'),'SOM_DATT':(r'Som Datt','1968-09-20'),'JASBIR':(r'Jasbir Singh','2022-02-01'),
 'PARASHOTAM':(r'Paras?hott?am Dass','2023-03-21'),'CHANDRA_KUMAR':(r'L\.\s?Chandra Kumar','1997-03-18'),'SANTOSH_LOHAR':(r'Santosh Lohar','2023-10-03'),
}
recs={os.path.basename(f)[:-5]:json.load(open(f)) for f in glob.glob(S+'/meta/*.json')}
out=collections.defaultdict(list)
for d,m in recs.items():
    if m.get('doc_type')!='judgment' or not m.get('text_path'): continue
    try: t=re.sub(r'\s+',' ',open(S[:-5]+'/'+m['text_path'],errors='replace').read())
    except Exception: continue
    for k,(rx,dt) in pats.items():
        if (m.get('issue_date') or '')<=dt: continue
        mm=re.search(rx,t,re.I)
        if mm:
            pg=t[:mm.start()].count('[[page ')
            out[k].append((m['issue_date'],d,m['court'],pg,t[max(0,mm.start()-150):mm.end()+200]))
json.dump(out,open(sys.argv[1],'w'))
for k,v in out.items(): print(k,len(v),collections.Counter(x[2][:12] for x in v).most_common())
