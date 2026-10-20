import json, sys, multiprocessing as mp, time
from collections import defaultdict
from tier0v2 import solve_equation, multisets
rows=[l.split() for l in open('/tmp/s4000_zf.txt') if l.startswith('ZF')]
from gmpy2 import mpz
def dp(x):
    p=1
    for ch in str(x): p*=int(ch)
    return p
S=[int(mpz(2)**int(a)*mpz(3)**int(b)*mpz(7)**int(c)) for _,d,a,b,c,p in rows]
kids=defaultdict(list)
for y in S:
    if y>=10: kids[dp(y)].append(y)
def orbit_end(x):
    while x>=10: x=dp(x)
    return x
QMAX=int(sys.argv[1]) if len(sys.argv)>1 else 6
verts=[]
for y in S:
    e=orbit_end(y)
    if e in (2,4,6,8):
        a=b=c=0; t=y
        while t%2==0: t//=2; a+=1
        while t%3==0: t//=3; b+=1
        while t%7==0: t//=7; c+=1
        if a+b+c<=QMAX: verts.append((e,y))
verts += [(d,d) for d in (2,4,6,8)]
verts=sorted(set(verts), key=lambda t:(t[1]))
import math
from tier0v2 import ten_adic_K, factor237
LOG3=math.log10(3)
def open_bound(a, D, nu, eps, co, L):
    """digits lower bound for any solution in this pattern other than the one exceptional coset point."""
    u=co.u1; norm=math.hypot(u[0],u[1])
    digits=int(norm/(2*math.sqrt(2))*LOG3)
    # exceptional point: the coset point nearest the origin ~ v0 reduced; check v0 itself
    # nearest coset point to the origin (Babai rounding on the reduced basis)
    u1,u2=co.u1,co.u2; v0=co.v0
    det=u1[0]*u2[1]-u1[1]*u2[0]
    x=(-v0[0]*u2[1]+v0[1]*u2[0])/det; yy=(v0[0]*u1[1]-v0[1]*u1[0])/det
    x=round(x); yy=round(yy)
    b0=v0[0]+x*u1[0]+yy*u2[0]; c0=v0[1]+x*u1[1]+yy*u2[1]; exc=None
    if b0>=0 and c0>=0 and max(b0,c0)<norm/2:
        y=2**a*3**b0*7**c0
        sY=str(y); from collections import Counter
        ok='0' not in sY and Counter(ch for ch in sY if ch!='1')==Counter(str(d) for d in D) and len(sY)%L==nu%L
        exc=(y if y<10**60 else f"~10^{len(sY)-1}", bool(ok))
    return digits, exc
def work(ev):
    e,s=ev; t0=time.time()
    out=[]; bounds=[]; excs=[]
    for M in multisets(s):
        r=solve_equation(s, tuple(sorted(M)), kids[s], verbose=False)
        for (a,nu,eps,co) in r['open']:
            dg,exc=open_bound(a,tuple(sorted(M)),nu,eps,co,r['levels'][-1][0])
            bounds.append(dg); excs.append((M,a,nu,eps,exc))
        out.append((M, len(r['open']), sorted(y for y in r['solutions'] if y>=10),
                    [(L,n_in,n_surv,cls) for (L,ps,n_in,n_surv,cls,el) in r['levels']]))
    found=set().union(*(set(o[2]) for o in out)) if out else set()
    nopen=sum(o[1] for o in out)
    exc_sols={ex[4][0] for ex in excs if ex[4] and ex[4][1] and isinstance(ex[4][0],int)}
    found|=exc_sols
    return dict(target=e, s=s, known=sorted(kids[s]), found=sorted(found), open=nopen,
                closed=(nopen==0 and found==set(kids[s])), digit_bound=(min(bounds) if bounds else None),
                complete_below=(found==set(kids[s]) and all(not ex[4] or ex[4][1]==False or (isinstance(ex[4][0],int) and ex[4][0] in kids[s]) for ex in excs)), exceptional=[(ex[0],ex[1],ex[2],ex[3],ex[4]) for ex in excs],
                secs=round(time.time()-t0), eqs=out)
if __name__=="__main__":
    print(f"{len(verts)} vertices", file=sys.stderr, flush=True)
    with mp.Pool(2) as pool:
        for res in pool.imap_unordered(work, verts):
            print(json.dumps(res), flush=True)
            st='CLOSED' if res['closed'] else (f"CLOSED BELOW 10^{res['digit_bound']:.2e} DIGITS" if res['complete_below'] else 'INCOMPLETE')
            print(f"A_{res['target']} s={res['s']} {st}; open patterns {res['open']}; children={res['found']} known={res['known']} {res['secs']}s", file=sys.stderr, flush=True)
