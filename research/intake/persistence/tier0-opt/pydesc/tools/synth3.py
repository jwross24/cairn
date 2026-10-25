"""synth3.py <out.pkl> <maxlen> <nmax>: like synth.py with extra random congruences on the cut coset"""
import sys, os, pickle, random
sys.path.insert(0, '/private/tmp/persist-pydesc/prod')
from lattice import Coset
from descent import cut_coset
out, maxlen, nmax = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
rng = random.Random(777)
S = []
for l in open('/private/tmp/persist-pydesc/prod/zf_below_1e4000.txt'):
    if l.startswith('ZF'):
        f = l.split(); a, b, c = int(f[2]), int(f[3]), int(f[4])
        y = 2**a * 3**b * 7**c
        if y >= 10 and len(str(y)) <= maxlen: S.append((y, a, b, c))
rng.shuffle(S)
rec = []
for (y, a, b, c) in S[:nmax]:
    s = str(y); n = len(s)
    pos = sorted((int(ch), i) for i, ch in enumerate(reversed(s)) if ch != '1')
    M = tuple(d for d, _ in pos)
    if not M or len(M) > 20: continue
    L = rng.choice([12, 24, 48, 96])
    grp = {}
    for d, i in pos: grp.setdefault(d, []).append(i % L)
    eps = tuple(e for d in sorted(grp) for e in sorted(grp[d]))
    for k in sorted(set([3, rng.randint(3, n + 2), n, n + 1])):
        if k < 3: continue
        co2 = cut_coset(Coset((0, 0), (1, 0), (0, 1)), a, y % 10**k, k)
        if co2 is None: continue
        for _ in range(3):
            co3 = co2
            for _ in range(rng.randint(0, 3)):
                m = rng.choice([2, 3, 4, 5, 7, 8, 9, 10, 16, 25, 125])
                A, B = rng.randrange(m), rng.randrange(m)
                want = rng.random() < 0.6
                r = (A * b + B * c) % m if want else rng.randrange(m)
                nxt = co3.intersect(A, B, r, m)
                if nxt is not None: co3 = nxt
            rec.append((a, n % L, eps, tuple(co3.v0), tuple(co3.u1), tuple(co3.u2), M, L, 400))
pickle.dump(rec, open(out, 'wb'))
print(len(rec), 'records')
