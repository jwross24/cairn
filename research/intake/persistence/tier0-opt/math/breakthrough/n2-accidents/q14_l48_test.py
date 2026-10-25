import sys, json, math
sys.dont_write_bytecode = True
sys.path.insert(0, "/Users/jwross/Documents/cairn/research/intake/persistence/tier0")
from lattice import Coset
H1 = "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/math/h1-anchoring/"
D = json.load(open(H1 + "density.json"))
rho = {int(L): int(v["index"]) / int(v["phi"]) for L, v in D.items()}
res = json.load(open(H1 + "l48_result.json"))
rows = {int(k): v for k, v in json.load(open("primes96.json")).items()}
A1 = 50
prev = {24: 12, 48: 24}
print("layered uniform model on s=124416, M=2^9 3^5 (per a; x50 for a=0..49):")
for L, nin, nout, st in res["levels"]:
    if L == 12:
        print(f" L=12 patterns={nin} survivors={nout} (pred {nin*rho[12]:.4g} per a)")
        continue
    pred = nin * rho[L] / rho[prev[L]]
    print(f" L={L} children={nin} survivors={nout} pred_per_a={pred:.4g} pred_x50={pred*A1:.4g} obs/pred_x50={nout/(pred*A1):.3g}")
N48 = 9451e14
for B in (5.291e9, 1e12):
    ps = sorted(p for p in rows if rows[p]["first_level"] <= 48)
    best = [None]
    def dfs(i, prod, co, phi, ch):
        if ch:
            idx = abs(co.u1[0] * co.u2[1] - co.u1[1] * co.u2[0])
            r = idx / phi
            if best[0] is None or r < best[0][0]:
                best[0] = (r, tuple(ch), prod)
        for j in range(i, len(ps)):
            p = ps[j]
            if prod * p <= B:
                dfs(j + 1, prod * p, co.intersect(rows[p]["d3"], rows[p]["d7"], 0, p - 1), phi * (p - 1), ch + [p])
    dfs(0, 1, Coset((0, 0), (1, 0), (0, 1)), 1, [])
    r, ch, pr = best[0]
    print(f"L=48 relaxed DP, budget {B:.2e}: primes {ch} rho_S={r:.3e}; N48*rho_S*50 = {N48*r*A1:.3e} (observed engine-open 17; exact accidents 0)")
print("Poisson 95% upper limit on accident count given 0 observed: 3.0; ratio to registered prediction 42:", round(3.0 / 42, 3))
