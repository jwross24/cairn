import sys
sys.path.insert(0,'.')
from export_level import level_chain
from math import gcd
for M in [(2,2,4,4,4,7,8),(3,3,5,6,9),(2,2,2,2,2,2,2,2,2,2,2,7)]:
    ch=level_chain(M,96)
    for L in (24,48,96):
        fg=ch[L][1]
        print(M,L,'nlin',len(fg.linear),[(i,m,g1,g2,gcd(gcd(g1,g2),m)) for (i,m,g1,g2,Nl) in fg.linear])
