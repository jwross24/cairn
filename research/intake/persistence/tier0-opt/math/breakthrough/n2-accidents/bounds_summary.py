import sys, json, math, itertools
sys.dont_write_bytecode = True
import numpy as np
rows = {int(k): v for k, v in json.load(open("primes96.json")).items()}
ps = sorted(rows)
D = json.load(open("/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/math/h1-anchoring/density.json"))
rho96 = int(D["96"]["index"]) / int(D["96"]["phi"])
B = json.load(open("tierc_budget.json"))
DP = json.load(open("dp_subset_bound.json"))

def large_sieve(X):
    logp = np.array([math.log10(p) for p in ps])
    w = np.array([(p - rows[p]["kappa"]) / rows[p]["kappa"] for p in ps])
    n = len(ps)
    logn = np.zeros(1); J = np.ones(1)
    for i in range(n):
        logn = np.concatenate([logn, logn + logp[i]])
        J = np.concatenate([J, J * w[i]])
    order = np.argsort(logn)
    logn, J = logn[order], np.cumsum(J[order])
    best = (float("inf"), None)
    for lz in np.arange(0, 96, 0.25):
        j = J[np.searchsorted(logn, lz, side="right") - 1]
        val = (X + 10 ** (2 * lz)) / j
        if val < best[0]:
            best = (val, lz)
    return best, J[-1]

(Xbest, lz), Jmax = large_sieve(1.3e97)
print(f"large sieve (independent primes, X=1.3e97): best bound {Xbest[0] if isinstance(Xbest, tuple) else Xbest:.3e} at log10 Z={lz}, J_max={Jmax:.4g}")
tot_phi_over_P = {}
print("DP subset budgets:", {k: (v['rho'], v['primes']) for k, v in DP.items()})
print("vertex  N96  mu(rho96)  sqrtN  LS-bound/N96  " + "  ".join(f"N*rho_S[{float(k):.0e}]" for k in DP))
for s, r in B.items():
    N = r["N96"]
    print(s, f"{N:.3e} {N*rho96:.3e} {math.sqrt(N):.3e} {Xbest/N:.3e} " + " ".join(f"{N*v['rho']:.3e}" for v in DP.values()))
