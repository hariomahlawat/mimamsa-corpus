import json, sys
a = json.load(open(sys.argv[1], encoding="utf-8")); b = json.load(open(sys.argv[2], encoding="utf-8"))
diff = [q for q in a if a[q] != b.get(q)]
print(f"queries {len(a)}  identical {len(a) - len(diff)}  different {len(diff)}")
for q in diff[:5]:
    x, y = a[q], b[q]
    for k in x:
        if x[k] != y.get(k):
            if k == "hits":
                i = next((i for i, (u, v) in enumerate(zip(x[k], y[k])) if u != v), min(len(x[k]), len(y[k])))
                print(f"  {q!r} hits differ at {i} (len {len(x[k])} vs {len(y[k])}): {x[k][i:i+1]} vs {y[k][i:i+1]}")
            else:
                print(f"  {q!r} {k}: {str(x[k])[:150]} vs {str(y[k])[:150]}")
