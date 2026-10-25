from math import lgamma, log, log10
def lC(n,k): return (lgamma(n+1)-lgamma(k+1)-lgamma(n-k+1))/log(10)
lmult=(lgamma(45)-lgamma(40)-lgamma(4)-lgamma(3))/log(10)
print("multinomial 44!/(39!3!2!) = 10^%.2f"%lmult)
for R in (2550,1400,1000,504,300):
    print("R=%d  log10 C(R,44)*mult = %.1f ; with pattern residues R/96=%.1f : log10 C(R/96+44,44)=%.1f"%(R,lC(R,44)+lmult,R/96,lC(int(R/96)+44,44)))
def lNL(L,ms=(39,3,2)):
    return log10(L)+sum(lC(L-1+m,m) for m in ms)
for L in (12,24,48,96,128,160,192,256):
    print("L=%d log10 N_L=%.1f  log10 rho_L(0.388L)= -%.1f  log10 mu=%.1f"%(L,lNL(L),0.388*L,lNL(L)-0.388*L))
# 2^q vs distinct-class count: expected classes occupied by 39 twos in 96 classes
import random
