import random
import numpy as np
from scipy.optimize import linprog


def lp_max(k, K, Y, K0, Z0, extra_tight=None):
    n = k + 1
    A, b = [], []
    for j in range(1, k):
        r = np.zeros(n); r[j] = 1; r[:j] -= K; A.append(r); b.append(0)
        r = np.zeros(n); r[j] = 1; r[j + 1:] -= Y; A.append(r); b.append(0)
    bounds = [(1, K0)] + [(1, None)] * (k - 1) + [(1, Z0)]
    res = linprog(-np.ones(n), A_ub=np.array(A), b_ub=b, bounds=bounds, method='highs')
    return -res.fun, res.x


def formula(k, K, Y, K0, Z0):
    return min(K0 * (1 + K) ** (m - 1) + Z0 * (1 + Y) ** (k - m) for m in range(1, k + 1))


def feasible(x, k, K, Y, K0, Z0, tol=1e-6):
    g = x[:k]
    E_k = x[k]
    S = np.concatenate([[0], np.cumsum(g)])
    E = np.zeros(k + 2)
    E[k] = E_k
    for j in range(k - 1, 0, -1):
        E[j] = E[j + 1] + g[j]
    ok = g[0] <= K0 * (1 + tol) and E_k <= Z0 * (1 + tol)
    for j in range(1, k):
        ok &= g[j] <= K * S[j] * (1 + tol) + tol
        ok &= g[j] <= Y * E[j + 1] * (1 + tol) + tol
    return bool(ok)


def main():
    rng = random.Random(3)
    worst = 0.0
    nfeas = 0
    trials = 0
    for _ in range(60):
        k = rng.randint(3, 14)
        K = 10 ** rng.uniform(0.5, 2)
        Y = 10 ** rng.uniform(0.5, 2)
        K0 = 10 ** rng.uniform(0.5, 2)
        Z0 = 10 ** rng.uniform(0.5, 2)
        v, x = lp_max(k, K, Y, K0, Z0)
        f = formula(k, K, Y, K0, Z0)
        worst = max(worst, abs(v - f) / f)
        nfeas += feasible(x, k, K, Y, K0, Z0)
        trials += 1
    print('LP optimum vs min_m [K0 (1+K)^(m-1) + Z0 (1+Y)^(k-m)]: %d random parameter sets (k 3..14), worst relative error %.2e, witnesses feasible %d/%d' % (trials, worst, nfeas, trials))
    k, K, Y, K0, Z0 = 8, 20.0, 20.0, 10.0, 10.0
    v, x = lp_max(k, K, Y, K0, Z0)
    print('example k=8 K=Y=20: optimum %.6g, formula %.6g, one-sided Baker chain K0 (1+K)^(k-1) = %.6g' % (v, formula(k, K, Y, K0, Z0), K0 * (1 + K) ** (k - 1)))
    print('  witness gaps g_0..g_{k-1}, E_k:', ['%.4g' % t for t in x])
    bad = formula(k, K, Y, K0, Z0) * 0.5
    print('planted negative: LP optimum is above half the formula, so a claimed bound of half the formula is refuted by the witness:', v > bad)
    import math
    kk = 44
    for lK, lY, lz in ((16.7, 18.2, 14.7), (3.0, 3.0, 14.7)):
        def l10sum(a, b):
            hi, lo = max(a, b), min(a, b)
            return hi + math.log10(1 + 10 ** (lo - hi))
        vals = [l10sum(lz + (m - 1) * math.log10(1 + 10 ** lK), lz + (kk - m) * math.log10(1 + 10 ** lY)) for m in range(1, kk + 1)]
        print('k=44, K=10^%.1f, Y=10^%.1f: class-optimal bound 10^%.1f at m=%d' % (lK, lY, min(vals), vals.index(min(vals)) + 1))


def explicit_witness(k, K, Y, K0, Z0):
    from fractions import Fraction as Fr
    K, Y, K0, Z0 = Fr(K), Fr(Y), Fr(K0), Fr(Z0)
    F = [K0 * (1 + K) ** (m - 1) + Z0 * (1 + Y) ** (k - m) for m in range(1, k + 1)]
    ms = F.index(min(F)) + 1
    S = {j: K0 * (1 + K) ** (j - 1) for j in range(1, ms + 1)}
    E = {j: Z0 * (1 + Y) ** (k - j) for j in range(ms, k + 1)}
    nstar = S[ms] + E[ms]
    for j in range(ms + 1, k + 1):
        S[j] = nstar - E[j]
    for j in range(1, ms):
        E[j] = nstar - S[j]
    g = [S[1]] + [S[j + 1] - S[j] for j in range(1, k)]
    return g, E[k], nstar, ms, (K, Y, K0, Z0)


def feasible_exact(g, Ek, k, par):
    K, Y, K0, Z0 = par
    S = [0]
    for t in g:
        S.append(S[-1] + t)
    E = {k: Ek}
    for j in range(k - 1, 0, -1):
        E[j] = E[j + 1] + g[j]
    ok = g[0] <= K0 and Ek <= Z0 and all(t > 0 for t in g)
    for j in range(1, k):
        ok = ok and g[j] <= K * S[j] and g[j] <= Y * E[j + 1]
    return ok


def check_explicit():
    rng = random.Random(11)
    ok = 0
    tot = 0
    for _ in range(300):
        k = rng.randint(3, 14)
        K = 10 ** rng.uniform(0.5, 2)
        Y = 10 ** rng.uniform(0.5, 2)
        K0 = 10 ** rng.uniform(0.5, 2)
        Z0 = 10 ** rng.uniform(0.5, 2)
        g, Ek, nstar, ms, par = explicit_witness(k, K, Y, K0, Z0)
        tot += 1
        ok += bool(feasible_exact(g, Ek, k, par) and sum(g) + Ek == nstar)
    print('explicit closed-form witness (exact rational arithmetic, no LP): feasible and n = min_m F(m) in %d of %d random parameter sets' % (ok, tot))
    g, Ek, nstar, ms, par = explicit_witness(8, 20.0, 20.0, 10.0, 10.0)
    g2 = list(g); g2[3] = g2[3] * 3 // 2 if hasattr(g2[3], 'numerator') else g2[3] * 1.5
    print('planted negative: inflating one gap of the witness breaks feasibility:', not feasible_exact(g2, Ek, 8, par))
    return tot - ok


if __name__ == '__main__':
    main()
    print('EXPLICIT FAILURES:', check_explicit())
