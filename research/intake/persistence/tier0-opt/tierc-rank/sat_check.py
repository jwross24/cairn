import sys, math
sys.path.insert(0, "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierc-rank")
from m0lib import pari, fa, R96, crt_pair


def val(x, p):
    v = 0
    while x % p == 0:
        x //= p
        v += 1
    return v


for base in (3, 7):
    L = 1
    for p, e in fa():
        if p == base:
            continue
        q = p ** e
        o = int(pari.znorder(pari.Mod(base, q)))
        L = L * o // math.gcd(L, o)
    g5 = pow(base, L, 5 ** 96)
    g2 = pow(base, L, 2 ** 96)
    print("base", base, "order of base mod R96 (prime base removed)", L, "v5(g-1) =", val(g5 - 1, 5), "v2(g-1) =", val(g2 - 1, 2))
