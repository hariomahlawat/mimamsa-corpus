import json,sys
r=json.load(open(sys.argv[1]))
def e(x): return f"k={x['k']} n={x['n']} cl={x['clusters']} unw={x['unweighted']} W{x['unweighted_wilson95']} w={x['weighted']} CP{x['weighted_design_cp95']} neff={x['weighted_design_cp_n_eff']}"
print("uncodable",r["uncodable"]); print("headline",r.get("headline_status")); print("anchor",r["evidence_anchor"])
def block(o,ind=""):
  for f,v in o.items():
    if not isinstance(v,dict) or "strict_precision" not in v: continue
    print(ind+f)
    for m in ["strict_precision","family_precision","coverage","coverage_counting_uncodable_items_as_not_covered"]: print(ind+"  ",m,e(v[m]))
    print(ind+"   cats",v["categories"],"undet",v["gold_units_undeterminable"],"abst",v["abstained"])
block(r["overall"])
for t,o in r.get("by_predicted_relation_type",{}).items(): print("TYPE",t); block(o,"  ")
for lab,s in r["sensitivity"].items(): print(lab,s["items_excluded"]); block(s["estimates"],"  ")
for k in ["by_court","by_stratum"]:
  for c,o in r[k].items(): print(k,c,o["targets_status"]); block(o["estimates"],"   ")
