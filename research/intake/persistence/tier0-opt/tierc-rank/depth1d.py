from collections import Counter, defaultdict
from depth1c import class_pools, completions, v2

RANK_PARAMS = {2: (5, 9), "b": (9, 10), "c": (10, 12)}


def analyze_rank(y, words, E, kind=2):
    e5, e2 = RANK_PARAMS[kind]
    a = v2(y)
    top = max(a + e2, e5)
    mod2 = 1 << (a + e2)
    mod5 = 5 ** e5
    mod = mod2 * mod5
    pools = class_pools(words)
    low = sorted(e for e in pools if e < top)
    nonlow_total = 1
    for e, pool in pools.items():
        if e >= top:
            nonlow_total *= completions(pool, None, E - 1) + sum(completions(pool, d, E - 1) for d in pool)
    base = ((10 ** 96 - 1) // 9) % mod
    states = {base: (1, 1)}
    for e in range(top):
        pool = pools.get(e)
        if pool:
            opts = [(None, completions(pool, None, E - 1))] + [(d, completions(pool, d, E - 1)) for d in pool]
            p10 = pow(10, e, mod)
            nxt = {}
            for t, (cn, wt) in states.items():
                for d, f in opts:
                    tt = t if d is None else (t + (d - 1) * p10) % mod
                    o = nxt.get(tt, (0, 0))
                    nxt[tt] = (o[0] + cn, o[1] + wt * f)
            states = nxt
        m2 = 1 << min(e + 1, a + e2)
        m5 = 5 ** min(e + 1, e5)
        states = {t: v for t, v in states.items() if (t - y) % m2 == 0 and (t - y) % m5 == 0}
        if not states:
            return 0, 0, nonlow_total
    s1 = wl = 0
    for t, (cn, wt) in states.items():
        if (t - y) % mod == 0:
            s1 += cn
            wl += wt
    ncases = 1
    for e in low:
        ncases *= 1 + len(pools[e])
    return s1, wl * nonlow_total, ncases


def uncut_nodes(y, words, E, kind=2):
    e5, e2 = RANK_PARAMS[kind]
    a = v2(y)
    top = max(a + e2, e5)
    pools = class_pools(words)
    tot = 1
    ncases = 1
    for e, pool in pools.items():
        t = completions(pool, None, E - 1) + sum(completions(pool, d, E - 1) for d in pool)
        tot *= t
        if e < top:
            ncases *= 1 + len(pool)
    return tot, ncases
