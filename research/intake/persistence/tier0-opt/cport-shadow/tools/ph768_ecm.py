import sys, time
from sympy import isprime
from sympy.ntheory import ecm
N768 = 10**256 - 10**128 + 1
c = N768 // (434689 * 859393)
t0 = time.time()
try:
    f = ecm(c, B1=20000, B2=1000000, max_curve=60, seed=1)
    print('ecm B1=2e4 B2=1e6, 60 curves: factors found', sorted(f), 'digits', [len(str(x)) for x in sorted(f)], f'{time.time()-t0:.0f}s')
except Exception as e:
    print('ecm: no factor found with B1=2e4 B2=1e6 over 60 curves', repr(e)[:100], f'{time.time()-t0:.0f}s')
