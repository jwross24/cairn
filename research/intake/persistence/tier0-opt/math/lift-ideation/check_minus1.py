import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ldiff
for name in ('393216_222222222222222223', '14336_47888'):
    for L in (24, 48):
        toks = open(os.path.join(ldiff.H, name, f'cfgL{L}.txt')).read().split()
        Lold, Lnew, A, q = (int(t) for t in toks[:4]); pos = 4 + q
        np_ = int(toks[pos]); pos += 1; primes = []
        for i in range(np_):
            p = int(toks[pos]); nf = int(toks[pos + 5]); primes.append(p)
            has_at = pos + 6 + 2 * nf + 2 * Lnew
            has = int(toks[has_at]); pos = has_at + 1 + (p if has else 0)
        print(name, 'Lold', Lold, 'Lnew', Lnew, 'primes', primes, '10^Lold mod p == p-1:', [pow(10, Lold, p) == p - 1 for p in primes])
