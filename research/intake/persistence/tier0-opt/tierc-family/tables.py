import sys
sys.dont_write_bytecode = True
sys.path.insert(0, '/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierc-family')
import time, json
from famlib import *


def conductor(lam, L):
    S = lam.plus(klat(L, L))
    G = S.index()
    c5 = next(c for c in range(1, L + 1) if lam.plus(klat(L, c)).index() == G)
    c2 = next(c for c in range(2, L + 1) if lam.plus(klat(c, L)).index() == G)
    assert lam.plus(klat(c2, c5)).index() == G
    return G, c2, c5


def subgroup(lam, m):
    gens = []
    for (x, y) in lam.rows():
        gens.append(pow(3, x, m) * pow(7, y, m) % m)
    seen = {1}
    frontier = [1]
    while frontier:
        nxt = []
        for h in frontier:
            for g in gens:
                z = h * g % m
                if z not in seen:
                    seen.add(z)
                    nxt.append(z)
        frontier = nxt
    return seen


def build_tables(levels=(96, 192, 384, 480)):
    lam = build_lambdas()
    tabs = {}
    for L in levels:
        G, c2, c5 = conductor(lam[L], L)
        m = (1 << c2) * 5 ** c5
        T = subgroup(lam[L], m)
        tabs[L] = dict(G=G, c2=c2, c5=c5, m=m, T=T)
    return lam, tabs


if __name__ == '__main__':
    t0 = time.time()
    lam, tabs = build_tables()
    for L, t in tabs.items():
        g = t['G']
        print(f"L={L} |G|=2^{v2(g)}*5^{round(math.log(g / 2 ** v2(g), 5))} conductor 2^{t['c2']}*5^{t['c5']} = {t['m']}  |T|={len(t['T'])}  |(Z/m)*|={(1 << (t['c2'] - 1)) * 4 * 5 ** (t['c5'] - 1)}  ratio={((1 << (t['c2'] - 1)) * 4 * 5 ** (t['c5'] - 1)) / len(t['T']):.1f}", flush=True)
    print('seconds', round(time.time() - t0, 1))
