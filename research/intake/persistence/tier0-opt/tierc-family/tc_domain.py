import sys
sys.dont_write_bytecode = True
sys.path.insert(0, '/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierc-family')
import math, time, json
from functools import lru_cache
from famlib import R, DATA

VERTICES = [3416267673274176, 128421199872, 913217421312, 727326941773824, 112717121716224, 1438916737499136]


def exps237(s):
    e = []
    for p in (2, 3, 7):
        c = 0
        while s % p == 0:
            s //= p
            c += 1
        e.append(c)
    assert s == 1
    return e


def multisets(al, be, ga):
    digs = {2: (1, 0, 0), 3: (0, 1, 0), 4: (2, 0, 0), 6: (1, 1, 0), 7: (0, 0, 1), 8: (3, 0, 0), 9: (0, 2, 0)}
    order = [9, 8, 7, 6, 4, 3, 2]

    @lru_cache(maxsize=None)
    def rec(i, a, b, c):
        if i == len(order):
            return [()] if (a, b, c) == (0, 0, 0) else []
        d = order[i]
        x, y, z = digs[d]
        out = []
        n = 0
        while n * x <= a and n * y <= b and n * z <= c:
            for rest in rec(i + 1, a - n * x, b - n * y, c - n * z):
                out.append(rest + (d,) * n)
            n += 1
        return out

    return rec(0, al, be, ga)


def digit_sum(z):
    return sum(map(int, str(z)))


def sigma_bound(y, mmax):
    s = str(y)
    n = len(s)
    best = None
    pre = 0
    for nu in range(min(n, 96), -1, -1):
        top = y // 10 ** nu
        if digit_sum(top) - 1 > mmax and nu < n - 1:
            break
        z = y - R(nu)
        if z < 0:
            continue
        ds = digit_sum(z)
        if best is None or ds < best[0]:
            best = (ds, nu)
    return best


if __name__ == '__main__':
    t0 = time.time()
    mm = {}
    mset_counts = {}
    for s in VERTICES:
        al, be, ga = exps237(s)
        ms = multisets(al, be, ga)
        mm[s] = (max(sum(d - 1 for d in m) for m in ms), min(sum(d - 1 for d in m) for m in ms), max(len(m) for m in ms))
        mset_counts[s] = len(ms)
    print('vertex: (max m, min m, max k), multisets', {s: (mm[s], mset_counts[s]) for s in VERTICES}, flush=True)
    mmax = max(v[0] for v in mm.values())
    lim = 10 ** 97
    l2, l3, l7 = math.log(2), math.log(3), math.log(7)
    top = math.log(lim)
    n_tr = 0
    n_pass = 0
    best = []
    a = 0
    while a * l2 < top:
        b = 0
        while a * l2 + b * l3 < top:
            c = 0
            while a * l2 + b * l3 + c * l7 < top:
                y = 2 ** a * 3 ** b * 7 ** c
                if y < lim:
                    n_tr += 1
                    r = sigma_bound(y, mmax)
                    if r is not None:
                        best.append((r[0], r[1], a, b, c))
                        if r[0] <= mmax:
                            n_pass += 1
                c += 1
            b += 1
        a += 1
        if a % 20 == 0:
            best.sort()
            best = best[:20]
            print('a', a, 'triples', n_tr, 'pass', n_pass, 'min sigma so far', best[:3], round(time.time() - t0), flush=True)
    best.sort()
    print('TOTAL triples', n_tr, 'with sigma <= mmax', n_pass, 'mmax', mmax)
    print('smallest sigma', best[:10])
    print('seconds', round(time.time() - t0, 1))
