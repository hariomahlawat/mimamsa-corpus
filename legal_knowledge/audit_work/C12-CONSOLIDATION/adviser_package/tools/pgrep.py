"""Helper: grep a pattern within pages of a text file at a git commit (read-only)."""
import re, subprocess, sys
doc, pat = sys.argv[1], sys.argv[2]
pages = sys.argv[3].split(',') if len(sys.argv) > 3 else None
t = subprocess.run(['git', '-C', '/home/user/c7', 'show', f'ad77758d:data/text/{doc}.txt'], capture_output=True, text=True, check=True).stdout
parts = re.split(r'\[\[page (\d+)\]\]', t)
for i in range(1, len(parts), 2):
    p, body = parts[i], re.sub(r'\s+', ' ', parts[i + 1])
    if pages and p not in pages:
        continue
    for m in re.finditer(pat, body, re.I):
        print(f'p.{p}: ...{body[max(0, m.start()-160):m.end()+200]}...')
