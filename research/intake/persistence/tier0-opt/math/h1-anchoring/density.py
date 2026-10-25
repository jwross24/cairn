import sys, json
sys.path.insert(0, "/Users/jwross/Documents/cairn/research/intake/persistence/tier0")
from sympy import primitive_root, factorint, cyclotomic_poly, divisors
from lattice import Coset
from dlog import discrete_log

def level_primes(L):
    ps = set()
    for d in divisors(L):
        ps |= set(int(p) for p in factorint(int(cyclotomic_poly(d, 10))))
    return sorted(p for p in ps if p not in (2, 3, 5, 7))

out = {}
for L in [int(x) for x in sys.argv[1:]]:
    ps = level_primes(L)
    co = Coset((0, 0), (1, 0), (0, 1))
    phi = 1
    for p in ps:
        g = primitive_root(p)
        co = co.intersect(discrete_log(p, 3 % p, g), discrete_log(p, 7 % p, g), 0, p - 1)
        phi *= p - 1
    det = abs(co.u1[0] * co.u2[1] - co.u1[1] * co.u2[0])
    out[L] = {"primes": len(ps), "index": det, "phi": phi}
    print(L, len(ps), "index", det, "phi", phi, flush=True)
json.dump({str(k): {kk: str(vv) for kk, vv in v.items()} for k, v in out.items()}, open(sys.argv[0].replace("density.py", "density.json"), "w"))
