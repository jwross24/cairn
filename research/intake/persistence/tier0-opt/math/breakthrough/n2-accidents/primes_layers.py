import sys, json
sys.dont_write_bytecode = True
sys.path.insert(0, "/Users/jwross/Documents/cairn/research/intake/persistence/tier0")
from math import gcd, prod
from sympy import primitive_root, factorint, cyclotomic_poly, divisors, n_order
from lattice import Coset
from dlog import discrete_log

def level_primes(L):
    ps = set()
    for d in divisors(L):
        ps |= set(int(p) for p in factorint(int(cyclotomic_poly(d, 10))))
    return sorted(p for p in ps if p not in (2, 3, 5, 7))

rows = {}
for p in level_primes(96):
    g = primitive_root(p)
    d3 = discrete_log(p, 3, g)
    d7 = discrete_log(p, 7, g)
    h = gcd(gcd(p - 1, d3), d7)
    rows[p] = dict(p=p, g=int(g), d3=d3, d7=d7, ord10=int(n_order(10, p)), kappa=(p - 1) // h,
                   first_level=min(L for L in (12, 24, 48, 96) if pow(10, L, p) == 1))

def joint_index(ps):
    co = Coset((0, 0), (1, 0), (0, 1))
    for p in ps:
        co = co.intersect(rows[p]["d3"], rows[p]["d7"], 0, p - 1)
    return abs(co.u1[0] * co.u2[1] - co.u1[1] * co.u2[0])

if __name__ == "__main__":
    Q = prod(rows)
    R96 = (10**96 - 1) // 9
    print("prod(primes)*21 == R_96:", Q * 21 == R96)
    for L in (12, 24, 48, 96):
        ps = [p for p in rows if rows[p]["first_level"] <= L]
        idx = joint_index(ps)
        phi = prod(p - 1 for p in ps)
        indep = prod(rows[p]["kappa"] / (p - 1) for p in ps)
        print(f"L={L} primes={len(ps)} P={prod(ps):.4e} |K|={idx:.4e} rho_joint={idx/phi:.4e} prod_indep_density={indep:.4e} loss={indep/(idx/phi):.3e}")
    for p, r in rows.items():
        print(p, "ord10", r["ord10"], "kappa", r["kappa"], "dens", f'{r["kappa"]/(p-1):.4g}', "lvl", r["first_level"])
    json.dump({str(p): r for p, r in rows.items()}, open("primes96.json", "w"))
