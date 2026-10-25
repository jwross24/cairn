"""synth4.py <out.pkl> <n>: survivors on shallow random lattices (tail of 0-3 digits) with genuine patterns"""
import sys, os, pickle, random
sys.path.insert(0, '/private/tmp/persist-pydesc/prod')
from lattice import Coset
out, nmax = sys.argv[1], int(sys.argv[2])
rng = random.Random(4242)
S = []
for l in open('/private/tmp/persist-pydesc/prod/zf_below_1e4000.txt'):
    if l.startswith('ZF'):
        f = l.split(); a, b, c = int(f[2]), int(f[3]), int(f[4])
        y = 2**a * 3**b * 7**c
        if y >= 10 and len(str(y)) <= 40: S.append((y, a, b, c))
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
    for _ in range(6):
        co = Coset((0, 0), (1, 0), (0, 1))
        for _ in range(rng.randint(1, 5)):
            m = rng.choice([2, 4, 5, 10, 20, 25, 50, 100, 125, 500, 1000, 3125, 9901, 101, 37, 13, 11])
            A, B = rng.randrange(m), rng.randrange(m)
            r = (A * b + B * c) % m if rng.random() < 0.8 else rng.randrange(m)
            nxt = co.intersect(A, B, r, m)
            if nxt is not None: co = nxt
        a2 = a if rng.random() < 0.7 else rng.randint(0, 8)
        rec.append((a2, n % L, eps, tuple(co.v0), tuple(co.u1), tuple(co.u2), M, L, 400))
pickle.dump(rec, open(out, 'wb'))
print(len(rec), 'records')
