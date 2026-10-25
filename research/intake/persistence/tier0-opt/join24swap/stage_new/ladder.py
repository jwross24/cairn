#!/usr/bin/env python3
"""
ladder.py — the kill-ladder profile of a base: for each level L, the primes of b^L - 1 outside the
digit primes and the fraction of residue vectors that are images of S-units.

For a level L with primes p_1..p_m (p_i ∤ b, p_i not a digit prime), a residue pattern survives the
level iff (y mod p_i)_i lies in the image of the digit primes' exponent vectors, a subgroup
H ⊂ ∏ (Z/p_i)^*.  Survival fraction (random-pattern model) = |H| / ∏ (p_i - 1).  |H| = |Z^k / ker|
= |det(kernel lattice)|, computed exactly from the congruences (no enumeration).

The free-prime image H_free (bounded primes fixed) gives the second column: it is the group the
engine's lattice coset lives in; the bounded exponents contribute at most (#admissible tuples)
extra patterns, so survival ≤ |H_free| · T / ∏ (p_i - 1).

Usage: python3 ladder.py <b> [levels...]   (default levels 4..48)
"""
import sys
from math import gcd
from sympy import factorint
from engine_b import Base, primes_for_level, PrimeData
from lattice3 import CosetK, _lll

def det_int(B):
    """|det| of a square integer matrix (Bareiss)."""
    n = len(B); M = [list(r) for r in B]; sign = 1; prev = 1
    for k in range(n - 1):
        if M[k][k] == 0:
            sw = next((i for i in range(k + 1, n) if M[i][k] != 0), None)
            if sw is None: return 0
            M[k], M[sw] = M[sw], M[k]; sign = -sign
        for i in range(k + 1, n):
            for j in range(k + 1, n):
                M[i][j] = (M[i][j] * M[k][k] - M[i][k] * M[k][j]) // prev
        prev = M[k][k]
    return abs(M[n - 1][n - 1])

def image_size(pdatas, idx):
    """|image of Z^{len(idx)}| where generator j has log pdatas[i].logs[idx[j]] mod p_i - 1."""
    k = len(idx)
    ck = CosetK.full(k)
    for pd in pdatas:
        ck = ck.intersect_congruence([pd.logs[j] for j in idx], 0, pd.p - 1)
    return det_int(ck.U)

def profile(b, levels):
    base = Base(b)
    rows = []
    for L in levels:
        ps = primes_for_level(base, L, set())
        if not ps: rows.append((L, [], 1, 1.0, 1.0)); continue
        pds = [PrimeData(base, p, L) for p in ps]
        full = 1
        for p in ps: full *= p - 1
        h_all = image_size(pds, list(range(base.k)))
        free_idx = [base.dp.index(p) for p in base.free]
        h_free = image_size(pds, free_idx) if free_idx else 1
        rows.append((L, ps, full, h_all / full, h_free / full))
    return base, rows

if __name__ == "__main__":
    b = int(sys.argv[1])
    levels = [int(x) for x in sys.argv[2:]] or list(range(4, 49))
    base, rows = profile(b, levels)
    print(f"base {b}: digit primes {base.dp}, bounded {base.bounded}, free {base.free}")
    print(f"{'L':>3} {'primes of b^L-1 outside digit primes':<48} {'surv(all S-units)':>18} {'surv(free, 1 bounded tuple)':>28}")
    for L, ps, full, fa, ff in rows:
        ptxt = ' '.join(str(p) for p in ps)
        if len(ptxt) > 46: ptxt = ptxt[:43] + '...'
        print(f"{L:>3} {ptxt:<48} {fa:>18.3e} {ff:>28.3e}")
