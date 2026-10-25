"""k2adic.py <out.pkl> <n> : survivors whose descent takes the 2-adic cut stages with k2 >= 2 (Kp >= a + 2)"""
import sys, pickle, random
sys.path.insert(0, '/private/tmp/persist-pydesc/prod')
from lattice import Coset
from descent import cut_coset, v2
from tier0v2 import ten_adic_K
out, nmax = sys.argv[1], int(sys.argv[2])
rng = random.Random(31337)
rec = []; tries = 0; k2seen = {}
while len(rec) < nmax and tries < 600000:
    tries += 1
    a = rng.randint(0, 6)
    k0 = rng.randint(3, 6)
    b0, c0 = rng.randrange(10**4), rng.randrange(10**4)
    mod0 = 10**k0
    Y0 = pow(2, a, mod0) * pow(3, b0, mod0) * pow(7, c0, mod0) % mod0
    co = cut_coset(Coset((0, 0), (1, 0), (0, 1)), a, Y0, k0)
    if co is None: continue
    K = ten_adic_K(co, 400, a)
    if not 1 <= K <= 8: continue
    v0 = (rng.randrange(-10**6, 10**6), rng.randrange(-10**6, 10**6))
    mod = 10**K
    Y = pow(2, a, mod) * pow(3, v0[0], mod) * pow(7, v0[1], mod) % mod
    s = str(Y).zfill(K)
    if '0' in s or len(s) != K or 9 * Y == mod: continue
    t = v2(abs(9 * Y - mod))
    if a == t or t < K: continue
    pos = [(int(ch), i) for i, ch in enumerate(reversed(s)) if ch != '1']
    for e in range(max(K, a + 1), min(t, K + 8) + 1):
        for d in range(2, 10):
            Yp = Y + 10**K * ((10**(e - K) - 1) // 9) + d * 10**e
            co_s = Coset(v0, co.u1, co.u2)
            if cut_coset(co_s, a, Yp, e + 1) is None: continue
            pat = sorted(pos + [(d, e)])
            M = tuple(x for x, _ in pat); eps = tuple(i for _, i in pat)
            if len(M) > 12: continue
            rec.append((a, rng.randrange(12), eps, tuple(v0), tuple(co.u1), tuple(co.u2), M, 12, 400))
            k2seen[e + 1 - a] = k2seen.get(e + 1 - a, 0) + 1
pickle.dump(rec, open(out, 'wb'))
print(len(rec), 'records from', tries, 'tries; k2 histogram', sorted(k2seen.items()))
