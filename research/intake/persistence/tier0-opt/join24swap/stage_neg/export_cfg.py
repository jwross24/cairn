#!/usr/bin/env python3
"""Export everything the C level-12 engine needs for one (s, multiset) as a text config."""
import io, sys, json
from collections import Counter
from tier0v2 import PrimeData, primes_for_level, two_adic_bound, ten_adic_K, chain_step
from fastlevel import FastLevel
from lattice import Coset

_STATIC = {}
_KCACHE = {}

def _static(L):
    """what a level-L config holds that does not depend on the multiset (cached for the level-12 chain)"""
    st = _STATIC.get(L)
    if st is not None:
        return st
    if L == 12:
        step = chain_step((12, 24, 48, 96), 0)
        pd, fl = step['pdata'], step['fl']
    else:
        ps = primes_for_level(L, set()); pd = [PrimeData(p, L) for p in ps]
        fl = FastLevel(pd)
    primes = [{'p': p.p, 'l2': p.l2, 'l3': p.l3, 'l7': p.l7, 'pow10': p.pow10, 'R': p.R,
               'logtable': p.table} for p in pd]
    comps = []
    for (lst, mods, H, Nl), c in zip(fl.comps, fl.crt):
        comps.append({'idx': [i for i, _ in lst], 'mods': list(mods), 'crt': c,
                      'H': [[list(k), list(v)] for k, v in H.items()]})
    buf = io.StringIO()
    w = lambda *xs: buf.write(' '.join(str(x) for x in xs) + '\n')
    w(len(pd))
    for p in pd:
        w(p.p, p.l2, p.l3, p.l7); w(*p.pow10); w(*p.R); w(*p.table)
    w(len(fl.comps))
    for (lst, mods, H, Nl), c in zip(fl.comps, fl.crt):
        w(len(lst)); w(*[i for i, _ in lst]); w(*mods); w(c, len(H))
        for k, v in H.items(): w(*k, *v)
    w(fl.N, fl.g, *fl.u); w(*fl.U2[0], *fl.U2[1])
    u = list(fl.u); U2 = [list(fl.U2[0]), list(fl.U2[1])]
    tail_json = ', '.join(['"primes": ' + json.dumps(primes), '"comps": ' + json.dumps(comps), '"N": ' + json.dumps(fl.N),
                           '"g": ' + json.dumps(fl.g), '"u": ' + json.dumps(u), '"U2": ' + json.dumps(U2)])
    st = dict(pd=pd, fl=fl, primes=primes, comps=comps, u=u, U2=U2, text=buf.getvalue(), tail_json=tail_json)
    if L == 12:
        _STATIC[L] = st
    return st

def export(M, path, L=12, kcap=60):
    M = tuple(sorted(M))
    st = _static(L)
    pd, fl = st['pd'], st['fl']
    A = two_adic_bound(M)
    cfg = {}
    cfg['L'] = L; cfg['A'] = A; cfg['digits'] = list(M)
    cfg['primes'] = st['primes']
    cfg['comps'] = st['comps']; cfg['N'] = fl.N
    cfg['g'] = fl.g; cfg['u'] = list(st['u']); cfg['U2'] = [list(st['U2'][0]), list(st['U2'][1])]
    K = []
    for a in range(A + 1):
        key = (L, a, kcap)
        if key not in _KCACHE:
            _KCACHE[key] = ten_adic_K(Coset((0, 0), fl.U2[0], fl.U2[1]), kcap, a)
        K.append(_KCACHE[key])
    cfg['K'] = K
    with open(path + '.json', 'w') as jf:
        jf.write('{' + ', '.join(['"L": ' + json.dumps(L), '"A": ' + json.dumps(A), '"digits": ' + json.dumps(cfg['digits'])]) + ', ' + st['tail_json'] + ', "K": ' + json.dumps(K) + '}')
    with open(path, 'w') as f:
        w = lambda *xs: f.write(' '.join(str(x) for x in xs) + '\n')
        w(L, A, len(M)); w(*M)
        f.write(st['text'])
        w(*cfg['K'])
    return cfg

if __name__ == "__main__":
    M = tuple(int(x) for x in sys.argv[1].split(','))
    cfg = export(M, sys.argv[2])
    print("A=", cfg['A'], "g=", cfg['g'], "K per a:", cfg['K'], "N=", cfg['N'])
