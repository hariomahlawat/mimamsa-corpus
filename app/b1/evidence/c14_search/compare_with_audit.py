"""Compare S1 search observations with the C14 walkthrough audit baseline (same 290-document release).

usage: python compare_with_audit.py <audit search_raw.json> <s1 search_raw_s1.json> <out.md>
The audit file is legal_knowledge/audit_work/C14-WALKTHROUGH/evidence/search_raw.json on branch
claude/c14-walkthrough-audit (corrected run, server timings present).
"""
import json
import sys

base = {q["id"]: q for q in json.load(open(sys.argv[1], encoding="utf-8-sig"))}
s1 = json.load(open(sys.argv[2], encoding="utf-8-sig"))


def rank(obs, doc):
    ids = [d["doc_id"] for d in obs["top_documents"]]
    return ids.index(doc) + 1 if doc in ids else None


rows = ["| Query | Text | Baseline mode / top 3 | S1 mode / top 3 | S1 chips |", "| --- | --- | --- | --- | --- |"]
for q in s1:
    b = base.get(q["id"].split("-")[0])
    o = q["observed"]
    top = lambda x: ", ".join(d["doc_id"] for d in x["top_documents"][:3]) or "—"  # noqa: E731
    rows.append(f"| {q['id']} | `{q['query']}`{' (service=army)' if q.get('params') else ''} | {b['observed']['mode']} · {top(b['observed'])} | "
                f"{o['mode']} · {top(o)} | {'; '.join(o['chips']) or '—'} |")
open(sys.argv[3], "w", encoding="utf-8").write("\n".join(rows) + "\n")

checks = {
    "Q28 IPC s.302 pinned with alias chip": lambda r: r["Q28"]["mode"] == "identifier" and any("IPC →" in c for c in r["Q28"]["chips"]) and r["Q28"]["top_passages"][0]["doc_id"] == "act-ipc-1860" and r["Q28"]["top_passages"][0]["tier"] == "identifier",
    "Q29 BNS s.103 pinned with alias chip": lambda r: r["Q29"]["mode"] == "identifier" and any("BNS →" in c for c in r["Q29"]["chips"]) and r["Q29"]["top_passages"][0]["doc_id"].startswith("act-bns-2023") and r["Q29"]["top_passages"][0]["tier"] == "identifier",
    "Q18 2013 INSC 408 ranks first by party name": lambda r: rank(r["Q18"], "sc-2013-dharamvir-singh-2013insc408") == 1,
    "Q19 SCC citation pinned or 'citation not held'": lambda r: any("Citation not recorded" in c for c in r["Q19"]["chips"]) or rank(r["Q19"], "sc-2013-dharamvir-singh-2013insc408") == 1,
    "Q25 suggestion dharamvir singh": lambda r: any("dharamvir singh" in c.lower() for c in r["Q25"]["chips"] if c.startswith("Did you mean")),
    "Q26 suggestion court martial": lambda r: any("court martial" in c for c in r["Q26"]["chips"] if c.startswith("Did you mean")),
    "Q27 suggestion disability pension": lambda r: any("disability pension" in c for c in r["Q27"]["chips"] if c.startswith("Did you mean")),
    "Q05 service=army: Army Act in top 3": lambda r: (rank(r["Q05-army"], "act-army-1950") or 99) <= 3,
    "Q07 service=army: Army Act in top 3": lambda r: (rank(r["Q07-army"], "act-army-1950") or 99) <= 3,
    "Q13 service=army: Army Act in top 3": lambda r: (rank(r["Q13-army"], "act-army-1950") or 99) <= 3,
}
obs = {q["id"]: q["observed"] for q in s1}
print(json.dumps({k: bool(f(obs)) for k, f in checks.items()}, indent=1))
print(json.dumps({k: {"baseline_army_act_rank": rank(base[k]["observed"], "act-army-1950"), "s1_army_act_rank": rank(obs[k + "-army"], "act-army-1950"),
                      "s1_first_army_act_passage": next((p for p in obs[k + "-army"]["top_passages"] if p["doc_id"] == "act-army-1950"), None)}
                  for k in ("Q05", "Q07", "Q13")}, indent=1, ensure_ascii=False))
