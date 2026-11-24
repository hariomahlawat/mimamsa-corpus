"""Counts-only attribution of fragment matches (see sensitive_check.py) to source copy, with a mechanical classification
of digit-bearing fragments. Never prints content."""
import subprocess, sys, json, re, collections
repo, base, old_tip, new_tip = sys.argv[1:5]
g = lambda *a: subprocess.run(["git", "-C", repo, *a], capture_output=True, check=True).stdout
P = "legal_knowledge/audit_work/C8-EVIDENCE"
final = {l.split()[2] for l in g("ls-tree", "-r", old_tip, "--", P).decode().splitlines()}
frag_src = collections.defaultdict(set)
for c in g("rev-list", f"{base}..{old_tip}").decode().split():
    for line in g("ls-tree", "-r", c, "--", P).decode().splitlines():
        meta, path = line.split("\t", 1); b = meta.split()[2]
        if b in final or not re.search(r"render_run[12]\.jsonl$|page_structure\.json$", path): continue
        data = g("cat-file", "blob", b).decode("utf-8", "replace")
        try: objs = [json.loads(data)]
        except Exception: objs = [json.loads(l) for l in data.splitlines() if l.strip()]
        def walk(o, src, k="$"):
            if isinstance(o, dict):
                src = o.get("held_path", src)
                for kk, v in o.items(): walk(v, src, kk)
            elif isinstance(o, list):
                for v in o: walk(v, src, k)
            elif isinstance(o, str) and k in ("text", "first_line", "last_line"):
                w = 40 if k == "text" else 30
                for i in range(0, max(len(o) - w + 1, 0), 10): frag_src[o[i:i + w]].add((src or "?").split("/")[-1])
        for o in objs: walk(o, None)
newdata = {}
for line in g("ls-tree", "-r", new_tip, "--", P).decode().splitlines():
    meta, path = line.split("\t", 1); newdata[path] = g("cat-file", "blob", meta.split()[2]).decode("utf-8", "replace")
allnew = "\n".join(newdata.values())
matched = [f for f in frag_src if f in allnew]
CASE_NO = re.compile(r"\d{1,6}\s*/\s*\d{4}")
SVC = re.compile(r"\b\d{6,8} ?M\b")
digit = [f for f in matched if re.search(r"\d{5,}", f)]
by = collections.Counter(s for f in matched for s in frag_src[f])
print("matched distinct fragments:", len(matched))
print("fragments attributed to more than one source copy:", sum(1 for f in matched if len(frag_src[f]) > 1))
print("by source copy (a fragment shared by two copies counts once for each):", dict(sorted(by.items())))
print("matched fragments containing a run of >=5 digits:", len(digit))
print("  of which contain a case-number form NNN/YYYY:", sum(1 for f in digit if CASE_NO.search(f)))
print("  of which contain a service-number-shaped token:", sum(1 for f in digit if SVC.search(f)))
print("matched fragments containing a service-number-shaped token (any):", sum(1 for f in matched if SVC.search(f)))
ny = [f for f in matched if any("yadav" in s.lower() for s in frag_src[f])]
print("matched fragments from the N S Yadav copy:", len(ny))
files = collections.Counter(p.split("C8-EVIDENCE/")[1] for f in ny for p, d in newdata.items() if f in d)
print("  files containing them:", dict(sorted(files.items())))
