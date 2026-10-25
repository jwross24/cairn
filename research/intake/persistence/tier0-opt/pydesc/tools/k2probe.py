import sys, random
sys.path.insert(0, '/private/tmp/persist-pydesc/prod')
from lattice import Coset
from descent import cut_coset, log3_mod5k
from tier0v2 import ten_adic_K
rng = random.Random(3); hist = {}
for K5 in (6, 9, 14, 20, 30):
    l7, N = log3_mod5k(7, K5)
    co = Coset((0, 0), (1, 0), (0, 1)).intersect(1, l7, 0, N)
    for a in range(0, 7):
        K = ten_adic_K(co, 400, a)
        for Kp in range(max(K + 1, 3), K + 5):
            b0, c0 = 0, 0
            Yp = pow(2, a, 10**Kp) * pow(3, b0, 10**Kp) * pow(7, c0, 10**Kp) % 10**Kp
            co2 = cut_coset(co, a, Yp, Kp)
            K2 = ten_adic_K(co2, 400, a) if co2 else None
            print(K5, a, 'K', K, 'Kp', Kp, 'K2', K2)
