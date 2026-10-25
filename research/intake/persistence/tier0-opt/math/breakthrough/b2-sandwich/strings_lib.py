from common import *
from math import factorial
from functools import lru_cache

def groups(De):
    g = defaultdict(Counter)
    for d, e in De: g[e][d] += 1
    return g

def acc_modulus(a):
    return 5 ** 5, 2 ** (a + 9)

def class_ways(mult, slots):
    vals = sorted(mult.items())
    @lru_cache(None)
    def ways(i, left):
        if i == len(vals): return 1
        v, m = vals[i]
        t = 0
        for c in range(0, min(m, left) + 1):
            t += _choose(left, c) * ways(i + 1, left - c)
        return t
    return ways(0, slots)

def _choose(n, k):
    return factorial(n) // (factorial(k) * factorial(n - k))

def enum_low(De, y, a):
    g = groups(De); w = a + 9
    classes = sorted(e for e in g if e < w)
    out = []
    def rec(p, L, used):
        if p == w:
            if (L - y) % (5 ** 5 * 2 ** w) == 0: out.append(dict(used))
            return
        e = p
        opts = [None]
        if e in g:
            for d in sorted(g[e]):
                if g[e][d] - used.get((e, d), 0) > 0: opts.append(d)
        for d in opts:
            dig = 1 if d is None else d
            L2 = L + dig * 10 ** p
            if (L2 - y) % 2 ** (p + 1): continue
            if p == 4 and (L2 - y) % 5 ** 5: continue
            if d is not None: used[(e, d)] = used.get((e, d), 0) + 1
            rec(p + 1, L2, used)
            if d is not None:
                used[(e, d)] -= 1
                if not used[(e, d)]: del used[(e, d)]
    rec(0, 0, {})
    return out

def count_feasible(De, y, a, D):
    g = groups(De); w = a + 9
    total_str = 0; total_obj = 0; nlow = 0
    for used in enum_low(De, y, a):
        nlow += 1
        s = 1; o = 1
        for e, mult in g.items():
            rem = Counter(mult)
            lowplaced = 0
            for (ee, d), c in used.items():
                if ee == e: rem[d] -= c; lowplaced += c
            rem = Counter({d: c for d, c in rem.items() if c > 0})
            slots = D if e >= w else D - 1
            s *= class_ways(rem, slots)
        total_str += s
    return total_str, nlow

def count_objects(De, y, a, D):
    g = groups(De); w = a + 9; total = 0
    for used in enum_low(De, y, a):
        o = 1
        for e, mult in g.items():
            lowc = Counter()
            for (ee, d), c in used.items():
                if ee == e: lowc[d] = c
            slots_low = 1 if e < w else 0
            n_here = sum(mult.values())
            o *= obj_ways(mult, lowc, D, e < w)
        total += o
    return total

def obj_ways(mult, lowc, D, low_class):
    # number of assignments of digit objects of this class to {low position (if class<w and placed) , copies 1..D-1 or all D, absent}
    vals = sorted(mult.items())
    slots = D - 1 if low_class else D
    @lru_cache(None)
    def ways(i, left):
        if i == len(vals): return 1
        v, m = vals[i]
        lc = lowc.get(v, 0)
        rem_objs = m - lc
        t = 0
        for c in range(0, min(rem_objs, left) + 1):
            t += _choose(left, c) * (factorial(rem_objs) // factorial(rem_objs - c)) * ways(i + 1, left - c)
        return t
    base = 1
    for v, m in vals:
        lc = lowc.get(v, 0)
        base *= factorial(m) // factorial(m - lc)
    return base * ways(0, slots)
