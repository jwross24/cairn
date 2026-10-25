import sys
sys.dont_write_bytecode = True
sys.path.insert(0, '/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierc-family')
from famlib import *

COND = {96: (9, 5), 192: (9, 5), 384: (13, 5), 480: (10, 5)}
LEVELS = (96, 192, 384, 480)


def modulus(a, L, cond=COND):
    c2, c5 = cond[L]
    return (1 << (a + c2)) * 5 ** c5


def alive_from_W(a, y, W, L, cond=COND):
    return (W - y) % modulus(a, L, cond) == 0


def groups_of(De):
    g = {}
    for d, e in De:
        g.setdefault(e, []).append((d - 1) * 10 ** e)
    return g


def subset_sums(groups):
    sums = [0]
    for e in sorted(groups):
        opts = [0] + groups[e]
        sums = [s + o for s in sums for o in opts]
    return sums


def family_counts(a, y, De, cond=COND, compress=True):
    qmax = a + max(c[0] for c in cond.values())
    g = groups_of(De)
    mult = 1
    if compress:
        low = {e: v for e, v in g.items() if e < qmax}
        for e, v in g.items():
            if e >= qmax:
                mult *= len(v) + 1
    else:
        low = g
    sums = subset_sums(low)
    base = R(96) - y
    mods = {L: modulus(a, L, cond) for L in cond}
    res = {L: 0 for L in cond}
    for s in sums:
        z = base + s
        if z % mods[96] == 0:
            for L in cond:
                if L != 96 and z % mods[L] == 0:
                    res[L] += 1
            res[96] += 1
    return {L: n * mult for L, n in res.items()}, len(sums), mult


def ref_alive(a, y, W, L, lam):
    co = window_coset(a, W, L)
    if co is None:
        return False
    f = factor237(y)
    S = lam[L].plus(co.lat)
    return S.contains(co.v[0] - f[1], co.v[1] - f[2])
