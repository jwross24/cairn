#!/usr/bin/env python3
"""Independent checks on tier0's verdicts.

1. Brute force: every y = R_n + sum (d_j-1)10^{e_j} with n <= NMAX, for each arrangement D of each
   multiset of s. Truth set T = those y in S (2^a 3^b 7^c), y >= 10.  tier0's SOLUTION set must equal T
   (restricted to n <= NMAX) and tier0 must never classify as DEAD a residue pattern that T occupies.
2. Planted negative: a fake "known child" that is not in S must trip the positive-control assertion.
"""
import sys, itertools
from tier0 import solve_equation, multisets, arrangements, factor237, two_adic_bound
from collections import Counter

def brute(D, nmax):
    q = len(D); out = []
    for n in range(q, nmax + 1):
        R = (10 ** n - 1) // 9
        for es in itertools.combinations(range(n), q):
            es = es[::-1]  # e_1 > ... > e_q
            y = R + sum((d - 1) * 10 ** e for d, e in zip(D, es))
            if y >= 10 and factor237(y) is not None:
                out.append((y, n, es))
    return out

def main(s, nmax=30):
    allok = True
    for M in multisets(s):
        A = two_adic_bound(M)
        for D in arrangements(M):
            T = brute(D, nmax)
            # 2-adic bound must hold on the truth set
            for y, n, es in T:
                a = factor237(y)[0]
                assert a <= A, f"2-adic bound violated: y={y} a={a} A={A}"
            r = solve_equation(s, D, [t[0] for t in T], verbose=False, time_budget=600)
            found = {y for y in r['solutions'] if y >= 10}
            truth = {t[0] for t in T}
            ok = truth <= found
            # every truth element must not be in a DEAD pattern: solve_equation asserts this via
            # positive controls (would have raised). Also check that found ⊆ S with product s:
            for y in found:
                st = str(y); p = 1
                for ch in st: p *= int(ch)
                assert p == s and factor237(y) is not None, f"bogus solution {y}"
            status = 'CLOSED' if r['closed'] else f"OPEN({len(r['open'])})"
            print(f"s={s} D={D} A={A} brute(n<={nmax})={sorted(truth)} tier0={sorted(found)} {status} "
                  f"{'OK' if ok else 'MISMATCH'}", flush=True)
            allok &= ok
    # planted negative: claim a non-member is a child
    D = arrangements(multisets(s)[0])[0]
    fake = int(''.join(str(d) for d in D) + '1' * 3)
    if factor237(fake) is None:
        try:
            solve_equation(s, D, [fake], verbose=False)
            print("PLANTED NEGATIVE NOT CAUGHT", fake); allok = False
        except AssertionError as e:
            print(f"planted negative {fake} caught: {type(e).__name__}")
    print("ALL OK" if allok else "PROBLEMS")

if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]) if len(sys.argv) > 2 else 30)
