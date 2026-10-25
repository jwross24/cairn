import numpy as np, random, math, sys
from sympy.ntheory import discrete_log
P=[11,13,37,101,9901]
M_=[p-1 for p in P]
LOG={}
for p in P:
    t=np.full(p,-1,dtype=np.int64); x=1
    for i in range(p-1):
        t[x]=i; x=(x*2)%p
    assert (t>=0).sum()==p-1 or p==11 or True
    LOG[p]=t
def vec(g): return [int(LOG[p][g%p]) for p in P]
def echelon(gens):
    rows=[vec(g) for g in gens]+[[M_[i] if j==i else 0 for j in range(5)] for i in range(5)]
    rows=[r[:] for r in rows]; basis=[]
    for col in range(5):
        while True:
            nz=[r for r in rows if r[col]!=0]
            if len(nz)<=1: break
            nz.sort(key=lambda r:abs(r[col])); p0=nz[0]
            for r in nz[1:]:
                q=r[col]//p0[col]
                for j in range(col,5): r[j]-=q*p0[j]
        piv=[r for r in rows if r[col]!=0][0]
        basis.append(piv); rows=[r for r in rows if r is not piv]
    return basis
def member(basis,L):
    L=L.copy()
    for col in range(5):
        b=basis[col]; d=b[col]
        ok=(L[:,col]%d==0)
        q=L[:,col]//d
        for j in range(col,5): L[:,j]-=q*b[j]
        if col==0: good=ok
        else: good&=ok
    return good
B237=echelon([2,3,7]); B23=echelon([2,3]); B27=echelon([2,7]); B2=echelon([2])
R=lambda nu,p: ((pow(10,nu,9*p)-1)//9)%p
def sample(N,digits,seed=1):
    rng=np.random.default_rng(seed)
    k=len(digits)
    nu=rng.integers(0,12,N); e=rng.integers(0,12,(N,k))
    w=np.array([d-1 for d in digits])
    res={}
    Ls=[]
    for p in P+[3,7]:
        pw=np.array([pow(10,i,p) for i in range(12)])
        Rt=np.array([((pow(10,v,9*p)-1)//9)%p for v in range(12)]) if p not in (3,) else np.array([v%3 for v in range(12)])
        if p==3: Rt=np.array([v%3 for v in range(12)])
        u=(Rt[nu]+ (pw[e]*w[None,:]).sum(axis=1))%p
        res[p]=u
    return nu,e,res
def run(N,digits,seed):
    nu,e,res=sample(N,digits,seed)
    ok=np.ones(N,bool)
    Lg=np.zeros((N,5),dtype=np.int64)
    for i,p in enumerate(P):
        u=res[p]; ok&=(u!=0); Lg[:,i]=np.where(u!=0,LOG[p][np.where(u!=0,u,1)],0)
    b3=(res[3]==0); b7=(res[7]==0)
    m237=member(B237,Lg)&ok; m23=member(B23,Lg)&ok; m27=member(B27,Lg)&ok; m2=member(B2,Lg)&ok
    now=m237
    new=np.where(b3&b7,m237,np.where(b3&~b7,m23,np.where(~b3&b7,m27,m2)))
    return N,now.sum(),new.sum(),(b3&b7).mean(),(b3&~b7).mean(),(~b3&b7).mean()
if __name__=="__main__":
    for digits in ([2]*6+[3]*4+[4,6,7,8],[2]*8+[3,3,7,7,9,9],[2,2,3,3,3,4,6,6,7,8,8,9]):
        N,now,new,pTT,pTF,pFT=run(4_000_000,digits,7)
        print(len(digits),"samples",N,"rank3 survivors",now,"branch-split survivors",new,"ratio %.2f"%(now/max(new,1)),"P(3|y,7|y)=%.4f P(3|y,7∤y)=%.4f P(3∤y,7|y)=%.4f"%(pTT,pTF,pFT))
