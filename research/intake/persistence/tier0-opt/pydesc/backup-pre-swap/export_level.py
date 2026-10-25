#!/usr/bin/env python3
"""Export the config for a C lift pass from level L_old to L_new (flat text)."""
import sys, json
import sympy
from sympy import primitive_root
from tier0v2 import PrimeData, primes_for_level, two_adic_bound, ten_adic_K
from fastlevel import FastLevel, FastLevelGen
from lattice import Coset

LEVELS = (12, 24, 48, 96)

def level_chain(M, upto):
    """FastLevel at 12 and FastLevelGen for each later level up to `upto`; returns dict L -> (pdata, obj, U)."""
    chain = {}
    used = set()
    U = None
    for L in LEVELS:
        if L > upto: break
        ps = primes_for_level(L, used); pd = [PrimeData(p, L) for p in ps]; used.update(ps)
        if L == 12:
            fl = FastLevel(pd); U = fl.U2; chain[L] = (pd, fl, U)
        else:
            fg = FastLevelGen(pd, U); U = fg.U_new; chain[L] = (pd, fg, U)
    return chain

def export(M, L_new, path, kcap=60):
    M = tuple(sorted(M)); A = two_adic_bound(M)
    chain = level_chain(M, L_new)
    L_old = LEVELS[LEVELS.index(L_new) - 1]
    pd, fg, U_new = chain[L_new]; U_old = chain[L_old][2]
    K = [ten_adic_K(Coset((0, 0), U_new[0], U_new[1]), kcap, a) for a in range(A + 1)]
    with open(path, 'w') as f:
        w = lambda *xs: f.write(' '.join(str(x) for x in xs) + '\n')
        w(L_old, L_new, A, len(M)); w(*M)
        w(len(pd))
        for p in pd:
            fac = sympy.factorint(p.p - 1)
            w(p.p, p.l2, p.l3, p.l7, p.g, len(fac)); w(*[x for q, e in fac.items() for x in (q, e)])
            w(*p.pow10); w(*p.R)
            if p.table is not None: w(1); w(*p.table)
            else: w(0)
        w(len(fg.comps))
        for (lst, mods, H, Nl), c in zip(fg.comps, fg.crt):
            w(len(lst)); w(*[i for i, _ in lst]); w(*mods); w(c, len(H))
            for k, v in H.items(): w(*k, *v)
        w(fg.N)
        w(len(fg.linear))
        for (i, m, g1, g2, Nl), c in zip(fg.linear, fg.crt_lin): w(i, m, g1, g2, c)
        w(*U_old[0], *U_old[1]); w(*U_new[0], *U_new[1])
        w(*K)
    return dict(A=A, K=K, N=fg.N, U_old=U_old, U_new=U_new, primes=[p.p for p in pd])

if __name__ == "__main__":
    M = tuple(int(x) for x in sys.argv[1].split(',')); L_new = int(sys.argv[2])
    info = export(M, L_new, sys.argv[3])
    print(info)
