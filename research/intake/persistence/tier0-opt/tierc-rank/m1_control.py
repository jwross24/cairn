import sys, re, math
sys.path.insert(0, "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierc-rank")
from chainrank import *

SRC = "/Users/jwross/Documents/cairn/research/intake/persistence/tier0/SANDWICH-run.txt"
pat = re.compile(r"s=(\d+)\s+M=(\d+)\s+a=(\d+)\s+y=(\d+)\s+k=(\d+)\s+reps=(\d+)\s+log10G=([\d.]+)\s+depth=(\d+)\s+subcosets=(\d+)\s+min-bound=([\d.]+)\s+margin=\+([\d.]+)")


def rank_of(y):
    return (y % 3 == 0) + (y % 7 == 0)


def depth_needed(lg):
    return 1 if lg <= 72 else math.ceil((lg - 72) / 48) + 1


rows = [pat.search(l) for l in open(SRC)]
rows = [m for m in rows if m]
print("rows", len(rows))
cache = {}
bad = 0
closed = 0
refused_inflated = 0
rk = {0: 0, 1: 0, 2: 0}
worst = 0.0
for m in rows:
    s, M, a, y, k, reps, lgrec, dep, sub, minb, marg = m.groups()
    a, y, k, dep = int(a), int(y), int(k), int(dep)
    lgrec, minb = float(lgrec), float(minb)
    rk[rank_of(y)] += 1
    key = (k, a)
    if key not in cache:
        cache[key] = float(log10_bound(alphas_for(a, 2), k, a))
    g = cache[key]
    worst = max(worst, abs(g - lgrec))
    if abs(g - lgrec) > 0.011:
        bad += 1
    if minb > g:
        closed += 1
    if not (minb > 400.0):
        refused_inflated += 1
print("rank of anchors", rk)
print("log10G reproduced within 0.011 for", len(rows) - bad, "of", len(rows), "max abs diff", round(worst, 4))
print("closed at recorded depth (min-bound > my G):", closed, "of", len(rows))
print("inflated G=10^400 refused:", refused_inflated, "of", len(rows))
dn = [depth_needed(cache[(int(m.group(5)), int(m.group(3)))]) for m in rows]
rec = [int(m.group(8)) for m in rows]
print("depth rule: matches recorded depth", sum(1 for x, y in zip(dn, rec) if x == y), "of", len(rows), "; not above recorded:", sum(1 for x, y in zip(dn, rec) if x <= y))

for m in rows:
    s, M, a, y, k, reps, lgrec, dep, sub, minb, marg = m.groups()
    y, a, k = int(y), int(a), int(k)
    if rank_of(y) == 1:
        which = "b" if y % 3 == 0 else "c"
        g1 = float(log10_bound(alphas_for(a, 1, which), k, a))
        print("rank-1 row: s", s, "M", M, "y", y, "a", a, "k", k, "recorded depth", dep, "min-bound", minb, "G rank-2 (recorded)", lgrec, "G rank-1 (mine)", round(g1, 2), "closes at recorded depth:", float(minb) > g1, "depth needed with G rank-1:", depth_needed(g1))
