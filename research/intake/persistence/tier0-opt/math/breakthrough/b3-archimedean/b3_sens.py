import b3_chain as bc
from mpmath import mp, mpf, log10
import sys

SK = [mpf(1)]; SY = [mpf(1)]
orig = bc.chain
def chain2(ctx, nu, k, a, m, fold=True):
    X, q, K0, K1, Y1 = orig(ctx, nu, k, a, m, fold)
    return X, q, K0, K1, Y1
# rebuild with multipliers by patching constants
import types
src = open('b3_chain.py').read()
src = src.replace("K1 = C(4)", "K1 = SK[0] * C(4)").replace("Y1 = CY(3)", "Y1 = SY[0] * CY(3)")
src = src.replace("K0 = C(3)", "K0 = SK[0] * C(3)").replace("K0 = C(4) * l2", "K0 = SK[0] * C(4) * l2")
ns = {'SK': SK, 'SY': SY, '__name__': 'x'}
exec(src, ns)
def best(k, a):
    b = None
    for m in range(1, k + 1):
        v = ns['bound'](k, a, m)
        if b is None or v < b[1]: b = (m, v)
    return b
if __name__ == '__main__':
    for k in (31, 44):
        for a in (0, 1):
            for e in (0, -3, -6, -9):
                SK[0] = mpf(10) ** e; SY[0] = mpf(10) ** e
                m, v = best(k, a)
                print('k=%d a=%d scale 1e%d (both K,Y): log10 G=%.1f m=%d' % (k, a, e, float(log10(v)), m))
