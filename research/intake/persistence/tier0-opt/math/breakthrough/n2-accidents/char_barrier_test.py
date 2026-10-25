import sys, itertools, json, cmath, math
sys.dont_write_bytecode = True
import numpy as np
from fractions import Fraction
from collections import Counter

PR = [11, 13, 37, 101, 9901]
P = math.prod(PR)
LOG = {}
for p in PR:
    t = np.full(p, -1, dtype=np.int64)
    x = 1
    for k in range(p - 1):
        t[x] = k
        x = x * 2 % p
    assert x == 1 and (t[1:] >= 0).all()
    LOG[p] = t

def values(M):
    c = Counter(M)
    parts = []
    for d, m in c.items():
        s = np.array(sorted({sum(pow(10, e, P) for e in comb) % P * (d - 1) % P
                             for comb in itertools.combinations_with_replacement(range(12), m)}), dtype=np.int64)
        mult = Counter()
        for comb in itertools.combinations_with_replacement(range(12), m):
            mult[sum(pow(10, e, P) for e in comb) % P * (d - 1) % P] += 1
        keys = np.array(list(mult.keys()), dtype=np.int64)
        cnt = np.array(list(mult.values()), dtype=np.int64)
        parts.append((keys, cnt))
    vals = np.array([(10**nu - 1) // 9 % P for nu in range(12)], dtype=np.int64)
    cnts = np.ones(12, dtype=np.int64)
    for keys, cnt in parts:
        vals = ((vals[:, None] + keys[None, :]) % P).ravel()
        cnts = (cnts[:, None] * cnt[None, :]).ravel()
    return vals, cnts

def dual_chars(primes, E=40):
    g = {p: math.gcd(p - 1, E) for p in primes}
    sols = []
    for u in itertools.product(*[range(g[p]) for p in primes]):
        ok = True
        for w in (2, 3, 7):
            tot = Fraction(0)
            for p, up in zip(primes, u):
                lw = int(LOG[p][w % p])
                tot += Fraction(up * lw, g[p])
            if tot.denominator != 1:
                ok = False
                break
        if ok:
            sols.append(u)
    return g, sols

def analyze(M, primes):
    vals, cnts = values(M)
    N = int(cnts.sum())
    unit = np.ones(len(vals), dtype=bool)
    for p in primes:
        unit &= (vals % p) != 0
    g, sols = dual_chars(primes)
    S = []
    lg = {p: np.where(unit, LOG[p][np.where(unit, vals % p, 1)], 0) for p in primes}
    for u in sols:
        ph = np.zeros(len(vals))
        for p, up in zip(primes, u):
            ph += up * lg[p] / g[p]
        z = np.sum(cnts * unit * np.exp(2j * np.pi * ph))
        S.append(z)
    S = np.array(S)
    nu = int((cnts * unit).sum())
    idx = len(sols)
    c_id = S.sum().real / idx
    nontriv = [abs(z) for z, u in zip(S, sols) if any(u)]
    return dict(M=M, N=N, N_units=nu, idx=idx, c_identity=round(c_id, 3), main=nu / idx,
                max_nontriv=float(max(nontriv)), sqrtN=math.sqrt(nu), ratio_max_over_sqrtN=float(max(nontriv)) / math.sqrt(nu),
                parseval_lhs=float((np.abs(S) ** 2).sum()))

if __name__ == "__main__":
    for M, truth in (((2, 2, 2, 2, 8), 4286), ((2, 2, 7, 8, 8), 18202), ((3, 3, 3, 4, 4, 4), 31177), ((3,) * 11, 178735)):
        r = analyze(M, PR)
        print(M, "engine survivors", truth, r)
