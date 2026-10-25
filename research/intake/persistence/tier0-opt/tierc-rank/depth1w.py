import sys, json
from collections import Counter, defaultdict
from math import comb


def v2(n):
    return (n & -n).bit_length() - 1


def s1_weighted(y, words, E):
    a = v2(y)
    mod = (1 << (a + 9)) * 5 ** 5
    g = Counter((d, e) for d, e in words)
    by_class = defaultdict(list)
    nonlow = 1
    for (d, e), c in g.items():
        if e < a + 9:
            by_class[e].append((d - 1, c))
        else:
            nonlow *= comb(c + E, E)
    base = ((10 ** 96 - 1) // 9) % mod
    states = {base: (1, 1)}
    for e in range(a + 9):
        grp = by_class.get(e)
        if grp:
            opts = [(0, 1, 1)]
            for w, c in grp:
                new = {}
                for s, cnt, wt in opts:
                    for m in range(c + 1):
                        f = comb(c - m + E - 1, E - 1)
                        k2 = s + m * w
                        o = new.get(k2, (0, 0))
                        new[k2] = (o[0] + cnt, o[1] + wt * f)
                opts = [(s, v[0], v[1]) for s, v in new.items()]
            p10 = pow(10, e, mod)
            nxt = {}
            for t, (cn, wt) in states.items():
                for s, c2, w2 in opts:
                    tt = (t + s * p10) % mod
                    o = nxt.get(tt, (0, 0))
                    nxt[tt] = (o[0] + cn * c2, o[1] + wt * w2)
            states = nxt
        mask = (1 << (e + 1)) - 1
        states = {t: v for t, v in states.items() if (t - y) & mask == 0}
        if not states:
            return 0, 0, nonlow
    s1 = 0
    wl = 0
    for t, (cn, wt) in states.items():
        if (t - y) % (5 ** 5) == 0:
            s1 += cn
            wl += wt
    return s1, wl, nonlow
