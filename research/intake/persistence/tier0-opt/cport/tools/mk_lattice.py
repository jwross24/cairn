import os, sys
py='/private/tmp/persist-cport/py'
os.chdir(py); sys.path.insert(0,py)
from sympy import primitive_root, factorint
import deepcut as DC
from dlog import discrete_log
W='/private/tmp/persist-cport/'
ps=DC.level_primes()
with open(W+'lattice96.txt','w') as f:
    f.write(f"# prime g log_g(3) log_g(7) nfac [q e]...\n")
    for p in ps:
        g=primitive_root(p)
        l3=discrete_log(p,3%p,g); l7=discrete_log(p,7%p,g)
        fac=factorint(p-1)
        f.write(f"{p} {g} {l3} {l7} {len(fac)} "+' '.join(f"{q} {e}" for q,e in sorted(fac.items()))+"\n")
print(len(ps), max(ps))
Lam=DC.kernel_lattice()
print(DC.shortest(Lam), Lam.index())
open(W+'lattice96.ref','w').write(f"{Lam.index()}\n{Lam.u1}\n{Lam.u2}\n")
