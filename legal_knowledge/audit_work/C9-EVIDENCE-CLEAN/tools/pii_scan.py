"""Counts-only scan for service-number-shaped tokens (officer form: 6-8 digits followed by optional space and 'M')
in every blob reachable from a commit, and in the C8-EVIDENCE tree at that commit. Prints paths and counts only."""
import subprocess, sys, re, collections
repo, tip = sys.argv[1:3]
g = lambda *a: subprocess.run(["git", "-C", repo, *a], capture_output=True, check=True).stdout
PAT = re.compile(rb"\b\d{6,8} ?M\b")
P = "legal_knowledge/audit_work/C8-EVIDENCE/"
by_path = collections.Counter()
for line in g("ls-tree", "-r", tip).decode().splitlines():
    meta, path = line.split("\t", 1)
    if meta.split()[1] != "blob": continue
    n = len(PAT.findall(g("cat-file", "blob", meta.split()[2])))
    if n: by_path[path] += n
inside = {p: n for p, n in by_path.items() if p.startswith(P)}
print(f"service-number-shaped tokens in tree at {tip[:12]}: {sum(by_path.values())} in {len(by_path)} files")
print(f"  inside C8-EVIDENCE: {sum(inside.values())} in {len(inside)} files")
for p, n in sorted(by_path.items()): print(f"  {n:4d} {p}")
