import csv, sys, collections
W=sys.argv[1]; idx=[int(a) for a in sys.argv[2:]]
r=list(csv.DictReader(open(W+'/ADJUDICATION_SHEET.csv')))
items=collections.OrderedDict()
for x in r: items.setdefault(x['item_id'],[]).append(x)
keys=list(items)
for i in idx:
  v=items[keys[i]]
  print('#####',i,keys[i],v[0]['rep_sha256'][:12])
  for x in v:
    print(' ',x['coding'],'|HCN:',x['host_case_numbers'],'|P:',x['proceeding'],'|',x['printed_disposal'],'|',x['substantive_result'],'|ps:',x['party_specific'],'|',x['final_or_interim'],'|pg',x['page'],'para',x['para'],'|',x['confidence'],'|EX:',x['excerpt'][:200],'|N:',x['notes'][:300])
