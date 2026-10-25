import math, time, sys
from math import lcm
from collections import defaultdict
from sympy import n_order
from lattice import Coset
import deepcut as DC, deepcut_lift as DL, classify_open as C, wordlift as W
t0=time.time()
Lam96=DC.kernel_lattice()
P192=[p for p in DL.new_primes(192,96) if p<10**12]; P384=[p for p in DL.new_primes(384,192) if p<10**12]; P480=[p for p in DL.new_primes(480,96) if p<10**12]
pds192=[DL.PD(p) for p in P192]; pds384=[DL.PD(p) for p in P384]; pds480=[DL.PD(p) for p in P480]
def order(co,p):
    g1=pow(3,co.u1[0],p)*pow(7,co.u1[1],p)%p; g2=pow(3,co.u2[0],p)*pow(7,co.u2[1],p)%p
    return lcm(n_order(g1,p) if g1!=1 else 1, n_order(g2,p) if g2!=1 else 1)
want=set(tuple(l.split()[:4]) for l in open('/tmp/surv43.txt'))
obs=defaultdict(lambda:[0,0]); pred=defaultdict(list); nw=0; seen=set()
for (s,M,a,nu,eps,y,sol) in C.entries('/home/claude/night/trees_mac_1250.jsonl'):
    key=(str(s),''.join(map(str,M)),str(a),str(y))
    if key not in want or key in seen: continue
    seen.add(key)
    fct=C.factor237(y); co0=Coset((fct[1],fct[2]),Lam96.u1,Lam96.u2)
    r1=C.exact_identity(M,y); reps=[(r1[0],tuple(zip(sorted(M,reverse=True),r1[1])))] if r1 else DC.all_representations(M,y)
    for (nu0,De) in reps:
        for co,state in W.depth1_words(co0,a,(nu0,De)):
            nw+=1
            V=W.R(nu0)+sum((d-1)*10**e for d,e in De)
            co1=DL.child_coset(co,a,V,pds192)
            if co1 is None: print("shadow failed 192?!", s, M, y); continue
            for tag,pds,base in (('384',pds384,co1),('480',pds480,co)):
                for pd in pds:
                    p=pd.p; o_sh=order(base,p); o_96=order(Lam96,p)
                    pred[(tag,p)].append(o_sh/o_96)
                    passed = DL.child_coset(base,a,V,[pd]) is not None
                    obs[(tag,p)][0]+=passed; obs[(tag,p)][1]+=1
    print(f"  {s} done [{time.time()-t0:.0f}s]", flush=True)
print(f"{nw} words; per prime: observed shadow pass rate vs predicted |im Λ'|/|im Λ_96|")
for key in sorted(obs, key=lambda k:(k[0],k[1])):
    tag,p=key; ok,n=obs[key]; pr=sum(pred[key])/len(pred[key])
    print(f"  level {tag} p={p:<14} observed {ok:>3}/{n} = {ok/n:5.2f}   predicted {pr:5.3f}   {'AUTO' if pr==1 else ''}")
