import sympy, math, sys, time
from sympy import factorint, primitive_root
from sympy.ntheory import discrete_log
x=sympy.Symbol('x')
def cyc10(d): return int(sympy.cyclotomic_poly(d,x).subs(x,10))
def prim(L):
    ps=set()
    for d in sympy.divisors(L):
        for p in factorint(cyc10(d)): ps.add(p)
    return sorted(ps-{2,3,5,7})
def lattice_index(rows,r):
    rows=[list(v) for v in rows]
    idx=1
    for col in range(r):
        while True:
            nz=[v for v in rows if v[col]!=0]
            if len(nz)<=1: break
            nz.sort(key=lambda v:abs(v[col]))
            p=nz[0]
            for v in nz[1:]:
                q=v[col]//p[col]
                for j in range(col,r): v[j]-=q*p[j]
        piv=[v for v in rows if v[col]!=0]
        assert piv
        idx*=abs(piv[0][col])
        rows=[v for v in rows if v is not piv[0]]
    return idx
def order_of_S(L, gens=(2,3,7)):
    ps=prim(L); r=len(ps)
    W=[[0]*r for _ in gens]
    ms=[]
    for i,p in enumerate(ps):
        g=primitive_root(p); m=p-1; ms.append(m)
        for t,a in enumerate(gens):
            W[t][i]=discrete_log(p,a%p,g)%m
    rows=[w[:] for w in W]
    for i,m in enumerate(ms):
        v=[0]*r; v[i]=m; rows.append(v)
    ind=lattice_index(rows,r)
    G=1
    for m in ms: G*=m
    return G, G//ind, ind, r
if __name__=="__main__":
    for L in [int(a) for a in sys.argv[1:]]:
        t=time.time()
        G,H,ind,r=order_of_S(L)
        G2,H2,ind2,_=order_of_S(L,(3,7))
        print(f"L={L} primes={r} log10G={math.log10(G):.3f} |<2,3,7>|=10^{math.log10(H):.3f} index(<2,3,7>)={G//H} |<3,7>|=10^{math.log10(H2):.3f} t={time.time()-t:.1f}s",flush=True)
