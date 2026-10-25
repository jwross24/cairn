import sys
from math import log, log10

OUT = sys.argv[1] if len(sys.argv) > 1 else "chain_out.txt"
L = []


def lsum(a, b):
    m = max(a, b)
    return m + log10(10 ** (a - m) + 10 ** (b - m))


def l1p(x):
    return lsum(0.0, x)


def F_two_ended(k, K, Y, K0, Z0, top_start=None, top_levels=0, top_step=0.0):
    best = None
    for m in range(1, k + 1):
        if top_levels and m <= top_levels:
            s = log10(top_step * m)
        elif top_levels:
            s = log10(top_step * top_levels) + (m - top_levels) * l1p(K)
        else:
            s = K0 + (m - 1) * l1p(K)
        e = Z0 + (k - m) * l1p(Y)
        v = lsum(s, e)
        if best is None or v < best[0]:
            best = (v, m)
    return best


K, Y, K0 = 16.7, 18.2, 14.7
L.append("T6 reproduction (log10 n bound = min_m [K0(1+K)^(m-1) + Z0(1+Y)^(k-m)], K=10^16.7, Y=10^18.2, K0=Z0=10^14.7):")
for k in (31, 44):
    L.append("  k=%d: %.2f at m=%d  (theta NOTES T6 quotes 396.9 at k=44)" % ((k,) + F_two_ended(k, K, Y, K0, K0)))

corpus = log10(6885)
L.append("log10(6885) = %.3f; the bottom-end floor log10 Z0 = 14.7 exceeds it by %.2f orders" % (corpus, 14.7 - corpus))
for k, logU, step in ((31, 281.5, 16.7), (44, 402.1, 18.2)):
    it = (logU - corpus) / step
    L.append("  k=%d: iterations from the corpus to log10 U=%.1f at 10^%.1f per step: %.2f -> %d" % (k, logU, step, it, int(it) + 1))

L.append("Baker separation length G* (distinct S-units share fewer than G* leading digits), Matveev n=3 and n=4 (D=1, A_i = log of 2,3,7[,5]):")
A3 = log(2) * log(3) * log(7)
A4 = A3 * log(5)
C3 = 1.4 * 30 ** 6 * 3 ** 4.5
C4 = 1.4 * 30 ** 7 * 4 ** 4.5
L.append("  C(3)=%.3e  C(3)*A=%.3e   C(4)=%.3e  C(4)*A=%.3e" % (C3, C3 * A3, C4, C4 * A4))
for k, logU in ((31, 281.5), (44, 402.1)):
    lnB = log(2.1) + logU * log(10)
    g3 = C3 * A3 * (1 + lnB) / log(10)
    g4 = C4 * A4 * (1 + lnB) / log(10)
    thr = 4 * logU
    L.append("  k=%d: ln B=%.1f  G*(3 logs)=10^%.2f  G*(4 logs)=10^%.2f  exceptional scale 4 log10 B=%.0f (10^%.2f)" % (k, lnB, log10(g3), log10(g4), thr, log10(thr)))

L.append("per-prefix verification (T8) trade: verify all prefixes to depth j0 by lattice reduction, Baker above.")
L.append("  gap after a non-exceptional prefix <= 4 log10 B (taken as Gne); patterns per level 8*Gne; cost log10 = j0*log10(8*Gne).")
for k, logU, step_k, step_y in ((31, 281.5, 16.7, 18.2), (44, 402.1, 16.7, 18.2)):
    Gne = 4 * logU
    L.append("  k=%d, Gne=%.0f, log10 patterns/level=%.2f" % (k, Gne, log10(8 * Gne)))
    for j0 in (0, 1, 2, 3, 5, 10, 20, 30, k):
        if j0 == 0:
            v = F_two_ended(k, step_k, step_y, 14.7, 14.7)
        else:
            v = F_two_ended(k, step_k, step_y, 14.7, 14.7, top_levels=j0, top_step=Gne)
        L.append("    j0=%2d: cost 10^%.1f reductions, log10 U = %.1f" % (j0, j0 * log10(8 * Gne), v[0]))

L.append("T9 requirement (S1=10^14.7 to target): per-gap multiplier Y max:")
for k in (31, 44):
    for tgt, name in ((72.0, "depth-1 target 10^72"),):
        one = (tgt - 14.7) / (k - 1)
        two = 2 * one
        L.append("  k=%d %s: one-ended 10^%.2f, two-ended 10^%.2f; Matveev/Yu 10^16.7/10^18.2 -> shortfall 10^%.1f to 10^%.1f (two-ended)" % (k, name, one, two, 16.7 - two, 18.2 - two))
open(OUT, "w").write("\n".join(L) + "\n")
