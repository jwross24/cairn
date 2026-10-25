import sys
sys.path.insert(0, "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierc-rank")
from chainrank import *
import re

txt = open("/Users/jwross/Documents/cairn/research/intake/persistence/tier0/BAKER-CHAIN.md").read().split("\n")
rows = []
for ln in txt[233:272]:
    m = re.match(r"^\s*(\d+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*$", ln)
    if m:
        rows.append([int(m.group(1))] + [float(m.group(i)) for i in range(2, 8)])
worst = 0.0
n = 0
for r in rows:
    k = r[0]
    for a, col in ((0, 1), (1, 3), (40, 5)):
        x = float(log10_bound(alphas_for(a, 2), k, a))
        d = x - r[col]
        worst = max(worst, abs(d))
        n += 1
        if abs(d) > 0.0021:
            print("MISMATCH", k, a, x, r[col])
print("rows", len(rows), "cells", n, "max abs diff", worst)
