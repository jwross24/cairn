import sys
sys.dont_write_bytecode = True
from math import log10
import count as C

print("Largest log10 G' at which the joint pair count stays under a budget (top equation of each Tier-C vertex, a=1)")
print("vertex             kmax  log10 G'(Baker 2-ended)  budget 1e18  1e22  1e30")
for s, ex in C.VERT.items():
    ms = C.multisets(ex)
    kmax = max(sum(m.values()) for m in ms)
    top = max((m for m in ms if sum(m.values()) == kmax), key=lambda m: C.pairs(m, 700))
    res = []
    for bud in (18, 22, 30):
        lo, hi = 1.0, 500.0
        for _ in range(60):
            mid = (lo + hi) / 2
            w = int(2 * mid + 0.4 + 0.301) + 1
            if log10(C.pairs(top, w)) <= bud:
                lo = mid
            else:
                hi = mid
        res.append(lo)
    print(f"{s:<18} {kmax:>3}  {C.logG(kmax):>8.1f}                {res[0]:>7.1f} {res[1]:>6.1f} {res[2]:>6.1f}")
