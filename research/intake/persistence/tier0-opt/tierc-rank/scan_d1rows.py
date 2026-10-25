import re
from collections import Counter

SRC = "/Users/jwross/Documents/cairn/research/intake/persistence/tier0/DEEPCUT-run-final-d1.txt"
pat = re.compile(r"s=(\d+)\s+M=(\d+)\s+a=(\d+)\s+y=(\d+)\s+reps=(\d+)\s+cases=(\d+)\s+(\S+)")
c = Counter()
rows = []
for l in open(SRC):
    m = pat.search(l)
    if not m:
        continue
    y = int(m.group(4))
    r = (y % 3 == 0) + (y % 7 == 0)
    c[(r, m.group(7))] += 1
    rows.append((r, m.groups()))
print(dict(c))
print("rank-0 rows:", [g for r, g in rows if r == 0][:10])
