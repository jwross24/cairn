import time
from common import *
Lam = DC.kernel_lattice()
pats = load_patterns()
print(len(pats), len({p['key'] for p in pats}))
p = [x for x in pats if x['key'][1] == '47888'][0]
co0 = anchor_coset(p, Lam)
for rep in reps_of(p):
    t = time.time()
    r = DC.deep_cut(co0, p['a'], rep, 2, 10**9)
    r2 = deep_cut_inst(co0, p['a'], rep, 2)
    print(rep, r, r2[:4], time.time() - t)
