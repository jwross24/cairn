import json, sys
from collections import defaultdict
cnt = {}
for ln in open("../tierc-rank/s2_40k.out"):
    t = ln.split()
    if t[-1].startswith("OVERFLOW"):
        continue
    y, k = t[0], int(t[1])
    if k != 0:
        continue
    for tok in t[2:-1]:
        nu, c = tok.split(":")
        cnt[(int(y), int(nu))] = int(c)
tot = sum(cnt.values())
cell_k = defaultdict(list)
for fn in sys.argv[1:]:
    for ln in open(fn):
        r = json.loads(ln)
        cell_k[(r["y"], r["nu"])].append(len(r["words"]))
rows = []
for c, ks in cell_k.items():
    rows.append((cnt[c] / tot, c, len(ks), sum(1 for k in ks if k >= 30) / len(ks), sum(ks) / len(ks)))
rows.sort(reverse=True)
print("cells with pilot samples", len(rows), "of", len(cnt))
for r in rows[:25]:
    print("share %.4f y=%d nu=%d n=%d f30=%.3f meank=%.1f" % (r[0], r[1][0], r[1][1], r[2], r[3], r[4]))
hi = [r for r in rows if r[3] > 0.2]
print("cells f30>0.2:", len(hi), "mass share", sum(r[0] for r in hi))
print("mass-weighted f30 by estimate", sum(r[0] * r[3] for r in rows))
import math
sh = sorted((c / tot for c in cnt.values()), reverse=True)
print("top5 shares", sh[:5], "top 50 cum", sum(sh[:50]))
