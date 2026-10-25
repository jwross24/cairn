"""k2synth.py <out.pkl> <n> : survivors whose descent reaches a child with ten_adic_K = Kp + 1 (and children whose tail has a leading zero)"""
import sys, os, pickle, random
sys.path.insert(0, '/private/tmp/persist-pydesc/prod')
from lattice import Coset
import descent, tier0
from descent import log3_mod5k, log_mod2k, cut_coset
from tier0v2 import ten_adic_K
out, nmax = sys.argv[1], int(sys.argv[2])
rng = random.Random(2026)
rec = []; tries = 0; kinds = {'k2eq_kp1': 0, 'pad': 0}
while len(rec) < nmax and tries < 400000:
    tries += 1
    K5 = rng.choice([8, 12, 20])
    j = rng.choice([3, 4, 5])
    l7, N = log3_mod5k(7, K5)
    co = Coset((0, 0), (1, 0), (0, 1)).intersect(1, l7, 0, N)
    s3, t3, half = log_mod2k(3, j); s7, t7, _ = log_mod2k(7, j)
    co = co.intersect(t3, t7, 0, half)
    a = rng.randint(1, 5)
    K = ten_adic_K(co, 400, a)
    if not 1 <= K <= 8: continue
    v0 = (rng.randrange(-10**6, 10**6), rng.randrange(-10**6, 10**6))
    mod = 10**K
    Y = pow(2, a, mod) * pow(3, v0[0], mod) * pow(7, v0[1], mod) % mod
    s = str(Y).zfill(K)
    if '0' in s or len(s) != K: continue
    pos = [(int(ch), i) for i, ch in enumerate(reversed(s)) if ch != '1']
    d = rng.randint(2, 9)
    e = K; Kp = e + 1
    Yp = Y + d * 10**e
    co_s = Coset(v0, co.u1, co.u2)
    co2 = cut_coset(co_s, a, Yp, Kp)
    if co2 is None: continue
    K2 = ten_adic_K(co2, 400, a)
    if K2 != Kp + 1: continue
    mod2 = 10**K2
    Y2 = pow(2, a, mod2) * pow(3, co2.v0[0], mod2) * pow(7, co2.v0[1], mod2) % mod2
    s2 = str(Y2).zfill(K2)
    extra = s2[0]
    for variant in ('with_x', 'plain'):
        pat = [(x, i) for x, i in pos] + [(d, e)]
        if variant == 'with_x' and extra not in '01': pat.append((int(extra), K2 - 1))
        elif variant == 'with_x': continue
        pat.sort(key=lambda t: (t[0], t[1]))
        M = tuple(x for x, _ in pat); eps = tuple(i for _, i in pat)
        if len(M) > 12: continue
        nu = rng.randrange(12)
        rec.append((a, nu, eps, tuple(v0), tuple(co.u1), tuple(co.u2), M, 12, 400))
        kinds['pad' if extra == '0' else 'k2eq_kp1'] += 1
pickle.dump(rec, open(out, 'wb'))
print(len(rec), 'records from', tries, 'tries', kinds)
