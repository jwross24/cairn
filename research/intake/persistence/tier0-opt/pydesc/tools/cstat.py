import sys, os, pickle
sys.path.insert(0,'/private/tmp/persist-pydesc/prod'); sys.path.insert(1,'/private/tmp/persist-pydesc/work')
from collections import Counter, defaultdict
from lattice import Coset
import pydesc
cnt=Counter(); nsol=0
for pk in sys.argv[1:]:
    rec=pickle.load(open(pk,'rb')); groups=defaultdict(list)
    for r in rec: groups[(r[6],r[7],r[8])].append(r)
    for (D,L,kcap),rs in groups.items():
        surv=[(a,nu,eps,Coset(v0,u1,u2)) for (a,nu,eps,v0,u1,u2,_,_,_) in rs]
        out=pydesc.classify_batch(surv,D,L,kcap,True)
        for code,s in out:
            cnt[code]+=1; nsol+= bool(s)
print(dict(cnt),'with solutions:',nsol)
