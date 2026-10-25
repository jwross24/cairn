import sys
sys.dont_write_bytecode = True
sys.path.insert(0, '/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierc-family')
import random
from famlib import *
rng = random.Random(3)
c1 = c2 = c3 = 0
ex = None
for a in (0, 1, 3):
    for L in (8, 12):
        m = 10 ** L
        for _ in range(60):
            b0, c0 = rng.randrange(-200, 200), rng.randrange(-200, 200)
            W = (pow(3, b0, m) * pow(7, c0, m) * 2 ** a) % m
            co = window_coset(a, W, L)
            if co is None:
                c1 += 1
                continue
            if not co.contains((b0, c0)):
                c2 += 1
                ex = ex or (a, L, b0, c0)
            p = (co.v[0] + 3 * co.lat.a, co.v[1] + 3 * co.lat.b + 4 * co.lat.d)
            if (pow(3, p[0], m) * pow(7, p[1], m) * 2 ** a - W) % m:
                c3 += 1
print(c1, c2, c3, ex)
