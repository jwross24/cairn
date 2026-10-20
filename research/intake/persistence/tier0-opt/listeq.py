import sys
from collections import Counter
from math import comb
from tier0v2 import multisets
def npat(M):
    p = 12
    for d, k in Counter(M).items(): p *= comb(12 + k - 1, k)
    return p
s = int(sys.argv[1])
eqs = sorted((tuple(sorted(M)) for M in multisets(s)), key=npat)
for M in eqs: print(npat(M), ','.join(map(str, M)))
