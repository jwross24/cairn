#!/usr/bin/env python3
"""Export everything the C level-12 engine needs for one (s, multiset) as a text config."""
import sys, json
from collections import Counter
from tier0v2 import PrimeData, primes_for_level, two_adic_bound, ten_adic_K
from fastlevel import FastLevel
from lattice import Coset

def export(M, path, L=12, kcap=60):
    M = tuple(sorted(M))
    ps = primes_for_level(L, set()); pd = [PrimeData(p, L) for p in ps]
    fl = FastLevel(pd)
    A = two_adic_bound(M)
    cfg = {}
    cfg['L'] = L; cfg['A'] = A; cfg['digits'] = list(M)
    cfg['primes'] = [{'p': p.p, 'l2': p.l2, 'l3': p.l3, 'l7': p.l7, 'pow10': p.pow10, 'R': p.R,
                      'logtable': p.table} for p in pd]
    comps = []
    for (lst, mods, H, Nl), c in zip(fl.comps, fl.crt):
        comps.append({'idx': [i for i, _ in lst], 'mods': list(mods), 'crt': c,
                      'H': [[list(k), list(v)] for k, v in H.items()]})
    cfg['comps'] = comps; cfg['N'] = fl.N
    cfg['g'] = fl.g; cfg['u'] = list(fl.u); cfg['U2'] = [list(fl.U2[0]), list(fl.U2[1])]
    # K per a (the 2-D lattice is fixed at this level)
    cfg['K'] = [ten_adic_K(Coset((0, 0), fl.U2[0], fl.U2[1]), kcap, a) for a in range(A + 1)]
    json.dump(cfg, open(path + '.json', 'w'))
    with open(path, 'w') as f:
        w = lambda *xs: f.write(' '.join(str(x) for x in xs) + '\n')
        w(L, A, len(M)); w(*M)
        w(len(pd))
        for p in pd:
            w(p.p, p.l2, p.l3, p.l7); w(*p.pow10); w(*p.R); w(*p.table)
        w(len(fl.comps))
        for (lst, mods, H, Nl), c in zip(fl.comps, fl.crt):
            w(len(lst)); w(*[i for i, _ in lst]); w(*mods); w(c, len(H))
            for k, v in H.items(): w(*k, *v)
        w(fl.N, fl.g, *fl.u); w(*fl.U2[0], *fl.U2[1])
        w(*cfg['K'])
    return cfg

if __name__ == "__main__":
    M = tuple(int(x) for x in sys.argv[1].split(','))
    cfg = export(M, sys.argv[2])
    print("A=", cfg['A'], "g=", cfg['g'], "K per a:", cfg['K'], "N=", cfg['N'])
