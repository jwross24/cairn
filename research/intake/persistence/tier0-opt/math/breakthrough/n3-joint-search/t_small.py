import sys, random, time
sys.dont_write_bytecode = True
import joint
from joint import *

def mk(a,b,c,P,K):
    n,D,fr = leading_digits(a,b,c,P)
    Bt = pow(2,a,10**K)*pow(3,b,10**K)*pow(7,c,10**K)%10**K
    return n,D,Bt

# exact check of solve_system / tail_lattice by brute force on small cases
random.seed(1)
bad=0
for trial in range(200):
    a=random.randrange(0,6); b=random.randrange(0,60); c=random.randrange(0,60); K=random.randrange(a+3,9)
    y=2**a*3**b*7**c; Bt=y%10**K
    r=tail_lattice(a,Bt,K)
    p,U=r
    # (b,c) must lie in p+lattice U
    det=U[0][0]*U[1][1]-U[0][1]*U[1][0]
    dx,dy=b-p[0],c-p[1]
    s=(dx*U[1][1]-dy*U[1][0]); t=(U[0][0]*dy-U[0][1]*dx)
    if s%det or t%det: bad+=1
    # brute force: all (b2,c2) in [0,60)^2 with congruence must be in coset
    for b2 in range(0,40):
        for c2 in range(0,40):
            ok=(2**a*3**b2*7**c2-Bt)%10**K==0
            dx,dy=b2-p[0],c2-p[1]
            s=(dx*U[1][1]-dy*U[1][0]); t=(U[0][0]*dy-U[0][1]*dx)
            inc= s%det==0 and t%det==0
            if ok!=inc: bad+=1
print("tail_lattice brute-force disagreements:",bad)
