import json, glob, os, sys, math, collections, time
HERE = os.path.dirname(os.path.abspath(__file__))
T0 = os.path.normpath(os.path.join(HERE, '..', '..', '..', 'tier0')); sys.path.insert(0, T0); sys.dont_write_bytecode = True
from tier0v2 import multisets, two_adic_bound
import numpy as np
rows = []
for f in glob.glob(os.path.join(HERE, '..', 'tierb-lift', 'logs', 'h12_*.jsonl')):
    for l in open(f):
        r = json.loads(l)
        if 'lift24' in r and r['lift24']['children'] > 0 and r['l12_n'] > 0: rows.append(r)
t = time.time()
for r in rows: r['A'] = two_adic_bound(tuple(r['M']))
print('A computed for', len(rows), 'rows in %.1fs' % (time.time() - t))
A = np.array([r['A'] for r in rows], float); k = np.array([r['k'] for r in rows], float)
spp = np.log(np.array([r['l12_n'] / r['npat'] for r in rows])); cpp = np.log(np.array([r['lift24']['children'] / max(r['lift24']['parents'], 1) for r in rows]))
par = np.log(np.array([r['lift24']['parents'] / r['npat'] for r in rows]))
def fit(X, y, name):
    X1 = np.vstack(X + [np.ones_like(y)]).T; c = np.linalg.lstsq(X1, y, rcond=None)[0]; res = y - X1 @ c
    print('%-34s coef %s  resid sd %.3f  R2 %.3f' % (name, np.round(c, 3), res.std(), 1 - res.var() / y.var()))
    return c
print('A range', A.min(), A.max(), 'by k:', {int(kk): (int(A[k == kk].min()), int(A[k == kk].max())) for kk in sorted(set(k))})
fit([k], spp, 'log(l12 surv/pattern) ~ k')
fit([np.log(A + 1)], spp, 'log(l12 surv/pattern) ~ log(A+1)')
fit([k, np.log(A + 1)], spp, 'log(spp) ~ k + log(A+1)')
fit([k], cpp, 'log(children/parent) ~ k')
fit([k, np.log(A + 1)], cpp, 'log(ch/parent) ~ k + log(A+1)')
fit([k], par, 'log(parents24/pattern) ~ k')
fit([k, np.log(A + 1)], par, 'log(par24/pattern) ~ k + log(A+1)')
