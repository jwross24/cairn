import sys, math
from sympy import factorint, isprime
from sympy.ntheory import n_order
N256 = 10**128 + 1
N768 = 10**256 - 10**128 + 1
small = {256: [257, 15361, 453377], 768: [434689, 859393]}
for d, N in ((256, N256), (768, N768)):
    c = N
    for p in small[d]:
        assert c % p == 0
        c //= p
    print(f"Phi_{d}(10): {len(str(N))} digits; found primes {small[d]}; cofactor {len(str(c))} digits, probable prime: {isprime(c)}")
    for p in small[d]:
        assert N % p == 0
        o = n_order(10, p)
        f = factorint(p - 1)
        qe = max(q ** e for q, e in f.items()); qmax = max(f)
        cost = sum(e * 2 * math.isqrt(q) for q, e in f.items())
        print(f"  p={p}  ord_p(10)={o}  p-1 = {' * '.join(f'{q}^{e}' if e > 1 else str(q) for q, e in sorted(f.items()))}  largest prime power {qe} (largest prime {qmax})  PH group ops ~ {cost}")
