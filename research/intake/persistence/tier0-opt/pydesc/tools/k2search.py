import sys, random
sys.path.insert(0, '/private/tmp/persist-pydesc/prod')
from lattice import Coset
from descent import cut_coset
from tier0v2 import ten_adic_K
seed, n = int(sys.argv[1]), int(sys.argv[2])
rng = random.Random(seed)
mods = [2, 3, 4, 5, 7, 8, 9, 10, 16, 20, 25, 50, 100, 125, 500, 1000, 3125, 9901, 101, 37, 13, 11, 73, 137, 17, 41, 271]
trials = bad = 0; hist = {}
while trials < n:
    co = Coset((0, 0), (1, 0), (0, 1))
    for _ in range(rng.randint(1, 6)):
        m = rng.choice(mods); A, B = rng.randrange(m), rng.randrange(m)
        nxt = co.intersect(A, B, rng.randrange(m), m)
        if nxt is not None: co = nxt
    a = rng.randint(0, 12)
    K = ten_adic_K(co, 400, a)
    if K < 1: continue
    b0, c0 = co.v0
    for Kp in range(max(K + 1, 3), K + 5):
        Yp = pow(2, a, 10**Kp) * pow(3, b0, 10**Kp) * pow(7, c0, 10**Kp) % 10**Kp
        co2 = cut_coset(co, a, Yp, Kp)
        assert co2 is not None
        K2 = ten_adic_K(co2, 400, a)
        trials += 1; hist[K2 - Kp] = hist.get(K2 - Kp, 0) + 1
        if K2 != Kp:
            bad += 1
            if bad <= 3: print('K2 != Kp', 'K', K, 'a', a, 'Kp', Kp, 'K2', K2, co.u1, co.u2, co.v0)
print(trials, 'trials', 'K2-Kp histogram', hist, 'violations', bad)
