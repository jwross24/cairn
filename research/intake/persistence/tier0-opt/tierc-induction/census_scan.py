import sys
import time
from array import array
from bisect import bisect_left
from math import log10
import re

NMAX = int(sys.argv[1]) if len(sys.argv) > 1 else 300
OUT = sys.argv[2] if len(sys.argv) > 2 else "census_out.txt"
KEYD = 18
SHIFT = 10 ** (KEYD - 4)
RUN = re.compile("0+")

buckets = [array("q") for _ in range(10000)]
runcount = {}
longruns = []
wit = []
total = 0
nbylen = {}
t0 = time.time()
limit = 10 ** NMAX
p2 = 1
a = 0
while p2 < limit:
    p3 = p2
    b = 0
    while p3 < limit:
        p7 = p3
        c = 0
        while p7 < limit:
            s = str(p7)
            n = len(s)
            total += 1
            if n >= KEYD:
                key = int(s[:KEYD])
                buckets[key // SHIFT].append(key)
            if "0000" in s:
                for m in RUN.finditer(s):
                    g = m.end() - m.start()
                    if g >= 4:
                        pos = m.start()
                        rk = (pos, g)
                        runcount[rk] = runcount.get(rk, 0) + 1
                        if g >= 5:
                            L = min(pos + g, KEYD)
                            if n >= KEYD:
                                wit.append((pos, g, L, int(s[:L]), n, a, b, c))
                        if g >= 6:
                            zeros = s.count("0", 0, pos)
                            longruns.append((n, a, b, c, pos, g, pos - zeros))
            p7 *= 7
            c += 1
        p3 *= 3
        b += 1
    p2 *= 2
    a += 1
    if a % 100 == 0:
        sys.stderr.write("a=%d total=%d %.0fs\n" % (a, total, time.time() - t0))

lines = []
lines.append("S-units below 10^%d: %d, scan %.0fs" % (NMAX, total, time.time() - t0))

maxg = max(g for (_, g) in runcount)
lines.append("longest zero run: %d" % maxg)
lines.append("zero runs by length g (all positions, count of runs):")
bylen = {}
for (pos, g), v in runcount.items():
    bylen[g] = bylen.get(g, 0) + v
for g in sorted(bylen):
    lines.append("  g=%d  %d" % (g, bylen[g]))

lines.append("max (s+g)/s over runs with g>=4, by prefix length bucket of s (s = digits before the run):")
edges = [1, 2, 3, 4, 6, 9, 17, 33, 65, 129, 10 ** 9]
for lo, hi in zip(edges[:-1], edges[1:]):
    best = None
    cnt = 0
    for (pos, g), v in runcount.items():
        if lo <= pos < hi:
            cnt += v
            if best is None or g > best[1] or (g == best[1] and pos < best[0]):
                best = (pos, g)
    if best:
        lines.append("  s in [%d,%d): runs=%d  maxg=%d at s=%d  ratio (s+g)/s=%.3f" % (lo, hi - 1, cnt, best[1], best[0], (best[0] + best[1]) / best[0]))

lines.append("zero runs with g>=6 (n a b c s g j=nonzero digits above):")
for r in sorted(longruns, key=lambda r: (-r[5], r[0])):
    lines.append("  " + " ".join(map(str, r)))

lcp_hist = {}
maxlcp = 0
maxpairs = []
eqkeys = 0
for bi, arr in enumerate(buckets):
    if len(arr) < 2:
        continue
    lst = sorted(arr)
    buckets[bi] = array("q", lst)
    for x, y in zip(lst, lst[1:]):
        if x == y:
            eqkeys += 1
            lcp = KEYD
        else:
            sx, sy = str(x), str(y)
            lcp = 0
            while sx[lcp] == sy[lcp]:
                lcp += 1
        lcp_hist[lcp] = lcp_hist.get(lcp, 0) + 1
        if lcp > maxlcp:
            maxlcp = lcp
            maxpairs = [(x, y)]
        elif lcp == maxlcp and len(maxpairs) < 5:
            maxpairs.append((x, y))
lines.append("adjacent sorted pairs of distinct units, by longest common leading prefix (digits), keys with n>=18:")
for l in sorted(lcp_hist):
    if l >= 8:
        lines.append("  lcp=%d  pairs=%d" % (l, lcp_hist[l]))
lines.append("max lcp %d, equal %d-digit keys: %d, examples %s" % (maxlcp, KEYD, eqkeys, maxpairs[:3]))
N = sum(len(x) for x in buckets)
lines.append("keys: %d; Benford random-model expected pairs sharing >=L digits: %s" % (
    N, ", ".join("L=%d:%.3g" % (L, N * N / 2 * 0.1698 * 10 ** (-(L - 1))) for L in range(12, 19))))


def count_prefix(L, val):
    lo = val * 10 ** (KEYD - L)
    hi = (val + 1) * 10 ** (KEYD - L)
    arr = buckets[lo // SHIFT]
    arr2 = arr
    i = bisect_left(arr2, lo)
    j = bisect_left(arr2, hi)
    return j - i


wstat = {}
for (pos, g, L, val, n, a_, b_, c_) in wit:
    sg = pos + g
    others = count_prefix(L, val) - 1
    key = min(sg, KEYD)
    d = wstat.setdefault(key, [0, 0])
    d[0] += 1
    if others > 0:
        d[1] += 1
lines.append("witness uniqueness: zero runs g>=5 in units with n>=18, grouped by min(s+g,18); count, with another unit sharing the leading min(s+g,18) digits:")
for k in sorted(wstat):
    lines.append("  s+g=%s%d  runs=%d  shared=%d" % (">=" if k == KEYD else "", k, wstat[k][0], wstat[k][1]))

hi_gap = []
for (pos, g, L, val, n, a_, b_, c_) in wit:
    if pos + g >= 16:
        hi_gap.append((pos, g, n, a_, b_, c_))
lines.append("runs g>=5 with s+g>=16: %d" % len(hi_gap))
open(OUT, "w").write("\n".join(lines) + "\n")
