import sys
sys.dont_write_bytecode = True
sys.path.insert(0, '/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierc-family')
import random, time
from famlib import *

rng = random.Random(7)
bad = 0
for e in (1, 2, 3, 5, 9, 20, 61):
    for _ in range(40):
        u = rng.randrange(1, 5 ** e)
        if u % 5 == 0:
            continue
        x = dlog3_5(u, e)
        bad += pow(3, x, 5 ** e) != u % 5 ** e
for e in (3, 4, 7, 20, 64, 130):
    for _ in range(40):
        u = rng.randrange(1, 1 << e) | 1
        s, t = dlog2(u, e)
        bad += ((-1) ** s * pow(5, t, 1 << e)) % (1 << e) != u
print('dlog failures', bad)

bad = 0
for (e2, e5) in [(3, 1), (5, 2), (7, 3), (4, 4), (2, 2), (6, 1)]:
    lat = klat(e2, e5)
    mod = (1 << e2) * 5 ** e5
    for b in range(-30, 31):
        for c in range(-30, 31):
            one = (pow(3, b, mod) * pow(7, c, mod)) % mod == 1
            bad += one != lat.contains(b, c)
print('klat failures', bad)

bad = 0
for a in (0, 1, 3):
    for L in (8, 12):
        for _ in range(60):
            b0, c0 = rng.randrange(-200, 200), rng.randrange(-200, 200)
            W = (pow(3, b0, 10 ** L) * pow(7, c0, 10 ** L) * 2 ** a) % 10 ** L
            co = window_coset(a, W, L)
            ok = co is not None and co.contains((b0, c0))
            bad += not ok
            if co is not None:
                for _ in range(5):
                    x, y = rng.randrange(-5, 5), rng.randrange(-5, 5)
                    p = (co.v[0] + x * co.lat.a, co.v[1] + x * co.lat.b + y * co.lat.d)
                    m = 10 ** L
                    bad += (pow(3, p[0], m) * pow(7, p[1], m) * 2 ** a - W) % m != 0
print('window failures', bad)

t0 = time.time()
lam = build_lambdas()
print('lambda built', time.time() - t0)
for L in (96, 192, 384, 480):
    t1 = time.time()
    K = klat(L, L)
    S = lam[L].plus(K)
    g = S.index()
    v5 = 0
    while g % 5 ** (v5 + 1) == 0:
        v5 += 1
    print(L, 'index Lambda', lam[L].index(), 'K', K.index(), 'G', g, '= 2^%d * 5^%d * %d' % (v2(g), v5, g // (2 ** v2(g) * 5 ** v5)), round(time.time() - t1, 2))
