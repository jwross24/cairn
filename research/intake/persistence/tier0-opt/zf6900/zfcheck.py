#!/usr/bin/env python3
"""Exact verification of sieve survivors: reads 'a b c' lines, computes 2^a 3^b 7^c exactly,
keeps the zero-free ones, computes their persistence. Prints ZF digits a b c pers."""
import sys
from gmpy2 import mpz

def digit_product(x):
    s = str(x)
    if "0" in s: return mpz(0)
    p = mpz(1)
    for d in "23456789":
        k = s.count(d)
        if k: p *= mpz(int(d)) ** k
    return p

def persistence(x):
    c = 0
    while x >= 10:
        x = digit_product(x); c += 1
    return c

n = 0; zf = 0; maxd = (0, None); maxp = (0, None)
for line in sys.stdin:
    a, b, c = map(int, line.split())
    n += 1
    x = mpz(2) ** a * mpz(3) ** b * mpz(7) ** c
    s = str(x)
    if "0" in s: continue
    zf += 1
    p = persistence(x)
    print("ZF", len(s), a, b, c, p)
    if len(s) > maxd[0]: maxd = (len(s), (a, b, c))
    if p > maxp[0]: maxp = (p, (a, b, c))
print(f"checked {n} survivors: {zf} zero-free; largest {maxd}; max persistence {maxp}", file=sys.stderr)
