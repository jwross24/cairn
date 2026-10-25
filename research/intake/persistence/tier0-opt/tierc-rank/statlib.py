import math
import random


def _betacf(a, b, x):
    qab, qap, qam = a + b, a + 1, a - 1
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < 1e-300:
        d = 1e-300
    d = 1.0 / d
    h = d
    for m in range(1, 400):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = 1e-300 if abs(d) < 1e-300 else d
        c = 1.0 + aa / c
        c = 1e-300 if abs(c) < 1e-300 else c
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = 1e-300 if abs(d) < 1e-300 else d
        c = 1.0 + aa / c
        c = 1e-300 if abs(c) < 1e-300 else c
        d = 1.0 / d
        de = d * c
        h *= de
        if abs(de - 1.0) < 3e-16:
            break
    return h


def betainc(a, b, x):
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    lbt = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1 - x)
    if x < (a + 1) / (a + b + 2):
        return math.exp(lbt) * _betacf(a, b, x) / a
    return 1 - math.exp(lbt) * _betacf(b, a, 1 - x) / b


def betaq(p, a, b):
    lo, hi = 0.0, 1.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if betainc(a, b, mid) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def clopper_pearson(x, n, alpha=0.05):
    lo = 0.0 if x == 0 else betaq(alpha / 2, x, n - x + 1)
    hi = 1.0 if x == n else betaq(1 - alpha / 2, x + 1, n - x)
    return lo, hi


def boot_total(vals, n, pop, reps=4000, seed=1):
    rng = random.Random(seed)
    m = len(vals)
    p = m / n
    out = []
    for _ in range(reps):
        mm = rng.binomialvariate(n, p)
        if mm == 0 or m == 0:
            out.append(0.0)
            continue
        s = 0
        for _ in range(mm):
            s += vals[rng.randrange(m)]
        out.append(s * pop / n)
    out.sort()
    return out[int(0.025 * reps)], out[int(0.975 * reps)], out
