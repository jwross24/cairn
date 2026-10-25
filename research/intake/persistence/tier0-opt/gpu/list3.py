import sys
from collections import Counter
from math import comb
from tier0v2 import multisets
from export_cfg import export
for s in (72,10800,14336):
    tot=0
    for M in sorted(tuple(sorted(M)) for M in multisets(s)):
        p=12
        for d,k in Counter(M).items(): p*=comb(12+k-1,k)
        tot+=p
        print(s,','.join(map(str,M)),p,flush=True)
        export(M,f"/private/tmp/persist-gpu/cfg/{s}_{''.join(map(str,M))}.txt")
    print(s,"TOTAL",tot)
