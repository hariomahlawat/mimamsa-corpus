"""Counts-only check that intermediate C8-EVIDENCE blobs from the old branch are not reachable from the clean branch.
Prints ids, paths and counts; never prints blob content."""
import subprocess, sys, json, re
repo, base, old_tip, new_tip = sys.argv[1:5]
def g(*a, inp=None):
    return subprocess.run(["git", "-C", repo, *a], capture_output=True, check=True, input=inp).stdout
P = "legal_knowledge/audit_work/C8-EVIDENCE"
commits = g("rev-list", f"{base}..{old_tip}").decode().split()
old = {}   # blob -> set(paths)
for c in commits:
    for line in g("ls-tree", "-r", c, "--", P).decode().splitlines():
        meta, path = line.split("\t", 1)
        old.setdefault(meta.split()[2], set()).add(path)
final = {l.split()[2] for l in g("ls-tree", "-r", old_tip, "--", P).decode().splitlines()}
removed = {b: p for b, p in old.items() if b not in final}
reach = set(l.split()[0] for l in g("rev-list", "--objects", new_tip).decode().splitlines())
hit = sorted(b for b in removed if b in reach)
print(f"old-branch commits examined: {len(commits)}")
print(f"distinct C8-EVIDENCE blobs on old branch: {len(old)}; in final reviewed tree: {len(final)}; intermediate (removed/changed): {len(removed)}")
print(f"objects reachable from clean branch: {len(reach)}")
print(f"intermediate blobs reachable from clean branch: {len(hit)}")
for b in hit: print("  REACHABLE", b, sorted(removed[b]))
# fragment check on the B-03 files
targets = [b for b, ps in removed.items() if any(re.search(r"render_run[12]\.jsonl$|page_structure\.json$", p) for p in ps)]
print(f"B-03 target blob versions (render_run1/2.jsonl, page_structure.json, intermediate): {len(targets)}")
frags = set()
def walk(o, key="$"):
    if isinstance(o, dict):
        for k, v in o.items(): walk(v, k)
    elif isinstance(o, list):
        for v in o: walk(v, key)
    elif isinstance(o, str) and key in ("text", "first_line", "last_line"):
        w = 40 if key == "text" else 30
        for i in range(0, max(len(o) - w + 1, 0), 10): frags.add(o[i:i+w])
for b in targets:
    data = g("cat-file", "blob", b).decode("utf-8", "replace")
    for line in data.splitlines():
        try: walk(json.loads(line))
        except Exception:
            try: walk(json.loads(data)); break
            except Exception: pass
print(f"text fragments (text: 40-char, first/last_line: 30-char windows, step 10) extracted from those blobs: {len(frags)}")
# search: every blob in the clean branch's C8-EVIDENCE tree and every non-binary blob changed on the branch vs staging
tree_blobs = {}
for line in g("ls-tree", "-r", new_tip, "--", P).decode().splitlines():
    meta, path = line.split("\t", 1); tree_blobs[meta.split()[2]] = path
counts = {}
for b, path in tree_blobs.items():
    data = g("cat-file", "blob", b).decode("utf-8", "replace")
    n = sum(1 for f in frags if f in data)
    if n: counts[path] = n
print(f"clean-branch C8-EVIDENCE files containing any fragment: {len(counts)}")
for p, n in sorted(counts.items()): print(f"  {n:6d} fragments  {p}")
