import numpy as np
from scipy.optimize import linprog
def lp(k, K, Y, g0=K_ if False else None):
    pass
def run(k, K, Y, K0=10.0, Z0=10.0):
    n = k + 1
    A = []; b = []
    for j in range(1, k):
        r = np.zeros(n); r[j] = 1; r[:j] -= K; A.append(r); b.append(0)
        r = np.zeros(n); r[j] = 1; r[j + 1:] -= Y; A.append(r); b.append(0)
    bounds = [(0, K0)] + [(0, None)] * (k - 1) + [(0, Z0)]
    res = linprog(-np.ones(n), A_ub=np.array(A), b_ub=b, bounds=bounds, method='highs')
    return -res.fun
for k in (6, 10, 14):
    K = Y = 10.0
    v = run(k, K, Y)
    m = k // 2
    pred = 10 * (1 + K) ** m
    print(k, v, 'two-ended formula min_m', min(10 * (1 + K) ** (m - 1) + 10 * (1 + Y) ** (k - m) for m in range(1, k + 1)), 'one-sided', 10 * (1 + K) ** (k - 1))
