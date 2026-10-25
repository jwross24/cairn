"""synth.py <out.pkl> <maxlen> <nmax> : survivors built from genuine members of S with lattices that fix k tail digits"""
import sys, os, pickle, random
sys.path.insert(0, '/private/tmp/persist-pydesc/prod')
from lattice import Coset
from descent import cut_coset
out, maxlen, nmax = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
rng = random.Random(555)
S = []
for l in open('/private/tmp/persist-pydesc/prod/zf_below_1e4000.txt'):
    if l.startswith('ZF'):
        f = l.split(); a, b, c = int(f[2]), int(f[3]), int(f[4])
        y = 2**a * 3**b * 7**c
        if y >= 10 and len(str(y)) <= maxlen and a <= 3: S.append((y, a, b, c))
print(len(S), 'genuine members up to', maxlen, 'digits')
rng.shuffle(S)
rec = []
for (y, a, b, c) in S[:nmax]:
    s = str(y); n = len(s)
    pos = sorted((int(ch), i) for i, ch in enumerate(reversed(s)) if ch != '1')
    M = tuple(d for d, _ in pos)
    if not M or len(M) > 20: continue
    for L in rng.sample([12, 24, 48, 96], 2):
        for k in sorted(set([3, 4, 5, rng.randint(3, n + 3), n - 1, n, n + 1, n + 2]) ):
            if k < 3: continue
            co = Coset((0, 0), (1, 0), (0, 1))
            co2 = cut_coset(co, a, y % 10**k, k)
            if co2 is None: continue
            grp = {}
            for d, i in pos: grp.setdefault(d, []).append(i % L)
            eps = tuple(e for d in sorted(grp) for e in sorted(grp[d]))
            nu = n % L
            rec.append((a, nu, eps, tuple(co2.v0), tuple(co2.u1), tuple(co2.u2), M, L, 400))
            if rng.random() < 0.3:
                e2 = list(eps); j = rng.randrange(len(e2)); e2[j] = (e2[j] + rng.randrange(1, L)) % L
                rec.append((a, nu, tuple(e2), tuple(co2.v0), tuple(co2.u1), tuple(co2.u2), M, L, 400))
            if rng.random() < 0.2:
                rec.append((a, (nu + 1) % L, eps, tuple(co2.v0), tuple(co2.u1), tuple(co2.u2), M, L, 400))
pickle.dump(rec, open(out, 'wb'))
print(len(rec), 'records')
