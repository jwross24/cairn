import sys, random
sys.dont_write_bytecode = True
from math import log10
from joint import tail_lattice

random.seed(3)
print("K    a   log10 det(Lambda_tail)   K-0.301a   difference")
for K, a in ((40, 0), (40, 10), (40, 20), (80, 0), (80, 30), (120, 60), (160, 100), (200, 0), (200, 150)):
    ds = []
    for t in range(6):
        b = random.randrange(10**3, 10**9)
        c = random.randrange(10**3, 10**9)
        Bt = pow(2, a, 10**K) * pow(3, b, 10**K) * pow(7, c, 10**K) % 10**K
        p, U = tail_lattice(a, Bt, K)
        ds.append(abs(U[0][0] * U[1][1] - U[0][1] * U[1][0]))
    assert len(set(ds)) == 1
    d = ds[0]
    print(f"{K:<4} {a:<3} {log10(d):>14.2f}        {K - 0.30103 * a:>8.2f}   {log10(d) - (K - 0.30103 * a):>8.2f}")
