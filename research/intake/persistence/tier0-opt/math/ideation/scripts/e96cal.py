import re
from math import comb
exec(open('randmodel.py').read().split("I96=")[0])
H37=10**56.449; G96=10**93.588
H24=10**13.527; G24=10**21.622
print("tier vertex  kmax  E24_nonanch(cal f=1.2e-3)  E96_nonanch(cal, f=1.2e-3..1.2e-2)  anchored~1e-8*N12")
for tier,s,e,n12,kmax,nms in rows:
    if tier=='A': continue
    ms=multisets(e)
    n24=sum(N(M,24) for M in ms); n96=sum(N(M,96) for M in ms); n48=sum(N(M,48) for M in ms)
    e24=n24*H24/G24*1.2e-3
    e96=n96*H37/G96
    print(f"{tier} {s:>16d} k={kmax:2d}  E24={e24:.2e}  E96={e96*1.2e-3:.2e}..{e96*1.2e-2:.2e}  anch~{1e-8*n12:.1e}")
