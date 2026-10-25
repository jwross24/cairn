import sys, random, bisect

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
with open(out, "w") as f:
    for _ in range(n):
        r = random.randrange(s)
        i = bisect.bisect_right(cum, r)
        y, k, nu, c = items[i]
        f.write(f"{y} {k} {nu}\n")
print("population patterns", s, "cells", len(items))
