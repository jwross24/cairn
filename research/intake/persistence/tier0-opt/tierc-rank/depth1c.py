import sys, json
from collections import Counter, defaultdict
from itertools import product


def v2(n):
    return (n & -n).bit_length() - 1


def class_pools(words):
    pools = defaultdict(Counter)
    for d, e in words:
        pools[e][d] += 1
    return pools


def completions(pool, x0, ncopies):
    left = Counter(pool)
    if x0 is not None:
        left[x0] -= 1
    vals = [d for d, c in left.items() if c > 0]
    memo = {}

    def rec(pos, cnt):
        if pos == 0:
            return 1
        key = (pos, tuple(sorted(cnt.items())))
        if key in memo:
            return memo[key]
        tot = rec(pos - 1, cnt)
        for d in list(cnt):
            if cnt[d] > 0:
                cnt[d] -= 1
                tot += rec(pos - 1, cnt)
                cnt[d] += 1
        memo[key] = tot
        return tot

    return rec(ncopies, Counter({d: left[d] for d in vals}))


def analyze(y, words, E):
    a = v2(y)
    mod = (1 << (a + 9)) * 5 ** 5
    pools = class_pools(words)
    low = sorted(e for e in pools if e < a + 9)
    nonlow_total = 1
    for e, pool in pools.items():
        if e >= a + 9:
            tot = completions(pool, None, E - 1) + sum(completions(pool, d, E - 1) for d in pool)
            nonlow_total *= tot
    base = ((10 ** 96 - 1) // 9) % mod
    states = {base: (1, 1)}
    for e in range(a + 9):
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
        mask = (1 << (e + 1)) - 1
        states = {t: v for t, v in states.items() if (t - y) & mask == 0}
        if not states:
            return 0, 0, nonlow_total
    s1 = wl = 0
    for t, (cn, wt) in states.items():
        if (t - y) % (5 ** 5) == 0:
            s1 += cn
            wl += wt
    ncases = 1
    for e in low:
        ncases *= 1 + len(pools[e])
    return s1, wl * nonlow_total, ncases
