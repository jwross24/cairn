import sys, pickle
sys.path.insert(0, '/private/tmp/persist-pydesc/prod'); sys.path.insert(1, '/private/tmp/persist-pydesc/work')
from lattice import Coset
import pydesc
rec = pickle.load(open('/private/tmp/persist-pydesc/cap/e14336_b.pkl', 'rb'))
D, L = rec[0][6], rec[0][7]
rs = [r for r in rec if r[6] == D and r[7] == L]
surv = [(a, nu, eps, Coset(v0, u1, u2)) for (a, nu, eps, v0, u1, u2, _, _, _) in rs]
r1 = pydesc.classify_batch(surv, D, L, 400, True); r2 = pydesc.classify_batch(surv, D, L, 399, True); r3 = pydesc.classify_batch(surv, D, L, 400, True)
print('kcap switch', 'consistent' if r1 == r3 == r2 else 'DIFFERENT', len(surv))
print('unsupported params ->', pydesc.classify_batch(surv, D, L, 5, True))
