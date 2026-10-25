import sys
sys.dont_write_bytecode = True
from fractions import Fraction
from math import comb, factorial, log10

G = {8: 72.37, 12: 109.46, 16: 146.85, 20: 181.08, 24: 215.07, 28: 249.19, 31: 279.23, 36: 317.93, 40: 355.6, 44: 393.93}
KS = sorted(G)


def logG(k):
    if k <= KS[0]:
        return G[KS[0]] * k / KS[0]
    for lo, hi in zip(KS, KS[1:]):
        if k <= hi:
            return G[lo] + (G[hi] - G[lo]) * (k - lo) / (hi - lo)
    return G[KS[-1]] + 9.0 * (k - KS[-1])


DIG = {2: (1, 0, 0), 3: (0, 1, 0), 4: (2, 0, 0), 6: (1, 1, 0), 7: (0, 0, 1), 8: (3, 0, 0), 9: (0, 2, 0)}
ORDER = [9, 8, 7, 6, 4, 3, 2]


def multisets(ex):
    out = []

    def rec(i, rem, cur):
        if i == len(ORDER):
            if rem == (0, 0, 0):
                out.append(dict(cur))
            return
        d = ORDER[i]
        v = DIG[d]
        j = 0
        r = rem
        while all(x >= 0 for x in r):
            cur[d] = j
            rec(i + 1, r, cur)
            j += 1
            r = (r[0] - v[0], r[1] - v[1], r[2] - v[2])
        cur[d] = 0

    rec(0, tuple(ex), {})
    return out


def sub_weights(m):
    poly = [Fraction(1)]
    for d, c in m.items():
        if c == 0:
            continue
        term = [Fraction(1, factorial(j)) for j in range(c + 1)]
        new = [Fraction(0)] * (len(poly) + c)
        for i, x in enumerate(poly):
            for j, y in enumerate(term):
                new[i + j] += x * y
        poly = new
    return [int(poly[kk] * factorial(kk)) for kk in range(len(poly))]


def pairs(m, w):
    W = sub_weights(m)
    return sum(comb(w, kk) * W[kk] for kk in range(len(W)) if kk <= w)


def window(k, a):
    lg = logG(k)
    return int(2 * lg + 0.4 + 0.301 * a) + 1


VERT = {
    3416267673274176: (6, 27, 1),
    128421199872: (23, 7, 1),
    913217421312: (29, 5, 1),
    727326941773824: (39, 3, 2),
    112717121716224: (34, 8, 0),
    1438916737499136: (24, 6, 6),
}
RECORDED = {3416267673274176: 306, 128421199872: 925, 913217421312: 911, 727326941773824: 834, 112717121716224: 2446, 1438916737499136: 829}
B1 = {3416267673274176: (2e11, 8, 34), 128421199872: (3e11, 7, 31), 913217421312: (9e11, 8, 35), 727326941773824: (6e13, 10, 44), 112717121716224: (1e14, 9, 42), 1438916737499136: (1e14, 8, 36)}

if __name__ == "__main__":
    print("vertex             n_multisets(recorded) kmax  top-eq window(a=1)  log10 pairs(top eq)  log10 pairs(all eqs, a=1)  log10 (a=160)   pipeline upper log10: open@96*(D+1)^kmax")
    for s, ex in VERT.items():
        ms = multisets(ex)
        assert 2 ** ex[0] * 3 ** ex[1] * 7 ** ex[2] == s
        tot = {1: 0, 160: 0}
        top = None
        kmax = max(sum(m.values()) for m in ms)
        for m in ms:
            k = sum(m.values())
            for a in (1, 160):
                tot[a] += pairs(m, window(k, a))
            if k == kmax and (top is None or pairs(m, window(k, 1)) > top[0]):
                top = (pairs(m, window(k, 1)), window(k, 1), m)
        o96, D, kk = B1[s]
        pipe = log10(o96) + kk * log10(D + 1)
        print(f"{s:<18} {len(ms):>5} ({RECORDED[s]:>4})  {kmax:>3}  {top[1]:>6}  {log10(top[0]):>12.1f}  {log10(tot[1]):>12.1f}  {log10(tot[160]):>12.1f}  {pipe:>12.1f}")
    print("window rule: w = 2*log10(G'(k)) + 0.4 + 0.301*a pinned digits (P + K) so that the expected number of lattice points per pair is about 1")
