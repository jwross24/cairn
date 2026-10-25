#!/usr/bin/env python3
"""
align.py — the 2,5-adic depth a single prime contributes to the compatibility group (X20).

For a prime p ∤ 10, G_p := Z² / (Ker_p + K_N),  Ker_p = {(b,c): 3^b 7^c ≡ 1 (mod p)},  K_N = {(b,c): 3^b 7^c ≡ 1 (mod 10^N)}
(N = 60 ≫ any p's 2,5-part).  |G_p| = 2^α 5^β is the depth p adds against wrap-0 shadows on its own; it is bounded
by the 2,5-parts of |⟨3,7⟩_p| and cut down by the misalignment between the modular and the q-adic logarithms.
Usage: python3 align.py p1 p2 ...   (or --levels L1,L2,...: all PH-feasible primes of those levels)
"""
import sys, time
from sympy import factorint, n_order, isprime
from math import lcm
from lattice import Coset
from descent import cut_coset, v2
import deepcut as DC, deepcut_lift as DL
from witness import lattice_sum

def v(n, q):
    k = 0
    while n % q == 0: n //= q; k += 1
    return k

if __name__ == "__main__":
    N = 60; t0 = time.time()
    KN = cut_coset(Coset((0, 0), (1, 0), (0, 1)), 0, 1, N)
    ps = []
    if '--levels' in sys.argv:
        for L in map(int, sys.argv[sys.argv.index('--levels') + 1].split(',')):
            ps += [(L, p) for p in DL.new_primes(L, 1)]
    else:
        ps = [(n_order(10, int(x)), int(x)) for x in sys.argv[1:] if x.isdigit()]
    tot = Coset((0, 0), (1, 0), (0, 1)); acc = []
    for (L, p) in ps:
        pd = DL.PD(p)
        ker = Coset((0, 0), (1, 0), (0, 1)).intersect(pd.l3, pd.l7, 0, p - 1)
        S = Coset((0, 0), *lattice_sum([ker.u1, ker.u2, KN.u1, KN.u2])); g = S.index()
        H = lcm(n_order(3, p), n_order(7, p))
        tot = tot.intersect(pd.l3, pd.l7, 0, p - 1)
        St = Coset((0, 0), *lattice_sum([tot.u1, tot.u2, KN.u1, KN.u2])); gt = St.index()
        print(f"p={p} (ord10={L}, p-1 2^{v(p-1,2)} 5^{v(p-1,5)}, |<3,7>| 2^{v(H,2)} 5^{v(H,5)}): depth alone 2^{v(g,2)} 5^{v(g,5)}; "
              f"cumulative 2^{v(gt,2)} 5^{v(gt,5)} [{time.time()-t0:.0f}s]", flush=True)
