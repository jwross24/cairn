import sys, json, math
sys.dont_write_bytecode = True
sys.path.insert(0, "/Users/jwross/Documents/cairn/research/intake/persistence/tier0")
from lattice import Coset

rows = {int(k): v for k, v in json.load(open("primes96.json")).items()}
ps = sorted(rows)
best = {}
budgets = [5.291e9, 1e11, 1e12, 1e14, 1e16, 1e20]
count = 0
def dfs(i, prod, co, phi, chosen):
    global count
    count += 1
    if chosen:
        idx = abs(co.u1[0] * co.u2[1] - co.u1[1] * co.u2[0])
        rho = idx / phi
        for B in budgets:
            if prod <= B and (B not in best or rho < best[B][0]):
                best[B] = (rho, tuple(chosen), prod, idx)
    for j in range(i, len(ps)):
        p = ps[j]
        if prod * p > budgets[-1]:
            continue
        c2 = co.intersect(rows[p]["d3"], rows[p]["d7"], 0, p - 1)
        dfs(j + 1, prod * p, c2, phi * (p - 1), chosen + [p])
dfs(0, 1, Coset((0, 0), (1, 0), (0, 1)), 1, [])
print("subsets visited", count)
for B in budgets:
    r, ch, pr, idx = best[B]
    print(f"budget P<={B:.3e}: best rho_S={r:.4e} (1/{1/r:.4g}) primes={ch} P={pr:.3e}")
json.dump({str(B): dict(rho=v[0], primes=v[1], P=v[2]) for B, v in best.items()}, open("dp_subset_bound.json", "w"))
