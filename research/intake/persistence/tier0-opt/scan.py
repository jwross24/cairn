import sys
from collections import Counter
from math import comb
from gmpy2 import mpz
from tier0v2 import multisets
def npat(M):
    p = 12
    for d, k in Counter(M).items(): p *= comb(12 + k - 1, k)
    return p
def dp(x):
    p = 1
    for ch in str(x): p *= int(ch)
    return p
rows=[l.split() for l in open('zf_below_1e4000.txt') if l.startswith('ZF')]
S=[int(mpz(2)**int(a)*mpz(3)**int(b)*mpz(7)**int(c)) for _,d,a,b,c,p in rows]
def end(x):
    while x>=10: x=dp(x)
    return x
for y in sorted(S):
    if y<10 or end(y) not in (2,4,6,8) or y>1e9: continue
    for M in multisets(y):
        M=tuple(sorted(M)); n=npat(M)
        if 1e6<=n<=3e7: print(y, n, ','.join(map(str,M)))
