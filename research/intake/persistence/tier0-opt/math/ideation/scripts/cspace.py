import re
from math import comb, log10
exec(open('randmodel.py').read().split("I96=")[0])
allW=set()
print("tier s  sumN12  #W  Wmin..Wmax  #(nu,c) upper  gain  | cum-universal")
tot_c=0
rowsX=[]
for tier,s,e,n12,kmax,nms in rows:
    if tier=='A': continue
    ms=multisets(e)
    n12c=sum(N(M,12) for M in ms)
    Ws=set(sum((d-1)*m for d,m in M.items()) for M in ms)
    allW|=Ws
    nc=12*sum(comb(W+11,11) for W in Ws)
    nc_cont=12*sum(comb(W+11,11) for W in range(min(Ws),max(Ws)+1))
    rowsX.append((tier,s,n12c,len(Ws),min(Ws),max(Ws),nc,n12c/nc))
    print(f"{tier} {s:>16d} {n12c:.2e} #W={len(Ws):3d} {min(Ws)}..{max(Ws)}  #c={nc:.2e} gain={n12c/nc:.1e}")
u=12*sum(comb(W+11,11) for W in allW)
print("universal over B,C: #W",len(allW),min(allW),max(allW),"#(nu,c)=%.3e"%u, "sum N12 over B,C = %.3e"%sum(r[2] for r in rowsX))
uB=12*sum(comb(W+11,11) for W in set().union(*[set(sum((d-1)*m for d,m in M.items()) for M in multisets(e)) for t,s,e,n,k,nm in rows if t=='B']))
print("tier B universal #c=%.3e vs sum N12_B=%.3e"%(uB,sum(r[2] for r in rowsX if r[0]=='B')))
