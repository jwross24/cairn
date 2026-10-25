import sys, json
from math import prod
s=int(sys.argv[1]); LIM=10**200
known=[]; a2=1
while a2<LIM:
    b3=a2
    while b3<LIM:
        y=b3
        while y<LIM:
            t=str(y)
            if y>=10 and '0' not in t and prod(int(ch) for ch in t if ch!='1')==s: known.append(y)
            y*=7
        b3*=3
    a2*=2
known.sort(); print(','.join(map(str,known)))
