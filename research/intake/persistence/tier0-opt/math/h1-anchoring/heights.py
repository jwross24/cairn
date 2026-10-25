import sys
sys.path.insert(0, "/Users/jwross/Documents/cairn/research/intake/persistence/tier0")
import classify_open as C
from collections import Counter
rows = []
for f in sys.argv[1:]:
    for (s, M, a, nu, eps, y, sol) in C.entries(f):
        rows.append((s, M, a, y))
n = len(rows)
ys = sorted(y for *_, y in rows)
print("open patterns:", n, "distinct anchors:", len(set(ys)), "max anchor:", ys[-1])
for T in (10**9, 10**10, 10**11, 10**12, 10**13):
    print("patterns with anchor >", f"{T:.0e}", sum(1 for y in ys if y > T), "distinct anchors", len({y for y in ys if y > T}))
big = Counter(y for y in ys if y > 10**10)
for y, c in sorted(big.items(), key=lambda t: -t[0])[:12]:
    print(y, C.factor237(y), c)
bysq = Counter(len(M) for s, M, a, y in rows)
print("q distribution of open patterns:", dict(sorted(bysq.items())))
