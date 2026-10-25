import sys
sys.dont_write_bytecode = True
from math import comb, log10
import count as C

assert sum(comb(120, j) * comb(200, 31 - j) for j in range(32)) == comb(320, 31)
print("Vandermonde: pairs(P,K) summed over J+L=k equals C(P+K,k) for every split (assert passed)")
print()
print("vertex             kmax  w=2logG'  log10 C(w,k)W   w3=3logG'  log10 pairs(a free)  gain  | sieve+lift estimate log10: open96 * (w/96+1)^k   vs sandwich open96*(D+1)^k")
for s, ex in C.VERT.items():
    ms = C.multisets(ex)
    kmax = max(sum(m.values()) for m in ms)
    top = max((m for m in ms if sum(m.values()) == kmax), key=lambda m: C.pairs(m, 700))
    lg = C.logG(kmax)
    w2 = C.window(kmax, 1)
    w3 = int(3 * lg + 0.7) + 1
    p2 = log10(C.pairs(top, w2))
    p3 = log10(C.pairs(top, w3))
    o96, D, kk = C.B1[s]
    lift = log10(o96) + kmax * log10(w2 / 96 + 1)
    sand = log10(o96) + kmax * log10(D + 1)
    print(f"{s:<18} {kmax:>3}  {w2:>6}   {p2:>10.1f}   {w3:>6}   {p3:>10.1f}      {p3 - p2:>5.1f}  | {lift:>8.1f}  vs {sand:>8.1f}")
