import itertools, time, math, sys
from collections import Counter
from lattice import Coset
from descent import cut_coset, v2
import deepcut as DC, classify_open as C, wordlift as W
keys = {('393216','222222244468','0','330812181'), ('3211264','222222277888','2','1411788'), ('14336','227888','0','78121827'), ('28672','2244788','0','330812181'), ('3211264','2222222247788','0','7411887')}
Lam96 = DC.kernel_lattice(); t0=time.time()
g = math.gcd(math.gcd(abs(Lam96.u1[0]), abs(Lam96.u1[1])), math.gcd(abs(Lam96.u2[0]), abs(Lam96.u2[1])))
v2c = 0; x=g
while x%2==0: x//=2; v2c+=1
v5c=0
while x%5==0: x//=5; v5c+=1
print('content', g, 'v2', v2c, 'v5', v5c, flush=True)
agree=dis=0; stats=Counter()
for (s, M, a, nu, eps, y, sol) in C.entries('/home/claude/night/trees_mac_1250.jsonl'):
    key=(str(s),''.join(map(str,M)),str(a),str(y))
    if key not in keys: continue
    fct=C.factor237(y); co0=Coset((fct[1],fct[2]),Lam96.u1,Lam96.u2)
    reps=DC.all_representations(M,y)
    if nu is not None: reps=[r for r in reps if r[0]==nu and Counter(e for _,e in r[1])==Counter(e%96 for e in eps)]
    mod = 2**(a+v2c+2) * 5**(v5c+1)
    for (nu0,De) in reps:
        V = W.R(nu0)+sum((d-1)*10**e for d,e in De); w=(V-y)//W.R(96)
        surv=set()
        for co,state in W.depth1_words(co0,a,(nu0,De)):
            surv.add(tuple(1 if st[0]=='F' else 0 for st in state))
        pred=set()
        for choice in itertools.product((0,1),repeat=len(De)):
            taken=Counter(e for (d,e),c in zip(De,choice) if c)
            if any(v>1 for v in taken.values()): continue
            SU = sum((d-1)*10**e for (d,e),c in zip(De,choice) if not c)
            L = W.R(96)+sum((d-1)*10**e for (d,e),c in zip(De,choice) if c)
            if v2(L)!=a or L%5==0: continue
            if (10**nu0 + 9*SU + w) % mod == 0: pred.add(choice)
        ok = (surv==pred); agree+=ok; dis+=(not ok); stats[(w, len(surv), len(pred))]+=1
        print(('OK' if ok else 'MISMATCH'), key, 'w',w, 'surv',len(surv),'pred',len(pred), f'[{time.time()-t0:.0f}s]', flush=True)
print('reps agree',agree,'disagree',dis, dict(stats), f'{time.time()-t0:.0f}s')
