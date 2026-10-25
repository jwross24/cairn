import re

SRC = "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/cport-shadow/logs/utable_u2_k29.log"
_T = {}
for ln in open(SRC):
    m = re.match(r"k=(\d+) a=(\d+) m=\d+ log10U''=([\d.]+)", ln)
    if m:
        _T[(int(m.group(1)), int(m.group(2)))] = float(m.group(3))
_T[(31, 0)] = 246.0183
AMAX = max(a for (_, a) in _T)


def u2(k, a):
    a = min(a, AMAX)
    if (k, a) in _T:
        return _T[(k, a)]
    base = [kk for (kk, aa) in _T if aa == a and kk <= 29]
    if not base:
        return None
    k2 = max(base)
    k1 = k2 - 5
    while (k1, a) not in _T:
        k1 -= 1
    slope = (_T[(k2, a)] - _T[(k1, a)]) / (k2 - k1)
    return _T[(k2, a)] + slope * (k - k2)


def depth_for(k, a):
    x = u2(k, a)
    d = 1
    while 24 + 48 * d <= x:
        d += 1
    return d, x


def exact_e(d, a):
    for e in range(1, d + 1):
        if 2 * 96 * e - a >= 96 * d:
            return e
    return d
