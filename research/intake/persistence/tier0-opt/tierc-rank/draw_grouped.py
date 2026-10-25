import sys, random, bisect
from collections import Counter

src = sys.argv[1]
n = int(sys.argv[2])
seed = int(sys.argv[3])
out = sys.argv[4]
items = []
for ln in open(src):
    t = ln.split()
    if t[-1].startswith("OVERFLOW"):
        continue
    y, k = t[0], int(t[1])
    for tok in t[2:-1]:
        nu, c = tok.split(":")
        items.append((y, k, int(nu), int(c)))
cum = []
s = 0
for it in items:
    s += it[3]
    cum.append(s)
random.seed(seed)
cnt = Counter()
for _ in range(n):
    r = random.randrange(s)
    cnt[bisect.bisect_right(cum, r)] += 1
with open(out, "w") as f:
    for i, m in sorted(cnt.items()):
        y, k, nu, c = items[i]
        f.write(f"{y} {k} {nu} {m}\n")
print("population patterns", s, "cells", len(items), "distinct cells drawn", len(cnt))
